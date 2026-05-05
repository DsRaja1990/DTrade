"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                    TRADING DATABASE v1.0                                     ║
║           SQLite Database for Signals, Trades & Analytics                    ║
║━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━║
║  Purpose: Store all trading data for analysis and Copilot enhancement       ║
║  Tables: signals, trades, ai_validations, market_context, analytics         ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import sqlite3
import json
import os
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from contextlib import contextmanager
import threading

logger = logging.getLogger(__name__)

# Database path
DB_PATH = os.path.join(os.path.dirname(__file__), 'trading_data.db')


class TradingDatabase:
    """
    SQLite database for storing all trading data
    
    Tables:
    - signals: All generated trading signals
    - trades: Executed trades with P&L
    - ai_validations: AI validation results
    - market_context: Market-wide context snapshots
    - daily_summary: Daily trading summaries
    - strategy_performance: Strategy metrics over time
    - engine_logs: Engine start/stop/error logs
    """
    
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self._local = threading.local()
        self._initialize_database()
        logger.info(f"📊 Trading Database initialized: {db_path}")
    
    def _get_connection(self) -> sqlite3.Connection:
        """Get thread-local database connection"""
        if not hasattr(self._local, 'connection') or self._local.connection is None:
            self._local.connection = sqlite3.connect(
                self.db_path, 
                check_same_thread=False,
                timeout=30
            )
            self._local.connection.row_factory = sqlite3.Row
        return self._local.connection
    
    @contextmanager
    def get_cursor(self):
        """Get database cursor with automatic commit/rollback"""
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            yield cursor
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"Database error: {e}")
            raise
    
    def _initialize_database(self):
        """Create all tables if they don't exist"""
        with self.get_cursor() as cursor:
            # Signals table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS signals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    symbol TEXT NOT NULL,
                    signal_type TEXT DEFAULT 'BUY',
                    confidence TEXT NOT NULL,
                    confidence_score REAL,
                    current_price REAL,
                    entry_price REAL,
                    target_price REAL,
                    stop_loss REAL,
                    rsi REAL,
                    patterns_matched TEXT,
                    pattern_count INTEGER,
                    volume_ratio REAL,
                    was_executed INTEGER DEFAULT 0,
                    execution_reason TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Trades table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS trades (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    trade_id TEXT UNIQUE NOT NULL,
                    signal_id INTEGER,
                    symbol TEXT NOT NULL,
                    trade_type TEXT DEFAULT 'BUY',
                    entry_price REAL NOT NULL,
                    exit_price REAL,
                    quantity INTEGER NOT NULL,
                    entry_time DATETIME NOT NULL,
                    exit_time DATETIME,
                    target_price REAL,
                    stop_loss REAL,
                    status TEXT DEFAULT 'OPEN',
                    exit_reason TEXT,
                    realized_pnl REAL,
                    pnl_percent REAL,
                    order_id TEXT,
                    exit_order_id TEXT,
                    ai_confidence REAL,
                    ai_thesis TEXT,
                    paper_trading INTEGER DEFAULT 1,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (signal_id) REFERENCES signals(id)
                )
            ''')
            
            # AI Validations table with Signal Engine integration
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS ai_validations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    signal_id INTEGER,
                    symbol TEXT NOT NULL,
                    pattern_confidence TEXT,
                    ai_approved INTEGER,
                    ai_confidence_level TEXT,
                    ai_confidence_score REAL,
                    position_multiplier REAL,
                    market_aligned INTEGER,
                    ai_signal_match INTEGER,
                    combined_thesis TEXT,
                    risk_factors TEXT,
                    catalysts TEXT,
                    market_bullish_count INTEGER,
                    market_bearish_count INTEGER,
                    market_bias TEXT,
                    service_available INTEGER,
                    validation_time_ms REAL,
                    signal_engine_aligned INTEGER DEFAULT 0,
                    signal_engine_nifty_signal TEXT,
                    signal_engine_banknifty_signal TEXT,
                    signal_engine_confidence_boost REAL DEFAULT 0.0,
                    signal_engine_reasons TEXT,
                    FOREIGN KEY (signal_id) REFERENCES signals(id)
                )
            ''')
            
            # Add Signal Engine columns if they don't exist (migration)
            try:
                cursor.execute('ALTER TABLE ai_validations ADD COLUMN signal_engine_aligned INTEGER DEFAULT 0')
            except sqlite3.OperationalError:
                pass  # Column already exists
            try:
                cursor.execute('ALTER TABLE ai_validations ADD COLUMN signal_engine_nifty_signal TEXT')
            except sqlite3.OperationalError:
                pass
            try:
                cursor.execute('ALTER TABLE ai_validations ADD COLUMN signal_engine_banknifty_signal TEXT')
            except sqlite3.OperationalError:
                pass
            try:
                cursor.execute('ALTER TABLE ai_validations ADD COLUMN signal_engine_confidence_boost REAL DEFAULT 0.0')
            except sqlite3.OperationalError:
                pass
            try:
                cursor.execute('ALTER TABLE ai_validations ADD COLUMN signal_engine_reasons TEXT')
            except sqlite3.OperationalError:
                pass
            
            # Market Context table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS market_context (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    bullish_count INTEGER,
                    bearish_count INTEGER,
                    neutral_count INTEGER,
                    weighted_bias TEXT,
                    strength_score REAL,
                    driver_sector TEXT,
                    top_movers TEXT,
                    sector_divergence TEXT,
                    vix_value REAL,
                    vix_change_pct REAL,
                    nifty_price REAL,
                    nifty_change_pct REAL
                )
            ''')
            
            # Daily Summary table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS daily_summary (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date DATE UNIQUE NOT NULL,
                    total_signals INTEGER DEFAULT 0,
                    signals_executed INTEGER DEFAULT 0,
                    signals_rejected INTEGER DEFAULT 0,
                    total_trades INTEGER DEFAULT 0,
                    winning_trades INTEGER DEFAULT 0,
                    losing_trades INTEGER DEFAULT 0,
                    win_rate REAL,
                    total_pnl REAL DEFAULT 0,
                    avg_win REAL,
                    avg_loss REAL,
                    profit_factor REAL,
                    max_drawdown REAL,
                    ai_approvals INTEGER DEFAULT 0,
                    ai_rejections INTEGER DEFAULT 0,
                    ai_accuracy REAL,
                    market_bias TEXT,
                    paper_trading INTEGER DEFAULT 1,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Strategy Performance table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS strategy_performance (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    period TEXT NOT NULL,
                    start_date DATE,
                    end_date DATE,
                    total_trades INTEGER,
                    winning_trades INTEGER,
                    losing_trades INTEGER,
                    win_rate REAL,
                    total_pnl REAL,
                    avg_pnl_per_trade REAL,
                    profit_factor REAL,
                    sharpe_ratio REAL,
                    max_drawdown REAL,
                    best_trade REAL,
                    worst_trade REAL,
                    avg_hold_time_minutes REAL,
                    patterns_performance TEXT,
                    rsi_zone_performance TEXT,
                    ai_enhancement_value REAL,
                    recommendations TEXT
                )
            ''')
            
            # Engine Logs table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS engine_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    event_type TEXT NOT NULL,
                    event_data TEXT,
                    capital REAL,
                    paper_trading INTEGER,
                    ai_enabled INTEGER,
                    error_message TEXT
                )
            ''')
            
            # Create indexes for faster queries
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_signals_symbol ON signals(symbol)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_signals_timestamp ON signals(timestamp)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_trades_symbol ON trades(symbol)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_trades_status ON trades(status)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_trades_entry_time ON trades(entry_time)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_daily_summary_date ON daily_summary(date)')
            
            logger.info("✅ Database tables initialized")
    
    # ========================================
    # SIGNAL OPERATIONS
    # ========================================
    
    def save_signal(
        self,
        symbol: str,
        confidence: str,
        confidence_score: float,
        current_price: float,
        entry_price: float,
        target_price: float,
        stop_loss: float,
        rsi: float,
        patterns_matched: List[str],
        volume_ratio: float = 1.0,
        signal_type: str = "BUY"
    ) -> int:
        """Save a trading signal and return its ID"""
        with self.get_cursor() as cursor:
            cursor.execute('''
                INSERT INTO signals (
                    symbol, signal_type, confidence, confidence_score,
                    current_price, entry_price, target_price, stop_loss,
                    rsi, patterns_matched, pattern_count, volume_ratio
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                symbol, signal_type, confidence, confidence_score,
                current_price, entry_price, target_price, stop_loss,
                rsi, json.dumps(patterns_matched), len(patterns_matched), volume_ratio
            ))
            return cursor.lastrowid
    
    def mark_signal_executed(self, signal_id: int, executed: bool, reason: str = None):
        """Mark a signal as executed or rejected"""
        with self.get_cursor() as cursor:
            cursor.execute('''
                UPDATE signals 
                SET was_executed = ?, execution_reason = ?
                WHERE id = ?
            ''', (1 if executed else 0, reason, signal_id))
    
    def get_recent_signals(self, hours: int = 24, symbol: str = None) -> List[Dict]:
        """Get recent signals"""
        with self.get_cursor() as cursor:
            if symbol:
                cursor.execute('''
                    SELECT * FROM signals 
                    WHERE timestamp > datetime('now', ?) AND symbol = ?
                    ORDER BY timestamp DESC
                ''', (f'-{hours} hours', symbol))
            else:
                cursor.execute('''
                    SELECT * FROM signals 
                    WHERE timestamp > datetime('now', ?)
                    ORDER BY timestamp DESC
                ''', (f'-{hours} hours',))
            return [dict(row) for row in cursor.fetchall()]
    
    # ========================================
    # TRADE OPERATIONS
    # ========================================
    
    def save_trade(
        self,
        trade_id: str,
        symbol: str,
        entry_price: float,
        quantity: int,
        entry_time: datetime,
        target_price: float,
        stop_loss: float,
        signal_id: int = None,
        order_id: str = None,
        ai_confidence: float = None,
        ai_thesis: str = None,
        paper_trading: bool = True
    ) -> int:
        """Save a new trade"""
        with self.get_cursor() as cursor:
            cursor.execute('''
                INSERT INTO trades (
                    trade_id, signal_id, symbol, entry_price, quantity,
                    entry_time, target_price, stop_loss, status, order_id,
                    ai_confidence, ai_thesis, paper_trading
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'OPEN', ?, ?, ?, ?)
            ''', (
                trade_id, signal_id, symbol, entry_price, quantity,
                entry_time.isoformat(), target_price, stop_loss, order_id,
                ai_confidence, ai_thesis, 1 if paper_trading else 0
            ))
            return cursor.lastrowid
    
    def close_trade(
        self,
        trade_id: str,
        exit_price: float,
        exit_time: datetime,
        exit_reason: str,
        exit_order_id: str = None
    ):
        """Close a trade with exit details"""
        with self.get_cursor() as cursor:
            # Get entry details
            cursor.execute('SELECT entry_price, quantity FROM trades WHERE trade_id = ?', (trade_id,))
            row = cursor.fetchone()
            if row:
                entry_price = row['entry_price']
                quantity = row['quantity']
                realized_pnl = (exit_price - entry_price) * quantity
                pnl_percent = ((exit_price - entry_price) / entry_price) * 100
                
                status = 'TARGET_HIT' if exit_reason == 'TARGET' else 'STOPLOSS_HIT' if exit_reason == 'STOPLOSS' else 'CLOSED'
                
                cursor.execute('''
                    UPDATE trades 
                    SET exit_price = ?, exit_time = ?, exit_reason = ?,
                        exit_order_id = ?, realized_pnl = ?, pnl_percent = ?,
                        status = ?
                    WHERE trade_id = ?
                ''', (
                    exit_price, exit_time.isoformat(), exit_reason,
                    exit_order_id, realized_pnl, pnl_percent, status, trade_id
                ))
    
    def get_open_trades(self) -> List[Dict]:
        """Get all open trades"""
        with self.get_cursor() as cursor:
            cursor.execute("SELECT * FROM trades WHERE status = 'OPEN' ORDER BY entry_time")
            return [dict(row) for row in cursor.fetchall()]
    
    def get_trades_by_date(self, date: str) -> List[Dict]:
        """Get trades for a specific date"""
        with self.get_cursor() as cursor:
            cursor.execute('''
                SELECT * FROM trades 
                WHERE DATE(entry_time) = ?
                ORDER BY entry_time
            ''', (date,))
            return [dict(row) for row in cursor.fetchall()]
    
    def get_trade_statistics(self, days: int = 30) -> Dict:
        """Get trade statistics for analysis"""
        with self.get_cursor() as cursor:
            cursor.execute('''
                SELECT 
                    COUNT(*) as total_trades,
                    SUM(CASE WHEN realized_pnl > 0 THEN 1 ELSE 0 END) as winning_trades,
                    SUM(CASE WHEN realized_pnl <= 0 THEN 1 ELSE 0 END) as losing_trades,
                    AVG(realized_pnl) as avg_pnl,
                    SUM(realized_pnl) as total_pnl,
                    AVG(CASE WHEN realized_pnl > 0 THEN realized_pnl END) as avg_win,
                    AVG(CASE WHEN realized_pnl < 0 THEN realized_pnl END) as avg_loss,
                    MAX(realized_pnl) as best_trade,
                    MIN(realized_pnl) as worst_trade
                FROM trades 
                WHERE status != 'OPEN' 
                AND entry_time > datetime('now', ?)
            ''', (f'-{days} days',))
            row = cursor.fetchone()
            if row:
                stats = dict(row)
                total = stats.get('total_trades', 0) or 0
                wins = stats.get('winning_trades', 0) or 0
                stats['win_rate'] = (wins / total * 100) if total > 0 else 0
                avg_win = abs(stats.get('avg_win', 0) or 0)
                avg_loss = abs(stats.get('avg_loss', 0) or 1)
                stats['profit_factor'] = avg_win / avg_loss if avg_loss > 0 else 0
                return stats
            return {}
    
    # ========================================
    # AI VALIDATION OPERATIONS
    # ========================================
    
    def save_ai_validation(
        self,
        symbol: str,
        pattern_confidence: str,
        ai_approved: bool,
        ai_confidence_level: str,
        ai_confidence_score: float,
        position_multiplier: float,
        market_aligned: bool,
        ai_signal_match: bool,
        combined_thesis: str,
        risk_factors: List[str],
        catalysts: List[str],
        market_bullish_count: int = 0,
        market_bearish_count: int = 0,
        market_bias: str = "NEUTRAL",
        service_available: bool = True,
        validation_time_ms: float = 0,
        signal_id: int = None,
        signal_engine_aligned: bool = False,
        signal_engine_nifty_signal: str = None,
        signal_engine_banknifty_signal: str = None,
        signal_engine_confidence_boost: float = 0.0,
        signal_engine_reasons: List[str] = None
    ) -> int:
        """Save AI validation result with Signal Engine data"""
        with self.get_cursor() as cursor:
            cursor.execute('''
                INSERT INTO ai_validations (
                    signal_id, symbol, pattern_confidence, ai_approved,
                    ai_confidence_level, ai_confidence_score, position_multiplier,
                    market_aligned, ai_signal_match, combined_thesis,
                    risk_factors, catalysts, market_bullish_count,
                    market_bearish_count, market_bias, service_available,
                    validation_time_ms, signal_engine_aligned, signal_engine_nifty_signal,
                    signal_engine_banknifty_signal, signal_engine_confidence_boost, signal_engine_reasons
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                signal_id, symbol, pattern_confidence, 1 if ai_approved else 0,
                ai_confidence_level, ai_confidence_score, position_multiplier,
                1 if market_aligned else 0, 1 if ai_signal_match else 0,
                combined_thesis, json.dumps(risk_factors), json.dumps(catalysts),
                market_bullish_count, market_bearish_count, market_bias,
                1 if service_available else 0, validation_time_ms,
                1 if signal_engine_aligned else 0, signal_engine_nifty_signal,
                signal_engine_banknifty_signal, signal_engine_confidence_boost,
                json.dumps(signal_engine_reasons) if signal_engine_reasons else None
            ))
            return cursor.lastrowid
    
    def get_ai_validation_stats(self, days: int = 7) -> Dict:
        """Get AI validation statistics"""
        with self.get_cursor() as cursor:
            cursor.execute('''
                SELECT 
                    COUNT(*) as total_validations,
                    SUM(ai_approved) as approvals,
                    SUM(CASE WHEN ai_approved = 0 THEN 1 ELSE 0 END) as rejections,
                    AVG(ai_confidence_score) as avg_confidence,
                    AVG(position_multiplier) as avg_position_size,
                    SUM(market_aligned) as market_aligned_count,
                    SUM(ai_signal_match) as ai_match_count,
                    SUM(service_available) as service_available_count,
                    AVG(validation_time_ms) as avg_validation_time
                FROM ai_validations 
                WHERE timestamp > datetime('now', ?)
            ''', (f'-{days} days',))
            row = cursor.fetchone()
            if row:
                stats = dict(row)
                total = stats.get('total_validations', 0) or 0
                approvals = stats.get('approvals', 0) or 0
                stats['approval_rate'] = (approvals / total * 100) if total > 0 else 0
                return stats
            return {}
    
    def get_signal_engine_analysis(self, days: int = 30) -> Dict:
        """
        Get comprehensive Signal Engine analysis for win rate enhancement.
        Analyzes correlation between Signal Engine alignment and trade outcomes.
        """
        with self.get_cursor() as cursor:
            # Signal Engine alignment stats
            cursor.execute('''
                SELECT 
                    COUNT(*) as total_validations,
                    SUM(signal_engine_aligned) as aligned_count,
                    SUM(CASE WHEN signal_engine_aligned = 0 THEN 1 ELSE 0 END) as not_aligned_count,
                    AVG(signal_engine_confidence_boost) as avg_confidence_boost,
                    signal_engine_nifty_signal,
                    COUNT(*) as signal_count
                FROM ai_validations 
                WHERE timestamp > datetime('now', ?)
                GROUP BY signal_engine_nifty_signal
            ''', (f'-{days} days',))
            nifty_distribution = [dict(row) for row in cursor.fetchall()]
            
            # Win rate when Signal Engine aligned
            cursor.execute('''
                SELECT 
                    a.signal_engine_aligned,
                    COUNT(t.id) as trade_count,
                    SUM(CASE WHEN t.realized_pnl > 0 THEN 1 ELSE 0 END) as wins,
                    AVG(t.realized_pnl) as avg_pnl,
                    SUM(t.realized_pnl) as total_pnl
                FROM ai_validations a
                LEFT JOIN trades t ON a.symbol = t.symbol 
                    AND DATE(a.timestamp) = DATE(t.entry_time)
                WHERE a.timestamp > datetime('now', ?)
                    AND t.status != 'OPEN'
                GROUP BY a.signal_engine_aligned
            ''', (f'-{days} days',))
            alignment_performance = [dict(row) for row in cursor.fetchall()]
            
            # Calculate win rates
            for perf in alignment_performance:
                trades = perf.get('trade_count', 0) or 0
                wins = perf.get('wins', 0) or 0
                perf['win_rate'] = (wins / trades * 100) if trades > 0 else 0
            
            # Overall stats
            cursor.execute('''
                SELECT 
                    COUNT(*) as total,
                    SUM(signal_engine_aligned) as aligned,
                    AVG(ai_confidence_score) as avg_score,
                    AVG(CASE WHEN signal_engine_aligned = 1 THEN ai_confidence_score END) as aligned_avg_score,
                    AVG(CASE WHEN signal_engine_aligned = 0 THEN ai_confidence_score END) as not_aligned_avg_score
                FROM ai_validations 
                WHERE timestamp > datetime('now', ?)
            ''', (f'-{days} days',))
            overview = dict(cursor.fetchone()) if cursor.fetchone() else {}
            
            return {
                'overview': overview,
                'nifty_signal_distribution': nifty_distribution,
                'alignment_performance': alignment_performance,
                'analysis_period_days': days
            }
    
    def get_winrate_breakdown(self, days: int = 30) -> Dict:
        """
        Comprehensive win rate breakdown for analysis and optimization.
        Useful for Copilot enhancement suggestions.
        """
        with self.get_cursor() as cursor:
            # By confidence level
            cursor.execute('''
                SELECT 
                    a.ai_confidence_level,
                    COUNT(t.id) as trade_count,
                    SUM(CASE WHEN t.realized_pnl > 0 THEN 1 ELSE 0 END) as wins,
                    AVG(t.realized_pnl) as avg_pnl
                FROM ai_validations a
                LEFT JOIN trades t ON a.symbol = t.symbol 
                    AND DATE(a.timestamp) = DATE(t.entry_time)
                WHERE a.timestamp > datetime('now', ?)
                    AND t.status != 'OPEN'
                GROUP BY a.ai_confidence_level
            ''', (f'-{days} days',))
            by_confidence = [dict(row) for row in cursor.fetchall()]
            
            # By pattern type
            cursor.execute('''
                SELECT 
                    a.pattern_confidence,
                    COUNT(t.id) as trade_count,
                    SUM(CASE WHEN t.realized_pnl > 0 THEN 1 ELSE 0 END) as wins,
                    AVG(t.realized_pnl) as avg_pnl
                FROM ai_validations a
                LEFT JOIN trades t ON a.symbol = t.symbol 
                    AND DATE(a.timestamp) = DATE(t.entry_time)
                WHERE a.timestamp > datetime('now', ?)
                    AND t.status != 'OPEN'
                GROUP BY a.pattern_confidence
            ''', (f'-{days} days',))
            by_pattern = [dict(row) for row in cursor.fetchall()]
            
            # By market alignment
            cursor.execute('''
                SELECT 
                    a.market_aligned,
                    COUNT(t.id) as trade_count,
                    SUM(CASE WHEN t.realized_pnl > 0 THEN 1 ELSE 0 END) as wins,
                    AVG(t.realized_pnl) as avg_pnl
                FROM ai_validations a
                LEFT JOIN trades t ON a.symbol = t.symbol 
                    AND DATE(a.timestamp) = DATE(t.entry_time)
                WHERE a.timestamp > datetime('now', ?)
                    AND t.status != 'OPEN'
                GROUP BY a.market_aligned
            ''', (f'-{days} days',))
            by_market = [dict(row) for row in cursor.fetchall()]
            
            # Calculate win rates
            for data in [by_confidence, by_pattern, by_market]:
                for item in data:
                    trades = item.get('trade_count', 0) or 0
                    wins = item.get('wins', 0) or 0
                    item['win_rate'] = (wins / trades * 100) if trades > 0 else 0
            
            return {
                'by_confidence_level': by_confidence,
                'by_pattern_type': by_pattern,
                'by_market_alignment': by_market,
                'analysis_period_days': days
            }

    # ========================================
    # MARKET CONTEXT OPERATIONS
    # ========================================
    
    def save_market_context(
        self,
        bullish_count: int,
        bearish_count: int,
        neutral_count: int,
        weighted_bias: str,
        strength_score: float,
        driver_sector: str = None,
        top_movers: List[str] = None,
        sector_divergence: str = None,
        vix_value: float = None,
        vix_change_pct: float = None,
        nifty_price: float = None,
        nifty_change_pct: float = None
    ) -> int:
        """Save market context snapshot"""
        with self.get_cursor() as cursor:
            cursor.execute('''
                INSERT INTO market_context (
                    bullish_count, bearish_count, neutral_count,
                    weighted_bias, strength_score, driver_sector,
                    top_movers, sector_divergence, vix_value,
                    vix_change_pct, nifty_price, nifty_change_pct
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                bullish_count, bearish_count, neutral_count,
                weighted_bias, strength_score, driver_sector,
                json.dumps(top_movers) if top_movers else None,
                sector_divergence, vix_value, vix_change_pct,
                nifty_price, nifty_change_pct
            ))
            return cursor.lastrowid
    
    def get_latest_market_context(self) -> Optional[Dict]:
        """Get latest market context"""
        with self.get_cursor() as cursor:
            cursor.execute('SELECT * FROM market_context ORDER BY timestamp DESC LIMIT 1')
            row = cursor.fetchone()
            return dict(row) if row else None
    
    # ========================================
    # DAILY SUMMARY OPERATIONS
    # ========================================
    
    def update_daily_summary(self, date: str = None):
        """Update or create daily summary for a date"""
        if date is None:
            date = datetime.now().strftime('%Y-%m-%d')
        
        with self.get_cursor() as cursor:
            # Get signal stats
            cursor.execute('''
                SELECT 
                    COUNT(*) as total_signals,
                    SUM(was_executed) as signals_executed
                FROM signals 
                WHERE DATE(timestamp) = ?
            ''', (date,))
            signal_stats = dict(cursor.fetchone())
            
            # Get trade stats
            cursor.execute('''
                SELECT 
                    COUNT(*) as total_trades,
                    SUM(CASE WHEN realized_pnl > 0 THEN 1 ELSE 0 END) as winning_trades,
                    SUM(CASE WHEN realized_pnl <= 0 AND status != 'OPEN' THEN 1 ELSE 0 END) as losing_trades,
                    SUM(realized_pnl) as total_pnl,
                    AVG(CASE WHEN realized_pnl > 0 THEN realized_pnl END) as avg_win,
                    AVG(CASE WHEN realized_pnl < 0 THEN realized_pnl END) as avg_loss
                FROM trades 
                WHERE DATE(entry_time) = ?
            ''', (date,))
            trade_stats = dict(cursor.fetchone())
            
            # Get AI stats
            cursor.execute('''
                SELECT 
                    SUM(ai_approved) as ai_approvals,
                    SUM(CASE WHEN ai_approved = 0 THEN 1 ELSE 0 END) as ai_rejections
                FROM ai_validations 
                WHERE DATE(timestamp) = ?
            ''', (date,))
            ai_stats = dict(cursor.fetchone())
            
            # Get market bias
            cursor.execute('''
                SELECT weighted_bias 
                FROM market_context 
                WHERE DATE(timestamp) = ?
                ORDER BY timestamp DESC LIMIT 1
            ''', (date,))
            market_row = cursor.fetchone()
            market_bias = market_row['weighted_bias'] if market_row else 'UNKNOWN'
            
            # Calculate derived stats
            total_trades = trade_stats.get('total_trades', 0) or 0
            winning = trade_stats.get('winning_trades', 0) or 0
            win_rate = (winning / total_trades * 100) if total_trades > 0 else 0
            
            avg_win = abs(trade_stats.get('avg_win', 0) or 0)
            avg_loss = abs(trade_stats.get('avg_loss', 0) or 1)
            profit_factor = avg_win / avg_loss if avg_loss > 0 else 0
            
            ai_approvals = ai_stats.get('ai_approvals', 0) or 0
            ai_rejections = ai_stats.get('ai_rejections', 0) or 0
            ai_total = ai_approvals + ai_rejections
            
            # Upsert daily summary
            cursor.execute('''
                INSERT OR REPLACE INTO daily_summary (
                    date, total_signals, signals_executed, signals_rejected,
                    total_trades, winning_trades, losing_trades, win_rate,
                    total_pnl, avg_win, avg_loss, profit_factor,
                    ai_approvals, ai_rejections, market_bias
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                date,
                signal_stats.get('total_signals', 0) or 0,
                signal_stats.get('signals_executed', 0) or 0,
                (signal_stats.get('total_signals', 0) or 0) - (signal_stats.get('signals_executed', 0) or 0),
                total_trades,
                winning,
                trade_stats.get('losing_trades', 0) or 0,
                win_rate,
                trade_stats.get('total_pnl', 0) or 0,
                avg_win,
                avg_loss,
                profit_factor,
                ai_approvals,
                ai_rejections,
                market_bias
            ))
    
    def get_daily_summary(self, date: str = None) -> Optional[Dict]:
        """Get daily summary for a date"""
        if date is None:
            date = datetime.now().strftime('%Y-%m-%d')
        
        with self.get_cursor() as cursor:
            cursor.execute('SELECT * FROM daily_summary WHERE date = ?', (date,))
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def get_weekly_summary(self) -> List[Dict]:
        """Get last 7 days summary"""
        with self.get_cursor() as cursor:
            cursor.execute('''
                SELECT * FROM daily_summary 
                WHERE date > DATE('now', '-7 days')
                ORDER BY date DESC
            ''')
            return [dict(row) for row in cursor.fetchall()]
    
    # ========================================
    # ENGINE LOG OPERATIONS
    # ========================================
    
    def log_engine_event(
        self,
        event_type: str,
        event_data: Dict = None,
        capital: float = None,
        paper_trading: bool = True,
        ai_enabled: bool = True,
        error_message: str = None
    ):
        """Log engine events (start, stop, error, etc.)"""
        with self.get_cursor() as cursor:
            cursor.execute('''
                INSERT INTO engine_logs (
                    event_type, event_data, capital, paper_trading,
                    ai_enabled, error_message
                ) VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                event_type,
                json.dumps(event_data) if event_data else None,
                capital,
                1 if paper_trading else 0,
                1 if ai_enabled else 0,
                error_message
            ))
    
    def get_engine_logs(self, hours: int = 24) -> List[Dict]:
        """Get recent engine logs"""
        with self.get_cursor() as cursor:
            cursor.execute('''
                SELECT * FROM engine_logs 
                WHERE timestamp > datetime('now', ?)
                ORDER BY timestamp DESC
            ''', (f'-{hours} hours',))
            return [dict(row) for row in cursor.fetchall()]
    
    # ========================================
    # ANALYTICS FOR COPILOT
    # ========================================
    
    def get_copilot_analysis_data(self) -> Dict:
        """
        Get comprehensive data for Copilot analysis
        Returns structured data for AI to analyze and suggest improvements
        """
        data = {
            "generated_at": datetime.now().isoformat(),
            "trade_statistics": self.get_trade_statistics(30),
            "ai_validation_stats": self.get_ai_validation_stats(7),
            "weekly_summary": self.get_weekly_summary(),
            "pattern_performance": self._get_pattern_performance(),
            "rsi_zone_performance": self._get_rsi_zone_performance(),
            "time_of_day_performance": self._get_time_performance(),
            "recent_losses": self._get_recent_losses(10),
            "market_context_correlation": self._get_market_correlation(),
            "recommendations": []
        }
        
        # Generate recommendations based on data
        data["recommendations"] = self._generate_recommendations(data)
        
        return data
    
    def _get_pattern_performance(self) -> Dict:
        """Analyze performance by pattern type"""
        with self.get_cursor() as cursor:
            cursor.execute('''
                SELECT 
                    s.patterns_matched,
                    COUNT(*) as signal_count,
                    SUM(CASE WHEN t.realized_pnl > 0 THEN 1 ELSE 0 END) as wins,
                    SUM(CASE WHEN t.realized_pnl <= 0 THEN 1 ELSE 0 END) as losses,
                    AVG(t.realized_pnl) as avg_pnl
                FROM signals s
                LEFT JOIN trades t ON s.id = t.signal_id
                WHERE t.status != 'OPEN' OR t.status IS NULL
                GROUP BY s.patterns_matched
            ''')
            
            pattern_stats = {}
            for row in cursor.fetchall():
                patterns = json.loads(row['patterns_matched']) if row['patterns_matched'] else []
                for pattern in patterns:
                    if pattern not in pattern_stats:
                        pattern_stats[pattern] = {'count': 0, 'wins': 0, 'losses': 0, 'total_pnl': 0}
                    pattern_stats[pattern]['count'] += 1
                    pattern_stats[pattern]['wins'] += row['wins'] or 0
                    pattern_stats[pattern]['losses'] += row['losses'] or 0
            
            # Calculate win rates
            for pattern, stats in pattern_stats.items():
                total = stats['wins'] + stats['losses']
                stats['win_rate'] = (stats['wins'] / total * 100) if total > 0 else 0
            
            return pattern_stats
    
    def _get_rsi_zone_performance(self) -> Dict:
        """Analyze performance by RSI zone"""
        with self.get_cursor() as cursor:
            cursor.execute('''
                SELECT 
                    CASE 
                        WHEN s.rsi <= 20 THEN 'LEGENDARY (<=20)'
                        WHEN s.rsi <= 25 THEN 'ULTRA (21-25)'
                        WHEN s.rsi <= 30 THEN 'PREMIUM (26-30)'
                        WHEN s.rsi <= 35 THEN 'STANDARD (31-35)'
                        ELSE 'OTHER (>35)'
                    END as rsi_zone,
                    COUNT(*) as signal_count,
                    SUM(CASE WHEN t.realized_pnl > 0 THEN 1 ELSE 0 END) as wins,
                    SUM(CASE WHEN t.realized_pnl <= 0 AND t.status != 'OPEN' THEN 1 ELSE 0 END) as losses,
                    AVG(t.realized_pnl) as avg_pnl
                FROM signals s
                LEFT JOIN trades t ON s.id = t.signal_id
                GROUP BY rsi_zone
                ORDER BY s.rsi
            ''')
            
            zones = {}
            for row in cursor.fetchall():
                zone = row['rsi_zone']
                wins = row['wins'] or 0
                losses = row['losses'] or 0
                total = wins + losses
                zones[zone] = {
                    'signal_count': row['signal_count'],
                    'wins': wins,
                    'losses': losses,
                    'win_rate': (wins / total * 100) if total > 0 else 0,
                    'avg_pnl': row['avg_pnl'] or 0
                }
            
            return zones
    
    def _get_time_performance(self) -> Dict:
        """Analyze performance by time of day"""
        with self.get_cursor() as cursor:
            cursor.execute('''
                SELECT 
                    CASE 
                        WHEN strftime('%H', entry_time) < '10' THEN 'OPENING (9:15-10:00)'
                        WHEN strftime('%H', entry_time) < '12' THEN 'MORNING (10:00-12:00)'
                        WHEN strftime('%H', entry_time) < '14' THEN 'AFTERNOON (12:00-14:00)'
                        ELSE 'CLOSING (14:00-15:30)'
                    END as time_slot,
                    COUNT(*) as trade_count,
                    SUM(CASE WHEN realized_pnl > 0 THEN 1 ELSE 0 END) as wins,
                    SUM(CASE WHEN realized_pnl <= 0 THEN 1 ELSE 0 END) as losses,
                    AVG(realized_pnl) as avg_pnl
                FROM trades 
                WHERE status != 'OPEN'
                GROUP BY time_slot
            ''')
            
            times = {}
            for row in cursor.fetchall():
                slot = row['time_slot']
                wins = row['wins'] or 0
                losses = row['losses'] or 0
                total = wins + losses
                times[slot] = {
                    'trade_count': row['trade_count'],
                    'wins': wins,
                    'losses': losses,
                    'win_rate': (wins / total * 100) if total > 0 else 0,
                    'avg_pnl': row['avg_pnl'] or 0
                }
            
            return times
    
    def _get_recent_losses(self, limit: int = 10) -> List[Dict]:
        """Get recent losing trades for analysis"""
        with self.get_cursor() as cursor:
            cursor.execute('''
                SELECT t.*, s.patterns_matched, s.rsi, s.confidence
                FROM trades t
                LEFT JOIN signals s ON t.signal_id = s.id
                WHERE t.realized_pnl < 0
                ORDER BY t.exit_time DESC
                LIMIT ?
            ''', (limit,))
            return [dict(row) for row in cursor.fetchall()]
    
    def _get_market_correlation(self) -> Dict:
        """Analyze trade performance vs market context"""
        with self.get_cursor() as cursor:
            cursor.execute('''
                SELECT 
                    m.weighted_bias,
                    COUNT(*) as trade_count,
                    SUM(CASE WHEN t.realized_pnl > 0 THEN 1 ELSE 0 END) as wins,
                    SUM(CASE WHEN t.realized_pnl <= 0 THEN 1 ELSE 0 END) as losses,
                    AVG(t.realized_pnl) as avg_pnl
                FROM trades t
                JOIN ai_validations av ON t.trade_id LIKE '%' || CAST(av.signal_id AS TEXT) || '%'
                JOIN market_context m ON DATE(m.timestamp) = DATE(t.entry_time)
                WHERE t.status != 'OPEN'
                GROUP BY m.weighted_bias
            ''')
            
            correlation = {}
            for row in cursor.fetchall():
                bias = row['weighted_bias'] or 'UNKNOWN'
                wins = row['wins'] or 0
                losses = row['losses'] or 0
                total = wins + losses
                correlation[bias] = {
                    'trade_count': row['trade_count'],
                    'wins': wins,
                    'losses': losses,
                    'win_rate': (wins / total * 100) if total > 0 else 0,
                    'avg_pnl': row['avg_pnl'] or 0
                }
            
            return correlation
    
    def _generate_recommendations(self, data: Dict) -> List[str]:
        """Generate strategy improvement recommendations"""
        recommendations = []
        
        # Check RSI zone performance
        rsi_perf = data.get('rsi_zone_performance', {})
        for zone, stats in rsi_perf.items():
            if stats.get('win_rate', 0) < 70 and stats.get('signal_count', 0) > 5:
                recommendations.append(f"Consider tightening criteria for {zone} zone (current WR: {stats['win_rate']:.1f}%)")
        
        # Check pattern performance
        pattern_perf = data.get('pattern_performance', {})
        weak_patterns = [p for p, s in pattern_perf.items() if s.get('win_rate', 0) < 60 and s.get('count', 0) > 3]
        if weak_patterns:
            recommendations.append(f"Review weak patterns: {', '.join(weak_patterns)}")
        
        # Check AI validation stats
        ai_stats = data.get('ai_validation_stats', {})
        if ai_stats.get('approval_rate', 0) > 80:
            recommendations.append("AI approval rate is high - consider stricter validation criteria")
        elif ai_stats.get('approval_rate', 0) < 30:
            recommendations.append("AI rejection rate is high - review signal quality or AI thresholds")
        
        # Check time performance
        time_perf = data.get('time_of_day_performance', {})
        for slot, stats in time_perf.items():
            if stats.get('win_rate', 0) < 60 and stats.get('trade_count', 0) > 5:
                recommendations.append(f"Avoid trading during {slot} (WR: {stats['win_rate']:.1f}%)")
        
        # Market correlation insights
        market_corr = data.get('market_context_correlation', {})
        if 'BEARISH' in market_corr and market_corr['BEARISH'].get('win_rate', 0) < 50:
            recommendations.append("Reduce position size in bearish market conditions")
        
        if not recommendations:
            recommendations.append("Strategy performing well - continue monitoring")
        
        return recommendations
    
    def export_for_copilot(self, filepath: str = None) -> str:
        """Export analysis data to JSON file for Copilot"""
        if filepath is None:
            filepath = os.path.join(os.path.dirname(self.db_path), 'copilot_analysis.json')
        
        data = self.get_copilot_analysis_data()
        
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2, default=str)
        
        logger.info(f"📊 Exported analysis data to {filepath}")
        return filepath
    
    def close(self):
        """Close database connection"""
        if hasattr(self._local, 'connection') and self._local.connection:
            self._local.connection.close()
            self._local.connection = None


