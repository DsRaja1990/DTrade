# Signal Engine Service Installer
# Run as Administrator

$ServiceName = "SignalEngineService"
$ServiceDisplayName = "World-Class Signal Engine Service"
$ServiceDescription = "AI-Powered Trading Signal Generator for NIFTY, BANKNIFTY, SENSEX"

$ScriptPath = $PSScriptRoot
$PythonExe = "$ScriptPath\..\\.venv\\Scripts\\python.exe"
$ServiceScript = "$ScriptPath\\world_class_signal_engine.py"

# Check if running as administrator
$currentPrincipal = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
if (-not $currentPrincipal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-Host "Please run as Administrator!" -ForegroundColor Red
    exit 1
}

# Check if service exists
$service = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue

if ($service) {
    Write-Host "Service already exists. Stopping and removing..." -ForegroundColor Yellow
    Stop-Service -Name $ServiceName -Force -ErrorAction SilentlyContinue
    sc.exe delete $ServiceName
    Start-Sleep -Seconds 2
}

# Create service using NSSM or sc.exe
Write-Host "Creating service: $ServiceDisplayName" -ForegroundColor Green

# Using nssm if available
$nssm = Get-Command nssm -ErrorAction SilentlyContinue
if ($nssm) {
    & nssm install $ServiceName $PythonExe $ServiceScript
    & nssm set $ServiceName DisplayName $ServiceDisplayName
    & nssm set $ServiceName Description $ServiceDescription
    & nssm set $ServiceName AppDirectory $ScriptPath
    & nssm set $ServiceName Start SERVICE_AUTO_START
    & nssm set $ServiceName AppStdout "$ScriptPath\\logs\\service_stdout.log"
    & nssm set $ServiceName AppStderr "$ScriptPath\\logs\\service_stderr.log"
} else {
    Write-Host "NSSM not found. Please install NSSM for proper service management." -ForegroundColor Yellow
    Write-Host "You can run the service manually with:" -ForegroundColor Cyan
    Write-Host "  python world_class_signal_engine.py" -ForegroundColor Cyan
}

Write-Host ""
Write-Host "Service installation complete!" -ForegroundColor Green
Write-Host "Port: 4090" -ForegroundColor Cyan
Write-Host ""
