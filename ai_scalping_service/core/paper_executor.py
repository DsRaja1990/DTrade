"""
Paper Trading Executor
Simulates trade execution without real money
All trades are stored in database for analysis
"""

import asyncio
import logging
import uuid
from datetime import datetime, date
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.models import (
    ScalpingDatabase, get_database, TradeMode, PaperTrade, Signal, SignalType
)
from market_data.real_data_client import LiveQuote


logger = logging.getLogger(__name__)


class OrderSide(Enum):
    BUY = "BUY"
    SELL = "SELL"


class OrderType(Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"


@dataclass
class PaperPosition:
    """Current paper trading position"""
    trade_id: str
    instrument: str
    symbol: str
    option_type: str  # CE or PE
    strike: float
    entry_price: float
    current_price: float
    quantity: int
    lot_size: int
    entry_time: datetime
    entry_reason: str
    momentum_at_entry: float
    ai_confidence: float
    unrealized_pnl: float = 0.0
    unrealized_pnl_pct: float = 0.0
    max_profit: float = 0.0
    max_loss: float = 0.0
    
    def update_price(self, new_price: float):
        """Update current price and PnL"""
        self.current_price = new_price
        self.unrealized_pnl = (new_price - self.entry_price) * self.quantity * self.lot_size
        self.unrealized_pnl_pct = (new_price - self.entry_price) / self.entry_price * 100
        
        # Track extremes
        self.max_profit = max(self.max_profit, self.unrealized_pnl)
        self.max_loss = min(self.max_loss, self.unrealized_pnl)


@dataclass
class ExecutionResult:
    """Result of trade execution"""
    success: bool
    trade_id: str = ""
    message: str = ""
    fill_price: float = 0.0
    fill_quantity: int = 0
    timestamp: datetime = field(default_factory=datetime.now)


class PaperTradingExecutor:
    """
    Paper trading execution engine
    - Simulates market orders with realistic slippage
    - Tracks all positions and PnL
    - Stores everything to database for analysis
    """
    
    # Slippage simulation
    SLIPPAGE_PCT = 0.05  # 0.05% slippage on execution
    
    # Position limits
    MAX_POSITIONS = 5
    MAX_EXPOSURE_PER_INSTRUMENT = 2
    
    # Lot sizes
    LOT_SIZES = {
        "NIFTY": 75,
        "BANKNIFTY": 35,
        "FINNIFTY": 65,
        "SENSEX": 20,
        "BANKEX": 30
    }
    
    def __init__(self, initial_capital: float = 500000.0):
        self.initial_capital = initial_capital
        self.capital = initial_capital
        self.realized_pnl = 0.0
        
        # Current positions
        self._positions: Dict[str, PaperPosition] = {}
        
        # Trade history
        self._trades: List[Dict] = []
        
        # Database
        self._db = get_database()
        
        # Daily tracking
        self._daily_trades = 0
        self._daily_pnl = 0.0
        self._current_date = date.today()
        
        logger.info(f"PaperTradingExecutor initialized with capital: ₹{initial_capital:,.2f}")
    
    @property
    def total_pnl(self) -> float:
        """Total realized + unrealized PnL"""
        unrealized = sum(p.unrealized_pnl for p in self._positions.values())
        return self.realized_pnl + unrealized
    
    @property
    def position_count(self) -> int:
        """Number of open positions"""
        return len(self._positions)
    
    @property
    def open_positions(self) -> List[PaperPosition]:
        """List of open positions"""
        return list(self._positions.values())
    
    def _reset_daily_if_needed(self):
        """Reset daily counters on new day"""
        today = date.today()
        if today != self._current_date:
            # Save previous day stats
            self._db.update_daily_stats(self._current_date)
            
            self._daily_trades = 0
            self._daily_pnl = 0.0
            self._current_date = today
    
    def _apply_slippage(self, price: float, side: OrderSide) -> float:
        """Apply realistic slippage to price"""
        slippage = price * self.SLIPPAGE_PCT / 100
        if side == OrderSide.BUY:
            return price + slippage  # Pay more when buying
        else:
            return price - slippage  # Get less when selling
    
    def can_enter_position(self, instrument: str) -> Tuple[bool, str]:
        """Check if we can enter a new position"""
        self._reset_daily_if_needed()
        
        # Check total position limit
        if len(self._positions) >= self.MAX_POSITIONS:
            return False, f"Max positions ({self.MAX_POSITIONS}) reached"
        
        # Check instrument exposure
        instrument_positions = sum(1 for p in self._positions.values() 
                                   if p.instrument == instrument)
        if instrument_positions >= self.MAX_EXPOSURE_PER_INSTRUMENT:
            return False, f"Max exposure for {instrument} reached"
        
        # Check capital
        if self.capital < self.initial_capital * 0.1:
            return False, "Insufficient capital"
        
        return True, "OK"
    
    async def enter_position(
        self,
        instrument: str,
        option_type: str,  # CE or PE
        strike: float,
        current_price: float,
        lots: int,
        reason: str,
        momentum_score: float = 0.0,
        ai_confidence: float = 0.0
    ) -> ExecutionResult:
        """
        Enter a new paper position
        
        Args:
            instrument: Index symbol (NIFTY, BANKNIFTY, etc.)
            option_type: CE or PE
            strike: Strike price
            current_price: Current option LTP
            lots: Number of lots
            reason: Entry reason for analysis
            momentum_score: Momentum score at entry
            ai_confidence: AI confidence at entry
        """
        can_enter, message = self.can_enter_position(instrument)
        if not can_enter:
            return ExecutionResult(success=False, message=message)
        
        # Generate trade ID
        trade_id = f"PT_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
        
        # Apply slippage
        fill_price = self._apply_slippage(current_price, OrderSide.BUY)
        
        lot_size = self.LOT_SIZES.get(instrument, 50)
        quantity = lots
        total_value = fill_price * quantity * lot_size
        
        # Create position
        position = PaperPosition(
            trade_id=trade_id,
            instrument=instrument,
            symbol=f"{instrument}_{strike}_{option_type}",
            option_type=option_type,
            strike=strike,
            entry_price=fill_price,
            current_price=fill_price,
            quantity=quantity,
            lot_size=lot_size,
            entry_time=datetime.now(),
            entry_reason=reason,
            momentum_at_entry=momentum_score,
            ai_confidence=ai_confidence
        )
        
        self._positions[trade_id] = position
        
        # Record in database
        paper_trade = PaperTrade(
            trade_id=trade_id,
            timestamp_entry=datetime.now(),
            instrument=instrument,
            option_type=option_type,
            strike=strike,
            entry_price=fill_price,
            quantity=quantity,
            lot_size=lot_size,
            status="entered",
            entry_reason=reason,
            momentum_at_entry=momentum_score,
            ai_confidence_entry=ai_confidence
        )
        self._db.insert_paper_trade(paper_trade)
        
        # Record signal
        signal = Signal(
            timestamp=datetime.now(),
            instrument=instrument,
            signal_type=SignalType.MOMENTUM_ENTRY.value,
            direction="LONG",
            strength=momentum_score,
            momentum_score=momentum_score,
            ai_confidence=ai_confidence,
            reason=reason,
            was_executed=True,
            execution_result=f"Entered at {fill_price}"
        )
        self._db.insert_signal(signal)
        
        self._daily_trades += 1
        
        logger.info(f"📈 PAPER ENTRY: {trade_id} | {instrument} {strike}{option_type} | "
                   f"{quantity} lots @ ₹{fill_price:.2f} | Reason: {reason}")
        
        return ExecutionResult(
            success=True,
            trade_id=trade_id,
            message=f"Position entered successfully",
            fill_price=fill_price,
            fill_quantity=quantity,
            timestamp=datetime.now()
        )
    
    async def exit_position(
        self,
        trade_id: str,
        current_price: float,
        reason: str,
        momentum_score: float = 0.0
    ) -> ExecutionResult:
        """
        Exit an open paper position
        
        Args:
            trade_id: Trade ID to exit
            current_price: Current option LTP
            reason: Exit reason for analysis
            momentum_score: Momentum score at exit
        """
        if trade_id not in self._positions:
            return ExecutionResult(success=False, message=f"Position {trade_id} not found")
        
        position = self._positions[trade_id]
        
        # Apply slippage
        fill_price = self._apply_slippage(current_price, OrderSide.SELL)
        
        # Calculate PnL
        pnl = (fill_price - position.entry_price) * position.quantity * position.lot_size
        pnl_pct = (fill_price - position.entry_price) / position.entry_price * 100
        
        # Update realized PnL
        self.realized_pnl += pnl
        self._daily_pnl += pnl
        
        # Update database
        self._db.update_paper_trade_exit(
            trade_id=trade_id,
            exit_price=fill_price,
            exit_reason=reason,
            momentum_at_exit=momentum_score,
            pnl=pnl,
            pnl_percent=pnl_pct
        )
        
        # Record exit signal
        signal = Signal(
            timestamp=datetime.now(),
            instrument=position.instrument,
            signal_type=reason if reason in [s.value for s in SignalType] else SignalType.MOMENTUM_EXIT.value,
            direction="EXIT",
            strength=momentum_score,
            momentum_score=momentum_score,
            ai_confidence=position.ai_confidence,
            reason=reason,
            was_executed=True,
            execution_result=f"Exited at {fill_price}, PnL: {pnl:+.2f}"
        )
        self._db.insert_signal(signal)
        
        # Remove position
        del self._positions[trade_id]
        
        emoji = "✅" if pnl > 0 else "❌"
        logger.info(f"{emoji} PAPER EXIT: {trade_id} | {position.instrument} {position.strike}{position.option_type} | "
                   f"@ ₹{fill_price:.2f} | PnL: ₹{pnl:+,.2f} ({pnl_pct:+.2f}%) | {reason}")
        
        return ExecutionResult(
            success=True,
            trade_id=trade_id,
            message=f"Position exited. PnL: ₹{pnl:+,.2f}",
            fill_price=fill_price,
            fill_quantity=position.quantity,
            timestamp=datetime.now()
        )
    
    async def exit_all_positions(self, prices: Dict[str, float], reason: str = "exit_all") -> List[ExecutionResult]:
        """Exit all open positions"""
        results = []
        
        for trade_id, position in list(self._positions.items()):
            price_key = f"{position.instrument}_{position.strike}_{position.option_type}"
            current_price = prices.get(price_key, position.current_price)
            
            result = await self.exit_position(trade_id, current_price, reason)
            results.append(result)
        
        return results
    
    def update_positions(self, prices: Dict[str, float]):
        """Update all position prices and PnL"""
        for trade_id, position in self._positions.items():
            price_key = f"{position.instrument}_{position.strike}_{position.option_type}"
            if price_key in prices:
                old_pnl = position.unrealized_pnl
                position.update_price(prices[price_key])
                
                # Update max profit/loss in database
                self._db.update_paper_trade_extremes(trade_id, position.unrealized_pnl)
    
    def get_position_summary(self) -> Dict:
        """Get summary of all positions"""
        positions_data = []
        total_unrealized = 0.0
        
        for pos in self._positions.values():
            positions_data.append({
                "trade_id": pos.trade_id,
                "instrument": pos.instrument,
                "option_type": pos.option_type,
                "strike": pos.strike,
                "entry_price": pos.entry_price,
                "current_price": pos.current_price,
                "quantity": pos.quantity,
                "lot_size": pos.lot_size,
                "unrealized_pnl": pos.unrealized_pnl,
                "unrealized_pnl_pct": pos.unrealized_pnl_pct,
                "entry_time": pos.entry_time.isoformat(),
                "duration_seconds": (datetime.now() - pos.entry_time).total_seconds()
            })
            total_unrealized += pos.unrealized_pnl
        
        return {
            "position_count": len(self._positions),
            "positions": positions_data,
            "unrealized_pnl": total_unrealized,
            "realized_pnl": self.realized_pnl,
            "total_pnl": self.realized_pnl + total_unrealized,
            "daily_trades": self._daily_trades,
            "daily_pnl": self._daily_pnl,
            "capital": self.capital,
            "total_value": self.capital + self.realized_pnl + total_unrealized
        }
    
    def get_trading_stats(self) -> Dict:
        """Get comprehensive trading statistics"""
        return self._db.get_analysis_summary()
    
    async def check_stop_loss_target(
        self,
        stop_loss_pct: float = 2.0,
        target_pct: float = 1.0,
        time_exit_minutes: int = 30
    ) -> List[ExecutionResult]:
        """
        Check all positions for stop loss, target, or time-based exit
        
        Args:
            stop_loss_pct: Stop loss percentage
            target_pct: Profit target percentage
            time_exit_minutes: Max holding time in minutes
        """
        results = []
        
        for trade_id, position in list(self._positions.items()):
            reason = None
            
            # Check stop loss
            if position.unrealized_pnl_pct <= -stop_loss_pct:
                reason = SignalType.STOP_LOSS.value
            
            # Check target
            elif position.unrealized_pnl_pct >= target_pct:
                reason = SignalType.TARGET_HIT.value
            
            # Check time exit
            else:
                duration = (datetime.now() - position.entry_time).total_seconds() / 60
                if duration >= time_exit_minutes:
                    reason = SignalType.TIME_EXIT.value
            
            if reason:
                result = await self.exit_position(
                    trade_id,
                    position.current_price,
                    reason
                )
                results.append(result)
        
        return results


class ProductionTradingExecutor:
    """
    Production trading executor
    Actually places orders through Dhan API
    """
    
    def __init__(self, access_token: str, client_id: str, initial_capital: float = 500000.0):
        self.access_token = access_token
        self.client_id = client_id
        self.initial_capital = initial_capital
        
        # Import Dhan client
        from market_data.dhan_client import DhanClient
        self._dhan = DhanClient(access_token, client_id)
        
        self._db = get_database()
        
        logger.info("ProductionTradingExecutor initialized - REAL TRADING ENABLED")
        logger.warning("⚠️ REAL MONEY WILL BE USED FOR TRADES ⚠️")
    
    async def enter_position(self, *args, **kwargs) -> ExecutionResult:
        """Enter position with real order"""
        # TODO: Implement real order placement
        logger.error("Production trading not yet implemented")
        return ExecutionResult(success=False, message="Production trading not yet implemented")
    
    async def exit_position(self, *args, **kwargs) -> ExecutionResult:
        """Exit position with real order"""
        # TODO: Implement real order placement
        logger.error("Production trading not yet implemented")
        return ExecutionResult(success=False, message="Production trading not yet implemented")


def create_executor(mode: TradeMode = None, initial_capital: float = 500000.0,
                    access_token: str = None, client_id: str = None):
    """
    Factory to create appropriate executor
    
    Args:
        mode: Trading mode (paper or production)
        initial_capital: Initial capital
        access_token: Dhan access token (for production)
        client_id: Dhan client ID (for production)
    """
    if mode is None:
        db = get_database()
        mode = db.get_trading_mode()
    
    if mode == TradeMode.PRODUCTION:
        if not access_token or not client_id:
            logger.error("Production mode requires access token and client ID")
            logger.info("Falling back to paper trading")
            return PaperTradingExecutor(initial_capital)
        return ProductionTradingExecutor(access_token, client_id, initial_capital)
    
    return PaperTradingExecutor(initial_capital)
