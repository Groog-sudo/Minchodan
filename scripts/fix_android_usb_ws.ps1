# Minchodan Android USB WS fix helper
# Usage:
#   powershell -ExecutionPolicy Bypass -File .\scripts\fix_android_usb_ws.ps1

$ErrorActionPreference = "Stop"

$serial = "R3CN90RKBRM"

Write-Host "[1/4] ADB devices"
adb devices -l

Write-Host "[2/4] Disconnect Wi-Fi ADB to avoid multi-device reverse failures"
adb disconnect 192.168.0.60:5555 | Out-Null

Write-Host "[3/4] Ensure only USB target is available"
adb devices -l

Write-Host "[4/4] Apply reverse mappings to USB device"
adb -s $serial reverse tcp:8081 tcp:8081
adb -s $serial reverse tcp:8000 tcp:8000
adb -s $serial reverse --list

Write-Host "Done. Keep app transport on USB mode and use ws://127.0.0.1:8000/ws/detect"
