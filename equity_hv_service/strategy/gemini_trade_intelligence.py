"""
╔══════════════════════════════════════════════════════════════════════════════════════╗
║                    GEMINI TRADE INTELLIGENCE ENGINE v1.0                             ║
║         Complete AI-Powered Trade Lifecycle Management with Gemini 3 Pro            ║
╠══════════════════════════════════════════════════════════════════════════════════════╣
║                                                                                      ║
║  STRATEGY: PROBE → CONFIRM → SCALE → MONITOR → EXIT                                ║
║  ─────────────────────────────────────────────────────────────────────────────────  ║
║                                                                                      ║
║  PHASE 1: PROBE ENTRY (10% Capital)                                                 ║
║    → Enter with minimal capital to test the trade                                   ║
║    → Wide stoploss (50% of premium)                                                 ║
║    → Monitor for confirmation                                                        ║
║                                                                                      ║
║  PHASE 2: SCALE UP (90% Capital on Gemini Confirmation)                             ║
║    → Tier 3 Gemini Pro confirms momentum is strong                                  ║
║    → Scale to full position                                                          ║
║    → Adjust stoploss to breakeven on probe                                          ║
║                                                                                      ║
║  PHASE 3: CONTINUOUS MONITORING                                                      ║
║    → Gemini 3 Pro consulted every 30 seconds                                        ║
║    → Different prompts for different scenarios                                       ║
║    → Momentum exhaustion detection                                                   ║
║                                                                                      ║
║  PHASE 4: INTELLIGENT EXIT                                                           ║
║    → If wrong: Exit probe with minimal loss                                         ║
║    → If right: Let profits run with 50-point trailing                               ║
║    → Gemini decides optimal exit timing                                             ║
║                                                                                      ║
║  GEMINI ENDPOINTS:                                                                   ║
║    /api/gemini/probe-confirmation     → Confirm probe success                       ║
║    /api/gemini/scale-decision         → Decide to scale up                          ║
║    /api/gemini/exit-analysis          → Real-time exit analysis                     ║
║    /api/gemini/loss-minimization      → Minimize loss strategy                      ║
║    /api/gemini/momentum-status        → Check momentum health                       ║
║                                                                                      ║
╚══════════════════════════════════════════════════════════════════════════════════════╝
"""

import asyncio
import aiohttp
import json
import logging
import os
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
import uuid

logger = logging.getLogger(__name__ + '.gemini_intelligence')


# ============================================================================
# CONFIGURATION
# ============================================================================

@dataclass
class GeminiConfig:
    """Gemini API Configuration from service_config.json"""
    tier_3_api_key: str = "AIzaSyA7FfMquiCuzLkbUryGw_7woTQ4KQngFG0"
    tier_3_model: str = "gemini-3-pro"
    base_url: str = "https://generativelanguage.googleapis.com/v1beta/models"
    local_service_url: str = "http://localhost:4080"
    temperature: float = 0.15
    max_tokens: int = 8192
    
    # Fallback to local service if direct API fails
    use_local_fallback: bool = True


@dataclass
class ProbeScaleConfig:
    """Probe and Scale Configuration"""
    # Capital Allocation
    probe_capital_percent: float = 10.0      # Initial probe: 10% of allocated capital
    scale_capital_percent: float = 90.0      # Scale up: remaining 90%
    
    # Stoploss (Wide - 50% of premium)
    probe_stoploss_percent: float = 50.0     # 50% stoploss on probe (wide)
    scaled_stoploss_percent: float = 30.0    # 30% stoploss after scaling
    
    # Trailing Stop
    trailing_activation_profit_percent: float = 30.0   # Activate trailing after 30% profit
    trailing_distance_percent: float = 20.0            # Trail at 20% from peak
    
    # Confirmation Thresholds
    min_profit_to_confirm_percent: float = 10.0   # Need 10% profit to consider scaling
    min_gemini_confidence_to_scale: float = 85.0  # Need 85% Gemini confidence to scale
    max_loss_to_abort_percent: float = 25.0       # Abort if loss exceeds 25% on probe
    
    # Timing
    probe_confirmation_timeout_seconds: int = 120   # 2 minutes to confirm probe
    gemini_check_interval_seconds: int = 30         # Check Gemini every 30 seconds
    max_holding_minutes: int = 60                   # Maximum holding time


# ============================================================================
# ENUMS
# ============================================================================

class TradePhase(Enum):
    """Trade lifecycle phases"""
    PENDING = "pending"
    PROBE = "probe"                 # Initial 10% entry
    AWAITING_CONFIRMATION = "awaiting_confirmation"
    SCALING = "scaling"             # Adding 90% position
    FULL_POSITION = "full_position" # Complete position
    EXITING = "exiting"
    EXITED = "exited"
    ABORTED = "aborted"             # Trade went wrong, exited early


class GeminiDecision(Enum):
    """Gemini decision types"""
    SCALE_UP = "scale_up"           # Add more capital
    HOLD = "hold"                   # Keep current position
    PARTIAL_EXIT = "partial_exit"   # Exit some quantity
    FULL_EXIT = "full_exit"         # Exit everything
    ABORT = "abort"                 # Trade failed, minimize loss


class MomentumStatus(Enum):
    """Momentum health status"""
    STRONG = "strong"               # Momentum intact, hold/scale
    MODERATE = "moderate"           # Momentum okay, hold
    WEAKENING = "weakening"         # Momentum fading, prepare exit
    EXHAUSTED = "exhausted"         # Momentum gone, exit now
    REVERSING = "reversing"         # Trend reversing, exit immediately


# ============================================================================
# DATA CLASSES
# ============================================================================

