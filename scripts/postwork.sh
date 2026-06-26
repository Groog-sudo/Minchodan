#!/usr/bin/env bash
# =============================================================================
# Script Name : postwork.sh
# Platform    : Linux / macOS (bash)
# Purpose     : Minchodan Post-work 자동화 -- 코딩 규칙 확인, 테스트 실행,
#               changelog 기록, git 커밋/푸시, PR 생성.
# Usage       : bash scripts/postwork.sh  (프로젝트 루트에서 실행)
# =============================================================================
set -euo pipefail

# --- Color codes ---
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
BOLD='\033[1m'
RESET='\033[0m'

print_ok()    { echo -e "${GREEN}[OK]${RESET} $1"; }
print_warn()  { echo -e "${YELLOW}[WARN]${RESET} $1"; }
print_error() { echo -e "${RED}[ERROR]${RESET} $1"; }
print_info()  { echo -e "${CYAN}[INFO]${RESET} $1"; }
print_manual(){ echo -e "${YELLOW}[MANUAL]${RESET} $1"; }
print_header(){ echo -e "\n${BOLD}=== $1 ===${RESET}"; }

# --- Test file lookup ---
get_test_cmd() {
    case "$1" in
        1) echo "python tests/test_ws_echo.py" ;;
        2) echo "python tests/test_frame_decode.py" ;;
        3) echo "python scripts/verify_gpu.py && python tests/test_detection.py" ;;
        4) echo "python scripts/eval_hitrate.py" ;;
        5) echo "python tests/test_rag_retrieval.py" ;;
        6) echo "python tests/test_langgraph.py" ;;
        7) echo "python tests/test_tts_reflex.py" ;;
    esac
}

# Track statuses for summary
COMMIT_MSG=""
PR_STATUS="생략"

# =============================================================================
# Step A -- 기본 정보 입력
# =============================================================================
print_header "Step A: 기본 정보 입력"

# --- 이니셜 ---
read -p "본인 브랜치 이니셜을 입력하세요 (dg/jh/jy/kb/th): " INITIAL
case "$INITIAL" in
    dg|jh|jy|kb|th) print_ok "이니셜: $INITIAL" ;;
    *)
        print_error "잘못된 이니셜 '$INITIAL'. dg, jh, jy, kb, th 중 하나를 입력하세요."
        exit 1
        ;;
esac

# --- 단계 ---
read -p "작업한 파이프라인 단계를 입력하세요 (1-7): " STAGE
if [[ ! "$STAGE" =~ ^[1-7]$ ]]; then
    print_error "잘못된 단계 '$STAGE'. 1~7 사이의 정수를 입력하세요."
    exit 1
fi
print_ok "단계: $STAGE"

# --- 날짜 ---
read -p "오늘 날짜를 입력하세요 (YYYY-MM-DD): " DATE
if [[ ! "$DATE" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}$ ]]; then
    print_error "잘못된 날짜 형식 '$DATE'. YYYY-MM-DD 형식으로 입력하세요."
    exit 1
fi
print_ok "날짜: $DATE"

# --- 작업 요약 ---
read -p "작업 요약을 입력하세요 (영문 소문자, 숫자, 밑줄만 허용, 예: websocket_handshake): " SUMMARY
if [[ ! "$SUMMARY" =~ ^[a-z0-9_]+$ ]]; then
    print_error "잘못된 요약 '$SUMMARY'. 영문 소문자, 숫자, 밑줄만 사용할 수 있습니다."
    exit 1
fi
print_ok "요약: $SUMMARY"

CHANGELOG_FILE="docs/changelogs/${INITIAL}.md"

# =============================================================================
# Step B -- 코딩 규칙 자체 점검 (안내)
# =============================================================================
print_header "Step B: 코딩 규칙 자체 점검"
echo ""
echo "  [코딩 규칙 자체 점검 -- 커밋 전 아래 항목을 확인하세요]"
echo "    [ ] 모든 새 Python 파일 첫 줄: # -*- coding: utf-8 -*- 및 sys.stdout.reconfigure(encoding='utf-8')"
echo "    [ ] 임포트 순서: 표준 라이브러리 -> 외부 라이브러리 -> 로컬 모듈"
echo "    [ ] 절대 경로 하드코딩 없음 (os.path.dirname(os.path.abspath(__file__)) 사용)"
echo "    [ ] 환경 변수: load_dotenv() + os.getenv(key, default) 패턴 적용"
echo "    [ ] 방어적 코딩: None 가드, dict.get(), 예외 후 루프 유지"
echo "    [ ] FastAPI 3계층 구조: Router -> Service -> Repository"
echo "    [ ] 코드 주석, 커밋 메시지, 문서 내 이모지 없음"
echo "    [ ] 모든 파일 UTF-8로 저장"
echo ""

