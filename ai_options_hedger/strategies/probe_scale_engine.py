"""
╔══════════════════════════════════════════════════════════════════════════════════════╗
║            PROBE-SCALE TRADING ENGINE v1.1 - AI OPTIONS HEDGER                       ║
║    Intelligent Entry & Exit with Gemini 3 Pro Consultation                          ║
╠══════════════════════════════════════════════════════════════════════════════════════╣
║                                                                                      ║
║  ENTRY METHODOLOGY:                                                                  ║
║    1. PROBE: Enter with 10% capital, 28% stoploss (risk-adjusted)                   ║
║    2. CONFIRM: Wait for Gemini 3 Pro confirmation                                   ║
║    3. SCALE: Add 90% capital on confirmation                                        ║
║                                                                                      ║
║  EXIT METHODOLOGY:                                                                   ║
║    - Gemini 3 Pro exit consultation every 30 seconds                                ║
║    - 50-point trailing stop after 50-point profit                                   ║
║    - Loss recovery with AI-guided exit                                              ║
║                                                                                      ║
║  CRITICAL FIXES (v1.1):                                                              ║
║    - Reduced probe stoploss from 50% to 28% for better risk management             ║
║    - PCR interpretation corrected: PCR < 0.8 = BULLISH (not oversold)              ║
║    - Correct lot sizes: NIFTY=75, BANKNIFTY=35, FINNIFTY=40                         ║
║                                                                                      ║
╚══════════════════════════════════════════════════════════════════════════════════════╝
"""

import asyncio
import aiohttp
import json
import logging
import sqlite3
from datetime import datetime, timedelta
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
import os

logger = logging.getLogger(__name__)


# ============================================================================
# CONFIGURATION
# ============================================================================

@dataclass
class ProbeScaleConfig:
    """Probe-Scale trading configuration"""
    
    # Capital allocation
    probe_capital_pct: float = 10.0        # 10% for initial probe
    scale_capital_pct: float = 90.0        # 90% for scale-up
    
    # Stoploss (REDUCED for better risk management - was 50%, now 28%)
    # Reasoning: 50% stoploss too wide, risking too much per probe
    # 28% allows for normal options volatility without excessive capital at risk
    probe_stoploss_pct: float = 28.0       # 28% stoploss on premium (reduced from 50%)
    scaled_stoploss_pct: float = 22.0      # 22% after scaling (reduced from 30%)
    
    # Trailing stop
    trailing_activation_points: float = 50.0   # Activate at 50 pts profit
    trailing_distance_points: float = 50.0     # Trail 50 pts behind
    
    # Scaling criteria
    min_profit_to_scale_pct: float = 10.0      # 10% profit to consider scaling
    min_gemini_confidence: float = 85.0        # 85% Gemini confidence to scale
    max_probe_loss_pct: float = 20.0           # Abort probe at 20% loss (reduced from 25%)
    
    # Timing
    probe_timeout_seconds: int = 120           # 2 min probe timeout
    gemini_check_interval: int = 30            # Check every 30 sec
    max_holding_minutes: int = 45              # Max hold time for options
    
    # Gemini service
    gemini_service_url: str = "http://localhost:4080"


class TradePhase(Enum):
    """Trade lifecycle phases"""
    PROBE = "PROBE"
    CONFIRMING = "CONFIRMING"
    SCALING = "SCALING"
    FULL_POSITION = "FULL_POSITION"
    REDUCING = "REDUCING"
    EXITING = "EXITING"
    CLOSED = "CLOSED"


class MomentumStatus(Enum):
    """Momentum status from Gemini"""
    STRONG = "STRONG"
    MODERATE = "MODERATE"
    WEAK = "WEAK"
    EXHAUSTED = "EXHAUSTED"
    REVERSING = "REVERSING"


