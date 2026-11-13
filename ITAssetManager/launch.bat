@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  py -3 --version >nul 2>&1
  if errorlevel 1 (
    echo Python 3.11 or newer is required. Install from python.org with the Python Launcher.
    echo Then double-click launch.bat again.
    pause
    exit /b 1
  )
  py -3 -m venv .venv
  if errorlevel 1 goto failed
)
".venv\Scripts\python.exe" -c "import sys; assert sys.version_info >= (3,11); import tkinter" >nul 2>&1
if errorlevel 1 (
  echo Python 3.11 or newer with Tcl/Tk is required.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" -c "import openpyxl; assert openpyxl.__version__ == '3.1.5'" >nul 2>&1
if errorlevel 1 (
  ".venv\Scripts\python.exe" -m pip install -r requirements.txt
  if errorlevel 1 goto failed
)
".venv\Scripts\python.exe" app.py
if errorlevel 1 goto failed
exit /b 0
:failed
echo.
echo Setup or launch failed. Please send the error text for support.
pause
exit /b 1
