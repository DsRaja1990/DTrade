@echo off
REM ============================================================================
REM Equity HV Trading Service Manager
REM Complete service management for Equity HV Service (Gemini AI Integrated)
REM ============================================================================

set SERVICE_NAME=EliteEquityHVService
set SERVICE_DISPLAY_NAME=Elite Equity HV Trading Service (Gemini AI)
set SERVICE_DESCRIPTION=High-Velocity F&O Trading with Gemini AI Integration - SQLite Database
set PYTHON_EXE=%~dp0venv\Scripts\python.exe
set SCRIPT_PATH=%~dp0equity_hv_service.py
set WORKING_DIR=%~dp0
set SERVICE_PORT=5080

:MENU
cls
echo.
echo ============================================================================
echo           EQUITY HV TRADING SERVICE - MANAGER
echo ============================================================================
echo.
echo Service: %SERVICE_NAME%
echo Port: %SERVICE_PORT%
echo Python: venv\Scripts\python.exe
echo Entry: equity_hv_service.py
echo.
echo [1] Install/Reinstall Service (Admin Required)
echo [2] Uninstall Service (Admin Required)
echo.
echo [3] Start Service
echo [4] Stop Service
echo [5] Restart Service
echo [6] Check Status
echo.
echo [7] View Standard Output Log
echo [8] View Error Log
echo [9] Clear Logs
echo [0] Open Logs Folder
echo.
echo [T] Test API Health
echo [L] Run Service Locally (for testing)
echo [A] Test All Endpoints
echo.
echo [X] Exit
echo.
echo ============================================================================
echo.

choice /C 1234567890TLAXZ /N /M "Select option: "

if errorlevel 15 goto EXIT
if errorlevel 14 goto EXIT
if errorlevel 13 goto TEST_ALL
if errorlevel 12 goto RUN_LOCAL
if errorlevel 11 goto TEST_API
if errorlevel 10 goto OPEN_LOGS
if errorlevel 9 goto CLEAR_LOGS
if errorlevel 8 goto VIEW_STDERR
if errorlevel 7 goto VIEW_STDOUT
if errorlevel 6 goto STATUS
if errorlevel 5 goto RESTART
if errorlevel 4 goto STOP
if errorlevel 3 goto START
if errorlevel 2 goto UNINSTALL
if errorlevel 1 goto INSTALL

:INSTALL
cls
echo.
echo ============================================================================
echo Installing Equity HV Trading Service
echo ============================================================================
echo.

REM Check if running as administrator
net session >nul 2>&1
if %errorLevel% NEQ 0 (
    echo ERROR: This operation requires Administrator privileges
    echo Please run this script as Administrator
    echo.
    pause
    goto MENU
)

REM Check if venv exists
if not exist "%PYTHON_EXE%" (
    echo ERROR: Virtual environment not found!
    echo Please create venv first: python -m venv venv
    echo Then install dependencies: venv\Scripts\pip install -r requirements.txt
    echo.
    pause
    goto MENU
)

REM Check if NSSM is available
where nssm >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: NSSM not found in PATH
    echo Please ensure NSSM is installed and added to PATH
    echo Download from: https://nssm.cc/download
    echo.
    pause
    goto MENU
)

echo Checking for existing service...
sc query %SERVICE_NAME% >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo Service already exists. Stopping and removing...
    sc stop %SERVICE_NAME% >nul 2>&1
    timeout /t 3 /nobreak >nul
    sc delete %SERVICE_NAME% >nul 2>&1
    timeout /t 2 /nobreak >nul
)

echo.
echo Installing service with uvicorn...

REM Use uvicorn to run the FastAPI service
nssm install %SERVICE_NAME% "%PYTHON_EXE%" -m uvicorn equity_hv_service:app --host 0.0.0.0 --port %SERVICE_PORT%

if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Failed to install service
    pause
    goto MENU
)

echo Configuring service parameters...
nssm set %SERVICE_NAME% DisplayName "%SERVICE_DISPLAY_NAME%"
nssm set %SERVICE_NAME% Description "%SERVICE_DESCRIPTION%"
nssm set %SERVICE_NAME% AppDirectory "%WORKING_DIR%"
nssm set %SERVICE_NAME% Start SERVICE_DELAYED_AUTO_START
nssm set %SERVICE_NAME% AppEnvironmentExtra PYTHONPATH=%WORKING_DIR%
nssm set %SERVICE_NAME% AppStdout "%WORKING_DIR%logs\elite_service_stdout.log"
nssm set %SERVICE_NAME% AppStderr "%WORKING_DIR%logs\elite_service_stderr.log"
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
echo Service installed successfully!
echo ============================================================================
echo.
echo Starting service...
sc start %SERVICE_NAME%

if %ERRORLEVEL% EQU 0 (
    echo Service started successfully!
    timeout /t 5 /nobreak >nul
    echo.
    sc query %SERVICE_NAME%
    echo.
    echo Testing API health...
    curl -s http://localhost:%SERVICE_PORT%/health
) else (
    echo Failed to start service. Check logs for details.
)

echo.
pause
goto MENU

:UNINSTALL
cls
echo.
echo ============================================================================
echo Uninstalling Equity HV Trading Service
echo ============================================================================
echo.

