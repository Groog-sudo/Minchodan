#!/usr/bin/env bash
# =============================================================================
# Script Name : postwork.sh
# Platform    : Linux / macOS (bash)
# Purpose     : Minchodan Post-work automation — coding rule check, test run,
#               changelog creation, git commit/push, PR creation.
# Usage       : bash scripts/postwork.sh  (run from project root)
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
PR_STATUS="skipped"

# =============================================================================
# Step A — Prompt for team initial, stage, date, summary
# =============================================================================
print_header "Step A: Basic Information"

# --- Initial ---
read -p "Enter your branch initial (dg/jh/jy/kb/th): " INITIAL
case "$INITIAL" in
    dg|jh|jy|kb|th) print_ok "Initial: $INITIAL" ;;
    *)
        print_error "Invalid initial '$INITIAL'. Must be one of: dg, jh, jy, kb, th."
        exit 1
        ;;
esac

# --- Stage ---
read -p "Enter pipeline stage (1-7): " STAGE
if [[ ! "$STAGE" =~ ^[1-7]$ ]]; then
    print_error "Invalid stage '$STAGE'. Must be an integer between 1 and 7."
    exit 1
fi
print_ok "Stage: $STAGE"

# --- Date ---
read -p "Enter today's date (YYYY-MM-DD): " DATE
if [[ ! "$DATE" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}$ ]]; then
    print_error "Invalid date format '$DATE'. Must be YYYY-MM-DD."
    exit 1
fi
print_ok "Date: $DATE"

# --- Summary ---
read -p "Enter a short work summary (lowercase, digits, underscores only, e.g. websocket_handshake): " SUMMARY
if [[ ! "$SUMMARY" =~ ^[a-z0-9_]+$ ]]; then
    print_error "Invalid summary '$SUMMARY'. Only lowercase letters, digits, and underscores are allowed."
    exit 1
fi
print_ok "Summary: $SUMMARY"

CHANGELOG_FILE="docs/changelogs/${DATE}_${INITIAL}_${SUMMARY}.md"

# =============================================================================
# Step B — Coding rule self-check (informational)
# =============================================================================
print_header "Step B: Coding Rule Self-Check"
echo ""
echo "  [CODING RULE SELF-CHECK -- Verify manually before continuing]"
echo "    [ ] All new Python files start with: # -*- coding: utf-8 -*- and sys.stdout.reconfigure(encoding='utf-8')"
echo "    [ ] Import order: stdlib -> third-party -> local"
echo "    [ ] No hardcoded absolute paths (use os.path.dirname(os.path.abspath(__file__)))"
echo "    [ ] Environment variables loaded via load_dotenv() + os.getenv(key, default)"
echo "    [ ] Defensive coding: None guard, dict.get(), exception handling with loop continuation"
echo "    [ ] FastAPI structure: Router -> Service -> Repository (3-layer)"
echo "    [ ] No emoji in code comments, commit messages, or documents"
echo "    [ ] All files saved as UTF-8"
echo ""

read -p "Have you completed the above checks? (y/N): " CODING_CHECK
if [[ "$CODING_CHECK" != "y" && "$CODING_CHECK" != "Y" ]]; then
    print_warn "Coding rule check not confirmed. Please review the checklist above and re-run."
    exit 1
fi
print_ok "Coding rule self-check confirmed."

# =============================================================================
# Step C — Dual-path principle violation check (informational)
# =============================================================================
print_header "Step C: Dual Path Violation Check"
echo ""
echo "  [DUAL PATH VIOLATION CHECK]"
echo "    [ ] Reflex path code has NO LLM calls"
echo "    [ ] Reflex path code has NO RAG search calls"
echo "    [ ] Reflex path code has NO real-time TTS synthesis calls"
echo "    [ ] Reflex audio references only pre-synthesized clips in data/reflex_clips/"
echo ""

read -p "Confirm no dual-path violations? (y/N): " DUAL_CHECK
if [[ "$DUAL_CHECK" != "y" && "$DUAL_CHECK" != "Y" ]]; then
    print_warn "Dual-path violation check not confirmed. Please review your reflex path code."
    exit 1
fi
print_ok "Dual-path principle confirmed."

# =============================================================================
# Step D — Run tests for the specified stage
# =============================================================================
print_header "Step D: Run Tests (Stage $STAGE)"
TEST_CMD=$(get_test_cmd "$STAGE")
print_info "Running: $TEST_CMD"
echo ""

eval "$TEST_CMD" || print_warn "Some tests may have failed."
echo ""

read -p "Did all tests pass and KPI targets met? (y/N): " TEST_PASS
if [[ "$TEST_PASS" != "y" && "$TEST_PASS" != "Y" ]]; then
    print_warn "Tests not fully passed. Proceeding anyway — please fix issues before PR merge."
fi

# =============================================================================
# Step E — Changelog file creation
# =============================================================================
print_header "Step E: Changelog File Creation"

if [ -f "$CHANGELOG_FILE" ]; then
    print_warn "File already exists: $CHANGELOG_FILE"
    read -p "Overwrite? (y/N): " OVERWRITE
    if [[ "$OVERWRITE" != "y" && "$OVERWRITE" != "Y" ]]; then
        print_info "Skipped changelog file creation."
    else
        cp docs/changelogs/TEMPLATE.md "$CHANGELOG_FILE"
        print_ok "Changelog file overwritten: $CHANGELOG_FILE"
    fi
