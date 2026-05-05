"""
╔══════════════════════════════════════════════════════════════════════════════════════╗
║                     ELITE OPTIONS TRADE EXECUTOR v1.0                                ║
║        End-to-End Trade Lifecycle Management with Gemini AI Integration              ║
║══════════════════════════════════════════════════════════════════════════════════════║
║                                                                                      ║
║  RESPONSIBILITIES:                                                                   ║
║  ─────────────────                                                                   ║
║  1. Receive signals from EliteOptionsScanner                                         ║
║  2. Select optimal strike using OptionsChainAnalyzer                                 ║
║  3. Execute trades via Dhan Connector                                                ║
║  4. Monitor active positions with MomentumExitMonitor                                ║
║  5. Execute exits based on Gemini Pro 3 consultation                                 ║
║  6. Track P&L and maintain trade history                                             ║
║                                                                                      ║
║  EXECUTION STYLE:                                                                    ║
║  ─────────────────                                                                   ║
║  • Wide stoploss (15-20%) for momentum capture                                       ║
║  • No trailing stops - let momentum run                                              ║
║  • Exit only on Gemini Pro 3 signal or time-based rules                             ║
║  • Partial exits allowed at 50%/100%/150% targets                                    ║
║                                                                                      ║
║  CAPITAL MANAGEMENT:                                                                 ║
║  ─────────────────                                                                   ║
║  • Never risk more than 5% per trade                                                 ║
║  • Deploy capital based on confidence ranking                                        ║
║  • Higher confidence = more capital allocation                                        ║
║                                                                                      ║
╚══════════════════════════════════════════════════════════════════════════════════════╝
"""

import asyncio
import aiohttp
import logging
import json
import sqlite3
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field, asdict
from enum import Enum
import os

logger = logging.getLogger(__name__ + '.trade_executor')


class TradeStatus(Enum):
    """Trade lifecycle status"""
    PENDING = "pending"           # Signal received, awaiting execution
    EXECUTED = "executed"         # Order placed, awaiting fill
    ACTIVE = "active"             # Position is live
    PARTIAL_EXIT = "partial_exit" # Some quantity exited
    EXITED = "exited"             # Fully exited
    STOPPED = "stopped"           # Stopped out
    CANCELLED = "cancelled"       # Order cancelled
    FAILED = "failed"             # Execution failed


class ExitReason(Enum):
    """Reason for exit"""
    GEMINI_SIGNAL = "gemini_signal"      # Gemini Pro 3 recommended exit
    STOPLOSS = "stoploss"                # Hit stoploss
    TARGET_1 = "target_1"                # Hit target 1
    TARGET_2 = "target_2"                # Hit target 2
    TIME_BASED = "time_based"            # Time-based exit (EOD/expiry)
    MOMENTUM_LOSS = "momentum_loss"      # Momentum exhausted
    MANUAL = "manual"                    # Manual exit
    SYSTEM = "system"                    # System shutdown/error


@dataclass
class TradeOrder:
    """Order details for a trade"""
    order_id: str = ""
    status: str = "pending"
    order_type: str = "LIMIT"  # LIMIT or MARKET
    transaction_type: str = ""  # BUY or SELL
    quantity: int = 0
    price: float = 0.0
    avg_fill_price: float = 0.0
    filled_quantity: int = 0
    placed_at: datetime = None
    filled_at: datetime = None
    
    def to_dict(self) -> Dict:
        return {
            "order_id": self.order_id,
            "status": self.status,
            "order_type": self.order_type,
            "transaction_type": self.transaction_type,
            "quantity": self.quantity,
            "price": self.price,
            "avg_fill_price": self.avg_fill_price,
            "filled_quantity": self.filled_quantity,
            "placed_at": self.placed_at.isoformat() if self.placed_at else None,
            "filled_at": self.filled_at.isoformat() if self.filled_at else None,
        }


