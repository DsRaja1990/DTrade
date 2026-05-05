@echo off
REM Run Equity HV Trading Service Locally (for development/testing)

set WORKING_DIR=C:\Users\Dhanasimmaraja\Documents\TradeApp\DTrade\equity_hv_service
set VENV_PYTHON=%WORKING_DIR%\venv\Scripts\python.exe
set SERVICE_PORT=5080

echo.
echo ============================================================================
echo Starting Equity HV Trading Service (Local Development)
echo ============================================================================
echo.
echo Working Directory: %WORKING_DIR%
echo Port: %SERVICE_PORT%
echo.

cd /d "%WORKING_DIR%"

REM Set PYTHONPATH for imports
set PYTHONPATH=%WORKING_DIR%

echo Starting uvicorn with auto-reload...
echo Press Ctrl+C to stop
echo.

"%VENV_PYTHON%" -m uvicorn equity_hv_service:app --host 127.0.0.1 --port %SERVICE_PORT% --reload

pause
