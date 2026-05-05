@echo off
echo.
echo ========================================
echo   Quick Restart - DhanHQ Backend
echo ========================================
echo.
echo Restarting DhanHQ Trading Backend service...
echo.

net stop DhanHQ_Service
timeout /t 2 /nobreak >nul
net start DhanHQ_Service

echo.
echo Done! Backend service restarted.
echo.
pause
