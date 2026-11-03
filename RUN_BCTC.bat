@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" goto setup
goto ready

:setup
echo [SETUP] Creating Python environment...
py -m venv .venv
if errorlevel 1 goto fail_env
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto fail_install

:ready
if defined VNSTOCK_API_KEY goto scan
echo Enter Vnstock API key. Input is visible.
set /p "VNSTOCK_API_KEY=API key: "
if not defined VNSTOCK_API_KEY goto fail_key

:scan
echo [1/2] Scanning configured tickers...
".venv\Scripts\python.exe" -m src.api_source
if errorlevel 1 echo API scan failed. Using saved data if available.
echo [2/2] Generating HTML...
".venv\Scripts\python.exe" -m src.html_report
if errorlevel 1 goto fail_report
start "" "%~dp0BCTC_Report.html"
echo Done. Report: %~dp0BCTC_Report.html
pause
exit /b 0

:fail_env
echo Cannot create Python environment.
goto failed
:fail_install
echo Cannot install Python dependencies.
goto failed
:fail_key
echo Missing API key.
goto failed
:fail_report
echo Cannot generate report.
:failed
pause
exit /b 1
