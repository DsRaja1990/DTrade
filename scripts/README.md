# DTrade Universal Service Launcher

A comprehensive service management system for the DTrade application that provides unified startup, monitoring, and management of all microservices.

## Overview

The DTrade Universal Service Launcher consists of three main components:

1. **Python Launcher** (`scripts/dtrade_launcher.py`) - Core service management engine
2. **Windows Batch File** (`start_dtrade.bat`) - Simple command-line interface
3. **PowerShell Script** (`start_dtrade.ps1`) - Advanced Windows interface with better features

## Services Managed

| Service | Port | Category | Description |
|---------|------|----------|-------------|
| React Frontend | 5173 | ui | Main user interface |
| DTrade Backend | 8000 | core | API server and core services |
| Index Scalping Service | 8003 | strategy | Index scalping trading strategy |
| QSBP Service | 8001 | strategy | Quantum Scalping Binary Predictor |
| Signal Engine | 8002 | engine | Revolutionary signal generation |
| Ratio Service | 8004 | strategy | Ratio-based trading strategies |

## Quick Start

### Option 1: Windows Batch File (Simplest)
```cmd
# Double-click start_dtrade.bat or run from command line
start_dtrade.bat
```

### Option 2: PowerShell Script (Recommended)
```powershell
# Start all services
.\start_dtrade.ps1

# Start specific categories
.\start_dtrade.ps1 -Categories core,ui

# Interactive mode
.\start_dtrade.ps1 -Interactive

# Show service status
.\start_dtrade.ps1 -Status
```

### Option 3: Python Script (Direct)
```bash
# Start all services
python scripts/dtrade_launcher.py

# Start specific categories
python scripts/dtrade_launcher.py --categories core ui

# Interactive mode
python scripts/dtrade_launcher.py --interactive
```

## Usage Modes

### 1. Start All Services
Launches all enabled services in the correct order:
- Backend services first (core, engine)
- Strategy services next
- Frontend last

### 2. Category-Based Launch
Start only services from specific categories:
- **core**: Backend API and essential services
- **ui**: Frontend React application
- **strategy**: Trading strategy services
- **engine**: Signal generation and processing

### 3. Interactive Mode
Provides a real-time command interface for:
- Starting/stopping individual services
- Checking service health
- Restarting failed services
- Viewing logs and status

### 4. Status Monitoring
Real-time monitoring of:
- Service health checks
- Port availability
- Process status
- Response times

## Command Line Options

### Python Launcher Options
```bash
python scripts/dtrade_launcher.py [OPTIONS]

Options:
  --categories TEXT     Service categories to start (core, ui, strategy, engine)
  --exclude TEXT        Services to exclude
  --interactive         Start in interactive mode
  --no-monitor         Don't monitor services after startup
  --status             Show current service status
  --help               Show help message
```

### PowerShell Script Options
```powershell
.\start_dtrade.ps1 [OPTIONS]

Parameters:
  -Categories STRING[]  Service categories to start
  -Exclude STRING[]     Services to exclude
  -Interactive          Start in interactive mode
  -NoMonitor           Don't monitor services
  -Status              Show service status
  -Help                Show help information
```

## Service Configuration

Services are configured in the Python launcher with the following properties:

```python
{
    "service_name": {
        "name": "Display Name",
        "command": ["python", "service_script.py"],
        "port": 8000,
        "health_endpoint": "/health",
        "category": "core|ui|strategy|engine",
        "startup_delay": 2,
        "enabled": True,
        "dependencies": ["other_service"]
    }
}
```

## Health Monitoring

The launcher includes comprehensive health monitoring:

### Health Check Endpoints
- **Backend**: `http://localhost:8000/health`
- **Index Scalping**: `http://localhost:8003/status`
- **QSBP Service**: `http://localhost:8001/health`
- **Signal Engine**: `http://localhost:8002/health`
- **Ratio Service**: `http://localhost:8004/health`
- **Frontend**: `http://localhost:5173` (availability check)

