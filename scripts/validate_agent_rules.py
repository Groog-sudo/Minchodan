#!/usr/bin/env python3
"""
다중 에이전트 규칙 자동 로드 통합 정합성 검증 스크립트 (pre-commit).

단일 진실 원천(AGENTS.md) + 얇은 진입점(thin pointer/symlink/요약본) 아키텍처가
깨지지 않았는지 커밋 직전에 검증합니다.

검증 항목:
  1. CLAUDE.md 가 @AGENTS.md thin pointer 인지 (정본 복사 금지)
  2. GEMINI.md symlink 가 AGENTS.md 를 가리키는지
  3. .antigravity/rules.md 가 존재 + 12,000자 이하 + 핵심 섹션 포함 (Antigravity workspace rules)
  4. .cursor/rules/00-core-guidelines.mdc 가 AGENTS.md 참조 여부
  5. .agents/skills/ 와 .claude/skills/ 내용 동일성 (미러 정합성)
  6. AGENTS.md 에 @SKILLS.md import 구문 존재 여부

사용:
  python scripts/validate_agent_rules.py          # 전체 검증
  python scripts/validate_agent_rules.py --quiet   # 요약만

pre-commit 연동:
  .git/hooks/pre-commit 에서 본 스크립트 호출.
  AGENTS.md/CLAUDE.md/GEMINI.md/.antigravity/.agents/skills/.claude/skills 변경 시에만 실행.
"""

from __future__ import annotations

import argparse
import filecmp
import os
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# 경로는 __file__ 기반으로 계산 (AGENTS.md §5 Pathing 규칙 준수)
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Antigravity 규칙 파일 1개당 문자 수 상한 (공식 문서 기준)
ANTIGRAVITY_CHAR_CAP = 12000

# 검증 대상 진입점/정본 경로
AGENTS_MD = PROJECT_ROOT / "AGENTS.md"
SKILLS_MD = PROJECT_ROOT / "SKILLS.md"
CLAUDE_MD = PROJECT_ROOT / "CLAUDE.md"
GEMINI_MD = PROJECT_ROOT / "GEMINI.md"
ANTIGRAVITY_RULES = PROJECT_ROOT / ".antigravity" / "rules.md"
CURSOR_CORE_RULE = PROJECT_ROOT / ".cursor" / "rules" / "00-core-guidelines.mdc"
AGENTS_SKILLS_DIR = PROJECT_ROOT / ".agents" / "skills"
CLAUDE_SKILLS_DIR = PROJECT_ROOT / ".claude" / "skills"

# .antigravity/rules.md 요약본이 반드시 포함해야 할 핵심 섹션 (드리프트 탐지용)
ANTIGRAVITY_REQUIRED_SECTIONS = [
    "이중 경로 원칙",
    "반사 경로에는 LLM/RAG/실시간 TTS를 절대 경유",
    "금지 행위",
    "이모지",
    "main",
    "changelog",
    "Router",
]


class CheckResult:
    """개별 검증 결과."""

    def __init__(self, name: str, ok: bool, detail: str = "") -> None:
        self.name = name
        self.ok = ok
        self.detail = detail

    def format(self, quiet: bool = False) -> str:
        tag = "PASS" if self.ok else "FAIL"
        line = f"[{tag}] {self.name}"
        if not quiet and self.detail:
            line += f"\n       {self.detail}"
        return line


def read_text(path: Path) -> str:
    """방어적 파일 읽기 (AGENTS.md §5 Defensive Coding)."""
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return ""
    except OSError:
        return ""


def check_claude_is_pointer() -> CheckResult:
    """CLAUDE.md 가 @AGENTS.md thin pointer 인지 검증."""
    if not CLAUDE_MD.exists():
        return CheckResult("CLAUDE.md thin pointer", False, "CLAUDE.md 파일 없음")
    content = read_text(CLAUDE_MD)
    has_import = "@AGENTS.md" in content
    # 정본(AGENTS.md) 전체 내용이 복사되었는지 탐지: AGENTS.md 고유 섹션 제목이 다수 포함되면 드리프트 의심
    canonical_markers = ["## 2. Technical Stack", "## 4. Code Structure", "## 5. AI Coding Rules"]
    copied_count = sum(1 for marker in canonical_markers if marker in content)
    is_pointer = has_import and copied_count == 0
    if is_pointer:
        return CheckResult("CLAUDE.md thin pointer", True, "@AGENTS.md import 포함, 정본 미복사")
    detail = (
        f"@AGENTS.md import={'있음' if has_import else '없음'}, 정본 섹션 {copied_count}개 복사됨"
    )
    return CheckResult("CLAUDE.md thin pointer", False, detail)


