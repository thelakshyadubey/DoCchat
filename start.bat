@echo off
echo ========================================
echo Smart StudyMate - Quick Start Script
echo ========================================
echo.

REM Check if MongoDB is running
echo Checking MongoDB...
tasklist /FI "IMAGENAME eq mongod.exe" 2>NUL | find /I /N "mongod.exe">NUL
if "%ERRORLEVEL%"=="1" (
    echo WARNING: MongoDB is not running!
    echo Please start MongoDB before continuing.
    echo.
    pause
)

REM Start Backend
echo Starting Backend Server...
start cmd /k "cd backend && venv\Scripts\activate && python main.py"

REM Wait a bit for backend to start
timeout /t 5 /nobreak

REM Start Frontend
echo Starting Frontend Development Server...
start cmd /k "cd frontend && npm start"

echo.
echo ========================================
echo Both servers are starting...
echo Backend: http://localhost:8000
echo Frontend: http://localhost:3000
echo API Docs: http://localhost:8000/docs
echo ========================================
echo.
echo Press any key to exit this window...
pause
