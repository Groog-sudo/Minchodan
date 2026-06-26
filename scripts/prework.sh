#!/usr/bin/env bash
# =============================================================================
# Script Name : prework.sh
# Platform    : Linux / macOS (bash)
# Purpose     : Minchodan Pre-work 자동화 -- Git 동기화, 환경 확인, GPU 검증,
#               인프라/문서 리마인더.
# Usage       : bash scripts/prework.sh  (프로젝트 루트에서 실행)
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
print_skip()  { echo -e "${YELLOW}[SKIP]${RESET} $1"; }
print_done()  { echo -e "${GREEN}[DONE]${RESET} $1"; }
print_header(){ echo -e "\n${BOLD}=== $1 ===${RESET}"; }

# --- Skill path lookup ---
get_skill_path() {
    case "$1" in
        1) echo ".agents/skills/websocket-gateway/SKILL.md" ;;
        2) echo ".agents/skills/camera-frame-capture/SKILL.md" ;;
        3) echo ".agents/skills/yolo-obstacle-detection/SKILL.md" ;;
        4) echo ".agents/skills/rag-knowledge-builder/SKILL.md" ;;
        5) echo ".agents/skills/rag-realtime-search/SKILL.md" ;;
        6) echo ".agents/skills/llm-guidance-orchestrator/SKILL.md" ;;
        7) echo ".agents/skills/tts-voice-streamer/SKILL.md" ;;
    esac
}

# Track statuses for summary
STATUS_GIT="DONE"
STATUS_ENV="DONE"
STATUS_GPU="SKIP"

# =============================================================================
# Step A -- 브랜치 이니셜 입력
# =============================================================================
print_header "Step A: 브랜치 이니셜 입력"
read -p "본인 브랜치 이니셜을 입력하세요 (dg/jh/jy/kb/th): " INITIAL
case "$INITIAL" in
    dg|jh|jy|kb|th) print_ok "이니셜: $INITIAL" ;;
    *)
        print_error "잘못된 이니셜 '$INITIAL'. dg, jh, jy, kb, th 중 하나를 입력하세요."
        exit 1
        ;;
esac

# =============================================================================
# Step B -- 파이프라인 단계 입력
# =============================================================================
print_header "Step B: 파이프라인 단계 입력"
read -p "작업할 파이프라인 단계를 입력하세요 (1-7): " STAGE
if [[ ! "$STAGE" =~ ^[1-7]$ ]]; then
    print_error "잘못된 단계 '$STAGE'. 1~7 사이의 정수를 입력하세요."
    exit 1
fi
SKILL_PATH=$(get_skill_path "$STAGE")
print_ok "단계: $STAGE  |  스킬: $SKILL_PATH"

# =============================================================================
# Step C -- Git 동기화
# =============================================================================
print_header "Step C: Git 동기화"

print_info "원격 저장소에서 가져오는 중..."
if git fetch origin; then
    print_ok "git fetch origin 완료"
else
    print_error "git fetch origin 실패."
    STATUS_GIT="WARN"
fi

print_info "dev 브랜치로 전환 후 최신 코드 가져오는 중..."
if git checkout dev && git pull origin dev; then
    print_ok "dev 브랜치가 최신 상태입니다."
else
    print_error "dev 브랜치 동기화에 실패했습니다."
    STATUS_GIT="WARN"
fi

print_info "개인 브랜치 '$INITIAL'(으)로 전환 중..."
if git checkout "$INITIAL" 2>/dev/null; then
    print_ok "'$INITIAL' 브랜치로 전환 완료."
else
    print_warn "'$INITIAL' 브랜치가 로컬에 없습니다. dev에서 새로 생성합니다..."
    if git checkout -b "$INITIAL" dev; then
        print_ok "dev 기반으로 '$INITIAL' 브랜치 생성 및 전환 완료."
    else
        print_error "'$INITIAL' 브랜치 생성에 실패했습니다."
        STATUS_GIT="WARN"
    fi
fi

print_info "최신 dev를 '$INITIAL'에 병합 중..."
if git merge dev --no-edit; then
    print_ok "dev를 '$INITIAL'에 병합 완료."
else
    print_warn "병합 충돌이 발생했습니다. 수동으로 해결해주세요."
    STATUS_GIT="WARN"
fi

# =============================================================================
# Step D -- 환경 파일 확인
# =============================================================================
print_header "Step D: 환경 파일 확인"
if [ -f ".env" ]; then
    print_ok ".env 파일이 존재합니다."
