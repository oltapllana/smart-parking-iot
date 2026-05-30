@echo off
echo.
echo ============================================================
echo      Smart Parking IoT - Start API Server
echo ============================================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed
    pause
    exit /b 1
)

echo [INFO] Starting Parking IoT API Server on port 5000...
echo.
echo You can access the API at: http://localhost:5000
echo API Endpoints:
echo   - GET  /api/health                    (Health check)
echo   - GET  /api/parking/status            (Current status)
echo   - GET  /api/parking/availability      (Availability prediction)
echo   - GET  /api/parking/demand            (Demand forecast)
echo   - GET  /api/parking/alerts            (Active alerts)
echo   - GET  /api/parking/zones             (Zone information)
echo   - GET  /api/parking/history           (Occupancy history)
echo.
echo Press Ctrl+C to stop the server
echo.

python parking_api_endpoints.py

pause
