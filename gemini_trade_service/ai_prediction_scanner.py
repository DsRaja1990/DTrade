"""
AI Prediction Scanner - ChartInk-like Intelligent Prediction System
====================================================================
Uses 3-Tier Gemini Architecture for predictive stock analysis

Prediction Types:
1. 5-Minute Momentum Predictor - Which stocks will move UP/DOWN in next 5 mins
2. Opening Rush Scanner (9:15-10:45) - Maximize first 1.5 hour momentum
3. Continuous Trend Detector - Stocks in persistent up/down trend
4. Reversal Predictor - When trend will reverse

AI Layers:
- Tier 1 (Flash-Lite): Volume, VWAP, Candle Structure
- Tier 2 (Flash): OI, CPR, Trend Coherence, Breakout Score 
- Tier 3 (Gemini 3 Pro): Macro, VIX, FII/DII, Final Prediction
"""

import logging
import json
from datetime import datetime, timedelta, time as dt_time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

# ============================================================================
# AI SYSTEM PROMPTS FOR PREDICTION
# ============================================================================

TIER_1_SCREENER_PROMPT = """
ROLE: You are a Technical Data Analyst for Indian Stock Markets.
TASK: Analyze raw stock data and extract key technical signals for screening.

INPUT: Stock data with price, volume, VWAP, candle patterns.

ANALYZE:
1. Volume Spike: Is current volume > 1.5x average? (HIGH_VOLUME | NORMAL | LOW_VOLUME)
2. VWAP Position: Is price above/below VWAP? (ABOVE | BELOW | AT_VWAP)
3. Candle Structure: Bullish/Bearish/Neutral? (STRONG_BULLISH | BULLISH | NEUTRAL | BEARISH | STRONG_BEARISH)
4. Momentum Score: Based on price action (0-10)

OUTPUT FORMAT (JSON ONLY):
{
  "stocks_analyzed": (number),
  "bullish_stocks": [
    {"symbol": "RELIANCE", "volume_signal": "HIGH_VOLUME", "vwap_signal": "ABOVE", "candle_signal": "BULLISH", "momentum_score": 8}
  ],
  "bearish_stocks": [
    {"symbol": "TCS", "volume_signal": "HIGH_VOLUME", "vwap_signal": "BELOW", "candle_signal": "BEARISH", "momentum_score": 7}
  ],
  "neutral_stocks": ["INFY", "HDFC"],
  "top_volume_movers": ["RELIANCE", "TATAMOTORS", "SBIN"]
}
"""

TIER_2_SCREENER_PROMPT = """
ROLE: You are an Options and Trend Analyst for Indian Stock Markets.
TASK: Analyze OI patterns, CPR levels, and trend coherence for trade setups.

INPUT: 
1. Tier 1 analysis (Volume, VWAP, Candle signals)
2. CPR data (Central Pivot Range)
3. SuperTrend signals
4. OI data (if available)

ANALYZE:
1. CPR Bias: Above CPR = Bullish, Below = Bearish, Inside = Avoid
2. Trend Coherence: Do all signals align? (ALIGNED | PARTIAL | CONFLICTING)
3. Breakout Quality Score: 0-10 based on:
   - Volume spike
   - Clean CPR break
   - SuperTrend confirmation
   - Trend alignment
4. OI Interpretation:
   - Call Unwinding + Put OI Rising = BULLISH
   - Put Unwinding + Call OI Rising = BEARISH
5. PCR Signal: PCR > 1 = Bullish, PCR < 0.8 = Bearish

OUTPUT FORMAT (JSON ONLY):
{
  "buy_candidates": [
    {
      "symbol": "RELIANCE",
      "cpr_bias": "BULLISH",
      "trend_coherence": "ALIGNED",
      "breakout_score": 8,
      "oi_signal": "CALL_UNWINDING",
      "pcr": 1.2,
      "trade_quality": "HIGH"
    }
  ],
  "sell_candidates": [
    {
      "symbol": "TCS",
      "cpr_bias": "BEARISH",
      "trend_coherence": "ALIGNED", 
      "breakout_score": 7,
      "oi_signal": "PUT_UNWINDING",
      "pcr": 0.7,
      "trade_quality": "MEDIUM"
    }
  ],
  "avoid_list": ["INFY", "HDFC"],
  "breakout_watchlist": ["TATAMOTORS", "SBIN"]
}
"""

