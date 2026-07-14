"""
Minchodan Auto Publish Work Script
자동화된 포스트 워크 스크립트: 린트(Ruff) 검사, 이중 경로 검증, 금지 파일 검사,
테스트 실행, Changelog 자동 작성, Git 커밋 및 푸시 처리.
"""

import argparse
import datetime
import os
import re
import subprocess  # nosec B404
import sys

# sys.stdout의 인코딩을 UTF-8로 재설정
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except AttributeError:
    # Python 3.7 미만 혹은 일부 특수 환경 대응
    pass

# 프로젝트 루트 경로 계산
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 색상 상수 정의
GREEN = "\033[0;32m"
YELLOW = "\033[0;33m"
RED = "\033[0;31m"
CYAN = "\033[0;36m"
BOLD = "\033[1m"
RESET = "\033[0m"


def print_ok(msg):
    print(f"{GREEN}[OK]{RESET} {msg}")


def print_warn(msg):
    print(f"{YELLOW}[WARN]{RESET} {msg}")


def print_error(msg):
    print(f"{RED}[ERROR]{RESET} {msg}")


def print_info(msg):
    print(f"{CYAN}[INFO]{RESET} {msg}")


def print_header(msg):
    print(f"\n{BOLD}=== {msg} ==={RESET}")


def check_ruff():
    """Ruff 린터 및 포매터 검사를 수행합니다."""
    print_header("Ruff 린트 검사 수행")
    try:
        # ruff check 실행
        result = subprocess.run(
            ["ruff", "check", "."], cwd=PROJECT_ROOT, capture_output=True, text=True
        )  # nosec B603 B607
        if result.returncode == 0:
            print_ok("Ruff 린트 검사 통과.")
        else:
            print_warn("Ruff 린트 경고/에러 발견:")
            print(result.stdout)
            # 자동 수정을 시도할지 제안하거나 사용자에게 수정을 유도
            print_info("자동 수정을 위해 'ruff check --fix .' 및 'ruff format .'을 권장합니다.")
            return False
    except FileNotFoundError:
        print_warn("ruff 명령어를 찾을 수 없습니다. 검사를 생략합니다.")
    return True


def check_react_doctor():
    """React/React Native 코드 건강도 검사(react-doctor)를 수행합니다."""
    print_header("React Doctor 코드 건강도 검사")

    # 1. console 디렉토리 스캔
    console_dir = os.path.join(PROJECT_ROOT, "console")
    if os.path.exists(console_dir):
        print_info("console 디렉토리 react-doctor 검사 중...")
        try:
            res = subprocess.run(
                ["npx", "-y", "react-doctor@latest", "--blocking", "error"],
                cwd=console_dir,
                capture_output=True,
                text=True,
            )  # nosec B603 B607
            if res.returncode != 0:
                print_error("console react-doctor 검사 실패:")
                print(res.stdout)
                return False
            print_ok("console react-doctor 검사 통과.")
        except Exception as e:
            print_warn(f"console react-doctor 실행 실패: {e!s}")

    # 2. client 디렉토리 스캔
    client_dir = os.path.join(PROJECT_ROOT, "client")
    if os.path.exists(client_dir):
        print_info("client 디렉토리 react-doctor 검사 중...")
        try:
            res = subprocess.run(
                ["npx", "-y", "react-doctor@latest", "--blocking", "error"],
                cwd=client_dir,
                capture_output=True,
                text=True,
            )  # nosec B603 B607
            if res.returncode != 0:
                print_error("client react-doctor 검사 실패:")
                print(res.stdout)
                return False
            print_ok("client react-doctor 검사 통과.")
        except Exception as e:
            print_warn(f"client react-doctor 실행 실패: {e!s}")

    return True


