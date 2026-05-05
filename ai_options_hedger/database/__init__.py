#!/usr/bin/env python3
"""
Database Package for AI Options Hedger Service
===============================================

Provides SQLite database management for options trading data.

Author: DTrade Systems
Version: 1.0.0
"""

from .options_db_manager import (
    OptionsDatabase,
    get_options_database,
    init_database,
    # Data Classes
    OptionsSignalRecord,
    OptionsTradeRecord,
    StackingEventRecord,
    DailyOptionsPerformance,
    # Enums
    OptionType,
    SignalType,
    TradeStatus,
    TradeOutcome,
    StackingDecision,
    MarketRegime,
)

__all__ = [
    # Main Classes
    'OptionsDatabase',
    'get_options_database',
    'init_database',
    # Data Classes
    'OptionsSignalRecord',
    'OptionsTradeRecord',
    'StackingEventRecord',
    'DailyOptionsPerformance',
    # Enums
    'OptionType',
    'SignalType',
    'TradeStatus',
    'TradeOutcome',
    'StackingDecision',
    'MarketRegime',
]
