"""
Database Module for Trading System
===================================
Uses the central database from equity_hv_service/database
"""

import sys
import os

# Add parent database to path
parent_db_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, parent_db_path)

try:
    from database.db_manager import (
        TradingDatabase,
        get_database,
        SignalRecord,
        TradeRecord,
        DailyPerformance,
        SignalType,
        TradeStatus,
        TradeOutcome
    )
except ImportError:
    # Fallback to local implementation
    from .trading_database import TradingDatabase
    get_database = None
    SignalRecord = None
    TradeRecord = None
    DailyPerformance = None
    SignalType = None
    TradeStatus = None
    TradeOutcome = None

__all__ = [
    'TradingDatabase',
    'get_database',
    'SignalRecord', 
    'TradeRecord',
    'DailyPerformance',
    'SignalType',
    'TradeStatus',
    'TradeOutcome'
]
