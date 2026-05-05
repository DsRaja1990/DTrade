@echo off
REM Install Gemini Trade Service - Run as Administrator
echo Installing Gemini Trade Service...
echo.

set VENV_PYTHON=C:\Users\Dhanasimmaraja\Documents\TradeApp\DTrade\gemini_trade_service\venv\Scripts\python.exe
set MAIN_SCRIPT=C:\Users\Dhanasimmaraja\Documents\TradeApp\DTrade\gemini_trade_service\main.py
set WORKING_DIR=C:\Users\Dhanasimmaraja\Documents\TradeApp\DTrade\gemini_trade_service

nssm install GeminiTradeService "%VENV_PYTHON%" "%MAIN_SCRIPT%"
nssm set GeminiTradeService DisplayName "Gemini Trade Service (Google AI)"
nssm set GeminiTradeService Description "Google AI (Gemini) powered trade signal analysis service"
nssm set GeminiTradeService AppDirectory "%WORKING_DIR%"
nssm set GeminiTradeService Start SERVICE_DELAYED_AUTO_START
nssm set GeminiTradeService AppEnvironmentExtra PORT=4080
nssm set GeminiTradeService AppStdout "%WORKING_DIR%\logs\gemini_service_stdout.log"
nssm set GeminiTradeService AppStderr "%WORKING_DIR%\logs\gemini_service_stderr.log"
nssm set GeminiTradeService AppStdoutCreationDisposition 4
nssm set GeminiTradeService AppStderrCreationDisposition 4
nssm set GeminiTradeService AppRotateFiles 1
nssm set GeminiTradeService AppRotateOnline 1
nssm set GeminiTradeService AppRotateSeconds 86400
nssm set GeminiTradeService AppRotateBytes 10485760
nssm set GeminiTradeService AppExit Default Restart
nssm set GeminiTradeService AppRestartDelay 5000
nssm set GeminiTradeService AppPriority NORMAL_PRIORITY_CLASS

echo.
echo Service installed! Starting...
sc start GeminiTradeService
timeout /t 3 /nobreak >nul

echo.
echo Checking status...
sc query GeminiTradeService

echo.
echo Testing API...
timeout /t 2 /nobreak >nul
curl -s http://localhost:4080/health

echo.
pause
