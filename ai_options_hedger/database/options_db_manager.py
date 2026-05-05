#!/usr/bin/env python3
"""
SQLite Database Manager for AI Options Hedger Service
======================================================

Stores comprehensive options trading data for analysis and service enhancement:
1. Options Signals - All signals generated with full context
2. Options Trades - Every trade with entry/exit details (CALL/PUT)
3. Position Tracking - Open positions with Greeks and hedges
4. Performance Metrics - Win/loss tracking, P&L history
5. Market Context - VIX, IV, sector data at signal time
6. AI Analysis - Gemini 3-tier responses for model improvement
7. Stacking Events - Decision engine events and outcomes
8. Error Logs - For debugging and reliability improvement

Author: DTrade Systems
Version: 1.0.0 - Options Specific
"""

import sqlite3
import json
import logging
from datetime import datetime, date
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict, field
from contextlib import contextmanager
from enum import Enum
import threading

logger = logging.getLogger(__name__)


# ============================================================================
# ENUMS FOR TYPE SAFETY
# ============================================================================

class OptionType(Enum):
    CALL = "CALL"
    PUT = "PUT"


class SignalType(Enum):
    STRONG_BULLISH = "STRONG_BULLISH"
    BULLISH = "BULLISH"
    WEAK_BULLISH = "WEAK_BULLISH"
    NEUTRAL = "NEUTRAL"
    WEAK_BEARISH = "WEAK_BEARISH"
    BEARISH = "BEARISH"
    STRONG_BEARISH = "STRONG_BEARISH"


class TradeStatus(Enum):
    PENDING = "PENDING"
    EXECUTED = "EXECUTED"
    PARTIAL = "PARTIAL"
    CLOSED = "CLOSED"
    CANCELLED = "CANCELLED"
    FAILED = "FAILED"
    HEDGED = "HEDGED"


class TradeOutcome(Enum):
    WIN = "WIN"
    LOSS = "LOSS"
    BREAKEVEN = "BREAKEVEN"
    OPEN = "OPEN"


class StackingDecision(Enum):
    STACK = "STACK"
    HOLD = "HOLD"
    EXIT = "EXIT"
    HEDGE = "HEDGE"
    REDUCE = "REDUCE"


class MarketRegime(Enum):
    TRENDING_UP = "TRENDING_UP"
    TRENDING_DOWN = "TRENDING_DOWN"
    RANGE_BOUND = "RANGE_BOUND"
    HIGH_VOLATILITY = "HIGH_VOLATILITY"
    LOW_VOLATILITY = "LOW_VOLATILITY"
    VOLATILE = "VOLATILE"
    NEUTRAL = "NEUTRAL"


# ============================================================================
# DATA CLASSES FOR OPTIONS TRADING
# ============================================================================

@dataclass
class OptionsSignalRecord:
    """Complete options signal record for storage"""
    # Identification
    signal_id: str  # Unique ID: {index}_{strike}_{option_type}_{timestamp}
    index_symbol: str  # NIFTY or BANKNIFTY
    strike_price: float
    option_type: str  # CALL or PUT
    expiry_date: date
    
    # Timing
    signal_time: datetime
    market_session: str  # "OPENING", "MID_SESSION", "CLOSING", "EXPIRY_DAY"
    days_to_expiry: int
    
    # Underlying Price Data
    index_price: float
    index_change_pct: float
    index_high: float
    index_low: float
    
    # Option Price Data
    option_price: float
    option_bid: float
    option_ask: float
    bid_ask_spread_pct: float
    
    # Greeks
    delta: float
    gamma: float
    theta: float
    vega: float
    iv: float  # Implied Volatility
    
    # Technical Analysis
    supertrend_signal: str
    supertrend_value: float
    vwap: float
    vwap_position: str
    rsi: float
    macd_signal: str
    
    # Volume & OI Analysis
    option_volume: int
    option_oi: int
    oi_change: int
    oi_change_pct: float
    volume_oi_ratio: float
    pcr: float  # Put-Call Ratio
    
    # Signals
    buy_signals: List[str] = field(default_factory=list)
    sell_signals: List[str] = field(default_factory=list)
    signal_type: str = "NEUTRAL"
    signal_strength: float = 0.0
    
    # AI Analysis (3-Tier Gemini)
    tier1_response: Optional[str] = None
    tier1_confidence: float = 0.0
    tier2_response: Optional[str] = None
    tier2_confidence: float = 0.0
    tier3_response: Optional[str] = None
    tier3_confidence: float = 0.0
    final_ai_direction: str = "NEUTRAL"
    final_ai_confidence: float = 0.0
    ai_reasoning: str = ""
    
    # Ultra AI Validation
    ultra_validator_score: float = 0.0
    neural_ensemble_score: float = 0.0
    quantum_filter_passed: bool = False
    
    # Multi-Factor Scores
    technical_score: float = 0.0
    ai_score: float = 0.0
    market_structure_score: float = 0.0
    volume_score: float = 0.0
    greeks_score: float = 0.0
    combined_score: float = 0.0
    signal_quality: str = "REJECT"
    
    # Market Context
    market_regime: str = "NEUTRAL"
    india_vix: float = 15.0
    vix_change_pct: float = 0.0
    max_pain: float = 0.0
    
    # Outcome Tracking
    was_traded: bool = False
    trade_id: Optional[str] = None
    actual_outcome: Optional[str] = None
    actual_move_pct: Optional[float] = None
    time_to_target_mins: Optional[int] = None


