# Institutional Algorithm Integration Summary

## Overview

This document describes the integration of world-class institutional trading algorithms into the DTrade trading system. Three specialized engines have been created and integrated into their respective services.

---

## 1. AI Scalping Service (Port 4002)

### Institutional Engine: `InstitutionalScalpingEngine`
**File:** `ai_scalping_service/core/institutional_scalping_engine.py`

### Algorithms Implemented:

#### 1.1 Smart Money Concepts (SMC)
- **Order Block Detection**: Identifies institutional accumulation/distribution zones
- **Fair Value Gap (FVG)**: Detects price imbalances for potential reversals
- **Liquidity Sweep Detection**: Identifies stop hunts and liquidity grabs
- **Change of Character (CHoCH)**: Detects trend reversals

#### 1.2 Volume Profile Analysis
- **Point of Control (POC)**: Highest volume price level
- **Value Area High/Low (VAH/VAL)**: 70% volume distribution range
- **High Volume Nodes (HVN)**: Support/resistance zones
- **Low Volume Nodes (LVN)**: Fast price movement zones

#### 1.3 Gamma Exposure Analysis
- **Dealer Gamma Calculation**: Net market maker gamma exposure
- **Gamma Flip Detection**: Identifies gamma positive/negative transitions
- **Squeeze Risk Assessment**: Detects potential gamma squeezes
- **Pin Risk Analysis**: Identifies potential expiry pinning levels

### Integration Points:
```python
# In production_scalping_service.py

# Import (line ~45)
from core.institutional_scalping_engine import (
    InstitutionalScalpingEngine, create_institutional_engine,
    InstitutionalSignal, SignalStrength, SignalDirection
)

# Initialization in ProductionScalpingEngine.__init__()
self._institutional_engine = create_institutional_engine({
    'min_confluence_score': 65,
    'max_signals_per_hour': 8
})

# Data feeding in update_momentum()
self._institutional_engine.update_data(instrument, price, volume, high, low)

# Signal generation in get_best_opportunity()
inst_signal = self._institutional_engine.analyze(instrument, current_price)
```

### New API Endpoints:
- `GET /institutional-signal/{instrument}` - Get institutional signal for one instrument
- `GET /institutional-signals` - Get signals for all tracked instruments

---

## 2. AI Options Hedger (Port 4003)

### Institutional Engine: `InstitutionalGreeksHedgingEngine`
**File:** `ai_options_hedger/core/engines/institutional_greeks_engine.py`

### Algorithms Implemented:

#### 2.1 Greeks Calculation (Full Surface)
- **First Order**: Delta, Gamma, Theta, Vega, Rho
- **Second Order**: Vanna, Volga, Charm, Veta, Vomma
- **Accurate Time-to-Expiry**: Proper decay calculations

#### 2.2 Dynamic Delta Hedging
- **Threshold-Based Rebalancing**: Adjusts when delta exceeds limits
- **Cost-Aware Hedging**: Considers transaction costs
- **Urgency Scoring**: Prioritizes hedges by risk

#### 2.3 Volatility Surface Arbitrage
- **SVI Parameterization**: Fits volatility surface
- **Skew Detection**: Identifies vol skew opportunities
- **Term Structure Analysis**: Calendar spread opportunities

#### 2.4 Gamma Scalping
- **Realized vs Implied Vol**: Detects scalping opportunities
- **Position Sizing**: Optimal gamma scalp sizes
- **Breakeven Calculation**: Required movement for profit

#### 2.5 Vanna-Volga Hedging
- **Second-Order Greeks**: Manages convexity risk
- **Smile Risk Hedging**: Protects against skew changes

### Integration Points:
```python
# In production_hedger_service.py

# Import (line ~45)
from core.engines.institutional_greeks_engine import (
    InstitutionalGreeksHedgingEngine, create_hedging_engine,
    GreeksExposure, HedgeRecommendation, HedgeStrategy
)

# Initialization in ProductionHedgerService.__init__()
self._greeks_engine = create_hedging_engine({
    'max_delta': 2000, 'max_gamma': 100, 'max_vega': 500
})

# Position tracking after trade execution
greeks = self._greeks_engine.add_position(symbol, strike, expiry, ...)

# Risk monitoring
risk_status = self._greeks_engine.check_risk_limits()
```

### New API Endpoints:
- `GET /greeks` - Get portfolio-level Greeks exposure
- `GET /hedge-recommendations?spot_price=` - Get hedge recommendations
- `GET /risk-limits` - Check if portfolio is within risk limits

---

## 3. Elite Equity HV Trading (Port 5080)

### Institutional Engine: `InstitutionalEquityAlphaEngine`
**File:** `equity_hv_service/strategy/institutional_alpha_engine.py`

### Algorithms Implemented:

#### 3.1 Statistical Arbitrage
- **Pairs Trading**: Cointegration-based pair identification
- **Mean Reversion**: Z-score based entry/exit
- **Spread Monitoring**: Dynamic spread calculation
- **Half-Life Estimation**: Optimal holding period

#### 3.2 Multi-Factor Model
- **Momentum Factor**: 12M-1M price momentum
- **Value Factor**: P/E, P/B, Dividend Yield
- **Quality Factor**: ROE, Debt/Equity, Margin stability
- **Volatility Factor**: Low volatility premium
- **Factor Combination**: Weighted alpha score

#### 3.3 Order Flow Analysis
- **Order Flow Imbalance (OFI)**: Buy/sell pressure
- **VPIN**: Volume-synchronized PIN
- **Iceberg Detection**: Hidden institutional orders
- **Toxicity Metrics**: Adverse selection risk

