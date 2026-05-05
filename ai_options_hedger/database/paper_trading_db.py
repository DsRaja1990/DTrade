"""
Paper Trading Extensions for AI Options Hedger
===============================================
Adds paper trading mode support to the existing database.
"""

import sqlite3
import logging
from datetime import datetime, date
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from contextlib import contextmanager

logger = logging.getLogger(__name__)


class TradingMode(Enum):
    """Trading execution mode"""
    PAPER = "paper"       # Simulated trades, no real money
    PRODUCTION = "production"  # Real trades with money
    EVALUATION = "evaluation"  # Evaluation mode - tracks signals and trades for analysis


@dataclass
class PaperPosition:
    """Paper trading position"""
    position_id: str
    trade_id: str
    instrument: str
    option_type: str
    strike: float
    entry_price: float
    current_price: float
    quantity: int
    lot_size: int
    entry_time: datetime
    entry_reason: str
    momentum_score: float = 0.0
    ai_confidence: float = 0.0
    unrealized_pnl: float = 0.0
    unrealized_pnl_pct: float = 0.0
    max_profit: float = 0.0
    max_loss: float = 0.0
    
    def update_price(self, new_price: float):
        """Update current price and PnL"""
        self.current_price = new_price
        self.unrealized_pnl = (new_price - self.entry_price) * self.quantity * self.lot_size
        self.unrealized_pnl_pct = (new_price - self.entry_price) / self.entry_price * 100 if self.entry_price > 0 else 0
        self.max_profit = max(self.max_profit, self.unrealized_pnl)
        self.max_loss = min(self.max_loss, self.unrealized_pnl)


