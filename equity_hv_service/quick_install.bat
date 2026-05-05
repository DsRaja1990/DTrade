@echo off
REM Quick Install Equity HV Trading Service - Run as Administrator
echo.
echo ============================================================================
echo Installing Equity HV Trading Service (EliteStocksService)
echo ============================================================================
echo.

set SERVICE_NAME=EliteEquityHVService
set VENV_PYTHON=C:\Users\Dhanasimmaraja\Documents\TradeApp\DTrade\equity_hv_service\venv\Scripts\python.exe
set WORKING_DIR=C:\Users\Dhanasimmaraja\Documents\TradeApp\DTrade\equity_hv_service
set SERVICE_PORT=5080

REM Check for admin rights
net session >nul 2>&1
if %errorLevel% NEQ 0 (
    echo ERROR: This script requires Administrator privileges!
    echo Please right-click and select "Run as administrator"
    pause
    exit /b 1
)

REM Check if venv exists
if not exist "%VENV_PYTHON%" (
    echo ERROR: Virtual environment not found at %VENV_PYTHON%
    echo Please create venv first
    pause
    exit /b 1
)

REM Remove existing service if present
echo Checking for existing service...
sc query %SERVICE_NAME% >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo Stopping and removing existing service...
    sc stop %SERVICE_NAME% >nul 2>&1
    timeout /t 3 /nobreak >nul
    sc delete %SERVICE_NAME% >nul 2>&1
    timeout /t 2 /nobreak >nul
)

echo.
echo Installing service...
nssm install %SERVICE_NAME% "%VENV_PYTHON%" -m uvicorn equity_hv_service:app --host 0.0.0.0 --port %SERVICE_PORT%

nssm set %SERVICE_NAME% DisplayName "Elite Equity HV Trading Service (Gemini AI)"
nssm set %SERVICE_NAME% Description "High-Velocity F&O Trading with Gemini AI Integration"
nssm set %SERVICE_NAME% AppDirectory "%WORKING_DIR%"
nssm set %SERVICE_NAME% Start SERVICE_DELAYED_AUTO_START
nssm set %SERVICE_NAME% AppEnvironmentExtra PYTHONPATH=%WORKING_DIR%
nssm set %SERVICE_NAME% AppStdout "%WORKING_DIR%\logs\elite_service_stdout.log"
nssm set %SERVICE_NAME% AppStderr "%WORKING_DIR%\logs\elite_service_stderr.log"
nssm set %SERVICE_NAME% AppStdoutCreationDisposition 4
nssm set %SERVICE_NAME% AppStderrCreationDisposition 4
nssm set %SERVICE_NAME% AppRotateFiles 1
nssm set %SERVICE_NAME% AppRotateOnline 1
nssm set %SERVICE_NAME% AppRotateSeconds 86400
nssm set %SERVICE_NAME% AppRotateBytes 10485760
nssm set %SERVICE_NAME% AppExit Default Restart
nssm set %SERVICE_NAME% AppRestartDelay 5000
nssm set %SERVICE_NAME% AppPriority NORMAL_PRIORITY_CLASS

echo.
echo ============================================================================
echo Service installed! Starting...
echo ============================================================================
sc start %SERVICE_NAME%
timeout /t 5 /nobreak >nul

echo.
echo Checking status...
sc query %SERVICE_NAME%

echo.
echo Testing API endpoints...
timeout /t 2 /nobreak >nul

echo.
echo [Health Check]
curl -s http://localhost:%SERVICE_PORT%/health

echo.
echo.
echo [Service Status]
curl -s http://localhost:%SERVICE_PORT%/status

echo.
echo.
echo ============================================================================
echo Installation Complete!
echo ============================================================================
echo.
echo Service Name: %SERVICE_NAME%
echo Port: %SERVICE_PORT%
echo.
echo Endpoints:
echo   - Health: http://localhost:%SERVICE_PORT%/health
echo   - Status: http://localhost:%SERVICE_PORT%/status
echo   - Config: http://localhost:%SERVICE_PORT%/config
echo   - Analytics: http://localhost:%SERVICE_PORT%/api/analytics/*
echo   - Auto-Trader: http://localhost:%SERVICE_PORT%/api/auto-trader/*
echo   - Gemini Engine: http://localhost:%SERVICE_PORT%/api/gemini-engine/*
echo.
pause