@dataclass
class ProbePosition:
    """Probe position tracking"""
    trade_id: str
    symbol: str
    option_type: str          # CE or PE
    strike: float
    expiry: str
    
    # Entry details
    entry_price: float
    entry_time: datetime
    probe_quantity: int       # 10% quantity
    probe_capital: float      # 10% capital used
    
    # Current state
    current_price: float = 0.0
    highest_price: float = 0.0
    lowest_price: float = 0.0
    
    # Stoploss
    stoploss_price: float = 0.0
    trailing_stop_price: float = 0.0
    trailing_activated: bool = False
    
    # P&L
    unrealized_pnl: float = 0.0
    pnl_percent: float = 0.0
    
    # Phase tracking
    phase: TradePhase = TradePhase.PROBE
    
    # Scaling info
    scaled_quantity: int = 0
    scaled_capital: float = 0.0
    scale_entry_price: float = 0.0
    scale_time: Optional[datetime] = None
    
    # Gemini tracking
    last_gemini_check: Optional[datetime] = None
    gemini_checks_count: int = 0
    last_gemini_decision: str = ""
    momentum_status: MomentumStatus = MomentumStatus.STRONG
    
    # Exit tracking
    exit_price: float = 0.0
    exit_time: Optional[datetime] = None
    exit_reason: str = ""
    realized_pnl: float = 0.0
    
    def total_quantity(self) -> int:
        return self.probe_quantity + self.scaled_quantity
    
    def total_capital(self) -> float:
        return self.probe_capital + self.scaled_capital
    
    def update_price(self, price: float):
        self.current_price = price
        self.highest_price = max(self.highest_price, price)
        self.lowest_price = min(self.lowest_price, price) if self.lowest_price > 0 else price
        
        # Calculate P&L
        avg_entry = self._calculate_avg_entry()
        self.unrealized_pnl = (price - avg_entry) * self.total_quantity()
        self.pnl_percent = ((price - avg_entry) / avg_entry) * 100 if avg_entry > 0 else 0
    
    def _calculate_avg_entry(self) -> float:
        if self.scaled_quantity > 0:
            total_cost = (self.entry_price * self.probe_quantity) + (self.scale_entry_price * self.scaled_quantity)
            return total_cost / self.total_quantity()
        return self.entry_price


@dataclass
class GeminiAnalysisResult:
    """Result from Gemini analysis"""
    decision: GeminiDecision
    confidence: float
    reasoning: str
    momentum_status: MomentumStatus
    recommended_action: str
    urgency: str                    # immediate, soon, can_wait
    exit_percent: float = 0.0       # For partial exit
    additional_insights: Dict = field(default_factory=dict)
    raw_response: str = ""
    timestamp: datetime = field(default_factory=datetime.now)


# ============================================================================
# GEMINI TRADE INTELLIGENCE ENGINE
# ============================================================================

