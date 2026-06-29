@echo off
setlocal

rem Minchodan Docker Build and Start - Windows
rem Redis + Ollama + FastAPI 3컨테이너 구성
rem 상세 명세: docs/deployment_guide.md

cd /d "%~dp0\.."

echo.
echo ========================================
echo Minchodan Docker Build and Start
echo ========================================
echo.

rem 1. Docker 데몬 실행 여부 확인
docker info >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Docker is not running.
    echo Please start Docker Desktop and try again.
    echo.
    pause
    exit /b 1
)

rem 2. .env 파일 존재 여부 확인
if not exist ".env" (
    echo [ERROR] .env file not found.
    echo.
    echo Please copy .env.example to .env, then edit environment values.
    echo See docs/environment_variables.md for variable details.
    echo.
    echo Command:
    echo copy .env.example .env
    echo.
    pause
    exit /b 1
)

rem 3. docker compose 설정 유효성 검사
echo [1/4] Checking Docker Compose config...
docker compose -f docker\docker-compose.yml config --quiet
if errorlevel 1 (
    echo.
    echo [ERROR] docker-compose.yml or .env has a configuration problem.
    echo Please check the error message above.
    echo.
    pause
    exit /b 1
)

rem 4. Docker 이미지 빌드
echo.
echo [2/4] Building Docker images (FastAPI)...
docker compose -f docker\docker-compose.yml build fastapi
if errorlevel 1 (
    echo.
    echo [ERROR] Docker image build failed.
    echo.
    pause
    exit /b 1
)

rem 5. 컨테이너 시작
echo.
echo [3/4] Starting containers (Redis + Ollama + FastAPI)...
docker compose -f docker\docker-compose.yml up -d
if errorlevel 1 (
    echo.
    echo [ERROR] Failed to start containers.
    echo.
    pause
    exit /b 1
)

rem 6. FastAPI 포트 대기 (최대 60초)
echo.
echo [4/4] Waiting for FastAPI server (port 8000)...
set WS_PORT=8000
for /f "usebackq tokens=1,* delims==" %%A in (".env") do (
    if /i "%%A"=="WS_PORT" set "WS_PORT=%%B"
)

for /l %%I in (1,1,30) do (
    powershell -NoProfile -ExecutionPolicy Bypass -Command "$client = New-Object Net.Sockets.TcpClient; try { $async = $client.BeginConnect('127.0.0.1', %WS_PORT%, $null, $null); if ($async.AsyncWaitHandle.WaitOne(2000)) { $client.EndConnect($async); exit 0 }; exit 1 } catch { exit 1 } finally { $client.Close() }" >nul 2>&1
    if not errorlevel 1 goto WEB_READY
    timeout /t 2 /nobreak >nul
)
echo [WARN] FastAPI server is still starting. Continuing anyway.

:WEB_READY
echo.
echo ========================================
echo Done!
echo ========================================
echo.
echo FastAPI URL:
echo http://127.0.0.1:%WS_PORT%/docs
echo.
echo Ollama URL:
echo http://127.0.0.1:11434/api/tags
echo.
echo Next steps (first run only):
echo   docker exec -it minchodan-ollama ollama pull gemma2:9b
echo   docker exec -it minchodan-ollama ollama pull llava
echo   docker exec -it minchodan-ollama ollama pull nomic-embed-text
echo.
echo Logs:
echo   docker compose -f docker\docker-compose.yml logs -f fastapi
echo.
echo Stop:
echo   docker compose -f docker\docker-compose.yml down
echo.

pause
endlocal