@dataclass
class OptionsTradeRecord:
    """Complete options trade execution record"""
    # Identification
    trade_id: str
    signal_id: str
    index_symbol: str  # NIFTY or BANKNIFTY
    strike_price: float
    option_type: str  # CALL or PUT
    expiry_date: date
    
    # Timing
    entry_time: datetime
    exit_time: Optional[datetime] = None
    hold_duration_mins: Optional[int] = None
    days_to_expiry_at_entry: int = 0
    
    # Trade Details
    entry_price: float = 0.0
    exit_price: Optional[float] = None
    stop_loss: float = 0.0
    target: float = 0.0
    trailing_stop: float = 0.0
    
    # Greeks at Entry
    entry_delta: float = 0.0
    entry_gamma: float = 0.0
    entry_theta: float = 0.0
    entry_vega: float = 0.0
    entry_iv: float = 0.0
    
    # Position Sizing
    quantity: int = 0
    lot_size: int = 75  # NIFTY=75, BANKNIFTY=35, FINNIFTY=65, SENSEX=20
    lots_traded: int = 1
    capital_used: float = 0.0
    margin_required: float = 0.0
    
    # Execution
    order_id: str = ""
    execution_mode: str = "PAPER"  # "PAPER" or "LIVE"
    status: str = "PENDING"
    
    # Stacking Info
    is_stacked: bool = False
    stacking_level: int = 0  # 0 = base, 1+ = stacked positions
    parent_trade_id: Optional[str] = None
    
    # Hedging Info
    is_hedged: bool = False
    hedge_trade_id: Optional[str] = None
    hedge_ratio: float = 0.0
    
    # P&L
    pnl: float = 0.0
    pnl_pct: float = 0.0
    pnl_points: float = 0.0
    max_profit: float = 0.0
    max_drawdown: float = 0.0
    
    # Exit Details
    exit_reason: Optional[str] = None
    outcome: str = "OPEN"
    
    # Risk Metrics
    risk_reward_planned: float = 0.0
    risk_reward_actual: Optional[float] = None
    
    # Market Context at Entry
    entry_index_price: float = 0.0
    entry_market_regime: str = "NEUTRAL"
    entry_vix: float = 15.0
    
    # Scores at Entry
    entry_combined_score: float = 0.0
    entry_ai_confidence: float = 0.0
    entry_ultra_validator_score: float = 0.0


@dataclass
class StackingEventRecord:
    """Record for stacking decision events"""
    event_id: str
    trade_id: str
    event_time: datetime
    
    # Decision
    decision: str  # STACK, HOLD, EXIT, HEDGE, REDUCE
    decision_confidence: float
    decision_reasoning: str
    
    # Position State Before
    positions_before: int
    total_exposure_before: float
    unrealized_pnl_before: float
    
    # Position State After
    positions_after: int
    total_exposure_after: float
    
    # Market Context
    index_price: float
    vix: float
    market_regime: str
    
    # AI Scores
    ai_stack_score: float
    neural_ensemble_score: float
    risk_score: float


@dataclass
class DailyOptionsPerformance:
    """Daily options trading performance summary"""
    date: date
    
    # Trade Counts
    total_trades: int = 0
    call_trades: int = 0
    put_trades: int = 0
    wins: int = 0
    losses: int = 0
    breakeven: int = 0
    
    # Win Rates
    overall_win_rate: float = 0.0
    call_win_rate: float = 0.0
    put_win_rate: float = 0.0
    
    # P&L
    gross_profit: float = 0.0
    gross_loss: float = 0.0
    net_pnl: float = 0.0
    net_points: float = 0.0
    profit_factor: float = 0.0
    
    # Trade Metrics
    avg_win: float = 0.0
    avg_loss: float = 0.0
    largest_win: float = 0.0
    largest_loss: float = 0.0
    avg_hold_time_mins: float = 0.0
    
    # Stacking Performance
    stacking_events: int = 0
    successful_stacks: int = 0
    stacking_win_rate: float = 0.0
    
    # Hedging Performance
    hedges_placed: int = 0
    hedge_effectiveness: float = 0.0
    
    # Market Context
    market_regime: str = "NEUTRAL"
    avg_vix: float = 15.0
    nifty_change_pct: float = 0.0
    
    # AI Performance
    ai_accuracy: float = 0.0
    ultra_validator_accuracy: float = 0.0
    signals_generated: int = 0
    signals_traded: int = 0


# ============================================================================
# OPTIONS DATABASE MANAGER
# ============================================================================