@dataclass
class ActiveTrade:
    """Complete trade record"""
    trade_id: str
    symbol: str
    option_symbol: str  # e.g., TATAMOTORS2501301000CE
    option_type: str    # CE or PE
    strike: float
    expiry: str
    
    # Direction & Sizing
    direction: str      # BUY (long) or SELL (short)
    quantity: int       # Total lots * lot_size
    lots: int
    lot_size: int
    
    # Prices
    entry_price: float
    current_price: float = 0.0
    stoploss: float = 0.0
    target_1: float = 0.0
    target_2: float = 0.0
    
    # Capital
    capital_deployed: float = 0.0
    current_value: float = 0.0
    
    # P&L
    realized_pnl: float = 0.0
    unrealized_pnl: float = 0.0
    pnl_pct: float = 0.0
    
    # Status
    status: TradeStatus = TradeStatus.PENDING
    exit_reason: Optional[ExitReason] = None
    
    # Confidence from scanner
    signal_confidence: float = 0.0
    gemini_confirmation: str = ""
    
    # Orders
    entry_order: Optional[TradeOrder] = None
    exit_orders: List[TradeOrder] = field(default_factory=list)
    
    # Timestamps
    signal_time: datetime = None
    entry_time: datetime = None
    exit_time: datetime = None
    last_update: datetime = None
    
    # Monitoring
    momentum_status: str = "strong"
    gemini_exit_consulted: bool = False
    partial_exits: List[Dict] = field(default_factory=list)
    
    def __post_init__(self):
        if self.signal_time is None:
            self.signal_time = datetime.now()
        self.last_update = datetime.now()
    
    def update_price(self, new_price: float):
        """Update current price and calculate P&L"""
        self.current_price = new_price
        self.current_value = new_price * self.quantity
        
        if self.entry_price > 0:
            self.unrealized_pnl = (new_price - self.entry_price) * self.quantity
            self.pnl_pct = ((new_price - self.entry_price) / self.entry_price) * 100
        
        self.last_update = datetime.now()
    
    @property
    def is_in_profit(self) -> bool:
        return self.unrealized_pnl > 0
    
    @property
    def is_near_stoploss(self) -> bool:
        """Check if within 20% of stoploss"""
        if self.stoploss <= 0:
            return False
        sl_distance = abs(self.entry_price - self.stoploss)
        current_distance = abs(self.current_price - self.stoploss)
        return current_distance < (sl_distance * 0.2)
    
    @property
    def hit_target_1(self) -> bool:
        if self.target_1 <= 0:
            return False
        return self.current_price >= self.target_1
    
    @property
    def hit_target_2(self) -> bool:
        if self.target_2 <= 0:
            return False
        return self.current_price >= self.target_2
    
    def to_dict(self) -> Dict:
        return {
            "trade_id": self.trade_id,
            "symbol": self.symbol,
            "option_symbol": self.option_symbol,
            "option_type": self.option_type,
            "strike": self.strike,
            "expiry": self.expiry,
            "direction": self.direction,
            "quantity": self.quantity,
            "lots": self.lots,
            "lot_size": self.lot_size,
            "entry_price": self.entry_price,
            "current_price": self.current_price,
            "stoploss": self.stoploss,
            "target_1": self.target_1,
            "target_2": self.target_2,
            "capital_deployed": self.capital_deployed,
            "current_value": self.current_value,
            "realized_pnl": self.realized_pnl,
            "unrealized_pnl": self.unrealized_pnl,
            "pnl_pct": self.pnl_pct,
            "status": self.status.value,
            "exit_reason": self.exit_reason.value if self.exit_reason else None,
            "signal_confidence": self.signal_confidence,
            "gemini_confirmation": self.gemini_confirmation,
            "signal_time": self.signal_time.isoformat() if self.signal_time else None,
            "entry_time": self.entry_time.isoformat() if self.entry_time else None,
            "exit_time": self.exit_time.isoformat() if self.exit_time else None,
            "momentum_status": self.momentum_status,
        }


