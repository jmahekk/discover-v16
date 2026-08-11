@echo off
title DISCOVER v15 - PUBLIC
rem Publishes DISCOVER v15 to a public URL via ngrok.
rem Step 1 of this file starts the app; then it opens the ngrok tunnel.
rem One-time setup (do ONCE, see instructions): install ngrok and run
rem     ngrok config add-authtoken YOUR_TOKEN

cd /d "%~dp0"
set PYTHONIOENCODING=utf-8
set HF_HUB_OFFLINE=1
set TRANSFORMERS_OFFLINE=1

echo.
echo  [1/2] Starting DISCOVER v15 server (wait for "Uvicorn running")...
echo.
start "DISCOVER v15 server" venv\Scripts\python.exe -m uvicorn api:app --port 8000

echo  Waiting 75 seconds for the app to finish loading...
timeout /t 75 /nobreak

echo.
echo  [2/2] Opening the public tunnel. Your public URL appears below
echo        as "Forwarding  https://xxxx.ngrok-free.app".
echo        Share that https link with anyone. Keep BOTH windows open.
echo.
"%~dp0ngrok.exe" http 8000

pause
