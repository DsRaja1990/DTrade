#Requires -Version 5.1
<#
.SYNOPSIS
    DTrade Services - Master Management Script
.DESCRIPTION
    Manages both AI trading services from a single interface
.PARAMETER Action
    The action to perform: start, stop, restart, status, test, install, uninstall
.PARAMETER Service
    Which service: scalping, hedger, or all (default)
.EXAMPLE
    .\Manage-All-Services.ps1 start
    .\Manage-All-Services.ps1 -Action status -Service scalping
    .\Manage-All-Services.ps1 install  # Install both as Windows Services
#>

[CmdletBinding()]
param(
    [Parameter(Position=0)]
    [ValidateSet('start', 'stop', 'restart', 'status', 'test', 'install', 'uninstall', 'help', 'menu')]
    [string]$Action = 'menu',
    
    [ValidateSet('scalping', 'hedger', 'equity', 'signal', 'gemini', 'backend', 'strategies', 'support', 'all')]
    [string]$Service = 'all'
)

$script:RootDir = $PSScriptRoot
$script:ScalpingDir = Join-Path $script:RootDir "ai_scalping_service"
$script:HedgerDir = Join-Path $script:RootDir "ai_options_hedger"
$script:EquityDir = Join-Path $script:RootDir "equity_hv_service"
$script:SignalDir = Join-Path $script:RootDir "signal_engine_service"
$script:GeminiDir = Join-Path $script:RootDir "gemini_trade_service"
$script:BackendDir = Join-Path $script:RootDir "backend"

$script:Services = @{
    scalping = @{
        Name = "AI Scalping Service"
        WinName = "AIScalpingService"
        Port = 4002
        Dir = $script:ScalpingDir
        Script = "Manage-Service.ps1"
        Type = "Strategy"
    }
    hedger = @{
        Name = "AI Options Hedger"
        WinName = "AIOptionsHedgerService"
        Port = 4003
        Dir = $script:HedgerDir
        Script = "Manage-Service.ps1"
        Type = "Strategy"
    }
    equity = @{
        Name = "Elite Equity HV Service"
        WinName = "EliteEquityHVService"
        Port = 5080
        Dir = $script:EquityDir
        Script = "Manage-Service.ps1"
        Type = "Strategy"
    }
    signal = @{
        Name = "AI Signal Engine"
        WinName = "AISignalEngineService"
        Port = 4001
        Dir = $script:SignalDir
        Script = "Manage-Service.ps1"
        Type = "Support"
    }
    gemini = @{
        Name = "Gemini Trade Service"
        WinName = "GeminiTradeService"
        Port = 4004
        Dir = $script:GeminiDir
        Script = "Manage-Service.ps1"
        Type = "Support"
    }
    backend = @{
        Name = "DhanHQ Backend"
        WinName = "DhanHQBackendService"
        Port = 3001
        Dir = $script:BackendDir
        Script = "Install-DhanHQ-Service.ps1"
        Type = "Support"
    }
}

function Write-Header {
    param([string]$Title)
    Write-Host ""
    Write-Host ("=" * 70) -ForegroundColor Magenta
    Write-Host "  $Title" -ForegroundColor White
    Write-Host ("=" * 70) -ForegroundColor Magenta
}

