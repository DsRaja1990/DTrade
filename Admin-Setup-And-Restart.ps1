<#
.SYNOPSIS
    Administrator Setup & Restart Script for All AI Trading Services
    
.DESCRIPTION
    This script requires Administrator privileges and performs:
    1. Creates/updates Signal Engine virtual environment
    2. Restarts all AI trading services
    3. Tests all service endpoints
    4. Enables evaluation mode (optional)
    
.PARAMETER SetupSignalEngine
    Setup Signal Engine venv and reinstall service
    
.PARAMETER EnableEvaluation
    Enable evaluation mode on all services after restart

.EXAMPLE
    .\Admin-Setup-And-Restart.ps1
    .\Admin-Setup-And-Restart.ps1 -SetupSignalEngine
    .\Admin-Setup-And-Restart.ps1 -EnableEvaluation
    
.NOTES
    Must be run as Administrator
#>

[CmdletBinding()]
param(
    [switch]$SetupSignalEngine,
    [switch]$EnableEvaluation
)

$ErrorActionPreference = "Continue"

# ============================================================================
#                     CHECK ADMINISTRATOR
# ============================================================================

$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $isAdmin) {
    Write-Host "⚠️  Administrator privileges required!" -ForegroundColor Yellow
    Write-Host "Relaunching as Administrator..." -ForegroundColor Cyan
    
    $arguments = "-NoProfile -ExecutionPolicy Bypass -File `"$PSCommandPath`""
    if ($SetupSignalEngine) { $arguments += " -SetupSignalEngine" }
    if ($EnableEvaluation) { $arguments += " -EnableEvaluation" }
    
    Start-Process PowerShell -Verb RunAs -ArgumentList $arguments
    exit
}

# ============================================================================
#                     PATHS & CONFIGURATION
# ============================================================================

$RootPath = Split-Path -Parent $PSCommandPath
$SignalEnginePath = Join-Path $RootPath "signal_engine_service"
$SignalEngineVenv = Join-Path $SignalEnginePath ".venv"

# Color functions
function Write-Success { param($Message) Write-Host "✅ $Message" -ForegroundColor Green }
function Write-Info { param($Message) Write-Host "ℹ️  $Message" -ForegroundColor Cyan }
function Write-Warn { param($Message) Write-Host "⚠️  $Message" -ForegroundColor Yellow }
function Write-Err { param($Message) Write-Host "❌ $Message" -ForegroundColor Red }

Write-Host ""
Write-Host "╔════════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║     AI TRADING SERVICES - ADMIN SETUP & RESTART SCRIPT        ║" -ForegroundColor Cyan
Write-Host "╚════════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

# ============================================================================
#                     SETUP SIGNAL ENGINE VENV
# ============================================================================

if ($SetupSignalEngine -or -not (Test-Path $SignalEngineVenv)) {
    Write-Host "═══════════════════════════════════════════════════════════════" -ForegroundColor Yellow
    Write-Host "  STEP 1: Setting up Signal Engine Virtual Environment" -ForegroundColor Yellow
    Write-Host "═══════════════════════════════════════════════════════════════" -ForegroundColor Yellow
    Write-Host ""
    
    # Check Python
    try {
        $pythonVersion = python --version 2>&1
        Write-Info "Python found: $pythonVersion"
    } catch {
        Write-Err "Python not found. Please install Python 3.9+"
        exit 1
    }
    
    # Create venv
    if (-not (Test-Path $SignalEngineVenv)) {
        Write-Info "Creating virtual environment..."
        Push-Location $SignalEnginePath
        python -m venv .venv
        Pop-Location
        Write-Success "Virtual environment created"
    } else {
        Write-Info "Virtual environment already exists"
    }
    
    # Install dependencies
    Write-Info "Installing dependencies..."
    $pip = Join-Path $SignalEngineVenv "Scripts\pip.exe"
    $requirements = Join-Path $SignalEnginePath "requirements.txt"
    
    & $pip install --upgrade pip --quiet 2>$null
    & $pip install -r $requirements --quiet 2>$null
    Write-Success "Dependencies installed"
    
    # Create directories
    $dirs = @("logs", "database", "config")
    foreach ($dir in $dirs) {
        $dirPath = Join-Path $SignalEnginePath $dir
        if (-not (Test-Path $dirPath)) {
            New-Item -ItemType Directory -Path $dirPath -Force | Out-Null
            Write-Info "Created directory: $dir"
        }
    }
    
    # Reinstall service with new venv
    Write-Info "Reinstalling AISignalEngineService with new venv..."
    
    $pythonExe = Join-Path $SignalEngineVenv "Scripts\python.exe"
    $scriptPath = Join-Path $SignalEnginePath "world_class_signal_engine.py"
    $serviceName = "AISignalEngineService"
    
    # Check for NSSM
    $nssm = Get-Command nssm -ErrorAction SilentlyContinue
    if (-not $nssm) {
        Write-Warn "NSSM not found. Installing via winget..."
        winget install --id nssm.nssm --silent --accept-source-agreements 2>$null
        # Refresh PATH
        $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
    }
    
    # Stop and remove existing service
    nssm stop $serviceName 2>$null
    Start-Sleep -Seconds 2
    nssm remove $serviceName confirm 2>$null
    Start-Sleep -Seconds 1
    
    # Install service with venv Python
    nssm install $serviceName $pythonExe $scriptPath
    nssm set $serviceName AppDirectory $SignalEnginePath
    nssm set $serviceName DisplayName "AI Signal Engine Service"
    nssm set $serviceName Description "World-Class AI Signal Engine for NIFTY, BANKNIFTY, SENSEX - Port 4090"
    nssm set $serviceName Start SERVICE_AUTO_START
    nssm set $serviceName AppStdout (Join-Path $SignalEnginePath "logs\service_stdout.log")
    nssm set $serviceName AppStderr (Join-Path $SignalEnginePath "logs\service_stderr.log")
    nssm set $serviceName AppRotateFiles 1
    nssm set $serviceName AppRotateBytes 10485760
    
    Write-Success "AISignalEngineService reinstalled with venv Python"
    Write-Host ""
}

# ============================================================================
#                     RESTART ALL SERVICES
# ============================================================================

Write-Host "═══════════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  STEP 2: Restarting All AI Trading Services" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$services = @(
    @{Name="DhanHQ_Service"; Port=8000; Desc="Dhan Backend"},
    @{Name="AIScalpingService"; Port=4002; Desc="AI Scalping"},
    @{Name="AIOptionsHedger"; Port=4003; Desc="AI Options Hedger"},
    @{Name="AISignalEngineService"; Port=4090; Desc="Signal Engine"},
    @{Name="EliteEquityHVService"; Port=5080; Desc="Elite Equity HV"},
    @{Name="GeminiTradeService"; Port=4080; Desc="Gemini Trade"}
)

foreach ($svc in $services) {
    $service = Get-Service -Name $svc.Name -ErrorAction SilentlyContinue
    if ($service) {
        Write-Info "Restarting $($svc.Desc) ($($svc.Name))..."
        
        if ($service.Status -eq 'Running') {
            Stop-Service -Name $svc.Name -Force -ErrorAction SilentlyContinue
            Start-Sleep -Seconds 2
        }
        
        Start-Service -Name $svc.Name -ErrorAction SilentlyContinue
        Start-Sleep -Seconds 2
        
        $service = Get-Service -Name $svc.Name
        if ($service.Status -eq 'Running') {
            Write-Success "$($svc.Desc) restarted - Port $($svc.Port)"
        } else {
            Write-Warn "$($svc.Desc) status: $($service.Status)"
        }
    } else {
        Write-Warn "Service not found: $($svc.Name)"
    }
}

Write-Host ""

# ============================================================================
#                     TEST SERVICE HEALTH
# ============================================================================

Write-Host "═══════════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  STEP 3: Testing Service Health" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

Start-Sleep -Seconds 5  # Wait for services to fully start

foreach ($svc in $services) {
    $url = "http://localhost:$($svc.Port)/health"
    try {
        $response = Invoke-RestMethod -Uri $url -TimeoutSec 10 -ErrorAction Stop
        Write-Success "$($svc.Desc) (Port $($svc.Port)): $($response.status)"
    } catch {
        Write-Warn "$($svc.Desc) (Port $($svc.Port)): Not responding"
    }
}

Write-Host ""

# ============================================================================
#                     TEST EVALUATION ENDPOINTS
# ============================================================================

Write-Host "═══════════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  STEP 4: Testing Evaluation Endpoints" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$evalServices = @(
    @{Name="AI Scalping"; Port=4002},
    @{Name="AI Options Hedger"; Port=4003},
    @{Name="Signal Engine"; Port=4090}
)

foreach ($svc in $evalServices) {
    $url = "http://localhost:$($svc.Port)/evaluation/status"
    try {
        $response = Invoke-RestMethod -Uri $url -TimeoutSec 5 -ErrorAction Stop
        $mode = $response.mode
        if (-not $mode) { $mode = "unknown" }
        Write-Success "$($svc.Name): Evaluation mode = $mode"
    } catch {
        Write-Warn "$($svc.Name): Evaluation endpoint not available"
    }
}

Write-Host ""

# ============================================================================
#                     ENABLE EVALUATION MODE (Optional)
# ============================================================================

if ($EnableEvaluation) {
    Write-Host "═══════════════════════════════════════════════════════════════" -ForegroundColor Yellow
    Write-Host "  STEP 5: Enabling Evaluation Mode" -ForegroundColor Yellow
    Write-Host "═══════════════════════════════════════════════════════════════" -ForegroundColor Yellow
    Write-Host ""
    
    foreach ($svc in $evalServices) {
        $url = "http://localhost:$($svc.Port)/evaluation/enable"
        try {
            $response = Invoke-RestMethod -Uri $url -Method POST -TimeoutSec 10 -ErrorAction Stop
            Write-Success "$($svc.Name): Evaluation mode ENABLED"
        } catch {
            Write-Warn "$($svc.Name): Failed to enable evaluation mode"
        }
    }
    
    Write-Host ""
}

# ============================================================================
#                     SUMMARY
# ============================================================================

Write-Host "╔════════════════════════════════════════════════════════════════╗" -ForegroundColor Green
Write-Host "║                    SETUP COMPLETE                              ║" -ForegroundColor Green
Write-Host "╚════════════════════════════════════════════════════════════════╝" -ForegroundColor Green
Write-Host ""
Write-Host "Service Status Summary:" -ForegroundColor Cyan
Get-Service -Name @("DhanHQ_Service", "AIScalpingService", "AIOptionsHedger", "AISignalEngineService", "EliteEquityHVService", "GeminiTradeService") -ErrorAction SilentlyContinue | Format-Table Name, Status, StartType -AutoSize

Write-Host ""
Write-Host "Quick Test Commands:" -ForegroundColor Cyan
Write-Host "  curl http://localhost:4090/health             # Signal Engine"
Write-Host "  curl http://localhost:4090/api/signals        # Get signals"
Write-Host "  curl http://localhost:4090/api/config/token   # Check token status"
Write-Host ""

Read-Host "Press Enter to exit"