read -p "위 항목을 모두 확인했습니까? (y/N): " CODING_CHECK
if [[ "$CODING_CHECK" != "y" && "$CODING_CHECK" != "Y" ]]; then
    print_warn "코딩 규칙 점검이 확인되지 않았습니다. 위 체크리스트를 검토 후 다시 실행하세요."
    exit 1
fi
print_ok "코딩 규칙 자체 점검 확인 완료."

# =============================================================================
# Step C -- 이중 경로 원칙 위반 확인 (안내)
# =============================================================================
print_header "Step C: 이중 경로 원칙 위반 확인"
echo ""
echo "  [이중 경로 위반 확인]"
echo "    [ ] 반사 경로 코드에 LLM 호출 없음"
echo "    [ ] 반사 경로 코드에 RAG 검색 호출 없음"
echo "    [ ] 반사 경로 코드에 실시간 TTS 합성 호출 없음"
echo "    [ ] 반사 음성이 data/reflex_clips/ 사전합성 클립만 참조"
echo ""

read -p "이중 경로 원칙 위반이 없는 것을 확인했습니까? (y/N): " DUAL_CHECK
if [[ "$DUAL_CHECK" != "y" && "$DUAL_CHECK" != "Y" ]]; then
    print_warn "이중 경로 위반 확인이 되지 않았습니다. 반사 경로 코드를 검토하세요."
    exit 1
fi
print_ok "이중 경로 원칙 확인 완료."

# =============================================================================
# Step D -- 단계별 테스트 실행
# =============================================================================
print_header "Step D: 테스트 실행 ($STAGE단계)"
TEST_CMD=$(get_test_cmd "$STAGE")
print_info "실행 중: $TEST_CMD"
echo ""

eval "$TEST_CMD" || print_warn "일부 테스트가 실패했을 수 있습니다."
echo ""

read -p "모든 테스트를 통과하고 KPI 목표를 달성했습니까? (y/N): " TEST_PASS
if [[ "$TEST_PASS" != "y" && "$TEST_PASS" != "Y" ]]; then
    print_warn "테스트가 완전히 통과되지 않았습니다. 계속 진행하지만 PR 병합 전 수정하세요."
fi

# =============================================================================
# Step E -- Changelog 엔트리 추가
# =============================================================================
print_header "Step E: Changelog 엔트리 추가"

# 팀원 파일이 없으면 생성
if [ ! -f "$CHANGELOG_FILE" ]; then
    cat > "$CHANGELOG_FILE" <<HEADER
# Changelog - $INITIAL

> 이 파일은 **$INITIAL**의 작업 내역을 시간순으로 누적 기록합니다.
> 새 항목은 파일 하단에 추가됩니다.
HEADER
    print_ok "Changelog 파일 생성: $CHANGELOG_FILE"
fi

# 새 엔트리 추가
cat >> "$CHANGELOG_FILE" <<ENTRY

---

### ${DATE} | ${STAGE}단계 | ${SUMMARY}

