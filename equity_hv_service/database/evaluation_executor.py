"""
Evaluation Trading Executor for Elite Equity HV Service
========================================================
Runs complete trade logic including order creation but:
- Does NOT send orders to exchange
- Logs everything as if real trade happened
- Tracks simulated fills based on market data
- Can be switched to production with single API call

This is separate from paper trading to keep production code unchanged.
"""

import logging
import uuid
from datetime import datetime, date
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from enum import Enum
import json
import sqlite3
from pathlib import Path

logger = logging.getLogger(__name__)


class ExecutionMode(Enum):
    """Trading execution modes"""
    PAPER = "paper"           # Simulated trades, no order creation
    EVALUATION = "evaluation" # Full logic with order creation, but not sent to exchange
    PRODUCTION = "production" # Real trades sent to exchange


# Alias for backward compatibility
EvaluationMode = ExecutionMode


@dataclass
class EvaluationOrder:
    """Order that would have been sent to exchange"""
    order_id: str
    trade_id: str
    timestamp: datetime
    symbol: str
    transaction_type: str  # BUY or SELL
    order_type: str  # MARKET or LIMIT
    quantity: int
    price: float
    simulated_fill_price: float
    slippage_applied: float
    status: str
    exchange_segment: str = "NSE_EQ"
    correlation_id: str = ""
    order_payload: Dict = field(default_factory=dict)


@dataclass
class EvaluationTrade:
    """Evaluation trade record"""
    trade_id: str
    timestamp_entry: datetime
    timestamp_exit: Optional[datetime] = None
    symbol: str = ""
    direction: str = ""  # LONG or SHORT
    entry_price: float = 0.0
    exit_price: float = 0.0
    quantity: int = 0
    pnl: float = 0.0
    pnl_percent: float = 0.0
    status: str = "open"
    entry_reason: str = ""
    exit_reason: str = ""
    signal_strength: float = 0.0
    ai_confidence: float = 0.0
    gemini_decision: str = ""
    gemini_reasoning: str = ""
    max_profit: float = 0.0
    max_loss: float = 0.0
    duration_seconds: int = 0
    strategy_type: str = ""