### Status Indicators
- ✅ **Running & Healthy**: Service is active and responding
- 🟡 **Port in Use**: Port is occupied but health check fails
- ❌ **Not Running**: Service is not active
- 🔄 **Starting**: Service is in startup process
- ⚠️ **Unhealthy**: Service running but health check fails

## Interactive Commands

When running in interactive mode, available commands:

| Command | Description |
|---------|-------------|
| `status` | Show all service status |
| `start <service>` | Start specific service |
| `stop <service>` | Stop specific service |
| `restart <service>` | Restart specific service |
| `logs <service>` | Show service logs |
| `health` | Run health checks |
| `list` | List all services |
| `quit` / `exit` | Exit interactive mode |

## Error Handling

The launcher includes robust error handling:

### Common Issues and Solutions

1. **Port Already in Use**
   - Automatically detects port conflicts
   - Suggests alternative actions
   - Can kill existing processes if needed

2. **Missing Dependencies**
   - PowerShell script auto-installs missing Python modules
   - Provides clear dependency installation instructions

3. **Service Startup Failures**
   - Detailed error logging
   - Automatic retry mechanisms
   - Service-specific troubleshooting tips

4. **Python Path Issues**
   - Automatic Python detection
   - Clear error messages for missing Python

## Logging

All services are logged to the `logs/` directory:

```
logs/
├── dtrade_launcher.log      # Main launcher log
├── backend.log              # Backend service log
├── frontend.log             # Frontend service log
├── index_scalping.log       # Index scalping service log
├── qsbp_service.log         # QSBP service log
├── signal_engine.log        # Signal engine log
└── ratio_service.log        # Ratio service log
```

## Requirements

### System Requirements
- Windows 10/11 (for .bat and .ps1 scripts)
- Python 3.8 or higher
- PowerShell 5.1 or higher (for .ps1 script)

### Python Dependencies
```
requests>=2.25.0
fastapi>=0.68.0
uvicorn>=0.15.0
psutil>=5.8.0
```

Install dependencies:
```bash
pip install -r requirements.txt
```

## Advanced Configuration

### Custom Service Addition

To add a new service, edit the `SERVICES` configuration in `scripts/dtrade_launcher.py`:

```python
"new_service": {
    "name": "New Service",
    "command": ["python", "new_service.py"],
    "port": 8005,
    "health_endpoint": "/health",
    "category": "strategy",
    "startup_delay": 3,
    "enabled": True,
    "dependencies": ["backend"]
}
```

### Environment Variables

Set environment variables for service configuration:

```bash
# Development mode
set DTRADE_ENV=development

# Debug logging
set DTRADE_DEBUG=true

# Custom ports
set DTRADE_BACKEND_PORT=8000
set DTRADE_FRONTEND_PORT=5173
```

## Troubleshooting

### Service Won't Start
1. Check if port is already in use
2. Verify Python dependencies are installed
3. Check service logs in `logs/` directory
4. Run health check manually

### Permission Issues (PowerShell)
```powershell
# Set execution policy
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### Python Not Found
1. Install Python 3.8+
2. Add Python to PATH
3. Verify with: `python --version`

### Port Conflicts
1. Use `netstat -ano | findstr :PORT` to find process
2. Kill process: `taskkill /PID <PID> /F`
3. Or use different ports in service configuration

## Contributing

To extend the launcher system:

1. Add new services to the configuration
2. Implement health check endpoints in services
3. Update documentation
4. Test with all launch modes

## Support

For issues and questions:

1. Check service logs in `logs/` directory
2. Run status check: `.\start_dtrade.ps1 -Status`
3. Use interactive mode for debugging
4. Verify all dependencies are installed

---

## Quick Reference

### Start Everything
```bash
start_dtrade.bat
# or
.\start_dtrade.ps1
# or
python scripts/dtrade_launcher.py
```

### Start Core Only
```bash
.\start_dtrade.ps1 -Categories core,ui
```

### Check Status
```bash
.\start_dtrade.ps1 -Status
```

### Interactive Mode
```bash
.\start_dtrade.ps1 -Interactive
```

This launcher system provides a professional, scalable solution for managing all DTrade services with comprehensive monitoring, error handling, and user-friendly interfaces.
