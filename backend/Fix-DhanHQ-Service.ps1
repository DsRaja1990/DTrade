# Fix DhanHQ Service - Run as Administrator
# This script removes the old service and installs with correct parameters

$ErrorActionPreference = "Continue"

Write-Host "============================================" -ForegroundColor Cyan
Write-Host "DhanHQ Service Reinstallation" -ForegroundColor Cyan  
Write-Host "============================================" -ForegroundColor Cyan

$ServiceName = "DhanHQ_Service"
$uvicornExe = "C:\Users\Dhanasimmaraja\Documents\TradeApp\DTrade\.venv\Scripts\uvicorn.exe"
$backendDir = "C:\Users\Dhanasimmaraja\Documents\TradeApp\DTrade\backend"
$logDir = "$backendDir\logs"

# Stop and remove existing service
Write-Host "`n[1/5] Stopping existing service..." -ForegroundColor Yellow
Stop-Service -Name $ServiceName -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 2

Write-Host "[2/5] Removing existing service..." -ForegroundColor Yellow
C:\nssm\nssm.exe stop $ServiceName confirm 2>$null
C:\nssm\nssm.exe remove $ServiceName confirm 2>$null
Start-Sleep -Seconds 2

# Verify old service is removed
$oldService = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue
if ($oldService) {
    Write-Host "Service still exists, using sc.exe to delete..." -ForegroundColor Yellow
    sc.exe delete $ServiceName
    Start-Sleep -Seconds 3
}

# Create logs directory
if (-not (Test-Path $logDir)) { 
    New-Item -ItemType Directory -Path $logDir -Force | Out-Null 
}

# Install new service
Write-Host "[3/5] Installing new service..." -ForegroundColor Green
C:\nssm\nssm.exe install $ServiceName $uvicornExe "dhan_backend:app --host 0.0.0.0 --port 8000"
C:\nssm\nssm.exe set $ServiceName AppDirectory $backendDir
C:\nssm\nssm.exe set $ServiceName DisplayName "DhanHQ Trading Backend"
C:\nssm\nssm.exe set $ServiceName Description "DTrade Backend - Dhan API integration for portfolio and trading"
C:\nssm\nssm.exe set $ServiceName AppStdout "$logDir\stdout.log"
C:\nssm\nssm.exe set $ServiceName AppStderr "$logDir\stderr.log"
C:\nssm\nssm.exe set $ServiceName AppRotateFiles 1
C:\nssm\nssm.exe set $ServiceName AppRotateBytes 5000000
C:\nssm\nssm.exe set $ServiceName Start SERVICE_AUTO_START

# Start service
Write-Host "[4/5] Starting service..." -ForegroundColor Green
Start-Sleep -Seconds 2
C:\nssm\nssm.exe start $ServiceName

# Check status
Write-Host "[5/5] Checking status..." -ForegroundColor Green
Start-Sleep -Seconds 3
$svc = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue
if ($svc) {
    Write-Host "`nService Status: $($svc.Status)" -ForegroundColor $(if($svc.Status -eq 'Running'){'Green'}else{'Red'})
} else {
    Write-Host "`nService not found!" -ForegroundColor Red
}

# Test health endpoint
Write-Host "`nTesting health endpoint..." -ForegroundColor Cyan
try {
    $response = Invoke-WebRequest -Uri "http://localhost:8000/health" -UseBasicParsing -TimeoutSec 5
    Write-Host "Backend is running! Status: $($response.StatusCode)" -ForegroundColor Green
} catch {
    Write-Host "Backend not responding yet. Check logs at: $logDir" -ForegroundColor Yellow
}

Write-Host "`n============================================" -ForegroundColor Cyan
Write-Host "Installation complete!" -ForegroundColor Green
Write-Host "============================================" -ForegroundColor Cyan

Read-Host "`nPress Enter to close"
