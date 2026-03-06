@echo off

:: Auto-elevate to admin
net session >nul 2>&1
if errorlevel 1 (
    powershell -Command "Start-Process '%~f0' -Verb RunAs"
    exit
)

:: Run bot fully hidden with no window
powershell -WindowStyle Hidden -Command "while ($true) { Start-Process py -ArgumentList 'Bot.py' -WorkingDirectory '%~dp0' -Wait -WindowStyle Hidden; Start-Sleep 5 }"