#### 3.4 Regime Detection
- **Market State Classification**: Trending/Mean-Reverting/Volatile/Crisis
- **Regime Transition Probability**: State change likelihood
- **Parameter Adjustment**: Regime-specific strategy params

### Integration Points:
```python
# In equity_hv_service.py

# Import (line ~200)
from strategy.institutional_alpha_engine import (
    InstitutionalEquityAlphaEngine, create_alpha_engine,
    AlphaSignal, MarketRegime, AlphaType
)

# Initialization in lifespan
service_state["alpha_engine"] = create_alpha_engine({
    'elite_stocks': list(ELITE_STOCKS.keys()),
    'max_position_pct': 20.0
})

# Signal generation
signals = await alpha_engine.generate_alpha_signals(price_data)
```

### New API Endpoints:
- `GET /alpha-signals` - Get institutional alpha signals
- `GET /market-regime` - Get current detected market regime
- `GET /factor-scores/{symbol}` - Get factor scores for a stock

---

## 4. Unified Orchestrator

### File: `scripts/unified_institutional_orchestrator.py`

The Unified Orchestrator combines all three engines for maximum alpha generation.

### Algorithm Execution Order:

1. **Regime Detection** (Alpha Engine)
   - Determines market state
   - Adjusts parameters for other algorithms

2. **SMC + Volume Profile Analysis** (Scalping Engine)
   - Detects institutional footprints
   - Identifies key price levels

3. **Greeks Calculation** (Greeks Engine)
   - Updates portfolio risk
   - Checks risk limits

4. **Factor Alpha Generation** (Alpha Engine)
   - Multi-factor scoring
   - Statistical arbitrage signals

5. **Signal Confluence**
   - Combines all signals (weighted)
   - Applies regime adjustments
   - Applies Greeks-based sizing

### Usage:
```python
from scripts.unified_institutional_orchestrator import create_unified_orchestrator

orchestrator = create_unified_orchestrator({
    'scalping_weight': 0.40,
    'greeks_weight': 0.25,
    'alpha_weight': 0.35,
    'min_confluence': 65
})

await orchestrator.initialize()

# Feed data
orchestrator.update_market_data(instrument, price, volume, high, low)

# Get unified signal
signal = await orchestrator.generate_unified_signal(
    instrument=instrument,
    current_price=price,
    option_chain=chain,
    price_data=historical_data
)

if signal:
    print(f"Direction: {signal.direction}")
    print(f"Confidence: {signal.confidence}")
    print(f"Unified Score: {signal.unified_score}")
```

---

## 5. Signal Confidence Levels

| Level | Score Range | Description |
|-------|-------------|-------------|
| LEGENDARY | 90%+ | Highest conviction, max position size |
| ULTRA | 80-89% | Very high conviction |
| STRONG | 70-79% | High conviction |
| MODERATE | 60-69% | Moderate conviction |
| WEAK | <60% | Low conviction, typically filtered out |

---

## 6. Risk Management

### Portfolio-Level Limits:
- **Max Delta**: 2000 (configurable)
- **Max Gamma**: 100 (configurable)
- **Max Vega**: 500 (configurable)
- **Delta Rebalance Threshold**: 15%
- **Gamma Threshold**: 10%

### Regime Adjustments:
| Regime | Position Multiplier |
|--------|---------------------|
| TRENDING_UP | 1.2x |
| TRENDING_DOWN | 1.2x |
| MEAN_REVERTING | 0.9x |
| HIGH_VOLATILITY | 0.7x |
| CRISIS | 0.5x |

---

## 7. Testing the Integration

### Verify Services Running:
```powershell
# Check all services
Get-Service AIScalpingService, AIOptionsHedger, EliteEquityHVService | Select Name, Status
```

### Test Endpoints:
```powershell
# AI Scalping Service
Invoke-RestMethod http://localhost:4002/health
Invoke-RestMethod http://localhost:4002/institutional-signals

# AI Options Hedger
Invoke-RestMethod http://localhost:4003/health
Invoke-RestMethod http://localhost:4003/greeks
Invoke-RestMethod "http://localhost:4003/hedge-recommendations?spot_price=24500"

# Equity HV Service
Invoke-RestMethod http://localhost:5080/health
Invoke-RestMethod http://localhost:5080/alpha-signals
Invoke-RestMethod http://localhost:5080/market-regime
```

---

## 8. Manage-Service.ps1 Scripts

Each service has a comprehensive management script:

```powershell
# Interactive menu
.\Manage-Service.ps1

# Direct commands
.\Manage-Service.ps1 start
.\Manage-Service.ps1 stop
.\Manage-Service.ps1 restart
.\Manage-Service.ps1 status
.\Manage-Service.ps1 logs
.\Manage-Service.ps1 install    # Admin required
.\Manage-Service.ps1 uninstall  # Admin required
.\Manage-Service.ps1 reinstall  # Admin required
```

---

## 9. Files Modified

### AI Scalping Service:
- `production_scalping_service.py` - Added imports, engine initialization, data feeding, signal integration

### AI Options Hedger:
- `production_hedger_service.py` - Added imports, engine initialization, Greeks tracking, API endpoints

### Equity HV Service:
- `equity_hv_service.py` - Added imports, engine initialization, API endpoints

### Created:
- `scripts/unified_institutional_orchestrator.py` - Combined orchestrator
- `docs/INSTITUTIONAL_ALGORITHM_INTEGRATION.md` - This documentation

---

## 10. Next Steps

1. **Data Integration**: Connect real-time market data to feed the engines
2. **Backtesting**: Test algorithms on historical data
3. **Parameter Tuning**: Optimize weights and thresholds
4. **Monitoring**: Add dashboards for algorithm performance
5. **Alerting**: Set up alerts for high-confluence signals
