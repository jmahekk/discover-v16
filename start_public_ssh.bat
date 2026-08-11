@echo off
title DISCOVER v15 - PUBLIC (ssh tunnel)
rem Publishes DISCOVER v15 to a public URL using the built-in Windows SSH
rem client and the free localhost.run service. No download, no ngrok,
rem nothing for antivirus to block.

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
echo  [2/2] Opening the public tunnel via localhost.run.
echo        Look for a line like:  https://xxxxxxxx.lhr.life
echo        THAT is your public link. Share it. Keep BOTH windows open.
echo.
ssh -o StrictHostKeyChecking=accept-new -R 80:localhost:8000 localhost.run

pause
