"""
SQLite Trade Performance Tracker
Tracks all trades, signals, and performance metrics for win rate analysis
"""

import sqlite3
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path
import json

logger = logging.getLogger(__name__)


class TradeTracker:
    """Track trades and performance metrics in SQLite"""
    
    def __init__(self, db_path: str = "trade_performance.db"):
        """Initialize tracker with database path"""
        self.db_path = db_path
        self._init_database()
        logger.info(f"TradeTracker initialized with database: {db_path}")
    
    def _init_database(self):
        """Create database tables if they don't exist"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Trades table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                trade_id TEXT UNIQUE,
                timestamp TEXT NOT NULL,
                symbol TEXT NOT NULL,
                instrument_type TEXT,
                side TEXT,
                entry_price REAL,
                exit_price REAL,
                quantity INTEGER,
                entry_time TEXT,
                exit_time TEXT,
                pnl REAL,
                pnl_percent REAL,
                status TEXT,
                signal_type TEXT,
                confidence REAL,
                momentum REAL,
                technical_score REAL,
                stop_loss REAL,
                target REAL,
                risk_reward REAL,
                strategy_params TEXT,
                notes TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Daily summary table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS daily_summary (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT UNIQUE NOT NULL,
                total_trades INTEGER DEFAULT 0,
                winning_trades INTEGER DEFAULT 0,
                losing_trades INTEGER DEFAULT 0,
                break_even_trades INTEGER DEFAULT 0,
                total_pnl REAL DEFAULT 0,
                gross_profit REAL DEFAULT 0,
                gross_loss REAL DEFAULT 0,
                win_rate REAL DEFAULT 0,
                avg_win REAL DEFAULT 0,
                avg_loss REAL DEFAULT 0,
                profit_factor REAL DEFAULT 0,
                sharpe_ratio REAL DEFAULT 0,
                max_drawdown REAL DEFAULT 0,
                largest_win REAL DEFAULT 0,
                largest_loss REAL DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Signals table (for tracking signal generation vs execution)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS signals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                signal_id TEXT UNIQUE,
                timestamp TEXT NOT NULL,
                symbol TEXT NOT NULL,
                signal_type TEXT,
                confidence REAL,
                entry_price REAL,
                target REAL,
                stop_loss REAL,
                risk_reward REAL,
                technical_score REAL,
                executed BOOLEAN DEFAULT 0,
                execution_time TEXT,
                outcome TEXT,
                reason_not_executed TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
        logger.info("Database tables initialized successfully")
    
    def log_trade(self, trade_data: Dict[str, Any]) -> bool:
        """Log a completed trade"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Serialize strategy params if present
            strategy_params = trade_data.get('strategy_params')
            if strategy_params and not isinstance(strategy_params, str):
                strategy_params = json.dumps(strategy_params)
            
            cursor.execute('''
                INSERT OR REPLACE INTO trades (
                    trade_id, timestamp, symbol, instrument_type, side,
                    entry_price, exit_price, quantity, entry_time, exit_time,
                    pnl, pnl_percent, status, signal_type, confidence,
                    momentum, technical_score, stop_loss, target, risk_reward,
                    strategy_params, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                trade_data.get('trade_id', f"trade-{datetime.now().timestamp()}"),
                trade_data.get('timestamp', datetime.now().isoformat()),
                trade_data['symbol'],
                trade_data.get('instrument_type', 'INDEX'),
                trade_data.get('side', 'BUY'),
                trade_data.get('entry_price', 0),
                trade_data.get('exit_price', 0),
                trade_data.get('quantity', 0),
                trade_data.get('entry_time'),
                trade_data.get('exit_time'),
                trade_data.get('pnl', 0),
                trade_data.get('pnl_percent', 0),
                trade_data.get('status', 'COMPLETED'),
                trade_data.get('signal_type', 'SCALP'),
                trade_data.get('confidence', 0.5),
                trade_data.get('momentum', 0),
                trade_data.get('technical_score', 0),
                trade_data.get('stop_loss', 0),
                trade_data.get('target', 0),
                trade_data.get('risk_reward', 0),
                strategy_params,
                trade_data.get('notes', '')
            ))
            
            conn.commit()
            conn.close()
            
            # Update daily summary
            self._update_daily_summary(trade_data.get('timestamp', datetime.now().isoformat()))
            
            logger.info(f"Trade logged: {trade_data.get('trade_id')} PnL: {trade_data.get('pnl', 0)}")
            return True
            
        except Exception as e:
            logger.error(f"Error logging trade: {e}")
            return False
    
    def log_signal(self, signal_data: Dict[str, Any]) -> bool:
        """Log a generated signal"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO signals (
                    signal_id, timestamp, symbol, signal_type, confidence,
                    entry_price, target, stop_loss, risk_reward, technical_score,
                    executed, execution_time, outcome, reason_not_executed
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                signal_data.get('signal_id', f"signal-{datetime.now().timestamp()}"),
                signal_data.get('timestamp', datetime.now().isoformat()),
                signal_data['symbol'],
                signal_data.get('signal_type', 'BUY'),
                signal_data.get('confidence', 0.5),
                signal_data.get('entry_price', 0),
                signal_data.get('target', 0),
                signal_data.get('stop_loss', 0),
                signal_data.get('risk_reward', 0),
                signal_data.get('technical_score', 0),
                signal_data.get('executed', False),
                signal_data.get('execution_time'),
                signal_data.get('outcome'),
                signal_data.get('reason_not_executed')
            ))
            
            conn.commit()
            conn.close()
            
            logger.info(f"Signal logged: {signal_data.get('signal_id')}")
            return True
            
        except Exception as e:
            logger.error(f"Error logging signal: {e}")
            return False
    
    def _update_daily_summary(self, date_str: str):
        """Update daily summary statistics"""
        try:
            date = date_str.split('T')[0]  # Extract date part
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get all trades for the day
            cursor.execute('''
                SELECT pnl, pnl_percent FROM trades 
                WHERE DATE(timestamp) = ? AND status = 'COMPLETED'
            ''', (date,))
            
            trades = cursor.fetchall()
            
            if not trades:
                conn.close()
                return
            
            total_trades = len(trades)
            pnls = [t[0] for t in trades if t[0] is not None]
            
            winning_trades = len([p for p in pnls if p > 0])
            losing_trades = len([p for p in pnls if p < 0])
            break_even_trades = len([p for p in pnls if p == 0])
            
            total_pnl = sum(pnls)
            gross_profit = sum([p for p in pnls if p > 0])
            gross_loss = abs(sum([p for p in pnls if p < 0]))
            
            win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
            avg_win = (gross_profit / winning_trades) if winning_trades > 0 else 0
            avg_loss = (gross_loss / losing_trades) if losing_trades > 0 else 0
            profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else 0
            
            largest_win = max(pnls) if pnls else 0
            largest_loss = min(pnls) if pnls else 0
            
            cursor.execute('''
                INSERT OR REPLACE INTO daily_summary (
                    date, total_trades, winning_trades, losing_trades, break_even_trades,
                    total_pnl, gross_profit, gross_loss, win_rate, avg_win, avg_loss,
                    profit_factor, largest_win, largest_loss, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                date, total_trades, winning_trades, losing_trades, break_even_trades,
                total_pnl, gross_profit, gross_loss, win_rate, avg_win, avg_loss,
                profit_factor, largest_win, largest_loss, datetime.now().isoformat()
            ))
            
            conn.commit()
            conn.close()
            
            logger.info(f"Daily summary updated for {date}: Win Rate: {win_rate:.2f}%")
            
        except Exception as e:
            logger.error(f"Error updating daily summary: {e}")
    
    def get_daily_stats(self, date: Optional[str] = None) -> Dict[str, Any]:
        """Get statistics for a specific date or today"""
        if date is None:
            date = datetime.now().strftime('%Y-%m-%d')
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT * FROM daily_summary WHERE date = ?
            ''', (date,))
            
            row = cursor.fetchone()
            conn.close()
            
            if not row:
                return {"date": date, "message": "No trades for this date"}
            
            columns = [desc[0] for desc in cursor.description]
            return dict(zip(columns, row))
            
        except Exception as e:
            logger.error(f"Error getting daily stats: {e}")
            return {"error": str(e)}
    
    def get_recent_trades(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent trades"""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT * FROM trades 
                ORDER BY timestamp DESC 
                LIMIT ?
            ''', (limit,))
            
            rows = cursor.fetchall()
            conn.close()
            
            return [dict(row) for row in rows]
            
        except Exception as e:
            logger.error(f"Error getting recent trades: {e}")
            return []
    
    def get_performance_summary(self, days: int = 30) -> Dict[str, Any]:
        """Get overall performance summary for last N days"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT 
                    COUNT(*) as total_trades,
                    SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) as winning_trades,
                    SUM(CASE WHEN pnl < 0 THEN 1 ELSE 0 END) as losing_trades,
                    SUM(pnl) as total_pnl,
                    AVG(pnl) as avg_pnl,
                    MAX(pnl) as best_trade,
                    MIN(pnl) as worst_trade,
                    AVG(CASE WHEN pnl > 0 THEN pnl END) as avg_win,
                    AVG(CASE WHEN pnl < 0 THEN pnl END) as avg_loss
                FROM trades 
                WHERE DATE(timestamp) >= DATE('now', '-' || ? || ' days')
                AND status = 'COMPLETED'
            ''', (days,))
            
            row = cursor.fetchone()
            conn.close()
            
            if not row or row[0] == 0:
                return {"message": f"No trades in last {days} days"}
            
            total_trades = row[0]
            winning_trades = row[1] or 0
            losing_trades = row[2] or 0
            total_pnl = row[3] or 0
            avg_pnl = row[4] or 0
            best_trade = row[5] or 0
            worst_trade = row[6] or 0
            avg_win = row[7] or 0
            avg_loss = row[8] or 0
            
            win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
            profit_factor = (avg_win / abs(avg_loss)) if avg_loss != 0 else 0
            
            return {
                "period_days": days,
                "total_trades": total_trades,
                "winning_trades": winning_trades,
                "losing_trades": losing_trades,
                "win_rate": round(win_rate, 2),
                "total_pnl": round(total_pnl, 2),
                "avg_pnl_per_trade": round(avg_pnl, 2),
                "best_trade": round(best_trade, 2),
                "worst_trade": round(worst_trade, 2),
                "avg_win": round(avg_win, 2),
                "avg_loss": round(avg_loss, 2),
                "profit_factor": round(profit_factor, 2)
            }
            
        except Exception as e:
            logger.error(f"Error getting performance summary: {e}")
            return {"error": str(e)}
