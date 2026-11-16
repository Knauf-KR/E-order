@echo off
setlocal
rem Run from any OneDrive path. Do not put a PC-specific venv in the shared folder.
set "ASSET_DIR=%~dp0."
if exist "%~dp0ITAssetManager\app.py" (
  set "APP_DIR=%~dp0ITAssetManager"
) else if exist "%~dp0app.py" (
  set "APP_DIR=%~dp0."
  set "ASSET_DIR="
) else (
  echo The ITAssetManager folder must be beside launch.bat.
  pause
  exit /b 1
)
if not defined LOCALAPPDATA (
  echo LOCALAPPDATA is unavailable. Please contact IT support.
  pause
  exit /b 1
)
set "ASSET_VENV=%LOCALAPPDATA%\KnaufITAssetManager\venv"
if not exist "%ASSET_VENV%\Scripts\python.exe" (
  py -3 -c "import sys; assert sys.version_info >= (3,11); import tkinter" >nul 2>&1
  if errorlevel 1 (
    echo Install Python 3.11 or newer with Python Launcher, pip and Tcl/Tk.
    pause
    exit /b 1
  )
  py -3 -m venv "%ASSET_VENV%"
  if errorlevel 1 goto failed
)
"%ASSET_VENV%\Scripts\python.exe" -c "import sys; assert sys.version_info >= (3,11); import tkinter" >nul 2>&1
if errorlevel 1 (
  echo The local Python environment needs repair. Please contact IT support.
  pause
  exit /b 1
)
"%ASSET_VENV%\Scripts\python.exe" -c "import openpyxl; assert openpyxl.__version__ == '3.1.5'" >nul 2>&1
if errorlevel 1 (
  "%ASSET_VENV%\Scripts\python.exe" -m pip install -r "%APP_DIR%\requirements.txt"
  if errorlevel 1 goto failed
)
if defined ASSET_DIR (
  "%ASSET_VENV%\Scripts\python.exe" "%APP_DIR%\app.py" --asset-dir "%ASSET_DIR%"
) else (
  "%ASSET_VENV%\Scripts\python.exe" "%APP_DIR%\app.py"
)
if errorlevel 1 goto failed
exit /b 0
:failed
echo.
echo Setup or launch failed. Please send the error text for support.
pause
exit /b 1
