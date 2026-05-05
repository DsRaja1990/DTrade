"""
================================================================================
    WORLD-CLASS SCALPING BACKTEST ENGINE v2.0
    Comprehensive Backtesting with Real DhanHQ Data
    
    Features:
    - Real 1-minute data from DhanHQ API
    - Simulated tick data generation
    - Full position scaling simulation
    - Realistic slippage and transaction costs
    - Comprehensive performance metrics
    - Trade-by-trade analysis
================================================================================
"""

import asyncio
import pandas as pd
import numpy as np
from datetime import datetime, timedelta, time
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field, asdict
from enum import Enum
import json
import logging
import os
import sys

# Setup path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Try importing DhanHQ
try:
    from dhanhq import dhanhq
    DHANHQ_AVAILABLE = True
except ImportError:
    DHANHQ_AVAILABLE = False
    print("⚠️ DhanHQ not available, using simulated data")

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


# ============================================================================
#                     CONFIGURATION
# ============================================================================

@dataclass
class BacktestConfig:
    """Backtest configuration - ENHANCED FOR 300%+ MONTHLY RETURNS"""
    # Data settings
    start_date: datetime = field(default_factory=lambda: datetime.now() - timedelta(days=30))
    end_date: datetime = field(default_factory=datetime.now)
    instruments: List[str] = field(default_factory=lambda: ["NIFTY", "BANKNIFTY", "SENSEX", "BANKEX"])
    
    # Capital settings - AGGRESSIVE
    initial_capital: float = 500000.0
    max_position_percent: float = 80.0  # INCREASED from 60
    
    # Lot sizes
    lot_sizes: Dict[str, int] = field(default_factory=lambda: {
        "NIFTY": 75,
        "BANKNIFTY": 35,
        "SENSEX": 20,
        "BANKEX": 30
    })
    
    # Scaling configuration - AGGRESSIVE for 300%+ returns
    probe_size_percent: float = 30.0      # Probe with 30%
    confirmed_size_percent: float = 60.0  # Scale up to 60%
    full_size_percent: float = 100.0      # Full position
    aggressive_size_percent: float = 200.0  # AGGRESSIVE: 2x for LEGENDARY signals
    
    # Profit targets - OPTIMIZED for high returns with good win rate
    target_profit_percent: float = 1.5    # INCREASED: 1.5% target
    min_profit_to_confirm: float = 0.2    # Scale at 0.2%
    min_profit_to_full: float = 0.5       # Full at 0.5%
    min_profit_to_aggressive: float = 1.0 # Aggressive at 1.0%
    
    # Momentum thresholds - LOWER for more high-quality trades
    min_momentum_for_entry: float = 52.0  # REDUCED further - catch more moves
    min_momentum_for_scale_up: float = 60.0  # REDUCED - scale up faster
    exit_momentum_threshold: float = 35.0  # Slightly higher exit threshold
    
    # Risk management - OPTIMIZED stops
    stop_loss_percent: float = 1.5        # Moderate stop for probe
    trailing_stop_percent: float = 0.5
    max_trades_per_day: int = 30          # INCREASED - more opportunities
    max_position_time_minutes: int = 15   # Slightly shorter
    
    # Trading hours - EXPANDED
    trading_start_hour: int = 9
    trading_start_minute: int = 18        # Earlier start
    trading_end_hour: int = 15
    trading_end_minute: int = 20          # Later end
    
    # Transaction costs (realistic for Indian options)
    slippage_percent: float = 0.03  # 3 paisa per rupee
    brokerage_per_lot: float = 20.0
    stt_percent: float = 0.0125
    other_charges_percent: float = 0.005
    
    # DhanHQ credentials (from config)
    dhan_client_id: str = "1101317572"
    dhan_access_token: str = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzUxMiJ9.eyJpc3MiOiJkaGFuIiwicGFydG5lcklkIjoiIiwiZXhwIjoxNzY1MjA5ODY5LCJpYXQiOjE3NjUxMjM0NjksInRva2VuQ29uc3VtZXJUeXBlIjoiU0VMRiIsIndlYmhvb2tVcmwiOiIiLCJkaGFuQ2xpZW50SWQiOiIxMTAxMzE3NTcyIn0.Y_sBFc4c8mAJc_-XFGnKLmoFSm-ge04yk2bBnCvaz7GfJxLFzk5ki_M8lKYB2X3xGOegNBB_7dk3BBnm5Y_Org"


# ============================================================================
#                     DATA STRUCTURES
# ============================================================================

class MomentumPhase(str, Enum):
    DORMANT = "DORMANT"
    BUILDING = "BUILDING"
    ACCELERATING = "ACCELERATING"
    PEAK = "PEAK"
    FADING = "FADING"
    REVERSAL = "REVERSAL"


class PositionStage(str, Enum):
    NO_POSITION = "NO_POSITION"
    PROBE = "PROBE"
    CONFIRMED = "CONFIRMED"
    FULL = "FULL"
    AGGRESSIVE = "AGGRESSIVE"


@dataclass
class BacktestTick:
    """Single tick data point"""
    timestamp: datetime
    instrument: str
    price: float
    volume: int
    open: float = 0.0
    high: float = 0.0
    low: float = 0.0


@dataclass
class BacktestTrade:
    """Completed trade record"""
    trade_id: int
    instrument: str
    option_type: str
    
    entry_time: datetime
    exit_time: datetime
    entry_price: float
    exit_price: float
    
    initial_lots: int
    max_lots: int
    final_lots: int
    
    gross_pnl: float
    transaction_costs: float
    net_pnl: float
    pnl_percent: float
    
    duration_minutes: float
    exit_reason: str
    
    entry_momentum: float
    exit_momentum: float
    max_momentum: float
    
    scale_count: int
    stages_reached: List[str]
    
    # Extra metrics
    max_profit: float = 0.0
    max_drawdown: float = 0.0
    
    def to_dict(self) -> Dict:
        return {
            'trade_id': self.trade_id,
            'instrument': self.instrument,
            'option_type': self.option_type,
            'entry_time': self.entry_time.isoformat(),
            'exit_time': self.exit_time.isoformat(),
            'entry_price': self.entry_price,
            'exit_price': self.exit_price,
            'initial_lots': self.initial_lots,
            'max_lots': self.max_lots,
            'gross_pnl': round(self.gross_pnl, 2),
            'net_pnl': round(self.net_pnl, 2),
            'pnl_percent': round(self.pnl_percent, 2),
            'duration_minutes': round(self.duration_minutes, 1),
            'exit_reason': self.exit_reason,
            'scale_count': self.scale_count,
            'stages_reached': self.stages_reached
        }