def check_gemini_symlink() -> CheckResult:
    """GEMINI.md symlink 가 AGENTS.md 를 가리키는지 검증."""
    if not GEMINI_MD.exists() and not GEMINI_MD.is_symlink():
        return CheckResult("GEMINI.md symlink", False, "GEMINI.md 없음 (symlink 미생성)")
    if not GEMINI_MD.is_symlink():
        return CheckResult(
            "GEMINI.md symlink",
            False,
            "GEMINI.md 가 symlink 가 아님 (일반 파일). `ln -sf AGENTS.md GEMINI.md` 로 재생성",
        )
    target = os.readlink(GEMINI_MD)
    if target == "AGENTS.md":
        return CheckResult("GEMINI.md symlink", True, "AGENTS.md 를 가리킴")
    return CheckResult("GEMINI.md symlink", False, f"대상이 '{target}' 임 (AGENTS.md 여야 함)")


def check_antigravity_rules() -> CheckResult:
    """.antigravity/rules.md 존재 + 12,000자 이하 + 핵심 섹션 포함 여부 검증.

    Antigravity workspace rules 는 파일당 12,000자 캡 적용.
    AGENTS.md 정본이 캡을 초과하므로 별도 요약본을 두며, 이 요약본의
    문자 수와 핵심 규칙 포함 여부를 검증.
    """
    if not ANTIGRAVITY_RULES.exists():
        return CheckResult(
            ".antigravity/rules.md",
            False,
            "파일 없음. Antigravity 가 workspace rules 를 로드하지 못함",
        )
    content = read_text(ANTIGRAVITY_RULES)
    char_count = len(content)
    if char_count > ANTIGRAVITY_CHAR_CAP:
        over = char_count - ANTIGRAVITY_CHAR_CAP
        return CheckResult(
            ".antigravity/rules.md",
            False,
            f"{char_count:,}자, 캡 초과 {over:,}자. 요약본 내용 축소 필요",
        )
    # 핵심 섹션 포함 여부 (요약본 드리프트 탐지)
    missing = [s for s in ANTIGRAVITY_REQUIRED_SECTIONS if s not in content]
    if missing:
        return CheckResult(
            ".antigravity/rules.md",
            False,
            f"핵심 키워드 누락: {missing}. AGENTS.md 변경 시 요약본 동기화 필요",
        )
    margin = ANTIGRAVITY_CHAR_CAP - char_count
    return CheckResult(
        ".antigravity/rules.md",
        True,
        f"{char_count:,}자 (여유 {margin:,}자), 핵심 섹션 {len(ANTIGRAVITY_REQUIRED_SECTIONS)}개 포함",
    )


def check_cursor_references_agents() -> CheckResult:
    """.cursor/rules/00-core-guidelines.mdc 가 AGENTS.md 를 참조하는지 검증."""
    if not CURSOR_CORE_RULE.exists():
        return CheckResult(
            ".cursor core rule AGENTS.md 참조",
            False,
            "00-core-guidelines.mdc 없음",
        )
    content = read_text(CURSOR_CORE_RULE)
    if "AGENTS.md" in content:
        return CheckResult(".cursor core rule AGENTS.md 참조", True, "AGENTS.md 참조 확인")
    return CheckResult(
        ".cursor core rule AGENTS.md 참조",
        False,
        "AGENTS.md 참조 문구 없음",
    )


