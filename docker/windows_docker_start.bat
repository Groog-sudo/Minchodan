@echo off
setlocal

cd /d "%~dp0"

echo.
echo ========================================
echo DoctorSkin Docker Build and Start
echo ========================================
echo.

docker info >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Docker is not running.
    echo Please start Docker Desktop and try again.
    echo.
    pause
    exit /b 1
)

if not exist ".env" (
    echo [ERROR] .env file not found.
    echo.
    echo Please copy .env.example to .env, then edit DB password,
    echo SECRET_KEY, API keys, and other environment values.
    echo.
    echo Command:
    echo copy .env.example .env
    echo.
    pause
    exit /b 1
)

set "HOST_PORT=8100"
for /f "usebackq tokens=1,* delims==" %%A in (".env") do (
    if /i "%%A"=="HOST_PORT" set "HOST_PORT=%%B"
)

echo [1/4] Checking Docker Compose config...
docker compose config --quiet
if errorlevel 1 (
    echo.
    echo [ERROR] docker-compose.yml or .env has a configuration problem.
    echo Please check the error message above.
    echo.
    pause
    exit /b 1
)

echo.
echo [2/4] Preparing Docker image version...
set "DOCKER_IMAGE_TAG="
for /f "usebackq delims=" %%I in (`powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\bump_docker_tag.ps1" -Preview`) do set "DOCKER_IMAGE_TAG=%%I"
if not defined DOCKER_IMAGE_TAG (
    echo.
    echo [ERROR] Failed to prepare Docker image version.
    echo.
    pause
    exit /b 1
)

echo Image tag: doctorskin:%DOCKER_IMAGE_TAG%

echo.
echo [3/4] Building Docker image...
docker compose build
if errorlevel 1 (
    echo.
    echo [ERROR] Docker image build failed.
    echo.
    pause
    exit /b 1
)

echo.
echo Saving Docker image version...
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\bump_docker_tag.ps1" -SetTag "%DOCKER_IMAGE_TAG%" >nul
if errorlevel 1 (
    echo.
    echo [ERROR] Failed to save Docker image version.
    echo.
    pause
    exit /b 1
)

echo.
echo [4/4] Starting containers...
docker compose up -d
if errorlevel 1 (
    echo.
    echo [ERROR] Failed to start containers.
    echo.
    pause
    exit /b 1
)

echo.
echo ========================================
echo Done!
echo ========================================
echo.
echo Waiting for web server...
for /l %%I in (1,1,30) do (
    powershell -NoProfile -ExecutionPolicy Bypass -Command "$client = New-Object Net.Sockets.TcpClient; try { $async = $client.BeginConnect('127.0.0.1', %HOST_PORT%, $null, $null); if ($async.AsyncWaitHandle.WaitOne(1000)) { $client.EndConnect($async); exit 0 }; exit 1 } catch { exit 1 } finally { $client.Close() }" >nul 2>&1
    if not errorlevel 1 goto WEB_READY
    timeout /t 2 /nobreak >nul
)
echo [WARN] Web server is still starting. Opening the URL anyway.

:WEB_READY
echo URL:
echo http://127.0.0.1:%HOST_PORT%
echo.
start "" "http://127.0.0.1:%HOST_PORT%"

@REM echo PC URL:
@REM echo http://[IP_ADDRESS]/
@REM echo.

echo Logs:
echo docker compose logs -f web
echo.
echo Stop:
echo docker compose down
echo.

pause
endlocal
