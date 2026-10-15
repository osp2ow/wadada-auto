"""post.json 형식 검사. 문제가 있으면 종료 코드 1.

사용법: python scripts/validate.py posts/2026-10-16   (폴더 안 모든 게시물)
        python scripts/validate.py posts/2026-10-16/1
"""
import json
import sys
from pathlib import Path

CATEGORIES = {"밈·화제", "생활정보", "IT·신제품", "연예", "스포츠"}


def check(pj: Path) -> list[str]:
    errs = []
    try:
        p = json.loads(pj.read_text(encoding="utf-8"))
    except Exception as e:
        return [f"JSON 파싱 실패: {e}"]
    if p.get("category") not in CATEGORIES:
        errs.append(f"category는 {sorted(CATEGORIES)} 중 하나여야 함")
    if not p.get("topic"):
        errs.append("topic 없음")
    slides = p.get("slides") or []
    if not 1 <= len(slides) <= 3:
        errs.append("slides는 1~3장")
    elif not slides[0].get("headline"):
        errs.append("첫 장에 headline 없음")
    else:
        if len(slides[0]["headline"].replace("**", "")) > 28:
            errs.append("headline이 너무 김 (28자 이내)")
        for i, s in enumerate(slides[1:], start=2):
            if not s.get("heading") or not s.get("body"):
                errs.append(f"{i}번째 장에 heading/body 없음")
            elif len(s["body"].replace("**", "")) > 160:
                errs.append(f"{i}번째 장 body가 너무 김 (160자 이내)")
    if not p.get("caption"):
        errs.append("caption 없음")
    if len(p.get("hashtags", [])) > 15:
        errs.append("hashtags는 15개 이하")
    if p.get("category") != "밈·화제" or p.get("sources"):
        srcs = p.get("sources") or []
        if len(srcs) < 1:
            errs.append("sources 최소 1개 필요")
        for s in srcs:
            if not isinstance(s, dict) or not s.get("name") or not s.get("url"):
                errs.append("sources 항목은 {name, url} 형식")
    return errs


def main():
    targets = []
    for a in sys.argv[1:] or ["posts"]:
        a = Path(a)
        targets += [a / "post.json"] if (a / "post.json").exists() else sorted(a.glob("**/post.json"))
    bad = 0
    for pj in targets:
        errs = check(pj)
        if errs:
            bad += 1
            print(f"✗ {pj}")
            for e in errs:
                print(f"   - {e}")
        else:
            print(f"✓ {pj}")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
