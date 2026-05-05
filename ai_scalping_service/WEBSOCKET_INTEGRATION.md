# AI Scalping Service - Direct WebSocket Integration

## Overview

The AI Scalping Service now connects **directly** to Dhan's WebSocket for real-time market data instead of polling the backend HTTP service. This provides:

- **Zero Latency**: Direct tick-by-tick data from Dhan's Live Market Feed
- **No Rate Limits**: WebSocket subscription has no API rate limits
- **Independence**: Service doesn't depend on backend for market data
- **Auto-Reconnection**: Built-in reconnection with exponential backoff

## Architecture Change

### Before
```
[Dhan API] --> [Backend HTTP :8000] --> [AI Scalping HTTP Poll :4002]
                                             |
                                             v
                                     [Process Signal]
```

### After
```
[Dhan WebSocket] ---> [AI Scalping :4002] ---> [Process Signal]
                           ^
                           |
                    [Direct Connection]
```

## WebSocket Protocol

- **URL**: `wss://api-feed.dhan.co?version=2&token={token}&clientId={clientId}&authType=2`
- **Data Format**: Binary (Little Endian)
- **Subscription Mode**: QUOTE (17) for bid/ask + LTP
- **Max Instruments**: 5000 per connection, 5 connections per user

## Subscribed Indices

| Index | Security ID | Exchange Segment |
|-------|-------------|------------------|
| NIFTY | 13 | IDX_I (0) |
| BANKNIFTY | 25 | IDX_I (0) |
| SENSEX | 51 | IDX_I (0) |
| BANKEX | 52 | IDX_I (0) |
| FINNIFTY | 27 | IDX_I (0) |

## New Endpoints

### GET /websocket/status
Returns WebSocket connection status and latest tick data.

```json
{
    "status": "connected",
    "connected": true,
    "tick_count": 1234,
    "last_tick": {
        "symbol": "NIFTY",
        "ltp": 24500.50,
        "timestamp": "2025-12-17T14:30:00"
    },
    "subscribed_count": 4,
    "reconnect_count": 0
}
```

### POST /websocket/reconnect
Force reconnect the WebSocket connection.

```json
{
    "success": true,
    "message": "WebSocket reconnected successfully"
}
```

## Configuration

The service shares `dhan_config.json` with the AI Options Hedger:

```json
{
    "access_token": "your_jwt_token",
    "client_id": "your_client_id"
}
```

**Config Location**: `ai_options_hedger/dhan_config.json`

## Token Update

When updating the Dhan token:

1. Run `Update-Token-Seamless.ps1` with the new token
2. The script will:
   - Update `dhan_config.json` on disk
   - Call `/update-token` API on all services
   - Call `/websocket/reconnect` to reconnect with new token

## Fallback to HTTP

If WebSocket fails to connect, the service automatically falls back to HTTP polling from the backend:

```python
# In production_scalping_service.py
if config.use_websocket and WEBSOCKET_CLIENT_AVAILABLE:
    # Try WebSocket first
    if await ws_client.connect():
        # Use WebSocket
    else:
        # Fall back to HTTP polling
        start_data_fetcher()
```

## Files Changed

1. **New**: `core/dhan_websocket_client.py` - WebSocket client implementation
2. **Modified**: `production_scalping_service.py` - Integrated WebSocket as primary data source
3. **Modified**: `Update-Token-Seamless.ps1` - Updated to use `/websocket/reconnect`

## Testing

```powershell
# Check WebSocket status
Invoke-RestMethod -Uri "http://localhost:4002/websocket/status" | ConvertTo-Json

# Check health
Invoke-RestMethod -Uri "http://localhost:4002/health" | ConvertTo-Json

# Force reconnect
Invoke-RestMethod -Uri "http://localhost:4002/websocket/reconnect" -Method POST | ConvertTo-Json
```

## Market Hours

- WebSocket will show `tick_count: 0` outside market hours (9:15 AM - 3:30 PM IST)
- During market hours, ticks flow in real-time without any polling delays