else
    cp docs/changelogs/TEMPLATE.md "$CHANGELOG_FILE"
    print_ok "Changelog file created: $CHANGELOG_FILE"
fi

echo ""
print_manual "[ACTION REQUIRED] Open the changelog file and fill in the change details, related files, and verification results."
print_manual "[ACTION REQUIRED] Add a new row to the top of the table in docs/changelogs/README.md."
echo ""

# =============================================================================
# Step F — Git staging safety check
# =============================================================================
print_header "Step F: Git Staging Safety Check"

GIT_STATUS=$(git status --short 2>/dev/null || echo "")

FORBIDDEN_FOUND=0
while IFS= read -r line; do
    if [[ -z "$line" ]]; then
        continue
    fi
    FILE_PATH="${line:3}"
    if [[ "$FILE_PATH" == ".env" || "$FILE_PATH" == ".env "* ]]; then
        print_error "Forbidden file detected in git status: .env  -- Do NOT commit this file."
        FORBIDDEN_FOUND=1
    fi
    if [[ "$FILE_PATH" == server/models/* ]]; then
        print_error "Forbidden file detected in git status: $FILE_PATH  -- Do NOT commit model weights."
        FORBIDDEN_FOUND=1
    fi
done <<< "$GIT_STATUS"

if [ "$FORBIDDEN_FOUND" -eq 1 ]; then
    print_error "Forbidden files detected. Add them to .gitignore and remove from staging before committing."
    exit 1
fi
print_ok "No forbidden files detected."

# =============================================================================
# Step G — Git commit
# =============================================================================
print_header "Step G: Git Commit"

read -p "Enter commit prefix (e.g. 1단계, docs, infra, test): " PREFIX
read -p "Enter commit description: " DESC

COMMIT_MSG="${PREFIX}: ${DESC}"
echo ""
print_info "Commit message: $COMMIT_MSG"

read -p "Confirm commit message? (y/N): " COMMIT_CONFIRM
if [[ "$COMMIT_CONFIRM" != "y" && "$COMMIT_CONFIRM" != "Y" ]]; then
    print_warn "Commit cancelled by user."
    exit 1
fi

git add .
git commit -m "$COMMIT_MSG"
if [ $? -eq 0 ]; then
    print_ok "Committed: $COMMIT_MSG"
else
    print_error "Commit failed."
    exit 1
fi

# =============================================================================
# Step H — Git push
# =============================================================================
print_header "Step H: Git Push"
print_info "Pushing to origin/$INITIAL..."

if git push origin "$INITIAL"; then
    print_ok "Pushed to origin/$INITIAL."
else
    print_error "Push failed. Check your remote connection."
    exit 1
fi

# =============================================================================
# Step I — PR creation (optional)
# =============================================================================
print_header "Step I: Pull Request (Optional)"

read -p "Create a Pull Request to dev now? (y/N): " CREATE_PR
if [[ "$CREATE_PR" == "y" || "$CREATE_PR" == "Y" ]]; then
    read -p "Enter PR title: " PR_TITLE
    if gh pr create --base dev --head "$INITIAL" --title "$PR_TITLE"; then
        print_ok "Pull Request created."
        PR_STATUS="created"
    else
        print_warn "PR creation failed. You can create it manually."
        PR_STATUS="failed"
    fi
    echo ""
    print_manual "[REMINDER] Add to PR description: changed files list, test results (KPI), dual-path principle confirmation."
else
    PR_STATUS="skipped"
    echo ""
    print_info "To create a PR manually, run:"
    echo "  gh pr create --base dev --head $INITIAL --title \"[$STAGE단계] $SUMMARY\""
fi

# =============================================================================
# Step J — Document consistency reminder (informational)
# =============================================================================
print_header "Step J: Document Consistency Check"
echo ""
echo "  [DOCUMENT CONSISTENCY CHECK -- Verify manually]"
echo "    [ ] New files added? -> Update Directory_Structure.md"
echo "    [ ] New environment variables? -> Update .env.example and README.md env table"
echo "    [ ] New Python dependencies? -> Update requirements.txt (team approval required first)"
echo "    [ ] API contract changed? -> Update docs/api_specification.md"
echo "    [ ] Architecture changed? -> Update docs/architecture.md"
echo ""

# =============================================================================
# Step K — Final summary
# =============================================================================
print_header "Post-work Summary"
echo ""
echo "  Branch     : $INITIAL"
echo "  Stage      : $STAGE"
echo "  Date       : $DATE"
echo "  Changelog  : $CHANGELOG_FILE"
echo "  Committed  : $COMMIT_MSG"
echo "  Pushed     : origin/$INITIAL"
echo "  PR         : $PR_STATUS"
echo "  ---"
echo -e "  ${YELLOW}[MANUAL]${RESET} Fill in changelog file details"
echo -e "  ${YELLOW}[MANUAL]${RESET} Add row to docs/changelogs/README.md"
echo -e "  ${YELLOW}[MANUAL]${RESET} Document consistency checks"
echo ""
echo "==========================================="
echo "  Post-work complete. Good job!"
echo "==========================================="
