@echo off
setlocal
cd /d "%~dp0"
chcp 65001 >nul
if not exist ".venv\Scripts\python.exe" (
  echo [SETUP] Creating Python virtual environment...
  py -3.12 --version >nul 2>&1
  if not errorlevel 1 (
    py -3.12 -m venv .venv
  ) else (
    py -3.13 --version >nul 2>&1
    if not errorlevel 1 (
      py -3.13 -m venv .venv
    ) else (
      echo Python 3.12 or 3.13 is required for this project.
      echo Download Python 3.12 from https://www.python.org/downloads/
      pause
      exit /b 1
    )
  )
  if errorlevel 1 (
    echo Could not create environment. Install Python 3.12 and retry.
    pause
    exit /b 1
  )
  ".venv\Scripts\python.exe" -m pip install -r requirements.txt
  if errorlevel 1 (echo Installation failed.& pause& exit /b 1)
)
if not defined VNSTOCK_API_KEY (
  echo Enter your Vnstock API key (input will be visible):
  set /p VNSTOCK_API_KEY=API key: 
)
if not defined VNSTOCK_API_KEY (echo API key missing.& pause& exit /b 1)
echo [1/2] Scanning configured tickers...
".venv\Scripts\python.exe" -m src.api_source
if errorlevel 1 (
  echo API scan failed. Report will use last saved data if available.
)
echo [2/2] Generating HTML...
".venv\Scripts\python.exe" -m src.html_report
if errorlevel 1 (echo Report failed.& pause& exit /b 1)
start "" "%~dp0BCTC_Report.html"
echo Done. Report: BCTC_Report.html
pause