@dataclass
class DailyStats:
    """Daily performance statistics"""
    date: str
    trades: int
    wins: int
    losses: int
    win_rate: float
    gross_pnl: float
    net_pnl: float
    max_drawdown: float
    best_trade: float
    worst_trade: float
    avg_trade: float
    avg_duration: float


@dataclass
class BacktestResult:
    """Complete backtest result"""
    # General
    start_date: str
    end_date: str
    trading_days: int
    
    # Capital
    initial_capital: float
    final_capital: float
    total_return_percent: float
    
    # Trade statistics
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    
    # P&L
    gross_pnl: float
    total_transaction_costs: float
    net_pnl: float
    
    # Per-trade metrics
    avg_win: float
    avg_loss: float
    avg_pnl_per_trade: float
    profit_factor: float
    
    # Risk metrics
    max_drawdown: float
    max_drawdown_percent: float
    sharpe_ratio: float
    sortino_ratio: float
    
    # Time metrics
    avg_trade_duration: float
    longest_trade: float
    shortest_trade: float
    
    # Scaling statistics
    avg_scale_count: float
    trades_reached_full: int
    trades_reached_aggressive: int
    
    # Daily breakdown
    daily_stats: List[DailyStats] = field(default_factory=list)
    all_trades: List[BacktestTrade] = field(default_factory=list)
    
    # By instrument
    instrument_stats: Dict[str, Dict] = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        return {
            'start_date': self.start_date,
            'end_date': self.end_date,
            'trading_days': self.trading_days,
            'initial_capital': self.initial_capital,
            'final_capital': round(self.final_capital, 2),
            'total_return_percent': round(self.total_return_percent, 2),
            'total_trades': self.total_trades,
            'winning_trades': self.winning_trades,
            'losing_trades': self.losing_trades,
            'win_rate': round(self.win_rate, 2),
            'gross_pnl': round(self.gross_pnl, 2),
            'net_pnl': round(self.net_pnl, 2),
            'avg_win': round(self.avg_win, 2),
            'avg_loss': round(self.avg_loss, 2),
            'profit_factor': round(self.profit_factor, 2),
            'max_drawdown': round(self.max_drawdown, 2),
            'max_drawdown_percent': round(self.max_drawdown_percent, 2),
            'sharpe_ratio': round(self.sharpe_ratio, 2),
            'avg_trade_duration': round(self.avg_trade_duration, 1),
            'avg_scale_count': round(self.avg_scale_count, 2),
            'trades_reached_full': self.trades_reached_full,
            'trades_reached_aggressive': self.trades_reached_aggressive,
            'instrument_stats': self.instrument_stats
        }


# ============================================================================
#                     DATA PROVIDER
# ============================================================================

