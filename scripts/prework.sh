#!/usr/bin/env bash
# =============================================================================
# Script Name : prework.sh
# Platform    : Linux / macOS (bash)
# Purpose     : Minchodan Pre-work automation — Git sync, env check, GPU check,
#               infrastructure/document reminders before coding.
# Usage       : bash scripts/prework.sh  (run from project root)
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
# Step A — Prompt for team initial
# =============================================================================
print_header "Step A: Team Initial"
read -p "Enter your branch initial (dg/jh/jy/kb/th): " INITIAL
case "$INITIAL" in
    dg|jh|jy|kb|th) print_ok "Initial: $INITIAL" ;;
    *)
        print_error "Invalid initial '$INITIAL'. Must be one of: dg, jh, jy, kb, th."
        exit 1
        ;;
esac

# =============================================================================
# Step B — Prompt for pipeline stage
# =============================================================================
print_header "Step B: Pipeline Stage"
read -p "Enter pipeline stage (1-7): " STAGE
if [[ ! "$STAGE" =~ ^[1-7]$ ]]; then
    print_error "Invalid stage '$STAGE'. Must be an integer between 1 and 7."
    exit 1
fi
SKILL_PATH=$(get_skill_path "$STAGE")
print_ok "Stage: $STAGE  |  Skill: $SKILL_PATH"

# =============================================================================
# Step C — Git synchronization
# =============================================================================
print_header "Step C: Git Synchronization"

print_info "Fetching from origin..."
if git fetch origin; then
    print_ok "git fetch origin"
else
    print_error "git fetch origin failed."
    STATUS_GIT="WARN"
fi

print_info "Switching to dev and pulling latest..."
if git checkout dev && git pull origin dev; then
    print_ok "dev branch is up to date."
else
    print_error "Failed to sync dev branch."
    STATUS_GIT="WARN"
fi

print_info "Switching to personal branch '$INITIAL'..."
if git checkout "$INITIAL" 2>/dev/null; then
    print_ok "Switched to branch '$INITIAL'."
else
    print_warn "Branch '$INITIAL' does not exist locally. Creating from dev..."
    if git checkout -b "$INITIAL" dev; then
        print_ok "Created and switched to new branch '$INITIAL' from dev."
    else
        print_error "Failed to create branch '$INITIAL'."
        STATUS_GIT="WARN"
    fi
fi

print_info "Merging latest dev into '$INITIAL'..."
if git merge dev --no-edit; then
    print_ok "Merged dev into '$INITIAL'."
else
    print_warn "Merge conflict detected. Please resolve manually."
    STATUS_GIT="WARN"
fi

# =============================================================================
# Step D — Environment file check
# =============================================================================
print_header "Step D: Environment File Check"
if [ -f ".env" ]; then
    print_ok ".env file found."
else
    if [ -f ".env.example" ]; then
        cp .env.example .env
        print_warn ".env was not found. Copied from .env.example. Please fill in actual values before running the server."
        STATUS_ENV="WARN"
    else
        print_error ".env.example also missing. Cannot create .env."
        STATUS_ENV="ERROR"
    fi
fi

# =============================================================================
# Step E — Python virtual environment activation check
# =============================================================================
print_header "Step E: Virtual Environment Check"
if [ -n "${VIRTUAL_ENV:-}" ]; then
    print_ok "Virtual environment is active: $VIRTUAL_ENV"
else
    print_warn "Virtual environment is NOT active."
    echo "  Please run:  source .venv/bin/activate"
fi

# =============================================================================
# Step F — Python dependency check
# =============================================================================
print_header "Step F: Python Dependency Check"
if pip install -r requirements.txt --quiet 2>/dev/null; then
    print_ok "Dependencies are installed."
else
    print_warn "pip install encountered issues. Check requirements.txt."
fi

# =============================================================================
# Step G — GPU environment check (Stage 3+)
# =============================================================================
print_header "Step G: GPU Environment Check"
if [ "$STAGE" -ge 3 ]; then
    if [ -f "scripts/verify_gpu.py" ]; then
        print_info "Running GPU verification..."
        python scripts/verify_gpu.py || print_warn "GPU verification reported issues."
        STATUS_GPU="DONE"
    else
        print_warn "scripts/verify_gpu.py not found. Skipping."
        STATUS_GPU="WARN"
    fi
else
    print_skip "GPU check skipped (Stage < 3)."
fi

# =============================================================================
# Step H — Infrastructure service check (informational)
# =============================================================================
print_header "Step H: Infrastructure Service Check"
echo ""
print_manual "Please verify the following services are running before you start coding:"
echo "    - Redis (default: localhost:6379)"
echo "    - Ollama with models: gemma2:9b, llava, nomic-embed-text (default: localhost:11434)"
echo "    - Docker containers if applicable: docker/linux_docker_start.sh (Linux) or docker/macos_docker_start.sh (macOS)"
echo ""

# =============================================================================
# Step I — Document reading checklist (informational)
# =============================================================================
print_header "Step I: Mandatory Document Reading"
echo ""
echo "  [MANDATORY READING -- Complete before writing any code]"
echo "    [ ] 1. README.md"
echo "    [ ] 2. docs/minchodan_design_note.md"
echo "    [ ] 3. docs/AGENTS.md"
echo "    [ ] 4. docs/course_codebase_guide.md"
echo "    [ ] 5. $SKILL_PATH"
echo ""

# =============================================================================
# Step J — Dual-path principle reminder
# =============================================================================
print_header "Step J: Dual Path Principle Reminder"
echo ""
echo -e "  ${RED}[CRITICAL -- DUAL PATH PRINCIPLE (NON-NEGOTIABLE)]${RESET}"
echo "    REFLEX path:  MUST NOT call LLM / RAG / real-time TTS."
echo "                  MUST use only pre-synthesized audio clips from data/reflex_clips/."
echo "                  Latency target: < 300ms (detection basis)."
echo "    COGNITIVE path: Uses Redis Streams -> LangGraph L1/L2/L3 -> RAG -> real-time TTS."
echo ""

# =============================================================================
# Step K — Final summary
# =============================================================================
print_header "Pre-work Summary"
echo ""
echo "  Branch     : $INITIAL"
echo "  Stage      : $STAGE"
echo "  Skill file : $SKILL_PATH"
echo "  ---"
echo -e "  ${GREEN}[$STATUS_GIT]${RESET} Git sync"
echo -e "  ${GREEN}[$STATUS_ENV]${RESET} .env check"
echo -e "  ${GREEN}[$STATUS_GPU]${RESET} GPU check"
echo -e "  ${YELLOW}[MANUAL]${RESET} Service check (Redis, Ollama, Docker)"
echo -e "  ${YELLOW}[MANUAL]${RESET} Document reading checklist"
echo ""
echo "==========================================="
echo "  Pre-work complete. You may start coding."
echo "==========================================="
