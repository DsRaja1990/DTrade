# Persistent Strategy State Management

## Overview

The trading system now supports **persistent strategy state management**. This allows you to control whether strategies actively trade while keeping Windows services running 24/7.

## Key Features

### 🎯 Default Active State
- All strategies are **ENABLED by default** when services start
- Ready to trade immediately without manual intervention
- Ideal for individual traders who want strategies always active

### 🔄 Persistent Toggle
- Toggle strategies ON/OFF from the frontend
- State persists across service restarts
- Windows services stay running regardless of strategy state
- No need to restart services when toggling

### 💾 State Storage

**AI Scalping & AI Options Hedger:**
- State stored in SQLite database: `service_state` table
- Key: `strategy_enabled`
- Value: `'1'` (enabled) or `'0'` (disabled)

**Elite Equity HV:**
- State stored in JSON file: `data/equity_strategy_state.json`
- Format: `{"strategy_enabled": true/false}`

## How It Works

### Architecture

```
┌─────────────────────────────────────────┐
│     Windows Service (Always Running)    │
│  ┌───────────────────────────────────┐  │
│  │   Strategy Logic Loop             │  │
│  │   • Check strategy_enabled state  │  │
│  │   • If enabled: Generate signals  │  │
│  │   • If disabled: Skip trading     │  │
│  └───────────────────────────────────┘  │
└─────────────────────────────────────────┘

┌─────────────────────────────────────────┐
│        Frontend Toggle Switch            │
│   • Calls /start or /stop endpoint      │
│   • Updates persistent state            │
│   • No service restart required         │
└─────────────────────────────────────────┘

┌─────────────────────────────────────────┐
│         Persistent Storage               │
│   • Database (Scalping, Hedger)         │
│   • JSON file (Elite Equity)            │
│   • Loaded on service startup           │
└─────────────────────────────────────────┘
```

### Workflow

1. **Service Starts**
   - Windows service initializes
   - Loads `strategy_enabled` state from storage
   - Default: `TRUE` (active)

2. **User Toggles Strategy**
   - Frontend sends POST request to `/start` or `/stop`
   - Service updates state in persistent storage
   - Service immediately enables/disables trading logic
   - Windows service keeps running

3. **Service Restarts**
   - State automatically loaded from storage
   - Strategy resumes with same enabled/disabled state
   - No manual intervention needed

## API Endpoints

### Get Status
```http
GET /status              # AI Scalping, AI Options Hedger
GET /api/status          # Elite Equity HV
```

**Response:**
```json
{
  "running": true,                 // Service running
  "strategy_enabled": true,        // Strategy actively trading
  "mode": "paper",
  "is_trading_time": true,
  "timestamp": "2025-12-13T10:30:00"
}
```

### Enable Strategy
```http
POST /start              # AI Scalping, AI Options Hedger
POST /api/start          # Elite Equity HV
```

**Request Body:**
```json
{
  "capital": 500000,
  "max_daily_loss": 0.05
}
```

**Response:**
```json
{
  "success": true,
  "message": "Strategy enabled",
  "running": true,
  "strategy_enabled": true
}
```

### Disable Strategy
```http
POST /stop               # AI Scalping, AI Options Hedger
POST /api/stop           # Elite Equity HV
```

**Response:**
```json
{
  "success": true,
  "message": "Strategy disabled",
  "running": false,
  "strategy_enabled": false
}
```

## Frontend Integration

### Status Display

The frontend displays the `strategy_enabled` state:

```tsx
// Toggle switch reflects strategy_enabled
<button className={strategy_enabled ? 'active' : 'inactive'}>
  {strategy_enabled ? 'ACTIVE' : 'INACTIVE'}
</button>
```

### Toggle Logic

```tsx
const toggleStrategy = async () => {
  // Check current strategy_enabled state
  const endpoint = status?.strategy_enabled ? '/stop' : '/start';
  
  await fetch(`${SERVICE_URL}${endpoint}`, {
    method: 'POST',
    body: JSON.stringify(config)
  });
  
  // Refresh status to get updated strategy_enabled
  await fetchStatus();
};
```

## Testing

### Test Current State

```powershell
# Run test script
.\Test-PersistentState.ps1
```

**Output:**
```
[1/3] AI SCALPING SERVICE
─────────────────────────────────────
  ✓ Service Online
  Strategy Enabled: YES (ACTIVE)
  Windows Service Running: YES
  Mode: paper
  
[2/3] AI OPTIONS HEDGER
─────────────────────────────────────
  ✓ Service Online
  Strategy Enabled: YES (ACTIVE)
  Windows Service Running: YES
  Mode: paper
  
[3/3] ELITE EQUITY HV
─────────────────────────────────────
  ✓ Service Online
  Strategy Enabled: YES (ACTIVE)
  Windows Service Running: YES
  Mode: paper
```

### Test Toggle & Persistence

```powershell
# Interactive toggle test
.\Test-Toggle.ps1

# Select service: 1=Scalping, 2=Hedger, 3=Equity
# Script will:
# 1. Show current state
# 2. Toggle to opposite state
# 3. Verify state persisted
# 4. Instructions for persistence test
```

### Manual Testing

```powershell
# 1. Check current state
Invoke-RestMethod "http://localhost:4002/status" | Select strategy_enabled

# 2. Disable strategy
Invoke-RestMethod "http://localhost:4002/stop" -Method Post

# 3. Verify disabled
Invoke-RestMethod "http://localhost:4002/status" | Select strategy_enabled

# 4. Restart service
Restart-Service AIScalpingService -Force

# 5. Verify state persisted (should still be disabled)
Invoke-RestMethod "http://localhost:4002/status" | Select strategy_enabled

# 6. Enable strategy
Invoke-RestMethod "http://localhost:4002/start" -Method Post
```

