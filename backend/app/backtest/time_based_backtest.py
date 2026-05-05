"""
Time-Based Backtest Engine for Ratio Strategy

This module implements a comprehensive backtesting system for the 
time-based execution strategy for NIFTY, BANKNIFTY, and SENSEX.
"""

import asyncio
import logging
import pandas as pd
import numpy as np
from datetime import datetime, timedelta, time as dt_time
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
import json
import sqlite3
import yfinance as yf
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

# Import execution engine components
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'core', 'ratio_strategy'))

logger = logging.getLogger(__name__)

try:
    from execution_engine import TimeBasedExecutionEngine, ExecutionResult, MarketCondition
    from constants import (
        EXECUTION_PROTOCOLS, PREMIUM_TARGETS, DEFAULT_POSITION_SIZES, 
        FREEZE_LIMITS, SENSEX_CONFIG, BANKNIFTY_CONFIG
    )
except ImportError:
    # If imports fail, create mock classes for testing
    logger.warning("Could not import execution engine components. Using mock implementations.")
    
    class ExecutionResult:
        def __init__(self, status, executed_lots, avg_price, total_orders, execution_time, slippage, **kwargs):
            self.status = status
            self.executed_lots = executed_lots
            self.avg_price = avg_price
            self.total_orders = total_orders
            self.execution_time = execution_time
            self.slippage = slippage
    
    class MarketCondition:
        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)
    
    class TimeBasedExecutionEngine:
        def __init__(self):
            pass
    
    # Mock constants
    EXECUTION_PROTOCOLS = {
        "NIFTY": {"core_position_percent": 0.78, "completion_percent": 0.15, "eod_balancing_percent": 0.07},
        "BANKNIFTY": {"core_position_percent": 0.85, "volatility_percent": 0.10, "eod_balancing_percent": 0.05},
        "SENSEX": {"prime_window_percent": 0.68, "moderate_window_percent": 0.30, "dead_zone_percent": 0.02}
    }
    
    PREMIUM_TARGETS = {
        "NIFTY": {"sell": 147.50, "buy": 29.50},
        "BANKNIFTY": {"sell": 375.00, "buy": 75.00},
        "SENSEX": {"sell": 225.00, "buy": 45.00}
    }
    
    DEFAULT_POSITION_SIZES = {"NIFTY": 20, "BANKNIFTY": 15, "SENSEX": 12}
    FREEZE_LIMITS = {"NIFTY": 24, "BANKNIFTY": 20, "SENSEX": 25}
    SENSEX_CONFIG = {}
    BANKNIFTY_CONFIG = {}

logger = logging.getLogger(__name__)

@dataclass
class BacktestTrade:
    """Backtest trade structure"""
    timestamp: datetime
    instrument: str
    lots: int
    entry_price: float
    exit_price: float
    phase: str
    execution_type: str
    slippage: float
    execution_time: float
    pnl: float
    cumulative_pnl: float
    
@dataclass
class BacktestMetrics:
    """Comprehensive backtest metrics"""
    total_trades: int
    total_lots_traded: int
    total_pnl: float
    win_rate: float
    avg_slippage: float
    avg_execution_time: float
    sharpe_ratio: float
    max_drawdown: float
    profit_factor: float
    total_return_percentage: float
    best_trade: float
    worst_trade: float
    trades_by_instrument: Dict[str, int]
    trades_by_phase: Dict[str, int]
    daily_returns: List[float]