class GeminiTradeIntelligence:
    """
    Complete AI-powered trade management using Gemini 3 Pro.
    
    Features:
    - Probe entry with 10% capital
    - AI confirmation before scaling
    - Continuous monitoring
    - Intelligent exit decisions
    - Loss minimization
    """
    
    def __init__(
        self,
        gemini_config: GeminiConfig = None,
        probe_config: ProbeScaleConfig = None
    ):
        self.gemini_config = gemini_config or GeminiConfig()
        self.probe_config = probe_config or ProbeScaleConfig()
        
        self.session: Optional[aiohttp.ClientSession] = None
        self.active_positions: Dict[str, ProbePosition] = {}
        
        logger.info("GeminiTradeIntelligence initialized with probe-scale strategy")
    
    async def _ensure_session(self):
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=60)
            )
    
    async def close(self):
        if self.session and not self.session.closed:
            await self.session.close()
    
    # =========================================================================
    # CORE GEMINI API CALLS
    # =========================================================================
    
    async def _call_gemini(self, prompt: str, endpoint_context: str = "") -> Dict[str, Any]:
        """
        Call Gemini 3 Pro API with the given prompt.
        Uses direct API first, falls back to local service.
        """
        await self._ensure_session()
        
        logger.debug(f"Calling Gemini for: {endpoint_context}")
        
        # Try direct Gemini API first
        try:
            url = f"{self.gemini_config.base_url}/{self.gemini_config.tier_3_model}:generateContent"
            url += f"?key={self.gemini_config.tier_3_api_key}"
            
            payload = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {
                    "temperature": self.gemini_config.temperature,
                    "maxOutputTokens": self.gemini_config.max_tokens,
                    "topP": 0.9,
                    "topK": 40
                }
            }
            
            async with self.session.post(url, json=payload) as response:
                if response.status == 200:
                    result = await response.json()
                    if "candidates" in result:
                        text = result["candidates"][0]["content"]["parts"][0]["text"]
                        return {"success": True, "response": text, "source": "direct_api"}
                else:
                    error_text = await response.text()
                    logger.warning(f"Gemini API error: {response.status} - {error_text[:200]}")
        except Exception as e:
            logger.warning(f"Direct Gemini API failed: {e}")
        
        # Fallback to local service
        if self.gemini_config.use_local_fallback:
            return await self._call_local_gemini_service(prompt, endpoint_context)
        
        return {"success": False, "response": "", "source": "none"}
    
    async def _call_local_gemini_service(self, prompt: str, endpoint_context: str) -> Dict[str, Any]:
        """Call local Gemini trade service as fallback"""
        try:
            url = f"{self.gemini_config.local_service_url}/api/gemini/analyze"
            payload = {
                "prompt": prompt,
                "model": self.gemini_config.tier_3_model,
                "context": endpoint_context,
                "temperature": self.gemini_config.temperature
            }
            
            async with self.session.post(url, json=payload) as response:
                if response.status == 200:
                    result = await response.json()
                    return {
                        "success": True, 
                        "response": result.get("analysis", result.get("response", "")),
                        "source": "local_service"
                    }
        except Exception as e:
            logger.error(f"Local Gemini service failed: {e}")
        
        return {"success": False, "response": "", "source": "none"}
    
    def _parse_json_response(self, response_text: str) -> Optional[Dict]:
        """Extract JSON from Gemini response"""
        try:
            # Find JSON in response
            json_start = response_text.find("{")
            json_end = response_text.rfind("}") + 1
            if json_start != -1 and json_end > json_start:
                return json.loads(response_text[json_start:json_end])
        except json.JSONDecodeError:
            logger.warning("Failed to parse JSON from Gemini response")
        return None
    
    # =========================================================================
    # ENDPOINT 1: PROBE CONFIRMATION
    # /api/gemini/probe-confirmation
    # =========================================================================
    
    async def analyze_probe_confirmation(self, position: ProbePosition) -> GeminiAnalysisResult:
        """
        Analyze if probe position should be confirmed for scaling.
        Called after probe entry to decide if we should add more capital.
        """
        prompt = f"""
You are an expert F&O options trader analyzing a PROBE POSITION to decide if it should be scaled up.

═══════════════════════════════════════════════════════════════════════════════
PROBE POSITION DETAILS:
═══════════════════════════════════════════════════════════════════════════════
Symbol: {position.symbol}
Option Type: {position.option_type}
Strike: {position.strike}
Expiry: {position.expiry}

ENTRY INFORMATION:
- Entry Price: ₹{position.entry_price:.2f}
- Entry Time: {position.entry_time.strftime("%H:%M:%S")}
- Probe Quantity: {position.probe_quantity} lots
- Probe Capital: ₹{position.probe_capital:,.2f}

CURRENT STATE:
- Current Price: ₹{position.current_price:.2f}
- Highest Price: ₹{position.highest_price:.2f}
- Lowest Price: ₹{position.lowest_price:.2f}
- Unrealized P&L: ₹{position.unrealized_pnl:,.2f}
- P&L Percent: {position.pnl_percent:+.2f}%
- Time in Trade: {(datetime.now() - position.entry_time).total_seconds() / 60:.1f} minutes

STOPLOSS:
- Current Stoploss: ₹{position.stoploss_price:.2f} (50% of entry)
- Distance to SL: {((position.current_price - position.stoploss_price) / position.current_price) * 100:.1f}%

═══════════════════════════════════════════════════════════════════════════════
DECISION REQUIRED:
═══════════════════════════════════════════════════════════════════════════════
Should we SCALE UP this probe position by adding 90% more capital?

SCALING CRITERIA:
1. Minimum 10% profit on probe for consideration
2. Strong momentum confirmation
3. No reversal signals
4. Favorable market conditions
5. High confidence in continued move

ANALYZE:
1. Is the initial direction validated?
2. Is momentum building or fading?
3. What's the probability of continued move?
4. Risk of reversal?
5. Time decay consideration

RESPOND IN EXACT JSON FORMAT:
{{
    "decision": "SCALE_UP" | "HOLD" | "ABORT",
    "confidence": <60-100>,
    "momentum_status": "STRONG" | "MODERATE" | "WEAKENING" | "EXHAUSTED",
    "reasoning": "<detailed 3-line analysis>",
    "recommended_action": "<specific action to take>",
    "urgency": "immediate" | "soon" | "can_wait",
    "scale_percent": <0-100 if scaling>,
    "additional_insights": {{
        "reversal_risk": <0-100>,
        "momentum_strength": <0-100>,
        "time_decay_impact": "low" | "medium" | "high",
        "market_alignment": "favorable" | "neutral" | "unfavorable"
    }}
}}
"""
        
        result = await self._call_gemini(prompt, "probe-confirmation")
        return self._parse_analysis_result(result, "probe-confirmation")
    
    # =========================================================================
    # ENDPOINT 2: SCALE DECISION
    # /api/gemini/scale-decision
    # =========================================================================
    
    async def analyze_scale_decision(
        self, 
        position: ProbePosition,
        remaining_capital: float,
        market_context: Dict = None
    ) -> GeminiAnalysisResult:
        """
        Final decision on whether to scale up and by how much.
        Called when probe is profitable and conditions are favorable.
        """
        market_context = market_context or {}
        
        prompt = f"""
You are a senior options strategist making a CAPITAL DEPLOYMENT decision.

═══════════════════════════════════════════════════════════════════════════════
CURRENT PROBE POSITION:
═══════════════════════════════════════════════════════════════════════════════
Symbol: {position.symbol} {position.option_type}
Strike: {position.strike}
Entry: ₹{position.entry_price:.2f} → Current: ₹{position.current_price:.2f}
P&L: {position.pnl_percent:+.2f}%
Probe Capital: ₹{position.probe_capital:,.2f}
Momentum: {position.momentum_status.value}

═══════════════════════════════════════════════════════════════════════════════
SCALING OPPORTUNITY:
═══════════════════════════════════════════════════════════════════════════════
Available Capital for Scaling: ₹{remaining_capital:,.2f}
Maximum Scale (90% allocation): ₹{remaining_capital * 0.9:,.2f}
Current Position Profit Cushion: ₹{position.unrealized_pnl:,.2f}

MARKET CONTEXT:
{json.dumps(market_context, indent=2) if market_context else "Not available"}

═══════════════════════════════════════════════════════════════════════════════
SCALING DECISION FRAMEWORK:
═══════════════════════════════════════════════════════════════════════════════
1. AGGRESSIVE SCALE (100% of remaining): If confidence > 95%, momentum STRONG
2. STANDARD SCALE (75% of remaining): If confidence 85-95%, momentum STRONG/MODERATE
3. CONSERVATIVE SCALE (50% of remaining): If confidence 75-85%, momentum MODERATE
4. NO SCALE (HOLD probe): If confidence < 75% or momentum WEAKENING
5. ABORT: If momentum EXHAUSTED or REVERSING

RISK CONSIDERATION:
- Probe is already profitable, providing cushion
- Scaling at wrong time = larger loss
- Not scaling at right time = missed opportunity

RESPOND IN EXACT JSON FORMAT:
{{
    "decision": "SCALE_UP" | "HOLD" | "ABORT",
    "confidence": <60-100>,
    "scale_percent": <0-100>,
    "scale_capital": <amount in rupees>,
    "reasoning": "<detailed 4-line strategic reasoning>",
    "momentum_status": "STRONG" | "MODERATE" | "WEAKENING" | "EXHAUSTED",
    "recommended_action": "<exact action with quantities>",
    "urgency": "immediate" | "soon" | "can_wait",
    "new_stoploss_strategy": {{
        "probe_stoploss": "<move to breakeven or keep wide>",
        "scale_stoploss": "<stoploss for new quantity>"
    }},
    "profit_targets": {{
        "target_1": <price for 50% exit>,
        "target_2": <price for remaining exit>
    }},
    "risk_assessment": {{
        "max_loss_scenario": "<worst case>",
        "expected_outcome": "<most likely>",
        "risk_reward_ratio": "<ratio>"
    }}
}}
"""
        
        result = await self._call_gemini(prompt, "scale-decision")
        return self._parse_analysis_result(result, "scale-decision")
    
    # =========================================================================
    # ENDPOINT 3: EXIT ANALYSIS
    # /api/gemini/exit-analysis
    # =========================================================================
    
    async def analyze_exit(self, position: ProbePosition) -> GeminiAnalysisResult:
        """
        Real-time exit analysis for active position.
        Called every 30 seconds while trade is running.
        """
        time_in_trade = (datetime.now() - position.entry_time).total_seconds() / 60
        
        prompt = f"""
You are monitoring an ACTIVE OPTIONS POSITION and must decide: EXIT or CONTINUE?

═══════════════════════════════════════════════════════════════════════════════
POSITION STATUS:
═══════════════════════════════════════════════════════════════════════════════
Symbol: {position.symbol} {position.option_type} @ {position.strike}
Phase: {position.phase.value}

ENTRY & CURRENT:
- Entry Price: ₹{position.entry_price:.2f}
- Current Price: ₹{position.current_price:.2f}
- Highest Price: ₹{position.highest_price:.2f}
- Lowest Price: ₹{position.lowest_price:.2f}

POSITION SIZE:
- Probe Quantity: {position.probe_quantity} lots
- Scaled Quantity: {position.scaled_quantity} lots
- Total Quantity: {position.total_quantity()} lots
- Total Capital: ₹{position.total_capital():,.2f}

P&L STATUS:
- Unrealized P&L: ₹{position.unrealized_pnl:,.2f}
- P&L Percent: {position.pnl_percent:+.2f}%
- Drawdown from High: {((position.highest_price - position.current_price) / position.highest_price) * 100:.1f}%

RISK LEVELS:
- Stoploss: ₹{position.stoploss_price:.2f}
- Trailing Stop: ₹{position.trailing_stop_price:.2f} (Active: {position.trailing_activated})
- Distance to SL: ₹{position.current_price - position.stoploss_price:.2f}

TIME FACTORS:
- Time in Trade: {time_in_trade:.1f} minutes
- Gemini Checks: {position.gemini_checks_count}
- Last Decision: {position.last_gemini_decision}

MOMENTUM:
- Current Status: {position.momentum_status.value}

═══════════════════════════════════════════════════════════════════════════════
EXIT DECISION FRAMEWORK:
═══════════════════════════════════════════════════════════════════════════════
IMMEDIATE EXIT IF:
- Momentum REVERSING or EXHAUSTED
- Price dropped 30%+ from high
- Clear reversal pattern
- Time decay becoming significant

PARTIAL EXIT (50%) IF:
- Profit > 50% and momentum WEAKENING
- Reached first target
- Risk:Reward deteriorating

HOLD IF:
- Momentum STRONG or MODERATE
- Price making new highs
- Trend intact
- Good time remaining

RESPOND IN EXACT JSON FORMAT:
{{
    "decision": "FULL_EXIT" | "PARTIAL_EXIT" | "HOLD",
    "confidence": <60-100>,
    "exit_percent": <0-100>,
    "reasoning": "<detailed 3-line analysis>",
    "momentum_status": "STRONG" | "MODERATE" | "WEAKENING" | "EXHAUSTED" | "REVERSING",
    "urgency": "immediate" | "soon" | "can_wait",
    "recommended_action": "<specific action>",
    "price_targets": {{
        "immediate_target": <next price level>,
        "exit_trigger": <price that triggers exit>
    }},
    "risk_update": {{
        "new_stoploss": <updated stoploss if any>,
        "trailing_update": <trailing stop update>
    }},
    "next_check_seconds": <when to check again>
}}
"""
        
        result = await self._call_gemini(prompt, "exit-analysis")
        return self._parse_analysis_result(result, "exit-analysis")
    
    # =========================================================================
    # ENDPOINT 4: LOSS MINIMIZATION
    # /api/gemini/loss-minimization
    # =========================================================================
    
    async def analyze_loss_minimization(self, position: ProbePosition) -> GeminiAnalysisResult:
        """
        Analyze how to minimize loss when trade goes wrong.
        Called when position is in loss and needs damage control.
        """
        prompt = f"""
You are a RISK MANAGER handling a LOSING POSITION. Objective: MINIMIZE LOSS.

═══════════════════════════════════════════════════════════════════════════════
LOSING POSITION:
═══════════════════════════════════════════════════════════════════════════════
Symbol: {position.symbol} {position.option_type}
Entry: ₹{position.entry_price:.2f}
Current: ₹{position.current_price:.2f}
Loss: {position.pnl_percent:.2f}% (₹{abs(position.unrealized_pnl):,.2f})

Position Size:
- Probe Quantity: {position.probe_quantity} lots (10% capital)
- Scaled Quantity: {position.scaled_quantity} lots (90% capital)
- Total at Risk: ₹{position.total_capital():,.2f}

Current Stoploss: ₹{position.stoploss_price:.2f} (50% wide)
Distance to SL: ₹{position.current_price - position.stoploss_price:.2f}

═══════════════════════════════════════════════════════════════════════════════
LOSS MINIMIZATION STRATEGIES:
═══════════════════════════════════════════════════════════════════════════════

1. IMMEDIATE EXIT: Accept current loss, prevent further damage
   - Best if momentum clearly reversed
   - No chance of recovery

2. PARTIAL EXIT: Exit 50-75% now, hold remainder for potential recovery
   - Reduces exposure
   - Keeps some upside potential

3. SCALE DOWN: Exit scaled portion, keep probe only
   - Limits max loss to probe amount
   - Wait for confirmation to re-enter

4. HEDGE: Add opposite position to neutralize
   - Complex but limits further loss
   - Allows time for analysis

5. HOLD: Keep position if recovery likely
   - Only if momentum shows signs of returning
   - Must have conviction

ANALYZE:
1. Is there any chance of recovery?
2. What's the momentum doing now?
3. How much more can we lose before stoploss?
4. Best strategy to minimize total loss?

RESPOND IN EXACT JSON FORMAT:
{{
    "decision": "FULL_EXIT" | "PARTIAL_EXIT" | "SCALE_DOWN" | "HOLD",
    "confidence": <60-100>,
    "exit_percent": <0-100>,
    "reasoning": "<detailed loss analysis>",
    "momentum_status": "STRONG" | "MODERATE" | "WEAKENING" | "EXHAUSTED" | "REVERSING",
    "urgency": "immediate" | "soon" | "can_wait",
    "recommended_action": "<exact action to minimize loss>",
    "loss_analysis": {{
        "current_loss": <current loss amount>,
        "max_loss_if_hold": <max loss at stoploss>,
        "expected_loss_with_action": <loss after recommended action>,
        "loss_saved": <amount saved by action>
    }},
    "recovery_probability": <0-100>,
    "alternative_strategies": [
        "<strategy 1>",
        "<strategy 2>"
    ]
}}
"""
        
        result = await self._call_gemini(prompt, "loss-minimization")
        return self._parse_analysis_result(result, "loss-minimization")
    
    # =========================================================================
    # ENDPOINT 5: MOMENTUM STATUS
    # /api/gemini/momentum-status
    # =========================================================================
    
    async def analyze_momentum_status(
        self, 
        position: ProbePosition,
        price_history: List[float] = None,
        volume_data: Dict = None
    ) -> GeminiAnalysisResult:
        """
        Detailed momentum health check.
        Called to assess if momentum is still intact.
        """
        price_history = price_history or []
        volume_data = volume_data or {}
        
        prompt = f"""
You are a MOMENTUM ANALYST evaluating the HEALTH of an active trade's momentum.

═══════════════════════════════════════════════════════════════════════════════
POSITION:
═══════════════════════════════════════════════════════════════════════════════
Symbol: {position.symbol} {position.option_type}
Direction: {"BULLISH" if position.option_type == "CE" else "BEARISH"}
Entry: ₹{position.entry_price:.2f}
Current: ₹{position.current_price:.2f}
Change: {position.pnl_percent:+.2f}%

═══════════════════════════════════════════════════════════════════════════════
PRICE ACTION:
═══════════════════════════════════════════════════════════════════════════════
Recent Prices: {price_history[-10:] if len(price_history) >= 10 else price_history}
Highest: ₹{position.highest_price:.2f}
Lowest: ₹{position.lowest_price:.2f}
Current vs High: {((position.highest_price - position.current_price) / position.highest_price) * 100:.2f}% below

VOLUME DATA:
{json.dumps(volume_data, indent=2) if volume_data else "Not available"}

═══════════════════════════════════════════════════════════════════════════════
MOMENTUM CLASSIFICATION:
═══════════════════════════════════════════════════════════════════════════════
STRONG: Price making new highs, volume increasing, trend accelerating
MODERATE: Price stable, trend intact but not accelerating
WEAKENING: Price consolidating, lower highs forming
EXHAUSTED: Price stalling, volume declining, no new highs for extended period
REVERSING: Price breaking trend, opposite direction forming

ANALYZE:
1. Velocity: How fast is price moving in trade direction?
2. Acceleration: Is momentum increasing or decreasing?
3. Volume: Does volume confirm the move?
4. Pattern: Any reversal patterns forming?
5. Exhaustion signals: Signs of top/bottom formation?

RESPOND IN EXACT JSON FORMAT:
{{
    "momentum_status": "STRONG" | "MODERATE" | "WEAKENING" | "EXHAUSTED" | "REVERSING",
    "confidence": <60-100>,
    "momentum_score": <0-100>,
    "reasoning": "<detailed momentum analysis>",
    "velocity": {{
        "value": <price change rate>,
        "trend": "accelerating" | "stable" | "decelerating"
    }},
    "exhaustion_signals": {{
        "present": true | false,
        "signals": ["<signal 1>", "<signal 2>"]
    }},
    "reversal_risk": <0-100>,
    "recommended_action": "HOLD" | "PREPARE_EXIT" | "EXIT_NOW",
    "time_remaining_estimate": "<how long momentum might last>",
    "key_levels": {{
        "support": <price>,
        "resistance": <price>,
        "breakout_trigger": <price>,
        "breakdown_trigger": <price>
    }}
}}
"""
        
        result = await self._call_gemini(prompt, "momentum-status")
        return self._parse_analysis_result(result, "momentum-status")
    
    # =========================================================================
    # HELPER METHODS
    # =========================================================================
    
    def _parse_analysis_result(self, api_result: Dict, endpoint: str) -> GeminiAnalysisResult:
        """Parse Gemini API response into structured result"""
        if not api_result.get("success"):
            return GeminiAnalysisResult(
                decision=GeminiDecision.HOLD,
                confidence=0,
                reasoning="Failed to get Gemini response",
                momentum_status=MomentumStatus.MODERATE,
                recommended_action="Hold - AI unavailable",
                urgency="can_wait"
            )
        
        response_text = api_result.get("response", "")
        parsed = self._parse_json_response(response_text)
        
        if not parsed:
            return GeminiAnalysisResult(
                decision=GeminiDecision.HOLD,
                confidence=50,
                reasoning="Failed to parse Gemini response",
                momentum_status=MomentumStatus.MODERATE,
                recommended_action="Hold - parse error",
                urgency="can_wait",
                raw_response=response_text
            )
        
        # Map decision string to enum
        decision_map = {
            "SCALE_UP": GeminiDecision.SCALE_UP,
            "HOLD": GeminiDecision.HOLD,
            "PARTIAL_EXIT": GeminiDecision.PARTIAL_EXIT,
            "FULL_EXIT": GeminiDecision.FULL_EXIT,
            "ABORT": GeminiDecision.ABORT,
            "SCALE_DOWN": GeminiDecision.PARTIAL_EXIT
        }
        
        momentum_map = {
            "STRONG": MomentumStatus.STRONG,
            "MODERATE": MomentumStatus.MODERATE,
            "WEAKENING": MomentumStatus.WEAKENING,
            "EXHAUSTED": MomentumStatus.EXHAUSTED,
            "REVERSING": MomentumStatus.REVERSING
        }
        
        decision_str = parsed.get("decision", "HOLD")
        momentum_str = parsed.get("momentum_status", "MODERATE")
        
        return GeminiAnalysisResult(
            decision=decision_map.get(decision_str, GeminiDecision.HOLD),
            confidence=float(parsed.get("confidence", 50)),
            reasoning=parsed.get("reasoning", ""),
            momentum_status=momentum_map.get(momentum_str, MomentumStatus.MODERATE),
            recommended_action=parsed.get("recommended_action", ""),
            urgency=parsed.get("urgency", "can_wait"),
            exit_percent=float(parsed.get("exit_percent", 0)),
            additional_insights=parsed,
            raw_response=response_text
        )
    
    # =========================================================================
    # POSITION MANAGEMENT
    # =========================================================================
    
    async def create_probe_position(
        self,
        symbol: str,
        option_type: str,
        strike: float,
        expiry: str,
        entry_price: float,
        total_capital: float,
        lot_size: int
    ) -> ProbePosition:
        """Create a new probe position with 10% capital"""
        
        # Calculate probe size (10% of allocated capital)
        probe_capital = total_capital * (self.probe_config.probe_capital_percent / 100)
        position_value = entry_price * lot_size
        probe_quantity = max(1, int(probe_capital / position_value))
        actual_probe_capital = probe_quantity * position_value
        
        # Wide stoploss (50% of entry price)
        stoploss_price = entry_price * (1 - self.probe_config.probe_stoploss_percent / 100)
        
        position = ProbePosition(
            trade_id=f"PROBE_{uuid.uuid4().hex[:8].upper()}",
            symbol=symbol,
            option_type=option_type,
            strike=strike,
            expiry=expiry,
            entry_price=entry_price,
            entry_time=datetime.now(),
            probe_quantity=probe_quantity,
            probe_capital=actual_probe_capital,
            current_price=entry_price,
            highest_price=entry_price,
            lowest_price=entry_price,
            stoploss_price=stoploss_price,
            phase=TradePhase.PROBE
        )
        
        self.active_positions[position.trade_id] = position
        
        logger.info(f"📊 PROBE ENTRY: {symbol} {option_type} @ ₹{entry_price:.2f}")
        logger.info(f"   Quantity: {probe_quantity} lots | Capital: ₹{actual_probe_capital:,.2f}")
        logger.info(f"   Stoploss: ₹{stoploss_price:.2f} (50% wide)")
        
        return position
    
    async def check_and_process_position(self, position: ProbePosition) -> Dict[str, Any]:
        """
        Main monitoring loop for a position.
        Decides scaling, exit, or loss minimization.
        """
        result = {
            "action": "HOLD",
            "details": {},
            "gemini_analysis": None
        }
        
        # Update check count
        position.gemini_checks_count += 1
        position.last_gemini_check = datetime.now()
        
        # Different handling based on phase
        if position.phase == TradePhase.PROBE:
            # Check if probe should be confirmed/scaled
            if position.pnl_percent >= self.probe_config.min_profit_to_confirm_percent:
                # Profitable probe - check for scale up
                analysis = await self.analyze_probe_confirmation(position)
                result["gemini_analysis"] = analysis
                
                if analysis.decision == GeminiDecision.SCALE_UP and \
                   analysis.confidence >= self.probe_config.min_gemini_confidence_to_scale:
                    result["action"] = "SCALE_UP"
                    result["details"] = {"confidence": analysis.confidence}
                    position.phase = TradePhase.AWAITING_CONFIRMATION
                    
            elif position.pnl_percent <= -self.probe_config.max_loss_to_abort_percent:
                # Probe failing - minimize loss
                analysis = await self.analyze_loss_minimization(position)
                result["gemini_analysis"] = analysis
                result["action"] = "ABORT"
                result["details"] = {"reason": "probe_failed", "loss": position.pnl_percent}
                
        elif position.phase in [TradePhase.FULL_POSITION, TradePhase.AWAITING_CONFIRMATION]:
            # Active position - regular exit check
            analysis = await self.analyze_exit(position)
            result["gemini_analysis"] = analysis
            position.momentum_status = analysis.momentum_status
            position.last_gemini_decision = analysis.decision.value
            
            if analysis.decision == GeminiDecision.FULL_EXIT:
                result["action"] = "EXIT"
                result["details"] = {"urgency": analysis.urgency, "reason": analysis.reasoning}
            elif analysis.decision == GeminiDecision.PARTIAL_EXIT:
                result["action"] = "PARTIAL_EXIT"
                result["details"] = {"exit_percent": analysis.exit_percent}
            
            # Check trailing stop update
            if position.pnl_percent >= self.probe_config.trailing_activation_profit_percent:
                if not position.trailing_activated:
                    position.trailing_activated = True
                    logger.info(f"📈 Trailing stop ACTIVATED for {position.symbol}")
                
                new_trail = position.current_price * (1 - self.probe_config.trailing_distance_percent / 100)
                if new_trail > position.trailing_stop_price:
                    position.trailing_stop_price = new_trail
        
        return result
    
    async def scale_up_position(
        self, 
        position: ProbePosition,
        remaining_capital: float,
        current_price: float,
        lot_size: int
    ) -> bool:
        """Scale up position after probe confirmation"""
        
        # Get scale decision from Gemini
        analysis = await self.analyze_scale_decision(position, remaining_capital)
        
        if analysis.decision != GeminiDecision.SCALE_UP:
            logger.info(f"Gemini says don't scale: {analysis.reasoning}")
            return False
        
        # Calculate scale quantity
        scale_capital = remaining_capital * (analysis.additional_insights.get("scale_percent", 75) / 100)
        position_value = current_price * lot_size
        scale_quantity = max(1, int(scale_capital / position_value))
        actual_scale_capital = scale_quantity * position_value
        
        # Update position
        position.scaled_quantity = scale_quantity
        position.scaled_capital = actual_scale_capital
        position.scale_entry_price = current_price
        position.scale_time = datetime.now()
        position.phase = TradePhase.FULL_POSITION
        
        # Update stoploss (tighter after scaling)
        avg_entry = position._calculate_avg_entry()
        position.stoploss_price = avg_entry * (1 - self.probe_config.scaled_stoploss_percent / 100)
        
        logger.info(f"📈 SCALED UP: {position.symbol}")
        logger.info(f"   Added: {scale_quantity} lots @ ₹{current_price:.2f}")
        logger.info(f"   Total Position: {position.total_quantity()} lots")
        logger.info(f"   New Stoploss: ₹{position.stoploss_price:.2f}")
        
        return True