@dataclass
class ProbePosition:
    """Probe-Scale position tracking"""
    trade_id: str
    symbol: str
    option_type: str  # CE or PE
    strike: float
    expiry: str
    lot_size: int
    
    # Capital allocation
    allocated_capital: float = 0.0
    probe_capital: float = 0.0
    scale_capital: float = 0.0
    
    # Probe entry
    probe_entry_price: float = 0.0
    probe_entry_time: str = ""
    probe_quantity: int = 0
    probe_stoploss: float = 0.0
    
    # Scale entry
    scale_entry_price: float = 0.0
    scale_entry_time: str = ""
    scale_quantity: int = 0
    scale_stoploss: float = 0.0
    
    # Current state
    phase: str = "PROBE"
    current_price: float = 0.0
    highest_price: float = 0.0
    lowest_price: float = 999999.0
    pnl_points: float = 0.0
    pnl_percent: float = 0.0
    unrealized_pnl: float = 0.0
    
    # Trailing
    trailing_activated: bool = False
    trailing_stop: float = 0.0
    
    # Gemini tracking
    gemini_checks: int = 0
    last_gemini_decision: str = ""
    momentum_status: str = "STRONG"
    gemini_confidence: float = 0.0
    
    # Exit
    exit_price: float = 0.0
    exit_time: str = ""
    exit_reason: str = ""
    realized_pnl: float = 0.0
    
    # Meta
    entry_reason: str = ""
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())


# ============================================================================
# PROBE-SCALE ENGINE
# ============================================================================

