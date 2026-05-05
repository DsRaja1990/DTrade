# Admin script to restart Signal Engine service
# Run this as Administrator

param(
    [switch]$Force
)

if (-not ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-Host "[ERROR] This script must be run as Administrator" -ForegroundColor Red
    exit 1
}

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "   Restarting AI Signal Engine Service   " -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

try {
    Write-Host "[*] Stopping AISignalEngineService..." -ForegroundColor Yellow
    Stop-Service "AISignalEngineService" -Force -ErrorAction Stop
    Start-Sleep -Seconds 2
    Write-Host "[OK] Service stopped" -ForegroundColor Green
    
    Write-Host "[*] Starting AISignalEngineService..." -ForegroundColor Yellow
    Start-Service "AISignalEngineService" -ErrorAction Stop
    Start-Sleep -Seconds 3
    
    $status = Get-Service "AISignalEngineService" | Select-Object -ExpandProperty Status
    if ($status -eq "Running") {
        Write-Host "[OK] Service started - Status: $status" -ForegroundColor Green
        
        # Test the health endpoint
        Write-Host "`n[*] Testing service health..." -ForegroundColor Yellow
        try {
            $health = Invoke-RestMethod -Uri "http://localhost:4090/health" -Method GET -TimeoutSec 5
            Write-Host "[OK] Service is healthy" -ForegroundColor Green
            Write-Host "     Status: $($health.status)" -ForegroundColor White
        } catch {
            Write-Host "[WARN] Health check failed: $($_.Exception.Message)" -ForegroundColor Yellow
        }
    } else {
        Write-Host "[ERROR] Service failed to start - Status: $status" -ForegroundColor Red
    }
} catch {
    Write-Host "[ERROR] Failed to restart service: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

Write-Host "`n========================================`n" -ForegroundColor Cyan
