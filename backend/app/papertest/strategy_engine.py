"""
Common Strategy Execution Engine for Paper Trading

This module provides a unified interface for executing different trading strategies
in a paper trading environment with real market data.
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List, Union
from enum import Enum
import json
from dataclasses import dataclass, asdict
import sqlite3
from pathlib import Path

logger = logging.getLogger(__name__)

class StrategyStatus(Enum):
    """Strategy execution status"""
    STOPPED = "stopped"
    RUNNING = "running"
    PAUSED = "paused"
    ERROR = "error"

class TradeDirection(Enum):
    """Trade direction"""
    BUY = "buy"
    SELL = "sell"

@dataclass
class Trade:
    """Trade data structure"""
    id: str
    strategy_name: str
    instrument: str
    direction: TradeDirection
    quantity: int
    price: float
    timestamp: datetime
    order_type: str = "market"
    status: str = "executed"
    pnl: float = 0.0
    fees: float = 0.0

@dataclass
class Position:
    """Position data structure"""
    instrument: str
    quantity: int
    average_price: float
    current_price: float
    unrealized_pnl: float
    realized_pnl: float
    timestamp: datetime

@dataclass
class StrategyMetrics:
    """Strategy performance metrics"""
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    total_pnl: float = 0.0
    win_rate: float = 0.0
    profit_factor: float = 0.0
    max_drawdown: float = 0.0
    sharpe_ratio: float = 0.0
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None

class BaseStrategy(ABC):
    """Base class for all trading strategies"""
    
    def __init__(self, name: str, config: Dict[str, Any]):
        self.name = name
        self.config = config
        self.status = StrategyStatus.STOPPED
        self.trades: List[Trade] = []
        self.positions: Dict[str, Position] = {}
        self.metrics = StrategyMetrics()
        self.logger = logging.getLogger(f"strategy.{name}")
        
    @abstractmethod
    async def initialize(self) -> bool:
        """Initialize the strategy"""
        pass
    
    @abstractmethod
    async def on_market_data(self, data: Dict[str, Any]) -> None:
        """Handle incoming market data"""
        pass
    
    @abstractmethod
    async def on_tick(self) -> None:
        """Called on each time tick"""
        pass
    
    @abstractmethod
    async def cleanup(self) -> None:
        """Cleanup strategy resources"""
        pass
    
    async def start(self) -> bool:
        """Start the strategy"""
        try:
            if await self.initialize():
                self.status = StrategyStatus.RUNNING
                self.metrics.start_time = datetime.now(timezone.utc)
                self.logger.info(f"Strategy {self.name} started successfully")
                return True
            return False
        except Exception as e:
            self.logger.error(f"Failed to start strategy {self.name}: {e}")
            self.status = StrategyStatus.ERROR
            return False
    
    async def stop(self) -> bool:
        """Stop the strategy"""
        try:
            await self.cleanup()
            self.status = StrategyStatus.STOPPED
            self.metrics.end_time = datetime.now(timezone.utc)
            self.logger.info(f"Strategy {self.name} stopped successfully")
            return True
        except Exception as e:
            self.logger.error(f"Failed to stop strategy {self.name}: {e}")
            return False
    
    async def pause(self) -> bool:
        """Pause the strategy"""
        if self.status == StrategyStatus.RUNNING:
            self.status = StrategyStatus.PAUSED
            self.logger.info(f"Strategy {self.name} paused")
            return True
        return False
    
    async def resume(self) -> bool:
        """Resume the strategy"""
        if self.status == StrategyStatus.PAUSED:
            self.status = StrategyStatus.RUNNING
            self.logger.info(f"Strategy {self.name} resumed")
            return True
        return False

class PaperTradingEngine:
    """
    Paper Trading Engine for executing strategies with real market data
    """
    
    def __init__(self, db_path: str = "papertest/paper_trading.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        self.strategies: Dict[str, BaseStrategy] = {}
        self.running_tasks: Dict[str, asyncio.Task] = {}
        self.market_data_feed = None
        self.logger = logging.getLogger(__name__)
        
        # Initialize database
        self._init_database()
    
    def _init_database(self):
        """Initialize SQLite database for paper trading"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Create trades table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS trades (
                        id TEXT PRIMARY KEY,
                        strategy_name TEXT NOT NULL,
                        instrument TEXT NOT NULL,
                        direction TEXT NOT NULL,
                        quantity INTEGER NOT NULL,
                        price REAL NOT NULL,
                        timestamp TEXT NOT NULL,
                        order_type TEXT DEFAULT 'market',
                        status TEXT DEFAULT 'executed',
                        pnl REAL DEFAULT 0.0,
                        fees REAL DEFAULT 0.0
                    )
                """)
                
                # Create positions table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS positions (
                        strategy_name TEXT NOT NULL,
                        instrument TEXT NOT NULL,
                        quantity INTEGER NOT NULL,
                        average_price REAL NOT NULL,
                        current_price REAL NOT NULL,
                        unrealized_pnl REAL NOT NULL,
                        realized_pnl REAL NOT NULL,
                        timestamp TEXT NOT NULL,
                        PRIMARY KEY (strategy_name, instrument)
                    )
                """)
                
                # Create strategy_metrics table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS strategy_metrics (
                        strategy_name TEXT PRIMARY KEY,
                        total_trades INTEGER DEFAULT 0,
                        winning_trades INTEGER DEFAULT 0,
                        losing_trades INTEGER DEFAULT 0,
                        total_pnl REAL DEFAULT 0.0,
                        win_rate REAL DEFAULT 0.0,
                        profit_factor REAL DEFAULT 0.0,
                        max_drawdown REAL DEFAULT 0.0,
                        sharpe_ratio REAL DEFAULT 0.0,
                        start_time TEXT,
                        end_time TEXT
                    )
                """)
                
                conn.commit()
                self.logger.info("Database initialized successfully")
        
        except Exception as e:
            self.logger.error(f"Failed to initialize database: {e}")
            raise
    
    def register_strategy(self, strategy: BaseStrategy) -> bool:
        """Register a strategy with the engine"""
        try:
            if strategy.name in self.strategies:
                self.logger.warning(f"Strategy {strategy.name} already registered")
                return False
            
            self.strategies[strategy.name] = strategy
            self.logger.info(f"Strategy {strategy.name} registered successfully")
            return True
        
        except Exception as e:
            self.logger.error(f"Failed to register strategy {strategy.name}: {e}")
            return False
    
    def unregister_strategy(self, strategy_name: str) -> bool:
        """Unregister a strategy from the engine"""
        try:
            if strategy_name not in self.strategies:
                self.logger.warning(f"Strategy {strategy_name} not found")
                return False
            
            # Stop strategy if running
            if strategy_name in self.running_tasks:
                asyncio.create_task(self.stop_strategy(strategy_name))
            
            del self.strategies[strategy_name]
            self.logger.info(f"Strategy {strategy_name} unregistered successfully")
            return True
        
        except Exception as e:
            self.logger.error(f"Failed to unregister strategy {strategy_name}: {e}")
            return False
    
    async def start_strategy(self, strategy_name: str) -> bool:
        """Start a specific strategy"""
        try:
            if strategy_name not in self.strategies:
                self.logger.error(f"Strategy {strategy_name} not found")
                return False
            
            if strategy_name in self.running_tasks:
                self.logger.warning(f"Strategy {strategy_name} is already running")
                return False
            
            strategy = self.strategies[strategy_name]
            
            if await strategy.start():
                # Start strategy execution task
                task = asyncio.create_task(self._run_strategy(strategy))
                self.running_tasks[strategy_name] = task
                self.logger.info(f"Strategy {strategy_name} started successfully")
                return True
            
            return False
        
        except Exception as e:
            self.logger.error(f"Failed to start strategy {strategy_name}: {e}")
            return False
    
    async def stop_strategy(self, strategy_name: str) -> bool:
        """Stop a specific strategy"""
        try:
            if strategy_name not in self.strategies:
                self.logger.error(f"Strategy {strategy_name} not found")
                return False
            
            strategy = self.strategies[strategy_name]
            
            # Cancel running task
            if strategy_name in self.running_tasks:
                self.running_tasks[strategy_name].cancel()
                del self.running_tasks[strategy_name]
            
            if await strategy.stop():
                self.logger.info(f"Strategy {strategy_name} stopped successfully")
                return True
            
            return False
        
        except Exception as e:
            self.logger.error(f"Failed to stop strategy {strategy_name}: {e}")
            return False
    
    async def pause_strategy(self, strategy_name: str) -> bool:
        """Pause a specific strategy"""
        if strategy_name not in self.strategies:
            return False
        
        return await self.strategies[strategy_name].pause()
    
    async def resume_strategy(self, strategy_name: str) -> bool:
        """Resume a specific strategy"""
        if strategy_name not in self.strategies:
            return False
        
        return await self.strategies[strategy_name].resume()
    
    async def _run_strategy(self, strategy: BaseStrategy):
        """Run strategy in a loop"""
        try:
            while strategy.status == StrategyStatus.RUNNING:
                # Simulate market data tick
                if self.market_data_feed:
                    market_data = await self.market_data_feed.get_data()
                    await strategy.on_market_data(market_data)
                
                # Call strategy tick
                await strategy.on_tick()
                
                # Sleep for a short interval
                await asyncio.sleep(1)  # 1 second interval
        
        except asyncio.CancelledError:
            self.logger.info(f"Strategy {strategy.name} task cancelled")
        except Exception as e:
            self.logger.error(f"Error running strategy {strategy.name}: {e}")
            strategy.status = StrategyStatus.ERROR
    
    def get_strategy_status(self, strategy_name: str) -> Optional[StrategyStatus]:
        """Get status of a specific strategy"""
        if strategy_name in self.strategies:
            return self.strategies[strategy_name].status
        return None
    
    def get_all_strategies(self) -> Dict[str, Dict[str, Any]]:
        """Get information about all registered strategies"""
        result = {}
        for name, strategy in self.strategies.items():
            result[name] = {
                "name": name,
                "status": strategy.status.value,
                "metrics": asdict(strategy.metrics),
                "config": strategy.config
            }
        return result
    
    def save_trade(self, trade: Trade):
        """Save trade to database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO trades VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    trade.id, trade.strategy_name, trade.instrument,
                    trade.direction.value, trade.quantity, trade.price,
                    trade.timestamp.isoformat(), trade.order_type,
                    trade.status, trade.pnl, trade.fees
                ))
                conn.commit()
        except Exception as e:
            self.logger.error(f"Failed to save trade: {e}")
    
    def save_position(self, strategy_name: str, position: Position):
        """Save position to database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO positions VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    strategy_name, position.instrument, position.quantity,
                    position.average_price, position.current_price,
                    position.unrealized_pnl, position.realized_pnl,
                    position.timestamp.isoformat()
                ))
                conn.commit()
        except Exception as e:
            self.logger.error(f"Failed to save position: {e}")
    
    def save_metrics(self, strategy_name: str, metrics: StrategyMetrics):
        """Save strategy metrics to database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO strategy_metrics VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    strategy_name, metrics.total_trades, metrics.winning_trades,
                    metrics.losing_trades, metrics.total_pnl, metrics.win_rate,
                    metrics.profit_factor, metrics.max_drawdown, metrics.sharpe_ratio,
                    metrics.start_time.isoformat() if metrics.start_time else None,
                    metrics.end_time.isoformat() if metrics.end_time else None
                ))
                conn.commit()
        except Exception as e:
            self.logger.error(f"Failed to save metrics: {e}")

# Global paper trading engine instance
paper_trading_engine = PaperTradingEngine()