TIER_3_PREDICTION_PROMPT = """
ROLE: You are an Elite Market Predictor using Gemini 3 Pro's advanced reasoning.
TASK: Generate precise predictions for stock movements in the next 5-30 minutes.

INPUT:
1. Tier 1 + Tier 2 analysis
2. Macro data (VIX, FII/DII, Global markets)
3. Current market phase (Opening Rush / Breakout Zone / Consolidation)
4. News sentiment

CRITICAL CONTEXT - OPENING RUSH (9:15-10:45):
- First 90 minutes have HIGHEST momentum
- Trends established here often continue
- Volume is 3x normal during this period
- CPR breakouts in this window are most reliable

PREDICT FOR EACH HIGH-PROBABILITY STOCK:
1. Direction: UP | DOWN | SIDEWAYS
2. Target Move: Expected % move in next 5-30 mins
3. Time to Target: How many minutes to reach target
4. Peak Level: Maximum price it will reach before reversal
5. Reversal Point: When/where the move will reverse
6. Confidence: 70% | 80% | 90%
7. Stop Loss: Where to exit if prediction fails
8. Hold Duration: How long to hold the position

OUTPUT FORMAT (JSON ONLY):
{
  "market_phase": "OPENING_RUSH",
  "market_bias": "BULLISH",
  "vix_impact": "LOW",
  
  "buy_predictions": [
    {
      "symbol": "RELIANCE",
      "trade": "BUY",
      "confidence": "87%",
      "strike": "2950 CE",
      "entry_range": "45-50",
      "stop_loss": "35",
      "target_1": "70",
      "target_2": "90",
      "predicted_move_pct": 1.2,
      "time_to_target_mins": 15,
      "peak_price": 2975,
      "reversal_point": 2980,
      "hold_duration_mins": 20,
      "reason": "CPR breakout + volume spike + call unwinding + opening rush momentum"
    }
  ],
  
  "sell_predictions": [
    {
      "symbol": "TCS",
      "trade": "SELL",
      "confidence": "82%",
      "strike": "4100 PE",
      "entry_range": "55-60",
      "stop_loss": "45",
      "target_1": "80",
      "target_2": "100",
      "predicted_move_pct": -1.5,
      "time_to_target_mins": 12,
      "bottom_price": 4050,
      "reversal_point": 4040,
      "hold_duration_mins": 18,
      "reason": "CPR breakdown + bearish candle + put unwinding + sector weakness"
    }
  ],
  
  "momentum_stocks": {
    "continuous_up": [
      {"symbol": "TATAMOTORS", "trend_bars": 5, "momentum_strength": 8, "predicted_continuation_mins": 10}
    ],
    "continuous_down": [
      {"symbol": "WIPRO", "trend_bars": 4, "momentum_strength": 7, "predicted_continuation_mins": 8}
    ]
  },
  
  "avoid_stocks": ["INFY", "HDFC"],
  "reasoning": "Opening rush phase with bullish FII flows, low VIX supports momentum plays"
}
"""

# ============================================================================
# PREDICTION DATA CLASSES
# ============================================================================

@dataclass
class StockPrediction:
    """Individual stock prediction"""
    symbol: str
    trade: str  # BUY | SELL | AVOID
    confidence: str  # "87%"
    strike: str  # "2950 CE" or "4100 PE"
    entry_range: str
    stop_loss: str
    target_1: str
    target_2: str
    predicted_move_pct: float
    time_to_target_mins: int
    peak_or_bottom_price: float
    reversal_point: float
    hold_duration_mins: int
    reason: str

