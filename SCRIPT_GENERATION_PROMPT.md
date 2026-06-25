# SCRIPT GENERATION PROMPT — Minchodan Project

> Version: v1.0.0
> Date: 2026-06-25
> Purpose: Ultimate prompt for AI agents to generate Pre-work and Post-work automation scripts.
> Target output: `scripts/prework.sh`, `scripts/prework.bat`, `scripts/postwork.sh`, `scripts/postwork.bat`

---

## INSTRUCTIONS FOR AI AGENT

You are an expert shell scripting engineer. Read this entire document carefully before writing any code.
Your task is to generate four automation scripts for the Minchodan project team.
All scripts must be placed in the `scripts/` directory relative to the project root (`./Minchodan`).

### Output Files to Generate

| File | Platform | Purpose |
| ---- | -------- | ------- |
| `scripts/prework.sh` | Linux / macOS (bash) | Pre-work automation |
| `scripts/prework.bat` | Windows (cmd) | Pre-work automation |
| `scripts/postwork.sh` | Linux / macOS (bash) | Post-work automation |
| `scripts/postwork.bat` | Windows (cmd) | Post-work automation |

---

## PROJECT CONTEXT

- **Project name**: Minchodan
- **Project root**: The directory containing this file. All relative paths are anchored here.
- **Python virtual environment**: `.venv/` (relative to project root)
- **Python entry point**: `server/main.py`
- **Environment file**: `.env` (copied from `.env.example` if missing)
- **Requirements file**: `requirements.txt`
- **Changelog template**: `docs/changelogs/TEMPLATE.md`
- **Changelog index**: `docs/changelogs/README.md`
- **Changelog output directory**: `docs/changelogs/`
- **Test scripts** (PowerShell / Python):
  - Stage 1: `tests/test_ws_echo.py`
  - Stage 2: `tests/test_frame_decode.py`
  - Stage 3: `tests/test_detection.py`
  - Stage 4: `scripts/eval_hitrate.py`
  - Stage 5: `tests/test_rag_retrieval.py`
  - Stage 6: `tests/test_langgraph.py`
  - Stage 7: `tests/test_tts_reflex.py`
  - GPU check: `scripts/verify_gpu.py`
- **Valid team initials (branch names)**: `dg`, `jh`, `jy`, `kb`, `th`
- **Valid commit prefixes**: `1단계:`, `2단계:`, `3단계:`, `4단계:`, `5단계:`, `6단계:`, `7단계:`, `docs:`, `infra:`, `test:`
- **Protected branches (never push directly)**: `master`, `main`, `dev`

---

## SCRIPT 1 — prework.sh / prework.bat

### Purpose

Automate all verifiable Pre-work checklist items before a team member starts coding.
Print a clear checklist at the end showing what was automated and what must be done manually.

### Required Behavior (implement all)

#### Step A — Prompt for team initial
- Ask the user to input their branch initial: `dg`, `jh`, `jy`, `kb`, or `th`.
- Validate the input. If invalid, print an error and exit.
- Store as variable `INITIAL`.

#### Step B — Prompt for pipeline stage
- Ask the user which pipeline stage they are working on (1–7).
- Validate input is an integer between 1 and 7.
- Store as variable `STAGE`.

#### Step C — Git synchronization
1. Run `git fetch origin`.
2. Switch to `dev` and pull latest: `git checkout dev && git pull origin dev`.
3. Switch to the personal branch: `git checkout $INITIAL`.
   - If the branch does not exist locally, create it from `dev`: `git checkout -b $INITIAL origin/dev` or `git checkout -b $INITIAL dev`.
4. Merge latest `dev` into the personal branch: `git merge dev`.
5. Print result of each git command (success or failure).

#### Step D — Environment file check
- Check if `.env` exists in the project root.
- If it does NOT exist, copy `.env.example` to `.env` and print a warning:
  `[WARNING] .env was not found. Copied from .env.example. Please fill in actual values before running the server.`
- If it already exists, print: `[OK] .env file found.`

