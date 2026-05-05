"""
╔══════════════════════════════════════════════════════════════════════════════════════╗
║        EQUITY HV SERVICE - PRODUCTION TRADING ENGINE v2.0                            ║
║                F&O Stock Options Trading (RELIANCE, TCS, HDFCBANK, etc.)            ║
╠══════════════════════════════════════════════════════════════════════════════════════╣
║                                                                                      ║
║  SERVICE: Equity HV Service - Port 5080                                             ║
║  INSTRUMENTS: Elite F&O Stocks - 10+ high-volume options                            ║
║  MODE: Paper Trading Default → Switchable to Live                                   ║
║                                                                                      ║
║  STOCK OPTIONS METHODOLOGY:                                                          ║
║  ═══════════════════════════════════════════════════════════════════════════════    ║
║                                                                                      ║
║  1. HISTORICAL VOLATILITY BASED ENTRY                                               ║
║     • HV analysis for optimal entry timing                                          ║
║     • 10% capital probe with 50% wide stoploss                                      ║
║     • Scale to 100% on Gemini confirmation                                          ║
║                                                                                      ║
║  2. STOCK-SPECIFIC EXIT                                                              ║
║     • Premium-based 50-point trailing after 50-point profit                         ║
║     • Stock correlation analysis with index                                         ║
║     • Sector momentum tracking                                                       ║
║                                                                                      ║
║  3. ELITE STOCK FOCUS                                                                ║
║     • RELIANCE, TCS, HDFCBANK, INFY, ICICIBANK                                     ║
║     • KOTAKBANK, SBIN, BHARTIARTL, LT, AXISBANK                                    ║
║     • High-liquidity options only                                                   ║
║                                                                                      ║
╚══════════════════════════════════════════════════════════════════════════════════════╝
"""

import asyncio
import aiohttp
import json
import logging
import sqlite3
import uuid
from datetime import datetime, date, time, timedelta
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
from pathlib import Path
import os
import sys

logger = logging.getLogger(__name__ + '.production_trading_engine')


# ============================================================================
# TRADING ENUMS
# ============================================================================

class TradingMode(str, Enum):
    """Trading mode - Paper for testing, Live for real trades"""
    PAPER = "PAPER"
    LIVE = "LIVE"


class StockSector(str, Enum):
    """Stock sector classification"""
    BANKING = "BANKING"
    IT = "IT"
    OIL_GAS = "OIL_GAS"
    TELECOM = "TELECOM"
    INFRA = "INFRA"
    FMCG = "FMCG"
    AUTO = "AUTO"
    PHARMA = "PHARMA"


class TradePhase(str, Enum):
    """Trade lifecycle phases"""
    SCANNING = "SCANNING"
    ANALYSING = "ANALYSING"
    PROBE = "PROBE"
    CONFIRMING = "CONFIRMING"
    SCALING = "SCALING"
    FULL_POSITION = "FULL_POSITION"
    TRAILING = "TRAILING"
    REDUCING = "REDUCING"
    EXITING = "EXITING"
    CLOSED = "CLOSED"


class TradeDirection(str, Enum):
    """Trade direction"""
    BULLISH = "BULLISH"
    BEARISH = "BEARISH"
    NEUTRAL = "NEUTRAL"


class ExitReason(str, Enum):
    """Exit reason tracking"""
    STOPLOSS = "STOPLOSS"
    TRAILING_STOP = "TRAILING_STOP"
    TARGET_HIT = "TARGET_HIT"
    GEMINI_EXIT = "GEMINI_EXIT"
    TIME_EXIT = "TIME_EXIT"
    HV_COLLAPSE = "HV_COLLAPSE"
    PROBE_ABORT = "PROBE_ABORT"
    USER_MANUAL = "USER_MANUAL"
    MARKET_CLOSE = "MARKET_CLOSE"
    SECTOR_ROTATION = "SECTOR_ROTATION"


# ============================================================================
# ELITE STOCK CONFIGURATION
# ============================================================================

@dataclass
class EliteStock:
    """Elite stock configuration with lot size and sector"""
    symbol: str
    lot_size: int
    sector: StockSector
    avg_daily_volume: int = 0
    beta: float = 1.0
    
    def to_dict(self) -> Dict:
        return {
            'symbol': self.symbol,
            'lot_size': self.lot_size,
            'sector': self.sector.value,
            'beta': self.beta
        }


# Elite F&O Stocks with lot sizes
ELITE_STOCKS: Dict[str, EliteStock] = {
    "RELIANCE": EliteStock("RELIANCE", 250, StockSector.OIL_GAS, beta=0.85),
    "TCS": EliteStock("TCS", 175, StockSector.IT, beta=0.75),
    "HDFCBANK": EliteStock("HDFCBANK", 550, StockSector.BANKING, beta=1.1),
    "INFY": EliteStock("INFY", 300, StockSector.IT, beta=0.8),
    "ICICIBANK": EliteStock("ICICIBANK", 700, StockSector.BANKING, beta=1.15),
    "KOTAKBANK": EliteStock("KOTAKBANK", 400, StockSector.BANKING, beta=1.0),
    "SBIN": EliteStock("SBIN", 1500, StockSector.BANKING, beta=1.25),
    "BHARTIARTL": EliteStock("BHARTIARTL", 925, StockSector.TELECOM, beta=0.95),
    "LT": EliteStock("LT", 225, StockSector.INFRA, beta=1.05),
    "AXISBANK": EliteStock("AXISBANK", 625, StockSector.BANKING, beta=1.2),
}


# ============================================================================
# CONFIGURATION
# ============================================================================