# ============================================================================
# API ROUTER FOR GEMINI ENDPOINTS
# ============================================================================

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()

# Global intelligence instance
_intelligence: Optional[GeminiTradeIntelligence] = None


def get_intelligence() -> GeminiTradeIntelligence:
    global _intelligence
    if _intelligence is None:
        _intelligence = GeminiTradeIntelligence()
    return _intelligence


class ProbeConfirmationRequest(BaseModel):
    trade_id: str
    symbol: str
    option_type: str
    strike: float
    entry_price: float
    current_price: float
    highest_price: float
    lowest_price: float
    pnl_percent: float
    probe_quantity: int
    probe_capital: float
    entry_time: str


class ScaleDecisionRequest(BaseModel):
    trade_id: str
    symbol: str
    option_type: str
    strike: float
    current_price: float
    pnl_percent: float
    remaining_capital: float
    market_context: Optional[Dict] = None


class ExitAnalysisRequest(BaseModel):
    trade_id: str
    symbol: str
    option_type: str
    strike: float
    entry_price: float
    current_price: float
    highest_price: float
    pnl_percent: float
    total_quantity: int
    total_capital: float
    stoploss_price: float
    trailing_stop_price: float
    trailing_activated: bool
    time_in_trade_minutes: float


class LossMinimizationRequest(BaseModel):
    trade_id: str
    symbol: str
    option_type: str
    entry_price: float
    current_price: float
    pnl_percent: float
    probe_quantity: int
    scaled_quantity: int
    total_capital: float
    stoploss_price: float


