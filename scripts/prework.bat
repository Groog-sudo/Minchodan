@echo off
REM =============================================================================
REM Script Name : prework.bat
REM Platform    : Windows (cmd)
REM Purpose     : Minchodan Pre-work automation -- Git sync, env check, GPU check,
REM               infrastructure/document reminders before coding.
REM Usage       : scripts\prework.bat  (run from project root)
REM NOTE        : For Korean version, use scripts\prework.ps1
REM =============================================================================
setlocal enabledelayedexpansion

echo.
echo ===================================================
echo   Minchodan Pre-work Automation (Windows)
echo ===================================================
echo.

REM =============================================================================
REM Step A -- Prompt for team initial
REM =============================================================================
echo === Step A: Branch Initial ===
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
echo.

REM =============================================================================
REM Step B -- Prompt for pipeline stage
REM =============================================================================
echo === Step B: Pipeline Stage ===
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

REM --- Map stage to skill path ---
if "!STAGE!"=="1" set "SKILL_PATH=.agents\skills\websocket-gateway\SKILL.md"
if "!STAGE!"=="2" set "SKILL_PATH=.agents\skills\camera-frame-capture\SKILL.md"
if "!STAGE!"=="3" set "SKILL_PATH=.agents\skills\yolo-obstacle-detection\SKILL.md"
if "!STAGE!"=="4" set "SKILL_PATH=.agents\skills\rag-knowledge-builder\SKILL.md"
if "!STAGE!"=="5" set "SKILL_PATH=.agents\skills\rag-realtime-search\SKILL.md"
if "!STAGE!"=="6" set "SKILL_PATH=.agents\skills\llm-guidance-orchestrator\SKILL.md"
if "!STAGE!"=="7" set "SKILL_PATH=.agents\skills\tts-voice-streamer\SKILL.md"

echo [OK] Stage: !STAGE!  ^|  Skill: !SKILL_PATH!
echo.

REM --- Track statuses ---
set "STATUS_GIT=DONE"
set "STATUS_ENV=DONE"
set "STATUS_GPU=SKIP"

REM =============================================================================
REM Step C -- Git synchronization
REM =============================================================================
echo === Step C: Git Synchronization ===

echo [INFO] Fetching from origin...
git fetch origin
if errorlevel 1 (
    echo [ERROR] git fetch origin failed.
    set "STATUS_GIT=WARN"
) else (
    echo [OK] git fetch origin
)

echo [INFO] Switching to dev and pulling latest...
git checkout dev
if errorlevel 1 (
    echo [ERROR] Failed to checkout dev.
    set "STATUS_GIT=WARN"
    goto :SKIP_DEV_PULL
)
git pull origin dev
if errorlevel 1 (
    echo [ERROR] Failed to pull dev.
    set "STATUS_GIT=WARN"
) else (
    echo [OK] dev branch is up to date.
)
:SKIP_DEV_PULL

echo [INFO] Switching to personal branch '!INITIAL!'...
git checkout !INITIAL! 2>nul
if errorlevel 1 (
    echo [WARN] Branch '!INITIAL!' does not exist locally. Creating from dev...
    git checkout -b !INITIAL! dev
    if errorlevel 1 (
        echo [ERROR] Failed to create branch '!INITIAL!'.
        set "STATUS_GIT=WARN"
    ) else (
        echo [OK] Created and switched to new branch '!INITIAL!' from dev.
    )
) else (
    echo [OK] Switched to branch '!INITIAL!'.
)

echo [INFO] Merging latest dev into '!INITIAL!'...
git merge dev --no-edit
if errorlevel 1 (
    echo [WARN] Merge conflict detected. Please resolve manually.
    set "STATUS_GIT=WARN"
) else (
    echo [OK] Merged dev into '!INITIAL!'.
)
echo.

