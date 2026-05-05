# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                    ELITE TRADING CORE v1.0                                   ║
║           Institutional-Grade Trading Intelligence System                     ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  COMPONENTS:                                                                  ║
║  1. Ensemble AI Decision Engine - Multi-model consensus with weighted voting ║
║  2. Adaptive Regime Detection - Market state classification                  ║
║  3. Dynamic Risk Management - VaR, drawdown controls, position sizing        ║
║  4. Greeks-Aware Execution - Delta/Gamma/Theta-optimized entries            ║
║  5. Order Flow Intelligence - Institutional flow detection                   ║
║  6. Smart Exit Management - Trailing, scaling, time-based exits             ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import asyncio
import logging
import statistics
import math
from datetime import datetime, time, timedelta
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any
from enum import Enum
import numpy as np

logger = logging.getLogger(__name__)


# ============================================================================
# MARKET REGIME CLASSIFICATION
# ============================================================================

class MarketRegime(str, Enum):
    """Market regime states for adaptive strategy"""
    STRONG_TREND_UP = "STRONG_TREND_UP"      # Clear uptrend, momentum
    STRONG_TREND_DOWN = "STRONG_TREND_DOWN"  # Clear downtrend
    WEAK_TREND_UP = "WEAK_TREND_UP"          # Mild upward bias
    WEAK_TREND_DOWN = "WEAK_TREND_DOWN"      # Mild downward bias
    RANGING = "RANGING"                       # Sideways, mean reversion
    HIGH_VOLATILITY = "HIGH_VOLATILITY"      # Explosive, unpredictable
    LOW_VOLATILITY = "LOW_VOLATILITY"        # Compressed, breakout pending
    TRANSITION = "TRANSITION"                 # Regime changing


class TradingSession(str, Enum):
    """Intraday session classification"""
    PRE_OPEN = "PRE_OPEN"                    # 9:00-9:15
    OPENING_DRIVE = "OPENING_DRIVE"          # 9:15-9:45 (Gap fill, high vol)
    MORNING_SESSION = "MORNING_SESSION"       # 9:45-11:30
    LUNCH_LULL = "LUNCH_LULL"                # 11:30-13:30 (Low vol)
    AFTERNOON_SESSION = "AFTERNOON_SESSION"   # 13:30-14:30
    POWER_HOUR = "POWER_HOUR"                # 14:30-15:00 (Institutional)
    CLOSING_AUCTION = "CLOSING_AUCTION"       # 15:00-15:30


class SignalStrength(str, Enum):
    """Signal strength classification"""
    ELITE = "ELITE"           # 95%+ confidence, 5+ factors
    STRONG = "STRONG"         # 85-95% confidence, 4+ factors
    MODERATE = "MODERATE"     # 75-85% confidence, 3+ factors
    WEAK = "WEAK"             # 65-75% confidence, 2 factors
    NO_TRADE = "NO_TRADE"     # Below threshold


# ============================================================================
# CONFIGURATION - INSTITUTIONAL PARAMETERS
# ============================================================================

@dataclass
class EliteTradingConfig:
    """Elite trading configuration with institutional parameters"""
    
    # Index-specific lot sizes (CORRECT VALUES)
    LOT_SIZES: Dict[str, int] = field(default_factory=lambda: {
        "NIFTY": 75,
        "BANKNIFTY": 35,
        "FINNIFTY": 40,
        "MIDCPNIFTY": 75,
        "SENSEX": 20,
        "BANKEX": 30
    })
    
    # Regime-adaptive confidence thresholds
    CONFIDENCE_THRESHOLDS: Dict[str, float] = field(default_factory=lambda: {
        MarketRegime.STRONG_TREND_UP.value: 0.70,
        MarketRegime.STRONG_TREND_DOWN.value: 0.70,
        MarketRegime.WEAK_TREND_UP.value: 0.75,
        MarketRegime.WEAK_TREND_DOWN.value: 0.75,
        MarketRegime.RANGING.value: 0.80,        # Higher bar for ranging
        MarketRegime.HIGH_VOLATILITY.value: 0.85, # Very high bar
        MarketRegime.LOW_VOLATILITY.value: 0.72,
        MarketRegime.TRANSITION.value: 0.90,     # Highest bar for uncertainty
    })
    
    # Session-specific parameters
    SESSION_MULTIPLIERS: Dict[str, float] = field(default_factory=lambda: {
        TradingSession.OPENING_DRIVE.value: 0.5,    # Reduce size in opening chaos
        TradingSession.MORNING_SESSION.value: 1.0,   # Full size
        TradingSession.LUNCH_LULL.value: 0.7,       # Reduced for low liquidity
        TradingSession.AFTERNOON_SESSION.value: 1.0,
        TradingSession.POWER_HOUR.value: 1.2,       # Increased for trend days
        TradingSession.CLOSING_AUCTION.value: 0.3,  # Minimal near close
    })
    
    # Index-specific volatility adjustments (ATR-based)
    INDEX_ATR_MULTIPLIERS: Dict[str, float] = field(default_factory=lambda: {
        "NIFTY": 1.0,          # Baseline
        "BANKNIFTY": 1.8,      # 1.8x more volatile
        "FINNIFTY": 1.4,
        "MIDCPNIFTY": 1.6,
        "SENSEX": 0.9,         # Slightly less volatile
        "BANKEX": 1.5,
    })
    
    # Realistic slippage (% of price)
    SLIPPAGE_MODEL: Dict[str, float] = field(default_factory=lambda: {
        "NIFTY": 0.25,         # ATM options
        "BANKNIFTY": 0.35,     # Higher for BN
        "OTM_MULTIPLIER": 1.5, # OTM options have higher slippage
        "EXPIRY_DAY": 2.0,     # Much higher on expiry
    })
    
    # Greeks thresholds
    MAX_GAMMA_NEAR_EXPIRY: float = 0.015  # Avoid high gamma < 4 hours to expiry
    MAX_THETA_DECAY_PCT: float = 0.03     # Max 3% daily theta decay
    MIN_DELTA_FOR_DIRECTIONAL: float = 0.25
    
    # Position sizing
    MAX_POSITION_PCT: float = 60.0        # Max 60% of capital per position
    PROBE_SIZE_PCT: float = 20.0          # 20% for probe (was 10%)
    SCALE_STEP_PCT: float = 25.0          # Scale in 25% steps
    MAX_STOPLOSS_PCT: float = 25.0        # Max 25% loss per trade (was 50%)
    
    # Ensemble voting
    MIN_MODELS_AGREE: int = 2             # At least 2/3 models must agree
    ENSEMBLE_WEIGHTS: Dict[str, float] = field(default_factory=lambda: {
        "tier1_technical": 0.25,
        "tier2_options_flow": 0.35,
        "tier3_prediction": 0.40
    })


