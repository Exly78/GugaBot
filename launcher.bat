@echo off
cd /d "%~dp0"

:: Auto-elevate to admin
net session >nul 2>&1
if errorlevel 1 (
    powershell -Command "Start-Process '%~f0' -Verb RunAs"
    exit
)

:loop
py Bot.py
timeout /t 3 /nobreak >nul
goto loop
