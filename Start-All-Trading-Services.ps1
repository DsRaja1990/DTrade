# DTrade - Start All Production Trading Services
# Master script to start all three trading services simultaneously

$ErrorActionPreference = "Stop"

Write-Host @"
================================================================================
                     DTRADE - PRODUCTION TRADING SYSTEM
================================================================================
                          Starting All Services...

   Service                   Port    Instruments
   ----------------------   ------   --------------------------------
   AI Options Hedger        4003    NIFTY, BANKNIFTY (Index Options)
   AI Scalping Service      4002    NIFTY, BANKNIFTY, SENSEX, BANKEX
   Equity HV Trading        5080    F&O Stocks (RELIANCE, TCS, etc.)
   Gemini Trade Service     4080    AI Decision Engine (Required)

================================================================================
"@ -ForegroundColor Cyan

# Get the script directory
$RootDir = Split-Path -Parent $MyInvocation.MyCommand.Path

# Check if Gemini service is running
Write-Host "`n[1/4] Checking Gemini Trade Service (Port 4080)..." -ForegroundColor Yellow
try {
    $response = Invoke-RestMethod -Uri "http://localhost:4080/health" -TimeoutSec 5 -ErrorAction SilentlyContinue
    if ($response.status -eq "healthy") {
        Write-Host "   [OK] Gemini Trade Service is running" -ForegroundColor Green
    } else {
        Write-Host "   [WARN] Gemini service response unexpected" -ForegroundColor Yellow
    }
} catch {
    Write-Host "   [WARN] Gemini Trade Service not detected at http://localhost:4080" -ForegroundColor Yellow
    Write-Host "   AI validation will be disabled until Gemini service starts" -ForegroundColor Gray
}

# Start AI Options Hedger (Port 4003)
Write-Host "`n[2/4] Starting AI Options Hedger (Port 4003)..." -ForegroundColor Yellow
$HedgerPath = Join-Path $RootDir "ai_options_hedger"
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$HedgerPath'; python production_hedger_service.py" -WindowStyle Normal
Write-Host "   [OK] AI Options Hedger started in new window" -ForegroundColor Green
Start-Sleep -Seconds 2

# Start AI Scalping Service (Port 4002)
Write-Host "[3/4] Starting AI Scalping Service (Port 4002)..." -ForegroundColor Yellow
$ScalpingPath = Join-Path $RootDir "ai_scalping_service"
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$ScalpingPath'; python production_scalping_service.py" -WindowStyle Normal
Write-Host "   [OK] AI Scalping Service started in new window" -ForegroundColor Green
Start-Sleep -Seconds 2

# Start Equity HV Service (Port 5080)
Write-Host "[4/4] Starting Equity HV Trading Service (Port 5080)..." -ForegroundColor Yellow
$EquityPath = Join-Path $RootDir "equity_hv_service"
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$EquityPath'; python equity_hv_service.py" -WindowStyle Normal
Write-Host "   [OK] Equity HV Trading Service started in new window" -ForegroundColor Green

# Wait for services to initialize
Write-Host "`n[*] Waiting for services to initialize..." -ForegroundColor Gray
Start-Sleep -Seconds 5

# Health check
Write-Host "`n[*] Performing health checks..." -ForegroundColor Yellow
Write-Host ""

$services = @(
    @{Name="AI Options Hedger"; Port=4003; Url="http://localhost:4003/health"},
    @{Name="AI Scalping Service"; Port=4002; Url="http://localhost:4002/health"},
    @{Name="Equity HV Trading"; Port=5080; Url="http://localhost:5080/health"}
)

$allHealthy = $true
foreach ($svc in $services) {
    try {
        $response = Invoke-RestMethod -Uri $svc.Url -TimeoutSec 5 -ErrorAction SilentlyContinue
        Write-Host "   [OK] $($svc.Name) (Port $($svc.Port)) - HEALTHY" -ForegroundColor Green
    } catch {
        Write-Host "   [!] $($svc.Name) (Port $($svc.Port)) - NOT RESPONDING" -ForegroundColor Red
        $allHealthy = $false
    }
}

Write-Host ""
if ($allHealthy) {
    Write-Host @"
================================================================================
                    ALL SERVICES STARTED SUCCESSFULLY!
================================================================================

   Trading Endpoints (Paper Mode by Default):
   ------------------------------------------
   AI Options Hedger:    http://localhost:4003/api/trading/
   AI Scalping Service:  http://localhost:4002/api/trading/
   Equity HV Trading:    http://localhost:5080/api/trading/

   Common API Endpoints:
   ---------------------
   GET  /api/trading/status     - Get engine status
   POST /api/trading/mode       - Switch paper/live mode
   POST /api/trading/start      - Start trading engine
   POST /api/trading/stop       - Stop trading engine
   POST /api/trading/signal     - Process trading signal
   GET  /api/trading/positions  - Active positions
   GET  /api/trading/trades     - Trade history

   Trading Features:
   -----------------
   - Probe-Scale: 10% probe capital, 90% on Gemini confirmation
   - Stoploss: 50% wide on options premium
   - Trailing: 50-point after 50-point profit
   - Mode: Paper (default) / Live (switchable via API)

================================================================================
"@ -ForegroundColor Green
} else {
    Write-Host "   [!] Some services failed to start. Check individual windows for errors." -ForegroundColor Red
}

Write-Host "Press any key to exit this window (services will continue running)..." -ForegroundColor Gray
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
