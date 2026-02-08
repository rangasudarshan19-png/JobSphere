@echo off
title JobSphere - Complete Application Launcher
color 0B
cls

echo ========================================
echo       JobSphere Application
echo     Complete Job Tracker System
echo ========================================
echo.
echo [1/3] Starting Backend Server...
echo.

cd /d "%~dp0backend\python-service"

REM API keys are loaded from environment variables (set in .env or system env)
REM Example: set GEMINI_API_KEY=your_key_here
REM          set OPENAI_API_KEY=your_key_here
REM          set GROQ_API_KEY=your_key_here
REM          set XAI_API_KEY=your_key_here
REM          set HUGGINGFACE_API_KEY=your_key_here
set LOG_FILE=NUL

REM JSearch API Key (set in environment)
REM Example: set JSEARCH_API_KEY=your_key_here

REM Check virtual environment
if not exist ".venv312\Scripts\python.exe" (
    echo.
    echo ERROR: Virtual environment not found!
    echo Expected: backend\python-service\.venv312
    echo.
    pause
    exit /b 1
)

echo Virtual environment: OK
echo Starting FastAPI server on port 8000...
echo.

REM Start server in minimized window
start "JobSphere Backend (Port 8000)" /MIN cmd /k ".venv312\Scripts\python.exe -m uvicorn main:app --host 0.0.0.0 --port 8000"

echo [2/3] Waiting for server initialization...
timeout /t 10 /nobreak >nul

echo.
echo [3/3] Starting Frontend...
echo.

REM Check if Live Server extension is available in VS Code
where code >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo Opening in VS Code with Live Server...
    cd /d "%~dp0"
    start "" code .
    timeout /t 3 /nobreak >nul
) else (
    echo VS Code not found, opening frontend directly...
)

REM Open index.html in default browser
cd /d "%~dp0frontend"
start "" "index.html"

cls
echo ========================================
echo       JobSphere is RUNNING!
echo ========================================
echo.
echo Backend API: http://localhost:8000
echo API Docs: http://localhost:8000/docs
echo.
echo Frontend: Opened in your browser
echo - Main Page: index.html
echo - Login: login.html
echo - Dashboard: dashboard.html
echo.
echo ========================================
echo          FEATURES AVAILABLE
echo ========================================
echo.
echo [User Access]
echo - Regular users login with credentials
echo - Auto-redirect to dashboard.html
echo - Cannot access admin panel
echo.
echo [Admin Access]  
echo - Admin users login with credentials
echo - Auto-redirect to admin.html
echo - Full system management capabilities
echo.
echo [Test Credentials]
echo - User: rangasudarshan19@gmail.com / Sudarshan@1
echo - Admin: admin@jobtracker.com / admin123
echo.
echo ========================================
echo        IMPORTANT NOTES
echo ========================================
echo.
echo 1. DON'T CLOSE the "JobSphere Backend" window!
echo 2. If using file:// (not Live Server), some features may be limited
echo 3. For best experience: Use VS Code Live Server extension
echo.
echo To STOP the server:
echo - Close the "JobSphere Backend (Port 8000)" window
echo - Or press Ctrl+C in that window
echo.
echo ========================================
echo.
echo Press any key to open VS Code...
pause >nul

REM Open VS Code
cd /d "%~dp0"
code .

exit
