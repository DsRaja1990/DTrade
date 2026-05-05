# DTrade Service Management Scripts

This document lists all the service management scripts and their purposes.

## Active Scripts (Use These)

### Token Update
- **`Update-DhanToken.bat`** - Interactive token update tool
  - Prompts for new Dhan access token
  - Updates all 7 service configuration files
  - Optionally restarts services after update
  - **Usage:** Double-click or run from command prompt

- **`Update-Token-Simple.ps1`** - PowerShell token update engine
  - Called by Update-DhanToken.bat
  - Updates tokens in all service configs
  - Creates .bak backups before updating
  - **Usage:** Called automatically by .bat file

### Service Restart
- **`Restart-All-Services.ps1`** - Restart all trading services
  - Restarts all 6 Windows services
  - Requires Administrator privileges
  - Auto-elevates if not running as admin
  - Shows status for each service
  - **Usage:** Double-click or run after token update

- **`Quick-Restart-Backend.bat`** - Quick restart of DhanHQ backend only
  - Stops and starts DhanHQ_Service only
  - Faster than restarting all services
  - **Usage:** Double-click when only backend needs restart

### Service Management
- **`Manage-All-Services.ps1`** - Advanced service control
  - Start, stop, restart, or check status of all services
  - Interactive menu-driven interface
  - **Usage:** For manual service control

## Windows Services (Installed)

| Service Name | Display Name | Port | Purpose |
|-------------|-------------|------|---------|
| `DhanHQ_Service` | DhanHQ Trading Backend | 8000 | Main API backend |
| `TradingBot_IndexScalping` | Index Scalping Strategy | 4002 | AI Scalping service |
| `TradingBot_OptionsHedger` | Options Hedger Strategy | 4003 | Options hedging |
| `EliteEquityHVService` | Elite Equity HV Service | 5080 | Equity high-volume trading |
| `TradingBot_IndexAdvanced` | Signal Engine Service | 4090 | AI signal generation |
| `TradingBot_DhanBackend` | Gemini Trade Service | 4080 | Gemini integration |

## Configuration Files Updated by Token Scripts

1. `ai_scalping_service\config\settings.py` - AI Scalping token
2. `backend\dhan_backend.py` - Main backend token
3. `ai_options_hedger\dhan_config.json` - Options hedger token
4. `equity_hv_service\strategies\high_volume_strategy.py` - Equity service token
5. `signal_engine_service\main.py` - Signal engine token
6. `gemini_trade_service\config\settings.py` - Gemini service token
7. `frontend\.env` - Frontend API token

## Workflow: Updating Dhan Token

1. Get new access token from Dhan portal
2. Run `Update-DhanToken.bat`
3. Paste the new token when prompted
4. Choose "Y" to restart all services
5. Verify in Settings UI with "Test Connection" button

## Troubleshooting

### Services won't start
- Check Windows Event Viewer for errors
- Verify token is valid and not expired
- Check service logs in respective `logs/` folders

### Token update fails
- Run PowerShell as Administrator
- Check file permissions on config files
- Verify backup files (.bak) are created

### Backend returns 401 Unauthorized
- Token has expired, update it using Update-DhanToken.bat
- Verify token was updated in backend\dhan_backend.py
- Restart DhanHQ_Service using Quick-Restart-Backend.bat

## Admin/Development Scripts (Advanced Use)

- `Admin-Setup-And-Restart.ps1` - Initial setup and service installation
- `Install-Services-Admin.ps1` - Install Windows services
- `Fix-And-Restart-All.ps1` - Fix common issues and restart

## Deprecated/Removed Scripts

The following scripts have been removed (were using incorrect service names):
- ❌ `Update-DhanToken-NEW.bat` (consolidated into Update-DhanToken.bat)
- ❌ `Update-Token-Interactive.bat` (replaced by Update-DhanToken.bat)
- ❌ Old `Update-DhanToken.ps1` (replaced by Update-Token-Simple.ps1)
- ❌ Old `Restart-All-Services.ps1` (recreated with correct service names)

---

**Last Updated:** December 13, 2025  
**Correct Backend Service:** DhanHQ_Service (DhanHQ Trading Backend)