def _dir_trees_equal(dir_a: Path, dir_b: Path) -> tuple[bool, list[str]]:
    """두 디렉토리 트리의 내용 동일성을 재귀 비교 (deep=True).

    반환: (동일여부, 차이점_메시지_목록)
    방어적 코딩: 어느 한쪽 디렉토리가 없으면 빈 것으로 간주.
    """
    diffs: list[str] = []
    if not dir_a.exists() and not dir_b.exists():
        return True, []
    if not dir_a.exists():
        return False, [f"정본 없음: {dir_a}"]
    if not dir_b.exists():
        return False, [f"사본 없음: {dir_b}"]

    deep = filecmp.dircmp(dir_a, dir_b)
    _collect_dircmp_diffs(deep, dir_a, dir_b, diffs)
    return len(diffs) == 0, diffs


def _collect_dircmp_diffs(dc: filecmp.dircmp, root_a: Path, root_b: Path, diffs: list[str]) -> None:
    """dircmp 결과를 순회하며 차이점을 수집."""
    if dc.left_only:
        diffs.append(f"정본에만 존재: {[str(root_a / n) for n in dc.left_only]}")
    if dc.right_only:
        diffs.append(f"사본에만 존재: {[str(root_b / n) for n in dc.right_only]}")
    if dc.diff_files:
        diffs.append(f"내용 상이: {[str(root_a / n) for n in dc.diff_files]}")
    if dc.funny_files:
        diffs.append(f"비교 불가: {dc.funny_files}")
    for sub_name, sub_dc in dc.subdirs.items():
        _collect_dircmp_diffs(sub_dc, root_a / sub_name, root_b / sub_name, diffs)


def check_skills_mirror() -> CheckResult:
    """.agents/skills/ (정본) 와 .claude/skills/ (사본) 내용 동일성 검증."""
    equal, diffs = _dir_trees_equal(AGENTS_SKILLS_DIR, CLAUDE_SKILLS_DIR)
    if equal:
        return CheckResult(".agents/skills 와 .claude/skills 미러", True, "내용 완전 일치")
    detail = f"{len(diffs)}건 차이: " + " | ".join(diffs[:3])
    if len(diffs) > 3:
        detail += f" ... 외 {len(diffs) - 3}건"
    return CheckResult(".agents/skills 와 .claude/skills 미러", False, detail)


def check_agents_imports_skills() -> CheckResult:
    """AGENTS.md 에 @SKILLS.md import 구문 존재 여부 검증."""
    content = read_text(AGENTS_MD)
    if "@SKILLS.md" in content:
        return CheckResult("AGENTS.md @SKILLS.md import", True, "import 구문 존재")
    return CheckResult(
        "AGENTS.md @SKILLS.md import",
        False,
        "@SKILLS.md 구문 없음. SKILLS.md 가 자동 주입되지 않음",
    )


def run_all_checks(quiet: bool = False) -> int:
    """전체 검증 실행. 실패 건수를 반환 (0 = 전체 통과)."""
    checks: list[CheckResult] = [
        check_claude_is_pointer(),
        check_gemini_symlink(),
        check_antigravity_rules(),
        check_cursor_references_agents(),
        check_skills_mirror(),
        check_agents_imports_skills(),
    ]

    print("=" * 60)
    print("다중 에이전트 규칙 정합성 검증 (pre-commit)")
    print("=" * 60)
    for chk in checks:
        print(chk.format(quiet=quiet))

    failed = [c for c in checks if not c.ok]
    print("-" * 60)
    if failed:
        print(f"검증 실패: {len(failed)}/{len(checks)} 건. 커밋을 중단합니다.")
        print("\n[수정 가이드]")
        print("  - CLAUDE.md/GEMINI.md 에 규칙을 직접 적지 말고 AGENTS.md 만 편집.")
        print("  - .antigravity/rules.md 는 AGENTS.md 변경 시 핵심 섹션 동기화.")
        print("  - 스킬 수정 시 .agents/skills/ 우선, .claude/skills/ 에 동일 반영.")
        return 1
    print(f"검증 통과: {len(checks)}/{len(checks)} 건.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="다중 에이전트 규칙 자동 로드 정합성 검증 (pre-commit)",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="상세 detail 생략, PASS/FAIL 요약만 출력",
    )
    args = parser.parse_args()
    return run_all_checks(quiet=args.quiet)


if __name__ == "__main__":
    sys.exit(main())
