# Fix AI Options Hedger Windows Service
# Run this script as Administrator

Write-Host "=== AI Options Hedger Service Fix ===" -ForegroundColor Cyan

# Configuration
$serviceName = "AIOptionsHedger"
$pythonPath = "C:\Users\Dhanasimmaraja\Documents\TradeApp\DTrade\.venv\Scripts\python.exe"
$appDir = "C:\Users\Dhanasimmaraja\Documents\TradeApp\DTrade\ai_options_hedger"
$mainFile = "main.py"
$logDir = "$appDir\logs"

# Check if running as Administrator
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "ERROR: Please run this script as Administrator!" -ForegroundColor Red
    Write-Host "Right-click PowerShell and select 'Run as Administrator'" -ForegroundColor Yellow
    Read-Host "Press Enter to exit"
    exit 1
}

# Check if NSSM is available
$nssm = Get-Command nssm -ErrorAction SilentlyContinue
if (-not $nssm) {
    Write-Host "ERROR: NSSM not found in PATH!" -ForegroundColor Red
    Write-Host "Download from: https://nssm.cc/download" -ForegroundColor Yellow
    Read-Host "Press Enter to exit"
    exit 1
}

# Check Python path
if (-not (Test-Path $pythonPath)) {
    Write-Host "ERROR: Python not found at: $pythonPath" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

# Check main.py
if (-not (Test-Path "$appDir\$mainFile")) {
    Write-Host "ERROR: main.py not found at: $appDir\$mainFile" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

# Create logs directory
if (-not (Test-Path $logDir)) {
    New-Item -ItemType Directory -Path $logDir -Force | Out-Null
    Write-Host "Created logs directory: $logDir" -ForegroundColor Green
}

Write-Host ""
Write-Host "Configuration:" -ForegroundColor Yellow
Write-Host "  Python: $pythonPath"
Write-Host "  App Dir: $appDir"
Write-Host "  Main File: $mainFile"
Write-Host ""

# Stop any process on port 8000
Write-Host "Checking port 8000..." -ForegroundColor Yellow
$portProcess = Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue
if ($portProcess) {
    Write-Host "Killing process on port 8000..." -ForegroundColor Yellow
    Stop-Process -Id $portProcess.OwningProcess -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 2
}

# Stop service if running
Write-Host "Stopping service..." -ForegroundColor Yellow
& net stop $serviceName 2>&1 | Out-Null

# Check if service exists and remove it
Write-Host "Checking existing service..." -ForegroundColor Yellow
$svcStatus = & nssm status $serviceName 2>&1
if ($svcStatus -notmatch "Can't open service") {
    Write-Host "Removing existing service..." -ForegroundColor Yellow
    & nssm remove $serviceName confirm 2>&1 | Out-Null
    Start-Sleep -Seconds 3
}

# Install service
Write-Host "Installing service..." -ForegroundColor Yellow
& nssm install $serviceName $pythonPath $mainFile 2>&1 | Out-Null

# Configure service
Write-Host "Configuring service..." -ForegroundColor Yellow
& nssm set $serviceName DisplayName "AI Options Hedger Trading Service" 2>&1 | Out-Null
& nssm set $serviceName Description "Intelligent Options Hedging Engine - Production Ready" 2>&1 | Out-Null
& nssm set $serviceName AppDirectory $appDir 2>&1 | Out-Null
& nssm set $serviceName AppStdout "$logDir\service_stdout.log" 2>&1 | Out-Null
& nssm set $serviceName AppStderr "$logDir\service_stderr.log" 2>&1 | Out-Null
& nssm set $serviceName AppStdoutCreationDisposition 4 2>&1 | Out-Null
& nssm set $serviceName AppStderrCreationDisposition 4 2>&1 | Out-Null
& nssm set $serviceName AppRotateFiles 1 2>&1 | Out-Null
& nssm set $serviceName AppRotateOnline 1 2>&1 | Out-Null
& nssm set $serviceName AppRotateBytes 10485760 2>&1 | Out-Null
& nssm set $serviceName AppEnvironmentExtra "PYTHONPATH=$appDir" 2>&1 | Out-Null
& nssm set $serviceName AppExit Default Restart 2>&1 | Out-Null
& nssm set $serviceName AppRestartDelay 5000 2>&1 | Out-Null
& nssm set $serviceName Start SERVICE_AUTO_START 2>&1 | Out-Null

Write-Host ""
Write-Host "Service installed successfully!" -ForegroundColor Green
Write-Host ""

# Start service
Write-Host "Starting service..." -ForegroundColor Yellow
$startResult = & net start $serviceName 2>&1

if ($startResult -match "started successfully") {
    Write-Host ""
    Write-Host "=== Service Started Successfully! ===" -ForegroundColor Green
    Write-Host ""
    Write-Host "Access the API at: http://localhost:8000" -ForegroundColor Cyan
    Write-Host "API Documentation: http://localhost:8000/docs" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Check logs at: $logDir" -ForegroundColor Yellow
    
    # Test API
    Start-Sleep -Seconds 5
    Write-Host ""
    Write-Host "Testing API..." -ForegroundColor Yellow
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:8000/health" -UseBasicParsing -TimeoutSec 10
        Write-Host "API is responding: $($response.StatusCode)" -ForegroundColor Green
    } catch {
        Write-Host "API not responding yet (may still be starting)" -ForegroundColor Yellow
    }
} else {
    Write-Host ""
    Write-Host "Service may have failed to start. Checking status..." -ForegroundColor Yellow
    & nssm status $serviceName
    Write-Host ""
    Write-Host "Check logs at: $logDir" -ForegroundColor Yellow
}

Write-Host ""
Read-Host "Press Enter to exit"
