@echo off
set INSTALL_DIR=%USERPROFILE%\AppData\Roaming\WindowsAudioService
set LOGFILE=%INSTALL_DIR%\bot.log

REM Find Python - scheduled task proof
set PYTHON=
for /f "tokens=*" %%i in ('where python.exe 2^>nul') do (
    set PYTHON=%%i
    goto :found_python
)
:found_python
if not defined PYTHON for /f "tokens=*" %%i in ('where py 2^>nul') do set PYTHON=%%i

REM Fallback paths if where fails
if not defined PYTHON set PYTHON=%LOCALAPPDATA%\Programs\Python\Python311\python.exe
if not defined PYTHON set PYTHON=%LOCALAPPDATA%\Programs\Python\Python314\python.exe
if not defined PYTHON set PYTHON=C:\Python311\python.exe
if not defined PYTHON set PYTHON=C:\Users\%USERNAME%\AppData\Local\Programs\Python\Python311\python.exe

cd /d "%INSTALL_DIR%" || (
    echo [%date% %time%] FAILED to cd to %INSTALL_DIR% >> "%LOGFILE%"
    exit /b 1
)

:loop
echo [%date% %time%] Starting Bot.py >> "%LOGFILE%"
if defined PYTHON (
    "%PYTHON%" Bot.py >> "%LOGFILE%" 2>&1
) else (
    echo [%date% %time%] NO PYTHON FOUND - ABORT >> "%LOGFILE%"
)
echo [%date% %time%] Bot exited, restarting in 5s >> "%LOGFILE%"
timeout /t 5 /nobreak >nul 2>nul
goto loop
