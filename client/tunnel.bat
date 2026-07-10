:loop
C:\Users\USER\AppData\Local\Android\Sdk\platform-tools\adb.exe reverse tcp:8081 tcp:8081
C:\Users\USER\AppData\Local\Android\Sdk\platform-tools\adb.exe reverse tcp:8000 tcp:8000
timeout /t 2 /nobreak > nul
goto loop