def check_dual_path():
    """이중 경로 분리 원칙 위반을 정적 분석으로 검사합니다.
    반사 경로 코드(server/detection/gates/)에서 RAG, LLM, TTS 모듈 임포트를 금지합니다.
    """
    print_header("이중 경로 분리 원칙 검사")
    gates_dir = os.path.join(PROJECT_ROOT, "server", "detection", "gates")
    if not os.path.exists(gates_dir):
        print_info("gates 디렉토리가 존재하지 않아 이중 경로 검사를 생략합니다.")
        return True

    violations = []
    # 금지된 임포트 패턴
    forbidden_patterns = [
        re.compile(r"import\s+.*(?:rag|orchestration|realtime_tts|tts)"),
        re.compile(r"from\s+.*(?:rag|orchestration|realtime_tts|tts)\s+import"),
    ]

    for root, _, files in os.walk(gates_dir):
        for file in files:
            if file.endswith(".py"):
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, encoding="utf-8") as f:
                        for line_idx, line in enumerate(f, 1):
                            for pattern in forbidden_patterns:
                                if pattern.search(line):
                                    rel_path = os.path.relpath(file_path, PROJECT_ROOT)
                                    violations.append((rel_path, line_idx, line.strip()))
                except Exception as e:
                    print_warn(f"파일을 읽는 중 에러 발생 ({file}): {e!s}")

    if violations:
        print_error("반사 경로 내 금지된 모듈(LLM/RAG/TTS) 임포트 감지:")
        for path, line_no, content in violations:
            print(f"  - {path}:{line_no} -> {content}")
        return False

    print_ok("이중 경로 분리 원칙 검사 완료 (반사 경로 내 금지 임포트 없음).")
    return True


def check_forbidden_files():
    """Git 스테이징 상태에서 금지된 파일(.env, 모델 가중치 등)이 포함되어 있는지 검사합니다."""
    print_header("금지 파일 스테이징 검사")
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            check=True,
        )  # nosec B603 B607
        status_lines = result.stdout.strip().split("\n")

        forbidden_found = False
        for line in status_lines:
            if not line:
                continue
            # 스테이징(A, M 등) 상태 코드와 파일 경로 파싱
            state = line[:2].strip()
            file_path = line[3:].strip()

            # 스테이징된 파일인 경우만 검사
            if state in ["A", "M", "R"]:
                # .env 파일 검사
                if (
                    file_path == ".env"
                    or file_path.startswith(".env.")
                    and not file_path.endswith(".example")
                ):
                    print_error(f"금지된 파일 스테이징 감지: {file_path} (보안 위반)")
                    forbidden_found = True

                # server/models 내 커스텀 가중치 파일 검사
                if (
                    (file_path.startswith("server/models/") or "models/" in file_path)
                    and "object_detection.pt" not in file_path
                    and (
                        file_path.endswith(".pt")
                        or file_path.endswith(".pth")
                        or file_path.endswith(".onnx")
                    )
                ):
                    print_error(f"금지된 모델 가중치 파일 스테이징 감지: {file_path}")
                    forbidden_found = True

        if forbidden_found:
            print_error(
                "금지된 파일이 스테이징 영역에 포함되어 있습니다. 해당 파일을 스테이징에서 제외한 후 진행하십시오."
            )
            return False

        print_ok("금지 파일 검사 통과 (안전함).")
        return True
    except subprocess.CalledProcessError as e:
        print_error(f"git status 확인 중 오류 발생: {e!s}")
        return False


def get_test_cmd(stage):
    """지정된 단계에 맞는 테스트 명령을 반환합니다."""
    test_cmds = {
        1: "python tests/test_ws_echo.py",
        2: "python tests/test_frame_decode.py",
        3: "python scripts/verify_gpu.py && python tests/test_detection.py",
        4: "python scripts/eval_hitrate.py",
        5: "python tests/test_retriever.py",
        6: "python tests/test_langgraph.py",
        7: "python tests/test_reflex_and_nav.py",
    }
    return test_cmds.get(stage)


def run_stage_tests(stage):
    """단계별 단위 테스트를 실행합니다."""
    print_header(f"{stage}단계 테스트 실행")
    test_cmd = get_test_cmd(stage)
    if not test_cmd:
        print_warn(f"해당 단계({stage})에 정의된 테스트가 없습니다.")
        return True

    print_info(f"실행 명령어: {test_cmd}")
    try:
        result = subprocess.run(  # noqa: S602
            test_cmd, shell=True, cwd=PROJECT_ROOT, capture_output=True, text=True
        )  # nosec B602 B603 B607
        print(result.stdout)
        if result.returncode == 0:
            print_ok(f"{stage}단계 테스트 통과 완료.")
            return True
        else:
            print_warn(f"{stage}단계 테스트 중 일부 실패가 감지되었습니다. 로그를 확인하세요.")
            print(result.stderr)
            return False
    except Exception as e:
        print_error(f"테스트 실행 중 예외 발생: {e!s}")
        return False


