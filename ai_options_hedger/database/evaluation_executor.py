"""
Evaluation Trading Executor for AI Options Hedger Service
==========================================================
Runs complete trade logic including order creation but:
- Does NOT send orders to exchange
- Logs everything as if real trade happened
- Tracks simulated fills based on market data
- Can be switched to production with single API call

This is separate from paper trading to keep production code unchanged.
"""

import asyncio
import logging
import uuid
from datetime import datetime, date
from typing import Dict, List, Optional, Tuple
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
    instrument: str
    option_type: str
    strike: float
    transaction_type: str  # BUY or SELL
    order_type: str  # MARKET or LIMIT
    quantity: int
    lot_size: int
    price: float
    simulated_fill_price: float
    slippage_applied: float
    status: str
    exchange_segment: str
    product_type: str
    correlation_id: str
    order_payload: Dict


class EvaluationDatabase:
    """
    Dedicated SQLite database for AI Hedger evaluation mode
    Stores all data needed to analyze strategy performance
    """
    
    def __init__(self, db_path: str = None):
        if db_path is None:
            db_dir = Path(__file__).parent.parent / "database"
            db_dir.mkdir(exist_ok=True)
            db_path = str(db_dir / "hedger_evaluation.db")
        
        self.db_path = db_path
        self._init_database()
        logger.info(f"Hedger evaluation database initialized: {db_path}")
    
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
                instrument TEXT NOT NULL,
                option_type TEXT,
                strike REAL,
                transaction_type TEXT NOT NULL,
                order_type TEXT NOT NULL,
                quantity INTEGER NOT NULL,
                lot_size INTEGER,
                requested_price REAL,
                simulated_fill_price REAL,
                slippage_applied REAL,
                status TEXT DEFAULT 'SIMULATED_FILLED',
                exchange_segment TEXT,
                product_type TEXT,
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
                instrument TEXT NOT NULL,
                option_type TEXT,
                strike REAL,
                entry_price REAL NOT NULL,
                exit_price REAL,
                quantity INTEGER NOT NULL,
                lot_size INTEGER,
                entry_order_id TEXT,
                exit_order_id TEXT,
                pnl REAL DEFAULT 0,
                pnl_percent REAL DEFAULT 0,
                status TEXT DEFAULT 'open',
                entry_reason TEXT,
                exit_reason TEXT,
                signal_strength REAL,
                ai_confidence REAL,
                ai_decision TEXT,
                ai_reasoning TEXT,
                hedge_type TEXT,
                duration_seconds INTEGER,
                max_profit REAL DEFAULT 0,
                max_loss REAL DEFAULT 0,
                market_conditions TEXT,
                strategy_parameters TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Hedge adjustments log
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS hedge_adjustments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TIMESTAMP NOT NULL,
                trade_id TEXT,
                adjustment_type TEXT NOT NULL,
                reason TEXT,
                before_delta REAL,
                after_delta REAL,
                adjustment_quantity INTEGER,
                adjustment_price REAL,
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
                avg_ai_confidence REAL DEFAULT 0,
                total_hedge_adjustments INTEGER DEFAULT 0,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Signal decisions log
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS signal_decisions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TIMESTAMP NOT NULL,
                instrument TEXT NOT NULL,
                signal_type TEXT,
                direction TEXT,
                signal_strength REAL,
                ai_decision TEXT,
                ai_confidence REAL,
                ai_reasoning TEXT,
                was_executed INTEGER DEFAULT 0,
                skip_reason TEXT,
                market_price REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_hedger_orders_trade ON evaluation_orders(trade_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_hedger_trades_date ON evaluation_trades(timestamp_entry)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_hedger_trades_status ON evaluation_trades(status)")
        
        # Initialize mode if not exists
        cursor.execute("SELECT COUNT(*) FROM execution_mode")
        if cursor.fetchone()[0] == 0:
            cursor.execute("INSERT INTO execution_mode (mode, notes) VALUES ('evaluation', 'Initial setup')")
        
        conn.commit()
        conn.close()
    
    def get_execution_mode(self) -> ExecutionMode:
        """Get current execution mode"""
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT mode FROM execution_mode ORDER BY id DESC LIMIT 1")
        row = cursor.fetchone()
        conn.close()
        return ExecutionMode(row['mode']) if row else ExecutionMode.EVALUATION
    
    def set_execution_mode(self, mode: ExecutionMode, updated_by: str = "api", notes: str = "") -> bool:
        """Set execution mode"""
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO execution_mode (mode, updated_by, notes) VALUES (?, ?, ?)
        """, (mode.value, updated_by, notes))
        conn.commit()
        conn.close()
        logger.info(f"Hedger execution mode changed to: {mode.value} by {updated_by}")
        return True
    
    def save_order(self, order: EvaluationOrder) -> int:
        """Save an evaluation order"""
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO evaluation_orders (
                order_id, trade_id, timestamp, instrument, option_type, strike,
                transaction_type, order_type, quantity, lot_size, requested_price,
                simulated_fill_price, slippage_applied, status, exchange_segment,
                product_type, correlation_id, order_payload
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            order.order_id, order.trade_id, order.timestamp, order.instrument,
            order.option_type, order.strike, order.transaction_type, order.order_type,
            order.quantity, order.lot_size, order.price, order.simulated_fill_price,
            order.slippage_applied, order.status, order.exchange_segment,
            order.product_type, order.correlation_id, json.dumps(order.order_payload)
        ))
        conn.commit()
        last_id = cursor.lastrowid
        conn.close()
        return last_id
    
    def save_trade(self, trade_id: str, entry_data: Dict) -> int:
        """Save a new trade entry"""
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO evaluation_trades (
                trade_id, timestamp_entry, instrument, option_type, strike,
                entry_price, quantity, lot_size, entry_order_id, status,
                entry_reason, signal_strength, ai_confidence, ai_decision,
                ai_reasoning, hedge_type, market_conditions, strategy_parameters
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'open', ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            trade_id, entry_data['timestamp'], entry_data['instrument'],
            entry_data['option_type'], entry_data['strike'], entry_data['entry_price'],
            entry_data['quantity'], entry_data['lot_size'], entry_data.get('entry_order_id'),
            entry_data.get('entry_reason', ''), entry_data.get('signal_strength', 0),
            entry_data.get('ai_confidence', 0), entry_data.get('ai_decision', ''),
            entry_data.get('ai_reasoning', ''), entry_data.get('hedge_type', ''),
            json.dumps(entry_data.get('market_conditions', {})),
            json.dumps(entry_data.get('strategy_parameters', {}))
        ))
        conn.commit()
        last_id = cursor.lastrowid
        conn.close()
        return last_id
    
    def update_trade_exit(self, trade_id: str, exit_data: Dict) -> bool:
        """Update trade with exit data"""
        conn = self._get_conn()
        cursor = conn.cursor()
        
        # Get entry time for duration calculation
        cursor.execute("SELECT timestamp_entry FROM evaluation_trades WHERE trade_id = ?", (trade_id,))
        row = cursor.fetchone()
        duration = 0
        if row:
            entry_time = datetime.fromisoformat(row['timestamp_entry'])
            duration = int((datetime.now() - entry_time).total_seconds())
        
        cursor.execute("""
            UPDATE evaluation_trades SET
                timestamp_exit = ?, exit_price = ?, exit_order_id = ?,
                pnl = ?, pnl_percent = ?, status = 'closed', exit_reason = ?,
                duration_seconds = ?
            WHERE trade_id = ?
        """, (
            exit_data['timestamp'], exit_data['exit_price'], exit_data.get('exit_order_id'),
            exit_data['pnl'], exit_data['pnl_percent'], exit_data.get('exit_reason', ''),
            duration, trade_id
        ))
        conn.commit()
        conn.close()
        return True
    
    def update_trade_extremes(self, trade_id: str, current_pnl: float):
        """Update max profit/loss for open trade"""
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT max_profit, max_loss FROM evaluation_trades WHERE trade_id = ?", (trade_id,))
        row = cursor.fetchone()
        if row:
            max_profit = max(row['max_profit'], current_pnl)
            max_loss = min(row['max_loss'], current_pnl)
            cursor.execute("""
                UPDATE evaluation_trades SET max_profit = ?, max_loss = ? WHERE trade_id = ?
            """, (max_profit, max_loss, trade_id))
            conn.commit()
        conn.close()
    
    def log_signal_decision(self, signal_data: Dict):
        """Log a signal decision for analysis"""
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO signal_decisions (
                timestamp, instrument, signal_type, direction, signal_strength,
                ai_decision, ai_confidence, ai_reasoning, was_executed,
                skip_reason, market_price
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            signal_data.get('timestamp', datetime.now()),
            signal_data.get('instrument', ''),
            signal_data.get('signal_type', ''),
            signal_data.get('direction', ''),
            signal_data.get('signal_strength', 0),
            signal_data.get('ai_decision', ''),
            signal_data.get('ai_confidence', 0),
            signal_data.get('ai_reasoning', ''),
            1 if signal_data.get('was_executed', False) else 0,
            signal_data.get('skip_reason', ''),
            signal_data.get('market_price', 0)
        ))
        conn.commit()
        conn.close()
    
    def log_hedge_adjustment(self, adjustment_data: Dict):
        """Log a hedge adjustment"""
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO hedge_adjustments (
                timestamp, trade_id, adjustment_type, reason,
                before_delta, after_delta, adjustment_quantity, adjustment_price
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            adjustment_data.get('timestamp', datetime.now()),
            adjustment_data.get('trade_id'),
            adjustment_data.get('adjustment_type', ''),
            adjustment_data.get('reason', ''),
            adjustment_data.get('before_delta', 0),
            adjustment_data.get('after_delta', 0),
            adjustment_data.get('adjustment_quantity', 0),
            adjustment_data.get('adjustment_price', 0)
        ))
        conn.commit()
        conn.close()
    
    def get_open_trades(self) -> List[Dict]:
        """Get all open evaluation trades"""
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM evaluation_trades WHERE status = 'open'")
        trades = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return trades
    
    def get_trades_by_date(self, target_date: date) -> List[Dict]:
        """Get all trades for a specific date"""
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM evaluation_trades 
            WHERE DATE(timestamp_entry) = ?
            ORDER BY timestamp_entry
        """, (target_date,))
        trades = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return trades
    
    def get_recent_trades(self, limit: int = 100) -> List[Dict]:
        """Get recent trades"""
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM evaluation_trades 
            ORDER BY timestamp_entry DESC LIMIT ?
        """, (limit,))
        trades = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return trades
    
    def get_orders_for_trade(self, trade_id: str) -> List[Dict]:
        """Get all orders for a trade"""
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM evaluation_orders WHERE trade_id = ? ORDER BY timestamp
        """, (trade_id,))
        orders = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return orders
    
    def get_signal_decisions(self, limit: int = 100) -> List[Dict]:
        """Get recent signal decisions"""
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM signal_decisions ORDER BY timestamp DESC LIMIT ?
        """, (limit,))
        decisions = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return decisions
    
    def update_daily_summary(self, target_date: date = None):
        """Update daily evaluation summary"""
        if target_date is None:
            target_date = date.today()
        
        conn = self._get_conn()
        cursor = conn.cursor()
        
        # Get trade stats
        cursor.execute("""
            SELECT 
                COUNT(*) as total_trades,
                SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) as winning,
                SUM(CASE WHEN pnl <= 0 THEN 1 ELSE 0 END) as losing,
                COALESCE(SUM(pnl), 0) as total_pnl,
                COALESCE(AVG(duration_seconds), 0) as avg_duration,
                COALESCE(AVG(signal_strength), 0) as avg_signal,
                COALESCE(AVG(ai_confidence), 0) as avg_confidence
            FROM evaluation_trades 
            WHERE DATE(timestamp_entry) = ? AND status = 'closed'
        """, (target_date,))
        trade_stats = cursor.fetchone()
        
        # Get order count
        cursor.execute("""
            SELECT COUNT(*) FROM evaluation_orders WHERE DATE(timestamp) = ?
        """, (target_date,))
        order_count = cursor.fetchone()[0]
        
        # Get hedge adjustment count
        cursor.execute("""
            SELECT COUNT(*) FROM hedge_adjustments WHERE DATE(timestamp) = ?
        """, (target_date,))
        adjustment_count = cursor.fetchone()[0]
        
        # Calculate win rate
        total = trade_stats['total_trades'] or 0
        winning = trade_stats['winning'] or 0
        win_rate = (winning / total * 100) if total > 0 else 0
        
        cursor.execute("""
            INSERT OR REPLACE INTO daily_evaluation_summary (
                date, total_orders_created, total_trades, winning_trades, losing_trades,
                win_rate, total_pnl, avg_trade_duration, avg_signal_strength,
                avg_ai_confidence, total_hedge_adjustments, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            target_date, order_count, total, winning, trade_stats['losing'] or 0,
            win_rate, trade_stats['total_pnl'], trade_stats['avg_duration'],
            trade_stats['avg_signal'], trade_stats['avg_confidence'],
            adjustment_count, datetime.now()
        ))
        conn.commit()
        conn.close()
    
    def get_evaluation_summary(self, days: int = 30) -> Dict:
        """Get comprehensive evaluation summary"""
        conn = self._get_conn()
        cursor = conn.cursor()
        
        summary = {}
        
        # Overall stats
        cursor.execute("""
            SELECT 
                COUNT(*) as total_trades,
                SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) as wins,
                SUM(CASE WHEN pnl <= 0 THEN 1 ELSE 0 END) as losses,
                COALESCE(SUM(pnl), 0) as total_pnl,
                COALESCE(AVG(pnl), 0) as avg_pnl,
                COALESCE(AVG(duration_seconds), 0) as avg_duration
            FROM evaluation_trades 
            WHERE status = 'closed' AND timestamp_entry >= date('now', '-' || ? || ' days')
        """, (days,))
        row = cursor.fetchone()
        
        total = row['total_trades'] or 0
        wins = row['wins'] or 0
        
        summary['overall'] = {
            'total_trades': total,
            'winning_trades': wins,
            'losing_trades': row['losses'] or 0,
            'win_rate': round((wins / total * 100), 2) if total > 0 else 0,
            'total_pnl': round(row['total_pnl'], 2),
            'avg_pnl_per_trade': round(row['avg_pnl'], 2),
            'avg_trade_duration_seconds': round(row['avg_duration'], 0)
        }
        
        # By instrument
        cursor.execute("""
            SELECT 
                instrument,
                COUNT(*) as trades,
                SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) as wins,
                ROUND(SUM(pnl), 2) as pnl
            FROM evaluation_trades 
            WHERE status = 'closed' AND timestamp_entry >= date('now', '-' || ? || ' days')
            GROUP BY instrument
        """, (days,))
        summary['by_instrument'] = [dict(row) for row in cursor.fetchall()]
        
        # By hedge type
        cursor.execute("""
            SELECT 
                hedge_type,
                COUNT(*) as trades,
                ROUND(SUM(pnl), 2) as pnl
            FROM evaluation_trades 
            WHERE status = 'closed' AND timestamp_entry >= date('now', '-' || ? || ' days')
            GROUP BY hedge_type
        """, (days,))
        summary['by_hedge_type'] = [dict(row) for row in cursor.fetchall()]
        
        # Daily trend
        cursor.execute("""
            SELECT * FROM daily_evaluation_summary 
            WHERE date >= date('now', '-' || ? || ' days')
            ORDER BY date
        """, (days,))
        summary['daily_trend'] = [dict(row) for row in cursor.fetchall()]
        
        # Current mode
        summary['current_mode'] = self.get_execution_mode().value
        
        conn.close()
        return summary


