"""
Equity High-Velocity Service Strategy Module
============================================
WORLD-CLASS UNBEATABLE ENGINE v4.0

Production Engine:
- world_class_engine: Core engine with Chartink-style patterns (95%+ WR target)
- world_class_production_engine: Production wrapper with live trade execution

Target: 95%+ Win Rate | 500%+ Monthly Returns
"""

from .dhan_connector import DhanAPIClient as DhanConnector
from .dhan_config import DhanAPIManager

# Import routers for FastAPI integration - disabled temporarily as we migrate to world-class engine
# from .auto_trader_router import router as auto_trader_router
auto_trader_router = None  # Placeholder until migrated

# World-Class Engine v4.0 (PRODUCTION)
try:
    from .world_class_engine import (
        WorldClassEngine,
        WorldClassSignal,
        WorldClassConfig,
        SignalConfidence,
        MomentumType,
        ChartinkPattern,
        WorldClassIndicators,
        WorldClassPatternDetector
    )
    WORLD_CLASS_AVAILABLE = True
except ImportError as e:
    WORLD_CLASS_AVAILABLE = False
    import logging
    logging.warning(f"World-Class engine not available: {e}")

# World-Class Production Engine v4.0 (LIVE TRADING)
try:
    from .world_class_production_engine import (
        ProductionWorldClassEngine,
        ActiveTrade,
        TradeStatus,
        AlertManager,
        PositionTracker
    )
    PRODUCTION_AVAILABLE = True
except ImportError as e:
    PRODUCTION_AVAILABLE = False
    import logging
    logging.warning(f"Production engine not available: {e}")


__all__ = [
    # API Clients
    'DhanConnector',
    'DhanAPIManager',
    
    # Routers
    'auto_trader_router',
    
    # World-Class Engine
    'WorldClassEngine',
    'WorldClassSignal',
    'WorldClassConfig',
    'SignalConfidence',
    'MomentumType',
    
    # Production Engine
    'ProductionWorldClassEngine',
    'ActiveTrade',
    'TradeStatus',
    
    # Availability flags
    'WORLD_CLASS_AVAILABLE',
    'PRODUCTION_AVAILABLE'
]