@dataclass
class EquityEngineConfig:
    """Equity HV Service Engine Configuration"""
    
    # Service settings
    service_name: str = "Equity_HV_Service"
    service_port: int = 5080
    
    # Trading mode - PAPER by default
    trading_mode: TradingMode = TradingMode.PAPER
    
    # Capital settings
    total_capital: float = 500000.0
    max_daily_loss_percent: float = 3.0
    max_capital_per_trade: float = 100000.0
    max_concurrent_positions: int = 3  # Multiple stocks allowed
    
    # Probe-Scale settings
    probe_capital_pct: float = 10.0       # 10% for probe
    scale_capital_pct: float = 90.0       # 90% for scale
    probe_stoploss_pct: float = 50.0      # 50% wide stoploss
    scaled_stoploss_pct: float = 30.0     # 30% after scaling
    
    # Trailing stop (50-point trailing as specified)
    trailing_activation_points: float = 50.0  # Activate at 50 pts profit
    trailing_distance_points: float = 50.0    # Trail 50 pts behind
    
    # HV (Historical Volatility) thresholds
    min_hv_for_entry: float = 20.0        # Min 20% HV
    max_hv_for_entry: float = 60.0        # Max 60% HV (too volatile)
    optimal_hv_range: Tuple[float, float] = field(default_factory=lambda: (25.0, 45.0))
    
    # AI settings
    gemini_service_url: str = "http://localhost:4080"
    min_gemini_confidence: float = 0.85
    gemini_check_interval: int = 30       # Check every 30 seconds
    
    # Scaling thresholds
    min_profit_to_scale_pct: float = 10.0
    max_probe_loss_pct: float = 25.0
    
    # Trading hours (IST)
    trading_start: time = field(default_factory=lambda: time(9, 20))
    trading_end: time = field(default_factory=lambda: time(15, 15))
    no_new_trades_after: time = field(default_factory=lambda: time(15, 0))
    
    # Timing (stock options can hold longer)
    probe_timeout_seconds: int = 180      # 3 min probe timeout
    max_position_minutes: int = 60        # Max 60 min for stock options
    
    # Database
    db_path: str = "strategy/database/equity_trades.db"
    
    # Paper trading settings
    paper_slippage_pct: float = 0.2       # Stock options have more slippage
    paper_latency_ms: int = 75            # Slightly slower execution


# ============================================================================
# HISTORICAL VOLATILITY TRACKING
# ============================================================================

@dataclass
class StockHVData:
    """Historical Volatility data for a stock"""
    symbol: str
    timestamp: datetime = field(default_factory=datetime.now)
    
    # Price data
    current_price: float = 0.0
    open_price: float = 0.0
    high_price: float = 0.0
    low_price: float = 0.0
    prev_close: float = 0.0
    
    # HV metrics
    hv_5d: float = 0.0        # 5-day HV
    hv_10d: float = 0.0       # 10-day HV
    hv_20d: float = 0.0       # 20-day HV
    hv_current: float = 0.0   # Current session HV
    
    # IV data (if available)
    iv_atm_ce: float = 0.0
    iv_atm_pe: float = 0.0
    iv_skew: float = 0.0
    
    # Correlation with index
    nifty_correlation: float = 0.0
    sector_correlation: float = 0.0
    
    # Volume analysis
    volume: int = 0
    volume_ratio: float = 1.0
    delivery_pct: float = 0.0
    
    # Price history for HV calculation
    price_history: List[float] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return {
            'symbol': self.symbol,
            'timestamp': self.timestamp.isoformat(),
            'current_price': self.current_price,
            'hv_5d': round(self.hv_5d, 2),
            'hv_10d': round(self.hv_10d, 2),
            'hv_20d': round(self.hv_20d, 2),
            'hv_current': round(self.hv_current, 2),
            'iv_atm_ce': round(self.iv_atm_ce, 2),
            'iv_atm_pe': round(self.iv_atm_pe, 2),
            'volume_ratio': round(self.volume_ratio, 2)
        }
    
    def update_price(self, new_price: float):
        """Update price and recalculate HV metrics"""
        self.price_history.append(new_price)
        
        # Keep only last 100 prices (for intraday HV)
        if len(self.price_history) > 100:
            self.price_history = self.price_history[-100:]
        
        self.current_price = new_price
        
        if len(self.price_history) >= 2:
            self._calculate_intraday_hv()
    
    def _calculate_intraday_hv(self):
        """Calculate intraday HV from price movements"""
        if len(self.price_history) < 10:
            return
        
        import math
        
        # Calculate returns
        returns = []
        for i in range(1, len(self.price_history)):
            if self.price_history[i-1] > 0:
                ret = (self.price_history[i] - self.price_history[i-1]) / self.price_history[i-1]
                returns.append(ret)
        
        if not returns:
            return
        
        # Calculate standard deviation of returns
        mean_return = sum(returns) / len(returns)
        variance = sum((r - mean_return) ** 2 for r in returns) / len(returns)
        std_dev = math.sqrt(variance)
        
        # Annualize (assuming 252 trading days, 375 min per day)
        # Scale by sqrt of periods
        self.hv_current = std_dev * math.sqrt(len(returns)) * 100


# ============================================================================
# POSITION DATA STRUCTURES
# ============================================================================

