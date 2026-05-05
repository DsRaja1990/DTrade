"""
╔══════════════════════════════════════════════════════════════════════════════════════╗
║                     MOMENTUM EXIT MONITOR v1.0                                       ║
║          Real-Time Momentum Exhaustion Detection with Gemini Pro 2.0                 ║
║══════════════════════════════════════════════════════════════════════════════════════║
║                                                                                      ║
║  PURPOSE:                                                                            ║
║  ─────────                                                                           ║
║  - Monitor active trades for momentum exhaustion signals                             ║
║  - Use Gemini Pro 2.0 for intelligent exit decisions                                 ║
║  - No trailing stop loss - capture complete momentum                                 ║
║  - Wide initial stop loss for volatility protection                                  ║
║                                                                                      ║
║  EXIT CONDITIONS:                                                                    ║
║  ─────────────────                                                                   ║
║  1. Momentum Exhaustion: AI detects momentum slowing/reversing                       ║
║  2. Target Achievement: T1 (5%) or T2 (8%) hit                                       ║
║  3. Wide Stop Loss: 5% adverse move (no trailing)                                    ║
║  4. Time-Based: Exit before expiry if momentum unclear                               ║
║  5. AI Override: Gemini Pro signals immediate exit                                   ║
║                                                                                      ║
║  AI CONSULTATION:                                                                    ║
║  ─────────────────                                                                   ║
║  Every 30 seconds, consult Gemini Pro 2.0:                                           ║
║  - "Should we exit or continue holding?"                                             ║
║  - Analyze momentum velocity, volume, price action                                   ║
║  - Consider market context and sector movement                                       ║
╚══════════════════════════════════════════════════════════════════════════════════════╝
"""

import asyncio
import aiohttp
import logging
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Callable
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__ + '.momentum_exit_monitor')

# Gemini Service URL
GEMINI_SERVICE_URL = "http://localhost:4080"


class ExitReason(Enum):
    """Reasons for exiting a trade"""
    MOMENTUM_EXHAUSTION = "momentum_exhaustion"
    TARGET_1_HIT = "target_1_hit"
    TARGET_2_HIT = "target_2_hit"
    STOP_LOSS_HIT = "stop_loss_hit"
    AI_EXIT_SIGNAL = "ai_exit_signal"
    TIME_BASED = "time_based"
    MARKET_REVERSAL = "market_reversal"
    MANUAL = "manual"


class ExitDecision(Enum):
    """AI exit decision"""
    HOLD = "hold"                    # Continue holding
    PARTIAL_EXIT = "partial_exit"    # Exit 50% position
    FULL_EXIT = "full_exit"          # Exit entire position
    BOOK_PROFIT = "book_profit"      # Book profits now
    EMERGENCY_EXIT = "emergency_exit"  # Immediate exit


@dataclass
class ActivePosition:
    """Active position being monitored"""
    position_id: str
    symbol: str
    direction: str  # CE or PE
    strike: float
    lots: int
    entry_price: float  # Option premium at entry
    entry_time: datetime
    
    # Price levels
    stop_loss: float  # Underlying price SL
    target_1: float
    target_2: float
    
    # Current state
    current_underlying_price: float = 0.0
    current_option_price: float = 0.0
    unrealized_pnl: float = 0.0
    max_profit_seen: float = 0.0
    
    # Momentum tracking
    momentum_velocity: float = 0.0
    momentum_acceleration: float = 0.0
    volume_trend: str = "stable"  # increasing, stable, decreasing
    
    # AI tracking
    last_ai_check: datetime = None
    ai_confidence_trend: List[float] = field(default_factory=list)
    ai_recommendation: str = "HOLD"
    
    # Exit info
    is_closed: bool = False
    exit_price: float = 0.0
    exit_time: datetime = None
    exit_reason: ExitReason = None
    realized_pnl: float = 0.0
    
    @property
    def holding_duration_minutes(self) -> float:
        """How long position has been held"""
        end_time = self.exit_time or datetime.now()
        return (end_time - self.entry_time).total_seconds() / 60
    
    @property
    def pnl_pct(self) -> float:
        """Current P&L percentage"""
        if self.entry_price > 0:
            return ((self.current_option_price - self.entry_price) / self.entry_price) * 100
        return 0
    
    @property
    def is_in_profit(self) -> bool:
        return self.current_option_price > self.entry_price
    
    @property
    def is_momentum_fading(self) -> bool:
        """Detect if momentum is fading"""
        return self.momentum_acceleration < -0.01 and self.volume_trend == "decreasing"


