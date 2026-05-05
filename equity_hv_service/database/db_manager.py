#!/usr/bin/env python3
"""
SQLite Database Manager for Equity HV Service
==============================================

Stores comprehensive trading data for analysis and service enhancement:
1. Screened Signals - All signals generated with full context
2. Trade Executions - Every trade with entry/exit details
3. Performance Metrics - Win/loss tracking, P&L history
4. Market Context - Market breadth, VIX, sector data at signal time
5. AI Analysis - Gemini responses for model improvement
6. Error Logs - For debugging and reliability improvement

Author: DTrade Systems
Version: 1.0.0
"""

import sqlite3
import json
import logging
from datetime import datetime, date
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from contextlib import contextmanager
from enum import Enum
import threading

logger = logging.getLogger(__name__)


class SignalType(Enum):
    STRONG_BUY = "STRONG_BUY"
    BUY = "BUY"
    WEAK_BUY = "WEAK_BUY"
    NEUTRAL = "NEUTRAL"
    WEAK_SELL = "WEAK_SELL"
    SELL = "SELL"
    STRONG_SELL = "STRONG_SELL"


class TradeStatus(Enum):
    PENDING = "PENDING"
    EXECUTED = "EXECUTED"
    PARTIAL = "PARTIAL"
    CLOSED = "CLOSED"
    CANCELLED = "CANCELLED"
    FAILED = "FAILED"


class TradeOutcome(Enum):
    WIN = "WIN"
    LOSS = "LOSS"
    BREAKEVEN = "BREAKEVEN"
    OPEN = "OPEN"


# ============================================================================
# DATA CLASSES FOR TYPE SAFETY
# ============================================================================

@dataclass
class SignalRecord:
    """Complete signal record for storage"""
    # Identification
    symbol: str
    signal_id: str  # Unique ID: {symbol}_{timestamp}
    
    # Timing
    signal_time: datetime
    market_session: str  # "OPENING", "MID_SESSION", "CLOSING"
    
    # Price Data
    current_price: float
    prev_close: float
    day_high: float
    day_low: float
    change_pct: float
    
    # Technical Indicators
    vwap: float
    vwap_position: str
    vwap_distance_pct: float
    supertrend_signal: str
    supertrend_value: float
    cpr_top: float
    cpr_pivot: float
    cpr_bottom: float
    cpr_position: str
    cpr_width_pct: float
    
    # Volume Analysis
    current_volume: int
    avg_volume: int
    volume_spike_ratio: float
    has_volume_spike: bool
    
    # Trend Analysis
    trend_5min: str
    trend_15min: str
    trend_1hour: str
    continuous_trend_bars: int
    
    # Candlestick
    candle_type: str
    candle_body_pct: float
    
    # Signals
    buy_signals: List[str]
    sell_signals: List[str]
    signal_type: str
    signal_strength: float
    
    # AI Analysis
    ai_confidence: float
    ai_direction: str
    ai_reasoning: str
    tier1_response: Optional[str] = None
    tier2_response: Optional[str] = None
    tier3_response: Optional[str] = None
    
    # Multi-Factor Scores
    technical_score: float = 0.0
    ai_score: float = 0.0
    market_structure_score: float = 0.0
    volume_score: float = 0.0
    combined_score: float = 0.0
    signal_quality: str = "REJECT"
    
    # Market Context at Signal Time
    market_regime: str = "NEUTRAL"
    advance_decline_ratio: float = 1.0
    india_vix: float = 15.0
    nifty_change_pct: float = 0.0
    sector_momentum: str = "STABLE"
    
    # F&O Data
    lot_size: int = 1
    fo_eligibility_score: float = 0.0
    option_oi_atm: int = 0
    pcr: float = 1.0
    max_pain: float = 0.0
    
    # Outcome Tracking (updated after trade)
    was_traded: bool = False
    trade_id: Optional[str] = None
    actual_outcome: Optional[str] = None  # "CORRECT", "INCORRECT", "PARTIAL"
    actual_move_pct: Optional[float] = None
    time_to_target_mins: Optional[int] = None


@dataclass
class TradeRecord:
    """Complete trade execution record"""
    # Identification
    trade_id: str
    signal_id: str
    symbol: str
    direction: str  # "CALL" or "PUT" - Required field, must be before optionals
    
    # Timing
    entry_time: datetime
    exit_time: Optional[datetime] = None
    hold_duration_mins: Optional[int] = None
    
    # Trade Details
    entry_price: float = 0.0
    exit_price: Optional[float] = None
    stop_loss: float = 0.0
    target: float = 0.0
    trailing_stop: float = 0.0
    
    # Position Sizing
    quantity: int = 0
    lot_size: int = 1
    lots_traded: int = 1
    capital_used: float = 0.0
    
    # Execution
    order_id: str = ""
    execution_mode: str = "PAPER"  # "PAPER" or "LIVE"
    status: str = "PENDING"
    
    # P&L
    pnl: float = 0.0
    pnl_pct: float = 0.0
    max_profit: float = 0.0
    max_drawdown: float = 0.0
    
    # Exit Details
    exit_reason: Optional[str] = None  # "TARGET", "STOP_LOSS", "TRAILING_STOP", "TIME_EXIT", "MANUAL"
    outcome: str = "OPEN"  # WIN, LOSS, BREAKEVEN
    
    # Risk Metrics
    risk_reward_planned: float = 0.0
    risk_reward_actual: Optional[float] = None
    
    # Market Context at Entry
    entry_market_regime: str = "NEUTRAL"
    entry_vix: float = 15.0
    entry_nifty_change: float = 0.0
    
    # Scores at Entry
    entry_combined_score: float = 0.0
    entry_ai_confidence: float = 0.0
    entry_technical_score: float = 0.0