class MomentumStatusRequest(BaseModel):
    symbol: str
    option_type: str
    entry_price: float
    current_price: float
    highest_price: float
    lowest_price: float
    price_history: Optional[List[float]] = None
    volume_data: Optional[Dict] = None


@router.post("/probe-confirmation")
async def probe_confirmation_endpoint(request: ProbeConfirmationRequest):
    """
    Analyze if probe position should be confirmed for scaling.
    """
    intelligence = get_intelligence()
    
    # Create temporary position object for analysis
    position = ProbePosition(
        trade_id=request.trade_id,
        symbol=request.symbol,
        option_type=request.option_type,
        strike=request.strike,
        expiry="",
        entry_price=request.entry_price,
        entry_time=datetime.fromisoformat(request.entry_time),
        probe_quantity=request.probe_quantity,
        probe_capital=request.probe_capital,
        current_price=request.current_price,
        highest_price=request.highest_price,
        lowest_price=request.lowest_price,
        stoploss_price=request.entry_price * 0.5,
        pnl_percent=request.pnl_percent
    )
    
    result = await intelligence.analyze_probe_confirmation(position)
    
    return {
        "decision": result.decision.value,
        "confidence": result.confidence,
        "momentum_status": result.momentum_status.value,
        "reasoning": result.reasoning,
        "recommended_action": result.recommended_action,
        "urgency": result.urgency,
        "additional_insights": result.additional_insights
    }


