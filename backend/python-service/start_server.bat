@echo off
REM Start the FastAPI server

cd /d "%~dp0"

echo.
echo ======================================
echo Starting JobSphere Server...
echo ======================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python is not installed or not in PATH
    pause
    exit /b 1
)

REM Install/upgrade dependencies if needed
echo Checking dependencies...
python -m pip install -q -r requirements.txt 2>nul

REM Start the server
echo.
echo Starting server on http://127.0.0.1:8000
echo Press Ctrl+C to stop the server
echo.
echo ======================================
echo.

python main.py

pause
