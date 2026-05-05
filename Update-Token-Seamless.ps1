# ============================================================================
# SEAMLESS DHAN TOKEN UPDATE SCRIPT
# ============================================================================
# This script updates the Dhan API token across ALL services WITHOUT requiring:
# - Admin privileges
# - Service restarts
# 
# It works by:
# 1. Updating config files on disk (for persistence across restarts)
# 2. Calling each service's /update-token API endpoint (for hot-reload)
# ============================================================================

param(
    [Parameter(Mandatory=$false)]
    [string]$NewToken
)

$ErrorActionPreference = "Continue"
$RootPath = Split-Path -Parent $MyInvocation.MyCommand.Path
$ClientId = "1101317572"  # Your Dhan Client ID

# Service endpoints
$Services = @(
    @{ Name = "DhanHQ Backend"; Port = 8000; UpdateEndpoint = "/update-token"; ReloadEndpoint = $null; UseQueryParams = $false },
    @{ Name = "AI Options Hedger"; Port = 4003; UpdateEndpoint = "/update-token"; ReloadEndpoint = "/reload"; UseQueryParams = $false },
    @{ Name = "AI Scalping Service"; Port = 4002; UpdateEndpoint = "/update-token"; ReloadEndpoint = "/websocket/reconnect"; UseQueryParams = $true },
    @{ Name = "AI Signal Engine"; Port = 4090; UpdateEndpoint = "/api/config/token"; ReloadEndpoint = "/api/config/reload"; UseQueryParams = $false },
    @{ Name = "Elite Equity HV"; Port = 5080; UpdateEndpoint = "/api/update-token"; ReloadEndpoint = $null; UseQueryParams = $false }
)

# Config files to update
$ConfigFiles = @(
    @{ Path = "$RootPath\backend\dhan_backend.py"; Pattern = '(self\.access_token\s*=\s*")[^"]*(")|("access_token"\s*:\s*")[^"]*(")|((access_token:\s*str\s*=\s*|DHAN_ACCESS_TOKEN\s*=\s*)")[^"]*"' },
    @{ Path = "$RootPath\ai_options_hedger\dhan_config.json"; Pattern = '"access_token"\s*:\s*"[^"]*"' },
    @{ Path = "$RootPath\ai_scalping_service\config\settings.py"; Pattern = '(access_token:\s*str\s*=\s*")[^"]*"' },
    @{ Path = "$RootPath\equity_hv_service\strategy\dhan_config.py"; Pattern = '(self\.access_token\s*=\s*access_token\s+or\s+")[^"]*"' },
    @{ Path = "$RootPath\signal_engine_service\config\dhan_config.json"; Pattern = '"access_token"\s*:\s*"[^"]*"' },
    @{ Path = "$RootPath\gemini_trade_service\service_config.py"; Pattern = '(dhan_access_token:\s*str\s*=\s*")[^"]*"' }
)

function Write-Success { param($Message) Write-Host "[OK] $Message" -ForegroundColor Green }
function Write-Info { param($Message) Write-Host "[INFO] $Message" -ForegroundColor Cyan }
function Write-Warn { param($Message) Write-Host "[WARN] $Message" -ForegroundColor Yellow }
function Write-Err { param($Message) Write-Host "[ERROR] $Message" -ForegroundColor Red }

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "   SEAMLESS DHAN TOKEN UPDATE" -ForegroundColor Cyan
Write-Host "   (No Admin Required, No Restart Needed)" -ForegroundColor Gray
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

# Get token if not provided
if (-not $NewToken) {
    $NewToken = Read-Host "Enter new Dhan access token"
}

if (-not $NewToken -or $NewToken.Length -lt 50) {
    Write-Err "Invalid token. Token must be at least 50 characters."
    exit 1
}

Write-Info "Token length: $($NewToken.Length) characters"
Write-Host ""

# ============================================================================
# STEP 1: Update Running Services via API (Hot-Reload)
# ============================================================================
Write-Host "STEP 1: Updating Running Services (Hot-Reload)" -ForegroundColor Yellow
Write-Host "================================================" -ForegroundColor Yellow

$apiSuccessCount = 0
$apiErrorCount = 0

