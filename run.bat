@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title Plainly

rem ---- find Python: the py launcher first, then python on PATH
set "PY="
py -3 --version >nul 2>&1 && set "PY=py -3"
if not defined PY python --version >nul 2>&1 && set "PY=python"
if not defined PY goto :nopython

rem ---- virtual environment in .venv
if not exist ".venv\Scripts\python.exe" (
  echo Creating a virtual environment...
  %PY% -m venv .venv
  if errorlevel 1 goto :fail
)
set "VPY=%~dp0.venv\Scripts\python.exe"

echo Installing packages. The first run takes a minute...
"%VPY%" -m pip install --disable-pip-version-check -q -r requirements.txt
if errorlevel 1 goto :fail
"%VPY%" -m pip install --disable-pip-version-check -q asyncpg >nul 2>&1
if errorlevel 1 echo Note: asyncpg did not install, so Tiger Data trends will use memory instead.

if not exist ".env" copy ".env.example" ".env" >nul

echo.
echo Plainly is starting at http://localhost:8000 and will open in your browser.
echo To add API keys: close this window, run "notepad .env", save, and run run.bat again.
echo For your iPhone: double-click phone.bat in this folder.
echo Press Ctrl+C to stop.
echo.
set "OPEN_BROWSER=1"
"%VPY%" main.py
if errorlevel 1 goto :fail
goto :eof

:nopython
echo Python 3.9 or newer is needed.
echo Install it from https://www.python.org/downloads/ and tick "Add python.exe to PATH" in the installer.
echo Then double-click run.bat again.
pause
exit /b 1

:fail
echo.
echo Something went wrong above. Fix the error shown and double-click run.bat again.
pause
exit /b 1
