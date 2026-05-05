# AI Scalping Service - Production Ready

## Overview

A production-ready AI-powered index options scalping service that:
- Uses **WebSocket** for real-time market data (no rate limits!)
- Runs in **PAPER mode** by default (no real money until you switch)
- Logs only **important data** (signals, trades, momentum at key moments)
- Stores everything in **SQLite** for strategy analysis

## Quick Start

### 1. Start the Service
```batch
cd ai_scalping_service
python production_service.py
```

Or use the batch file:
```batch
run_service.bat start
```

### 2. Check Status
Open browser or use curl:
- **Health**: http://localhost:4002/health
- **Status**: http://localhost:4002/status
- **Momentum**: http://localhost:4002/momentum
- **Positions**: http://localhost:4002/positions
- **Config**: http://localhost:4002/config

### 3. Monitor During Market Hours
The service automatically:
- Subscribes to NIFTY, BANKNIFTY, SENSEX, BANKEX via WebSocket
- Tracks momentum (score, velocity, consecutive ticks)
- Generates entry signals when conditions are met
- Executes paper trades (simulated)
- Logs signals and trades to SQLite

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Service info |
| `/health` | GET | Health check |
| `/status` | GET | Full status with momentum |
| `/trading-mode` | GET | Current mode (paper/production) |
| `/trading-mode` | POST | Switch mode |
| `/positions` | GET | Open positions |
| `/momentum` | GET | All instruments momentum |
| `/trades/today` | GET | Today's trades |
| `/trades/recent` | GET | Recent trades |
| `/analysis` | GET | Analysis summary for strategy improvement |
| `/signals/today` | GET | Today's signals |
| `/stats/daily` | GET | Daily statistics |
| `/config` | GET | Current configuration |
| `/exit-all` | POST | Exit all positions |

## Configuration

Located in `config/settings.py` and `production_service.py`:

```python
# Strategy parameters - TUNE THESE
MIN_MOMENTUM_FOR_ENTRY = 72.0      # Minimum momentum score
MIN_CONSECUTIVE_TICKS = 4          # Consecutive same-direction ticks
STOP_LOSS_PCT = 1.5                # Stop loss percentage
TARGET_PCT = 0.8                   # Target profit percentage
MAX_HOLDING_MINUTES = 20           # Maximum hold time
MAX_TRADES_PER_DAY = 15            # Max trades per day
MAX_POSITIONS = 3                  # Max concurrent positions

# Trading hours
MORNING: 9:20 AM - 11:30 AM
AFTERNOON: 1:30 PM - 3:15 PM
```

## Trading Mode

### Paper Mode (Default - Safe)
```json
POST /trading-mode
{"mode": "paper"}
```

### Production Mode (Real Money - DANGER!)
```json
POST /trading-mode
{
  "mode": "production",
  "confirmation": "I_UNDERSTAND_REAL_MONEY"
}
```

## Database

SQLite database at: `database/scalping_data.db`

### Tables
- **paper_trades**: All simulated trades with PnL
- **signals**: All trading signals generated
- **momentum_snapshots**: Periodic momentum state (for analysis)
- **daily_stats**: Aggregated daily performance
- **trading_mode**: Current mode setting
- **learning_insights**: AI recommendations

### Analyzing Data
Use the `/analysis` endpoint or query SQLite directly:

```python
from database.models import get_database

db = get_database()

# Get analysis summary
summary = db.get_analysis_summary()

# Get win rate by momentum range
by_momentum = db.get_win_rate_by_momentum_range()

# Get best performing instruments
instruments = db.get_best_performing_instruments()
```

## Files Structure

```
ai_scalping_service/
├── production_service.py    # Main service (FastAPI + WebSocket)
├── run_service.bat          # Windows service manager
├── test_production.py       # Test script
├── config/
│   └── settings.py          # Dhan token and config
├── database/
│   ├── models.py            # SQLite models
│   ├── __init__.py
│   └── scalping_data.db     # Database file
├── market_data/
│   ├── websocket_client.py  # WebSocket client (no rate limits!)
│   └── __init__.py
├── core/
│   ├── paper_executor.py    # Paper trade execution
│   └── strategy_analyzer.py # Strategy analysis
└── logs/
    └── scalping_YYYYMMDD.log
```

## What Gets Logged

### Important (Always Logged)
- ✅ Trade entries and exits
- ✅ Signals at generation time
- ✅ Momentum at signal moments
- ✅ PnL and trade results
- ✅ Errors and warnings

### Not Logged (To Save Space)
- ❌ Every tick (unnecessary)
- ❌ Momentum every tick (only every 50 ticks)
- ❌ Raw WebSocket data

## Daily Analysis Workflow

1. **Run during market hours** (9:15 AM - 3:30 PM IST)
2. **After market close**, use the analysis endpoint:
   ```
   GET http://localhost:4002/analysis
   ```
3. **Review**:
   - Win rate by momentum range
   - Best performing instruments
   - Optimal entry conditions
4. **Tune parameters** in `production_service.py`
5. **Repeat** next trading day

## Dhan API Configuration

Token and client ID are in `config/settings.py`:

```python
access_token = "your_dhan_token"
client_id = "your_client_id"
```

### WebSocket Details
- URL: `wss://api-feed.dhan.co?version=2&token=xxx&clientId=xxx&authType=2`
- Rate Limits: **UNLIMITED** (unlike REST which is 25/sec)
- Response: Binary format (Little Endian)
- Subscription modes: Ticker, Quote, Full

## Troubleshooting

### No Ticks Received
- Market may be closed (check time: 9:15 AM - 3:30 PM IST)
- Token may be expired (renew in Dhan console)
- Check logs: `logs/scalping_YYYYMMDD.log`

### Service Won't Start
```batch
python production_service.py
```
Check for import errors in console output.

### WebSocket Disconnects
- The client auto-reconnects with exponential backoff
- Check network connectivity
- Check Dhan status page

## Safety Notes

1. **PAPER MODE** is the default - no real money at risk
2. To switch to production, you MUST provide the confirmation string
3. All trades are logged for audit
4. Stop loss is enforced at 1.5%
5. Maximum 15 trades per day limit
6. Maximum 3 concurrent positions

---

**Service is running at**: http://localhost:4002

**Current Mode**: PAPER (Safe)
