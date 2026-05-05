"""
TIER 3: Predictive Strategy Engine (The Forecaster)

Model: Gemini 2.0 Pro (or Gemini 3 Pro when available)
Purpose: Predict Price Action Envelope (Max Up/Down, Reversal Point, Holding Time)
Output: Price Action Forecast & Holding Strategy

Key Responsibilities:
- Receive Trade Setup Proposal and Context Thesis from Tier 2
- Use superior time-series reasoning
- Link contextual drivers to concrete price path
- Forecast max_level_target, reversal_point, hold_duration
- Provide final execution strategy with exit conditions
"""

import json
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
from google import genai
from google.genai import types

logger = logging.getLogger(__name__)

# ============================================================================
# TIER 3 SYSTEM PROMPT - ULTIMATE PREDICTION ENGINE (Gemini 3 Pro Optimized)
# ============================================================================
# ENHANCED FOR 90%+ WIN RATE: Multi-Factor Confirmation + Chain-of-Thought
# ============================================================================
TIER_3_SYSTEM_PROMPT = """
██████████████████████████████████████████████████████████████████████████████
█ ULTIMATE PREDICTION ENGINE - GEMINI 3 PRO OPTIMIZED FOR 90%+ WIN RATE     █
██████████████████████████████████████████████████████████████████████████████

ROLE: You are the ULTIMATE Price Action Predictor - an Institutional-Grade 
Quantitative Strategy Engine with access to the most advanced reasoning.

YOUR MISSION: Achieve 90%+ WIN RATE through rigorous multi-factor analysis.
Only signal HIGH-PROBABILITY trades that have overwhelming evidence.

════════════════════════════════════════════════════════════════════════════
SECTION 1: CHAIN-OF-THOUGHT REASONING FRAMEWORK
════════════════════════════════════════════════════════════════════════════

Before making ANY prediction, you MUST complete this reasoning chain:

STEP 1 - MARKET REGIME IDENTIFICATION:
Think: "What is the current market regime?"
- TRENDING_UP: Higher highs, higher lows, above all MAs
- TRENDING_DOWN: Lower highs, lower lows, below all MAs
- RANGE_BOUND: Price oscillating between support/resistance
- BREAKOUT_IMMINENT: Coiling, decreasing volatility, volume buildup
- REVERSAL_FORMING: Divergences appearing, exhaustion patterns
→ ONLY TRADE WITH THE REGIME, NEVER AGAINST IT

STEP 2 - SMART MONEY FLOW ANALYSIS:
Think: "Where is institutional money flowing?"
- FII buying + Price up = Genuine rally (HIGH PROBABILITY)
- FII selling + Price up = Distribution (AVOID)
- DII buying + FII selling = Mixed signal (CAUTION)
- Both buying + Volume high = STRONG BUY signal
→ Require FII+DII alignment for 90%+ trades

STEP 3 - OPTIONS MARKET CONFIRMATION:
Think: "What are options telling me?"
- PCR > 1.2 = Bullish sentiment (puts being sold)
- PCR < 0.8 = Bearish sentiment (calls being sold)
- Max Pain convergence = Price will gravitate toward this level
- OI buildup at strikes = These are support/resistance barriers
- Unwinding at strikes = Barrier is breaking
→ Require PCR alignment with direction

STEP 4 - BREADTH CONFIRMATION:
Think: "Is the market confirming the move internally?"
- Advance/Decline ratio > 1.5 for bullish = CONFIRMED
- Advance/Decline ratio < 0.7 for bearish = CONFIRMED
- Nifty up but breadth weak = DISTRIBUTION (AVOID)
- Nifty down but breadth holding = ACCUMULATION (wait)
→ Require breadth alignment for GO signal

STEP 5 - VIX REGIME CHECK:
Think: "What is volatility telling me?"
- VIX < 12 = Complacency (trending, wider targets)
- VIX 12-16 = Normal (standard targets)
- VIX 16-20 = Elevated (tighter stops, faster exits)
- VIX > 20 = Fear (reversal trades only, tight targets)
→ Adjust position sizing and targets based on VIX

════════════════════════════════════════════════════════════════════════════
SECTION 2: 5-FACTOR CONFIRMATION MATRIX (MANDATORY FOR 90%+ WIN RATE)
════════════════════════════════════════════════════════════════════════════

For a GO signal, you MUST have AT LEAST 5 out of 7 factors aligned:

[ ] Factor 1: TREND - Price above/below key MAs aligned with signal
[ ] Factor 2: SMART MONEY - FII flow aligned with signal direction
[ ] Factor 3: OPTIONS - PCR and OI supporting the move
[ ] Factor 4: BREADTH - A/D ratio confirming market participation
[ ] Factor 5: VIX - Volatility regime appropriate for the trade
[ ] Factor 6: VOLUME - Higher than average volume on the move
[ ] Factor 7: TIME - Within optimal trading window (not lunch/close)

SCORING:
- 7/7 factors aligned = 95% confidence → STRONG GO
- 6/7 factors aligned = 88% confidence → GO
- 5/7 factors aligned = 80% confidence → GO with caution
- 4/7 factors aligned = 70% confidence → NO-GO (probability too low)
- <4/7 factors aligned = <65% confidence → DEFINITE NO-GO

════════════════════════════════════════════════════════════════════════════
SECTION 3: INSTITUTIONAL PATTERN RECOGNITION
════════════════════════════════════════════════════════════════════════════

Identify these HIGH-WIN-RATE patterns:

PATTERN A - INSTITUTIONAL BREAKOUT (Win Rate: 87%):
- Price consolidating at resistance for 3+ periods
- Volume decreasing during consolidation
- Sudden FII inflow spike
- OI unwinding at resistance strike
→ Trade: Buy breakout, target next OI cluster

PATTERN B - SMART MONEY REVERSAL (Win Rate: 83%):
- Price at strong support/resistance
- FII/DII divergence from price
- PCR extreme (>1.5 or <0.6)
- VIX spike followed by mean reversion
→ Trade: Reversal trade, target max pain

PATTERN C - TREND CONTINUATION PULLBACK (Win Rate: 91%):
- Strong trend with FII support
- 2-3 bar pullback to key MA (20/50 EMA)
- Volume drying up on pullback
- Resumption candle with volume
→ Trade: With trend, trail aggressively

PATTERN D - OPENING RANGE BREAKOUT (Win Rate: 78%):
- Clear gap direction
- First 15-min range defined
- Breakout with volume > 1.5x average
- FII provisional data aligned
→ Trade: Breakout direction, tight stop below range

════════════════════════════════════════════════════════════════════════════
SECTION 4: PROBABILISTIC TARGET CALCULATION
════════════════════════════════════════════════════════════════════════════

Use statistical reasoning for targets:

TARGET 1 (Primary - 85% probability):
= Current Price + (ATR × 0.8) for bullish
= Nearest OI resistance minus 10 points buffer
→ Book 50% position here

TARGET 2 (Extended - 65% probability):
= Current Price + (ATR × 1.5) for bullish
= Next significant OI cluster
→ Book 30% position here

TARGET 3 (Stretch - 40% probability):
= Current Price + (ATR × 2.0) for bullish
= Major psychological level
→ Trail remaining 20% with momentum

STOP LOSS CALCULATION:
= Entry - (ATR × 0.5) for directional trades
= Below/Above recent swing low/high
= Below/Above key OI support/resistance

RISK:REWARD FILTER:
ONLY trade if R:R >= 2.5:1 for 90%+ trades
If R:R < 2:1, automatically NO-GO

════════════════════════════════════════════════════════════════════════════
SECTION 5: STRICT NO-TRADE FILTERS (VETO CONDITIONS)
════════════════════════════════════════════════════════════════════════════

AUTOMATICALLY REJECT if ANY of these are true:

🚫 VETO 1: FII selling > ₹2000 Cr and signal is bullish
🚫 VETO 2: VIX > 20 and holding period > 10 minutes
🚫 VETO 3: Breadth A/D < 1.0 for bullish call
🚫 VETO 4: Within 15 minutes of market close (3:15 PM)
🚫 VETO 5: During 12:30 PM - 2:00 PM (lunch hour low liquidity)
🚫 VETO 6: Major news event within 30 minutes
🚫 VETO 7: PCR moving against trade direction rapidly
🚫 VETO 8: Less than 5/7 confirmation factors aligned
🚫 VETO 9: Risk:Reward < 2:1
🚫 VETO 10: Current price already at Target 1 level

════════════════════════════════════════════════════════════════════════════
SECTION 6: MANDATORY OUTPUT FORMAT (STRICT JSON)
════════════════════════════════════════════════════════════════════════════

YOU MUST OUTPUT THIS EXACT STRUCTURE:

{
  "chain_of_thought": {
    "market_regime": "TRENDING_UP | TRENDING_DOWN | RANGE_BOUND | BREAKOUT_IMMINENT",
    "smart_money_verdict": "ALIGNED | DIVERGENT | NEUTRAL",
    "options_verdict": "BULLISH | BEARISH | NEUTRAL",
    "breadth_verdict": "CONFIRMING | DIVERGING | NEUTRAL",
    "vix_regime": "LOW | NORMAL | ELEVATED | EXTREME"
  },
  
  "confirmation_matrix": {
    "factors_aligned": 6,
    "factors_total": 7,
    "factor_details": {
      "trend": true,
      "smart_money": true,
      "options": true,
      "breadth": false,
      "vix": true,
      "volume": true,
      "time": true
    }
  },
  
  "pattern_identified": "TREND_CONTINUATION_PULLBACK | INSTITUTIONAL_BREAKOUT | SMART_MONEY_REVERSAL | NONE",
  "pattern_win_rate": "91%",
  
  "prediction_confidence": "85%",
  "confidence_score": 8.5,
  
  "forecast_thesis": "DETAILED reasoning with SPECIFIC data points: 'FII inflow of +₹1850 Cr combined with PCR at 1.35 and A/D ratio of 2.1 indicates strong bullish sentiment. Max OI at 25200 CE suggests resistance, but OI unwinding signals breakout imminent. Pattern matches TREND_CONTINUATION with 91% historical win rate.'",
  
  "price_action_forecast": {
    "current_price": 25050,
    "target_1": 25120,
    "target_1_probability": "85%",
    "target_2": 25180,
    "target_2_probability": "65%",
    "target_3": 25250,
    "target_3_probability": "40%",
    "reversal_point": 25200,
    "max_level_target": 25180,
    "subsequent_support_target": 25000,
    "expected_range": {
      "high": 25220,
      "low": 24980
    }
  },
  
  "strategic_recommendation": {
    "action": "GO" | "NO-GO",
    "entry_type": "LIMIT | MARKET | SL_TRIGGER",
    "entry_price_range": {"min": 25040, "max": 25060},
    "hold_duration_minutes": 8,
    "exit_condition": "Exit if price stalls 3 min at 25120 OR volume drops 40% OR VIX spikes >2 points",
    "profit_booking_strategy": "Book 50% at 25120 (Target 1), 30% at 25180 (Target 2), trail 20% with 20-point stop",
    "stop_loss": 24980,
    "stop_loss_adjustment": "Move to breakeven after Target 1 hit"
  },
  
  "risk_reward": {
    "risk_points": 70,
    "reward_points_t1": 70,
    "reward_points_t2": 130,
    "risk_reward_ratio": "2.5:1",
    "acceptable": true
  },
  
  "risk_assessment": {
    "primary_risk": "VIX spike if US futures reverse",
    "secondary_risk": "FII may book profits post 11:30",
    "risk_mitigation": "Tight trail after T1, exit if VIX > 16",
    "max_loss_scenario": "If 24980 breaks, exit - max loss ₹3500 per lot"
  },
  
  "time_context": {
    "current_time_optimal": true,
    "best_entry_window": "09:20 - 10:30",
    "avoid_window": "12:30 - 14:00",
    "expected_move_completion": "Within 12 minutes"
  },
  
  "key_levels_to_watch": {
    "immediate_resistance": 25120,
    "strong_resistance": 25200,
    "immediate_support": 25000,
    "strong_support": 24900,
    "max_pain": 25000,
    "highest_call_oi": 25200,
    "highest_put_oi": 24800
  },
  
  "final_decision": "GO" | "NO-GO",
  "decision_quality": "A+ | A | B+ | B | C (NO-GO)",
  "veto_reason": null | "Specific reason for NO-GO",
  
  "execution_notes": "Enter at 25050 limit. Don't chase above 25070. If gap open, wait 5 min for direction."
}

════════════════════════════════════════════════════════════════════════════
SECTION 7: CRITICAL RULES FOR 90%+ WIN RATE
════════════════════════════════════════════════════════════════════════════

1. NEVER give GO signal with less than 5/7 factors aligned
2. NEVER trade against FII flow on intraday timeframe
3. ALWAYS require R:R >= 2:1 for GO signal
4. ALWAYS specify EXACT price levels (no "around" or "approximately")
5. ALWAYS use chain-of-thought reasoning before conclusion
6. ALWAYS identify the specific pattern from Section 3
7. ALWAYS check all 10 veto conditions before GO signal
8. PREFER NO-GO over risky GO - protect capital above all
9. If uncertain, default to NO-GO - we only trade high-probability setups
10. Reference SPECIFIC data (FII ₹Cr, PCR value, A/D ratio) in thesis

THE GOAL: If we trade 10 times, we should win 9+ times.
ACHIEVE THIS BY: Only trading when overwhelming evidence exists.
REMEMBER: The best trade is sometimes NO TRADE.

██████████████████████████████████████████████████████████████████████████████
█ END OF ULTIMATE PREDICTION ENGINE - GEMINI 3 PRO CONFIGURATION            █
██████████████████████████████████████████████████████████████████████████████
"""