class OptionsDatabase:
    """
    SQLite database manager for options trading data storage and retrieval.
    Thread-safe with connection pooling.
    """
    
    def __init__(self, db_path: str = "data/options_trading.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._local = threading.local()
        self._lock = threading.Lock()
        
        # Initialize database
        self._init_database()
        
        logger.info(f"Options trading database initialized at {self.db_path}")
    
    @property
    def connection(self) -> sqlite3.Connection:
        """Get thread-local database connection"""
        if not hasattr(self._local, 'connection') or self._local.connection is None:
            self._local.connection = sqlite3.connect(
                str(self.db_path),
                check_same_thread=False,
                timeout=30.0
            )
            self._local.connection.row_factory = sqlite3.Row
            # Enable foreign keys
            self._local.connection.execute("PRAGMA foreign_keys = ON")
        return self._local.connection
    
    @contextmanager
    def get_cursor(self):
        """Get a cursor with automatic commit/rollback"""
        cursor = self.connection.cursor()
        try:
            yield cursor
            self.connection.commit()
        except Exception as e:
            self.connection.rollback()
            logger.error(f"Database error: {e}")
            raise
        finally:
            cursor.close()
    
    def _init_database(self):
        """Initialize database schema for options trading"""
        with self.get_cursor() as cursor:
            # ================================================================
            # OPTIONS SIGNALS TABLE
            # ================================================================
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS options_signals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    signal_id TEXT UNIQUE NOT NULL,
                    index_symbol TEXT NOT NULL,
                    strike_price REAL NOT NULL,
                    option_type TEXT NOT NULL,
                    expiry_date DATE NOT NULL,
                    
                    -- Timing
                    signal_time TIMESTAMP NOT NULL,
                    market_session TEXT,
                    days_to_expiry INTEGER,
                    
                    -- Underlying Price
                    index_price REAL,
                    index_change_pct REAL,
                    index_high REAL,
                    index_low REAL,
                    
                    -- Option Price
                    option_price REAL,
                    option_bid REAL,
                    option_ask REAL,
                    bid_ask_spread_pct REAL,
                    
                    -- Greeks
                    delta REAL,
                    gamma REAL,
                    theta REAL,
                    vega REAL,
                    iv REAL,
                    
                    -- Technical
                    supertrend_signal TEXT,
                    supertrend_value REAL,
                    vwap REAL,
                    vwap_position TEXT,
                    rsi REAL,
                    macd_signal TEXT,
                    
                    -- Volume & OI
                    option_volume INTEGER,
                    option_oi INTEGER,
                    oi_change INTEGER,
                    oi_change_pct REAL,
                    volume_oi_ratio REAL,
                    pcr REAL,
                    
                    -- Signals
                    buy_signals TEXT,
                    sell_signals TEXT,
                    signal_type TEXT,
                    signal_strength REAL,
                    
                    -- AI 3-Tier Analysis
                    tier1_response TEXT,
                    tier1_confidence REAL,
                    tier2_response TEXT,
                    tier2_confidence REAL,
                    tier3_response TEXT,
                    tier3_confidence REAL,
                    final_ai_direction TEXT,
                    final_ai_confidence REAL,
                    ai_reasoning TEXT,
                    
                    -- Ultra AI Validation
                    ultra_validator_score REAL,
                    neural_ensemble_score REAL,
                    quantum_filter_passed BOOLEAN,
                    
                    -- Scores
                    technical_score REAL,
                    ai_score REAL,
                    market_structure_score REAL,
                    volume_score REAL,
                    greeks_score REAL,
                    combined_score REAL,
                    signal_quality TEXT,
                    
                    -- Market Context
                    market_regime TEXT,
                    india_vix REAL,
                    vix_change_pct REAL,
                    max_pain REAL,
                    
                    -- Outcome
                    was_traded BOOLEAN DEFAULT 0,
                    trade_id TEXT,
                    actual_outcome TEXT,
                    actual_move_pct REAL,
                    time_to_target_mins INTEGER,
                    
                    -- Metadata
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # ================================================================
            # OPTIONS TRADES TABLE
            # ================================================================
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS options_trades (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    trade_id TEXT UNIQUE NOT NULL,
                    signal_id TEXT,
                    index_symbol TEXT NOT NULL,
                    strike_price REAL NOT NULL,
                    option_type TEXT NOT NULL,
                    expiry_date DATE NOT NULL,
                    
                    -- Timing
                    entry_time TIMESTAMP NOT NULL,
                    exit_time TIMESTAMP,
                    hold_duration_mins INTEGER,
                    days_to_expiry_at_entry INTEGER,
                    
                    -- Trade Details
                    entry_price REAL,
                    exit_price REAL,
                    stop_loss REAL,
                    target REAL,
                    trailing_stop REAL,
                    
                    -- Greeks at Entry
                    entry_delta REAL,
                    entry_gamma REAL,
                    entry_theta REAL,
                    entry_vega REAL,
                    entry_iv REAL,
                    
                    -- Position
                    quantity INTEGER,
                    lot_size INTEGER,
                    lots_traded INTEGER,
                    capital_used REAL,
                    margin_required REAL,
                    
                    -- Execution
                    order_id TEXT,
                    execution_mode TEXT,
                    status TEXT,
                    
                    -- Stacking
                    is_stacked BOOLEAN DEFAULT 0,
                    stacking_level INTEGER DEFAULT 0,
                    parent_trade_id TEXT,
                    
                    -- Hedging
                    is_hedged BOOLEAN DEFAULT 0,
                    hedge_trade_id TEXT,
                    hedge_ratio REAL,
                    
                    -- P&L
                    pnl REAL DEFAULT 0,
                    pnl_pct REAL DEFAULT 0,
                    pnl_points REAL DEFAULT 0,
                    max_profit REAL DEFAULT 0,
                    max_drawdown REAL DEFAULT 0,
                    
                    -- Exit
                    exit_reason TEXT,
                    outcome TEXT DEFAULT 'OPEN',
                    
                    -- Risk
                    risk_reward_planned REAL,
                    risk_reward_actual REAL,
                    
                    -- Market Context
                    entry_index_price REAL,
                    entry_market_regime TEXT,
                    entry_vix REAL,
                    
                    -- Scores
                    entry_combined_score REAL,
                    entry_ai_confidence REAL,
                    entry_ultra_validator_score REAL,
                    
                    -- Metadata
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    
                    FOREIGN KEY (signal_id) REFERENCES options_signals(signal_id),
                    FOREIGN KEY (parent_trade_id) REFERENCES options_trades(trade_id)
                )
            """)
            
            # ================================================================
            # STACKING EVENTS TABLE
            # ================================================================
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS stacking_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_id TEXT UNIQUE NOT NULL,
                    trade_id TEXT NOT NULL,
                    event_time TIMESTAMP NOT NULL,
                    
                    -- Decision
                    decision TEXT NOT NULL,
                    decision_confidence REAL,
                    decision_reasoning TEXT,
                    
                    -- Position State Before
                    positions_before INTEGER,
                    total_exposure_before REAL,
                    unrealized_pnl_before REAL,
                    
                    -- Position State After
                    positions_after INTEGER,
                    total_exposure_after REAL,
                    
                    -- Market Context
                    index_price REAL,
                    vix REAL,
                    market_regime TEXT,
                    
                    -- AI Scores
                    ai_stack_score REAL,
                    neural_ensemble_score REAL,
                    risk_score REAL,
                    
                    -- Outcome
                    event_outcome TEXT,
                    pnl_impact REAL,
                    
                    -- Metadata
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    
                    FOREIGN KEY (trade_id) REFERENCES options_trades(trade_id)
                )
            """)
            
            # ================================================================
            # DAILY PERFORMANCE TABLE
            # ================================================================
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS daily_performance (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date DATE UNIQUE NOT NULL,
                    
                    -- Trade Counts
                    total_trades INTEGER DEFAULT 0,
                    call_trades INTEGER DEFAULT 0,
                    put_trades INTEGER DEFAULT 0,
                    wins INTEGER DEFAULT 0,
                    losses INTEGER DEFAULT 0,
                    breakeven INTEGER DEFAULT 0,
                    
                    -- Win Rates
                    overall_win_rate REAL DEFAULT 0,
                    call_win_rate REAL DEFAULT 0,
                    put_win_rate REAL DEFAULT 0,
                    
                    -- P&L
                    gross_profit REAL DEFAULT 0,
                    gross_loss REAL DEFAULT 0,
                    net_pnl REAL DEFAULT 0,
                    net_points REAL DEFAULT 0,
                    profit_factor REAL DEFAULT 0,
                    
                    -- Trade Metrics
                    avg_win REAL DEFAULT 0,
                    avg_loss REAL DEFAULT 0,
                    largest_win REAL DEFAULT 0,
                    largest_loss REAL DEFAULT 0,
                    avg_hold_time_mins REAL DEFAULT 0,
                    
                    -- Stacking
                    stacking_events INTEGER DEFAULT 0,
                    successful_stacks INTEGER DEFAULT 0,
                    stacking_win_rate REAL DEFAULT 0,
                    
                    -- Hedging
                    hedges_placed INTEGER DEFAULT 0,
                    hedge_effectiveness REAL DEFAULT 0,
                    
                    -- Market Context
                    market_regime TEXT,
                    avg_vix REAL,
                    nifty_change_pct REAL,
                    
                    -- AI Performance
                    ai_accuracy REAL DEFAULT 0,
                    ultra_validator_accuracy REAL DEFAULT 0,
                    signals_generated INTEGER DEFAULT 0,
                    signals_traded INTEGER DEFAULT 0,
                    
                    -- Metadata
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # ================================================================
            # POSITIONS TABLE - Real-time position tracking
            # ================================================================
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS open_positions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    position_id TEXT UNIQUE NOT NULL,
                    trade_id TEXT NOT NULL,
                    index_symbol TEXT NOT NULL,
                    strike_price REAL NOT NULL,
                    option_type TEXT NOT NULL,
                    expiry_date DATE NOT NULL,
                    
                    -- Position Details
                    quantity INTEGER,
                    lot_size INTEGER,
                    lots_traded INTEGER,
                    entry_price REAL,
                    current_price REAL,
                    
                    -- Current Greeks
                    current_delta REAL,
                    current_gamma REAL,
                    current_theta REAL,
                    current_vega REAL,
                    current_iv REAL,
                    
                    -- Risk Levels
                    stop_loss REAL,
                    target REAL,
                    trailing_stop REAL,
                    
                    -- P&L
                    unrealized_pnl REAL DEFAULT 0,
                    unrealized_pnl_pct REAL DEFAULT 0,
                    max_profit REAL DEFAULT 0,
                    max_drawdown REAL DEFAULT 0,
                    
                    -- Stacking/Hedge Status
                    is_stacked BOOLEAN DEFAULT 0,
                    stacking_level INTEGER DEFAULT 0,
                    is_hedged BOOLEAN DEFAULT 0,
                    hedge_position_id TEXT,
                    
                    -- Metadata
                    opened_at TIMESTAMP NOT NULL,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    
                    FOREIGN KEY (trade_id) REFERENCES options_trades(trade_id)
                )
            """)
            
            # ================================================================
            # ERROR LOGS TABLE
            # ================================================================
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS error_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    error_type TEXT NOT NULL,
                    error_message TEXT,
                    error_traceback TEXT,
                    component TEXT,
                    trade_id TEXT,
                    signal_id TEXT,
                    context TEXT,
                    resolved BOOLEAN DEFAULT 0,
                    resolution_notes TEXT
                )
            """)
            
            # ================================================================
            # TOKEN MANAGEMENT TABLE
            # ================================================================
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS token_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    token_hash TEXT NOT NULL,
                    client_id TEXT NOT NULL,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expires_at TIMESTAMP,
                    update_source TEXT,
                    is_valid BOOLEAN DEFAULT 1
                )
            """)
            
            # ================================================================
            # SERVICE STATE TABLE - Persistent strategy enabled/disabled state
            # ================================================================
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS service_state (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # ================================================================
            # CREATE INDEXES FOR PERFORMANCE
            # ================================================================
            indexes = [
                "CREATE INDEX IF NOT EXISTS idx_signals_symbol ON options_signals(index_symbol)",
                "CREATE INDEX IF NOT EXISTS idx_signals_time ON options_signals(signal_time)",
                "CREATE INDEX IF NOT EXISTS idx_signals_quality ON options_signals(signal_quality)",
                "CREATE INDEX IF NOT EXISTS idx_trades_symbol ON options_trades(index_symbol)",
                "CREATE INDEX IF NOT EXISTS idx_trades_time ON options_trades(entry_time)",
                "CREATE INDEX IF NOT EXISTS idx_trades_status ON options_trades(status)",
                "CREATE INDEX IF NOT EXISTS idx_trades_outcome ON options_trades(outcome)",
                "CREATE INDEX IF NOT EXISTS idx_positions_symbol ON open_positions(index_symbol)",
                "CREATE INDEX IF NOT EXISTS idx_stacking_trade ON stacking_events(trade_id)",
                "CREATE INDEX IF NOT EXISTS idx_daily_date ON daily_performance(date)",
                "CREATE INDEX IF NOT EXISTS idx_errors_type ON error_logs(error_type)",
            ]
            for idx in indexes:
                cursor.execute(idx)
            
            logger.info("Database schema initialized successfully")
    
    # ========================================================================
    # SIGNAL OPERATIONS
    # ========================================================================
    
    def save_signal(self, signal: OptionsSignalRecord) -> bool:
        """Save an options signal to the database"""
        try:
            with self.get_cursor() as cursor:
                cursor.execute("""
                    INSERT OR REPLACE INTO options_signals (
                        signal_id, index_symbol, strike_price, option_type, expiry_date,
                        signal_time, market_session, days_to_expiry,
                        index_price, index_change_pct, index_high, index_low,
                        option_price, option_bid, option_ask, bid_ask_spread_pct,
                        delta, gamma, theta, vega, iv,
                        supertrend_signal, supertrend_value, vwap, vwap_position, rsi, macd_signal,
                        option_volume, option_oi, oi_change, oi_change_pct, volume_oi_ratio, pcr,
                        buy_signals, sell_signals, signal_type, signal_strength,
                        tier1_response, tier1_confidence, tier2_response, tier2_confidence,
                        tier3_response, tier3_confidence, final_ai_direction, final_ai_confidence, ai_reasoning,
                        ultra_validator_score, neural_ensemble_score, quantum_filter_passed,
                        technical_score, ai_score, market_structure_score, volume_score, greeks_score,
                        combined_score, signal_quality,
                        market_regime, india_vix, vix_change_pct, max_pain,
                        was_traded, trade_id, actual_outcome, actual_move_pct, time_to_target_mins,
                        updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                """, (
                    signal.signal_id, signal.index_symbol, signal.strike_price, signal.option_type, 
                    signal.expiry_date.isoformat() if isinstance(signal.expiry_date, date) else signal.expiry_date,
                    signal.signal_time.isoformat() if isinstance(signal.signal_time, datetime) else signal.signal_time,
                    signal.market_session, signal.days_to_expiry,
                    signal.index_price, signal.index_change_pct, signal.index_high, signal.index_low,
                    signal.option_price, signal.option_bid, signal.option_ask, signal.bid_ask_spread_pct,
                    signal.delta, signal.gamma, signal.theta, signal.vega, signal.iv,
                    signal.supertrend_signal, signal.supertrend_value, signal.vwap, signal.vwap_position, signal.rsi, signal.macd_signal,
                    signal.option_volume, signal.option_oi, signal.oi_change, signal.oi_change_pct, signal.volume_oi_ratio, signal.pcr,
                    json.dumps(signal.buy_signals), json.dumps(signal.sell_signals), signal.signal_type, signal.signal_strength,
                    signal.tier1_response, signal.tier1_confidence, signal.tier2_response, signal.tier2_confidence,
                    signal.tier3_response, signal.tier3_confidence, signal.final_ai_direction, signal.final_ai_confidence, signal.ai_reasoning,
                    signal.ultra_validator_score, signal.neural_ensemble_score, signal.quantum_filter_passed,
                    signal.technical_score, signal.ai_score, signal.market_structure_score, signal.volume_score, signal.greeks_score,
                    signal.combined_score, signal.signal_quality,
                    signal.market_regime, signal.india_vix, signal.vix_change_pct, signal.max_pain,
                    signal.was_traded, signal.trade_id, signal.actual_outcome, signal.actual_move_pct, signal.time_to_target_mins
                ))
            logger.info(f"Saved signal: {signal.signal_id}")
            return True
        except Exception as e:
            logger.error(f"Error saving signal: {e}")
            return False
    
    def get_signal(self, signal_id: str) -> Optional[Dict[str, Any]]:
        """Get a signal by ID"""
        try:
            with self.get_cursor() as cursor:
                cursor.execute("SELECT * FROM options_signals WHERE signal_id = ?", (signal_id,))
                row = cursor.fetchone()
                if row:
                    return dict(row)
            return None
        except Exception as e:
            logger.error(f"Error getting signal: {e}")
            return None
    
    def get_signals_by_date(self, target_date: date) -> List[Dict[str, Any]]:
        """Get all signals for a specific date"""
        try:
            with self.get_cursor() as cursor:
                cursor.execute("""
                    SELECT * FROM options_signals 
                    WHERE DATE(signal_time) = ?
                    ORDER BY signal_time DESC
                """, (target_date.isoformat(),))
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Error getting signals by date: {e}")
            return []
    
    # ========================================================================
    # TRADE OPERATIONS
    # ========================================================================
    
    def save_trade(self, trade: OptionsTradeRecord) -> bool:
        """Save an options trade to the database"""
        try:
            with self.get_cursor() as cursor:
                cursor.execute("""
                    INSERT OR REPLACE INTO options_trades (
                        trade_id, signal_id, index_symbol, strike_price, option_type, expiry_date,
                        entry_time, exit_time, hold_duration_mins, days_to_expiry_at_entry,
                        entry_price, exit_price, stop_loss, target, trailing_stop,
                        entry_delta, entry_gamma, entry_theta, entry_vega, entry_iv,
                        quantity, lot_size, lots_traded, capital_used, margin_required,
                        order_id, execution_mode, status,
                        is_stacked, stacking_level, parent_trade_id,
                        is_hedged, hedge_trade_id, hedge_ratio,
                        pnl, pnl_pct, pnl_points, max_profit, max_drawdown,
                        exit_reason, outcome,
                        risk_reward_planned, risk_reward_actual,
                        entry_index_price, entry_market_regime, entry_vix,
                        entry_combined_score, entry_ai_confidence, entry_ultra_validator_score,
                        updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                """, (
                    trade.trade_id, trade.signal_id, trade.index_symbol, trade.strike_price, trade.option_type,
                    trade.expiry_date.isoformat() if isinstance(trade.expiry_date, date) else trade.expiry_date,
                    trade.entry_time.isoformat() if isinstance(trade.entry_time, datetime) else trade.entry_time,
                    trade.exit_time.isoformat() if trade.exit_time and isinstance(trade.exit_time, datetime) else trade.exit_time,
                    trade.hold_duration_mins, trade.days_to_expiry_at_entry,
                    trade.entry_price, trade.exit_price, trade.stop_loss, trade.target, trade.trailing_stop,
                    trade.entry_delta, trade.entry_gamma, trade.entry_theta, trade.entry_vega, trade.entry_iv,
                    trade.quantity, trade.lot_size, trade.lots_traded, trade.capital_used, trade.margin_required,
                    trade.order_id, trade.execution_mode, trade.status,
                    trade.is_stacked, trade.stacking_level, trade.parent_trade_id,
                    trade.is_hedged, trade.hedge_trade_id, trade.hedge_ratio,
                    trade.pnl, trade.pnl_pct, trade.pnl_points, trade.max_profit, trade.max_drawdown,
                    trade.exit_reason, trade.outcome,
                    trade.risk_reward_planned, trade.risk_reward_actual,
                    trade.entry_index_price, trade.entry_market_regime, trade.entry_vix,
                    trade.entry_combined_score, trade.entry_ai_confidence, trade.entry_ultra_validator_score
                ))
            logger.info(f"Saved trade: {trade.trade_id}")
            return True
        except Exception as e:
            logger.error(f"Error saving trade: {e}")
            return False
    
    def update_trade_exit(self, trade_id: str, exit_price: float, exit_time: datetime,
                          exit_reason: str, pnl: float, pnl_pct: float, outcome: str) -> bool:
        """Update trade with exit details"""
        try:
            with self.get_cursor() as cursor:
                # Calculate hold duration
                cursor.execute("SELECT entry_time FROM options_trades WHERE trade_id = ?", (trade_id,))
                row = cursor.fetchone()
                if row:
                    entry_time = datetime.fromisoformat(row['entry_time'])
                    hold_duration = int((exit_time - entry_time).total_seconds() / 60)
                else:
                    hold_duration = 0
                
                cursor.execute("""
                    UPDATE options_trades SET
                        exit_price = ?,
                        exit_time = ?,
                        exit_reason = ?,
                        pnl = ?,
                        pnl_pct = ?,
                        outcome = ?,
                        status = 'CLOSED',
                        hold_duration_mins = ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE trade_id = ?
                """, (exit_price, exit_time.isoformat(), exit_reason, pnl, pnl_pct, outcome, hold_duration, trade_id))
            logger.info(f"Updated trade exit: {trade_id}")
            return True
        except Exception as e:
            logger.error(f"Error updating trade exit: {e}")
            return False
    
    def get_open_trades(self) -> List[Dict[str, Any]]:
        """Get all open trades"""
        try:
            with self.get_cursor() as cursor:
                cursor.execute("""
                    SELECT * FROM options_trades 
                    WHERE status NOT IN ('CLOSED', 'CANCELLED', 'FAILED')
                    ORDER BY entry_time DESC
                """)
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Error getting open trades: {e}")
            return []
    
    def get_trades_by_date(self, target_date: date) -> List[Dict[str, Any]]:
        """Get all trades for a specific date"""
        try:
            with self.get_cursor() as cursor:
                cursor.execute("""
                    SELECT * FROM options_trades 
                    WHERE DATE(entry_time) = ?
                    ORDER BY entry_time DESC
                """, (target_date.isoformat(),))
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Error getting trades by date: {e}")
            return []
    
    # ========================================================================
    # POSITION OPERATIONS
    # ========================================================================
    
    def save_position(self, trade_id: str, index_symbol: str, strike_price: float,
                      option_type: str, expiry_date: date, quantity: int, lot_size: int,
                      entry_price: float, current_price: float, stop_loss: float,
                      target: float) -> str:
        """Save a new open position"""
        try:
            position_id = f"POS_{trade_id}"
            with self.get_cursor() as cursor:
                cursor.execute("""
                    INSERT OR REPLACE INTO open_positions (
                        position_id, trade_id, index_symbol, strike_price, option_type, expiry_date,
                        quantity, lot_size, lots_traded, entry_price, current_price,
                        stop_loss, target, opened_at, last_updated
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                """, (
                    position_id, trade_id, index_symbol, strike_price, option_type,
                    expiry_date.isoformat(), quantity, lot_size, quantity // lot_size,
                    entry_price, current_price, stop_loss, target
                ))
            logger.info(f"Saved position: {position_id}")
            return position_id
        except Exception as e:
            logger.error(f"Error saving position: {e}")
            return ""
    
    def update_position_price(self, position_id: str, current_price: float,
                              delta: float = 0, gamma: float = 0, theta: float = 0,
                              vega: float = 0, iv: float = 0) -> bool:
        """Update position with current price and Greeks"""
        try:
            with self.get_cursor() as cursor:
                # Get entry price for P&L calc
                cursor.execute("SELECT entry_price, quantity FROM open_positions WHERE position_id = ?", (position_id,))
                row = cursor.fetchone()
                if row:
                    entry_price = row['entry_price']
                    quantity = row['quantity']
                    unrealized_pnl = (current_price - entry_price) * quantity
                    unrealized_pnl_pct = ((current_price / entry_price) - 1) * 100 if entry_price > 0 else 0
                    
                    cursor.execute("""
                        UPDATE open_positions SET
                            current_price = ?,
                            current_delta = ?,
                            current_gamma = ?,
                            current_theta = ?,
                            current_vega = ?,
                            current_iv = ?,
                            unrealized_pnl = ?,
                            unrealized_pnl_pct = ?,
                            max_profit = MAX(COALESCE(max_profit, 0), ?),
                            max_drawdown = MIN(COALESCE(max_drawdown, 0), ?),
                            last_updated = CURRENT_TIMESTAMP
                        WHERE position_id = ?
                    """, (current_price, delta, gamma, theta, vega, iv, unrealized_pnl, unrealized_pnl_pct,
                          unrealized_pnl, unrealized_pnl, position_id))
                return True
        except Exception as e:
            logger.error(f"Error updating position: {e}")
            return False
    
    def close_position(self, position_id: str) -> bool:
        """Remove a closed position"""
        try:
            with self.get_cursor() as cursor:
                cursor.execute("DELETE FROM open_positions WHERE position_id = ?", (position_id,))
            logger.info(f"Closed position: {position_id}")
            return True
        except Exception as e:
            logger.error(f"Error closing position: {e}")
            return False
    
    def get_all_open_positions(self) -> List[Dict[str, Any]]:
        """Get all open positions"""
        try:
            with self.get_cursor() as cursor:
                cursor.execute("SELECT * FROM open_positions ORDER BY opened_at DESC")
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Error getting positions: {e}")
            return []
    
    # ========================================================================
    # DAILY PERFORMANCE OPERATIONS
    # ========================================================================
    
    def update_daily_performance(self, target_date: date) -> bool:
        """Calculate and update daily performance from trades"""
        try:
            with self.get_cursor() as cursor:
                # Get all closed trades for the date
                cursor.execute("""
                    SELECT * FROM options_trades 
                    WHERE DATE(entry_time) = ? AND status = 'CLOSED'
                """, (target_date.isoformat(),))
                trades = [dict(row) for row in cursor.fetchall()]
                
                if not trades:
                    return True
                
                # Calculate metrics
                total_trades = len(trades)
                call_trades = len([t for t in trades if t['option_type'] == 'CALL'])
                put_trades = len([t for t in trades if t['option_type'] == 'PUT'])
                
                wins = len([t for t in trades if t['outcome'] == 'WIN'])
                losses = len([t for t in trades if t['outcome'] == 'LOSS'])
                breakeven = len([t for t in trades if t['outcome'] == 'BREAKEVEN'])
                
                win_rate = (wins / total_trades * 100) if total_trades > 0 else 0
                
                call_wins = len([t for t in trades if t['option_type'] == 'CALL' and t['outcome'] == 'WIN'])
                put_wins = len([t for t in trades if t['option_type'] == 'PUT' and t['outcome'] == 'WIN'])
                call_win_rate = (call_wins / call_trades * 100) if call_trades > 0 else 0
                put_win_rate = (put_wins / put_trades * 100) if put_trades > 0 else 0
                
                gross_profit = sum(t['pnl'] for t in trades if t['pnl'] > 0)
                gross_loss = abs(sum(t['pnl'] for t in trades if t['pnl'] < 0))
                net_pnl = gross_profit - gross_loss
                profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else gross_profit
                
                winning_trades = [t['pnl'] for t in trades if t['outcome'] == 'WIN']
                losing_trades = [t['pnl'] for t in trades if t['outcome'] == 'LOSS']
                
                avg_win = sum(winning_trades) / len(winning_trades) if winning_trades else 0
                avg_loss = sum(losing_trades) / len(losing_trades) if losing_trades else 0
                largest_win = max(winning_trades) if winning_trades else 0
                largest_loss = min(losing_trades) if losing_trades else 0
                
                hold_times = [t['hold_duration_mins'] for t in trades if t['hold_duration_mins']]
                avg_hold_time = sum(hold_times) / len(hold_times) if hold_times else 0
                
                # Insert or update
                cursor.execute("""
                    INSERT OR REPLACE INTO daily_performance (
                        date, total_trades, call_trades, put_trades, wins, losses, breakeven,
                        overall_win_rate, call_win_rate, put_win_rate,
                        gross_profit, gross_loss, net_pnl, profit_factor,
                        avg_win, avg_loss, largest_win, largest_loss, avg_hold_time_mins,
                        updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                """, (
                    target_date.isoformat(), total_trades, call_trades, put_trades, wins, losses, breakeven,
                    win_rate, call_win_rate, put_win_rate,
                    gross_profit, gross_loss, net_pnl, profit_factor,
                    avg_win, avg_loss, largest_win, largest_loss, avg_hold_time
                ))
            logger.info(f"Updated daily performance for {target_date}")
            return True
        except Exception as e:
            logger.error(f"Error updating daily performance: {e}")
            return False
    
    def get_performance_summary(self, days: int = 30) -> Dict[str, Any]:
        """Get performance summary for last N days"""
        try:
            with self.get_cursor() as cursor:
                cursor.execute("""
                    SELECT * FROM daily_performance 
                    ORDER BY date DESC LIMIT ?
                """, (days,))
                daily = [dict(row) for row in cursor.fetchall()]
                
                if not daily:
                    return {"message": "No performance data available"}
                
                return {
                    "days_analyzed": len(daily),
                    "total_trades": sum(d['total_trades'] for d in daily),
                    "total_wins": sum(d['wins'] for d in daily),
                    "total_losses": sum(d['losses'] for d in daily),
                    "overall_win_rate": sum(d['wins'] for d in daily) / sum(d['total_trades'] for d in daily) * 100 if sum(d['total_trades'] for d in daily) > 0 else 0,
                    "total_pnl": sum(d['net_pnl'] for d in daily),
                    "avg_daily_pnl": sum(d['net_pnl'] for d in daily) / len(daily),
                    "best_day": max(daily, key=lambda x: x['net_pnl'])['date'],
                    "worst_day": min(daily, key=lambda x: x['net_pnl'])['date'],
                    "daily_breakdown": daily
                }
        except Exception as e:
            logger.error(f"Error getting performance summary: {e}")
            return {"error": str(e)}
    
    # ========================================================================
    # ERROR LOGGING
    # ========================================================================
    
    def log_error(self, error_type: str, error_message: str, component: str,
                  traceback: str = "", trade_id: str = "", signal_id: str = "",
                  context: str = "") -> bool:
        """Log an error to the database"""
        try:
            with self.get_cursor() as cursor:
                cursor.execute("""
                    INSERT INTO error_logs (
                        error_type, error_message, error_traceback, component,
                        trade_id, signal_id, context
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (error_type, error_message, traceback, component, trade_id, signal_id, context))
            return True
        except Exception as e:
            logger.error(f"Error logging error: {e}")
            return False
    
    def get_recent_errors(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent errors"""
        try:
            with self.get_cursor() as cursor:
                cursor.execute("""
                    SELECT * FROM error_logs 
                    ORDER BY timestamp DESC LIMIT ?
                """, (limit,))
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Error getting errors: {e}")
            return []
    
    # ========================================================================
    # TOKEN MANAGEMENT
    # ========================================================================
    
    def log_token_update(self, token_hash: str, client_id: str, expires_at: datetime,
                         update_source: str = "API") -> bool:
        """Log a token update"""
        try:
            with self.get_cursor() as cursor:
                # Mark previous tokens as invalid
                cursor.execute("UPDATE token_history SET is_valid = 0")
                
                # Insert new token
                cursor.execute("""
                    INSERT INTO token_history (
                        token_hash, client_id, expires_at, update_source, is_valid
                    ) VALUES (?, ?, ?, ?, 1)
                """, (token_hash, client_id, expires_at.isoformat(), update_source))
            return True
        except Exception as e:
            logger.error(f"Error logging token update: {e}")
            return False
    
    # ========================================================================
    # DATABASE MAINTENANCE
    # ========================================================================
    
    def vacuum(self):
        """Optimize database"""
        try:
            with self.get_cursor() as cursor:
                cursor.execute("VACUUM")
            logger.info("Database vacuumed successfully")
        except Exception as e:
            logger.error(f"Error vacuuming database: {e}")
    
    def close(self):
        """Close database connection"""
        if hasattr(self._local, 'connection') and self._local.connection:
            self._local.connection.close()
            self._local.connection = None
            logger.info("Database connection closed")


# ============================================================================
# SINGLETON INSTANCE
# ============================================================================

_db_instance: Optional[OptionsDatabase] = None
_db_lock = threading.Lock()


def get_options_database(db_path: str = "data/options_trading.db") -> OptionsDatabase:
    """Get or create the singleton database instance"""
    global _db_instance
    with _db_lock:
        if _db_instance is None:
            _db_instance = OptionsDatabase(db_path)
        return _db_instance


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

def init_database(db_path: str = "data/options_trading.db") -> OptionsDatabase:
    """Initialize and return database instance"""
    return get_options_database(db_path)
