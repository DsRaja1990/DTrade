@echo off
setlocal enabledelayedexpansion

echo.
echo ==========================================
echo    Dhan Token Update Tool
echo ==========================================
echo.

:: Check if token is passed as argument, otherwise prompt
if "%~1"=="" (
    set /p "NEW_TOKEN=Enter new Dhan access token: "
) else (
    set "NEW_TOKEN=%~1"
)

if "!NEW_TOKEN!"=="" (
    echo [ERROR] Token cannot be empty
    pause
    exit /b 1
)

echo.
echo Updating token across all services...
echo.

:: Create a temporary file to pass the token safely
set "TEMP_TOKEN_FILE=%TEMP%\dhan_token_%RANDOM%.tmp"
echo !NEW_TOKEN!> "!TEMP_TOKEN_FILE!"

:: Run PowerShell script with token from temp file
powershell -ExecutionPolicy Bypass -Command "& { $token = Get-Content '%TEMP_TOKEN_FILE%' -Raw; $token = $token.Trim(); & '%~dp0Update-Token-Simple.ps1' -NewToken $token }"

set "PS_EXIT_CODE=!ERRORLEVEL!"

:: Clean up temp file
if exist "!TEMP_TOKEN_FILE!" del "!TEMP_TOKEN_FILE!"

if !PS_EXIT_CODE! EQU 0 (
    echo.
    echo ==========================================
    echo Token updated successfully!
    echo ==========================================
    echo.
    echo Next step: Restart services to apply changes
    set /p "RESTART=Restart all services now? (Y/N): "
    
    if /i "!RESTART!"=="Y" (
        echo.
        echo Restarting services...
        powershell -ExecutionPolicy Bypass -File "%~dp0Restart-All-Services.ps1"
    )
) else (
    echo.
    echo [ERROR] Token update failed with exit code: !PS_EXIT_CODE!
    echo Please check the errors above.
)

echo.
pause
