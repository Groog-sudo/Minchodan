# 2026-07-14 Commit Note

## Commit Message

style(console): 회원등록 폼 1열 세로 정렬 및 등록 버튼 높이 조정

## Staged Changes (정확 기준)

- 대상 파일: `console/src/styles.css`
- `.member-form` 레이아웃을 다열 자동 배치에서 1열 고정으로 변경
  - `grid-template-columns: 1fr`
  - `row-gap: 16px`, `column-gap: 0`
- `.member-form label` 간격을 `gap` 단일값에서 축별 값으로 조정
  - `row-gap: 14px`, `column-gap: 6px`
- 회원등록 폼 내부 등록 버튼 세로 크기 증가
  - `.member-form .refresh-btn { padding: 10px 10px; }`

## Scope

- 회원관리 페이지의 등록 폼 UI 배치 및 버튼 높이만 변경
- 비즈니스 로직/API/상태관리 변경 없음