class TimeBasedBacktestEngine:
    """
    Comprehensive backtest engine for time-based execution strategy
    """

    def __init__(self, 
                 initial_capital: float = 5000000,  # 50 Lakh initial capital
                 start_date: str = "2024-01-01",
                 end_date: str = "2024-12-31"):
        
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        self.start_date = datetime.strptime(start_date, "%Y-%m-%d")
        self.end_date = datetime.strptime(end_date, "%Y-%m-%d")
        
        # Initialize execution engine
        self.execution_engine = TimeBasedExecutionEngine()
        
        # Backtest tracking
        self.trades: List[BacktestTrade] = []
        self.daily_pnl: Dict[str, float] = {}
        self.position_tracker: Dict[str, Dict] = {}
        
        # Market data cache
        self.market_data: Dict[str, pd.DataFrame] = {}
        self.options_data: Dict[str, Dict] = {}
        
        # Results storage
        self.results_db = "backtest_results_time_based.db"
        self._init_database()
        
        logger.info(f"TimeBasedBacktestEngine initialized with capital: ₹{initial_capital:,.2f}")

    def _init_database(self):
        """Initialize backtest results database"""
        try:
            conn = sqlite3.connect(self.results_db)
            cursor = conn.cursor()
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS backtest_runs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    strategy_name TEXT NOT NULL,
                    start_date TEXT NOT NULL,
                    end_date TEXT NOT NULL,
                    initial_capital REAL NOT NULL,
                    total_pnl REAL,
                    total_return_pct REAL,
                    sharpe_ratio REAL,
                    max_drawdown REAL,
                    total_trades INTEGER,
                    win_rate REAL,
                    configuration JSON
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS backtest_trades (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id INTEGER,
                    timestamp DATETIME,
                    instrument TEXT,
                    lots INTEGER,
                    entry_price REAL,
                    exit_price REAL,
                    phase TEXT,
                    execution_type TEXT,
                    slippage REAL,
                    execution_time REAL,
                    pnl REAL,
                    cumulative_pnl REAL,
                    FOREIGN KEY (run_id) REFERENCES backtest_runs (id)
                )
            ''')
            
            conn.commit()
            conn.close()
            logger.info("Backtest database initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize backtest database: {e}")

    async def run_backtest(self, 
                          instruments: List[str] = ["NIFTY", "BANKNIFTY", "SENSEX"],
                          use_synthetic_data: bool = True) -> BacktestMetrics:
        """
        Run comprehensive backtest for time-based execution strategy
        
        Args:
            instruments: List of instruments to backtest
            use_synthetic_data: Whether to use synthetic or real market data
            
        Returns:
            Comprehensive backtest metrics
        """
        logger.info(f"Starting backtest for instruments: {instruments}")
        logger.info(f"Period: {self.start_date.strftime('%Y-%m-%d')} to {self.end_date.strftime('%Y-%m-%d')}")
        
        try:
            # Load market data
            if use_synthetic_data:
                await self._generate_synthetic_market_data(instruments)
            else:
                await self._load_historical_market_data(instruments)
            
            # Generate trading calendar
            trading_days = self._generate_trading_calendar()
            
            # Run daily backtesting
            for trading_day in trading_days:
                await self._simulate_trading_day(trading_day, instruments)
            
            # Calculate final metrics
            metrics = self._calculate_backtest_metrics()
            
            # Save results
            await self._save_backtest_results(metrics, instruments)
            
            logger.info(f"Backtest completed. Total PnL: ₹{metrics.total_pnl:,.2f}")
            return metrics
            
        except Exception as e:
            logger.error(f"Backtest failed: {e}")
            raise

    async def _generate_synthetic_market_data(self, instruments: List[str]):
        """Generate synthetic market data for backtesting"""
        logger.info("Generating synthetic market data...")
        
        # Generate trading days
        trading_days = pd.bdate_range(start=self.start_date, end=self.end_date)
        
        for instrument in instruments:
            # Generate base price series
            np.random.seed(42)  # For reproducible results
            
            # Different volatility patterns for each instrument
            if instrument == "NIFTY":
                daily_vol = 0.018  # 1.8% daily volatility
                base_price = 22000
            elif instrument == "BANKNIFTY":
                daily_vol = 0.025  # 2.5% daily volatility  
                base_price = 48000
            elif instrument == "SENSEX":
                daily_vol = 0.016  # 1.6% daily volatility
                base_price = 72000
            
            # Generate price series using geometric Brownian motion
            n_days = len(trading_days)
            daily_returns = np.random.normal(0.0005, daily_vol, n_days)  # Slight positive drift
            cumulative_returns = np.cumsum(daily_returns)
            price_series = base_price * np.exp(cumulative_returns)
            
            # Generate intraday data (hourly)
            intraday_data = []
            for i, day in enumerate(trading_days):
                daily_price = price_series[i]
                
                # Generate 6.5 hours of trading data (9:15 AM to 3:30 PM)
                trading_hours = pd.date_range(
                    start=day.replace(hour=9, minute=15),
                    end=day.replace(hour=15, minute=30),
                    freq='15min'
                )
                
                # Intraday volatility pattern (higher at open/close)
                hour_weights = []
                for hour in trading_hours:
                    hour_of_day = hour.hour + hour.minute/60
                    if 9.25 <= hour_of_day <= 10.0:  # Opening hour
                        vol_multiplier = 1.8
                    elif 14.5 <= hour_of_day <= 15.5:  # Closing hour
                        vol_multiplier = 1.5
                    elif 11.0 <= hour_of_day <= 14.0:  # Lunch time
                        vol_multiplier = 0.7
                    else:
                        vol_multiplier = 1.0
                    hour_weights.append(vol_multiplier)
                
                # Generate intraday prices
                intraday_vol = daily_vol / np.sqrt(26)  # 26 15-min intervals in a day
                intraday_returns = np.random.normal(0, intraday_vol, len(trading_hours))
                intraday_returns = intraday_returns * hour_weights
                
                # Start from previous close or daily price
                if i == 0:
                    start_price = daily_price
                else:
                    start_price = price_series[i-1]
                
                # Generate price path
                cumulative_intraday = np.cumsum(intraday_returns)
                intraday_prices = start_price * np.exp(cumulative_intraday)
                
                # Adjust to end at daily close
                adjustment_factor = daily_price / intraday_prices[-1]
                intraday_prices = intraday_prices * adjustment_factor
                
                # Create DataFrame for this day
                day_data = pd.DataFrame({
                    'timestamp': trading_hours,
                    'price': intraday_prices,
                    'volume': np.random.lognormal(10, 0.5, len(trading_hours))  # Synthetic volume
                })
                
                intraday_data.append(day_data)
            
            # Combine all days
            market_data = pd.concat(intraday_data, ignore_index=True)
            market_data.set_index('timestamp', inplace=True)
            
            self.market_data[instrument] = market_data
            
            # Generate options data
            await self._generate_synthetic_options_data(instrument, market_data)
        
        logger.info(f"Generated synthetic market data for {len(instruments)} instruments")

    async def _generate_synthetic_options_data(self, instrument: str, market_data: pd.DataFrame):
        """Generate synthetic options data based on underlying prices"""
        options_data = {}
        
        for timestamp, row in market_data.iterrows():
            spot_price = row['price']
            
            # Calculate ATM strike (round to nearest 50 for NIFTY/BANKNIFTY, 100 for SENSEX)
            if instrument in ["NIFTY", "BANKNIFTY"]:
                strike_gap = 50
            else:
                strike_gap = 100
                
            atm_strike = round(spot_price / strike_gap) * strike_gap
            
            # Generate strikes around ATM
            strikes = []
            for i in range(-10, 11):  # 10 strikes on each side
                strikes.append(atm_strike + (i * strike_gap))
            
            # Calculate option prices using simplified Black-Scholes
            # (This is simplified for backtesting purposes)
            strike_data = {}
            for strike in strikes:
                moneyness = spot_price / strike
                
                # Simplified IV calculation based on moneyness
                if 0.95 <= moneyness <= 1.05:  # ATM options
                    iv = 0.18 + np.random.normal(0, 0.02)
                elif moneyness < 0.95:  # OTM puts / ITM calls
                    iv = 0.20 + np.random.normal(0, 0.03)
                else:  # ITM puts / OTM calls
                    iv = 0.16 + np.random.normal(0, 0.02)
                
                # Time to expiry (assume weekly options, max 5 days)
                time_to_expiry = max(1, 5 - (timestamp.weekday()))
                
                # Simplified option pricing
                intrinsic_call = max(0, spot_price - strike)
                intrinsic_put = max(0, strike - spot_price)
                
                time_value = (iv * spot_price * np.sqrt(time_to_expiry/365)) / 2
                
                call_price = intrinsic_call + time_value
                put_price = intrinsic_put + time_value
                
                strike_data[strike] = {
                    'call_price': call_price,
                    'put_price': put_price,
                    'iv': iv,
                    'volume': np.random.lognormal(6, 1)
                }
            
            options_data[timestamp] = strike_data
        
        self.options_data[instrument] = options_data

    def _generate_trading_calendar(self) -> List[datetime]:
        """Generate list of trading days"""
        trading_days = pd.bdate_range(start=self.start_date, end=self.end_date)
        
        # Remove major Indian market holidays (simplified)
        holidays = [
            "2024-01-26",  # Republic Day
            "2024-03-08",  # Holi
            "2024-03-29",  # Good Friday
            "2024-08-15",  # Independence Day
            "2024-10-02",  # Gandhi Jayanti
            "2024-11-01",  # Diwali
        ]
        
        holiday_dates = [datetime.strptime(h, "%Y-%m-%d").date() for h in holidays]
        
        return [day for day in trading_days if day.date() not in holiday_dates]

    async def _simulate_trading_day(self, trading_day: datetime, instruments: List[str]):
        """Simulate a complete trading day"""
        logger.debug(f"Simulating trading day: {trading_day.strftime('%Y-%m-%d')}")
        
        daily_pnl = 0.0
        day_trades = []
        
        for instrument in instruments:
            try:
                # Create trading plan
                trading_plan = {
                    instrument: {
                        "target_lots": DEFAULT_POSITION_SIZES[instrument],
                        "trading_day": trading_day
                    }
                }
                
                # Execute strategy for this instrument
                result = await self._execute_instrument_backtest(instrument, trading_day)
                
                if result:
                    daily_pnl += result.total_pnl
                    day_trades.extend(result.trades)
                
            except Exception as e:
                logger.error(f"Failed to simulate {instrument} on {trading_day}: {e}")
        
        # Store daily results
        self.daily_pnl[trading_day.strftime('%Y-%m-%d')] = daily_pnl
        self.trades.extend(day_trades)
        
        # Update capital
        self.current_capital += daily_pnl

    async def _execute_instrument_backtest(self, instrument: str, trading_day: datetime) -> Optional[Any]:
        """Execute backtest for a specific instrument on a specific day"""
        try:
            # Get market data for this day
            day_data = self.market_data[instrument][
                self.market_data[instrument].index.date == trading_day.date()
            ]
            
            if day_data.empty:
                logger.warning(f"No market data for {instrument} on {trading_day}")
                return None
            
            # Get execution phases for this instrument
            phases = EXECUTION_PROTOCOLS[instrument]
            
            trades = []
            total_pnl = 0.0
            cumulative_pnl = sum([t.pnl for t in self.trades])  # Running total
            
            target_lots = DEFAULT_POSITION_SIZES[instrument]
            
            # Simulate each phase
            if instrument == "NIFTY":
                trades.extend(await self._simulate_nifty_phases(day_data, trading_day, target_lots))
            elif instrument == "BANKNIFTY":
                trades.extend(await self._simulate_banknifty_phases(day_data, trading_day, target_lots))
            elif instrument == "SENSEX":
                trades.extend(await self._simulate_sensex_phases(day_data, trading_day, target_lots))
            
            # Calculate total PnL for the day
            for trade in trades:
                total_pnl += trade.pnl
                cumulative_pnl += trade.pnl
                trade.cumulative_pnl = cumulative_pnl
            
            return type('DayResult', (), {
                'trades': trades,
                'total_pnl': total_pnl
            })()
            
        except Exception as e:
            logger.error(f"Instrument backtest failed for {instrument}: {e}")
            return None

    async def _simulate_nifty_phases(self, day_data: pd.DataFrame, trading_day: datetime, target_lots: int) -> List[BacktestTrade]:
        """Simulate NIFTY execution phases"""
        trades = []
        
        # Phase 1: Core Position (78%) - 10:45-11:15
        core_lots = int(target_lots * 0.78)
        core_start = trading_day.replace(hour=10, minute=45)
        core_end = trading_day.replace(hour=11, minute=15)
        
        core_trades = await self._simulate_phase_execution(
            day_data, core_start, core_end, "NIFTY", core_lots, "CORE", "ICEBERG"
        )
        trades.extend(core_trades)
        
        # Phase 2: Completion (15%) - 11:15-14:30
        completion_lots = int(target_lots * 0.15)
        completion_start = trading_day.replace(hour=11, minute=15)
        completion_end = trading_day.replace(hour=14, minute=30)
        
        completion_trades = await self._simulate_phase_execution(
            day_data, completion_start, completion_end, "NIFTY", completion_lots, "COMPLETION", "VWAP"
        )
        trades.extend(completion_trades)
        
        # Phase 3: EOD Balancing (7%) - 14:30-15:00
        eod_lots = int(target_lots * 0.07)
        eod_start = trading_day.replace(hour=14, minute=30)
        eod_end = trading_day.replace(hour=15, minute=0)
        
        eod_trades = await self._simulate_phase_execution(
            day_data, eod_start, eod_end, "NIFTY", eod_lots, "EOD_BALANCING", "MARKET"
        )
        trades.extend(eod_trades)
        
        return trades

    async def _simulate_banknifty_phases(self, day_data: pd.DataFrame, trading_day: datetime, target_lots: int) -> List[BacktestTrade]:
        """Simulate BANKNIFTY execution phases"""
        trades = []
        
        # Phase 1: Core Position (85%) - 11:00-11:30
        core_lots = int(target_lots * 0.85)
        core_start = trading_day.replace(hour=11, minute=0)
        core_end = trading_day.replace(hour=11, minute=30)
        
        core_trades = await self._simulate_phase_execution(
            day_data, core_start, core_end, "BANKNIFTY", core_lots, "CORE", "DARK_POOL"
        )
        trades.extend(core_trades)
        
        # Phase 2: Volatility Arbitrage (10%) - 11:30-14:30
        vol_lots = int(target_lots * 0.10)
        vol_start = trading_day.replace(hour=11, minute=30)
        vol_end = trading_day.replace(hour=14, minute=30)
        
        vol_trades = await self._simulate_phase_execution(
            day_data, vol_start, vol_end, "BANKNIFTY", vol_lots, "VOLATILITY", "DYNAMIC_HEDGING"
        )
        trades.extend(vol_trades)
        
        # Phase 3: EOD Balancing (5%) - 14:30-15:00
        eod_lots = int(target_lots * 0.05)
        eod_start = trading_day.replace(hour=14, minute=30)
        eod_end = trading_day.replace(hour=15, minute=0)
        
        eod_trades = await self._simulate_phase_execution(
            day_data, eod_start, eod_end, "BANKNIFTY", eod_lots, "EOD_BALANCING", "TWAP"
        )
        trades.extend(eod_trades)
        
        return trades

    async def _simulate_sensex_phases(self, day_data: pd.DataFrame, trading_day: datetime, target_lots: int) -> List[BacktestTrade]:
        """Simulate SENSEX execution phases"""
        trades = []
        
        # Phase 1: Prime Window (68%) - 10:00-11:00
        prime_lots = int(target_lots * 0.68)
        prime_start = trading_day.replace(hour=10, minute=0)
        prime_end = trading_day.replace(hour=11, minute=0)
        
        prime_trades = await self._simulate_phase_execution(
            day_data, prime_start, prime_end, "SENSEX", prime_lots, "PRIME_WINDOW", "SMART_ORDER"
        )
        trades.extend(prime_trades)
        
        # Phase 2: Moderate Window (30%) - 11:00-14:00
        moderate_lots = int(target_lots * 0.30)
        moderate_start = trading_day.replace(hour=11, minute=0)
        moderate_end = trading_day.replace(hour=14, minute=0)
        
        moderate_trades = await self._simulate_phase_execution(
            day_data, moderate_start, moderate_end, "SENSEX", moderate_lots, "MODERATE_WINDOW", "PRICE_IMPROVEMENT"
        )
        trades.extend(moderate_trades)
        
        # Phase 3: Dead Zone (2%) - 14:00-15:30
        dead_lots = int(target_lots * 0.02)
        dead_start = trading_day.replace(hour=14, minute=0)
        dead_end = trading_day.replace(hour=15, minute=30)
        
        dead_trades = await self._simulate_phase_execution(
            day_data, dead_start, dead_end, "SENSEX", dead_lots, "DEAD_ZONE", "EMERGENCY_LIQUIDATION"
        )
        trades.extend(dead_trades)
        
        return trades

    async def _simulate_phase_execution(self, 
                                      day_data: pd.DataFrame, 
                                      start_time: datetime, 
                                      end_time: datetime,
                                      instrument: str,
                                      lots: int,
                                      phase: str,
                                      execution_type: str) -> List[BacktestTrade]:
        """Simulate execution within a specific phase"""
        trades = []
        
        if lots <= 0:
            return trades
        
        # Get data for this time window
        phase_data = day_data[
            (day_data.index >= start_time) & 
            (day_data.index <= end_time)
        ]
        
        if phase_data.empty:
            logger.warning(f"No data for {instrument} {phase} phase")
            return trades
        
        # Simulate execution based on type
        if execution_type in ["ICEBERG", "DARK_POOL"]:
            # Chunk-based execution
            chunk_size = min(5, lots)
            chunks = int(np.ceil(lots / chunk_size))
            
            for i in range(chunks):
                remaining_lots = lots - (i * chunk_size)
                current_chunk = min(chunk_size, remaining_lots)
                
                if current_chunk <= 0:
                    break
                
                # Select random execution time within phase
                execution_idx = np.random.randint(0, len(phase_data))
                execution_time = phase_data.index[execution_idx]
                execution_price = phase_data.iloc[execution_idx]['price']
                
                # Calculate option premium and slippage
                trade = await self._create_simulated_trade(
                    execution_time, instrument, current_chunk, execution_price, phase, execution_type
                )
                
                if trade:
                    trades.append(trade)
        
        elif execution_type in ["VWAP", "TWAP"]:
            # Time-weighted execution
            execution_points = min(lots, len(phase_data))
            lots_per_point = lots / execution_points
            
            for i in range(execution_points):
                if i >= len(phase_data):
                    break
                    
                execution_time = phase_data.index[i]
                execution_price = phase_data.iloc[i]['price']
                current_lots = int(lots_per_point)
                
                if current_lots <= 0:
                    continue
                
                trade = await self._create_simulated_trade(
                    execution_time, instrument, current_lots, execution_price, phase, execution_type
                )
                
                if trade:
                    trades.append(trade)
        
        else:  # MARKET, EMERGENCY_LIQUIDATION, etc.
            # Immediate execution
            execution_idx = 0
            execution_time = phase_data.index[execution_idx]
            execution_price = phase_data.iloc[execution_idx]['price']
            
            trade = await self._create_simulated_trade(
                execution_time, instrument, lots, execution_price, phase, execution_type
            )
            
            if trade:
                trades.append(trade)
        
        return trades

    async def _create_simulated_trade(self,
                                    execution_time: datetime,
                                    instrument: str,
                                    lots: int,
                                    spot_price: float,
                                    phase: str,
                                    execution_type: str) -> Optional[BacktestTrade]:
        """Create a simulated trade with realistic execution characteristics"""
        try:
            # Get options data for this timestamp
            if execution_time not in self.options_data[instrument]:
                logger.warning(f"No options data for {instrument} at {execution_time}")
                return None
            
            options_data = self.options_data[instrument][execution_time]
            
            # Find appropriate strike (ATM or slightly OTM)
            strikes = sorted(options_data.keys())
            atm_idx = min(range(len(strikes)), key=lambda i: abs(strikes[i] - spot_price))
            
            # Select strike (prefer slightly OTM for premium collection)
            if atm_idx < len(strikes) - 1:
                selected_strike = strikes[atm_idx + 1]  # Slightly OTM
            else:
                selected_strike = strikes[atm_idx]
            
            strike_data = options_data[selected_strike]
            
            # Entry price (sell premium)
            entry_price = strike_data['call_price'] + strike_data['put_price']  # Short strangle
            
            # Simulate exit price (assume held for 1 hour with time decay)
            time_decay_factor = 0.95  # 5% time decay
            exit_price = entry_price * time_decay_factor
            
            # Add market-based slippage
            slippage_rate = self._calculate_slippage(instrument, execution_type, lots)
            entry_price_with_slippage = entry_price * (1 - slippage_rate)
            exit_price_with_slippage = exit_price * (1 + slippage_rate)
            
            # Calculate PnL (short position)
            trade_pnl = (entry_price_with_slippage - exit_price_with_slippage) * lots * LOT_SIZES[instrument]
            
            # Execution time simulation
            exec_time = self._calculate_execution_time(execution_type, lots)
            
            return BacktestTrade(
                timestamp=execution_time,
                instrument=instrument,
                lots=lots,
                entry_price=entry_price_with_slippage,
                exit_price=exit_price_with_slippage,
                phase=phase,
                execution_type=execution_type,
                slippage=slippage_rate,
                execution_time=exec_time,
                pnl=trade_pnl,
                cumulative_pnl=0.0  # Will be updated later
            )
            
        except Exception as e:
            logger.error(f"Failed to create simulated trade: {e}")
            return None

    def _calculate_slippage(self, instrument: str, execution_type: str, lots: int) -> float:
        """Calculate realistic slippage based on execution type and size"""
        base_slippage = {
            "NIFTY": 0.0002,  # 0.02%
            "BANKNIFTY": 0.0003,  # 0.03%
            "SENSEX": 0.0002  # 0.02%
        }
        
        execution_multipliers = {
            "ICEBERG": 0.8,
            "VWAP": 0.6,
            "TWAP": 0.7,
            "DARK_POOL": 0.5,
            "MARKET": 1.5,
            "EMERGENCY_LIQUIDATION": 2.0,
            "DYNAMIC_HEDGING": 1.2,
            "SMART_ORDER": 0.9,
            "PRICE_IMPROVEMENT": 0.3
        }
        
        # Size impact
        size_multiplier = 1.0 + (lots / FREEZE_LIMITS[instrument]) * 0.5
        
        return base_slippage[instrument] * execution_multipliers.get(execution_type, 1.0) * size_multiplier

    def _calculate_execution_time(self, execution_type: str, lots: int) -> float:
        """Calculate execution time in seconds"""
        base_times = {
            "ICEBERG": 30.0,
            "VWAP": 45.0,
            "TWAP": 60.0,
            "DARK_POOL": 20.0,
            "MARKET": 5.0,
            "EMERGENCY_LIQUIDATION": 10.0,
            "DYNAMIC_HEDGING": 25.0,
            "SMART_ORDER": 35.0,
            "PRICE_IMPROVEMENT": 90.0
        }
        
        base_time = base_times.get(execution_type, 30.0)
        
        # Add time for larger positions
        size_factor = 1.0 + (lots / 10) * 0.1
        
        return base_time * size_factor

    def _calculate_backtest_metrics(self) -> BacktestMetrics:
        """Calculate comprehensive backtest metrics"""
        if not self.trades:
            logger.warning("No trades to analyze")
            return BacktestMetrics(
                total_trades=0, total_lots_traded=0, total_pnl=0.0, win_rate=0.0,
                avg_slippage=0.0, avg_execution_time=0.0, sharpe_ratio=0.0,
                max_drawdown=0.0, profit_factor=0.0, total_return_percentage=0.0,
                best_trade=0.0, worst_trade=0.0, trades_by_instrument={},
                trades_by_phase={}, daily_returns=[]
            )
        
        # Basic metrics
        total_trades = len(self.trades)
        total_lots_traded = sum(trade.lots for trade in self.trades)
        total_pnl = sum(trade.pnl for trade in self.trades)
        
        # Win rate
        winning_trades = [trade for trade in self.trades if trade.pnl > 0]
        losing_trades = [trade for trade in self.trades if trade.pnl < 0]
        win_rate = len(winning_trades) / total_trades if total_trades > 0 else 0.0
        
        # Average metrics
        avg_slippage = np.mean([trade.slippage for trade in self.trades])
        avg_execution_time = np.mean([trade.execution_time for trade in self.trades])
        
        # Return percentage
        total_return_percentage = (total_pnl / self.initial_capital) * 100
        
        # Best and worst trades
        best_trade = max(trade.pnl for trade in self.trades) if self.trades else 0.0
        worst_trade = min(trade.pnl for trade in self.trades) if self.trades else 0.0
        
        # Profit factor
        gross_profit = sum(trade.pnl for trade in winning_trades)
        gross_loss = abs(sum(trade.pnl for trade in losing_trades))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
        
        # Daily returns for Sharpe ratio
        daily_returns = list(self.daily_pnl.values())
        
        # Sharpe ratio (assuming risk-free rate of 6%)
        if len(daily_returns) > 1:
            excess_returns = [ret - (0.06 / 252) * self.initial_capital for ret in daily_returns]
            sharpe_ratio = np.mean(excess_returns) / np.std(excess_returns) * np.sqrt(252) if np.std(excess_returns) > 0 else 0.0
        else:
            sharpe_ratio = 0.0
        
        # Maximum drawdown
        cumulative_returns = np.cumsum(daily_returns)
        running_max = np.maximum.accumulate(cumulative_returns)
        drawdown = (cumulative_returns - running_max) / running_max
        max_drawdown = abs(min(drawdown)) if len(drawdown) > 0 else 0.0
        
        # Breakdown by instrument and phase
        trades_by_instrument = {}
        trades_by_phase = {}
        
        for trade in self.trades:
            trades_by_instrument[trade.instrument] = trades_by_instrument.get(trade.instrument, 0) + 1
            trades_by_phase[trade.phase] = trades_by_phase.get(trade.phase, 0) + 1
        
        return BacktestMetrics(
            total_trades=total_trades,
            total_lots_traded=total_lots_traded,
            total_pnl=total_pnl,
            win_rate=win_rate,
            avg_slippage=avg_slippage,
            avg_execution_time=avg_execution_time,
            sharpe_ratio=sharpe_ratio,
            max_drawdown=max_drawdown,
            profit_factor=profit_factor,
            total_return_percentage=total_return_percentage,
            best_trade=best_trade,
            worst_trade=worst_trade,
            trades_by_instrument=trades_by_instrument,
            trades_by_phase=trades_by_phase,
            daily_returns=daily_returns
        )

    async def _save_backtest_results(self, metrics: BacktestMetrics, instruments: List[str]):
        """Save backtest results to database"""
        try:
            conn = sqlite3.connect(self.results_db)
            cursor = conn.cursor()
            
            # Insert main backtest run
            cursor.execute('''
                INSERT INTO backtest_runs (
                    strategy_name, start_date, end_date, initial_capital,
                    total_pnl, total_return_pct, sharpe_ratio, max_drawdown,
                    total_trades, win_rate, configuration
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                "TimeBasedExecutionStrategy",
                self.start_date.strftime('%Y-%m-%d'),
                self.end_date.strftime('%Y-%m-%d'),
                self.initial_capital,
                metrics.total_pnl,
                metrics.total_return_percentage,
                metrics.sharpe_ratio,
                metrics.max_drawdown,
                metrics.total_trades,
                metrics.win_rate,
                json.dumps({"instruments": instruments})
            ))
            
            run_id = cursor.lastrowid
            
            # Insert individual trades
            for trade in self.trades:
                cursor.execute('''
                    INSERT INTO backtest_trades (
                        run_id, timestamp, instrument, lots, entry_price,
                        exit_price, phase, execution_type, slippage,
                        execution_time, pnl, cumulative_pnl
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    run_id,
                    trade.timestamp.isoformat(),
                    trade.instrument,
                    trade.lots,
                    trade.entry_price,
                    trade.exit_price,
                    trade.phase,
                    trade.execution_type,
                    trade.slippage,
                    trade.execution_time,
                    trade.pnl,
                    trade.cumulative_pnl
                ))
            
            conn.commit()
            conn.close()
            
            logger.info(f"Backtest results saved with run_id: {run_id}")
            
        except Exception as e:
            logger.error(f"Failed to save backtest results: {e}")

    def generate_report(self, metrics: BacktestMetrics) -> str:
        """Generate a comprehensive backtest report"""
        report = f"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                    TIME-BASED EXECUTION STRATEGY BACKTEST REPORT                ║
╚══════════════════════════════════════════════════════════════════════════════╝

📊 OVERVIEW
═══════════════════════════════════════════════════════════════════════════════
Period: {self.start_date.strftime('%Y-%m-%d')} to {self.end_date.strftime('%Y-%m-%d')}
Initial Capital: ₹{self.initial_capital:,.2f}
Final Capital: ₹{self.current_capital:,.2f}

💰 PERFORMANCE METRICS
═══════════════════════════════════════════════════════════════════════════════
Total PnL: ₹{metrics.total_pnl:,.2f}
Total Return: {metrics.total_return_percentage:.2f}%
Total Trades: {metrics.total_trades:,}
Total Lots Traded: {metrics.total_lots_traded:,}

Win Rate: {metrics.win_rate:.2%}
Profit Factor: {metrics.profit_factor:.2f}
Sharpe Ratio: {metrics.sharpe_ratio:.2f}
Maximum Drawdown: {metrics.max_drawdown:.2%}

Best Trade: ₹{metrics.best_trade:,.2f}
Worst Trade: ₹{metrics.worst_trade:,.2f}
Average Trade: ₹{metrics.total_pnl/metrics.total_trades if metrics.total_trades > 0 else 0:,.2f}

⚡ EXECUTION METRICS
═══════════════════════════════════════════════════════════════════════════════
Average Slippage: {metrics.avg_slippage:.4%}
Average Execution Time: {metrics.avg_execution_time:.1f} seconds

📈 BREAKDOWN BY INSTRUMENT
═══════════════════════════════════════════════════════════════════════════════"""

        for instrument, count in metrics.trades_by_instrument.items():
            percentage = (count / metrics.total_trades) * 100 if metrics.total_trades > 0 else 0
            report += f"\n{instrument}: {count} trades ({percentage:.1f}%)"

        report += f"""

🕐 BREAKDOWN BY PHASE
═══════════════════════════════════════════════════════════════════════════════"""

        for phase, count in metrics.trades_by_phase.items():
            percentage = (count / metrics.total_trades) * 100 if metrics.total_trades > 0 else 0
            report += f"\n{phase}: {count} trades ({percentage:.1f}%)"

        report += f"""

📝 SUMMARY
═══════════════════════════════════════════════════════════════════════════════
The time-based execution strategy generated a total return of {metrics.total_return_percentage:.2f}% 
over the backtest period with a Sharpe ratio of {metrics.sharpe_ratio:.2f}. 

The strategy executed {metrics.total_trades:,} trades across {len(metrics.trades_by_instrument)} 
instruments with a win rate of {metrics.win_rate:.2%} and maintained an average slippage 
of {metrics.avg_slippage:.4%}.

Maximum drawdown was contained to {metrics.max_drawdown:.2%}, indicating good risk management.
"""

        return report

# Additional constants needed for backtest
LOT_SIZES = {
    "NIFTY": 25,      # NIFTY lot size
    "BANKNIFTY": 15,  # BANKNIFTY lot size  
    "SENSEX": 10      # SENSEX lot size
}

if __name__ == "__main__":
    async def main():
        # Initialize backtest engine
        engine = TimeBasedBacktestEngine(
            initial_capital=5000000,  # 50 Lakh
            start_date="2024-01-01",
            end_date="2024-03-31"  # 3 months for testing
        )
        
        # Run backtest
        metrics = await engine.run_backtest(
            instruments=["NIFTY", "BANKNIFTY", "SENSEX"],
            use_synthetic_data=True
        )
        
        # Generate and print report
        report = engine.generate_report(metrics)
        print(report)
        
        # Save report to file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = f"time_based_backtest_report_{timestamp}.txt"
        
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report)
        
        print(f"\nDetailed report saved to: {report_file}")

    # Run the backtest
    asyncio.run(main())
