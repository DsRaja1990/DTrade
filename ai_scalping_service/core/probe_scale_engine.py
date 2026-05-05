"""
╔══════════════════════════════════════════════════════════════════════════════════════╗
║            PROBE-SCALE SCALPING ENGINE v1.0 - AI SCALPING SERVICE                    ║
║    Intelligent Entry & Exit with Gemini 3 Pro Consultation                          ║
╠══════════════════════════════════════════════════════════════════════════════════════╣
║                                                                                      ║
║  SERVICE: AI Scalping Service (Index Options - NIFTY, BANKNIFTY, SENSEX, BANKEX)   ║
║  PORT: 4002                                                                         ║
║                                                                                      ║
║  ENTRY METHODOLOGY:                                                                  ║
║    1. PROBE: Enter with 10% capital, 50% wide stoploss                              ║
║    2. CONFIRM: Wait for Gemini 3 Pro confirmation                                   ║
║    3. SCALE: Add 90% capital on confirmation                                        ║
║                                                                                      ║
║  EXIT METHODOLOGY:                                                                   ║
║    - Gemini 3 Pro exit consultation every 30 seconds                                ║
║    - 50-point trailing stop after 50-point profit                                   ║
║    - Loss recovery with AI-guided exit                                              ║
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
from typing import Dict, List, Optional, Any
from enum import Enum
import os

logger = logging.getLogger(__name__)


# ============================================================================
# CONFIGURATION - SCALPING SPECIFIC
# ============================================================================

@dataclass 
class ScalpingProbeConfig:
    """Scalping-specific probe-scale configuration"""
    
    # Capital allocation
    probe_capital_pct: float = 10.0        # 10% for initial probe
    scale_capital_pct: float = 90.0        # 90% for scale-up
    
    # Stoploss (WIDE as requested - 50% of premium)
    probe_stoploss_pct: float = 50.0       # 50% wide stoploss on premium
    scaled_stoploss_pct: float = 30.0      # 30% after scaling
    
    # Trailing stop (in points for index options)
    trailing_activation_points: float = 50.0   # Activate at 50 pts profit
    trailing_distance_points: float = 50.0     # Trail 50 pts behind
    
    # Scaling criteria
    min_profit_to_scale_pct: float = 10.0      # 10% profit to consider scaling
    min_gemini_confidence: float = 85.0        # 85% Gemini confidence to scale
    max_probe_loss_pct: float = 25.0           # Abort probe at 25% loss
    
    # Timing (faster for scalping)
    probe_timeout_seconds: int = 90            # 1.5 min probe timeout
    gemini_check_interval: int = 30            # Check every 30 sec
    max_holding_minutes: int = 30              # Max 30 min for scalping
    
    # Index lot sizes
    lot_sizes: Dict[str, int] = field(default_factory=lambda: {
        "NIFTY": 75,
        "BANKNIFTY": 35,
        "SENSEX": 20,
        "BANKEX": 30
    })
    
    # Gemini service
    gemini_service_url: str = "http://localhost:4080"
    
    # Database
    db_path: str = "database/scalping_probe_trades.db"


class ScalpingPhase(Enum):
    """Scalping trade phases"""
    PROBE = "PROBE"
    CONFIRMING = "CONFIRMING"
    SCALING = "SCALING"  
    FULL_POSITION = "FULL_POSITION"
    REDUCING = "REDUCING"
    EXITING = "EXITING"
    CLOSED = "CLOSED"


@dataclass
class ScalpingProbePosition:
    """Scalping probe position"""
    trade_id: str
    instrument: str  # NIFTY, BANKNIFTY, SENSEX, BANKEX
    option_type: str  # CE or PE
    strike: float
    expiry: str
    lot_size: int
    
    # Capital
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
    
    # Momentum tracking
    momentum_score: float = 0.0
    momentum_phase: str = "BUILDING"
    
    # Gemini
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
# SCALPING PROBE-SCALE ENGINE
# ============================================================================

class ScalpingProbeEngine:
    """
    Probe-Scale Engine for AI Scalping Service
    
    Specialized for index options scalping:
    - NIFTY, BANKNIFTY, SENSEX, BANKEX
    - Faster timeouts for scalping
    - Point-based trailing stops
    - Momentum-aware scaling
    """
    
    def __init__(self, config: ScalpingProbeConfig = None):
        self.config = config or ScalpingProbeConfig()
        
        # State
        self.positions: Dict[str, ScalpingProbePosition] = {}
        self.session: Optional[aiohttp.ClientSession] = None
        
        # Capital tracking
        self.total_capital = 500000.0
        self.deployed_capital = 0.0
        self.daily_pnl = 0.0
        
        # Initialize database
        self._init_database()
        
        logger.info("=" * 60)
        logger.info("SCALPING PROBE-SCALE ENGINE INITIALIZED")
        logger.info(f"Probe: {self.config.probe_capital_pct}% | Scale: {self.config.scale_capital_pct}%")
        logger.info(f"Probe SL: {self.config.probe_stoploss_pct}% (wide)")
        logger.info(f"Trailing: {self.config.trailing_distance_points}pt after {self.config.trailing_activation_points}pt profit")
        logger.info(f"Max Hold: {self.config.max_holding_minutes} minutes (scalping)")
        logger.info("=" * 60)
    
    def _init_database(self):
        """Initialize SQLite database"""
        os.makedirs(os.path.dirname(self.config.db_path) if os.path.dirname(self.config.db_path) else ".", exist_ok=True)
        
        with sqlite3.connect(self.config.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS scalping_positions (
                    trade_id TEXT PRIMARY KEY,
                    data TEXT NOT NULL,
                    created_at TEXT,
                    updated_at TEXT
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS scalping_history (
                    trade_id TEXT PRIMARY KEY,
                    data TEXT NOT NULL,
                    closed_at TEXT,
                    pnl REAL
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
        instrument: str,
        option_type: str,
        strike: float,
        expiry: str,
        entry_price: float,
        allocated_capital: float,
        momentum_score: float = 0.0,
        entry_reason: str = "AI Signal"
    ) -> Optional[ScalpingProbePosition]:
        """
        Enter probe position with 10% capital and 50% wide stoploss
        """
        import uuid
        trade_id = f"SCALP_{uuid.uuid4().hex[:8].upper()}"
        
        lot_size = self.config.lot_sizes.get(instrument, 50)
        
        # Calculate probe allocation
        probe_capital = allocated_capital * (self.config.probe_capital_pct / 100)
        position_value = entry_price * lot_size
        probe_quantity = max(1, int(probe_capital / position_value))
        actual_probe_capital = probe_quantity * position_value
        
        # 50% wide stoploss
        stoploss = entry_price * (1 - self.config.probe_stoploss_pct / 100)
        
        position = ScalpingProbePosition(
            trade_id=trade_id,
            instrument=instrument,
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
            phase=ScalpingPhase.PROBE.value,
            current_price=entry_price,
            highest_price=entry_price,
            lowest_price=entry_price,
            momentum_score=momentum_score,
            entry_reason=entry_reason
        )
        
        self.positions[trade_id] = position
        self.deployed_capital += actual_probe_capital
        self._save_position(position)
        
        logger.info("=" * 50)
        logger.info(f"✅ SCALP PROBE: {instrument} {option_type} {strike}")
        logger.info(f"   Trade ID: {trade_id}")
        logger.info(f"   Entry: ₹{entry_price:.2f}")
        logger.info(f"   Qty: {probe_quantity} lots ({probe_quantity * lot_size} units)")
        logger.info(f"   Capital: ₹{actual_probe_capital:,.2f} (10%)")
        logger.info(f"   SL: ₹{stoploss:.2f} (50% wide)")
        logger.info(f"   Scale Reserve: ₹{position.scale_capital:,.2f}")
        logger.info("=" * 50)
        
        return position
    
    # =========================================================================
    # PRICE UPDATE & MONITORING
    # =========================================================================
    
    async def update_price(self, trade_id: str, current_price: float, momentum_score: float = None) -> Dict[str, Any]:
        """Update price and check conditions"""
        
        position = self.positions.get(trade_id)
        if not position:
            return {'action': 'NOT_FOUND'}
        
        # Update prices
        position.current_price = current_price
        position.highest_price = max(position.highest_price, current_price)
        position.lowest_price = min(position.lowest_price, current_price)
        
        if momentum_score is not None:
            position.momentum_score = momentum_score
        
        # Calculate P&L
        if position.phase == ScalpingPhase.FULL_POSITION.value and position.scale_quantity > 0:
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
        
        # Hard stoploss check
        active_sl = position.scale_stoploss if position.phase == ScalpingPhase.FULL_POSITION.value else position.probe_stoploss
        if current_price <= active_sl:
            return await self._trigger_exit(position, "STOPLOSS_HIT")
        
        # Trailing stop check
        if position.trailing_activated and current_price <= position.trailing_stop:
            return await self._trigger_exit(position, "TRAILING_STOP_HIT")
        
        # Update trailing
        if position.pnl_points >= self.config.trailing_activation_points:
            if not position.trailing_activated:
                position.trailing_activated = True
                logger.info(f"📈 Trailing ACTIVATED: {trade_id}")
            
            new_trail = current_price - self.config.trailing_distance_points
            if new_trail > position.trailing_stop:
                position.trailing_stop = new_trail
                logger.debug(f"   Trail updated: ₹{new_trail:.2f}")
        
        # Phase logic
        if position.phase == ScalpingPhase.PROBE.value:
            return await self._handle_probe(position)
        elif position.phase == ScalpingPhase.FULL_POSITION.value:
            return await self._handle_full(position)
        
        self._save_position(position)
        return {'action': 'HOLD', 'position': asdict(position)}
    
    async def _handle_probe(self, position: ScalpingProbePosition) -> Dict[str, Any]:
        """Handle probe phase"""
        
        # Profitable? Check for scale
        if position.pnl_percent >= self.config.min_profit_to_scale_pct:
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
        
        # Too much loss?
        elif position.pnl_percent <= -self.config.max_probe_loss_pct:
            return await self._trigger_exit(position, f"PROBE_ABORT: {position.pnl_percent:.1f}% loss")
        
        # Timeout?
        entry_time = datetime.fromisoformat(position.probe_entry_time)
        elapsed = (datetime.now() - entry_time).total_seconds()
        
        if elapsed > self.config.probe_timeout_seconds:
            if position.pnl_percent < self.config.min_profit_to_scale_pct:
                return await self._trigger_exit(position, "PROBE_TIMEOUT")
        
        self._save_position(position)
        return {'action': 'HOLD', 'position': asdict(position)}
    
    async def _handle_full(self, position: ScalpingProbePosition) -> Dict[str, Any]:
        """Handle full position"""
        
        # Consult Gemini
        analysis = await self._consult_gemini_exit(position)
        position.gemini_checks += 1
        position.last_gemini_decision = analysis.get('decision', 'HOLD')
        position.momentum_status = analysis.get('momentum_status', 'MODERATE')
        
        if analysis.get('decision') == 'FULL_EXIT':
            return await self._trigger_exit(position, f"GEMINI: {analysis.get('reasoning', 'Exit now')[:25]}")
        
        elif analysis.get('decision') == 'PARTIAL_EXIT':
            return {
                'action': 'PARTIAL_EXIT',
                'exit_percent': analysis.get('exit_percent', 50),
                'reasoning': analysis.get('reasoning', ''),
                'position': asdict(position)
            }
        
        # Momentum exhausted?
        if position.momentum_status in ['EXHAUSTED', 'REVERSING']:
            return await self._trigger_exit(position, f"MOMENTUM_{position.momentum_status}")
        
        # Max hold time?
        entry_time = datetime.fromisoformat(position.probe_entry_time)
        elapsed_min = (datetime.now() - entry_time).total_seconds() / 60
        
        if elapsed_min > self.config.max_holding_minutes:
            return await self._trigger_exit(position, "MAX_HOLD_TIME")
        
        self._save_position(position)
        return {'action': 'HOLD', 'position': asdict(position)}
    
    # =========================================================================
    # SCALE UP
    # =========================================================================
    
    async def scale_up(self, trade_id: str, scale_percent: float = 90.0) -> Dict[str, Any]:
        """Scale up position"""
        
        position = self.positions.get(trade_id)
        if not position:
            return {'success': False, 'error': 'Not found'}
        
        if position.phase != ScalpingPhase.PROBE.value:
            return {'success': False, 'error': 'Already scaled'}
        
        scale_capital = position.scale_capital * (scale_percent / 100)
        position_value = position.current_price * position.lot_size
        scale_quantity = max(1, int(scale_capital / position_value))
        
        total_qty = position.probe_quantity + scale_quantity
        avg_entry = (position.probe_entry_price * position.probe_quantity + 
                    position.current_price * scale_quantity) / total_qty
        scale_stoploss = avg_entry * (1 - self.config.scaled_stoploss_pct / 100)
        
        position.scale_entry_price = position.current_price
        position.scale_entry_time = datetime.now().isoformat()
        position.scale_quantity = scale_quantity
        position.scale_stoploss = scale_stoploss
        position.phase = ScalpingPhase.FULL_POSITION.value
        
        actual_scale_capital = scale_quantity * position_value
        self.deployed_capital += actual_scale_capital
        self._save_position(position)
        
        logger.info("=" * 50)
        logger.info(f"✅ SCALED: {position.instrument} {position.option_type}")
        logger.info(f"   Added: {scale_quantity} lots @ ₹{position.current_price:.2f}")
        logger.info(f"   Total: {total_qty} lots")
        logger.info(f"   Avg: ₹{avg_entry:.2f}")
        logger.info(f"   SL: ₹{scale_stoploss:.2f} (30%)")
        logger.info("=" * 50)
        
        return {
            'success': True,
            'scale_quantity': scale_quantity,
            'total_quantity': total_qty,
            'avg_entry': avg_entry,
            'new_stoploss': scale_stoploss
        }
    
    # =========================================================================
    # EXIT
    # =========================================================================
    
    async def _trigger_exit(self, position: ScalpingProbePosition, reason: str) -> Dict[str, Any]:
        """Trigger exit"""
        position.phase = ScalpingPhase.EXITING.value
        self._save_position(position)
        return {'action': 'EXIT', 'reason': reason, 'position': asdict(position)}
    
    async def execute_exit(self, trade_id: str, exit_price: float, reason: str = "Manual") -> Dict[str, Any]:
        """Execute exit"""
        
        position = self.positions.get(trade_id)
        if not position:
            return {'success': False, 'error': 'Not found'}
        
        if position.scale_quantity > 0:
            total_qty = position.probe_quantity + position.scale_quantity
            avg_entry = (position.probe_entry_price * position.probe_quantity + 
                        position.scale_entry_price * position.scale_quantity) / total_qty
        else:
            total_qty = position.probe_quantity
            avg_entry = position.probe_entry_price
        
        pnl = (exit_price - avg_entry) * total_qty * position.lot_size
        
        position.exit_price = exit_price
        position.exit_time = datetime.now().isoformat()
        position.exit_reason = reason
        position.realized_pnl = pnl
        position.phase = ScalpingPhase.CLOSED.value
        
        # Update capital
        capital_used = position.probe_capital
        if position.scale_quantity > 0:
            capital_used += position.scale_quantity * position.scale_entry_price * position.lot_size
        
        self.deployed_capital -= capital_used
        self.daily_pnl += pnl
        
        self._save_to_history(position)
        del self.positions[trade_id]
        
        logger.info("=" * 50)
        logger.info(f"✅ EXITED: {position.instrument} {position.option_type}")
        logger.info(f"   Reason: {reason}")
        logger.info(f"   Exit: ₹{exit_price:.2f}")
        logger.info(f"   P&L: ₹{pnl:+,.2f}")
        logger.info(f"   Daily P&L: ₹{self.daily_pnl:+,.2f}")
        logger.info("=" * 50)
        
        return {'success': True, 'pnl': pnl, 'exit_price': exit_price}
    
    # =========================================================================
    # GEMINI CONSULTATIONS
    # =========================================================================
    
    async def _consult_gemini_scale(self, position: ScalpingProbePosition) -> Dict[str, Any]:
        """Consult Gemini for scale decision"""
        await self._ensure_session()
        
        try:
            payload = {
                'service': 'scalping',
                'trade_id': position.trade_id,
                'instrument': position.instrument,
                'option_type': position.option_type,
                'strike': position.strike,
                'entry_price': position.probe_entry_price,
                'current_price': position.current_price,
                'highest_price': position.highest_price,
                'pnl_percent': position.pnl_percent,
                'momentum_score': position.momentum_score,
                'remaining_capital': position.scale_capital,
                'time_in_trade': (datetime.now() - datetime.fromisoformat(position.probe_entry_time)).total_seconds()
            }
            
            async with self.session.post(
                f"{self.config.gemini_service_url}/api/trade-intel/scale-decision",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=15)
            ) as resp:
                if resp.status == 200:
                    return await resp.json()
                    
        except Exception as e:
            logger.error(f"Gemini scale error: {e}")
        
        return {'decision': 'HOLD', 'confidence': 50}
    
    async def _consult_gemini_exit(self, position: ScalpingProbePosition) -> Dict[str, Any]:
        """Consult Gemini for exit decision"""
        await self._ensure_session()
        
        try:
            total_qty = position.probe_quantity + position.scale_quantity
            
            payload = {
                'service': 'scalping',
                'trade_id': position.trade_id,
                'instrument': position.instrument,
                'option_type': position.option_type,
                'strike': position.strike,
                'entry_price': position.probe_entry_price,
                'current_price': position.current_price,
                'highest_price': position.highest_price,
                'pnl_percent': position.pnl_percent,
                'pnl_points': position.pnl_points,
                'total_quantity': total_qty,
                'momentum_score': position.momentum_score,
                'trailing_activated': position.trailing_activated,
                'trailing_stop': position.trailing_stop,
                'time_in_trade_minutes': (datetime.now() - datetime.fromisoformat(position.probe_entry_time)).total_seconds() / 60
            }
            
            async with self.session.post(
                f"{self.config.gemini_service_url}/api/trade-intel/exit-consultation",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=15)
            ) as resp:
                if resp.status == 200:
                    return await resp.json()
                    
        except Exception as e:
            logger.error(f"Gemini exit error: {e}")
        
        return {'decision': 'HOLD', 'momentum_status': 'MODERATE'}
    
    # =========================================================================
    # DATABASE
    # =========================================================================
    
    def _save_position(self, position: ScalpingProbePosition):
        with sqlite3.connect(self.config.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO scalping_positions (trade_id, data, created_at, updated_at)
                VALUES (?, ?, ?, ?)
            """, (position.trade_id, json.dumps(asdict(position)), position.created_at, datetime.now().isoformat()))
            conn.commit()
    
    def _save_to_history(self, position: ScalpingProbePosition):
        with sqlite3.connect(self.config.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO scalping_history (trade_id, data, closed_at, pnl)
                VALUES (?, ?, ?, ?)
            """, (position.trade_id, json.dumps(asdict(position)), datetime.now().isoformat(), position.realized_pnl))
            conn.execute("DELETE FROM scalping_positions WHERE trade_id = ?", (position.trade_id,))
            conn.commit()
    
    def get_position(self, trade_id: str) -> Optional[Dict]:
        pos = self.positions.get(trade_id)
        return asdict(pos) if pos else None
    
    def get_all_positions(self) -> List[Dict]:
        return [asdict(p) for p in self.positions.values()]
    
    def get_status(self) -> Dict:
        return {
            'active_positions': len(self.positions),
            'deployed_capital': self.deployed_capital,
            'daily_pnl': self.daily_pnl,
            'positions': self.get_all_positions()
        }