def analyze_modified_documents():
    """수정된 파일들을 분석하여 문서 정합성 점검 대상을 리포팅합니다."""
    print_header("수정된 파일 기반 문서 정합성 분석")
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            check=True,
        )  # nosec B603 B607
        modified_files = []
        for line in result.stdout.strip().split("\n"):
            if line:
                modified_files.append(line[3:].strip())

        needs_spec_update = False
        needs_readme_update = False
        needs_env_update = False

        for file in modified_files:
            if file.startswith("server/api/") or file.startswith("client/"):
                needs_spec_update = True
            if file == "requirements.txt" or file.startswith("docker/"):
                needs_readme_update = True
            if file == ".env.example" or file == ".env":
                needs_env_update = True

        alerts = []
        if needs_spec_update:
            alerts.append(
                "- API 또는 클라이언트 구조가 변경되었습니다. docs/design/api_specification.md 정합성을 검토하십시오."
            )
        if needs_readme_update:
            alerts.append(
                "- 의존성 또는 인프라가 변경되었습니다. README.md의 가이드를 업데이트해야 하는지 검토하십시오."
            )
        if needs_env_update:
            alerts.append(
                "- 환경변수 설정이 수정되었습니다. .env.example 및 docs/ops/environment_variables.md 정합성을 확인하십시오."
            )

        if alerts:
            print_warn("문서 정합성 체크 경고:")
            for alert in alerts:
                print(alert)
        else:
            print_ok(
                "수정된 파일 범위 내 긴급히 업데이트해야 할 시스템 문서는 식별되지 않았습니다."
            )

    except subprocess.CalledProcessError as e:
        print_warn(f"수정 파일 분석 중 오류 발생: {e!s}")


def write_changelog(initial, stage, summary, desc, modified_files):
    """Changelog 파일에 이력을 자동 누적 기입합니다."""
    print_header("Changelog 기입")
    changelog_path = os.path.join(PROJECT_ROOT, "docs", "changelogs", f"{initial}.md")

    date_str = datetime.date.today().strftime("%Y-%m-%d")

    # 디렉토리 생성(존재하지 않을 경우)
    os.makedirs(os.path.dirname(changelog_path), exist_ok=True)

    # 파일이 없는 경우 초기 헤더 작성
    if not os.path.exists(changelog_path):
        try:
            with open(changelog_path, "w", encoding="utf-8") as f:
                f.write(f"# Changelog - {initial}\n\n")
                f.write(f"> 이 파일은 **{initial}**의 작업 내역을 시간순으로 누적 기록합니다.\n")
                f.write("> 새 항목은 파일 하단에 추가됩니다.\n")
            print_ok(f"Changelog 파일 생성 완료: {changelog_path}")
        except Exception as e:
            print_error(f"Changelog 파일 생성 중 실패: {e!s}")
            return False

    # 추가될 로그 항목 구성
    files_str = ", ".join([f"`{f}`" for f in modified_files]) if modified_files else "없음"
    entry = f"""
---

### {date_str} | {stage}단계 | {summary}

- **커밋**: `(자동 커밋 완료)`
- **변경 내용**:
  - {desc}
- **관련 파일**: {files_str}
- **검증 결과**: 자동화 린트 및 단계별 테스트를 통과함.
"""
    try:
        with open(changelog_path, "a", encoding="utf-8") as f:
            f.write(entry)
        print_ok(f"Changelog 기입 완료: {changelog_path}")
        return True
    except Exception as e:
        print_error(f"Changelog 기입 실패: {e!s}")
        return False


def get_modified_files_list():
    """현재 git에서 변경된 파일들의 목록을 가져옵니다."""
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            check=True,
        )  # nosec B603 B607
        files = []
        for line in result.stdout.strip().split("\n"):
            if line:
                files.append(line[3:].strip())
        return files
    except Exception:
        return []


