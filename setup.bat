@echo off
REM Quick Start Script for AIOps MVP on Windows

echo ===============================================
echo AIOps MVP - Quick Start Setup
echo ===============================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed or not in PATH
    echo Please install Python 3.8+ from https://python.org
    pause
    exit /b 1
)

echo [1/3] Creating virtual environment...
if not exist venv (
    python -m venv venv
    echo Virtual environment created
) else (
    echo Virtual environment already exists
)

echo.
echo [2/3] Activating virtual environment and installing dependencies...
call venv\Scripts\activate.bat
pip install -r requirements.txt

echo.
echo [3/3] Setup complete!
echo.
echo ===============================================
echo How to run:
echo ===============================================
echo.
echo 1. Start the server:
echo    venv\Scripts\activate.bat
echo    python app.py
echo.
echo 2. In another terminal, run the test script:
echo    venv\Scripts\activate.bat
echo    python test_aiops.py
echo.
echo ===============================================
echo.

pause
