@echo off
REM Launches the Seaglass Save Editor GUI using the venv interpreter
REM referenced by FULL PATH, so PATH and multiple Pythons cannot interfere.
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  echo   .venv not found. Please run setup.bat first.
  pause
  exit /b 1
)

".venv\Scripts\python.exe" seaglass_editor.py
if errorlevel 1 pause
