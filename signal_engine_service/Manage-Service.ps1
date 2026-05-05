# ============================================
# AI Signal Engine Service Installer
# Service Name: AISignalEngineService
# Port: 4090
# Run as Administrator
# ============================================

param(
    [switch]$Install,
    [switch]$Uninstall,
    [switch]$Start,
    [switch]$Stop,
    [switch]$Restart,
    [switch]$Status
)

$ErrorActionPreference = "Stop"

$ServiceName = "AISignalEngineService"
$ServiceDisplayName = "AI Signal Engine Service"
$ServiceDescription = "World-Class AI-Powered Trading Signal Generator for NIFTY, BANKNIFTY, SENSEX. Port 4090"

$ScriptPath = $PSScriptRoot
$ProjectRoot = Split-Path -Parent $ScriptPath
$PythonExe = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
$ServiceScript = Join-Path $ScriptPath "windows_service.py"
$MainScript = Join-Path $ScriptPath "world_class_signal_engine.py"

# Colors
function Write-Info { param($msg) Write-Host $msg -ForegroundColor Cyan }
function Write-Success { param($msg) Write-Host $msg -ForegroundColor Green }
function Write-Warn { param($msg) Write-Host $msg -ForegroundColor Yellow }
function Write-Err { param($msg) Write-Host $msg -ForegroundColor Red }

# Check admin
function Test-Admin {
    $currentPrincipal = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
    return $currentPrincipal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

# Get service status
function Get-ServiceStatus {
    $svc = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue
    if ($svc) {
        Write-Info "Service: $ServiceDisplayName"
        Write-Info "Status: $($svc.Status)"
        Write-Info "Name: $ServiceName"
        
        # Check if port is listening
        $port = netstat -ano | Select-String ":4090"
        if ($port) {
            Write-Success "Port 4090: LISTENING"
        } else {
            Write-Warn "Port 4090: NOT LISTENING"
        }
        
        # Check health endpoint
        try {
            $health = Invoke-RestMethod -Uri "http://localhost:4090/health" -TimeoutSec 5 -ErrorAction SilentlyContinue
            if ($health.status -eq "healthy") {
                Write-Success "Health: OK"
                Write-Info "Cached Signals: $($health.cached_signals)"
            }
        } catch {
            Write-Warn "Health endpoint not responding"
        }
    } else {
        Write-Warn "Service not installed"
    }
}

# Install service
function Install-SignalService {
    if (-not (Test-Admin)) {
        Write-Err "Please run as Administrator!"
        return
    }
    
    Write-Info "Installing $ServiceDisplayName..."
    
    # Remove old service if exists
    $existing = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue
    if ($existing) {
        Write-Warn "Removing existing service..."
        Stop-Service -Name $ServiceName -Force -ErrorAction SilentlyContinue
        Start-Sleep -Seconds 2
        sc.exe delete $ServiceName | Out-Null
        Start-Sleep -Seconds 2
    }
    
    # Also remove any old signal engine services
    $oldServices = @("SignalEngineService", "WorldClassSignalEngine")
    foreach ($oldSvc in $oldServices) {
        $old = Get-Service -Name $oldSvc -ErrorAction SilentlyContinue
        if ($old) {
            Write-Warn "Removing old service: $oldSvc"
            Stop-Service -Name $oldSvc -Force -ErrorAction SilentlyContinue
            sc.exe delete $oldSvc | Out-Null
            Start-Sleep -Seconds 1
        }
    }
    
    # Install using pywin32
    Write-Info "Installing service using pywin32..."
    
    try {
        & $PythonExe $ServiceScript install
        if ($LASTEXITCODE -eq 0) {
            Write-Success "Service installed successfully!"
            
            # Set service to auto-start
            sc.exe config $ServiceName start= auto | Out-Null
            
            # Update description
            sc.exe description $ServiceName "$ServiceDescription" | Out-Null
            
            Write-Info "Starting service..."
            Start-Service -Name $ServiceName
            Start-Sleep -Seconds 3
            
            Get-ServiceStatus
        } else {
            Write-Err "Installation failed"
        }
    } catch {
        Write-Err "Error: $_"
        Write-Warn "Trying alternative method with NSSM..."
        
        # Try NSSM if available
        $nssm = Get-Command nssm -ErrorAction SilentlyContinue
        if ($nssm) {
            & nssm install $ServiceName $PythonExe $MainScript
            & nssm set $ServiceName DisplayName $ServiceDisplayName
            & nssm set $ServiceName Description $ServiceDescription
            & nssm set $ServiceName AppDirectory $ScriptPath
            & nssm set $ServiceName Start SERVICE_AUTO_START
            & nssm set $ServiceName AppStdout "$ScriptPath\logs\service_stdout.log"
            & nssm set $ServiceName AppStderr "$ScriptPath\logs\service_stderr.log"
            & nssm start $ServiceName
            Write-Success "Service installed with NSSM"
        } else {
            Write-Err "NSSM not found. Please install pywin32 or NSSM."
        }
    }
}

# Uninstall service
function Uninstall-SignalService {
    if (-not (Test-Admin)) {
        Write-Err "Please run as Administrator!"
        return
    }
    
    $svc = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue
    if (-not $svc) {
        Write-Warn "Service not installed"
        return
    }
    
    Write-Info "Stopping service..."
    Stop-Service -Name $ServiceName -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 2
    
    Write-Info "Removing service..."
    try {
        & $PythonExe $ServiceScript remove
    } catch {
        sc.exe delete $ServiceName | Out-Null
    }
    
    Write-Success "Service removed"
}

# Start service
function Start-SignalService {
    $svc = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue
    if (-not $svc) {
        Write-Err "Service not installed. Run with -Install first."
        return
    }
    
    if ($svc.Status -eq "Running") {
        Write-Info "Service already running"
        return
    }
    
    Write-Info "Starting service..."
    Start-Service -Name $ServiceName
    Start-Sleep -Seconds 3
    Get-ServiceStatus
}

# Stop service
function Stop-SignalService {
    $svc = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue
    if (-not $svc) {
        Write-Warn "Service not installed"
        return
    }
    
    Write-Info "Stopping service..."
    Stop-Service -Name $ServiceName -Force
    Write-Success "Service stopped"
}

# Restart service
function Restart-SignalService {
    Stop-SignalService
    Start-Sleep -Seconds 2
    Start-SignalService
}

# Main
Write-Host ""
Write-Host "========================================" -ForegroundColor Magenta
Write-Host "  AI Signal Engine Service Manager" -ForegroundColor Magenta
Write-Host "========================================" -ForegroundColor Magenta
Write-Host ""

if ($Install) {
    Install-SignalService
} elseif ($Uninstall) {
    Uninstall-SignalService
} elseif ($Start) {
    Start-SignalService
} elseif ($Stop) {
    Stop-SignalService
} elseif ($Restart) {
    Restart-SignalService
} elseif ($Status) {
    Get-ServiceStatus
} else {
    Write-Info "Usage:"
    Write-Host "  .\Manage-Service.ps1 -Install    # Install and start service"
    Write-Host "  .\Manage-Service.ps1 -Uninstall  # Remove service"
    Write-Host "  .\Manage-Service.ps1 -Start      # Start service"
    Write-Host "  .\Manage-Service.ps1 -Stop       # Stop service"
    Write-Host "  .\Manage-Service.ps1 -Restart    # Restart service"
    Write-Host "  .\Manage-Service.ps1 -Status     # Check status"
    Write-Host ""
    
    # Show current status
    Get-ServiceStatus
}

Write-Host ""