@router.post("/scale-decision")
async def scale_decision_endpoint(request: ScaleDecisionRequest):
    """
    Final decision on whether to scale up and by how much.
    """
    intelligence = get_intelligence()
    
    position = ProbePosition(
        trade_id=request.trade_id,
        symbol=request.symbol,
        option_type=request.option_type,
        strike=request.strike,
        expiry="",
        entry_price=request.current_price,  # Approximate
        entry_time=datetime.now(),
        probe_quantity=1,
        probe_capital=0,
        current_price=request.current_price,
        pnl_percent=request.pnl_percent
    )
    
    result = await intelligence.analyze_scale_decision(
        position, 
        request.remaining_capital,
        request.market_context
    )
    
    return {
        "decision": result.decision.value,
        "confidence": result.confidence,
        "reasoning": result.reasoning,
        "momentum_status": result.momentum_status.value,
        "recommended_action": result.recommended_action,
        "urgency": result.urgency,
        "scale_details": result.additional_insights
    }


@router.post("/exit-analysis")
async def exit_analysis_endpoint(request: ExitAnalysisRequest):
    """
    Real-time exit analysis for active position.
    Called every 30 seconds while trade is running.
    """
    intelligence = get_intelligence()
    
    position = ProbePosition(
        trade_id=request.trade_id,
        symbol=request.symbol,
        option_type=request.option_type,
        strike=request.strike,
        expiry="",
        entry_price=request.entry_price,
        entry_time=datetime.now() - timedelta(minutes=request.time_in_trade_minutes),
        probe_quantity=request.total_quantity // 2,
        probe_capital=request.total_capital / 2,
        current_price=request.current_price,
        highest_price=request.highest_price,
        stoploss_price=request.stoploss_price,
        trailing_stop_price=request.trailing_stop_price,
        trailing_activated=request.trailing_activated,
        pnl_percent=request.pnl_percent,
        scaled_quantity=request.total_quantity // 2,
        scaled_capital=request.total_capital / 2,
        phase=TradePhase.FULL_POSITION
    )
    
    result = await intelligence.analyze_exit(position)
    
    return {
        "decision": result.decision.value,
        "confidence": result.confidence,
        "exit_percent": result.exit_percent,
        "momentum_status": result.momentum_status.value,
        "reasoning": result.reasoning,
        "recommended_action": result.recommended_action,
        "urgency": result.urgency,
        "exit_details": result.additional_insights
    }


