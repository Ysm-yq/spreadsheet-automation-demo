@echo off
setlocal
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" goto install
where py >nul 2>nul
if errorlevel 1 goto usepython
py -3 -c "import sys; sys.exit(0 if sys.version_info >= (3,11) else 1)"
if errorlevel 1 goto missing
py -3 -m venv .venv
if errorlevel 1 goto failed
goto install
:usepython
python -c "import sys; sys.exit(0 if sys.version_info >= (3,11) else 1)"
if errorlevel 1 goto missing
python -m venv .venv
if errorlevel 1 goto failed
:install
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto failed
echo Setup complete. Double-click run_demo.bat to start.
pause
exit /b 0
:missing
echo Install Python 3.11 or later from python.org with Add Python to PATH enabled.
pause
exit /b 1
:failed
echo Setup did not finish. Check your Internet connection and the message above, then retry.
pause
exit /b 1