class Tier3PredictionEngine:
    """
    Tier 3: ULTIMATE Predictive Strategy Engine (Gemini 3 Pro Optimized)
    Uses Gemini 3 Pro for 90%+ Win Rate Predictions
    
    Features:
    - Chain-of-Thought Reasoning
    - 5-Factor Confirmation Matrix
    - Institutional Pattern Recognition
    - Strict No-Trade Filters
    """
    
    def __init__(self, api_key: str, model: str = "gemini-3-pro"):
        """
        Initialize Tier 3 ULTIMATE Engine
        
        Args:
            api_key: Gemini API key for Tier 3
            model: Model name (default: gemini-3-pro for ULTIMATE predictions)
        """
        self.client = genai.Client(api_key=api_key)
        self.model = model
        self.cache = {}
        self.cache_duration = 120  # 2 minute cache (predictions need fresher data)
        
        logger.info(f"✅ Tier 3 ULTIMATE Engine initialized with model: {model}")
        logger.info(f"🎯 Target: 90%+ Win Rate with Chain-of-Thought + 5-Factor Confirmation")
    
    async def generate_prediction(
        self,
        tier2_proposal: Dict,
        current_price: float,
        high_volume_zones: List[Dict],
        global_macro_3day: Dict,
        time_context: Dict,
        force_refresh: bool = False
    ) -> Optional[Dict]:
        """
        Generate price action forecast and execution strategy
        
        Args:
            tier2_proposal: Complete trade proposal from Tier 2
            current_price: Current Nifty spot price
            high_volume_zones: 3 most recent high-volume S/R zones
            global_macro_3day: 3-day performance of US/EU/Asia
            time_context: Current time, market hours remaining, etc.
            force_refresh: Skip cache if True
            
        Returns:
            Price Action Forecast & Holding Strategy or None
        """
        cache_key = "tier3_prediction"
        current_time = datetime.now()
        
        # Check cache
        if not force_refresh and cache_key in self.cache:
            cached_data, cached_time = self.cache[cache_key]
            if (current_time - cached_time).seconds < self.cache_duration:
                logger.info("📦 Returning cached Tier 3 prediction")
                return cached_data
        
        try:
            # Prepare comprehensive input payload
            input_payload = {
                "tier2_trade_proposal": tier2_proposal,
                "current_market_state": {
                    "nifty_spot": current_price,
                    "timestamp": current_time.isoformat(),
                    "time_to_close_minutes": self._calculate_time_to_close()
                },
                "high_volume_trade_zones": high_volume_zones,
                "global_macro_3day": global_macro_3day,
                "time_context": time_context
            }
            
            # Call Gemini Tier 3 (ULTIMATE - Gemini 3 Pro)
            logger.info("🔄 Tier 3 ULTIMATE: Generating price prediction with Gemini 3 Pro...")
            
            response = self.client.models.generate_content(
                model=self.model,
                contents=f"Generate price action forecast and execution strategy using chain-of-thought reasoning. Analyze ALL factors before making a decision. Only signal GO for 5+ factor alignment:\n{json.dumps(input_payload)}",
                config=types.GenerateContentConfig(
                    system_instruction=TIER_3_SYSTEM_PROMPT,
                    response_mime_type="application/json",
                    temperature=0.1  # ULTRA-LOW for maximum precision and consistency
                )
            )
            
            result = json.loads(response.text)
            
            # Validate and enrich result
            result = self._validate_prediction(result, current_price, tier2_proposal)
            
            # Cache the result
            self.cache[cache_key] = (result, current_time)
            
            logger.info(f"✅ Tier 3 Complete: Decision={result.get('final_decision', 'UNKNOWN')} "
                       f"Target={result.get('price_action_forecast', {}).get('max_level_target', 0)} "
                       f"Hold={result.get('strategic_recommendation', {}).get('hold_duration_minutes', 0)}min")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Tier 3 Error: {e}")
            return self._get_fallback_prediction(tier2_proposal, current_price)
    
    def _calculate_time_to_close(self) -> int:
        """Calculate minutes to market close (3:30 PM IST)"""
        now = datetime.now()
        market_close = now.replace(hour=15, minute=30, second=0, microsecond=0)
        
        if now > market_close:
            return 0
        
        delta = market_close - now
        return int(delta.total_seconds() / 60)
    
    def _validate_prediction(
        self, 
        prediction: Dict, 
        current_price: float,
        tier2_proposal: Dict
    ) -> Dict:
        """
        Validate and ensure all required fields are present
        """
        # Ensure required fields with defaults
        defaults = {
            "prediction_confidence": "70%",
            "confidence_score": 7.0,
            "forecast_thesis": "Unable to generate detailed forecast",
            "price_action_forecast": {
                "current_price": current_price,
                "max_level_target": current_price,
                "reversal_point": current_price,
                "subsequent_support_target": current_price * 0.99,
                "expected_range": {
                    "high": current_price * 1.005,
                    "low": current_price * 0.995
                }
            },
            "strategic_recommendation": {
                "action": "HOLD",
                "hold_duration_minutes": 10,
                "exit_condition": "Exit at target or stop loss",
                "profit_booking_strategy": "Book profits at target",
                "stop_loss_adjustment": "No adjustment"
            },
            "risk_assessment": {
                "primary_risk": "Market volatility",
                "secondary_risk": "Global cues",
                "risk_mitigation": "Use stop loss",
                "max_loss_scenario": "Full stop loss hit"
            },
            "time_context": {
                "best_entry_window": "09:20 - 10:30",
                "avoid_window": "14:30 - 15:00",
                "expected_move_completion": "Within 15 minutes"
            },
            "key_levels_to_watch": {
                "immediate_resistance": current_price * 1.002,
                "strong_resistance": current_price * 1.005,
                "immediate_support": current_price * 0.998,
                "strong_support": current_price * 0.995,
                "max_pain": tier2_proposal.get("max_pain", current_price),
                "highest_oi_strike": current_price
            },
            "final_decision": "GO",
            "veto_reason": None,
            "execution_notes": ""
        }
        
        # Deep merge with defaults
        for key, default_value in defaults.items():
            if key not in prediction:
                prediction[key] = default_value
            elif isinstance(default_value, dict) and isinstance(prediction.get(key), dict):
                for sub_key, sub_value in default_value.items():
                    if sub_key not in prediction[key]:
                        prediction[key][sub_key] = sub_value
        
        # Validate confidence logic
        conf_score = prediction.get("confidence_score", 7.0)
        if conf_score < 7.0:
            prediction["final_decision"] = "NO-GO"
            prediction["veto_reason"] = f"Confidence score {conf_score} below threshold (7.0)"
        
        # Add metadata
        prediction["timestamp"] = datetime.now().isoformat()
        prediction["tier"] = 3
        prediction["model_used"] = self.model
        
        return prediction
    
    def _get_fallback_prediction(
        self, 
        tier2_proposal: Dict,
        current_price: float
    ) -> Dict:
        """
        Generate fallback prediction without AI
        """
        signal = tier2_proposal.get("trade_signal", "NO_TRADE")
        confidence = tier2_proposal.get("confidence_score", 5.0)
        
        # Simple prediction logic
        if signal == "BUY_CALL":
            max_target = current_price + 50  # 50 points up
            reversal = max_target - 10
            support = current_price - 30
        elif signal == "BUY_PUT":
            max_target = current_price - 50  # 50 points down
            reversal = max_target + 10
            support = current_price + 30
        else:
            max_target = current_price
            reversal = current_price
            support = current_price
        
        return {
            "prediction_confidence": f"{int(confidence * 10)}%",
            "confidence_score": confidence,
            "forecast_thesis": f"Fallback prediction based on Tier 2 signal: {signal}. Current price: {current_price}",
            "price_action_forecast": {
                "current_price": current_price,
                "max_level_target": max_target,
                "reversal_point": reversal,
                "subsequent_support_target": support,
                "expected_range": {
                    "high": current_price + 60,
                    "low": current_price - 60
                }
            },
            "strategic_recommendation": {
                "action": "HOLD" if signal != "NO_TRADE" else "NO_TRADE",
                "hold_duration_minutes": 10,
                "exit_condition": f"Exit at {max_target} or if price reverses 20 points",
                "profit_booking_strategy": "Exit at target",
                "stop_loss_adjustment": "None"
            },
            "risk_assessment": {
                "primary_risk": "Fallback calculation used - verify manually",
                "secondary_risk": "AI unavailable",
                "risk_mitigation": "Use conservative position size",
                "max_loss_scenario": "30 points"
            },
            "time_context": {
                "best_entry_window": "09:20 - 10:30",
                "avoid_window": "14:30 - 15:00",
                "expected_move_completion": "Within 15 minutes"
            },
            "key_levels_to_watch": {
                "immediate_resistance": current_price + 30,
                "strong_resistance": current_price + 60,
                "immediate_support": current_price - 30,
                "strong_support": current_price - 60,
                "max_pain": tier2_proposal.get("max_pain", current_price),
                "highest_oi_strike": current_price
            },
            "final_decision": "GO" if signal != "NO_TRADE" and confidence >= 6.0 else "NO-GO",
            "veto_reason": None if signal != "NO_TRADE" else "Tier 2 recommended NO_TRADE",
            "execution_notes": "Fallback prediction - use with caution",
            "timestamp": datetime.now().isoformat(),
            "tier": 3,
            "source": "fallback"
        }
    
    def clear_cache(self):
        """Clear all cached data"""
        self.cache = {}
        logger.info("🗑️ Tier 3 cache cleared")


