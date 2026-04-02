@echo off
title GamblAI — Starting...
cd /d "%~dp0"

echo.
echo  ==========================================
echo   GamblAI — AI Prediction Market Bot
echo  ==========================================
echo.
echo  Starting dashboard on http://localhost:8000
echo  Starting pipeline loop (every 30 minutes)
echo.
echo  Keep both windows open to keep the bot running.
echo  Dashboard auto-refreshes every 30s in your browser.
echo.
pause

:: Start dashboard in a new window
start "GamblAI Dashboard" cmd /k ".venv\Scripts\python.exe main.py dashboard --host 127.0.0.1 --port 8000"

:: Give dashboard 3 seconds to boot
timeout /t 3 /nobreak >nul

:: Open browser
start http://localhost:8000

:: Start pipeline loop in this window
title GamblAI — Pipeline Loop (30 min interval)
.venv\Scripts\python.exe main.py loop --interval 1800