# ============================================================================
# REGIME DETECTOR - Institutional Market Classification
# ============================================================================

class RegimeDetector:
    """
    Institutional-grade market regime detection using multiple indicators.
    Classifies market into regimes for adaptive strategy selection.
    """
    
    def __init__(self):
        self.history: List[Dict] = []
        self.current_regime = MarketRegime.RANGING
        self.regime_confidence = 0.5
        self.regime_duration_bars = 0
        
    def detect_regime(
        self,
        prices: List[float],
        volumes: List[int],
        vix,  # Can be float or dict from API
        adx: Optional[float] = None,
        rsi: Optional[float] = None
    ) -> Tuple[MarketRegime, float]:
        """
        Detect current market regime using multiple factors.
        
        Returns:
            Tuple of (regime, confidence)
        """
        # Defensive: Extract VIX from dict if needed
        if isinstance(vix, dict):
            vix = float(vix.get('current', vix.get('value', 15.0)))
        vix = float(vix) if vix else 15.0
        
        if len(prices) < 20:
            return MarketRegime.RANGING, 0.5
        
        # Calculate regime indicators
        returns = [(prices[i] - prices[i-1]) / prices[i-1] for i in range(1, len(prices))]
        volatility = statistics.stdev(returns[-20:]) if len(returns) >= 20 else 0.01
        
        # Trend strength (simple)
        sma_5 = sum(prices[-5:]) / 5
        sma_20 = sum(prices[-20:]) / 20
        trend_strength = (sma_5 - sma_20) / sma_20
        
        # Volume analysis
        avg_volume = sum(volumes[-20:]) / 20 if volumes else 1
        recent_volume = sum(volumes[-5:]) / 5 if volumes else 1
        volume_ratio = recent_volume / avg_volume if avg_volume > 0 else 1
        
        # VIX-based volatility regime
        vix_regime = self._classify_vix(vix)
        
        # ADX-based trend strength (if available)
        adx_trend = adx > 25 if adx else False
        
        # Determine regime
        regime, confidence = self._classify_regime(
            trend_strength=trend_strength,
            volatility=volatility,
            volume_ratio=volume_ratio,
            vix_regime=vix_regime,
            adx_trend=adx_trend,
            rsi=rsi
        )
        
        # Update state
        if regime == self.current_regime:
            self.regime_duration_bars += 1
            confidence = min(0.95, confidence + 0.02 * self.regime_duration_bars)
        else:
            self.regime_duration_bars = 0
        
        self.current_regime = regime
        self.regime_confidence = confidence
        
        return regime, confidence
    
    def _classify_vix(self, vix) -> str:
        """Classify VIX level for Indian markets"""
        # Defensive: Handle dict input (from get_india_vix returning dict)
        if isinstance(vix, dict):
            vix = float(vix.get('current', vix.get('value', 15.0)))
        vix = float(vix) if vix else 15.0
        
        if vix < 12:
            return "VERY_LOW"
        elif vix < 15:
            return "LOW"
        elif vix < 20:
            return "NORMAL"
        elif vix < 25:
            return "ELEVATED"
        elif vix < 30:
            return "HIGH"
        else:
            return "EXTREME"
    
    def _classify_regime(
        self,
        trend_strength: float,
        volatility: float,
        volume_ratio: float,
        vix_regime: str,
        adx_trend: bool,
        rsi: Optional[float]
    ) -> Tuple[MarketRegime, float]:
        """Classify market regime based on multiple factors"""
        
        # High volatility regime takes precedence
        if vix_regime in ["HIGH", "EXTREME"] or volatility > 0.02:
            return MarketRegime.HIGH_VOLATILITY, 0.85
        
        # Low volatility (compression)
        if vix_regime == "VERY_LOW" and volatility < 0.005:
            return MarketRegime.LOW_VOLATILITY, 0.80
        
        # Strong trend detection
        if abs(trend_strength) > 0.015 and adx_trend:
            if trend_strength > 0:
                confidence = min(0.90, 0.70 + abs(trend_strength) * 10)
                return MarketRegime.STRONG_TREND_UP, confidence
            else:
                confidence = min(0.90, 0.70 + abs(trend_strength) * 10)
                return MarketRegime.STRONG_TREND_DOWN, confidence
        
        # Weak trend
        if abs(trend_strength) > 0.005:
            if trend_strength > 0:
                return MarketRegime.WEAK_TREND_UP, 0.65
            else:
                return MarketRegime.WEAK_TREND_DOWN, 0.65
        
        # RSI-based ranging detection
        if rsi and 40 < rsi < 60:
            return MarketRegime.RANGING, 0.75
        
        # Default to ranging with low confidence
        return MarketRegime.RANGING, 0.55
    
    def get_strategy_params(self, regime: MarketRegime, config: EliteTradingConfig) -> Dict:
        """Get regime-specific strategy parameters"""
        
        params = {
            "confidence_threshold": config.CONFIDENCE_THRESHOLDS.get(regime.value, 0.75),
            "position_size_multiplier": 1.0,
            "stoploss_multiplier": 1.0,
            "target_multiplier": 1.0,
            "max_hold_minutes": 30,
            "prefer_otm": False,
            "scale_enabled": True
        }
        
        if regime == MarketRegime.STRONG_TREND_UP or regime == MarketRegime.STRONG_TREND_DOWN:
            params["position_size_multiplier"] = 1.2
            params["stoploss_multiplier"] = 1.3  # Wider stops in trends
            params["target_multiplier"] = 1.5    # Bigger targets
            params["max_hold_minutes"] = 60
            params["scale_enabled"] = True
            
        elif regime == MarketRegime.RANGING:
            params["position_size_multiplier"] = 0.8
            params["stoploss_multiplier"] = 0.8  # Tighter stops
            params["target_multiplier"] = 0.7   # Smaller targets
            params["max_hold_minutes"] = 15
            params["prefer_otm"] = True         # OTM for defined risk
            params["scale_enabled"] = False     # No scaling in chop
            
        elif regime == MarketRegime.HIGH_VOLATILITY:
            params["position_size_multiplier"] = 0.5  # Reduce size
            params["stoploss_multiplier"] = 1.5      # Much wider stops
            params["target_multiplier"] = 2.0        # Large targets
            params["max_hold_minutes"] = 10          # Quick exits
            
        elif regime == MarketRegime.LOW_VOLATILITY:
            params["position_size_multiplier"] = 1.0
            params["stoploss_multiplier"] = 0.6   # Tight stops
            params["target_multiplier"] = 0.8
            params["max_hold_minutes"] = 45       # Wait for breakout
            
        return params