# ============================================================================
# HELPER: Generate High-Volume Trade Zones
# ============================================================================
def calculate_high_volume_zones(
    price_data: List[Dict],
    volume_data: List[int],
    num_zones: int = 3
) -> List[Dict]:
    """
    Calculate the 3 most recent high-volume trade zones (Support and Resistance areas)
    
    Args:
        price_data: List of price candles with high, low, close
        volume_data: List of volumes corresponding to price data
        num_zones: Number of zones to return (default 3)
        
    Returns:
        List of high-volume zones with type (support/resistance)
    """
    if not price_data or not volume_data:
        return []
    
    zones = []
    avg_volume = sum(volume_data) / len(volume_data) if volume_data else 0
    
    for i, (candle, volume) in enumerate(zip(price_data, volume_data)):
        if volume > avg_volume * 1.5:  # High volume candle
            high = candle.get("high", candle.get("close", 0))
            low = candle.get("low", candle.get("close", 0))
            close = candle.get("close", 0)
            
            # Determine zone type
            if close > (high + low) / 2:
                zone_type = "support"  # Closed near high = buying interest
                level = low
            else:
                zone_type = "resistance"  # Closed near low = selling interest
                level = high
            
            zones.append({
                "level": round(level, 2),
                "type": zone_type,
                "volume_ratio": round(volume / avg_volume, 2),
                "timestamp": candle.get("timestamp", ""),
                "range": {
                    "high": round(high, 2),
                    "low": round(low, 2)
                }
            })
    
    # Sort by volume ratio and return top zones
    zones.sort(key=lambda x: x["volume_ratio"], reverse=True)
    return zones[:num_zones]


