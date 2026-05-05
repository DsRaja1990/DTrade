# DhanHQ Backend Service Installation Script
# Run this script as Administrator

param(
    [switch]$Uninstall,
    [switch]$Reinstall
)

$ErrorActionPreference = "Stop"

# Configuration
$ServiceName = "DhanHQ_Service"
$ServiceDisplayName = "DhanHQ Trading Backend Service"
$ServiceDescription = "DTrade AI Trading Platform Backend - Provides Dhan API integration, portfolio management, and trading services"
$BackendPath = "C:\Users\Dhanasimmaraja\Documents\TradeApp\DTrade\backend"
$VenvPath = "C:\Users\Dhanasimmaraja\Documents\TradeApp\DTrade\.venv"
$PythonExe = "$VenvPath\Scripts\python.exe"
$MainScript = "$BackendPath\dhan_backend.py"
$LogPath = "$BackendPath\logs"
$Port = 8000

# NSSM path
$NSSMPath = "C:\nssm\nssm.exe"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "DhanHQ Backend Service Installer" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check if running as Administrator
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "ERROR: This script must be run as Administrator!" -ForegroundColor Red
    Write-Host "Please right-click PowerShell and select 'Run as Administrator'" -ForegroundColor Yellow
    exit 1
}

# Check if NSSM exists
if (-not (Test-Path $NSSMPath)) {
    Write-Host "NSSM not found at $NSSMPath" -ForegroundColor Yellow
    Write-Host "Downloading NSSM..." -ForegroundColor Cyan
    
    # Create nssm directory
    if (-not (Test-Path "C:\nssm")) {
        New-Item -ItemType Directory -Path "C:\nssm" -Force | Out-Null
    }
    
    # Download NSSM
    $nssmUrl = "https://nssm.cc/release/nssm-2.24.zip"
    $zipPath = "$env:TEMP\nssm.zip"
    
    try {
        Invoke-WebRequest -Uri $nssmUrl -OutFile $zipPath -UseBasicParsing
        Expand-Archive -Path $zipPath -DestinationPath "$env:TEMP\nssm" -Force
        Copy-Item "$env:TEMP\nssm\nssm-2.24\win64\nssm.exe" -Destination $NSSMPath -Force
        Remove-Item $zipPath -Force
        Remove-Item "$env:TEMP\nssm" -Recurse -Force
        Write-Host "NSSM downloaded and installed successfully" -ForegroundColor Green
    } catch {
        Write-Host "Failed to download NSSM. Please download manually from https://nssm.cc/download" -ForegroundColor Red
        Write-Host "Extract nssm.exe to C:\nssm\nssm.exe" -ForegroundColor Yellow
        exit 1
    }
}

# Verify paths exist
if (-not (Test-Path $PythonExe)) {
    Write-Host "ERROR: Python executable not found at $PythonExe" -ForegroundColor Red
    exit 1
}

if (-not (Test-Path $MainScript)) {
    Write-Host "ERROR: Main script not found at $MainScript" -ForegroundColor Red
    exit 1
}

# Create logs directory
if (-not (Test-Path $LogPath)) {
    New-Item -ItemType Directory -Path $LogPath -Force | Out-Null
    Write-Host "Created logs directory: $LogPath" -ForegroundColor Green
}

# Uninstall existing service if requested
if ($Uninstall -or $Reinstall) {
    Write-Host "Checking for existing service..." -ForegroundColor Cyan
    
    $existingService = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue
    if ($existingService) {
        Write-Host "Stopping service..." -ForegroundColor Yellow
        & $NSSMPath stop $ServiceName 2>$null
        Start-Sleep -Seconds 2
        
        Write-Host "Removing service..." -ForegroundColor Yellow
        & $NSSMPath remove $ServiceName confirm
        Start-Sleep -Seconds 2
        Write-Host "Service removed successfully" -ForegroundColor Green
    } else {
        Write-Host "No existing service found" -ForegroundColor Gray
    }
    
    if ($Uninstall) {
        Write-Host "Uninstall complete!" -ForegroundColor Green
        exit 0
    }
}