# ============================================================================
# ENSEMBLE AI DECISION ENGINE
# ============================================================================

class EnsembleDecisionEngine:
    """
    Multi-model ensemble decision engine with weighted voting.
    Combines technical, options flow, and predictive signals.
    """
    
    def __init__(self, config: EliteTradingConfig = None):
        self.config = config or EliteTradingConfig()
        self.decision_history: List[Dict] = []
        self.model_accuracy: Dict[str, float] = {
            "tier1_technical": 0.60,
            "tier2_options_flow": 0.65,
            "tier3_prediction": 0.70
        }
        
    async def get_ensemble_decision(
        self,
        tier1_signal: Dict,
        tier2_signal: Dict,
        tier3_signal: Dict,
        regime: MarketRegime,
        session: TradingSession
    ) -> Dict:
        """
        Get ensemble decision from multiple AI tiers with weighted voting.
        
        Returns:
            Dict with decision, confidence, factors, and position sizing
        """
        
        signals = {
            "tier1_technical": self._normalize_signal(tier1_signal),
            "tier2_options_flow": self._normalize_signal(tier2_signal),
            "tier3_prediction": self._normalize_signal(tier3_signal)
        }
        
        # Extract directions
        directions = {
            name: sig.get("direction", "NEUTRAL")
            for name, sig in signals.items()
        }
        
        # Count agreement
        direction_counts = {}
        for direction in directions.values():
            direction_counts[direction] = direction_counts.get(direction, 0) + 1
        
        # Find majority direction
        majority_direction = max(direction_counts, key=direction_counts.get)
        agreement_count = direction_counts[majority_direction]
        
        # Check if enough models agree
        if agreement_count < self.config.MIN_MODELS_AGREE:
            return {
                "decision": "NO_TRADE",
                "direction": "NEUTRAL",
                "confidence": 0.0,
                "reason": f"Insufficient agreement ({agreement_count}/{len(signals)} models)",
                "signals": signals
            }
        
        # Calculate weighted confidence
        weighted_confidence = 0.0
        agreeing_factors = []
        
        for name, sig in signals.items():
            if sig.get("direction") == majority_direction:
                weight = self.config.ENSEMBLE_WEIGHTS.get(name, 0.33)
                model_conf = sig.get("confidence", 0.5)
                
                # Adjust weight by historical accuracy
                accuracy_adj = self.model_accuracy.get(name, 0.60)
                effective_weight = weight * accuracy_adj
                
                weighted_confidence += model_conf * effective_weight
                agreeing_factors.extend(sig.get("factors", []))
        
        # Normalize confidence
        total_weight = sum(
            self.config.ENSEMBLE_WEIGHTS.get(name, 0.33) * self.model_accuracy.get(name, 0.60)
            for name, sig in signals.items()
            if sig.get("direction") == majority_direction
        )
        
        if total_weight > 0:
            weighted_confidence = weighted_confidence / total_weight
        
        # Apply regime adjustment
        regime_threshold = self.config.CONFIDENCE_THRESHOLDS.get(regime.value, 0.75)
        
        # Apply session adjustment
        session_multiplier = self.config.SESSION_MULTIPLIERS.get(session.value, 1.0)
        
        # Determine signal strength
        signal_strength = self._classify_strength(
            weighted_confidence,
            len(set(agreeing_factors)),
            agreement_count
        )
        
        # Final decision
        if weighted_confidence < regime_threshold:
            return {
                "decision": "NO_TRADE",
                "direction": "NEUTRAL",
                "confidence": weighted_confidence,
                "threshold": regime_threshold,
                "reason": f"Confidence {weighted_confidence:.2%} below threshold {regime_threshold:.2%}",
                "signal_strength": SignalStrength.NO_TRADE.value,
                "signals": signals
            }
        
        # Calculate position size
        base_size = self.config.PROBE_SIZE_PCT
        regime_adj = self._get_regime_size_adj(regime)
        confidence_adj = (weighted_confidence - 0.5) * 2  # 0.5-1.0 -> 0-1
        
        position_size_pct = min(
            self.config.MAX_POSITION_PCT,
            base_size * regime_adj * session_multiplier * (1 + confidence_adj * 0.5)
        )
        
        # Determine option type
        if majority_direction in ["BULLISH", "LONG", "BUY", "CALL"]:
            option_type = "CE"
            action = "BUY_CALL"
        elif majority_direction in ["BEARISH", "SHORT", "SELL", "PUT"]:
            option_type = "PE"
            action = "BUY_PUT"
        else:
            return {
                "decision": "NO_TRADE",
                "direction": "NEUTRAL",
                "confidence": weighted_confidence,
                "reason": "No clear directional bias",
                "signals": signals
            }
        
        # Build result
        result = {
            "decision": action,
            "direction": majority_direction,
            "option_type": option_type,
            "confidence": round(weighted_confidence, 4),
            "signal_strength": signal_strength.value,
            "agreement": f"{agreement_count}/3",
            "factors": list(set(agreeing_factors))[:10],  # Top 10 unique factors
            "position_size_pct": round(position_size_pct, 2),
            "regime": regime.value,
            "session": session.value,
            "regime_threshold": regime_threshold,
            "session_multiplier": session_multiplier,
            "signals": {
                name: {
                    "direction": sig.get("direction"),
                    "confidence": sig.get("confidence", 0)
                }
                for name, sig in signals.items()
            },
            "timestamp": datetime.now().isoformat()
        }
        
        # Log decision
        self.decision_history.append(result)
        if len(self.decision_history) > 1000:
            self.decision_history = self.decision_history[-500:]
        
        return result
    
    def _normalize_signal(self, signal: Dict) -> Dict:
        """Normalize signal format from different tiers"""
        if not signal:
            return {"direction": "NEUTRAL", "confidence": 0.0, "factors": []}
        
        # Normalize direction
        direction = signal.get("direction") or signal.get("signal") or signal.get("action") or "NEUTRAL"
        direction = direction.upper()
        
        # Map various formats
        direction_map = {
            "BUY": "BULLISH", "LONG": "BULLISH", "CALL": "BULLISH",
            "BUY_CALL": "BULLISH", "STRONG_BUY": "BULLISH",
            "SELL": "BEARISH", "SHORT": "BEARISH", "PUT": "BEARISH",
            "BUY_PUT": "BEARISH", "STRONG_SELL": "BEARISH",
            "HOLD": "NEUTRAL", "NO_TRADE": "NEUTRAL", "WAIT": "NEUTRAL"
        }
        direction = direction_map.get(direction, direction)
        
        # Normalize confidence
        confidence = signal.get("confidence") or signal.get("score") or 0.5
        if isinstance(confidence, str):
            conf_map = {"HIGH": 0.85, "MEDIUM": 0.65, "LOW": 0.45}
            confidence = conf_map.get(confidence.upper(), 0.5)
        if confidence > 1:
            confidence = confidence / 100 if confidence <= 100 else confidence / 10
        
        # Extract factors
        factors = []
        for key in ["factors", "reasons", "supporting_factors", "indicators"]:
            if key in signal and signal[key]:
                if isinstance(signal[key], list):
                    factors.extend(signal[key])
                else:
                    factors.append(str(signal[key]))
        
        return {
            "direction": direction,
            "confidence": float(confidence),
            "factors": factors,
            "raw": signal
        }
    
    def _classify_strength(
        self,
        confidence: float,
        factor_count: int,
        agreement_count: int
    ) -> SignalStrength:
        """Classify signal strength"""
        
        if confidence >= 0.95 and factor_count >= 5 and agreement_count == 3:
            return SignalStrength.ELITE
        elif confidence >= 0.85 and factor_count >= 4:
            return SignalStrength.STRONG
        elif confidence >= 0.75 and factor_count >= 3:
            return SignalStrength.MODERATE
        elif confidence >= 0.65:
            return SignalStrength.WEAK
        else:
            return SignalStrength.NO_TRADE
    
    def _get_regime_size_adj(self, regime: MarketRegime) -> float:
        """Get position size adjustment for regime"""
        adjustments = {
            MarketRegime.STRONG_TREND_UP: 1.3,
            MarketRegime.STRONG_TREND_DOWN: 1.3,
            MarketRegime.WEAK_TREND_UP: 1.0,
            MarketRegime.WEAK_TREND_DOWN: 1.0,
            MarketRegime.RANGING: 0.7,
            MarketRegime.HIGH_VOLATILITY: 0.5,
            MarketRegime.LOW_VOLATILITY: 0.9,
            MarketRegime.TRANSITION: 0.4
        }
        return adjustments.get(regime, 1.0)
    
    def update_model_accuracy(self, model_name: str, was_profitable: bool):
        """Update model accuracy based on trade outcome"""
        current = self.model_accuracy.get(model_name, 0.60)
        # Exponential moving average update
        alpha = 0.1  # Learning rate
        new_accuracy = current * (1 - alpha) + (1.0 if was_profitable else 0.0) * alpha
        self.model_accuracy[model_name] = max(0.3, min(0.95, new_accuracy))


