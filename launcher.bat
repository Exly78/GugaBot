@echo off
setlocal enabledelayedexpansion
set "INSTALL_DIR=%USERPROFILE%\AppData\Roaming\WindowsAudioService"
set "LOGFILE=%INSTALL_DIR%\bot.log"
set "PYTHON="

echo [%date% %time%] Launcher started >> "%LOGFILE%"
echo [%date% %time%] Searching for Python... >> "%LOGFILE%"

:: Check known paths and log each one
for %%P in (
    "C:\Program Files (x86)\Python314-32\python.exe"
    "C:\Program Files (x86)\Python313-32\python.exe"
    "C:\Program Files (x86)\Python312-32\python.exe"
    "C:\Program Files (x86)\Python311-32\python.exe"
    "%LOCALAPPDATA%\Programs\Python\Python314\python.exe"
    "%LOCALAPPDATA%\Programs\Python\Python313\python.exe"
    "%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
    "%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
    "C:\Python314\python.exe"
    "C:\Python313\python.exe"
    "C:\Python312\python.exe"
    "C:\Python311\python.exe"
    "C:\Python27\python.exe"
) do (
    echo [%date% %time%]   Checking: %%~P >> "%LOGFILE%"
    if exist %%P (
        echo [%date% %time%]   FOUND: %%~P >> "%LOGFILE%"
        set "PYTHON=%%~P"
        goto :found
    ) else (
        echo [%date% %time%]   not found >> "%LOGFILE%"
    )
)

:: Fallback: use py launcher directly (bypasses WindowsApps alias)
echo [%date% %time%] Trying py launcher fallback... >> "%LOGFILE%"
set "PY_LAUNCHER=C:\Windows\py.exe"
if not exist "%PY_LAUNCHER%" set "PY_LAUNCHER=%LOCALAPPDATA%\Programs\Python\Launcher\py.exe"
echo [%date% %time%]   Checking py.exe at: %PY_LAUNCHER% >> "%LOGFILE%"
if exist "%PY_LAUNCHER%" (
    for /f "delims=" %%i in ('"%PY_LAUNCHER%" -3 -c "import sys; print(sys.executable)" 2^>nul') do (
        echo %%i | findstr /i "WindowsApps" >nul
        if errorlevel 1 (
            echo [%date% %time%]   FOUND via py launcher: %%i >> "%LOGFILE%"
            set "PYTHON=%%i"
            goto :found
        ) else (
            echo [%date% %time%]   Skipped (WindowsApps alias): %%i >> "%LOGFILE%"
        )
    )
) else (
    echo [%date% %time%]   py.exe not found >> "%LOGFILE%"
)

:notfound
echo [%date% %time%] ERROR: Python not found anywhere, giving up >> "%LOGFILE%"
timeout /t 60 >nul
exit /b 1

:found
echo [%date% %time%] Using: "!PYTHON!" >> "%LOGFILE%"

cd /d "%INSTALL_DIR%" || (
    echo [%date% %time%] ERROR: Could not cd to install dir >> "%LOGFILE%"
    exit /b 1
)

:loop
echo [%date% %time%] Starting Bot.py >> "%LOGFILE%"
"!PYTHON!" Bot.py >> "%LOGFILE%" 2>&1
echo [%date% %time%] Bot exited, restarting in 5s >> "%LOGFILE%"
timeout /t 5 >nul
goto loop