#### Step E — Python virtual environment activation check
- Check if the virtual environment is already active by inspecting the `VIRTUAL_ENV` environment variable.
- If NOT active, print instructions for the user:
  - Windows: `.\.venv\Scripts\activate.bat`
  - Linux/macOS: `source .venv/bin/activate`
- Do NOT auto-activate (sourcing in a subprocess has no effect on the parent shell). Print the command for the user to run manually.
- If already active, print: `[OK] Virtual environment is active.`

#### Step F — Python dependency check
- Run `pip install -r requirements.txt --quiet`.
- Print result.

#### Step G — GPU environment check (Stage 3 and above only)
- If `STAGE >= 3`, run `python scripts/verify_gpu.py`.
- Print the output.
- If `STAGE < 3`, skip and print: `[SKIP] GPU check skipped (Stage < 3).`

#### Step H — Infrastructure service check (informational)
- Print reminder messages (do NOT attempt to start services automatically):
  ```
  [MANUAL CHECK REQUIRED]
  Please verify the following services are running before you start coding:
    - Redis (default: localhost:6379)
    - Ollama with models: gemma2:9b, llava, nomic-embed-text (default: localhost:11434)
    - Docker containers if applicable: docker/windows_docker_start.bat (Windows) or docker/linux_docker_start.sh (Linux)
  ```

#### Step I — Print document reading checklist (informational)
- Print the following checklist as a reminder. Do NOT attempt to open files automatically.
  ```
  [MANDATORY READING — Complete before writing any code]
    [ ] 1. README.md
    [ ] 2. docs/minchodan_design_note.md
    [ ] 3. docs/AGENTS.md
    [ ] 4. docs/course_codebase_guide.md
    [ ] 5. .agents/skills/[skill-for-stage]/SKILL.md
  ```
- Map `STAGE` to the skill path:
  - 1 → `.agents/skills/websocket-gateway/SKILL.md`
  - 2 → `.agents/skills/camera-frame-capture/SKILL.md`
  - 3 → `.agents/skills/yolo-obstacle-detection/SKILL.md`
  - 4 → `.agents/skills/rag-knowledge-builder/SKILL.md`
  - 5 → `.agents/skills/rag-realtime-search/SKILL.md`
  - 6 → `.agents/skills/llm-guidance-orchestrator/SKILL.md`
  - 7 → `.agents/skills/tts-voice-streamer/SKILL.md`

#### Step J — Print dual-path principle reminder
- Print the following every time, regardless of stage:
  ```
  [CRITICAL — DUAL PATH PRINCIPLE (NON-NEGOTIABLE)]
    REFLEX path:  MUST NOT call LLM / RAG / real-time TTS.
                  MUST use only pre-synthesized audio clips from data/reflex_clips/.
                  Latency target: < 300ms (detection basis).
    COGNITIVE path: Uses Redis Streams -> LangGraph L1/L2/L3 -> RAG -> real-time TTS.
  ```

#### Step K — Final summary
- Print a summary table:
  ```
  === Pre-work Summary ===
  Branch     : [INITIAL]
  Stage      : [STAGE]
  Skill file : [path to SKILL.md]
  ---
  [DONE] Git sync
  [DONE/WARN] .env check
  [DONE/SKIP] GPU check
  [MANUAL] Service check (Redis, Ollama, Docker)
  [MANUAL] Document reading checklist
  =======================
  ```

---

## SCRIPT 2 — postwork.sh / postwork.bat

### Purpose

Automate all verifiable Post-work checklist items after a team member finishes coding.
Guide the user through steps that require human input (commit message, PR title).

### Required Behavior (implement all)

#### Step A — Prompt for team initial and stage
- Same as prework Step A and B.
- Additionally prompt: `Enter today's date (YYYY-MM-DD):` and store as `DATE`.
- Additionally prompt: `Enter a short work summary in English (used for changelog filename, e.g. websocket_handshake):` and store as `SUMMARY`.
  - Validate: only allow lowercase letters, digits, and underscores. Reject spaces or special characters.

