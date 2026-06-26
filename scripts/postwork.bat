@echo off
REM =============================================================================
REM Script Name : postwork.bat
REM Platform    : Windows (cmd)
REM Purpose     : Minchodan Post-work automation -- coding rule check, test run,
REM               changelog record, git commit/push, PR creation.
REM Usage       : scripts\postwork.bat  (run from project root)
REM NOTE        : For Korean version, use scripts\postwork.ps1
REM =============================================================================
setlocal enabledelayedexpansion

echo.
echo ===================================================
echo   Minchodan Post-work Automation (Windows)
echo ===================================================
echo.

REM =============================================================================
REM Step A -- Prompt for team initial, stage, date, summary
REM =============================================================================
echo === Step A: Basic Information ===

REM --- Initial ---
set /p INITIAL=Enter your branch initial (dg/jh/jy/kb/th): 

if "!INITIAL!"=="dg" goto :INITIAL_OK
if "!INITIAL!"=="jh" goto :INITIAL_OK
if "!INITIAL!"=="jy" goto :INITIAL_OK
if "!INITIAL!"=="kb" goto :INITIAL_OK
if "!INITIAL!"=="th" goto :INITIAL_OK

echo [ERROR] Invalid initial '!INITIAL!'. Must be one of: dg, jh, jy, kb, th.
exit /b 1

:INITIAL_OK
echo [OK] Initial: !INITIAL!

REM --- Stage ---
set /p STAGE=Enter pipeline stage (1-7): 

if "!STAGE!"=="1" goto :STAGE_OK
if "!STAGE!"=="2" goto :STAGE_OK
if "!STAGE!"=="3" goto :STAGE_OK
if "!STAGE!"=="4" goto :STAGE_OK
if "!STAGE!"=="5" goto :STAGE_OK
if "!STAGE!"=="6" goto :STAGE_OK
if "!STAGE!"=="7" goto :STAGE_OK

echo [ERROR] Invalid stage '!STAGE!'. Must be an integer between 1 and 7.
exit /b 1

:STAGE_OK
echo [OK] Stage: !STAGE!

REM --- Date ---
set /p DATE=Enter today's date (YYYY-MM-DD): 

set "DATE_LEN=0"
set "TMP_DATE=!DATE!"
:DATE_LEN_LOOP
if defined TMP_DATE (
    set "TMP_DATE=!TMP_DATE:~1!"
    set /a DATE_LEN+=1
    goto :DATE_LEN_LOOP
)
if not "!DATE_LEN!"=="10" (
    echo [ERROR] Invalid date format '!DATE!'. Must be YYYY-MM-DD (10 chars).
    exit /b 1
)
echo [OK] Date: !DATE!

REM --- Summary ---
set /p SUMMARY=Enter work summary (lowercase, digits, underscores only, e.g. websocket_handshake):

echo !SUMMARY! | findstr /r " " >nul 2>&1
if not errorlevel 1 (
    echo [ERROR] Invalid summary '!SUMMARY!'. Spaces are not allowed.
    exit /b 1
)
if "!SUMMARY!"=="" (
    echo [ERROR] Summary cannot be empty.
    exit /b 1
)
echo [OK] Summary: !SUMMARY!

set "CHANGELOG_FILE=docs\changelogs\!INITIAL!.md"
echo.

REM =============================================================================
REM Step B -- Coding rule self-check (informational)
REM =============================================================================
echo === Step B: Coding Rule Self-Check ===
echo.
echo   [CODING RULE SELF-CHECK -- Verify before continuing]
echo     [ ] Python file header: # -*- coding: utf-8 -*- and sys.stdout.reconfigure
echo     [ ] Import order: stdlib -^> third-party -^> local
echo     [ ] No hardcoded absolute paths
echo     [ ] Environment vars: load_dotenv() + os.getenv(key, default)
echo     [ ] Defensive coding: None guard, dict.get(), exception handling
echo     [ ] FastAPI 3-layer: Router -^> Service -^> Repository
echo     [ ] No emoji in code, commits, or docs
echo     [ ] All files saved as UTF-8
echo.

set /p CODING_CHECK=Have you completed the above checks? (y/N): 
if /i not "!CODING_CHECK!"=="y" (
    echo [WARN] Coding rule check not confirmed. Review the checklist and re-run.
    exit /b 1
)
echo [OK] Coding rule self-check confirmed.
echo.