# Install the service
Write-Host ""
Write-Host "Installing $ServiceName..." -ForegroundColor Cyan

# Install service using NSSM
& $NSSMPath install $ServiceName $PythonExe

# Configure service parameters
& $NSSMPath set $ServiceName AppParameters "-m uvicorn main:app --host 0.0.0.0 --port $Port"
& $NSSMPath set $ServiceName AppDirectory $BackendPath
& $NSSMPath set $ServiceName DisplayName $ServiceDisplayName
& $NSSMPath set $ServiceName Description $ServiceDescription

# Set environment variables for the service
& $NSSMPath set $ServiceName AppEnvironmentExtra "PYTHONPATH=$BackendPath"

# Configure logging
& $NSSMPath set $ServiceName AppStdout "$LogPath\dhanhq_service_stdout.log"
& $NSSMPath set $ServiceName AppStderr "$LogPath\dhanhq_service_stderr.log"
& $NSSMPath set $ServiceName AppStdoutCreationDisposition 4
& $NSSMPath set $ServiceName AppStderrCreationDisposition 4
& $NSSMPath set $ServiceName AppRotateFiles 1
& $NSSMPath set $ServiceName AppRotateOnline 1
& $NSSMPath set $ServiceName AppRotateBytes 10485760

# Configure restart behavior
& $NSSMPath set $ServiceName AppRestartDelay 5000
& $NSSMPath set $ServiceName AppThrottle 5000

# Set service to start automatically
& $NSSMPath set $ServiceName Start SERVICE_AUTO_START

Write-Host "Service installed successfully!" -ForegroundColor Green
Write-Host ""

# Start the service
Write-Host "Starting $ServiceName..." -ForegroundColor Cyan
& $NSSMPath start $ServiceName

Start-Sleep -Seconds 3

# Check service status
$service = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue
if ($service) {
    if ($service.Status -eq 'Running') {
        Write-Host ""
        Write-Host "========================================" -ForegroundColor Green
        Write-Host "Service is RUNNING!" -ForegroundColor Green
        Write-Host "========================================" -ForegroundColor Green
        Write-Host ""
        Write-Host "Service Details:" -ForegroundColor Cyan
        Write-Host "  Name: $ServiceName"
        Write-Host "  Display Name: $ServiceDisplayName"
        Write-Host "  Status: $($service.Status)"
        Write-Host "  API URL: http://localhost:$Port"
        Write-Host "  Docs: http://localhost:$Port/docs"
        Write-Host "  Health: http://localhost:$Port/health"
        Write-Host ""
        Write-Host "Management Commands:" -ForegroundColor Yellow
        Write-Host "  Start:   nssm start $ServiceName"
        Write-Host "  Stop:    nssm stop $ServiceName"
        Write-Host "  Restart: nssm restart $ServiceName"
        Write-Host "  Status:  Get-Service $ServiceName"
        Write-Host ""
        
        # Test the health endpoint
        Write-Host "Testing health endpoint..." -ForegroundColor Cyan
        Start-Sleep -Seconds 2
        try {
            $health = Invoke-RestMethod -Uri "http://localhost:$Port/health" -TimeoutSec 10
            Write-Host "Health check passed!" -ForegroundColor Green
            Write-Host "  Status: $($health.status)" -ForegroundColor Gray
        } catch {
            Write-Host "Health check pending... Service may still be starting" -ForegroundColor Yellow
        }
    } else {
        Write-Host "Service installed but not running. Status: $($service.Status)" -ForegroundColor Yellow
        Write-Host "Check logs at: $LogPath" -ForegroundColor Yellow
    }
} else {
    Write-Host "ERROR: Service installation may have failed" -ForegroundColor Red
}

Write-Host ""
Write-Host "Installation complete!" -ForegroundColor Green
