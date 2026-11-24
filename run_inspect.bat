@echo off
REM Runs the phase-1 read-only inspector using the venv interpreter
REM referenced by FULL PATH, so PATH and multiple Pythons can't interfere.
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  echo   .venv not found. Please run setup.bat first.
  pause
  exit /b 1
)

".venv\Scripts\python.exe" seaglass_inspect.py %*
pause

