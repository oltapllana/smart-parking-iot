@echo off
echo.
echo ============================================================
echo      Smart Parking IoT System - Setup Script for Windows
echo ============================================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed or not in PATH
    echo Please install Python 3.8+ from https://www.python.org
    pause
    exit /b 1
)

echo [INFO] Python is installed
python --version

REM Check if Node.js is installed
node --version >nul 2>&1
if errorlevel 1 (
    echo [WARNING] Node.js is not installed. React dashboard will not work.
    echo Install from: https://nodejs.org/
) else (
    echo [INFO] Node.js is installed
    node --version
)

echo.
echo [INFO] Installing Python dependencies...
pip install -r requirements.txt
if errorlevel 1 (
    echo [ERROR] Failed to install Python dependencies
    pause
    exit /b 1
)

echo [SUCCESS] Python dependencies installed

echo.
if exist node_modules (
    echo [INFO] Node modules already installed
) else (
    echo [INFO] Installing Node.js dependencies...
    call npm install
    if errorlevel 1 (
        echo [WARNING] Failed to install Node dependencies
    ) else (
        echo [SUCCESS] Node dependencies installed
    )
)

echo.
echo [SUCCESS] Setup completed!
echo.
echo Next steps:
echo   1. Start API Server:    python parking_api_endpoints.py
echo   2. Start React Dashboard: npm start
echo   3. Open browser to http://localhost:3000
echo.
pause
