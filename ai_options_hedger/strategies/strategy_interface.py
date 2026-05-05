"""
Universal Strategy Interface for Paper Trading Engine
All strategies must implement this interface to be compatible with the paper trading engine
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum
import pandas as pd
from datetime import datetime

class SignalStrength(Enum):
    """Signal strength levels"""
    STRONG_BUY = "STRONG_BUY"
    BUY = "BUY"
    WEAK_BUY = "WEAK_BUY"
    HOLD = "HOLD"
    WEAK_SELL = "WEAK_SELL"
    SELL = "SELL"
    STRONG_SELL = "STRONG_SELL"

class TradeType(Enum):
    """Trade types"""
    ENTRY = "ENTRY"
    HEDGE = "HEDGE"
    STACK = "STACK"
    EXIT = "EXIT"

@dataclass
class TradeSignal:
    """Universal trade signal structure"""
    timestamp: datetime
    symbol: str
    signal_strength: SignalStrength
    trade_type: TradeType
    quantity: int
    target_price: Optional[float] = None
    stop_loss: Optional[float] = None
    confidence_score: float = 0.0
    metadata: Dict[str, Any] = None

@dataclass
class MarketData:
    """Market data structure for strategy evaluation"""
    timestamp: datetime
    index_price: float
    vix: float
    option_chain: Dict[str, Any]
    technical_indicators: Dict[str, float]
    market_depth: Dict[str, Any] = None

class StrategyRunner(ABC):
    """
    Universal Strategy Interface
    All strategies must implement this class to work with the paper trading engine
    """
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize strategy with configuration"""
        self.config = config
        self.name = self.__class__.__name__
        self.is_active = False
        
    @abstractmethod
    async def initialize(self) -> bool:
        """
        Initialize strategy components
        Returns True if initialization successful, False otherwise
        """
        pass
    
    @abstractmethod
    async def evaluate_signals(self, market_data: MarketData) -> List[TradeSignal]:
        """
        Evaluate market conditions and generate trade signals
        
        Args:
            market_data: Current market data including prices, indicators, etc.
            
        Returns:
            List of trade signals to execute
        """
        pass
    
    @abstractmethod
    async def update_positions(self, positions: List[Dict[str, Any]]) -> None:
        """
        Update strategy with current position status
        
        Args:
            positions: List of current open positions
        """
        pass
    
    @abstractmethod
    async def risk_check(self, proposed_signal: TradeSignal) -> bool:
        """
        Perform risk validation on proposed trade signal
        
        Args:
            proposed_signal: Signal to validate
            
        Returns:
            True if signal passes risk checks, False otherwise
        """
        pass
    
    @abstractmethod
    async def cleanup(self) -> None:
        """Cleanup resources when strategy stops"""
        pass
    
    def get_strategy_info(self) -> Dict[str, Any]:
        """Get strategy metadata"""
        return {
            "name": self.name,
            "is_active": self.is_active,
            "config": self.config
        }