foreach ($svc in $Services) {
    Write-Host "`n[$($svc.Name) - Port $($svc.Port)]" -ForegroundColor White
    
    # Check if service is running
    try {
        $null = Invoke-RestMethod -Uri "http://localhost:$($svc.Port)/health" -Method GET -TimeoutSec 5 -ErrorAction Stop
        Write-Info "Service is running"
    } catch {
        try {
            $null = Invoke-RestMethod -Uri "http://localhost:$($svc.Port)/" -Method GET -TimeoutSec 5 -ErrorAction Stop
            Write-Info "Service is running"
        } catch {
            Write-Warn "Service not running - will use updated config on next start"
            continue
        }
    }
    
    # Update token via API
    if ($svc.UpdateEndpoint) {
        try {
            $uri = "http://localhost:$($svc.Port)$($svc.UpdateEndpoint)"
            $result = $null
            
            # Use query parameters or body based on service type
            if ($svc.UseQueryParams) {
                # For services that expect query parameters (like AI Scalping)
                # Use System.Web.HttpUtility for proper URL encoding of JWT tokens
                $encodedToken = [System.Web.HttpUtility]::UrlEncode($NewToken)
                $uri = "$uri`?access_token=$encodedToken&client_id=$ClientId"
                $result = Invoke-RestMethod -Uri $uri -Method POST -TimeoutSec 5
            } else {
                # For services that expect JSON body
                $body = @{ access_token = $NewToken; client_id = $ClientId } | ConvertTo-Json
                $result = Invoke-RestMethod -Uri $uri -Method POST -Body $body -ContentType "application/json" -TimeoutSec 5
            }
            
            if ($result.success -eq $true -or $result.status -eq $true -or $result.status -eq "success") {
                Write-Success "Token updated via API"
                $apiSuccessCount++
                
                # Trigger reload if available
                if ($svc.ReloadEndpoint) {
                    try {
                        $reloadResult = Invoke-RestMethod -Uri "http://localhost:$($svc.Port)$($svc.ReloadEndpoint)" -Method POST -TimeoutSec 10
                        if ($reloadResult.success -eq $true -or $reloadResult.status -eq "success") {
                            Write-Success "Service reloaded - reconnected with new token"
                        } else {
                            Write-Info "Reload response: $($reloadResult | ConvertTo-Json -Compress)"
                        }
                    } catch {
                        Write-Warn "Reload endpoint failed - token updated but may need manual reconnect"
                    }
                }
            } else {
                Write-Warn "API returned: $($result | ConvertTo-Json -Compress)"
            }
        } catch {
            Write-Warn "API update failed: $($_.Exception.Message)"
            $apiErrorCount++
        }
    } else {
        Write-Info "No API update endpoint - will use file update"
    }
}

# ============================================================================
# STEP 2: Update Config Files (For Persistence)
# ============================================================================
Write-Host "`n"
Write-Host "STEP 2: Updating Config Files (Persistence)" -ForegroundColor Yellow
Write-Host "============================================" -ForegroundColor Yellow

$fileSuccessCount = 0
$fileErrorCount = 0

foreach ($cfg in $ConfigFiles) {
    $fileName = Split-Path $cfg.Path -Leaf
    
    if (-not (Test-Path $cfg.Path)) {
        Write-Warn "$fileName - File not found"
        continue
    }
    
    try {
        $content = Get-Content $cfg.Path -Raw -Encoding UTF8
        $originalContent = $content
        
        # Handle JSON files
        if ($cfg.Path -like "*.json") {
            $json = $content | ConvertFrom-Json
            $json.access_token = $NewToken
            if ($json.PSObject.Properties.Name -contains 'client_id') {
                $json.client_id = $ClientId
            }
            $newContent = $json | ConvertTo-Json -Depth 10
            Set-Content -Path $cfg.Path -Value $newContent -Encoding UTF8
            Write-Success "$fileName - Updated"
            $fileSuccessCount++
        }
        # Handle Python files
        elseif ($cfg.Path -like "*.py") {
            # Try multiple patterns
            $patterns = @(
                @{ Find = '(self\.access_token\s*=\s*")[^"]*"'; Replace = "`$1$NewToken`"" },
                @{ Find = '(self\.access_token\s*=\s*access_token\s+or\s+")[^"]*"'; Replace = "`$1$NewToken`"" },
                @{ Find = '(access_token:\s*str\s*=\s*")[^"]*"'; Replace = "`$1$NewToken`"" },
                @{ Find = '(dhan_access_token:\s*str\s*=\s*")[^"]*"'; Replace = "`$1$NewToken`"" }
            )
            
            $updated = $false
            foreach ($p in $patterns) {
                if ($content -match $p.Find) {
                    $content = $content -replace $p.Find, $p.Replace
                    $updated = $true
                    break
                }
            }
            
            if ($updated -and $content -ne $originalContent) {
                # Backup
                Copy-Item $cfg.Path "$($cfg.Path).bak" -Force
                Set-Content -Path $cfg.Path -Value $content -NoNewline -Encoding UTF8
                Write-Success "$fileName - Updated"
                $fileSuccessCount++
            } elseif (-not $updated) {
                Write-Warn "$fileName - No matching pattern found"
            } else {
                Write-Info "$fileName - Already up to date"
            }
        }
    } catch {
        Write-Err "$fileName - Failed: $($_.Exception.Message)"
        $fileErrorCount++
    }
}

# ============================================================================
# SUMMARY
# ============================================================================
Write-Host "`n"
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "   UPDATE SUMMARY" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "API Hot-Reload:" -ForegroundColor White
Write-Host "  Success: $apiSuccessCount services" -ForegroundColor Green
if ($apiErrorCount -gt 0) {
    Write-Host "  Errors:  $apiErrorCount services" -ForegroundColor Red
}
Write-Host ""
Write-Host "Config Files:" -ForegroundColor White
Write-Host "  Updated: $fileSuccessCount files" -ForegroundColor Green
if ($fileErrorCount -gt 0) {
    Write-Host "  Errors:  $fileErrorCount files" -ForegroundColor Red
}
Write-Host ""

if ($apiSuccessCount -gt 0) {
    Write-Host "Token is now LIVE in running services!" -ForegroundColor Green
    Write-Host "No restart required." -ForegroundColor Gray
} else {
    Write-Host "Config files updated. Services will use new token on next restart." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan

# Verify token is working
Write-Host "`nVerifying token..." -ForegroundColor Cyan
try {
    $verify = Invoke-RestMethod -Uri "http://localhost:8000/token-status" -Method GET -TimeoutSec 5
    if ($verify.is_valid -eq $true) {
        Write-Success "Token verified working! (Client: $($verify.client_id))"
    } else {
        Write-Warn "Token may not be valid - please check manually"
    }
} catch {
    Write-Info "Could not verify - backend may need restart"
}

Write-Host ""