class ProbeScaleEngine:
    """
    Probe-Scale Trading Engine for AI Options Hedger
    
    Implements the intelligent entry/exit methodology:
    - 10% probe entry with 50% wide stoploss
    - Gemini 3 Pro confirmation for scale-up
    - Continuous exit consultation
    - Loss recovery with AI guidance
    """
    
    def __init__(self, config: ProbeScaleConfig = None, db_path: str = None):
        self.config = config or ProbeScaleConfig()
        self.db_path = db_path or "database/probe_scale_trades.db"
        
        # State
        self.positions: Dict[str, ProbePosition] = {}
        self.session: Optional[aiohttp.ClientSession] = None
        
        # Initialize database
        self._init_database()
        
        logger.info("=" * 60)
        logger.info("PROBE-SCALE ENGINE INITIALIZED")
        logger.info(f"Probe: {self.config.probe_capital_pct}% | Scale: {self.config.scale_capital_pct}%")
        logger.info(f"Probe SL: {self.config.probe_stoploss_pct}% (wide)")
        logger.info(f"Trailing: {self.config.trailing_distance_points}pt after {self.config.trailing_activation_points}pt")
        logger.info("=" * 60)
    
    def _init_database(self):
        """Initialize SQLite database for position persistence"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS probe_positions (
                    trade_id TEXT PRIMARY KEY,
                    data TEXT NOT NULL,
                    created_at TEXT,
                    updated_at TEXT
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS trade_history (
                    trade_id TEXT PRIMARY KEY,
                    data TEXT NOT NULL,
                    closed_at TEXT
                )
            """)
            conn.commit()
    
    async def _ensure_session(self):
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=30)
            )
    
    async def close(self):
        if self.session and not self.session.closed:
            await self.session.close()
    
    # =========================================================================
    # PROBE ENTRY
    # =========================================================================
    
    async def enter_probe(
        self,
        symbol: str,
        option_type: str,
        strike: float,
        expiry: str,
        entry_price: float,
        lot_size: int,
        allocated_capital: float,
        entry_reason: str = "AI Signal"
    ) -> Optional[ProbePosition]:
        """
        Enter a probe position with 10% capital and 50% wide stoploss
        
        Args:
            symbol: Stock symbol
            option_type: CE or PE
            strike: Strike price
            expiry: Expiry date
            entry_price: Entry price per unit
            lot_size: Lot size
            allocated_capital: Total capital allocated for this trade
            entry_reason: Reason for entry
            
        Returns:
            ProbePosition if successful, None otherwise
        """
        import uuid
        trade_id = f"HEDGER_{uuid.uuid4().hex[:8].upper()}"
        
        # Calculate probe allocation
        probe_capital = allocated_capital * (self.config.probe_capital_pct / 100)
        position_value = entry_price * lot_size
        probe_quantity = max(1, int(probe_capital / position_value))
        actual_probe_capital = probe_quantity * position_value
        
        # Calculate 50% wide stoploss
        stoploss = entry_price * (1 - self.config.probe_stoploss_pct / 100)
        
        # Create position
        position = ProbePosition(
            trade_id=trade_id,
            symbol=symbol,
            option_type=option_type,
            strike=strike,
            expiry=expiry,
            lot_size=lot_size,
            allocated_capital=allocated_capital,
            probe_capital=actual_probe_capital,
            scale_capital=allocated_capital - actual_probe_capital,
            probe_entry_price=entry_price,
            probe_entry_time=datetime.now().isoformat(),
            probe_quantity=probe_quantity,
            probe_stoploss=stoploss,
            phase=TradePhase.PROBE.value,
            current_price=entry_price,
            highest_price=entry_price,
            lowest_price=entry_price,
            entry_reason=entry_reason
        )
        
        # Store
        self.positions[trade_id] = position
        self._save_position(position)
        
        logger.info("=" * 50)
        logger.info(f"✅ PROBE ENTERED: {symbol} {option_type} {strike}")
        logger.info(f"   Trade ID: {trade_id}")
        logger.info(f"   Entry: ₹{entry_price:.2f}")
        logger.info(f"   Quantity: {probe_quantity} lots ({probe_quantity * lot_size} shares)")
        logger.info(f"   Capital: ₹{actual_probe_capital:,.2f} (10%)")
        logger.info(f"   Stoploss: ₹{stoploss:.2f} (50% wide)")
        logger.info(f"   Remaining for scale: ₹{position.scale_capital:,.2f}")
        logger.info("=" * 50)
        
        return position
    
    # =========================================================================
    # PRICE UPDATE & MONITORING
    # =========================================================================
    
    async def update_price(self, trade_id: str, current_price: float) -> Dict[str, Any]:
        """
        Update position with current price and check all conditions
        
        Returns action to take: HOLD, SCALE, EXIT, PARTIAL_EXIT
        """
        position = self.positions.get(trade_id)
        if not position:
            return {'action': 'NOT_FOUND'}
        
        # Update prices
        position.current_price = current_price
        position.highest_price = max(position.highest_price, current_price)
        position.lowest_price = min(position.lowest_price, current_price)
        
        # Calculate P&L
        if position.phase == TradePhase.FULL_POSITION.value and position.scale_quantity > 0:
            total_qty = position.probe_quantity + position.scale_quantity
            avg_entry = (position.probe_entry_price * position.probe_quantity + 
                        position.scale_entry_price * position.scale_quantity) / total_qty
            position.pnl_points = current_price - avg_entry
            position.pnl_percent = (position.pnl_points / avg_entry) * 100
            position.unrealized_pnl = position.pnl_points * total_qty * position.lot_size
        else:
            position.pnl_points = current_price - position.probe_entry_price
            position.pnl_percent = (position.pnl_points / position.probe_entry_price) * 100
            position.unrealized_pnl = position.pnl_points * position.probe_quantity * position.lot_size
        
        # Check hard stoploss first (no AI needed)
        active_sl = position.scale_stoploss if position.phase == TradePhase.FULL_POSITION.value else position.probe_stoploss
        if current_price <= active_sl:
            return await self._prepare_exit(position, "STOPLOSS_HIT")
        
        # Check trailing stop
        if position.trailing_activated and current_price <= position.trailing_stop:
            return await self._prepare_exit(position, "TRAILING_STOP_HIT")
        
        # Update trailing stop
        if position.pnl_points >= self.config.trailing_activation_points:
            if not position.trailing_activated:
                position.trailing_activated = True
                logger.info(f"📈 Trailing activated for {trade_id}")
            
            new_trail = current_price - self.config.trailing_distance_points
            if new_trail > position.trailing_stop:
                position.trailing_stop = new_trail
        
        # Phase-specific logic
        if position.phase == TradePhase.PROBE.value:
            return await self._handle_probe_phase(position)
        elif position.phase == TradePhase.FULL_POSITION.value:
            return await self._handle_full_position(position)
        
        self._save_position(position)
        return {'action': 'HOLD', 'position': asdict(position)}
    
    async def _handle_probe_phase(self, position: ProbePosition) -> Dict[str, Any]:
        """Handle probe phase - check for scale or abort"""
        
        # Check if profitable enough
        if position.pnl_percent >= self.config.min_profit_to_scale_pct:
            # Consult Gemini for confirmation
            analysis = await self._consult_gemini_scale(position)
            position.gemini_checks += 1
            position.last_gemini_decision = analysis.get('decision', 'HOLD')
            position.gemini_confidence = analysis.get('confidence', 0)
            position.momentum_status = analysis.get('momentum_status', 'MODERATE')
            
            if analysis.get('decision') == 'SCALE_UP' and \
               analysis.get('confidence', 0) >= self.config.min_gemini_confidence:
                return {
                    'action': 'SCALE',
                    'scale_percent': analysis.get('scale_percent', 75),
                    'reasoning': analysis.get('reasoning', ''),
                    'position': asdict(position)
                }
        
        # Check if losing too much
        elif position.pnl_percent <= -self.config.max_probe_loss_pct:
            logger.warning(f"⚠️ Probe {position.trade_id} losing {position.pnl_percent:.1f}%")
            return await self._prepare_exit(position, f"PROBE_ABORT: Loss {position.pnl_percent:.1f}%")
        
        # Check timeout
        entry_time = datetime.fromisoformat(position.probe_entry_time)
        elapsed = (datetime.now() - entry_time).total_seconds()
        
        if elapsed > self.config.probe_timeout_seconds:
            if position.pnl_percent < self.config.min_profit_to_scale_pct:
                logger.info(f"⏰ Probe {position.trade_id} timeout without confirmation")
                return await self._prepare_exit(position, "PROBE_TIMEOUT")
        
        self._save_position(position)
        return {'action': 'HOLD', 'position': asdict(position)}
    
    async def _handle_full_position(self, position: ProbePosition) -> Dict[str, Any]:
        """Handle full position - check exit conditions"""
        
        # Consult Gemini for exit
        analysis = await self._consult_gemini_exit(position)
        position.gemini_checks += 1
        position.last_gemini_decision = analysis.get('decision', 'HOLD')
        position.momentum_status = analysis.get('momentum_status', 'MODERATE')
        
        if analysis.get('decision') == 'FULL_EXIT':
            return await self._prepare_exit(position, f"GEMINI_EXIT: {analysis.get('reasoning', '')[:30]}")
        
        elif analysis.get('decision') == 'PARTIAL_EXIT':
            return {
                'action': 'PARTIAL_EXIT',
                'exit_percent': analysis.get('exit_percent', 50),
                'reasoning': analysis.get('reasoning', ''),
                'position': asdict(position)
            }
        
        # Check momentum exhaustion
        if analysis.get('momentum_status') in ['EXHAUSTED', 'REVERSING']:
            logger.warning(f"⚠️ Momentum {analysis.get('momentum_status')} for {position.trade_id}")
            return await self._prepare_exit(position, f"MOMENTUM_{analysis.get('momentum_status')}")
        
        # Check max holding time
        entry_time = datetime.fromisoformat(position.probe_entry_time)
        elapsed_min = (datetime.now() - entry_time).total_seconds() / 60
        
        if elapsed_min > self.config.max_holding_minutes:
            return await self._prepare_exit(position, "MAX_HOLD_TIME")
        
        self._save_position(position)
        return {'action': 'HOLD', 'position': asdict(position)}
    
    # =========================================================================
    # SCALE UP
    # =========================================================================
    
    async def scale_up(self, trade_id: str, scale_percent: float = 90.0) -> Dict[str, Any]:
        """Scale up position by adding remaining capital"""
        
        position = self.positions.get(trade_id)
        if not position:
            return {'success': False, 'error': 'Position not found'}
        
        if position.phase != TradePhase.PROBE.value:
            return {'success': False, 'error': 'Position already scaled'}
        
        # Calculate scale quantity
        scale_capital = position.scale_capital * (scale_percent / 100)
        position_value = position.current_price * position.lot_size
        scale_quantity = max(1, int(scale_capital / position_value))
        
        # Calculate new stoploss (tighter after scaling)
        total_qty = position.probe_quantity + scale_quantity
        avg_entry = (position.probe_entry_price * position.probe_quantity + 
                    position.current_price * scale_quantity) / total_qty
        scale_stoploss = avg_entry * (1 - self.config.scaled_stoploss_pct / 100)
        
        # Update position
        position.scale_entry_price = position.current_price
        position.scale_entry_time = datetime.now().isoformat()
        position.scale_quantity = scale_quantity
        position.scale_stoploss = scale_stoploss
        position.phase = TradePhase.FULL_POSITION.value
        
        self._save_position(position)
        
        logger.info("=" * 50)
        logger.info(f"✅ SCALED UP: {position.symbol} {position.option_type}")
        logger.info(f"   Added: {scale_quantity} lots @ ₹{position.current_price:.2f}")
        logger.info(f"   Total: {total_qty} lots")
        logger.info(f"   Avg Entry: ₹{avg_entry:.2f}")
        logger.info(f"   New SL: ₹{scale_stoploss:.2f} (30%)")
        logger.info("=" * 50)
        
        return {
            'success': True,
            'scale_quantity': scale_quantity,
            'total_quantity': total_qty,
            'avg_entry': avg_entry,
            'new_stoploss': scale_stoploss,
            'position': asdict(position)
        }
    
    # =========================================================================
    # EXIT
    # =========================================================================
    
    async def _prepare_exit(self, position: ProbePosition, reason: str) -> Dict[str, Any]:
        """Prepare exit action"""
        position.phase = TradePhase.EXITING.value
        self._save_position(position)
        
        return {
            'action': 'EXIT',
            'reason': reason,
            'position': asdict(position)
        }
    
    async def execute_exit(self, trade_id: str, exit_price: float, reason: str = "Manual") -> Dict[str, Any]:
        """Execute full exit"""
        
        position = self.positions.get(trade_id)
        if not position:
            return {'success': False, 'error': 'Position not found'}
        
        # Calculate P&L
        if position.scale_quantity > 0:
            total_qty = position.probe_quantity + position.scale_quantity
            avg_entry = (position.probe_entry_price * position.probe_quantity + 
                        position.scale_entry_price * position.scale_quantity) / total_qty
        else:
            total_qty = position.probe_quantity
            avg_entry = position.probe_entry_price
        
        pnl = (exit_price - avg_entry) * total_qty * position.lot_size
        
        # Update position
        position.exit_price = exit_price
        position.exit_time = datetime.now().isoformat()
        position.exit_reason = reason
        position.realized_pnl = pnl
        position.phase = TradePhase.CLOSED.value
        
        # Move to history
        self._save_to_history(position)
        del self.positions[trade_id]
        
        logger.info("=" * 50)
        logger.info(f"✅ EXITED: {position.symbol} {position.option_type}")
        logger.info(f"   Reason: {reason}")
        logger.info(f"   Exit Price: ₹{exit_price:.2f}")
        logger.info(f"   P&L: ₹{pnl:+,.2f}")
        logger.info("=" * 50)
        
        return {
            'success': True,
            'realized_pnl': pnl,
            'exit_price': exit_price,
            'position': asdict(position)
        }
    
    # =========================================================================
    # GEMINI CONSULTATIONS
    # =========================================================================
    
    async def _consult_gemini_scale(self, position: ProbePosition) -> Dict[str, Any]:
        """Consult Gemini 3 Pro for scale decision"""
        await self._ensure_session()
        
        try:
            payload = {
                'trade_id': position.trade_id,
                'symbol': position.symbol,
                'option_type': position.option_type,
                'strike': position.strike,
                'entry_price': position.probe_entry_price,
                'current_price': position.current_price,
                'highest_price': position.highest_price,
                'pnl_percent': position.pnl_percent,
                'probe_quantity': position.probe_quantity,
                'remaining_capital': position.scale_capital,
                'time_in_trade_seconds': (datetime.now() - datetime.fromisoformat(position.probe_entry_time)).total_seconds()
            }
            
            async with self.session.post(
                f"{self.config.gemini_service_url}/api/trade-intel/scale-decision",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=15)
            ) as resp:
                if resp.status == 200:
                    return await resp.json()
                    
        except Exception as e:
            logger.error(f"Gemini scale consultation error: {e}")
        
        return {'decision': 'HOLD', 'confidence': 50, 'scale_percent': 0}
    
    async def _consult_gemini_exit(self, position: ProbePosition) -> Dict[str, Any]:
        """Consult Gemini 3 Pro for exit decision"""
        await self._ensure_session()
        
        try:
            total_qty = position.probe_quantity + position.scale_quantity
            
            payload = {
                'trade_id': position.trade_id,
                'symbol': position.symbol,
                'option_type': position.option_type,
                'strike': position.strike,
                'entry_price': position.probe_entry_price,
                'current_price': position.current_price,
                'highest_price': position.highest_price,
                'lowest_price': position.lowest_price,
                'pnl_percent': position.pnl_percent,
                'pnl_points': position.pnl_points,
                'total_quantity': total_qty,
                'stoploss': position.scale_stoploss,
                'trailing_stop': position.trailing_stop,
                'trailing_activated': position.trailing_activated,
                'time_in_trade_minutes': (datetime.now() - datetime.fromisoformat(position.probe_entry_time)).total_seconds() / 60,
                'gemini_checks': position.gemini_checks
            }
            
            async with self.session.post(
                f"{self.config.gemini_service_url}/api/trade-intel/exit-consultation",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=15)
            ) as resp:
                if resp.status == 200:
                    return await resp.json()
                    
        except Exception as e:
            logger.error(f"Gemini exit consultation error: {e}")
        
        return {'decision': 'HOLD', 'confidence': 50, 'momentum_status': 'MODERATE'}
    
    # =========================================================================
    # DATABASE
    # =========================================================================
    
    def _save_position(self, position: ProbePosition):
        """Save position to database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO probe_positions (trade_id, data, created_at, updated_at)
                VALUES (?, ?, ?, ?)
            """, (position.trade_id, json.dumps(asdict(position)), position.created_at, datetime.now().isoformat()))
            conn.commit()
    
    def _save_to_history(self, position: ProbePosition):
        """Move closed position to history"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO trade_history (trade_id, data, closed_at)
                VALUES (?, ?, ?)
            """, (position.trade_id, json.dumps(asdict(position)), datetime.now().isoformat()))
            conn.execute("DELETE FROM probe_positions WHERE trade_id = ?", (position.trade_id,))
            conn.commit()
    
    def get_position(self, trade_id: str) -> Optional[Dict]:
        """Get position by trade_id"""
        pos = self.positions.get(trade_id)
        return asdict(pos) if pos else None
    
    def get_all_positions(self) -> List[Dict]:
        """Get all active positions"""
        return [asdict(p) for p in self.positions.values()]
    
    def get_history(self, limit: int = 50) -> List[Dict]:
        """Get trade history"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT data FROM trade_history ORDER BY closed_at DESC LIMIT ?",
                (limit,)
            )
            return [json.loads(row[0]) for row in cursor.fetchall()]
