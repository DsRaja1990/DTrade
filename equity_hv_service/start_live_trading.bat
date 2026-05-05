@echo off
REM =========================================================
REM 🏆 LEGENDARY PRODUCTION ENGINE v2.1 - LIVE TRADING
REM =========================================================
REM 
REM USAGE:
REM   start_live_trading.bat
REM   start_live_trading.bat --telegram-token YOUR_TOKEN --telegram-chat CHAT_ID
REM
REM ENVIRONMENT VARIABLES (optional):
REM   TELEGRAM_BOT_TOKEN - Your Telegram bot token
REM   TELEGRAM_CHAT_ID - Your Telegram chat ID
REM   WEBHOOK_URL - Custom webhook URL for alerts
REM =========================================================

echo.
echo =========================================================
echo 🏆 LEGENDARY PRODUCTION ENGINE v2.1 - LIVE MODE
echo =========================================================
echo    RSI Zones: 28, 38, 39
echo    Min Confirmations: 5+
echo    3-Tier Gemini AI Integration
echo    Multi-Position Management (up to 10)
echo =========================================================
echo.

REM Activate virtual environment
call "%~dp0..\.venv\Scripts\activate.bat"

REM Run the engine
cd /d "%~dp0"
python start_live_engine.py %*

pause
