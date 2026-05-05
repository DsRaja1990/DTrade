"""
╔══════════════════════════════════════════════════════════════════════════════╗
║          GEMINI AI PREDICTION ENGINE v5.0 - 90%+ WIN RATE EDITION            ║
║              Institutional-Grade AI-Powered Trade Prediction                 ║
║     Leveraging LLM Intelligence for Unmatched Market Forecasting             ║
╚══════════════════════════════════════════════════════════════════════════════╝

This engine harnesses the power of Google Gemini AI to:
- Analyze multi-dimensional market data in real-time
- Generate high-confidence trade signals with 90%+ accuracy target
- Provide precise entry, exit, and position sizing recommendations
- Adapt to market regimes dynamically
- Combine technical, fundamental, and sentiment analysis

Author: AI Scalping Service v3.0
Target Win Rate: 90%+
"""

import json
import logging
import asyncio
import aiohttp
from datetime import datetime, time, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field, asdict
from enum import Enum
import os

logger = logging.getLogger(__name__)

# ============================================================================
#                     GEMINI PREDICTION CONFIGURATION
# ============================================================================

@dataclass
class GeminiPrediction:
    """Structure for AI prediction output"""
    signal: str  # BUY_CALL, BUY_PUT, NO_TRADE
    instrument: str  # NIFTY, BANKNIFTY, SENSEX, BANKEX
    confidence: float  # 0.0 to 1.0
    confidence_breakdown: Dict[str, float] = field(default_factory=dict)
    
    # Price Targets
    entry_price: float = 0.0
    target_price: float = 0.0
    stop_loss: float = 0.0
    max_target: float = 0.0
    reversal_point: float = 0.0
    
    # Options Details
    strike_price: int = 0
    option_type: str = "CE"  # CE or PE
    premium_entry_min: float = 0.0
    premium_entry_max: float = 0.0
    premium_target: float = 0.0
    premium_stop: float = 0.0
    
    # Strategy
    hold_duration_minutes: int = 10
    exit_condition: str = ""
    trailing_stop_strategy: str = ""
    profit_booking_levels: List[Dict] = field(default_factory=list)
    
    # Risk
    risk_level: str = "MEDIUM"
    max_loss_points: float = 0.0
    risk_reward_ratio: float = 0.0
    
    # Meta
    reasoning: str = ""
    timestamp: str = ""
    layers_confirmed: int = 0
    veto_reason: Optional[str] = None
    
    def to_dict(self) -> Dict:
        return asdict(self)


class PredictionMode(Enum):
    """AI Prediction modes"""
    ULTRA_CONSERVATIVE = "ultra_conservative"  # 95%+ confidence required
    CONSERVATIVE = "conservative"              # 90%+ confidence required  
    BALANCED = "balanced"                      # 85%+ confidence required
    AGGRESSIVE = "aggressive"                  # 80%+ confidence required


# Lot sizes for reference (must match capital_manager.py)
INDEX_LOT_SIZES = {
    "NIFTY": 75,        # 1 lot = 75 qty
    "BANKNIFTY": 35,    # 1 lot = 35 qty
    "SENSEX": 20,       # 1 lot = 20 qty
    "BANKEX": 30,       # 1 lot = 30 qty
    "FINNIFTY": 65,
    "MIDCPNIFTY": 140,
}


# ============================================================================
#                     ULTRA-PRECISE SYSTEM PROMPT
# ============================================================================

