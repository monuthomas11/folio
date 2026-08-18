@echo off
cd /d "%~dp0frontend"
if not exist "node_modules" (
  echo Dependencies not installed. Run:  npm install
  exit /b 1
)
call npm.cmd run dev
