@echo off
setlocal
cd /d "%~dp0"

python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found! Please install Python and check "Add to PATH".
    pause
    exit /b 1
)

if not exist ".venv" (
    echo Creating virtual environment...
    python -m venv .venv
)

.venv\Scripts\python.exe -c "import a2s, curses" >nul 2>&1
if errorlevel 1 (
    echo Installing missing dependencies...
    .venv\Scripts\python.exe -m pip install python-a2s windows-curses
)

.venv\Scripts\python.exe see.py
if errorlevel 1 (
    pause
)