#### Step B — Coding rule self-check (informational)
- Print a checklist for the user to manually verify before committing:
  ```
  [CODING RULE SELF-CHECK — Verify manually before continuing]
    [ ] All new Python files start with: # -*- coding: utf-8 -*- and sys.stdout.reconfigure(encoding='utf-8')
    [ ] Import order: stdlib -> third-party -> local
    [ ] No hardcoded absolute paths (use os.path.dirname(os.path.abspath(__file__)))
    [ ] Environment variables loaded via load_dotenv() + os.getenv(key, default)
    [ ] Defensive coding: None guard, dict.get(), exception handling with loop continuation
    [ ] FastAPI structure: Router -> Service -> Repository (3-layer)
    [ ] No emoji in code comments, commit messages, or documents
    [ ] All files saved as UTF-8
  ```
- Prompt: `Have you completed the above checks? (y/N):` and wait for confirmation. If not `y`, print warning and exit.

#### Step C — Dual-path principle violation check (informational)
- Print the following checklist:
  ```
  [DUAL PATH VIOLATION CHECK]
    [ ] Reflex path code has NO LLM calls
    [ ] Reflex path code has NO RAG search calls
    [ ] Reflex path code has NO real-time TTS synthesis calls
    [ ] Reflex audio references only pre-synthesized clips in data/reflex_clips/
  ```
- Prompt: `Confirm no dual-path violations? (y/N):` and wait. If not `y`, print warning and exit.

#### Step D — Run tests for the specified stage
- Based on `STAGE`, run the corresponding test file with `python`:
  - 1 → `python tests/test_ws_echo.py`
  - 2 → `python tests/test_frame_decode.py`
  - 3 → `python tests/test_detection.py` (also run `python scripts/verify_gpu.py` first)
  - 4 → `python scripts/eval_hitrate.py`
  - 5 → `python tests/test_rag_retrieval.py`
  - 6 → `python tests/test_langgraph.py`
  - 7 → `python tests/test_tts_reflex.py`
- Print test output.
- Prompt: `Did all tests pass and KPI targets met? (y/N):` If not `y`, print warning (do NOT block — the user may choose to proceed).

#### Step E — Changelog file creation
- Construct the changelog filename: `${DATE}_${INITIAL}_${SUMMARY}.md`
  - Example: `2026-06-25_dg_websocket_handshake.md`
- Copy `docs/changelogs/TEMPLATE.md` to `docs/changelogs/${DATE}_${INITIAL}_${SUMMARY}.md`.
- If the destination file already exists, print a warning and ask: `File already exists. Overwrite? (y/N):`. If `N`, skip.
- Print: `[OK] Changelog file created: docs/changelogs/${DATE}_${INITIAL}_${SUMMARY}.md`
- Print reminder: `[ACTION REQUIRED] Open the changelog file and fill in the change details, related files, and verification results.`
- Print reminder: `[ACTION REQUIRED] Add a new row to the top of the table in docs/changelogs/README.md.`

#### Step F — Git staging safety check
- Run `git status --short` and capture output.
- Scan the output for any of the following forbidden paths:
  - `.env`
  - `server/models/`
- If any forbidden path is found in the staged or modified files, print:
  `[ERROR] Forbidden file detected in git status: [filename]. Do NOT commit this file. Add it to .gitignore if needed.`
  and exit with error code 1.
- If clean, print: `[OK] No forbidden files detected.`

#### Step G — Git commit
- Prompt: `Enter commit prefix (e.g. 1단계, docs, infra, test):` and store as `PREFIX`.
- Prompt: `Enter commit description (Korean or English):` and store as `DESC`.
- Construct commit message: `${PREFIX}: ${DESC}`
- Print the constructed message and prompt: `Confirm commit message? (y/N):`
- If confirmed, run:
  ```
  git add .
  git commit -m "${PREFIX}: ${DESC}"
  ```
- Print result.

#### Step H — Git push
- Run: `git push origin $INITIAL`
- Print result.

#### Step I — PR creation (optional)
- Prompt: `Create a Pull Request to dev now? (y/N):`
- If `y`:
  - Prompt: `Enter PR title:` and store as `PR_TITLE`.
  - Run: `gh pr create --base dev --head $INITIAL --title "$PR_TITLE"`
  - Print: `[REMINDER] Add to PR description: changed files list, test results (KPI), dual-path principle confirmation.`
  - Print result.
