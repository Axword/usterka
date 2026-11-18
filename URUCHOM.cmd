@echo off
cd /d "%~dp0"
docker compose up --build -d || (pause & exit /b 1)
timeout /t 5 >nul
start http://localhost:5173/
