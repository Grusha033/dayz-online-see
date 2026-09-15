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
    echo Setting up environment, please wait...
    python -m venv .venv
    call .venv\Scripts\activate.bat
    python -m pip install --upgrade pip >nul 2>&1
    python -m pip install python-a2s windows-curses >nul 2>&1
) else (
    call .venv\Scripts\activate.bat
)

python see.py