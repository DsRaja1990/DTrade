# Equity High-Velocity (HV) Trading Service

## Overview

Production-ready F&O trading service integrated with **Gemini AI Trading Engine** for intelligent stock screening and trade execution via **Dhan API**.

**Port: 5080**

## 🚀 Key Features

### Gemini AI Integration
- 3-tier AI screening (Quick Filter → Deep Analysis → Final Validation)
- Real-time signal generation with confidence scores
- Multi-factor scoring: Technical (40%), AI (30%), Market Structure (15%), Volume (15%)

### Production Auto-Trader
- Continuous market monitoring (9:15 AM - 3:30 PM IST)
- Sophisticated multi-factor screening every 5 minutes
- Auto-execution of high-probability trades
- Circuit breakers and risk management

### SQLite Database
- Local signal/trade storage at `data/trading_data.db`
- Performance analytics for ML enhancement
- Historical data for strategy optimization

### Dhan API Integration
- Real-time market data
- Order execution (Paper/Live modes)
- Position management

## 📁 Service Structure

```
equity_hv_service/
├── equity_hv_service.py           # Main FastAPI service
├── gemini_engine_router.py        # Gemini AI endpoints
├── requirements.txt               # Dependencies
├── Dockerfile                     # Container deployment
├── docker-compose.yml
│
├── strategy/                      # Trading Strategy
│   ├── production_auto_trader.py  # Auto-trading engine
│   ├── auto_trader_router.py      # Auto-trader endpoints
│   ├── sophisticated_screener.py  # Multi-factor screener
│   ├── gemini_ai_trading_engine.py# Gemini AI integration
│   ├── dhan_connector.py          # Dhan API client
│   └── dhan_config.py             # Dhan configuration
│
├── database/                      # SQLite Database
│   ├── db_manager.py              # Database manager
│   ├── analytics_router.py        # Analytics endpoints
│   └── __init__.py
│
├── api/                           # API Routes
│   ├── equity_hv_router.py        # Strategy endpoints
│   └── __init__.py
│
├── config/                        # Configuration
│   └── dhan_config.py
│
├── data/                          # Database storage
│   └── trading_data.db
│
└── logs/                          # Service logs
```

## 🔌 API Endpoints

### Core
- `GET /health` - Service health check
- `GET /config` - Service configuration
- `GET /status` - Detailed service status
- `GET /stocks` - Elite stocks list

### Gemini Engine (`/api/gemini-engine`)
- Screen stocks with AI analysis
- Get signal confidence scores

### Auto-Trader (`/api/auto-trader`)
- Start/stop auto-trading
- Get current positions
- View trade history

### Analytics (`/api/analytics`)
- `GET /performance/summary` - Performance metrics
- `GET /performance/daily` - Daily P&L
- `GET /signals/recent` - Recent signals
- `GET /trades/open` - Open positions
- `GET /recommendations` - ML-driven suggestions

## 🚀 Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run the service
cd equity_hv_service
python -m uvicorn equity_hv_service:app --host 0.0.0.0 --port 5080

# Or from parent directory
python -m uvicorn equity_hv_service.equity_hv_service:app --port 5080
```

## ⚙️ Configuration

### Elite Stocks (Top 10 F&O)
- RELIANCE, TCS, HDFCBANK, INFY, ICICIBANK
- KOTAKBANK, BHARTIARTL, ITC, SBIN, BAJFINANCE

### Trading Parameters
- Capital: ₹5,00,000
- Max Positions: 5
- Stop Loss: 2%
- Target: 3%

### Dependencies
- Gemini Trade Service on port 4080
- Dhan API credentials in environment

## 📊 Database Schema

### Tables
- `signals` - All generated trading signals
- `trades` - Executed trades with outcomes
- `daily_performance` - Daily P&L records
- `market_context` - Market regime snapshots
- `error_logs` - System errors

## 🔗 Related Services

- **Gemini Trade Service** (Port 4080) - AI screening for 100+ F&O stocks
- **AI Options Hedger** - Options hedging strategies

## 📝 Version

- **Version**: 3.0.0
- **Build**: gemini-integrated
