"""
Position Tracker - Leg Position State Manager
Tracks all open legs (CE/PE) with quantity, strike, price, timestamp.
Marks legs as stacked or hedge and syncs with performance_tracker.py for P&L.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any, Set
from dataclasses import dataclass, field
from enum import Enum
import sqlite3
import json
import pandas as pd
import numpy as np
from decimal import Decimal

# Import from local performance tracker
from ai_engine.performance_analytics_advanced import AdvancedPerformanceTracker

# Local performance metrics classes
@dataclass
class PerformanceMetrics:
    """Local performance metrics class"""
    total_pnl: float = 0.0
    realized_pnl: float = 0.0
    unrealized_pnl: float = 0.0
    win_rate: float = 0.0
    avg_win: float = 0.0
    avg_loss: float = 0.0
    max_drawdown: float = 0.0
    sharpe_ratio: float = 0.0
    trades_count: int = 0

class PerformanceTracker:
    """Local performance tracker class"""
    def __init__(self):
        self.metrics = PerformanceMetrics()
        self.trades = []
    
    def add_trade(self, trade_pnl: float):
        """Add a trade to performance tracking"""
        self.trades.append(trade_pnl)
        self._update_metrics()
    
    def _update_metrics(self):
        """Update performance metrics"""
        if not self.trades:
            return
        
        self.metrics.total_pnl = sum(self.trades)
        winning_trades = [t for t in self.trades if t > 0]
        losing_trades = [t for t in self.trades if t <= 0]
        
        self.metrics.trades_count = len(self.trades)
        self.metrics.win_rate = len(winning_trades) / len(self.trades) if self.trades else 0
        self.metrics.avg_win = sum(winning_trades) / len(winning_trades) if winning_trades else 0
        self.metrics.avg_loss = sum(losing_trades) / len(losing_trades) if losing_trades else 0

logger = logging.getLogger(__name__)

class LegType(Enum):
    """Option leg types"""
    CE = "CE"  # Call Option
    PE = "PE"  # Put Option

class LegRole(Enum):
    """Role of the leg in strategy"""
    DIRECTIONAL = "DIRECTIONAL"  # Primary directional bet
    HEDGE = "HEDGE"  # Hedge against directional position
    STACKED = "STACKED"  # Additional legs stacked on directional
    PROTECTIVE = "PROTECTIVE"  # Protective stops

class LegStatus(Enum):
    """Leg position status"""
    OPEN = "OPEN"
    PARTIAL_FILLED = "PARTIAL_FILLED"
    CLOSED = "CLOSED"
    EXPIRED = "EXPIRED"
    ASSIGNED = "ASSIGNED"

class PositionSide(Enum):
    """Position side"""
    LONG = "LONG"
    SHORT = "SHORT"

@dataclass
class OptionLeg:
    """Individual option leg tracking"""
    leg_id: str
    underlying: str
    strike: float
    expiry: datetime
    leg_type: LegType
    leg_role: LegRole
    side: PositionSide
    quantity: int
    entry_price: float
    current_price: float = 0.0
    entry_time: datetime = field(default_factory=datetime.now)
    leg_status: LegStatus = LegStatus.OPEN
    
    # Strategy specific fields
    strategy_id: str = ""
    parent_position_id: str = ""
    hedge_ratio: float = 1.0
    
    # P&L tracking
    unrealized_pnl: float = 0.0
    realized_pnl: float = 0.0
    
    # Greeks (if available)
    delta: Optional[float] = None
    gamma: Optional[float] = None
    theta: Optional[float] = None
    vega: Optional[float] = None
    iv: Optional[float] = None
    
    # Risk metrics
    max_loss: Optional[float] = None
    max_profit: Optional[float] = None
    break_even: Optional[float] = None
    
    # Metadata
    tags: List[str] = field(default_factory=list)
    notes: str = ""
    
    def __post_init__(self):
        if not self.leg_id:
            self.leg_id = f"{self.underlying}_{self.strike}_{self.leg_type.value}_{int(self.entry_time.timestamp())}"
    
    def update_current_price(self, price: float):
        """Update current price and recalculate P&L"""
        self.current_price = price
        self._calculate_unrealized_pnl()
    
    def _calculate_unrealized_pnl(self):
        """Calculate unrealized P&L"""
        if self.current_price > 0:
            price_diff = self.current_price - self.entry_price
            if self.side == PositionSide.LONG:
                self.unrealized_pnl = price_diff * self.quantity
            else:
                self.unrealized_pnl = -price_diff * self.quantity
    
    def close_position(self, exit_price: float, close_time: datetime = None):
        """Close the position and calculate realized P&L"""
        if close_time is None:
            close_time = datetime.now()
        
        price_diff = exit_price - self.entry_price
        if self.side == PositionSide.LONG:
            self.realized_pnl = price_diff * self.quantity
        else:
            self.realized_pnl = -price_diff * self.quantity
        
        self.leg_status = LegStatus.CLOSED
        self.current_price = exit_price
        self.unrealized_pnl = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage"""
        return {
            'leg_id': self.leg_id,
            'underlying': self.underlying,
            'strike': self.strike,
            'expiry': self.expiry.isoformat(),
            'leg_type': self.leg_type.value,
            'leg_role': self.leg_role.value,
            'side': self.side.value,
            'quantity': self.quantity,
            'entry_price': self.entry_price,
            'current_price': self.current_price,
            'entry_time': self.entry_time.isoformat(),
            'leg_status': self.leg_status.value,
            'strategy_id': self.strategy_id,
            'parent_position_id': self.parent_position_id,
            'hedge_ratio': self.hedge_ratio,
            'unrealized_pnl': self.unrealized_pnl,
            'realized_pnl': self.realized_pnl,
            'delta': self.delta,
            'gamma': self.gamma,
            'theta': self.theta,
            'vega': self.vega,
            'iv': self.iv,
            'max_loss': self.max_loss,
            'max_profit': self.max_profit,
            'break_even': self.break_even,
            'tags': json.dumps(self.tags),
            'notes': self.notes
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'OptionLeg':
        """Create from dictionary"""
        leg = cls(
            leg_id=data['leg_id'],
            underlying=data['underlying'],
            strike=data['strike'],
            expiry=datetime.fromisoformat(data['expiry']),
            leg_type=LegType(data['leg_type']),
            leg_role=LegRole(data['leg_role']),
            side=PositionSide(data['side']),
            quantity=data['quantity'],
            entry_price=data['entry_price'],
            current_price=data.get('current_price', 0.0),
            entry_time=datetime.fromisoformat(data['entry_time']),
            leg_status=LegStatus(data['leg_status']),
            strategy_id=data.get('strategy_id', ''),
            parent_position_id=data.get('parent_position_id', ''),
            hedge_ratio=data.get('hedge_ratio', 1.0),
            unrealized_pnl=data.get('unrealized_pnl', 0.0),
            realized_pnl=data.get('realized_pnl', 0.0),
            delta=data.get('delta'),
            gamma=data.get('gamma'),
            theta=data.get('theta'),
            vega=data.get('vega'),
            iv=data.get('iv'),
            max_loss=data.get('max_loss'),
            max_profit=data.get('max_profit'),
            break_even=data.get('break_even'),
            tags=json.loads(data.get('tags', '[]')),
            notes=data.get('notes', '')
        )
        return leg

@dataclass
class StrategyPosition:
    """Strategy-level position tracking multiple legs"""
    position_id: str
    strategy_name: str
    underlying: str
    legs: List[OptionLeg] = field(default_factory=list)
    entry_time: datetime = field(default_factory=datetime.now)
    status: str = "ACTIVE"
    
    # Strategy P&L
    total_unrealized_pnl: float = 0.0
    total_realized_pnl: float = 0.0
    
    # Risk metrics
    total_delta: float = 0.0
    total_gamma: float = 0.0
    total_theta: float = 0.0
    total_vega: float = 0.0
    
    # Position sizing
    total_capital_used: float = 0.0
    max_risk: float = 0.0
    
    def add_leg(self, leg: OptionLeg):
        """Add a leg to the position"""
        leg.parent_position_id = self.position_id
        self.legs.append(leg)
        self._update_metrics()
    
    def remove_leg(self, leg_id: str) -> bool:
        """Remove a leg from the position"""
        for i, leg in enumerate(self.legs):
            if leg.leg_id == leg_id:
                del self.legs[i]
                self._update_metrics()
                return True
        return False
    
    def _update_metrics(self):
        """Update position-level metrics"""
        self.total_unrealized_pnl = sum(leg.unrealized_pnl for leg in self.legs)
        self.total_realized_pnl = sum(leg.realized_pnl for leg in self.legs)
        
        # Greeks
        self.total_delta = sum(leg.delta or 0 for leg in self.legs)
        self.total_gamma = sum(leg.gamma or 0 for leg in self.legs)
        self.total_theta = sum(leg.theta or 0 for leg in self.legs)
        self.total_vega = sum(leg.vega or 0 for leg in self.legs)
        
        # Capital
        self.total_capital_used = sum(leg.entry_price * leg.quantity for leg in self.legs)
    
    def get_directional_legs(self) -> List[OptionLeg]:
        """Get directional legs"""
        return [leg for leg in self.legs if leg.leg_role == LegRole.DIRECTIONAL]
    
    def get_hedge_legs(self) -> List[OptionLeg]:
        """Get hedge legs"""
        return [leg for leg in self.legs if leg.leg_role == LegRole.HEDGE]
    
    def get_stacked_legs(self) -> List[OptionLeg]:
        """Get stacked legs"""
        return [leg for leg in self.legs if leg.leg_role == LegRole.STACKED]

class PositionTracker:
    """
    Position tracking system that integrates with local performance analytics modules.
    Manages all option legs and their states, P&L, and synchronization.
    """
    
    def __init__(self, db_path: str = "positions.db"):
        """Initialize position tracker"""
        self.db_path = db_path
        self.legs: Dict[str, OptionLeg] = {}
        self.strategy_positions: Dict[str, StrategyPosition] = {}
        
        # Integration with local performance analytics
        self.performance_tracker = PerformanceTracker()
        
        # Threading locks
        self._position_lock = asyncio.Lock()
        
        # Caching
        self._cache_expiry = 30  # seconds
        self._last_cache_update = None
        self._cached_metrics = None
        
        logger.info("Position Tracker initialized")
    
    async def initialize(self):
        """Initialize the position tracker"""
        await self._create_database()
        await self._load_positions()
        logger.info("Position Tracker initialized successfully")
    
    async def _create_database(self):
        """Create database tables for position tracking"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Option legs table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS option_legs (
                leg_id TEXT PRIMARY KEY,
                underlying TEXT NOT NULL,
                strike REAL NOT NULL,
                expiry TEXT NOT NULL,
                leg_type TEXT NOT NULL,
                leg_role TEXT NOT NULL,
                side TEXT NOT NULL,
                quantity INTEGER NOT NULL,
                entry_price REAL NOT NULL,
                current_price REAL DEFAULT 0.0,
                entry_time TEXT NOT NULL,
                leg_status TEXT NOT NULL,
                strategy_id TEXT,
                parent_position_id TEXT,
                hedge_ratio REAL DEFAULT 1.0,
                unrealized_pnl REAL DEFAULT 0.0,
                realized_pnl REAL DEFAULT 0.0,
                delta REAL,
                gamma REAL,
                theta REAL,
                vega REAL,
                iv REAL,
                max_loss REAL,
                max_profit REAL,
                break_even REAL,
                tags TEXT DEFAULT '[]',
                notes TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Strategy positions table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS strategy_positions (
                position_id TEXT PRIMARY KEY,
                strategy_name TEXT NOT NULL,
                underlying TEXT NOT NULL,
                entry_time TEXT NOT NULL,
                status TEXT DEFAULT 'ACTIVE',
                total_unrealized_pnl REAL DEFAULT 0.0,
                total_realized_pnl REAL DEFAULT 0.0,
                total_delta REAL DEFAULT 0.0,
                total_gamma REAL DEFAULT 0.0,
                total_theta REAL DEFAULT 0.0,
                total_vega REAL DEFAULT 0.0,
                total_capital_used REAL DEFAULT 0.0,
                max_risk REAL DEFAULT 0.0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Indices for performance
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_legs_underlying ON option_legs(underlying)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_legs_status ON option_legs(leg_status)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_legs_strategy ON option_legs(strategy_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_positions_underlying ON strategy_positions(underlying)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_positions_status ON strategy_positions(status)')
        
        conn.commit()
        conn.close()
    
    async def _load_positions(self):
        """Load existing positions from database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Load option legs
        cursor.execute('SELECT * FROM option_legs WHERE leg_status != ?', (LegStatus.CLOSED.value,))
        leg_rows = cursor.fetchall()
        
        for row in leg_rows:
            columns = [desc[0] for desc in cursor.description]
            leg_data = dict(zip(columns, row))
            leg = OptionLeg.from_dict(leg_data)
            self.legs[leg.leg_id] = leg
        
        # Load strategy positions
        cursor.execute('SELECT * FROM strategy_positions WHERE status = ?', ('ACTIVE',))
        position_rows = cursor.fetchall()
        
        for row in position_rows:
            columns = [desc[0] for desc in cursor.description]
            pos_data = dict(zip(columns, row))
            
            position = StrategyPosition(
                position_id=pos_data['position_id'],
                strategy_name=pos_data['strategy_name'],
                underlying=pos_data['underlying'],
                entry_time=datetime.fromisoformat(pos_data['entry_time']),
                status=pos_data['status']
            )
            
            # Add legs to position
            position_legs = [leg for leg in self.legs.values() 
                           if leg.parent_position_id == position.position_id]
            position.legs = position_legs
            position._update_metrics()
            
            self.strategy_positions[position.position_id] = position
        
        conn.close()
        logger.info(f"Loaded {len(self.legs)} legs and {len(self.strategy_positions)} positions")
    
    async def add_leg(self, leg: OptionLeg, strategy_position_id: str = None) -> bool:
        """Add a new option leg"""
        async with self._position_lock:
            try:
                # Store in memory
                self.legs[leg.leg_id] = leg
                
                # Add to strategy position if specified
                if strategy_position_id and strategy_position_id in self.strategy_positions:
                    self.strategy_positions[strategy_position_id].add_leg(leg)
                
                # Store in database
                await self._save_leg(leg)
                
                # Sync with performance tracker
                await self._sync_with_performance_tracker()
                
                logger.info(f"Added leg: {leg.leg_id}")
                return True
                
            except Exception as e:
                logger.error(f"Error adding leg {leg.leg_id}: {e}")
                return False
    
    async def update_leg_price(self, leg_id: str, current_price: float) -> bool:
        """Update leg current price and P&L"""
        if leg_id not in self.legs:
            return False
        
        async with self._position_lock:
            try:
                leg = self.legs[leg_id]
                leg.update_current_price(current_price)
                
                # Update strategy position metrics
                if leg.parent_position_id in self.strategy_positions:
                    self.strategy_positions[leg.parent_position_id]._update_metrics()
                
                # Update database
                await self._save_leg(leg)
                
                return True
                
            except Exception as e:
                logger.error(f"Error updating leg price {leg_id}: {e}")
                return False
    
    async def close_leg(self, leg_id: str, exit_price: float, close_time: datetime = None) -> bool:
        """Close an option leg"""
        if leg_id not in self.legs:
            return False
        
        async with self._position_lock:
            try:
                leg = self.legs[leg_id]
                leg.close_position(exit_price, close_time)
                
                # Update strategy position
                if leg.parent_position_id in self.strategy_positions:
                    position = self.strategy_positions[leg.parent_position_id]
                    position._update_metrics()
                    
                    # Check if all legs are closed
                    active_legs = [l for l in position.legs if l.leg_status == LegStatus.OPEN]
                    if not active_legs:
                        position.status = "CLOSED"
                        await self._save_strategy_position(position)
                
                # Update database
                await self._save_leg(leg)
                
                # Sync with performance tracker
                await self._sync_with_performance_tracker()
                
                logger.info(f"Closed leg: {leg_id} with P&L: {leg.realized_pnl}")
                return True
                
            except Exception as e:
                logger.error(f"Error closing leg {leg_id}: {e}")
                return False
    
    async def create_strategy_position(self, position: StrategyPosition) -> bool:
        """Create a new strategy position"""
        async with self._position_lock:
            try:
                self.strategy_positions[position.position_id] = position
                await self._save_strategy_position(position)
                logger.info(f"Created strategy position: {position.position_id}")
                return True
            except Exception as e:
                logger.error(f"Error creating strategy position: {e}")
                return False
    
    async def get_current_positions(self) -> List[OptionLeg]:
        """Get all current open positions"""
        return [leg for leg in self.legs.values() if leg.leg_status == LegStatus.OPEN]
    
    async def get_positions_by_underlying(self, underlying: str) -> List[OptionLeg]:
        """Get positions for specific underlying"""
        return [leg for leg in self.legs.values() 
                if leg.underlying == underlying and leg.leg_status == LegStatus.OPEN]
    
    async def get_positions_by_role(self, role: LegRole) -> List[OptionLeg]:
        """Get positions by role"""
        return [leg for leg in self.legs.values() 
                if leg.leg_role == role and leg.leg_status == LegStatus.OPEN]
    
    async def get_strategy_position(self, position_id: str) -> Optional[StrategyPosition]:
        """Get strategy position by ID"""
        return self.strategy_positions.get(position_id)
    
    async def get_portfolio_pnl(self) -> Dict[str, float]:
        """Get total portfolio P&L"""
        total_unrealized = sum(leg.unrealized_pnl for leg in self.legs.values())
        total_realized = sum(leg.realized_pnl for leg in self.legs.values())
        
        return {
            'unrealized_pnl': total_unrealized,
            'realized_pnl': total_realized,
            'total_pnl': total_unrealized + total_realized
        }
    
    async def get_portfolio_greeks(self) -> Dict[str, float]:
        """Get total portfolio Greeks"""
        open_legs = await self.get_current_positions()
        
        return {
            'delta': sum(leg.delta or 0 for leg in open_legs),
            'gamma': sum(leg.gamma or 0 for leg in open_legs),
            'theta': sum(leg.theta or 0 for leg in open_legs),
            'vega': sum(leg.vega or 0 for leg in open_legs)
        }
    
    async def get_risk_metrics(self) -> Dict[str, Any]:
        """Get portfolio risk metrics"""
        open_legs = await self.get_current_positions()
        
        if not open_legs:
            return {}
        
        # Calculate various risk metrics
        total_capital = sum(leg.entry_price * leg.quantity for leg in open_legs)
        current_value = sum(leg.current_price * leg.quantity for leg in open_legs)
        
        return {
            'total_capital_used': total_capital,
            'current_portfolio_value': current_value,
            'number_of_positions': len(open_legs),
            'number_of_underlyings': len(set(leg.underlying for leg in open_legs)),
            'ce_positions': len([leg for leg in open_legs if leg.leg_type == LegType.CE]),
            'pe_positions': len([leg for leg in open_legs if leg.leg_type == LegType.PE]),
            'long_positions': len([leg for leg in open_legs if leg.side == PositionSide.LONG]),
            'short_positions': len([leg for leg in open_legs if leg.side == PositionSide.SHORT])
        }
    
    async def update_positions(self, market_data: Dict[str, Any]):
        """Update all positions with latest market data"""
        for leg in self.legs.values():
            if leg.leg_status == LegStatus.OPEN:
                # Get current price from market data
                symbol_key = f"{leg.underlying}_{leg.strike}_{leg.leg_type.value}"
                if symbol_key in market_data:
                    await self.update_leg_price(leg.leg_id, market_data[symbol_key])
    
    async def _save_leg(self, leg: OptionLeg):
        """Save leg to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        leg_data = leg.to_dict()
        placeholders = ', '.join(['?' for _ in leg_data])
        columns = ', '.join(leg_data.keys())
        
        cursor.execute(f'''
            INSERT OR REPLACE INTO option_legs ({columns})
            VALUES ({placeholders})
        ''', list(leg_data.values()))
        
        conn.commit()
        conn.close()
    
    async def _save_strategy_position(self, position: StrategyPosition):
        """Save strategy position to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO strategy_positions 
            (position_id, strategy_name, underlying, entry_time, status, 
             total_unrealized_pnl, total_realized_pnl, total_delta, total_gamma, 
             total_theta, total_vega, total_capital_used, max_risk, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            position.position_id, position.strategy_name, position.underlying,
            position.entry_time.isoformat(), position.status,
            position.total_unrealized_pnl, position.total_realized_pnl,
            position.total_delta, position.total_gamma, position.total_theta,
            position.total_vega, position.total_capital_used, position.max_risk,
            datetime.now().isoformat()
        ))
        
        conn.commit()
        conn.close()
    
    async def _sync_with_performance_tracker(self):
        """Sync position data with local performance analytics"""
        try:
            # Get current positions and P&L
            pnl_data = await self.get_portfolio_pnl()
            
            # Update performance tracker
            await self.performance_tracker.update_performance_from_positions(pnl_data)
            
        except Exception as e:
            logger.error(f"Error syncing with performance tracker: {e}")
    
    async def cleanup(self):
        """Cleanup resources"""
        try:
            # Close any remaining connections
            if hasattr(self.performance_tracker, 'cleanup'):
                await self.performance_tracker.cleanup()
        except Exception as e:
            logger.error(f"Error in cleanup: {e}")
