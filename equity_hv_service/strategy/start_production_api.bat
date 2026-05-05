@echo off
REM ============================================================================
REM Production Trading System Startup Script
REM ============================================================================
REM This script starts the complete trading system with:
REM   1. Trading API Server (Flask) on port 5000
REM   2. Production World-Class Engine v4.2
REM   3. SQLite Database for persistence
REM ============================================================================

echo.
echo ╔══════════════════════════════════════════════════════════════════════╗
echo ║         PRODUCTION TRADING SYSTEM - STARTUP                          ║
echo ╠══════════════════════════════════════════════════════════════════════╣
echo ║  API: http://localhost:5000                                          ║
echo ║  Database: strategy/database/trading_data.db                         ║
echo ║  Engine: World-Class v4.2 + Gemini AI                                ║
echo ╚══════════════════════════════════════════════════════════════════════╝
echo.

REM Activate virtual environment
cd /d "c:\Users\Dhanasimmaraja\Documents\TradeApp\DTrade"
call .venv\Scripts\activate.bat

REM Navigate to strategy folder
cd equity_hv_service\strategy

REM Start the API server
echo [%time%] Starting Production API Server...
python production_api.py --port 5000

pause