@dataclass
class EquityPosition:
    """Equity options position tracking"""
    position_id: str
    symbol: str               # RELIANCE, TCS, etc.
    option_type: str          # CE or PE
    strike: float
    expiry: str
    
    # Stock info
    sector: StockSector = StockSector.BANKING
    lot_size: int = 250
    
    # Position sizing
    probe_lots: int = 0
    scaled_lots: int = 0
    total_lots: int = 0
    
    # Prices
    probe_entry_price: float = 0.0
    scaled_entry_price: float = 0.0
    avg_entry_price: float = 0.0
    current_price: float = 0.0
    peak_price: float = 0.0
    
    # Underlying price
    underlying_entry_price: float = 0.0
    underlying_current_price: float = 0.0
    
    # Capital
    probe_capital: float = 0.0
    scaled_capital: float = 0.0
    total_capital: float = 0.0
    
    # Stoploss
    initial_stoploss: float = 0.0
    current_stoploss: float = 0.0
    trailing_activated: bool = False
    
    # PnL
    unrealized_pnl: float = 0.0
    unrealized_pnl_pct: float = 0.0
    peak_pnl: float = 0.0
    
    # State
    phase: TradePhase = TradePhase.SCANNING
    direction: TradeDirection = TradeDirection.NEUTRAL
    
    # HV data at entry
    entry_hv: float = 0.0
    current_hv: float = 0.0
    
    # AI
    gemini_confidence: float = 0.0
    gemini_recommendation: str = ""
    last_gemini_check: Optional[datetime] = None
    
    # Timestamps
    created_at: datetime = field(default_factory=datetime.now)
    probe_entry_time: Optional[datetime] = None
    scale_time: Optional[datetime] = None
    exit_time: Optional[datetime] = None
    exit_reason: Optional[ExitReason] = None
    
    def to_dict(self) -> Dict:
        return {
            'position_id': self.position_id,
            'symbol': self.symbol,
            'sector': self.sector.value,
            'option_type': self.option_type,
            'strike': self.strike,
            'expiry': self.expiry,
            'probe_lots': self.probe_lots,
            'scaled_lots': self.scaled_lots,
            'total_lots': self.total_lots,
            'avg_entry_price': self.avg_entry_price,
            'current_price': self.current_price,
            'underlying_current_price': self.underlying_current_price,
            'current_stoploss': self.current_stoploss,
            'trailing_activated': self.trailing_activated,
            'unrealized_pnl': round(self.unrealized_pnl, 2),
            'unrealized_pnl_pct': round(self.unrealized_pnl_pct, 2),
            'phase': self.phase.value,
            'direction': self.direction.value,
            'entry_hv': round(self.entry_hv, 2),
            'current_hv': round(self.current_hv, 2),
            'gemini_confidence': self.gemini_confidence,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


@dataclass
class EquityStats:
    """Daily equity trading statistics"""
    date: str = field(default_factory=lambda: date.today().isoformat())
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    total_pnl: float = 0.0
    max_drawdown: float = 0.0
    win_rate: float = 0.0
    probes_taken: int = 0
    probes_scaled: int = 0
    
    # Sector-wise stats
    banking_trades: int = 0
    it_trades: int = 0
    other_trades: int = 0
    
    # Best/worst by sector
    best_sector: str = ""
    best_sector_pnl: float = 0.0


# ============================================================================
# PAPER TRADE EXECUTOR
# ============================================================================

class PaperEquityExecutor:
    """Paper trading executor for equity options"""
    
    def __init__(self, config: EquityEngineConfig):
        self.config = config
        self.logger = logging.getLogger(__name__ + '.paper_executor')
        self.executed_orders: List[Dict] = []
        self.order_counter = 0
    
    async def execute_buy(
        self,
        symbol: str,
        option_type: str,
        strike: float,
        expiry: str,
        lots: int,
        price: float,
        lot_size: int
    ) -> Dict:
        """Simulate buy order execution"""
        await asyncio.sleep(self.config.paper_latency_ms / 1000)
        
        # Apply slippage (stock options have more spread)
        slippage = price * (self.config.paper_slippage_pct / 100)
        execution_price = price + slippage
        
        self.order_counter += 1
        order_id = f"EQ_BUY_{self.order_counter}_{datetime.now().strftime('%H%M%S')}"
        
        quantity = lots * lot_size
        value = execution_price * quantity
        
        order = {
            'order_id': order_id,
            'type': 'BUY',
            'symbol': symbol,
            'option_type': option_type,
            'strike': strike,
            'expiry': expiry,
            'lots': lots,
            'lot_size': lot_size,
            'quantity': quantity,
            'requested_price': price,
            'execution_price': execution_price,
            'slippage': slippage,
            'value': value,
            'status': 'FILLED',
            'mode': 'PAPER',
            'timestamp': datetime.now().isoformat()
        }
        
        self.executed_orders.append(order)
        
        self.logger.info(
            f"📄 EQ BUY: {symbol} {strike}{option_type} | "
            f"{lots} lots @ ₹{execution_price:.2f} | Value: ₹{value:,.2f}"
        )
        
        return order
    
    async def execute_sell(
        self,
        symbol: str,
        option_type: str,
        strike: float,
        expiry: str,
        lots: int,
        price: float,
        lot_size: int
    ) -> Dict:
        """Simulate sell order execution"""
        await asyncio.sleep(self.config.paper_latency_ms / 1000)
        
        slippage = price * (self.config.paper_slippage_pct / 100)
        execution_price = price - slippage
        
        self.order_counter += 1
        order_id = f"EQ_SELL_{self.order_counter}_{datetime.now().strftime('%H%M%S')}"
        
        quantity = lots * lot_size
        value = execution_price * quantity
        
        order = {
            'order_id': order_id,
            'type': 'SELL',
            'symbol': symbol,
            'option_type': option_type,
            'strike': strike,
            'expiry': expiry,
            'lots': lots,
            'lot_size': lot_size,
            'quantity': quantity,
            'requested_price': price,
            'execution_price': execution_price,
            'slippage': slippage,
            'value': value,
            'status': 'FILLED',
            'mode': 'PAPER',
            'timestamp': datetime.now().isoformat()
        }
        
        self.executed_orders.append(order)
        
        self.logger.info(
            f"📄 EQ SELL: {symbol} {strike}{option_type} | "
            f"{lots} lots @ ₹{execution_price:.2f} | Value: ₹{value:,.2f}"
        )
        
        return order


# ============================================================================
# LIVE TRADE EXECUTOR
# ============================================================================

class LiveEquityExecutor:
    """Live trading executor for equity options"""
    
    def __init__(self, config: EquityEngineConfig):
        self.config = config
        self.logger = logging.getLogger(__name__ + '.live_executor')
        self._session: Optional[aiohttp.ClientSession] = None
        
        self.dhan_token = os.getenv('DHAN_ACCESS_TOKEN', '')
        self.dhan_client_id = os.getenv('DHAN_CLIENT_ID', '')
        
        if not self.dhan_token:
            self.logger.warning("⚠️ DHAN_ACCESS_TOKEN not set - Live trading disabled")
    
    async def execute_buy(
        self,
        symbol: str,
        option_type: str,
        strike: float,
        expiry: str,
        lots: int,
        price: float,
        lot_size: int
    ) -> Dict:
        """Execute live buy order"""
        if not self.dhan_token:
            raise RuntimeError("Dhan API token not configured")
        
        quantity = lots * lot_size
        
        self.logger.info(
            f"🔴 LIVE EQ BUY: {symbol} {strike}{option_type} | "
            f"{lots} lots ({quantity} qty) @ ₹{price:.2f}"
        )
        
        # TODO: Implement Dhan API integration
        return {
            'order_id': f"LIVE_EQ_{datetime.now().strftime('%H%M%S')}",
            'status': 'PENDING',
            'mode': 'LIVE'
        }
    
    async def execute_sell(
        self,
        symbol: str,
        option_type: str,
        strike: float,
        expiry: str,
        lots: int,
        price: float,
        lot_size: int
    ) -> Dict:
        """Execute live sell order"""
        if not self.dhan_token:
            raise RuntimeError("Dhan API token not configured")
        
        quantity = lots * lot_size
        
        self.logger.info(
            f"🔴 LIVE EQ SELL: {symbol} {strike}{option_type} | "
            f"{lots} lots ({quantity} qty) @ ₹{price:.2f}"
        )
        
        return {
            'order_id': f"LIVE_EQ_{datetime.now().strftime('%H%M%S')}",
            'status': 'PENDING',
            'mode': 'LIVE'
        }
    
    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()


# ============================================================================
# GEMINI AI CLIENT FOR EQUITY
# ============================================================================

class EquityGeminiClient:
    """Gemini AI Client for stock options analysis"""
    
    def __init__(self, config: EquityEngineConfig):
        self.config = config
        self.logger = logging.getLogger(__name__ + '.gemini_client')
        self._session: Optional[aiohttp.ClientSession] = None
        self._healthy = False
        
        self.requests = 0
        self.successes = 0
        self.failures = 0
    
    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=30)
            )
        return self._session
    
    async def check_health(self) -> bool:
        """Check Gemini service health"""
        try:
            session = await self._get_session()
            async with session.get(
                f"{self.config.gemini_service_url}/health",
                timeout=5
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    self._healthy = data.get('status') == 'healthy'
                    return self._healthy
        except Exception as e:
            self.logger.warning(f"Gemini health check failed: {e}")
            self._healthy = False
        return False
    
    async def validate_equity_entry(
        self,
        symbol: str,
        direction: str,
        current_hv: float,
        price: float,
        sector: str,
        underlying_price: float
    ) -> Dict:
        """Validate equity options entry"""
        try:
            self.requests += 1
            session = await self._get_session()
            
            payload = {
                'symbol': symbol,
                'direction': direction,
                'historical_volatility': current_hv,
                'current_price': price,
                'sector': sector,
                'underlying_price': underlying_price,
                'trade_type': 'equity_option',
                'query_type': 'equity_entry_validation'
            }
            
            async with session.post(
                f"{self.config.gemini_service_url}/api/validate/trade",
                json=payload,
                timeout=15
            ) as resp:
                if resp.status == 200:
                    self.successes += 1
                    return await resp.json()
                else:
                    self.failures += 1
        except Exception as e:
            self.failures += 1
            self.logger.error(f"Equity validation error: {e}")
        
        return {'valid': False, 'confidence': 0.0, 'reason': 'Service unavailable'}
    
    async def get_scaling_decision(
        self,
        symbol: str,
        direction: str,
        entry_price: float,
        current_price: float,
        pnl_percent: float,
        current_hv: float,
        holding_seconds: int
    ) -> Dict:
        """Get scaling decision for equity position"""
        try:
            self.requests += 1
            session = await self._get_session()
            
            payload = {
                'symbol': symbol,
                'direction': direction,
                'entry_price': entry_price,
                'current_price': current_price,
                'pnl_percent': pnl_percent,
                'current_hv': current_hv,
                'holding_seconds': holding_seconds,
                'query_type': 'equity_scale_decision'
            }
            
            async with session.post(
                f"{self.config.gemini_service_url}/api/probe-scale/scale-decision",
                json=payload,
                timeout=15
            ) as resp:
                if resp.status == 200:
                    self.successes += 1
                    return await resp.json()
                else:
                    self.failures += 1
        except Exception as e:
            self.failures += 1
        
        return {'scale': False, 'confidence': 0.0, 'reason': 'Service unavailable'}
    
    async def get_exit_decision(
        self,
        symbol: str,
        direction: str,
        entry_price: float,
        current_price: float,
        pnl_percent: float,
        current_hv: float,
        entry_hv: float,
        holding_seconds: int,
        peak_pnl_percent: float
    ) -> Dict:
        """Get exit decision for equity position"""
        try:
            self.requests += 1
            session = await self._get_session()
            
            payload = {
                'symbol': symbol,
                'direction': direction,
                'entry_price': entry_price,
                'current_price': current_price,
                'pnl_percent': pnl_percent,
                'current_hv': current_hv,
                'entry_hv': entry_hv,
                'hv_change': current_hv - entry_hv,
                'holding_seconds': holding_seconds,
                'peak_pnl_percent': peak_pnl_percent,
                'query_type': 'equity_exit_decision'
            }
            
            async with session.post(
                f"{self.config.gemini_service_url}/api/probe-scale/exit-decision",
                json=payload,
                timeout=15
            ) as resp:
                if resp.status == 200:
                    self.successes += 1
                    return await resp.json()
                else:
                    self.failures += 1
        except Exception as e:
            self.failures += 1
        
        return {'exit': False, 'confidence': 0.0, 'reason': 'Service unavailable'}
    
    async def get_sector_analysis(self, sector: str) -> Dict:
        """Get sector momentum analysis"""
        try:
            self.requests += 1
            session = await self._get_session()
            
            async with session.get(
                f"{self.config.gemini_service_url}/api/sector/{sector}",
                timeout=10
            ) as resp:
                if resp.status == 200:
                    self.successes += 1
                    return await resp.json()
                else:
                    self.failures += 1
        except Exception as e:
            self.failures += 1
        
        return {'momentum': 'NEUTRAL', 'strength': 50}
    
    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()


# ============================================================================
# DATABASE MANAGER
# ============================================================================

class EquityDatabase:
    """SQLite database for equity trade history"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self._init_db()
    
    def _init_db(self):
        """Initialize database tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS equity_trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                position_id TEXT UNIQUE,
                symbol TEXT,
                sector TEXT,
                option_type TEXT,
                strike REAL,
                expiry TEXT,
                direction TEXT,
                
                probe_lots INTEGER,
                scaled_lots INTEGER,
                total_lots INTEGER,
                lot_size INTEGER,
                
                probe_entry_price REAL,
                scaled_entry_price REAL,
                avg_entry_price REAL,
                exit_price REAL,
                
                underlying_entry_price REAL,
                underlying_exit_price REAL,
                
                probe_capital REAL,
                scaled_capital REAL,
                total_capital REAL,
                
                realized_pnl REAL,
                realized_pnl_pct REAL,
                peak_pnl REAL,
                
                entry_hv REAL,
                exit_hv REAL,
                
                hold_duration_seconds INTEGER,
                phase TEXT,
                exit_reason TEXT,
                trading_mode TEXT,
                
                gemini_entry_confidence REAL,
                gemini_scale_confidence REAL,
                gemini_exit_confidence REAL,
                
                probe_entry_time TEXT,
                scale_time TEXT,
                exit_time TEXT,
                
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sector_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT,
                sector TEXT,
                total_trades INTEGER,
                winning_trades INTEGER,
                total_pnl REAL,
                UNIQUE(date, sector)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def save_trade(self, position: EquityPosition, exit_price: float, realized_pnl: float, hold_seconds: int):
        """Save completed equity trade"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO equity_trades (
                position_id, symbol, sector, option_type, strike, expiry, direction,
                probe_lots, scaled_lots, total_lots, lot_size,
                probe_entry_price, scaled_entry_price, avg_entry_price, exit_price,
                underlying_entry_price, underlying_exit_price,
                probe_capital, scaled_capital, total_capital,
                realized_pnl, realized_pnl_pct, peak_pnl,
                entry_hv, exit_hv,
                hold_duration_seconds, phase, exit_reason, trading_mode,
                gemini_entry_confidence, gemini_scale_confidence, gemini_exit_confidence,
                probe_entry_time, scale_time, exit_time
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            position.position_id, position.symbol, position.sector.value,
            position.option_type, position.strike, position.expiry, position.direction.value,
            position.probe_lots, position.scaled_lots, position.total_lots, position.lot_size,
            position.probe_entry_price, position.scaled_entry_price, position.avg_entry_price, exit_price,
            position.underlying_entry_price, position.underlying_current_price,
            position.probe_capital, position.scaled_capital, position.total_capital,
            realized_pnl, (realized_pnl / position.total_capital * 100) if position.total_capital > 0 else 0,
            position.peak_pnl,
            position.entry_hv, position.current_hv,
            hold_seconds, position.phase.value,
            position.exit_reason.value if position.exit_reason else None, "PAPER",
            position.gemini_confidence, 0, 0,
            position.probe_entry_time.isoformat() if position.probe_entry_time else None,
            position.scale_time.isoformat() if position.scale_time else None,
            datetime.now().isoformat()
        ))
        
        conn.commit()
        conn.close()
    
    def get_today_stats(self) -> Dict:
        """Get today's equity trading statistics"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        today = date.today().isoformat()
        
        cursor.execute('''
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN realized_pnl > 0 THEN 1 ELSE 0 END) as wins,
                SUM(CASE WHEN realized_pnl <= 0 THEN 1 ELSE 0 END) as losses,
                COALESCE(SUM(realized_pnl), 0) as total_pnl,
                AVG(hold_duration_seconds) as avg_hold
            FROM equity_trades
            WHERE DATE(exit_time) = ?
        ''', (today,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            total = row[0] or 0
            wins = row[1] or 0
            return {
                'total_trades': total,
                'winning_trades': wins,
                'losing_trades': row[2] or 0,
                'total_pnl': row[3] or 0,
                'win_rate': (wins / total * 100) if total > 0 else 0,
                'avg_hold_seconds': row[4] or 0
            }
        
        return {'total_trades': 0, 'winning_trades': 0, 'losing_trades': 0, 'total_pnl': 0, 'win_rate': 0}


# ============================================================================
# PRODUCTION EQUITY ENGINE
# ============================================================================

class ProductionEquityEngine:
    """
    Production Trading Engine for Equity HV Service
    
    Implements:
    - HV-based entry analysis for F&O stocks
    - Probe-scale methodology with Gemini AI validation
    - 50-point trailing after 50-point profit
    - Sector rotation awareness
    - Multiple concurrent positions (up to 3)
    """
    
    def __init__(self, config: Optional[EquityEngineConfig] = None):
        self.config = config or EquityEngineConfig()
        self.logger = logging.getLogger(__name__ + '.engine')
        
        # Trading mode
        self._trading_mode = self.config.trading_mode
        
        # Executors
        self.paper_executor = PaperEquityExecutor(self.config)
        self.live_executor = LiveEquityExecutor(self.config)
        
        # AI Client
        self.gemini_client = EquityGeminiClient(self.config)
        
        # Database
        self.database = EquityDatabase(self.config.db_path)
        
        # HV tracking for all elite stocks
        self.hv_data: Dict[str, StockHVData] = {
            symbol: StockHVData(symbol=symbol) for symbol in ELITE_STOCKS.keys()
        }
        
        # Positions (multiple allowed for equity)
        self.active_positions: Dict[str, EquityPosition] = {}
        self.closed_positions: List[EquityPosition] = []
        
        # Statistics
        self.stats = EquityStats()
        
        # State
        self._running = False
        self._monitoring_task: Optional[asyncio.Task] = None
        
        self.logger.info(
            f"🚀 Production Equity Engine initialized | "
            f"Mode: {self._trading_mode.value} | "
            f"Capital: ₹{self.config.total_capital:,.2f} | "
            f"Elite Stocks: {len(ELITE_STOCKS)}"
        )
    
    @property
    def trading_mode(self) -> TradingMode:
        return self._trading_mode
    
    @property
    def executor(self):
        """Get current executor based on trading mode"""
        if self._trading_mode == TradingMode.LIVE:
            return self.live_executor
        return self.paper_executor
    
    def switch_mode(self, mode: TradingMode) -> Dict:
        """Switch trading mode between PAPER and LIVE"""
        old_mode = self._trading_mode
        
        if mode == TradingMode.LIVE:
            if not os.getenv('DHAN_ACCESS_TOKEN'):
                return {
                    'success': False,
                    'error': 'Cannot switch to LIVE mode - DHAN_ACCESS_TOKEN not configured'
                }
            
            if len(self.active_positions) > 0:
                return {
                    'success': False,
                    'error': 'Cannot switch to LIVE mode with active positions'
                }
        
        self._trading_mode = mode
        
        self.logger.info(f"⚡ Trading mode switched: {old_mode.value} → {mode.value}")
        
        return {
            'success': True,
            'old_mode': old_mode.value,
            'new_mode': mode.value,
            'timestamp': datetime.now().isoformat()
        }
    
    async def start(self):
        """Start the equity engine"""
        if self._running:
            return
        
        self._running = True
        
        gemini_healthy = await self.gemini_client.check_health()
        self.logger.info(f"🤖 Gemini AI Status: {'Healthy' if gemini_healthy else 'Unavailable'}")
        
        self._monitoring_task = asyncio.create_task(self._position_monitor_loop())
        
        self.logger.info("✅ Production Equity Engine started")
    
    async def stop(self):
        """Stop the equity engine"""
        self._running = False
        
        if self._monitoring_task:
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass
        
        await self.gemini_client.close()
        await self.live_executor.close()
        
        self.logger.info("🛑 Production Equity Engine stopped")
    
    async def _position_monitor_loop(self):
        """Monitor all active positions"""
        while self._running:
            try:
                for position_id, position in list(self.active_positions.items()):
                    await self._monitor_position(position)
                await asyncio.sleep(self.config.gemini_check_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Position monitor error: {e}")
                await asyncio.sleep(5)
    
    async def _monitor_position(self, position: EquityPosition):
        """Monitor single equity position"""
        if position.phase == TradePhase.CLOSED:
            return
        
        # Update PnL
        self._update_position_pnl(position)
        
        # Update HV
        hv_data = self.hv_data.get(position.symbol)
        if hv_data:
            position.current_hv = hv_data.hv_current
        
        holding_seconds = (datetime.now() - position.probe_entry_time).total_seconds() if position.probe_entry_time else 0
        
        # Check trailing stop
        if self._check_trailing_stop(position):
            await self._exit_position(position, ExitReason.TRAILING_STOP)
            return
        
        # Check stoploss
        if self._check_stoploss(position):
            await self._exit_position(position, ExitReason.STOPLOSS)
            return
        
        # Check HV collapse (volatility crush)
        if position.current_hv < position.entry_hv * 0.5:  # HV dropped by 50%
            await self._exit_position(position, ExitReason.HV_COLLAPSE)
            return
        
        # Check max holding time
        if holding_seconds >= self.config.max_position_minutes * 60:
            await self._exit_position(position, ExitReason.TIME_EXIT)
            return
        
        # Get Gemini exit decision
        exit_decision = await self.gemini_client.get_exit_decision(
            symbol=position.symbol,
            direction=position.direction.value,
            entry_price=position.avg_entry_price,
            current_price=position.current_price,
            pnl_percent=position.unrealized_pnl_pct,
            current_hv=position.current_hv,
            entry_hv=position.entry_hv,
            holding_seconds=int(holding_seconds),
            peak_pnl_percent=(position.peak_pnl / position.total_capital * 100) if position.total_capital > 0 else 0
        )
        
        if exit_decision.get('exit', False) and exit_decision.get('confidence', 0) >= self.config.min_gemini_confidence:
            await self._exit_position(position, ExitReason.GEMINI_EXIT)
            return
        
        # Check scaling opportunity
        if position.phase == TradePhase.PROBE and position.unrealized_pnl_pct >= self.config.min_profit_to_scale_pct:
            scale_decision = await self.gemini_client.get_scaling_decision(
                symbol=position.symbol,
                direction=position.direction.value,
                entry_price=position.probe_entry_price,
                current_price=position.current_price,
                pnl_percent=position.unrealized_pnl_pct,
                current_hv=position.current_hv,
                holding_seconds=int(holding_seconds)
            )
            
            if scale_decision.get('scale', False) and scale_decision.get('confidence', 0) >= self.config.min_gemini_confidence:
                await self._scale_position(position)
    
    def _update_position_pnl(self, position: EquityPosition):
        """Update position PnL calculations"""
        if position.total_lots == 0 or position.avg_entry_price == 0:
            return
        
        price_diff = position.current_price - position.avg_entry_price
        
        position.unrealized_pnl = price_diff * position.total_lots * position.lot_size
        position.unrealized_pnl_pct = (price_diff / position.avg_entry_price) * 100
        
        if position.unrealized_pnl > position.peak_pnl:
            position.peak_pnl = position.unrealized_pnl
        
        if position.current_price > position.peak_price:
            position.peak_price = position.current_price
    
    def _check_trailing_stop(self, position: EquityPosition) -> bool:
        """Check trailing stop (50-point trailing after 50-point profit)"""
        if not position.trailing_activated:
            profit_points = position.current_price - position.avg_entry_price
            if profit_points >= self.config.trailing_activation_points:
                position.trailing_activated = True
                position.current_stoploss = position.current_price - self.config.trailing_distance_points
                self.logger.info(
                    f"📈 Trailing activated for {position.symbol} | "
                    f"Trail at ₹{position.current_stoploss:.2f}"
                )
        else:
            new_trailing_stop = position.peak_price - self.config.trailing_distance_points
            if new_trailing_stop > position.current_stoploss:
                position.current_stoploss = new_trailing_stop
            
            if position.current_price <= position.current_stoploss:
                return True
        
        return False
    
    def _check_stoploss(self, position: EquityPosition) -> bool:
        """Check if stoploss is hit"""
        stoploss_pct = self.config.probe_stoploss_pct if position.phase == TradePhase.PROBE else self.config.scaled_stoploss_pct
        loss_pct = ((position.avg_entry_price - position.current_price) / position.avg_entry_price) * 100
        
        return loss_pct >= stoploss_pct
    
    async def enter_equity_probe(
        self,
        symbol: str,
        direction: TradeDirection,
        strike: float,
        option_type: str,
        expiry: str,
        option_price: float,
        underlying_price: float
    ) -> Optional[EquityPosition]:
        """Enter equity options probe position"""
        if len(self.active_positions) >= self.config.max_concurrent_positions:
            self.logger.warning("Max concurrent positions reached")
            return None
        
        # Get stock info
        stock_info = ELITE_STOCKS.get(symbol)
        if not stock_info:
            self.logger.warning(f"Unknown stock: {symbol}")
            return None
        
        # Check HV
        hv_data = self.hv_data.get(symbol)
        current_hv = hv_data.hv_current if hv_data else 0
        
        if current_hv < self.config.min_hv_for_entry:
            self.logger.warning(f"HV too low for {symbol}: {current_hv:.1f}%")
            return None
        
        if current_hv > self.config.max_hv_for_entry:
            self.logger.warning(f"HV too high for {symbol}: {current_hv:.1f}%")
            return None
        
        # Validate with Gemini
        validation = await self.gemini_client.validate_equity_entry(
            symbol=symbol,
            direction=direction.value,
            current_hv=current_hv,
            price=option_price,
            sector=stock_info.sector.value,
            underlying_price=underlying_price
        )
        
        if not validation.get('valid', False):
            self.logger.info(f"❌ Equity entry rejected by Gemini")
            return None
        
        # Calculate probe size
        probe_capital = self.config.total_capital * (self.config.probe_capital_pct / 100)
        lot_size = stock_info.lot_size
        probe_lots = max(1, int(probe_capital / (option_price * lot_size)))
        
        position_id = f"EQ_{symbol}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
        
        position = EquityPosition(
            position_id=position_id,
            symbol=symbol,
            option_type=option_type,
            strike=strike,
            expiry=expiry,
            sector=stock_info.sector,
            lot_size=lot_size,
            probe_lots=probe_lots,
            total_lots=probe_lots,
            direction=direction,
            entry_hv=current_hv,
            current_hv=current_hv,
            underlying_entry_price=underlying_price,
            underlying_current_price=underlying_price,
            gemini_confidence=validation.get('confidence', 0)
        )
        
        # Execute probe entry
        order = await self.executor.execute_buy(
            symbol=symbol,
            option_type=option_type,
            strike=strike,
            expiry=expiry,
            lots=probe_lots,
            price=option_price,
            lot_size=lot_size
        )
        
        position.probe_entry_price = order['execution_price']
        position.avg_entry_price = order['execution_price']
        position.current_price = order['execution_price']
        position.peak_price = order['execution_price']
        position.probe_capital = order['value']
        position.total_capital = order['value']
        position.probe_entry_time = datetime.now()
        position.phase = TradePhase.PROBE
        
        # Set initial stoploss (50% of premium)
        position.initial_stoploss = position.probe_entry_price * (1 - self.config.probe_stoploss_pct / 100)
        position.current_stoploss = position.initial_stoploss
        
        self.active_positions[position_id] = position
        self.stats.probes_taken += 1
        
        # Update sector stats
        if stock_info.sector == StockSector.BANKING:
            self.stats.banking_trades += 1
        elif stock_info.sector == StockSector.IT:
            self.stats.it_trades += 1
        else:
            self.stats.other_trades += 1
        
        self.logger.info(
            f"✅ EQUITY PROBE: {symbol} {strike}{option_type} | "
            f"{probe_lots} lots @ ₹{position.probe_entry_price:.2f} | "
            f"HV: {current_hv:.1f}% | Sector: {stock_info.sector.value}"
        )
        
        return position
    
    async def _scale_position(self, position: EquityPosition):
        """Scale up equity position"""
        if position.phase != TradePhase.PROBE:
            return
        
        scale_capital = self.config.total_capital * (self.config.scale_capital_pct / 100)
        lot_size = position.lot_size
        scale_lots = max(1, int(scale_capital / (position.current_price * lot_size)))
        
        order = await self.executor.execute_buy(
            symbol=position.symbol,
            option_type=position.option_type,
            strike=position.strike,
            expiry=position.expiry,
            lots=scale_lots,
            price=position.current_price,
            lot_size=lot_size
        )
        
        position.scaled_lots = scale_lots
        position.scaled_entry_price = order['execution_price']
        position.total_lots = position.probe_lots + position.scaled_lots
        position.scaled_capital = order['value']
        position.total_capital = position.probe_capital + position.scaled_capital
        
        total_value = (position.probe_entry_price * position.probe_lots + 
                       position.scaled_entry_price * position.scaled_lots)
        position.avg_entry_price = total_value / position.total_lots
        
        position.current_stoploss = position.avg_entry_price * (1 - self.config.scaled_stoploss_pct / 100)
        position.phase = TradePhase.FULL_POSITION
        position.scale_time = datetime.now()
        
        self.stats.probes_scaled += 1
        
        self.logger.info(
            f"📈 EQUITY SCALED: {position.symbol} | Added {scale_lots} lots | "
            f"Total: {position.total_lots} lots @ ₹{position.avg_entry_price:.2f}"
        )
    
    async def _exit_position(self, position: EquityPosition, reason: ExitReason):
        """Exit equity position"""
        if position.phase == TradePhase.CLOSED:
            return
        
        order = await self.executor.execute_sell(
            symbol=position.symbol,
            option_type=position.option_type,
            strike=position.strike,
            expiry=position.expiry,
            lots=position.total_lots,
            price=position.current_price,
            lot_size=position.lot_size
        )
        
        exit_price = order['execution_price']
        price_diff = exit_price - position.avg_entry_price
        realized_pnl = price_diff * position.total_lots * position.lot_size
        
        hold_seconds = int((datetime.now() - position.probe_entry_time).total_seconds()) if position.probe_entry_time else 0
        
        position.exit_time = datetime.now()
        position.exit_reason = reason
        position.phase = TradePhase.CLOSED
        
        self.database.save_trade(position, exit_price, realized_pnl, hold_seconds)
        
        # Update stats
        self.stats.total_trades += 1
        if realized_pnl > 0:
            self.stats.winning_trades += 1
        else:
            self.stats.losing_trades += 1
        
        self.stats.total_pnl += realized_pnl
        self.stats.win_rate = (self.stats.winning_trades / self.stats.total_trades * 100) if self.stats.total_trades > 0 else 0
        
        # Remove from active positions
        if position.position_id in self.active_positions:
            del self.active_positions[position.position_id]
        
        self.closed_positions.append(position)
        
        emoji = "🟢" if realized_pnl > 0 else "🔴"
        self.logger.info(
            f"{emoji} EQUITY EXIT: {position.symbol} | "
            f"PnL: ₹{realized_pnl:+,.2f} ({position.unrealized_pnl_pct:+.2f}%) | "
            f"Hold: {hold_seconds}s | Reason: {reason.value}"
        )
    
    def update_stock_price(self, symbol: str, price: float, volume: int = 0):
        """Update stock price and recalculate HV"""
        if symbol in self.hv_data:
            self.hv_data[symbol].update_price(price)
            self.hv_data[symbol].volume = volume
        
        # Update active positions
        for position in self.active_positions.values():
            if position.symbol == symbol:
                position.underlying_current_price = price
    
    def update_option_price(self, symbol: str, option_type: str, strike: float, price: float):
        """Update option price for matching positions"""
        for position in self.active_positions.values():
            if (position.symbol == symbol and 
                position.option_type == option_type and 
                position.strike == strike):
                position.current_price = price
    
    def get_elite_stocks(self) -> List[Dict]:
        """Get list of elite stocks with current HV"""
        result = []
        for symbol, stock in ELITE_STOCKS.items():
            hv_data = self.hv_data.get(symbol)
            result.append({
                **stock.to_dict(),
                'current_hv': hv_data.hv_current if hv_data else 0,
                'current_price': hv_data.current_price if hv_data else 0
            })
        return result
    
    def get_status(self) -> Dict:
        """Get engine status"""
        return {
            'service': self.config.service_name,
            'trading_mode': self._trading_mode.value,
            'running': self._running,
            'active_positions': len(self.active_positions),
            'positions': [p.to_dict() for p in self.active_positions.values()],
            'elite_stocks': len(ELITE_STOCKS),
            'hv_data': {s: h.to_dict() for s, h in self.hv_data.items()},
            'stats': {
                'total_trades': self.stats.total_trades,
                'winning_trades': self.stats.winning_trades,
                'losing_trades': self.stats.losing_trades,
                'win_rate': round(self.stats.win_rate, 2),
                'total_pnl': round(self.stats.total_pnl, 2),
                'probes_taken': self.stats.probes_taken,
                'probes_scaled': self.stats.probes_scaled,
                'banking_trades': self.stats.banking_trades,
                'it_trades': self.stats.it_trades
            },
            'config': {
                'total_capital': self.config.total_capital,
                'max_concurrent_positions': self.config.max_concurrent_positions,
                'probe_capital_pct': self.config.probe_capital_pct,
                'trailing_activation_points': self.config.trailing_activation_points,
                'min_hv_for_entry': self.config.min_hv_for_entry,
                'max_hv_for_entry': self.config.max_hv_for_entry
            },
            'gemini': {
                'healthy': self.gemini_client._healthy,
                'requests': self.gemini_client.requests,
                'successes': self.gemini_client.successes,
                'failures': self.gemini_client.failures
            },
            'timestamp': datetime.now().isoformat()
        }


# ============================================================================
# FACTORY FUNCTION
# ============================================================================

def create_equity_engine(config: Optional[EquityEngineConfig] = None) -> ProductionEquityEngine:
    """Factory function to create equity engine"""
    return ProductionEquityEngine(config)


# ============================================================================
# STANDALONE TESTING
# ============================================================================

if __name__ == "__main__":
    import asyncio
    
    async def test_engine():
        """Test the equity engine"""
        engine = create_equity_engine()
        
        await engine.start()
        
        print(f"Engine Status: {json.dumps(engine.get_status(), indent=2)}")
        
        # Simulate price updates
        for stock in ["RELIANCE", "TCS", "HDFCBANK"]:
            for i in range(20):
                price = 1000 + i * 10
                engine.update_stock_price(stock, price, volume=100000)
        
        print(f"\nHV Data:")
        for symbol, hv in engine.hv_data.items():
            print(f"  {symbol}: HV={hv.hv_current:.2f}%, Price=₹{hv.current_price:.2f}")
        
        await engine.stop()
        
        print("\n✅ Equity engine test complete")
    
    asyncio.run(test_engine())