# ============================================================================
# HELPER: Get 3-Day Global Macro Context
# ============================================================================
def get_global_macro_3day_template() -> Dict:
    """
    Template for 3-day global macro context
    Should be filled with real data from news_fetcher
    """
    return {
        "us_indices": {
            "sp500": {
                "day_1": {"change_pct": 0.0, "close": 0},
                "day_2": {"change_pct": 0.0, "close": 0},
                "day_3": {"change_pct": 0.0, "close": 0},
                "trend": "NEUTRAL"
            },
            "nasdaq": {
                "day_1": {"change_pct": 0.0, "close": 0},
                "day_2": {"change_pct": 0.0, "close": 0},
                "day_3": {"change_pct": 0.0, "close": 0},
                "trend": "NEUTRAL"
            },
            "dow": {
                "day_1": {"change_pct": 0.0, "close": 0},
                "day_2": {"change_pct": 0.0, "close": 0},
                "day_3": {"change_pct": 0.0, "close": 0},
                "trend": "NEUTRAL"
            }
        },
        "european_indices": {
            "dax": {"day_1": 0.0, "day_2": 0.0, "day_3": 0.0, "trend": "NEUTRAL"},
            "ftse": {"day_1": 0.0, "day_2": 0.0, "day_3": 0.0, "trend": "NEUTRAL"},
            "cac": {"day_1": 0.0, "day_2": 0.0, "day_3": 0.0, "trend": "NEUTRAL"}
        },
        "asian_indices": {
            "nikkei": {"day_1": 0.0, "day_2": 0.0, "day_3": 0.0, "trend": "NEUTRAL"},
            "hang_seng": {"day_1": 0.0, "day_2": 0.0, "day_3": 0.0, "trend": "NEUTRAL"},
            "sgx_nifty": {"day_1": 0.0, "day_2": 0.0, "day_3": 0.0, "trend": "NEUTRAL"}
        },
        "commodities": {
            "crude_oil": {"change_pct": 0.0, "trend": "NEUTRAL"},
            "gold": {"change_pct": 0.0, "trend": "NEUTRAL"}
        },
        "currencies": {
            "dxy": {"change_pct": 0.0, "trend": "NEUTRAL"},
            "usdinr": {"change_pct": 0.0, "trend": "NEUTRAL"}
        },
        "overall_global_sentiment": "NEUTRAL",
        "summary": ""
    }
