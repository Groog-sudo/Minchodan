# 코드-문서 정합성 검토 핸드오프

> **작성일**: 2026-07-28
> **버전**: v1.0.0
> **대상**: 프로젝트 코드와 문서(AGENTS.md / SKILLS.md / docs/) 간 정합성 검토 및 수정 작업
> **작업 브랜치**: `kb`

---

## 오늘 작업 요약

어제(2026-07-27)부터 오늘에 걸쳐, 3개 영역을 병렬로 조사한 뒤 사용자의 부분 업데이트 후 재점검까지 완료했습니다. 조사는 Explore 에이전트 3종을 병렬 실행하여 수행했습니다.

| 조사 영역 | 조사 방법 | 핵심 결론 |
| :--- | :--- | :--- |
| **코드-문서 기술 스택 정합성** | server/ 및 client/ 실제 구현 vs AGENTS.md §2 Technical Stack 비교 | TTS/STT/카메라/YOLO/LLM/세그멘테이션 7개 항목 중 6건 완전 일치. 게이트 개수만 불일치(이슈 A) |
| **다중 에이전트 진입점·스킬 미러** | AGENTS.md §10 단일 소스 원칙 검증 + `validate_agent_rules.py` 실행 | CLAUDE.md/GEMINI.md/.antigravity/스킬 미러 모두 정합(6/6 통과). 단 pre-commit 미등록(이슈 B) |
| **핵심 문서 간 정합성** | README/AGENTS/design_note/architecture/pipeline/env_vars 교차 검증 | 임베딩 모델·LLM 클라이언트 표기·TTL 수치·상대경로 링크 등 7건 모순 발견 |

---

## 발견된 이슈 현황 (8건)

재점검 완료된 최신 상태 기준입니다. 각 이슈는 코드 그라운드 트루스(정답)와 구식 문서 위치를 명시하여 다음 세션에서 재조사 없이 바로 수정할 수 있도록 정리했습니다.

### H1. architecture.md 섹션 번호 중복 — 미해결

| 항목 | 내용 |
| :--- | :--- |
| **현상** | `docs/design/architecture.md`에 `## 11` 헤더가 두 번 등장 |
| **위치** | L470 `## 11. 학습 환경 전제 (v1.1 C3)` / **L673 `## 11. 필드 테스트 개선 (2026-07-17, M1-M7)` ← 중복** |
| **조치** | L673의 `## 11`을 `## 15`로 번호 재지정 (현재 §14 Post-MVP 이후) |
| **비고** | §13 중복은 이전 보고와 달리 현재 단일로 정리됨. `environment_variables.md` 헤더(L7)가 본 파일의 "10절·13.4절"을 설계 기준으로 참조하므로 번호 정리 필요 |

### H2. 임베딩 모델 2원화 (nomic vs bge-m3) — 부분해결

| 항목 | 내용 |
| :--- | :--- |
| **현상** | 생활지원(convenience) RAG 임베딩이 문서마다 다름 |
| **코드 정답** | `EMBEDDING_MODEL=nomic-embed-text`(보행 수칙 기본) + `CONVENIENCE_EMBEDDING_MODEL=bge-m3`(생활지원 폴백). `environment_variables.md` §2.3/§2.16에 이중 명세 |
| **해결됨** | `README.md` L62/L240/L251, `deployment_guide.md` L107-113 — bge-m3 용도 분리 명시 |
| **미해결(구식)** | `AGENTS.md` L41/L166(nomic 단일), `architecture.md` L25/L272/L428/L443(nomic 단일), `minchodan_design_note.md` L123/L124/L200(nomic 단일) |
| **조치 결정 필요** | AGENTS.md §2에 bge-m3/생활지원 RAG 이중 임베딩을 명시할지, 아니면 AGENTS.md는 상위 원칙이므로 nomic만 유지하고 상세 문서로 위임할지 정책 결정 필요 |

### H3. LLM 클라이언트 표기 (ChatOllama vs SimpleOllamaClient) — 미해결

| 항목 | 내용 |
| :--- | :--- |
| **현상** | 6단계 LLM 호출 클라이언트가 구식 `ChatOllama`/`BaseChatModel`로 표기됨 |
| **코드 정답** | `server/orchestration/llm_client_factory.py:51/94/138` — `SimpleOllamaClient`/`SimpleOpenAIClient`/`SimpleGeminiClient` raw 구현. `ChatOllama`/`BaseChatModel` 미사용. `langchain_core.messages` 스키마만 import |
| **정확한 문서** | `AGENTS.md` §2 L40, `pipeline_stage_design.md` §5.6 L131, `architecture.md` §2 L24 |
| **미해결(구식)** | `architecture.md` L90/§4 L193/§4 L196/§9 L427, `minchodan_design_note.md` §6 L156/L159 |
| **자기모순** | `architecture.md` 내부에서 L24는 raw Simple\*로 정확, L90/193/196/427은 ChatOllama로 오기 |
| **조치** | 구식 6곳을 `SimpleOllamaClient(gemma4-e4b)`로 통일. `BaseChatModel` 표기는 "BaseChatModel과 호환되는 클라이언트"(코드 주석 L216)로 정정 |