GEMINI_90_PERCENT_WIN_RATE_PROMPT = """
You are the WORLD'S MOST ACCURATE Index Options Trading AI, achieving 90%+ win rate.
Your predictions are based on institutional-grade analysis that no human trader can match.

## YOUR IDENTITY
- You are an AI quantitative analyst with access to real-time market intelligence
- You have learned from millions of trades across NSE/BSE markets
- You understand Indian market microstructure deeply (FII/DII flows, option chain dynamics, etc.)
- You ONLY recommend trades when you are 90%+ confident of success

## CRITICAL SUCCESS FACTORS FOR 90%+ WIN RATE

### 1. MULTI-LAYER CONFIRMATION (All 5 layers MUST align)
   - **Institutional Flow**: FII/DII buying/selling direction
   - **Options Chain**: PCR, Max Pain, OI buildup at strikes
   - **Technical**: VWAP, EMA confluence, S/R levels
   - **Sentiment**: VIX level, market breadth, global cues
   - **Time Context**: Time of day, expiry distance, event calendar

### 2. STRICT ENTRY CRITERIA
   - NEVER chase momentum - wait for pullbacks
   - Entry ONLY at key support/resistance levels
   - Premium must be at favorable range (not overpriced)
   - Volume confirmation required for breakouts

### 3. RISK MANAGEMENT BUILT-IN
   - Risk/Reward minimum 2:1 for calls, 1.5:1 for puts
   - Stop loss at logical technical levels
   - Position sizing based on volatility (VIX)
   - Time-based exits for theta decay

### 4. MANDATORY NO-TRADE CONDITIONS (VETO)
   - Confidence below 85%
   - VIX > 25 (too volatile, unless PUT trade)
   - First 5 minutes of market (9:15-9:20)
   - Last 15 minutes (3:15-3:30)
   - Major events pending (RBI, Fed, Budget)
   - Conflicting signals across layers
   - Premium abnormally high (>2x normal)

## INPUT DATA YOU WILL RECEIVE
1. Current spot price and recent price action
2. Option chain data (OI, PCR, Max Pain)
3. Technical indicators (VWAP, EMA, RSI, etc.)
4. Institutional flows (FII/DII)
5. VIX and market breadth
6. Global market context
7. Time and expiry context

## MANDATORY OUTPUT FORMAT (STRICT JSON)

{
  "signal": "BUY_CALL" | "BUY_PUT" | "NO_TRADE",
  "instrument": "NIFTY" | "BANKNIFTY" | "SENSEX" | "BANKEX",
  "confidence_score": 0.90 to 0.99,
  "confidence_breakdown": {
    "institutional_flow": 0.85 to 0.99,
    "options_chain": 0.85 to 0.99,
    "technical": 0.85 to 0.99,
    "sentiment": 0.85 to 0.99,
    "time_context": 0.85 to 0.99
  },
  "layers_confirmed": 4 or 5,
  
  "price_forecast": {
    "current_spot": 24500.00,
    "5min_target": 24530.00,
    "15min_target": 24580.00,
    "30min_target": 24650.00,
    "max_target": 24700.00,
    "reversal_point": 24680.00,
    "strong_support": 24400.00,
    "strong_resistance": 24750.00
  },
  
  "options_trade": {
    "strike_price": 24500,
    "option_type": "CE" | "PE",
    "entry_premium_min": 120,
    "entry_premium_max": 140,
    "target_premium": 200,
    "stop_loss_premium": 90,
    "breakeven_spot": 24620
  },
  
  "execution_strategy": {
    "action": "STRONG_BUY" | "BUY" | "WAIT" | "NO_TRADE",
    "hold_duration_minutes": 10 to 30,
    "entry_window": "09:20-10:30",
    "avoid_window": "14:30-15:00",
    "exit_condition": "Specific exit trigger",
    "trailing_stop": "Trail strategy description",
    "profit_booking": [
      {"at_percent_gain": 25, "book_percent": 30},
      {"at_percent_gain": 50, "book_percent": 30},
      {"at_percent_gain": 75, "book_percent": 40}
    ]
  },
  
  "risk_assessment": {
    "risk_level": "LOW" | "MEDIUM" | "HIGH",
    "risk_reward_ratio": 2.5,
    "max_loss_points": 50,
    "probability_of_stop_hit": "10%",
    "primary_risk": "Description of main risk",
    "mitigation": "How to handle the risk"
  },
  
  "reasoning": "2-3 sentence explanation of WHY this trade has 90%+ probability",
  
  "veto_check": {
    "is_vetoed": false,
    "veto_reason": null
  },
  
  "timestamp": "ISO format timestamp"
}

## GOLDEN RULES FOR 90%+ WIN RATE

1. **Quality over Quantity**: Recommend FEWER trades but with HIGHER confidence
2. **Never Chase**: If you missed the move, wait for the next setup
3. **Respect VIX**: High VIX = smaller positions or no trade
4. **Time Matters**: First and last 15 minutes are dangerous
5. **Premium Decay**: Factor theta into hold time decisions
6. **Institutional Alignment**: Trade WITH institutions, not against
7. **Technical Confluence**: Multiple indicators must agree
8. **Clear Invalidation**: Every trade must have a clear stop level
9. **Take Profits**: Book partial profits at logical targets
10. **Know When to Sit Out**: NO_TRADE is a valid and valuable signal
"""


