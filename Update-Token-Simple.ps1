param(
    [Parameter(Mandatory=$true)]
    [string]$NewToken
)

$ErrorActionPreference = "Stop"
$RootPath = Split-Path -Parent $MyInvocation.MyCommand.Path

Write-Host "`n=== Dhan Token Update Script ===" -ForegroundColor Cyan
Write-Host "Root Path: $RootPath`n" -ForegroundColor Gray

$updateCount = 0
$errorCount = 0

function Update-File {
    param(
        [string]$FilePath,
        [string]$ServiceName
    )
    
    try {
        if (-not (Test-Path $FilePath)) {
            Write-Host "[ERROR] File not found: $FilePath" -ForegroundColor Red
            return $false
        }
        
        $content = Get-Content $FilePath -Raw -Encoding UTF8
        $originalContent = $content
        
        # Try multiple patterns to find and replace token
        $patterns = @(
            # Python self.access_token = access_token or "..." (equity_hv_service)
            '(self\.access_token\s*=\s*access_token\s+or\s+")[^"]*(")',
            # Python dataclass field (service_config.py)
            '(dhan_access_token:\s*str\s*=\s*")[^"]*(")',
            # Python variable assignment (dhan_backend.py)
            '(DHAN_ACCESS_TOKEN\s*=\s*")[^"]*(")',
            # Python dataclass field (settings.py)
            '(access_token:\s*str\s*=\s*")[^"]*(")',
            # JSON format - dhan_access_token
            '("dhan_access_token"\s*:\s*")[^"]*(")',
            # JSON format - access_token
            '("access_token"\s*:\s*")[^"]*(")',
            # .env format
            '(VITE_DHAN_ACCESS_TOKEN=).*',
            # .env format without quotes
            '(DHAN_ACCESS_TOKEN=).*'
        )
        
        $replaced = $false
        foreach ($pattern in $patterns) {
            if ($content -match $pattern) {
                if ($pattern -like '*VITE_DHAN_ACCESS_TOKEN*' -or $pattern -like '*DHAN_ACCESS_TOKEN=.*') {
                    # For .env format (no quotes)
                    $content = $content -replace $pattern, "`$1$NewToken"
                } else {
                    # For quoted formats
                    $content = $content -replace $pattern, "`$1$NewToken`$2"
                }
                $replaced = $true
                break
            }
        }
        
        if (-not $replaced) {
            Write-Host "[WARN] $ServiceName - No token pattern matched in file" -ForegroundColor Yellow
            return $false
        }
        
        if ($content -eq $originalContent) {
            Write-Host "[OK] $ServiceName - Token already up-to-date" -ForegroundColor Green
            return $true
        }
        
        # Backup original file
        $backupPath = "$FilePath.bak"
        Copy-Item $FilePath $backupPath -Force
        
        # Write updated content
        Set-Content -Path $FilePath -Value $content -NoNewline -Encoding UTF8
        
        Write-Host "[SUCCESS] $ServiceName - Token updated" -ForegroundColor Green
        return $true
        
    } catch {
        Write-Host "[ERROR] $ServiceName failed: $_" -ForegroundColor Red
        return $false
    }
}

# Update all service configurations
Write-Host "[1/7] AI Scalping Service..." -ForegroundColor Cyan
if (Update-File -FilePath "$RootPath\ai_scalping_service\config\settings.py" -ServiceName "AI Scalping") {
    $updateCount++
} else {
    $errorCount++
}

Write-Host "`n[2/7] AI Options Hedger Service..." -ForegroundColor Cyan
if (Update-File -FilePath "$RootPath\ai_options_hedger\dhan_config.json" -ServiceName "AI Options Hedger") {
    $updateCount++
} else {
    $errorCount++
}

Write-Host "`n[3/7] Elite Equity HV Service..." -ForegroundColor Cyan
if (Update-File -FilePath "$RootPath\equity_hv_service\strategy\dhan_config.py" -ServiceName "Elite Equity HV") {
    $updateCount++
} else {
    $errorCount++
}

Write-Host "`n[4/7] Signal Engine Service..." -ForegroundColor Cyan
if (Update-File -FilePath "$RootPath\signal_engine_service\config\dhan_config.json" -ServiceName "Signal Engine") {
    $updateCount++
} else {
    $errorCount++
}

Write-Host "`n[5/7] Gemini Trade Service..." -ForegroundColor Cyan
if (Update-File -FilePath "$RootPath\gemini_trade_service\service_config.py" -ServiceName "Gemini Trade") {
    $updateCount++
} else {
    $errorCount++
}

Write-Host "`n[6/7] Backend Service..." -ForegroundColor Cyan
if (Update-File -FilePath "$RootPath\backend\dhan_backend.py" -ServiceName "Backend") {
    $updateCount++
} else {
    $errorCount++
}

Write-Host "`n[7/7] Frontend..." -ForegroundColor Cyan
if (Update-File -FilePath "$RootPath\frontend\.env" -ServiceName "Frontend") {
    $updateCount++
} else {
    $errorCount++
}

# Summary
Write-Host "`n================================" -ForegroundColor Cyan
Write-Host "Update Summary:" -ForegroundColor White
Write-Host "  [OK] Success: $updateCount files" -ForegroundColor Green
Write-Host "  [FAIL] Errors: $errorCount files" -ForegroundColor Red
Write-Host "================================`n" -ForegroundColor Cyan

if ($updateCount -gt 0) {
    Write-Host "All tokens are up-to-date!" -ForegroundColor Green
    Write-Host "`nNext steps:" -ForegroundColor Yellow
    Write-Host "1. Restart all services for changes to take effect" -ForegroundColor Gray
    Write-Host "2. The batch file will offer to restart services automatically" -ForegroundColor Gray
    exit 0
} else {
    Write-Host "No files were updated. Please check if the files exist." -ForegroundColor Red
    exit 1
}