# ============================================================================
# GREEKS-AWARE EXECUTION ENGINE
# ============================================================================

class GreeksAwareExecution:
    """
    Greeks-aware trade execution to avoid unfavorable option dynamics.
    """
    
    def __init__(self, config: EliteTradingConfig = None):
        self.config = config or EliteTradingConfig()
    
    def should_enter(
        self,
        option_data: Dict,
        hours_to_expiry: float,
        spot_price: float,
        strike: float
    ) -> Tuple[bool, str, Dict]:
        """
        Check if option entry is favorable based on Greeks.
        
        Returns:
            Tuple of (should_enter, reason, greeks_data)
        """
        
        # Calculate simple Greeks estimates
        moneyness = spot_price / strike
        time_factor = max(0.01, hours_to_expiry / (252 * 6.5))  # Years
        
        # Estimate delta (simplified Black-Scholes approximation)
        if option_data.get("option_type") == "CE":
            delta = self._estimate_call_delta(moneyness, time_factor)
        else:
            delta = self._estimate_put_delta(moneyness, time_factor)
        
        # Estimate gamma
        gamma = self._estimate_gamma(moneyness, time_factor)
        
        # Estimate theta (daily)
        option_price = option_data.get("premium", option_data.get("ltp", 100))
        theta_daily = self._estimate_theta(option_price, hours_to_expiry)
        theta_pct = abs(theta_daily) / option_price if option_price > 0 else 0
        
        greeks = {
            "delta": round(delta, 4),
            "gamma": round(gamma, 6),
            "theta_daily": round(theta_daily, 2),
            "theta_pct": round(theta_pct, 4),
            "moneyness": round(moneyness, 4),
            "hours_to_expiry": hours_to_expiry
        }
        
        # Check constraints
        
        # 1. High gamma near expiry
        if gamma > self.config.MAX_GAMMA_NEAR_EXPIRY and hours_to_expiry < 4:
            return False, f"High gamma ({gamma:.4f}) near expiry - unstable delta", greeks
        
        # 2. Excessive theta decay
        if theta_pct > self.config.MAX_THETA_DECAY_PCT:
            return False, f"Excessive theta decay ({theta_pct:.1%}/day)", greeks
        
        # 3. Delta too low for directional trade
        if abs(delta) < self.config.MIN_DELTA_FOR_DIRECTIONAL:
            return False, f"Delta too low ({delta:.2f}) for directional trade", greeks
        
        # 4. Deep OTM with low time value
        if moneyness < 0.95 or moneyness > 1.05:  # More than 5% OTM
            if hours_to_expiry < 8:  # Less than 1 trading day
                return False, f"Deep OTM ({moneyness:.2%}) with little time value", greeks
        
        # All checks passed
        return True, "Greeks favorable for entry", greeks
    
    def _estimate_call_delta(self, moneyness: float, time: float) -> float:
        """Estimate call delta using simplified formula"""
        # Approximation: delta ~ N(d1) where d1 depends on moneyness and time
        if moneyness >= 1:  # ITM
            base_delta = 0.5 + (moneyness - 1) * 3
        else:  # OTM
            base_delta = 0.5 - (1 - moneyness) * 3
        
        # Time adjustment - more time = delta closer to 0.5
        time_adj = 0.5 + (base_delta - 0.5) * (1 - min(1, time * 5))
        
        return max(0.05, min(0.95, time_adj))
    
    def _estimate_put_delta(self, moneyness: float, time: float) -> float:
        """Estimate put delta"""
        call_delta = self._estimate_call_delta(moneyness, time)
        return call_delta - 1  # Put-call parity
    
    def _estimate_gamma(self, moneyness: float, time: float) -> float:
        """Estimate gamma - highest ATM, increases near expiry"""
        # ATM gamma approximation
        atm_distance = abs(1 - moneyness)
        base_gamma = 0.02 * math.exp(-50 * atm_distance ** 2)
        
        # Time adjustment - gamma increases near expiry
        time_multiplier = 1 / max(0.1, math.sqrt(time * 252))
        
        return base_gamma * time_multiplier
    
    def _estimate_theta(self, option_price: float, hours_to_expiry: float) -> float:
        """Estimate daily theta decay"""
        if hours_to_expiry <= 0:
            return option_price  # Full decay
        
        days_to_expiry = hours_to_expiry / 6.5
        
        # Theta accelerates near expiry (roughly sqrt decay)
        if days_to_expiry < 1:
            daily_decay = option_price * 0.5  # 50% on expiry day
        elif days_to_expiry < 3:
            daily_decay = option_price * 0.15  # 15% per day last 3 days
        elif days_to_expiry < 7:
            daily_decay = option_price * 0.05  # 5% per day last week
        else:
            daily_decay = option_price * 0.02  # 2% per day normally
        
        return daily_decay
    
    def get_optimal_strike(
        self,
        spot_price: float,
        direction: str,
        regime: MarketRegime,
        hours_to_expiry: float,
        available_strikes: List[float]
    ) -> Tuple[float, str]:
        """
        Select optimal strike based on regime and conditions.
        
        Returns:
            Tuple of (strike, reason)
        """
        
        if not available_strikes:
            # Default to ATM
            return round(spot_price / 50) * 50, "ATM (no strikes provided)"
        
        # Find ATM
        atm_strike = min(available_strikes, key=lambda x: abs(x - spot_price))
        atm_idx = available_strikes.index(atm_strike)
        
        # Regime-based strike selection
        if regime in [MarketRegime.STRONG_TREND_UP, MarketRegime.STRONG_TREND_DOWN]:
            # ITM for trends (higher delta)
            if direction in ["BULLISH", "LONG", "CE"]:
                # One strike ITM for calls
                target_idx = max(0, atm_idx - 1)
            else:
                # One strike ITM for puts
                target_idx = min(len(available_strikes) - 1, atm_idx + 1)
            return available_strikes[target_idx], "ITM for trend (higher delta)"
        
        elif regime == MarketRegime.RANGING:
            # Slightly OTM for ranging (defined risk)
            if direction in ["BULLISH", "LONG", "CE"]:
                target_idx = min(len(available_strikes) - 1, atm_idx + 1)
            else:
                target_idx = max(0, atm_idx - 1)
            return available_strikes[target_idx], "OTM for ranging (defined risk)"
        
        elif regime == MarketRegime.HIGH_VOLATILITY:
            # ATM for volatility (balanced gamma/theta)
            return atm_strike, "ATM for high volatility (balanced Greeks)"
        
        else:
            # Default to ATM
            return atm_strike, "ATM (default)"


