@echo off
cd /d "%~dp0backend"
if not exist ".venv\Scripts\python.exe" (
  echo Python venv not found. Run:  python -m venv .venv  then install requirements
  exit /b 1
)
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