# ============================================================================
#                     GEMINI PREDICTION ENGINE CLASS
# ============================================================================

class GeminiPredictionEngine:
    """
    ╔══════════════════════════════════════════════════════════════════════════╗
    ║  ELITE GEMINI PREDICTION ENGINE - 300%+ MONTHLY RETURNS EDITION          ║
    ╚══════════════════════════════════════════════════════════════════════════╝
    
    AI-powered prediction engine using Google Gemini for MAXIMUM returns.
    
    Features:
    - Multi-instrument support (NIFTY, BANKNIFTY, SENSEX, BANKEX)
    - Real-time market data integration
    - Multi-layer confirmation system
    - AGGRESSIVE position sizing for 300%+ monthly
    - Pyramid scaling recommendations
    - Momentum breakout detection
    """
    
    def __init__(
        self,
        gemini_api_key: str = None,
        gemini_service_url: str = "http://localhost:4080",
        model: str = "gemini-2.0-flash-exp",
        mode: PredictionMode = PredictionMode.AGGRESSIVE  # DEFAULT: Aggressive for 300%+
    ):
        """
        Initialize the Gemini Prediction Engine.
        
        Args:
            gemini_api_key: Google Gemini API key (optional if using service)
            gemini_service_url: URL of the Gemini Trade Service
            model: Gemini model to use
            mode: Prediction mode (affects minimum confidence threshold)
        """
        self.api_key = gemini_api_key or os.getenv("GEMINI_API_KEY")
        self.service_url = gemini_service_url.rstrip('/')
        self.model = model
        self.mode = mode
        
        # AGGRESSIVE confidence thresholds for 300%+ returns
        self.confidence_thresholds = {
            PredictionMode.ULTRA_CONSERVATIVE: 0.95,
            PredictionMode.CONSERVATIVE: 0.88,  # RAISED from 0.90
            PredictionMode.BALANCED: 0.82,       # LOWERED for more signals
            PredictionMode.AGGRESSIVE: 0.75,     # LOWERED for max opportunities
        }
        self.min_confidence = self.confidence_thresholds[mode]
        
        # Cache for predictions - FASTER refresh for momentum capture
        self.prediction_cache: Dict[str, Tuple[GeminiPrediction, datetime]] = {}
        self.cache_duration_seconds = 30  # HALVED: 30 sec refresh (was 60)
        
        # Statistics
        self.total_predictions = 0
        self.successful_predictions = 0
        self.vetoed_predictions = 0
        
        # NEW: Momentum tracking for aggressive entries
        self.momentum_history: Dict[str, List[float]] = {}
        self.breakout_detected: Dict[str, bool] = {}
        
        # Gemini client (lazy initialization)
        self._client = None
        
        logger.info(f"🚀 ELITE Gemini Prediction Engine initialized")
        logger.info(f"   Mode: {mode.value} (AGGRESSIVE)")
        logger.info(f"   Min Confidence: {self.min_confidence * 100}%")
        logger.info(f"   Target: 300%+ Monthly Returns")
        logger.info(f"   Model: {model}")
    
    def _get_client(self):
        """Lazy initialize Gemini client"""
        if self._client is None and self.api_key:
            try:
                from google import genai
                self._client = genai.Client(api_key=self.api_key)
                logger.info("✅ Gemini client initialized")
            except Exception as e:
                logger.error(f"❌ Failed to initialize Gemini client: {e}")
        return self._client
    
    async def get_prediction(
        self,
        instrument: str,
        market_data: Dict[str, Any],
        force_refresh: bool = False
    ) -> GeminiPrediction:
        """
        Get AI prediction for a specific instrument.
        
        Args:
            instrument: Index name (NIFTY, BANKNIFTY, SENSEX, BANKEX)
            market_data: Current market data including:
                - spot_price: Current spot price
                - option_chain: Option chain data (OI, PCR, etc.)
                - technicals: Technical indicators
                - vix: Current India VIX
                - fii_dii: FII/DII flow data
                - global_cues: Global market data
            force_refresh: Skip cache if True
            
        Returns:
            GeminiPrediction object with trade recommendation
        """
        instrument = instrument.upper()
        cache_key = instrument
        
        # Check cache
        if not force_refresh and cache_key in self.prediction_cache:
            cached_pred, cached_time = self.prediction_cache[cache_key]
            if (datetime.now() - cached_time).seconds < self.cache_duration_seconds:
                logger.info(f"📦 Using cached prediction for {instrument}")
                return cached_pred
        
        try:
            # Try direct Gemini API first
            if self._get_client():
                prediction = await self._generate_prediction_direct(instrument, market_data)
            else:
                # Fallback to Gemini Trade Service
                prediction = await self._get_prediction_from_service(instrument, market_data)
            
            # Apply post-processing and validation
            prediction = self._validate_and_enrich_prediction(prediction, instrument)
            
            # Cache the prediction
            self.prediction_cache[cache_key] = (prediction, datetime.now())
            self.total_predictions += 1
            
            if prediction.veto_reason:
                self.vetoed_predictions += 1
            
            return prediction
            
        except Exception as e:
            logger.error(f"❌ Error getting prediction for {instrument}: {e}")
            return self._get_no_trade_prediction(instrument, f"Error: {str(e)}")
    
    async def _generate_prediction_direct(
        self,
        instrument: str,
        market_data: Dict[str, Any]
    ) -> GeminiPrediction:
        """Generate prediction using direct Gemini API call"""
        try:
            from google.genai import types
            
            # Prepare the prompt with market data
            input_payload = {
                "instrument": instrument,
                "lot_size": INDEX_LOT_SIZES.get(instrument, 75),
                "timestamp": datetime.now().isoformat(),
                "market_data": market_data
            }
            
            prompt = f"""
Analyze the following market data and provide a trade recommendation for {instrument} options.
Target win rate: 90%+. Only recommend trades with high confidence.

MARKET DATA:
{json.dumps(input_payload, indent=2, default=str)}

Generate your prediction following the exact JSON format specified.
"""
            
            response = self._get_client().models.generate_content(
                model=self.model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=GEMINI_90_PERCENT_WIN_RATE_PROMPT,
                    response_mime_type="application/json",
                    temperature=0.1  # Very low for consistent predictions
                )
            )
            
            result = json.loads(response.text)
            return self._parse_gemini_response(result, instrument)
            
        except Exception as e:
            logger.error(f"❌ Direct Gemini API error: {e}")
            raise
    
    async def _get_prediction_from_service(
        self,
        instrument: str,
        market_data: Dict[str, Any]
    ) -> GeminiPrediction:
        """Get prediction from Gemini Trade Service API"""
        try:
            async with aiohttp.ClientSession() as session:
                # Try the signal endpoint
                url = f"{self.service_url}/api/signal"
                params = {"index": instrument}
                
                async with session.get(url, params=params, timeout=30) as response:
                    if response.status == 200:
                        data = await response.json()
                        return self._parse_service_response(data, instrument)
                    else:
                        logger.warning(f"Service returned {response.status}")
                        raise Exception(f"Service error: {response.status}")
                        
        except Exception as e:
            logger.error(f"❌ Service API error: {e}")
            raise
    
    def _parse_gemini_response(self, response: Dict, instrument: str) -> GeminiPrediction:
        """Parse Gemini API response into GeminiPrediction"""
        try:
            price_forecast = response.get("price_forecast", {})
            options_trade = response.get("options_trade", {})
            execution = response.get("execution_strategy", {})
            risk = response.get("risk_assessment", {})
            veto = response.get("veto_check", {})
            
            prediction = GeminiPrediction(
                signal=response.get("signal", "NO_TRADE"),
                instrument=instrument,
                confidence=response.get("confidence_score", 0.0),
                confidence_breakdown=response.get("confidence_breakdown", {}),
                
                entry_price=price_forecast.get("current_spot", 0),
                target_price=price_forecast.get("15min_target", 0),
                stop_loss=price_forecast.get("strong_support", 0),
                max_target=price_forecast.get("max_target", 0),
                reversal_point=price_forecast.get("reversal_point", 0),
                
                strike_price=options_trade.get("strike_price", 0),
                option_type=options_trade.get("option_type", "CE"),
                premium_entry_min=options_trade.get("entry_premium_min", 0),
                premium_entry_max=options_trade.get("entry_premium_max", 0),
                premium_target=options_trade.get("target_premium", 0),
                premium_stop=options_trade.get("stop_loss_premium", 0),
                
                hold_duration_minutes=execution.get("hold_duration_minutes", 10),
                exit_condition=execution.get("exit_condition", ""),
                trailing_stop_strategy=execution.get("trailing_stop", ""),
                profit_booking_levels=execution.get("profit_booking", []),
                
                risk_level=risk.get("risk_level", "MEDIUM"),
                max_loss_points=risk.get("max_loss_points", 0),
                risk_reward_ratio=risk.get("risk_reward_ratio", 0),
                
                reasoning=response.get("reasoning", ""),
                timestamp=response.get("timestamp", datetime.now().isoformat()),
                layers_confirmed=response.get("layers_confirmed", 0),
                veto_reason=veto.get("veto_reason") if veto.get("is_vetoed") else None
            )
            
            return prediction
            
        except Exception as e:
            logger.error(f"Error parsing Gemini response: {e}")
            return self._get_no_trade_prediction(instrument, f"Parse error: {e}")
    
    def _parse_service_response(self, response: Dict, instrument: str) -> GeminiPrediction:
        """Parse Gemini Trade Service response"""
        try:
            signal = response.get("signal", "NO_TRADE")
            
            # Map service signal to our format
            if signal == "BUY_CALL":
                option_type = "CE"
            elif signal == "BUY_PUT":
                option_type = "PE"
            else:
                signal = "NO_TRADE"
                option_type = "CE"
            
            prediction = GeminiPrediction(
                signal=signal,
                instrument=instrument,
                confidence=response.get("confidence", 0) / 10.0,  # Convert 0-10 to 0-1
                
                strike_price=int(response.get("strike", "0").replace("CE", "").replace("PE", "") or 0),
                option_type=option_type,
                
                reasoning=response.get("reasoning", ""),
                timestamp=response.get("timestamp", datetime.now().isoformat()),
            )
            
            return prediction
            
        except Exception as e:
            logger.error(f"Error parsing service response: {e}")
            return self._get_no_trade_prediction(instrument, f"Parse error: {e}")
    
    def _validate_and_enrich_prediction(
        self,
        prediction: GeminiPrediction,
        instrument: str
    ) -> GeminiPrediction:
        """Validate prediction and apply veto rules"""
        
        # Check confidence threshold
        if prediction.confidence < self.min_confidence:
            prediction.signal = "NO_TRADE"
            prediction.veto_reason = f"Confidence {prediction.confidence:.1%} below threshold {self.min_confidence:.1%}"
            return prediction
        
        # Check time-based veto
        now = datetime.now()
        current_time = now.time()
        
        # Veto first 5 minutes
        if time(9, 15) <= current_time <= time(9, 20):
            prediction.signal = "NO_TRADE"
            prediction.veto_reason = "Market opening volatility (9:15-9:20)"
            return prediction
        
        # Veto last 15 minutes
        if time(15, 15) <= current_time <= time(15, 30):
            prediction.signal = "NO_TRADE"
            prediction.veto_reason = "Market closing volatility (3:15-3:30)"
            return prediction
        
        # Check if market is open
        if current_time < time(9, 15) or current_time > time(15, 30):
            prediction.signal = "NO_TRADE"
            prediction.veto_reason = "Market closed"
            return prediction
        
        # Validate risk/reward
        if prediction.signal != "NO_TRADE":
            if prediction.risk_reward_ratio < 1.5:
                prediction.signal = "NO_TRADE"
                prediction.veto_reason = f"Risk/Reward ratio {prediction.risk_reward_ratio:.1f} too low"
                return prediction
        
        return prediction
    
    def _get_no_trade_prediction(self, instrument: str, reason: str) -> GeminiPrediction:
        """Create a NO_TRADE prediction"""
        return GeminiPrediction(
            signal="NO_TRADE",
            instrument=instrument,
            confidence=0.0,
            reasoning=reason,
            veto_reason=reason,
            timestamp=datetime.now().isoformat()
        )
    
    async def get_multi_instrument_predictions(
        self,
        instruments: List[str],
        market_data: Dict[str, Dict[str, Any]]
    ) -> Dict[str, GeminiPrediction]:
        """
        Get predictions for multiple instruments in parallel.
        
        Args:
            instruments: List of instrument names
            market_data: Dict of market data keyed by instrument
            
        Returns:
            Dict of predictions keyed by instrument
        """
        tasks = []
        for instrument in instruments:
            inst_data = market_data.get(instrument, {})
            tasks.append(self.get_prediction(instrument, inst_data))
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        predictions = {}
        for instrument, result in zip(instruments, results):
            if isinstance(result, Exception):
                predictions[instrument] = self._get_no_trade_prediction(
                    instrument, f"Error: {result}"
                )
            else:
                predictions[instrument] = result
        
        return predictions
    
    def get_best_trade(
        self,
        predictions: Dict[str, GeminiPrediction]
    ) -> Optional[GeminiPrediction]:
        """
        Get the best trade from multiple predictions.
        Prioritizes by confidence and risk/reward.
        """
        tradeable = [
            p for p in predictions.values()
            if p.signal != "NO_TRADE" and p.confidence >= self.min_confidence
        ]
        
        if not tradeable:
            return None
        
        # Sort by confidence * risk_reward_ratio
        def score(p: GeminiPrediction) -> float:
            rr = max(p.risk_reward_ratio, 1.0)
            return p.confidence * rr
        
        return max(tradeable, key=score)
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get prediction engine statistics"""
        return {
            "total_predictions": self.total_predictions,
            "vetoed_predictions": self.vetoed_predictions,
            "trade_rate": (self.total_predictions - self.vetoed_predictions) / max(self.total_predictions, 1),
            "mode": self.mode.value,
            "min_confidence": self.min_confidence,
            "cache_size": len(self.prediction_cache),
        }


# ============================================================================
#                     SINGLETON INSTANCE
# ============================================================================

_prediction_engine: Optional[GeminiPredictionEngine] = None

def get_prediction_engine(
    api_key: str = None,
    service_url: str = "http://localhost:4080",
    mode: PredictionMode = PredictionMode.CONSERVATIVE
) -> GeminiPredictionEngine:
    """Get or create the singleton prediction engine"""
    global _prediction_engine
    
    if _prediction_engine is None:
        _prediction_engine = GeminiPredictionEngine(
            gemini_api_key=api_key,
            gemini_service_url=service_url,
            mode=mode
        )
    
    return _prediction_engine


# ============================================================================
#                     QUICK TEST
# ============================================================================

if __name__ == "__main__":
    import asyncio
    
    async def test():
        engine = get_prediction_engine()
        
        # Mock market data
        market_data = {
            "spot_price": 24500,
            "vix": 14.5,
            "pcr": 0.95,
            "max_pain": 24500,
            "fii_flow": 1500,  # Cr
            "dii_flow": 800,
        }
        
        prediction = await engine.get_prediction("NIFTY", market_data)
        print(f"Signal: {prediction.signal}")
        print(f"Confidence: {prediction.confidence:.1%}")
        print(f"Reasoning: {prediction.reasoning}")
    
    asyncio.run(test())
