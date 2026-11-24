@echo off
REM =====================================================================
REM  build_exe.bat  --  build a single-file Windows exe with PyInstaller
REM
REM  Usage:
REM    1. Make sure the venv exists (run setup.bat once).
REM    2. Double-click this file (or run it from a terminal).
REM    3. The finished exe appears in:  dist\SeaglassEditor.exe
REM
REM  If you add an icon later, put app.ico next to this script and it
REM  will be picked up automatically.
REM =====================================================================
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  echo   .venv not found. Run setup.bat first.
  pause
  exit /b 1
)

REM Install/refresh PyInstaller if missing.
".venv\Scripts\python.exe" -m PyInstaller --version >nul 2>&1
if errorlevel 1 (
  echo   Installing PyInstaller...
  ".venv\Scripts\python.exe" -m pip install pyinstaller
)

REM Optional icon.
set ICON_ARG=
if exist "app.ico" set ICON_ARG=--icon app.ico

echo.
echo   Building one-file exe (this can take a minute)...
echo.

".venv\Scripts\python.exe" -m PyInstaller ^
  --noconfirm ^
  --clean ^
  --onefile ^
  --windowed ^
  --name SeaglassEditor ^
  %ICON_ARG% ^
  --hidden-import PySide6.QtCore ^
  --hidden-import PySide6.QtGui ^
  --hidden-import PySide6.QtWidgets ^
  seaglass_editor.py

if errorlevel 1 (
  echo.
  echo   BUILD FAILED. See messages above.
  pause
  exit /b 1
)

echo.
echo   Done. Exe is at: dist\SeaglassEditor.exe
echo.
pause
