"""
Equity High-Velocity Service API Module
"""

try:
    from .equity_hv_router import router, set_strategy_engine
    __all__ = ["router", "set_strategy_engine"]
except ImportError:
    # Handle import errors gracefully
    pass