@router.post("/loss-minimization")
async def loss_minimization_endpoint(request: LossMinimizationRequest):
    """
    Analyze how to minimize loss when trade goes wrong.
    """
    intelligence = get_intelligence()
    
    position = ProbePosition(
        trade_id=request.trade_id,
        symbol=request.symbol,
        option_type=request.option_type,
        strike=0,
        expiry="",
        entry_price=request.entry_price,
        entry_time=datetime.now(),
        probe_quantity=request.probe_quantity,
        probe_capital=request.total_capital * 0.1,
        current_price=request.current_price,
        stoploss_price=request.stoploss_price,
        pnl_percent=request.pnl_percent,
        scaled_quantity=request.scaled_quantity,
        scaled_capital=request.total_capital * 0.9
    )
    
    result = await intelligence.analyze_loss_minimization(position)
    
    return {
        "decision": result.decision.value,
        "confidence": result.confidence,
        "exit_percent": result.exit_percent,
        "momentum_status": result.momentum_status.value,
        "reasoning": result.reasoning,
        "recommended_action": result.recommended_action,
        "urgency": result.urgency,
        "loss_analysis": result.additional_insights
    }


@router.post("/momentum-status")
async def momentum_status_endpoint(request: MomentumStatusRequest):
    """
    Detailed momentum health check.
    """
    intelligence = get_intelligence()
    
    position = ProbePosition(
        trade_id="TEMP",
        symbol=request.symbol,
        option_type=request.option_type,
        strike=0,
        expiry="",
        entry_price=request.entry_price,
        entry_time=datetime.now(),
        probe_quantity=1,
        probe_capital=0,
        current_price=request.current_price,
        highest_price=request.highest_price,
        lowest_price=request.lowest_price
    )
    
    result = await intelligence.analyze_momentum_status(
        position,
        request.price_history,
        request.volume_data
    )
    
    return {
        "momentum_status": result.momentum_status.value,
        "confidence": result.confidence,
        "reasoning": result.reasoning,
        "recommended_action": result.recommended_action,
        "momentum_details": result.additional_insights
    }


@router.get("/health")
async def health_check():
    """Health check for Gemini Intelligence service"""
    return {
        "status": "healthy",
        "service": "gemini-trade-intelligence",
        "model": "gemini-3-pro",
        "endpoints": [
            "/api/gemini/probe-confirmation",
            "/api/gemini/scale-decision",
            "/api/gemini/exit-analysis",
            "/api/gemini/loss-minimization",
            "/api/gemini/momentum-status"
        ]
    }