### H4. camera-frame-capture 전송 방식 (base64 vs 바이너리) — 미해결

| 항목 | 내용 |
| :--- | :--- |
| **현상** | AGENTS.md 스킬 표가 구식 "base64 전송"으로 남음 |
| **코드 정답** | 바이너리(raw JPEG) 전송이 기본, base64는 폴백. `architecture.md` L335 "2026-07-07부터 base64 미경유 바이너리", `api_specification.md` §3.1, `design_note` §2 일치 |
| **미해결(구식)** | `AGENTS.md` §8 스킬 표 L164 `이중 캡처(...), base64 전송` |
| **정확한 표현** | `SKILLS.md` L90 `바이너리(raw JPEG) 전송(base64는 폴백)` |
| **조치** | AGENTS.md L164 한 줄을 SKILLS.md L90 표현으로 동기화 |

### H5. 상대경로 링크 깨짐 — 부분해결

| 항목 | 내용 |
| :--- | :--- |
| **현상** | `docs/design/` 하위 문서들이 존재하지 않는 상대경로 참조 |
| **해결됨** | architecture.md의 `environment_variables.md`(L464/L466), `field_test_improvement_plan.md`(L675) 링크는 `../ops/`, `../research/`로 정정됨 |
| **미해결(깨진 링크)** | `course_codebase_guide.md` 3곳: design_note L8, architecture L6, pipeline_stage_design L6 → `../dev-guides/course_codebase_guide.md`<br>`post_mvp_hybrid_roadmap.md` 3곳: design_note L207, architecture L645/L669 → `../research/post_mvp_hybrid_roadmap.md`<br>`environment_variables.md` 1곳: architecture L435 → `../ops/environment_variables.md` |
| **비고** | AGENTS.md/SKILLS.md는 올바른 절대 상대경로(`docs/dev-guides/...`) 사용. 정본(AGENTS.md)과 설계 문서 간 정합성 깨짐 |

### H6. Surface 억제 TTL 수치 (15초 vs 60초) — 미해결

| 항목 | 내용 |
| :--- | :--- |
| **현상** | 노면 surface 경보 억제 TTL 수치가 설계 문서와 코드/운영 문서가 다름 |
| **코드 정답** | `server/tts/suppressor.py:29` `REFLEX_SURFACE_SUPPRESS_TTL_S = int(os.getenv("REFLEX_SURFACE_SUPPRESS_TTL_S", "60"))` — **60초**. 상향 이력: 15→30→60초(2회 상향) |
| **정확한 문서** | `environment_variables.md` §2.6 L114(60초, 상향 이력 명시), `.env.example` L118(60초) |
| **미해결(구식)** | `architecture.md` L199/L306/L504(15초), `pipeline_stage_design.md` §5.7 L138(15초) |
| **조치** | 설계 문서 4곳을 60초로 정정, 상향 이력(15→30→60) 주석 추가 |

### A. 게이트 개수 (이중 → 3중) — 미해결

| 항목 | 내용 |
| :--- | :--- |
| **현상** | AGENTS/SKILLS/yolo SKILL 3종이 "이중 게이트" 명시, 실제 코드는 3중 게이트 |
| **코드 정답** | `server/detection/gates/`에 게이트 3개: `reflex_gate.py`, `surface_gate.py`, **`head_level_gate.py`**. `detection_pipeline.py:19/385`에서 head_level_gate import 및 호출 |
| **정확한 문서** | `architecture.md` L177, `api_specification.md` L293/L314/L322 — 3중 게이트 정확히 문서화 |
| **미해결(구식)** | `AGENTS.md` §8 L165 `이중 게이트`, `SKILLS.md` L35/L91, `.agents/skills/yolo-obstacle-detection/SKILL.md` L6/L13/L20/L28/L35 |
| **조치** | "이중 게이트(Reflex Gate + Surface Gate)" → "3중 게이트(Reflex Gate + Surface Gate + Head Level Gate)"로 통일 |
| **미러 주의** | SKILL.md 수정 시 `.agents/skills/`와 `.claude/skills/` 양쪽 동시 반영 + `.antigravity/rules.md`(요약본 6,310자) 동기화 검토 |

### B. validate_agent_rules.py pre-commit 미등록 — 미해결

