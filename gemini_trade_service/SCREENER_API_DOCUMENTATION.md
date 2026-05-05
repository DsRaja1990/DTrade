# Stock Screener & AI Prediction API Documentation

## Overview

This document describes the Stock Screener and AI Prediction Scanner endpoints added to the Gemini Trade Service.

## Architecture

The screener uses the same **3-Tier AI Architecture**:
- **Tier 1** (gemini-2.0-flash-lite): Raw data analysis
- **Tier 2** (gemini-2.0-flash): Strategy filtering
- **Tier 3** (gemini-3-pro-preview): Final prediction with macro context

---

## Endpoints

### 1. Stock Screener Signals
**GET** `/api/screener/signals`

Scans NIFTY 50 stocks and generates BUY/SELL/SIDEWAYS signals.

#### Signal Criteria:

| Signal | Criteria |
|--------|----------|
| **BUY** | Volume spike + Price > VWAP + SuperTrend Buy + Price > CPR + Bullish candle + Call unwinding/Put OI rising + PCR > 1 |
| **SELL** | Volume spike + Price < VWAP + SuperTrend Sell + Price < CPR + Bearish candle + Put unwinding/Call OI rising + PCR < 0.8 |
| **SIDEWAYS** | Price inside CPR + Low volume + Conflicting OI + Price hugging VWAP |

#### Query Parameters:
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `stocks` | string | All NIFTY 50 | Comma-separated stock symbols |
| `min_confidence` | int | 70 | Minimum confidence percentage |
| `signal_type` | string | ALL | BUY, SELL, SIDEWAYS, or ALL |

#### Response:
```json
{
  "status": "success",
  "signals": [
    {
      "trade": "BUY",
      "symbol": "RELIANCE",
      "confidence": 87,
      "strike": "48700 CE",
      "stop_loss": 35,
      "target": 90,
      "reason": "CPR breakout + volume + call unwinding",
      "breakout_quality": 8.5,
      "indicators": {
        "vwap_position": "ABOVE",
        "supertrend": "BUY",
        "cpr_position": "ABOVE",
        "oi_bias": "BULLISH",
        "pcr": 1.15
      }
    }
  ],
  "summary": {
    "total_scanned": 50,
    "signals_found": 8,
    "buy_signals": 5,
    "sell_signals": 3,
    "sideways": 42
  }
}
```

---

### 2. Individual Stock Analysis
**GET** `/api/screener/stock/<symbol>`

Get detailed analysis for a specific stock.

#### Example:
```
GET /api/screener/stock/RELIANCE
```

#### Response:
```json
{
  "status": "success",
  "symbol": "RELIANCE",
  "analysis": {
    "trade": "BUY",
    "confidence": 87,
    "indicators": {
      "volume_spike": true,
      "volume_ratio": 2.3,
      "vwap": 2450.50,
      "current_price": 2465.25,
      "vwap_position": "ABOVE",
      "supertrend": {
        "signal": "BUY",
        "value": 2440.00
      },
      "cpr": {
        "pivot": 2445.00,
        "bc": 2438.00,
        "tc": 2452.00,
        "position": "ABOVE"
      },
      "oi_data": {
        "call_oi_change": -50000,
        "put_oi_change": 75000,
        "pcr": 1.15,
        "bias": "BULLISH"
      }
    },
    "strike_recommendation": "48700 CE",
    "stop_loss": 35,
    "target": 90,
    "tier1_analysis": {...},
    "tier2_analysis": {...},
    "tier3_prediction": {...}
  }
}
```

---

### 3. 5-Minute Movement Predictions
**GET** `/api/prediction/5min`

ChartInk-style predictions for which stocks will move in the next 5 minutes.

#### Query Parameters:
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `direction` | string | ALL | UP, DOWN, or ALL |
| `min_probability` | int | 70 | Minimum prediction probability |
| `limit` | int | 20 | Maximum results |

#### Response:
```json
{
  "status": "success",
  "predictions": [
    {
      "symbol": "RELIANCE",
      "direction": "UP",
      "probability": 85,
      "expected_move_percent": 0.45,
      "momentum_score": 8.2,
      "trigger_reason": "Volume surge + SuperTrend crossover",
      "current_price": 2465.25,
      "predicted_price_5min": 2476.35
    }
  ]
}
```

---

### 4. High Momentum Stocks
**GET** `/api/prediction/momentum`

Identifies stocks with strong momentum (best during 9:15-10:45 AM).

#### Query Parameters:
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `direction` | string | ALL | UP, DOWN, or ALL |
| `min_score` | float | 7.0 | Minimum momentum score (0-10) |

#### Response:
```json
{
  "status": "success",
  "momentum_stocks": [
    {
      "symbol": "TATAMOTORS",
      "direction": "UP",
      "momentum_score": 8.7,
      "consecutive_candles": 5,
      "volume_acceleration": 2.1,
      "price_velocity": 0.35,
      "is_breakout": true
    }
  ],
  "is_morning_momentum_window": true,
  "morning_window": "09:15 - 10:45"
}
```

