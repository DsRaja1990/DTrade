@echo off
echo =====================================================
echo Gemini Trade Service - Windows Service Installer
echo =====================================================
echo.

REM Check for admin rights
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo ERROR: This script requires Administrator privileges!
    echo Please right-click and select "Run as administrator"
    pause
    exit /b 1
)

echo Running as Administrator...
echo.

REM Set paths
set PYTHON_EXE=C:\Users\Dhanasimmaraja\Documents\TradeApp\DTrade\gemini_trade_service\venv\Scripts\python.exe
set APP_DIR=C:\Users\Dhanasimmaraja\Documents\TradeApp\DTrade\gemini_trade_service
set LOG_DIR=%APP_DIR%\logs

REM Stop and remove existing service
echo Stopping existing service...
nssm stop GeminiTradeService >nul 2>&1
timeout /t 2 /nobreak >nul

echo Removing existing service...
nssm remove GeminiTradeService confirm >nul 2>&1
timeout /t 2 /nobreak >nul

REM Install new service
echo Installing Gemini Trade Service...
nssm install GeminiTradeService "%PYTHON_EXE%" main.py
nssm set GeminiTradeService AppDirectory "%APP_DIR%"
nssm set GeminiTradeService DisplayName "Gemini Trade Service (Google AI)"
nssm set GeminiTradeService Description "Google AI (Gemini) powered trade signal analysis service - 3-tier validation system"
nssm set GeminiTradeService Start SERVICE_AUTO_START
nssm set GeminiTradeService AppStdout "%LOG_DIR%\gemini_service_stdout.log"
nssm set GeminiTradeService AppStderr "%LOG_DIR%\gemini_service_stderr.log"
nssm set GeminiTradeService AppStdoutCreationDisposition 4
nssm set GeminiTradeService AppStderrCreationDisposition 4

echo.
echo Starting service...
nssm start GeminiTradeService
timeout /t 3 /nobreak >nul

echo.
echo Checking service status...
nssm status GeminiTradeService

echo.
echo =====================================================
echo Service installation complete!
echo.
echo To check if running, visit: http://localhost:4080/health
echo =====================================================
pause