@dataclass
class DailyPerformance:
    """Daily performance summary"""
    date: date
    total_trades: int = 0
    wins: int = 0
    losses: int = 0
    breakeven: int = 0
    win_rate: float = 0.0
    gross_profit: float = 0.0
    gross_loss: float = 0.0
    net_pnl: float = 0.0
    profit_factor: float = 0.0
    avg_win: float = 0.0
    avg_loss: float = 0.0
    largest_win: float = 0.0
    largest_loss: float = 0.0
    max_consecutive_wins: int = 0
    max_consecutive_losses: int = 0
    signals_generated: int = 0
    signals_traded: int = 0
    hit_rate: float = 0.0  # % of signals that hit target
    avg_hold_time_mins: float = 0.0
    market_regime: str = "NEUTRAL"
    avg_vix: float = 15.0


# ============================================================================
# DATABASE MANAGER
# ============================================================================

class TradingDatabase:
    """
    SQLite database manager for trading data storage and retrieval.
    Thread-safe with connection pooling.
    """
    
    def __init__(self, db_path: str = "data/trading_data.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._local = threading.local()
        self._lock = threading.Lock()
        
        # Initialize database
        self._init_database()
        
        logger.info(f"Trading database initialized at {self.db_path}")
    
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
        """Initialize database schema"""
        with self.get_cursor() as cursor:
            # ================================================================
            # SIGNALS TABLE - All generated signals with full context
            # ================================================================
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS signals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    signal_id TEXT UNIQUE NOT NULL,
                    symbol TEXT NOT NULL,
                    signal_time TIMESTAMP NOT NULL,
                    market_session TEXT,
                    
                    -- Price Data
                    current_price REAL,
                    prev_close REAL,
                    day_high REAL,
                    day_low REAL,
                    change_pct REAL,
                    
                    -- Technical Indicators
                    vwap REAL,
                    vwap_position TEXT,
                    vwap_distance_pct REAL,
                    supertrend_signal TEXT,
                    supertrend_value REAL,
                    cpr_top REAL,
                    cpr_pivot REAL,
                    cpr_bottom REAL,
                    cpr_position TEXT,
                    cpr_width_pct REAL,
                    
                    -- Volume
                    current_volume INTEGER,
                    avg_volume INTEGER,
                    volume_spike_ratio REAL,
                    has_volume_spike BOOLEAN,
                    
                    -- Trends
                    trend_5min TEXT,
                    trend_15min TEXT,
                    trend_1hour TEXT,
                    continuous_trend_bars INTEGER,
                    
                    -- Candlestick
                    candle_type TEXT,
                    candle_body_pct REAL,
                    
                    -- Signal Details
                    buy_signals TEXT,  -- JSON array
                    sell_signals TEXT,  -- JSON array
                    signal_type TEXT,
                    signal_strength REAL,
                    
                    -- AI Analysis
                    ai_confidence REAL,
                    ai_direction TEXT,
                    ai_reasoning TEXT,
                    tier1_response TEXT,
                    tier2_response TEXT,
                    tier3_response TEXT,
                    
                    -- Multi-Factor Scores
                    technical_score REAL,
                    ai_score REAL,
                    market_structure_score REAL,
                    volume_score REAL,
                    combined_score REAL,
                    signal_quality TEXT,
                    
                    -- Market Context
                    market_regime TEXT,
                    advance_decline_ratio REAL,
                    india_vix REAL,
                    nifty_change_pct REAL,
                    sector_momentum TEXT,
                    
                    -- F&O Data
                    lot_size INTEGER,
                    fo_eligibility_score REAL,
                    option_oi_atm INTEGER,
                    pcr REAL,
                    max_pain REAL,
                    
                    -- Outcome Tracking
                    was_traded BOOLEAN DEFAULT 0,
                    trade_id TEXT,
                    actual_outcome TEXT,
                    actual_move_pct REAL,
                    time_to_target_mins INTEGER,
                    
                    -- Metadata
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    
                    -- Indexes
                    FOREIGN KEY (trade_id) REFERENCES trades(trade_id)
                )
            """)
            
            # ================================================================
            # TRADES TABLE - All executed trades
            # ================================================================
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS trades (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    trade_id TEXT UNIQUE NOT NULL,
                    signal_id TEXT,
                    symbol TEXT NOT NULL,
                    
                    -- Timing
                    entry_time TIMESTAMP NOT NULL,
                    exit_time TIMESTAMP,
                    hold_duration_mins INTEGER,
                    
                    -- Trade Details
                    direction TEXT NOT NULL,
                    entry_price REAL,
                    exit_price REAL,
                    stop_loss REAL,
                    target REAL,
                    trailing_stop REAL,
                    
                    -- Position
                    quantity INTEGER,
                    lot_size INTEGER,
                    lots_traded INTEGER,
                    capital_used REAL,
                    
                    -- Execution
                    order_id TEXT,
                    execution_mode TEXT,
                    status TEXT,
                    
                    -- P&L
                    pnl REAL DEFAULT 0,
                    pnl_pct REAL DEFAULT 0,
                    max_profit REAL DEFAULT 0,
                    max_drawdown REAL DEFAULT 0,
                    
                    -- Exit
                    exit_reason TEXT,
                    outcome TEXT DEFAULT 'OPEN',
                    
                    -- Risk
                    risk_reward_planned REAL,
                    risk_reward_actual REAL,
                    
                    -- Market Context
                    entry_market_regime TEXT,
                    entry_vix REAL,
                    entry_nifty_change REAL,
                    
                    -- Scores
                    entry_combined_score REAL,
                    entry_ai_confidence REAL,
                    entry_technical_score REAL,
                    
                    -- Metadata
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    
                    FOREIGN KEY (signal_id) REFERENCES signals(signal_id)
                )
            """)
            
            # ================================================================
            # DAILY PERFORMANCE TABLE
            # ================================================================
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS daily_performance (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date DATE UNIQUE NOT NULL,
                    total_trades INTEGER DEFAULT 0,
                    wins INTEGER DEFAULT 0,
                    losses INTEGER DEFAULT 0,
                    breakeven INTEGER DEFAULT 0,
                    win_rate REAL DEFAULT 0,
                    gross_profit REAL DEFAULT 0,
                    gross_loss REAL DEFAULT 0,
                    net_pnl REAL DEFAULT 0,
                    profit_factor REAL DEFAULT 0,
                    avg_win REAL DEFAULT 0,
                    avg_loss REAL DEFAULT 0,
                    largest_win REAL DEFAULT 0,
                    largest_loss REAL DEFAULT 0,
                    max_consecutive_wins INTEGER DEFAULT 0,
                    max_consecutive_losses INTEGER DEFAULT 0,
                    signals_generated INTEGER DEFAULT 0,
                    signals_traded INTEGER DEFAULT 0,
                    hit_rate REAL DEFAULT 0,
                    avg_hold_time_mins REAL DEFAULT 0,
                    market_regime TEXT,
                    avg_vix REAL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # ================================================================
            # MARKET CONTEXT TABLE - Historical market data
            # ================================================================
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS market_context (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TIMESTAMP NOT NULL,
                    
                    -- Nifty Data
                    nifty_price REAL,
                    nifty_change_pct REAL,
                    nifty_rsi REAL,
                    
                    -- Market Breadth
                    positive_stocks INTEGER,
                    negative_stocks INTEGER,
                    neutral_stocks INTEGER,
                    advance_decline_ratio REAL,
                    
                    -- VIX
                    india_vix REAL,
                    vix_change_pct REAL,
                    
                    -- FII/DII
                    fii_net REAL,
                    dii_net REAL,
                    
                    -- Sector Data (JSON)
                    sector_performance TEXT,
                    
                    -- Global Markets (JSON)
                    global_indices TEXT,
                    
                    -- Regime
                    market_regime TEXT,
                    
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # ================================================================
            # AI RESPONSES TABLE - For model analysis
            # ================================================================
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS ai_responses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    signal_id TEXT,
                    symbol TEXT NOT NULL,
                    timestamp TIMESTAMP NOT NULL,
                    
                    -- Request
                    tier TEXT NOT NULL,  -- "TIER_1", "TIER_2", "TIER_3"
                    model_name TEXT,
                    prompt_hash TEXT,
                    input_data TEXT,  -- JSON
                    
                    -- Response
                    response_data TEXT,  -- JSON
                    confidence REAL,
                    direction TEXT,
                    reasoning TEXT,
                    
                    -- Metrics
                    response_time_ms INTEGER,
                    token_count INTEGER,
                    
                    -- Validation
                    was_correct BOOLEAN,
                    actual_outcome TEXT,
                    
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    
                    FOREIGN KEY (signal_id) REFERENCES signals(signal_id)
                )
            """)
            
            # ================================================================
            # ERROR LOGS TABLE
            # ================================================================
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS error_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    category TEXT NOT NULL,
                    error_type TEXT,
                    message TEXT,
                    stack_trace TEXT,
                    context_data TEXT,  -- JSON with relevant context
                    resolved BOOLEAN DEFAULT 0,
                    resolution_notes TEXT
                )
            """)
            
            # ================================================================
            # SCREENER CONFIGURATIONS TABLE
            # ================================================================
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS screener_configs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    config_name TEXT UNIQUE NOT NULL,
                    config_data TEXT NOT NULL,  -- JSON
                    is_active BOOLEAN DEFAULT 0,
                    backtest_win_rate REAL,
                    backtest_profit_factor REAL,
                    live_win_rate REAL,
                    live_profit_factor REAL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # ================================================================
            # SCREENING SESSIONS TABLE
            # ================================================================
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS screening_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT UNIQUE NOT NULL,
                    start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    end_time TIMESTAMP,
                    stocks_scanned INTEGER DEFAULT 0,
                    signals_generated INTEGER DEFAULT 0,
                    trades_executed INTEGER DEFAULT 0,
                    status TEXT DEFAULT 'running'
                )
            """)
            
            # ================================================================
            # CREATE INDEXES FOR PERFORMANCE
            # ================================================================
            indexes = [
                "CREATE INDEX IF NOT EXISTS idx_signals_symbol ON signals(symbol)",
                "CREATE INDEX IF NOT EXISTS idx_signals_time ON signals(signal_time)",
                "CREATE INDEX IF NOT EXISTS idx_signals_type ON signals(signal_type)",
                "CREATE INDEX IF NOT EXISTS idx_signals_quality ON signals(signal_quality)",
                "CREATE INDEX IF NOT EXISTS idx_signals_combined_score ON signals(combined_score)",
                "CREATE INDEX IF NOT EXISTS idx_signals_was_traded ON signals(was_traded)",
                "CREATE INDEX IF NOT EXISTS idx_trades_symbol ON trades(symbol)",
                "CREATE INDEX IF NOT EXISTS idx_trades_entry_time ON trades(entry_time)",
                "CREATE INDEX IF NOT EXISTS idx_trades_outcome ON trades(outcome)",
                "CREATE INDEX IF NOT EXISTS idx_trades_status ON trades(status)",
                "CREATE INDEX IF NOT EXISTS idx_daily_perf_date ON daily_performance(date)",
                "CREATE INDEX IF NOT EXISTS idx_market_context_time ON market_context(timestamp)",
                "CREATE INDEX IF NOT EXISTS idx_ai_responses_tier ON ai_responses(tier)",
                "CREATE INDEX IF NOT EXISTS idx_error_logs_category ON error_logs(category)",
            ]
            
            for idx_sql in indexes:
                cursor.execute(idx_sql)
            
            logger.info("Database schema initialized successfully")
    
    # ========================================================================
    # SIGNAL OPERATIONS
    # ========================================================================
    
    def save_signal(self, signal: SignalRecord) -> bool:
        """Save a signal record"""
        try:
            with self.get_cursor() as cursor:
                cursor.execute("""
                    INSERT OR REPLACE INTO signals (
                        signal_id, symbol, signal_time, market_session,
                        current_price, prev_close, day_high, day_low, change_pct,
                        vwap, vwap_position, vwap_distance_pct,
                        supertrend_signal, supertrend_value,
                        cpr_top, cpr_pivot, cpr_bottom, cpr_position, cpr_width_pct,
                        current_volume, avg_volume, volume_spike_ratio, has_volume_spike,
                        trend_5min, trend_15min, trend_1hour, continuous_trend_bars,
                        candle_type, candle_body_pct,
                        buy_signals, sell_signals, signal_type, signal_strength,
                        ai_confidence, ai_direction, ai_reasoning,
                        tier1_response, tier2_response, tier3_response,
                        technical_score, ai_score, market_structure_score, volume_score,
                        combined_score, signal_quality,
                        market_regime, advance_decline_ratio, india_vix, nifty_change_pct, sector_momentum,
                        lot_size, fo_eligibility_score, option_oi_atm, pcr, max_pain,
                        was_traded, trade_id, actual_outcome, actual_move_pct, time_to_target_mins,
                        updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                """, (
                    signal.signal_id, signal.symbol, signal.signal_time.isoformat(), signal.market_session,
                    signal.current_price, signal.prev_close, signal.day_high, signal.day_low, signal.change_pct,
                    signal.vwap, signal.vwap_position, signal.vwap_distance_pct,
                    signal.supertrend_signal, signal.supertrend_value,
                    signal.cpr_top, signal.cpr_pivot, signal.cpr_bottom, signal.cpr_position, signal.cpr_width_pct,
                    signal.current_volume, signal.avg_volume, signal.volume_spike_ratio, signal.has_volume_spike,
                    signal.trend_5min, signal.trend_15min, signal.trend_1hour, signal.continuous_trend_bars,
                    signal.candle_type, signal.candle_body_pct,
                    json.dumps(signal.buy_signals), json.dumps(signal.sell_signals), signal.signal_type, signal.signal_strength,
                    signal.ai_confidence, signal.ai_direction, signal.ai_reasoning,
                    signal.tier1_response, signal.tier2_response, signal.tier3_response,
                    signal.technical_score, signal.ai_score, signal.market_structure_score, signal.volume_score,
                    signal.combined_score, signal.signal_quality,
                    signal.market_regime, signal.advance_decline_ratio, signal.india_vix, signal.nifty_change_pct, signal.sector_momentum,
                    signal.lot_size, signal.fo_eligibility_score, signal.option_oi_atm, signal.pcr, signal.max_pain,
                    signal.was_traded, signal.trade_id, signal.actual_outcome, signal.actual_move_pct, signal.time_to_target_mins
                ))
            return True
        except Exception as e:
            logger.error(f"Error saving signal: {e}")
            return False
    
    def get_signals_by_date(self, date: date) -> List[Dict]:
        """Get all signals for a specific date"""
        with self.get_cursor() as cursor:
            cursor.execute("""
                SELECT * FROM signals 
                WHERE DATE(signal_time) = ?
                ORDER BY signal_time DESC
            """, (date.isoformat(),))
            return [dict(row) for row in cursor.fetchall()]
    
    def get_signals_by_symbol(self, symbol: str, limit: int = 100) -> List[Dict]:
        """Get recent signals for a symbol"""
        with self.get_cursor() as cursor:
            cursor.execute("""
                SELECT * FROM signals 
                WHERE symbol = ?
                ORDER BY signal_time DESC
                LIMIT ?
            """, (symbol, limit))
            return [dict(row) for row in cursor.fetchall()]
    
    def get_high_score_signals(self, min_score: float = 80.0, limit: int = 50) -> List[Dict]:
        """Get signals with high combined scores"""
        with self.get_cursor() as cursor:
            cursor.execute("""
                SELECT * FROM signals 
                WHERE combined_score >= ?
                ORDER BY combined_score DESC, signal_time DESC
                LIMIT ?
            """, (min_score, limit))
            return [dict(row) for row in cursor.fetchall()]
    
    def update_signal_outcome(self, signal_id: str, was_traded: bool, trade_id: str = None,
                              actual_outcome: str = None, actual_move_pct: float = None,
                              time_to_target_mins: int = None):
        """Update signal with actual outcome"""
        with self.get_cursor() as cursor:
            cursor.execute("""
                UPDATE signals SET
                    was_traded = ?,
                    trade_id = ?,
                    actual_outcome = ?,
                    actual_move_pct = ?,
                    time_to_target_mins = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE signal_id = ?
            """, (was_traded, trade_id, actual_outcome, actual_move_pct, time_to_target_mins, signal_id))
    
    # ========================================================================
    # TRADE OPERATIONS
    # ========================================================================
    
    def save_trade(self, trade: TradeRecord) -> bool:
        """Save a trade record"""
        try:
            with self.get_cursor() as cursor:
                cursor.execute("""
                    INSERT OR REPLACE INTO trades (
                        trade_id, signal_id, symbol,
                        entry_time, exit_time, hold_duration_mins,
                        direction, entry_price, exit_price, stop_loss, target, trailing_stop,
                        quantity, lot_size, lots_traded, capital_used,
                        order_id, execution_mode, status,
                        pnl, pnl_pct, max_profit, max_drawdown,
                        exit_reason, outcome,
                        risk_reward_planned, risk_reward_actual,
                        entry_market_regime, entry_vix, entry_nifty_change,
                        entry_combined_score, entry_ai_confidence, entry_technical_score,
                        updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                """, (
                    trade.trade_id, trade.signal_id, trade.symbol,
                    trade.entry_time.isoformat(), trade.exit_time.isoformat() if trade.exit_time else None, trade.hold_duration_mins,
                    trade.direction, trade.entry_price, trade.exit_price, trade.stop_loss, trade.target, trade.trailing_stop,
                    trade.quantity, trade.lot_size, trade.lots_traded, trade.capital_used,
                    trade.order_id, trade.execution_mode, trade.status,
                    trade.pnl, trade.pnl_pct, trade.max_profit, trade.max_drawdown,
                    trade.exit_reason, trade.outcome,
                    trade.risk_reward_planned, trade.risk_reward_actual,
                    trade.entry_market_regime, trade.entry_vix, trade.entry_nifty_change,
                    trade.entry_combined_score, trade.entry_ai_confidence, trade.entry_technical_score
                ))
            return True
        except Exception as e:
            logger.error(f"Error saving trade: {e}")
            return False
    
    def update_trade(self, trade_id: str, updates: Dict) -> bool:
        """Update trade with new data"""
        try:
            set_clauses = ", ".join([f"{k} = ?" for k in updates.keys()])
            values = list(updates.values()) + [trade_id]
            
            with self.get_cursor() as cursor:
                cursor.execute(f"""
                    UPDATE trades SET {set_clauses}, updated_at = CURRENT_TIMESTAMP
                    WHERE trade_id = ?
                """, values)
            return True
        except Exception as e:
            logger.error(f"Error updating trade: {e}")
            return False
    
    def close_trade(self, trade_id: str, exit_price: float, exit_reason: str, pnl: float, pnl_pct: float):
        """Close a trade with exit details"""
        exit_time = datetime.now()
        
        # Get entry time for duration
        with self.get_cursor() as cursor:
            cursor.execute("SELECT entry_time FROM trades WHERE trade_id = ?", (trade_id,))
            row = cursor.fetchone()
            if row:
                entry_time = datetime.fromisoformat(row['entry_time'])
                hold_duration = int((exit_time - entry_time).total_seconds() / 60)
            else:
                hold_duration = 0
        
        outcome = "WIN" if pnl > 0 else "LOSS" if pnl < 0 else "BREAKEVEN"
        
        self.update_trade(trade_id, {
            "exit_time": exit_time.isoformat(),
            "exit_price": exit_price,
            "exit_reason": exit_reason,
            "pnl": pnl,
            "pnl_pct": pnl_pct,
            "outcome": outcome,
            "status": "CLOSED",
            "hold_duration_mins": hold_duration
        })
    
    def get_trades_by_date(self, date: date) -> List[Dict]:
        """Get trades for a specific date"""
        with self.get_cursor() as cursor:
            cursor.execute("""
                SELECT * FROM trades 
                WHERE DATE(entry_time) = ?
                ORDER BY entry_time DESC
            """, (date.isoformat(),))
            return [dict(row) for row in cursor.fetchall()]
    
    def get_open_trades(self) -> List[Dict]:
        """Get all open trades"""
        with self.get_cursor() as cursor:
            cursor.execute("""
                SELECT * FROM trades 
                WHERE status IN ('PENDING', 'EXECUTED', 'PARTIAL')
                ORDER BY entry_time DESC
            """)
            return [dict(row) for row in cursor.fetchall()]
    
    # ========================================================================
    # PERFORMANCE ANALYTICS
    # ========================================================================
    
    def calculate_daily_performance(self, target_date: date) -> DailyPerformance:
        """Calculate and store daily performance metrics"""
        with self.get_cursor() as cursor:
            # Get all closed trades for the date
            cursor.execute("""
                SELECT * FROM trades 
                WHERE DATE(entry_time) = ? AND status = 'CLOSED'
            """, (target_date.isoformat(),))
            trades = [dict(row) for row in cursor.fetchall()]
            
            # Get signals count
            cursor.execute("""
                SELECT COUNT(*) as count FROM signals 
                WHERE DATE(signal_time) = ?
            """, (target_date.isoformat(),))
            signals_count = cursor.fetchone()['count']
        
        if not trades:
            return DailyPerformance(date=target_date, signals_generated=signals_count)
        
        # Calculate metrics
        wins = [t for t in trades if t['outcome'] == 'WIN']
        losses = [t for t in trades if t['outcome'] == 'LOSS']
        breakeven = [t for t in trades if t['outcome'] == 'BREAKEVEN']
        
        total_trades = len(trades)
        win_count = len(wins)
        loss_count = len(losses)
        breakeven_count = len(breakeven)
        
        gross_profit = sum(t['pnl'] for t in wins)
        gross_loss = abs(sum(t['pnl'] for t in losses))
        net_pnl = gross_profit - gross_loss
        
        win_rate = (win_count / total_trades * 100) if total_trades > 0 else 0
        profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else float('inf')
        avg_win = (gross_profit / win_count) if win_count > 0 else 0
        avg_loss = (gross_loss / loss_count) if loss_count > 0 else 0
        
        largest_win = max([t['pnl'] for t in wins]) if wins else 0
        largest_loss = min([t['pnl'] for t in losses]) if losses else 0
        
        avg_hold_time = sum(t['hold_duration_mins'] or 0 for t in trades) / total_trades if total_trades > 0 else 0
        
        # Traded signals
        signals_traded = len(set(t['signal_id'] for t in trades if t['signal_id']))
        
        perf = DailyPerformance(
            date=target_date,
            total_trades=total_trades,
            wins=win_count,
            losses=loss_count,
            breakeven=breakeven_count,
            win_rate=win_rate,
            gross_profit=gross_profit,
            gross_loss=gross_loss,
            net_pnl=net_pnl,
            profit_factor=profit_factor,
            avg_win=avg_win,
            avg_loss=avg_loss,
            largest_win=largest_win,
            largest_loss=largest_loss,
            signals_generated=signals_count,
            signals_traded=signals_traded,
            avg_hold_time_mins=avg_hold_time
        )
        
        # Save to database
        self._save_daily_performance(perf)
        
        return perf
    
    def record_daily_performance(self, perf: DailyPerformance):
        """Public method to record daily performance"""
        self._save_daily_performance(perf)
    
    def get_daily_performance(self, date_str: str) -> Optional[Dict]:
        """Get daily performance for a specific date"""
        with self.get_cursor() as cursor:
            cursor.execute("""
                SELECT * FROM daily_performance WHERE date = ?
            """, (date_str,))
            row = cursor.fetchone()
            if row:
                return dict(row)
        return None
    
    def _save_daily_performance(self, perf: DailyPerformance):
        """Save daily performance to database"""
        with self.get_cursor() as cursor:
            cursor.execute("""
                INSERT OR REPLACE INTO daily_performance (
                    date, total_trades, wins, losses, breakeven, win_rate,
                    gross_profit, gross_loss, net_pnl, profit_factor,
                    avg_win, avg_loss, largest_win, largest_loss,
                    max_consecutive_wins, max_consecutive_losses,
                    signals_generated, signals_traded, hit_rate, avg_hold_time_mins,
                    market_regime, avg_vix, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (
                perf.date.isoformat(), perf.total_trades, perf.wins, perf.losses, perf.breakeven, perf.win_rate,
                perf.gross_profit, perf.gross_loss, perf.net_pnl, perf.profit_factor,
                perf.avg_win, perf.avg_loss, perf.largest_win, perf.largest_loss,
                perf.max_consecutive_wins, perf.max_consecutive_losses,
                perf.signals_generated, perf.signals_traded, perf.hit_rate, perf.avg_hold_time_mins,
                perf.market_regime, perf.avg_vix
            ))
    
    def get_performance_summary(self, days: int = 30) -> Dict:
        """Get performance summary for last N days"""
        with self.get_cursor() as cursor:
            cursor.execute("""
                SELECT * FROM daily_performance 
                ORDER BY date DESC LIMIT ?
            """, (days,))
            daily_data = [dict(row) for row in cursor.fetchall()]
        
        if not daily_data:
            return {"message": "No performance data available"}
        
        total_trades = sum(d['total_trades'] for d in daily_data)
        total_wins = sum(d['wins'] for d in daily_data)
        total_losses = sum(d['losses'] for d in daily_data)
        total_profit = sum(d['gross_profit'] for d in daily_data)
        total_loss = sum(d['gross_loss'] for d in daily_data)
        net_pnl = total_profit - total_loss
        
        return {
            "period_days": len(daily_data),
            "total_trades": total_trades,
            "total_wins": total_wins,
            "total_losses": total_losses,
            "win_rate": (total_wins / total_trades * 100) if total_trades > 0 else 0,
            "gross_profit": total_profit,
            "gross_loss": total_loss,
            "net_pnl": net_pnl,
            "profit_factor": (total_profit / total_loss) if total_loss > 0 else float('inf'),
            "avg_daily_pnl": net_pnl / len(daily_data),
            "best_day": max(daily_data, key=lambda x: x['net_pnl']),
            "worst_day": min(daily_data, key=lambda x: x['net_pnl']),
            "daily_breakdown": daily_data
        }
    
    # ========================================================================
    # SCREENING SESSION TRACKING
    # ========================================================================
    
    def start_screening_session(self, session_id: str, stocks_scanned: int = 0, signals_generated: int = 0):
        """Start a new screening session"""
        with self.get_cursor() as cursor:
            cursor.execute("""
                INSERT INTO screening_sessions (session_id, stocks_scanned, signals_generated, status)
                VALUES (?, ?, ?, 'running')
            """, (session_id, stocks_scanned, signals_generated))
    
    def end_screening_session(self, session_id: str, trades_executed: int = 0):
        """End a screening session"""
        with self.get_cursor() as cursor:
            cursor.execute("""
                UPDATE screening_sessions 
                SET end_time = CURRENT_TIMESTAMP, 
                    trades_executed = ?, 
                    status = 'completed'
                WHERE session_id = ?
            """, (trades_executed, session_id))
    
    def get_recent_sessions(self, limit: int = 50) -> List[Dict]:
        """Get recent screening sessions"""
        with self.get_cursor() as cursor:
            cursor.execute("""
                SELECT * FROM screening_sessions 
                ORDER BY start_time DESC LIMIT ?
            """, (limit,))
            return [dict(row) for row in cursor.fetchall()]
    
    # ========================================================================
    # ANALYSIS QUERIES FOR ENHANCEMENT
    # ========================================================================
    
    def get_signal_accuracy_by_score(self) -> List[Dict]:
        """Analyze signal accuracy by score ranges - for optimization"""
        with self.get_cursor() as cursor:
            cursor.execute("""
                SELECT 
                    CASE 
                        WHEN combined_score >= 90 THEN '90-100'
                        WHEN combined_score >= 80 THEN '80-90'
                        WHEN combined_score >= 70 THEN '70-80'
                        WHEN combined_score >= 60 THEN '60-70'
                        ELSE 'Below 60'
                    END as score_range,
                    COUNT(*) as total_signals,
                    SUM(CASE WHEN was_traded = 1 THEN 1 ELSE 0 END) as traded,
                    SUM(CASE WHEN actual_outcome = 'CORRECT' THEN 1 ELSE 0 END) as correct,
                    AVG(actual_move_pct) as avg_move_pct
                FROM signals
                WHERE was_traded = 1
                GROUP BY score_range
                ORDER BY score_range DESC
            """)
            return [dict(row) for row in cursor.fetchall()]
    
    def get_signal_accuracy_by_indicator(self) -> Dict:
        """Analyze which indicators correlate with successful trades"""
        with self.get_cursor() as cursor:
            # VWAP Position accuracy
            cursor.execute("""
                SELECT 
                    vwap_position,
                    COUNT(*) as count,
                    SUM(CASE WHEN actual_outcome = 'CORRECT' THEN 1 ELSE 0 END) as correct,
                    AVG(actual_move_pct) as avg_move
                FROM signals WHERE was_traded = 1
                GROUP BY vwap_position
            """)
            vwap_analysis = [dict(row) for row in cursor.fetchall()]
            
            # SuperTrend accuracy
            cursor.execute("""
                SELECT 
                    supertrend_signal,
                    COUNT(*) as count,
                    SUM(CASE WHEN actual_outcome = 'CORRECT' THEN 1 ELSE 0 END) as correct,
                    AVG(actual_move_pct) as avg_move
                FROM signals WHERE was_traded = 1
                GROUP BY supertrend_signal
            """)
            supertrend_analysis = [dict(row) for row in cursor.fetchall()]
            
            # CPR Position accuracy
            cursor.execute("""
                SELECT 
                    cpr_position,
                    COUNT(*) as count,
                    SUM(CASE WHEN actual_outcome = 'CORRECT' THEN 1 ELSE 0 END) as correct,
                    AVG(actual_move_pct) as avg_move
                FROM signals WHERE was_traded = 1
                GROUP BY cpr_position
            """)
            cpr_analysis = [dict(row) for row in cursor.fetchall()]
            
            return {
                "vwap": vwap_analysis,
                "supertrend": supertrend_analysis,
                "cpr": cpr_analysis
            }
    
    def get_ai_confidence_accuracy(self) -> List[Dict]:
        """Analyze AI confidence vs actual outcomes"""
        with self.get_cursor() as cursor:
            cursor.execute("""
                SELECT 
                    CASE 
                        WHEN ai_confidence >= 9 THEN '9-10'
                        WHEN ai_confidence >= 8 THEN '8-9'
                        WHEN ai_confidence >= 7 THEN '7-8'
                        WHEN ai_confidence >= 6 THEN '6-7'
                        ELSE 'Below 6'
                    END as confidence_range,
                    COUNT(*) as total,
                    SUM(CASE WHEN actual_outcome = 'CORRECT' THEN 1 ELSE 0 END) as correct,
                    ROUND(SUM(CASE WHEN actual_outcome = 'CORRECT' THEN 1.0 ELSE 0.0 END) / COUNT(*) * 100, 2) as accuracy_pct
                FROM signals
                WHERE was_traded = 1 AND ai_confidence > 0
                GROUP BY confidence_range
                ORDER BY confidence_range DESC
            """)
            return [dict(row) for row in cursor.fetchall()]
    
    def get_market_regime_performance(self) -> List[Dict]:
        """Analyze performance by market regime"""
        with self.get_cursor() as cursor:
            cursor.execute("""
                SELECT 
                    entry_market_regime as regime,
                    COUNT(*) as trades,
                    SUM(CASE WHEN outcome = 'WIN' THEN 1 ELSE 0 END) as wins,
                    ROUND(SUM(CASE WHEN outcome = 'WIN' THEN 1.0 ELSE 0.0 END) / COUNT(*) * 100, 2) as win_rate,
                    SUM(pnl) as total_pnl,
                    AVG(pnl) as avg_pnl
                FROM trades
                WHERE status = 'CLOSED'
                GROUP BY entry_market_regime
            """)
            return [dict(row) for row in cursor.fetchall()]
    
    def get_best_trading_hours(self) -> List[Dict]:
        """Analyze which hours perform best"""
        with self.get_cursor() as cursor:
            cursor.execute("""
                SELECT 
                    strftime('%H', entry_time) as hour,
                    COUNT(*) as trades,
                    SUM(CASE WHEN outcome = 'WIN' THEN 1 ELSE 0 END) as wins,
                    ROUND(SUM(CASE WHEN outcome = 'WIN' THEN 1.0 ELSE 0.0 END) / COUNT(*) * 100, 2) as win_rate,
                    SUM(pnl) as total_pnl
                FROM trades
                WHERE status = 'CLOSED'
                GROUP BY hour
                ORDER BY hour
            """)
            return [dict(row) for row in cursor.fetchall()]
    
    def get_symbol_performance(self) -> List[Dict]:
        """Get performance breakdown by symbol"""
        with self.get_cursor() as cursor:
            cursor.execute("""
                SELECT 
                    symbol,
                    COUNT(*) as trades,
                    SUM(CASE WHEN outcome = 'WIN' THEN 1 ELSE 0 END) as wins,
                    SUM(CASE WHEN outcome = 'LOSS' THEN 1 ELSE 0 END) as losses,
                    ROUND(SUM(CASE WHEN outcome = 'WIN' THEN 1.0 ELSE 0.0 END) / COUNT(*) * 100, 2) as win_rate,
                    SUM(pnl) as total_pnl,
                    AVG(pnl) as avg_pnl,
                    MAX(pnl) as best_trade,
                    MIN(pnl) as worst_trade
                FROM trades
                WHERE status = 'CLOSED'
                GROUP BY symbol
                ORDER BY total_pnl DESC
            """)
            return [dict(row) for row in cursor.fetchall()]
    
    # ========================================================================
    # MARKET CONTEXT
    # ========================================================================
    
    def save_market_context(self, context: Dict):
        """Save market context snapshot"""
        with self.get_cursor() as cursor:
            cursor.execute("""
                INSERT INTO market_context (
                    timestamp, nifty_price, nifty_change_pct, nifty_rsi,
                    positive_stocks, negative_stocks, neutral_stocks, advance_decline_ratio,
                    india_vix, vix_change_pct, fii_net, dii_net,
                    sector_performance, global_indices, market_regime
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                context.get('timestamp', datetime.now().isoformat()),
                context.get('nifty_price'), context.get('nifty_change_pct'), context.get('nifty_rsi'),
                context.get('positive_stocks'), context.get('negative_stocks'), context.get('neutral_stocks'),
                context.get('advance_decline_ratio'),
                context.get('india_vix'), context.get('vix_change_pct'),
                context.get('fii_net'), context.get('dii_net'),
                json.dumps(context.get('sector_performance', {})),
                json.dumps(context.get('global_indices', {})),
                context.get('market_regime')
            ))
    
    # ========================================================================
    # ERROR LOGGING
    # ========================================================================
    
    def log_error(self, category: str, error_type: str, message: str, 
                  stack_trace: str = None, context_data: Dict = None):
        """Log an error for tracking"""
        with self.get_cursor() as cursor:
            cursor.execute("""
                INSERT INTO error_logs (category, error_type, message, stack_trace, context_data)
                VALUES (?, ?, ?, ?, ?)
            """, (category, error_type, message, stack_trace, json.dumps(context_data) if context_data else None))
    
    def get_error_summary(self, days: int = 7) -> Dict:
        """Get error summary for last N days"""
        with self.get_cursor() as cursor:
            cursor.execute("""
                SELECT 
                    category,
                    error_type,
                    COUNT(*) as count,
                    MAX(timestamp) as last_occurrence
                FROM error_logs
                WHERE timestamp >= datetime('now', ?)
                GROUP BY category, error_type
                ORDER BY count DESC
            """, (f'-{days} days',))
            return [dict(row) for row in cursor.fetchall()]
    
    # ========================================================================
    # CLEANUP
    # ========================================================================
    
    def close(self):
        """Close database connection"""
        if hasattr(self._local, 'connection') and self._local.connection:
            self._local.connection.close()
            self._local.connection = None


# ============================================================================
# SINGLETON INSTANCE
# ============================================================================

_db_instance: Optional[TradingDatabase] = None

def get_database(db_path: str = "data/trading_data.db") -> TradingDatabase:
    """Get singleton database instance"""
    global _db_instance
    if _db_instance is None:
        _db_instance = TradingDatabase(db_path)
    return _db_instance


# Export
__all__ = [
    'TradingDatabase',
    'get_database',
    'SignalRecord',
    'TradeRecord',
    'DailyPerformance',
    'SignalType',
    'TradeStatus',
    'TradeOutcome'
]
