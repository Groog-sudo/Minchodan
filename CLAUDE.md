# Claude Code Entry Point (Thin Pointer)

이 파일은 Claude Code 자동 로드를 위한 진입점 포인터입니다.
본 파일 자체에는 규칙 내용을 두지 않으며, **정본 규칙은 `AGENTS.md`(단일 진실 원천)** 에만 존재합니다.

`AGENTS.md` 최상단의 `@SKILLS.md` import 구문까지 함께 확장되어, Claude Code 세션 시작 시 아래 체인이 자동 주입됩니다.

```text
CLAUDE.md (@AGENTS.md) → AGENTS.md (@SKILLS.md) → SKILLS.md
```

> **편집 규칙**: 규칙을 변경할 때는 본 파일이 아닌 `AGENTS.md`만 편집합니다.
> 다중 에이전트 진입점 아키텍처의 전체 구조는 `AGENTS.md` §10과
> [`docs/dev-guides/multi_agent_setup.md`](docs/dev-guides/multi_agent_setup.md)를 참조.

@AGENTS.md
