@echo off
setlocal

rem Minchodan Docker Build and Start - Windows
rem Redis + MariaDB + FastAPI 3컨테이너 구성 + host-local Ollama
rem 상세 명세: docs/ops/deployment_guide.md

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
    echo Please start Docker Desktop or another Docker daemon and try again.
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

echo ========================================
echo Choose Hardware Execution Mode:
echo   [1] GPU Mode (NVIDIA GPU + CUDA/WSL2 required)
echo   [2] CPU Only Mode (macOS / Windows without NVIDIA GPU)
echo ========================================
set /p MODE="Enter choice (1 or 2, default is 1): "
if "%MODE%"=="" set MODE=1

set COMPOSE_FILE=docker\docker-compose.yml
if "%MODE%"=="2" (
    set COMPOSE_FILE=docker\docker-compose.macos.yml
)
echo Using config: %COMPOSE_FILE%
echo.

rem 5. docker compose 설정 유효성 검사
echo [1/4] Checking Docker Compose config...
docker compose --env-file .env -f %COMPOSE_FILE% config --quiet
if errorlevel 1 (
    echo.
    echo [ERROR] %COMPOSE_FILE% or .env has a configuration problem.
    echo Please check the error message above.
    echo.
    pause
    exit /b 1
)

rem 6. Docker 이미지 빌드
echo.
echo [2/4] Building Docker images (FastAPI)...
docker compose --env-file .env -f %COMPOSE_FILE% build fastapi
if errorlevel 1 (
    echo.
    echo [ERROR] Docker image build failed.
    echo.
    pause
    exit /b 1
)

rem 7. 컨테이너 시작
echo.
echo [3/4] Starting containers (Redis + MariaDB + FastAPI)...
docker compose --env-file .env -f %COMPOSE_FILE% up -d
if errorlevel 1 (
    echo.
    echo [ERROR] Failed to start containers.
    echo.
    pause
    exit /b 1
)

rem 8. FastAPI 포트 대기 (최대 60초)
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
echo [FastAPI] WebSocket:
echo   ws://127.0.0.1:%WS_PORT%/ws/detect
echo   Swagger: http://127.0.0.1:%WS_PORT%/docs
echo.
echo [Tailscale] 외부 접속용 호스트 확인:
echo   tailscale ip -4
echo   client\.env의 EXPO_PUBLIC_TAILSCALE_HOST에 위 IP 또는 MagicDNS 이름 입력
echo.
echo [Expo] 호스트 PC에서 별도 실행 필요:
echo   cd client
echo   npx expo start
echo   (스마트폰 Expo Go 앱에서 QR 코드 스캔)
echo.
echo [Ollama] 호스트 로컬에서 별도 실행 필요:
echo   ollama serve
echo   (최초 1회) ollama pull gemma4:e4b
echo   (최초 1회) ollama pull nomic-embed-text
echo.
echo Logs:
echo   docker compose --env-file .env -f %COMPOSE_FILE% logs -f fastapi
echo.
echo Stop:
echo   docker compose --env-file .env -f %COMPOSE_FILE% down
echo.

pause
endlocal
