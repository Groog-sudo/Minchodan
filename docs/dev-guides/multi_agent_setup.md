# 다중 에이전트 셋업 가이드 (Multi-Agent Setup)

> **작성일**: 2026-07-17
> **버전**: v1.0
> **목적**: 팀원이 Codex, Claude Code, Cursor, ZCode, opencode, Antigravity, Grok 등 서로 다른 AI 코딩 에이전트를 사용해도, 세션 시작 시 동일한 프로젝트 규칙이 자동으로 로드되도록 통합하는 아키텍처를 설명합니다.

---

## 1. 핵심 원칙: 단일 진실 원천 (Single Source of Truth)

본 프로젝트는 **규칙을 한 곳(AGENTS.md)에서만 편집**하고, 각 에이전트가 요구하는 파일명은 `AGENTS.md`를 가리키는 얇은 진입점(thin pointer / symlink / 요약본)으로만 둡니다. 진입점 자체에 규칙 내용을 복사하지 않습니다.

```text
                 AGENTS.md  (정본, 유일한 편집 대상)
                     |
            @SKILLS.md import (시작 시퀀스/금지 행위 자동 주입)
                     |
   +--------+--------+--------+--------+--------+--------+
   |        |        |        |        |        |        |
 CLAUDE  GEMINI  .antigravity .cursor  (직접)  (직접)
 .md     .md     /rules.md   /rules/  AGENTS  AGENTS
 thin    symlink  요약본     간접참조   .md     .md
pointer  (12k캡대응)                  Codex   ZCode
                                   opencode Grok
```

---

## 2. 에이전트별 자동 로드 매핑

| 에이전트 | 자동 로드 파일 | 진입점 방식 | 비고 |
| :--- | :--- | :--- | :--- |
| **OpenAI Codex** | `AGENTS.md` | 정본 직접 | 원조 구현체, cascade 병합 |
| **ZCode** | `AGENTS.md` | 정본 직접 | 사용자+워크스페이스 병합 |
| **opencode** | `AGENTS.md` + `opencode.json` | 정본 직접 | `opencode.json` 권한 병행 |
| **Grok Build** | `AGENTS.md` | 정본 직접 | 계층적 cascade |
| **Antigravity** | `.antigravity/rules.md` + `AGENTS.md` | 요약본 + 정본 | **12,000자 캡 대응** |
| **Claude Code** | `CLAUDE.md` | thin pointer(`@AGENTS.md`) | import 한 줄 |
| **Cursor** | `.cursor/rules/*.mdc` | 간접 참조 | `00-core-guidelines.mdc`가 AGENTS.md 참조 |

> `GEMINI.md`(symlink→AGENTS.md)는 Antigravity가 루트 GEMINI.md도 읽으므로 보조 진입점으로 유지합니다.

---

## 3. 각 진입점의 역할과 동작

### 3.1 AGENTS.md (정본)

- 프로젝트 규칙의 **유일한 편집 대상**입니다.
- 최상단 `@SKILLS.md` import 구문으로 시작 시퀀스/금지 행위를 자동 주입합니다.
- Codex, ZCode, opencode, Grok은 이 파일을 세션 시작 시 자동 읽습니다.

### 3.2 CLAUDE.md (thin pointer)

- Claude Code는 `CLAUDE.md`를 자동 읽습니다.
- 본 파일은 `@AGENTS.md` import 한 줄만 포함하며, Claude Code가 import를 확장해 AGENTS.md 전체를 주입합니다.
- 규칙을 직접 적지 않습니다(드리프트 방지).

### 3.3 GEMINI.md (symlink)

- `ln -s AGENTS.md GEMINI.md`로 생성된 심볼릭 링크입니다.
- Antigravity가 루트 GEMINI.md를 읽을 때 AGENTS.md 내용이 전달됩니다.
- Windows에서는 `git config core.symlinks true`가 필요합니다.

### 3.4 .antigravity/rules.md (Antigravity 전용 요약본)

- Antigravity workspace rules는 파일당 **12,000자 캡**을 적용합니다.
- AGENTS.md 정본(약 15,000자)이 캡을 초과하므로, 핵심 규칙을 압축한 요약본(약 6,000자)을 별도 유지합니다.
- AGENTS.md의 모든 규칙을 담지는 않지만, 이중 경로 원칙, 코딩 규칙, 금지 행위, Git 전략, 스킬 인덱스 등 행동에 즉시 필요한 규칙은 포함합니다.
- 충돌 시 AGENTS.md 정본이 우선합니다.

### 3.5 .cursor/rules/ (Cursor 전용)

- Cursor는 루트 마크다운을 파일명으로 자동 인식하지 않으므로 `.cursor/rules/*.mdc` 독점 포맷을 사용합니다.
- `00-core-guidelines.mdc`(`alwaysApply: true`)가 항상 로드되며 AGENTS.md를 참조합니다.
- stage별 `.mdc`는 `globs:` 기반으로 작업 경로 진입 시 자동 첨부됩니다.

---

## 4. 정합성 자동 검증 (pre-commit)

`scripts/validate_agent_rules.py`가 커밋 직전에 아래 6가지를 검증합니다.

