# Changelog - kb (관범)

> 이 파일은 **kb(관범)**의 작업 내역을 시간순으로 누적 기록합니다.
> 새 항목은 파일 하단에 추가됩니다.

---

### 2026-06-24 | 전체 | 문서 기준선 구축

- **커밋**: `docs: 프로젝트 문서 기준선 구축 및 초기 디렉토리 골격 생성`
- **변경 내용**:
  - `minchodan_design_note.md` 7단계 골격을 기반으로 루트 README 작성.
  - 스킬 문서(`skills.md`)와 docs 문서 세트 전체 작성 (AGENTS, architecture, api_specification, test_specification, git_branching_strategy, pipeline_stage_design).
  - `.env.example` 환경변수 템플릿과 `requirements.txt` 파이썬 의존성 초기화.
  - 개인 문서 폴더(`docs/{dg,jh,jy,kb,th}/`)를 제거하고, 모든 설계 문서를 `docs/` 폴더에서 공유로 관리하도록 통일.
  - 디렉토리 골격(`.gitkeep`)을 유지하며, 코드 구현은 각 단계별로 진행 예정.
- **관련 파일**: `README.md`, `skills.md`, `docs/README.md`, `docs/AGENTS.md`, `docs/architecture.md`, `docs/api_specification.md`, `docs/test_specification.md`, `docs/git_branching_strategy.md`, `docs/pipeline_stage_design.md`, `.env.example`, `requirements.txt`
- **검증 결과**: 문서 구조 확인, 링크 정합성 확인
- **비고**: 초기 커밋 기준선. 코드 구현은 1단계(WebSocket Gateway)부터 순차 진행.
