# 문서 기준선 구축

> **작성일**: 2026-06-24
> **작성자**: 초기
> **단계**: 전체 - 프로젝트 초기 셋업

---

## 작업 제목

프로젝트 문서 기준선 구축 및 초기 디렉토리 골격 생성

---

## 변경 내용

- `minchodan_design_note.md` 7단계 골격을 기반으로 루트 README 작성.
- 스킬 문서(`skills.md`)와 docs 문서 세트 전체 작성 (AGENTS, architecture, api_specification, test_specification, git_branching_strategy, pipeline_stage_design).
- `.env.example` 환경변수 템플릿과 `requirements.txt` 파이썬 의존성 초기화.
- 개인 문서 폴더(`docs/{dg,jh,jy,kb,th}/`)를 제거하고, 모든 설계 문서를 `docs/` 폴더에서 공유로 관리하도록 통일.
- 디렉토리 골격(`.gitkeep`)을 유지하며, 코드 구현은 각 단계별로 진행 예정.

---

## 관련 파일

| 파일 경로 | 변경 유형 | 설명 |
| --------- | --------- | ---- |
| `README.md` | 신규 | 프로젝트 루트 README |
| `skills.md` | 신규 | 에이전트 스킬 가이드 |
| `docs/README.md` | 신규 | 문서 인덱스 |
| `docs/AGENTS.md` | 신규 | 코딩·커뮤니케이션 규칙 |
| `docs/architecture.md` | 신규 | 시스템 아키텍처 |
| `docs/api_specification.md` | 신규 | WebSocket API 명세 |
| `docs/test_specification.md` | 신규 | 7단계 검증 기준 |
| `docs/git_branching_strategy.md` | 신규 | Git 브랜칭 전략 |
| `docs/pipeline_stage_design.md` | 신규 | 파이프라인 단계 설계 |
| `.env.example` | 신규 | 환경변수 템플릿 |
| `requirements.txt` | 신규 | 파이썬 의존성 목록 |

---

## 검증 결과

- [x] 문서 구조 확인
- [x] 링크 정합성 확인
- [ ] 단위 테스트 통과 (코드 구현 전)

---

## 비고

초기 커밋 기준선. 코드 구현은 1단계(WebSocket Gateway)부터 순차 진행.