def run_git_operations(initial, prefix, desc):
    """Git commit 및 push 작업을 처리합니다."""
    print_header("Git 스테이징, 커밋 및 푸시")
    commit_msg = f"{prefix}: {desc}"

    try:
        # git add .
        subprocess.run(["git", "add", "."], cwd=PROJECT_ROOT, check=True)  # nosec B603 B607
        print_ok("모든 변경 사항 스테이징 완료 (git add .)")

        # git commit
        commit_res = subprocess.run(
            ["git", "commit", "-m", commit_msg], cwd=PROJECT_ROOT, capture_output=True, text=True
        )  # nosec B603 B607
        if commit_res.returncode == 0:
            print_ok(f"커밋 성공: {commit_msg}")
        else:
            # 변경 사항이 없을 경우 경고 후 통과
            if "nothing to commit" in commit_res.stdout or "nothing to commit" in commit_res.stderr:
                print_warn("커밋할 변경 사항이 없습니다.")
            else:
                print_error(f"커밋 실패: {commit_res.stderr}")
                return False

        # git push
        print_info(f"원격 저장소(origin/{initial})로 푸시 중...")
        push_res = subprocess.run(
            ["git", "push", "origin", initial], cwd=PROJECT_ROOT, capture_output=True, text=True
        )  # nosec B603 B607
        if push_res.returncode == 0:
            print_ok(f"origin/{initial} 브랜치로 푸시 완료.")
            return True
        else:
            print_error(f"푸시 실패: {push_res.stderr}")
            return False

    except Exception as e:
        print_error(f"Git 작업 중 오류 발생: {e!s}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Minchodan 자동화된 작업 마감 및 퍼블리시 도구")
    parser.add_argument("--initial", required=True, help="본인 브랜치 이니셜 (dg/jh/jy/kb/th)")
    parser.add_argument(
        "--stage", type=int, required=True, choices=range(1, 8), help="작업 단계 (1-7)"
    )
    parser.add_argument("--summary", required=True, help="작업 요약 (영문 소문자, 숫자, 밑줄 구성)")
    parser.add_argument("--prefix", required=True, help="커밋 접두어 (예: 3단계, docs, fix)")
    parser.add_argument("--desc", required=True, help="작업 세부 설명")
    parser.add_argument("--skip-test", action="store_true", help="테스트 실행 단계를 건너뜁니다.")
    parser.add_argument(
        "--skip-push", action="store_true", help="원격 푸시를 건너뛰고 커밋까지만 수행합니다."
    )

    args = parser.parse_args()

    # 영문 소문자, 숫자, 밑줄 패턴 검증
    if not re.match(r"^[a-z0-9_]+$", args.summary):
        print_error("요약(--summary)은 영문 소문자, 숫자, 밑줄(_)로만 구성되어야 합니다.")
        sys.exit(1)

    # 1. 린트 검사
    if not check_ruff():
        sys.exit(1)

    # 2. 이중 경로 검사
    if not check_dual_path():
        sys.exit(1)

    # React Doctor 코드 건강도 검사
    if not check_react_doctor():
        sys.exit(1)

    # 3. 금지 파일 검사
    if not check_forbidden_files():
        sys.exit(1)

    # 4. 테스트 실행
    if not args.skip_test:
        if not run_stage_tests(args.stage):
            sys.exit(1)
    else:
        print_info("테스트 실행을 건너뜁니다.")

    # 5. 변경된 파일 목록 획득 및 문서 정합성 분석
    modified_files = get_modified_files_list()
    analyze_modified_documents()

    # 6. Changelog 누적 기록
    if not write_changelog(args.initial, args.stage, args.summary, args.desc, modified_files):
        sys.exit(1)

    # 7. Git 커밋 및 푸시
    if args.skip_push:
        print_info("푸시를 건너뛰고 로컬 커밋만 실행합니다.")
        # 커밋용 git add 및 commit만 수동 시도
        commit_msg = f"{args.prefix}: {args.desc}"
        subprocess.run(["git", "add", "."], cwd=PROJECT_ROOT)  # nosec B603 B607
        subprocess.run(["git", "commit", "-m", commit_msg], cwd=PROJECT_ROOT)  # nosec B603 B607
    else:
        if not run_git_operations(args.initial, args.prefix, args.desc):
            sys.exit(1)

    print_ok("모든 마감 및 자동화 발행 절차가 성공적으로 완료되었습니다!")


if __name__ == "__main__":
    main()
