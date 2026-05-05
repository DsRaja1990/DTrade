"""
Backtest Configuration Module

This module provides configurable parameters for the backtest system
to enable easy customization and scenario testing.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
from datetime import datetime

@dataclass
class BacktestScenario:
    """Configuration for a backtest scenario"""
    name: str
    start_date: str
    end_date: str
    initial_capital: float
    instruments: List[str]
    description: str = ""
    
@dataclass 
class MarketDataConfig:
    """Market data simulation configuration"""
    use_synthetic_data: bool = True
    volatility_regime: str = "medium"  # low, medium, high
    correlation_strength: float = 0.85
    trend_strength: float = 0.001
    noise_level: float = 0.02
    
@dataclass
class ExecutionConfig:
    """Execution simulation configuration"""
    base_slippage_bps: float = 1.8
    impact_multiplier: float = 1.0
    latency_ms: int = 50
    fill_rate_target: float = 0.95
    commission_per_lot: Dict[str, float] = None
    
    def __post_init__(self):
        if self.commission_per_lot is None:
            self.commission_per_lot = {
                "NIFTY": 20.0,
                "BANKNIFTY": 25.0,
                "SENSEX": 22.0
            }

@dataclass
class RiskConfig:
    """Risk management configuration"""
    max_position_size_pct: float = 0.3
    max_daily_loss_pct: float = 0.02
    volatility_threshold: float = 0.25
    correlation_threshold: float = 0.9
    stop_loss_pct: float = 0.05

class BacktestConfig:
    """Main backtest configuration class"""
    
    def __init__(self):
        self.scenarios = self._get_default_scenarios()
        self.market_data = MarketDataConfig()
        self.execution = ExecutionConfig()
        self.risk = RiskConfig()
        
    def _get_default_scenarios(self) -> List[BacktestScenario]:
        """Get default backtest scenarios"""
        return [
            BacktestScenario(
                name="Quick Test",
                start_date="2024-01-01",
                end_date="2024-01-31",
                initial_capital=5000000,
                instruments=["NIFTY"],
                description="One month test with NIFTY only"
            ),
            BacktestScenario(
                name="Quarter Test",
                start_date="2024-01-01", 
                end_date="2024-03-31",
                initial_capital=5000000,
                instruments=["NIFTY", "BANKNIFTY", "SENSEX"],
                description="Three month comprehensive test"
            ),
            BacktestScenario(
                name="Half Year Test",
                start_date="2024-01-01",
                end_date="2024-06-30", 
                initial_capital=10000000,
                instruments=["NIFTY", "BANKNIFTY", "SENSEX"],
                description="Six month test with larger capital"
            ),
            BacktestScenario(
                name="Full Year Test",
                start_date="2024-01-01",
                end_date="2024-12-31",
                initial_capital=10000000,
                instruments=["NIFTY", "BANKNIFTY", "SENSEX"],
                description="Full year comprehensive backtest"
            ),
            BacktestScenario(
                name="High Volatility Test",
                start_date="2024-03-01",
                end_date="2024-05-31",
                initial_capital=5000000,
                instruments=["NIFTY", "BANKNIFTY"],
                description="Test during high volatility period"
            ),
            BacktestScenario(
                name="Single Instrument Deep Dive",
                start_date="2024-01-01",
                end_date="2024-12-31",
                initial_capital=5000000,
                instruments=["BANKNIFTY"],
                description="Full year test with BANKNIFTY only"
            )
        ]
    
    def add_custom_scenario(self, scenario: BacktestScenario):
        """Add a custom backtest scenario"""
        self.scenarios.append(scenario)
        
    def get_scenario_by_name(self, name: str) -> Optional[BacktestScenario]:
        """Get scenario by name"""
        for scenario in self.scenarios:
            if scenario.name == name:
                return scenario
        return None
        
    def update_market_conditions(self, 
                                volatility: str = "medium",
                                correlation: float = 0.85,
                                trend: float = 0.001):
        """Update market data simulation parameters"""
        self.market_data.volatility_regime = volatility
        self.market_data.correlation_strength = correlation  
        self.market_data.trend_strength = trend
        
    def update_execution_quality(self,
                                slippage_bps: float = 1.8,
                                fill_rate: float = 0.95,
                                latency_ms: int = 50):
        """Update execution simulation parameters"""
        self.execution.base_slippage_bps = slippage_bps
        self.execution.fill_rate_target = fill_rate
        self.execution.latency_ms = latency_ms
        
    def to_dict(self) -> Dict:
        """Convert configuration to dictionary"""
        return {
            "scenarios": [
                {
                    "name": s.name,
                    "start_date": s.start_date,
                    "end_date": s.end_date,
                    "initial_capital": s.initial_capital,
                    "instruments": s.instruments,
                    "description": s.description
                } for s in self.scenarios
            ],
            "market_data": {
                "use_synthetic_data": self.market_data.use_synthetic_data,
                "volatility_regime": self.market_data.volatility_regime,
                "correlation_strength": self.market_data.correlation_strength,
                "trend_strength": self.market_data.trend_strength,
                "noise_level": self.market_data.noise_level
            },
            "execution": {
                "base_slippage_bps": self.execution.base_slippage_bps,
                "impact_multiplier": self.execution.impact_multiplier,
                "latency_ms": self.execution.latency_ms,
                "fill_rate_target": self.execution.fill_rate_target,
                "commission_per_lot": self.execution.commission_per_lot
            },
            "risk": {
                "max_position_size_pct": self.risk.max_position_size_pct,
                "max_daily_loss_pct": self.risk.max_daily_loss_pct,
                "volatility_threshold": self.risk.volatility_threshold,
                "correlation_threshold": self.risk.correlation_threshold,
                "stop_loss_pct": self.risk.stop_loss_pct
            }
        }

# Predefined configurations for different market conditions
BULL_MARKET_CONFIG = BacktestConfig()
BULL_MARKET_CONFIG.update_market_conditions(volatility="low", trend=0.002)
BULL_MARKET_CONFIG.update_execution_quality(slippage_bps=1.5, fill_rate=0.98)

BEAR_MARKET_CONFIG = BacktestConfig()
BEAR_MARKET_CONFIG.update_market_conditions(volatility="high", trend=-0.001)
BEAR_MARKET_CONFIG.update_execution_quality(slippage_bps=2.5, fill_rate=0.90)

VOLATILE_MARKET_CONFIG = BacktestConfig()
VOLATILE_MARKET_CONFIG.update_market_conditions(volatility="high", correlation=0.75)
VOLATILE_MARKET_CONFIG.update_execution_quality(slippage_bps=2.2, fill_rate=0.92)

DEFAULT_CONFIG = BacktestConfig()
