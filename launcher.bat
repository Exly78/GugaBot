@echo off
setlocal enabledelayedexpansion
set "INSTALL_DIR=%USERPROFILE%\AppData\Roaming\WindowsAudioService"
set "LOGFILE=%INSTALL_DIR%\bot.log"

REM Python path - auto-patched by setup.bat, fallback to py launcher
set "PYTHON=%LOCALAPPDATA%\Programs\Python\Python311\python.exe"

REM If hardcoded path missing, fall back to 'py' launcher
if not exist "%PYTHON%" (
    for /f "delims=" %%i in ('py -c "import sys; print(sys.executable)" 2^>nul') do set "PYTHON=%%i"
)

echo [%date% %time%] Using: "%PYTHON%" >> "%LOGFILE%"

if not exist "%PYTHON%" (
    echo [%date% %time%] ERROR: Python not found >> "%LOGFILE%"
    timeout /t 30 >nul
    exit /b 1
)

cd /d "%INSTALL_DIR%" || (
    echo [%date% %time%] ERROR: Directory failed >> "%LOGFILE%"
    exit /b 1
)

:loop
echo [%date% %time%] Launching Bot.py >> "%LOGFILE%"
"%PYTHON%" Bot.py >> "%LOGFILE%" 2>&1
echo [%date% %time%] Bot stopped, restarting in 5s >> "%LOGFILE%"
timeout /t 5 >nul
goto loop
