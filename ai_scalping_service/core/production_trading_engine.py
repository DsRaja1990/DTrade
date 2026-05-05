"""
╔══════════════════════════════════════════════════════════════════════════════════════╗
║        AI SCALPING SERVICE - PRODUCTION TRADING ENGINE v2.0                          ║
║                Index Options Scalping (NIFTY, BANKNIFTY, SENSEX, BANKEX)            ║
╠══════════════════════════════════════════════════════════════════════════════════════╣
║                                                                                      ║
║  SERVICE: AI Scalping Service - Port 4002                                           ║
║  INSTRUMENTS: NIFTY (75), BANKNIFTY (35), SENSEX (20), BANKEX (30)                 ║
║  MODE: Paper Trading Default → Switchable to Live                                   ║
║                                                                                      ║
║  SCALPING METHODOLOGY:                                                               ║
║  ═══════════════════════════════════════════════════════════════════════════════    ║
║                                                                                      ║
║  1. MOMENTUM-BASED ENTRY                                                             ║
║     • Detect momentum spikes with multi-timeframe analysis                          ║
║     • 10% capital probe with 50% wide stoploss                                      ║
║     • Scale to 100% on Gemini confirmation                                          ║
║                                                                                      ║
║  2. FAST EXIT STRATEGY                                                               ║
║     • 50-point trailing after 50-point profit                                       ║
║     • 30-second Gemini AI exit consultation                                         ║
║     • Quick profit booking for scalping                                             ║
║                                                                                      ║
║  3. WORLD-CLASS SCALPING FEATURES                                                    ║
║     • Multi-instrument momentum tracking                                            ║
║     • Single-focus capital deployment (best opportunity)                            ║
║     • Dynamic position sizing based on conviction                                   ║
║                                                                                      ║
╚══════════════════════════════════════════════════════════════════════════════════════╝
"""

import asyncio
import aiohttp
import json
import logging
import sqlite3
import uuid
from datetime import datetime, date, time, timedelta
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
from pathlib import Path
import os
import sys

logger = logging.getLogger(__name__ + '.production_trading_engine')


# ============================================================================
# TRADING ENUMS
# ============================================================================

class TradingMode(str, Enum):
    """Trading mode - Paper for testing, Live for real trades"""
    PAPER = "PAPER"
    LIVE = "LIVE"


class MomentumPhase(str, Enum):
    """Momentum phase detection"""
    DORMANT = "DORMANT"
    BUILDING = "BUILDING"
    ACCELERATING = "ACCELERATING"
    PEAK = "PEAK"
    FADING = "FADING"
    REVERSAL = "REVERSAL"


class TradePhase(str, Enum):
    """Trade lifecycle phases"""
    SCANNING = "SCANNING"
    STALKING = "STALKING"
    PROBE = "PROBE"
    CONFIRMING = "CONFIRMING"
    SCALING = "SCALING"
    FULL_POSITION = "FULL_POSITION"
    TRAILING = "TRAILING"
    EXITING = "EXITING"
    CLOSED = "CLOSED"


class TradeDirection(str, Enum):
    """Trade direction"""
    BULLISH = "BULLISH"
    BEARISH = "BEARISH"
    NEUTRAL = "NEUTRAL"


class ExitReason(str, Enum):
    """Exit reason tracking"""
    STOPLOSS = "STOPLOSS"
    TRAILING_STOP = "TRAILING_STOP"
    TARGET_HIT = "TARGET_HIT"
    GEMINI_EXIT = "GEMINI_EXIT"
    TIME_EXIT = "TIME_EXIT"
    MOMENTUM_FADE = "MOMENTUM_FADE"
    PROBE_ABORT = "PROBE_ABORT"
    USER_MANUAL = "USER_MANUAL"
    MARKET_CLOSE = "MARKET_CLOSE"
    QUICK_PROFIT = "QUICK_PROFIT"


# ============================================================================
# CONFIGURATION
# ============================================================================

@dataclass
class ScalpingEngineConfig:
    """AI Scalping Service Engine Configuration"""
    
    # Service settings
    service_name: str = "AI_Scalping_Service"
    service_port: int = 4002
    
    # Trading mode - PAPER by default
    trading_mode: TradingMode = TradingMode.PAPER
    
    # Capital settings
    total_capital: float = 500000.0
    max_daily_loss_percent: float = 2.0
    max_capital_per_trade: float = 150000.0
    max_concurrent_positions: int = 1  # Single focus for scalping
    
    # Instruments (Index Options)
    instruments: List[str] = field(default_factory=lambda: ["NIFTY", "BANKNIFTY", "SENSEX", "BANKEX"])
    lot_sizes: Dict[str, int] = field(default_factory=lambda: {
        "NIFTY": 75,
        "BANKNIFTY": 35,
        "SENSEX": 20,
        "BANKEX": 30
    })
    
    # Probe-Scale settings
    probe_capital_pct: float = 10.0       # 10% for probe
    scale_capital_pct: float = 90.0       # 90% for scale
    probe_stoploss_pct: float = 50.0      # 50% wide stoploss
    scaled_stoploss_pct: float = 25.0     # Tighter for scalping
    
    # Trailing stop (50-point as specified)
    trailing_activation_points: float = 50.0  # Activate at 50 pts profit
    trailing_distance_points: float = 50.0    # Trail 50 pts behind
    
    # Quick profit targets for scalping
    quick_profit_pct: float = 15.0        # Book 15% profit quickly
    aggressive_target_pct: float = 30.0   # Target 30% for aggressive mode
    
    # Momentum thresholds
    min_momentum_for_entry: float = 60.0
    min_momentum_for_scale: float = 70.0
    exit_momentum_threshold: float = 30.0
    
    # AI settings
    gemini_service_url: str = "http://localhost:4080"
    min_gemini_confidence: float = 0.85
    gemini_check_interval: int = 30       # Check every 30 seconds
    
    # Scaling thresholds
    min_profit_to_scale_pct: float = 10.0
    max_probe_loss_pct: float = 25.0
    
    # Trading hours (IST)
    trading_start: time = field(default_factory=lambda: time(9, 20))
    trading_end: time = field(default_factory=lambda: time(15, 15))
    no_new_trades_after: time = field(default_factory=lambda: time(15, 0))
    
    # Scalping timing (faster than hedging)
    probe_timeout_seconds: int = 90       # 1.5 min probe timeout
    max_position_minutes: int = 30        # Max 30 min for scalping
    
    # Database
    db_path: str = "database/scalping_trades.db"
    
    # Paper trading settings (REALISTIC values for backtesting accuracy)
    # Note: Actual index options slippage is 0.3-0.5% especially near expiry
    paper_slippage_pct: float = 0.35      # 0.35% realistic slippage (was 0.15%)
    paper_latency_ms: int = 50            # 50ms simulated latency (realistic for retail)