class EquityEvaluationDatabase:
    """
    Dedicated SQLite database for Elite Equity HV evaluation mode
    Stores all data needed to analyze strategy performance
    """
    
    def __init__(self, db_path: str = None):
        if db_path is None:
            db_dir = Path(__file__).parent
            db_dir.mkdir(exist_ok=True)
            db_path = str(db_dir / "equity_evaluation.db")
        
        self.db_path = db_path
        self._init_database()
        logger.info(f"Equity evaluation database initialized: {db_path}")
    
    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def _init_database(self):
        """Initialize evaluation-specific tables"""
        conn = self._get_conn()
        cursor = conn.cursor()
        
        # Execution mode tracking
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS execution_mode (
                id INTEGER PRIMARY KEY,
                mode TEXT NOT NULL DEFAULT 'evaluation',
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_by TEXT DEFAULT 'system',
                notes TEXT
            )
        """)
        
        # Orders that would have been sent
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS evaluation_orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id TEXT UNIQUE NOT NULL,
                trade_id TEXT NOT NULL,
                timestamp TIMESTAMP NOT NULL,
                symbol TEXT NOT NULL,
                transaction_type TEXT NOT NULL,
                order_type TEXT NOT NULL,
                quantity INTEGER NOT NULL,
                requested_price REAL,
                simulated_fill_price REAL,
                slippage_applied REAL,
                status TEXT DEFAULT 'SIMULATED_FILLED',
                exchange_segment TEXT DEFAULT 'NSE_EQ',
                correlation_id TEXT,
                order_payload TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Evaluation trades with full details
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS evaluation_trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                trade_id TEXT UNIQUE NOT NULL,
                timestamp_entry TIMESTAMP NOT NULL,
                timestamp_exit TIMESTAMP,
                symbol TEXT NOT NULL,
                direction TEXT,
                entry_price REAL NOT NULL,
                exit_price REAL,
                quantity INTEGER NOT NULL,
                pnl REAL DEFAULT 0,
                pnl_percent REAL DEFAULT 0,
                status TEXT DEFAULT 'open',
                entry_reason TEXT,
                exit_reason TEXT,
                signal_strength REAL,
                ai_confidence REAL,
                gemini_decision TEXT,
                gemini_reasoning TEXT,
                strategy_type TEXT,
                duration_seconds INTEGER,
                max_profit REAL DEFAULT 0,
                max_loss REAL DEFAULT 0,
                market_conditions TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Daily evaluation summary
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS daily_evaluation_summary (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date DATE UNIQUE NOT NULL,
                total_orders_created INTEGER DEFAULT 0,
                total_trades INTEGER DEFAULT 0,
                winning_trades INTEGER DEFAULT 0,
                losing_trades INTEGER DEFAULT 0,
                win_rate REAL DEFAULT 0,
                total_pnl REAL DEFAULT 0,
                avg_trade_duration INTEGER DEFAULT 0,
                avg_signal_strength REAL DEFAULT 0,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Signal decisions log
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS signal_decisions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TIMESTAMP NOT NULL,
                symbol TEXT NOT NULL,
                signal_type TEXT,
                direction TEXT,
                signal_strength REAL,
                ai_confidence REAL,
                gemini_decision TEXT,
                gemini_reasoning TEXT,
                was_executed INTEGER DEFAULT 0,
                skip_reason TEXT,
                market_price REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Alpha signals tracking
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS alpha_signals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TIMESTAMP NOT NULL,
                symbol TEXT NOT NULL,
                alpha_type TEXT,
                signal_value REAL,
                regime TEXT,
                factor_exposures TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_equity_orders_trade ON evaluation_orders(trade_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_equity_trades_date ON evaluation_trades(timestamp_entry)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_equity_trades_status ON evaluation_trades(status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_equity_trades_symbol ON evaluation_trades(symbol)")
        
        # Initialize mode if not exists
        cursor.execute("SELECT COUNT(*) FROM execution_mode")
        if cursor.fetchone()[0] == 0:
            cursor.execute("INSERT INTO execution_mode (mode, notes) VALUES ('paper', 'Initial setup')")
        
        conn.commit()
        conn.close()
    
    def get_execution_mode(self) -> ExecutionMode:
        """Get current execution mode"""
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT mode FROM execution_mode ORDER BY id DESC LIMIT 1")
        row = cursor.fetchone()
        conn.close()
        try:
            return ExecutionMode(row['mode']) if row else ExecutionMode.PAPER
        except ValueError:
            return ExecutionMode.PAPER
    
    def set_execution_mode(self, mode: ExecutionMode, updated_by: str = "api", notes: str = "") -> bool:
        """Set execution mode"""
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO execution_mode (mode, updated_by, notes) VALUES (?, ?, ?)
        """, (mode.value, updated_by, notes))
        conn.commit()
        conn.close()
        logger.info(f"Equity execution mode changed to: {mode.value} by {updated_by}")
        return True
    
    def save_order(self, order: EvaluationOrder) -> int:
        """Save an evaluation order"""
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO evaluation_orders (
                order_id, trade_id, timestamp, symbol,
                transaction_type, order_type, quantity, requested_price,
                simulated_fill_price, slippage_applied, status, 
                exchange_segment, correlation_id, order_payload
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            order.order_id, order.trade_id, order.timestamp, order.symbol,
            order.transaction_type, order.order_type, order.quantity, order.price,
            order.simulated_fill_price, order.slippage_applied, order.status,
            order.exchange_segment, order.correlation_id, json.dumps(order.order_payload)
        ))
        conn.commit()
        last_id = cursor.lastrowid
        conn.close()
        return last_id
    
    def save_trade(self, trade: EvaluationTrade) -> int:
        """Save a new trade entry"""
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO evaluation_trades (
                trade_id, timestamp_entry, symbol, direction,
                entry_price, quantity, status, entry_reason,
                signal_strength, ai_confidence, gemini_decision,
                gemini_reasoning, strategy_type
            ) VALUES (?, ?, ?, ?, ?, ?, 'open', ?, ?, ?, ?, ?, ?)
        """, (
            trade.trade_id, trade.timestamp_entry, trade.symbol, trade.direction,
            trade.entry_price, trade.quantity, trade.entry_reason,
            trade.signal_strength, trade.ai_confidence, trade.gemini_decision,
            trade.gemini_reasoning, trade.strategy_type
        ))
        conn.commit()
        last_id = cursor.lastrowid
        conn.close()
        return last_id
    
    def update_trade_exit(self, trade_id: str, exit_data: Dict) -> bool:
        """Update trade with exit data"""
        conn = self._get_conn()
        cursor = conn.cursor()
        
        # Calculate duration
        cursor.execute("SELECT timestamp_entry FROM evaluation_trades WHERE trade_id = ?", (trade_id,))
        row = cursor.fetchone()
        duration = 0
        if row:
            entry_time = datetime.fromisoformat(row['timestamp_entry'])
            duration = int((datetime.now() - entry_time).total_seconds())
        
        cursor.execute("""
            UPDATE evaluation_trades SET
                timestamp_exit = ?,
                exit_price = ?,
                pnl = ?,
                pnl_percent = ?,
                status = 'closed',
                exit_reason = ?,
                duration_seconds = ?,
                max_profit = ?,
                max_loss = ?
            WHERE trade_id = ?
        """, (
            datetime.now().isoformat(),
            exit_data.get('exit_price', 0),
            exit_data.get('pnl', 0),
            exit_data.get('pnl_percent', 0),
            exit_data.get('exit_reason', ''),
            duration,
            exit_data.get('max_profit', 0),
            exit_data.get('max_loss', 0),
            trade_id
        ))
        conn.commit()
        conn.close()
        return True
    
    def update_trade_mfe_mae(self, trade_id: str, current_price: float, entry_price: float, direction: str):
        """Update maximum favorable/adverse excursion"""
        conn = self._get_conn()
        cursor = conn.cursor()
        
        if direction == "LONG":
            current_pnl = current_price - entry_price
        else:
            current_pnl = entry_price - current_price
        
        cursor.execute("SELECT max_profit, max_loss FROM evaluation_trades WHERE trade_id = ?", (trade_id,))
        row = cursor.fetchone()
        if row:
            max_profit = max(row['max_profit'] or 0, current_pnl)
            max_loss = min(row['max_loss'] or 0, current_pnl)
            cursor.execute("""
                UPDATE evaluation_trades SET max_profit = ?, max_loss = ? WHERE trade_id = ?
            """, (max_profit, max_loss, trade_id))
            conn.commit()
        conn.close()
    
    def save_signal_decision(self, decision: Dict) -> int:
        """Save a signal decision"""
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO signal_decisions (
                timestamp, symbol, signal_type, direction, signal_strength,
                ai_confidence, gemini_decision, gemini_reasoning,
                was_executed, skip_reason, market_price
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            datetime.now().isoformat(),
            decision.get('symbol', ''),
            decision.get('signal_type', ''),
            decision.get('direction', ''),
            decision.get('signal_strength', 0),
            decision.get('ai_confidence', 0),
            decision.get('gemini_decision', ''),
            decision.get('gemini_reasoning', ''),
            1 if decision.get('was_executed', False) else 0,
            decision.get('skip_reason', ''),
            decision.get('market_price', 0)
        ))
        conn.commit()
        last_id = cursor.lastrowid
        conn.close()
        return last_id
    
    def save_alpha_signal(self, alpha: Dict) -> int:
        """Save an alpha signal"""
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO alpha_signals (
                timestamp, symbol, alpha_type, signal_value, regime, factor_exposures
            ) VALUES (?, ?, ?, ?, ?, ?)
        """, (
            datetime.now().isoformat(),
            alpha.get('symbol', ''),
            alpha.get('alpha_type', ''),
            alpha.get('signal_value', 0),
            alpha.get('regime', ''),
            json.dumps(alpha.get('factor_exposures', {}))
        ))
        conn.commit()
        last_id = cursor.lastrowid
        conn.close()
        return last_id
    
    def get_open_trades(self) -> List[Dict]:
        """Get all open evaluation trades"""
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM evaluation_trades WHERE status = 'open'")
        trades = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return trades
    
    def get_recent_trades(self, limit: int = 100) -> List[Dict]:
        """Get recent evaluation trades"""
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM evaluation_trades ORDER BY timestamp_entry DESC LIMIT ?
        """, (limit,))
        trades = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return trades
    
    def get_trades_by_symbol(self, symbol: str, limit: int = 50) -> List[Dict]:
        """Get trades for a specific symbol"""
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM evaluation_trades WHERE symbol = ?
            ORDER BY timestamp_entry DESC LIMIT ?
        """, (symbol, limit))
        trades = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return trades
    
    def get_signal_decisions(self, limit: int = 100) -> List[Dict]:
        """Get recent signal decisions"""
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM signal_decisions ORDER BY timestamp DESC LIMIT ?
        """, (limit,))
        signals = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return signals
    
    def get_daily_summary(self, target_date: date = None) -> Dict:
        """Get daily evaluation summary"""
        if target_date is None:
            target_date = date.today()
        
        conn = self._get_conn()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                COUNT(*) as total_trades,
                SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) as winning_trades,
                SUM(CASE WHEN pnl <= 0 AND status = 'closed' THEN 1 ELSE 0 END) as losing_trades,
                SUM(pnl) as total_pnl,
                AVG(duration_seconds) as avg_duration,
                AVG(signal_strength) as avg_signal_strength
            FROM evaluation_trades 
            WHERE DATE(timestamp_entry) = ?
        """, (target_date.isoformat(),))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            total = row['total_trades'] or 0
            wins = row['winning_trades'] or 0
            return {
                'date': target_date.isoformat(),
                'total_trades': total,
                'winning_trades': wins,
                'losing_trades': row['losing_trades'] or 0,
                'win_rate': (wins / total * 100) if total > 0 else 0,
                'total_pnl': row['total_pnl'] or 0,
                'avg_duration_seconds': row['avg_duration'] or 0,
                'avg_signal_strength': row['avg_signal_strength'] or 0
            }
        return {'date': target_date.isoformat(), 'total_trades': 0}
    
    def get_performance_metrics(self) -> Dict:
        """Get overall performance metrics"""
        conn = self._get_conn()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                COUNT(*) as total_trades,
                SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) as winning_trades,
                SUM(CASE WHEN pnl <= 0 AND status = 'closed' THEN 1 ELSE 0 END) as losing_trades,
                SUM(pnl) as total_pnl,
                AVG(pnl) as avg_pnl,
                MAX(pnl) as best_trade,
                MIN(pnl) as worst_trade,
                AVG(duration_seconds) as avg_duration,
                AVG(signal_strength) as avg_signal_strength,
                SUM(CASE WHEN status = 'open' THEN 1 ELSE 0 END) as open_trades,
                COUNT(DISTINCT symbol) as symbols_traded
            FROM evaluation_trades
        """)
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            total = row['total_trades'] or 0
            wins = row['winning_trades'] or 0
            open_trades = row['open_trades'] or 0
            closed = total - open_trades
            return {
                'total_trades': total,
                'winning_trades': wins,
                'losing_trades': row['losing_trades'] or 0,
                'open_trades': open_trades,
                'win_rate': (wins / closed * 100) if closed > 0 else 0,
                'total_pnl': row['total_pnl'] or 0,
                'avg_pnl': row['avg_pnl'] or 0,
                'best_trade': row['best_trade'] or 0,
                'worst_trade': row['worst_trade'] or 0,
                'avg_duration_seconds': row['avg_duration'] or 0,
                'avg_signal_strength': row['avg_signal_strength'] or 0,
                'symbols_traded': row['symbols_traded'] or 0
            }
        return {'total_trades': 0}
    
    def clear_all_data(self):
        """Clear all evaluation data"""
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM evaluation_trades")
        cursor.execute("DELETE FROM evaluation_orders")
        cursor.execute("DELETE FROM signal_decisions")
        cursor.execute("DELETE FROM alpha_signals")
        conn.commit()
        conn.close()
        logger.info("All equity evaluation data cleared")


class EquityEvaluationExecutor:
    """
    Evaluation executor for equity trades
    Simulates trade execution without sending to exchange
    """
    
    def __init__(self, initial_capital: float = 500000):
        self._db = EquityEvaluationDatabase()
        self._initial_capital = initial_capital
        self._current_capital = initial_capital
        self._positions: Dict[str, EvaluationTrade] = {}
        self._session_id = str(uuid.uuid4())[:8]
        self._session_pnl = 0.0
        self._session_trades = 0
        
        # Load any open positions from DB
        self._load_open_positions()
        logger.info(f"Equity Evaluation Executor initialized. Session: {self._session_id}")
    
    def _load_open_positions(self):
        """Load open positions from database"""
        open_trades = self._db.get_open_trades()
        for trade in open_trades:
            self._positions[trade['trade_id']] = EvaluationTrade(
                trade_id=trade['trade_id'],
                timestamp_entry=datetime.fromisoformat(trade['timestamp_entry']),
                symbol=trade['symbol'],
                direction=trade['direction'],
                entry_price=trade['entry_price'],
                quantity=trade['quantity'],
                signal_strength=trade.get('signal_strength', 0)
            )
        logger.info(f"Loaded {len(self._positions)} open evaluation positions")
    
    @property
    def mode(self) -> ExecutionMode:
        return self._db.get_execution_mode()
    
    def enable_evaluation(self) -> Dict:
        """Enable evaluation mode"""
        self._db.set_execution_mode(ExecutionMode.EVALUATION, "api", "Evaluation mode enabled")
        return {"success": True, "mode": "evaluation"}
    
    def disable_evaluation(self, target_mode: str = "paper") -> Dict:
        """Disable evaluation mode"""
        mode = ExecutionMode.PAPER if target_mode == "paper" else ExecutionMode.PRODUCTION
        self._db.set_execution_mode(mode, "api", f"Switched to {target_mode}")
        return {"success": True, "mode": target_mode}
    
    def enter_position(
        self,
        symbol: str,
        direction: str,
        quantity: int,
        entry_price: float,
        signal_strength: float = 0,
        ai_confidence: float = 0,
        gemini_decision: str = "",
        gemini_reasoning: str = "",
        entry_reason: str = "",
        strategy_type: str = ""
    ) -> Optional[str]:
        """Enter a new evaluation position"""
        trade_id = f"EQ-EVAL-{self._session_id}-{len(self._positions)+1:04d}"
        
        # Create order
        order = EvaluationOrder(
            order_id=f"ORD-{trade_id}",
            trade_id=trade_id,
            timestamp=datetime.now(),
            symbol=symbol,
            transaction_type="BUY" if direction == "LONG" else "SELL",
            order_type="MARKET",
            quantity=quantity,
            price=entry_price,
            simulated_fill_price=entry_price,
            slippage_applied=0,
            status="SIMULATED_FILLED",
            correlation_id=self._session_id
        )
        self._db.save_order(order)
        
        # Create trade
        trade = EvaluationTrade(
            trade_id=trade_id,
            timestamp_entry=datetime.now(),
            symbol=symbol,
            direction=direction,
            entry_price=entry_price,
            quantity=quantity,
            signal_strength=signal_strength,
            ai_confidence=ai_confidence,
            gemini_decision=gemini_decision,
            gemini_reasoning=gemini_reasoning,
            entry_reason=entry_reason,
            strategy_type=strategy_type
        )
        self._db.save_trade(trade)
        self._positions[trade_id] = trade
        self._session_trades += 1
        
        logger.info(f"[EQ-EVAL] Entered {direction} {symbol} @ {entry_price} | ID: {trade_id}")
        
        # Log signal decision
        self._db.save_signal_decision({
            'symbol': symbol,
            'signal_type': 'ENTRY',
            'direction': direction,
            'signal_strength': signal_strength,
            'ai_confidence': ai_confidence,
            'gemini_decision': gemini_decision,
            'gemini_reasoning': gemini_reasoning,
            'was_executed': True,
            'market_price': entry_price
        })
        
        return trade_id
    
    def exit_position(
        self,
        trade_id: str,
        exit_price: float,
        exit_reason: str = ""
    ) -> Optional[float]:
        """Exit an evaluation position"""
        if trade_id not in self._positions:
            logger.warning(f"Trade {trade_id} not found in positions")
            return None
        
        trade = self._positions[trade_id]
        
        # Calculate PnL
        if trade.direction == "LONG":
            pnl = (exit_price - trade.entry_price) * trade.quantity
        else:
            pnl = (trade.entry_price - exit_price) * trade.quantity
        
        pnl_percent = (pnl / (trade.entry_price * trade.quantity)) * 100
        
        # Create exit order
        order = EvaluationOrder(
            order_id=f"ORD-EXIT-{trade_id}",
            trade_id=trade_id,
            timestamp=datetime.now(),
            symbol=trade.symbol,
            transaction_type="SELL" if trade.direction == "LONG" else "BUY",
            order_type="MARKET",
            quantity=trade.quantity,
            price=exit_price,
            simulated_fill_price=exit_price,
            slippage_applied=0,
            status="SIMULATED_FILLED",
            correlation_id=self._session_id
        )
        self._db.save_order(order)
        
        # Update trade in DB
        self._db.update_trade_exit(trade_id, {
            'exit_price': exit_price,
            'pnl': pnl,
            'pnl_percent': pnl_percent,
            'exit_reason': exit_reason,
            'max_profit': trade.max_profit,
            'max_loss': trade.max_loss
        })
        
        # Update session stats
        self._session_pnl += pnl
        self._current_capital += pnl
        
        # Remove from active positions
        del self._positions[trade_id]
        
        logger.info(f"[EQ-EVAL] Exited {trade.symbol} @ {exit_price} | PnL: {pnl:.2f} ({pnl_percent:.2f}%)")
        
        return pnl
    
    def get_open_positions(self) -> List[Dict]:
        """Get all open positions"""
        return [
            {
                'trade_id': t.trade_id,
                'symbol': t.symbol,
                'direction': t.direction,
                'entry_price': t.entry_price,
                'quantity': t.quantity,
                'entry_time': t.timestamp_entry.isoformat(),
                'signal_strength': t.signal_strength
            }
            for t in self._positions.values()
        ]
    
    def update_position_price(self, trade_id: str, current_price: float):
        """Update position price and track MFE/MAE"""
        if trade_id in self._positions:
            trade = self._positions[trade_id]
            # Calculate current P&L
            if trade.direction == "LONG":
                pnl = (current_price - trade.entry_price) * trade.quantity
            else:
                pnl = (trade.entry_price - current_price) * trade.quantity
            
            # Update MFE/MAE
            trade.max_profit = max(trade.max_profit, pnl)
            trade.max_loss = min(trade.max_loss, pnl)
    
    def check_exits(self, current_prices: Dict[str, float], alpha_signals: Dict[str, Dict] = None) -> List[Dict]:
        """
        INTELLIGENT EXIT LOGIC for Equity trades
        - Factor-based signal reversals
        - Trailing profit protection
        - Adaptive stop loss
        - Time-based considerations
        
        Args:
            current_prices: Dict of symbol -> current price
            alpha_signals: Dict of symbol -> signal info from alpha engine
        """
        results = []
        
        for trade_id, trade in list(self._positions.items()):
            symbol = trade.symbol
            current_price = current_prices.get(symbol)
            
            if current_price is None:
                continue
            
            # Calculate current P&L
            if trade.direction == "LONG":
                pnl = (current_price - trade.entry_price) * trade.quantity
                pnl_pct = ((current_price - trade.entry_price) / trade.entry_price) * 100
            else:
                pnl = (trade.entry_price - current_price) * trade.quantity
                pnl_pct = ((trade.entry_price - current_price) / trade.entry_price) * 100
            
            # Update MFE/MAE
            trade.max_profit = max(trade.max_profit, pnl)
            trade.max_loss = min(trade.max_loss, pnl)
            
            hold_time = (datetime.now() - trade.timestamp_entry).total_seconds() / 60
            
            exit_reason = None
            
            # Get alpha signal if available
            signal_info = alpha_signals.get(symbol, {}) if alpha_signals else {}
            signal_direction = signal_info.get('direction', 'neutral')
            signal_strength = signal_info.get('strength', 0)
            
            # =====================================================
            # INTELLIGENT EQUITY EXIT STRATEGY
            # =====================================================
            
            # 1. ALPHA SIGNAL REVERSAL
            if trade.direction == "LONG" and signal_direction in ["SELL", "SHORT", "bearish"]:
                if pnl_pct > 0.5:  # Lock even small profit on reversal
                    exit_reason = f"alpha_reversal_profit_lock ({pnl_pct:.2f}%)"
                elif signal_strength > 0.7:  # Strong sell signal
                    exit_reason = f"strong_alpha_reversal ({signal_direction})"
            elif trade.direction == "SHORT" and signal_direction in ["BUY", "LONG", "bullish"]:
                if pnl_pct > 0.5:
                    exit_reason = f"alpha_reversal_profit_lock ({pnl_pct:.2f}%)"
                elif signal_strength > 0.7:
                    exit_reason = f"strong_alpha_reversal ({signal_direction})"
            
            # 2. TRAILING PROFIT PROTECTION (Equities move slower than options)
            if exit_reason is None and pnl_pct > 0:
                if pnl_pct >= 5.0:
                    # At 5%+ profit, protect 60%
                    if signal_strength < 0.3:  # Momentum fading
                        exit_reason = f"big_profit_lock ({pnl_pct:.2f}%)"
                elif pnl_pct >= 3.0:
                    # At 3%+ profit, exit if signal weakening
                    if signal_strength < 0.4:
                        exit_reason = f"profit_lock_weak_signal ({pnl_pct:.2f}%)"
                elif pnl_pct >= 1.5:
                    # At 1.5%+ profit, exit if neutral
                    if signal_direction == "neutral" and hold_time > 60:
                        exit_reason = f"profit_lock_neutral ({pnl_pct:.2f}%)"
                elif pnl_pct >= 0.5:
                    # Quick profit if held too long
                    if hold_time > 120:  # 2 hours
                        exit_reason = f"quick_profit_time ({pnl_pct:.2f}%)"
            
            # 3. ADAPTIVE STOP LOSS
            if exit_reason is None:
                # Dynamic stop based on profit level
                if pnl_pct >= 3.0:
                    adaptive_stop = -1.0  # Protect most profit
                elif pnl_pct >= 1.5:
                    adaptive_stop = -0.5  # Break-even protection
                elif hold_time <= 30:
                    adaptive_stop = -2.0  # Give room initially
                elif hold_time <= 120:
                    adaptive_stop = -1.5  # Tighten after 30 mins
                else:
                    adaptive_stop = -1.0  # Tight after 2 hours
                
                if pnl_pct <= adaptive_stop:
                    exit_reason = f"adaptive_stop ({pnl_pct:.2f}% < {adaptive_stop}%)"
            
            # 4. HARD STOP LOSS
            if exit_reason is None and pnl_pct <= -3.0:
                exit_reason = f"hard_stop_loss ({pnl_pct:.2f}%)"
            
            # 5. TIME-BASED EXIT (Intraday for equities)
            if exit_reason is None and hold_time >= 300:  # 5 hours max
                exit_reason = f"time_exit ({hold_time:.0f} mins, P&L: {pnl_pct:.2f}%)"
            
            # Execute exit
            if exit_reason:
                result_pnl = self.exit_position(trade_id, current_price, exit_reason)
                results.append({
                    'trade_id': trade_id,
                    'symbol': symbol,
                    'direction': trade.direction,
                    'pnl': result_pnl,
                    'pnl_pct': pnl_pct,
                    'reason': exit_reason
                })
                logger.info(f"🎯 [EQ-EVAL] Intelligent Exit: {symbol} {trade.direction} | {exit_reason}")
        
        return results
    
    def get_evaluation_summary(self) -> Dict:
        """Get evaluation summary"""
        metrics = self._db.get_performance_metrics()
        daily = self._db.get_daily_summary()
        
        return {
            'session_id': self._session_id,
            'session_trades': self._session_trades,
            'session_pnl': self._session_pnl,
            'current_capital': self._current_capital,
            'open_positions': len(self._positions),
            'overall': metrics,
            'today': daily,
            'mode': self.mode.value
        }
    
    def get_position_summary(self) -> Dict:
        """Get position summary"""
        return {
            'open_positions': self.get_open_positions(),
            'count': len(self._positions),
            'session_pnl': self._session_pnl,
            'current_capital': self._current_capital
        }


# Singleton instance
_equity_evaluation_executor: Optional[EquityEvaluationExecutor] = None


def get_equity_evaluation_executor() -> Optional[EquityEvaluationExecutor]:
    """Get or create the equity evaluation executor"""
    global _equity_evaluation_executor
    if _equity_evaluation_executor is None:
        _equity_evaluation_executor = EquityEvaluationExecutor()
    return _equity_evaluation_executor


def create_equity_evaluation_executor(initial_capital: float = 500000) -> EquityEvaluationExecutor:
    """Create a new equity evaluation executor"""
    global _equity_evaluation_executor
    _equity_evaluation_executor = EquityEvaluationExecutor(initial_capital)
    return _equity_evaluation_executor
