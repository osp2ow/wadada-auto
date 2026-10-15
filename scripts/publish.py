"""승인된(= main에 머지된) 게시물을 인스타그램에 올립니다.

규칙
- 오늘(한국 시간) 날짜 폴더에서, 아직 안 올린 게시물 중 슬롯 번호가 가장 작은 것 1개를 올립니다.
- 슬롯 시간(SLOT_HOURS)이 아직 안 됐으면 올리지 않습니다. --now 를 주면 시간 무시.
- 올린 뒤 published.json 을 남겨서 중복 게시를 막습니다.

환경변수
  IG_ACCESS_TOKEN   인스타 토큰 (GitHub Secret)
  GITHUB_REPOSITORY owner/repo  (Actions가 자동으로 넣어줌)
  IMAGE_REF         이미지 URL에 쓸 커밋 SHA (Actions가 자동으로 넣어줌)

사용법
  python scripts/publish.py            # 정해진 시간 규칙대로
  python scripts/publish.py --now      # 시간 무시하고 다음 것 바로
  python scripts/publish.py --dry-run  # 실제로 안 올리고 무엇을 올릴지만 출력
  python scripts/publish.py posts/2026-10-15/1   # 특정 게시물
"""
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
API = "https://graph.instagram.com/v24.0"
KST = timezone(timedelta(hours=9))
SLOT_HOURS = {1: 13, 2: 14, 3: 15}  # 슬롯 → 게시 시각(한국 시간)


def call(method: str, path: str, params: dict) -> dict:
    params = {**params, "access_token": os.environ["IG_ACCESS_TOKEN"]}
    url = f"{API}/{path}"
    data = None
    if method == "GET":
        url += "?" + urllib.parse.urlencode(params)
    else:
        data = urllib.parse.urlencode(params).encode()
    req = urllib.request.Request(url, data=data, method=method)
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")
        raise SystemExit(f"인스타 API 오류 ({e.code}) {path}: {body}")


def wait_ready(container_id: str):
    for _ in range(30):
        st = call("GET", container_id, {"fields": "status_code,status"})
        code = st.get("status_code")
        if code == "FINISHED":
            return
        if code in ("ERROR", "EXPIRED"):
            raise SystemExit(f"컨테이너 처리 실패: {st}")
        time.sleep(4)
    raise SystemExit(f"컨테이너 처리 시간 초과: {container_id}")


def build_caption(post: dict) -> str:
    parts = [post.get("caption", "").strip()]
    srcs = [s["name"] if isinstance(s, dict) else s for s in post.get("sources", [])]
    if srcs:
        parts.append("출처: " + ", ".join(srcs))
    tags = [t.lstrip("#").replace(" ", "") for t in post.get("hashtags", [])][:20]
    if tags:
        parts.append(" ".join("#" + t for t in tags))
    return "\n\n".join(p for p in parts if p)[:2200]


def image_urls(post_dir: Path) -> list[str]:
    repo = os.environ["GITHUB_REPOSITORY"]
    ref = os.environ.get("IMAGE_REF", "main")
    rel = post_dir.relative_to(ROOT).as_posix()
    files = sorted(post_dir.glob("slide-*.jpg"), key=lambda p: int(p.stem.split("-")[1]))
    if not files:
        raise SystemExit(f"{rel}: 이미지가 없음 (render.py 먼저 실행)")
    return [f"https://raw.githubusercontent.com/{repo}/{ref}/{rel}/{f.name}" for f in files]


def publish(post_dir: Path) -> dict:
    post = json.loads((post_dir / "post.json").read_text(encoding="utf-8"))
    urls = image_urls(post_dir)
    caption = build_caption(post)
    me = call("GET", "me", {"fields": "user_id,username"})
    ig_id = me["user_id"]

    if len(urls) == 1:
        c = call("POST", f"{ig_id}/media", {"image_url": urls[0], "caption": caption})
        creation_id = c["id"]
    else:
        children = []
        for u in urls:
            c = call("POST", f"{ig_id}/media", {"image_url": u, "is_carousel_item": "true"})
            wait_ready(c["id"])
            children.append(c["id"])
        c = call("POST", f"{ig_id}/media", {
            "media_type": "CAROUSEL", "children": ",".join(children), "caption": caption,
        })
        creation_id = c["id"]

    wait_ready(creation_id)
    res = call("POST", f"{ig_id}/media_publish", {"creation_id": creation_id})
    media = call("GET", res["id"], {"fields": "permalink"})
    record = {
        "media_id": res["id"],
        "permalink": media.get("permalink"),
        "account": me.get("username"),
        "published_at": datetime.now(KST).isoformat(timespec="seconds"),
    }
    (post_dir / "published.json").write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return record


def next_due(now: datetime, ignore_time: bool) -> Path | None:
    day_dir = ROOT / "posts" / now.strftime("%Y-%m-%d")
    candidates = []
    for pj in day_dir.glob("*/post.json"):
        d = pj.parent
        if (d / "published.json").exists() or (d / "skip").exists():
            continue
        slot = int(d.name)
        if not ignore_time and now.hour < SLOT_HOURS.get(slot, 0):
            continue
        candidates.append((slot, d))
    return min(candidates)[1] if candidates else None


def main():
    args = sys.argv[1:]
    dry = "--dry-run" in args
    paths = [a for a in args if not a.startswith("--")]
    target = Path(paths[0]).resolve() if paths else next_due(datetime.now(KST), "--now" in args)
    if not target:
        print("지금 올릴 게시물 없음 (승인 안 됐거나, 이미 다 올렸거나, 아직 시간이 안 됨)")
        return
    rel = target.relative_to(ROOT).as_posix()
    if (target / "published.json").exists():
        print(f"{rel}: 이미 게시됨 — 건너뜀")
        return
    if dry:
        print(f"[dry-run] 올릴 대상: {rel}")
        print(build_caption(json.loads((target / 'post.json').read_text(encoding='utf-8'))))
        return
    rec = publish(target)
    print(f"게시 완료: {rel} → {rec['permalink']}")


if __name__ == "__main__":
    main()
