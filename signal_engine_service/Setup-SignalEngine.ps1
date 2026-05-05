<#
.SYNOPSIS
    Setup Signal Engine Service with Virtual Environment
    
.DESCRIPTION
    Creates a Python virtual environment, installs dependencies,
    and prepares the Signal Engine service for production.
    
.EXAMPLE
    .\Setup-SignalEngine.ps1
    
.NOTES
    Run this script before installing the service
#>

[CmdletBinding()]
param(
    [switch]$Force,  # Force recreation of venv
    [switch]$InstallService  # Also install as Windows service
)

$ErrorActionPreference = "Stop"
$ServicePath = Split-Path -Parent $PSCommandPath
$VenvPath = Join-Path $ServicePath ".venv"
$RequirementsPath = Join-Path $ServicePath "requirements.txt"

# Color output
function Write-Success { param($Message) Write-Host "✅ $Message" -ForegroundColor Green }
function Write-Info { param($Message) Write-Host "ℹ️  $Message" -ForegroundColor Cyan }
function Write-Warn { param($Message) Write-Host "⚠️  $Message" -ForegroundColor Yellow }
function Write-Error { param($Message) Write-Host "❌ $Message" -ForegroundColor Red }

Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  SIGNAL ENGINE SERVICE SETUP" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

# Check Python
Write-Info "Checking Python installation..."
try {
    $pythonVersion = python --version 2>&1
    Write-Success "Python found: $pythonVersion"
} catch {
    Write-Error "Python not found. Please install Python 3.9+ first."
    exit 1
}

# Create/recreate virtual environment
if ((Test-Path $VenvPath) -and -not $Force) {
    Write-Info "Virtual environment already exists at: $VenvPath"
    $response = Read-Host "Recreate it? (y/N)"
    if ($response -eq 'y' -or $response -eq 'Y') {
        Write-Info "Removing existing virtual environment..."
        Remove-Item -Path $VenvPath -Recurse -Force
    }
}

if (-not (Test-Path $VenvPath)) {
    Write-Info "Creating virtual environment..."
    python -m venv $VenvPath
    Write-Success "Virtual environment created at: $VenvPath"
}

# Activate venv and install dependencies
Write-Info "Activating virtual environment..."
$activateScript = Join-Path $VenvPath "Scripts\Activate.ps1"
. $activateScript

Write-Info "Upgrading pip..."
python -m pip install --upgrade pip --quiet

Write-Info "Installing dependencies from requirements.txt..."
if (Test-Path $RequirementsPath) {
    python -m pip install -r $RequirementsPath --quiet
    Write-Success "Dependencies installed successfully"
} else {
    Write-Warn "requirements.txt not found, installing core packages..."
    python -m pip install fastapi uvicorn aiohttp websockets pandas numpy pywin32 dhanhq --quiet
    Write-Success "Core packages installed"
}

# Create necessary directories
$dirs = @("logs", "database", "config")
foreach ($dir in $dirs) {
    $dirPath = Join-Path $ServicePath $dir
    if (-not (Test-Path $dirPath)) {
        New-Item -ItemType Directory -Path $dirPath -Force | Out-Null
        Write-Info "Created directory: $dir"
    }
}

# Verify config file exists
$configPath = Join-Path $ServicePath "config\dhan_config.json"
if (-not (Test-Path $configPath)) {
    Write-Warn "Config file not found. Please create config\dhan_config.json with Dhan credentials."
}

# Show Python path for service configuration
$pythonExe = Join-Path $VenvPath "Scripts\python.exe"
Write-Info ""
Write-Info "Configuration for NSSM service:"
Write-Host "  Python Path: $pythonExe" -ForegroundColor Yellow
Write-Host "  Script Path: $(Join-Path $ServicePath 'world_class_signal_engine.py')" -ForegroundColor Yellow

# Install as Windows service if requested
if ($InstallService) {
    Write-Host ""
    Write-Info "Installing as Windows Service..."
    
    # Check for admin privileges
    $isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
    if (-not $isAdmin) {
        Write-Warn "Administrator privileges required to install service."
        Write-Info "Please run as Administrator or use: .\Manage-Service.ps1 -Install"
    } else {
        # Check for NSSM
        $nssm = Get-Command nssm -ErrorAction SilentlyContinue
        if (-not $nssm) {
            Write-Warn "NSSM not found. Installing via winget..."
            winget install --id nssm.nssm --silent
        }
        
        $serviceName = "AISignalEngineService"
        $scriptPath = Join-Path $ServicePath "world_class_signal_engine.py"
        
        # Remove existing service if present
        nssm stop $serviceName 2>$null
        nssm remove $serviceName confirm 2>$null
        
        # Install new service
        nssm install $serviceName $pythonExe $scriptPath
        nssm set $serviceName AppDirectory $ServicePath
        nssm set $serviceName DisplayName "AI Signal Engine Service"
        nssm set $serviceName Description "World-Class AI Signal Engine for NIFTY, BANKNIFTY, SENSEX"
        nssm set $serviceName Start SERVICE_AUTO_START
        nssm set $serviceName AppStdout (Join-Path $ServicePath "logs\service_stdout.log")
        nssm set $serviceName AppStderr (Join-Path $ServicePath "logs\service_stderr.log")
        
        # Start the service
        nssm start $serviceName
        Start-Sleep -Seconds 3
        
        $service = Get-Service -Name $serviceName -ErrorAction SilentlyContinue
        if ($service -and $service.Status -eq 'Running') {
            Write-Success "Service installed and running!"
        } else {
            Write-Warn "Service installed but may need manual start"
        }
    }
}

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  SETUP COMPLETE" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""
Write-Info "Next steps:"
Write-Host "  1. Verify config\dhan_config.json has correct token"
Write-Host "  2. Run: .\Manage-Service.ps1 -Install  (as Administrator)"
Write-Host "  3. Test: curl http://localhost:4090/health"
Write-Host ""