---

### 5. Continuous Trends
**GET** `/api/prediction/trends`

Finds stocks in continuous up/down trends.

#### Query Parameters:
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `direction` | string | ALL | UP, DOWN, or ALL |
| `min_candles` | int | 3 | Minimum consecutive candles |

#### Response:
```json
{
  "status": "success",
  "trending_stocks": [
    {
      "symbol": "HDFCBANK",
      "direction": "UP",
      "consecutive_candles": 7,
      "trend_strength": 8.5,
      "total_move_percent": 1.2,
      "volume_trend": "INCREASING",
      "sustainability_score": 7.8
    }
  ]
}
```

---

### 6. Peak/Bottom Predictions
**GET** `/api/prediction/peak`

Identifies stocks near intraday peak or bottom.

#### Query Parameters:
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `type` | string | ALL | PEAK, BOTTOM, or ALL |
| `threshold` | float | 95 | How close to peak/bottom (0-100%) |

#### Response:
```json
{
  "status": "success",
  "predictions": [
    {
      "symbol": "INFY",
      "type": "PEAK",
      "proximity_percent": 97.5,
      "current_price": 1850.00,
      "day_high": 1855.00,
      "day_low": 1820.00,
      "reversal_probability": 72,
      "suggested_action": "BOOK_PROFIT"
    }
  ]
}
```

---

### 7. Top AI Picks
**GET** `/api/screener/top-picks`

Combined AI-filtered top trading opportunities.

#### Query Parameters:
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `limit` | int | 10 | Maximum results |
| `risk_level` | string | MEDIUM | LOW, MEDIUM, or HIGH |

#### Response:
```json
{
  "status": "success",
  "top_picks": [
    {
      "symbol": "RELIANCE",
      "trade": "BUY",
      "confidence": 87,
      "momentum_score": 8.2,
      "breakout_quality": 8.5,
      "combined_score": 84.5,
      "strike": "48700 CE",
      "stop_loss": 35,
      "target": 90,
      "reason": "CPR breakout + volume + momentum",
      "expected_move": 0.45
    }
  ],
  "total_analyzed": 50,
  "momentum_matches": 12
}
```

---

### 8. Health Check
**GET** `/api/screener/health`

Check availability of screener services.

#### Response:
```json
{
  "status": "success",
  "services": {
    "stock_screener": true,
    "ai_prediction_scanner": true,
    "tier1_engine": true,
    "tier2_engine": true,
    "tier3_engine": true
  },
  "endpoints": [
    "/api/screener/signals",
    "/api/screener/stock/<symbol>",
    "/api/prediction/5min",
    "/api/prediction/momentum",
    "/api/prediction/trends",
    "/api/prediction/peak",
    "/api/screener/top-picks"
  ]
}
```

---

## Morning Momentum Window

The prediction scanner has special handling for the first 1 hour 30 minutes (9:15 AM - 10:45 AM) when momentum is typically highest.

During this window:
- Momentum scores are amplified
- Volume spikes are weighted higher
- Breakout signals are prioritized
- Trend sustainability is boosted

---

## Signal Output Format

All signals follow this standardized format:

```
Trade: BUY  
Confidence: 87%  
Strike: 48700 CE  
SL: 35  
Target: 90  
Reason: CPR breakout + volume + call unwinding
```

---

## Error Handling

All endpoints return standardized error responses:

```json
{
  "status": "error",
  "message": "Detailed error description"
}
```

HTTP Status Codes:
- `200`: Success
- `404`: Stock not found
- `500`: Internal server error
- `503`: Service unavailable (screener not loaded)

---

## Usage Examples

### Get all BUY signals with high confidence
```
GET /api/screener/signals?signal_type=BUY&min_confidence=80
```

### Get 5-min UP predictions
```
GET /api/prediction/5min?direction=UP&min_probability=75
```

### Get morning momentum stocks
```
GET /api/prediction/momentum?min_score=8&direction=UP
```

### Get top 5 low-risk picks
```
GET /api/screener/top-picks?limit=5&risk_level=LOW
```

---

## NIFTY 50 Stocks Covered

The screener covers all NIFTY 50 stocks including:
- RELIANCE, TCS, HDFCBANK, INFY, ICICIBANK
- HINDUNILVR, ITC, SBIN, BHARTIARTL, KOTAKBANK
- LT, AXISBANK, ASIANPAINT, MARUTI, SUNPHARMA
- TITAN, BAJFINANCE, WIPRO, ULTRACEMCO, NESTLEIND
- And 30 more...

---

## AI Model Configuration

| Tier | Model | Temperature | Purpose |
|------|-------|-------------|---------|
| 1 | gemini-2.0-flash-lite | 0.1 | Data analysis |
| 2 | gemini-2.0-flash | 0.3 | Strategy filtering |
| 3 | gemini-3-pro-preview | 0.2 | Final prediction (PAID) |

---

*Last Updated: $(date)*
*Gemini Trade Service v2.0*
