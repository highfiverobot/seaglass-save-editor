@echo off
REM ---------------------------------------------------------------
REM  One-time setup. Double-click me.
REM  Creates a local virtual environment (.venv) using the `py`
REM  launcher, then installs dependencies INTO that venv.
REM  Nothing here relies on `python` being on PATH.
REM ---------------------------------------------------------------
setlocal
cd /d "%~dp0"

echo [1/3] Checking for the py launcher...
py -3 --version >nul 2>&1
if errorlevel 1 (
  echo.
  echo   ERROR: The `py` launcher was not found.
  echo   Install Python 3.x from https://www.python.org/downloads/windows/
  echo   and be sure to tick "py launcher" during install.
  echo.
  pause
  exit /b 1
)

echo [2/3] Creating virtual environment in .venv ...
if not exist ".venv\Scripts\python.exe" (
  py -3 -m venv .venv
  if errorlevel 1 (
    echo   ERROR: failed to create the virtual environment.
    pause
    exit /b 1
  )
) else (
  echo   .venv already exists, reusing it.
)

echo [3/3] Installing dependencies into .venv ...
".venv\Scripts\python.exe" -m pip install --upgrade pip
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 (
  echo   ERROR: dependency install failed.
  pause
  exit /b 1
)

echo.
echo   Done. Launch the editor with: run_app.bat
echo   (Optional) read-only inspector: run_inspect.bat

echo.
pause
