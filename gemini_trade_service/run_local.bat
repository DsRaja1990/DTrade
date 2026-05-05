@echo off
REM Run Gemini Trade Service Locally (for development/testing)

set WORKING_DIR=C:\Users\Dhanasimmaraja\Documents\TradeApp\DTrade\gemini_trade_service
set VENV_PYTHON=%WORKING_DIR%\venv\Scripts\python.exe
set SERVICE_PORT=4080

echo.
echo ============================================================================
echo Starting Gemini Trade Service (Local Development)
echo ============================================================================
echo.
echo Working Directory: %WORKING_DIR%
echo Port: %SERVICE_PORT%
echo.

cd /d "%WORKING_DIR%"

REM Set environment variables
set PORT=%SERVICE_PORT%

echo Starting Flask app...
echo Press Ctrl+C to stop
echo.

"%VENV_PYTHON%" main.py

pause