REM =============================================================================
REM Step C -- Dual-path principle violation check
REM =============================================================================
echo === Step C: Dual Path Violation Check ===
echo.
echo   [DUAL PATH VIOLATION CHECK]
echo     [ ] Reflex path: NO LLM calls
echo     [ ] Reflex path: NO RAG search calls
echo     [ ] Reflex path: NO real-time TTS synthesis
echo     [ ] Reflex audio: only pre-synthesized clips in data\reflex_clips\
echo.

set /p DUAL_CHECK=Confirm no dual-path violations? (y/N): 
if /i not "!DUAL_CHECK!"=="y" (
    echo [WARN] Dual-path violation not confirmed. Review reflex path code.
    exit /b 1
)
echo [OK] Dual-path principle confirmed.
echo.

REM =============================================================================
REM Step D -- Run tests for the specified stage
REM =============================================================================
echo === Step D: Run Tests (Stage !STAGE!) ===

if "!STAGE!"=="1" (
    echo [INFO] Running: python tests\test_ws_echo.py
    python tests\test_ws_echo.py
)
if "!STAGE!"=="2" (
    echo [INFO] Running: python tests\test_frame_decode.py
    python tests\test_frame_decode.py
)
if "!STAGE!"=="3" (
    echo [INFO] Running: python scripts\verify_gpu.py
    python scripts\verify_gpu.py
    echo [INFO] Running: python tests\test_detection.py
    python tests\test_detection.py
)
if "!STAGE!"=="4" (
    echo [INFO] Running: python scripts\eval_hitrate.py
    python scripts\eval_hitrate.py
)
if "!STAGE!"=="5" (
    echo [INFO] Running: python tests\test_rag_retrieval.py
    python tests\test_rag_retrieval.py
)
if "!STAGE!"=="6" (
    echo [INFO] Running: python tests\test_langgraph.py
    python tests\test_langgraph.py
)
if "!STAGE!"=="7" (
    echo [INFO] Running: python tests\test_tts_reflex.py
    python tests\test_tts_reflex.py
)

echo.
set /p TEST_PASS=Did all tests pass and KPI targets met? (y/N): 
if /i not "!TEST_PASS!"=="y" (
    echo [WARN] Tests not fully passed. Proceeding -- fix before PR merge.
)
echo.

REM =============================================================================
REM Step E -- Changelog entry append
REM =============================================================================
echo === Step E: Changelog Entry Append ===

if not exist "!CHANGELOG_FILE!" (
    echo # Changelog - !INITIAL!> "!CHANGELOG_FILE!"
    echo.>> "!CHANGELOG_FILE!"
    echo ^> Work log for **!INITIAL!**. New entries appended at the bottom.>> "!CHANGELOG_FILE!"
    echo [OK] Created changelog file: !CHANGELOG_FILE!
)

echo.>> "!CHANGELOG_FILE!"
echo --->> "!CHANGELOG_FILE!"
echo.>> "!CHANGELOG_FILE!"
echo ### !DATE! ^| Stage !STAGE! ^| !SUMMARY!>> "!CHANGELOG_FILE!"
echo.>> "!CHANGELOG_FILE!"
echo - **Commit**: `(to be filled after commit)`>> "!CHANGELOG_FILE!"
echo - **Changes**:>> "!CHANGELOG_FILE!"
echo   - (Fill in details after work is done.)>> "!CHANGELOG_FILE!"
echo - **Files**: (List changed files.)>> "!CHANGELOG_FILE!"
echo - **Verification**: (Test results and KPI status.)>> "!CHANGELOG_FILE!"

echo [OK] Changelog entry appended to: !CHANGELOG_FILE!
echo.
echo [MANUAL] Open !CHANGELOG_FILE! and fill in the change details.
echo.

REM =============================================================================
REM Step F -- Git staging safety check
REM =============================================================================
echo === Step F: Git Staging Safety Check ===

set "FORBIDDEN_FOUND=0"