class HedgerEvaluationPosition:
    """Wrapper class for hedger evaluation positions with update_price method"""
    def __init__(self, position_dict: Dict, executor: 'HedgerEvaluationExecutor'):
        self._data = position_dict
        self._executor = executor
    
    @property
    def trade_id(self) -> str:
        return self._data.get('trade_id', '')
    
    @property
    def instrument(self) -> str:
        return self._data.get('instrument', '')
    
    @property
    def option_type(self) -> str:
        return self._data.get('option_type', '')
    
    @property
    def strike(self) -> float:
        return self._data.get('strike', 0.0)
    
    @property
    def entry_price(self) -> float:
        return self._data.get('entry_price', 0.0)
    
    @property
    def current_price(self) -> float:
        return self._data.get('current_price', 0.0)
    
    @property
    def quantity(self) -> int:
        return self._data.get('quantity', 0)
    
    @property
    def lot_size(self) -> int:
        return self._data.get('lot_size', 1)
    
    @property
    def unrealized_pnl(self) -> float:
        return self._data.get('unrealized_pnl', 0.0)
    
    @property
    def unrealized_pnl_pct(self) -> float:
        return self._data.get('unrealized_pnl_pct', 0.0)
    
    def update_price(self, new_price: float):
        """Update current price and PnL - delegates to executor"""
        self._executor.update_position_price(self.trade_id, new_price)
        self._data['current_price'] = new_price