else
    if [ -f ".env.example" ]; then
        cp .env.example .env
        print_warn ".env 파일이 없어서 .env.example에서 복사했습니다. 서버 실행 전 실제 값을 입력해주세요."
        STATUS_ENV="WARN"
    else
        print_error ".env.example 파일도 없습니다. .env를 생성할 수 없습니다."
        STATUS_ENV="ERROR"
    fi
fi

# =============================================================================
# Step E -- 가상환경 활성화 확인
# =============================================================================
print_header "Step E: 가상환경 활성화 확인"
if [ -n "${VIRTUAL_ENV:-}" ]; then
    print_ok "가상환경이 활성화되어 있습니다: $VIRTUAL_ENV"
else
    print_warn "가상환경이 활성화되어 있지 않습니다."
    echo "  다음 명령어를 실행하세요:  source .venv/bin/activate"
fi

# =============================================================================
# Step F -- Python 의존성 확인
# =============================================================================
print_header "Step F: Python 의존성 확인"
if pip install -r requirements.txt --quiet 2>/dev/null; then
    print_ok "의존성 설치가 완료되었습니다."
else
    print_warn "pip install 중 문제가 발생했습니다. requirements.txt를 확인하세요."
fi

# =============================================================================
# Step G -- GPU 환경 확인 (3단계 이상)
# =============================================================================
print_header "Step G: GPU 환경 확인"
if [ "$STAGE" -ge 3 ]; then
    if [ -f "scripts/verify_gpu.py" ]; then
        print_info "GPU 검증 실행 중..."
        python scripts/verify_gpu.py || print_warn "GPU 검증에서 문제가 보고되었습니다."
        STATUS_GPU="DONE"
    else
        print_warn "scripts/verify_gpu.py 파일이 없습니다. 건너뜁니다."
        STATUS_GPU="WARN"
    fi
else
    print_skip "GPU 확인 생략 (3단계 미만)."
fi

# =============================================================================
# Step H -- 인프라 서비스 확인 (안내)
# =============================================================================
print_header "Step H: 인프라 서비스 확인"
echo ""
print_manual "코딩 시작 전 아래 서비스들이 실행 중인지 확인하세요:"
echo "    - Redis (기본: localhost:6379)"
echo "    - Ollama 모델: gemma2:9b, llava, nomic-embed-text (기본: localhost:11434)"
echo "    - Docker 컨테이너 (해당 시): docker/linux_docker_start.sh (Linux) 또는 docker/macos_docker_start.sh (macOS)"
echo ""

# =============================================================================
# Step I -- 필수 문서 읽기 체크리스트 (안내)
# =============================================================================
print_header "Step I: 필수 문서 읽기"
echo ""
echo "  [필수 읽기 -- 코드 작성 전 반드시 완료하세요]"
echo "    [ ] 1. README.md"
echo "    [ ] 2. docs/minchodan_design_note.md"
echo "    [ ] 3. docs/AGENTS.md"
echo "    [ ] 4. docs/course_codebase_guide.md"
echo "    [ ] 5. $SKILL_PATH"
echo ""

# =============================================================================
# Step J -- 이중 경로 원칙 리마인더
# =============================================================================
print_header "Step J: 이중 경로 원칙 리마인더"
echo ""
echo -e "  ${RED}[필수 -- 이중 경로 원칙 (비협상)]${RESET}"
echo "    반사 경로: LLM / RAG / 실시간 TTS 호출 절대 금지."
echo "              data/reflex_clips/ 사전합성 클립만 사용."
echo "              지연 목표: < 300ms (탐지 기준)."
echo "    인지 경로: Redis Streams -> LangGraph L1/L2/L3 -> RAG -> 실시간 TTS 사용."
echo ""

# =============================================================================
# Step K -- 최종 요약
# =============================================================================
print_header "Pre-work 요약"
echo ""
echo "  브랜치     : $INITIAL"
echo "  단계       : $STAGE"
echo "  스킬 파일  : $SKILL_PATH"
echo "  ---"
echo -e "  ${GREEN}[$STATUS_GIT]${RESET} Git 동기화"
echo -e "  ${GREEN}[$STATUS_ENV]${RESET} .env 확인"
echo -e "  ${GREEN}[$STATUS_GPU]${RESET} GPU 확인"
echo -e "  ${YELLOW}[MANUAL]${RESET} 서비스 확인 (Redis, Ollama, Docker)"
echo -e "  ${YELLOW}[MANUAL]${RESET} 문서 읽기 체크리스트"
echo ""
echo "==========================================="
echo "  Pre-work 완료. 코딩을 시작하세요."
echo "==========================================="