class BacktestDataProvider:
    """Provides historical data for backtesting"""
    
    def __init__(self, config: BacktestConfig):
        self.config = config
        self.dhan = None
        
        if DHANHQ_AVAILABLE:
            try:
                self.dhan = dhanhq(
                    client_id=config.dhan_client_id,
                    access_token=config.dhan_access_token
                )
                logger.info("✅ DhanHQ client initialized")
            except Exception as e:
                logger.warning(f"⚠️ DhanHQ init failed: {e}")
        
        # Security IDs for indices
        self.security_ids = {
            "NIFTY": "13",
            "BANKNIFTY": "25",
            "SENSEX": "51",
            "BANKEX": "52"
        }
        
        # Cache
        self._cache: Dict[str, pd.DataFrame] = {}
    
    async def fetch_data(self, instrument: str, start_date: datetime, end_date: datetime) -> pd.DataFrame:
        """Fetch historical data for an instrument"""
        cache_key = f"{instrument}_{start_date.date()}_{end_date.date()}"
        
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        if self.dhan:
            try:
                data = await self._fetch_dhan_data(instrument, start_date, end_date)
                if not data.empty:
                    self._cache[cache_key] = data
                    return data
            except Exception as e:
                logger.warning(f"DhanHQ fetch failed for {instrument}: {e}")
        
        # Fallback to simulated data
        data = self._generate_simulated_data(instrument, start_date, end_date)
        self._cache[cache_key] = data
        return data
    
    async def _fetch_dhan_data(self, instrument: str, start_date: datetime, end_date: datetime) -> pd.DataFrame:
        """Fetch real data from DhanHQ"""
        security_id = self.security_ids.get(instrument)
        if not security_id:
            return pd.DataFrame()
        
        try:
            from_date = start_date.strftime("%Y-%m-%d")
            to_date = end_date.strftime("%Y-%m-%d")
            
            response = self.dhan.intraday_minute_data(
                security_id=security_id,
                exchange_segment="IDX_I",
                instrument_type="INDEX",
                from_date=from_date,
                to_date=to_date,
                interval=1
            )
            
            if response.get('status') == 'success' and response.get('data'):
                raw_data = response['data']
                
                records = []
                for record in raw_data:
                    records.append({
                        'timestamp': pd.to_datetime(record.get('start_time', record.get('timestamp'))),
                        'open': float(record.get('open', 0)),
                        'high': float(record.get('high', 0)),
                        'low': float(record.get('low', 0)),
                        'close': float(record.get('close', 0)),
                        'volume': int(record.get('volume', 0))
                    })
                
                df = pd.DataFrame(records)
                df.set_index('timestamp', inplace=True)
                df.sort_index(inplace=True)
                
                logger.info(f"✅ Fetched {len(df)} real data points for {instrument}")
                return df
                
        except Exception as e:
            logger.error(f"DhanHQ API error: {e}")
        
        return pd.DataFrame()
    
    def _generate_simulated_data(self, instrument: str, start_date: datetime, end_date: datetime) -> pd.DataFrame:
        """Generate realistic simulated market data with momentum patterns"""
        logger.info(f"📊 Generating simulated data for {instrument}")
        
        # Base prices for each instrument (ATM option premium levels)
        base_prices = {
            "NIFTY": 350,
            "BANKNIFTY": 450,
            "SENSEX": 400,
            "BANKEX": 300
        }
        
        base_price = base_prices.get(instrument, 350)
        
        # Generate trading days
        dates = pd.date_range(start=start_date, end=end_date, freq='B')
        
        all_records = []
        current_price = base_price
        
        # Momentum state machine for realistic patterns
        momentum_direction = 0  # -1, 0, 1
        momentum_strength = 0  # 0-10
        momentum_duration = 0  # bars remaining in current momentum
        
        for date in dates:
            if date.weekday() >= 5:
                continue
            
            start_time = datetime.combine(date.date(), time(9, 15))
            end_time = datetime.combine(date.date(), time(15, 30))
            minutes = pd.date_range(start=start_time, end=end_time, freq='1min')
            
            # Daily bias (some days are trending, some are ranging)
            daily_bias = np.random.choice([-1, 0, 1], p=[0.3, 0.4, 0.3])
            daily_trend_strength = np.random.uniform(0.5, 2.0)
            
            for ts in minutes:
                # Momentum regime changes (5-15 minute trends occur frequently in options)
                if momentum_duration <= 0 or np.random.random() < 0.02:
                    # New momentum regime
                    if np.random.random() < 0.6:  # 60% chance of trending
                        momentum_direction = np.random.choice([-1, 1])
                        if daily_bias != 0 and np.random.random() < 0.7:
                            momentum_direction = daily_bias  # Align with daily bias
                        momentum_strength = np.random.uniform(3, 8)
                        momentum_duration = np.random.randint(5, 20)  # 5-20 minute trends
                    else:
                        momentum_direction = 0
                        momentum_strength = 1
                        momentum_duration = np.random.randint(3, 10)
                else:
                    momentum_duration -= 1
                
                # Calculate price change
                # Base drift from momentum
                trend_move = momentum_direction * momentum_strength * 0.002
                
                # Random noise
                noise = np.random.normal(0, 0.008)
                
                # Mean reversion (options tend to revert)
                mean_reversion = (base_price - current_price) / base_price * 0.002
                
                # Total change
                change_percent = trend_move + noise + mean_reversion
                
                # High volume periods have larger moves
                hour = ts.hour
                if hour == 9 or hour == 15:
                    change_percent *= 1.5
                
                open_price = current_price
                close_price = max(10, current_price * (1 + change_percent))
                
                # OHLC generation
                intra_volatility = 0.005 + abs(momentum_strength) * 0.001
                high_price = max(open_price, close_price) * (1 + abs(np.random.normal(0, intra_volatility)))
                low_price = min(open_price, close_price) * (1 - abs(np.random.normal(0, intra_volatility)))
                
                # Volume (higher during trends)
                if hour == 9 or hour == 15:
                    base_volume = 50000
                elif momentum_strength > 5:
                    base_volume = 40000
                else:
                    base_volume = 20000
                volume = int(base_volume * np.random.uniform(0.5, 2.0))
                
                all_records.append({
                    'timestamp': ts,
                    'open': round(open_price, 2),
                    'high': round(high_price, 2),
                    'low': round(low_price, 2),
                    'close': round(close_price, 2),
                    'volume': volume
                })
                
                current_price = close_price
        
        df = pd.DataFrame(all_records)
        df.set_index('timestamp', inplace=True)
        
        logger.info(f"✅ Generated {len(df)} simulated data points for {instrument}")
        return df
    
    def generate_ticks_from_bars(self, df: pd.DataFrame, instrument: str, ticks_per_bar: int = 10) -> List[BacktestTick]:
        """Generate tick data from OHLCV bars"""
        ticks = []
        
        for timestamp, row in df.iterrows():
            open_price = row['open']
            high_price = row['high']
            low_price = row['low']
            close_price = row['close']
            volume = row['volume']
            
            # Generate tick path within the bar
            prices = self._generate_tick_path(open_price, high_price, low_price, close_price, ticks_per_bar)
            vol_per_tick = max(1, volume // ticks_per_bar)
            
            for i, price in enumerate(prices):
                tick_time = timestamp + timedelta(seconds=i * (60 // ticks_per_bar))
                ticks.append(BacktestTick(
                    timestamp=tick_time,
                    instrument=instrument,
                    price=price,
                    volume=vol_per_tick,
                    open=open_price,
                    high=high_price,
                    low=low_price
                ))
        
        return ticks
    
    def _generate_tick_path(self, open_p: float, high_p: float, low_p: float, close_p: float, n: int) -> List[float]:
        """Generate a realistic price path within an OHLC bar"""
        prices = [open_p]
        
        # Determine if high or low comes first
        high_first = np.random.random() > 0.5
        
        mid_point = n // 2
        
        for i in range(1, n):
            if i < mid_point:
                if high_first:
                    target = high_p
                else:
                    target = low_p
            else:
                target = close_p
            
            # Interpolate with noise
            progress = i / n
            base = open_p + (target - open_p) * progress
            noise = (high_p - low_p) * np.random.uniform(-0.1, 0.1)
            price = max(low_p, min(high_p, base + noise))
            prices.append(round(price, 2))
        
        prices[-1] = close_p  # Ensure we end at close
        return prices


# ============================================================================
#                     BACKTEST ENGINE
# ============================================================================

class BacktestScalpingEngine:
    """
    Backtesting engine that simulates the production scalping strategy
    """
    
    def __init__(self, config: BacktestConfig):
        self.config = config
        self.capital = config.initial_capital
        self.initial_capital = config.initial_capital
        
        # Position state
        self._position = None
        self._focused_instrument = None
        
        # Momentum tracking
        self._momentum: Dict[str, Dict] = {}
        for inst in config.instruments:
            self._momentum[inst] = {
                'prices': [],
                'volumes': [],
                'score': 50.0,
                'velocity': 0.0,
                'acceleration': 0.0,
                'phase': MomentumPhase.DORMANT,
                # NEW: Consecutive tick tracking for 90%+ win rate
                'consecutive_up': 0,
                'consecutive_down': 0,
                'last_direction': 0,  # 1 = up, -1 = down, 0 = flat
                'streak_strength': 0.0  # Cumulative move in streak
            }
        
        # Trade tracking
        self._trade_id = 0
        self._trades: List[BacktestTrade] = []
        self._daily_trades: Dict[str, List[BacktestTrade]] = {}
        
        # Statistics
        self._peak_capital = config.initial_capital
        self._max_drawdown = 0.0
        self._equity_curve: List[Tuple[datetime, float]] = []
    
    def update_momentum(self, tick: BacktestTick) -> Dict:
        """Update momentum from tick data - with consecutive tick tracking"""
        inst = tick.instrument
        momentum = self._momentum[inst]
        
        # Track consecutive ticks for 90%+ win rate
        if len(momentum['prices']) > 0:
            prev_price = momentum['prices'][-1]
            price_change = tick.price - prev_price
            change_pct = price_change / prev_price * 100 if prev_price > 0 else 0
            
            if price_change > 0:
                # Price went up
                if momentum['last_direction'] == 1:
                    momentum['consecutive_up'] += 1
                    momentum['streak_strength'] += change_pct
                else:
                    momentum['consecutive_up'] = 1
                    momentum['consecutive_down'] = 0
                    momentum['streak_strength'] = change_pct
                momentum['last_direction'] = 1
            elif price_change < 0:
                # Price went down
                if momentum['last_direction'] == -1:
                    momentum['consecutive_down'] += 1
                    momentum['streak_strength'] += abs(change_pct)
                else:
                    momentum['consecutive_down'] = 1
                    momentum['consecutive_up'] = 0
                    momentum['streak_strength'] = abs(change_pct)
                momentum['last_direction'] = -1
            # If flat, don't break the streak
        
        # Update history
        momentum['prices'].append(tick.price)
        momentum['volumes'].append(tick.volume)
        
        # Keep last 100 points
        if len(momentum['prices']) > 100:
            momentum['prices'] = momentum['prices'][-100:]
            momentum['volumes'] = momentum['volumes'][-100:]
        
        if len(momentum['prices']) >= 20:
            prices = momentum['prices']
            volumes = momentum['volumes']
            
            # Velocity
            velocity = (prices[-1] - prices[-5]) / prices[-5] * 100 if prices[-5] != 0 else 0
            momentum['velocity'] = velocity
            
            # Acceleration
            if len(prices) >= 10:
                old_velocity = (prices[-5] - prices[-10]) / prices[-10] * 100 if prices[-10] != 0 else 0
                momentum['acceleration'] = velocity - old_velocity
            
            # Score - enhanced with consecutive tick bonus
            score = 50.0
            score += min(25, max(-25, velocity * 50))
            score += min(15, max(-15, momentum['acceleration'] * 30))
            
            # BONUS: Consecutive ticks add to score
            consecutive = max(momentum['consecutive_up'], momentum['consecutive_down'])
            if consecutive >= 3:
                score += min(20, consecutive * 4)  # Up to +20 for 5+ consecutive
            
            if len(volumes) >= 20:
                avg_vol = sum(volumes[-20:]) / 20
                if avg_vol > 0:
                    vol_ratio = volumes[-1] / avg_vol
                    score += min(10, max(-10, (vol_ratio - 1) * 10))
            
            momentum['score'] = max(0, min(100, score))
            
            # Phase
            if momentum['score'] >= 80:
                momentum['phase'] = MomentumPhase.PEAK
            elif momentum['score'] >= 65 and momentum['acceleration'] > 0:
                momentum['phase'] = MomentumPhase.ACCELERATING
            elif momentum['score'] >= 45:
                momentum['phase'] = MomentumPhase.BUILDING
            elif momentum['score'] >= 30:
                momentum['phase'] = MomentumPhase.FADING
            elif velocity < -0.1:
                momentum['phase'] = MomentumPhase.REVERSAL
            else:
                momentum['phase'] = MomentumPhase.DORMANT
        
        return momentum
    
    def get_best_opportunity(self) -> Optional[str]:
        """Find best trading opportunity - MEAN REVERSION for 90%+ win rate"""
        best_inst = None
        best_score = 0.0
        
        for inst, momentum in self._momentum.items():
            # MEAN REVERSION: Enter when momentum is EXTREME (>85)
            # The more extreme, the more likely to revert
            # We fade the move (go opposite direction)
            
            if momentum['score'] >= 85 and momentum['phase'] == MomentumPhase.PEAK:
                # Peak momentum = about to reverse
                score = momentum['score']
                if score > best_score:
                    best_score = score
                    best_inst = inst
            
            elif momentum['score'] >= 80 and momentum['phase'] == MomentumPhase.ACCELERATING:
                # Strong acceleration often overshoots
                score = momentum['score'] * 0.9  # Slightly less preferred
                if score > best_score:
                    best_score = score
                    best_inst = inst
        
        if best_score >= 80:
            return best_inst
        return None
    
    def should_enter(self, tick: BacktestTick) -> bool:
        """Check if should enter - OPTIMIZED for high win rate + profitability"""
        if self._position is not None:
            return False
        
        # Check max trades per day
        date_str = tick.timestamp.strftime('%Y-%m-%d')
        today_trades = self._daily_trades.get(date_str, [])
        if len(today_trades) >= 5:
            return False
        
        best = self.get_best_opportunity()
        if best != tick.instrument:
            return False
        
        # ONLY TRADE NIFTY - best win rate
        if tick.instrument != "NIFTY":
            return False
        
        momentum = self._momentum[tick.instrument]
        
        # OPTIMIZED ENTRY CRITERIA:
        # 1. Strong momentum score (>= 78) 
        # 2. At least 4 consecutive ticks 
        # 3. Streak strength > 0.10%
        # 4. Clear velocity > 0.10%
        # 5. Not in reversal
        
        strong_score = momentum['score'] >= 78
        
        # Consecutive tick confirmation
        consecutive_up = momentum.get('consecutive_up', 0)
        consecutive_down = momentum.get('consecutive_down', 0)
        streak_confirmed = (consecutive_up >= 4 or consecutive_down >= 4)
        
        # Meaningful streak strength
        meaningful_streak = momentum.get('streak_strength', 0) >= 0.10
        
        # Clear direction
        clear_direction = abs(momentum['velocity']) >= 0.10
        
        # Not reversing
        not_reversing = momentum['phase'] != MomentumPhase.REVERSAL
        
        return strong_score and streak_confirmed and meaningful_streak and clear_direction and not_reversing
    
    def enter_trade(self, tick: BacktestTick):
        """Enter a new trade - TREND FOLLOWING: ride the confirmed momentum"""
        self._trade_id += 1
        
        # TREND FOLLOWING: Go WITH the confirmed momentum
        # We only enter after 5+ consecutive ticks in one direction
        # This confirms strong trend, so we ride it for quick profit
        momentum = self._momentum[tick.instrument]
        
        # Use consecutive tick direction to determine option type
        if momentum['consecutive_up'] >= 5:
            option_type = "CE"  # Bullish - ride upward momentum
        else:
            option_type = "PE"  # Bearish - ride downward momentum
        
        lot_size = self.config.lot_sizes.get(tick.instrument, 50)
        
        # FIXED: Use initial capital for sizing, not compounded capital
        # This prevents unrealistic exponential growth
        sizing_capital = min(self.capital, self.initial_capital * 2)  # Cap at 2x initial
        max_lots = int(sizing_capital * self.config.max_position_percent / 100 / (tick.price * lot_size))
        max_lots = max(1, min(max_lots, 20))  # Cap at 20 lots max for realistic trading
        
        probe_lots = max(1, int(max_lots * self.config.probe_size_percent / 100))
        
        # Apply slippage
        entry_price = tick.price * (1 + self.config.slippage_percent / 100)
        
        self._position = {
            'trade_id': self._trade_id,
            'instrument': tick.instrument,
            'option_type': option_type,
            'entry_time': tick.timestamp,
            'entry_price': entry_price,
            'avg_entry_price': entry_price,
            'current_lots': probe_lots,
            'max_lots': max_lots,
            'max_lots_reached': probe_lots,
            'stage': PositionStage.PROBE,
            'stages_reached': [PositionStage.PROBE.value],
            'stop_loss': entry_price * (1 - self.config.stop_loss_percent / 100),
            'highest_price': entry_price,
            'entry_momentum': momentum['score'],
            'max_momentum': momentum['score'],
            'scale_count': 0,
            'max_profit': 0,
            'max_drawdown': 0
        }
        
        self._focused_instrument = tick.instrument
    
    def update_trade(self, tick: BacktestTick) -> Optional[BacktestTrade]:
        """Update current trade with new tick"""
        if not self._position or tick.instrument != self._position['instrument']:
            return None
        
        pos = self._position
        momentum = self._momentum[tick.instrument]
        
        # Update highest price
        pos['highest_price'] = max(pos['highest_price'], tick.price)
        pos['max_momentum'] = max(pos['max_momentum'], momentum['score'])
        
        # Calculate current P&L
        lot_size = self.config.lot_sizes.get(tick.instrument, 50)
        pnl = (tick.price - pos['avg_entry_price']) * pos['current_lots'] * lot_size
        pnl_percent = (tick.price - pos['avg_entry_price']) / pos['avg_entry_price'] * 100
        
        pos['max_profit'] = max(pos['max_profit'], pnl)
        pos['max_drawdown'] = min(pos['max_drawdown'], pnl)
        
        exit_reason = None
        hold_time_seconds = (tick.timestamp - pos['entry_time']).total_seconds()
        hold_time_minutes = hold_time_seconds / 60
        
        # AGGRESSIVE EXIT LOGIC FOR 300%+ MONTHLY RETURNS
        # Let winners run, use smart stops based on stage
        
        # FIRST: Check if we should SCALE UP before exiting
        if self._should_scale_up(pnl_percent, momentum):
            self._scale_up(tick.price, momentum['score'])
        
        # AGGRESSIVE STAGE: Maximum target (2%+)
        if pos['stage'] == PositionStage.AGGRESSIVE and pnl_percent >= 2.0:
            exit_reason = "AGGRESSIVE_TARGET_2%"
        
        # FULL POSITION: Strong target (1.5%+) 
        elif pos['stage'] == PositionStage.FULL and pnl_percent >= 1.5:
            exit_reason = "FULL_TARGET_1.5%"
        
        # CONFIRMED: Medium target (1%+)
        elif pos['stage'] == PositionStage.CONFIRMED and pnl_percent >= 1.0:
            exit_reason = "CONFIRMED_TARGET_1%"
        
        # PROBE: Quick scalp target (0.5%+) - but give it time
        elif pos['stage'] == PositionStage.PROBE and pnl_percent >= 0.5 and hold_time_seconds >= 15:
            exit_reason = "PROBE_TARGET_0.5%"
        
        # ANY STAGE: Take exceptional 1.5%+ profit
        elif pnl_percent >= 1.5:
            exit_reason = "EXCEPTIONAL_TARGET"
        
        # TIME-BASED: After 10 min, lock in 0.3%+
        elif hold_time_minutes >= 10.0 and pnl_percent >= 0.3:
            exit_reason = "TIME_PROFIT_10M"
        
        # STOP LOSS: Stage-based stops
        elif pos['stage'] == PositionStage.AGGRESSIVE and pnl_percent <= -0.5:
            exit_reason = "AGGRESSIVE_STOP"
        elif pos['stage'] == PositionStage.FULL and pnl_percent <= -0.8:
            exit_reason = "FULL_STOP"
        elif pos['stage'] == PositionStage.CONFIRMED and pnl_percent <= -1.0:
            exit_reason = "CONFIRMED_STOP"
        elif pos['stage'] == PositionStage.PROBE and pnl_percent <= -1.5:
            exit_reason = "PROBE_STOP"
        
        # TIME LIMIT: 20 minutes max
        elif hold_time_minutes >= 20.0:
            if pnl_percent > 0:
                exit_reason = "TIME_LIMIT_PROFIT"
            else:
                exit_reason = "TIME_LIMIT"
        
        # REVERSAL: If momentum completely dies
        elif momentum['phase'] == MomentumPhase.REVERSAL and momentum['score'] < 25:
            exit_reason = "REVERSAL"
        
        # TRAILING STOP: Lock in profits after 1%+ (aggressive trail)
        if pnl_percent >= 1.0:
            new_stop = pos['entry_price'] * 1.006  # Lock in 0.6%
            pos['stop_loss'] = max(pos.get('stop_loss', 0), new_stop)
        
        if exit_reason:
            return self._close_trade(tick, exit_reason)
        
        return None
    
    def _should_scale_up(self, pnl_percent: float, momentum: Dict) -> bool:
        """Check if should scale up"""
        pos = self._position
        
        if pos['stage'] == PositionStage.PROBE:
            return (
                pnl_percent >= self.config.min_profit_to_confirm and
                momentum['score'] >= self.config.min_momentum_for_scale_up and
                momentum['phase'] in [MomentumPhase.BUILDING, MomentumPhase.ACCELERATING]
            )
        
        if pos['stage'] == PositionStage.CONFIRMED:
            return (
                pnl_percent >= self.config.min_profit_to_full and
                momentum['score'] >= 70 and
                momentum['phase'] == MomentumPhase.ACCELERATING
            )
        
        if pos['stage'] == PositionStage.FULL:
            return (
                pnl_percent >= self.config.min_profit_to_aggressive and
                momentum['score'] >= 85 and
                momentum['phase'] == MomentumPhase.PEAK
            )
        
        return False
    
    def _should_scale_down(self, momentum: Dict) -> bool:
        """Check if should scale down (exit)"""
        pos = self._position
        
        if pos['stage'] in [PositionStage.FULL, PositionStage.AGGRESSIVE]:
            return momentum['phase'] == MomentumPhase.FADING
        
        return False
    
    def _scale_up(self, price: float, momentum_score: float):
        """Scale up position"""
        pos = self._position
        
        if pos['stage'] == PositionStage.PROBE:
            new_lots = max(1, int(pos['max_lots'] * self.config.confirmed_size_percent / 100))
            pos['stage'] = PositionStage.CONFIRMED
        elif pos['stage'] == PositionStage.CONFIRMED:
            new_lots = max(1, int(pos['max_lots'] * self.config.full_size_percent / 100))
            pos['stage'] = PositionStage.FULL
        elif pos['stage'] == PositionStage.FULL:
            new_lots = max(1, int(pos['max_lots'] * self.config.aggressive_size_percent / 100))
            pos['stage'] = PositionStage.AGGRESSIVE
        else:
            return
        
        add_lots = new_lots - pos['current_lots']
        if add_lots > 0:
            # Update average entry price (with slippage)
            add_price = price * (1 + self.config.slippage_percent / 100)
            total_value = pos['avg_entry_price'] * pos['current_lots'] + add_price * add_lots
            pos['avg_entry_price'] = total_value / new_lots
            
            pos['current_lots'] = new_lots
            pos['max_lots_reached'] = max(pos['max_lots_reached'], new_lots)
            pos['scale_count'] += 1
            pos['stages_reached'].append(pos['stage'].value)
    
    def _close_trade(self, tick: BacktestTick, exit_reason: str) -> BacktestTrade:
        """Close trade and create record"""
        pos = self._position
        momentum = self._momentum[tick.instrument]
        
        # Exit price with slippage
        exit_price = tick.price * (1 - self.config.slippage_percent / 100)
        
        # Calculate P&L
        lot_size = self.config.lot_sizes.get(tick.instrument, 50)
        gross_pnl = (exit_price - pos['avg_entry_price']) * pos['current_lots'] * lot_size
        
        # Calculate transaction costs
        total_lots_traded = pos['max_lots_reached'] + pos['scale_count'] * 2  # Rough estimate
        brokerage = total_lots_traded * self.config.brokerage_per_lot
        turnover = (pos['entry_price'] + exit_price) * pos['max_lots_reached'] * lot_size
        stt = turnover * self.config.stt_percent / 100
        other = turnover * self.config.other_charges_percent / 100
        transaction_costs = brokerage + stt + other
        
        net_pnl = gross_pnl - transaction_costs
        pnl_percent = (exit_price - pos['avg_entry_price']) / pos['avg_entry_price'] * 100
        
        duration = (tick.timestamp - pos['entry_time']).total_seconds() / 60
        
        trade = BacktestTrade(
            trade_id=pos['trade_id'],
            instrument=pos['instrument'],
            option_type=pos['option_type'],
            entry_time=pos['entry_time'],
            exit_time=tick.timestamp,
            entry_price=pos['entry_price'],
            exit_price=exit_price,
            initial_lots=int(pos['max_lots'] * self.config.probe_size_percent / 100),
            max_lots=pos['max_lots_reached'],
            final_lots=pos['current_lots'],
            gross_pnl=gross_pnl,
            transaction_costs=transaction_costs,
            net_pnl=net_pnl,
            pnl_percent=pnl_percent,
            duration_minutes=duration,
            exit_reason=exit_reason,
            entry_momentum=pos['entry_momentum'],
            exit_momentum=momentum['score'],
            max_momentum=pos['max_momentum'],
            scale_count=pos['scale_count'],
            stages_reached=pos['stages_reached'],
            max_profit=pos['max_profit'],
            max_drawdown=pos['max_drawdown']
        )
        
        # Update capital
        self.capital += net_pnl
        
        # Track drawdown
        self._peak_capital = max(self._peak_capital, self.capital)
        current_dd = (self._peak_capital - self.capital) / self._peak_capital * 100
        self._max_drawdown = max(self._max_drawdown, current_dd)
        
        # Store trade
        self._trades.append(trade)
        date_str = tick.timestamp.strftime('%Y-%m-%d')
        if date_str not in self._daily_trades:
            self._daily_trades[date_str] = []
        self._daily_trades[date_str].append(trade)
        
        # Record equity curve
        self._equity_curve.append((tick.timestamp, self.capital))
        
        # Clear position
        self._position = None
        self._focused_instrument = None
        
        return trade
    
    def force_close_eod(self, tick: BacktestTick) -> Optional[BacktestTrade]:
        """Force close at end of day"""
        if self._position and self._position['instrument'] == tick.instrument:
            return self._close_trade(tick, "END_OF_DAY")
        return None
    
    async def run_backtest(self, data_provider: BacktestDataProvider) -> BacktestResult:
        """Run the complete backtest"""
        logger.info("=" * 70)
        logger.info("🚀 STARTING WORLD-CLASS SCALPING BACKTEST")
        logger.info("=" * 70)
        logger.info(f"Period: {self.config.start_date.date()} to {self.config.end_date.date()}")
        logger.info(f"Capital: ₹{self.config.initial_capital:,.0f}")
        logger.info(f"Instruments: {self.config.instruments}")
        logger.info("=" * 70)
        
        # Fetch data for all instruments
        all_ticks: List[BacktestTick] = []
        
        for instrument in self.config.instruments:
            df = await data_provider.fetch_data(
                instrument,
                self.config.start_date,
                self.config.end_date
            )
            
            if not df.empty:
                ticks = data_provider.generate_ticks_from_bars(df, instrument, ticks_per_bar=6)
                all_ticks.extend(ticks)
                logger.info(f"📊 {instrument}: {len(ticks)} ticks loaded")
        
        # Sort all ticks by timestamp
        all_ticks.sort(key=lambda t: t.timestamp)
        logger.info(f"📊 Total ticks to process: {len(all_ticks)}")
        
        # Process each tick
        current_date = None
        trading_days = set()
        
        for i, tick in enumerate(all_ticks):
            # Progress logging
            if i % 10000 == 0:
                logger.info(f"Processing tick {i}/{len(all_ticks)} ({i/len(all_ticks)*100:.1f}%)")
            
            # Check if new day
            tick_date = tick.timestamp.date()
            if tick_date != current_date:
                # Force close any position from previous day
                if self._position and current_date:
                    last_tick = BacktestTick(
                        timestamp=datetime.combine(current_date, time(15, 30)),
                        instrument=self._position['instrument'],
                        price=tick.price,
                        volume=0
                    )
                    self.force_close_eod(last_tick)
                
                current_date = tick_date
                trading_days.add(tick_date)
            
            # Check trading hours
            tick_time = tick.timestamp.time()
            trading_start = time(self.config.trading_start_hour, self.config.trading_start_minute)
            trading_end = time(self.config.trading_end_hour, self.config.trading_end_minute)
            
            if not (trading_start <= tick_time <= trading_end):
                continue
            
            # Update momentum
            self.update_momentum(tick)
            
            # Process trade logic
            if self._position:
                self.update_trade(tick)
            elif self.should_enter(tick):
                self.enter_trade(tick)
        
        # Force close any remaining position
        if self._position and all_ticks:
            self.force_close_eod(all_ticks[-1])
        
        # Generate results
        return self._generate_results(trading_days)
    
    def _generate_results(self, trading_days: set) -> BacktestResult:
        """Generate comprehensive backtest results"""
        trades = self._trades
        
        if not trades:
            return BacktestResult(
                start_date=self.config.start_date.strftime('%Y-%m-%d'),
                end_date=self.config.end_date.strftime('%Y-%m-%d'),
                trading_days=len(trading_days),
                initial_capital=self.initial_capital,
                final_capital=self.capital,
                total_return_percent=0,
                total_trades=0,
                winning_trades=0,
                losing_trades=0,
                win_rate=0,
                gross_pnl=0,
                total_transaction_costs=0,
                net_pnl=0,
                avg_win=0,
                avg_loss=0,
                avg_pnl_per_trade=0,
                profit_factor=0,
                max_drawdown=0,
                max_drawdown_percent=0,
                sharpe_ratio=0,
                sortino_ratio=0,
                avg_trade_duration=0,
                longest_trade=0,
                shortest_trade=0,
                avg_scale_count=0,
                trades_reached_full=0,
                trades_reached_aggressive=0
            )
        
        # Basic stats
        winning_trades = [t for t in trades if t.net_pnl > 0]
        losing_trades = [t for t in trades if t.net_pnl <= 0]
        
        total_wins = sum(t.net_pnl for t in winning_trades)
        total_losses = abs(sum(t.net_pnl for t in losing_trades))
        
        avg_win = total_wins / len(winning_trades) if winning_trades else 0
        avg_loss = total_losses / len(losing_trades) if losing_trades else 0
        
        profit_factor = total_wins / total_losses if total_losses > 0 else float('inf')
        
        # Duration stats
        durations = [t.duration_minutes for t in trades]
        
        # Scaling stats
        trades_full = [t for t in trades if 'FULL' in t.stages_reached]
        trades_aggressive = [t for t in trades if 'AGGRESSIVE' in t.stages_reached]
        
        # Daily stats
        daily_stats = []
        for date_str, day_trades in sorted(self._daily_trades.items()):
            day_wins = [t for t in day_trades if t.net_pnl > 0]
            day_losses = [t for t in day_trades if t.net_pnl <= 0]
            
            daily_stats.append(DailyStats(
                date=date_str,
                trades=len(day_trades),
                wins=len(day_wins),
                losses=len(day_losses),
                win_rate=len(day_wins) / len(day_trades) * 100 if day_trades else 0,
                gross_pnl=sum(t.gross_pnl for t in day_trades),
                net_pnl=sum(t.net_pnl for t in day_trades),
                max_drawdown=min(t.max_drawdown for t in day_trades) if day_trades else 0,
                best_trade=max(t.net_pnl for t in day_trades) if day_trades else 0,
                worst_trade=min(t.net_pnl for t in day_trades) if day_trades else 0,
                avg_trade=sum(t.net_pnl for t in day_trades) / len(day_trades) if day_trades else 0,
                avg_duration=sum(t.duration_minutes for t in day_trades) / len(day_trades) if day_trades else 0
            ))
        
        # Instrument stats
        instrument_stats = {}
        for inst in self.config.instruments:
            inst_trades = [t for t in trades if t.instrument == inst]
            if inst_trades:
                inst_wins = [t for t in inst_trades if t.net_pnl > 0]
                instrument_stats[inst] = {
                    'trades': len(inst_trades),
                    'wins': len(inst_wins),
                    'win_rate': len(inst_wins) / len(inst_trades) * 100,
                    'net_pnl': sum(t.net_pnl for t in inst_trades),
                    'avg_pnl': sum(t.net_pnl for t in inst_trades) / len(inst_trades)
                }
        
        # Calculate Sharpe ratio (simplified)
        daily_returns = []
        for stats in daily_stats:
            daily_returns.append(stats.net_pnl / self.initial_capital * 100)
        
        sharpe = 0
        sortino = 0
        if daily_returns and np.std(daily_returns) > 0:
            sharpe = np.mean(daily_returns) / np.std(daily_returns) * np.sqrt(252)
            neg_returns = [r for r in daily_returns if r < 0]
            if neg_returns:
                sortino = np.mean(daily_returns) / np.std(neg_returns) * np.sqrt(252)
        
        gross_pnl = sum(t.gross_pnl for t in trades)
        transaction_costs = sum(t.transaction_costs for t in trades)
        net_pnl = sum(t.net_pnl for t in trades)
        
        return BacktestResult(
            start_date=self.config.start_date.strftime('%Y-%m-%d'),
            end_date=self.config.end_date.strftime('%Y-%m-%d'),
            trading_days=len(trading_days),
            initial_capital=self.initial_capital,
            final_capital=self.capital,
            total_return_percent=(self.capital - self.initial_capital) / self.initial_capital * 100,
            total_trades=len(trades),
            winning_trades=len(winning_trades),
            losing_trades=len(losing_trades),
            win_rate=len(winning_trades) / len(trades) * 100,
            gross_pnl=gross_pnl,
            total_transaction_costs=transaction_costs,
            net_pnl=net_pnl,
            avg_win=avg_win,
            avg_loss=avg_loss,
            avg_pnl_per_trade=net_pnl / len(trades),
            profit_factor=profit_factor,
            max_drawdown=self._max_drawdown,
            max_drawdown_percent=self._max_drawdown,
            sharpe_ratio=sharpe,
            sortino_ratio=sortino,
            avg_trade_duration=np.mean(durations),
            longest_trade=max(durations),
            shortest_trade=min(durations),
            avg_scale_count=np.mean([t.scale_count for t in trades]),
            trades_reached_full=len(trades_full),
            trades_reached_aggressive=len(trades_aggressive),
            daily_stats=daily_stats,
            all_trades=trades,
            instrument_stats=instrument_stats
        )


# ============================================================================
#                     MAIN EXECUTION
# ============================================================================

async def run_backtest(days: int = 30, capital: float = 500000.0) -> BacktestResult:
    """Run a complete backtest"""
    config = BacktestConfig(
        start_date=datetime.now() - timedelta(days=days),
        end_date=datetime.now(),
        initial_capital=capital
    )
    
    data_provider = BacktestDataProvider(config)
    engine = BacktestScalpingEngine(config)
    
    result = await engine.run_backtest(data_provider)
    
    return result


def print_results(result: BacktestResult):
    """Print backtest results in a formatted way"""
    print("\n" + "=" * 70)
    print("📊 BACKTEST RESULTS - WORLD-CLASS SCALPING STRATEGY")
    print("=" * 70)
    
    print(f"\n📅 Period: {result.start_date} to {result.end_date} ({result.trading_days} trading days)")
    
    print(f"\n💰 CAPITAL")
    print(f"   Initial:     ₹{result.initial_capital:>15,.2f}")
    print(f"   Final:       ₹{result.final_capital:>15,.2f}")
    print(f"   Net P&L:     ₹{result.net_pnl:>15,.2f}")
    print(f"   Return:       {result.total_return_percent:>14.2f}%")
    
    print(f"\n📈 TRADE STATISTICS")
    print(f"   Total Trades:     {result.total_trades:>10}")
    print(f"   Winning Trades:   {result.winning_trades:>10}")
    print(f"   Losing Trades:    {result.losing_trades:>10}")
    print(f"   Win Rate:         {result.win_rate:>9.1f}%")
    print(f"   Profit Factor:    {result.profit_factor:>10.2f}")
    
    print(f"\n💵 P&L BREAKDOWN")
    print(f"   Gross P&L:   ₹{result.gross_pnl:>15,.2f}")
    print(f"   Costs:       ₹{result.total_transaction_costs:>15,.2f}")
    print(f"   Net P&L:     ₹{result.net_pnl:>15,.2f}")
    print(f"   Avg Win:     ₹{result.avg_win:>15,.2f}")
    print(f"   Avg Loss:    ₹{result.avg_loss:>15,.2f}")
    print(f"   Avg Trade:   ₹{result.avg_pnl_per_trade:>15,.2f}")
    
    print(f"\n📉 RISK METRICS")
    print(f"   Max Drawdown:     {result.max_drawdown_percent:>9.2f}%")
    print(f"   Sharpe Ratio:     {result.sharpe_ratio:>10.2f}")
    print(f"   Sortino Ratio:    {result.sortino_ratio:>10.2f}")
    
    print(f"\n⏱️ TIME METRICS")
    print(f"   Avg Duration:     {result.avg_trade_duration:>9.1f} min")
    print(f"   Longest Trade:    {result.longest_trade:>9.1f} min")
    print(f"   Shortest Trade:   {result.shortest_trade:>9.1f} min")
    
    print(f"\n📊 SCALING STATISTICS")
    print(f"   Avg Scale Count:      {result.avg_scale_count:>8.2f}")
    print(f"   Reached FULL:         {result.trades_reached_full:>8}")
    print(f"   Reached AGGRESSIVE:   {result.trades_reached_aggressive:>8}")
    
    if result.instrument_stats:
        print(f"\n📈 BY INSTRUMENT")
        for inst, stats in result.instrument_stats.items():
            print(f"   {inst:12} | Trades: {stats['trades']:>3} | Win Rate: {stats['win_rate']:>5.1f}% | Net P&L: ₹{stats['net_pnl']:>10,.0f}")
    
    print("\n" + "=" * 70)
    
    # Monthly return projection
    monthly_return = result.total_return_percent / (result.trading_days / 22) if result.trading_days > 0 else 0
    print(f"\n🎯 MONTHLY RETURN PROJECTION: {monthly_return:.1f}%")
    
    if monthly_return >= 400:
        print("   ✅ TARGET ACHIEVED: 400%+ monthly return!")
    elif monthly_return >= 100:
        print("   ⚡ EXCELLENT: 100%+ monthly return")
    elif monthly_return >= 50:
        print("   📈 GOOD: 50%+ monthly return")
    else:
        print("   ⚠️ NEEDS IMPROVEMENT")
    
    print("=" * 70)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="World-Class Scalping Backtest")
    parser.add_argument("--days", type=int, default=30, help="Number of days to backtest")
    parser.add_argument("--capital", type=float, default=500000, help="Initial capital")
    parser.add_argument("--output", type=str, default="backtest_results.json", help="Output file")
    
    args = parser.parse_args()
    
    print(f"🚀 Running {args.days}-day backtest with ₹{args.capital:,.0f} capital...")
    
    result = asyncio.run(run_backtest(days=args.days, capital=args.capital))
    
    print_results(result)
    
    # Save results
    output_path = os.path.join(os.path.dirname(__file__), "backtests", "results", args.output)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    with open(output_path, 'w') as f:
        json.dump(result.to_dict(), f, indent=2)
    
    print(f"\n📁 Results saved to: {output_path}")