for /f "tokens=1,*" %%a in ('git status --short 2^>nul') do (
    set "FILE_PATH=%%b"
    if "!FILE_PATH!"==".env" (
        echo [ERROR] Forbidden file detected: .env -- Do NOT commit this file.
        set "FORBIDDEN_FOUND=1"
    )
    echo !FILE_PATH! | findstr /b "server\models\" >nul 2>&1
    if not errorlevel 1 (
        echo [ERROR] Forbidden file detected: !FILE_PATH! -- Do NOT commit model weights.
        set "FORBIDDEN_FOUND=1"
    )
    echo !FILE_PATH! | findstr /b "server/models/" >nul 2>&1
    if not errorlevel 1 (
        echo [ERROR] Forbidden file detected: !FILE_PATH! -- Do NOT commit model weights.
        set "FORBIDDEN_FOUND=1"
    )
)

if "!FORBIDDEN_FOUND!"=="1" (
    echo [ERROR] Forbidden files detected. Add to .gitignore and remove from staging.
    exit /b 1
)
echo [OK] No forbidden files detected.
echo.

REM =============================================================================
REM Step G -- Git commit
REM =============================================================================
echo === Step G: Git Commit ===

set /p PREFIX=Enter commit prefix (e.g. stage1, docs, infra, test):
set /p DESC=Enter commit description: 

set "COMMIT_MSG=!PREFIX!: !DESC!"
echo.
echo [INFO] Commit message: !COMMIT_MSG!

set /p COMMIT_CONFIRM=Confirm commit message? (y/N): 
if /i not "!COMMIT_CONFIRM!"=="y" (
    echo [WARN] Commit cancelled by user.
    exit /b 1
)

git add .
git commit -m "!COMMIT_MSG!"
if errorlevel 1 (
    echo [ERROR] Commit failed.
    exit /b 1
)
echo [OK] Committed: !COMMIT_MSG!
echo.

REM =============================================================================
REM Step H -- Git push
REM =============================================================================
echo === Step H: Git Push ===
echo [INFO] Pushing to origin/!INITIAL!...

git push origin !INITIAL!
if errorlevel 1 (
    echo [ERROR] Push failed. Check your remote connection.
    exit /b 1
)
echo [OK] Pushed to origin/!INITIAL!.
echo.

REM =============================================================================
REM Step I -- PR creation (optional)
REM =============================================================================
echo === Step I: Pull Request (Optional) ===

set "PR_STATUS=skipped"
set /p CREATE_PR=Create a Pull Request to dev now? (y/N): 

if /i "!CREATE_PR!"=="y" (
    set /p PR_TITLE=Enter PR title: 
    gh pr create --base dev --head !INITIAL! --title "!PR_TITLE!"
    if errorlevel 1 (
        echo [WARN] PR creation failed. Create it manually.
        set "PR_STATUS=failed"
    ) else (
        echo [OK] Pull Request created.
        set "PR_STATUS=created"
    )
    echo.
    echo [MANUAL] Add to PR description: changed files, test results (KPI), dual-path confirmation.
) else (
    echo.
    echo [INFO] To create a PR manually:
    echo   gh pr create --base dev --head !INITIAL! --title "[Stage !STAGE!] !SUMMARY!"
)
echo.

REM =============================================================================
REM Step J -- Document consistency reminder
REM =============================================================================
echo === Step J: Document Consistency Check ===
echo.
echo   [DOCUMENT CONSISTENCY CHECK -- Verify manually]
echo     [ ] New files added? -^> Update Directory_Structure.md
echo     [ ] New env variables? -^> Update .env.example and README.md
echo     [ ] New dependencies? -^> Update requirements.txt (team approval required)
echo     [ ] API contract changed? -^> Update docs\api_specification.md
echo     [ ] Architecture changed? -^> Update docs\architecture.md
echo.

REM =============================================================================
REM Step K -- Final summary
REM =============================================================================
echo === Post-work Summary ===
echo.
echo   Branch     : !INITIAL!
echo   Stage      : !STAGE!
echo   Date       : !DATE!
echo   Changelog  : !CHANGELOG_FILE! (entry appended)
echo   Committed  : !COMMIT_MSG!
echo   Pushed     : origin/!INITIAL!
echo   PR         : !PR_STATUS!
echo   ---
echo   [MANUAL] Fill in changelog entry details in !CHANGELOG_FILE!
echo   [MANUAL] Document consistency checks
echo.
echo ===========================================
echo   Post-work complete. Good job!
echo ===========================================

endlocal