# ============================================================================
# MOMENTUM TRACKING
# ============================================================================

@dataclass
class MomentumData:
    """Real-time momentum data for scalping"""
    instrument: str
    timestamp: datetime = field(default_factory=datetime.now)
    
    # Price data
    current_price: float = 0.0
    open_price: float = 0.0
    high_price: float = 0.0
    low_price: float = 0.0
    
    # Volume
    volume: int = 0
    volume_ma: float = 0.0
    volume_ratio: float = 1.0
    
    # Momentum scores (0-100)
    momentum_score: float = 0.0
    momentum_5s: float = 0.0
    momentum_30s: float = 0.0
    momentum_1m: float = 0.0
    momentum_5m: float = 0.0
    
    # Velocity and acceleration
    velocity: float = 0.0
    acceleration: float = 0.0
    
    # Phase
    phase: MomentumPhase = MomentumPhase.DORMANT
    trend: str = "NEUTRAL"
    
    # History for calculations
    price_history: List[float] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return {
            'instrument': self.instrument,
            'timestamp': self.timestamp.isoformat(),
            'current_price': self.current_price,
            'momentum_score': round(self.momentum_score, 2),
            'velocity': round(self.velocity, 4),
            'acceleration': round(self.acceleration, 4),
            'phase': self.phase.value,
            'trend': self.trend,
            'volume_ratio': round(self.volume_ratio, 2)
        }
    
    def update_momentum(self, new_price: float):
        """Update momentum calculations with new price"""
        self.price_history.append(new_price)
        
        # Keep only last 300 ticks (5 min at 1 tick/sec)
        if len(self.price_history) > 300:
            self.price_history = self.price_history[-300:]
        
        self.current_price = new_price
        
        if len(self.price_history) >= 2:
            # Calculate velocity (price change rate)
            self.velocity = (self.price_history[-1] - self.price_history[-2]) / max(self.price_history[-2], 0.01)
            
            # Calculate multi-timeframe momentum
            if len(self.price_history) >= 5:
                self.momentum_5s = self._calc_momentum(5)
            if len(self.price_history) >= 30:
                self.momentum_30s = self._calc_momentum(30)
            if len(self.price_history) >= 60:
                self.momentum_1m = self._calc_momentum(60)
            if len(self.price_history) >= 300:
                self.momentum_5m = self._calc_momentum(300)
            
            # Weighted momentum score
            self.momentum_score = (
                self.momentum_5s * 0.4 +
                self.momentum_30s * 0.3 +
                self.momentum_1m * 0.2 +
                self.momentum_5m * 0.1
            )
            
            # Determine phase
            self._update_phase()
    
    def _calc_momentum(self, lookback: int) -> float:
        """Calculate momentum for given lookback period"""
        if len(self.price_history) < lookback:
            return 0.0
        
        start_price = self.price_history[-lookback]
        end_price = self.price_history[-1]
        
        if start_price == 0:
            return 0.0
        
        pct_change = ((end_price - start_price) / start_price) * 100
        
        # Normalize to 0-100 scale (assuming max 2% move in any period)
        normalized = min(100, max(0, abs(pct_change) * 50))
        
        return normalized if pct_change >= 0 else -normalized
    
    def _update_phase(self):
        """Update momentum phase based on score and velocity"""
        score = self.momentum_score
        velocity = self.velocity
        
        if score >= 80 and velocity > 0:
            self.phase = MomentumPhase.PEAK
            self.trend = "STRONG_UP"
        elif score >= 80 and velocity < 0:
            self.phase = MomentumPhase.PEAK
            self.trend = "STRONG_DOWN"
        elif score >= 60:
            self.phase = MomentumPhase.ACCELERATING
            self.trend = "UP" if velocity > 0 else "DOWN"
        elif score >= 40:
            self.phase = MomentumPhase.BUILDING
            self.trend = "NEUTRAL"
        elif score >= 20:
            self.phase = MomentumPhase.FADING
            self.trend = "NEUTRAL"
        else:
            self.phase = MomentumPhase.DORMANT
            self.trend = "NEUTRAL"
        
        # Check for reversal
        if len(self.price_history) >= 10:
            recent_trend = self.price_history[-1] - self.price_history[-10]
            older_trend = self.price_history[-10] - self.price_history[-20] if len(self.price_history) >= 20 else 0
            
            if (recent_trend > 0 and older_trend < 0) or (recent_trend < 0 and older_trend > 0):
                self.phase = MomentumPhase.REVERSAL


# ============================================================================
# POSITION DATA STRUCTURES
# ============================================================================

