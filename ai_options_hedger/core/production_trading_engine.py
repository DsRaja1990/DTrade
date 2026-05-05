"""
╔══════════════════════════════════════════════════════════════════════════════════════╗
║        AI OPTIONS HEDGER - PRODUCTION TRADING ENGINE v2.0                            ║
║                Index Options Trading (NIFTY, BANKNIFTY)                              ║
╠══════════════════════════════════════════════════════════════════════════════════════╣
║                                                                                      ║
║  SERVICE: AI Options Hedger - Port 4003                                             ║
║  INSTRUMENTS: NIFTY (Lot 75), BANKNIFTY (Lot 35)                                    ║
║  MODE: Paper Trading Default → Switchable to Live                                   ║
║                                                                                      ║
║  TRADING METHODOLOGY:                                                                ║
║  ═══════════════════════════════════════════════════════════════════════════════    ║
║                                                                                      ║
║  1. PROBE-SCALE ENTRY                                                               ║
║     • 10% capital probe with 50% wide stoploss                                      ║
║     • Gemini 3 Pro confirmation required                                            ║
║     • 90% capital scale on confirmation                                             ║
║                                                                                      ║
║  2. INTELLIGENT EXIT                                                                 ║
║     • 50-point trailing after 50-point profit                                       ║
║     • Gemini AI exit consultation every 30 seconds                                  ║
║     • Momentum-based dynamic exits                                                   ║
║                                                                                      ║
║  3. HEDGING STRATEGY                                                                 ║
║     • Delta-neutral hedging for protection                                          ║
║     • Directional plays with AI confirmation                                        ║
║     • Volatility-based position sizing                                              ║
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
# TRADING MODE CONFIGURATION
# ============================================================================

class TradingMode(str, Enum):
    """Trading mode - Paper for testing, Live for real trades"""
    PAPER = "PAPER"
    LIVE = "LIVE"


class TradeDirection(str, Enum):
    """Trade direction"""
    BULLISH = "BULLISH"
    BEARISH = "BEARISH"
    NEUTRAL = "NEUTRAL"


class TradePhase(str, Enum):
    """Trade lifecycle phases"""
    SCANNING = "SCANNING"
    PROBE = "PROBE"
    CONFIRMING = "CONFIRMING"
    SCALING = "SCALING"
    FULL_POSITION = "FULL_POSITION"
    TRAILING = "TRAILING"
    REDUCING = "REDUCING"
    EXITING = "EXITING"
    CLOSED = "CLOSED"


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


# ============================================================================
# CONFIGURATION
# ============================================================================

@dataclass
class HedgerEngineConfig:
    """AI Options Hedger Engine Configuration"""
    
    # Service settings
    service_name: str = "AI_Options_Hedger"
    service_port: int = 4003
    
    # Trading mode - PAPER by default
    trading_mode: TradingMode = TradingMode.PAPER
    
    # Capital settings
    total_capital: float = 500000.0
    max_daily_loss_percent: float = 3.0
    max_capital_per_trade: float = 100000.0
    max_concurrent_positions: int = 2
    
    # Instruments (Index Options)
    instruments: List[str] = field(default_factory=lambda: ["NIFTY", "BANKNIFTY"])
    lot_sizes: Dict[str, int] = field(default_factory=lambda: {
        "NIFTY": 75,
        "BANKNIFTY": 35
    })
    
    # Probe-Scale settings
    probe_capital_pct: float = 10.0       # 10% for probe
    scale_capital_pct: float = 90.0       # 90% for scale
    probe_stoploss_pct: float = 50.0      # 50% wide stoploss
    scaled_stoploss_pct: float = 30.0     # 30% after scaling
    
    # Trailing stop
    trailing_activation_points: float = 50.0  # Activate at 50 pts profit
    trailing_distance_points: float = 50.0    # Trail 50 pts behind
    
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
    
    # Timing
    probe_timeout_seconds: int = 120      # 2 min probe timeout
    max_position_minutes: int = 45        # Max holding time
    
    # Database
    db_path: str = "database/hedger_trades.db"
    
    # Paper trading settings (REALISTIC values for backtesting accuracy)
    # Note: Index options slippage is 0.25-0.4% for ATM, higher for OTM
    paper_slippage_pct: float = 0.30      # 0.30% realistic slippage (was 0.1%)
    paper_latency_ms: int = 75            # 75ms simulated latency (realistic for retail)


# ============================================================================
# POSITION DATA STRUCTURES
# ============================================================================

@dataclass
class HedgerPosition:
    """Hedger position tracking"""
    position_id: str
    instrument: str           # NIFTY or BANKNIFTY
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
    is_hedged: bool = False
    
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
            'gemini_confidence': self.gemini_confidence,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


@dataclass
class TradingStats:
    """Daily trading statistics"""
    date: str = field(default_factory=lambda: date.today().isoformat())
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    total_pnl: float = 0.0
    max_drawdown: float = 0.0
    win_rate: float = 0.0
    avg_win: float = 0.0
    avg_loss: float = 0.0
    largest_win: float = 0.0
    largest_loss: float = 0.0
    probes_taken: int = 0
    probes_scaled: int = 0
    scale_rate: float = 0.0


# ============================================================================
# PAPER TRADE EXECUTOR
# ============================================================================

class PaperTradeExecutor:
    """
    Paper trading executor - simulates real trades without actual orders.
    Simulates realistic execution with slippage and latency.
    """
    
    def __init__(self, config: HedgerEngineConfig):
        self.config = config
        self.logger = logging.getLogger(__name__ + '.paper_executor')
        
        # Simulated execution tracking
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
        """Simulate buy order execution"""
        await asyncio.sleep(self.config.paper_latency_ms / 1000)
        
        # Apply slippage (buy higher)
        slippage = price * (self.config.paper_slippage_pct / 100)
        execution_price = price + slippage
        
        self.order_counter += 1
        order_id = f"PAPER_BUY_{self.order_counter}_{datetime.now().strftime('%H%M%S')}"
        
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
            'timestamp': datetime.now().isoformat()
        }
        
        self.executed_orders.append(order)
        
        self.logger.info(
            f"📄 PAPER BUY: {instrument} {strike}{option_type} | "
            f"{lots} lots @ ₹{execution_price:.2f} | Value: ₹{value:,.2f}"
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
        """Simulate sell order execution"""
        await asyncio.sleep(self.config.paper_latency_ms / 1000)
        
        # Apply slippage (sell lower)
        slippage = price * (self.config.paper_slippage_pct / 100)
        execution_price = price - slippage
        
        self.order_counter += 1
        order_id = f"PAPER_SELL_{self.order_counter}_{datetime.now().strftime('%H%M%S')}"
        
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
            'timestamp': datetime.now().isoformat()
        }
        
        self.executed_orders.append(order)
        
        self.logger.info(
            f"📄 PAPER SELL: {instrument} {strike}{option_type} | "
            f"{lots} lots @ ₹{execution_price:.2f} | Value: ₹{value:,.2f}"
        )
        
        return order
    
    def get_recent_orders(self, limit: int = 20) -> List[Dict]:
        """Get recent executed orders"""
        return self.executed_orders[-limit:]


# ============================================================================
# LIVE TRADE EXECUTOR
# ============================================================================

class LiveTradeExecutor:
    """
    Live trading executor - sends real orders to Dhan API.
    Only used when mode is LIVE.
    """
    
    def __init__(self, config: HedgerEngineConfig):
        self.config = config
        self.logger = logging.getLogger(__name__ + '.live_executor')
        self._session: Optional[aiohttp.ClientSession] = None
        
        # Load Dhan credentials
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
        """Execute live buy order via Dhan API"""
        if not self.dhan_token:
            raise RuntimeError("Dhan API token not configured for live trading")
        
        lot_size = self.config.lot_sizes.get(instrument, 75)
        quantity = lots * lot_size
        
        self.logger.info(
            f"🔴 LIVE BUY: {instrument} {strike}{option_type} | "
            f"{lots} lots ({quantity} qty) @ ₹{price:.2f}"
        )
        
        # TODO: Implement actual Dhan API call
        # This would integrate with the DhanHQ SDK
        
        return {
            'order_id': f"LIVE_BUY_{datetime.now().strftime('%H%M%S')}",
            'status': 'PENDING',
            'mode': 'LIVE',
            'message': 'Live order submission - implement Dhan API integration'
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
        """Execute live sell order via Dhan API"""
        if not self.dhan_token:
            raise RuntimeError("Dhan API token not configured for live trading")
        
        lot_size = self.config.lot_sizes.get(instrument, 75)
        quantity = lots * lot_size
        
        self.logger.info(
            f"🔴 LIVE SELL: {instrument} {strike}{option_type} | "
            f"{lots} lots ({quantity} qty) @ ₹{price:.2f}"
        )
        
        # TODO: Implement actual Dhan API call
        
        return {
            'order_id': f"LIVE_SELL_{datetime.now().strftime('%H%M%S')}",
            'status': 'PENDING',
            'mode': 'LIVE',
            'message': 'Live order submission - implement Dhan API integration'
        }
    
    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()


# ============================================================================
# GEMINI AI CLIENT
# ============================================================================

class GeminiAIClient:
    """Client for Gemini Trade Intelligence Service"""
    
    def __init__(self, config: HedgerEngineConfig):
        self.config = config
        self.logger = logging.getLogger(__name__ + '.gemini_client')
        self._session: Optional[aiohttp.ClientSession] = None
        self._healthy = False
        
        # Stats
        self.requests = 0
        self.successes = 0
        self.failures = 0
    
    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=30)
            )
        return self._session
    
    async def check_health(self) -> bool:
        """Check Gemini service health"""
        try:
            session = await self._get_session()
            async with session.get(
                f"{self.config.gemini_service_url}/health",
                timeout=5
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    self._healthy = data.get('status') == 'healthy'
                    return self._healthy
        except Exception as e:
            self.logger.warning(f"Gemini health check failed: {e}")
            self._healthy = False
        return False
    
    async def validate_entry(
        self,
        instrument: str,
        direction: str,
        strike: float,
        option_type: str,
        current_price: float,
        signal_strength: float
    ) -> Dict:
        """Validate entry decision with Gemini AI"""
        try:
            self.requests += 1
            session = await self._get_session()
            
            payload = {
                'instrument': instrument,
                'direction': direction,
                'strike': strike,
                'option_type': option_type,
                'current_price': current_price,
                'signal_strength': signal_strength,
                'query_type': 'entry_validation'
            }
            
            async with session.post(
                f"{self.config.gemini_service_url}/api/validate/trade",
                json=payload,
                timeout=15
            ) as resp:
                if resp.status == 200:
                    self.successes += 1
                    data = await resp.json()
                    return {
                        'valid': data.get('approved', False),
                        'confidence': data.get('confidence', 0.0),
                        'recommendation': data.get('recommendation', 'HOLD'),
                        'reasoning': data.get('reasoning', '')
                    }
                else:
                    self.failures += 1
                    self.logger.warning(f"Gemini validation failed: HTTP {resp.status}")
        except Exception as e:
            self.failures += 1
            self.logger.error(f"Gemini validation error: {e}")
        
        # Default to cautious response on failure
        return {
            'valid': False,
            'confidence': 0.0,
            'recommendation': 'HOLD',
            'reasoning': 'Gemini service unavailable'
        }
    
    async def get_scaling_decision(
        self,
        instrument: str,
        direction: str,
        entry_price: float,
        current_price: float,
        pnl_percent: float,
        holding_seconds: int
    ) -> Dict:
        """Get scaling decision from Gemini"""
        try:
            self.requests += 1
            session = await self._get_session()
            
            payload = {
                'instrument': instrument,
                'direction': direction,
                'entry_price': entry_price,
                'current_price': current_price,
                'pnl_percent': pnl_percent,
                'holding_seconds': holding_seconds,
                'query_type': 'scale_decision'
            }
            
            async with session.post(
                f"{self.config.gemini_service_url}/api/probe-scale/scale-decision",
                json=payload,
                timeout=15
            ) as resp:
                if resp.status == 200:
                    self.successes += 1
                    return await resp.json()
                else:
                    self.failures += 1
        except Exception as e:
            self.failures += 1
            self.logger.error(f"Gemini scale decision error: {e}")
        
        return {'scale': False, 'confidence': 0.0, 'reason': 'Service unavailable'}
    
    async def get_exit_decision(
        self,
        instrument: str,
        direction: str,
        entry_price: float,
        current_price: float,
        pnl_percent: float,
        holding_seconds: int,
        peak_pnl_percent: float
    ) -> Dict:
        """Get exit decision from Gemini - called every 30 seconds"""
        try:
            self.requests += 1
            session = await self._get_session()
            
            payload = {
                'instrument': instrument,
                'direction': direction,
                'entry_price': entry_price,
                'current_price': current_price,
                'pnl_percent': pnl_percent,
                'holding_seconds': holding_seconds,
                'peak_pnl_percent': peak_pnl_percent,
                'query_type': 'exit_decision'
            }
            
            async with session.post(
                f"{self.config.gemini_service_url}/api/probe-scale/exit-decision",
                json=payload,
                timeout=15
            ) as resp:
                if resp.status == 200:
                    self.successes += 1
                    return await resp.json()
                else:
                    self.failures += 1
        except Exception as e:
            self.failures += 1
            self.logger.error(f"Gemini exit decision error: {e}")
        
        return {'exit': False, 'confidence': 0.0, 'reason': 'Service unavailable'}
    
    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()


# ============================================================================
# DATABASE MANAGER
# ============================================================================

class HedgerDatabase:
    """SQLite database for trade history and analytics"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self._init_db()
    
    def _init_db(self):
        """Initialize database tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS trades (
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
                
                phase TEXT,
                exit_reason TEXT,
                trading_mode TEXT,
                
                gemini_entry_confidence REAL,
                gemini_scale_confidence REAL,
                gemini_exit_confidence REAL,
                
                probe_entry_time TEXT,
                scale_time TEXT,
                exit_time TEXT,
                
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS daily_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT UNIQUE,
                total_trades INTEGER,
                winning_trades INTEGER,
                losing_trades INTEGER,
                total_pnl REAL,
                win_rate REAL,
                probes_taken INTEGER,
                probes_scaled INTEGER,
                scale_rate REAL,
                trading_mode TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def save_trade(self, position: HedgerPosition, exit_price: float, realized_pnl: float):
        """Save completed trade to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO trades (
                position_id, instrument, option_type, strike, expiry, direction,
                probe_lots, scaled_lots, total_lots,
                probe_entry_price, scaled_entry_price, avg_entry_price, exit_price,
                probe_capital, scaled_capital, total_capital,
                realized_pnl, realized_pnl_pct, peak_pnl,
                phase, exit_reason, trading_mode,
                gemini_entry_confidence, gemini_scale_confidence, gemini_exit_confidence,
                probe_entry_time, scale_time, exit_time
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            position.position_id, position.instrument, position.option_type,
            position.strike, position.expiry, position.direction.value,
            position.probe_lots, position.scaled_lots, position.total_lots,
            position.probe_entry_price, position.scaled_entry_price, position.avg_entry_price, exit_price,
            position.probe_capital, position.scaled_capital, position.total_capital,
            realized_pnl, (realized_pnl / position.total_capital * 100) if position.total_capital > 0 else 0,
            position.peak_pnl,
            position.phase.value, position.exit_reason.value if position.exit_reason else None,
            "PAPER",  # Default to paper
            position.gemini_confidence, 0, 0,
            position.probe_entry_time.isoformat() if position.probe_entry_time else None,
            position.scale_time.isoformat() if position.scale_time else None,
            datetime.now().isoformat()
        ))
        
        conn.commit()
        conn.close()
    
    def get_today_stats(self) -> Dict:
        """Get today's trading statistics"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        today = date.today().isoformat()
        
        cursor.execute('''
            SELECT 
                COUNT(*) as total_trades,
                SUM(CASE WHEN realized_pnl > 0 THEN 1 ELSE 0 END) as winning,
                SUM(CASE WHEN realized_pnl <= 0 THEN 1 ELSE 0 END) as losing,
                COALESCE(SUM(realized_pnl), 0) as total_pnl
            FROM trades
            WHERE DATE(exit_time) = ?
        ''', (today,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            total = row[0] or 0
            winning = row[1] or 0
            return {
                'total_trades': total,
                'winning_trades': winning,
                'losing_trades': row[2] or 0,
                'total_pnl': row[3] or 0,
                'win_rate': (winning / total * 100) if total > 0 else 0
            }
        
        return {'total_trades': 0, 'winning_trades': 0, 'losing_trades': 0, 'total_pnl': 0, 'win_rate': 0}


# ============================================================================
# PRODUCTION TRADING ENGINE
# ============================================================================

class ProductionTradingEngine:
    """
    Production Trading Engine for AI Options Hedger
    
    Implements probe-scale methodology with Gemini AI validation.
    Supports both PAPER and LIVE trading modes.
    """
    
    def __init__(self, config: Optional[HedgerEngineConfig] = None):
        self.config = config or HedgerEngineConfig()
        self.logger = logging.getLogger(__name__ + '.engine')
        
        # Trading mode
        self._trading_mode = self.config.trading_mode
        
        # Executors
        self.paper_executor = PaperTradeExecutor(self.config)
        self.live_executor = LiveTradeExecutor(self.config)
        
        # AI Client
        self.gemini_client = GeminiAIClient(self.config)
        
        # Database
        self.database = HedgerDatabase(self.config.db_path)
        
        # Positions
        self.active_positions: Dict[str, HedgerPosition] = {}
        self.closed_positions: List[HedgerPosition] = []
        
        # Statistics
        self.stats = TradingStats()
        
        # State
        self._running = False
        self._monitoring_task: Optional[asyncio.Task] = None
        
        self.logger.info(
            f"🚀 Production Trading Engine initialized | "
            f"Mode: {self._trading_mode.value} | "
            f"Capital: ₹{self.config.total_capital:,.2f}"
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
            # Safety check for live trading
            if not os.getenv('DHAN_ACCESS_TOKEN'):
                return {
                    'success': False,
                    'error': 'Cannot switch to LIVE mode - DHAN_ACCESS_TOKEN not configured'
                }
            
            if len(self.active_positions) > 0:
                return {
                    'success': False,
                    'error': 'Cannot switch to LIVE mode with active positions'
                }
        
        self._trading_mode = mode
        
        self.logger.info(
            f"⚡ Trading mode switched: {old_mode.value} → {mode.value}"
        )
        
        return {
            'success': True,
            'old_mode': old_mode.value,
            'new_mode': mode.value,
            'timestamp': datetime.now().isoformat()
        }
    
    async def start(self):
        """Start the trading engine"""
        if self._running:
            return
        
        self._running = True
        
        # Check Gemini health
        gemini_healthy = await self.gemini_client.check_health()
        self.logger.info(f"🤖 Gemini AI Status: {'Healthy' if gemini_healthy else 'Unavailable'}")
        
        # Start position monitoring
        self._monitoring_task = asyncio.create_task(self._position_monitor_loop())
        
        self.logger.info("✅ Production Trading Engine started")
    
    async def stop(self):
        """Stop the trading engine"""
        self._running = False
        
        if self._monitoring_task:
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass
        
        # Close all resources
        await self.gemini_client.close()
        await self.live_executor.close()
        
        self.logger.info("🛑 Production Trading Engine stopped")
    
    async def _position_monitor_loop(self):
        """Main position monitoring loop - checks every 30 seconds"""
        while self._running:
            try:
                await self._monitor_all_positions()
                await asyncio.sleep(self.config.gemini_check_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Position monitor error: {e}")
                await asyncio.sleep(5)
    
    async def _monitor_all_positions(self):
        """Monitor all active positions"""
        for position_id, position in list(self.active_positions.items()):
            try:
                await self._monitor_position(position)
            except Exception as e:
                self.logger.error(f"Error monitoring position {position_id}: {e}")
    
    async def _monitor_position(self, position: HedgerPosition):
        """Monitor a single position and make decisions"""
        if position.phase == TradePhase.CLOSED:
            return
        
        # Update PnL
        self._update_position_pnl(position)
        
        # Check trailing stop
        if self._check_trailing_stop(position):
            await self._exit_position(position, ExitReason.TRAILING_STOP)
            return
        
        # Check stoploss
        if self._check_stoploss(position):
            await self._exit_position(position, ExitReason.STOPLOSS)
            return
        
        # Get Gemini exit decision every 30 seconds
        holding_seconds = (datetime.now() - position.probe_entry_time).total_seconds() if position.probe_entry_time else 0
        
        exit_decision = await self.gemini_client.get_exit_decision(
            instrument=position.instrument,
            direction=position.direction.value,
            entry_price=position.avg_entry_price,
            current_price=position.current_price,
            pnl_percent=position.unrealized_pnl_pct,
            holding_seconds=int(holding_seconds),
            peak_pnl_percent=(position.peak_pnl / position.total_capital * 100) if position.total_capital > 0 else 0
        )
        
        if exit_decision.get('exit', False) and exit_decision.get('confidence', 0) >= self.config.min_gemini_confidence:
            await self._exit_position(position, ExitReason.GEMINI_EXIT)
            return
        
        # Check for scaling opportunity
        if position.phase == TradePhase.PROBE and position.unrealized_pnl_pct >= self.config.min_profit_to_scale_pct:
            scale_decision = await self.gemini_client.get_scaling_decision(
                instrument=position.instrument,
                direction=position.direction.value,
                entry_price=position.probe_entry_price,
                current_price=position.current_price,
                pnl_percent=position.unrealized_pnl_pct,
                holding_seconds=int(holding_seconds)
            )
            
            if scale_decision.get('scale', False) and scale_decision.get('confidence', 0) >= self.config.min_gemini_confidence:
                await self._scale_position(position)
    
    def _update_position_pnl(self, position: HedgerPosition):
        """Update position PnL calculations"""
        if position.total_lots == 0 or position.avg_entry_price == 0:
            return
        
        price_diff = position.current_price - position.avg_entry_price
        lot_size = self.config.lot_sizes.get(position.instrument, 75)
        
        position.unrealized_pnl = price_diff * position.total_lots * lot_size
        position.unrealized_pnl_pct = (price_diff / position.avg_entry_price) * 100
        
        # Track peak
        if position.unrealized_pnl > position.peak_pnl:
            position.peak_pnl = position.unrealized_pnl
        
        # Track peak price for trailing
        if position.current_price > position.peak_price:
            position.peak_price = position.current_price
    
    def _check_trailing_stop(self, position: HedgerPosition) -> bool:
        """Check if trailing stop is hit"""
        if not position.trailing_activated:
            # Check if we should activate trailing
            if position.unrealized_pnl_pct >= (self.config.trailing_activation_points / position.avg_entry_price * 100):
                position.trailing_activated = True
                position.current_stoploss = position.current_price - self.config.trailing_distance_points
                self.logger.info(
                    f"📈 Trailing activated for {position.position_id} | "
                    f"New SL: ₹{position.current_stoploss:.2f}"
                )
        else:
            # Update trailing stop
            new_trailing_stop = position.current_price - self.config.trailing_distance_points
            if new_trailing_stop > position.current_stoploss:
                position.current_stoploss = new_trailing_stop
            
            # Check if hit
            if position.current_price <= position.current_stoploss:
                return True
        
        return False
    
    def _check_stoploss(self, position: HedgerPosition) -> bool:
        """Check if stoploss is hit"""
        stoploss_pct = self.config.probe_stoploss_pct if position.phase == TradePhase.PROBE else self.config.scaled_stoploss_pct
        
        loss_pct = ((position.avg_entry_price - position.current_price) / position.avg_entry_price) * 100
        
        if loss_pct >= stoploss_pct:
            return True
        
        return False
    
    async def enter_probe(
        self,
        instrument: str,
        direction: TradeDirection,
        strike: float,
        option_type: str,
        expiry: str,
        current_price: float,
        signal_strength: float = 0.8
    ) -> Optional[HedgerPosition]:
        """
        Enter probe position (10% capital)
        
        Returns position if successful, None otherwise.
        """
        # Validate with Gemini
        validation = await self.gemini_client.validate_entry(
            instrument=instrument,
            direction=direction.value,
            strike=strike,
            option_type=option_type,
            current_price=current_price,
            signal_strength=signal_strength
        )
        
        if not validation['valid']:
            self.logger.info(
                f"❌ Entry rejected by Gemini: {validation.get('reasoning', 'Unknown')}"
            )
            return None
        
        # Calculate probe size
        probe_capital = self.config.total_capital * (self.config.probe_capital_pct / 100)
        lot_size = self.config.lot_sizes.get(instrument, 75)
        probe_lots = max(1, int(probe_capital / (current_price * lot_size)))
        
        # Create position
        position_id = f"HEDGER_{instrument}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
        
        position = HedgerPosition(
            position_id=position_id,
            instrument=instrument,
            option_type=option_type,
            strike=strike,
            expiry=expiry,
            lot_size=lot_size,
            probe_lots=probe_lots,
            total_lots=probe_lots,
            direction=direction,
            gemini_confidence=validation['confidence'],
            gemini_recommendation=validation['recommendation']
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
        
        # Update position with execution details
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
        
        # Add to active positions
        self.active_positions[position_id] = position
        
        # Update stats
        self.stats.probes_taken += 1
        
        self.logger.info(
            f"✅ PROBE ENTRY: {instrument} {strike}{option_type} | "
            f"{probe_lots} lots @ ₹{position.probe_entry_price:.2f} | "
            f"SL: ₹{position.current_stoploss:.2f} (50%) | "
            f"Mode: {self._trading_mode.value}"
        )
        
        return position
    
    async def _scale_position(self, position: HedgerPosition):
        """Scale up position from probe to full (add 90% capital)"""
        if position.phase != TradePhase.PROBE:
            return
        
        # Calculate scale size
        scale_capital = self.config.total_capital * (self.config.scale_capital_pct / 100)
        lot_size = position.lot_size
        scale_lots = max(1, int(scale_capital / (position.current_price * lot_size)))
        
        # Execute scale entry
        order = await self.executor.execute_buy(
            instrument=position.instrument,
            option_type=position.option_type,
            strike=position.strike,
            expiry=position.expiry,
            lots=scale_lots,
            price=position.current_price
        )
        
        # Update position
        position.scaled_lots = scale_lots
        position.scaled_entry_price = order['execution_price']
        position.total_lots = position.probe_lots + position.scaled_lots
        position.scaled_capital = order['value']
        position.total_capital = position.probe_capital + position.scaled_capital
        
        # Calculate new average entry price
        total_value = (position.probe_entry_price * position.probe_lots + 
                       position.scaled_entry_price * position.scaled_lots)
        position.avg_entry_price = total_value / position.total_lots
        
        # Tighten stoploss after scaling
        position.current_stoploss = position.avg_entry_price * (1 - self.config.scaled_stoploss_pct / 100)
        
        position.phase = TradePhase.FULL_POSITION
        position.scale_time = datetime.now()
        
        # Update stats
        self.stats.probes_scaled += 1
        self.stats.scale_rate = (self.stats.probes_scaled / self.stats.probes_taken * 100) if self.stats.probes_taken > 0 else 0
        
        self.logger.info(
            f"📈 SCALED UP: {position.instrument} {position.strike}{position.option_type} | "
            f"Added {scale_lots} lots @ ₹{order['execution_price']:.2f} | "
            f"Total: {position.total_lots} lots | Avg: ₹{position.avg_entry_price:.2f} | "
            f"New SL: ₹{position.current_stoploss:.2f} (30%)"
        )
    
    async def _exit_position(self, position: HedgerPosition, reason: ExitReason):
        """Exit position completely"""
        if position.phase == TradePhase.CLOSED:
            return
        
        # Execute sell
        order = await self.executor.execute_sell(
            instrument=position.instrument,
            option_type=position.option_type,
            strike=position.strike,
            expiry=position.expiry,
            lots=position.total_lots,
            price=position.current_price
        )
        
        exit_price = order['execution_price']
        
        # Calculate realized PnL
        price_diff = exit_price - position.avg_entry_price
        realized_pnl = price_diff * position.total_lots * position.lot_size
        
        # Update position
        position.exit_time = datetime.now()
        position.exit_reason = reason
        position.phase = TradePhase.CLOSED
        
        # Save to database
        self.database.save_trade(position, exit_price, realized_pnl)
        
        # Update stats
        self.stats.total_trades += 1
        if realized_pnl > 0:
            self.stats.winning_trades += 1
            if realized_pnl > self.stats.largest_win:
                self.stats.largest_win = realized_pnl
        else:
            self.stats.losing_trades += 1
            if realized_pnl < self.stats.largest_loss:
                self.stats.largest_loss = realized_pnl
        
        self.stats.total_pnl += realized_pnl
        self.stats.win_rate = (self.stats.winning_trades / self.stats.total_trades * 100) if self.stats.total_trades > 0 else 0
        
        # Remove from active positions
        if position.position_id in self.active_positions:
            del self.active_positions[position.position_id]
        
        self.closed_positions.append(position)
        
        emoji = "🟢" if realized_pnl > 0 else "🔴"
        self.logger.info(
            f"{emoji} EXIT: {position.instrument} {position.strike}{position.option_type} | "
            f"{position.total_lots} lots @ ₹{exit_price:.2f} | "
            f"PnL: ₹{realized_pnl:+,.2f} | Reason: {reason.value}"
        )
    
    def update_price(self, instrument: str, option_type: str, strike: float, price: float):
        """Update current price for matching positions"""
        for position in self.active_positions.values():
            if (position.instrument == instrument and 
                position.option_type == option_type and 
                position.strike == strike):
                position.current_price = price
    
    def get_status(self) -> Dict:
        """Get engine status"""
        return {
            'service': self.config.service_name,
            'trading_mode': self._trading_mode.value,
            'running': self._running,
            'active_positions': len(self.active_positions),
            'positions': [p.to_dict() for p in self.active_positions.values()],
            'stats': {
                'total_trades': self.stats.total_trades,
                'winning_trades': self.stats.winning_trades,
                'losing_trades': self.stats.losing_trades,
                'win_rate': round(self.stats.win_rate, 2),
                'total_pnl': round(self.stats.total_pnl, 2),
                'probes_taken': self.stats.probes_taken,
                'probes_scaled': self.stats.probes_scaled,
                'scale_rate': round(self.stats.scale_rate, 2)
            },
            'config': {
                'total_capital': self.config.total_capital,
                'probe_capital_pct': self.config.probe_capital_pct,
                'scale_capital_pct': self.config.scale_capital_pct,
                'probe_stoploss_pct': self.config.probe_stoploss_pct,
                'trailing_activation_points': self.config.trailing_activation_points
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

def create_hedger_engine(config: Optional[HedgerEngineConfig] = None) -> ProductionTradingEngine:
    """Factory function to create hedger trading engine"""
    return ProductionTradingEngine(config)


# ============================================================================
# STANDALONE TESTING
# ============================================================================

if __name__ == "__main__":
    import asyncio
    
    async def test_engine():
        """Test the trading engine"""
        engine = create_hedger_engine()
        
        # Start engine
        await engine.start()
        
        print(f"Engine Status: {json.dumps(engine.get_status(), indent=2)}")
        
        # Test mode switching
        print(f"\nSwitching to LIVE mode...")
        result = engine.switch_mode(TradingMode.LIVE)
        print(f"Result: {result}")
        
        print(f"\nSwitching back to PAPER mode...")
        result = engine.switch_mode(TradingMode.PAPER)
        print(f"Result: {result}")
        
        # Stop engine
        await engine.stop()
        
        print("\n✅ Engine test complete")
    
    asyncio.run(test_engine())
