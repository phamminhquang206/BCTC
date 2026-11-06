@echo off
setlocal
cd /d "%~dp0"
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0bootstrap.ps1" %*
if errorlevel 1 (
  echo.
  echo Khong khoi dong duoc. Vui long xem thong bao ben tren.
  pause
  exit /b 1
)
endlocal
