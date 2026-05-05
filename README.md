# DTrade - AI-Powered Trading Platform

Complete AI trading system with 4 autonomous services, real-time market data, and intelligent signal generation.

## 🚀 Quick Start

### Update Dhan Token
```powershell
# Run this script whenever you need to update your Dhan access token
.\Update-DhanToken.ps1 -NewToken "YOUR_NEW_TOKEN_HERE"
```

This will automatically:
- Update token in all 5 services (Backend, AI Options Hedger, Elite Equity HV, Gemini Trade, Frontend)
- Restart all Windows services
- Verify connectivity with Dhan API

### Start/Stop Services
```powershell
# Start all services
.\Manage-All-Services.ps1 -Action Start

# Stop all services
.\Manage-All-Services.ps1 -Action Stop

# Restart all services
.\Restart-AI-Services.ps1
```

### Launch Application
```powershell
# Frontend (port 3000)
cd frontend
npm run dev

# Access at: http://localhost:3000
```

## 📦 Services Architecture

### Backend Service (Port 8000)
**DhanHQ_Service** - Main trading backend
- **Status**: http://localhost:8000/health
- **API**: http://localhost:8000/api
- **Features**: Portfolio, Orders, Positions, Holdings, Funds, WebSocket

### AI Trading Services

1. **AI Scalping Service** (Port 4002)
   - **Name**: AIScalpingService
   - **Type**: Index scalping (Nifty/Bank Nifty)
   - **Strategy**: High-frequency intraday scalping

2. **AI Options Hedger** (Port 4003)
   - **Name**: AIOptionsHedger
   - **Type**: Options hedging strategies
   - **Strategy**: Smart delta-neutral hedging

3. **Elite Equity HV Service** (Port 5080)
   - **Name**: EliteEquityHVService
   - **Type**: High volatility equity trading
   - **Strategy**: 90% win rate equity system
   - **Note**: Token expiry 2025-12-16

4. **Gemini Trade Service** (Port 4080)
   - **Name**: GeminiTradeService
   - **Type**: AI signal generation (Google Gemini)
   - **Architecture**: 3-tier predictive system
     - Tier 1: Data preparation (Gemini 2.5 Flash-Lite)
     - Tier 2: Strategy synthesis (Gemini 2.5 Flash)
     - Tier 3: Predictive modeling (Gemini 3 Pro)

## 🔧 Configuration Files

### Token Locations
- **Backend**: `backend/dhan_backend.py` (line 28)
- **AI Options Hedger**: `ai_options_hedger/dhan_config.json`
- **Elite Equity HV**: `equity_hv_service/strategy/dhan_config.py` (line 24)
- **Gemini Trade**: `gemini_trade_service/service_config.py` (line 24)
- **Frontend**: `frontend/.env`

### Service Credentials
- **Dhan Client ID**: 1101317572
- **Current Token**: Updated 2025-12-11
- **Token Expiry**: 2025-12-16 (5 days validity)

## 📊 API Endpoints

### Backend (http://localhost:8000)
- `GET /health` - Service health check
- `GET /api/portfolio` - Complete portfolio overview
- `GET /api/holdings` - Current holdings
- `GET /api/positions` - Open positions
- `GET /api/orders` - Today's orders
- `GET /api/funds` - Fund limits & balance
- `GET /api/services/status` - All services status
- `GET /api/signals/latest` - Latest AI signals
- `WS /ws` - WebSocket for live updates
- `WS /ws/live-data` - Market data WebSocket

### Service Health Checks
```powershell
# Check all services
Invoke-RestMethod http://localhost:8000/api/services/status

# Individual service health
Invoke-RestMethod http://localhost:4002/health  # AI Scalping
Invoke-RestMethod http://localhost:4003/health  # AI Options Hedger
Invoke-RestMethod http://localhost:4080/health  # Gemini Trade
Invoke-RestMethod http://localhost:5080/health  # Elite Equity HV
```

## 🔐 Current Status (as of 2025-12-11)

✅ **All Services Running**
- DhanHQ_Service: ✅ Running
- AIScalpingService: ✅ Running
- AIOptionsHedger: ✅ Running
- EliteEquityHVService: ✅ Running
- GeminiTradeService: ✅ Running

✅ **Dhan API Connected**
- Balance: ₹284.70
- Token Status: Active
- Token Expiry: 2025-12-16

✅ **Frontend Connected**
- WebSocket: Native WebSocket (auto-reconnect)
- API: Connected to backend (port 8000)
- Balance Display: Fixed ✅

## 📁 Project Structure

```
DTrade/
├── backend/                    # Main trading backend (FastAPI)
├── frontend/                   # React + TypeScript UI
├── ai_options_hedger/         # AI Options Hedger service
├── ai_scalping_service/       # AI Scalping service
├── equity_hv_service/         # Elite Equity HV service
├── gemini_trade_service/      # Gemini AI service
├── scripts/                   # Utility scripts & tests
├── docs/                      # Documentation
├── data/                      # Database files
├── logs/                      # Service logs
├── config/                    # Configuration files
└── Update-DhanToken.ps1       # Token update script ⭐
```

## 🛠️ Maintenance

### Daily Tasks
1. **Check Token Expiry**: Token expires every 24-48 hours
   ```powershell
   # Update token when expired
   .\Update-DhanToken.ps1 -NewToken "NEW_TOKEN"
   ```

2. **Monitor Services**:
   ```powershell
   # Check all services status
   Get-Service -Name "*Service*" | Where-Object { $_.Name -match "AI|Gemini|Elite|DhanHQ" }
   ```

3. **View Logs**: Check `logs/` folder for service-specific logs

### Troubleshooting

**Service Won't Start**:
```powershell
# Check if port is in use
Get-NetTCPConnection -LocalPort 8000  # Backend
Get-NetTCPConnection -LocalPort 4002  # AI Scalping
Get-NetTCPConnection -LocalPort 4003  # AI Options Hedger
Get-NetTCPConnection -LocalPort 4080  # Gemini Trade
Get-NetTCPConnection -LocalPort 5080  # Elite Equity HV
```

**Token Expired**:
1. Get new token from Dhan web portal
2. Run: `.\Update-DhanToken.ps1 -NewToken "NEW_TOKEN"`
3. Services will restart automatically

**Frontend Not Connecting**:
1. Verify backend is running: `Invoke-RestMethod http://localhost:8000/health`
2. Restart frontend: `cd frontend; npm run dev`
3. Clear browser cache

**Balance Not Showing**:
- Frontend now uses backend API (fixed ✅)
- Check: `Invoke-RestMethod http://localhost:8000/api/funds`
- Should show: `availabelBalance: 284.7`

## 🎯 Next Steps

1. **Monitor token expiry** (expires 2025-12-16)
2. **Use Update-DhanToken.ps1** for quick token updates
3. **Check service health** daily via `/api/services/status`
4. **Review logs** for any errors or warnings

## 📞 Support

- Dhan API Docs: https://api.dhan.co
- Client ID: 1101317572
- Services: Running on localhost (4002, 4003, 4080, 5080, 8000)

---

**Last Updated**: 2025-12-11  
**Token Updated**: 2025-12-11  
**Token Expires**: 2025-12-16