class HedgerEvaluationExecutor:
    """
    Evaluation mode executor for Options Hedger
    Creates real order payloads but doesn't send to exchange
    Simulates fills based on market data
    """
    
    # Options have higher slippage
    SLIPPAGE_PCT = 0.5
    
    # Lot sizes
    LOT_SIZES = {
        "NIFTY": 75,
        "BANKNIFTY": 35,
        "FINNIFTY": 65,
        "SENSEX": 20,
        "BANKEX": 30
    }
    
    # Exchange segments
    EXCHANGE_SEGMENTS = {
        "NIFTY": "NSE_FNO",
        "BANKNIFTY": "NSE_FNO",
        "FINNIFTY": "NSE_FNO",
        "SENSEX": "BSE_FNO",
        "BANKEX": "BSE_FNO"
    }
    
    def __init__(self, access_token: str, client_id: str, initial_capital: float = 500000.0):
        self.access_token = access_token
        self.client_id = client_id
        self.initial_capital = initial_capital
        self.capital = initial_capital
        self.realized_pnl = 0.0
        
        self._positions: Dict[str, Dict] = {}
        self._db = EvaluationDatabase()
        self._signal_engine = None  # Will be set by service for intelligent exits
        
        self._daily_trades = 0
        self._current_date = date.today()
        
        logger.info(f"HedgerEvaluationExecutor initialized - EVALUATION MODE")
        logger.info(f"Orders will be created but NOT sent to exchange")
    
    def set_signal_engine(self, signal_engine):
        """Set signal engine reference for intelligent exit logic"""
        self._signal_engine = signal_engine
    
    @property
    def position_count(self) -> int:
        return len(self._positions)
    
    @property
    def open_positions(self) -> List[HedgerEvaluationPosition]:
        """Return positions wrapped in HedgerEvaluationPosition objects for compatibility"""
        return [HedgerEvaluationPosition(pos, self) for pos in self._positions.values()]
    
    def _create_order_payload(self, instrument: str, option_type: str, strike: float,
                               transaction_type: str, quantity: int, price: float) -> Dict:
        """Create the exact order payload that would be sent to Dhan API"""
        lot_size = self.LOT_SIZES.get(instrument, 75)
        exchange = self.EXCHANGE_SEGMENTS.get(instrument, "NSE_FNO")
        
        expiry = datetime.now().strftime("%d%b%y").upper()
        symbol = f"{instrument}{expiry}{int(strike)}{option_type}"
        
        return {
            "dhanClientId": self.client_id,
            "correlationId": f"HEVAL_{int(datetime.now().timestamp())}",
            "transactionType": transaction_type,
            "exchangeSegment": exchange,
            "productType": "INTRADAY",
            "orderType": "MARKET",
            "validity": "DAY",
            "tradingSymbol": symbol,
            "securityId": "",
            "quantity": str(quantity * lot_size),
            "disclosedQuantity": "0",
            "price": str(price),
            "triggerPrice": "0",
            "afterMarketOrder": False
        }
    
    def _apply_slippage(self, price: float, is_buy: bool) -> float:
        """Apply realistic slippage for options"""
        slippage = price * self.SLIPPAGE_PCT / 100
        if is_buy:
            return price + slippage
        else:
            return price - slippage
    
    async def enter_position(
        self,
        instrument: str,
        option_type: str,
        strike: float,
        current_price: float,
        lots: int = 1,
        reason: str = "",
        signal_strength: float = 0.0,
        ai_confidence: float = 0.0,
        hedge_type: str = "",
        market_conditions: Dict = None
    ) -> Dict:
        """Enter a position in evaluation mode"""
        
        trade_id = f"HEVAL_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
        order_id = f"HORD_{uuid.uuid4().hex[:8]}"
        
        lot_size = self.LOT_SIZES.get(instrument, 75)
        
        order_payload = self._create_order_payload(
            instrument, option_type, strike, "BUY", lots, current_price
        )
        
        fill_price = self._apply_slippage(current_price, is_buy=True)
        slippage = fill_price - current_price
        
        order = EvaluationOrder(
            order_id=order_id,
            trade_id=trade_id,
            timestamp=datetime.now(),
            instrument=instrument,
            option_type=option_type,
            strike=strike,
            transaction_type="BUY",
            order_type="MARKET",
            quantity=lots,
            lot_size=lot_size,
            price=current_price,
            simulated_fill_price=fill_price,
            slippage_applied=slippage,
            status="SIMULATED_FILLED",
            exchange_segment=self.EXCHANGE_SEGMENTS.get(instrument, "NSE_FNO"),
            product_type="INTRADAY",
            correlation_id=order_payload["correlationId"],
            order_payload=order_payload
        )
        
        self._db.save_order(order)
        
        position = {
            'trade_id': trade_id,
            'instrument': instrument,
            'option_type': option_type,
            'strike': strike,
            'entry_price': fill_price,
            'current_price': fill_price,
            'quantity': lots,
            'lot_size': lot_size,
            'entry_time': datetime.now(),
            'entry_order_id': order_id,
            'unrealized_pnl': 0.0,
            'unrealized_pnl_pct': 0.0,
            'max_profit': 0.0,
            'max_loss': 0.0,
            'ai_confidence': ai_confidence
        }
        
        self._positions[trade_id] = position
        self._daily_trades += 1
        
        self._db.save_trade(trade_id, {
            'timestamp': datetime.now(),
            'instrument': instrument,
            'option_type': option_type,
            'strike': strike,
            'entry_price': fill_price,
            'quantity': lots,
            'lot_size': lot_size,
            'entry_order_id': order_id,
            'entry_reason': reason,
            'signal_strength': signal_strength,
            'ai_confidence': ai_confidence,
            'hedge_type': hedge_type,
            'market_conditions': market_conditions or {}
        })
        
        self._db.log_signal_decision({
            'timestamp': datetime.now(),
            'instrument': instrument,
            'signal_type': 'HEDGE_ENTRY',
            'direction': option_type,
            'signal_strength': signal_strength,
            'ai_confidence': ai_confidence,
            'was_executed': True,
            'market_price': current_price
        })
        
        logger.info(f"📈 HEDGER EVAL ENTRY: {trade_id} | {instrument} {strike}{option_type} @ ₹{fill_price:.2f}")
        
        return {
            'success': True,
            'trade_id': trade_id,
            'order_id': order_id,
            'fill_price': fill_price,
            'slippage': slippage,
            'message': 'Position entered (EVALUATION MODE)',
            'order_payload': order_payload
        }
    
    async def exit_position(
        self,
        trade_id: str,
        current_price: float,
        reason: str = "manual"
    ) -> Dict:
        """Exit a position in evaluation mode"""
        
        if trade_id not in self._positions:
            return {'success': False, 'message': 'Position not found'}
        
        position = self._positions[trade_id]
        order_id = f"HORD_{uuid.uuid4().hex[:8]}"
        
        order_payload = self._create_order_payload(
            position['instrument'], position['option_type'], position['strike'],
            "SELL", position['quantity'], current_price
        )
        
        fill_price = self._apply_slippage(current_price, is_buy=False)
        slippage = current_price - fill_price
        
        order = EvaluationOrder(
            order_id=order_id,
            trade_id=trade_id,
            timestamp=datetime.now(),
            instrument=position['instrument'],
            option_type=position['option_type'],
            strike=position['strike'],
            transaction_type="SELL",
            order_type="MARKET",
            quantity=position['quantity'],
            lot_size=position['lot_size'],
            price=current_price,
            simulated_fill_price=fill_price,
            slippage_applied=slippage,
            status="SIMULATED_FILLED",
            exchange_segment=self.EXCHANGE_SEGMENTS.get(position['instrument'], "NSE_FNO"),
            product_type="INTRADAY",
            correlation_id=order_payload["correlationId"],
            order_payload=order_payload
        )
        
        self._db.save_order(order)
        
        pnl = (fill_price - position['entry_price']) * position['quantity'] * position['lot_size']
        pnl_pct = (fill_price - position['entry_price']) / position['entry_price'] * 100
        
        self.realized_pnl += pnl
        
        self._db.update_trade_exit(trade_id, {
            'timestamp': datetime.now(),
            'exit_price': fill_price,
            'exit_order_id': order_id,
            'pnl': pnl,
            'pnl_percent': pnl_pct,
            'exit_reason': reason
        })
        
        del self._positions[trade_id]
        
        emoji = "✅" if pnl > 0 else "❌"
        logger.info(f"{emoji} HEDGER EVAL EXIT: {trade_id} @ ₹{fill_price:.2f} | PnL: ₹{pnl:+,.2f}")
        
        return {
            'success': True,
            'trade_id': trade_id,
            'order_id': order_id,
            'fill_price': fill_price,
            'pnl': pnl,
            'pnl_pct': pnl_pct,
            'message': f'Position exited (EVALUATION MODE) - PnL: ₹{pnl:+,.2f}'
        }
    
    def update_position_price(self, trade_id: str, new_price: float):
        """Update position with current price"""
        if trade_id not in self._positions:
            return
        
        pos = self._positions[trade_id]
        pos['current_price'] = new_price
        pos['unrealized_pnl'] = (new_price - pos['entry_price']) * pos['quantity'] * pos['lot_size']
        pos['unrealized_pnl_pct'] = (new_price - pos['entry_price']) / pos['entry_price'] * 100
        
        pos['max_profit'] = max(pos['max_profit'], pos['unrealized_pnl'])
        pos['max_loss'] = min(pos['max_loss'], pos['unrealized_pnl'])
        
        self._db.update_trade_extremes(trade_id, pos['unrealized_pnl'])
    
    async def check_exits(
        self,
        stop_loss_pct: float = 30.0,
        target_pct: float = 50.0,
        time_exit_minutes: int = 60
    ) -> List[Dict]:
        """
        INTELLIGENT EXIT LOGIC for Options Hedger Evaluation
        - Direction-aware trend exits (CE vs PE)
        - Trailing profit lock
        - Adaptive stop loss based on profit level
        """
        results = []
        
        for trade_id, pos in list(self._positions.items()):
            pnl_pct = pos['unrealized_pnl_pct']
            hold_time = (datetime.now() - pos['entry_time']).total_seconds() / 60
            reason = None
            
            # Get current trend from signal engine if available
            trend = None
            signal_strength = 0
            if self._signal_engine:
                try:
                    state = self._signal_engine.get_state(pos['instrument'])
                    if state:
                        trend = state.get('trend_direction')
                        signal_strength = state.get('signal_strength', 0)
                except:
                    pass
            
            # =====================================================
            # INTELLIGENT OPTIONS EXIT STRATEGY
            # =====================================================
            
            # 1. DIRECTION-AWARE TREND EXIT
            if trend and hasattr(trend, 'value'):
                if pos['option_type'] == "CE" and trend.value == "bearish":
                    if pnl_pct > 10:
                        reason = f"trend_reversal_profit_lock ({pnl_pct:.1f}%)"
                    elif signal_strength > 0.5:
                        reason = "strong_bearish_reversal"
                elif pos['option_type'] == "PE" and trend.value == "bullish":
                    if pnl_pct > 10:
                        reason = f"trend_reversal_profit_lock ({pnl_pct:.1f}%)"
                    elif signal_strength > 0.5:
                        reason = "strong_bullish_reversal"
            
            # 2. TRAILING PROFIT LOCK
            if reason is None and pnl_pct > 0:
                if pnl_pct >= 80:
                    if signal_strength < 0.3:
                        reason = f"mega_profit_lock ({pnl_pct:.1f}%)"
                elif pnl_pct >= 50:
                    if signal_strength < 0.4:
                        reason = f"profit_lock_momentum_fade ({pnl_pct:.1f}%)"
                elif pnl_pct >= 30:
                    if trend is None or (hasattr(trend, 'value') and trend.value == "neutral"):
                        reason = f"profit_lock_neutral ({pnl_pct:.1f}%)"
                elif pnl_pct >= 15 and hold_time >= 30:
                    reason = f"profit_lock_time_decay ({pnl_pct:.1f}%)"
            
            # 3. ADAPTIVE STOP LOSS
            if reason is None:
                if pnl_pct >= 30:
                    adaptive_stop = -15.0
                elif pnl_pct >= 15:
                    adaptive_stop = -5.0
                elif hold_time <= 10:
                    adaptive_stop = -25.0
                elif hold_time <= 30:
                    adaptive_stop = -20.0
                else:
                    adaptive_stop = -15.0
                
                if pnl_pct <= adaptive_stop:
                    reason = f"adaptive_stop ({pnl_pct:.1f}% < {adaptive_stop}%)"
            
            # 4. HARD STOP LOSS
            if reason is None and pnl_pct <= -stop_loss_pct:
                reason = f"hard_stop_loss ({pnl_pct:.1f}%)"
            
            # 5. TIME-BASED EXIT
            if reason is None and hold_time >= time_exit_minutes:
                reason = f"time_exit ({hold_time:.0f} mins, P&L: {pnl_pct:.1f}%)"
            
            # Execute exit
            if reason:
                result = await self.exit_position(trade_id, pos['current_price'], reason)
                results.append(result)
                logger.info(f"🎯 [EVAL] Intelligent Exit: {pos['instrument']} {pos['option_type']} | {reason}")
        
        return results
    
    def get_position_summary(self) -> Dict:
        """Get summary of all positions"""
        unrealized = sum(p['unrealized_pnl'] for p in self._positions.values())
        
        return {
            'mode': 'EVALUATION',
            'service': 'AI Options Hedger',
            'position_count': len(self._positions),
            'positions': [
                {
                    'trade_id': p['trade_id'],
                    'instrument': p['instrument'],
                    'option_type': p['option_type'],
                    'strike': p['strike'],
                    'entry_price': p['entry_price'],
                    'current_price': p['current_price'],
                    'quantity': p['quantity'],
                    'lot_size': p['lot_size'],
                    'unrealized_pnl': p['unrealized_pnl'],
                    'unrealized_pnl_pct': p['unrealized_pnl_pct'],
                    'hold_time_mins': (datetime.now() - p['entry_time']).total_seconds() / 60
                }
                for p in self._positions.values()
            ],
            'unrealized_pnl': unrealized,
            'realized_pnl': self.realized_pnl,
            'total_pnl': self.realized_pnl + unrealized,
            'daily_trades': self._daily_trades
        }
    
    def get_evaluation_summary(self, days: int = 30) -> Dict:
        """Get comprehensive evaluation summary"""
        return self._db.get_evaluation_summary(days)


# Global database instance
_hedger_eval_db_instance = None

def get_hedger_evaluation_database() -> EvaluationDatabase:
    """Get the global evaluation database instance for hedger"""
    global _hedger_eval_db_instance
    if _hedger_eval_db_instance is None:
        _hedger_eval_db_instance = EvaluationDatabase()
    return _hedger_eval_db_instance
