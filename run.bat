@echo off
setlocal
".venv\Scripts\python.exe" main.py 2>&1
echo 退出码: %ERRORLEVEL%
endlocal