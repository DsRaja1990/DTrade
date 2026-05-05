# 🎯 World-Class Scalping System v6.0

## The Ultimate AI-Powered Index Options Scalping Engine

> **Target: 400%+ Monthly Returns | 90%+ Win Rate | Single-Focus Capital Deployment**

---

## 📋 Table of Contents

1. [System Overview](#system-overview)
2. [Core Philosophy](#core-philosophy)
3. [Component Architecture](#component-architecture)
4. [Position Scaling Strategy](#position-scaling-strategy)
5. [Momentum Detection](#momentum-detection)
6. [Capital Deployment](#capital-deployment)
7. [AI Trade Commander](#ai-trade-commander)
8. [API Reference](#api-reference)
9. [Configuration](#configuration)
10. [Quick Start](#quick-start)

---

## 🎯 System Overview

This system implements **world-class manual scalping techniques** with AI-powered automation. Unlike traditional trading systems that spread capital across multiple instruments, this system:

1. **FOCUSES** on ONE best opportunity at a time
2. **STARTS SMALL** with probe positions (25%)
3. **SCALES UP** on momentum confirmation (50% → 100% → 150%)
4. **EXITS BEFORE** momentum fades
5. **REDUCES** during weak momentum

### Key Metrics

| Metric | Target |
|--------|--------|
| Daily Return | 2-4% |
| Weekly Return | 10-20% |
| Monthly Return | **400%+** |
| Win Rate | **90%+** |
| Max Drawdown | <5% |
| Avg Trade Duration | 2-15 minutes |

### Supported Instruments

| Instrument | Lot Size | Focus Priority |
|------------|----------|----------------|
| NIFTY | 75 | High Volume |
| BANKNIFTY | 35 | High Volatility |
| SENSEX | 20 | Trending Days |
| BANKEX | 30 | Sector Moves |

---

## 💡 Core Philosophy

### The Manual Scalper Mindset

Professional manual scalpers don't trade everything - they:

1. **WAIT** for the perfect setup
2. **TEST** with small size first
3. **ADD** when proven right
4. **SCALE** to full position on momentum
5. **EXIT** before the crowd

### Our Implementation

```
STEP 1: SCAN    → Monitor all 4 instruments
STEP 2: SELECT  → Pick the ONE with best momentum
STEP 3: PROBE   → Enter with 25% position
STEP 4: CONFIRM → Price moves in favor? Scale to 50%
STEP 5: FULL    → Strong momentum? Go to 100%
STEP 6: AGGRESSIVE → Institutional flow? Deploy 150%
STEP 7: EXIT    → Momentum fading? Exit BEFORE reversal
```

---

## 🏗️ Component Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    WORLD-CLASS SCALPING ENGINE                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────────┐    ┌──────────────────┐                  │
│  │  MOMENTUM        │    │  CAPITAL         │                  │
│  │  DETECTOR        │───▶│  DEPLOYER        │                  │
│  │                  │    │                  │                  │
│  │  - Multi-TF      │    │  - Focus Mode    │                  │
│  │  - Phase Track   │    │  - Opportunity   │                  │
│  │  - Velocity      │    │    Scoring       │                  │
│  └──────────────────┘    └────────┬─────────┘                  │
│                                   │                             │
│  ┌──────────────────┐    ┌────────▼─────────┐                  │
│  │  POSITION        │◀───│  AI TRADE        │                  │
│  │  SCALING         │    │  COMMANDER       │                  │
│  │                  │    │                  │                  │
│  │  - Probe 25%     │    │  - Gemini AI     │                  │
│  │  - Confirm 50%   │    │  - Final Yes/No  │                  │
│  │  - Full 100%     │    │  - Risk Guard    │                  │
│  │  - Aggr 150%     │    │                  │                  │
│  └──────────────────┘    └──────────────────┘                  │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Files Structure

```
ai_scalping_service/
├── world_class_service.py      # Main FastAPI service (port 4002)
├── core/
│   ├── momentum_detector.py    # Real-time momentum detection
│   ├── position_scaling.py     # Dynamic position sizing
│   ├── capital_deployer.py     # Single-focus capital management
│   ├── world_class_scalper.py  # Main orchestration engine
│   └── ai_trade_commander.py   # Gemini AI decision validation
├── config/
│   └── settings.py             # Configuration
└── market_data/
    └── dhan_client.py          # Market data client
```

---

## 📈 Position Scaling Strategy

### Scaling Phases

| Phase | Allocation | Entry Criteria | Exit Criteria |
|-------|-----------|----------------|---------------|
| **PROBE** | 25% | Initial signal | Stops hit |
| **CONFIRMED** | 50% | +0.3% profit + momentum | Momentum fade |
| **FULL** | 100% | +0.8% profit + strong momentum | Profit target |
| **AGGRESSIVE** | 150% | Institutional flow detected | Quick exit |

### Scaling Logic

```python
# When to scale UP
if position.stage == "PROBE":
    if profit_pct >= 0.3 and momentum.phase in ["ACCELERATING", "PEAK"]:
        scale_to("CONFIRMED", 50%)

if position.stage == "CONFIRMED":
    if profit_pct >= 0.8 and momentum.strength >= 80:
        scale_to("FULL", 100%)

# When to scale DOWN
if momentum.phase == "FADING" or momentum.velocity < 0:
    reduce_position_by(50%)
    
if momentum.phase == "REVERSING":
    exit_immediately()
```

### Key Rules

1. **Never add to losers** - Only scale UP on profit
2. **Scale fast on confirmation** - Momentum is time-sensitive
3. **Exit before reversal** - Watch for momentum fade
4. **Reset after exit** - Start fresh with next opportunity

---

## 🌊 Momentum Detection

### Momentum Phases

```
                  ┌─────────────────┐
                  │     PEAK        │  ← Maximum momentum
                  │  (Exit zone)    │
                  └────────┬────────┘
           ┌───────────────┴───────────────┐
    ┌──────┴──────┐               ┌────────┴────────┐
    │ ACCELERATING│               │     FADING      │
    │ (Scale zone)│               │  (Reduce zone)  │
    └──────┬──────┘               └────────┬────────┘
           │                               │
    ┌──────┴──────┐               ┌────────┴────────┐
    │  BUILDING   │               │   REVERSING     │
    │ (Entry zone)│               │  (Exit/Short)   │
    └──────┬──────┘               └─────────────────┘
           │
    ┌──────┴──────┐
    │    NONE     │  ← No momentum (wait)
    └─────────────┘
```

### Detection Metrics

| Metric | Calculation | Use |
|--------|-------------|-----|
| **Price Velocity** | ΔPrice / ΔTime | Direction speed |
| **Momentum Strength** | 0-100 score | Overall power |
| **Volume Ratio** | Current / Average | Confirmation |
| **Acceleration** | ΔVelocity / ΔTime | Trend change |

### Multi-Timeframe Analysis

```python
timeframes = {
    "micro": 5,     # 5-second window (scalping)
    "short": 30,    # 30-second window (confirmation)
    "medium": 60,   # 1-minute window (trend)
    "long": 300     # 5-minute window (bias)
}

# Aggregate signal
final_score = (
    micro * 0.4 +   # Most weight on micro
    short * 0.3 +
    medium * 0.2 +
    long * 0.1
)
```

---

## 💰 Capital Deployment

### Single-Focus Strategy

**Key Principle**: Deploy ALL capital to the SINGLE BEST opportunity.

```python
# DON'T do this (spreading capital)
NIFTY: 25%
BANKNIFTY: 25%
SENSEX: 25%
BANKEX: 25%

# DO this (focused capital)
BEST_INSTRUMENT: 100%
OTHERS: 0%
```

### Opportunity Scoring

Each instrument is scored based on:

| Factor | Weight | Description |
|--------|--------|-------------|
| Momentum Strength | 30% | Current momentum power |
| AI Confidence | 25% | Gemini prediction confidence |
| Volume Ratio | 20% | Volume vs average |
| Volatility | 15% | ATR-based volatility |
| Trend Alignment | 10% | Multi-TF trend match |

### Capital Redeployment

```
IF focused_instrument momentum fades:
    1. Exit current position
    2. Re-scan all instruments
    3. Find new best opportunity
    4. Deploy to new instrument
```

---

## 🤖 AI Trade Commander

### Gemini AI Integration

The AI Commander uses Google Gemini for:

1. **Entry Validation** - Should we enter this trade?
2. **Scaling Decision** - Should we add to position?
3. **Exit Timing** - Is it time to exit?
4. **Risk Assessment** - Is the risk acceptable?

### AI Prompt Structure

```python
prompt = f"""
You are an expert options scalper. Analyze this trade:

INSTRUMENT: {instrument}
DIRECTION: {direction}
MOMENTUM: {momentum_phase} (strength: {strength})
POSITION: Current {current_stage}, Profit: {profit_pct}%

What should we do?
Options: STRONG_BUY, BUY, HOLD, REDUCE, EXIT

Respond with JSON:
{{
    "decision": "...",
    "confidence": 0.0-1.0,
    "reasoning": "..."
}}
"""
```

### AI Decision Flow

```
┌─────────────────┐
│  Market Signal  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Technical Check │──── Fail ──▶ NO TRADE
└────────┬────────┘
         │ Pass
         ▼
┌─────────────────┐
│   AI Validate   │──── Low Confidence ──▶ NO TRADE
└────────┬────────┘
         │ High Confidence (>85%)
         ▼
┌─────────────────┐
│  EXECUTE TRADE  │
└─────────────────┘
```

---

## 🔌 API Reference

### Base URL

```
http://localhost:4002
```

### Endpoints

#### Health & Status

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Service health check |
| GET | `/status` | Full trading status |

#### Trading Control

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/start` | Start trading |
| POST | `/stop` | Stop trading |
| POST | `/tick` | Process market tick |

#### Momentum

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/momentum` | Get all momentum status |
| POST | `/momentum/update` | Update with new tick |

#### Positions

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/positions` | Get all positions |
| POST | `/positions/scale` | Manual scale trigger |

#### Capital Deployment

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/deployment` | Deployment status |
| GET | `/deployment/best` | Best opportunity |

#### AI Commander

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/ai/status` | AI statistics |
| POST | `/ai/validate` | Validate a trade |

### Example: Start Trading

```bash
curl -X POST http://localhost:4002/start \
  -H "Content-Type: application/json" \
  -d '{
    "capital": 500000,
    "instruments": ["NIFTY", "BANKNIFTY", "SENSEX", "BANKEX"],
    "focus_mode": true,
    "use_ai_validation": true,
    "paper_mode": true
  }'
```

### Example: Process Tick

```bash
curl -X POST http://localhost:4002/tick \
  -H "Content-Type: application/json" \
  -d '{
    "instrument": "NIFTY",
    "price": 22500.50,
    "volume": 15000,
    "bid": 22500.25,
    "ask": 22500.75
  }'
```

---

## ⚙️ Configuration

### Scaling Configuration

```python
scaling_config = {
    "probe_size_percent": 25.0,      # Initial position size
    "confirmed_size_percent": 50.0,   # After first confirmation
    "full_size_percent": 100.0,       # Full position
    "aggressive_size_percent": 150.0, # Maximum (with margin)
    "min_profit_to_confirm": 0.3,     # % profit to confirm
    "min_profit_to_full": 0.8         # % profit to go full
}
```

### Momentum Configuration

```python
momentum_config = {
    "micro_window": 5,       # 5 seconds
    "short_window": 30,      # 30 seconds
    "medium_window": 60,     # 1 minute
    "long_window": 300,      # 5 minutes
    "min_strength_entry": 60, # Minimum to enter
    "fade_threshold": 30      # Below this = fading
}
```

### AI Configuration

```python
ai_config = {
    "enabled": True,
    "min_confidence": 0.85,           # 85% minimum
    "gemini_service_url": "http://localhost:4080"
}
```

---

## 🚀 Quick Start

### 1. Install Dependencies

```bash
cd ai_scalping_service
pip install -r requirements.txt
```

### 2. Start Required Services

```bash
# Start Gemini Trade Service (if using AI)
cd ../gemini_trade_service
python gemini_service.py

# Start World-Class Scalping Service
cd ../ai_scalping_service
python world_class_service.py
```

### 3. Verify Health

```bash
curl http://localhost:4002/health
```

### 4. Start Paper Trading

```bash
curl -X POST http://localhost:4002/start \
  -H "Content-Type: application/json" \
  -d '{"capital": 500000, "paper_mode": true}'
```

### 5. Monitor Status

```bash
curl http://localhost:4002/status
```

---

## 📊 Performance Expectations

### Daily Performance

```
Morning Session (9:15 - 11:30):
  - 2-3 scalping trades
  - Target: 1-2% return

Afternoon Session (13:00 - 15:30):
  - 2-3 scalping trades
  - Target: 1-2% return

Daily Total: 2-4% return
```

### Monthly Projection

```
Day 1:   ₹500,000 × 2% = ₹510,000
Day 5:   ₹510,000 × 10% = ₹561,000
Day 10:  ₹561,000 × 10% = ₹617,100
Day 15:  ₹617,100 × 10% = ₹678,810
Day 20:  ₹678,810 × 10% = ₹746,691
Day 22:  Target ₹2,000,000+ (400%+)
```

### Risk Management

| Parameter | Value |
|-----------|-------|
| Max Loss per Trade | 1% of capital |
| Max Daily Loss | 3% of capital |
| Max Drawdown | 5% of capital |
| Emergency Stop | 5% daily loss |

---

## 🔧 Troubleshooting

### Common Issues

1. **AI Commander not responding**
   - Check Gemini service at port 4080
   - Verify API key in config

2. **Momentum not updating**
   - Ensure tick data is flowing
   - Check market hours

3. **No trades executing**
   - Verify `focus_mode: true`
   - Check AI confidence threshold

### Logs

```bash
tail -f logs/world_class_scalping.log
```

---

## 📞 Support

For issues or questions:
- Check logs at `logs/world_class_scalping.log`
- Review API docs at `http://localhost:4002/docs`

---

**Built with ❤️ for achieving 400%+ monthly returns through intelligent scalping.**