- **커밋**: \`(postwork 스크립트에서 입력 예정)\`
- **변경 내용**:
  - (작업 완료 후 상세 내용을 직접 기입하세요.)
- **관련 파일**: (변경된 파일 목록을 기입하세요.)
- **검증 결과**: (테스트 결과 및 KPI 달성 여부를 기입하세요.)
ENTRY

print_ok "Changelog 엔트리 추가 완료: $CHANGELOG_FILE"
print_manual "[필수] $CHANGELOG_FILE 파일을 열어 상세 내용을 기입하세요."
echo ""

# =============================================================================
# Step F -- Git 스테이징 안전 검사
# =============================================================================
print_header "Step F: Git 스테이징 안전 검사"

GIT_STATUS=$(git status --short 2>/dev/null || echo "")

FORBIDDEN_FOUND=0
while IFS= read -r line; do
    if [[ -z "$line" ]]; then
        continue
    fi
    FILE_PATH="${line:3}"
    if [[ "$FILE_PATH" == ".env" || "$FILE_PATH" == ".env "* ]]; then
        print_error "금지된 파일이 감지되었습니다: .env -- 이 파일을 커밋하지 마세요."
        FORBIDDEN_FOUND=1
    fi
    if [[ "$FILE_PATH" == server/models/* ]]; then
        print_error "금지된 파일이 감지되었습니다: $FILE_PATH -- 모델 가중치를 커밋하지 마세요."
        FORBIDDEN_FOUND=1
    fi
done <<< "$GIT_STATUS"

if [ "$FORBIDDEN_FOUND" -eq 1 ]; then
    print_error "금지된 파일이 감지되었습니다. .gitignore에 추가하고 스테이징에서 제거하세요."
    exit 1
fi
print_ok "금지된 파일이 감지되지 않았습니다."

# =============================================================================
# Step G -- Git 커밋
# =============================================================================
print_header "Step G: Git 커밋"

read -p "커밋 접두어를 입력하세요 (예: 1단계, docs, infra, test): " PREFIX
read -p "커밋 설명을 입력하세요: " DESC

COMMIT_MSG="${PREFIX}: ${DESC}"
echo ""
print_info "커밋 메시지: $COMMIT_MSG"

read -p "이 커밋 메시지로 진행하시겠습니까? (y/N): " COMMIT_CONFIRM
if [[ "$COMMIT_CONFIRM" != "y" && "$COMMIT_CONFIRM" != "Y" ]]; then
    print_warn "사용자에 의해 커밋이 취소되었습니다."
    exit 1
fi

git add .
git commit -m "$COMMIT_MSG"
if [ $? -eq 0 ]; then
    print_ok "커밋 완료: $COMMIT_MSG"
else
    print_error "커밋 실패."
    exit 1
fi

# =============================================================================
# Step H -- Git 푸시
# =============================================================================
print_header "Step H: Git 푸시"
print_info "origin/$INITIAL(으)로 푸시 중..."

if git push origin "$INITIAL"; then
    print_ok "origin/$INITIAL(으)로 푸시 완료."
else
    print_error "푸시 실패. 원격 연결 상태를 확인하세요."
    exit 1
fi

# =============================================================================
# Step I -- PR 생성 (선택)
# =============================================================================
print_header "Step I: Pull Request (선택)"

read -p "dev 브랜치로 Pull Request를 지금 생성하시겠습니까? (y/N): " CREATE_PR
if [[ "$CREATE_PR" == "y" || "$CREATE_PR" == "Y" ]]; then
    read -p "PR 제목을 입력하세요: " PR_TITLE
    if gh pr create --base dev --head "$INITIAL" --title "$PR_TITLE"; then
        print_ok "Pull Request가 생성되었습니다."
        PR_STATUS="생성 완료"
    else
        print_warn "PR 생성에 실패했습니다. 수동으로 생성하세요."
        PR_STATUS="실패"
    fi
    echo ""
    print_manual "[리마인더] PR 설명에 다음을 포함하세요: 변경 파일 목록, 테스트 결과(KPI), 이중 경로 원칙 확인."
else
    PR_STATUS="생략"
    echo ""
    print_info "수동으로 PR을 생성하려면 다음 명령어를 사용하세요:"
    echo "  gh pr create --base dev --head $INITIAL --title \"[$STAGE단계] $SUMMARY\""
fi

# =============================================================================
# Step J -- 문서 정합성 확인 (안내)
# =============================================================================
print_header "Step J: 문서 정합성 확인"
echo ""
echo "  [문서 정합성 확인 -- 수동으로 검토하세요]"
echo "    [ ] 새 파일 추가? -> Directory_Structure.md 업데이트"
echo "    [ ] 새 환경변수 추가? -> .env.example 및 README.md 환경변수 표 업데이트"
echo "    [ ] 새 Python 의존성 추가? -> requirements.txt 업데이트 (팀 사전 협의 필수)"
echo "    [ ] API 계약 변경? -> docs/api_specification.md 업데이트"
echo "    [ ] 아키텍처 변경? -> docs/architecture.md 업데이트"
echo ""

# =============================================================================
# Step K -- 최종 요약
# =============================================================================
print_header "Post-work 요약"
echo ""
echo "  브랜치     : $INITIAL"
echo "  단계       : $STAGE"
echo "  날짜       : $DATE"
echo "  Changelog  : $CHANGELOG_FILE (엔트리 추가됨)"
echo "  커밋       : $COMMIT_MSG"
echo "  푸시       : origin/$INITIAL"
echo "  PR         : $PR_STATUS"
echo "  ---"
echo -e "  ${YELLOW}[MANUAL]${RESET} $CHANGELOG_FILE 상세 내용 기입"
echo -e "  ${YELLOW}[MANUAL]${RESET} 문서 정합성 확인"
echo ""
echo "==========================================="
echo "  Post-work 완료. 수고하셨습니다!"
echo "==========================================="
