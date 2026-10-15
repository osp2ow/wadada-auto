"""카드 이미지 렌더러.

posts/<날짜>/<슬롯>/post.json 을 읽어서 같은 폴더에 slide-1.jpg, slide-2.jpg ... 를 만듭니다.

사용법:
  python scripts/render.py                 # 이미지가 없는 게시물만 렌더링
  python scripts/render.py --force         # 전부 다시 렌더링
  python scripts/render.py posts/2026-10-15/1   # 특정 게시물만
"""
import io
import json
import sys
from pathlib import Path

from PIL import Image
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
TEMPLATE = (ROOT / "template" / "card.html").read_text(encoding="utf-8")
HANDLE = "@wadada_cat"
MAX_SLIDES = 3


def load_post(post_dir: Path) -> dict:
    data = json.loads((post_dir / "post.json").read_text(encoding="utf-8"))
    slides = data.get("slides") or []
    if not slides:
        raise ValueError(f"{post_dir}: slides가 비어 있음")
    if len(slides) > MAX_SLIDES:
        raise ValueError(f"{post_dir}: 슬라이드는 최대 {MAX_SLIDES}장")
    return data


def build_html(post: dict, date_str: str, index: int) -> str:
    _, m, d = date_str.split("-")
    data = {
        "category": post.get("category", "밈·화제"),
        "date": f"{int(m)}.{int(d)}",
        "slideIndex": index,
        "total": len(post["slides"]),
        "handle": HANDLE,
        "sources": [s["name"] if isinstance(s, dict) else s for s in post.get("sources", [])][:3],
        "slides": post["slides"],
    }
    payload = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    start = TEMPLATE.index("/*__DATA__*/")
    end = TEMPLATE.index("/*__END__*/") + len("/*__END__*/")
    return TEMPLATE[:start] + payload + TEMPLATE[end:]


def render_post(page, post_dir: Path) -> list[Path]:
    post = load_post(post_dir)
    date_str = post_dir.parent.name
    for old in post_dir.glob("slide-*.jpg"):
        old.unlink()
    outputs = []
    tmp = ROOT / "template" / "_render.html"  # 폰트 상대경로를 쓰려고 template 폴더에 임시 파일 생성
    for i in range(len(post["slides"])):
        tmp.write_text(build_html(post, date_str, i), encoding="utf-8")
        page.goto(tmp.as_uri(), wait_until="load")
        page.wait_for_selector("body[data-ready='1']", state="attached", timeout=15000)
        png = page.screenshot(type="png", clip={"x": 0, "y": 0, "width": 1080, "height": 1350})
        out = post_dir / f"slide-{i + 1}.jpg"
        # 인스타 API는 JPEG만 받음
        Image.open(io.BytesIO(png)).convert("RGB").save(out, "JPEG", quality=92, optimize=True)
        outputs.append(out)
    tmp.unlink(missing_ok=True)
    return outputs


def find_targets(args: list[str]) -> list[Path]:
    force = "--force" in args
    paths = [a for a in args if not a.startswith("--")]
    if paths:
        return [Path(p).resolve() for p in paths]
    targets = []
    for pj in sorted((ROOT / "posts").glob("*/*/post.json")):
        d = pj.parent
        if force or not (d / "slide-1.jpg").exists() or (d / "slide-1.jpg").stat().st_mtime < pj.stat().st_mtime:
            targets.append(d)
    return targets


def main():
    targets = find_targets(sys.argv[1:])
    if not targets:
        print("렌더링할 게시물 없음")
        return
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1080, "height": 1350}, device_scale_factor=1)
        for d in targets:
            outs = render_post(page, d)
            print(f"렌더링 완료: {d.relative_to(ROOT)} → {len(outs)}장")
        browser.close()


if __name__ == "__main__":
    main()
