# DTrade Production Services

## Overview

Two production trading services are available:

| Service | Port | Purpose |
|---------|------|---------|
| AI Scalping Service | 4002 | Index momentum scalping (NIFTY, BANKNIFTY, etc.) |
| AI Options Hedger | 4003 | Options hedging and stacking |

## Service Features

### Common Features
- ✅ **Paper Trading Mode** (default) - Simulates trades without real execution
- ✅ **Production Mode** - Real trade execution (requires confirmation)
- ✅ **Real-time WebSocket Data** - No rate limits via Dhan WebSocket API
- ✅ **SQLite Database** - Stores signals, trades, and analysis data
- ✅ **Isolated Virtual Environment** - `.venv` inside each service folder

---

## AI Scalping Service (Port 4002)

### Location
```
ai_scalping_service/
├── .venv/                    # Virtual environment
├── production_service.py     # Main service
├── run_service.bat           # Windows batch script
├── market_data/
│   └── websocket_client.py   # Dhan WebSocket client
├── database/
│   └── models.py             # SQLite models
└── core/
    └── paper_executor.py     # Paper trading executor
```

### Run Commands
```batch
# Using batch script
cd ai_scalping_service
run_service.bat start

# Or directly
.\.venv\Scripts\python.exe production_service.py
```

### Endpoints
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/status` | GET | Full service status |
| `/trading-mode` | GET | Current trading mode |
| `/trading-mode` | POST | Switch trading mode |
| `/momentum` | GET | Momentum analysis |
| `/positions` | GET | Open positions |
| `/trades/today` | GET | Today's trades |

---

## AI Options Hedger (Port 4003)

### Location
```
ai_options_hedger/
├── .venv/                       # Virtual environment
├── production_hedger_service.py # Main service
├── run_hedger_service.bat       # Windows batch script
├── core/
│   └── websocket_client.py      # Dhan WebSocket client
├── database/
│   ├── options_db_manager.py    # Options database
│   └── paper_trading_db.py      # Paper trading extensions
└── dhan_config.json             # Dhan API credentials
```

### Run Commands
```batch
# Using batch script
cd ai_options_hedger
run_hedger_service.bat start

# Or directly
.\.venv\Scripts\python.exe production_hedger_service.py
```

### Endpoints
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/status` | GET | Full service status |
| `/trading-mode` | GET | Current trading mode |
| `/trading-mode` | POST | Switch trading mode |
| `/signals` | GET | Current AI signals |
| `/analysis` | GET | Options analysis |
| `/positions` | GET | Open positions |
| `/trades/today` | GET | Today's trades |
| `/history` | GET | Trade history |

---

## Trading Modes

### Paper Mode (Default)
- Trades are simulated
- No real money involved
- All signals and trades logged to database
- Use for testing and evaluation

### Production Mode
Requires confirmation to enable:
```powershell
# PowerShell
$body = @{mode="production"; confirmation="I_UNDERSTAND_REAL_MONEY"} | ConvertTo-Json
Invoke-RestMethod -Uri "http://localhost:4003/trading-mode" -Method POST -Body $body -ContentType "application/json"
```

### Switch Back to Paper Mode
```powershell
$body = @{mode="paper"} | ConvertTo-Json
Invoke-RestMethod -Uri "http://localhost:4003/trading-mode" -Method POST -Body $body -ContentType "application/json"
```

---

## Database Schema

### AI Scalping Service Database (`ai_scalping_service/data/scalping_production.db`)
- `trades` - All executed trades
- `signals` - AI-generated signals
- `momentum_snapshots` - Momentum analysis data
- `daily_stats` - Daily performance statistics
- `learning_insights` - ML learning data

### AI Options Hedger Database (`ai_options_hedger/data/paper_trading.db`)
- `options_signals` - Options trading signals
- `options_trades` - Trade records
- `stacking_events` - Position stacking events
- `daily_performance` - Daily P&L metrics
- `open_positions` - Current positions
- `trading_mode` - Current mode settings

---

## WebSocket Configuration

Both services use Dhan WebSocket API for real-time data:
- **URL**: `wss://api-feed.dhan.co?version=2&token={token}&clientId={clientId}&authType=2`
- **Mode**: QUOTE (LTP, volume, OI updates)
- **No Rate Limits**: WebSocket subscription has no rate limits

### Instruments Tracked
| Instrument | Lot Size |
|------------|----------|
| NIFTY | 75 |
| BANKNIFTY | 35 |
| SENSEX | 20 |
| BANKEX | 30 |
| FINNIFTY | 65 |

---

## Trading Windows

| Session | Time (IST) |
|---------|------------|
| Morning | 9:20 AM - 11:30 AM |
| Afternoon | 1:30 PM - 3:15 PM |

---

## Quick Status Check

```powershell
# Check both services
Write-Host "Scalping Service:"; Invoke-RestMethod -Uri "http://localhost:4002/health"
Write-Host "Options Hedger:"; Invoke-RestMethod -Uri "http://localhost:4003/health"
```

---

## Logs Location

| Service | Log Path |
|---------|----------|
| AI Scalping | `ai_scalping_service/logs/` |
| AI Options Hedger | `ai_options_hedger/logs/` |

---

## Windows Service Installation

Both services can run as Windows services using NSSM or the provided batch scripts.

### Using Batch Scripts
```batch
# AI Scalping Service
cd ai_scalping_service
run_service.bat

# AI Options Hedger
cd ai_options_hedger  
run_hedger_service.bat
```

### Available Commands
- `start` - Start the service
- `stop` - Stop the service
- `restart` - Restart the service
- `status` - Check service status
- `logs` - View live logs

---

## Dhan API Configuration

Configuration file: `ai_options_hedger/dhan_config.json`
```json
{
    "access_token": "YOUR_TOKEN",
    "client_id": "YOUR_CLIENT_ID"
}
```

**Token Expiry**: Check the JWT expiry in the token payload.

---

## Data Logged for Analysis

### Critical Data (Always Logged)
- AI signals with confidence scores
- Trade entries and exits
- Position changes
- Error conditions

### Analysis Data
- Daily performance metrics
- Win/loss ratios
- Trend predictions vs actual
- Signal accuracy

---

## Support

For issues:
1. Check service health: `http://localhost:{port}/health`
2. Check logs in `logs/` folder
3. Verify WebSocket connection in status