- If `N`, print the command for manual use:
  ```
  gh pr create --base dev --head [INITIAL] --title "[STAGE] [SUMMARY]"
  ```

#### Step J — Document consistency reminder (informational)
- Print the following checklist:
  ```
  [DOCUMENT CONSISTENCY CHECK — Verify manually]
    [ ] New files added? -> Update Directory_Structure.md
    [ ] New environment variables? -> Update .env.example and README.md env table
    [ ] New Python dependencies? -> Update requirements.txt (team approval required first)
    [ ] API contract changed? -> Update docs/api_specification.md
    [ ] Architecture changed? -> Update docs/architecture.md
  ```

#### Step K — Final summary
- Print:
  ```
  === Post-work Summary ===
  Branch     : [INITIAL]
  Stage      : [STAGE]
  Date       : [DATE]
  Changelog  : docs/changelogs/[DATE]_[INITIAL]_[SUMMARY].md
  Committed  : [PREFIX]: [DESC]
  Pushed     : origin/[INITIAL]
  PR         : [created / skipped]
  ---
  [MANUAL] Fill in changelog file details
  [MANUAL] Add row to docs/changelogs/README.md
  [MANUAL] Document consistency checks
  =========================
  ```

---

## GENERAL CODING REQUIREMENTS FOR THE SCRIPTS

Apply the following rules when writing the shell and batch scripts:

### For .sh (bash)
- Use `#!/usr/bin/env bash` shebang.
- Use `set -euo pipefail` for safe execution (exit on error, undefined variable, pipe failure).
- Use functions for reusable logic (e.g., `check_git_branch`, `run_test`).
- Use ANSI color codes for output clarity:
  - Green `\033[0;32m` for `[OK]`
  - Yellow `\033[0;33m` for `[WARN]` and `[MANUAL]`
  - Red `\033[0;31m` for `[ERROR]`
  - Reset `\033[0m`
- Use `read -p "prompt: " VAR` for user input.
- Validate all user inputs (branch initial, stage number, date format YYYY-MM-DD).

### For .bat (Windows cmd)
- Use `@echo off` at the top.
- Use `setlocal enabledelayedexpansion` for variable handling inside loops/conditionals.
- Use `set /p VAR=prompt:` for user input.
- Validate branch initial and stage using `if` comparisons.
- Use `echo [OK]`, `echo [WARN]`, `echo [ERROR]` prefixes consistently.
- Use `goto :eof` and labeled sections (`:LABEL`) for flow control.
- Handle errors with `if errorlevel 1`.
- At the top of the file, print a header comment block explaining what the script does.

### Shared rules for both platforms
- Scripts must be runnable from the project root directory.
- Never hardcode absolute paths. Use relative paths from the project root.
- All echo/print output must be in Korean or English. No emoji in output text.
- Scripts must be saved with UTF-8 encoding and LF line endings (for .sh) / CRLF (for .bat).
- Add a comment block at the top of each file with: script name, platform, purpose, usage example.

---

## EXAMPLE USAGE

### prework
```bash
# Linux/macOS
bash scripts/prework.sh

# Windows
scripts\prework.bat
```

### postwork
```bash
# Linux/macOS
bash scripts/postwork.sh

# Windows
scripts\postwork.bat
```

---

## FINAL CHECKLIST FOR AI AGENT

Before submitting the generated scripts, verify:

- [ ] All four files are generated: `prework.sh`, `prework.bat`, `postwork.sh`, `postwork.bat`
- [ ] All steps described above are implemented in each script
- [ ] Input validation is present for: branch initial (dg/jh/jy/kb/th), stage (1-7), date (YYYY-MM-DD), summary (no spaces/special chars)
- [ ] Forbidden file check (`.env`, `server/models/`) is implemented in postwork
- [ ] Changelog template copy logic is implemented in postwork
- [ ] Color-coded output is used in .sh scripts
- [ ] No emoji in any output text
- [ ] No hardcoded absolute paths
- [ ] Scripts are executable from the project root directory