REM Check if running as administrator
net session >nul 2>&1
if %errorLevel% NEQ 0 (
    echo ERROR: This operation requires Administrator privileges
    echo Please run this script as Administrator
    echo.
    pause
    goto MENU
)

echo Stopping service...
sc stop %SERVICE_NAME% >nul 2>&1
timeout /t 3 /nobreak >nul

echo Removing service...
sc delete %SERVICE_NAME%

if %ERRORLEVEL% EQU 0 (
    echo Service uninstalled successfully!
) else (
    echo Failed to uninstall service or service not found.
)

echo.
pause
goto MENU

:START
echo.
echo Starting Equity HV Trading Service...
sc start %SERVICE_NAME%
if %ERRORLEVEL% EQU 0 (
    echo Service started successfully!
    timeout /t 5 /nobreak >nul
    sc query %SERVICE_NAME%
) else (
    echo Failed to start service!
    echo Try running as Administrator if you get access denied.
)
pause
goto MENU

:STOP
echo.
echo Stopping Equity HV Trading Service...
sc stop %SERVICE_NAME%
if %ERRORLEVEL% EQU 0 (
    echo Service stopped successfully!
) else (
    echo Failed to stop service!
    echo Try running as Administrator if you get access denied.
)
pause
goto MENU

:RESTART
echo.
echo Restarting Equity HV Trading Service...
sc stop %SERVICE_NAME%
timeout /t 3 /nobreak >nul
sc start %SERVICE_NAME%
if %ERRORLEVEL% EQU 0 (
    echo Service restarted successfully!
    timeout /t 5 /nobreak >nul
    sc query %SERVICE_NAME%
) else (
    echo Failed to restart service!
)
pause
goto MENU

:STATUS
cls
echo.
echo ============================================================================
echo Service Status
echo ============================================================================
echo.
sc query %SERVICE_NAME%
echo.
echo ============================================================================
echo.
pause
goto MENU

:VIEW_STDOUT
cls
echo.
echo ============================================================================
echo Standard Output Log (last 50 lines)
echo ============================================================================
echo.
if exist "%WORKING_DIR%logs\elite_service_stdout.log" (
    powershell -Command "Get-Content '%WORKING_DIR%logs\elite_service_stdout.log' -Tail 50"
) else (
    echo Log file not found.
)
echo.
pause
goto MENU

:VIEW_STDERR
cls
echo.
echo ============================================================================
echo Error Log (last 50 lines)
echo ============================================================================
echo.
if exist "%WORKING_DIR%logs\elite_service_stderr.log" (
    powershell -Command "Get-Content '%WORKING_DIR%logs\elite_service_stderr.log' -Tail 50"
) else (
    echo Log file not found.
)
echo.
pause
goto MENU

:CLEAR_LOGS
echo.
echo Clearing log files...
del /Q "%WORKING_DIR%logs\elite_service_stdout.log" 2>nul
del /Q "%WORKING_DIR%logs\elite_service_stderr.log" 2>nul
del /Q "%WORKING_DIR%logs\equity_hv_service.log" 2>nul
echo Logs cleared.
pause
goto MENU

:OPEN_LOGS
start explorer "%WORKING_DIR%logs"
goto MENU

:TEST_API
cls
echo.
echo ============================================================================
echo Testing API Health
echo ============================================================================
echo.
echo [Health Check] http://localhost:%SERVICE_PORT%/health
echo.
curl -s http://localhost:%SERVICE_PORT%/health
echo.
echo.
echo [Status] http://localhost:%SERVICE_PORT%/status
echo.
curl -s http://localhost:%SERVICE_PORT%/status
echo.
echo.
pause
goto MENU

:TEST_ALL
cls
echo.
echo ============================================================================
echo Testing All Endpoints
echo ============================================================================
echo.
echo [1] Health Check...
curl -s http://localhost:%SERVICE_PORT%/health
echo.
echo.
echo [2] Service Status...
curl -s http://localhost:%SERVICE_PORT%/status
echo.
echo.
echo [3] Configuration...
curl -s http://localhost:%SERVICE_PORT%/config
echo.
echo.
echo [4] Elite Stocks...
curl -s http://localhost:%SERVICE_PORT%/stocks
echo.
echo.
echo [5] Analytics Health...
curl -s http://localhost:%SERVICE_PORT%/api/analytics/health
echo.
echo.
echo [6] Auto-Trader Health...
curl -s http://localhost:%SERVICE_PORT%/api/auto-trader/health
echo.
echo.
echo [7] Gemini Engine Status...
curl -s http://localhost:%SERVICE_PORT%/api/gemini-engine/status
echo.
echo.
pause
goto MENU

:RUN_LOCAL
cls
echo.
echo ============================================================================
echo Running Service Locally (for testing)
echo ============================================================================
echo.
echo Working Directory: %WORKING_DIR%
echo Port: %SERVICE_PORT%
echo.
echo Press Ctrl+C to stop
echo.
cd /d "%WORKING_DIR%"
"%PYTHON_EXE%" -m uvicorn equity_hv_service:app --host 127.0.0.1 --port %SERVICE_PORT% --reload
pause
goto MENU

:EXIT
exit /b 0