# Global database instance
_db_instance = None

def get_database() -> TradingDatabase:
    """Get or create global database instance"""
    global _db_instance
    if _db_instance is None:
        _db_instance = TradingDatabase()
    return _db_instance


# Test function
def test_database():
    """Test database operations"""
    db = TradingDatabase(":memory:")  # Use in-memory for testing
    
    # Test signal
    signal_id = db.save_signal(
        symbol="RELIANCE",
        confidence="legendary",
        confidence_score=92.5,
        current_price=2500,
        entry_price=2500,
        target_price=2550,
        stop_loss=2487.5,
        rsi=21.5,
        patterns_matched=["OVERSOLD_REVERSAL", "MACD_REVERSAL"],
        volume_ratio=2.3
    )
    print(f"✅ Signal saved: ID={signal_id}")
    
    # Test trade
    db.save_trade(
        trade_id="WC20251208001",
        symbol="RELIANCE",
        entry_price=2500,
        quantity=4,
        entry_time=datetime.now(),
        target_price=2550,
        stop_loss=2487.5,
        signal_id=signal_id,
        ai_confidence=92.5,
        paper_trading=True
    )
    print("✅ Trade saved")
    
    # Test AI validation
    db.save_ai_validation(
        symbol="RELIANCE",
        pattern_confidence="legendary",
        ai_approved=True,
        ai_confidence_level="ULTRA",
        ai_confidence_score=88.5,
        position_multiplier=0.9,
        market_aligned=True,
        ai_signal_match=True,
        combined_thesis="Strong pattern with bullish market context",
        risk_factors=["VIX slightly elevated"],
        catalysts=["Oversold RSI", "Volume spike"],
        market_bullish_count=35,
        market_bearish_count=10,
        market_bias="BULLISH",
        signal_id=signal_id
    )
    print("✅ AI validation saved")
    
    # Test analytics
    analysis = db.get_copilot_analysis_data()
    print(f"✅ Analysis data: {len(analysis)} sections")
    
    print("\n✅ All database tests passed!")


if __name__ == "__main__":
    test_database()