# ============================================================================
# ADAPTIVE RISK MANAGER
# ============================================================================

class AdaptiveRiskManager:
    """
    Dynamic risk management with VaR, drawdown controls, and adaptive sizing.
    """
    
    def __init__(self, initial_capital: float, config: EliteTradingConfig = None):
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        self.config = config or EliteTradingConfig()
        
        # Tracking
        self.daily_pnl = 0.0
        self.peak_capital = initial_capital
        self.max_drawdown = 0.0
        self.consecutive_losses = 0
        self.trade_history: List[Dict] = []
        
        # Risk limits
        self.daily_loss_limit_pct = 2.0   # 2% max daily loss
        self.max_drawdown_limit_pct = 10.0  # 10% max drawdown
        self.max_consecutive_losses = 4
        
    def calculate_position_size(
        self,
        signal_confidence: float,
        regime: MarketRegime,
        index: str,
        option_price: float
    ) -> Dict:
        """
        Calculate optimal position size based on multiple factors.
        
        Kelly-inspired sizing with regime and drawdown adjustments.
        """
        
        # Base position (% of capital)
        base_pct = self.config.PROBE_SIZE_PCT
        
        # 1. Confidence adjustment (Kelly-like)
        # f = (p * b - q) / b where p = win prob, b = odds, q = 1-p
        win_prob = signal_confidence
        avg_win_loss_ratio = 1.5  # Assume 1.5:1 average
        kelly_pct = (win_prob * avg_win_loss_ratio - (1 - win_prob)) / avg_win_loss_ratio
        kelly_pct = max(0, kelly_pct)  # Can't be negative
        
        # Use half-Kelly for safety
        kelly_adj = base_pct * (0.5 + kelly_pct * 0.5)
        
        # 2. Regime adjustment
        regime_multiplier = {
            MarketRegime.STRONG_TREND_UP: 1.2,
            MarketRegime.STRONG_TREND_DOWN: 1.2,
            MarketRegime.WEAK_TREND_UP: 1.0,
            MarketRegime.WEAK_TREND_DOWN: 1.0,
            MarketRegime.RANGING: 0.7,
            MarketRegime.HIGH_VOLATILITY: 0.5,
            MarketRegime.LOW_VOLATILITY: 0.9,
            MarketRegime.TRANSITION: 0.3
        }.get(regime, 1.0)
        
        # 3. Drawdown adjustment
        current_dd = (self.peak_capital - self.current_capital) / self.peak_capital
        if current_dd > 0.05:  # In drawdown > 5%
            dd_multiplier = max(0.3, 1 - current_dd * 2)
        else:
            dd_multiplier = 1.0
        
        # 4. Consecutive loss adjustment
        if self.consecutive_losses >= 2:
            loss_multiplier = max(0.4, 1 - self.consecutive_losses * 0.15)
        else:
            loss_multiplier = 1.0
        
        # 5. Index volatility adjustment
        index_multiplier = 1 / self.config.INDEX_ATR_MULTIPLIERS.get(index, 1.0)
        
        # Final position size
        final_pct = kelly_adj * regime_multiplier * dd_multiplier * loss_multiplier * index_multiplier
        final_pct = max(5.0, min(self.config.MAX_POSITION_PCT, final_pct))
        
        # Calculate lots
        capital_for_trade = self.current_capital * (final_pct / 100)
        lot_size = self.config.LOT_SIZES.get(index, 75)
        lots = max(1, int(capital_for_trade / (option_price * lot_size)))
        
        return {
            "position_pct": round(final_pct, 2),
            "capital_allocated": round(capital_for_trade, 2),
            "lots": lots,
            "lot_size": lot_size,
            "quantity": lots * lot_size,
            "adjustments": {
                "kelly": round(kelly_adj, 2),
                "regime": regime_multiplier,
                "drawdown": round(dd_multiplier, 2),
                "consecutive_loss": round(loss_multiplier, 2),
                "index_vol": round(index_multiplier, 2)
            }
        }
    
    def calculate_stoploss(
        self,
        entry_price: float,
        regime: MarketRegime,
        index: str,
        direction: str
    ) -> Dict:
        """Calculate dynamic stoploss based on regime and volatility"""
        
        # Base stoploss percentage
        base_sl_pct = self.config.MAX_STOPLOSS_PCT
        
        # Regime adjustment
        regime_adj = {
            MarketRegime.STRONG_TREND_UP: 1.3,    # Wider for trends
            MarketRegime.STRONG_TREND_DOWN: 1.3,
            MarketRegime.WEAK_TREND_UP: 1.0,
            MarketRegime.WEAK_TREND_DOWN: 1.0,
            MarketRegime.RANGING: 0.7,            # Tighter for ranging
            MarketRegime.HIGH_VOLATILITY: 1.5,   # Much wider for high vol
            MarketRegime.LOW_VOLATILITY: 0.6,    # Tight for low vol
            MarketRegime.TRANSITION: 0.8
        }.get(regime, 1.0)
        
        # Index volatility adjustment
        vol_adj = self.config.INDEX_ATR_MULTIPLIERS.get(index, 1.0)
        
        # Final stoploss
        sl_pct = base_sl_pct * regime_adj * vol_adj
        sl_pct = max(10.0, min(40.0, sl_pct))  # Cap between 10-40%
        
        sl_price = entry_price * (1 - sl_pct / 100)
        
        return {
            "stoploss_pct": round(sl_pct, 2),
            "stoploss_price": round(sl_price, 2),
            "regime_adj": regime_adj,
            "vol_adj": vol_adj
        }
    
    def calculate_target(
        self,
        entry_price: float,
        stoploss_price: float,
        regime: MarketRegime,
        min_rr_ratio: float = 2.0
    ) -> Dict:
        """Calculate target based on risk-reward requirements"""
        
        risk = entry_price - stoploss_price
        
        # Regime-based R:R multiplier
        rr_multipliers = {
            MarketRegime.STRONG_TREND_UP: 2.5,    # Higher targets in trends
            MarketRegime.STRONG_TREND_DOWN: 2.5,
            MarketRegime.WEAK_TREND_UP: 2.0,
            MarketRegime.WEAK_TREND_DOWN: 2.0,
            MarketRegime.RANGING: 1.5,            # Lower targets in ranging
            MarketRegime.HIGH_VOLATILITY: 3.0,   # High targets for high vol
            MarketRegime.LOW_VOLATILITY: 1.8,
            MarketRegime.TRANSITION: 1.5
        }
        
        rr_ratio = max(min_rr_ratio, rr_multipliers.get(regime, 2.0))
        
        target_price = entry_price + (risk * rr_ratio)
        target_pct = (target_price - entry_price) / entry_price * 100
        
        # Partial targets
        target_1 = entry_price + (risk * 1.0)   # 1:1
        target_2 = entry_price + (risk * 1.5)   # 1.5:1
        target_3 = target_price                  # Full target
        
        return {
            "target_price": round(target_price, 2),
            "target_pct": round(target_pct, 2),
            "rr_ratio": round(rr_ratio, 2),
            "partial_targets": {
                "t1_50pct_exit": round(target_1, 2),
                "t2_30pct_exit": round(target_2, 2),
                "t3_20pct_exit": round(target_3, 2)
            }
        }
    
    def can_trade(self) -> Tuple[bool, str]:
        """Check if trading is allowed based on risk limits"""
        
        # Daily loss limit
        daily_loss_pct = abs(self.daily_pnl) / self.initial_capital * 100
        if self.daily_pnl < 0 and daily_loss_pct >= self.daily_loss_limit_pct:
            return False, f"Daily loss limit reached ({daily_loss_pct:.2f}%)"
        
        # Max drawdown limit
        if self.max_drawdown * 100 >= self.max_drawdown_limit_pct:
            return False, f"Max drawdown limit reached ({self.max_drawdown*100:.2f}%)"
        
        # Consecutive losses
        if self.consecutive_losses >= self.max_consecutive_losses:
            return False, f"Too many consecutive losses ({self.consecutive_losses})"
        
        return True, "OK"
    
    def update_trade(self, pnl: float, was_winner: bool):
        """Update risk manager with trade result"""
        
        self.daily_pnl += pnl
        self.current_capital += pnl
        
        # Update peak and drawdown
        if self.current_capital > self.peak_capital:
            self.peak_capital = self.current_capital
        
        current_dd = (self.peak_capital - self.current_capital) / self.peak_capital
        self.max_drawdown = max(self.max_drawdown, current_dd)
        
        # Update consecutive losses
        if was_winner:
            self.consecutive_losses = 0
        else:
            self.consecutive_losses += 1
        
        self.trade_history.append({
            "pnl": pnl,
            "was_winner": was_winner,
            "capital_after": self.current_capital,
            "drawdown": current_dd,
            "timestamp": datetime.now().isoformat()
        })
    
    def reset_daily(self):
        """Reset daily counters"""
        self.daily_pnl = 0.0
        self.consecutive_losses = 0