## Database Schema

### service_state Table

```sql
CREATE TABLE IF NOT EXISTS service_state (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Example data
INSERT INTO service_state (key, value) VALUES ('strategy_enabled', '1');
```

**Keys:**
- `strategy_enabled`: `'1'` (enabled) or `'0'` (disabled)

## File Locations

### Code Files
- `ai_scalping_service/production_service.py` - Scalping state management
- `ai_options_hedger/production_hedger_service.py` - Hedger state management
- `equity_hv_service/equity_hv_service.py` - Elite Equity state management

### Database Files
- `ai_scalping_service/data/scalping.db` - Scalping service database
- `ai_options_hedger/data/hedger.db` - Hedger service database

### State Files
- `equity_hv_service/data/equity_strategy_state.json` - Elite Equity state

### Frontend Files
- `frontend/src/pages/StrategiesPage.tsx` - Strategy dashboard UI

## Benefits

### For Individual Traders

1. **Always Ready**
   - Services default to active
   - No manual enabling needed after restarts
   - Immediate trading when market opens

2. **Easy Control**
   - Simple toggle in frontend
   - No need to access server
   - No service restarts required

3. **Persistent State**
   - Toggle once, state persists
   - Service restarts don't affect state
   - Consistent behavior

### For Production

1. **24/7 Service Uptime**
   - Windows services never stop
   - No downtime for toggling
   - Monitoring stays active

2. **User-Friendly**
   - Frontend toggle interface
   - Clear active/inactive status
   - Real-time state updates

3. **Maintenance Friendly**
   - Service restarts safe
   - State automatically restored
   - No configuration loss

## Troubleshooting

### Strategy Not Trading

**Check 1: Service Online?**
```powershell
Get-Service AIScalpingService
# Should be: Running
```

**Check 2: Strategy Enabled?**
```powershell
Invoke-RestMethod "http://localhost:4002/status" | Select strategy_enabled
# Should be: True
```

**Check 3: Trading Time?**
```powershell
Invoke-RestMethod "http://localhost:4002/status" | Select is_trading_time
# Should be: True (during market hours)
```

### State Not Persisting

**For Scalping/Hedger (Database):**
```powershell
# Check if database table exists
sqlite3 ai_scalping_service/data/scalping.db "SELECT * FROM service_state;"
# Should show: strategy_enabled | 1 | timestamp
```

**For Elite Equity (JSON):**
```powershell
# Check if state file exists
Get-Content equity_hv_service/data/equity_strategy_state.json
# Should show: {"strategy_enabled": true}
```

### Frontend Not Updating

**Check 1: Services responding?**
```powershell
Invoke-RestMethod "http://localhost:4002/status"
Invoke-RestMethod "http://localhost:4003/status"
Invoke-RestMethod "http://localhost:5080/api/status"
```

**Check 2: CORS enabled?**
- All services have CORS middleware enabled
- Frontend on `localhost:3000` should connect

**Check 3: Frontend running?**
```powershell
cd frontend
npm run dev
# Should be: http://localhost:3000
```

## Implementation Details

### State Management Classes

**AI Scalping:**
```python
class ProductionScalpingService:
    def __init__(self):
        self._strategy_enabled = True  # Default
        self._load_strategy_state()
    
    def _load_strategy_state(self):
        # Load from database
        result = conn.execute(
            "SELECT value FROM service_state WHERE key = 'strategy_enabled'"
        ).fetchone()
        self._strategy_enabled = result[0] == '1'
    
    def _save_strategy_state(self, enabled: bool):
        # Save to database
        conn.execute(
            "INSERT OR REPLACE INTO service_state (key, value) VALUES (?, ?)",
            ('strategy_enabled', '1' if enabled else '0')
        )
```

**Elite Equity:**
```python
def load_strategy_state() -> bool:
    if STATE_FILE.exists():
        data = json.load(open(STATE_FILE))
        return data.get('strategy_enabled', True)
    return True  # Default

def save_strategy_state(enabled: bool):
    json.dump({'strategy_enabled': enabled}, open(STATE_FILE, 'w'))
```

## Future Enhancements

### Planned Features

1. **Schedule-Based Activation**
   - Auto-enable during market hours
   - Auto-disable outside market hours
   - Configurable schedules

2. **User-Level State (Multi-User)**
   - Each user has own enabled/disabled state
   - Multiple users trade independently
   - See: `docs/MULTI_USER_ARCHITECTURE.md`

3. **State History**
   - Track when strategy enabled/disabled
   - Track who toggled (with authentication)
   - Audit trail for compliance

4. **Conditional Activation**
   - Enable only if certain conditions met
   - Disable if daily loss limit reached
   - Auto-recovery logic

## Summary

✅ **Implemented:**
- Persistent strategy state across service restarts
- Default active state (strategies enabled by default)
- Frontend toggle switches
- Database/file storage
- Status API endpoints

✅ **Tested:**
- State persists after service restart
- Toggle works from frontend
- All three services supported

✅ **Production Ready:**
- Individual trader use case
- 24/7 Windows service uptime
- Easy strategy control
- No downtime for toggling

---

**Last Updated:** December 13, 2025
**Version:** 1.0
**Status:** Production Ready ✅