| 항목 | 내용 |
| :--- | :--- |
| **현상** | 검증 스크립트는 존재하고 6/6 통과하지만 pre-commit에 등록되지 않아 커밋 시 자동 실행 안 됨 |
| **현재 상태** | `scripts/validate_agent_rules.py`(10,805 bytes) 존재, 6개 항목 검증(CLAUDE/GEMINI/.antigravity/cursor/스킬 미러/@SKILLS import) 모두 통과 |
| **미해결** | `.pre-commit-config.yaml`에 등록된 hook은 ruff-format/ruff/bandit/trailing-whitespace/end-of-file-fixer/check-yaml/check-toml/check-merge-conflict만. validate_agent_rules 미등록 |
| **조치** | `.pre-commit-config.yaml`에 local repo hook으로 등록<br>`files: '^(AGENTS\.md\|CLAUDE\.md\|GEMINI\.md\|\.antigravity/rules\.md\|\.cursor/rules/.*\.mdc\|\.agents/skills/.*\|\.claude/skills/.*)$'` |
| **비고** | AGENTS.md §10 "pre-commit이 검증한다" 규칙을 실제로 충족시키는 조치 |

---

## 다음 세션 진행 방향 (우선순위 제안)

| 순위 | 이슈 | 작업 범위 | 예상 난이도 |
| :--- | :--- | :--- | :--- |
| **1순위** | H4 | AGENTS.md L164 한 줄 수정 | 매우 쉬움(1줄) |
| **1순위** | A | AGENTS.md §8 + SKILLS.md + yolo SKILL.md(미러 양쪽) + .antigravity/rules.md 동기화 | 쉬움(표현 통일) |
| **2순위** | H3 | architecture.md(4곳) + design_note(2곳) ChatOllama→SimpleOllamaClient | 중간(6곳 정정) |
| **2순위** | H6 | architecture.md(3곳) + pipeline_stage_design.md(1곳) 15초→60초 | 쉬움(수치 정정) |
| **3순위** | H1 | architecture.md §11 중복 → §15 재번호 (이후 섹션 밀림 확인 필요) | 중간(구조 수정) |
| **3순위** | H5 | course_codebase(3곳)/post_mvp(3곳)/env_vars(1곳) 상대경로 정정 | 쉬움(링크 정정) |
| **4순위** | H2 | **정책 결정 필요**: AGENTS.md에 bge-m3 이중 임베딩 명시 여부 | 결정 후 적용 |
| **4순위** | B | .pre-commit-config.yaml에 validate_agent_rules 훅 등록 | 쉬움(YAML 추가) |

---

## 코드 그라운드 트루스 참조 (정답 위치)

다음 세션에서 재조사 없이 바로 수정 가능하도록, 각 이슈의 "정답"이 되는 코드 위치를 정리합니다.

| 이슈 | 정답 코드/문서 위치 |
| :--- | :--- |
| H3 LLM 클라이언트 | `server/orchestration/llm_client_factory.py:51`(SimpleOllamaClient), `:94`(SimpleOpenAIClient), `:138`(SimpleGeminiClient) |
| H4 전송 방식 | `architecture.md:335`(2026-07-07 바이너리 확정) |
| H6 Surface TTL | `server/tts/suppressor.py:29`(기본 60초), `environment_variables.md` §2.6(상향 이력) |
| A 게이트 개수 | `server/detection/gates/`(3파일), `detection_pipeline.py:19/385` |
| H2 임베딩 | `environment_variables.md` §2.3(nomic)/§2.16(CONVENIENCE_EMBEDDING_MODEL bge-m3 폴백) |

---

## 주의사항

- **스킬 미러**: `.agents/skills/`(정본) 수정 시 반드시 `.claude/skills/`(사본)에 동일 반영. `diff -rq`로 검증. 현재 MD5 전수 일치 상태 유지 중
- **요약본 동기화**: `.antigravity/rules.md`(6,310자 요약본)은 AGENTS.md §8 게이트 표현 변경 시 동기화 검토 대상(12,000자 캡 대응 요약본)
- **단일 소스 원칙**: 규칙 편집은 항상 AGENTS.md에서. CLAUDE.md/GEMINI.md는 pointer/symlink만 유지
- **Changelog 의무**: 본 작업 완료 후 `docs/changelogs/kb.md`에 엔트리 추가 필수(SKILLS.md PROHIBITED ACTIONS #7)
- **이중 경로 분리**: 반사 경로(`server/detection/gates/`)에서 오케스트레이션/RAG/TTS 임포트 금지 원칙은 현재 완벽히 준수 중(본 검토에서 위반 0건)

---

## 재현/검증 방법

- **정합성 검증 스크립트**: `python3 scripts/validate_agent_rules.py`(다중 에이전트 진입점 6종 검증, 현재 6/6 통과)
- **스킬 미러 검증**: `diff -rq .agents/skills/ .claude/skills/`(출력 없으면 일치)
- **코드 품질 검증**: `ruff check . ; bandit -r server/ scripts/ ; mypy server/ ; jscpd ; pip-audit -r requirements.txt`(AGENTS.md §5)
- **상대경로 링크 검증**: 각 문서의 markdown 링크를 클릭하거나 `grep -nE '\]\([^)]+\)'`로 추출 후 존재 여부 확인
