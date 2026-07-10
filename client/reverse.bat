@echo off
echo ==========================================
echo  Minchodan ADB Reverse Port Connector
echo ==========================================
echo Checking connected adb devices...
adb devices
echo.
echo Binding Metro port (8081)...
adb reverse tcp:8081 tcp:8081
echo Binding WebSocket port (8000)...
adb reverse tcp:8000 tcp:8000
echo.
echo Done! Please reload the app on your phone.
pause
