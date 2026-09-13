@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Please run setup_windows.bat first.
  pause
  exit /b 1
)
echo Open http://localhost:8501 if your browser does not open automatically.
echo Keep this window open. Press Ctrl+C here to stop the demo.
".venv\Scripts\python.exe" -m streamlit run app.py --server.address 127.0.0.1
if errorlevel 1 pause
