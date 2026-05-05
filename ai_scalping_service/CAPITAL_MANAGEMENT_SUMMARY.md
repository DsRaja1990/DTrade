# AI Scalping Service - Institutional Grade Enhancement Summary

## Version 3.0 - Capital Management Integration

### 🎯 Overview
The ai_scalping_service has been enhanced with institutional-grade capital management, 
integrating the sophisticated allocation system from ai_options_hedger.

---

## ✅ Files Created

### 1. `core/capital_manager.py`
**Institutional Capital Manager v4.0**
- Dynamic position sizing with Kelly Criterion
- VIX-adjusted lot calculations
- Confidence-scaled entries
- Priority-based instrument allocation
- Order slicing for freeze quantity limits
- Real-time P&L tracking

### 2. `core/__init__.py`
Module exports for capital management

### 3. `config/capital_config.json`
Configuration file for capital management settings

### 4. `test_capital_manager.py`
Comprehensive test suite for capital management

---

## ✅ Files Modified

### 1. `strategies/scalping_engine_nifty.py` (v3.0)
- Added institutional capital manager import
- Enhanced `_calculate_optimal_position_size()` to return (quantity, order_slices)
- Added `_place_live_order_sliced()` for freeze quantity handling
- Updated `_execute_nifty_signal()` for sliced order execution

### 2. `strategies/scalping_engine_sensex.py` (v3.0)
- Added institutional capital manager import
- Enhanced `_execute_sensex_signal()` with capital management integration
- Added `_place_live_order_sliced()` for freeze quantity handling

### 3. `index_scalping_service.py` (v3.0)
Added capital management API endpoints:
- `GET /capital` - Get capital status
- `POST /capital/configure` - Configure capital settings
- `POST /capital/update_premiums` - Update live ATM premiums
- `GET /capital/position_size/{instrument}` - Calculate position size
- `POST /capital/allocate` - Allocate capital by priority
- `POST /capital/record_trade` - Record trade P&L
- `POST /capital/reset_daily` - Reset daily statistics

### 4. `config/settings.py`
Fixed property definitions for max_daily_loss_percent and max_capital_per_trade_percent

---

## 📊 Position Sizing Results (₹5L Capital)

| Instrument | Confidence | Premium | Lots | Quantity | Capital |
|------------|------------|---------|------|----------|---------|
| NIFTY | 0.92 | ₹150 | 10 | 750 | ₹112,500 |
| BANKNIFTY | 0.85 | ₹350 | 7 | 245 | ₹85,750 |
| FINNIFTY | 0.88 | ₹140 | 9 | 585 | ₹81,900 |
| SENSEX | 0.90 | ₹250 | 25 | 500 | ₹125,000 |
| BANKEX | 0.87 | ₹180 | 16 | 480 | ₹86,400 |
| MIDCPNIFTY | 0.91 | ₹80 | 8 | 1120 | ₹89,600 |

---

## 🔢 VIX-Adjusted Position Sizing

| VIX Level | NIFTY Lots | Adjustment |
|-----------|------------|------------|
| 12 (Low) | 11 | +10% |
| 15 (Normal) | 10 | Normal |
| 20 (Elevated) | 8 | -20% |
| 28 (High) | 6 | -40% |
| 38 (Extreme) | 3 | -70% |

---

## 📦 Order Slicing (₹50L Capital Example)

| Instrument | Total Qty | Freeze Qty | Slices |
|------------|-----------|------------|--------|
| NIFTY | 7,875 | 1,800 | 5 (1800+1800+1800+1800+675) |
| BANKNIFTY | 3,395 | 1,050 | 4 (1050+1050+1050+245) |
| SENSEX | 4,760 | 1,000 | 5 (1000+1000+1000+1000+760) |

---

## 🔄 Priority-Based Allocation

| Priority | Instrument | Reason |
|----------|------------|--------|
| 1 | NIFTY | Moderate premium, highest liquidity |
| 2 | MIDCPNIFTY | Lower premium, good movement |
| 3 | SENSEX | Moderate premium, BSE primary |
| 4 | FINNIFTY | Similar to NIFTY |
| 5 | BANKEX | BSE bank index |
| 6 | BANKNIFTY | **LAST** - Highest premiums |

*BANKNIFTY is allocated last because it has the highest ATM premiums, 
meaning fewer lots can be purchased. Allocate to other instruments first, 
then give remaining capital to BANKNIFTY.*

---

## 📈 Risk Configuration

```json
{
    "max_position_risk_percent": 5.0,
    "max_daily_loss_percent": 3.0,
    "max_concurrent_positions": 6,
    "stop_loss_percent": 0.5,
    "take_profit_percent": 1.0,
    "max_exposure_percent": 60.0,
    "max_capital_per_position_percent": 25.0,
    "vix_threshold_high": 25.0,
    "vix_threshold_extreme": 35.0
}
```

---

## 🚀 Running the Service

```bash
cd ai_scalping_service
python index_scalping_service.py
# Service runs on port 8003
```

### Test Capital Manager
```bash
python test_capital_manager.py
```

### API Examples
```bash
# Get capital status
curl http://localhost:8003/capital

# Calculate position size
curl http://localhost:8003/capital/position_size/NIFTY?confidence=0.92

# Allocate capital
curl -X POST http://localhost:8003/capital/allocate \
  -H "Content-Type: application/json" \
  -d '["NIFTY", "SENSEX", "BANKNIFTY"]'
```

---

## 🎯 Key Features

1. **Kelly Criterion Integration**: Optimal position sizing based on win rate and R:R
2. **Confidence Scaling**: Larger positions for higher confidence signals
3. **VIX Adjustment**: Automatic size reduction in high volatility
4. **Order Slicing**: Handles exchange freeze quantity limits
5. **Priority Allocation**: Intelligent capital distribution across instruments
6. **P&L Tracking**: Real-time tracking with daily loss limits
7. **Live Premium Updates**: Dynamic position sizing with real ATM premiums

---

*Last Updated: December 2024*
*Dhan Token Updated: Active*
*Service Port: 8003*