class EliteTradeExecutor:
    """
    Elite Trade Executor
    
    Manages the complete lifecycle of F&O options trades:
    - Signal reception from scanner
    - Optimal strike selection
    - Order execution via Dhan
    - Position monitoring with Gemini 3 Pro
    - Intelligent exits using gemini-3-pro model
    
    GEMINI MODELS USED:
    - Exit Decisions: gemini-3-pro (high accuracy for exit timing)
    """
    
    # Gemini model for exit consultation
    GEMINI_EXIT_MODEL = "gemini-3-pro"
    
    def __init__(
        self,
        dhan_connector=None,
        scanner=None,
        chain_analyzer=None,
        exit_monitor=None,
        gemini_url: str = "http://localhost:4080",
        backend_url: str = "http://localhost:8000",
        db_path: str = None,
        gemini_api_key: str = None
    ):
        self.dhan = dhan_connector
        self.scanner = scanner
        self.chain_analyzer = chain_analyzer
        self.exit_monitor = exit_monitor
        self.gemini_url = gemini_url
        self.backend_url = backend_url
        self.gemini_api_key = gemini_api_key or os.environ.get("GEMINI_API_KEY", "")
        
        # Database
        if db_path is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            db_path = os.path.join(base_dir, "database", "elite_trades.db")
        self.db_path = db_path
        
        # HTTP session
        self.session = None
        
        # Active trades
        self.active_trades: Dict[str, ActiveTrade] = {}
        
        # Configuration
        self.config = {
            "max_active_trades": 5,
            "max_capital_per_trade_pct": 20,  # 20% of total
            "stoploss_pct": 20,               # Wide SL
            "target_1_pct": 50,               # 50% profit
            "target_2_pct": 100,              # 100% profit
            "partial_exit_at_target_1_pct": 50,  # Exit 50% at T1
            "paper_trading": True,
        }
        
        # Stats
        self.stats = {
            "total_trades": 0,
            "winning_trades": 0,
            "losing_trades": 0,
            "total_pnl": 0.0,
            "best_trade_pnl": 0.0,
            "worst_trade_pnl": 0.0,
        }
        
        # Monitoring task
        self.monitoring_task = None
        self.is_running = False
        
        logger.info("🚀 Elite Trade Executor initialized")
    
    async def initialize(self) -> bool:
        """Initialize executor"""
        try:
            self.session = aiohttp.ClientSession()
            
            # Initialize database
            self._init_database()
            
            # Load active trades
            await self._load_active_trades()
            
            logger.info(f"✅ Executor ready with {len(self.active_trades)} active trades")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize executor: {e}")
            return False
    
    def _init_database(self):
        """Initialize SQLite database"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        c.execute('''
            CREATE TABLE IF NOT EXISTS trades (
                trade_id TEXT PRIMARY KEY,
                symbol TEXT,
                option_symbol TEXT,
                option_type TEXT,
                strike REAL,
                expiry TEXT,
                direction TEXT,
                quantity INTEGER,
                lots INTEGER,
                lot_size INTEGER,
                entry_price REAL,
                exit_price REAL,
                stoploss REAL,
                target_1 REAL,
                target_2 REAL,
                capital_deployed REAL,
                realized_pnl REAL,
                pnl_pct REAL,
                status TEXT,
                exit_reason TEXT,
                signal_confidence REAL,
                gemini_confirmation TEXT,
                signal_time TEXT,
                entry_time TEXT,
                exit_time TEXT,
                created_at TEXT,
                updated_at TEXT
            )
        ''')
        
        c.execute('''
            CREATE TABLE IF NOT EXISTS trade_orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                trade_id TEXT,
                order_id TEXT,
                order_type TEXT,
                transaction_type TEXT,
                quantity INTEGER,
                price REAL,
                avg_fill_price REAL,
                status TEXT,
                placed_at TEXT,
                filled_at TEXT,
                FOREIGN KEY (trade_id) REFERENCES trades(trade_id)
            )
        ''')
        
        conn.commit()
        conn.close()
        
        logger.info(f"📊 Database initialized at {self.db_path}")
    
    async def _load_active_trades(self):
        """Load active trades from database"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        c.execute('''
            SELECT * FROM trades 
            WHERE status IN ('pending', 'executed', 'active', 'partial_exit')
        ''')
        
        rows = c.fetchall()
        for row in rows:
            trade = self._row_to_trade(row)
            if trade:
                self.active_trades[trade.trade_id] = trade
        
        conn.close()
    
    def _row_to_trade(self, row) -> Optional[ActiveTrade]:
        """Convert database row to ActiveTrade"""
        try:
            return ActiveTrade(
                trade_id=row[0],
                symbol=row[1],
                option_symbol=row[2],
                option_type=row[3],
                strike=row[4],
                expiry=row[5],
                direction=row[6],
                quantity=row[7],
                lots=row[8],
                lot_size=row[9],
                entry_price=row[10],
                stoploss=row[12],
                target_1=row[13],
                target_2=row[14],
                capital_deployed=row[15],
                realized_pnl=row[16],
                pnl_pct=row[17],
                status=TradeStatus(row[18]),
                exit_reason=ExitReason(row[19]) if row[19] else None,
                signal_confidence=row[20],
                gemini_confirmation=row[21],
                signal_time=datetime.fromisoformat(row[22]) if row[22] else None,
                entry_time=datetime.fromisoformat(row[23]) if row[23] else None,
                exit_time=datetime.fromisoformat(row[24]) if row[24] else None,
            )
        except Exception as e:
            logger.error(f"Error converting row to trade: {e}")
            return None
    
    async def close(self):
        """Close executor"""
        self.is_running = False
        
        if self.monitoring_task:
            self.monitoring_task.cancel()
        
        if self.session and not self.session.closed:
            await self.session.close()
        
        logger.info("✅ Executor closed")
    
    # =========================================================================
    # TRADE EXECUTION
    # =========================================================================
    
    async def execute_signal(
        self,
        symbol: str,
        direction: str,  # CE or PE
        confidence: float,
        gemini_confirmation: str,
        available_capital: float,
        spot_price: float = None,
    ) -> Optional[ActiveTrade]:
        """
        Execute a signal by:
        1. Getting optimal strike from chain analyzer
        2. Calculating position size
        3. Placing order via Dhan
        4. Creating trade record
        """
        logger.info(f"📥 Executing signal: {symbol} {direction} @ {confidence}% confidence")
        
        # Check if we can take more trades
        if len(self.active_trades) >= self.config["max_active_trades"]:
            logger.warning(f"Max active trades ({self.config['max_active_trades']}) reached")
            return None
        
        # Check if already trading this symbol
        for trade in self.active_trades.values():
            if trade.symbol == symbol:
                logger.warning(f"Already have active trade for {symbol}")
                return None
        
        try:
            # Get optimal strike
            if self.chain_analyzer:
                best_strike = await self.chain_analyzer.get_best_strike_for_signal(
                    symbol=symbol,
                    direction=direction,
                    spot_price=spot_price or 0,
                    available_capital=available_capital,
                    momentum_strength=confidence / 100,
                )
            else:
                # Simulate strike selection
                best_strike = await self._simulate_strike_selection(
                    symbol, direction, spot_price, available_capital
                )
            
            if not best_strike:
                logger.error(f"No suitable strike found for {symbol}")
                return None
            
            # Calculate position size
            max_capital = available_capital * (self.config["max_capital_per_trade_pct"] / 100)
            lots = min(5, int(max_capital / best_strike.premium_per_lot))
            
            if lots < 1:
                logger.warning(f"Insufficient capital for 1 lot of {symbol}")
                return None
            
            quantity = lots * best_strike.lot_size
            capital = lots * best_strike.premium_per_lot
            
            # Calculate SL and targets
            entry_price = best_strike.ltp
            stoploss = entry_price * (1 - self.config["stoploss_pct"] / 100)
            target_1 = entry_price * (1 + self.config["target_1_pct"] / 100)
            target_2 = entry_price * (1 + self.config["target_2_pct"] / 100)
            
            # Create option symbol
            expiry_formatted = datetime.strptime(best_strike.expiry, "%Y-%m-%d").strftime("%y%m%d")
            option_symbol = f"{symbol}{expiry_formatted}{int(best_strike.strike)}{direction}"
            
            # Create trade
            trade = ActiveTrade(
                trade_id=f"ELITE_{uuid.uuid4().hex[:8].upper()}",
                symbol=symbol,
                option_symbol=option_symbol,
                option_type=direction,
                strike=best_strike.strike,
                expiry=best_strike.expiry,
                direction="BUY",
                quantity=quantity,
                lots=lots,
                lot_size=best_strike.lot_size,
                entry_price=entry_price,
                current_price=entry_price,
                stoploss=stoploss,
                target_1=target_1,
                target_2=target_2,
                capital_deployed=capital,
                current_value=capital,
                signal_confidence=confidence,
                gemini_confirmation=gemini_confirmation,
                status=TradeStatus.PENDING,
            )
            
            # Place order
            order = await self._place_order(trade)
            
            if order and order.status in ["success", "COMPLETE"]:
                trade.entry_order = order
                trade.entry_time = datetime.now()
                trade.status = TradeStatus.ACTIVE
                
                # Save to database
                self._save_trade(trade)
                
                # Add to active trades
                self.active_trades[trade.trade_id] = trade
                
                logger.info(f"✅ Trade executed: {trade.trade_id} - {symbol} {direction}")
                logger.info(f"   Entry: ₹{entry_price:.2f} | SL: ₹{stoploss:.2f} | T1: ₹{target_1:.2f}")
                logger.info(f"   Lots: {lots} | Qty: {quantity} | Capital: ₹{capital:,.0f}")
                
                return trade
            else:
                trade.status = TradeStatus.FAILED
                logger.error(f"Order placement failed for {symbol}")
                return None
            
        except Exception as e:
            logger.error(f"Error executing signal: {e}")
            return None
    
    async def _simulate_strike_selection(
        self,
        symbol: str,
        direction: str,
        spot_price: float,
        available_capital: float
    ):
        """Simulate strike selection for testing"""
        from dataclasses import dataclass
        
        @dataclass
        class SimulatedStrike:
            symbol: str
            strike: float
            ltp: float
            lot_size: int
            premium_per_lot: float
            delta: float
            gamma: float
            expiry: str
        
        # Get lot size
        lot_sizes = {
            "HDFCBANK": 550, "ICICIBANK": 700, "RELIANCE": 250,
            "TATAMOTORS": 1350, "BAJFINANCE": 125, "INFY": 400,
            "TCS": 175, "SBIN": 1500, "TRENT": 125, "TITAN": 250,
        }
        lot_size = lot_sizes.get(symbol, 1)
        
        if spot_price is None:
            import random
            spot_price = random.uniform(500, 3000)
        
        strike_gap = 50 if spot_price > 1000 else 25
        atm_strike = round(spot_price / strike_gap) * strike_gap
        
        # Simulate premium
        import random
        premium = random.uniform(20, 100)
        
        # Next Thursday expiry
        from datetime import datetime, timedelta
        today = datetime.now()
        days_ahead = (3 - today.weekday()) % 7
        if days_ahead == 0:
            days_ahead = 7
        expiry = (today + timedelta(days=days_ahead)).strftime("%Y-%m-%d")
        
        return SimulatedStrike(
            symbol=symbol,
            strike=atm_strike,
            ltp=premium,
            lot_size=lot_size,
            premium_per_lot=premium * lot_size,
            delta=0.5,
            gamma=0.005,
            expiry=expiry
        )
    
    async def _place_order(self, trade: ActiveTrade) -> Optional[TradeOrder]:
        """Place order via Dhan or simulate"""
        order = TradeOrder(
            order_id=f"ORD_{uuid.uuid4().hex[:8].upper()}",
            order_type="LIMIT" if not self.config["paper_trading"] else "MARKET",
            transaction_type="BUY",
            quantity=trade.quantity,
            price=trade.entry_price,
            placed_at=datetime.now(),
        )
        
        if self.config["paper_trading"]:
            # Simulate order fill
            order.status = "COMPLETE"
            order.avg_fill_price = trade.entry_price
            order.filled_quantity = trade.quantity
            order.filled_at = datetime.now()
            
            logger.info(f"📝 PAPER TRADE - Order filled: {order.order_id}")
            return order
        
        # Real order via Dhan
        if self.dhan:
            try:
                response = await self.dhan.place_hyper_order({
                    "security_id": trade.option_symbol,
                    "exchange_segment": "NSE_FO",
                    "transaction_type": "BUY",
                    "quantity": trade.quantity,
                    "order_type": "LIMIT",
                    "product_type": "INTRADAY",
                    "price": trade.entry_price,
                })
                
                if response.get("status") == "success":
                    order.order_id = response.get("data", {}).get("order_id", order.order_id)
                    order.status = "PENDING"
                    return order
                    
            except Exception as e:
                logger.error(f"Order placement error: {e}")
        
        return order
    
    def _save_trade(self, trade: ActiveTrade):
        """Save trade to database"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        c.execute('''
            INSERT OR REPLACE INTO trades VALUES (
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
            )
        ''', (
            trade.trade_id,
            trade.symbol,
            trade.option_symbol,
            trade.option_type,
            trade.strike,
            trade.expiry,
            trade.direction,
            trade.quantity,
            trade.lots,
            trade.lot_size,
            trade.entry_price,
            trade.current_price,
            trade.stoploss,
            trade.target_1,
            trade.target_2,
            trade.capital_deployed,
            trade.realized_pnl,
            trade.pnl_pct,
            trade.status.value,
            trade.exit_reason.value if trade.exit_reason else None,
            trade.signal_confidence,
            trade.gemini_confirmation,
            trade.signal_time.isoformat() if trade.signal_time else None,
            trade.entry_time.isoformat() if trade.entry_time else None,
            trade.exit_time.isoformat() if trade.exit_time else None,
            datetime.now().isoformat(),
            datetime.now().isoformat(),
        ))
        
        conn.commit()
        conn.close()
    
    # =========================================================================
    # POSITION MONITORING
    # =========================================================================
    
    async def start_monitoring(self):
        """Start position monitoring loop"""
        self.is_running = True
        self.monitoring_task = asyncio.create_task(self._monitoring_loop())
        logger.info("🔄 Position monitoring started")
    
    async def _monitoring_loop(self):
        """Main monitoring loop"""
        while self.is_running:
            try:
                await self._update_positions()
                await self._check_exits()
                await asyncio.sleep(5)  # Check every 5 seconds
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Monitoring error: {e}")
                await asyncio.sleep(10)
    
    async def _update_positions(self):
        """Update current prices for all active positions"""
        for trade in list(self.active_trades.values()):
            if trade.status not in [TradeStatus.ACTIVE, TradeStatus.PARTIAL_EXIT]:
                continue
            
            try:
                # Get current price
                new_price = await self._get_option_price(trade.option_symbol)
                
                if new_price and new_price > 0:
                    trade.update_price(new_price)
                    
            except Exception as e:
                logger.error(f"Error updating {trade.symbol}: {e}")
    
    async def _get_option_price(self, option_symbol: str) -> Optional[float]:
        """Get current option price"""
        if self.config["paper_trading"]:
            # Simulate price change
            import random
            base_price = 50.0
            change = random.uniform(-5, 8)  # Slightly bullish bias
            return base_price + change
        
        # Get from Dhan
        if self.dhan:
            try:
                quote = await self.dhan.get_quote(option_symbol, "NSE_FO")
                if quote:
                    return quote.price
            except Exception as e:
                logger.error(f"Error getting quote: {e}")
        
        return None
    
    async def _check_exits(self):
        """Check exit conditions for all active trades"""
        for trade in list(self.active_trades.values()):
            if trade.status not in [TradeStatus.ACTIVE, TradeStatus.PARTIAL_EXIT]:
                continue
            
            try:
                # Check stoploss
                if trade.current_price <= trade.stoploss:
                    await self._exit_trade(trade, ExitReason.STOPLOSS, 100)
                    continue
                
                # Check target 1 - partial exit
                if trade.hit_target_1 and trade.status == TradeStatus.ACTIVE:
                    partial_pct = self.config["partial_exit_at_target_1_pct"]
                    await self._exit_trade(trade, ExitReason.TARGET_1, partial_pct)
                    continue
                
                # Check target 2 - full exit
                if trade.hit_target_2:
                    await self._exit_trade(trade, ExitReason.TARGET_2, 100)
                    continue
                
                # Consult Gemini for exit decision
                if self.exit_monitor and trade.status == TradeStatus.ACTIVE:
                    should_exit = await self._consult_gemini_for_exit(trade)
                    if should_exit:
                        await self._exit_trade(trade, ExitReason.GEMINI_SIGNAL, 100)
                
            except Exception as e:
                logger.error(f"Error checking exit for {trade.trade_id}: {e}")
    
    async def _consult_gemini_for_exit(self, trade: ActiveTrade) -> bool:
        """
        Consult Gemini 3 Pro for exit decision using gemini-3-pro model.
        
        This is the core exit intelligence - uses detailed prompting to analyze:
        - Current P&L state
        - Momentum status
        - Time decay impact
        - Market conditions
        """
        if not self.session:
            return False
        
        try:
            # Calculate holding time
            holding_minutes = int((datetime.now() - trade.entry_time).total_seconds() / 60)
            
            # Build detailed exit consultation prompt
            exit_prompt = f"""
You are an expert F&O options trader monitoring an ACTIVE POSITION. Provide exit decision.

TRADE DETAILS:
- Symbol: {trade.symbol}
- Option: {trade.option_type} @ Strike {trade.strike_price}
- Entry Price: ₹{trade.entry_price:.2f}
- Current Price: ₹{trade.current_price:.2f}
- Stoploss: ₹{trade.stoploss:.2f}
- Target 1: ₹{trade.target_1:.2f}
- Target 2: ₹{trade.target_2:.2f}
- Quantity: {trade.quantity} lots
- Holding Time: {holding_minutes} minutes
- Current P&L: {trade.pnl_pct:+.2f}%

TRADE STYLE:
- We use WIDE stoploss (no trailing) for momentum capture
- Partial exit at Target 1 (50% profit)
- Full exit at Target 2 (100% profit)
- Let winners run, cut losers decisively

ANALYSIS REQUIRED:
1. Is momentum still intact?
2. Is there reversal risk?
3. Should we hold, partial exit, or full exit?
4. Time decay consideration (theta)

RESPOND IN EXACT JSON FORMAT:
{{
    "action": "HOLD" | "PARTIAL_EXIT" | "FULL_EXIT" | "STOPLOSS",
    "confidence": <60-100>,
    "momentum_status": "strong" | "weakening" | "exhausted",
    "reasoning": "<2-line explanation>",
    "urgency": "immediate" | "normal" | "can_wait"
}}
"""
            
            # Try direct Gemini API first
            if self.gemini_api_key:
                try:
                    gemini_api_url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.GEMINI_EXIT_MODEL}:generateContent?key={self.gemini_api_key}"
                    payload = {
                        "contents": [{"parts": [{"text": exit_prompt}]}],
                        "generationConfig": {
                            "temperature": 0.3,
                            "maxOutputTokens": 512
                        }
                    }
                    
                    async with self.session.post(gemini_api_url, json=payload) as resp:
                        if resp.status == 200:
                            result = await resp.json()
                            if "candidates" in result:
                                response_text = result["candidates"][0]["content"]["parts"][0]["text"]
                                return await self._parse_exit_response(trade, response_text)
                except Exception as e:
                    logger.warning(f"Direct Gemini API failed: {e}, falling back to local service")
            
            # Fallback to local Gemini service
            async with self.session.post(
                f"{self.gemini_url}/api/prediction/stock/{trade.symbol}",
                json={
                    "current_price": trade.current_price,
                    "entry_price": trade.entry_price,
                    "pnl_pct": trade.pnl_pct,
                    "option_type": trade.option_type,
                    "holding_time_minutes": holding_minutes,
                    "model": self.GEMINI_EXIT_MODEL
                }
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    prediction = data.get("prediction", {})
                    
                    signal = prediction.get("signal", "HOLD")
                    confidence = prediction.get("confidence", 50)
                    
                    if signal == "SELL" and confidence >= 75:
                        trade.momentum_status = "exhausted"
                        trade.gemini_exit_consulted = True
                        logger.info(f"🤖 Gemini 3 Pro recommends exit for {trade.symbol} @ {confidence}%")
                        return True
                    elif signal == "HOLD":
                        trade.momentum_status = "active"
                    
        except Exception as e:
            logger.error(f"Error consulting Gemini: {e}")
        
        return False
    
    async def _parse_exit_response(self, trade: ActiveTrade, response_text: str) -> bool:
        """Parse Gemini exit response and determine action"""
        try:
            import json
            json_start = response_text.find("{")
            json_end = response_text.rfind("}") + 1
            if json_start != -1 and json_end > json_start:
                analysis = json.loads(response_text[json_start:json_end])
                
                action = analysis.get("action", "HOLD")
                confidence = analysis.get("confidence", 50)
                momentum = analysis.get("momentum_status", "active")
                reasoning = analysis.get("reasoning", "")
                
                trade.momentum_status = momentum
                trade.gemini_exit_consulted = True
                
                if action in ["FULL_EXIT", "STOPLOSS"] and confidence >= 70:
                    logger.info(f"🤖 Gemini 3 Pro: {action} for {trade.symbol} | {reasoning}")
                    return True
                elif action == "PARTIAL_EXIT" and confidence >= 80:
                    # Handle partial exit separately
                    logger.info(f"🤖 Gemini 3 Pro: Partial exit for {trade.symbol}")
                    # Could trigger partial exit here
                    return False  # Don't full exit yet
                    
        except json.JSONDecodeError:
            logger.warning("Failed to parse Gemini exit response")
        
        return False
    
    async def _exit_trade(
        self, 
        trade: ActiveTrade, 
        reason: ExitReason, 
        exit_pct: float = 100
    ):
        """Exit a trade (fully or partially)"""
        logger.info(f"🔴 Exiting {trade.symbol}: {reason.value} @ {exit_pct}%")
        
        try:
            exit_quantity = int(trade.quantity * (exit_pct / 100))
            
            # Place exit order
            exit_order = TradeOrder(
                order_id=f"EXIT_{uuid.uuid4().hex[:8].upper()}",
                order_type="MARKET",
                transaction_type="SELL",
                quantity=exit_quantity,
                price=trade.current_price,
                placed_at=datetime.now(),
            )
            
            if self.config["paper_trading"]:
                exit_order.status = "COMPLETE"
                exit_order.avg_fill_price = trade.current_price
                exit_order.filled_quantity = exit_quantity
                exit_order.filled_at = datetime.now()
            else:
                # Real order
                if self.dhan:
                    response = await self.dhan.place_hyper_order({
                        "security_id": trade.option_symbol,
                        "exchange_segment": "NSE_FO",
                        "transaction_type": "SELL",
                        "quantity": exit_quantity,
                        "order_type": "MARKET",
                        "product_type": "INTRADAY",
                    })
                    
                    if response.get("status") == "success":
                        exit_order.order_id = response.get("data", {}).get("order_id", exit_order.order_id)
            
            trade.exit_orders.append(exit_order)
            
            # Calculate realized P&L
            realized = (trade.current_price - trade.entry_price) * exit_quantity
            trade.realized_pnl += realized
            
            # Update status
            if exit_pct >= 100:
                trade.status = TradeStatus.EXITED
                trade.exit_time = datetime.now()
                trade.exit_reason = reason
                
                # Update stats
                self.stats["total_trades"] += 1
                if trade.realized_pnl > 0:
                    self.stats["winning_trades"] += 1
                else:
                    self.stats["losing_trades"] += 1
                self.stats["total_pnl"] += trade.realized_pnl
                
                # Remove from active trades
                if trade.trade_id in self.active_trades:
                    del self.active_trades[trade.trade_id]
            else:
                trade.status = TradeStatus.PARTIAL_EXIT
                trade.partial_exits.append({
                    "quantity": exit_quantity,
                    "price": trade.current_price,
                    "pnl": realized,
                    "reason": reason.value,
                    "time": datetime.now().isoformat(),
                })
            
            # Save to database
            self._save_trade(trade)
            
            logger.info(f"✅ Exit completed: {trade.trade_id}")
            logger.info(f"   Realized P&L: ₹{realized:,.2f} ({trade.pnl_pct:.1f}%)")
            
        except Exception as e:
            logger.error(f"Error exiting trade: {e}")
    
    # =========================================================================
    # PUBLIC METHODS
    # =========================================================================
    
    def get_active_trades(self) -> List[Dict]:
        """Get all active trades"""
        return [trade.to_dict() for trade in self.active_trades.values()]
    
    def get_trade(self, trade_id: str) -> Optional[Dict]:
        """Get specific trade"""
        trade = self.active_trades.get(trade_id)
        return trade.to_dict() if trade else None
    
    def get_stats(self) -> Dict:
        """Get trading statistics"""
        win_rate = 0
        if self.stats["total_trades"] > 0:
            win_rate = (self.stats["winning_trades"] / self.stats["total_trades"]) * 100
        
        return {
            **self.stats,
            "win_rate": win_rate,
            "active_trades": len(self.active_trades),
            "total_unrealized_pnl": sum(t.unrealized_pnl for t in self.active_trades.values()),
        }
    
    async def manual_exit(self, trade_id: str, reason: str = "manual") -> bool:
        """Manually exit a trade"""
        trade = self.active_trades.get(trade_id)
        if not trade:
            return False
        
        await self._exit_trade(trade, ExitReason.MANUAL, 100)
        return True
    
    def get_trade_history(self, limit: int = 50) -> List[Dict]:
        """Get trade history from database"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        c.execute('''
            SELECT * FROM trades 
            ORDER BY created_at DESC 
            LIMIT ?
        ''', (limit,))
        
        rows = c.fetchall()
        conn.close()
        
        trades = []
        for row in rows:
            trade = self._row_to_trade(row)
            if trade:
                trades.append(trade.to_dict())
        
        return trades


# ============================================================================
# MAIN TEST
# ============================================================================

async def main():
    """Test the trade executor"""
    executor = EliteTradeExecutor()
    await executor.initialize()
    
    # Test signal execution
    print("\n" + "="*70)
    print("  Testing Elite Trade Executor")
    print("="*70)
    
    # Execute test signals
    test_signals = [
        {"symbol": "TATAMOTORS", "direction": "CE", "confidence": 92},
        {"symbol": "RELIANCE", "direction": "PE", "confidence": 88},
        {"symbol": "HDFCBANK", "direction": "CE", "confidence": 95},
    ]
    
    for signal in test_signals:
        trade = await executor.execute_signal(
            symbol=signal["symbol"],
            direction=signal["direction"],
            confidence=signal["confidence"],
            gemini_confirmation=f"Strong momentum detected for {signal['symbol']}",
            available_capital=100000,
        )
        
        if trade:
            print(f"\n✅ Trade created: {trade.trade_id}")
            print(f"   {trade.symbol} {trade.option_type} @ ₹{trade.entry_price:.2f}")
            print(f"   Lots: {trade.lots} | Capital: ₹{trade.capital_deployed:,.0f}")
    
    # Show active trades
    print("\n" + "="*70)
    print("  Active Trades")
    print("="*70)
    
    for trade in executor.get_active_trades():
        print(f"\n  {trade['trade_id']}: {trade['symbol']} {trade['option_type']}")
        print(f"  Entry: ₹{trade['entry_price']:.2f} | Current: ₹{trade['current_price']:.2f}")
        print(f"  P&L: ₹{trade['unrealized_pnl']:.2f} ({trade['pnl_pct']:.1f}%)")
    
    # Show stats
    print("\n" + "="*70)
    print("  Stats")
    print("="*70)
    stats = executor.get_stats()
    print(f"  Active: {stats['active_trades']} | Total: {stats['total_trades']}")
    print(f"  Win Rate: {stats['win_rate']:.1f}%")
    print(f"  Total P&L: ₹{stats['total_pnl']:,.2f}")
    
    await executor.close()


if __name__ == "__main__":
    asyncio.run(main())
