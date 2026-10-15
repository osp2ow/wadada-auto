# wadada-auto

고양이 와다다(@wadada_cat)가 매일 재밌는 이슈를 물어다 주는 인스타 자동 게시 저장소.

## 하루 흐름

| 시간 (한국) | 무엇이 | 하는 일 |
|---|---|---|
| 오전 11시경 | Claude Code 루틴 | 이슈 3개 골라 원고 작성 → `claude/posts-날짜` 브랜치 푸시 |
| 바로 이어서 | GitHub Actions (초안 미리보기) | 카드 이미지 렌더링 → **[승인 대기] PR** 생성 |
| 1시 전까지 | 나 | GitHub 앱에서 PR 보고 **Merge = 승인** |
| 13:05 / 14:05 / 15:05 | GitHub Actions (인스타 게시) | 승인된 카드 1개씩 게시 |

- 늦게 승인해도 18시까지 매시 5분에 밀린 것부터 하나씩 올라감
- 특정 카드만 빼려면 그 폴더에 `skip` 빈 파일을 넣고 Merge
- 수동 게시: Actions → 인스타 게시 → Run workflow → "지금 바로 다음 것"

## 폴더

```
posts/2026-10-16/1/post.json      원고 (루틴이 작성)
posts/2026-10-16/1/slide-1.jpg    카드 이미지 (Actions가 렌더링)
posts/2026-10-16/1/published.json 게시 기록 (게시 후 생성)
template/card.html                카드 디자인
scripts/render.py                 카드 렌더링
scripts/publish.py                인스타 게시
scripts/validate.py               원고 형식 검사
CLAUDE.md                         루틴이 따르는 작업 지침 (주제, 금지 이슈, 말투)
```

## 필요한 Secret

- `IG_ACCESS_TOKEN` — wadada_cat 인스타 토큰 (60일마다 갱신 필요)

폰트: [Pretendard](https://github.com/orioncactus/pretendard) (SIL OFL 1.1)