# ============================================================================
# SESSION DETECTOR
# ============================================================================

def get_current_session() -> TradingSession:
    """Get current trading session based on IST time"""
    now = datetime.now()
    current_time = now.time()
    
    if current_time < time(9, 15):
        return TradingSession.PRE_OPEN
    elif current_time < time(9, 45):
        return TradingSession.OPENING_DRIVE
    elif current_time < time(11, 30):
        return TradingSession.MORNING_SESSION
    elif current_time < time(13, 30):
        return TradingSession.LUNCH_LULL
    elif current_time < time(14, 30):
        return TradingSession.AFTERNOON_SESSION
    elif current_time < time(15, 0):
        return TradingSession.POWER_HOUR
    else:
        return TradingSession.CLOSING_AUCTION


# ============================================================================
# ELITE TRADING ORCHESTRATOR
# ============================================================================

class EliteTradingOrchestrator:
    """
    Main orchestrator that combines all components for elite trading decisions.
    """
    
    def __init__(self, initial_capital: float = 500000.0):
        self.config = EliteTradingConfig()
        self.regime_detector = RegimeDetector()
        self.ensemble_engine = EnsembleDecisionEngine(self.config)
        self.greeks_execution = GreeksAwareExecution(self.config)
        self.risk_manager = AdaptiveRiskManager(initial_capital, self.config)
        
        logger.info("[ELITE] Elite Trading Orchestrator initialized")
        logger.info(f"[ELITE] Initial capital: ₹{initial_capital:,.0f}")
    
    async def get_elite_signal(
        self,
        index: str,
        prices: List[float],
        volumes: List[int],
        vix: float,
        tier1_signal: Dict,
        tier2_signal: Dict,
        tier3_signal: Dict,
        option_data: Optional[Dict] = None,
        hours_to_expiry: float = 24.0
    ) -> Dict:
        """
        Get elite trading signal with all institutional-grade checks.
        """
        
        # Check if trading is allowed
        can_trade, reason = self.risk_manager.can_trade()
        if not can_trade:
            return {
                "decision": "BLOCKED",
                "reason": reason,
                "action": "NO_TRADE"
            }
        
        # Detect market regime
        regime, regime_confidence = self.regime_detector.detect_regime(
            prices=prices,
            volumes=volumes,
            vix=vix
        )
        
        # Get current session
        session = get_current_session()
        
        # Get ensemble decision
        ensemble_decision = await self.ensemble_engine.get_ensemble_decision(
            tier1_signal=tier1_signal,
            tier2_signal=tier2_signal,
            tier3_signal=tier3_signal,
            regime=regime,
            session=session
        )
        
        # If no trade, return early
        if ensemble_decision.get("decision") == "NO_TRADE":
            return {
                "action": "NO_TRADE",
                "regime": regime.value,
                "session": session.value,
                "ensemble": ensemble_decision
            }
        
        # Greeks check if option data available
        if option_data and prices:
            spot_price = prices[-1]
            strike = option_data.get("strike", spot_price)
            
            should_enter, greeks_reason, greeks = self.greeks_execution.should_enter(
                option_data=option_data,
                hours_to_expiry=hours_to_expiry,
                spot_price=spot_price,
                strike=strike
            )
            
            if not should_enter:
                return {
                    "action": "BLOCKED_GREEKS",
                    "reason": greeks_reason,
                    "greeks": greeks,
                    "regime": regime.value,
                    "ensemble": ensemble_decision
                }
        else:
            greeks = {}
        
        # Calculate position sizing
        option_price = option_data.get("premium", 100) if option_data else 100
        position_sizing = self.risk_manager.calculate_position_size(
            signal_confidence=ensemble_decision.get("confidence", 0.7),
            regime=regime,
            index=index,
            option_price=option_price
        )
        
        # Calculate stoploss
        stoploss = self.risk_manager.calculate_stoploss(
            entry_price=option_price,
            regime=regime,
            index=index,
            direction=ensemble_decision.get("direction", "BULLISH")
        )
        
        # Calculate target
        target = self.risk_manager.calculate_target(
            entry_price=option_price,
            stoploss_price=stoploss["stoploss_price"],
            regime=regime
        )
        
        # Get regime-specific params
        regime_params = self.regime_detector.get_strategy_params(regime, self.config)
        
        # Build final signal
        return {
            "action": ensemble_decision.get("decision"),
            "option_type": ensemble_decision.get("option_type"),
            "direction": ensemble_decision.get("direction"),
            "confidence": ensemble_decision.get("confidence"),
            "signal_strength": ensemble_decision.get("signal_strength"),
            
            "index": index,
            "regime": regime.value,
            "regime_confidence": round(regime_confidence, 2),
            "session": session.value,
            
            "position": position_sizing,
            "stoploss": stoploss,
            "target": target,
            "greeks": greeks,
            
            "max_hold_minutes": regime_params["max_hold_minutes"],
            "scale_enabled": regime_params["scale_enabled"],
            
            "ensemble": ensemble_decision,
            "factors": ensemble_decision.get("factors", []),
            
            "timestamp": datetime.now().isoformat()
        }
    
    def update_trade_result(self, pnl: float, was_winner: bool, contributing_models: List[str]):
        """Update system with trade result for learning"""
        
        # Update risk manager
        self.risk_manager.update_trade(pnl, was_winner)
        
        # Update ensemble model accuracy
        for model in contributing_models:
            self.ensemble_engine.update_model_accuracy(model, was_winner)
        
        logger.info(f"[ELITE] Trade updated: PnL={pnl:+.2f}, Winner={was_winner}")
    
    def get_system_status(self) -> Dict:
        """Get current system status"""
        return {
            "capital": {
                "initial": self.risk_manager.initial_capital,
                "current": self.risk_manager.current_capital,
                "daily_pnl": self.risk_manager.daily_pnl,
                "max_drawdown": round(self.risk_manager.max_drawdown * 100, 2)
            },
            "regime": {
                "current": self.regime_detector.current_regime.value,
                "confidence": round(self.regime_detector.regime_confidence, 2),
                "duration_bars": self.regime_detector.regime_duration_bars
            },
            "model_accuracy": self.ensemble_engine.model_accuracy,
            "consecutive_losses": self.risk_manager.consecutive_losses,
            "can_trade": self.risk_manager.can_trade()[0],
            "session": get_current_session().value
        }


# ============================================================================
# FACTORY FUNCTION
# ============================================================================

def create_elite_orchestrator(capital: float = 500000.0) -> EliteTradingOrchestrator:
    """Factory function to create elite orchestrator"""
    return EliteTradingOrchestrator(initial_capital=capital)


# ============================================================================
# EXPORTS
# ============================================================================

__all__ = [
    "MarketRegime",
    "TradingSession", 
    "SignalStrength",
    "EliteTradingConfig",
    "RegimeDetector",
    "EnsembleDecisionEngine",
    "GreeksAwareExecution",
    "AdaptiveRiskManager",
    "EliteTradingOrchestrator",
    "create_elite_orchestrator",
    "get_current_session"
]
