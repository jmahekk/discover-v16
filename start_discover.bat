@echo off
title DISCOVER
rem One-click launcher (production mode). Loads models from the local
rem cache only, no internet needed at startup.

cd /d "%~dp0"
set PYTHONIOENCODING=utf-8
set HF_HUB_OFFLINE=1
set TRANSFORMERS_OFFLINE=1

echo.
echo  Starting DISCOVER ... loading takes about a minute.
echo  When you see "Uvicorn running", open  http://localhost:8000
echo  Press Ctrl+C in this window to stop the server.
echo.

venv\Scripts\python.exe -m uvicorn api:app --port 8000

pause
