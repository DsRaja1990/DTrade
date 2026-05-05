@echo off
setlocal enabledelayedexpansion

echo.
echo ==========================================
echo    SEAMLESS DHAN TOKEN UPDATE
echo    (No Admin Required, No Restart Needed)
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
powershell -ExecutionPolicy Bypass -Command "& { $token = Get-Content '%TEMP_TOKEN_FILE%' -Raw; $token = $token.Trim(); & '%~dp0Update-Token-Seamless.ps1' -NewToken $token }"

set "PS_EXIT_CODE=!ERRORLEVEL!"

:: Clean up temp file
if exist "!TEMP_TOKEN_FILE!" del "!TEMP_TOKEN_FILE!"

echo.
echo ==========================================
if !PS_EXIT_CODE! EQU 0 (
    echo Token update complete!
    echo.
    echo Your services should now be using the new token.
    echo NO RESTART REQUIRED.
) else (
    echo Update completed with some warnings.
    echo Check the output above for details.
)
echo ==========================================
echo.

pause
