@echo off
title Quick Server Check
color 0A

echo ========================================
echo   JobSphere Backend Health Check
echo ========================================
echo.

echo Checking if server is running...
echo.

curl -s http://127.0.0.1:8000/docs >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo [OK] Server is RUNNING on port 8000
    echo.
    echo Testing login endpoint...
    echo.
    
    REM Test regular user login
    echo Testing regular user login...
    curl -s -X POST http://127.0.0.1:8000/api/auth/login ^
        -H "Content-Type: application/json" ^
        -d "{\"email\":\"rangasudarshan19@gmail.com\",\"password\":\"Sudarshan@1\"}" | findstr "access_token" >nul 2>&1
    
    if %ERRORLEVEL% EQU 0 (
        echo [OK] Regular User Login: Working!
    ) else (
        echo [WARN] Regular User Login: Failed
    )
    
    echo.
    echo Testing admin login...
    curl -s -X POST http://127.0.0.1:8000/api/auth/login ^
        -H "Content-Type: application/json" ^
        -d "{\"email\":\"admin@jobtracker.com\",\"password\":\"admin123\"}" | findstr "access_token" >nul 2>&1
    
    if %ERRORLEVEL% EQU 0 (
        echo [OK] Admin Login: Working!
    ) else (
        echo [WARN] Admin Login: Failed
    )
    
    echo.
    echo ========================================
    echo   ALL SYSTEMS OPERATIONAL
    echo ========================================
    echo.
    echo Access Points:
    echo - Frontend: file:///C:/Users/Chait/OneDrive/Desktop/Project/frontend/index.html
    echo - API Docs: http://localhost:8000/docs
    echo - API Redoc: http://localhost:8000/redoc
    echo.
    echo Test Credentials:
    echo - User: rangasudarshan19@gmail.com / Sudarshan@1
    echo - Admin: admin@jobtracker.com / admin123
    echo.
    echo Important:
    echo - Admin users automatically redirect to admin.html on login
    echo - Regular users can ONLY see their own dashboard (no admin panel button)
    echo.
        echo You can now login at:
        echo http://127.0.0.1:8000/frontend/login.html
        echo.
    ) else (
        echo [ERROR] Login endpoint not responding
    )
) else (
    echo [ERROR] Server is NOT running!
    echo.
    echo Please run: LAUNCH_JOBSPHERE.bat
)

echo.
pause
