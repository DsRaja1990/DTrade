#!/usr/bin/env pwsh
# Toggle Test Script - Tests persistent state toggling
# Demonstrates strategy state persists even when service restarts

Write-Host "`n" -ForegroundColor Cyan
Write-Host "╔════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║        TOGGLE TEST - PERSISTENT STATE MANAGEMENT          ║" -ForegroundColor Cyan
Write-Host "╚════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan

$service = Read-Host "`nSelect service to test [1=Scalping, 2=Hedger, 3=Equity]"

switch ($service) {
    "1" {
        $name = "AI Scalping"
        $baseUrl = "http://localhost:4002"
        $statusUrl = "$baseUrl/status"
    }
    "2" {
        $name = "AI Options Hedger"
        $baseUrl = "http://localhost:4003"
        $statusUrl = "$baseUrl/status"
    }
    "3" {
        $name = "Elite Equity HV"
        $baseUrl = "http://localhost:5080"
        $statusUrl = "$baseUrl/api/status"
    }
    default {
        Write-Host "Invalid selection" -ForegroundColor Red
        exit
    }
}

Write-Host "`n═══ Testing $name ═══" -ForegroundColor Cyan

# Get current state
Write-Host "`n[1] Fetching current state..." -ForegroundColor Yellow
$currentState = Invoke-RestMethod $statusUrl
Write-Host "   Current: Strategy Enabled = $($currentState.strategy_enabled)" -ForegroundColor $(if($currentState.strategy_enabled){'Green'}else{'Red'})

# Toggle to opposite state
$endpoint = if ($currentState.strategy_enabled) { "/stop" } else { "/start" }
$action = if ($currentState.strategy_enabled) { "DISABLE" } else { "ENABLE" }

Write-Host "`n[2] Toggling strategy to $action..." -ForegroundColor Yellow
if ($service -eq "3") {
    $toggleUrl = "$baseUrl/api$endpoint"
} else {
    $toggleUrl = "$baseUrl$endpoint"
}

$body = @{
    capital = 500000
    max_daily_loss = 0.05
} | ConvertTo-Json

$response = Invoke-RestMethod $toggleUrl -Method Post -Body $body -ContentType "application/json"
Write-Host "   ✓ Toggled: Strategy Enabled = $($response.strategy_enabled)" -ForegroundColor $(if($response.strategy_enabled){'Green'}else{'Red'})

# Verify state persists
Write-Host "`n[3] Verifying state persisted..." -ForegroundColor Yellow
Start-Sleep -Seconds 2
$newState = Invoke-RestMethod $statusUrl
Write-Host "   ✓ Verified: Strategy Enabled = $($newState.strategy_enabled)" -ForegroundColor $(if($newState.strategy_enabled){'Green'}else{'Red'})

# Explain persistence
Write-Host "`n" -ForegroundColor Cyan
Write-Host "╔════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║                  PERSISTENCE TEST                          ║" -ForegroundColor Cyan
Write-Host "╚════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan

Write-Host "`n  Current State:" -ForegroundColor Yellow
Write-Host "  • Strategy Enabled: $($newState.strategy_enabled)" -ForegroundColor White
Write-Host "  • This state is saved to database/file" -ForegroundColor White
Write-Host "`n  What Happens:" -ForegroundColor Yellow
Write-Host "  • Windows service stays running 24/7" -ForegroundColor White
Write-Host "  • Strategy only trades when enabled" -ForegroundColor White
Write-Host "  • State persists across service restarts" -ForegroundColor White
Write-Host "  • Frontend shows current state on page load" -ForegroundColor White

Write-Host "`n  Test Persistence:" -ForegroundColor Yellow
Write-Host "  1. Note the current state: $(if($newState.strategy_enabled){'ENABLED'}else{'DISABLED'})" -ForegroundColor White
Write-Host "  2. Restart the service:" -ForegroundColor White

switch ($service) {
    "1" { Write-Host "     Restart-Service AIScalpingService -Force" -ForegroundColor Gray }
    "2" { Write-Host "     Restart-Service AIOptionsHedgerService -Force" -ForegroundColor Gray }
    "3" { Write-Host "     Restart-Service EliteEquityHVService -Force" -ForegroundColor Gray }
}

Write-Host "  3. Run .\Test-PersistentState.ps1 to verify state" -ForegroundColor White
Write-Host "  4. State should be: $(if($newState.strategy_enabled){'ENABLED'}else{'DISABLED'})" -ForegroundColor $(if($newState.strategy_enabled){'Green'}else{'Red'})

Write-Host "`n"