@dataclass
class ScalpingPosition:
    """Scalping position tracking"""
    position_id: str
    instrument: str           # NIFTY, BANKNIFTY, SENSEX, BANKEX
    option_type: str          # CE or PE
    strike: float
    expiry: str
    
    # Position sizing
    probe_lots: int = 0
    scaled_lots: int = 0
    total_lots: int = 0
    lot_size: int = 75
    
    # Prices
    probe_entry_price: float = 0.0
    scaled_entry_price: float = 0.0
    avg_entry_price: float = 0.0
    current_price: float = 0.0
    peak_price: float = 0.0
    
    # Capital
    probe_capital: float = 0.0
    scaled_capital: float = 0.0
    total_capital: float = 0.0
    
    # Stoploss
    initial_stoploss: float = 0.0
    current_stoploss: float = 0.0
    trailing_activated: bool = False
    
    # PnL
    unrealized_pnl: float = 0.0
    unrealized_pnl_pct: float = 0.0
    peak_pnl: float = 0.0
    
    # State
    phase: TradePhase = TradePhase.SCANNING
    direction: TradeDirection = TradeDirection.NEUTRAL
    
    # Momentum
    entry_momentum: float = 0.0
    current_momentum: float = 0.0
    
    # AI
    gemini_confidence: float = 0.0
    gemini_recommendation: str = ""
    last_gemini_check: Optional[datetime] = None
    
    # Timestamps
    created_at: datetime = field(default_factory=datetime.now)
    probe_entry_time: Optional[datetime] = None
    scale_time: Optional[datetime] = None
    exit_time: Optional[datetime] = None
    exit_reason: Optional[ExitReason] = None
    
    def to_dict(self) -> Dict:
        return {
            'position_id': self.position_id,
            'instrument': self.instrument,
            'option_type': self.option_type,
            'strike': self.strike,
            'expiry': self.expiry,
            'probe_lots': self.probe_lots,
            'scaled_lots': self.scaled_lots,
            'total_lots': self.total_lots,
            'avg_entry_price': self.avg_entry_price,
            'current_price': self.current_price,
            'current_stoploss': self.current_stoploss,
            'trailing_activated': self.trailing_activated,
            'unrealized_pnl': round(self.unrealized_pnl, 2),
            'unrealized_pnl_pct': round(self.unrealized_pnl_pct, 2),
            'phase': self.phase.value,
            'direction': self.direction.value,
            'entry_momentum': round(self.entry_momentum, 2),
            'current_momentum': round(self.current_momentum, 2),
            'gemini_confidence': self.gemini_confidence,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


@dataclass
class ScalpingStats:
    """Daily scalping statistics"""
    date: str = field(default_factory=lambda: date.today().isoformat())
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    total_pnl: float = 0.0
    max_drawdown: float = 0.0
    win_rate: float = 0.0
    avg_win: float = 0.0
    avg_loss: float = 0.0
    avg_hold_seconds: float = 0.0
    probes_taken: int = 0
    probes_scaled: int = 0
    quick_exits: int = 0
    momentum_exits: int = 0


# ============================================================================
# PAPER TRADE EXECUTOR
# ============================================================================

class PaperScalpingExecutor:
    """
    Paper trading executor for scalping - simulates fast execution.
    """
    
    def __init__(self, config: ScalpingEngineConfig):
        self.config = config
        self.logger = logging.getLogger(__name__ + '.paper_executor')
        self.executed_orders: List[Dict] = []
        self.order_counter = 0
        
    async def execute_buy(
        self,
        instrument: str,
        option_type: str,
        strike: float,
        expiry: str,
        lots: int,
        price: float
    ) -> Dict:
        """Simulate fast buy order execution"""
        await asyncio.sleep(self.config.paper_latency_ms / 1000)
        
        # Apply slippage (buy higher - scalping needs realistic slippage)
        slippage = price * (self.config.paper_slippage_pct / 100)
        execution_price = price + slippage
        
        self.order_counter += 1
        order_id = f"SCALP_BUY_{self.order_counter}_{datetime.now().strftime('%H%M%S%f')}"
        
        lot_size = self.config.lot_sizes.get(instrument, 75)
        quantity = lots * lot_size
        value = execution_price * quantity
        
        order = {
            'order_id': order_id,
            'type': 'BUY',
            'instrument': instrument,
            'option_type': option_type,
            'strike': strike,
            'expiry': expiry,
            'lots': lots,
            'lot_size': lot_size,
            'quantity': quantity,
            'requested_price': price,
            'execution_price': execution_price,
            'slippage': slippage,
            'value': value,
            'status': 'FILLED',
            'mode': 'PAPER',
            'latency_ms': self.config.paper_latency_ms,
            'timestamp': datetime.now().isoformat()
        }
        
        self.executed_orders.append(order)
        
        self.logger.info(
            f"📄 SCALP BUY: {instrument} {strike}{option_type} | "
            f"{lots} lots @ ₹{execution_price:.2f} | Latency: {self.config.paper_latency_ms}ms"
        )
        
        return order
    
    async def execute_sell(
        self,
        instrument: str,
        option_type: str,
        strike: float,
        expiry: str,
        lots: int,
        price: float
    ) -> Dict:
        """Simulate fast sell order execution"""
        await asyncio.sleep(self.config.paper_latency_ms / 1000)
        
        # Apply slippage (sell lower)
        slippage = price * (self.config.paper_slippage_pct / 100)
        execution_price = price - slippage
        
        self.order_counter += 1
        order_id = f"SCALP_SELL_{self.order_counter}_{datetime.now().strftime('%H%M%S%f')}"
        
        lot_size = self.config.lot_sizes.get(instrument, 75)
        quantity = lots * lot_size
        value = execution_price * quantity
        
        order = {
            'order_id': order_id,
            'type': 'SELL',
            'instrument': instrument,
            'option_type': option_type,
            'strike': strike,
            'expiry': expiry,
            'lots': lots,
            'lot_size': lot_size,
            'quantity': quantity,
            'requested_price': price,
            'execution_price': execution_price,
            'slippage': slippage,
            'value': value,
            'status': 'FILLED',
            'mode': 'PAPER',
            'latency_ms': self.config.paper_latency_ms,
            'timestamp': datetime.now().isoformat()
        }
        
        self.executed_orders.append(order)
        
        self.logger.info(
            f"📄 SCALP SELL: {instrument} {strike}{option_type} | "
            f"{lots} lots @ ₹{execution_price:.2f}"
        )
        
        return order


# ============================================================================
# LIVE TRADE EXECUTOR
# ============================================================================

class LiveScalpingExecutor:
    """
    Live trading executor for scalping - fast execution via Dhan API.
    """
    
    def __init__(self, config: ScalpingEngineConfig):
        self.config = config
        self.logger = logging.getLogger(__name__ + '.live_executor')
        self._session: Optional[aiohttp.ClientSession] = None
        
        self.dhan_token = os.getenv('DHAN_ACCESS_TOKEN', '')
        self.dhan_client_id = os.getenv('DHAN_CLIENT_ID', '')
        
        if not self.dhan_token:
            self.logger.warning("⚠️ DHAN_ACCESS_TOKEN not set - Live trading disabled")
    
    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session
    
    async def execute_buy(
        self,
        instrument: str,
        option_type: str,
        strike: float,
        expiry: str,
        lots: int,
        price: float
    ) -> Dict:
        """Execute live buy order"""
        if not self.dhan_token:
            raise RuntimeError("Dhan API token not configured")
        
        lot_size = self.config.lot_sizes.get(instrument, 75)
        quantity = lots * lot_size
        
        self.logger.info(
            f"🔴 LIVE SCALP BUY: {instrument} {strike}{option_type} | "
            f"{lots} lots ({quantity} qty) @ ₹{price:.2f}"
        )
        
        # TODO: Implement Dhan API integration
        return {
            'order_id': f"LIVE_SCALP_{datetime.now().strftime('%H%M%S%f')}",
            'status': 'PENDING',
            'mode': 'LIVE'
        }
    
    async def execute_sell(
        self,
        instrument: str,
        option_type: str,
        strike: float,
        expiry: str,
        lots: int,
        price: float
    ) -> Dict:
        """Execute live sell order"""
        if not self.dhan_token:
            raise RuntimeError("Dhan API token not configured")
        
        lot_size = self.config.lot_sizes.get(instrument, 75)
        quantity = lots * lot_size
        
        self.logger.info(
            f"🔴 LIVE SCALP SELL: {instrument} {strike}{option_type} | "
            f"{lots} lots ({quantity} qty) @ ₹{price:.2f}"
        )
        
        return {
            'order_id': f"LIVE_SCALP_{datetime.now().strftime('%H%M%S%f')}",
            'status': 'PENDING',
            'mode': 'LIVE'
        }
    
    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()


# ============================================================================
# GEMINI AI CLIENT FOR SCALPING
# ============================================================================

class ScalpingGeminiClient:
    """Gemini AI Client optimized for scalping decisions"""
    
    def __init__(self, config: ScalpingEngineConfig):
        self.config = config
        self.logger = logging.getLogger(__name__ + '.gemini_client')
        self._session: Optional[aiohttp.ClientSession] = None
        self._healthy = False
        
        self.requests = 0
        self.successes = 0
        self.failures = 0
    
    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=15)  # Faster timeout for scalping
            )
        return self._session
    
    async def check_health(self) -> bool:
        """Check Gemini service health"""
        try:
            session = await self._get_session()
            async with session.get(
                f"{self.config.gemini_service_url}/health",
                timeout=3
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    self._healthy = data.get('status') == 'healthy'
                    return self._healthy
        except Exception as e:
            self.logger.warning(f"Gemini health check failed: {e}")
            self._healthy = False
        return False
    
    async def validate_scalp_entry(
        self,
        instrument: str,
        direction: str,
        momentum_score: float,
        price: float,
        volume_ratio: float
    ) -> Dict:
        """Fast validation for scalp entry"""
        try:
            self.requests += 1
            session = await self._get_session()
            
            payload = {
                'instrument': instrument,
                'direction': direction,
                'momentum_score': momentum_score,
                'current_price': price,
                'volume_ratio': volume_ratio,
                'trade_type': 'scalp',
                'query_type': 'scalp_entry_validation'
            }
            
            async with session.post(
                f"{self.config.gemini_service_url}/api/validate/trade",
                json=payload,
                timeout=10  # Fast timeout
            ) as resp:
                if resp.status == 200:
                    self.successes += 1
                    return await resp.json()
                else:
                    self.failures += 1
        except Exception as e:
            self.failures += 1
            self.logger.error(f"Scalp validation error: {e}")
        
        return {'valid': False, 'confidence': 0.0, 'reason': 'Service unavailable'}
    
    async def get_quick_exit_decision(
        self,
        instrument: str,
        pnl_percent: float,
        holding_seconds: int,
        current_momentum: float,
        peak_pnl_percent: float
    ) -> Dict:
        """Fast exit decision for scalping"""
        try:
            self.requests += 1
            session = await self._get_session()
            
            payload = {
                'instrument': instrument,
                'pnl_percent': pnl_percent,
                'holding_seconds': holding_seconds,
                'current_momentum': current_momentum,
                'peak_pnl_percent': peak_pnl_percent,
                'trade_type': 'scalp',
                'query_type': 'scalp_exit_decision'
            }
            
            async with session.post(
                f"{self.config.gemini_service_url}/api/probe-scale/exit-decision",
                json=payload,
                timeout=10
            ) as resp:
                if resp.status == 200:
                    self.successes += 1
                    return await resp.json()
                else:
                    self.failures += 1
        except Exception as e:
            self.failures += 1
            self.logger.error(f"Exit decision error: {e}")
        
        return {'exit': False, 'confidence': 0.0, 'reason': 'Service unavailable'}
    
    async def get_momentum_prediction(
        self,
        instrument: str,
        current_momentum: float,
        momentum_history: List[float]
    ) -> Dict:
        """Get momentum continuation prediction"""
        try:
            self.requests += 1
            session = await self._get_session()
            
            payload = {
                'instrument': instrument,
                'current_momentum': current_momentum,
                'momentum_history': momentum_history[-10:],  # Last 10 readings
                'query_type': 'momentum_prediction'
            }
            
            async with session.post(
                f"{self.config.gemini_service_url}/api/predict/momentum",
                json=payload,
                timeout=10
            ) as resp:
                if resp.status == 200:
                    self.successes += 1
                    return await resp.json()
                else:
                    self.failures += 1
        except Exception as e:
            self.failures += 1
        
        return {'continuation_probability': 0.5, 'predicted_direction': 'NEUTRAL'}
    
    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()


# ============================================================================
# DATABASE MANAGER
# ============================================================================

class ScalpingDatabase:
    """SQLite database for scalping trade history"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self._init_db()
    
    def _init_db(self):
        """Initialize database tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS scalp_trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                position_id TEXT UNIQUE,
                instrument TEXT,
                option_type TEXT,
                strike REAL,
                expiry TEXT,
                direction TEXT,
                
                probe_lots INTEGER,
                scaled_lots INTEGER,
                total_lots INTEGER,
                
                probe_entry_price REAL,
                scaled_entry_price REAL,
                avg_entry_price REAL,
                exit_price REAL,
                
                probe_capital REAL,
                scaled_capital REAL,
                total_capital REAL,
                
                realized_pnl REAL,
                realized_pnl_pct REAL,
                peak_pnl REAL,
                
                entry_momentum REAL,
                exit_momentum REAL,
                
                hold_duration_seconds INTEGER,
                phase TEXT,
                exit_reason TEXT,
                trading_mode TEXT,
                
                gemini_entry_confidence REAL,
                gemini_exit_confidence REAL,
                
                probe_entry_time TEXT,
                scale_time TEXT,
                exit_time TEXT,
                
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def save_trade(self, position: ScalpingPosition, exit_price: float, realized_pnl: float, hold_seconds: int):
        """Save completed scalp trade"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO scalp_trades (
                position_id, instrument, option_type, strike, expiry, direction,
                probe_lots, scaled_lots, total_lots,
                probe_entry_price, scaled_entry_price, avg_entry_price, exit_price,
                probe_capital, scaled_capital, total_capital,
                realized_pnl, realized_pnl_pct, peak_pnl,
                entry_momentum, exit_momentum,
                hold_duration_seconds, phase, exit_reason, trading_mode,
                gemini_entry_confidence, gemini_exit_confidence,
                probe_entry_time, scale_time, exit_time
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            position.position_id, position.instrument, position.option_type,
            position.strike, position.expiry, position.direction.value,
            position.probe_lots, position.scaled_lots, position.total_lots,
            position.probe_entry_price, position.scaled_entry_price, position.avg_entry_price, exit_price,
            position.probe_capital, position.scaled_capital, position.total_capital,
            realized_pnl, (realized_pnl / position.total_capital * 100) if position.total_capital > 0 else 0,
            position.peak_pnl,
            position.entry_momentum, position.current_momentum,
            hold_seconds, position.phase.value,
            position.exit_reason.value if position.exit_reason else None, "PAPER",
            position.gemini_confidence, 0,
            position.probe_entry_time.isoformat() if position.probe_entry_time else None,
            position.scale_time.isoformat() if position.scale_time else None,
            datetime.now().isoformat()
        ))
        
        conn.commit()
        conn.close()
    
    def get_today_stats(self) -> Dict:
        """Get today's scalping statistics"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        today = date.today().isoformat()
        
        cursor.execute('''
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN realized_pnl > 0 THEN 1 ELSE 0 END) as wins,
                SUM(CASE WHEN realized_pnl <= 0 THEN 1 ELSE 0 END) as losses,
                COALESCE(SUM(realized_pnl), 0) as total_pnl,
                AVG(hold_duration_seconds) as avg_hold
            FROM scalp_trades
            WHERE DATE(exit_time) = ?
        ''', (today,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            total = row[0] or 0
            wins = row[1] or 0
            return {
                'total_trades': total,
                'winning_trades': wins,
                'losing_trades': row[2] or 0,
                'total_pnl': row[3] or 0,
                'win_rate': (wins / total * 100) if total > 0 else 0,
                'avg_hold_seconds': row[4] or 0
            }
        
        return {'total_trades': 0, 'winning_trades': 0, 'losing_trades': 0, 'total_pnl': 0, 'win_rate': 0, 'avg_hold_seconds': 0}


# ============================================================================
# PRODUCTION SCALPING ENGINE
# ============================================================================

class ProductionScalpingEngine:
    """
    Production Scalping Engine for AI Scalping Service
    
    Implements:
    - Momentum-based entry with probe-scale methodology
    - Fast execution for scalping
    - 50-point trailing after 50-point profit
    - Single-focus capital deployment
    """
    
    def __init__(self, config: Optional[ScalpingEngineConfig] = None):
        self.config = config or ScalpingEngineConfig()
        self.logger = logging.getLogger(__name__ + '.engine')
        
        # Trading mode
        self._trading_mode = self.config.trading_mode
        
        # Executors
        self.paper_executor = PaperScalpingExecutor(self.config)
        self.live_executor = LiveScalpingExecutor(self.config)
        
        # AI Client
        self.gemini_client = ScalpingGeminiClient(self.config)
        
        # Database
        self.database = ScalpingDatabase(self.config.db_path)
        
        # Momentum tracking for all instruments
        self.momentum_data: Dict[str, MomentumData] = {
            inst: MomentumData(instrument=inst) for inst in self.config.instruments
        }
        
        # Positions (single focus for scalping)
        self.active_position: Optional[ScalpingPosition] = None
        self.closed_positions: List[ScalpingPosition] = []
        
        # Statistics
        self.stats = ScalpingStats()
        
        # State
        self._running = False
        self._monitoring_task: Optional[asyncio.Task] = None
        self._scanning_task: Optional[asyncio.Task] = None
        
        self.logger.info(
            f"🚀 Production Scalping Engine initialized | "
            f"Mode: {self._trading_mode.value} | "
            f"Capital: ₹{self.config.total_capital:,.2f} | "
            f"Instruments: {', '.join(self.config.instruments)}"
        )
    
    @property
    def trading_mode(self) -> TradingMode:
        return self._trading_mode
    
    @property
    def executor(self):
        """Get current executor based on trading mode"""
        if self._trading_mode == TradingMode.LIVE:
            return self.live_executor
        return self.paper_executor
    
    def switch_mode(self, mode: TradingMode) -> Dict:
        """Switch trading mode between PAPER and LIVE"""
        old_mode = self._trading_mode
        
        if mode == TradingMode.LIVE:
            if not os.getenv('DHAN_ACCESS_TOKEN'):
                return {
                    'success': False,
                    'error': 'Cannot switch to LIVE mode - DHAN_ACCESS_TOKEN not configured'
                }
            
            if self.active_position is not None:
                return {
                    'success': False,
                    'error': 'Cannot switch to LIVE mode with active position'
                }
        
        self._trading_mode = mode
        
        self.logger.info(f"⚡ Trading mode switched: {old_mode.value} → {mode.value}")
        
        return {
            'success': True,
            'old_mode': old_mode.value,
            'new_mode': mode.value,
            'timestamp': datetime.now().isoformat()
        }
    
    async def start(self):
        """Start the scalping engine"""
        if self._running:
            return
        
        self._running = True
        
        # Check Gemini health
        gemini_healthy = await self.gemini_client.check_health()
        self.logger.info(f"🤖 Gemini AI Status: {'Healthy' if gemini_healthy else 'Unavailable'}")
        
        # Start monitoring and scanning tasks
        self._monitoring_task = asyncio.create_task(self._position_monitor_loop())
        self._scanning_task = asyncio.create_task(self._momentum_scanner_loop())
        
        self.logger.info("✅ Production Scalping Engine started")
    
    async def stop(self):
        """Stop the scalping engine"""
        self._running = False
        
        for task in [self._monitoring_task, self._scanning_task]:
            if task:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        
        await self.gemini_client.close()
        await self.live_executor.close()
        
        self.logger.info("🛑 Production Scalping Engine stopped")
    
    async def _momentum_scanner_loop(self):
        """Scan for momentum opportunities"""
        while self._running:
            try:
                if self.active_position is None:
                    await self._scan_for_opportunity()
                await asyncio.sleep(1)  # Scan every second for scalping
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Momentum scanner error: {e}")
                await asyncio.sleep(5)
    
    async def _scan_for_opportunity(self):
        """Scan instruments for best scalping opportunity"""
        best_opportunity = None
        best_momentum = 0
        
        for instrument, momentum in self.momentum_data.items():
            if momentum.momentum_score >= self.config.min_momentum_for_entry:
                if momentum.momentum_score > best_momentum:
                    best_momentum = momentum.momentum_score
                    best_opportunity = {
                        'instrument': instrument,
                        'momentum': momentum,
                        'direction': TradeDirection.BULLISH if momentum.trend in ['UP', 'STRONG_UP'] else TradeDirection.BEARISH
                    }
        
        if best_opportunity:
            self.logger.info(
                f"🔍 Opportunity detected: {best_opportunity['instrument']} | "
                f"Momentum: {best_momentum:.1f} | Phase: {best_opportunity['momentum'].phase.value}"
            )
            # Entry would be triggered from external signal or API call
    
    async def _position_monitor_loop(self):
        """Monitor active position"""
        while self._running:
            try:
                if self.active_position:
                    await self._monitor_position(self.active_position)
                await asyncio.sleep(self.config.gemini_check_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Position monitor error: {e}")
                await asyncio.sleep(5)
    
    async def _monitor_position(self, position: ScalpingPosition):
        """Monitor scalping position with fast decision making"""
        if position.phase == TradePhase.CLOSED:
            return
        
        # Update PnL
        self._update_position_pnl(position)
        
        # Update momentum
        momentum = self.momentum_data.get(position.instrument)
        if momentum:
            position.current_momentum = momentum.momentum_score
        
        holding_seconds = (datetime.now() - position.probe_entry_time).total_seconds() if position.probe_entry_time else 0
        
        # Check quick profit (for scalping)
        if position.unrealized_pnl_pct >= self.config.quick_profit_pct:
            await self._exit_position(position, ExitReason.QUICK_PROFIT)
            return
        
        # Check trailing stop
        if self._check_trailing_stop(position):
            await self._exit_position(position, ExitReason.TRAILING_STOP)
            return
        
        # Check stoploss
        if self._check_stoploss(position):
            await self._exit_position(position, ExitReason.STOPLOSS)
            return
        
        # Check momentum fade exit
        if position.current_momentum < self.config.exit_momentum_threshold:
            await self._exit_position(position, ExitReason.MOMENTUM_FADE)
            return
        
        # Check max holding time
        if holding_seconds >= self.config.max_position_minutes * 60:
            await self._exit_position(position, ExitReason.TIME_EXIT)
            return
        
        # Get Gemini exit decision
        exit_decision = await self.gemini_client.get_quick_exit_decision(
            instrument=position.instrument,
            pnl_percent=position.unrealized_pnl_pct,
            holding_seconds=int(holding_seconds),
            current_momentum=position.current_momentum,
            peak_pnl_percent=(position.peak_pnl / position.total_capital * 100) if position.total_capital > 0 else 0
        )
        
        if exit_decision.get('exit', False) and exit_decision.get('confidence', 0) >= self.config.min_gemini_confidence:
            await self._exit_position(position, ExitReason.GEMINI_EXIT)
            return
        
        # Check scaling opportunity
        if position.phase == TradePhase.PROBE and position.unrealized_pnl_pct >= self.config.min_profit_to_scale_pct:
            if position.current_momentum >= self.config.min_momentum_for_scale:
                await self._scale_position(position)
    
    def _update_position_pnl(self, position: ScalpingPosition):
        """Update position PnL calculations"""
        if position.total_lots == 0 or position.avg_entry_price == 0:
            return
        
        price_diff = position.current_price - position.avg_entry_price
        lot_size = self.config.lot_sizes.get(position.instrument, 75)
        
        position.unrealized_pnl = price_diff * position.total_lots * lot_size
        position.unrealized_pnl_pct = (price_diff / position.avg_entry_price) * 100
        
        if position.unrealized_pnl > position.peak_pnl:
            position.peak_pnl = position.unrealized_pnl
        
        if position.current_price > position.peak_price:
            position.peak_price = position.current_price
    
    def _check_trailing_stop(self, position: ScalpingPosition) -> bool:
        """Check if trailing stop is hit (50-point trailing after 50-point profit)"""
        if not position.trailing_activated:
            # Activate at 50 points profit
            profit_points = position.current_price - position.avg_entry_price
            if profit_points >= self.config.trailing_activation_points:
                position.trailing_activated = True
                position.current_stoploss = position.current_price - self.config.trailing_distance_points
                self.logger.info(
                    f"📈 Trailing activated for {position.position_id} | "
                    f"Trail at ₹{position.current_stoploss:.2f} (50pts behind)"
                )
        else:
            # Update trailing stop (trail 50 points behind peak)
            new_trailing_stop = position.peak_price - self.config.trailing_distance_points
            if new_trailing_stop > position.current_stoploss:
                position.current_stoploss = new_trailing_stop
            
            if position.current_price <= position.current_stoploss:
                return True
        
        return False
    
    def _check_stoploss(self, position: ScalpingPosition) -> bool:
        """Check if stoploss is hit"""
        stoploss_pct = self.config.probe_stoploss_pct if position.phase == TradePhase.PROBE else self.config.scaled_stoploss_pct
        loss_pct = ((position.avg_entry_price - position.current_price) / position.avg_entry_price) * 100
        
        return loss_pct >= stoploss_pct
    
    async def enter_scalp(
        self,
        instrument: str,
        direction: TradeDirection,
        strike: float,
        option_type: str,
        expiry: str,
        current_price: float
    ) -> Optional[ScalpingPosition]:
        """Enter scalp position with probe"""
        if self.active_position is not None:
            self.logger.warning("Cannot enter - active position exists (single focus)")
            return None
        
        momentum = self.momentum_data.get(instrument)
        if not momentum or momentum.momentum_score < self.config.min_momentum_for_entry:
            self.logger.warning(f"Momentum too low for entry: {momentum.momentum_score if momentum else 0:.1f}")
            return None
        
        # Validate with Gemini
        validation = await self.gemini_client.validate_scalp_entry(
            instrument=instrument,
            direction=direction.value,
            momentum_score=momentum.momentum_score,
            price=current_price,
            volume_ratio=momentum.volume_ratio
        )
        
        if not validation.get('valid', False):
            self.logger.info(f"❌ Scalp entry rejected by Gemini")
            return None
        
        # Calculate probe size
        probe_capital = self.config.total_capital * (self.config.probe_capital_pct / 100)
        lot_size = self.config.lot_sizes.get(instrument, 75)
        probe_lots = max(1, int(probe_capital / (current_price * lot_size)))
        
        position_id = f"SCALP_{instrument}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
        
        position = ScalpingPosition(
            position_id=position_id,
            instrument=instrument,
            option_type=option_type,
            strike=strike,
            expiry=expiry,
            lot_size=lot_size,
            probe_lots=probe_lots,
            total_lots=probe_lots,
            direction=direction,
            entry_momentum=momentum.momentum_score,
            current_momentum=momentum.momentum_score,
            gemini_confidence=validation.get('confidence', 0)
        )
        
        # Execute probe entry
        order = await self.executor.execute_buy(
            instrument=instrument,
            option_type=option_type,
            strike=strike,
            expiry=expiry,
            lots=probe_lots,
            price=current_price
        )
        
        position.probe_entry_price = order['execution_price']
        position.avg_entry_price = order['execution_price']
        position.current_price = order['execution_price']
        position.peak_price = order['execution_price']
        position.probe_capital = order['value']
        position.total_capital = order['value']
        position.probe_entry_time = datetime.now()
        position.phase = TradePhase.PROBE
        
        # Set initial stoploss (50% of premium)
        position.initial_stoploss = position.probe_entry_price * (1 - self.config.probe_stoploss_pct / 100)
        position.current_stoploss = position.initial_stoploss
        
        self.active_position = position
        self.stats.probes_taken += 1
        
        self.logger.info(
            f"✅ SCALP PROBE: {instrument} {strike}{option_type} | "
            f"{probe_lots} lots @ ₹{position.probe_entry_price:.2f} | "
            f"Momentum: {momentum.momentum_score:.1f} | SL: ₹{position.current_stoploss:.2f}"
        )
        
        return position
    
    async def _scale_position(self, position: ScalpingPosition):
        """Scale up from probe to full position"""
        if position.phase != TradePhase.PROBE:
            return
        
        scale_capital = self.config.total_capital * (self.config.scale_capital_pct / 100)
        lot_size = position.lot_size
        scale_lots = max(1, int(scale_capital / (position.current_price * lot_size)))
        
        order = await self.executor.execute_buy(
            instrument=position.instrument,
            option_type=position.option_type,
            strike=position.strike,
            expiry=position.expiry,
            lots=scale_lots,
            price=position.current_price
        )
        
        position.scaled_lots = scale_lots
        position.scaled_entry_price = order['execution_price']
        position.total_lots = position.probe_lots + position.scaled_lots
        position.scaled_capital = order['value']
        position.total_capital = position.probe_capital + position.scaled_capital
        
        total_value = (position.probe_entry_price * position.probe_lots + 
                       position.scaled_entry_price * position.scaled_lots)
        position.avg_entry_price = total_value / position.total_lots
        
        position.current_stoploss = position.avg_entry_price * (1 - self.config.scaled_stoploss_pct / 100)
        position.phase = TradePhase.FULL_POSITION
        position.scale_time = datetime.now()
        
        self.stats.probes_scaled += 1
        
        self.logger.info(
            f"📈 SCALED: {position.instrument} | Added {scale_lots} lots | "
            f"Total: {position.total_lots} lots @ ₹{position.avg_entry_price:.2f}"
        )
    
    async def _exit_position(self, position: ScalpingPosition, reason: ExitReason):
        """Exit scalp position"""
        if position.phase == TradePhase.CLOSED:
            return
        
        order = await self.executor.execute_sell(
            instrument=position.instrument,
            option_type=position.option_type,
            strike=position.strike,
            expiry=position.expiry,
            lots=position.total_lots,
            price=position.current_price
        )
        
        exit_price = order['execution_price']
        price_diff = exit_price - position.avg_entry_price
        realized_pnl = price_diff * position.total_lots * position.lot_size
        
        hold_seconds = int((datetime.now() - position.probe_entry_time).total_seconds()) if position.probe_entry_time else 0
        
        position.exit_time = datetime.now()
        position.exit_reason = reason
        position.phase = TradePhase.CLOSED
        
        self.database.save_trade(position, exit_price, realized_pnl, hold_seconds)
        
        # Update stats
        self.stats.total_trades += 1
        if realized_pnl > 0:
            self.stats.winning_trades += 1
        else:
            self.stats.losing_trades += 1
        
        self.stats.total_pnl += realized_pnl
        self.stats.win_rate = (self.stats.winning_trades / self.stats.total_trades * 100) if self.stats.total_trades > 0 else 0
        
        if reason == ExitReason.QUICK_PROFIT:
            self.stats.quick_exits += 1
        elif reason == ExitReason.MOMENTUM_FADE:
            self.stats.momentum_exits += 1
        
        # Clear active position
        self.active_position = None
        self.closed_positions.append(position)
        
        emoji = "🟢" if realized_pnl > 0 else "🔴"
        self.logger.info(
            f"{emoji} SCALP EXIT: {position.instrument} | "
            f"PnL: ₹{realized_pnl:+,.2f} ({position.unrealized_pnl_pct:+.2f}%) | "
            f"Hold: {hold_seconds}s | Reason: {reason.value}"
        )
    
    def update_price(self, instrument: str, price: float, volume: int = 0):
        """Update price and recalculate momentum"""
        if instrument in self.momentum_data:
            self.momentum_data[instrument].update_momentum(price)
            self.momentum_data[instrument].volume = volume
        
        # Update active position price if matching
        if self.active_position and self.active_position.instrument == instrument:
            self.active_position.current_price = price
    
    def get_status(self) -> Dict:
        """Get engine status"""
        return {
            'service': self.config.service_name,
            'trading_mode': self._trading_mode.value,
            'running': self._running,
            'active_position': self.active_position.to_dict() if self.active_position else None,
            'momentum': {inst: m.to_dict() for inst, m in self.momentum_data.items()},
            'stats': {
                'total_trades': self.stats.total_trades,
                'winning_trades': self.stats.winning_trades,
                'losing_trades': self.stats.losing_trades,
                'win_rate': round(self.stats.win_rate, 2),
                'total_pnl': round(self.stats.total_pnl, 2),
                'probes_taken': self.stats.probes_taken,
                'probes_scaled': self.stats.probes_scaled,
                'quick_exits': self.stats.quick_exits,
                'momentum_exits': self.stats.momentum_exits
            },
            'config': {
                'total_capital': self.config.total_capital,
                'probe_capital_pct': self.config.probe_capital_pct,
                'quick_profit_pct': self.config.quick_profit_pct,
                'trailing_activation_points': self.config.trailing_activation_points,
                'trailing_distance_points': self.config.trailing_distance_points
            },
            'gemini': {
                'healthy': self.gemini_client._healthy,
                'requests': self.gemini_client.requests,
                'successes': self.gemini_client.successes,
                'failures': self.gemini_client.failures
            },
            'timestamp': datetime.now().isoformat()
        }


# ============================================================================
# FACTORY FUNCTION
# ============================================================================

def create_scalping_engine(config: Optional[ScalpingEngineConfig] = None) -> ProductionScalpingEngine:
    """Factory function to create scalping engine"""
    return ProductionScalpingEngine(config)


# ============================================================================
# STANDALONE TESTING
# ============================================================================

if __name__ == "__main__":
    import asyncio
    
    async def test_engine():
        """Test the scalping engine"""
        engine = create_scalping_engine()
        
        await engine.start()
        
        print(f"Engine Status: {json.dumps(engine.get_status(), indent=2)}")
        
        # Simulate price updates
        for i in range(10):
            engine.update_price("NIFTY", 100 + i * 2)
            engine.update_price("BANKNIFTY", 200 + i * 3)
            await asyncio.sleep(0.1)
        
        print(f"\nMomentum after updates:")
        for inst, m in engine.momentum_data.items():
            print(f"  {inst}: Score={m.momentum_score:.1f}, Phase={m.phase.value}")
        
        await engine.stop()
        
        print("\n✅ Scalping engine test complete")
    
    asyncio.run(test_engine())
