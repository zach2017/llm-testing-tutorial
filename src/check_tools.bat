@echo off
REM check_tools.bat - verify everything needed to run the grocery-store LLM benchmark (Windows, CPU only).
REM Usage: double-click, or run  check_tools.bat  from a Command Prompt in the grocery-llm-eval folder.
setlocal EnableDelayedExpansion
cd /d "%~dp0"
if "%MODEL%"=="" set MODEL=deepseek-r1:1.5b
set HOST=http://localhost:11434
set MISSING=0
set PY=

echo === Grocery LLM benchmark: tool check (Windows) ===
for /f "tokens=2 delims==" %%A in ('wmic os get TotalVisibleMemorySize /value 2^>nul ^| find "="') do set /a RAM_GB=%%A/1024/1024
echo CPU cores: %NUMBER_OF_PROCESSORS%   RAM: %RAM_GB% GB
if %RAM_GB% LSS 4 (echo   [WARN] Less than 4 GB RAM; a 1.5B model needs ~2 GB free.) else (echo   [OK]   RAM is enough for a 1-3B model on CPU)

REM --- Python (3.9+). Try 'python', then 'py -3'.
python -c "import sys; sys.exit(0 if sys.version_info >= (3,9) else 1)" >nul 2>&1
if !errorlevel! EQU 0 (
  set PY=python
) else (
  py -3 -c "import sys; sys.exit(0 if sys.version_info >= (3,9) else 1)" >nul 2>&1
  if !errorlevel! EQU 0 set PY=py -3
)
if defined PY (
  for /f "delims=" %%V in ('!PY! --version 2^>^&1') do echo   [OK]   Python: %%V  ^(!PY!^)
) else (
  echo   [MISSING] Python 3.9+ not found. Install from https://www.python.org/downloads/ and tick "Add python.exe to PATH".
  set MISSING=1
)

REM --- optional matplotlib
if defined PY (
  !PY! -c "import matplotlib" >nul 2>&1
  if !errorlevel! EQU 0 (echo   [OK]   matplotlib ^(charts^) installed) else (echo   [WARN] matplotlib not installed: report will have no charts. Optional: !PY! -m pip install matplotlib)
)

REM --- Ollama CLI
where ollama >nul 2>&1
if !errorlevel! EQU 0 (
  for /f "delims=" %%V in ('ollama --version 2^>^&1') do echo   [OK]   Ollama CLI: %%V
) else (
  echo   [MISSING] Ollama not installed. Download https://ollama.com/download/windows and run the installer, then reopen this window.
  set MISSING=1
)

REM --- Ollama server
set SERVER=0
curl -s --max-time 3 %HOST%/api/version >nul 2>&1
if !errorlevel! EQU 0 (
  echo   [OK]   Ollama server is running at %HOST%
  set SERVER=1
) else (
  echo   [MISSING] Ollama server not reachable at %HOST%. Start the Ollama app ^(Start menu^) or run:  ollama serve
  set MISSING=1
)

REM --- model downloaded
if !SERVER! EQU 1 (
  ollama list 2>nul | findstr /b /c:"%MODEL%" >nul
  if !errorlevel! EQU 0 (echo   [OK]   Model '%MODEL%' is downloaded) else (
    echo   [MISSING] Model '%MODEL%' not downloaded. Run:  ollama pull %MODEL%   ^(~1.1 GB^)
    set MISSING=1
  )
)

REM --- project files
for %%F in (run_eval.py make_report.py ask.py data\grocery_store.txt data\questions.json data\prompts.json grocery_eval\scoring.py) do (
  if exist "%%F" (echo   [OK]   found %%F) else (echo   [MISSING] project file missing: %%F ^(run this from the grocery-llm-eval folder^) & set MISSING=1)
)

REM --- scorer self-test
if defined PY if exist run_eval.py (
  !PY! run_eval.py --self-test >nul 2>&1
  if !errorlevel! EQU 0 (echo   [OK]   scorer self-test passes) else (echo   [MISSING] scorer self-test FAILED: run  !PY! run_eval.py --self-test & set MISSING=1)
)

echo.
if !MISSING! EQU 0 (
  echo All good. Next:  !PY! setup_wizard.py     or     !PY! run_eval.py --models %MODEL% --variants baseline --limit 5 --num-predict 1500
) else (
  echo Fix the [MISSING] items above, then run this script again ^(or run: python setup_wizard.py for guided help^).
)
echo.
pause
exit /b !MISSING!