@dataclass
class ExitSignal:
    """Exit signal from the monitor"""
    position_id: str
    decision: ExitDecision
    reason: ExitReason
    confidence: float  # 0-100
    
    # Details
    current_pnl_pct: float
    recommended_action: str
    ai_thesis: str
    
    # Urgency
    urgency: str  # "immediate", "within_1min", "flexible"
    
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


class MomentumExitMonitor:
    """
    Monitors active positions and generates exit signals using Gemini Pro 2.0
    
    Features:
    - Real-time momentum tracking
    - AI-powered exit decisions
    - No trailing stop loss (capture full momentum)
    - Wide initial stop loss
    - Intelligent profit booking
    """
    
    def __init__(self, gemini_url: str = GEMINI_SERVICE_URL):
        self.gemini_url = gemini_url
        self.session = None
        self.is_available = False
        
        # Active positions
        self.positions: Dict[str, ActivePosition] = {}
        
        # Configuration
        self.ai_check_interval = 30  # seconds
        self.price_check_interval = 5  # seconds
        
        # Callbacks
        self.on_exit_signal: Optional[Callable[[ExitSignal], None]] = None
        
        # Stats
        self.total_exits = 0
        self.profitable_exits = 0
        
        logger.info("📊 Momentum Exit Monitor initialized")
    
    async def initialize(self) -> bool:
        """Initialize monitor"""
        try:
            self.session = aiohttp.ClientSession()
            
            async with self.session.get(f"{self.gemini_url}/health") as resp:
                if resp.status == 200:
                    self.is_available = True
                    logger.info("✅ Gemini Pro 2.0 connected for exit monitoring")
                    return True
                    
        except Exception as e:
            logger.error(f"Failed to initialize exit monitor: {e}")
        
        return False
    
    async def close(self):
        """Close session"""
        if self.session and not self.session.closed:
            await self.session.close()
    
    def add_position(self, position: ActivePosition):
        """Add a position to monitor"""
        self.positions[position.position_id] = position
        logger.info(f"📍 Monitoring position: {position.symbol} {position.direction} {position.strike}")
    
    def remove_position(self, position_id: str):
        """Remove a position from monitoring"""
        if position_id in self.positions:
            del self.positions[position_id]
    
    # =========================================================================
    # AI CONSULTATION
    # =========================================================================
    
    async def consult_ai_for_exit(
        self,
        position: ActivePosition
    ) -> Tuple[ExitDecision, str, float]:
        """
        Consult Gemini Pro 2.0 for exit decision
        
        Returns: (decision, thesis, confidence)
        """
        if not self.is_available:
            return ExitDecision.HOLD, "AI unavailable", 50.0
        
        try:
            # Build the prompt for AI
            prompt_data = {
                "symbol": position.symbol,
                "direction": position.direction,
                "entry_price": position.entry_price,
                "current_price": position.current_underlying_price,
                "option_price": position.current_option_price,
                "pnl_pct": position.pnl_pct,
                "holding_minutes": position.holding_duration_minutes,
                "momentum_velocity": position.momentum_velocity,
                "momentum_acceleration": position.momentum_acceleration,
                "volume_trend": position.volume_trend,
                "max_profit_seen": position.max_profit_seen,
                "target_1": position.target_1,
                "target_2": position.target_2,
                "stop_loss": position.stop_loss
            }
            
            # Get AI recommendation
            async with self.session.post(
                f"{self.gemini_url}/api/momentum-exit",
                json=prompt_data,
                timeout=10
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    
                    decision_str = data.get("decision", "HOLD").upper()
                    
                    if decision_str == "FULL_EXIT":
                        decision = ExitDecision.FULL_EXIT
                    elif decision_str == "PARTIAL_EXIT":
                        decision = ExitDecision.PARTIAL_EXIT
                    elif decision_str == "BOOK_PROFIT":
                        decision = ExitDecision.BOOK_PROFIT
                    elif decision_str == "EMERGENCY_EXIT":
                        decision = ExitDecision.EMERGENCY_EXIT
                    else:
                        decision = ExitDecision.HOLD
                    
                    thesis = data.get("thesis", "Continue monitoring")
                    confidence = float(data.get("confidence", 50))
                    
                    return decision, thesis, confidence
                    
        except Exception as e:
            logger.debug(f"AI exit consultation error: {e}")
        
        # Fallback: Use rule-based decision
        return self._fallback_exit_decision(position)
    
    def _fallback_exit_decision(
        self,
        position: ActivePosition
    ) -> Tuple[ExitDecision, str, float]:
        """
        Rule-based fallback exit decision when AI unavailable
        """
        decision = ExitDecision.HOLD
        thesis = "Continue holding"
        confidence = 60.0
        
        # Check P&L thresholds
        if position.pnl_pct >= 80:  # 80%+ profit on options
            decision = ExitDecision.FULL_EXIT
            thesis = "Exceptional profit - book gains"
            confidence = 90.0
        elif position.pnl_pct >= 50:  # 50%+ profit
            if position.is_momentum_fading:
                decision = ExitDecision.BOOK_PROFIT
                thesis = "Strong profit + momentum fading"
                confidence = 85.0
            else:
                decision = ExitDecision.PARTIAL_EXIT
                thesis = "Book 50% profits, let rest ride"
                confidence = 75.0
        elif position.pnl_pct <= -40:  # 40%+ loss on options
            decision = ExitDecision.FULL_EXIT
            thesis = "Loss limit reached"
            confidence = 90.0
        elif position.is_momentum_fading and position.pnl_pct > 0:
            decision = ExitDecision.BOOK_PROFIT
            thesis = "Momentum exhaustion in profit"
            confidence = 70.0
        
        return decision, thesis, confidence
    
    # =========================================================================
    # PRICE MONITORING
    # =========================================================================
    
    async def update_position_prices(
        self,
        position: ActivePosition,
        underlying_price: float,
        option_price: float,
        volume: int = 0
    ):
        """Update position with latest prices"""
        prev_price = position.current_underlying_price
        
        position.current_underlying_price = underlying_price
        position.current_option_price = option_price
        
        # Update P&L
        position.unrealized_pnl = (
            (option_price - position.entry_price) * 
            position.lots * 
            self._get_lot_size(position.symbol)
        )
        
        # Track max profit
        if position.unrealized_pnl > position.max_profit_seen:
            position.max_profit_seen = position.unrealized_pnl
        
        # Calculate momentum velocity (price change rate)
        if prev_price > 0:
            price_change = (underlying_price - prev_price) / prev_price
            prev_velocity = position.momentum_velocity
            position.momentum_velocity = price_change * 100
            position.momentum_acceleration = position.momentum_velocity - prev_velocity
        
        # Volume trend detection would require historical data
        # For now, simulate based on velocity
        if abs(position.momentum_acceleration) > 0.01:
            position.volume_trend = "increasing" if position.momentum_acceleration > 0 else "decreasing"
    
    def _get_lot_size(self, symbol: str) -> int:
        """Get lot size for symbol"""
        from elite_options_scanner import FO_STOCKS
        return FO_STOCKS.get(symbol, {}).get("lot_size", 1)
    
    # =========================================================================
    # EXIT CONDITION CHECKS
    # =========================================================================
    
    async def check_exit_conditions(
        self,
        position: ActivePosition
    ) -> Optional[ExitSignal]:
        """
        Check all exit conditions for a position
        
        Returns: ExitSignal if exit warranted, None otherwise
        """
        price = position.current_underlying_price
        
        # Check stop loss (wide - 5%)
        if position.direction == "CE":
            if price <= position.stop_loss:
                return ExitSignal(
                    position_id=position.position_id,
                    decision=ExitDecision.FULL_EXIT,
                    reason=ExitReason.STOP_LOSS_HIT,
                    confidence=100,
                    current_pnl_pct=position.pnl_pct,
                    recommended_action="EXIT IMMEDIATELY",
                    ai_thesis="Stop loss level breached",
                    urgency="immediate"
                )
        else:  # PE
            if price >= position.stop_loss:
                return ExitSignal(
                    position_id=position.position_id,
                    decision=ExitDecision.FULL_EXIT,
                    reason=ExitReason.STOP_LOSS_HIT,
                    confidence=100,
                    current_pnl_pct=position.pnl_pct,
                    recommended_action="EXIT IMMEDIATELY",
                    ai_thesis="Stop loss level breached",
                    urgency="immediate"
                )
        
        # Check Target 2 (8%)
        if position.direction == "CE":
            if price >= position.target_2:
                return ExitSignal(
                    position_id=position.position_id,
                    decision=ExitDecision.FULL_EXIT,
                    reason=ExitReason.TARGET_2_HIT,
                    confidence=100,
                    current_pnl_pct=position.pnl_pct,
                    recommended_action="BOOK FULL PROFIT",
                    ai_thesis="Target 2 achieved - maximum profit captured",
                    urgency="within_1min"
                )
        else:
            if price <= position.target_2:
                return ExitSignal(
                    position_id=position.position_id,
                    decision=ExitDecision.FULL_EXIT,
                    reason=ExitReason.TARGET_2_HIT,
                    confidence=100,
                    current_pnl_pct=position.pnl_pct,
                    recommended_action="BOOK FULL PROFIT",
                    ai_thesis="Target 2 achieved - maximum profit captured",
                    urgency="within_1min"
                )
        
        # Check Target 1 (5%) - Consult AI for partial exit
        if position.direction == "CE":
            target_1_hit = price >= position.target_1
        else:
            target_1_hit = price <= position.target_1
        
        if target_1_hit and position.holding_duration_minutes > 5:
            # Consult AI for decision
            decision, thesis, confidence = await self.consult_ai_for_exit(position)
            
            if decision in [ExitDecision.FULL_EXIT, ExitDecision.BOOK_PROFIT]:
                return ExitSignal(
                    position_id=position.position_id,
                    decision=decision,
                    reason=ExitReason.TARGET_1_HIT,
                    confidence=confidence,
                    current_pnl_pct=position.pnl_pct,
                    recommended_action="BOOK PROFIT AT T1",
                    ai_thesis=thesis,
                    urgency="within_1min"
                )
            elif decision == ExitDecision.PARTIAL_EXIT:
                return ExitSignal(
                    position_id=position.position_id,
                    decision=decision,
                    reason=ExitReason.TARGET_1_HIT,
                    confidence=confidence,
                    current_pnl_pct=position.pnl_pct,
                    recommended_action="BOOK 50%, RIDE REST TO T2",
                    ai_thesis=thesis,
                    urgency="flexible"
                )
        
        # Periodic AI consultation for momentum exhaustion
        now = datetime.now()
        if position.last_ai_check is None or \
           (now - position.last_ai_check).total_seconds() > self.ai_check_interval:
            
            position.last_ai_check = now
            decision, thesis, confidence = await self.consult_ai_for_exit(position)
            
            # Track AI confidence trend
            position.ai_confidence_trend.append(confidence)
            if len(position.ai_confidence_trend) > 10:
                position.ai_confidence_trend = position.ai_confidence_trend[-10:]
            
            if decision in [ExitDecision.FULL_EXIT, ExitDecision.EMERGENCY_EXIT]:
                return ExitSignal(
                    position_id=position.position_id,
                    decision=decision,
                    reason=ExitReason.MOMENTUM_EXHAUSTION if decision == ExitDecision.FULL_EXIT else ExitReason.AI_EXIT_SIGNAL,
                    confidence=confidence,
                    current_pnl_pct=position.pnl_pct,
                    recommended_action="AI SIGNALS EXIT",
                    ai_thesis=thesis,
                    urgency="immediate" if decision == ExitDecision.EMERGENCY_EXIT else "within_1min"
                )
            elif decision == ExitDecision.BOOK_PROFIT and position.pnl_pct > 20:
                return ExitSignal(
                    position_id=position.position_id,
                    decision=decision,
                    reason=ExitReason.MOMENTUM_EXHAUSTION,
                    confidence=confidence,
                    current_pnl_pct=position.pnl_pct,
                    recommended_action="BOOK PROFIT - MOMENTUM SLOWING",
                    ai_thesis=thesis,
                    urgency="flexible"
                )
        
        return None
    
    # =========================================================================
    # MONITORING LOOP
    # =========================================================================
    
    async def monitor_all_positions(
        self,
        price_fetcher: Callable[[str], Tuple[float, float]]
    ):
        """
        Main monitoring loop for all active positions
        
        Args:
            price_fetcher: Function to get (underlying_price, option_price) for symbol
        """
        logger.info("🔄 Starting position monitoring loop...")
        
        while True:
            try:
                for position_id, position in list(self.positions.items()):
                    if position.is_closed:
                        continue
                    
                    try:
                        # Fetch latest prices
                        underlying_price, option_price = await price_fetcher(position.symbol)
                        
                        # Update position
                        await self.update_position_prices(
                            position, underlying_price, option_price
                        )
                        
                        # Check exit conditions
                        exit_signal = await self.check_exit_conditions(position)
                        
                        if exit_signal:
                            logger.info(
                                f"🚨 EXIT SIGNAL: {position.symbol} - {exit_signal.decision.value} "
                                f"({exit_signal.reason.value})"
                            )
                            
                            # Call exit callback
                            if self.on_exit_signal:
                                await self.on_exit_signal(exit_signal)
                            
                            # Mark position for exit if full exit
                            if exit_signal.decision in [
                                ExitDecision.FULL_EXIT, 
                                ExitDecision.EMERGENCY_EXIT
                            ]:
                                position.exit_reason = exit_signal.reason
                                position.exit_time = datetime.now()
                                position.exit_price = option_price
                                position.realized_pnl = position.unrealized_pnl
                                position.is_closed = True
                                
                                self.total_exits += 1
                                if position.realized_pnl > 0:
                                    self.profitable_exits += 1
                                
                    except Exception as e:
                        logger.error(f"Error monitoring {position.symbol}: {e}")
                
                # Wait before next check
                await asyncio.sleep(self.price_check_interval)
                
            except asyncio.CancelledError:
                logger.info("Monitoring loop cancelled")
                break
            except Exception as e:
                logger.error(f"Monitoring loop error: {e}")
                await asyncio.sleep(1)
    
    # =========================================================================
    # STATS
    # =========================================================================
    
    def get_stats(self) -> Dict:
        """Get monitoring statistics"""
        active = len([p for p in self.positions.values() if not p.is_closed])
        closed = len([p for p in self.positions.values() if p.is_closed])
        
        win_rate = (
            (self.profitable_exits / self.total_exits * 100) 
            if self.total_exits > 0 else 0
        )
        
        return {
            "active_positions": active,
            "closed_positions": closed,
            "total_exits": self.total_exits,
            "profitable_exits": self.profitable_exits,
            "win_rate": win_rate,
            "ai_available": self.is_available
        }


# ============================================================================
# AI EXIT ENDPOINT (Add to Gemini Trade Service)
# ============================================================================

MOMENTUM_EXIT_PROMPT = """
You are a momentum trading AI assistant. Analyze this active trade and decide whether to EXIT or HOLD.

POSITION DETAILS:
- Symbol: {symbol}
- Direction: {direction} (CE=Bullish, PE=Bearish)
- Entry Price: ₹{entry_price}
- Current Price: ₹{current_price}
- Option P&L: {pnl_pct:.1f}%
- Holding Time: {holding_minutes:.0f} minutes

MOMENTUM METRICS:
- Momentum Velocity: {momentum_velocity:.3f}
- Momentum Acceleration: {momentum_acceleration:.3f}
- Volume Trend: {volume_trend}
- Max Profit Seen: ₹{max_profit_seen:.0f}

PRICE LEVELS:
- Target 1: ₹{target_1}
- Target 2: ₹{target_2}
- Stop Loss: ₹{stop_loss}

DECISION CRITERIA:
1. If momentum is exhausting (velocity decreasing, acceleration negative), EXIT
2. If price is stalling after strong move, BOOK_PROFIT
3. If strong momentum continues, HOLD
4. If reversal signs appear, EMERGENCY_EXIT

Respond with JSON:
{{
    "decision": "HOLD" | "PARTIAL_EXIT" | "FULL_EXIT" | "BOOK_PROFIT" | "EMERGENCY_EXIT",
    "confidence": <0-100>,
    "thesis": "<brief explanation>",
    "momentum_status": "building" | "peak" | "exhausting" | "reversing"
}}
"""


# ============================================================================
# STANDALONE TEST
# ============================================================================

async def test_exit_monitor():
    """Test the exit monitor"""
    monitor = MomentumExitMonitor()
    await monitor.initialize()
    
    # Create test position
    position = ActivePosition(
        position_id="TEST001",
        symbol="RELIANCE",
        direction="CE",
        strike=2950,
        lots=5,
        entry_price=75,
        entry_time=datetime.now() - timedelta(minutes=15),
        stop_loss=2800,
        target_1=3100,
        target_2=3200,
        current_underlying_price=3050,
        current_option_price=95
    )
    
    monitor.add_position(position)
    
    # Check exit conditions
    await monitor.update_position_prices(position, 3050, 95)
    exit_signal = await monitor.check_exit_conditions(position)
    
    if exit_signal:
        print(f"Exit Signal: {exit_signal.decision.value}")
        print(f"Reason: {exit_signal.reason.value}")
        print(f"Thesis: {exit_signal.ai_thesis}")
    else:
        print("No exit signal - continue holding")
    
    print(f"\nStats: {monitor.get_stats()}")
    
    await monitor.close()


if __name__ == "__main__":
    asyncio.run(test_exit_monitor())
