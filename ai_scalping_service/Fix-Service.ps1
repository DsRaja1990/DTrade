# Fix-AIScalpingService.ps1 - Run this script as Administrator
# This fixes the NSSM configuration pointing to wrong script

$ErrorActionPreference = "Stop"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  AI Scalping Service - NSSM Fix Script" -ForegroundColor White
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check admin
$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "[!] This script requires Administrator privileges!" -ForegroundColor Red
    Write-Host "    Right-click and 'Run as Administrator'" -ForegroundColor Yellow
    Read-Host "Press Enter to exit"
    exit 1
}

$serviceName = "AIScalpingService"
$serviceDir = "c:\Users\Dhanasimmaraja\Documents\TradeApp\DTrade\ai_scalping_service"
$correctScript = Join-Path $serviceDir "production_scalping_service.py"
$pythonPath = Join-Path $serviceDir ".venv\Scripts\python.exe"

Write-Host "[i] Checking paths..." -ForegroundColor Cyan
if (-not (Test-Path $pythonPath)) {
    Write-Host "[X] Python not found at: $pythonPath" -ForegroundColor Red
    exit 1
}
if (-not (Test-Path $correctScript)) {
    Write-Host "[X] Script not found at: $correctScript" -ForegroundColor Red
    exit 1
}
Write-Host "[OK] Paths verified" -ForegroundColor Green

# Find NSSM
$nssm = Get-Command nssm -ErrorAction SilentlyContinue
if (-not $nssm) {
    $nssmPaths = @("C:\Windows\System32\nssm.exe", "C:\nssm\nssm.exe")
    foreach ($p in $nssmPaths) {
        if (Test-Path $p) { $nssm = $p; break }
    }
}
if (-not $nssm) {
    Write-Host "[X] NSSM not found!" -ForegroundColor Red
    exit 1
}
$nssmPath = if ($nssm.Source) { $nssm.Source } else { $nssm }
Write-Host "[i] Using NSSM: $nssmPath" -ForegroundColor Cyan

# Stop service
Write-Host ""
Write-Host "[i] Stopping service..." -ForegroundColor Cyan
Stop-Service -Name $serviceName -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 3

# Kill any stuck processes
$procs = Get-Process python, python3 -ErrorAction SilentlyContinue | Where-Object {
    try { $_.CommandLine -like "*production*scalping*" } catch { $false }
}
if ($procs) {
    $procs | Stop-Process -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 1
}

# Configure NSSM with correct script
Write-Host "[i] Configuring NSSM..." -ForegroundColor Cyan

# Use proper escaping for the script path
& $nssmPath set $serviceName Application "$pythonPath"
& $nssmPath set $serviceName AppParameters "`"$correctScript`""
& $nssmPath set $serviceName AppDirectory "$serviceDir"
& $nssmPath set $serviceName DisplayName "AI Scalping Service"
& $nssmPath set $serviceName Description "Production AI Scalping Service for Index Options Trading - Port 4002"
& $nssmPath set $serviceName Start SERVICE_AUTO_START

# Logging
$logDir = Join-Path $serviceDir "logs"
if (-not (Test-Path $logDir)) { New-Item -ItemType Directory -Path $logDir -Force | Out-Null }
& $nssmPath set $serviceName AppStdout (Join-Path $logDir "service_stdout.log")
& $nssmPath set $serviceName AppStderr (Join-Path $logDir "service_stderr.log")
& $nssmPath set $serviceName AppStdoutCreationDisposition 4
& $nssmPath set $serviceName AppStderrCreationDisposition 4
& $nssmPath set $serviceName AppRotateFiles 1
& $nssmPath set $serviceName AppRotateBytes 10485760
& $nssmPath set $serviceName AppRestartDelay 10000

Write-Host "[OK] NSSM configured!" -ForegroundColor Green

# Show current config
Write-Host ""
Write-Host "[i] Current NSSM configuration:" -ForegroundColor Cyan
& $nssmPath get $serviceName Application
& $nssmPath get $serviceName AppParameters
& $nssmPath get $serviceName AppDirectory

# Start service
Write-Host ""
Write-Host "[i] Starting service..." -ForegroundColor Cyan
Start-Service -Name $serviceName
Start-Sleep -Seconds 5

# Check status
$svc = Get-Service -Name $serviceName
if ($svc.Status -eq "Running") {
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Green
    Write-Host "  [OK] SERVICE FIXED AND RUNNING!" -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Green
    
    # Test endpoint
    Start-Sleep -Seconds 3
    try {
        $health = Invoke-RestMethod -Uri "http://localhost:4002/health" -TimeoutSec 10
        Write-Host "  Health: $($health.status)" -ForegroundColor Green
    } catch {
        Write-Host "  Health check pending (service starting up)" -ForegroundColor Yellow
    }
} else {
    Write-Host "[!] Service Status: $($svc.Status)" -ForegroundColor Yellow
    Write-Host "    Check logs at: $logDir" -ForegroundColor Yellow
}

Write-Host ""
Read-Host "Press Enter to exit"
