# Install-Services-Admin.ps1
# Run this script with Administrator privileges to install Windows Services

param(
    [switch]$Uninstall,
    [switch]$Reinstall
)

$ErrorActionPreference = "Stop"

# Service definitions
$services = @(
    @{
        Name = "AIScalpingService"
        DisplayName = "AI Scalping Service"
        Description = "AI-powered index options scalping service for Indian markets"
        Path = "c:\Users\Dhanasimmaraja\Documents\TradeApp\DTrade\ai_scalping_service"
        Script = "production_service.py"
        Port = 4002
    },
    @{
        Name = "AIOptionsHedger"
        DisplayName = "AI Options Hedger"
        Description = "AI-powered options hedging service for Indian markets"
        Path = "c:\Users\Dhanasimmaraja\Documents\TradeApp\DTrade\ai_options_hedger"
        Script = "production_hedger_service.py"
        Port = 4003
    }
)

# Check for admin privileges
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $isAdmin) {
    Write-Host ""
    Write-Host "ERROR: This script requires Administrator privileges!" -ForegroundColor Red
    Write-Host ""
    Write-Host "Please run PowerShell as Administrator and try again." -ForegroundColor Yellow
    Write-Host ""
    exit 1
}

Write-Host ""
Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host "  AI Trading Services - Windows Service Installer" -ForegroundColor Cyan
Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host ""

# Check NSSM
$nssmPath = (Get-Command nssm -ErrorAction SilentlyContinue).Source
if (-not $nssmPath) {
    Write-Host "ERROR: NSSM not found!" -ForegroundColor Red
    Write-Host "Please install NSSM: winget install nssm" -ForegroundColor Yellow
    exit 1
}
Write-Host "NSSM found: $nssmPath" -ForegroundColor Green
Write-Host ""

function Uninstall-Service {
    param($svc)
    
    Write-Host "----------------------------------------" -ForegroundColor Gray
    Write-Host "Uninstalling: $($svc.DisplayName)" -ForegroundColor Yellow
    Write-Host "----------------------------------------" -ForegroundColor Gray
    
    # Check if service exists
    $existingService = Get-Service -Name $svc.Name -ErrorAction SilentlyContinue
    
    if ($existingService) {
        # Stop service if running
        if ($existingService.Status -eq 'Running') {
            Write-Host "  Stopping service..." -ForegroundColor Gray
            Stop-Service -Name $svc.Name -Force -ErrorAction SilentlyContinue
            Start-Sleep -Seconds 2
        }
        
        # Remove with NSSM
        Write-Host "  Removing service..." -ForegroundColor Gray
        $result = & nssm remove $svc.Name confirm 2>&1
        Write-Host "  $result" -ForegroundColor Gray
        Start-Sleep -Seconds 1
        
        Write-Host "  Service uninstalled!" -ForegroundColor Green
    } else {
        Write-Host "  Service not found (already uninstalled)" -ForegroundColor Gray
    }
    
    # Also kill any running Python processes for this service
    $pythonPath = Join-Path $svc.Path ".venv\Scripts\python.exe"
    Get-Process -Name "python" -ErrorAction SilentlyContinue | Where-Object {
        $_.Path -eq $pythonPath
    } | ForEach-Object {
        Write-Host "  Killing orphan process: $($_.Id)" -ForegroundColor Gray
        Stop-Process -Id $_.Id -Force -ErrorAction SilentlyContinue
    }
    
    Write-Host ""
}

function Install-Service {
    param($svc)
    
    Write-Host "----------------------------------------" -ForegroundColor Gray
    Write-Host "Installing: $($svc.DisplayName)" -ForegroundColor Cyan
    Write-Host "----------------------------------------" -ForegroundColor Gray
    
    $pythonPath = Join-Path $svc.Path ".venv\Scripts\python.exe"
    $scriptPath = Join-Path $svc.Path $svc.Script
    
    # Verify paths exist
    if (-not (Test-Path $pythonPath)) {
        Write-Host "  ERROR: Python not found at $pythonPath" -ForegroundColor Red
        Write-Host "  Please create venv first: python -m venv .venv" -ForegroundColor Yellow
        return $false
    }
    
    if (-not (Test-Path $scriptPath)) {
        Write-Host "  ERROR: Script not found at $scriptPath" -ForegroundColor Red
        return $false
    }
    
    Write-Host "  Python: $pythonPath" -ForegroundColor Gray
    Write-Host "  Script: $scriptPath" -ForegroundColor Gray
    Write-Host "  Port: $($svc.Port)" -ForegroundColor Gray
    
    # Install service with NSSM
    Write-Host "  Installing service..." -ForegroundColor Gray
    & nssm install $svc.Name $pythonPath $scriptPath
    
    if ($LASTEXITCODE -ne 0) {
        Write-Host "  ERROR: Failed to install service" -ForegroundColor Red
        return $false
    }
    
    # Configure service
    Write-Host "  Configuring service..." -ForegroundColor Gray
    
    & nssm set $svc.Name DisplayName $svc.DisplayName
    & nssm set $svc.Name Description $svc.Description
    & nssm set $svc.Name AppDirectory $svc.Path
    & nssm set $svc.Name Start SERVICE_AUTO_START
    & nssm set $svc.Name AppStopMethodSkip 0
    & nssm set $svc.Name AppStopMethodConsole 3000
    & nssm set $svc.Name AppStopMethodWindow 3000
    & nssm set $svc.Name AppStopMethodThreads 3000
    & nssm set $svc.Name AppThrottle 5000
    & nssm set $svc.Name AppExit Default Restart
    & nssm set $svc.Name AppRestartDelay 10000
    
    # Configure logging
    $logPath = Join-Path $svc.Path "logs"
    if (-not (Test-Path $logPath)) {
        New-Item -ItemType Directory -Path $logPath -Force | Out-Null
    }
    
    $stdoutLog = Join-Path $logPath "service_stdout.log"
    $stderrLog = Join-Path $logPath "service_stderr.log"
    
    & nssm set $svc.Name AppStdout $stdoutLog
    & nssm set $svc.Name AppStderr $stderrLog
    & nssm set $svc.Name AppStdoutCreationDisposition 4
    & nssm set $svc.Name AppStderrCreationDisposition 4
    & nssm set $svc.Name AppRotateFiles 1
    & nssm set $svc.Name AppRotateOnline 1
    & nssm set $svc.Name AppRotateBytes 10485760
    
    Write-Host "  Service installed!" -ForegroundColor Green
    Write-Host ""
    
    return $true
}

