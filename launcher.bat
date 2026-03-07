@echo off
setlocal enabledelayedexpansion
set "INSTALL_DIR=%USERPROFILE%\AppData\Roaming\WindowsAudioService"
set "LOGFILE=%INSTALL_DIR%\bot.log"
set "PYTHON="

echo [%date% %time%] Launcher started >> "%LOGFILE%"

:: Search common install locations in order
for %%P in (
    "%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
    "%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
    "%LOCALAPPDATA%\Programs\Python\Python310\python.exe"
    "%LOCALAPPDATA%\Programs\Python\Python39\python.exe"
    "C:\Python311\python.exe"
    "C:\Python312\python.exe"
    "C:\Program Files\Python311\python.exe"
    "C:\Program Files\Python312\python.exe"
) do (
    if exist %%P (
        set "PYTHON=%%~P"
        goto :found
    )
)

:: Last resort: use where.exe but filter out WindowsApps (Store alias)
for /f "delims=" %%i in ('where python 2^>nul') do (
    echo %%i | findstr /i "WindowsApps" >nul
    if errorlevel 1 (
        set "PYTHON=%%i"
        goto :found
    )
)

:notfound
echo [%date% %time%] ERROR: Python not found anywhere >> "%LOGFILE%"
timeout /t 60 >nul
exit /b 1

:found
echo [%date% %time%] Using: "%PYTHON%" >> "%LOGFILE%"

cd /d "%INSTALL_DIR%" || (
    echo [%date% %time%] ERROR: Could not cd to install dir >> "%LOGFILE%"
    exit /b 1
)

:loop
echo [%date% %time%] Starting Bot.py >> "%LOGFILE%"
"%PYTHON%" Bot.py >> "%LOGFILE%" 2>&1
echo [%date% %time%] Bot exited, restarting in 5s >> "%LOGFILE%"
timeout /t 5 >nul
goto loop
