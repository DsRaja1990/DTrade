@echo off
echo.
echo ╔══════════════════════════════════════════════════════════════════╗
echo ║          WORLD-CLASS PRODUCTION ENGINE v4.0 LAUNCHER            ║
echo ║         90%+ Win Rate | 300%+ Monthly Returns Target            ║
echo ╚══════════════════════════════════════════════════════════════════╝
echo.

cd /d "%~dp0"

echo [%TIME%] Starting World-Class Production Engine...
echo.

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found! Please install Python 3.8+
    pause
    exit /b 1
)

REM Run the production engine
python world_class_production_engine.py

echo.
echo [%TIME%] Engine stopped.
pause
