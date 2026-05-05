<#
.SYNOPSIS
    Restart all DTrade Windows Services
    
.DESCRIPTION
    Restarts all trading services to apply updated configurations (like new Dhan tokens)
    Requires Administrator privileges
    
.NOTES
    Run this after updating Dhan access token
#>

# Check if running as Administrator
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $isAdmin) {
    Write-Host "This script requires Administrator privileges." -ForegroundColor Yellow
    Write-Host "Re-launching with Administrator rights..." -ForegroundColor Cyan
    Start-Process powershell -Verb RunAs -ArgumentList "-NoProfile -ExecutionPolicy Bypass -File `"$PSCommandPath`""
    exit
}

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  Restarting All DTrade Services" -ForegroundColor White
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

# Actual Windows services installed on the system
$services = @(
    @{Name="DhanHQ_Service"; Display="DhanHQ Trading Backend"; Port=8000},
    @{Name="TradingBot_IndexScalping"; Display="Index Scalping Strategy"; Port=4002},
    @{Name="TradingBot_OptionsHedger"; Display="Options Hedger Strategy"; Port=4003},
    @{Name="EliteEquityHVService"; Display="Elite Equity HV Service"; Port=5080},
    @{Name="TradingBot_IndexAdvanced"; Display="Signal Engine Service"; Port=4090},
    @{Name="TradingBot_DhanBackend"; Display="Gemini Trade Service"; Port=4080}
)

$successCount = 0
$failCount = 0

foreach ($svc in $services) {
    $serviceName = $svc.Name
    $displayName = $svc.Display
    
    Write-Host "Processing: $displayName ($serviceName)..." -ForegroundColor Cyan
    
    try {
        $service = Get-Service -Name $serviceName -ErrorAction Stop
        
        if ($service.Status -eq 'Running') {
            Write-Host "  Stopping $displayName..." -ForegroundColor Yellow
            Stop-Service -Name $serviceName -Force -ErrorAction Stop
            Start-Sleep -Seconds 2
        }
        
        Write-Host "  Starting $displayName..." -ForegroundColor Green
        Start-Service -Name $serviceName -ErrorAction Stop
        
        # Wait and verify
        Start-Sleep -Seconds 3
        $service = Get-Service -Name $serviceName
        
        if ($service.Status -eq 'Running') {
            Write-Host "  ✓ $displayName is running on port $($svc.Port)" -ForegroundColor Green
            $successCount++
        } else {
            Write-Host "  ✗ $displayName failed to start (Status: $($service.Status))" -ForegroundColor Red
            $failCount++
        }
        
    } catch {
        Write-Host "  ✗ Error with $displayName : $_" -ForegroundColor Red
        $failCount++
    }
    
    Write-Host ""
}

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "Summary:" -ForegroundColor White
Write-Host "  ✓ Successfully restarted: $successCount services" -ForegroundColor Green
Write-Host "  ✗ Failed: $failCount services" -ForegroundColor Red
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

if ($failCount -eq 0) {
    Write-Host "All services restarted successfully!" -ForegroundColor Green
} else {
    Write-Host "Some services failed to restart. Check logs for details." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Press any key to exit..."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