@dataclass 
class MomentumStock:
    """Stock in continuous momentum"""
    symbol: str
    direction: str  # UP | DOWN
    trend_bars: int
    momentum_strength: int  # 0-10
    predicted_continuation_mins: int

@dataclass
class ScannerOutput:
    """Complete scanner output"""
    timestamp: str
    market_phase: str
    market_bias: str
    vix_impact: str
    
    buy_predictions: List[StockPrediction]
    sell_predictions: List[StockPrediction]
    
    momentum_up: List[MomentumStock]
    momentum_down: List[MomentumStock]
    
    avoid_stocks: List[str]
    reasoning: str

# ============================================================================
# AI PREDICTION SCANNER CLASS
# ============================================================================

class AIPredictionScanner:
    """
    AI-Powered Prediction Scanner using 3-Tier Gemini Architecture
    
    Flow:
    1. Tier 1 (Flash-Lite): Volume, VWAP, Candle analysis
    2. Tier 2 (Flash): OI, CPR, Trend coherence, Breakout score
    3. Tier 3 (Gemini 3 Pro): Final prediction with targets
    """
    
    def __init__(self, gemini_tier_1_client=None, gemini_tier_2_client=None, gemini_tier_3_client=None):
        self.tier_1_client = gemini_tier_1_client
        self.tier_2_client = gemini_tier_2_client
        self.tier_3_client = gemini_tier_3_client
        self.last_scan_time = None
        self.cache = {}
    
    def get_market_phase(self) -> str:
        """Determine current market phase"""
        now = datetime.now()
        current_time = now.time()
        
        if dt_time(9, 15) <= current_time < dt_time(9, 30):
            return "OPENING_RUSH"
        elif dt_time(9, 30) <= current_time < dt_time(10, 0):
            return "TREND_FORMATION"
        elif dt_time(10, 0) <= current_time < dt_time(10, 45):
            return "BREAKOUT_ZONE"
        elif dt_time(10, 45) <= current_time < dt_time(14, 0):
            return "CONSOLIDATION"
        elif dt_time(14, 0) <= current_time < dt_time(15, 0):
            return "CLOSING_MOVE"
        elif dt_time(15, 0) <= current_time < dt_time(15, 30):
            return "FINAL_HOUR"
        else:
            return "MARKET_CLOSED"
    
    def is_high_momentum_phase(self) -> bool:
        """Check if we're in high momentum phase (9:15-10:45)"""
        phase = self.get_market_phase()
        return phase in ["OPENING_RUSH", "TREND_FORMATION", "BREAKOUT_ZONE"]
    
    async def run_tier_1_scan(self, stock_data: List[Dict]) -> Optional[Dict]:
        """
        Tier 1: Volume, VWAP, Candle Structure Analysis
        Uses gemini-2.0-flash-lite for fast processing
        """
        if not self.tier_1_client:
            logger.warning("Tier 1 client not available, using fallback")
            return self._fallback_tier_1(stock_data)
        
        try:
            response = self.tier_1_client(
                system_prompt=TIER_1_SCREENER_PROMPT,
                user_content=f"Analyze these stocks for volume, VWAP, candle signals: {json.dumps(stock_data)}"
            )
            return response
        except Exception as e:
            logger.error(f"Tier 1 scan error: {e}")
            return self._fallback_tier_1(stock_data)
    
    async def run_tier_2_scan(self, tier1_result: Dict, stock_data: List[Dict]) -> Optional[Dict]:
        """
        Tier 2: OI, CPR, Trend Coherence, Breakout Score
        Uses gemini-2.0-flash for balanced analysis
        """
        if not self.tier_2_client:
            logger.warning("Tier 2 client not available, using fallback")
            return self._fallback_tier_2(tier1_result, stock_data)
        
        try:
            tier2_input = {
                "tier1_analysis": tier1_result,
                "stock_data": stock_data,
                "market_phase": self.get_market_phase()
            }
            
            response = self.tier_2_client(
                system_prompt=TIER_2_SCREENER_PROMPT,
                user_content=f"Analyze OI, CPR, trend coherence: {json.dumps(tier2_input)}"
            )
            return response
        except Exception as e:
            logger.error(f"Tier 2 scan error: {e}")
            return self._fallback_tier_2(tier1_result, stock_data)
    
    async def run_tier_3_prediction(self, tier1_result: Dict, tier2_result: Dict, 
                                     macro_data: Dict = None) -> Optional[Dict]:
        """
        Tier 3: Final Prediction using Gemini 3 Pro
        Generates precise predictions with targets, timing, and confidence
        """
        if not self.tier_3_client:
            logger.warning("Tier 3 client not available, using fallback")
            return self._fallback_tier_3(tier2_result)
        
        try:
            tier3_input = {
                "tier1_analysis": tier1_result,
                "tier2_analysis": tier2_result,
                "market_phase": self.get_market_phase(),
                "is_high_momentum": self.is_high_momentum_phase(),
                "macro_data": macro_data or {},
                "timestamp": datetime.now().isoformat()
            }
            
            response = self.tier_3_client(
                system_prompt=TIER_3_PREDICTION_PROMPT,
                user_content=f"Generate predictions for high-probability stocks: {json.dumps(tier3_input)}"
            )
            return response
        except Exception as e:
            logger.error(f"Tier 3 prediction error: {e}")
            return self._fallback_tier_3(tier2_result)
    
    async def full_scan(self, stock_screener_results: Dict, macro_data: Dict = None) -> Dict:
        """
        Run full 3-tier prediction scan
        
        Args:
            stock_screener_results: Output from StockScreener.scan_all_stocks()
            macro_data: VIX, FII/DII, global market data
        
        Returns:
            Complete prediction output with buy/sell candidates and targets
        """
        logger.info(f"🔄 Starting full AI prediction scan - Phase: {self.get_market_phase()}")
        
        # Prepare stock data for AI analysis
        all_stocks = []
        for category in ["strong_buy", "buy", "weak_buy", "sell", "strong_sell", "momentum_up", "momentum_down", "volume_movers"]:
            if category in stock_screener_results:
                for result in stock_screener_results[category]:
                    all_stocks.append(self._result_to_ai_input(result))
        
        if not all_stocks:
            return {"error": "No stocks to analyze", "market_phase": self.get_market_phase()}
        
        # Run 3-Tier Analysis
        logger.info(f"📊 Analyzing {len(all_stocks)} stocks...")
        
        # Tier 1
        tier1_result = await self.run_tier_1_scan(all_stocks)
        logger.info(f"✅ Tier 1 Complete: {len(tier1_result.get('bullish_stocks', []))} bullish, {len(tier1_result.get('bearish_stocks', []))} bearish")
        
        # Tier 2
        tier2_result = await self.run_tier_2_scan(tier1_result, all_stocks)
        logger.info(f"✅ Tier 2 Complete: {len(tier2_result.get('buy_candidates', []))} buy, {len(tier2_result.get('sell_candidates', []))} sell")
        
        # Tier 3
        tier3_result = await self.run_tier_3_prediction(tier1_result, tier2_result, macro_data)
        logger.info(f"✅ Tier 3 Complete: Predictions generated")
        
        # Combine results
        output = {
            "status": "success",
            "timestamp": datetime.now().isoformat(),
            "market_phase": self.get_market_phase(),
            "is_high_momentum_phase": self.is_high_momentum_phase(),
            
            "tier_1_summary": {
                "bullish_count": len(tier1_result.get('bullish_stocks', [])),
                "bearish_count": len(tier1_result.get('bearish_stocks', [])),
                "volume_movers": tier1_result.get('top_volume_movers', [])
            },
            
            "tier_2_summary": {
                "buy_candidates": len(tier2_result.get('buy_candidates', [])),
                "sell_candidates": len(tier2_result.get('sell_candidates', [])),
                "breakout_watchlist": tier2_result.get('breakout_watchlist', [])
            },
            
            "predictions": tier3_result,
            
            "quick_picks": self._generate_quick_picks(tier3_result)
        }
        
        return output
    
    def _result_to_ai_input(self, result) -> Dict:
        """Convert StockScreenResult to AI input format"""
        if hasattr(result, '__dict__'):
            return {
                "symbol": result.symbol,
                "price": result.current_price,
                "change_pct": result.change_pct,
                "volume_ratio": result.volume_spike_ratio,
                "vwap_position": result.vwap_position,
                "supertrend": result.supertrend_signal,
                "cpr_position": result.cpr_position,
                "candle_type": result.candle_type,
                "signal": result.signal.value if hasattr(result.signal, 'value') else str(result.signal),
                "signal_strength": result.signal_strength,
                "trend_5min": result.trend_5min.value if hasattr(result.trend_5min, 'value') else str(result.trend_5min),
                "buy_signals": result.buy_signals,
                "sell_signals": result.sell_signals
            }
        return result
    
    def _generate_quick_picks(self, tier3_result: Dict) -> Dict:
        """Generate quick actionable picks from Tier 3 results"""
        quick_picks = {
            "top_buy": None,
            "top_sell": None,
            "momentum_play": None
        }
        
        buy_preds = tier3_result.get("buy_predictions", [])
        sell_preds = tier3_result.get("sell_predictions", [])
        
        if buy_preds:
            top_buy = buy_preds[0] if isinstance(buy_preds[0], dict) else buy_preds[0].__dict__
            quick_picks["top_buy"] = {
                "symbol": top_buy.get("symbol"),
                "action": "BUY",
                "confidence": top_buy.get("confidence"),
                "strike": top_buy.get("strike"),
                "stop_loss": top_buy.get("stop_loss"),
                "target": top_buy.get("target_1"),
                "reason": top_buy.get("reason", "")[:100]
            }
        
        if sell_preds:
            top_sell = sell_preds[0] if isinstance(sell_preds[0], dict) else sell_preds[0].__dict__
            quick_picks["top_sell"] = {
                "symbol": top_sell.get("symbol"),
                "action": "SELL",
                "confidence": top_sell.get("confidence"),
                "strike": top_sell.get("strike"),
                "stop_loss": top_sell.get("stop_loss"),
                "target": top_sell.get("target_1"),
                "reason": top_sell.get("reason", "")[:100]
            }
        
        # Momentum play from continuous trends
        momentum_stocks = tier3_result.get("momentum_stocks", {})
        up_stocks = momentum_stocks.get("continuous_up", [])
        
        if up_stocks:
            mom_stock = up_stocks[0] if isinstance(up_stocks[0], dict) else up_stocks[0].__dict__
            quick_picks["momentum_play"] = {
                "symbol": mom_stock.get("symbol"),
                "direction": "UP",
                "trend_bars": mom_stock.get("trend_bars"),
                "continuation_mins": mom_stock.get("predicted_continuation_mins")
            }
        
        return quick_picks
    
    # ========================================================================
    # FALLBACK METHODS (when AI is not available)
    # ========================================================================
    
    def _fallback_tier_1(self, stock_data: List[Dict]) -> Dict:
        """Fallback Tier 1 analysis without AI"""
        bullish = []
        bearish = []
        neutral = []
        volume_movers = []
        
        for stock in stock_data:
            symbol = stock.get("symbol", "UNKNOWN")
            volume_ratio = stock.get("volume_ratio", 1.0)
            vwap_pos = stock.get("vwap_position", "NEUTRAL")
            change_pct = stock.get("change_pct", 0)
            
            if volume_ratio >= 2.0:
                volume_movers.append(symbol)
            
            if vwap_pos == "ABOVE" and change_pct > 0.5:
                bullish.append({
                    "symbol": symbol,
                    "volume_signal": "HIGH_VOLUME" if volume_ratio > 1.5 else "NORMAL",
                    "vwap_signal": "ABOVE",
                    "candle_signal": "BULLISH",
                    "momentum_score": min(10, int(5 + change_pct))
                })
            elif vwap_pos == "BELOW" and change_pct < -0.5:
                bearish.append({
                    "symbol": symbol,
                    "volume_signal": "HIGH_VOLUME" if volume_ratio > 1.5 else "NORMAL",
                    "vwap_signal": "BELOW",
                    "candle_signal": "BEARISH",
                    "momentum_score": min(10, int(5 + abs(change_pct)))
                })
            else:
                neutral.append(symbol)
        
        return {
            "stocks_analyzed": len(stock_data),
            "bullish_stocks": bullish,
            "bearish_stocks": bearish,
            "neutral_stocks": neutral,
            "top_volume_movers": volume_movers[:5]
        }
    
    def _fallback_tier_2(self, tier1_result: Dict, stock_data: List[Dict]) -> Dict:
        """Fallback Tier 2 analysis without AI"""
        buy_candidates = []
        sell_candidates = []
        avoid_list = []
        breakout_watchlist = []
        
        for stock in tier1_result.get("bullish_stocks", []):
            buy_candidates.append({
                "symbol": stock["symbol"],
                "cpr_bias": "BULLISH",
                "trend_coherence": "ALIGNED",
                "breakout_score": stock.get("momentum_score", 5),
                "oi_signal": "NEUTRAL",
                "pcr": 1.0,
                "trade_quality": "MEDIUM"
            })
        
        for stock in tier1_result.get("bearish_stocks", []):
            sell_candidates.append({
                "symbol": stock["symbol"],
                "cpr_bias": "BEARISH",
                "trend_coherence": "ALIGNED",
                "breakout_score": stock.get("momentum_score", 5),
                "oi_signal": "NEUTRAL",
                "pcr": 1.0,
                "trade_quality": "MEDIUM"
            })
        
        return {
            "buy_candidates": buy_candidates,
            "sell_candidates": sell_candidates,
            "avoid_list": tier1_result.get("neutral_stocks", [])[:5],
            "breakout_watchlist": breakout_watchlist
        }
    
    def _fallback_tier_3(self, tier2_result: Dict) -> Dict:
        """Fallback Tier 3 prediction without AI"""
        buy_predictions = []
        sell_predictions = []
        
        for candidate in tier2_result.get("buy_candidates", [])[:3]:
            buy_predictions.append({
                "symbol": candidate["symbol"],
                "trade": "BUY",
                "confidence": f"{50 + candidate.get('breakout_score', 5) * 4}%",
                "strike": "ATM CE",
                "entry_range": "Market",
                "stop_loss": "2%",
                "target_1": "3%",
                "target_2": "5%",
                "predicted_move_pct": 1.0,
                "time_to_target_mins": 20,
                "peak_price": 0,
                "reversal_point": 0,
                "hold_duration_mins": 25,
                "reason": f"Technical signals aligned - {candidate.get('trend_coherence', 'PARTIAL')}"
            })
        
        for candidate in tier2_result.get("sell_candidates", [])[:3]:
            sell_predictions.append({
                "symbol": candidate["symbol"],
                "trade": "SELL",
                "confidence": f"{50 + candidate.get('breakout_score', 5) * 4}%",
                "strike": "ATM PE",
                "entry_range": "Market",
                "stop_loss": "2%",
                "target_1": "3%",
                "target_2": "5%",
                "predicted_move_pct": -1.0,
                "time_to_target_mins": 20,
                "bottom_price": 0,
                "reversal_point": 0,
                "hold_duration_mins": 25,
                "reason": f"Technical signals aligned - {candidate.get('trend_coherence', 'PARTIAL')}"
            })
        
        return {
            "market_phase": self.get_market_phase(),
            "market_bias": "NEUTRAL",
            "vix_impact": "UNKNOWN",
            "buy_predictions": buy_predictions,
            "sell_predictions": sell_predictions,
            "momentum_stocks": {
                "continuous_up": [],
                "continuous_down": []
            },
            "avoid_stocks": tier2_result.get("avoid_list", []),
            "reasoning": "Fallback prediction - AI not available"
        }


# Global instance
ai_prediction_scanner = AIPredictionScanner()
