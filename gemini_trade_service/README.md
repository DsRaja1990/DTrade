# Gemini Trade Service

Google AI (Gemini) powered trade signal analysis service with 3-tier validation system.

## Quick Start

### 1. Setup Virtual Environment (First Time Only)

```powershell
# Create virtual environment
python -m venv venv

# Install dependencies
.\venv\Scripts\pip install -r requirements.txt
```

### 2. Manage Service

Run `manage_service.bat` for all service operations:

```cmd
manage_service.bat
```

**Menu Options:**
- **[1] Install/Reinstall Service** - Install service (requires Admin)
- **[2] Uninstall Service** - Remove service (requires Admin)
- **[3] Start Service** - Start the service
- **[4] Stop Service** - Stop the service
- **[5] Restart Service** - Restart the service
- **[6] Check Status** - View service status
- **[7] View Standard Output Log** - View stdout log
- **[8] View Error Log** - View stderr log
- **[9] Clear Logs** - Delete log files
- **[0] Open Logs Folder** - Open logs directory
- **[T] Test API Health** - Test API endpoint
- **[L] Run Service Locally** - Run for testing (not as service)
- **[X] Exit**

### 3. Verify Service

```powershell
# Check service status
sc query GeminiTradeService

# Test API
curl http://localhost:4080/health
```

## Service Configuration

- **Service Name**: GeminiTradeService
- **Port**: 4080
- **Python**: `venv\Scripts\python.exe` (virtual environment)
- **Startup**: Automatic (Delayed)
- **Logs**: `logs\gemini_service_stdout.log` and `logs\gemini_service_stderr.log`

## API Endpoints

- `GET /health` - Health check
- `GET /config/status` - Configuration status
- `POST /config/update` - Update API keys/tokens
- `POST /config/reload` - Reload configuration

## Configuration

Edit `service_config.json` to update:
- Dhan API credentials
- Gemini API keys (Tier 1/2 and Tier 3)
- Service settings

## Files

- `manage_service.bat` - **Main service manager** (use this for all operations)
- `main.py` - Service entry point
- `service_config.py` - Configuration management
- `service_config.json` - Configuration file
- `dhan_client.py` - Dhan API client
- `requirements.txt` - Python dependencies
- `venv/` - Virtual environment (isolated dependencies)
- `logs/` - Service logs

## Troubleshooting

1. **Service won't start**: Check `logs\gemini_service_stderr.log`
2. **Import errors**: Reinstall venv dependencies
3. **Access denied**: Run `manage_service.bat` as Administrator for install/uninstall
4. **Port conflict**: Change PORT in service configuration

## Requirements

- Python 3.14+
- NSSM (Non-Sucking Service Manager)
- Windows OS
