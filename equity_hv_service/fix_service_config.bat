@echo off
REM Fix Equity HV Service Configuration - Run as Administrator
echo.
echo ============================================================================
echo Fixing Elite Equity HV Service Configuration
echo ============================================================================
echo.

set SERVICE_NAME=EliteEquityHVService
set WORKING_DIR=C:\Users\Dhanasimmaraja\Documents\TradeApp\DTrade\equity_hv_service

REM Check admin rights
net session >nul 2>&1
if %errorLevel% NEQ 0 (
    echo ERROR: This script requires Administrator privileges!
    echo Please right-click and select "Run as administrator"
    pause
    exit /b 1
)

echo Current Configuration:
echo ----------------------
nssm get %SERVICE_NAME% Application
nssm get %SERVICE_NAME% AppParameters
echo.

echo Stopping service...
sc stop %SERVICE_NAME% >nul 2>&1
timeout /t 3 /nobreak >nul

echo.
echo Updating configuration to use uvicorn...
nssm set %SERVICE_NAME% AppParameters "-m uvicorn equity_hv_service:app --host 0.0.0.0 --port 5080"
nssm set %SERVICE_NAME% AppEnvironmentExtra PYTHONPATH=%WORKING_DIR%

echo.
echo New Configuration:
echo ------------------
nssm get %SERVICE_NAME% Application
nssm get %SERVICE_NAME% AppParameters
echo.

echo Starting service...
sc start %SERVICE_NAME%
timeout /t 5 /nobreak >nul

echo.
echo Checking status...
sc query %SERVICE_NAME%

echo.
echo Testing API...
timeout /t 2 /nobreak >nul
curl -s http://localhost:5080/health
echo.
echo.

pause
