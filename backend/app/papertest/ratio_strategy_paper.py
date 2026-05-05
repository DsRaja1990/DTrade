"""
Ratio Strategy Paper Trading Implementation

This module adapts the existing ratio strategy for paper trading execution
with real market data integration.
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
import uuid
from dataclasses import dataclass

from .strategy_engine import BaseStrategy, Trade, TradeDirection, Position, StrategyStatus
# Updated to use ratio service instead of backend ratio strategy
import requests
import asyncio
from typing import Dict, Any

logger = logging.getLogger(__name__)

# Constants moved from backend ratio strategy
STRATEGIES = {
    "NIFTY": {
        "symbol": "NIFTY",
        "execution_windows": [
            {"start": "09:15", "end": "09:45", "type": "opening"},
            {"start": "11:30", "end": "12:30", "type": "midday"},
            {"start": "14:30", "end": "15:15", "type": "closing"}
        ]
    },
    "BANKNIFTY": {
        "symbol": "BANKNIFTY", 
        "execution_windows": [
            {"start": "09:15", "end": "09:45", "type": "opening"},
            {"start": "11:00", "end": "12:00", "type": "midday"},
            {"start": "14:45", "end": "15:25", "type": "closing"}
        ]
    },
    "SENSEX": {
        "symbol": "SENSEX",
        "execution_windows": [
            {"start": "09:15", "end": "09:45", "type": "opening"},
            {"start": "11:45", "end": "12:45", "type": "midday"},
            {"start": "14:15", "end": "15:00", "type": "closing"}
        ]
    }
}

RATIO_SERVICE_URL = "http://localhost:8001"  # Ratio service URL

# Constants moved from backend ratio strategy
STRIKE_INTERVALS = {
    "NIFTY": 50,
    "BANKNIFTY": 100,
    "SENSEX": 100
}

STRIKE_OFFSETS = {
    "NIFTY": {"CE": 100, "PE": -100},
    "BANKNIFTY": {"CE": 200, "PE": -200},
    "SENSEX": {"CE": 150, "PE": -150}
}

RATIO_CONFIGS = {
    "NIFTY": {"ratio": 1.2, "min_premium": 15, "max_premium": 45},
    "BANKNIFTY": {"ratio": 1.1, "min_premium": 25, "max_premium": 75},
    "SENSEX": {"ratio": 1.15, "min_premium": 20, "max_premium": 60}
}

PREMIUM_TARGETS = {
    "NIFTY": {"min": 15, "max": 45, "optimal": 30},
    "BANKNIFTY": {"min": 25, "max": 75, "optimal": 50},
    "SENSEX": {"min": 20, "max": 60, "optimal": 40}
}

def get_market_data(symbol: str):
    """Get market data from ratio service"""
    try:
        response = requests.get(f"{RATIO_SERVICE_URL}/market-data/{symbol}")
        if response.status_code == 200:
            return response.json()
        return None
    except:
        return None

def is_market_hours():
    """Check if market is open"""
    now = datetime.now().time()
    market_start = datetime.strptime("09:15", "%H:%M").time()
    market_end = datetime.strptime("15:30", "%H:%M").time()
    return market_start <= now <= market_end

def get_current_market_phase():
    """Get current market phase"""
    now = datetime.now().time()
    if datetime.strptime("09:15", "%H:%M").time() <= now <= datetime.strptime("11:00", "%H:%M").time():
        return "opening"
    elif datetime.strptime("11:00", "%H:%M").time() <= now <= datetime.strptime("14:00", "%H:%M").time():
        return "midday"
    else:
        return "closing"

@dataclass
class RatioTradeSetup:
    """Ratio strategy trade setup"""
    underlying: str
    ce_strike: float
    pe_strike: float
    ce_quantity: int
    pe_quantity: int
    ce_premium: float
    pe_premium: float
    setup_time: datetime
    target_premium: float
    stop_loss: float

class RatioStrategyPaperTrader(BaseStrategy):
    """
    Paper Trading implementation of Ratio Strategy
    
    Executes ratio spread strategies using real market data in a simulated environment
    """
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__("ratio_strategy", config)
        
        # Strategy configuration
        self.nifty_lots = config.get('nifty_lots', 20)
        self.banknifty_lots = config.get('banknifty_lots', 30)
        self.sensex_lots = config.get('sensex_lots', 50)
        
        # Paper trading specific attributes
        self.virtual_capital = config.get('virtual_capital', 1000000.0)  # 10 Lakh
        self.current_capital = self.virtual_capital
        self.active_setups: Dict[str, RatioTradeSetup] = {}
        self.market_data_cache: Dict[str, Dict[str, Any]] = {}
        
        # Risk management
        self.max_position_risk = config.get('max_position_risk', 0.02)  # 2% per trade
        self.max_total_risk = config.get('max_total_risk', 0.10)  # 10% total exposure
        
        # Performance tracking
        self.daily_pnl = 0.0
        self.total_fees = 0.0
        self.max_drawdown = 0.0
        self.peak_capital = self.virtual_capital
        
        # Market data subscription
        self.subscribed_instruments = set()
        
        self.logger.info(f"Ratio Strategy Paper Trader initialized with capital: ₹{self.virtual_capital:,.2f}")
    
    async def initialize(self) -> bool:
        """Initialize the strategy"""
        try:
            # Initialize core strategy
            if hasattr(self.core_strategy, 'initialize'):
                await self.core_strategy.initialize()
            
            # Subscribe to market data for major indices
            self.subscribed_instruments.update(["NIFTY", "BANKNIFTY", "SENSEX"])
            
            # Initialize positions tracking
            for instrument in self.subscribed_instruments:
                self.positions[instrument + "_CE"] = Position(
                    instrument=instrument + "_CE",
                    quantity=0,
                    average_price=0.0,
                    current_price=0.0,
                    unrealized_pnl=0.0,
                    realized_pnl=0.0,
                    timestamp=datetime.now(timezone.utc)
                )
                self.positions[instrument + "_PE"] = Position(
                    instrument=instrument + "_PE",
                    quantity=0,
                    average_price=0.0,
                    current_price=0.0,
                    unrealized_pnl=0.0,
                    realized_pnl=0.0,
                    timestamp=datetime.now(timezone.utc)
                )
            
            self.logger.info("Ratio strategy initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize ratio strategy: {e}")
            return False
    
    async def on_market_data(self, data: Dict[str, Any]) -> None:
        """Handle incoming market data"""
        try:
            # Update market data cache
            for instrument, price_data in data.items():
                self.market_data_cache[instrument] = price_data
                
                # Update position prices
                for position_key in self.positions:
                    if instrument in position_key:
                        position = self.positions[position_key]
                        if position.quantity != 0:
                            position.current_price = price_data.get('ltp', position.current_price)
                            position.unrealized_pnl = (position.current_price - position.average_price) * position.quantity
                            position.timestamp = datetime.now(timezone.utc)
            
            # Check for trading opportunities
            await self._check_trading_opportunities()
            
        except Exception as e:
            self.logger.error(f"Error processing market data: {e}")
    
    async def on_tick(self) -> None:
        """Called on each time tick"""
        try:
            if self.status != StrategyStatus.RUNNING:
                return
            
            # Check market hours
            if not is_market_hours():
                return
            
            # Update performance metrics
            await self._update_performance_metrics()
            
            # Monitor active positions
            await self._monitor_positions()
            
            # Check exit conditions
            await self._check_exit_conditions()
            
        except Exception as e:
            self.logger.error(f"Error in strategy tick: {e}")
    
    async def cleanup(self) -> None:
        """Cleanup strategy resources"""
        try:
            # Close all active positions
            await self._close_all_positions()
            
            # Save final metrics
            await self._save_final_metrics()
            
            self.logger.info("Ratio strategy cleanup completed")
            
        except Exception as e:
            self.logger.error(f"Error during cleanup: {e}")
    
    async def _check_trading_opportunities(self):
        """Check for ratio trading opportunities"""
        try:
            current_phase = get_current_market_phase()
            
            for underlying in ["NIFTY", "BANKNIFTY", "SENSEX"]:
                if underlying not in self.market_data_cache:
                    continue
                
                market_data = self.market_data_cache[underlying]
                spot_price = market_data.get('ltp', 0)
                
                if spot_price == 0:
                    continue
                
                # Check if we can enter a new position
                if self._can_enter_position(underlying):
                    setup = await self._identify_ratio_setup(underlying, spot_price, current_phase)
                    if setup:
                        await self._execute_ratio_setup(setup)
        
        except Exception as e:
            self.logger.error(f"Error checking trading opportunities: {e}")
    
    def _can_enter_position(self, underlying: str) -> bool:
        """Check if we can enter a new position for the underlying"""
        # Check if already have active setup for this underlying
        for setup_id, setup in self.active_setups.items():
            if setup.underlying == underlying:
                return False
        
        # Check capital availability
        required_margin = self._calculate_required_margin(underlying)
        available_capital = self.current_capital * self.max_position_risk
        
        return required_margin <= available_capital
    
    def _calculate_required_margin(self, underlying: str) -> float:
        """Calculate required margin for a position"""
        # Simplified margin calculation (in real implementation, use broker's margin calculator)
        base_margins = {
            "NIFTY": 50000,
            "BANKNIFTY": 80000,
            "SENSEX": 60000
        }
        return base_margins.get(underlying, 50000)
    
    async def _identify_ratio_setup(self, underlying: str, spot_price: float, market_phase: str) -> Optional[RatioTradeSetup]:
        """Identify potential ratio spread setup"""
        try:
            # Get ATM strikes
            strike_interval = STRIKE_INTERVALS.get(underlying, 50)
            atm_strike = round(spot_price / strike_interval) * strike_interval
            
            # Define CE and PE strikes based on strategy configuration
            ce_strike = atm_strike + STRIKE_OFFSETS[underlying]["CE"]
            pe_strike = atm_strike + STRIKE_OFFSETS[underlying]["PE"]
            
            # Get option premiums (simulated for paper trading)
            ce_premium = await self._get_option_premium(underlying, ce_strike, "CE", spot_price)
            pe_premium = await self._get_option_premium(underlying, pe_strike, "PE", spot_price)
            
            if ce_premium <= 0 or pe_premium <= 0:
                return None
            
            # Calculate quantities for ratio spread
            position_size = self.core_strategy.position_sizes[underlying]
            ce_quantity = position_size
            pe_quantity = int(position_size * RATIO_CONFIGS[underlying]["ratio"])
            
            # Check if premium targets are met
            target_premium = PREMIUM_TARGETS[underlying]["min"]
            if ce_premium < target_premium or pe_premium < target_premium:
                return None
            
            return RatioTradeSetup(
                underlying=underlying,
                ce_strike=ce_strike,
                pe_strike=pe_strike,
                ce_quantity=ce_quantity,
                pe_quantity=pe_quantity,
                ce_premium=ce_premium,
                pe_premium=pe_premium,
                setup_time=datetime.now(timezone.utc),
                target_premium=target_premium * 1.5,  # 50% profit target
                stop_loss=target_premium * 0.7  # 30% stop loss
            )
            
        except Exception as e:
            self.logger.error(f"Error identifying ratio setup for {underlying}: {e}")
            return None
    
    async def _get_option_premium(self, underlying: str, strike: float, option_type: str, spot_price: float) -> float:
        """Get option premium (simulated for paper trading)"""
        try:
            # Simplified Black-Scholes approximation for paper trading
            # In real implementation, get from market data feed
            
            import math
            
            # Basic parameters
            time_to_expiry = 7 / 365  # 1 week
            risk_free_rate = 0.06  # 6%
            volatility = 0.20  # 20% IV
            
            # Moneyness
            moneyness = spot_price / strike
            
            # Simplified premium calculation
            if option_type == "CE":
                intrinsic_value = max(0, spot_price - strike)
                time_value = strike * volatility * math.sqrt(time_to_expiry) * 0.4
            else:  # PE
                intrinsic_value = max(0, strike - spot_price)
                time_value = strike * volatility * math.sqrt(time_to_expiry) * 0.4
            
            premium = intrinsic_value + time_value
            
            # Add some randomness for realistic simulation
            import random
            premium *= (1 + random.uniform(-0.1, 0.1))  # ±10% variation
            
            return max(1.0, premium)  # Minimum ₹1 premium
            
        except Exception as e:
            self.logger.error(f"Error calculating option premium: {e}")
            return 0.0
    
    async def _execute_ratio_setup(self, setup: RatioTradeSetup):
        """Execute the ratio spread setup"""
        try:
            setup_id = str(uuid.uuid4())
            
            # Execute CE trade (sell)
            ce_trade = Trade(
                id=str(uuid.uuid4()),
                strategy_name=self.name,
                instrument=f"{setup.underlying}_{setup.ce_strike}_CE",
                direction=TradeDirection.SELL,
                quantity=setup.ce_quantity,
                price=setup.ce_premium,
                timestamp=datetime.now(timezone.utc),
                order_type="market",
                fees=self._calculate_fees(setup.ce_quantity, setup.ce_premium)
            )
            
            # Execute PE trade (sell)
            pe_trade = Trade(
                id=str(uuid.uuid4()),
                strategy_name=self.name,
                instrument=f"{setup.underlying}_{setup.pe_strike}_PE",
                direction=TradeDirection.SELL,
                quantity=setup.pe_quantity,
                price=setup.pe_premium,
                timestamp=datetime.now(timezone.utc),
                order_type="market",
                fees=self._calculate_fees(setup.pe_quantity, setup.pe_premium)
            )
            
            # Save trades
            self.trades.extend([ce_trade, pe_trade])
            
            # Update positions
            ce_position_key = f"{setup.underlying}_CE"
            pe_position_key = f"{setup.underlying}_PE"
            
            self.positions[ce_position_key].quantity += setup.ce_quantity
            self.positions[ce_position_key].average_price = setup.ce_premium
            self.positions[ce_position_key].current_price = setup.ce_premium
            
            self.positions[pe_position_key].quantity += setup.pe_quantity
            self.positions[pe_position_key].average_price = setup.pe_premium
            self.positions[pe_position_key].current_price = setup.pe_premium
            
            # Update capital
            premium_received = (setup.ce_premium * setup.ce_quantity) + (setup.pe_premium * setup.pe_quantity)
            fees_paid = ce_trade.fees + pe_trade.fees
            self.current_capital += premium_received - fees_paid
            
            # Store active setup
            self.active_setups[setup_id] = setup
            
            self.logger.info(f"Executed ratio setup for {setup.underlying}: "
                           f"CE {setup.ce_strike}@{setup.ce_premium:.2f}, "
                           f"PE {setup.pe_strike}@{setup.pe_premium:.2f}")
            
        except Exception as e:
            self.logger.error(f"Error executing ratio setup: {e}")
    
    def _calculate_fees(self, quantity: int, price: float) -> float:
        """Calculate trading fees"""
        turnover = quantity * price
        
        # Simplified fee structure
        brokerage = min(20, turnover * 0.0003)  # Max ₹20 or 0.03%
        stt = turnover * 0.0001  # 0.01% STT
        transaction_charges = turnover * 0.00003  # 0.003%
        gst = (brokerage + transaction_charges) * 0.18  # 18% GST
        
        total_fees = brokerage + stt + transaction_charges + gst
        return round(total_fees, 2)
    
    async def _monitor_positions(self):
        """Monitor active positions for management"""
        try:
            for setup_id, setup in list(self.active_setups.items()):
                # Get current premiums
                ce_current_premium = await self._get_option_premium(
                    setup.underlying, setup.ce_strike, "CE", 
                    self.market_data_cache.get(setup.underlying, {}).get('ltp', 0)
                )
                pe_current_premium = await self._get_option_premium(
                    setup.underlying, setup.pe_strike, "PE",
                    self.market_data_cache.get(setup.underlying, {}).get('ltp', 0)
                )
                
                # Calculate current P&L
                ce_pnl = (setup.ce_premium - ce_current_premium) * setup.ce_quantity
                pe_pnl = (setup.pe_premium - pe_current_premium) * setup.pe_quantity
                total_pnl = ce_pnl + pe_pnl
                
                # Check exit conditions
                should_exit = False
                exit_reason = ""
                
                # Profit target
                if total_pnl >= setup.target_premium:
                    should_exit = True
                    exit_reason = "profit_target"
                
                # Stop loss
                elif total_pnl <= -setup.stop_loss:
                    should_exit = True
                    exit_reason = "stop_loss"
                
                # Time-based exit (end of day)
                elif datetime.now().hour >= 15:  # After 3 PM
                    should_exit = True
                    exit_reason = "time_exit"
                
                if should_exit:
                    await self._close_position(setup_id, exit_reason, total_pnl)
        
        except Exception as e:
            self.logger.error(f"Error monitoring positions: {e}")
    
    async def _close_position(self, setup_id: str, reason: str, pnl: float):
        """Close a specific position"""
        try:
            if setup_id not in self.active_setups:
                return
            
            setup = self.active_setups[setup_id]
            
            # Create closing trades
            ce_close_trade = Trade(
                id=str(uuid.uuid4()),
                strategy_name=self.name,
                instrument=f"{setup.underlying}_{setup.ce_strike}_CE",
                direction=TradeDirection.BUY,  # Buy back the sold CE
                quantity=setup.ce_quantity,
                price=await self._get_option_premium(setup.underlying, setup.ce_strike, "CE", 
                                                   self.market_data_cache.get(setup.underlying, {}).get('ltp', 0)),
                timestamp=datetime.now(timezone.utc),
                pnl=pnl * 0.5,  # Split P&L between legs
                fees=self._calculate_fees(setup.ce_quantity, setup.ce_premium)
            )
            
            pe_close_trade = Trade(
                id=str(uuid.uuid4()),
                strategy_name=self.name,
                instrument=f"{setup.underlying}_{setup.pe_strike}_PE",
                direction=TradeDirection.BUY,  # Buy back the sold PE
                quantity=setup.pe_quantity,
                price=await self._get_option_premium(setup.underlying, setup.pe_strike, "PE",
                                                   self.market_data_cache.get(setup.underlying, {}).get('ltp', 0)),
                timestamp=datetime.now(timezone.utc),
                pnl=pnl * 0.5,  # Split P&L between legs
                fees=self._calculate_fees(setup.pe_quantity, setup.pe_premium)
            )
            
            # Save closing trades
            self.trades.extend([ce_close_trade, pe_close_trade])
            
            # Update positions
            ce_position_key = f"{setup.underlying}_CE"
            pe_position_key = f"{setup.underlying}_PE"
            
            self.positions[ce_position_key].quantity = 0
            self.positions[ce_position_key].realized_pnl += pnl * 0.5
            
            self.positions[pe_position_key].quantity = 0
            self.positions[pe_position_key].realized_pnl += pnl * 0.5
            
            # Update capital
            fees_paid = ce_close_trade.fees + pe_close_trade.fees
            self.current_capital += pnl - fees_paid
            
            # Remove from active setups
            del self.active_setups[setup_id]
            
            # Update metrics
            self.metrics.total_trades += 1
            if pnl > 0:
                self.metrics.winning_trades += 1
            else:
                self.metrics.losing_trades += 1
            
            self.metrics.total_pnl += pnl
            
            self.logger.info(f"Closed position for {setup.underlying} - Reason: {reason}, P&L: ₹{pnl:.2f}")
            
        except Exception as e:
            self.logger.error(f"Error closing position {setup_id}: {e}")
    
    async def _close_all_positions(self):
        """Close all active positions"""
        for setup_id in list(self.active_setups.keys()):
            await self._close_position(setup_id, "strategy_stop", 0.0)
    
    async def _check_exit_conditions(self):
        """Check global exit conditions"""
        try:
            # Check maximum drawdown
            current_drawdown = (self.peak_capital - self.current_capital) / self.peak_capital
            if current_drawdown > 0.05:  # 5% max drawdown
                self.logger.warning(f"Maximum drawdown reached: {current_drawdown:.2%}")
                await self._close_all_positions()
                self.status = StrategyStatus.PAUSED
            
            # Update peak capital
            if self.current_capital > self.peak_capital:
                self.peak_capital = self.current_capital
                
        except Exception as e:
            self.logger.error(f"Error checking exit conditions: {e}")
    
    async def _update_performance_metrics(self):
        """Update strategy performance metrics"""
        try:
            if self.metrics.total_trades > 0:
                self.metrics.win_rate = self.metrics.winning_trades / self.metrics.total_trades
                
                if self.metrics.losing_trades > 0:
                    avg_win = sum(t.pnl for t in self.trades if t.pnl > 0) / max(1, self.metrics.winning_trades)
                    avg_loss = abs(sum(t.pnl for t in self.trades if t.pnl < 0)) / max(1, self.metrics.losing_trades)
                    self.metrics.profit_factor = avg_win / avg_loss if avg_loss > 0 else 0
            
            # Calculate daily P&L
            today_trades = [t for t in self.trades if t.timestamp.date() == datetime.now().date()]
            self.daily_pnl = sum(t.pnl for t in today_trades)
            
        except Exception as e:
            self.logger.error(f"Error updating performance metrics: {e}")
    
    async def _save_final_metrics(self):
        """Save final performance metrics"""
        try:
            # Calculate final metrics
            await self._update_performance_metrics()
            
            self.metrics.max_drawdown = (self.peak_capital - min(self.current_capital, self.peak_capital)) / self.peak_capital
            
            # Log final performance
            self.logger.info(f"Final Performance - Capital: ₹{self.current_capital:.2f}, "
                           f"Total P&L: ₹{self.metrics.total_pnl:.2f}, "
                           f"Win Rate: {self.metrics.win_rate:.2%}, "
                           f"Trades: {self.metrics.total_trades}")
            
        except Exception as e:
            self.logger.error(f"Error saving final metrics: {e}")
    
    def get_status_summary(self) -> Dict[str, Any]:
        """Get current status summary"""
        return {
            "strategy_name": self.name,
            "status": self.status.value,
            "current_capital": self.current_capital,
            "daily_pnl": self.daily_pnl,
            "total_trades": self.metrics.total_trades,
            "win_rate": self.metrics.win_rate,
            "active_positions": len(self.active_setups),
            "subscribed_instruments": list(self.subscribed_instruments)
        }