function Test-Administrator {
    $currentUser = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($currentUser)
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

function Get-PortPID {
    param([int]$Port)
    try {
        $connections = netstat -ano 2>$null | Select-String ":$Port\s" | Select-String "LISTENING"
        if ($connections) {
            $line = $connections[0].ToString().Trim()
            $parts = $line -split '\s+'
            $procId = $parts[-1]
            if ($procId -match '^\d+$') {
                return [int]$procId
            }
        }
    } catch {}
    return $null
}

function Invoke-ServiceAction {
    param(
        [string]$ServiceKey,
        [string]$ActionName
    )
    
    $svc = $script:Services[$ServiceKey]
    $scriptPath = Join-Path $svc.Dir $svc.Script
    
    if (Test-Path $scriptPath) {
        Write-Host ""
        Write-Host ">>> $($svc.Name) <<<" -ForegroundColor Yellow
        Push-Location $svc.Dir
        try {
            & $scriptPath $ActionName
        } finally {
            Pop-Location
        }
    } else {
        Write-Host "Script not found: $scriptPath" -ForegroundColor Red
    }
}

function Get-ServicesToManage {
    $servicesToManage = @()
    
    switch ($Service) {
        'all' { 
            $servicesToManage = @('scalping', 'hedger', 'equity', 'signal', 'gemini', 'backend')
        }
        'strategies' {
            $servicesToManage = @('scalping', 'hedger', 'equity')
        }
        'support' {
            $servicesToManage = @('signal', 'gemini', 'backend')
        }
        default {
            $servicesToManage = @($Service)
        }
    }
    
    return $servicesToManage
}

function Start-AllServices {
    Write-Header "Starting Services"
    
    $services = Get-ServicesToManage
    foreach ($svcKey in $services) {
        if ($script:Services.ContainsKey($svcKey)) {
            Invoke-ServiceAction $svcKey 'start'
        }
    }
}

function Stop-AllServices {
    Write-Header "Stopping Services"
    
    $services = Get-ServicesToManage
    foreach ($svcKey in $services) {
        if ($script:Services.ContainsKey($svcKey)) {
            Invoke-ServiceAction $svcKey 'stop'
        }
    }
}

function Restart-AllServices {
    Write-Header "Restarting Services"
    
    if (-not (Test-Administrator)) {
        Write-Host ""
        Write-Host "WARNING: Not running as Administrator!" -ForegroundColor Yellow
        Write-Host "Service restarts may fail. Please run as Administrator for best results." -ForegroundColor Yellow
        Write-Host ""
        $continue = Read-Host "Continue anyway? (Y/N)"
        if ($continue -ne 'Y' -and $continue -ne 'y') {
            return
        }
    }
    
    $services = Get-ServicesToManage
    
    Write-Host ""
    Write-Host "Restarting $($services.Count) service(s)..." -ForegroundColor Cyan
    Write-Host ""
    
    foreach ($svcKey in $services) {
        if ($script:Services.ContainsKey($svcKey)) {
            $svc = $script:Services[$svcKey]
            Write-Host "[$($svc.Name)]" -ForegroundColor Yellow
            
            # Check if Windows service exists
            $winService = Get-Service -Name $svc.WinName -ErrorAction SilentlyContinue
            
            if ($winService) {
                try {
                    Restart-Service -Name $svc.WinName -Force -ErrorAction Stop
                    Write-Host "  [OK] Windows Service restarted" -ForegroundColor Green
                } catch {
                    Write-Host "  [FAILED] Error: $_" -ForegroundColor Red
                }
            } else {
                Write-Host "  [WARNING] Not installed as Windows Service, skipping..." -ForegroundColor Yellow
                Write-Host "  [INFO] To restart this service, use its individual Manage-Service.ps1" -ForegroundColor Cyan
            }
            Write-Host ""
        }
    }
    
    Write-Host "[WAIT] Waiting for services to start..." -ForegroundColor Yellow
    Start-Sleep -Seconds 10
    
    Write-Host ""
    Write-Host "Verifying services..." -ForegroundColor Cyan
    Get-AllServicesStatus
}

function Get-AllServicesStatus {
    Write-Header "Services Status"
    
    # Group by type
    $strategyServices = @('scalping', 'hedger', 'equity')
    $supportServices = @('signal', 'gemini', 'backend')
    
    Write-Host ""
    Write-Host "  --- STRATEGY SERVICES ---" -ForegroundColor Magenta
    
    foreach ($key in $strategyServices) {
        if ($script:Services.ContainsKey($key)) {
            Show-ServiceStatus $key
        }
    }
    
    Write-Host ""
    Write-Host "  --- SUPPORT SERVICES ---" -ForegroundColor Cyan
    
    foreach ($key in $supportServices) {
        if ($script:Services.ContainsKey($key)) {
            Show-ServiceStatus $key
        }
    }
    
    Write-Host ""
}

function Show-ServiceStatus {
    param([string]$key)
    
    $svc = $script:Services[$key]
    Write-Host ""
    Write-Host "  [$($svc.Name)]" -ForegroundColor Yellow
    Write-Host ("  " + ("-" * 50))
    
    # Check Windows Service
    $winSvc = Get-Service -Name $svc.WinName -ErrorAction SilentlyContinue
    if ($winSvc) {
        $winColor = if ($winSvc.Status -eq 'Running') { 'Green' } else { 'Red' }
        Write-Host "    Windows Service: " -NoNewline
        Write-Host "$($winSvc.Status)" -ForegroundColor $winColor
    } else {
        Write-Host "    Windows Service: " -NoNewline
        Write-Host "NOT INSTALLED" -ForegroundColor DarkGray
    }
    
    # Check if running on port
    $procId = Get-PortPID -Port $svc.Port
    if ($procId) {
        Write-Host "    Process Status:  " -NoNewline
        Write-Host "RUNNING" -ForegroundColor Green
        Write-Host "    PID:             $procId"
        Write-Host "    Port:            $($svc.Port)"
        
        # Get detailed status for strategy services
        if ($svc.Type -eq 'Strategy') {
            try {
                $statusUrl = if ($key -eq 'equity') { "http://localhost:$($svc.Port)/api/status" } else { "http://localhost:$($svc.Port)/status" }
                $status = Invoke-RestMethod -Uri $statusUrl -TimeoutSec 3 -ErrorAction Stop
                
                # Mode
                if ($status.mode) {
                    $modeColor = if ($status.mode -eq 'paper') { 'Yellow' } else { 'Red' }
                    Write-Host "    Mode:            " -NoNewline
                    Write-Host "$($status.mode)" -ForegroundColor $modeColor
                }
                
                # Strategy Enabled
                if ($null -ne $status.strategy_enabled) {
                    $enabledColor = if ($status.strategy_enabled) { 'Green' } else { 'Red' }
                    $enabledText = if ($status.strategy_enabled) { 'ACTIVE' } else { 'INACTIVE' }
                    Write-Host "    Strategy:        " -NoNewline
                    Write-Host "$enabledText" -ForegroundColor $enabledColor
                }
            } catch {
                Write-Host "    Status:          (could not fetch)" -ForegroundColor Gray
            }
        } else {
            # Health check for support services
            try {
                $health = Invoke-RestMethod -Uri "http://localhost:$($svc.Port)/health" -TimeoutSec 3 -ErrorAction Stop
                Write-Host "    Health:          " -NoNewline
                Write-Host "$($health.status)" -ForegroundColor Green
            } catch {
                Write-Host "    Health:          (could not fetch)" -ForegroundColor Gray
            }
        }
    } else {
        Write-Host "    Process Status:  " -NoNewline
        Write-Host "STOPPED" -ForegroundColor Red
    }
}

function Test-AllServices {
    Write-Header "Testing Services"
    
    foreach ($key in $script:Services.Keys) {
        $svc = $script:Services[$key]
        Write-Host ""
        Write-Host "Testing $($svc.Name)..." -ForegroundColor Yellow
        
        try {
            $health = Invoke-RestMethod -Uri "http://localhost:$($svc.Port)/health" -TimeoutSec 3 -ErrorAction Stop
            Write-Host "  Health: $($health.status)" -ForegroundColor Green
            
            try {
                $token = Invoke-RestMethod -Uri "http://localhost:$($svc.Port)/token-status" -TimeoutSec 3 -ErrorAction Stop
                if ($token.expired) {
                    Write-Host "  Token: EXPIRED" -ForegroundColor Red
                } else {
                    Write-Host "  Token: Valid until $($token.expires_at)" -ForegroundColor Green
                }
            } catch {
                Write-Host "  Token: Could not check" -ForegroundColor Yellow
            }
        } catch {
            Write-Host "  Not responding" -ForegroundColor Red
        }
    }
    Write-Host ""
}

function Install-AllWindowsServices {
    Write-Header "Install Windows Services"
    
    if (-not (Test-Administrator)) {
        Write-Host "ERROR: Administrator privileges required!" -ForegroundColor Red
        Write-Host "Please run PowerShell as Administrator and try again." -ForegroundColor Yellow
        return
    }
    
    $services = Get-ServicesToManage
    foreach ($svcKey in $services) {
        if ($script:Services.ContainsKey($svcKey)) {
            Invoke-ServiceAction $svcKey 'install'
        }
    }
}

function Uninstall-AllWindowsServices {
    Write-Header "Uninstall Windows Services"
    
    if (-not (Test-Administrator)) {
        Write-Host "ERROR: Administrator privileges required!" -ForegroundColor Red
        Write-Host "Please run PowerShell as Administrator and try again." -ForegroundColor Yellow
        return
    }
    
    $services = Get-ServicesToManage
    foreach ($svcKey in $services) {
        if ($script:Services.ContainsKey($svcKey)) {
            Invoke-ServiceAction $svcKey 'uninstall'
        }
    }
}

function Show-Menu {
    while ($true) {
        Clear-Host
        Write-Host ""
        Write-Host "=======================================================================" -ForegroundColor Magenta
        Write-Host "  DTrade - All Services Manager (6 Services)" -ForegroundColor White
        Write-Host "=======================================================================" -ForegroundColor Magenta
        Write-Host ""
        
        # Strategy Services
        Write-Host "  --- STRATEGY SERVICES ---" -ForegroundColor Magenta
        $strategyKeys = @('scalping', 'hedger', 'equity')
        foreach ($key in $strategyKeys) {
            if ($script:Services.ContainsKey($key)) {
                $svc = $script:Services[$key]
                $procId = Get-PortPID -Port $svc.Port
                $status = if ($procId) { "[*]" } else { "[ ]" }
                $color = if ($procId) { "Green" } else { "Red" }
                Write-Host "    $status " -NoNewline -ForegroundColor $color
                Write-Host "$($svc.Name) " -NoNewline
                Write-Host "(Port $($svc.Port))" -ForegroundColor Gray
            }
        }
        
        # Support Services
        Write-Host ""
        Write-Host "  --- SUPPORT SERVICES ---" -ForegroundColor Cyan
        $supportKeys = @('signal', 'gemini', 'backend')
        foreach ($key in $supportKeys) {
            if ($script:Services.ContainsKey($key)) {
                $svc = $script:Services[$key]
                $procId = Get-PortPID -Port $svc.Port
                $status = if ($procId) { "[*]" } else { "[ ]" }
                $color = if ($procId) { "Green" } else { "Red" }
                Write-Host "    $status " -NoNewline -ForegroundColor $color
                Write-Host "$($svc.Name) " -NoNewline
                Write-Host "(Port $($svc.Port))" -ForegroundColor Gray
            }
        }
        
        Write-Host ""
        Write-Host "-----------------------------------------------------------------------" -ForegroundColor DarkGray
        Write-Host "  MAIN ACTIONS" -ForegroundColor Yellow
        Write-Host "-----------------------------------------------------------------------" -ForegroundColor DarkGray
        Write-Host "    1. Start All Services (6)"
        Write-Host "    2. Stop All Services"
        Write-Host "    3. Restart All Services" -ForegroundColor Green
        Write-Host "    4. View Detailed Status"
        Write-Host "    5. Test Services Health"
        Write-Host ""
        Write-Host "-----------------------------------------------------------------------" -ForegroundColor DarkGray
        Write-Host "  GROUP ACTIONS" -ForegroundColor Yellow
        Write-Host "-----------------------------------------------------------------------" -ForegroundColor DarkGray
        Write-Host "    S. Restart Strategy Services Only (3)"
        Write-Host "    P. Restart Support Services Only (3)"
        Write-Host ""
        Write-Host "-----------------------------------------------------------------------" -ForegroundColor DarkGray
        Write-Host "  INDIVIDUAL SERVICE MANAGEMENT" -ForegroundColor Yellow
        Write-Host "-----------------------------------------------------------------------" -ForegroundColor DarkGray
        Write-Host "    A. AI Scalping Service"
        Write-Host "    B. AI Options Hedger"
        Write-Host "    C. Elite Equity HV Service"
        Write-Host "    D. AI Signal Engine"
        Write-Host "    E. Gemini Trade Service"
        Write-Host "    F. DhanHQ Backend"
        Write-Host ""
        Write-Host "-----------------------------------------------------------------------" -ForegroundColor DarkGray
        Write-Host "  WINDOWS SERVICE MANAGEMENT (Admin)" -ForegroundColor Yellow
        Write-Host "-----------------------------------------------------------------------" -ForegroundColor DarkGray
        Write-Host "    I. Install All as Windows Services"
        Write-Host "    U. Uninstall All Windows Services"
        Write-Host ""
        Write-Host "    0. Exit"
        Write-Host ""
        Write-Host "=======================================================================" -ForegroundColor Magenta
        Write-Host ""
        
        $choice = Read-Host "Select option"
        
        switch ($choice.ToLower()) {
            '1' { 
                $script:Service = 'all'
                Start-AllServices 
                Read-Host "`nPress Enter to continue"
            }
            '2' { 
                $script:Service = 'all'
                Stop-AllServices 
                Read-Host "`nPress Enter to continue"
            }
            '3' { 
                $script:Service = 'all'
                Restart-AllServices 
                Read-Host "`nPress Enter to continue"
            }
            '4' { 
                Get-AllServicesStatus 
                Read-Host "`nPress Enter to continue"
            }
            '5' { 
                Test-AllServices 
                Read-Host "`nPress Enter to continue"
            }
            's' {
                $script:Service = 'strategies'
                Restart-AllServices
                Read-Host "`nPress Enter to continue"
            }
            'p' {
                $script:Service = 'support'
                Restart-AllServices
                Read-Host "`nPress Enter to continue"
            }
            'a' { 
                Push-Location $script:ScalpingDir
                try { & ".\Manage-Service.ps1" menu } finally { Pop-Location }
            }
            'b' {
                Push-Location $script:HedgerDir
                try { & ".\Manage-Service.ps1" menu } finally { Pop-Location }
            }
            'c' {
                Push-Location $script:EquityDir
                try { & ".\Manage-Service.ps1" menu } finally { Pop-Location }
            }
            'd' {
                Push-Location $script:SignalDir
                try { & ".\Manage-Service.ps1" menu } finally { Pop-Location }
            }
            'e' {
                Push-Location $script:GeminiDir
                try { & ".\Manage-Service.ps1" menu } finally { Pop-Location }
            }
            'f' {
                Write-Host "`nDhanHQ Backend service management not yet implemented" -ForegroundColor Yellow
                Read-Host "`nPress Enter to continue"
            }
            'i' { 
                $script:Service = 'all'
                Install-AllWindowsServices 
                Read-Host "`nPress Enter to continue"
            }
            'u' { 
                $script:Service = 'all'
                Uninstall-AllWindowsServices 
                Read-Host "`nPress Enter to continue"
            }
            '0' { return }
            default { 
                Write-Host "`nInvalid option" -ForegroundColor Red 
                Start-Sleep -Seconds 1
            }
        }
    }
}

function Show-Help {
    Write-Host @"

DTrade - All Services Manager (6 Services)

Usage: .\Manage-All-Services.ps1 [-Action <action>] [-Service <service>]

Actions:
  start     - Start services
  stop      - Stop services
  restart   - Restart services (recommended after code changes)
  status    - Show status of all services
  test      - Test service health
  install   - Install as Windows Services (requires Admin)
  uninstall - Remove Windows Services (requires Admin)
  menu      - Interactive menu (default)

Services:
  scalping   - AI Scalping Service (Port 4002)
  hedger     - AI Options Hedger (Port 4003)
  equity     - Elite Equity HV Service (Port 5080)
  signal     - AI Signal Engine (Port 4001)
  gemini     - Gemini Trade Service (Port 4004)
  backend    - DhanHQ Backend (Port 3001)
  strategies - All 3 strategy services
  support    - All 3 support services
  all        - All 6 services (default)

Examples:
  .\Manage-All-Services.ps1 restart
  .\Manage-All-Services.ps1 -Action restart -Service strategies
  .\Manage-All-Services.ps1 -Action status
  .\Manage-All-Services.ps1 -Action stop -Service equity
  .\Manage-All-Services.ps1 install

Common Scenarios:
  # After making code changes - restart strategy services
  .\Manage-All-Services.ps1 restart -Service strategies
  
  # Check if all services are running
  .\Manage-All-Services.ps1 status
  
  # Restart everything
  .\Manage-All-Services.ps1 restart
  
  # Interactive menu (easiest)
  .\Manage-All-Services.ps1

Individual Service Management:
  cd ai_scalping_service
  .\Manage-Service.ps1

  cd ai_options_hedger
  .\Manage-Service.ps1
  
  cd equity_hv_service
  .\Manage-Service.ps1

"@
}

# Main execution
switch ($Action) {
    'start'     { Start-AllServices }
    'stop'      { Stop-AllServices }
    'restart'   { Restart-AllServices }
    'status'    { Get-AllServicesStatus }
    'test'      { Test-AllServices }
    'install'   { Install-AllWindowsServices }
    'uninstall' { Uninstall-AllWindowsServices }
    'help'      { Show-Help }
    'menu'      { Show-Menu }
    default     { Show-Menu }
}
