# Restart AI Trading Services
# Run this script as Administrator to apply code changes

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "  AI Trading Services Restart Script     " -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan

# Check if running as admin
$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $isAdmin) {
    Write-Host "`n[ERROR] This script requires Administrator privileges!" -ForegroundColor Red
    Write-Host "Please right-click on PowerShell and select 'Run as Administrator'" -ForegroundColor Yellow
    Read-Host "Press Enter to exit"
    exit 1
}

# All AI services including Signal Engine
$services = @("AIScalpingService", "AIOptionsHedger", "AISignalEngineService", "GeminiTradeService")

Write-Host "`n[INFO] Current service status:" -ForegroundColor Green
Get-Service -Name $services 2>$null | Format-Table Name, Status, StartType -AutoSize

Write-Host "[INFO] Stopping services..." -ForegroundColor Yellow
foreach ($svc in $services) {
    try {
        Stop-Service -Name $svc -Force -ErrorAction SilentlyContinue
        Write-Host "  - $svc stopped" -ForegroundColor Gray
    } catch {
        Write-Host "  - $svc not found or already stopped" -ForegroundColor DarkGray
    }
}

Start-Sleep -Seconds 3

Write-Host "`n[INFO] Starting services..." -ForegroundColor Yellow
foreach ($svc in $services) {
    try {
        Start-Service -Name $svc -ErrorAction SilentlyContinue
        Write-Host "  - $svc started" -ForegroundColor Green
    } catch {
        Write-Host "  - $svc failed to start: $_" -ForegroundColor Red
    }
}

Start-Sleep -Seconds 5

Write-Host "`n[INFO] Final service status:" -ForegroundColor Green
Get-Service -Name $services 2>$null | Format-Table Name, Status, StartType -AutoSize

Write-Host "`n[INFO] Testing service health..." -ForegroundColor Green
$endpoints = @(
    @{Name="AI Scalping Service"; URL="http://localhost:4002/health"},
    @{Name="AI Options Hedger"; URL="http://localhost:4003/health"},
    @{Name="AI Signal Engine"; URL="http://localhost:4090/health"},
    @{Name="Gemini AI Service"; URL="http://localhost:4080/health"}
)

foreach ($ep in $endpoints) {
    try {
        $response = Invoke-RestMethod -Uri $ep.URL -TimeoutSec 10 -ErrorAction Stop
        Write-Host "  [OK] $($ep.Name): $($response.status)" -ForegroundColor Green
    } catch {
        Write-Host "  [FAIL] $($ep.Name): Not responding" -ForegroundColor Red
    }
}

# Test evaluation endpoints
Write-Host "`n[INFO] Testing evaluation endpoints..." -ForegroundColor Green
$evalEndpoints = @(
    @{Name="Scalping Evaluation"; URL="http://localhost:4002/evaluation/status"},
    @{Name="Hedger Evaluation"; URL="http://localhost:4003/evaluation/status"},
    @{Name="Signal Engine Evaluation"; URL="http://localhost:4090/evaluation/status"}
)

foreach ($ep in $evalEndpoints) {
    try {
        $response = Invoke-RestMethod -Uri $ep.URL -TimeoutSec 5 -ErrorAction Stop
        Write-Host "  [OK] $($ep.Name): Mode=$($response.mode)" -ForegroundColor Green
    } catch {
        Write-Host "  [WARN] $($ep.Name): Not available" -ForegroundColor Yellow
    }
}

Write-Host "`n==========================================" -ForegroundColor Cyan
Write-Host "  Restart Complete                        " -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "`nServices are ready with updated code!" -ForegroundColor Green

Read-Host "`nPress Enter to exit"
