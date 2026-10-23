@echo off
REM Launches the setup wizard on Windows. Double-click or run from Command Prompt.
cd /d "%~dp0"
python -c "import sys; sys.exit(0 if sys.version_info >= (3,9) else 1)" >nul 2>&1
if %errorlevel% EQU 0 (
  python setup_wizard.py %*
) else (
  py -3 setup_wizard.py %* 2>nul || (
    echo Python 3.9+ was not found. Install it from https://www.python.org/downloads/ and tick "Add python.exe to PATH".
  )
)
pause
