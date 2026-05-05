@echo off
REM ============================================================================
REM Gemini Trade Service Manager
REM Complete service management for Gemini Trade Service (Google AI)
REM ============================================================================

set SERVICE_NAME=GeminiTradeService
set SERVICE_DISPLAY_NAME=Gemini Trade Service (Google AI)
set SERVICE_DESCRIPTION=Google AI (Gemini) powered trade signal analysis service - 3-tier validation system
set PYTHON_EXE=%~dp0venv\Scripts\python.exe
set SCRIPT_PATH=%~dp0main.py
set WORKING_DIR=%~dp0
set SERVICE_PORT=4080

:MENU
cls
echo.
echo ============================================================================
echo           GEMINI TRADE SERVICE - MANAGER
echo ============================================================================
echo.
echo Service: %SERVICE_NAME%
echo Port: %SERVICE_PORT%
echo Python: venv\Scripts\python.exe
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
echo.
echo [X] Exit
echo.
echo ============================================================================
echo.

choice /C 1234567890TLXZ /N /M "Select option: "

if errorlevel 14 goto EXIT
if errorlevel 13 goto EXIT
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
echo Installing Gemini Trade Service
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
echo Installing service...
nssm install %SERVICE_NAME% "%PYTHON_EXE%" "%SCRIPT_PATH%"

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
nssm set %SERVICE_NAME% AppEnvironmentExtra PORT=%SERVICE_PORT%
nssm set %SERVICE_NAME% AppStdout "%WORKING_DIR%logs\gemini_service_stdout.log"
nssm set %SERVICE_NAME% AppStderr "%WORKING_DIR%logs\gemini_service_stderr.log"
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
    timeout /t 3 /nobreak >nul
    echo.
    sc query %SERVICE_NAME%
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
echo Uninstalling Gemini Trade Service
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
echo Starting Gemini Trade Service...
sc start %SERVICE_NAME%
if %ERRORLEVEL% EQU 0 (
    echo Service started successfully!
    timeout /t 3 /nobreak >nul
    sc query %SERVICE_NAME%
) else (
    echo Failed to start service!
    echo Try running as Administrator if you get access denied.
)
pause
goto MENU

:STOP
echo.
echo Stopping Gemini Trade Service...
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
echo Restarting Gemini Trade Service...
sc stop %SERVICE_NAME%
timeout /t 2 /nobreak >nul
sc start %SERVICE_NAME%
if %ERRORLEVEL% EQU 0 (
    echo Service restarted successfully!
    timeout /t 3 /nobreak >nul
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
echo Standard Output Log
echo ============================================================================
echo.
if exist "%WORKING_DIR%logs\gemini_service_stdout.log" (
    type "%WORKING_DIR%logs\gemini_service_stdout.log"
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
echo Error Log
echo ============================================================================
echo.
if exist "%WORKING_DIR%logs\gemini_service_stderr.log" (
    type "%WORKING_DIR%logs\gemini_service_stderr.log"
) else (
    echo Log file not found.
)
echo.
pause
goto MENU

:CLEAR_LOGS
echo.
echo Clearing log files...
del /Q "%WORKING_DIR%logs\gemini_service_stdout.log" 2>nul
del /Q "%WORKING_DIR%logs\gemini_service_stderr.log" 2>nul
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
echo Endpoint: http://localhost:%SERVICE_PORT%/health
echo.
curl -s http://localhost:%SERVICE_PORT%/health
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
echo Press Ctrl+C to stop
echo.
"%PYTHON_EXE%" "%SCRIPT_PATH%"
pause
goto MENU

:EXIT
exit /b 0
