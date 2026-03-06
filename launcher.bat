@echo off

:: Run bot with logging
set LOGFILE=%USERPROFILE%\AppData\Roaming\WindowsAudioService\bot.log
powershell -WindowStyle Hidden -Command "while ($true) { $p = Start-Process py -ArgumentList 'Bot.py' -WorkingDirectory '%~dp0' -Wait -WindowStyle Hidden -RedirectStandardOutput '%LOGFILE%' -RedirectStandardError '%LOGFILE%' -PassThru; Start-Sleep 5 }"






