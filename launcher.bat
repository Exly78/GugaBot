@echo off

:: Run bot fully hidden with no window
powershell -WindowStyle Hidden -Command "while ($true) { Start-Process py -ArgumentList 'Bot.py' -WorkingDirectory '%~dp0' -Wait -WindowStyle Hidden; Start-Sleep 5 }"
