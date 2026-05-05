"""
AI Scalping Service - Core Module

Contains:
- InstitutionalCapitalManager: World-class capital management and position sizing
"""

from .capital_manager import (
    InstitutionalCapitalManager,
    PositionSizingMode,
    PositionSize,
    RiskConfig,
    get_capital_manager,
    capital_manager,
    INDEX_LOT_SIZES,
    FREEZE_QUANTITIES,
    INSTRUMENT_ALLOCATION_PRIORITY,
    DEFAULT_ATM_PREMIUM_PER_SHARE,
    ALL_INDEX_INSTRUMENTS,
)

__all__ = [
    "InstitutionalCapitalManager",
    "PositionSizingMode",
    "PositionSize",
    "RiskConfig",
    "get_capital_manager",
    "capital_manager",
    "INDEX_LOT_SIZES",
    "FREEZE_QUANTITIES",
    "INSTRUMENT_ALLOCATION_PRIORITY",
    "DEFAULT_ATM_PREMIUM_PER_SHARE",
    "ALL_INDEX_INSTRUMENTS",
]