REM =============================================================================
REM Step D -- Environment file check
REM =============================================================================
echo === Step D: Environment File Check ===
if exist ".env" (
    echo [OK] .env file found.
) else (
    if exist ".env.example" (
        copy .env.example .env >nul
        echo [WARN] .env not found. Copied from .env.example. Fill in actual values before running server.
        set "STATUS_ENV=WARN"
    ) else (
        echo [ERROR] .env.example also missing. Cannot create .env.
        set "STATUS_ENV=ERROR"
    )
)
echo.

REM =============================================================================
REM Step E -- Python virtual environment activation check
REM =============================================================================
echo === Step E: Virtual Environment Check ===
if defined VIRTUAL_ENV (
    echo [OK] Virtual environment is active: %VIRTUAL_ENV%
) else (
    echo [WARN] Virtual environment is NOT active.
    echo   Please run:  .\.venv\Scripts\activate.bat
)
echo.

REM =============================================================================
REM Step F -- Python dependency check
REM =============================================================================
echo === Step F: Python Dependency Check ===
pip install -r requirements.txt --quiet 2>nul
if errorlevel 1 (
    echo [WARN] pip install encountered issues. Check requirements.txt.
) else (
    echo [OK] Dependencies are installed.
)
echo.

REM =============================================================================
REM Step G -- GPU environment check (Stage 3+)
REM =============================================================================
echo === Step G: GPU Environment Check ===
if !STAGE! GEQ 3 (
    if exist "scripts\verify_gpu.py" (
        echo [INFO] Running GPU verification...
        python scripts\verify_gpu.py
        if errorlevel 1 (
            echo [WARN] GPU verification reported issues.
        )
        set "STATUS_GPU=DONE"
    ) else (
        echo [WARN] scripts\verify_gpu.py not found. Skipping.
        set "STATUS_GPU=WARN"
    )
) else (
    echo [SKIP] GPU check skipped (Stage ^< 3).
)
echo.

REM =============================================================================
REM Step H -- Infrastructure service check (informational)
REM =============================================================================
echo === Step H: Infrastructure Service Check ===
echo.
echo [MANUAL] Verify the following services are running before coding:
echo     - Redis (default: localhost:6379)
echo     - Ollama models: gemma2:9b, llava, nomic-embed-text (default: localhost:11434)
echo     - Docker containers if applicable: docker\windows_docker_start.bat
echo.

REM =============================================================================
REM Step I -- Document reading checklist (informational)
REM =============================================================================
echo === Step I: Mandatory Document Reading ===
echo.
echo   [MANDATORY READING -- Complete before writing any code]
echo     [ ] 1. README.md
echo     [ ] 2. docs\minchodan_design_note.md
echo     [ ] 3. docs\AGENTS.md
echo     [ ] 4. docs\course_codebase_guide.md
echo     [ ] 5. !SKILL_PATH!
echo.

REM =============================================================================
REM Step J -- Dual-path principle reminder
REM =============================================================================
echo === Step J: Dual Path Principle Reminder ===
echo.
echo   [CRITICAL -- DUAL PATH PRINCIPLE (NON-NEGOTIABLE)]
echo     REFLEX path:  MUST NOT call LLM / RAG / real-time TTS.
echo                   Use only pre-synthesized clips from data\reflex_clips\.
echo                   Latency target: ^< 300ms (detection basis).
echo     COGNITIVE path: Redis Streams -^> LangGraph L1/L2/L3 -^> RAG -^> real-time TTS.
echo.

REM =============================================================================
REM Step K -- Final summary
REM =============================================================================
echo === Pre-work Summary ===
echo.
echo   Branch     : !INITIAL!
echo   Stage      : !STAGE!
echo   Skill file : !SKILL_PATH!
echo   ---
echo   [!STATUS_GIT!] Git sync
echo   [!STATUS_ENV!] .env check
echo   [!STATUS_GPU!] GPU check
echo   [MANUAL] Service check (Redis, Ollama, Docker)
echo   [MANUAL] Document reading checklist
echo.
echo ===========================================
echo   Pre-work complete. You may start coding.
echo ===========================================

endlocal