function Start-InstalledService {
    param($svc)
    
    Write-Host "Starting: $($svc.DisplayName)..." -ForegroundColor Gray
    
    try {
        Start-Service -Name $svc.Name -ErrorAction Stop
        Start-Sleep -Seconds 3
        
        $service = Get-Service -Name $svc.Name
        if ($service.Status -eq 'Running') {
            Write-Host "  Started successfully!" -ForegroundColor Green
            
            # Verify port
            Start-Sleep -Seconds 2
            try {
                $response = Invoke-RestMethod -Uri "http://localhost:$($svc.Port)/health" -TimeoutSec 10
                Write-Host "  Health: $($response.status)" -ForegroundColor Green
            } catch {
                Write-Host "  Waiting for service to become healthy..." -ForegroundColor Yellow
            }
        } else {
            Write-Host "  Status: $($service.Status)" -ForegroundColor Yellow
        }
    } catch {
        Write-Host "  ERROR: Failed to start service: $_" -ForegroundColor Red
    }
    Write-Host ""
}

# Main execution
if ($Uninstall) {
    Write-Host "UNINSTALLING SERVICES..." -ForegroundColor Yellow
    Write-Host ""
    
    foreach ($svc in $services) {
        Uninstall-Service -svc $svc
    }
    
    Write-Host "======================================================================" -ForegroundColor Cyan
    Write-Host "  All services uninstalled!" -ForegroundColor Green
    Write-Host "======================================================================" -ForegroundColor Cyan
    
} elseif ($Reinstall) {
    Write-Host "REINSTALLING SERVICES..." -ForegroundColor Yellow
    Write-Host ""
    
    # Uninstall first
    foreach ($svc in $services) {
        Uninstall-Service -svc $svc
    }
    
    Write-Host ""
    Write-Host "Installing fresh..." -ForegroundColor Cyan
    Write-Host ""
    
    # Install
    $allSuccess = $true
    foreach ($svc in $services) {
        $result = Install-Service -svc $svc
        if (-not $result) { $allSuccess = $false }
    }
    
    if ($allSuccess) {
        Write-Host ""
        Write-Host "Starting services..." -ForegroundColor Cyan
        Write-Host ""
        
        foreach ($svc in $services) {
            Start-InstalledService -svc $svc
        }
        
        Write-Host "======================================================================" -ForegroundColor Cyan
        Write-Host "  All services reinstalled and started!" -ForegroundColor Green
        Write-Host "======================================================================" -ForegroundColor Cyan
    }
    
} else {
    # Install only
    Write-Host "INSTALLING SERVICES..." -ForegroundColor Cyan
    Write-Host ""
    
    # Uninstall existing first (clean install)
    foreach ($svc in $services) {
        $existingService = Get-Service -Name $svc.Name -ErrorAction SilentlyContinue
        if ($existingService) {
            Write-Host "Service $($svc.Name) exists, removing first..." -ForegroundColor Yellow
            Uninstall-Service -svc $svc
        }
    }
    
    # Install
    $allSuccess = $true
    foreach ($svc in $services) {
        $result = Install-Service -svc $svc
        if (-not $result) { $allSuccess = $false }
    }
    
    if ($allSuccess) {
        Write-Host ""
        Write-Host "Starting services..." -ForegroundColor Cyan
        Write-Host ""
        
        foreach ($svc in $services) {
            Start-InstalledService -svc $svc
        }
        
        Write-Host "======================================================================" -ForegroundColor Cyan
        Write-Host "  All services installed and started!" -ForegroundColor Green
        Write-Host "======================================================================" -ForegroundColor Cyan
    }
}

Write-Host ""
Write-Host "Service Status:" -ForegroundColor Cyan
Write-Host "----------------------------------------" -ForegroundColor Gray

foreach ($svc in $services) {
    $service = Get-Service -Name $svc.Name -ErrorAction SilentlyContinue
    if ($service) {
        $statusColor = if ($service.Status -eq 'Running') { 'Green' } else { 'Yellow' }
        Write-Host "  $($svc.DisplayName): $($service.Status)" -ForegroundColor $statusColor
    } else {
        Write-Host "  $($svc.DisplayName): Not Installed" -ForegroundColor Red
    }
}

Write-Host ""
Write-Host "Management Commands:" -ForegroundColor Cyan
Write-Host "  Get-Service AIScalpingService" -ForegroundColor Gray
Write-Host "  Get-Service AIOptionsHedger" -ForegroundColor Gray
Write-Host "  Start-Service <name>" -ForegroundColor Gray
Write-Host "  Stop-Service <name>" -ForegroundColor Gray
Write-Host "  Restart-Service <name>" -ForegroundColor Gray
Write-Host ""
Write-Host "Health Endpoints:" -ForegroundColor Cyan
Write-Host "  http://localhost:4002/health" -ForegroundColor Gray
Write-Host "  http://localhost:4003/health" -ForegroundColor Gray
Write-Host ""
