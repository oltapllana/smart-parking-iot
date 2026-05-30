@echo off
echo.
echo ============================================================
echo      Smart Parking IoT - Start React Dashboard
echo ============================================================
echo.

REM Check if Node.js is installed
node --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Node.js is not installed
    echo Please install from: https://nodejs.org/
    pause
    exit /b 1
)

echo [INFO] Starting React Dashboard...
echo.
echo The dashboard will open at: http://localhost:3000
echo Make sure the API Server is running on port 5000
echo.
echo Press Ctrl+C to stop
echo.

call npm start

pause