| 검증 항목 | 내용 |
| :--- | :--- |
| CLAUDE.md thin pointer | `@AGENTS.md` import 포함 + 정본 미복사 |
| GEMINI.md symlink | AGENTS.md를 가리키는 symlink |
| `.antigravity/rules.md` | 존재 + 12,000자 이하 + 핵심 섹션 7개 포함 |
| `.cursor` core rule | `00-core-guidelines.mdc`가 AGENTS.md 참조 |
| 스킬 미러 | `.agents/skills/` 와 `.claude/skills/` 내용 동일 |
| AGENTS.md import | `@SKILLS.md` 구문 존재 |

실행:
```bash
python scripts/validate_agent_rules.py          # 전체 검증
python scripts/validate_agent_rules.py --quiet   # 요약만
```

### pre-commit 훅 연동

`.git/hooks/pre-commit` 파일을 생성하고 실행 권한을 부여합니다:

```bash
#!/bin/sh
# 규칙 파일 변경 시에만 검증 실행
if git diff --cached --name-only | grep -qE '^(AGENTS\.md|CLAUDE\.md|GEMINI\.md|SKILLS\.md|\.antigravity/|\.agents/skills/|\.claude/skills/)'; then
    echo "[pre-commit] 다중 에이전트 규칙 정합성 검증..."
    python scripts/validate_agent_rules.py --quiet || exit 1
fi
```

```bash
chmod +x .git/hooks/pre-commit
```

---

## 5. 규칙 편집 워크플로우

### 5.1 일반 규칙 변경

1. `AGENTS.md`만 편집합니다.
2. 변경 내용이 핵심 규칙(이중 경로, 코딩 규칙, 금지 행위, Git)에 해당하면 `.antigravity/rules.md` 요약본에도 반영합니다.
3. 커밋 시 pre-commit이 정합성을 검증합니다.

### 5.2 스킬 추가/수정

1. `.agents/skills/`(정본)에서 먼저 수정합니다.
2. 동일 내용을 `.claude/skills/`(사본)에 반영합니다.
3. pre-commit이 두 디렉토리의 미러 정합성을 검증합니다.

### 5.3 절대 하면 안 되는 행위

- `CLAUDE.md`, `GEMINI.md`에 규칙 내용을 직접 적기 (단일 소스 붕괴)
- `.antigravity/rules.md`에만 규칙을 추가하고 AGENTS.md에 누락 (요약본은 정본의 부분집합이어야 함)
- `.claude/skills/`만 수정하고 `.agents/skills/`을 그대로 둠 (미러 깨짐)

---

## 6. 신규 에이전트 추가 체크리스트

새로운 에이전트를 도입할 때의 진입점 추가 절차입니다.

| 단계 | 확인 사항 |
| :--- | :--- |
| 1 | 해당 에이전트가 `AGENTS.md`를 네이티브로 읽는가? → 그러면 진입점 추가 불필요 |
| 2 | 별도 파일명을 요구하는가? (예: `FOO.md`) → thin pointer(`@AGENTS.md`) 또는 symlink 생성 |
| 3 | 문자 수 캡이 있는가? → 요약본(예: `.foo/rules.md`)을 12,000자 이하로 별도 생성 |
| 4 | 독점 포맷인가? (예: Cursor `.mdc`) → 해당 포맷에 맞춰 AGENTS.md 참조 파일 생성 |
| 5 | `scripts/validate_agent_rules.py`에 신규 진입점 검증 로직 추가 |
| 6 | 본 가이드 §2 매핑 테이블과 AGENTS.md §10에 신규 에이전트 행 추가 |

---

## 7. Antigravity 12,000자 캡 운영 지침

Antigravity는 규칙 파일당 12,000 Unicode 문자를 초과하면 내용을 자릅니다. 이를 방지하기 위해:

- **정본(AGENTS.md)**: 모든 규칙을 담음 (약 15,000자, 캡 초과이나 Antigravity 외 에이전트용)
- **요약본(`.antigravity/rules.md`)**: 핵심 행동 규칙만 압축 (약 6,000자, 캡 이내)
- pre-commit이 요약본 문자 수와 핵심 섹션 7개(이중 경로 원칙, 반사 경로 LLM 금지, 금지 행위, 이모지, main push 금지, changelog, Router 계층) 포함 여부를 검증합니다.
- AGENTS.md가 지나치게 커지면(예: 20,000자 초과) 비행 원칙 섹션을 별도 문서로 분할하는 것을 검토합니다.

---

## 8. 관련 파일 인덱스

| 파일 | 역할 |
| :--- | :--- |
| `AGENTS.md` | 규칙 정본 (단일 진실 원천), §10에 본 가이드 요약 |
| `SKILLS.md` | 시작 시퀀스, 문서 규칙, 금지 행위 |
| `CLAUDE.md` | Claude Code thin pointer (`@AGENTS.md`) |
| `GEMINI.md` | Antigravity 보조 진입점 (symlink→AGENTS.md) |
| `.antigravity/rules.md` | Antigravity workspace rules 요약본 (12k 캡 대응) |
| `.cursor/rules/00-core-guidelines.mdc` | Cursor 핵심 규칙 (AGENTS.md 참조) |
| `opencode.json` | opencode 권한 설정 |
| `.mcp.json` | MCP 서버 설정 (xcodebuildmcp) |
| `scripts/validate_agent_rules.py` | pre-commit 정합성 검증 스크립트 |