class PaperTradingDB:
    """
    Paper trading database extension
    Adds trading mode and paper trading tables to existing options DB
    """
    
    def __init__(self, db_path: str = None):
        if db_path is None:
            db_dir = Path(__file__).parent
            db_path = str(db_dir / "hedger_data.db")
        
        self.db_path = db_path
        self._init_tables()
    
    @contextmanager
    def get_cursor(self):
        """Get database cursor with auto-commit"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            cursor = conn.cursor()
            yield cursor
            conn.commit()
        finally:
            conn.close()
    
    def _get_conn(self):
        """Get a raw database connection (caller must close it)"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def _init_tables(self):
        """Initialize paper trading tables"""
        with self.get_cursor() as cursor:
            # Trading mode table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS trading_mode (
                    id INTEGER PRIMARY KEY,
                    mode TEXT NOT NULL DEFAULT 'paper',
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_by TEXT DEFAULT 'system'
                )
            """)
            
            # Initialize with paper mode if empty
            cursor.execute("SELECT COUNT(*) FROM trading_mode")
            if cursor.fetchone()[0] == 0:
                cursor.execute("INSERT INTO trading_mode (mode) VALUES ('paper')")
            
            # Paper trades table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS paper_trades (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    trade_id TEXT UNIQUE NOT NULL,
                    timestamp_entry TIMESTAMP NOT NULL,
                    timestamp_exit TIMESTAMP,
                    instrument TEXT NOT NULL,
                    option_type TEXT NOT NULL,
                    strike REAL NOT NULL,
                    expiry DATE,
                    entry_price REAL NOT NULL,
                    exit_price REAL,
                    quantity INTEGER NOT NULL,
                    lot_size INTEGER NOT NULL,
                    pnl REAL DEFAULT 0,
                    pnl_pct REAL DEFAULT 0,
                    pnl_points REAL DEFAULT 0,
                    status TEXT DEFAULT 'entered',
                    entry_reason TEXT,
                    exit_reason TEXT,
                    momentum_at_entry REAL,
                    momentum_at_exit REAL,
                    ai_confidence_entry REAL,
                    duration_seconds INTEGER,
                    max_profit REAL DEFAULT 0,
                    max_loss REAL DEFAULT 0,
                    greeks_delta REAL,
                    greeks_gamma REAL,
                    greeks_theta REAL,
                    greeks_vega REAL,
                    iv_at_entry REAL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Important signals table - only high-quality signals for analysis
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS important_signals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TIMESTAMP NOT NULL,
                    instrument TEXT NOT NULL,
                    signal_type TEXT NOT NULL,
                    direction TEXT,
                    strength REAL,
                    ai_confidence REAL,
                    tier1_direction TEXT,
                    tier2_direction TEXT,
                    tier3_direction TEXT,
                    combined_score REAL,
                    reason TEXT,
                    was_traded BOOLEAN DEFAULT 0,
                    trade_result TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Daily summary table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS daily_summary (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date DATE UNIQUE NOT NULL,
                    total_signals INTEGER DEFAULT 0,
                    traded_signals INTEGER DEFAULT 0,
                    total_trades INTEGER DEFAULT 0,
                    winning_trades INTEGER DEFAULT 0,
                    losing_trades INTEGER DEFAULT 0,
                    win_rate REAL DEFAULT 0,
                    total_pnl REAL DEFAULT 0,
                    avg_pnl REAL DEFAULT 0,
                    best_trade REAL DEFAULT 0,
                    worst_trade REAL DEFAULT 0,
                    avg_hold_time_mins REAL DEFAULT 0,
                    market_regime TEXT,
                    avg_vix REAL,
                    notes TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Important errors table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS important_errors (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    error_type TEXT NOT NULL,
                    error_message TEXT NOT NULL,
                    component TEXT,
                    context TEXT,
                    resolved BOOLEAN DEFAULT 0
                )
            """)
            
            # Create indexes
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_paper_trades_status ON paper_trades(status)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_paper_trades_time ON paper_trades(timestamp_entry)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_signals_time ON important_signals(timestamp)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_daily_date ON daily_summary(date)")
            
            logger.info("Paper trading tables initialized")
    
    # ========================================================================
    # TRADING MODE OPERATIONS
    # ========================================================================
    
    def get_trading_mode(self) -> TradingMode:
        """Get current trading mode"""
        with self.get_cursor() as cursor:
            cursor.execute("SELECT mode FROM trading_mode ORDER BY id DESC LIMIT 1")
            row = cursor.fetchone()
            return TradingMode(row['mode']) if row else TradingMode.PAPER
    
    def set_trading_mode(self, mode: TradingMode, updated_by: str = "api") -> bool:
        """Set trading mode"""
        with self.get_cursor() as cursor:
            cursor.execute("""
                UPDATE trading_mode SET mode = ?, updated_at = ?, updated_by = ?
                WHERE id = (SELECT MAX(id) FROM trading_mode)
            """, (mode.value, datetime.now(), updated_by))
            return cursor.rowcount > 0
    
    # ========================================================================
    # PAPER TRADE OPERATIONS
    # ========================================================================
    
    def insert_paper_trade(self, trade: Dict) -> int:
        """Insert a paper trade"""
        with self.get_cursor() as cursor:
            cursor.execute("""
                INSERT INTO paper_trades (
                    trade_id, timestamp_entry, instrument, option_type, strike, expiry,
                    entry_price, quantity, lot_size, status, entry_reason,
                    momentum_at_entry, ai_confidence_entry, greeks_delta, greeks_gamma,
                    greeks_theta, greeks_vega, iv_at_entry
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                trade.get('trade_id'),
                trade.get('timestamp_entry', datetime.now()),
                trade.get('instrument'),
                trade.get('option_type'),
                trade.get('strike'),
                trade.get('expiry'),
                trade.get('entry_price'),
                trade.get('quantity'),
                trade.get('lot_size'),
                trade.get('status', 'entered'),
                trade.get('entry_reason'),
                trade.get('momentum_at_entry', 0),
                trade.get('ai_confidence_entry', 0),
                trade.get('greeks_delta'),
                trade.get('greeks_gamma'),
                trade.get('greeks_theta'),
                trade.get('greeks_vega'),
                trade.get('iv_at_entry')
            ))
            return cursor.lastrowid
    
    def update_paper_trade_exit(
        self,
        trade_id: str,
        exit_price: float,
        exit_reason: str,
        pnl: float,
        pnl_pct: float,
        momentum_at_exit: float = 0
    ):
        """Update paper trade with exit details"""
        with self.get_cursor() as cursor:
            # Get entry time for duration
            cursor.execute("SELECT timestamp_entry FROM paper_trades WHERE trade_id = ?", (trade_id,))
            row = cursor.fetchone()
            duration = 0
            if row:
                entry_time = datetime.fromisoformat(row['timestamp_entry']) if isinstance(row['timestamp_entry'], str) else row['timestamp_entry']
                duration = int((datetime.now() - entry_time).total_seconds())
            
            cursor.execute("""
                UPDATE paper_trades SET
                    timestamp_exit = ?, exit_price = ?, exit_reason = ?,
                    pnl = ?, pnl_pct = ?, status = 'exited',
                    duration_seconds = ?, momentum_at_exit = ?
                WHERE trade_id = ?
            """, (datetime.now(), exit_price, exit_reason, pnl, pnl_pct, duration, momentum_at_exit, trade_id))
    
    def get_open_paper_trades(self) -> List[Dict]:
        """Get all open paper trades"""
        with self.get_cursor() as cursor:
            cursor.execute("SELECT * FROM paper_trades WHERE status = 'entered'")
            return [dict(row) for row in cursor.fetchall()]
    
    def get_paper_trades_by_date(self, target_date: date) -> List[Dict]:
        """Get paper trades for a specific date"""
        with self.get_cursor() as cursor:
            cursor.execute("""
                SELECT * FROM paper_trades 
                WHERE DATE(timestamp_entry) = ?
                ORDER BY timestamp_entry DESC
            """, (target_date.isoformat(),))
            return [dict(row) for row in cursor.fetchall()]
    
    def get_recent_paper_trades(self, limit: int = 50) -> List[Dict]:
        """Get recent paper trades"""
        with self.get_cursor() as cursor:
            cursor.execute("""
                SELECT * FROM paper_trades 
                ORDER BY timestamp_entry DESC 
                LIMIT ?
            """, (limit,))
            return [dict(row) for row in cursor.fetchall()]
    
    # ========================================================================
    # SIGNAL OPERATIONS
    # ========================================================================
    
    def save_important_signal(self, signal: Dict) -> int:
        """Save an important signal for analysis"""
        with self.get_cursor() as cursor:
            cursor.execute("""
                INSERT INTO important_signals (
                    timestamp, instrument, signal_type, direction, strength,
                    ai_confidence, tier1_direction, tier2_direction, tier3_direction,
                    combined_score, reason, was_traded
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                signal.get('timestamp', datetime.now()),
                signal.get('instrument'),
                signal.get('signal_type'),
                signal.get('direction'),
                signal.get('strength', 0),
                signal.get('ai_confidence', 0),
                signal.get('tier1_direction'),
                signal.get('tier2_direction'),
                signal.get('tier3_direction'),
                signal.get('combined_score', 0),
                signal.get('reason'),
                signal.get('was_traded', False)
            ))
            return cursor.lastrowid
    
    def get_signals_by_date(self, target_date: date) -> List[Dict]:
        """Get signals for a specific date"""
        with self.get_cursor() as cursor:
            cursor.execute("""
                SELECT * FROM important_signals 
                WHERE DATE(timestamp) = ?
                ORDER BY timestamp DESC
            """, (target_date.isoformat(),))
            return [dict(row) for row in cursor.fetchall()]
    
    # ========================================================================
    # ERROR LOGGING
    # ========================================================================
    
    def log_error(self, error_type: str, message: str, component: str = None, context: str = None):
        """Log an important error"""
        with self.get_cursor() as cursor:
            cursor.execute("""
                INSERT INTO important_errors (error_type, error_message, component, context)
                VALUES (?, ?, ?, ?)
            """, (error_type, message, component, context))
    
    def get_unresolved_errors(self) -> List[Dict]:
        """Get unresolved errors"""
        with self.get_cursor() as cursor:
            cursor.execute("SELECT * FROM important_errors WHERE resolved = 0 ORDER BY timestamp DESC")
            return [dict(row) for row in cursor.fetchall()]
    
    # ========================================================================
    # DAILY SUMMARY
    # ========================================================================
    
    def update_daily_summary(self, target_date: date = None):
        """Calculate and update daily summary"""
        if target_date is None:
            target_date = date.today()
        
        with self.get_cursor() as cursor:
            # Get trade stats
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_trades,
                    SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) as winning_trades,
                    SUM(CASE WHEN pnl <= 0 THEN 1 ELSE 0 END) as losing_trades,
                    SUM(pnl) as total_pnl,
                    AVG(pnl) as avg_pnl,
                    MAX(pnl) as best_trade,
                    MIN(pnl) as worst_trade,
                    AVG(duration_seconds / 60.0) as avg_hold_time_mins
                FROM paper_trades 
                WHERE DATE(timestamp_entry) = ? AND status = 'exited'
            """, (target_date.isoformat(),))
            
            stats = cursor.fetchone()
            if not stats or stats['total_trades'] == 0:
                return
            
            total_trades = stats['total_trades']
            winning_trades = stats['winning_trades'] or 0
            win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
            
            # Get signal stats
            cursor.execute("""
                SELECT COUNT(*) as total_signals,
                       SUM(CASE WHEN was_traded = 1 THEN 1 ELSE 0 END) as traded_signals
                FROM important_signals WHERE DATE(timestamp) = ?
            """, (target_date.isoformat(),))
            signal_stats = cursor.fetchone()
            
            # Upsert
            cursor.execute("""
                INSERT INTO daily_summary (
                    date, total_signals, traded_signals, total_trades, winning_trades,
                    losing_trades, win_rate, total_pnl, avg_pnl, best_trade, worst_trade,
                    avg_hold_time_mins, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(date) DO UPDATE SET
                    total_signals = excluded.total_signals,
                    traded_signals = excluded.traded_signals,
                    total_trades = excluded.total_trades,
                    winning_trades = excluded.winning_trades,
                    losing_trades = excluded.losing_trades,
                    win_rate = excluded.win_rate,
                    total_pnl = excluded.total_pnl,
                    avg_pnl = excluded.avg_pnl,
                    best_trade = excluded.best_trade,
                    worst_trade = excluded.worst_trade,
                    avg_hold_time_mins = excluded.avg_hold_time_mins,
                    updated_at = excluded.updated_at
            """, (
                target_date.isoformat(),
                signal_stats['total_signals'] or 0,
                signal_stats['traded_signals'] or 0,
                total_trades,
                winning_trades,
                stats['losing_trades'] or 0,
                win_rate,
                stats['total_pnl'] or 0,
                stats['avg_pnl'] or 0,
                stats['best_trade'] or 0,
                stats['worst_trade'] or 0,
                stats['avg_hold_time_mins'] or 0,
                datetime.now()
            ))
    
    def get_daily_summaries(self, days: int = 30) -> List[Dict]:
        """Get daily summaries"""
        with self.get_cursor() as cursor:
            cursor.execute("""
                SELECT * FROM daily_summary 
                ORDER BY date DESC LIMIT ?
            """, (days,))
            return [dict(row) for row in cursor.fetchall()]
    
    # ========================================================================
    # ANALYSIS QUERIES
    # ========================================================================
    
    def get_analysis_summary(self) -> Dict:
        """Get comprehensive analysis summary"""
        with self.get_cursor() as cursor:
            summary = {}
            
            # Overall paper trade stats
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_trades,
                    SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) as wins,
                    ROUND(SUM(CASE WHEN pnl > 0 THEN 1.0 ELSE 0 END) / NULLIF(COUNT(*), 0) * 100, 2) as win_rate,
                    ROUND(SUM(pnl), 2) as total_pnl,
                    ROUND(AVG(pnl), 2) as avg_pnl,
                    ROUND(AVG(duration_seconds / 60.0), 1) as avg_duration_mins
                FROM paper_trades WHERE status = 'exited'
            """)
            summary['overall'] = dict(cursor.fetchone())
            
            # By instrument
            cursor.execute("""
                SELECT 
                    instrument,
                    COUNT(*) as trades,
                    SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) as wins,
                    ROUND(SUM(CASE WHEN pnl > 0 THEN 1.0 ELSE 0 END) / COUNT(*) * 100, 2) as win_rate,
                    ROUND(SUM(pnl), 2) as total_pnl
                FROM paper_trades WHERE status = 'exited'
                GROUP BY instrument
            """)
            summary['by_instrument'] = [dict(row) for row in cursor.fetchall()]
            
            # By option type
            cursor.execute("""
                SELECT 
                    option_type,
                    COUNT(*) as trades,
                    SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) as wins,
                    ROUND(SUM(CASE WHEN pnl > 0 THEN 1.0 ELSE 0 END) / COUNT(*) * 100, 2) as win_rate,
                    ROUND(SUM(pnl), 2) as total_pnl
                FROM paper_trades WHERE status = 'exited'
                GROUP BY option_type
            """)
            summary['by_option_type'] = [dict(row) for row in cursor.fetchall()]
            
            # Signal quality analysis
            cursor.execute("""
                SELECT 
                    signal_type,
                    COUNT(*) as signals,
                    SUM(CASE WHEN was_traded = 1 THEN 1 ELSE 0 END) as traded,
                    ROUND(AVG(ai_confidence), 2) as avg_ai_confidence,
                    ROUND(AVG(combined_score), 2) as avg_score
                FROM important_signals
                GROUP BY signal_type
            """)
            summary['signal_analysis'] = [dict(row) for row in cursor.fetchall()]
            
            return summary


# Global instance
_paper_db: Optional[PaperTradingDB] = None

def get_paper_trading_db() -> PaperTradingDB:
    """Get global paper trading database instance"""
    global _paper_db
    if _paper_db is None:
        _paper_db = PaperTradingDB()
    return _paper_db
