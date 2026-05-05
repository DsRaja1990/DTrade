"""
Institutional-Grade Advanced AI Trading Engine
Proprietary Options Trading Algorithm with Deep Learning and Quantitative Analysis
"""

import asyncio
import logging
import math
import uuid
import time
import os
from datetime import datetime, timedelta, date
from typing import Dict, List, Optional, Tuple, Any, Union, Callable
from enum import Enum, auto
from dataclasses import dataclass, field, asdict
from functools import lru_cache
import pandas as pd
import numpy as np
import json
from collections import deque, defaultdict
from scipy import stats, optimize, signal
from scipy.stats import norm, percentileofscore
import statsmodels.api as sm
from statsmodels.tsa.stattools import adfuller, acf, pacf
from statsmodels.tsa.arima.model import ARIMA
from statsmodels.tsa.regime_switching.markov_regression import MarkovRegression
import joblib

# Define fallback classes first
class Sequential:
    def __init__(self, *args, **kwargs): pass
    def add(self, *args, **kwargs): pass
    def compile(self, *args, **kwargs): pass
    def fit(self, *args, **kwargs): return type('obj', (object,), {'history': {}})
    def predict(self, *args, **kwargs): return np.array([])
    def save(self, *args, **kwargs): pass

class Model:
    def __init__(self, *args, **kwargs): pass
    def compile(self, *args, **kwargs): pass
    def fit(self, *args, **kwargs): return type('obj', (object,), {'history': {}})
    def predict(self, *args, **kwargs): return np.array([])
    def save(self, *args, **kwargs): pass

class LSTM:
    def __init__(self, *args, **kwargs): pass

class Dense:
    def __init__(self, *args, **kwargs): pass

class Dropout:
    def __init__(self, *args, **kwargs): pass

class BatchNormalization:
    def __init__(self, *args, **kwargs): pass

class Input:
    def __init__(self, *args, **kwargs): pass

class Conv1D:
    def __init__(self, *args, **kwargs): pass

class MaxPooling1D:
    def __init__(self, *args, **kwargs): pass

class GlobalAveragePooling1D:
    def __init__(self, *args, **kwargs): pass

class Bidirectional:
    def __init__(self, *args, **kwargs): pass

class Adam:
    def __init__(self, *args, **kwargs): pass

class EarlyStopping:
    def __init__(self, *args, **kwargs): pass

class ModelCheckpoint:
    def __init__(self, *args, **kwargs): pass

class ReduceLROnPlateau:
    def __init__(self, *args, **kwargs): pass

def load_model(*args, **kwargs):
    return Model()

# Optional deep learning imports with graceful fallbacks
TF_AVAILABLE = False
try:
    import tensorflow as tf  # type: ignore
    # Only import if tensorflow is available
    from tensorflow.keras.models import Sequential as TF_Sequential, Model as TF_Model, load_model as tf_load_model  # type: ignore
    from tensorflow.keras.layers import LSTM as TF_LSTM, Dense as TF_Dense, Dropout as TF_Dropout  # type: ignore
    from tensorflow.keras.layers import BatchNormalization as TF_BatchNorm, Input as TF_Input, Conv1D as TF_Conv1D  # type: ignore
    from tensorflow.keras.layers import Attention, MultiHeadAttention, LayerNormalization, GRU  # type: ignore
    from tensorflow.keras.layers import Bidirectional as TF_Bidirectional, TimeDistributed, GlobalAveragePooling1D as TF_GlobalAvgPool1D, MaxPooling1D as TF_MaxPool1D  # type: ignore
    from tensorflow.keras.optimizers import Adam as TF_Adam  # type: ignore
    from tensorflow.keras.callbacks import EarlyStopping as TF_EarlyStopping, ModelCheckpoint as TF_ModelCheckpoint, ReduceLROnPlateau as TF_ReduceLR  # type: ignore
    
    # Use TensorFlow classes
    Sequential = TF_Sequential
    Model = TF_Model
    LSTM = TF_LSTM
    Dense = TF_Dense
    Dropout = TF_Dropout
    BatchNormalization = TF_BatchNorm
    Input = TF_Input
    Conv1D = TF_Conv1D
    MaxPooling1D = TF_MaxPool1D
    GlobalAveragePooling1D = TF_GlobalAvgPool1D
    Bidirectional = TF_Bidirectional
    Adam = TF_Adam
    EarlyStopping = TF_EarlyStopping
    ModelCheckpoint = TF_ModelCheckpoint
    ReduceLROnPlateau = TF_ReduceLR
    load_model = tf_load_model
    
    TF_AVAILABLE = True
except ImportError:
    # Use fallback classes (already defined above)
    pass

try:
    import torch
    import torch.nn as nn
    import torch.optim as optim
    from torch.utils.data import Dataset, DataLoader, TensorDataset
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False

try:
    from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor, RandomForestClassifier
    from sklearn.preprocessing import StandardScaler, MinMaxScaler, RobustScaler
    from sklearn.model_selection import train_test_split, TimeSeriesSplit, GridSearchCV
    from sklearn.metrics import mean_squared_error, r2_score, confusion_matrix, classification_report
    from sklearn.pipeline import Pipeline
    from sklearn.decomposition import PCA
    from sklearn.feature_selection import SelectKBest, f_regression
    from sklearn.cluster import KMeans
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False

# Application imports
from app.core.config import settings
from app.core.redis_client import redis_client
from app.core.websocket_manager import websocket_manager
from app.services.dhan_service import dhan_service
from app.services.market_data_service import MarketDataService
from app.models.trading import Position, Order
# from app.services.time_service import TimeService  # TODO: Implement if needed

# Configure logger
logger = logging.getLogger(__name__)
handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.INFO)

# Configure trade journal logger
trade_logger = logging.getLogger("trade_journal")
file_handler = logging.FileHandler("trade_journal.log")
file_handler.setFormatter(formatter)
trade_logger.addHandler(file_handler)
trade_logger.setLevel(logging.INFO)

# Global constants
MIN_STOP_DISTANCE = 0.05  # Minimum stop distance as percentage
MAX_POSITION_LEVERAGE = 3  # Maximum leverage per position
VOLATILITY_WINDOW = 30  # Window for volatility calculation
BACKTESTING_MODE = False  # Set to True for backtesting
DEFAULT_RISK_FREE_RATE = 0.05  # 5% risk-free rate
DEFAULT_DIVIDEND_YIELD = 0.0  # 0% dividend yield
MAX_IV_THRESHOLD = 0.80  # Maximum IV threshold (80%)
MIN_IV_THRESHOLD = 0.15  # Minimum IV threshold (15%)
MAX_POSITION_DELTA = 0.30  # Maximum delta exposure (30%)
KELLY_FRACTION = 0.5  # Kelly criterion fraction (50%)


class SignalType(Enum):
    """Enhanced trade signal types"""
    BUY_CALL = "BUY_CALL"
    BUY_PUT = "BUY_PUT"
    SELL_CALL = "SELL_CALL"
    SELL_PUT = "SELL_PUT"
    BUY_CALL_SPREAD = "BUY_CALL_SPREAD"
    BUY_PUT_SPREAD = "BUY_PUT_SPREAD"
    SELL_CALL_SPREAD = "SELL_CALL_SPREAD"
    SELL_PUT_SPREAD = "SELL_PUT_SPREAD"
    IRON_CONDOR = "IRON_CONDOR"
    IRON_BUTTERFLY = "IRON_BUTTERFLY"
    CALENDAR_SPREAD = "CALENDAR_SPREAD"
    DIAGONAL_SPREAD = "DIAGONAL_SPREAD"
    RATIO_SPREAD = "RATIO_SPREAD"
    JADE_LIZARD = "JADE_LIZARD"
    DOUBLE_DIAGONAL = "DOUBLE_DIAGONAL"
    HEDGE_DELTA = "HEDGE_DELTA"
    HEDGE_GAMMA = "HEDGE_GAMMA"
    HEDGE_VEGA = "HEDGE_VEGA"
    EXIT_POSITION = "EXIT_POSITION"
    TRAIL_STOP = "TRAIL_STOP"
    ADJUST_POSITION = "ADJUST_POSITION"
    ROLL_POSITION = "ROLL_POSITION"
    CLOSE_AND_REVERSE = "CLOSE_AND_REVERSE"


class MarketRegime(Enum):
    """Market regime classifications"""
    BULL_TREND = "BULL_TREND"
    BEAR_TREND = "BEAR_TREND"
    BULL_VOLATILE = "BULL_VOLATILE"
    BEAR_VOLATILE = "BEAR_VOLATILE"
    SIDEWAYS = "SIDEWAYS"
    SIDEWAYS_VOLATILE = "SIDEWAYS_VOLATILE"
    LOW_VOLATILITY = "LOW_VOLATILITY"
    HIGH_VOLATILITY = "HIGH_VOLATILITY"
    REGIME_TRANSITION = "REGIME_TRANSITION"
    MEAN_REVERTING = "MEAN_REVERTING"
    MOMENTUM = "MOMENTUM"
    CAPITULATION = "CAPITULATION"
    LIQUIDITY_CRISIS = "LIQUIDITY_CRISIS"
    
    @classmethod
    def from_indicators(cls, trend: float, volatility: float, 
                        momentum: float, mean_reversion: float) -> 'MarketRegime':
        """Determine market regime from quantitative indicators"""
        if trend > 0.7 and volatility < 0.3:
            return cls.BULL_TREND
        elif trend > 0.5 and volatility > 0.7:
            return cls.BULL_VOLATILE
        elif trend < -0.7 and volatility < 0.3:
            return cls.BEAR_TREND
        elif trend < -0.5 and volatility > 0.7:
            return cls.BEAR_VOLATILE
        elif abs(trend) < 0.3 and volatility < 0.3:
            return cls.SIDEWAYS
        elif abs(trend) < 0.3 and volatility > 0.7:
            return cls.SIDEWAYS_VOLATILE
        elif volatility < 0.2:
            return cls.LOW_VOLATILITY
        elif volatility > 0.8:
            return cls.HIGH_VOLATILITY
        elif abs(trend - trend) > 0.4:  # Recent trend change
            return cls.REGIME_TRANSITION
        elif mean_reversion > 0.7:
            return cls.MEAN_REVERTING
        elif momentum > 0.7:
            return cls.MOMENTUM
        elif trend < -0.8 and volatility > 0.9:
            return cls.CAPITULATION
        else:
            return cls.SIDEWAYS


class MarketDirection(Enum):
    """Enhanced market direction analysis with strength indicators"""
    STRONG_BULLISH = "STRONG_BULLISH"
    BULLISH = "BULLISH"
    WEAK_BULLISH = "WEAK_BULLISH"
    SIDEWAYS = "SIDEWAYS"
    WEAK_BEARISH = "WEAK_BEARISH"
    BEARISH = "BEARISH"
    STRONG_BEARISH = "STRONG_BEARISH"
    VOLATILE_BULLISH = "VOLATILE_BULLISH"
    VOLATILE_BEARISH = "VOLATILE_BEARISH"
    VOLATILE_NEUTRAL = "VOLATILE_NEUTRAL"
    TREND_REVERSAL_UP = "TREND_REVERSAL_UP"
    TREND_REVERSAL_DOWN = "TREND_REVERSAL_DOWN"
    BREAKOUT_UP = "BREAKOUT_UP"
    BREAKOUT_DOWN = "BREAKOUT_DOWN"
    CONSOLIDATION_BULLISH = "CONSOLIDATION_BULLISH"
    CONSOLIDATION_BEARISH = "CONSOLIDATION_BEARISH"


class TimeFrame(Enum):
    """Multiple timeframes for analysis"""
    TICK = "TICK"
    ONE_MINUTE = "1m"
    THREE_MINUTE = "3m"
    FIVE_MINUTE = "5m"
    FIFTEEN_MINUTE = "15m"
    THIRTY_MINUTE = "30m"
    ONE_HOUR = "1h"
    TWO_HOUR = "2h"
    FOUR_HOUR = "4h"
    DAILY = "1d"
    WEEKLY = "1w"
    MONTHLY = "1M"


class ExecutionStyle(Enum):
    """Advanced order execution styles"""
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    TWAP = "TWAP"  # Time-Weighted Average Price
    VWAP = "VWAP"  # Volume-Weighted Average Price
    SMART = "SMART"  # Smart order routing
    ICEBERG = "ICEBERG"  # Iceberg/hidden orders
    PARTICIPATION = "PARTICIPATION"  # Participation rate
    AGGRESSIVE = "AGGRESSIVE"  # Aggressive liquidity taking
    PASSIVE = "PASSIVE"  # Passive liquidity providing
    DARK_POOL = "DARK_POOL"  # Dark pool routing
    LAYERED = "LAYERED"  # Multiple limit orders at different prices
    ADAPTIVE = "ADAPTIVE"  # Adaptive to market conditions
    LIQUIDITY_SEEKING = "LIQUIDITY_SEEKING"  # Seeks out liquidity
    MARKET_ON_CLOSE = "MARKET_ON_CLOSE"  # MOC order


class StrategyType(Enum):
    """Trading strategy types"""
    DIRECTIONAL = "DIRECTIONAL"
    VOLATILITY = "VOLATILITY"
    MEAN_REVERSION = "MEAN_REVERSION"
    MOMENTUM = "MOMENTUM"
    STATISTICAL_ARBITRAGE = "STATISTICAL_ARBITRAGE"
    MARKET_NEUTRAL = "MARKET_NEUTRAL"
    DELTA_NEUTRAL = "DELTA_NEUTRAL"
    CALENDAR_SPREAD = "CALENDAR_SPREAD"
    YIELD_ENHANCEMENT = "YIELD_ENHANCEMENT"
    GAMMA_SCALPING = "GAMMA_SCALPING"
    VEGA_TRADING = "VEGA_TRADING"
    DISPERSION_TRADING = "DISPERSION_TRADING"
    PAIRS_TRADING = "PAIRS_TRADING"
    TREND_FOLLOWING = "TREND_FOLLOWING"
    BREAKOUT = "BREAKOUT"


class TradingPhase(Enum):
    """Market trading phases"""
    PRE_MARKET = "PRE_MARKET"
    MARKET_OPEN = "MARKET_OPEN"
    MORNING_SESSION = "MORNING_SESSION"
    LUNCH_HOUR = "LUNCH_HOUR"
    AFTERNOON_SESSION = "AFTERNOON_SESSION"
    POWER_HOUR = "POWER_HOUR"
    MARKET_CLOSE = "MARKET_CLOSE"
    AFTER_HOURS = "AFTER_HOURS"


class OptionGreeks:
    """Full options greeks calculation with advanced analytics"""
    
    def __init__(self, spot: float, strike: float, expiry_days: float, 
                 interest_rate: float, dividend_yield: float,
                 option_type: str, volatility: float):
        """Initialize with option parameters"""
        self.spot = spot
        self.strike = strike
        self.expiry_days = expiry_days
        self.time_to_expiry = expiry_days / 365.0  # in years
        self.interest_rate = interest_rate
        self.dividend_yield = dividend_yield
        self.option_type = option_type.upper()  # CE or PE
        self.implied_volatility = volatility
    
    def calculate_greeks(self) -> Dict[str, float]:
        """Calculate complete option greeks"""
        greeks = {}
        
        # Black-Scholes parameters
        S = self.spot
        K = self.strike
        T = self.time_to_expiry
        r = self.interest_rate
        q = self.dividend_yield
        sigma = self.implied_volatility
        
        if T <= 0:
            # Handle expired options
            if self.option_type == "CE":
                greeks["price"] = max(0, S - K)
            else:
                greeks["price"] = max(0, K - S)
            greeks["delta"] = 0
            greeks["gamma"] = 0
            greeks["theta"] = 0
            greeks["vega"] = 0
            greeks["rho"] = 0
            return greeks
        
        # d1 and d2 calculations
        d1 = (np.log(S / K) + (r - q + 0.5 * sigma**2) * T) / (sigma * np.sqrt(T))
        d2 = d1 - sigma * np.sqrt(T)
        
        # Price calculation
        if self.option_type == "CE":
            greeks["price"] = S * np.exp(-q * T) * stats.norm.cdf(d1) - K * np.exp(-r * T) * stats.norm.cdf(d2)
            greeks["delta"] = np.exp(-q * T) * stats.norm.cdf(d1)
            greeks["rho"] = K * T * np.exp(-r * T) * stats.norm.cdf(d2) / 100
        else:
            greeks["price"] = K * np.exp(-r * T) * stats.norm.cdf(-d2) - S * np.exp(-q * T) * stats.norm.cdf(-d1)
            greeks["delta"] = -np.exp(-q * T) * stats.norm.cdf(-d1)
            greeks["rho"] = -K * T * np.exp(-r * T) * stats.norm.cdf(-d2) / 100
        
        # Common greeks
        greeks["gamma"] = np.exp(-q * T) * stats.norm.pdf(d1) / (S * sigma * np.sqrt(T))
        greeks["vega"] = S * np.exp(-q * T) * stats.norm.pdf(d1) * np.sqrt(T) / 100
        greeks["theta"] = (-S * np.exp(-q * T) * stats.norm.pdf(d1) * sigma / (2 * np.sqrt(T)) 
                          - r * K * np.exp(-r * T) * stats.norm.cdf(d2 if self.option_type == "CE" else -d2) 
                          + q * S * np.exp(-q * T) * stats.norm.cdf(d1 if self.option_type == "CE" else -d1)) / 365
        
        # Advanced greeks
        greeks["charm"] = self._calculate_charm(S, K, T, r, q, sigma, d1, d2)
        greeks["vomma"] = self._calculate_vomma(S, K, T, r, q, sigma, d1)
        greeks["vanna"] = self._calculate_vanna(S, K, T, r, q, sigma, d1)
        greeks["color"] = self._calculate_color(S, K, T, r, q, sigma, d1, d2)
        greeks["speed"] = self._calculate_speed(S, K, T, r, q, sigma, d1)
        greeks["zomma"] = self._calculate_zomma(S, K, T, r, q, sigma, d1)
        greeks["ultima"] = self._calculate_ultima(S, K, T, r, q, sigma, d1)
        
        # Derived metrics
        greeks["theta_decay_rate"] = -greeks["theta"] / greeks["price"] if greeks["price"] > 0 else 0
        greeks["leverage"] = greeks["delta"] * S / greeks["price"] if greeks["price"] > 0 else 0
        greeks["gamma_exposure"] = greeks["gamma"] * S * S * 0.01  # GEX for 1% move
        
        return greeks
    
    def _calculate_charm(self, S, K, T, r, q, sigma, d1, d2):
        """Calculate Charm (delta decay)"""
        if self.option_type == "CE":
            return -q * np.exp(-q * T) * stats.norm.cdf(d1) - np.exp(-q * T) * stats.norm.pdf(d1) * (
                (2 * (r - q) - sigma**2) / (2 * sigma * np.sqrt(T)) - d2 / (2 * T))
        else:
            return q * np.exp(-q * T) * stats.norm.cdf(-d1) - np.exp(-q * T) * stats.norm.pdf(d1) * (
                (2 * (r - q) - sigma**2) / (2 * sigma * np.sqrt(T)) - d2 / (2 * T))
    
    def _calculate_vomma(self, S, K, T, r, q, sigma, d1):
        """Calculate Vomma (vega convexity)"""
        return S * np.exp(-q * T) * stats.norm.pdf(d1) * np.sqrt(T) * d1 * d1 / sigma
    
    def _calculate_vanna(self, S, K, T, r, q, sigma, d1):
        """Calculate Vanna (delta sensitivity to vol changes)"""
        return -np.exp(-q * T) * stats.norm.pdf(d1) * d1 / sigma
    
    def _calculate_color(self, S, K, T, r, q, sigma, d1, d2):
        """Calculate Color (gamma decay) - dGamma/dt"""
        term1 = -np.exp(-q * T) * stats.norm.pdf(d1) / (2 * S * T * sigma * np.sqrt(T))
        term2 = (2 * (r - q) + sigma**2) / (2 * sigma * np.sqrt(T))
        term3 = d1 * d2 / (sigma * np.sqrt(T))
        return term1 * (term2 + term3)
    
    def _calculate_speed(self, S, K, T, r, q, sigma, d1):
        """Calculate Speed (dGamma/dS) - third derivative of price with respect to spot"""
        return -np.exp(-q * T) * stats.norm.pdf(d1) * d1 / (S * S * sigma * np.sqrt(T)) * (1 + d1 / (sigma * np.sqrt(T)))
    
    def _calculate_zomma(self, S, K, T, r, q, sigma, d1):
        """Calculate Zomma (dGamma/dVol) - third derivative of price with respect to vol and spot"""
        return np.exp(-q * T) * stats.norm.pdf(d1) * ((d1 * d1 - 1) / (sigma * S * np.sqrt(T)))
    
    def _calculate_ultima(self, S, K, T, r, q, sigma, d1):
        """Calculate Ultima (dVomma/dVol) - third derivative of price with respect to vol"""
        d1_squared = d1 * d1
        return -np.exp(-q * T) * stats.norm.pdf(d1) * np.sqrt(T) / (sigma * sigma) * (
            d1_squared * d1_squared - 6 * d1_squared + 3)
    
    @staticmethod
    @lru_cache(maxsize=1024)
    def black_scholes_price(spot: float, strike: float, expiry_days: float, 
                            interest_rate: float, dividend_yield: float,
                            volatility: float, option_type: str) -> float:
        """Cached Black-Scholes price calculation"""
        T = expiry_days / 365.0  # in years
        if T <= 0:
            if option_type.upper() == "CE":
                return max(0, spot - strike)
            else:
                return max(0, strike - spot)
        
        S = spot
        K = strike
        r = interest_rate
        q = dividend_yield
        sigma = volatility
        
        d1 = (np.log(S / K) + (r - q + 0.5 * sigma**2) * T) / (sigma * np.sqrt(T))
        d2 = d1 - sigma * np.sqrt(T)
        
        if option_type.upper() == "CE":
            return S * np.exp(-q * T) * stats.norm.cdf(d1) - K * np.exp(-r * T) * stats.norm.cdf(d2)
        else:
            return K * np.exp(-r * T) * stats.norm.cdf(-d2) - S * np.exp(-q * T) * stats.norm.cdf(-d1)
    
    @classmethod
    def estimate_implied_volatility(cls, market_price: float, 
                                   spot: float, strike: float, 
                                   expiry_days: float, 
                                   interest_rate: float, 
                                   dividend_yield: float, 
                                   option_type: str) -> float:
        """Estimate implied volatility using numerical methods"""
        def objective_function(sigma):
            price = cls.black_scholes_price(
                spot, strike, expiry_days, interest_rate, 
                dividend_yield, sigma, option_type
            )
            return abs(price - market_price)
        
        # Start with reasonable bounds for vol
        result = optimize.minimize_scalar(objective_function, bounds=(0.01, 3.0), method='bounded')
        
        if result.success:
            return result.x
        else:
            # Fallback to historical volatility estimate
            return 0.3  # Default vol
    
    @classmethod
    def calculate_position_greeks(cls, positions: List[Dict[str, Any]], 
                                 underlying_price: float) -> Dict[str, float]:
        """Calculate aggregate Greeks for a list of positions"""
        net_greeks = {
            "delta": 0.0, "gamma": 0.0, "theta": 0.0, "vega": 0.0,
            "rho": 0.0, "charm": 0.0, "vanna": 0.0, "gamma_exposure": 0.0
        }
        
        for position in positions:
            # Skip if missing data
            if (not position.get("strike_price") or 
                not position.get("option_type") or 
                not position.get("quantity") or
                not position.get("expiry_date")):
                continue
            
            # Get position data
            strike = position.get("strike_price")
            option_type = position.get("option_type")
            qty = position.get("quantity")
            side = position.get("side", "BUY")
            
            # Calculate days to expiry
            try:
                expiry_date = datetime.strptime(position.get("expiry_date"), "%Y-%m-%d")
                days_to_expiry = max(0, (expiry_date - datetime.now()).days)
            except:
                days_to_expiry = 7  # Default fallback
            
            # Create option calculator
            option = cls(
                spot=underlying_price,
                strike=strike,
                expiry_days=days_to_expiry,
                interest_rate=DEFAULT_RISK_FREE_RATE,
                dividend_yield=DEFAULT_DIVIDEND_YIELD,
                option_type=option_type,
                volatility=position.get("implied_volatility", 0.3)
            )
            
            # Calculate Greeks
            greeks = option.calculate_greeks()
            
            # Apply quantity and direction
            multiplier = qty * (1 if side == "BUY" else -1)
            
            for greek in net_greeks:
                if greek in greeks:
                    net_greeks[greek] += greeks[greek] * multiplier
        
        return net_greeks


class VolatilitySurface:
    """Advanced volatility surface modeling with term structure"""
    
    def __init__(self):
        """Initialize volatility surface"""
        self.volatility_data = {}
        self.last_update = datetime.now()
        self.expiry_dates = []
        self.strikes = []
        self.surface_matrix = None
        self.term_structure = {}
        self.iv_percentile = {}
        self.iv_rank = {}
        self.skew_by_expiry = {}
        self.historical_iv = deque(maxlen=100)
        self.pcr_by_expiry = {}
    
    async def update_surface(self, option_chain: Dict[str, Any], underlying_price: float):
        """Update volatility surface with new market data"""
        try:
            if not option_chain:
                return
            
            # Extract expiry dates and strikes
            expirations = set()
            strikes = set()
            vol_data = {}
            
            # Process option chain data
            for exp_date, exp_data in option_chain.items():
                if isinstance(exp_data, dict):
                    expirations.add(exp_date)
                    exp_days = (datetime.strptime(exp_date, '%Y-%m-%d') - datetime.now()).days
                    
                    call_oi_total = 0
                    put_oi_total = 0
                    
                    for strike_str, strike_data in exp_data.items():
                        strike = float(strike_str)
                        strikes.add(strike)
                        
                        # Calculate implied volatility for calls and puts
                        for opt_type in ['ce', 'pe']:
                            if opt_type in strike_data:
                                market_price = strike_data[opt_type].get('last_price', 0)
                                if market_price > 0:
                                    try:
                                        iv = OptionGreeks.estimate_implied_volatility(
                                            market_price, 
                                            underlying_price,
                                            strike,
                                            exp_days,
                                            DEFAULT_RISK_FREE_RATE,
                                            DEFAULT_DIVIDEND_YIELD,
                                            'CE' if opt_type == 'ce' else 'PE'
                                        )
                                        
                                        key = (exp_date, strike, opt_type.upper())
                                        vol_data[key] = {
                                            'iv': iv,
                                            'price': market_price,
                                            'strike_pct': strike / underlying_price,
                                            'days_to_expiry': exp_days,
                                            'moneyness': underlying_price / strike - 1
                                        }
                                        
                                        # Accumulate OI for put/call ratio
                                        oi = strike_data[opt_type].get('oi', 0)
                                        if opt_type == 'ce':
                                            call_oi_total += oi
                                        else:
                                            put_oi_total += oi
                                    except:
                                        pass  # Skip calculation errors
                    
                    # Calculate put/call ratio
                    if call_oi_total > 0:
                        self.pcr_by_expiry[exp_date] = put_oi_total / call_oi_total
                    else:
                        self.pcr_by_expiry[exp_date] = 1.0
            
            # Update internal data
            self.volatility_data = vol_data
            self.expiry_dates = sorted(list(expirations))
            self.strikes = sorted(list(strikes))
            self.last_update = datetime.now()
            
            # Create surface matrix
            self._build_surface_matrix()
            
            # Calculate term structure
            self._calculate_term_structure(underlying_price)
            
            # Track historical IV
            if len(self.term_structure) > 0:
                # Use ATM 30-day volatility as representative IV
                closest_expiry = min(self.term_structure.keys(), key=lambda x: abs(x - 30))
                self.historical_iv.append(self.term_structure[closest_expiry])
                
                # Calculate IV rank and percentile
                if len(self.historical_iv) > 10:
                    current_iv = self.term_structure[closest_expiry]
                    iv_min = min(self.historical_iv)
                    iv_max = max(self.historical_iv)
                    
                    if iv_max > iv_min:
                        self.iv_rank[30] = (current_iv - iv_min) / (iv_max - iv_min)
                    else:
                        self.iv_rank[30] = 0.5
                    
                    self.iv_percentile[30] = sum(1 for iv in self.historical_iv if iv <= current_iv) / len(self.historical_iv)
            
            # Calculate skew metrics for each expiry
            for exp_date in self.expiry_dates:
                self.skew_by_expiry[exp_date] = self.get_iv_skew(exp_date)
            
        except Exception as e:
            logger.error(f"❌ Error updating volatility surface: {e}")
    
    def _build_surface_matrix(self):
        """Build interpolated volatility surface"""
        if not self.expiry_dates or not self.strikes:
            return
        
        # Create empty matrix
        n_expiries = len(self.expiry_dates)
        n_strikes = len(self.strikes)
        self.surface_matrix = np.zeros((n_expiries, n_strikes, 2))  # Call and Put IVs
        
        # Fill with available data
        for i, exp_date in enumerate(self.expiry_dates):
            for j, strike in enumerate(self.strikes):
                for k, opt_type in enumerate(['CE', 'PE']):
                    key = (exp_date, strike, opt_type)
                    if key in self.volatility_data:
                        self.surface_matrix[i, j, k] = self.volatility_data[key]['iv']
        
        # Interpolate missing values
        self._interpolate_surface()
    
    def _interpolate_surface(self):
        """Interpolate missing values in volatility surface using advanced methods"""
        if self.surface_matrix is None:
            return
        
        # For each option type (call/put)
        for k in range(2):
            # Process each expiry slice
            for i in range(len(self.expiry_dates)):
                expiry_slice = self.surface_matrix[i, :, k]
                
                # Find missing values
                missing_mask = expiry_slice == 0
                valid_mask = ~missing_mask
                
                # Skip if not enough valid points
                if np.sum(valid_mask) < 3:
                    continue
                
                # Get valid indices and values
                valid_indices = np.where(valid_mask)[0]
                valid_values = expiry_slice[valid_mask]
                
                try:
                    # Use cubic spline interpolation if enough points
                    if len(valid_values) >= 4:
                        from scipy.interpolate import CubicSpline
                        cs = CubicSpline(valid_indices, valid_values)
                        missing_indices = np.where(missing_mask)[0]
                        self.surface_matrix[i, missing_indices, k] = cs(missing_indices)
                    # Fallback to linear interpolation
                    else:
                        missing_indices = np.where(missing_mask)[0]
                        self.surface_matrix[i, missing_indices, k] = np.interp(
                            missing_indices, valid_indices, valid_values
                        )
                except Exception as e:
                    logger.debug(f"Interpolation error: {e}")
                    # Simple fill with nearest valid value
                    for j in np.where(missing_mask)[0]:
                        if len(valid_indices) > 0:
                            nearest_idx = valid_indices[np.abs(valid_indices - j).argmin()]
                            self.surface_matrix[i, j, k] = self.surface_matrix[i, nearest_idx, k]
    
    def _calculate_term_structure(self, underlying_price: float):
        """Calculate volatility term structure (IV vs time to expiry)"""
        self.term_structure = {}
        
        # For each expiry, get ATM volatility
        for i, exp_date in enumerate(self.expiry_dates):
            try:
                # Get days to expiry
                exp_days = (datetime.strptime(exp_date, '%Y-%m-%d') - datetime.now()).days
                
                # Find ATM strike (closest to underlying price)
                atm_idx = np.abs(np.array(self.strikes) - underlying_price).argmin()
                
                # Get average of call and put IV
                call_iv = self.surface_matrix[i, atm_idx, 0]
                put_iv = self.surface_matrix[i, atm_idx, 1]
                
                # Use average if both available, otherwise use the available one
                if call_iv > 0 and put_iv > 0:
                    atm_iv = (call_iv + put_iv) / 2
                elif call_iv > 0:
                    atm_iv = call_iv
                elif put_iv > 0:
                    atm_iv = put_iv
                else:
                    continue
                
                self.term_structure[exp_days] = atm_iv
            except Exception as e:
                logger.debug(f"Term structure calculation error: {e}")
    
    def get_iv(self, strike: float, expiry_date: str, option_type: str) -> float:
        """Get interpolated implied volatility for given strike and expiry"""
        try:
            if not self.surface_matrix is None:
                # Find nearest expiry and strike
                exp_idx = self._find_nearest_index(self.expiry_dates, expiry_date)
                strike_idx = self._find_nearest_index(self.strikes, strike)
                opt_idx = 0 if option_type.upper() == 'CE' else 1
                
                return self.surface_matrix[exp_idx, strike_idx, opt_idx]
            
            # Direct lookup
            key = (expiry_date, strike, option_type.upper())
            if key in self.volatility_data:
                return self.volatility_data[key]['iv']
                
            return 0.3  # Default fallback volatility
            
        except Exception as e:
            logger.error(f"❌ Error getting IV for {strike}/{expiry_date}/{option_type}: {e}")
            return 0.3  # Default volatility
    
    def _find_nearest_index(self, arr, value):
        """Find nearest value index in array"""
        if isinstance(value, str):
            if value in arr:
                return arr.index(value)
            # Handle date comparison
            if '-' in value:
                target_date = datetime.strptime(value, '%Y-%m-%d')
                date_diffs = [abs((datetime.strptime(d, '%Y-%m-%d') - target_date).days) for d in arr]
                return np.argmin(date_diffs)
            return 0
        else:
            # Numeric value
            idx = np.abs(np.array(arr) - value).argmin()
            return idx
    
    def get_iv_skew(self, expiry_date: str) -> Dict[str, float]:
        """Calculate volatility skew metrics for given expiry"""
        try:
            if not self.expiry_dates or expiry_date not in self.expiry_dates:
                return {"skew": 0, "smile": 0}
                
            exp_idx = self.expiry_dates.index(expiry_date)
            
            # Get call and put IVs for this expiry
            call_ivs = self.surface_matrix[exp_idx, :, 0]
            put_ivs = self.surface_matrix[exp_idx, :, 1]
            
            # Calculate skew (high strikes vs low strikes)
            high_idx = len(self.strikes) // 4 * 3  # 75th percentile
            mid_idx = len(self.strikes) // 2       # Median
            low_idx = len(self.strikes) // 4       # 25th percentile
            
            if high_idx >= len(call_ivs) or mid_idx >= len(call_ivs) or low_idx >= len(call_ivs):
                return {"skew": 0, "smile": 0}
            
            # Skew = low strike IV - high strike IV (normalized)
            skew = (put_ivs[low_idx] - call_ivs[high_idx]) / call_ivs[mid_idx]
            
            # Smile = average of wings vs ATM
            smile = ((put_ivs[low_idx] + call_ivs[high_idx]) / 2 - call_ivs[mid_idx]) / call_ivs[mid_idx]
            
            # Wing skew = OTM put IV / OTM call IV
            wing_skew = put_ivs[low_idx] / call_ivs[high_idx] if call_ivs[high_idx] > 0 else 1.0
            
            # Convexity = curvature of the smile
            if len(call_ivs) > 5:
                try:
                    # Fit quadratic function to measure convexity
                    indices = np.array([low_idx, mid_idx, high_idx])
                    ivs = np.array([put_ivs[low_idx], call_ivs[mid_idx], call_ivs[high_idx]])
                    coeffs = np.polyfit(indices, ivs, 2)
                    convexity = coeffs[0]  # Second derivative coefficient
                except:
                    convexity = 0
            else:
                convexity = 0
            
            return {
                "skew": float(skew),
                "smile": float(smile),
                "wing_skew": float(wing_skew),
                "convexity": float(convexity),
                "put_call_iv_ratio": float(np.mean(put_ivs) / np.mean(call_ivs)) if np.mean(call_ivs) > 0 else 1.0,
                "put_call_oi_ratio": self.pcr_by_expiry.get(expiry_date, 1.0)
            }
            
        except Exception as e:
            logger.error(f"❌ Error calculating IV skew: {e}")
            return {"skew": 0, "smile": 0}
    
    def analyze_term_structure(self) -> Dict[str, Any]:
        """Analyze the volatility term structure for trading signals"""
        try:
            if not self.term_structure or len(self.term_structure) < 2:
                return {"shape": "UNKNOWN", "slope": 0, "curvature": 0}
            
            # Sort by days to expiry
            days = sorted(self.term_structure.keys())
            ivs = [self.term_structure[d] for d in days]
            
            # Calculate slope between short and long term
            if len(days) >= 2:
                short_term = days[0]
                long_term = days[-1]
                slope = (self.term_structure[long_term] - self.term_structure[short_term]) / (long_term - short_term)
            else:
                slope = 0
                
            # Determine shape
            shape = "FLAT"
            if slope > 0.001:
                shape = "CONTANGO"  # Upward sloping
            elif slope < -0.001:
                shape = "BACKWARDATION"  # Downward sloping
                
            # Calculate curvature if enough points
            curvature = 0
            if len(days) >= 3:
                try:
                    # Fit quadratic function
                    coeffs = np.polyfit(days, ivs, 2)
                    curvature = coeffs[0]  # Second derivative coefficient
                except:
                    pass
                    
            return {
                "shape": shape,
                "slope": float(slope),
                "curvature": float(curvature),
                "short_term_iv": float(self.term_structure[days[0]]) if days else 0,
                "mid_term_iv": float(self.term_structure[days[len(days)//2]]) if days else 0,
                "long_term_iv": float(self.term_structure[days[-1]]) if days else 0,
                "iv_rank": self.iv_rank.get(30, 0.5),
                "iv_percentile": self.iv_percentile.get(30, 0.5)
            }
        
        except Exception as e:
            logger.error(f"❌ Error analyzing volatility term structure: {e}")
            return {"shape": "ERROR", "slope": 0, "curvature": 0}


@dataclass
class MarketDepthAnalysis:
    """Advanced market depth and order flow analysis"""
    bid_ask_imbalance: float = 0.0
    bid_ask_spread_percent: float = 0.0
    depth_imbalance: float = 0.0
    buying_pressure: float = 0.0
    selling_pressure: float = 0.0
    absorption_rate: float = 0.0
    liquidity_score: float = 0.0
    significant_levels: List[Dict[str, Any]] = field(default_factory=list)
    order_flow_signature: str = "NEUTRAL"
    tape_speed: float = 0.0  # Speed of transactions
    block_trades: List[Dict[str, Any]] = field(default_factory=list)  # Large trades
    hidden_liquidity_estimate: float = 0.0  # Estimated hidden orders
    price_impact: float = 0.0  # Price impact per unit volume
    smart_money_flow: float = 0.0  # Smart money flow indicator
    
    @classmethod
    async def analyze(cls, market_depth_data: Dict[str, Any], 
                     trade_history: List[Dict[str, Any]]) -> 'MarketDepthAnalysis':
        """Analyze order book and trade history for market microstructure insights"""
        analysis = cls()
        
        try:
            if not market_depth_data or 'bid' not in market_depth_data or 'ask' not in market_depth_data:
                return analysis
                
            bids = market_depth_data.get('bid', [])
            asks = market_depth_data.get('ask', [])
            
            if not bids or not asks:
                return analysis
            
            # Calculate bid-ask spread
            top_bid = bids[0].get('price', 0)
            top_ask = asks[0].get('price', 0)
            mid_price = (top_bid + top_ask) / 2
            
            if mid_price > 0:
                analysis.bid_ask_spread_percent = (top_ask - top_bid) / mid_price * 100
            
            # Calculate volume imbalance
            bid_volume = sum(bid.get('quantity', 0) for bid in bids)
            ask_volume = sum(ask.get('quantity', 0) for ask in asks)
            total_volume = bid_volume + ask_volume
            
            if total_volume > 0:
                analysis.bid_ask_imbalance = (bid_volume - ask_volume) / total_volume
                analysis.depth_imbalance = analysis.bid_ask_imbalance
                
                # Determine buying/selling pressure
                if analysis.bid_ask_imbalance > 0.2:
                    analysis.buying_pressure = min(1.0, analysis.bid_ask_imbalance)
                    analysis.order_flow_signature = "BUYING_PRESSURE"
                elif analysis.bid_ask_imbalance < -0.2:
                    analysis.selling_pressure = min(1.0, -analysis.bid_ask_imbalance)
                    analysis.order_flow_signature = "SELLING_PRESSURE"
            
            # Analyze trade history for advanced order flow metrics
            if trade_history and len(trade_history) > 10:
                # Calculate trade metrics
                buy_volume = sum(trade.get('quantity', 0) for trade in trade_history 
                                if trade.get('side', '') == 'BUY')
                sell_volume = sum(trade.get('quantity', 0) for trade in trade_history 
                                 if trade.get('side', '') == 'SELL')
                
                recent_trades = trade_history[-20:]
                
                # Calculate tape speed (trades per minute)
                if len(recent_trades) >= 2:
                    first_time = datetime.fromisoformat(recent_trades[0].get('timestamp', '').replace('Z', '+00:00'))
                    last_time = datetime.fromisoformat(recent_trades[-1].get('timestamp', '').replace('Z', '+00:00'))
                    duration = (last_time - first_time).total_seconds() / 60  # minutes
                    if duration > 0:
                        analysis.tape_speed = len(recent_trades) / duration
                
                # Identify block trades (large volume)
                avg_trade_size = (buy_volume + sell_volume) / len(trade_history)
                analysis.block_trades = [
                    trade for trade in trade_history
                    if trade.get('quantity', 0) > avg_trade_size * 3
                ]
                
                # Calculate price impact
                if len(recent_trades) >= 5 and total_volume > 0:
                    price_start = recent_trades[0].get('price', mid_price)
                    price_end = recent_trades[-1].get('price', mid_price)
                    volume_sum = sum(t.get('quantity', 0) for t in recent_trades)
                    if volume_sum > 0:
                        analysis.price_impact = abs(price_end - price_start) / price_start / volume_sum * 10000
                
                # Smart money flow (block trades direction)
                block_buy_vol = sum(trade.get('quantity', 0) for trade in analysis.block_trades 
                                   if trade.get('side', '') == 'BUY')
                block_sell_vol = sum(trade.get('quantity', 0) for trade in analysis.block_trades 
                                    if trade.get('side', '') == 'SELL')
                
                if block_buy_vol + block_sell_vol > 0:
                    analysis.smart_money_flow = (block_buy_vol - block_sell_vol) / (block_buy_vol + block_sell_vol)
                
                # Detect hidden liquidity
                if total_volume > 0:
                    trade_volume = buy_volume + sell_volume
                    analysis.absorption_rate = trade_volume / total_volume
                    analysis.hidden_liquidity_estimate = max(0, (trade_volume - total_volume) / trade_volume) if trade_volume > total_volume else 0
                    
                    # Determine liquidity score
                    analysis.liquidity_score = (1 - analysis.bid_ask_spread_percent / 2) * (
                        0.5 + analysis.absorption_rate / 2)
                    
                    # Detect significant price levels
                    analysis.significant_levels = cls._detect_significant_levels(
                        bids, asks, trade_history, mid_price)
                    
                    # Refine order flow signature based on trades and market depth
                    if buy_volume > sell_volume * 1.5 and analysis.buying_pressure > 0.4:
                        if analysis.tape_speed > 10:  # Fast tape
                            analysis.order_flow_signature = "AGGRESSIVE_BUYING"
                        else:
                            analysis.order_flow_signature = "STEADY_BUYING"
                    elif sell_volume > buy_volume * 1.5 and analysis.selling_pressure > 0.4:
                        if analysis.tape_speed > 10:  # Fast tape
                            analysis.order_flow_signature = "AGGRESSIVE_SELLING"
                        else:
                            analysis.order_flow_signature = "STEADY_SELLING"
                    elif analysis.absorption_rate > 0.8:
                        analysis.order_flow_signature = "HIGH_ABSORPTION"
                    elif analysis.smart_money_flow > 0.5:
                        analysis.order_flow_signature = "SMART_MONEY_BUYING"
                    elif analysis.smart_money_flow < -0.5:
                        analysis.order_flow_signature = "SMART_MONEY_SELLING"
            
            return analysis
            
        except Exception as e:
            logger.error(f"❌ Error in market depth analysis: {e}")
            return analysis
    
    @staticmethod
    def _detect_significant_levels(bids, asks, trades, mid_price):
        """Detect significant support/resistance levels from order book and trades"""
        significant_levels = []
        
        # Group bid/ask volumes by price (rounded to nearest tick)
        grouped_bids = {}
        grouped_asks = {}
        
        for bid in bids:
            price = bid.get('price', 0)
            qty = bid.get('quantity', 0)
            rounded_price = round(price * 20) / 20  # Round to nearest 0.05
            if rounded_price in grouped_bids:
                grouped_bids[rounded_price] += qty
            else:
                grouped_bids[rounded_price] = qty
                
        for ask in asks:
            price = ask.get('price', 0)
            qty = ask.get('quantity', 0)
            rounded_price = round(price * 20) / 20  # Round to nearest 0.05
            if rounded_price in grouped_asks:
                grouped_asks[rounded_price] += qty
            else:
                grouped_asks[rounded_price] = qty
        
        # Find peaks in bid volume (support)
        bid_prices = sorted(grouped_bids.keys())
        for i in range(1, len(bid_prices) - 1):
            price = bid_prices[i]
            vol = grouped_bids[price]
            if (vol > grouped_bids[bid_prices[i-1]] and 
                vol > grouped_bids[bid_prices[i+1]] and
                vol > np.mean(list(grouped_bids.values())) * 2):
                
                strength = vol / np.mean(list(grouped_bids.values()))
                significant_levels.append({
                    'price': price,
                    'type': 'SUPPORT',
                    'strength': min(1.0, strength / 5),
                    'distance': abs(price - mid_price) / mid_price
                })
        
        # Find peaks in ask volume (resistance)
        ask_prices = sorted(grouped_asks.keys())
        for i in range(1, len(ask_prices) - 1):
            price = ask_prices[i]
            vol = grouped_asks[price]
            if (vol > grouped_asks[ask_prices[i-1]] and 
                vol > grouped_asks[ask_prices[i+1]] and
                vol > np.mean(list(grouped_asks.values())) * 2):
                
                strength = vol / np.mean(list(grouped_asks.values()))
                significant_levels.append({
                    'price': price,
                    'type': 'RESISTANCE',
                    'strength': min(1.0, strength / 5),
                    'distance': abs(price - mid_price) / mid_price
                })
        
        # Identify historical trade clusters
        price_clusters = {}
        for trade in trades:
            price = trade.get('price', 0)
            qty = trade.get('quantity', 0)
            if price == 0:
                continue
                
            rounded_price = round(price * 20) / 20
            if rounded_price in price_clusters:
                price_clusters[rounded_price]['volume'] += qty
                price_clusters[rounded_price]['count'] += 1
            else:
                price_clusters[rounded_price] = {
                    'volume': qty,
                    'count': 1
                }
        
        # Identify high-volume price levels from trades
        if price_clusters:
            avg_volume = np.mean([data['volume'] for data in price_clusters.values()])
            for price, data in price_clusters.items():
                if data['volume'] > avg_volume * 2 and data['count'] > 5:
                    level_type = 'RESISTANCE' if price > mid_price else 'SUPPORT'
                    
                    # Check if not already in significant_levels
                    if not any(abs(level['price'] - price) / price < 0.001 for level in significant_levels):
                        significant_levels.append({
                            'price': price,
                            'type': level_type,
                            'strength': min(1.0, data['volume'] / avg_volume / 3),
                            'distance': abs(price - mid_price) / mid_price
                        })
        
        # Sort by distance from mid price
        significant_levels.sort(key=lambda x: x['distance'])
        
        return significant_levels[:7]  # Return top 7 levels
    
    def get_trading_signals(self) -> Dict[str, Any]:
        """Derive trading signals from order flow analysis"""
        signals = {
            "order_imbalance": self.bid_ask_imbalance,
            "strength": max(self.buying_pressure, self.selling_pressure),
            "direction": 1 if self.buying_pressure > self.selling_pressure else -1,
            "conviction": 0.0,
            "suggested_action": "WAIT"
        }
        
        # Calculate conviction based on multiple factors
        conviction_factors = []
        
        # Factor 1: Order imbalance
        if abs(self.bid_ask_imbalance) > 0.3:
            conviction_factors.append(abs(self.bid_ask_imbalance))
            
        # Factor 2: Smart money flow
        if abs(self.smart_money_flow) > 0.3:
            conviction_factors.append(abs(self.smart_money_flow) * 1.5)  # Higher weight to smart money
        
        # Factor 3: Price impact
        if self.price_impact > 0:
            normalized_impact = min(1.0, self.price_impact / 0.5)  # Normalize with max expected impact of 0.5
            conviction_factors.append(normalized_impact)
        
        # Factor 4: Significant levels proximity
        nearest_level = None
        for level in self.significant_levels:
            if nearest_level is None or level['distance'] < nearest_level['distance']:
                nearest_level = level
        
        if nearest_level and nearest_level['distance'] < 0.005:  # Within 0.5%
            conviction_factors.append(nearest_level['strength'] * (1 - nearest_level['distance'] * 100))
            
            # Add level type as context
            if nearest_level['type'] == 'SUPPORT' and signals['direction'] > 0:
                signals['context'] = "BOUNCING_OFF_SUPPORT"
            elif nearest_level['type'] == 'RESISTANCE' and signals['direction'] < 0:
                signals['context'] = "BREAKING_RESISTANCE"
        
        # Calculate overall conviction
        if conviction_factors:
            signals['conviction'] = min(1.0, sum(conviction_factors) / len(conviction_factors))
            
            # Determine suggested action based on conviction and direction
            if signals['conviction'] > 0.7:
                if signals['direction'] > 0:
                    signals['suggested_action'] = "STRONG_BUY"
                else:
                    signals['suggested_action'] = "STRONG_SELL"
            elif signals['conviction'] > 0.4:
                if signals['direction'] > 0:
                    signals['suggested_action'] = "BUY"
                else:
                    signals['suggested_action'] = "SELL"
            elif signals['conviction'] > 0.2:
                if signals['direction'] > 0:
                    signals['suggested_action'] = "WEAK_BUY"
                else:
                    signals['suggested_action'] = "WEAK_SELL"
        
        return signals


@dataclass
class TradingSignal:
    """Advanced trading signal with comprehensive metadata"""
    signal_id: str
    signal_type: SignalType
    underlying: str
    instruments: List[Dict[str, Any]]  # Multiple legs for spreads/combos
    confidence: float
    entry_prices: Dict[str, float]
    target_price: float
    stop_loss: float
    reasoning: str
    market_analysis: Dict[str, Any]
    risk_reward_ratio: float
    timestamp: datetime
    expected_duration: str
    execution_style: ExecutionStyle
    timeframe: TimeFrame
    model_used: str
    position_sizing: Dict[str, Any]
    
    @classmethod
    def create(cls, signal_type: SignalType, underlying: str, 
              instruments: List[Dict[str, Any]], confidence: float,
              entry_prices: Dict[str, float], target_price: float,
              stop_loss: float, reasoning: str, market_analysis: Dict[str, Any], 
              risk_reward_ratio: float, expected_duration: str = "INTRADAY",
              execution_style: ExecutionStyle = ExecutionStyle.SMART,
              timeframe: TimeFrame = TimeFrame.FIVE_MINUTE,
              model_used: str = "ENSEMBLE",
              position_sizing: Optional[Dict[str, Any]] = None):
        """Factory method to create a signal with ID and timestamp"""
        if position_sizing is None:
            position_sizing = {
                "risk_percent": 1.0,
                "position_value": 0.0,
                "margin_required": 0.0,
                "max_drawdown": 0.0
            }
            
        return cls(
            signal_id=f"SIG_{uuid.uuid4().hex[:8].upper()}",
            signal_type=signal_type,
            underlying=underlying,
            instruments=instruments,
            confidence=confidence,
            entry_prices=entry_prices,
            target_price=target_price,
            stop_loss=stop_loss,
            reasoning=reasoning,
            market_analysis=market_analysis,
            risk_reward_ratio=risk_reward_ratio,
            timestamp=datetime.now(),
            expected_duration=expected_duration,
            execution_style=execution_style,
            timeframe=timeframe,
            model_used=model_used,
            position_sizing=position_sizing
        )


@dataclass
class PositionLeg:
    """Individual leg of a position"""
    instrument: Dict[str, Any]
    quantity: int
    entry_price: float
    current_price: float
    side: str  # BUY or SELL
    option_type: str  # CE or PE
    strike_price: float
    expiry_date: str
    leg_pnl: float
    greeks: Dict[str, float]
    orders: List[Dict[str, Any]]
    leg_type: str  # MAIN, HEDGE, ADJUSTMENT
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to serializable dictionary"""
        result = asdict(self)
        result['greeks'] = {k: float(v) for k, v in self.greeks.items()}
        return result


@dataclass
class PositionManager:
    """Advanced position management with Greeks tracking"""
    position_id: str
    underlying: str
    legs: List[PositionLeg]
    current_pnl: float
    unrealized_pnl: float
    max_profit: float
    max_loss: float
    entry_time: datetime
    last_update: datetime
    is_active: bool
    strategy_type: str
    greeks: Dict[str, float]  # Net position Greeks
    exit_conditions: Dict[str, Any]
    risk_metrics: Dict[str, float]
    trade_journal: List[Dict[str, Any]]
    
    def update_greeks(self, underlying_price: float, volatility_surface: VolatilitySurface):
        """Update position Greeks"""
        net_delta = 0.0
        net_gamma = 0.0
        net_theta = 0.0
        net_vega = 0.0
        net_rho = 0.0
        net_vanna = 0.0
        net_charm = 0.0
        
        for leg in self.legs:
            # Skip if missing data
            if not leg.instrument or not leg.strike_price or not leg.expiry_date:
                continue
                
            strike = leg.strike_price
            option_type = leg.option_type
            
            # Calculate days to expiry
            try:
                expiry_date = datetime.strptime(leg.expiry_date, "%Y-%m-%d")
                days_to_expiry = max(0, (expiry_date - datetime.now()).days)
            except:
                days_to_expiry = 7  # Default fallback
            
                        # Get IV from surface
            iv = volatility_surface.get_iv(strike, leg.expiry_date, option_type)
            
            # Calculate greeks
            option = OptionGreeks(
                spot=underlying_price,
                strike=strike,
                expiry_days=days_to_expiry,
                interest_rate=DEFAULT_RISK_FREE_RATE,
                dividend_yield=DEFAULT_DIVIDEND_YIELD,
                option_type=option_type,
                volatility=iv
            )
            
            greeks = option.calculate_greeks()
            leg.greeks = greeks
            
            # Apply quantity and direction
            multiplier = leg.quantity * (1 if leg.side == "BUY" else -1)
            
            net_delta += greeks.get("delta", 0) * multiplier
            net_gamma += greeks.get("gamma", 0) * multiplier
            net_theta += greeks.get("theta", 0) * multiplier
            net_vega += greeks.get("vega", 0) * multiplier
            net_rho += greeks.get("rho", 0) * multiplier
            net_vanna += greeks.get("vanna", 0) * multiplier
            net_charm += greeks.get("charm", 0) * multiplier
        
        # Update position Greeks
        self.greeks = {
            "delta": net_delta,
            "gamma": net_gamma,
            "theta": net_theta,
            "vega": net_vega,
            "rho": net_rho,
            "vanna": net_vanna,
            "charm": net_charm,
            "weighted_delta": net_delta / max(abs(sum(leg.quantity for leg in self.legs)), 1),
            "delta_dollars": net_delta * underlying_price,
            "gamma_dollars": net_gamma * underlying_price * underlying_price * 0.01  # Dollar impact of 1% move
        }
        
        # Update risk metrics based on greeks
        self.risk_metrics["delta_exposure"] = abs(self.greeks["delta"])
        self.risk_metrics["gamma_risk"] = self.greeks["gamma"]
        self.risk_metrics["theta_burn"] = -self.greeks["theta"]
        self.risk_metrics["vega_exposure"] = abs(self.greeks["vega"])
    
    def update_pnl(self) -> float:
        """Update position P&L based on current prices"""
        total_pnl = 0.0
        
        for leg in self.legs:
            # Calculate P&L based on direction (long/short)
            if leg.side == "BUY":
                leg_pnl = (leg.current_price - leg.entry_price) * leg.quantity
            else:  # SELL
                leg_pnl = (leg.entry_price - leg.current_price) * leg.quantity
                
            leg.leg_pnl = leg_pnl
            total_pnl += leg_pnl
        
        self.unrealized_pnl = total_pnl
        
        # Track max profit/loss
        if total_pnl > self.max_profit:
            self.max_profit = total_pnl
        if total_pnl < self.max_loss:
            self.max_loss = total_pnl
            
        # Calculate drawdown from max profit
        if self.max_profit > 0:
            drawdown = (self.max_profit - total_pnl) / self.max_profit if self.max_profit > 0 else 0
            self.risk_metrics["current_drawdown"] = max(0, drawdown)
            
        return total_pnl
    
    def add_journal_entry(self, action: str, details: Dict[str, Any]):
        """Add entry to trade journal"""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "action": action,
            "pnl": self.unrealized_pnl,
            "details": details
        }
        self.trade_journal.append(entry)
        
        # Log to trade journal
        trade_logger.info(f"[{self.position_id}] {action}: PnL=${self.unrealized_pnl:.2f} | {json.dumps(details)}")
    
    def check_adjustment_needed(self) -> Tuple[bool, str, Dict[str, Any]]:
        """Check if position needs adjustment based on Greeks and metrics"""
        adjustment_needed = False
        reason = ""
        adjustment_details = {}
        
        # Too much delta risk (more than 30% of max position delta)
        if abs(self.greeks.get("delta", 0)) > MAX_POSITION_DELTA:
            adjustment_needed = True
            reason = "HIGH_DELTA_EXPOSURE"
            adjustment_details = {
                "current_delta": self.greeks.get("delta", 0),
                "target_delta": self.greeks.get("delta", 0) * 0.5,  # Reduce by half
                "adjustment_type": "DELTA_HEDGE"
            }
        
        # Too much gamma risk near expiration
        closest_expiry = min([datetime.strptime(leg.expiry_date, "%Y-%m-%d") for leg in self.legs], 
                            default=datetime.now() + timedelta(days=30))
        days_to_expiry = max(0, (closest_expiry - datetime.now()).days)
        
        if (abs(self.greeks.get("gamma", 0)) > 0.1 and days_to_expiry < 3):
            adjustment_needed = True
            reason = "HIGH_GAMMA_EXPOSURE_NEAR_EXPIRY"
            adjustment_details = {
                "current_gamma": self.greeks.get("gamma", 0),
                "days_to_expiry": days_to_expiry,
                "adjustment_type": "ROLL_POSITION"
            }
        
        # Too much vega exposure in high IV environment
        if (abs(self.greeks.get("vega", 0)) > 0.2 and 
            self.risk_metrics.get("iv_percentile", 0) > 80):
            
            adjustment_needed = True
            reason = "HIGH_VEGA_IN_HIGH_IV"
            adjustment_details = {
                "current_vega": self.greeks.get("vega", 0),
                "iv_percentile": self.risk_metrics.get("iv_percentile", 0),
                "adjustment_type": "VEGA_HEDGE"
            }
        
        # P&L drawdown exceeding threshold
        max_allowed_drawdown = 0.3  # 30% drawdown from max profit
        if (self.max_profit > 0 and 
            self.risk_metrics.get("current_drawdown", 0) > max_allowed_drawdown and
            self.unrealized_pnl > 0):
            
            adjustment_needed = True
            reason = "PROFIT_DRAWDOWN_PROTECTION"
            adjustment_details = {
                "max_profit": self.max_profit,
                "current_pnl": self.unrealized_pnl,
                "drawdown": self.risk_metrics.get("current_drawdown", 0),
                "adjustment_type": "PARTIAL_EXIT"
            }
        
        # Excessive negative theta near expiration
        if (self.greeks.get("theta", 0) < -50 and days_to_expiry < 5):
            adjustment_needed = True
            reason = "EXCESSIVE_THETA_DECAY"
            adjustment_details = {
                "current_theta": self.greeks.get("theta", 0),
                "days_to_expiry": days_to_expiry,
                "adjustment_type": "ROLL_POSITION"
            }
            
        return adjustment_needed, reason, adjustment_details
    
    def check_exit_conditions(self, current_market_regime: str) -> Tuple[bool, str]:
        """Check if position should be exited based on defined conditions"""
        should_exit = False
        exit_reason = ""
        
        # Check target price
        target = self.exit_conditions.get("target_price", float('inf'))
        if self.unrealized_pnl >= target:
            should_exit = True
            exit_reason = "TARGET_REACHED"
        
        # Check stop loss
        stop_loss = self.exit_conditions.get("stop_loss", float('-inf'))
        if self.unrealized_pnl <= stop_loss:
            should_exit = True
            exit_reason = "STOP_LOSS_HIT"
        
        # Check time-based exit
        max_duration = self.exit_conditions.get("max_duration_days", 30)
        days_open = (datetime.now() - self.entry_time).days
        if days_open >= max_duration:
            should_exit = True
            exit_reason = "MAX_DURATION_REACHED"
        
        # Check market regime change exit condition
        entry_regime = self.exit_conditions.get("entry_market_regime", "")
        if (entry_regime and 
            current_market_regime != entry_regime and
            self.exit_conditions.get("exit_on_regime_change", False)):
            
            should_exit = True
            exit_reason = f"REGIME_CHANGE_FROM_{entry_regime}_TO_{current_market_regime}"
        
        # Check technical condition exit
        if self.exit_conditions.get("technical_exit_triggered", False):
            should_exit = True
            exit_reason = "TECHNICAL_EXIT_SIGNAL"
        
        return should_exit, exit_reason
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert position to serializable dictionary"""
        result = {
            "position_id": self.position_id,
            "underlying": self.underlying,
            "legs": [leg.to_dict() for leg in self.legs],
            "current_pnl": float(self.current_pnl),
            "unrealized_pnl": float(self.unrealized_pnl),
            "max_profit": float(self.max_profit),
            "max_loss": float(self.max_loss),
            "entry_time": self.entry_time.isoformat(),
            "last_update": self.last_update.isoformat(),
            "is_active": self.is_active,
            "strategy_type": self.strategy_type,
            "greeks": {k: float(v) for k, v in self.greeks.items()},
            "risk_metrics": {k: float(v) for k, v in self.risk_metrics.items()}
        }
        return result


class DeepLearningModel:
    """Advanced deep learning model for financial time series"""
    
    def __init__(self, input_shape, output_dim=1, model_type="transformer"):
        """Initialize model architecture"""
        self.model = None
        self.input_shape = input_shape
        self.output_dim = output_dim
        self.model_type = model_type
        self.scaler = StandardScaler()
        self.history = None
        self.model_path = f"models/{model_type}_{uuid.uuid4().hex[:8]}.h5"
    
    def build_model(self):
        """Build deep learning model architecture"""
        try:
            if not TF_AVAILABLE:
                logger.warning("⚠️ TensorFlow not available, cannot build deep learning model")
                return
            
            if self.model_type == "transformer":
                self._build_transformer()
            elif self.model_type == "lstm":
                self._build_lstm()
            elif self.model_type == "cnn_lstm":
                self._build_cnn_lstm()
            else:
                logger.warning(f"⚠️ Unknown model type: {self.model_type}")
                
            logger.info(f"✅ {self.model_type.upper()} model built successfully")
            
        except Exception as e:
            logger.error(f"❌ Error building deep learning model: {e}")
    
    def _build_transformer(self):
        """Build transformer architecture for time series"""
        # Input layers
        inputs = Input(shape=self.input_shape)
        
        # CNN feature extraction for local patterns
        x = Conv1D(filters=32, kernel_size=3, padding='same', activation='relu')(inputs)
        x = BatchNormalization()(x)
        x = Conv1D(filters=64, kernel_size=3, padding='same', activation='relu')(x)
        x = BatchNormalization()(x)
        
        # Transformer encoder layers
        for _ in range(3):  # 3 transformer blocks
            # Multi-head self-attention
            attention_output = MultiHeadAttention(
                num_heads=4, key_dim=64
            )(x, x, x)
            attention_output = Dropout(0.1)(attention_output)
            x = LayerNormalization(epsilon=1e-6)(x + attention_output)
            
            # Feed-forward network
            ffn = Dense(256, activation='relu')(x)
            ffn = Dense(64)(ffn)
            ffn = Dropout(0.1)(ffn)
            x = LayerNormalization(epsilon=1e-6)(x + ffn)
        
        # Output layers
        x = GlobalAveragePooling1D()(x)
        x = Dense(64, activation='relu')(x)
        x = Dropout(0.2)(x)
        outputs = Dense(self.output_dim)(x)
        
        # Create model
        self.model = Model(inputs=inputs, outputs=outputs)
        self.model.compile(
            optimizer=Adam(learning_rate=0.001),
            loss='mse',
            metrics=['mae']
        )
    
    def _build_lstm(self):
        """Build LSTM architecture for time series"""
        self.model = Sequential([
            LSTM(128, return_sequences=True, input_shape=self.input_shape),
            Dropout(0.2),
            BatchNormalization(),
            LSTM(64, return_sequences=False),
            Dropout(0.2),
            BatchNormalization(),
            Dense(32, activation='relu'),
            Dense(self.output_dim)
        ])
        
        self.model.compile(
            optimizer=Adam(learning_rate=0.001),
            loss='mse',
            metrics=['mae']
        )
    
    def _build_cnn_lstm(self):
        """Build hybrid CNN-LSTM architecture for time series"""
        self.model = Sequential([
            # CNN for feature extraction
            Conv1D(filters=64, kernel_size=3, padding='same', activation='relu', input_shape=self.input_shape),
            BatchNormalization(),
            Conv1D(filters=128, kernel_size=5, padding='same', activation='relu'),
            BatchNormalization(),
            MaxPooling1D(pool_size=2),
            
            # LSTM layers for sequence modeling
            Bidirectional(LSTM(64, return_sequences=True)),
            Dropout(0.2),
            Bidirectional(LSTM(32, return_sequences=False)),
            Dropout(0.2),
            
            # Output layers
            Dense(32, activation='relu'),
            Dense(self.output_dim)
        ])
        
        self.model.compile(
            optimizer=Adam(learning_rate=0.0005),
            loss='mse',
            metrics=['mae']
        )
    
    def train(self, X_train, y_train, epochs=50, batch_size=32, validation_split=0.2):
        """Train the model with time series data"""
        try:
            if self.model is None:
                self.build_model()
                if self.model is None:
                    return
            
            # Scale features
            X_scaled = self.scaler.fit_transform(X_train.reshape(-1, X_train.shape[-1])).reshape(X_train.shape)
            
            # Train model
            self.history = self.model.fit(
                X_scaled, y_train,
                epochs=epochs,
                batch_size=batch_size,
                validation_split=validation_split,
                verbose=1,
                callbacks=[
                    EarlyStopping(
                        monitor='val_loss',
                        patience=10,
                        restore_best_weights=True
                    ),
                    ReduceLROnPlateau(
                        monitor='val_loss',
                        factor=0.5,
                        patience=5,
                        min_lr=0.00001
                    ),
                    ModelCheckpoint(
                        self.model_path,
                        save_best_only=True,
                        monitor='val_loss'
                    )
                ]
            )
            
            logger.info(f"✅ {self.model_type.upper()} model trained successfully")
            return self.history
            
        except Exception as e:
            logger.error(f"❌ Error training deep learning model: {e}")
    
    def predict(self, X_test):
        """Make predictions with scaled inputs"""
        try:
            if self.model is None:
                logger.warning("⚠️ Model not built, cannot make predictions")
                return None
            
            # Scale features
            X_scaled = self.scaler.transform(X_test.reshape(-1, X_test.shape[-1])).reshape(X_test.shape)
            
            # Make predictions
            return self.model.predict(X_scaled)
            
        except Exception as e:
            logger.error(f"❌ Error making predictions: {e}")
            return None
    
    def save(self, path=None):
        """Save model to disk"""
        try:
            if self.model is None:
                logger.warning("⚠️ No model to save")
                return
                
            save_path = path or self.model_path
            self.model.save(save_path)
            
            # Save scaler
            scaler_path = save_path.replace('.h5', '_scaler.pkl')
            joblib.dump(self.scaler, scaler_path)
            
            logger.info(f"✅ Model saved to {save_path}")
            
        except Exception as e:
            logger.error(f"❌ Error saving model: {e}")
    
    def load(self, path):
        """Load model from disk"""
        try:
            if not TF_AVAILABLE:
                logger.warning("⚠️ TensorFlow not available, cannot load model")
                return
                
            self.model = load_model(path)
            
            # Load scaler
            scaler_path = path.replace('.h5', '_scaler.pkl')
            if os.path.exists(scaler_path):
                self.scaler = joblib.load(scaler_path)
            
            logger.info(f"✅ Model loaded from {path}")
            
        except Exception as e:
            logger.error(f"❌ Error loading model: {e}")


class MarketRegimeDetector:
    """Market regime detection using statistical methods and machine learning"""
    
    def __init__(self):
        """Initialize regime detector"""
        self.model = None
        self.last_regime = MarketRegime.SIDEWAYS
        self.regime_history = deque(maxlen=20)
        self.history_length = 100
        self.min_samples = 60
    
    def train(self, price_data: pd.DataFrame):
        """Train market regime detector model"""
        try:
            if len(price_data) < self.min_samples:
                logger.warning(f"⚠️ Insufficient data for regime detection (need {self.min_samples} samples)")
                return
            
            # Calculate returns
            if 'close' in price_data.columns:
                price_data['returns'] = price_data['close'].pct_change().fillna(0)
                
                # Use Markov regime switching model
                if not price_data['returns'].isna().any() and len(price_data) >= 60:
                    try:
                        # 2-state Markov model (bull/bear)
                        self.model = MarkovRegression(
                            price_data['returns'].values, k_regimes=2, trend='c', switching_variance=True
                        )
                        self.model = self.model.fit()
                        logger.info("✅ Markov regime switching model trained")
                    except Exception as e:
                        logger.error(f"❌ Error training Markov model: {e}")
                
            logger.info("✅ Market regime detector trained")
            
        except Exception as e:
            logger.error(f"❌ Error training regime detector: {e}")
    
    def detect_regime(self, market_data: Dict[str, Any]) -> MarketRegime:
        """Detect current market regime from market data"""
        try:
            # Extract key metrics
            if not market_data:
                return self.last_regime
            
            # 1. Calculate trend strength
            trend_strength = self._calculate_trend_strength(market_data)
            
            # 2. Calculate volatility
            volatility = self._calculate_volatility(market_data)
            
            # 3. Calculate momentum
            momentum = self._calculate_momentum(market_data)
            
            # 4. Calculate mean reversion tendency
            mean_reversion = self._calculate_mean_reversion(market_data)
            
            # Determine market regime
            regime = MarketRegime.from_indicators(
                trend_strength, volatility, momentum, mean_reversion
            )
            
            # Check if regime change is significant
            if regime != self.last_regime:
                # Only confirm regime change if it's persisted for a while or is a major change
                self.regime_history.append(regime)
                
                # Check if new regime appears in majority of recent history
                counts = {}
                for r in self.regime_history:
                    counts[r] = counts.get(r, 0) + 1
                
                most_common = max(counts.items(), key=lambda x: x[1])
                if most_common[0] == regime and most_common[1] >= 3:
                    # Regime change confirmed
                    logger.info(f"📊 Market regime change: {self.last_regime.value} -> {regime.value}")
                    self.last_regime = regime
                else:
                    # Not confirmed yet, return previous regime
                    regime = self.last_regime
            
            return regime
            
        except Exception as e:
            logger.error(f"❌ Error detecting market regime: {e}")
            return self.last_regime
    
    def _calculate_trend_strength(self, market_data: Dict[str, Any]) -> float:
        """Calculate trend strength (-1 to 1, with 1 being strong uptrend)"""
        try:
            # Use price data history
            if 'price_history' not in market_data or len(market_data['price_history']) < 10:
                return 0.0
            
            prices = [p.get('close', 0) for p in market_data['price_history']]
            
            # Calculate moving averages
            if len(prices) >= 50:
                ma20 = sum(prices[-20:]) / 20
                ma50 = sum(prices[-50:]) / 50
                
                # Fast MA above/below slow MA
                ma_factor = 1 if ma20 > ma50 else -1
                
                # Slope of recent prices
                recent_slope = (prices[-1] - prices[-10]) / prices[-10] if prices[-10] > 0 else 0
                
                # Overall trend strength (-1 to 1)
                trend_strength = ma_factor * min(1.0, abs(recent_slope) * 20)
                return trend_strength
            else:
                # Simple calculation for limited data
                return (prices[-1] - prices[0]) / prices[0] if prices[0] > 0 else 0
                
        except Exception as e:
            logger.debug(f"Error calculating trend strength: {e}")
            return 0.0
    
    def _calculate_volatility(self, market_data: Dict[str, Any]) -> float:
        """Calculate normalized volatility (0 to 1)"""
        try:
            # Use price data history
            if 'price_history' not in market_data or len(market_data['price_history']) < 10:
                return 0.5  # Default to medium volatility
            
            prices = [p.get('close', 0) for p in market_data['price_history']]
            returns = [(prices[i] / prices[i-1] - 1) for i in range(1, len(prices))]
            
            # Calculate volatility (standard deviation of returns)
            if returns:
                vol = np.std(returns) * np.sqrt(252)  # Annualized volatility
                
                # Normalize to 0-1 scale (typical market vol range is 0.1 to 0.4)
                norm_vol = min(1.0, max(0.0, (vol - 0.05) / 0.35))
                return norm_vol
            else:
                return 0.5
                
        except Exception as e:
            logger.debug(f"Error calculating volatility: {e}")
            return 0.5
    
    def _calculate_momentum(self, market_data: Dict[str, Any]) -> float:
        """Calculate momentum strength (-1 to 1)"""
        try:
            # Use price data history
            if 'price_history' not in market_data or len(market_data['price_history']) < 20:
                return 0.0
            
            prices = [p.get('close', 0) for p in market_data['price_history']]
            
            # Calculate returns over different periods
            ret_1d = (prices[-1] / prices[-2] - 1) if prices[-2] > 0 else 0
            ret_5d = (prices[-1] / prices[-6] - 1) if len(prices) > 5 and prices[-6] > 0 else 0
            ret_20d = (prices[-1] / prices[-21] - 1) if len(prices) > 20 and prices[-21] > 0 else 0
            
            # Weight recent returns more heavily
            momentum = 0.5 * ret_1d + 0.3 * ret_5d + 0.2 * ret_20d
            
            # Normalize to -1 to 1
            return max(-1.0, min(1.0, momentum * 10))  # Scale by 10 for better sensitivity
                
        except Exception as e:
            logger.debug(f"Error calculating momentum: {e}")
            return 0.0
    
    def _calculate_mean_reversion(self, market_data: Dict[str, Any]) -> float:
        """Calculate mean reversion tendency (0 to 1)"""
        try:
            # Use price data history
            if 'price_history' not in market_data or len(market_data['price_history']) < 30:
                return 0.0
            
            prices = [p.get('close', 0) for p in market_data['price_history']]
            returns = [(prices[i] / prices[i-1] - 1) for i in range(1, len(prices))]
            
            if len(returns) < 30:
                return 0.0
            
            # Calculate autocorrelation of returns (negative indicates mean reversion)
            lag1_autocorr = np.corrcoef(returns[:-1], returns[1:])[0, 1]
            
            # Test for stationarity (ADF test)
            try:
                adf_result = adfuller(prices)
                is_stationary = adf_result[1] < 0.05  # p-value < 0.05 suggests stationarity
            except:
                is_stationary = False
            
            # Calculate distance from moving average
            ma20 = sum(prices[-20:]) / 20
            distance_from_ma = abs(prices[-1] - ma20) / ma20
            
            # Combine signals (negative autocorrelation and stationarity suggest mean reversion)
            mean_reversion_score = 0.0
            
            if lag1_autocorr < -0.1:
                mean_reversion_score += 0.4
            
            if is_stationary:
                mean_reversion_score += 0.3
            
            if distance_from_ma > 0.02:  # More than 2% away from MA
                mean_reversion_score += 0.3 * min(1.0, distance_from_ma * 10)  # Cap at 1
            
            return min(1.0, mean_reversion_score)
                
        except Exception as e:
            logger.debug(f"Error calculating mean reversion: {e}")
            return 0.0


class AITradingEngine:
    """
    Institutional-Grade AI Trading Engine
    
    Advanced Features:
    - Deep neural network architectures with attention mechanisms
    - Options pricing with full Greeks calculation
    - Volatility surface modeling and skew analysis
    - Market microstructure and order flow analysis
    - Dynamic position adjustments based on Greeks
    - Advanced execution algorithms
    - Comprehensive risk management
    """
    
    def __init__(self):
        self.is_running = False
        self.active_positions: Dict[str, PositionManager] = {}
        self.pending_orders: Dict[str, Order] = {}
        self.daily_pnl = 0.0
        self.max_daily_loss = settings.MAX_DAILY_LOSS
        self.max_position_size = settings.MAX_POSITION_SIZE
        
        # Strategy components
        self.volatility_surface = VolatilitySurface()
        self.market_regime_detector = MarketRegimeDetector()
        self.current_market_regime = MarketRegime.SIDEWAYS
        
        # ML Models
        self.models = {}
        self.ensemble_predictions = {}
        self.feature_importance = {}
        
        # Market data storage
        self.market_data_cache = {}
        self.historical_data = {}
        self.option_chain_cache = {}
        self.trade_history = deque(maxlen=1000)
        self.volatility_history = deque(maxlen=100)
        
        # Feature stores
        self.feature_store = {}
        self.technical_indicators = {}
        
        # Trading parameters
        self.risk_percentage = settings.RISK_PERCENTAGE
        self.trailing_stop_percentage = settings.TRAILING_STOP_PERCENTAGE
        
        # Services
        # self.time_service = TimeService()  # TODO: Implement TimeService if needed
        self.time_service = None
        self.market_data_service = None
        
        # Performance metrics
        self.total_trades = 0
        self.winning_trades = 0
        self.losing_trades = 0
        self.total_profit = 0.0
        self.total_loss = 0.0
        self.sharpe_ratio = 0.0
        self.max_drawdown = 0.0
        self.daily_returns = deque(maxlen=30)  # Last 30 days
        
        # Risk management
        self.portfolio_var = 0.0
        self.portfolio_beta = 1.0
        self.portfolio_correlation = {}
        self.drawdown_control_enabled = True
        self.risk_limits = {
            "max_position_count": 5,
            "max_delta_exposure": 1.0,
            "max_vega_exposure": 0.5,
            "max_gamma_exposure": 0.5,
            "max_leverage": 3.0,
            "max_sector_exposure": 0.3
        }
        
        # System status
        self.last_error = None
        self.system_health = "OK"
        self.last_heartbeat = datetime.now()
        self.initialization_timestamp = None
        
        # Real-time analysis
        self.market_depth_analysis = None
        self.sentiment_analysis = {
            "market_sentiment": 0.0,  # -1 to 1
            "fear_greed_index": 50,   # 0 to 100
            "vix_percentile": 0.5,    # 0 to 1
            "options_sentiment": 0.0   # -1 to 1 (put/call ratio derived)
        }
        
        # Current trading opportunity
        self.current_opportunities = []
    
    async def initialize(self):
        """Initialize the AI trading engine"""
        try:
            logger.info("🧠 Initializing Institutional-Grade AI Trading Engine...")
            start_time = time.time()
            
            # Register shutdown handler
            import atexit
            atexit.register(asyncio.run, self.shutdown())
            
            # Initialize market data service
            self.market_data_service = MarketDataService()
            await self.market_data_service.initialize()
            
            # Initialize ML models
            await self._initialize_ml_models()
            
            # Load historical data for training
            await self._load_training_data()
            
            # Train models
            await self._train_models()
            
            # Initialize feature stores
            await self._initialize_feature_stores()
            
            # Initialize volatility surface
            option_chain = await self._get_option_chain("NIFTY")
            await self.volatility_surface.update_surface(
                option_chain, 
                await self._get_underlying_price("NIFTY")
            )
            
            # Detect initial market regime
            self.current_market_regime = await self._analyze_market_regime()
            
            # Start monitoring tasks
            if settings.AI_ENABLED:
                asyncio.create_task(self._market_monitoring_loop())
                asyncio.create_task(self._position_monitoring_loop())
                asyncio.create_task(self._risk_monitoring_loop())
                asyncio.create_task(self._ml_prediction_loop())
                asyncio.create_task(self._metrics_reporting_loop())
            
            self.is_running = True
            self.initialization_timestamp = datetime.now()
            
            elapsed = time.time() - start_time
            logger.info(f"✅ Institutional-Grade AI Trading Engine initialized successfully in {elapsed:.2f} seconds")
            
            # Send initialization notification
            await websocket_manager.send_system_alert({
                "type": "ENGINE_INITIALIZED",
                "message": "Institutional-Grade AI Trading Engine initialized successfully",
                "timestamp": datetime.now().isoformat(),
                "engine_version": "3.0.0"
            })
            
        except Exception as e:
            self.last_error = str(e)
            self.system_health = "ERROR"
            logger.error(f"❌ Failed to initialize Institutional-Grade AI Trading Engine: {e}")
            raise
    
    async def _initialize_ml_models(self):
        """Initialize advanced machine learning models"""
        try:
            logger.info("Initializing ML models...")
            
            if SKLEARN_AVAILABLE:
                # Price prediction model
                self.models["price_prediction"] = RandomForestRegressor(
                    n_estimators=200, max_depth=10, n_jobs=-1, random_state=42
                )
                
                # Volatility prediction model
                self.models["volatility_prediction"] = GradientBoostingRegressor(
                    n_estimators=150, max_depth=8, learning_rate=0.1, random_state=42
                )
                
                # Market regime classification model
                self.models["regime_classification"] = RandomForestClassifier(
                    n_estimators=100, max_depth=6, n_jobs=-1, random_state=42
                )
            
            # Deep learning models (if available)
            if TF_AVAILABLE:
                # Transformer model for price prediction
                self.models["transformer_price"] = DeepLearningModel(
                    input_shape=(60, 50),  # 60 timesteps, 50 features
                    output_dim=5,          # Predict 5 values (future prices)
                    model_type="transformer"
                )
                
                # LSTM model for volatility prediction
                self.models["lstm_volatility"] = DeepLearningModel(
                    input_shape=(30, 40),  # 30 timesteps, 40 features
                    output_dim=1,          # Predict future volatility
                    model_type="lstm"
                )
                
                # CNN-LSTM hybrid for options pricing
                self.models["cnn_lstm_options"] = DeepLearningModel(
                    input_shape=(20, 30),  # 20 timesteps, 30 features
                    output_dim=1,          # Predict option price
                    model_type="cnn_lstm"
                )
            
            logger.info("✅ ML models initialized")
            
        except Exception as e:
            logger.error(f"❌ Error initializing ML models: {e}")
    
    async def _initialize_feature_stores(self):
        """Initialize feature stores for rapid feature calculation"""
        try:
            # Initialize feature stores for each symbol
            for symbol in ["NIFTY", "BANKNIFTY"]:
                self.technical_indicators[symbol] = {}
                self.feature_store[symbol] = {}
            
            # Calculate initial features
            await self._update_feature_stores()
            
        except Exception as e:
            logger.error(f"❌ Error initializing feature stores: {e}")
    
    async def _update_feature_stores(self):
        """Update feature stores with latest market data"""
        try:
            for symbol in ["NIFTY", "BANKNIFTY"]:
                if symbol in self.historical_data:
                    data = self.historical_data[symbol]
                    if isinstance(data, dict):
                        # Multi-timeframe data
                        for timeframe, ohlc_data in data.items():
                            if len(ohlc_data) > 50:
                                df = pd.DataFrame(ohlc_data)
                                
                                # Calculate technical indicators for this timeframe
                                indicators = self._calculate_indicators(df)
                                if symbol not in self.technical_indicators:
                                    self.technical_indicators[symbol] = {}
                                self.technical_indicators[symbol][timeframe] = indicators
                                
                                # Extract features for ML models
                                features = self._extract_features(df, indicators)
                                if symbol not in self.feature_store:
                                    self.feature_store[symbol] = {}
                                self.feature_store[symbol][timeframe] = features
                    elif len(data) > 50:
                        # Single timeframe data
                        df = pd.DataFrame(data)
                        
                        # Calculate technical indicators
                        indicators = self._calculate_indicators(df)
                        self.technical_indicators[symbol] = indicators
                        
                        # Extract features for ML models
                        features = self._extract_features(df, indicators)
                        self.feature_store[symbol] = features
                        
        except Exception as e:
            logger.error(f"❌ Error updating feature stores: {e}")
    
    async def _load_training_data(self):
        """Load historical data for model training"""
        try:
            logger.info("Loading training data...")
            
            # Get data for multiple underlyings
            for symbol, security_id in [("NIFTY", "13"), ("BANKNIFTY", "33")]:
                # Load daily data
                historical_data = await self.market_data_service.get_historical_data(
                    security_id=security_id,
                    exchange_segment="IDX_I",
                    instrument="INDEX",
                    days=365
                )
                
                if historical_data and len(historical_data) > 0:
                    self.historical_data[symbol] = {}
                    self.historical_data[symbol][TimeFrame.DAILY.value] = historical_data
                    logger.info(f"✅ Loaded {len(historical_data)} daily records for {symbol}")
                
                # Load multi-timeframe data
                await self._load_multi_timeframe_data(symbol, security_id)
                
                # Load option chain for volatility surface modeling
                option_chain = await self._get_option_chain(symbol)
                if option_chain:
                    self.option_chain_cache[symbol] = option_chain
            
            logger.info("✅ Training data loaded")
            
        except Exception as e:
            logger.error(f"❌ Error loading training data: {e}")
    
    async def _load_multi_timeframe_data(self, symbol: str, security_id: str):
        """Load data for multiple timeframes"""
        try:
            timeframes = {
                TimeFrame.FIVE_MINUTE: 5,
                TimeFrame.FIFTEEN_MINUTE: 15,
                TimeFrame.THIRTY_MINUTE: 30,
                TimeFrame.ONE_HOUR: 60
            }
            
            for timeframe, minutes in timeframes.items():
                data = await self.market_data_service.get_intraday_data(
                    security_id=security_id,
                    exchange_segment="IDX_I",
                    interval=minutes,
                    days=30
                )
                
                if data and len(data) > 0:
                    if symbol not in self.historical_data:
                        self.historical_data[symbol] = {}
                    
                    self.historical_data[symbol][timeframe.value] = data
                    logger.debug(f"Loaded {len(data)} records for {symbol} {timeframe.value}")
            
        except Exception as e:
            logger.error(f"❌ Error loading multi-timeframe data: {e}")
    
    async def _get_option_chain(self, symbol: str) -> Dict[str, Any]:
        """Get option chain for a symbol"""
        try:
            security_id = "13" if symbol == "NIFTY" else "33"  # NIFTY or BANKNIFTY
            
            option_chain = await dhan_service.get_option_chain(security_id, "IDX_I")
            
            return option_chain
        except Exception as e:
            logger.error(f"❌ Error getting option chain for {symbol}: {e}")
            return {}
    
    async def _get_underlying_price(self, symbol: str) -> float:
        """Get current price for an underlying"""
        try:
            security_id = "13" if symbol == "NIFTY" else "33"  # NIFTY or BANKNIFTY
            
            quote = await dhan_service.get_market_quote(security_id, "IDX_I")
            
            if quote:
                return quote.get("last_price", 0.0)
            
            return 0.0
            
        except Exception as e:
            logger.error(f"❌ Error getting underlying price for {symbol}: {e}")
            return 0.0
    
    async def _train_models(self):
        """Train machine learning models"""
        try:
            logger.info("Training models...")
            
            for symbol in self.historical_data:
                # Get daily data for main models
                if (symbol in self.historical_data and 
                    TimeFrame.DAILY.value in self.historical_data[symbol]):
                    
                    daily_data = self.historical_data[symbol][TimeFrame.DAILY.value]
                    
                    if len(daily_data) < 100:
                        logger.warning(f"⚠️ Insufficient data for {symbol} training")
                        continue
                    
                    # Convert to DataFrame
                    df = pd.DataFrame(daily_data)
                    
                    # Calculate indicators
                    indicators = self._calculate_indicators(df)
                    
                    # Extract features
                    features = self._extract_features(df, indicators)
                    if len(features) < 50:
                        continue
                    
                    # Train traditional ML models
                    await self._train_traditional_ml(symbol, df, features)
                    
                    # Train deep learning models
                    await self._train_deep_learning_models(symbol, df, features)
                    
                    # Train market regime detector
                    self.market_regime_detector.train(df)
            
            logger.info("✅ Models trained successfully")
            
        except Exception as e:
            logger.error(f"❌ Error training models: {e}")
    
    async def _train_traditional_ml(self, symbol: str, df: pd.DataFrame, features: pd.DataFrame):
        """Train traditional machine learning models"""
        try:
            if not SKLEARN_AVAILABLE:
                logger.warning("⚠️ scikit-learn not available, skipping traditional ML training")
                return
                
            # Prepare training data
            X = features.values
            
            # Target variables
            y_price_1d = df['close'].shift(-1).fillna(method='ffill')  # Next day price
            y_price_5d = df['close'].shift(-5).fillna(method='ffill')  # 5-day price
            
            y_volatility = df['high'].sub(df['low']).div(df['close']).shift(-1).fillna(method='ffill')
            
            # Calculate regime labels
            returns = df['close'].pct_change().fillna(0)
            vol = returns.rolling(20).std().fillna(0)
            trend = df['close'].rolling(20).mean().pct_change(20).fillna(0)
            
            regimes = pd.Series(index=df.index, data=2)  # Default: NORMAL
            regimes[(trend > 0.03) & (vol < 0.015)] = 3  # BULLISH_TREND
            regimes[(trend < -0.03) & (vol < 0.015)] = 0  # BEARISH_TREND
            regimes[vol > 0.02] = 4  # HIGH_VOLATILITY
            regimes[(abs(trend) < 0.01) & (vol < 0.01)] = 1  # RANGE_BOUND
            
            # Scale features
            scaler = StandardScaler()
            X_scaled = scaler.fit_transform(X)
            
            # Split data
            split_idx = int(len(X_scaled) * 0.8)
            X_train, X_test = X_scaled[:split_idx], X_scaled[split_idx:]
            y_price_1d_train, y_price_1d_test = y_price_1d[:split_idx], y_price_1d[split_idx:]
            y_vol_train, y_vol_test = y_volatility[:split_idx], y_volatility[split_idx:]
            y_regime_train, y_regime_test = regimes[:split_idx], regimes[split_idx:]
            
            # Train price prediction model
            if len(X_train) > 50 and "price_prediction" in self.models:
                self.models["price_prediction"].fit(X_train, y_price_1d_train)
                
                # Evaluate
                price_pred = self.models["price_prediction"].predict(X_test)
                price_rmse = np.sqrt(np.mean((price_pred - y_price_1d_test) ** 2))
                logger.info(f"{symbol} Price model RMSE: {price_rmse:.4f}")
                
                # Feature importance
                if hasattr(self.models["price_prediction"], "feature_importances_"):
                    self.feature_importance["price"] = self.models["price_prediction"].feature_importances_
            
            # Train volatility model
            if len(X_train) > 50 and "volatility_prediction" in self.models and not y_vol_train.isna().any():
                self.models["volatility_prediction"].fit(X_train, y_vol_train)
                
                # Evaluate
                vol_pred = self.models["volatility_prediction"].predict(X_test)
                vol_rmse = np.sqrt(np.mean((vol_pred - y_vol_test) ** 2))
                logger.info(f"{symbol} Volatility model RMSE: {vol_rmse:.4f}")
                
                # Feature importance
                if hasattr(self.models["volatility_prediction"], "feature_importances_"):
                    self.feature_importance["volatility"] = self.models["volatility_prediction"].feature_importances_
            
            # Train regime model
            if len(X_train) > 50 and "regime_classification" in self.models and not y_regime_train.isna().any():
                self.models["regime_classification"].fit(X_train, y_regime_train)
                
                # Evaluate
                regime_pred = self.models["regime_classification"].predict(X_test)
                regime_accuracy = np.mean(regime_pred == y_regime_test)
                logger.info(f"{symbol} Regime model accuracy: {regime_accuracy:.4f}")
                
                # Feature importance
                if hasattr(self.models["regime_classification"], "feature_importances_"):
                    self.feature_importance["regime"] = self.models["regime_classification"].feature_importances_
                    
        except Exception as e:
            logger.error(f"❌ Error training traditional ML for {symbol}: {e}")
    
    async def _train_deep_learning_models(self, symbol: str, df: pd.DataFrame, features: pd.DataFrame):
        """Train deep learning models"""
        try:
            if not TF_AVAILABLE:
                return
                
            # Prepare sequence data
            X = features.values
            
            # Prepare target variables
            future_prices = np.column_stack([
                df['close'].shift(-i).fillna(method='ffill').values for i in range(1, 6)
            ])
            
            future_volatility = np.array([
                df['high'].sub(df['low']).div(df['close']).rolling(window=5).mean().shift(-1).fillna(method='ffill').values
            ]).T
            
            # Scale features
            scaler = StandardScaler()
            X_scaled = scaler.fit_transform(X)
            
            # Create sequence data for time series models
            seq_length = min(60, len(X_scaled) // 2)
            
            X_seq, y_seq_prices = self._prepare_sequence_data(X_scaled, future_prices, seq_length)
            _, y_seq_vol = self._prepare_sequence_data(X_scaled, future_volatility, seq_length)
            
            # Train only if enough sequence data
            if len(X_seq) > 10:
                # Split data
                split_idx = int(len(X_seq) * 0.8)
                X_train, X_test = X_seq[:split_idx], X_seq[split_idx:]
                y_train_prices, y_test_prices = y_seq_prices[:split_idx], y_seq_prices[split_idx:]
                y_train_vol, y_test_vol = y_seq_vol[:split_idx], y_seq_vol[split_idx:]
                
                # Train transformer model for price prediction
                if "transformer_price" in self.models:
                    logger.info(f"Training transformer model for {symbol} price prediction...")
                    await asyncio.to_thread(
                        self.models["transformer_price"].train,
                        X_train, y_train_prices, epochs=30, batch_size=32
                    )
                
                # Train LSTM model for volatility prediction
                if "lstm_volatility" in self.models:
                    logger.info(f"Training LSTM model for {symbol} volatility prediction...")
                    await asyncio.to_thread(
                        self.models["lstm_volatility"].train,
                        X_train, y_train_vol, epochs=30, batch_size=32
                    )
                    
        except Exception as e:
            logger.error(f"❌ Error training deep learning models for {symbol}: {e}")
    
    def _prepare_sequence_data(self, X: np.ndarray, y: np.ndarray, seq_length: int):
        """Prepare sequence data for time series models"""
        X_seq = []
        y_seq = []
        
        for i in range(len(X) - seq_length):
            X_seq.append(X[i:i+seq_length])
            y_seq.append(y[i+seq_length])
            
        return np.array(X_seq), np.array(y_seq)
    
    def _calculate_indicators(self, df: pd.DataFrame) -> Dict[str, pd.Series]:
        """Calculate comprehensive technical indicators"""
        indicators = {}
        
        try:
            # Basic price and volume metrics
            if all(col in df.columns for col in ['open', 'high', 'low', 'close']):
                # Moving averages
                for period in [5, 10, 20, 50, 100, 200]:
                    if len(df) >= period:
                        indicators[f'sma_{period}'] = df['close'].rolling(period).mean()
                        indicators[f'ema_{period}'] = df['close'].ewm(span=period, adjust=False).mean()
                
                # Bollinger Bands
                if len(df) >= 20:
                    indicators['bb_middle'] = df['close'].rolling(20).mean()
                    indicators['bb_std'] = df['close'].rolling(20).std()
                    indicators['bb_upper'] = indicators['bb_middle'] + 2 * indicators['bb_std']
                    indicators['bb_lower'] = indicators['bb_middle'] - 2 * indicators['bb_std']
                    indicators['bb_width'] = (indicators['bb_upper'] - indicators['bb_lower']) / indicators['bb_middle']
                
                # Momentum indicators
                if len(df) >= 14:
                    # RSI calculation
                    delta = df['close'].diff()
                    gain = delta.where(delta > 0, 0).fillna(0)
                    loss = -delta.where(delta < 0, 0).fillna(0)
                    avg_gain = gain.rolling(14).mean()
                    avg_loss = loss.rolling(14).mean()
                    rs = avg_gain / avg_loss.replace(0, 0.001)  # Avoid division by zero
                    indicators['rsi'] = 100 - (100 / (1 + rs))
                    
                    # Stochastic
                    low_14 = df['low'].rolling(14).min()
                    high_14 = df['high'].rolling(14).max()
                    indicators['stoch_k'] = 100 * ((df['close'] - low_14) / (high_14 - low_14 + 0.0001))
                    indicators['stoch_d'] = indicators['stoch_k'].rolling(3).mean()
                
                # MACD
                if len(df) >= 26:
                    ema12 = df['close'].ewm(span=12, adjust=False).mean()
                    ema26 = df['close'].ewm(span=26, adjust=False).mean()
                    indicators['macd'] = ema12 - ema26
                    indicators['macd_signal'] = indicators['macd'].ewm(span=9, adjust=False).mean()
                    indicators['macd_histogram'] = indicators['macd'] - indicators['macd_signal']
                
                # ADX (Average Directional Index)
                if len(df) >= 14:
                    # +DM, -DM
                    high_diff = df['high'].diff()
                    low_diff = df['low'].diff().multiply(-1)
                    
                    pos_dm = ((high_diff > low_diff) & (high_diff > 0)) * high_diff
                    neg_dm = ((low_diff > high_diff) & (low_diff > 0)) * low_diff
                    
                    # TR (True Range)
                    tr = pd.DataFrame({
                        'hl': df['high'] - df['low'],
                        'hc': abs(df['high'] - df['close'].shift(1)),
                        'lc': abs(df['low'] - df['close'].shift(1))
                    }).max(axis=1)
                    
                    # 14-period smoothed +DM, -DM, TR
                    smoothed_pos_dm = pos_dm.rolling(14).sum()
                    smoothed_neg_dm = neg_dm.rolling(14).sum()
                    smoothed_tr = tr.rolling(14).sum()
                    
                    # +DI, -DI
                    plus_di = 100 * smoothed_pos_dm / smoothed_tr
                    minus_di = 100 * smoothed_neg_dm / smoothed_tr
                    
                    # DX and ADX
                    dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
                    indicators['adx'] = dx.rolling(14).mean()
                    indicators['plus_di'] = plus_di
                    indicators['minus_di'] = minus_di
                
                # Volatility indicators
                if len(df) >= 20:
                    # ATR (Average True Range)
                    tr = pd.DataFrame({
                        'hl': df['high'] - df['low'],
                        'hc': abs(df['high'] - df['close'].shift(1)),
                        'lc': abs(df['low'] - df['close'].shift(1))
                    }).max(axis=1)
                    
                    indicators['atr'] = tr.rolling(14).mean()
                    indicators['atr_percent'] = indicators['atr'] / df['close'] * 100
                    
                    # Historical Volatility
                    returns = df['close'].pct_change()
                    indicators['hist_volatility'] = returns.rolling(20).std() * np.sqrt(252)
                
                # Volume indicators
                if 'volume' in df.columns:
                    indicators['volume_sma'] = df['volume'].rolling(20).mean()
                    indicators['volume_ratio'] = df['volume'] / indicators['volume_sma']
                    
                    # OBV (On-Balance Volume)
                    obv = pd.Series(0, index=df.index)
                    for i in range(1, len(df)):
                        if df['close'].iloc[i] > df['close'].iloc[i-1]:
                            obv.iloc[i] = obv.iloc[i-1] + df['volume'].iloc[i]
                        elif df['close'].iloc[i] < df['close'].iloc[i-1]:
                            obv.iloc[i] = obv.iloc[i-1] - df['volume'].iloc[i]
                        else:
                            obv.iloc[i] = obv.iloc[i-1]
                    
                    indicators['obv'] = obv
                    indicators['obv_sma'] = indicators['obv'].rolling(20).mean()
                
                # Price action patterns
                if len(df) >= 5:
                    # Doji
                    body = abs(df['close'] - df['open'])
                    range_day = df['high'] - df['low']
                    indicators['doji'] = body / (range_day + 0.0001) < 0.1
                    
                    # Hammer
                    lower_wick = df.apply(lambda x: min(x['open'], x['close']) - x['low'], axis=1)
                    upper_wick = df.apply(lambda x: x['high'] - max(x['open'], x['close']), axis=1)
                    indicators['hammer'] = (body / (range_day + 0.0001) < 0.3) & (lower_wick / (range_day + 0.0001) > 0.6) & (upper_wick / (range_day + 0.0001) < 0.1)
                    
                    # Engulfing patterns
                    indicators['bullish_engulfing'] = (df['open'].shift(1) > df['close'].shift(1)) & (df['close'] > df['open']) & (df['open'] < df['close'].shift(1)) & (df['close'] > df['open'].shift(1))
                    indicators['bearish_engulfing'] = (df['close'].shift(1) > df['open'].shift(1)) & (df['open'] > df['close']) & (df['open'] > df['close'].shift(1)) & (df['close'] < df['open'].shift(1))
                
                # Support and resistance levels
                if len(df) >= 20:
                    swing_high = (df['high'] > df['high'].shift(1)) & (df['high'] > df['high'].shift(-1)) & (df['high'] > df['high'].shift(2)) & (df['high'] > df['high'].shift(-2))
                    swing_low = (df['low'] < df['low'].shift(1)) & (df['low'] < df['low'].shift(-1)) & (df['low'] < df['low'].shift(2)) & (df['low'] < df['low'].shift(-2))
                    
                    indicators['swing_high'] = swing_high
                    indicators['swing_low'] = swing_low
                
                # Trend strength indicators
                if len(df) >= 50:
                    indicators['adx_trend_strength'] = indicators['adx'].apply(
                        lambda x: 'STRONG' if x > 25 else ('WEAK' if x > 15 else 'NO_TREND')
                    )
                    
                    # Price relative to moving averages
                    indicators['price_vs_sma50'] = df['close'] / indicators['sma_50'] - 1
                    indicators['price_vs_sma200'] = df['close'] / indicators['sma_200'] - 1
                    indicators['sma50_vs_sma200'] = indicators['sma_50'] / indicators['sma_200'] - 1
                
            return {k: v for k, v in indicators.items() if not v.isna().all()}
            
        except Exception as e:
            logger.debug(f"Error calculating indicators: {e}")
            return indicators
    
    def _extract_features(self, df: pd.DataFrame, indicators: Dict[str, pd.Series]) -> pd.DataFrame:
        """Extract features for ML models from price data and indicators"""
        features = pd.DataFrame(index=df.index)
        
        try:
            # Basic price features
            if 'open' in df.columns:
                features['open'] = df['open']
            if 'high' in df.columns:
                features['high'] = df['high']
            if 'low' in df.columns:
                features['low'] = df['low']
            if 'close' in df.columns:
                features['close'] = df['close']
                
                # Returns
                features['daily_return'] = df['close'].pct_change()
                features['weekly_return'] = df['close'].pct_change(5)
                features['monthly_return'] = df['close'].pct_change(20)
                
                # Relative price levels
                features['high_low_ratio'] = df['high'] / df['low']
                features['close_open_ratio'] = df['close'] / df['open']
            
            # Volume features
            if 'volume' in df.columns:
                features['volume'] = df['volume']
                features['volume_ma_ratio'] = df['volume'] / df['volume'].rolling(10).mean()
                
                # Money Flow
                if all(col in df.columns for col in ['high', 'low', 'close']):
                    typical_price = (df['high'] + df['low'] + df['close']) / 3
                    money_flow = typical_price * df['volume']
                    features['money_flow'] = money_flow
                    
                    # Money Flow Index
                    positive_flow = ((typical_price > typical_price.shift(1)) * money_flow).fillna(0)
                    negative_flow = ((typical_price < typical_price.shift(1)) * money_flow).fillna(0)
                    
                    pos_flow_sum = positive_flow.rolling(window=14).sum()
                    neg_flow_sum = negative_flow.rolling(window=14).sum()
                    
                    money_ratio = pos_flow_sum / neg_flow_sum.replace(0, 0.001)
                    features['mfi'] = 100 - (100 / (1 + money_ratio))
                    
                    # Accumulation/Distribution Line
                    clv = ((df['close'] - df['low']) - (df['high'] - df['close'])) / (df['high'] - df['low'] + 0.0001)
                    ad_line = (clv * df['volume']).cumsum()
                    features['ad_line'] = ad_line
                    
                    # Chaikin Money Flow
                    features['cmf'] = (clv * df['volume']).rolling(20).sum() / df['volume'].rolling(20).sum()
                    
                    # VWAP (for intraday data)
                    if 'datetime' in df.columns:
                        df['date'] = pd.to_datetime(df['datetime']).dt.date
                        vwap = df.groupby('date').apply(lambda x: (x['close'] * x['volume']).cumsum() / x['volume'].cumsum())
                        features['vwap'] = vwap
                        features['price_vwap_ratio'] = df['close'] / features['vwap']
            
            # Add indicators to features
            for name, indicator in indicators.items():
                if isinstance(indicator, pd.Series) and not indicator.isna().all():
                    features[name] = indicator
            
            # Advanced feature engineering
            if 'rsi' in features.columns:
                # RSI momentum
                features['rsi_change'] = features['rsi'].diff()
                features['rsi_ma'] = features['rsi'].rolling(14).mean()
                features['rsi_divergence'] = ((features['rsi'] < 30) & (df['close'] > df['close'].shift(1)))
            
            if all(col in features.columns for col in ['sma_20', 'sma_50']):
                # Moving average crossovers
                features['ma_crossover_20_50'] = (features['sma_20'] > features['sma_50']).astype(int)
                features['ma_distance_20_50'] = features['sma_20'] / features['sma_50'] - 1
            
            # Volatility features
            if 'hist_volatility' in features.columns:
                features['volatility_ratio'] = features['hist_volatility'] / features['hist_volatility'].rolling(90).mean()
            
            if 'atr' in features.columns:
                features['atr_ratio'] = features['atr'] / features['atr'].rolling(90).mean()
            
            # Market regime features
            if 'close' in df.columns:
                # Trend strength
                if 'sma_50' in features.columns and 'sma_200' in features.columns:
                    # Golden/Death cross
                    features['golden_cross'] = (features['sma_50'] > features['sma_200']).astype(int)
                    
                    # Trend strength
                    features['trend_strength'] = abs(features['sma_50'] / features['sma_200'] - 1) * 100
                
                # Volatility regime
                if 'hist_volatility' in features.columns:
                    vol_percentile = features['hist_volatility'].rolling(90).apply(
                        lambda x: percentileofscore(x, x.iloc[-1]) / 100 if len(x.dropna()) > 0 else 0.5
                    )
                    features['volatility_regime'] = vol_percentile.apply(
                        lambda x: 'HIGH' if x > 0.8 else ('LOW' if x < 0.2 else 'NORMAL')
                    )
                    features['vol_percentile'] = vol_percentile
            
            # Options-specific features if available
            if 'implied_volatility' in df.columns:
                features['implied_volatility'] = df['implied_volatility']
                
                if 'hist_volatility' in features.columns:
                    features['iv_hv_ratio'] = df['implied_volatility'] / features['hist_volatility']
                
                if 'option_type' in df.columns and 'strike' in df.columns and 'underlying_price' in df.columns:
                    # Option moneyness
                    features['moneyness'] = df['underlying_price'] / df['strike'] - 1
                    
                    # Option gamma exposure
                    if 'gamma' in df.columns and 'open_interest' in df.columns:
                        features['gamma_exposure'] = df['gamma'] * df['open_interest'] * df['underlying_price'] * df['underlying_price'] * 0.01
            
            # Time-based features
            if 'datetime' in df.columns:
                dt = pd.to_datetime(df['datetime'])
                features['day_of_week'] = dt.dt.dayofweek
                features['hour_of_day'] = dt.dt.hour
                features['days_to_expiry'] = None
                if 'expiry_date' in df.columns:
                    features['days_to_expiry'] = (pd.to_datetime(df['expiry_date']) - dt).dt.days
            
            # Fill missing values and drop constant columns
            features = features.fillna(method='ffill').fillna(0)
            
            # Drop columns with zero variance
            var_threshold = 0.0001
            features = features.loc[:, features.var() > var_threshold]
            
            return features
            
        except Exception as e:
            logger.error(f"❌ Error extracting features: {e}")
            return pd.DataFrame()
    
    async def _market_monitoring_loop(self):
        """Continuous market monitoring and signal generation"""
        while self.is_running:
            try:
                # Get current market data
                market_data = await self._get_current_market_data()
                
                if market_data:
                    # Update volatility surface
                    option_chain = await self._get_option_chain("NIFTY")
                    underlying_price = await self._get_underlying_price("NIFTY")
                    await self.volatility_surface.update_surface(option_chain, underlying_price)
                    
                    # Update features and indicators
                    await self._update_feature_stores()
                    
                    # Analyze market conditions
                    market_analysis = await self._analyze_market_conditions(market_data)
                    
                    # Update current market regime
                    self.current_market_regime = await self._analyze_market_regime()
                    
                    # Update market depth analysis
                    if 'market_depth' in market_data:
                        self.market_depth_analysis = await MarketDepthAnalysis.analyze(
                            market_data['market_depth'], 
                            list(self.trade_history)
                        )
                    
                    # Generate trading signals
                    signals = await self._generate_trading_signals(market_analysis)
                    
                    # Identify trading opportunities
                    opportunities = await self._identify_opportunities(market_analysis, signals)
                    
                    if opportunities:
                        self.current_opportunities = opportunities
                        
                        # Process high-confidence opportunities
                        for opportunity in opportunities:
                            if opportunity.get('confidence', 0) > 0.7:
                                await self._process_trading_opportunity(opportunity)
                    
                    # Broadcast market analysis
                    await self._broadcast_market_updates(market_analysis)
                
                # Wait before next iteration
                await asyncio.sleep(5)  # 5-second intervals
                
            except Exception as e:
                logger.error(f"❌ Error in market monitoring loop: {e}")
                await asyncio.sleep(10)
    
    async def _position_monitoring_loop(self):
        """Monitor and manage active positions"""
        while self.is_running:
            try:
                for position_id, position in list(self.active_positions.items()):
                    if not position.is_active:
                        continue
                        
                    # Update position with current prices
                    await self._update_position_prices(position)
                    
                    # Calculate position P&L
                    position.update_pnl()
                    
                    # Update position Greeks
                    underlying_price = await self._get_underlying_price(position.underlying)
                    position.update_greeks(underlying_price, self.volatility_surface)
                    
                    # Check for position adjustments
                    need_adjustment, reason, details = position.check_adjustment_needed()
                    if need_adjustment:
                        await self._adjust_position(position, reason, details)
                    
                    # Check exit conditions
                    should_exit, exit_reason = position.check_exit_conditions(
                        self.current_market_regime.value
                    )
                    if should_exit:
                        await self._close_position(position.position_id, exit_reason)
                    
                # Update portfolio metrics
                await self._update_portfolio_metrics()
                
                await asyncio.sleep(2)  # 2-second intervals
                
            except Exception as e:
                logger.error(f"❌ Error in position monitoring loop: {e}")
                await asyncio.sleep(5)
    
    async def _risk_monitoring_loop(self):
        """Monitor risk levels and enforce limits"""
        while self.is_running:
            try:
                # Check daily loss limit
                if self.daily_pnl <= -self.max_daily_loss:
                    logger.warning("🚨 Daily loss limit reached! Closing all positions")
                    await self._emergency_close_all_positions("DAILY_LOSS_LIMIT")
                
                # Calculate portfolio-level risk metrics
                await self._calculate_portfolio_risk()
                
                # Check portfolio-level risk limits
                if self.portfolio_var > self.risk_limits["max_position_count"]:
                    logger.warning("🚨 Portfolio VaR exceeding limits! Reducing exposure")
                    await self._reduce_portfolio_risk()
                
                # Check individual position risks
                for position in list(self.active_positions.values()):
                    if not position.is_active:
                        continue
                        
                    # Check drawdown limit
                    if position.risk_metrics.get("current_drawdown", 0) > 0.5:  # 50% drawdown from peak
                        logger.warning(f"🚨 Position {position.position_id} exceeding drawdown limit")
                        await self._close_position(position.position_id, "MAX_DRAWDOWN_LIMIT")
                    
                    # Check delta exposure
                    if abs(position.greeks.get("delta", 0)) > self.risk_limits["max_delta_exposure"]:
                        logger.warning(f"🚨 Position {position.position_id} exceeding delta limit")
                        await self._adjust_position(position, "DELTA_LIMIT", {
                            "current_delta": position.greeks.get("delta", 0),
                            "max_delta": self.risk_limits["max_delta_exposure"]
                        })
                
                await asyncio.sleep(10)  # 10-second intervals
                
            except Exception as e:
                logger.error(f"❌ Error in risk monitoring loop: {e}")
                await asyncio.sleep(15)
    
    async def _ml_prediction_loop(self):
        """Generate continuous ML predictions"""
        while self.is_running:
            try:
                # Get latest market data
                market_data = await self._get_current_market_data()
                
                if market_data and "NIFTY" in self.feature_store:
                    # Make price predictions
                    price_pred = await self._predict_price_movement("NIFTY")
                    
                    # Make volatility predictions
                    vol_pred = await self._predict_volatility("NIFTY")
                    
                    # Store predictions
                    self.ensemble_predictions = {
                        "price_direction": price_pred.get("direction", 0),
                        "price_magnitude": price_pred.get("magnitude", 0),
                        "predicted_move": price_pred.get("predicted_move", 0),
                        "confidence": price_pred.get("confidence", 0),
                        "volatility_forecast": vol_pred.get("forecast", 0),
                        "iv_forecast": vol_pred.get("iv_forecast", 0),
                        "regime_forecast": await self._predict_regime_change("NIFTY"),
                        "timestamp": datetime.now().isoformat()
                    }
                    
                    # Log predictions if significant
                    if abs(price_pred.get("predicted_move", 0)) > 0.5 and price_pred.get("confidence", 0) > 0.7:
                        logger.info(f"🔮 High-confidence prediction: {price_pred['direction_str']} move of {price_pred['predicted_move']:.2f}% with {price_pred['confidence']:.2f} confidence")
                
                await asyncio.sleep(60)  # 60-second intervals
                
            except Exception as e:
                logger.error(f"❌ Error in ML prediction loop: {e}")
                await asyncio.sleep(120)
    
    async def _metrics_reporting_loop(self):
        """Report system metrics and performance"""
        while self.is_running:
            try:
                # Calculate system metrics
                metrics = {
                    "active_positions": len([p for p in self.active_positions.values() if p.is_active]),
                    "daily_pnl": self.daily_pnl,
                    "unrealized_pnl": sum(p.unrealized_pnl for p in self.active_positions.values() if p.is_active),
                    "win_rate": self.winning_trades / max(1, self.total_trades) * 100,
                    "sharpe_ratio": self.sharpe_ratio,
                    "max_drawdown": self.max_drawdown,
                    "market_regime": self.current_market_regime.value,
                    "portfolio_var": self.portfolio_var,
                    "portfolio_beta": self.portfolio_beta,
                    "system_health": self.system_health,
                    "timestamp": datetime.now().isoformat()
                }
                
                # Log metrics periodically
                logger.info(f"📊 Performance metrics: PnL=${metrics['daily_pnl']:.2f} | Win rate: {metrics['win_rate']:.1f}% | Active positions: {metrics['active_positions']}")
                
                # Store metrics in Redis
                await redis_client.set("trading_metrics", json.dumps(metrics), ttl=300)
                
                # Send metrics to websocket clients
                await websocket_manager.send_metrics_update(metrics)
                
                # Update system health status
                self._update_system_health()
                self.last_heartbeat = datetime.now()
                
                await asyncio.sleep(30)  # 30-second intervals
                
            except Exception as e:
                logger.error(f"❌ Error in metrics reporting loop: {e}")
                await asyncio.sleep(60)
    
    def _update_system_health(self):
        """Update system health status"""
        health_status = "OK"
        
        # Check for recent errors
        if self.last_error and (datetime.now() - datetime.fromisoformat(self.last_error.get('timestamp', '2000-01-01'))) < timedelta(minutes=5):
            health_status = "WARNING"
        
        # Check for excessive drawdown
        if self.max_drawdown > 0.15:  # 15% drawdown
            health_status = "WARNING"
        
        if self.max_drawdown > 0.25:  # 25% drawdown
            health_status = "CRITICAL"
        
        # Check data freshness
        if (datetime.now() - self.last_heartbeat) > timedelta(minutes=2):
            health_status = "WARNING"
        
        if (datetime.now() - self.last_heartbeat) > timedelta(minutes=5):
            health_status = "CRITICAL"
        
        self.system_health = health_status
    
    async def _get_current_market_data(self) -> Dict[str, Any]:
        """Get comprehensive current market data"""
        try:
            # Get NIFTY and BANKNIFTY current data
            nifty_quote = await dhan_service.get_market_quote("13", "IDX_I")
            banknifty_quote = await dhan_service.get_market_quote("33", "IDX_I")
            
            # Get option chain data
            nifty_options = await dhan_service.get_option_chain("13", "IDX_I")
            
            # Get market depth data
            nifty_depth = await dhan_service.get_market_depth("13", "IDX_I")
            
            # Get recent trades
            recent_trades = await dhan_service.get_recent_trades("13", "IDX_I")
            if recent_trades:
                self.trade_history.extend(recent_trades)
            
            # Get price history
            nifty_history = await dhan_service.get_intraday_data("13", "IDX_I", interval=5, days=1)
            
            # Get IV and other option data
            iv_data = await self._extract_iv_data(nifty_options)
            
            market_data = {
                "nifty": nifty_quote,
                "banknifty": banknifty_quote,
                "nifty_options": nifty_options,
                "market_depth": nifty_depth,
                "recent_trades": recent_trades,
                "price_history": nifty_history,
                "iv_data": iv_data,
                "timestamp": datetime.now()
            }
            
            # Cache market data
            self.market_data_cache = market_data
            
            return market_data
            
        except Exception as e:
            logger.error(f"❌ Error getting market data: {e}")
            return {}
    
    async def _extract_iv_data(self, option_chain: Dict[str, Any]) -> Dict[str, Any]:
        """Extract implied volatility and other option metrics from option chain"""
        iv_data = {
            "atm_iv": 0.0,
            "skew": 0.0,
            "term_structure": {},
            "put_call_ratio": 0.0,
            "iv_percentile": 0.0,
            "top_oi_strikes": []
        }
        
        try:
            if not option_chain:
                return iv_data
            
            # Get current underlying price
            underlying_price = await self._get_underlying_price("NIFTY")
            if underlying_price == 0:
                return iv_data
            
            # Find ATM options
            atm_strike = round(underlying_price / 50) * 50  # Round to nearest 50
            
            # Extract IVs by expiry
            total_call_oi = 0
            total_put_oi = 0
            
            for expiry, strikes in option_chain.items():
                if not isinstance(strikes, dict):
                    continue
                
                # Look for ATM strike
                if str(atm_strike) in strikes:
                    strike_data = strikes[str(atm_strike)]
                    
                    # Get ATM IVs
                    if 'ce' in strike_data and 'iv' in strike_data['ce']:
                        iv_data["atm_iv"] = strike_data['ce']['iv']
                    elif 'ce' in strike_data and 'last_price' in strike_data['ce']:
                        # Calculate IV if not provided
                        try:
                            expiry_date = datetime.strptime(expiry, '%Y-%m-%d')
                            days_to_expiry = max(0, (expiry_date - datetime.now()).days)
                            
                            iv = OptionGreeks.estimate_implied_volatility(
                                strike_data['ce']['last_price'],
                                underlying_price,
                                atm_strike,
                                days_to_expiry,
                                DEFAULT_RISK_FREE_RATE,
                                DEFAULT_DIVIDEND_YIELD,
                                'CE'
                            )
                            iv_data["atm_iv"] = iv
                        except:
                            pass
                
                # Accumulate OI for put/call ratio
                for strike, data in strikes.items():
                    if 'ce' in data and 'oi' in data['ce']:
                        total_call_oi += data['ce']['oi']
                    
                    if 'pe' in data and 'oi' in data['pe']:
                        total_put_oi += data['pe']['oi']
                    
                    # Find top OI strikes
                    oi_data = {}
                    if 'ce' in data and 'oi' in data['ce']:
                        oi_data["call_oi"] = data['ce']['oi']
                    if 'pe' in data and 'oi' in data['pe']:
                        oi_data["put_oi"] = data['pe']['oi']
                    
                    if oi_data:
                        oi_data["strike"] = float(strike)
                        oi_data["total_oi"] = oi_data.get("call_oi", 0) + oi_data.get("put_oi", 0)
                        iv_data["top_oi_strikes"].append(oi_data)
            
            # Calculate put/call ratio
            if total_call_oi > 0:
                iv_data["put_call_ratio"] = total_put_oi / total_call_oi
            
            # Sort top OI strikes
            iv_data["top_oi_strikes"] = sorted(iv_data["top_oi_strikes"], key=lambda x: x.get("total_oi", 0), reverse=True)[:5]
            
            # Get IV skew and term structure
            iv_data["skew"] = self.volatility_surface.get_iv_skew(list(option_chain.keys())[0]) if option_chain else {}
            iv_data["term_structure"] = self.volatility_surface.analyze_term_structure()
            iv_data["iv_percentile"] = self.volatility_surface.iv_percentile.get(30, 0.5)
            
            return iv_data
            
        except Exception as e:
            logger.error(f"❌ Error extracting IV data: {e}")
            return iv_data
    
    async def _analyze_market_conditions(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Comprehensive market analysis using AI and statistical methods"""
        try:
            analysis = {
                "regime": self.current_market_regime.value,
                "direction": MarketDirection.SIDEWAYS.value,
                "strength": 0.5,
                "volatility": 0.5,
                "support_levels": [],
                "resistance_levels": [],
                "key_levels": [],
                "reversal_signals": [],
                "trend_signals": [],
                "options_analysis": {},
                "sentiment": 0.0,
                "liquidity": 0.5,
                "confidence": 0.5
            }
            
            if not market_data:
                return analysis
            
            # Analyze price action
            price_analysis = await self._analyze_price_action(market_data)
            analysis.update(price_analysis)
            
            # Analyze options data
            options_analysis = await self._analyze_options_data(market_data.get("nifty_options", {}), market_data.get("iv_data", {}))
            analysis["options_analysis"] = options_analysis
            
            # Analyze market depth and order flow
            if self.market_depth_analysis:
                analysis["order_flow"] = {
                    "signature": self.market_depth_analysis.order_flow_signature,
                    "buying_pressure": self.market_depth_analysis.buying_pressure,
                    "selling_pressure": self.market_depth_analysis.selling_pressure,
                    "significant_levels": self.market_depth_analysis.significant_levels,
                    "smart_money_flow": self.market_depth_analysis.smart_money_flow
                }
                
                order_flow_signals = self.market_depth_analysis.get_trading_signals()
                analysis["order_flow_signals"] = order_flow_signals
            
            # Add ML predictions
            if self.ensemble_predictions:
                analysis["ml_predictions"] = self.ensemble_predictions
            
            # Calculate overall market direction and confidence
            direction, strength, confidence = self._determine_market_direction(analysis)
            analysis["direction"] = direction
            analysis["strength"] = strength
            analysis["confidence"] = confidence
            
            return analysis
            
        except Exception as e:
            logger.error(f"❌ Error analyzing market conditions: {e}")
            return {}
    
    async def _analyze_price_action(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze price action and technical patterns"""
        analysis = {
            "trend": {
                "short_term": "NEUTRAL",
                "medium_term": "NEUTRAL",
                "long_term": "NEUTRAL",
                "strength": 0.5
            },
            "momentum": {
                "value": 0.0,
                "signal": "NEUTRAL",
                "divergence": False
            },
            "volatility": {
                "current": 0.0,
                "percentile": 0.5,
                "regime": "NORMAL"
            },
            "support_levels": [],
            "resistance_levels": [],
            "patterns": []
        }
        
        try:
            # Get price history
            price_history = market_data.get("price_history", [])
            if not price_history or len(price_history) < 10:
                return analysis
            
            # Convert to DataFrame
            df = pd.DataFrame(price_history)
            if df.empty or 'close' not in df.columns:
                return analysis
            
            # Calculate basic indicators
            indicators = self._calculate_indicators(df)
            
            # Determine trends
            if 'sma_20' in indicators and 'sma_50' in indicators and 'sma_200' in indicators:
                current_price = df['close'].iloc[-1]
                
                # Short-term trend (vs 20 SMA)
                sma20 = indicators['sma_20'].iloc[-1]
                analysis['trend']['short_term'] = "BULLISH" if current_price > sma20 else "BEARISH"
                
                # Medium-term trend (vs 50 SMA)
                sma50 = indicators['sma_50'].iloc[-1]
                analysis['trend']['medium_term'] = "BULLISH" if current_price > sma50 else "BEARISH"
                
                # Long-term trend (vs 200 SMA)
                sma200 = indicators['sma_200'].iloc[-1]
                analysis['trend']['long_term'] = "BULLISH" if current_price > sma200 else "BEARISH"
                
                # Trend strength (based on alignment and slope)
                trend_alignment = (current_price > sma20 and sma20 > sma50 and sma50 > sma200) or \
                                 (current_price < sma20 and sma20 < sma50 and sma50 < sma200)
                
                slope_20 = (indicators['sma_20'].iloc[-1] - indicators['sma_20'].iloc[-10]) / indicators['sma_20'].iloc[-10] if len(indicators['sma_20']) > 10 else 0
                
                analysis['trend']['strength'] = min(1.0, (0.7 if trend_alignment else 0.3) + abs(slope_20) * 5)
            
            # Momentum analysis
            if 'rsi' in indicators and 'macd' in indicators and 'macd_signal' in indicators:
                rsi = indicators['rsi'].iloc[-1]
                macd = indicators['macd'].iloc[-1]
                macd_signal = indicators['macd_signal'].iloc[-1]
                
                # RSI momentum
                if rsi > 70:
                    rsi_signal = "OVERBOUGHT"
                elif rsi < 30:
                    rsi_signal = "OVERSOLD"
                elif rsi > 50:
                    rsi_signal = "BULLISH"
                else:
                    rsi_signal = "BEARISH"
                
                # MACD momentum
                macd_cross = macd > macd_signal
                macd_signal = "BULLISH" if macd_cross else "BEARISH"
                
                # Combined momentum
                momentum = (rsi - 50) / 50  # -1 to +1
                
                analysis['momentum'] = {
                    "value": momentum,
                    "signal": "BULLISH" if momentum > 0.1 else ("BEARISH" if momentum < -0.1 else "NEUTRAL"),
                    "rsi": rsi,
                    "rsi_signal": rsi_signal,
                    "macd_signal": macd_signal,
                    "divergence": False  # Will be set later if detected
                }
                
                # Check for divergence
                price_higher = df['close'].iloc[-1] > df['close'].iloc[-5]
                rsi_higher = indicators['rsi'].iloc[-1] > indicators['rsi'].iloc[-5]
                
                if price_higher and not rsi_higher:
                    analysis['momentum']['divergence'] = True
                    analysis['momentum']['divergence_type'] = "BEARISH"
                elif not price_higher and rsi_higher:
                    analysis['momentum']['divergence'] = True
                    analysis['momentum']['divergence_type'] = "BULLISH"
            
            # Volatility analysis
            if 'hist_volatility' in indicators and 'atr' in indicators:
                vol = indicators['hist_volatility'].iloc[-1]
                vol_history = indicators['hist_volatility'].dropna()
                
                if len(vol_history) > 20:
                    vol_percentile = sum(1 for v in vol_history if v <= vol) / len(vol_history)
                    vol_regime = "HIGH" if vol_percentile > 0.8 else ("LOW" if vol_percentile < 0.2 else "NORMAL")
                    
                    analysis['volatility'] = {
                        "current": vol,
                        "percentile": vol_percentile,
                        "regime": vol_regime,
                        "atr": indicators['atr'].iloc[-1],
                        "atr_percent": indicators['atr'].iloc[-1] / df['close'].iloc[-1] * 100
                    }
            
            # Support and resistance levels
            if 'swing_high' in indicators and 'swing_low' in indicators:
                # Find recent swing highs (resistance)
                high_mask = indicators['swing_high']
                recent_highs = df.loc[high_mask].sort_values('high', ascending=False)['high'].head(3).tolist()
                
                # Find recent swing lows (support)
                low_mask = indicators['swing_low']
                recent_lows = df.loc[low_mask].sort_values('low')['low'].head(3).tolist()
                
                analysis['support_levels'] = recent_lows
                analysis['resistance_levels'] = recent_highs
            
            # Round numbers
            current_price = df['close'].iloc[-1]
            
            # Add round number levels
            round_levels = []
            
            # Major round numbers
            base = 1000
            lower_bound = (current_price // base - 2) * base
            upper_bound = (current_price // base + 3) * base
            
            for level in range(int(lower_bound), int(upper_bound), base):
                round_levels.append({
                    'price': level,
                    'type': 'MAJOR_ROUND',
                    'distance': abs(level - current_price) / current_price
                })
            
            # Minor round numbers (hundreds)
            base = 100
            lower_bound = (current_price // base - 5) * base
            upper_bound = (current_price // base + 6) * base
            
            for level in range(int(lower_bound), int(upper_bound), base):
                if level % 1000 != 0:  # Skip levels already added as major rounds
                    round_levels.append({
                        'price': level,
                        'type': 'MINOR_ROUND',
                        'distance': abs(level - current_price) / current_price
                    })
            
            # Sort by distance from current price
            round_levels.sort(key=lambda x: x['distance'])
            
            analysis['key_levels'] = round_levels[:5]
            
            # Detect chart patterns
            patterns = []
            
            # Doji pattern
            if len(df) > 1 and 'doji' in indicators and indicators['doji'].iloc[-1]:
                patterns.append({
                    'name': 'DOJI',
                    'type': 'REVERSAL',
                    'strength': 0.6
                })
            
            # Engulfing patterns
            if len(df) > 1:
                if 'bullish_engulfing' in indicators and indicators['bullish_engulfing'].iloc[-1]:
                    patterns.append({
                        'name': 'BULLISH_ENGULFING',
                        'type': 'REVERSAL',
                        'direction': 'UP',
                        'strength': 0.8
                    })
                elif 'bearish_engulfing' in indicators and indicators['bearish_engulfing'].iloc[-1]:
                    patterns.append({
                        'name': 'BEARISH_ENGULFING',
                        'type': 'REVERSAL',
                        'direction': 'DOWN',
                        'strength': 0.8
                    })
            
            analysis['patterns'] = patterns
            
            return analysis
            
        except Exception as e:
            logger.error(f"❌ Error analyzing price action: {e}")
            return analysis
    
    async def _analyze_options_data(self, option_chain: Dict[str, Any], iv_data: Dict[str, Any]) -> Dict[str, Any]:
        """Advanced options chain analysis"""
        analysis = {
            "atm_strike": 0,
            "call_put_ratio": 1.0,
            "iv_skew": {},
            "term_structure": {},
            "max_pain": 0,
            "put_wall": [],
            "call_wall": [],
            "expected_range": {},
            "unusual_activity": [],
            "sentiment_score": 0.0
        }
        
        try:
            # Get current underlying price
            underlying_price = await self._get_underlying_price("NIFTY")
            
            # Use volatility surface data
            analysis["iv_skew"] = self.volatility_surface.skew_by_expiry
            analysis["term_structure"] = self.volatility_surface.analyze_term_structure()
            
            # Find ATM strike
            atm_strike = round(underlying_price / 50) * 50  # Round to nearest 50
            analysis["atm_strike"] = atm_strike
            
            # Max pain calculation
            max_pain = await self._calculate_max_pain(option_chain)
            if max_pain:
                analysis["max_pain"] = max_pain
            
            # Expected move calculation
            if iv_data and "atm_iv" in iv_data and iv_data["atm_iv"] > 0:
                atm_iv = iv_data["atm_iv"]
                
                # Calculate expected moves for different periods
                for days, label in [(1, "daily"), (7, "weekly"), (30, "monthly")]:
                    expected_move = underlying_price * atm_iv * np.sqrt(days/365)
                    expected_range = {
                        "lower": underlying_price - expected_move,
                        "upper": underlying_price + expected_move,
                        "percentage": atm_iv * np.sqrt(days/365) * 100
                    }
                    analysis["expected_range"][label] = expected_range
            
            # Get IV percentile from volatility surface
            analysis["iv_percentile"] = iv_data.get("iv_percentile", 0.5)
            
            # Add put/call ratio
            analysis["call_put_ratio"] = iv_data.get("put_call_ratio", 1.0)
            
            # Find option walls (high OI strikes)
            if option_chain and len(option_chain) > 0:
                first_expiry = list(option_chain.keys())[0]  # Use first expiry
                exp_data = option_chain[first_expiry]
                
                call_oi_by_strike = {}
                put_oi_by_strike = {}
                
                for strike, data in exp_data.items():
                    if 'ce' in data and 'oi' in data['ce']:
                        call_oi_by_strike[float(strike)] = data['ce']['oi']
                    
                    if 'pe' in data and 'oi' in data['pe']:
                        put_oi_by_strike[float(strike)] = data['pe']['oi']
                
                # Sort by OI and get top strikes
                call_wall = sorted(call_oi_by_strike.items(), key=lambda x: x[1], reverse=True)[:3]
                put_wall = sorted(put_oi_by_strike.items(), key=lambda x: x[1], reverse=True)[:3]
                
                analysis["call_wall"] = [{"strike": k, "oi": v} for k, v in call_wall]
                analysis["put_wall"] = [{"strike": k, "oi": v} for k, v in put_wall]
            
            # Calculate sentiment score (-1 to 1)
            if analysis["call_put_ratio"] > 0:
                if analysis["call_put_ratio"] > 1:
                    # More puts than calls
                    sentiment = -min(1.0, (analysis["call_put_ratio"] - 1) / 1.5)
                else:
                    # More calls than puts
                    sentiment = min(1.0, (1 - analysis["call_put_ratio"]) / 0.7)
                
                # Adjust by skew
                skew_adjustment = 0
                if analysis["iv_skew"] and first_expiry in analysis["iv_skew"]:
                    skew = analysis["iv_skew"][first_expiry].get("skew", 0)
                    skew_adjustment = -min(0.5, max(-0.5, skew))
                
                analysis["sentiment_score"] = sentiment + skew_adjustment
            
            return analysis
            
        except Exception as e:
            logger.error(f"❌ Error analyzing options data: {e}")
            return analysis
    
    async def _calculate_max_pain(self, option_chain: Dict[str, Any]) -> float:
        """Calculate max pain - the strike price where option writers have the least losses"""
        try:
            if not option_chain or len(option_chain) == 0:
                return 0
                
            first_expiry = list(option_chain.keys())[0]  # Use first expiry
            exp_data = option_chain[first_expiry]
            
            strikes = [float(strike) for strike in exp_data.keys()]
            if not strikes:
                return 0
                
            pain_by_strike = {}
            
            for potential_price in strikes:
                total_pain = 0
                
                for strike, data in exp_data.items():
                    strike_price = float(strike)
                    
                    # Call pain
                    if 'ce' in data and 'oi' in data['ce']:
                        call_oi = data['ce']['oi']
                        call_pain = max(0, potential_price - strike_price) * call_oi
                        total_pain += call_pain
                    
                    # Put pain
                    if 'pe' in data and 'oi' in data['pe']:
                        put_oi = data['pe']['oi']
                        put_pain = max(0, strike_price - potential_price) * put_oi
                        total_pain += put_pain
                
                pain_by_strike[potential_price] = total_pain
            
            # Find strike with minimum pain
            if pain_by_strike:
                max_pain = min(pain_by_strike.items(), key=lambda x: x[1])[0]
                return max_pain
            
            return 0
            
        except Exception as e:
            logger.error(f"❌ Error calculating max pain: {e}")
            return 0
    
    async def _analyze_market_regime(self) -> MarketRegime:
        """Analyze and determine current market regime"""
        try:
            # Get market data
            market_data = self.market_data_cache
            if not market_data:
                return MarketRegime.SIDEWAYS
            
            # Use market regime detector
            regime = self.market_regime_detector.detect_regime(market_data)
            
            return regime
            
        except Exception as e:
            logger.error(f"❌ Error analyzing market regime: {e}")
            return MarketRegime.SIDEWAYS
    
    def _determine_market_direction(self, analysis: Dict[str, Any]) -> Tuple[str, float, float]:
        """Determine overall market direction and strength based on analysis"""
        try:
            direction = MarketDirection.SIDEWAYS
            strength = 0.5
            confidence = 0.5
            
            # Price action factors
            if 'trend' in analysis:
                trend_short = analysis['trend']['short_term'] == 'BULLISH'
                trend_medium = analysis['trend']['medium_term'] == 'BULLISH'
                trend_long = analysis['trend']['long_term'] == 'BULLISH'
                
                trend_strength = analysis['trend'].get('strength', 0.5)
                
                if trend_short and trend_medium and trend_long:
                    direction = MarketDirection.STRONG_BULLISH
                    strength = trend_strength
                elif trend_short and trend_medium:
                    direction = MarketDirection.BULLISH
                    strength = trend_strength * 0.8
                elif trend_short:
                    direction = MarketDirection.WEAK_BULLISH
                    strength = trend_strength * 0.6
                elif not trend_short and not trend_medium and not trend_long:
                    direction = MarketDirection.STRONG_BEARISH
                    strength = trend_strength
                elif not trend_short and not trend_medium:
                    direction = MarketDirection.BEARISH
                    strength = trend_strength * 0.8
                elif not trend_short:
                    direction = MarketDirection.WEAK_BEARISH
                    strength = trend_strength * 0.6
                else:
                    direction = MarketDirection.SIDEWAYS
                    strength = 0.5
            
            # Momentum factors
            if 'momentum' in analysis:
                momentum_value = analysis['momentum'].get('value', 0)
                momentum_signal = analysis['momentum'].get('signal', 'NEUTRAL')
                
                # Adjust direction based on momentum
                if momentum_signal == 'BULLISH' and momentum_value > 0.3:
                    if direction in [MarketDirection.SIDEWAYS, MarketDirection.WEAK_BULLISH]:
                        direction = MarketDirection.BULLISH
                        strength = max(strength, abs(momentum_value))
                elif momentum_signal == 'BEARISH' and momentum_value < -0.3:
                    if direction in [MarketDirection.SIDEWAYS, MarketDirection.WEAK_BEARISH]:
                        direction = MarketDirection.BEARISH
                        strength = max(strength, abs(momentum_value))
                
                # Check for divergence
                if analysis['momentum'].get('divergence', False):
                    divergence_type = analysis['momentum'].get('divergence_type', '')
                    
                    if divergence_type == 'BULLISH' and direction.value.endswith('BEARISH'):
                        direction = MarketDirection.TREND_REVERSAL_UP
                    elif divergence_type == 'BEARISH' and direction.value.endswith('BULLISH'):
                        direction = MarketDirection.TREND_REVERSAL_DOWN
            
            # Volatility factors
            if 'volatility' in analysis:
                vol_regime = analysis['volatility'].get('regime', 'NORMAL')
                vol_percentile = analysis['volatility'].get('percentile', 0.5)
                
                if vol_regime == 'HIGH':
                    if direction == MarketDirection.BULLISH:
                        direction = MarketDirection.VOLATILE_BULLISH
                    elif direction == MarketDirection.BEARISH:
                        direction = MarketDirection.VOLATILE_BEARISH
                    else:
                        direction = MarketDirection.VOLATILE_NEUTRAL
            
            # Options factors
            if 'options_analysis' in analysis:
                options = analysis['options_analysis']
                
                # Check if price is near max pain
                if options.get('max_pain', 0) > 0:
                    underlying_price = self.market_data_cache.get('nifty', {}).get('last_price', 0)
                    
                    if abs(underlying_price - options['max_pain']) / underlying_price < 0.005:  # Within 0.5%
                        if direction == MarketDirection.BULLISH:
                            direction = MarketDirection.CONSOLIDATION_BULLISH
                        elif direction == MarketDirection.BEARISH:
                            direction = MarketDirection.CONSOLIDATION_BEARISH
                        else:
                            direction = MarketDirection.SIDEWAYS
            
            # Order flow factors
            if 'order_flow' in analysis:
                signature = analysis['order_flow'].get('signature', 'NEUTRAL')
                
                if signature == 'AGGRESSIVE_BUYING':
                    if direction == MarketDirection.BEARISH:
                        direction = MarketDirection.TREND_REVERSAL_UP
                    elif direction == MarketDirection.SIDEWAYS:
                        direction = MarketDirection.BREAKOUT_UP
                
                elif signature == 'AGGRESSIVE_SELLING':
                    if direction == MarketDirection.BULLISH:
                        direction = MarketDirection.TREND_REVERSAL_DOWN
                    elif direction == MarketDirection.SIDEWAYS:
                        direction = MarketDirection.BREAKOUT_DOWN
            
            # Calculate confidence
            confidence_factors = []
            
            # Trend alignment confidence
            if 'trend' in analysis:
                trend_alignment = ((analysis['trend']['short_term'] == analysis['trend']['medium_term']) and
                                 (analysis['trend']['medium_term'] == analysis['trend']['long_term']))
                confidence_factors.append(0.8 if trend_alignment else 0.4)
            
            # Momentum alignment confidence
            if 'momentum' in analysis and 'trend' in analysis:
                momentum_alignment = (
                    (analysis['momentum']['signal'] == 'BULLISH' and analysis['trend']['short_term'] == 'BULLISH') or
                    (analysis['momentum']['signal'] == 'BEARISH' and analysis['trend']['short_term'] == 'BEARISH')
                )
                confidence_factors.append(0.7 if momentum_alignment else 0.5)
            
            # Options sentiment alignment
            if 'options_analysis' in analysis:
                sentiment = analysis['options_analysis'].get('sentiment_score', 0)
                
                sentiment_alignment = (
                    (sentiment > 0.2 and direction.value.endswith('BULLISH')) or
                    (sentiment < -0.2 and direction.value.endswith('BEARISH'))
                )
                confidence_factors.append(0.7 if sentiment_alignment else 0.5)
            
            # ML prediction alignment
            if 'ml_predictions' in analysis:
                ml_direction = analysis['ml_predictions'].get('price_direction', 0)
                ml_confidence = analysis['ml_predictions'].get('confidence', 0.5)
                
                ml_alignment = (
                    (ml_direction > 0.2 and direction.value.endswith('BULLISH')) or
                    (ml_direction < -0.2 and direction.value.endswith('BEARISH'))
                )
                confidence_factors.append(ml_confidence if ml_alignment else 0.5)
            
            # Calculate overall confidence
            if confidence_factors:
                confidence = sum(confidence_factors) / len(confidence_factors)
            
            return direction.value, strength, confidence
            
        except Exception as e:
            logger.error(f"❌ Error determining market direction: {e}")
            return MarketDirection.SIDEWAYS.value, 0.5, 0.5
    
    async def _generate_trading_signals(self, market_analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate intelligent trading signals based on market analysis"""
        signals = []
        
        try:
            if not market_analysis:
                return signals
                
            # Get current market regime and direction
            regime = market_analysis.get("regime", MarketRegime.SIDEWAYS.value)
            direction = market_analysis.get("direction", MarketDirection.SIDEWAYS.value)
            strength = market_analysis.get("strength", 0.5)
            confidence = market_analysis.get("confidence", 0.5)
            
            # Get option chain and underlying price
            option_chain = await self._get_option_chain("NIFTY")
            underlying_price = await self._get_underlying_price("NIFTY")
            
            if not option_chain or underlying_price == 0:
                return signals
            
            # Extract first expiry
            if len(option_chain) == 0:
                return signals
                
            first_expiry = list(option_chain.keys())[0]
            
            # Get ATM strike
            atm_strike = round(underlying_price / 50) * 50
            
            # Generate signals based on market regime and direction
            if regime == MarketRegime.BULL_TREND.value:
                if direction in [MarketDirection.STRONG_BULLISH.value, MarketDirection.BULLISH.value]:
                    # Strong bullish in bull trend - directional call buying
                    signals.append(self._create_directional_signal(
                        SignalType.BUY_CALL,
                        "NIFTY",
                        atm_strike,
                        first_expiry,
                        "Directional long call in strong bull trend",
                        confidence * strength,
                        market_analysis
                    ))
                elif direction == MarketDirection.BREAKOUT_UP.value:
                    # Bullish breakout - call debit spread
                    signals.append(self._create_spread_signal(
                        SignalType.BUY_CALL_SPREAD,
                        "NIFTY",
                        atm_strike,
                        atm_strike + 100,
                        first_expiry,
                        "Bullish breakout with call debit spread",
                        confidence * strength,
                        market_analysis
                    ))
                
            elif regime == MarketRegime.BEAR_TREND.value:
                if direction in [MarketDirection.STRONG_BEARISH.value, MarketDirection.BEARISH.value]:
                    # Strong bearish in bear trend - directional put buying
                    signals.append(self._create_directional_signal(
                        SignalType.BUY_PUT,
                        "NIFTY",
                        atm_strike,
                        first_expiry,
                        "Directional long put in strong bear trend",
                        confidence * strength,
                        market_analysis
                    ))
                elif direction == MarketDirection.BREAKOUT_DOWN.value:
                    # Bearish breakout - put debit spread
                    signals.append(self._create_spread_signal(
                        SignalType.BUY_PUT_SPREAD,
                        "NIFTY",
                        atm_strike,
                        atm_strike - 100,
                        first_expiry,
                        "Bearish breakout with put debit spread",
                        confidence * strength,
                        market_analysis
                    ))
                
            elif regime == MarketRegime.SIDEWAYS.value or regime == MarketRegime.LOW_VOLATILITY.value:
                if direction == MarketDirection.CONSOLIDATION_BULLISH.value:
                    # Bullish consolidation - sell puts (cash-secured)
                    signals.append(self._create_directional_signal(
                        SignalType.SELL_PUT,
                        "NIFTY",
                        atm_strike - 100,  # OTM put
                        first_expiry,
                        "Sell OTM put in bullish consolidation",
                        confidence * 0.7,
                        market_analysis
                    ))
                elif direction == MarketDirection.CONSOLIDATION_BEARISH.value:
                    # Bearish consolidation - sell calls (covered)
                    signals.append(self._create_directional_signal(
                        SignalType.SELL_CALL,
                        "NIFTY",
                        atm_strike + 100,  # OTM call
                        first_expiry,
                        "Sell OTM call in bearish consolidation",
                        confidence * 0.7,
                        market_analysis
                    ))
                elif direction == MarketDirection.SIDEWAYS.value:
                    # Sideways market - iron condor
                    signals.append(self._create_iron_condor_signal(
                        "NIFTY",
                        atm_strike,
                        first_expiry,
                        "Iron condor in sideways market",
                        confidence * 0.8,
                        market_analysis
                    ))
                
            elif regime in [MarketRegime.HIGH_VOLATILITY.value, MarketRegime.VOLATILE_BULLISH.value, 
                           MarketRegime.VOLATILE_BEARISH.value]:
                # High volatility regimes - volatility strategies
                
                if 'volatility' in market_analysis and market_analysis['volatility'].get('percentile', 0.5) > 0.7:
                    # High volatility - sell volatility
                    signals.append(self._create_iron_condor_signal(
                        "NIFTY",
                        atm_strike,
                        first_expiry,
                        "Sell volatility with wide iron condor in high vol environment",
                        confidence * 0.7,
                        market_analysis,
                        width=200  # Wider wings in high vol
                    ))
                elif 'volatility' in market_analysis and market_analysis['volatility'].get('percentile', 0.5) < 0.3:
                    # Low volatility but volatile regime - buy volatility
                    signals.append(self._create_straddle_signal(
                        "NIFTY",
                        atm_strike,
                        first_expiry,
                        "Buy volatility with straddle in expanding volatility environment",
                        confidence * 0.7,
                        market_analysis
                    ))
                
            elif regime == MarketRegime.REGIME_TRANSITION.value:
                # Regime transition - wait for confirmation or use neutral strategies
                if direction == MarketDirection.TREND_REVERSAL_UP.value:
                    # Potential bullish reversal
                    signals.append(self._create_spread_signal(
                        SignalType.BUY_CALL_SPREAD,
                        "NIFTY",
                        atm_strike,
                        atm_strike + 100,
                        first_expiry,
                        "Potential bullish reversal with limited risk call spread",
                        confidence * 0.6,
                        market_analysis
                    ))
                elif direction == MarketDirection.TREND_REVERSAL_DOWN.value:
                    # Potential bearish reversal
                    signals.append(self._create_spread_signal(
                        SignalType.BUY_PUT_SPREAD,
                        "NIFTY",
                        atm_strike,
                        atm_strike - 100,
                        first_expiry,
                        "Potential bearish reversal with limited risk put spread",
                        confidence * 0.6,
                        market_analysis
                    ))
            
            # Filter signals by confidence
            signals = [s for s in signals if s["confidence"] > 0.5]
            
            # Add hedge signals for risk management if directional exposure
            if signals and regime not in [MarketRegime.SIDEWAYS.value, MarketRegime.LOW_VOLATILITY.value]:
                for signal in signals:
                    if signal["signal_type"] in [SignalType.BUY_CALL.value, SignalType.BUY_PUT.value]:
                        # Add hedge for directional trades
                        hedge_type = SignalType.BUY_PUT if signal["signal_type"] == SignalType.BUY_CALL.value else SignalType.BUY_CALL
                        
                        signals.append(self._create_directional_signal(
                            hedge_type,
                            "NIFTY",
                            atm_strike + (100 if hedge_type == SignalType.BUY_PUT else -100),
                            first_expiry,
                            f"Hedge for {signal['signal_type']} position",
                            0.6,
                            market_analysis,
                            is_hedge=True
                        ))
            
            return signals
            
        except Exception as e:
            logger.error(f"❌ Error generating trading signals: {e}")
            return []
    
    def _create_directional_signal(self, signal_type: SignalType, underlying: str, 
                                  strike: float, expiry_date: str, reasoning: str, 
                                  confidence: float, market_analysis: Dict[str, Any],
                                  is_hedge: bool = False) -> Dict[str, Any]:
        """Create a directional options signal"""
        option_type = "CE" if signal_type in [SignalType.BUY_CALL, SignalType.SELL_CALL] else "PE"
        side = "BUY" if signal_type in [SignalType.BUY_CALL, SignalType.BUY_PUT] else "SELL"
        
        # Calculate entry price (estimated)
        entry_price = self._estimate_option_price(underlying, strike, expiry_date, option_type)
        
        # Calculate target and stop loss
        if side == "BUY":
            target_price = entry_price * 1.5
            stop_loss = entry_price * 0.7
            risk_reward = (target_price - entry_price) / (entry_price - stop_loss) if entry_price > stop_loss else 1.5
        else:
            target_price = entry_price * 0.5
            stop_loss = entry_price * 1.3
            risk_reward = (entry_price - target_price) / (stop_loss - entry_price) if stop_loss > entry_price else 1.5
        
        # Position sizing
        quantity = self._calculate_position_size(entry_price, confidence, risk_reward, is_hedge)
        
        instrument = {
            "strike_price": strike,
            "option_type": option_type,
            "expiry_date": expiry_date,
            "side": side,
            "quantity": quantity
        }
        
        return {
            "signal_type": signal_type.value,
            "underlying": underlying,
            "instruments": [instrument],
            "confidence": confidence,
            "entry_prices": {str(strike) + option_type: entry_price},
            "target_price": target_price,
            "stop_loss": stop_loss,
            "reasoning": reasoning,
            "risk_reward_ratio": risk_reward,
            "is_hedge": is_hedge,
            "timeframe": TimeFrame.THIRTY_MINUTE.value,
            "expected_duration": "SWING" if "expiry" in expiry_date else "INTRADAY"
        }
    
    def _create_spread_signal(self, signal_type: SignalType, underlying: str,
                             long_strike: float, short_strike: float, expiry_date: str,
                             reasoning: str, confidence: float, market_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Create a spread options signal"""
        if signal_type == SignalType.BUY_CALL_SPREAD:
            option_type = "CE"
            long_side = "BUY"
            short_side = "SELL"
        elif signal_type == SignalType.BUY_PUT_SPREAD:
            option_type = "PE"
            long_side = "BUY"
            short_side = "SELL"
        elif signal_type == SignalType.SELL_CALL_SPREAD:
            option_type = "CE"
            long_side = "BUY"
            short_side = "SELL"
            # Swap strikes for credit spread
            long_strike, short_strike = short_strike, long_strike
        elif signal_type == SignalType.SELL_PUT_SPREAD:
            option_type = "PE"
            long_side = "BUY"
            short_side = "SELL"
            # Swap strikes for credit spread
            long_strike, short_strike = short_strike, long_strike
        else:
            return {}
        
        # Calculate entry prices
        long_price = self._estimate_option_price(underlying, long_strike, expiry_date, option_type)
        short_price = self._estimate_option_price(underlying, short_strike, expiry_date, option_type)
        
        # Net premium
        net_premium = long_price - short_price
        max_profit = abs(long_strike - short_strike) - net_premium if net_premium > 0 else abs(short_price - long_price)
        max_loss = net_premium if net_premium > 0 else abs(long_strike - short_strike) - abs(short_price - long_price)
        
        # Risk-reward ratio
        risk_reward = max_profit / max_loss if max_loss > 0 else 1.0
        
        # Position sizing
        quantity = self._calculate_position_size(max_loss, confidence, risk_reward)
        
        instruments = [
            {
                "strike_price": long_strike,
                "option_type": option_type,
                "expiry_date": expiry_date,
                "side": long_side,
                                "quantity": quantity
            },
            {
                "strike_price": short_strike,
                "option_type": option_type,
                "expiry_date": expiry_date,
                "side": short_side,
                "quantity": quantity
            }
        ]
        
        return {
            "signal_type": signal_type.value,
            "underlying": underlying,
            "instruments": instruments,
            "confidence": confidence,
            "entry_prices": {
                str(long_strike) + option_type: long_price,
                str(short_strike) + option_type: short_price
            },
            "target_price": max_profit * 0.8,  # Target 80% of max profit
            "stop_loss": max_loss * 1.2,  # Stop at 120% of max loss
            "reasoning": reasoning,
            "risk_reward_ratio": risk_reward,
            "is_hedge": False,
            "timeframe": TimeFrame.DAILY.value,
            "expected_duration": "SWING",
            "max_profit": max_profit,
            "max_loss": max_loss
        }
    
    def _create_iron_condor_signal(self, underlying: str, atm_strike: float, expiry_date: str,
                                  reasoning: str, confidence: float, market_analysis: Dict[str, Any],
                                  width: int = 100) -> Dict[str, Any]:
        """Create an iron condor options signal"""
        # Calculate strikes
        call_short_strike = atm_strike + width // 2
        call_long_strike = call_short_strike + width
        put_short_strike = atm_strike - width // 2
        put_long_strike = put_short_strike - width
        
        # Calculate entry prices
        call_short_price = self._estimate_option_price(underlying, call_short_strike, expiry_date, "CE")
        call_long_price = self._estimate_option_price(underlying, call_long_strike, expiry_date, "CE")
        put_short_price = self._estimate_option_price(underlying, put_short_strike, expiry_date, "PE")
        put_long_price = self._estimate_option_price(underlying, put_long_strike, expiry_date, "PE")
        
        # Net premium
        net_credit = (call_short_price - call_long_price) + (put_short_price - put_long_price)
        
        # Max profit and loss
        max_profit = net_credit
        max_loss = width - net_credit
        
        # Risk-reward ratio
        risk_reward = max_profit / max_loss if max_loss > 0 else 1.0
        
        # Position sizing
        quantity = self._calculate_position_size(max_loss, confidence, risk_reward)
        
        instruments = [
            # Call spread
            {
                "strike_price": call_short_strike,
                "option_type": "CE",
                "expiry_date": expiry_date,
                "side": "SELL",
                "quantity": quantity
            },
            {
                "strike_price": call_long_strike,
                "option_type": "CE",
                "expiry_date": expiry_date,
                "side": "BUY",
                "quantity": quantity
            },
            # Put spread
            {
                "strike_price": put_short_strike,
                "option_type": "PE",
                "expiry_date": expiry_date,
                "side": "SELL",
                "quantity": quantity
            },
            {
                "strike_price": put_long_strike,
                "option_type": "PE",
                "expiry_date": expiry_date,
                "side": "BUY",
                "quantity": quantity
            }
        ]
        
        return {
            "signal_type": SignalType.IRON_CONDOR.value,
            "underlying": underlying,
            "instruments": instruments,
            "confidence": confidence,
            "entry_prices": {
                str(call_short_strike) + "CE": call_short_price,
                str(call_long_strike) + "CE": call_long_price,
                str(put_short_strike) + "PE": put_short_price,
                str(put_long_strike) + "PE": put_long_price
            },
            "target_price": max_profit * 0.7,  # Target 70% of max profit
            "stop_loss": max_loss * 1.5,  # Stop at 150% of max loss
            "reasoning": reasoning,
            "risk_reward_ratio": risk_reward,
            "is_hedge": False,
            "timeframe": TimeFrame.DAILY.value,
            "expected_duration": "SWING",
            "max_profit": max_profit,
            "max_loss": max_loss,
            "width": width
        }
    
    def _create_straddle_signal(self, underlying: str, atm_strike: float, expiry_date: str,
                               reasoning: str, confidence: float, market_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Create a straddle options signal (long call and put at same strike)"""
        # Calculate entry prices
        call_price = self._estimate_option_price(underlying, atm_strike, expiry_date, "CE")
        put_price = self._estimate_option_price(underlying, atm_strike, expiry_date, "PE")
        
        # Total cost
        total_cost = call_price + put_price
        
        # Calculate profit target and stop loss
        target_price = total_cost * 1.7  # Target 70% profit
        stop_loss = total_cost * 0.7  # Stop at 30% loss
        
        # Risk-reward ratio (estimated)
        risk_reward = 1.7
        
        # Position sizing
        quantity = self._calculate_position_size(total_cost, confidence, risk_reward)
        
        instruments = [
            {
                "strike_price": atm_strike,
                "option_type": "CE",
                "expiry_date": expiry_date,
                "side": "BUY",
                "quantity": quantity
            },
            {
                "strike_price": atm_strike,
                "option_type": "PE",
                "expiry_date": expiry_date,
                "side": "BUY",
                "quantity": quantity
            }
        ]
        
        return {
            "signal_type": "STRADDLE",  # Custom signal type
            "underlying": underlying,
            "instruments": instruments,
            "confidence": confidence,
            "entry_prices": {
                str(atm_strike) + "CE": call_price,
                str(atm_strike) + "PE": put_price
            },
            "target_price": target_price,
            "stop_loss": stop_loss,
            "reasoning": reasoning,
            "risk_reward_ratio": risk_reward,
            "is_hedge": False,
            "timeframe": TimeFrame.DAILY.value,
            "expected_duration": "SWING",
            "total_cost": total_cost
        }
    
    def _estimate_option_price(self, underlying: str, strike: float, expiry_date: str, option_type: str) -> float:
        """Estimate option price using Black-Scholes model"""
        try:
            # Get current underlying price
            underlying_price = self.market_data_cache.get(underlying.lower(), {}).get('last_price', 0)
            if underlying_price == 0:
                return 0
            
            # Calculate days to expiry
            try:
                expiry = datetime.strptime(expiry_date, '%Y-%m-%d')
                days_to_expiry = max(1, (expiry - datetime.now()).days + 1)
            except:
                days_to_expiry = 7  # Default to 7 days if date format is invalid
            
            # Get implied volatility from surface
            iv = self.volatility_surface.get_iv(strike, expiry_date, option_type)
            if iv == 0:
                # Use default IV based on market regime
                if self.current_market_regime in [MarketRegime.HIGH_VOLATILITY, MarketRegime.VOLATILE_BULLISH, MarketRegime.VOLATILE_BEARISH]:
                    iv = 0.4  # High vol
                elif self.current_market_regime in [MarketRegime.LOW_VOLATILITY]:
                    iv = 0.15  # Low vol
                else:
                    iv = 0.25  # Normal vol
            
            # Calculate option price using Black-Scholes
            price = OptionGreeks.black_scholes_price(
                underlying_price,
                strike,
                days_to_expiry,
                DEFAULT_RISK_FREE_RATE,
                DEFAULT_DIVIDEND_YIELD,
                iv,
                option_type
            )
            
            return price
            
        except Exception as e:
            logger.error(f"❌ Error estimating option price: {e}")
            return 0
    
    def _calculate_position_size(self, price_per_contract: float, confidence: float, 
                                risk_reward: float, is_hedge: bool = False) -> int:
        """Calculate position size based on Kelly criterion and risk management"""
        try:
            # Base size on account size and risk percentage
            account_size = settings.ACCOUNT_SIZE
            risk_percentage = settings.RISK_PERCENTAGE
            
            # Apply Kelly fraction for position sizing
            win_rate = self.winning_trades / max(1, self.total_trades)  # Historical win rate
            
            # Adjust win rate by signal confidence
            adjusted_win_rate = win_rate * 0.7 + confidence * 0.3
            
            # Kelly formula: f* = (bp - q) / b where:
            # f* = fraction of bankroll to bet
            # b = net odds received on the wager (risk_reward)
            # p = probability of winning
            # q = probability of losing (1 - p)
            kelly_fraction = (adjusted_win_rate * risk_reward - (1 - adjusted_win_rate)) / risk_reward
            
            # Limit Kelly to avoid excessive risk (half-Kelly)
            kelly_fraction = min(KELLY_FRACTION, max(0.01, kelly_fraction))
            
            # Calculate max risk amount
            max_risk_amount = account_size * risk_percentage / 100
            
            # For hedges, use smaller size
            if is_hedge:
                max_risk_amount *= 0.5
                kelly_fraction *= 0.5
            
            # Calculate position size
            risk_per_contract = price_per_contract * 0.3  # Assume 30% risk per contract
            max_contracts = int(max_risk_amount * kelly_fraction / risk_per_contract)
            
            # Enforce minimum and maximum limits
            min_contracts = 1
            max_allowed = settings.MAX_POSITION_SIZE
            
            position_size = max(min_contracts, min(max_contracts, max_allowed))
            
            return position_size
            
        except Exception as e:
            logger.error(f"❌ Error calculating position size: {e}")
            return 1  # Default to 1 contract
    
    async def _identify_opportunities(self, market_analysis: Dict[str, Any], 
                                    signals: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Identify high-quality trading opportunities from signals and analysis"""
        opportunities = []
        
        try:
            # Skip if no signals
            if not signals:
                return []
                
            # Process each signal
            for signal in signals:
                # Filter by confidence
                if signal.get("confidence", 0) < 0.5:
                    continue
                
                # Filter by risk-reward
                if signal.get("risk_reward_ratio", 0) < 1.2:
                    continue
                
                # Check market conditions alignment
                is_aligned = self._check_signal_market_alignment(signal, market_analysis)
                
                # Calculate opportunity score
                opportunity_score = (
                    signal.get("confidence", 0) * 0.4 +
                    min(1.0, signal.get("risk_reward_ratio", 0) / 3) * 0.3 +
                    (0.3 if is_aligned else 0)
                )
                
                # Create opportunity object
                opportunity = {
                    "signal": signal,
                    "score": opportunity_score,
                    "confidence": signal.get("confidence", 0),
                    "risk_reward": signal.get("risk_reward_ratio", 0),
                    "is_aligned": is_aligned,
                    "timestamp": datetime.now().isoformat()
                }
                
                opportunities.append(opportunity)
            
            # Sort by score
            opportunities.sort(key=lambda x: x["score"], reverse=True)
            
            return opportunities
            
        except Exception as e:
            logger.error(f"❌ Error identifying opportunities: {e}")
            return []
    
    def _check_signal_market_alignment(self, signal: Dict[str, Any], 
                                      market_analysis: Dict[str, Any]) -> bool:
        """Check if signal aligns with overall market analysis"""
        try:
            signal_type = signal.get("signal_type", "")
            market_direction = market_analysis.get("direction", "")
            
            # For directional signals, check alignment with market direction
            if signal_type == SignalType.BUY_CALL.value:
                return market_direction.endswith("BULLISH")
                
            elif signal_type == SignalType.BUY_PUT.value:
                return market_direction.endswith("BEARISH")
                
            elif signal_type == SignalType.SELL_CALL.value:
                return market_direction.endswith("BEARISH") or market_direction == MarketDirection.SIDEWAYS.value
                
            elif signal_type == SignalType.SELL_PUT.value:
                return market_direction.endswith("BULLISH") or market_direction == MarketDirection.SIDEWAYS.value
                
            # For spreads, check alignment
            elif signal_type == SignalType.BUY_CALL_SPREAD.value:
                return market_direction.endswith("BULLISH")
                
            elif signal_type == SignalType.BUY_PUT_SPREAD.value:
                return market_direction.endswith("BEARISH")
                
            # For iron condors, check for sideways
            elif signal_type == SignalType.IRON_CONDOR.value:
                return market_direction == MarketDirection.SIDEWAYS.value or market_direction.startswith("CONSOLIDATION")
                
            # For straddles, check for volatile conditions
            elif signal_type == "STRADDLE":
                return market_direction.startswith("VOLATILE") or market_direction.startswith("BREAKOUT")
                
            return True  # Default to aligned if no specific checks
            
        except Exception as e:
            logger.error(f"❌ Error checking signal alignment: {e}")
            return False
    
    async def _process_trading_opportunity(self, opportunity: Dict[str, Any]):
        """Process a trading opportunity to execute a trade"""
        try:
            signal = opportunity.get("signal", {})
            
            # Check if we should trade based on opportunity score
            if opportunity.get("score", 0) < 0.7:
                logger.info(f"⚠️ Opportunity score too low: {opportunity.get('score', 0):.2f}")
                return
            
            # Check for existing positions in the same underlying
            underlying = signal.get("underlying", "")
            existing_positions = [p for p in self.active_positions.values() 
                                 if p.underlying == underlying and p.is_active]
            
            # Check if we already have too many positions in this underlying
            if len(existing_positions) >= self.risk_limits["max_position_count"] / 2:
                logger.info(f"⚠️ Maximum positions reached for {underlying}")
                return
            
            # Process the signal to create a trade
            position_id = await self._execute_trading_signal(signal)
            
            if position_id:
                logger.info(f"✅ Successfully executed opportunity: {opportunity.get('score', 0):.2f} score, position {position_id}")
                
                # Add to trade journal
                trade_logger.info(f"NEW POSITION: {position_id} | Signal: {signal.get('signal_type')} | Score: {opportunity.get('score', 0):.2f} | Confidence: {opportunity.get('confidence', 0):.2f} | R:R: {opportunity.get('risk_reward', 0):.2f}")
                
        except Exception as e:
            logger.error(f"❌ Error processing trading opportunity: {e}")
    
    async def _execute_trading_signal(self, signal: Dict[str, Any]) -> Optional[str]:
        """Execute a trading signal by placing orders"""
        try:
            instruments = signal.get("instruments", [])
            if not instruments:
                return None
            
            # Generate position ID
            position_id = f"POS_{uuid.uuid4().hex[:8].upper()}"
            
            # Create position legs
            position_legs = []
            executed_legs = 0
            
            for instrument in instruments:
                # Extract instrument details
                strike = instrument.get("strike_price", 0)
                option_type = instrument.get("option_type", "")
                expiry_date = instrument.get("expiry_date", "")
                side = instrument.get("side", "")
                quantity = instrument.get("quantity", 0)
                
                if not all([strike, option_type, expiry_date, side, quantity > 0]):
                    logger.error(f"❌ Invalid instrument data: {instrument}")
                    continue
                
                # Find actual option instrument
                option_instrument = await self._find_option_instrument(
                    signal.get("underlying", ""),
                    strike,
                    option_type,
                    expiry_date
                )
                
                if not option_instrument:
                    logger.error(f"❌ Option instrument not found: {signal.get('underlying')} {strike} {option_type} {expiry_date}")
                    continue
                
                # Get current price
                entry_price = self._estimate_option_price(
                    signal.get("underlying", ""),
                    strike,
                    expiry_date,
                    option_type
                )
                
                # Execute the trade (place order)
                order_result = await self._place_option_order(
                    option_instrument,
                    side,
                    quantity,
                    entry_price
                )
                
                if order_result:
                    # Create position leg
                    leg = PositionLeg(
                        instrument=option_instrument,
                        quantity=quantity,
                        entry_price=entry_price,
                        current_price=entry_price,
                        side=side,
                        option_type=option_type,
                        strike_price=strike,
                        expiry_date=expiry_date,
                        leg_pnl=0.0,
                        greeks={},
                        orders=[order_result],
                        leg_type="MAIN" if executed_legs == 0 else "HEDGE"
                    )
                    
                    position_legs.append(leg)
                    executed_legs += 1
                else:
                    logger.error(f"❌ Failed to execute order for {strike} {option_type}")
            
            # Check if we have any executed legs
            if not position_legs:
                logger.error("❌ No legs were successfully executed")
                return None
            
            # Create position manager
            position = PositionManager(
                position_id=position_id,
                underlying=signal.get("underlying", ""),
                legs=position_legs,
                current_pnl=0.0,
                unrealized_pnl=0.0,
                max_profit=0.0,
                max_loss=0.0,
                entry_time=datetime.now(),
                last_update=datetime.now(),
                is_active=True,
                strategy_type=signal.get("signal_type", ""),
                greeks={},
                exit_conditions={
                    "target_price": signal.get("target_price", 0),
                    "stop_loss": signal.get("stop_loss", 0),
                    "max_duration_days": 7,
                    "entry_market_regime": self.current_market_regime.value,
                    "exit_on_regime_change": True,
                    "technical_exit_triggered": False
                },
                risk_metrics={
                    "current_drawdown": 0.0,
                    "delta_exposure": 0.0,
                    "gamma_risk": 0.0,
                    "theta_burn": 0.0,
                    "vega_exposure": 0.0,
                    "iv_percentile": self.volatility_surface.iv_percentile.get(30, 0.5)
                },
                trade_journal=[]
            )
            
            # Add journal entry
            position.add_journal_entry("POSITION_OPENED", {
                "signal_type": signal.get("signal_type", ""),
                "reasoning": signal.get("reasoning", ""),
                "legs_count": len(position_legs),
                "confidence": signal.get("confidence", 0),
                "market_regime": self.current_market_regime.value
            })
            
            # Store position
            self.active_positions[position_id] = position
            
            # Send notification
            await websocket_manager.send_trade_alert({
                "type": "POSITION_OPENED",
                "position_id": position_id,
                "signal_type": signal.get("signal_type", ""),
                "underlying": signal.get("underlying", ""),
                "legs_count": len(position_legs),
                "timestamp": datetime.now().isoformat()
            })
            
            return position_id
            
        except Exception as e:
            logger.error(f"❌ Error executing trading signal: {e}")
            return None
    
    async def _find_option_instrument(self, underlying: str, strike: float, 
                                     option_type: str, expiry_date: str) -> Optional[Dict[str, Any]]:
        """Find option instrument details"""
        try:
            # Get options chain
            option_chain = await self._get_option_chain(underlying)
            
            if not option_chain:
                return None
                
            # Check if expiry exists
            if expiry_date not in option_chain:
                return None
                
            # Check if strike exists
            if str(strike) not in option_chain[expiry_date]:
                return None
                
            # Check if option type exists
            option_key = option_type.lower()
            if option_key not in option_chain[expiry_date][str(strike)]:
                return None
                
            # Get instrument data
            instrument_data = option_chain[expiry_date][str(strike)][option_key]
            
            # Enhance with additional data needed for trading
            instrument_data["underlying"] = underlying
            instrument_data["strike_price"] = strike
            instrument_data["option_type"] = option_type
            instrument_data["expiry_date"] = expiry_date
            
            return instrument_data
            
        except Exception as e:
            logger.error(f"❌ Error finding option instrument: {e}")
            return None
    
    async def _place_option_order(self, instrument: Dict[str, Any], side: str, 
                                 quantity: int, price: float) -> Optional[Dict[str, Any]]:
        """Place an option order"""
        try:
            if settings.PAPER_TRADING_MODE:
                # Simulate order execution in paper trading mode
                order_id = f"PAPER_{uuid.uuid4().hex[:8].upper()}"
                
                order_result = {
                    "order_id": order_id,
                    "status": "EXECUTED",
                    "side": side,
                    "quantity": quantity,
                    "price": price,
                    "timestamp": datetime.now().isoformat(),
                    "instrument": instrument
                }
                
                logger.info(f"📝 Paper trading order placed: {side} {quantity} x {instrument.get('underlying')} {instrument.get('strike_price')} {instrument.get('option_type')}")
                
                return order_result
            else:
                # Real trading mode - place actual order
                security_id = instrument.get("security_id", "")
                exchange_segment = "NSE_FNO"  # For Indian options
                
                if not security_id:
                    logger.error("❌ Missing security ID for order placement")
                    return None
                
                order_data = {
                    "dhanClientId": settings.DHAN_CLIENT_ID,
                    "correlationId": f"ORDER_{uuid.uuid4().hex[:8].upper()}",
                    "transactionType": side,
                    "exchangeSegment": exchange_segment,
                    "productType": settings.PRODUCT_TYPE,  # MARGIN, INTRADAY, etc.
                    "orderType": "LIMIT",
                    "securityId": security_id,
                    "quantity": str(quantity),
                    "price": str(price),
                    "validity": "DAY",
                    "offMarket": False,
                    "disclosedQuantity": "",
                    "tradingSymbol": instrument.get('underlying', '')  # For freeze limit lookup
                }
                
                # Place order through broker API with automatic slicing for large orders
                order_result = await dhan_service.place_order_with_slicing(order_data)
                
                if order_result:
                    logger.info(f"✅ Real order placed: {side} {quantity} x {instrument.get('underlying')} {instrument.get('strike_price')} {instrument.get('option_type')}")
                    return order_result
                else:
                    logger.error("❌ Failed to place real order")
                    return None
                
        except Exception as e:
            logger.error(f"❌ Error placing option order: {e}")
            return None
    
    async def _broadcast_market_updates(self, market_analysis: Dict[str, Any]):
        """Broadcast market updates to clients"""
        try:
            # Prepare simplified analysis for broadcast
            broadcast_data = {
                "timestamp": datetime.now().isoformat(),
                "market_regime": self.current_market_regime.value,
                "market_direction": market_analysis.get("direction", "UNKNOWN"),
                "confidence": market_analysis.get("confidence", 0),
                "support_resistance": {
                    "support": market_analysis.get("support_levels", [])[:2],
                    "resistance": market_analysis.get("resistance_levels", [])[:2]
                },
                "volatility": market_analysis.get("volatility", {}).get("regime", "NORMAL"),
                "sentiment": market_analysis.get("options_analysis", {}).get("sentiment_score", 0),
                "patterns": market_analysis.get("patterns", []),
                "trading_signals": len(self.current_opportunities),
                "active_positions": len([p for p in self.active_positions.values() if p.is_active])
            }
            
            # Add ML predictions if available
            if "ml_predictions" in market_analysis:
                broadcast_data["predictions"] = {
                    "direction": market_analysis["ml_predictions"].get("price_direction", 0),
                    "magnitude": market_analysis["ml_predictions"].get("price_magnitude", 0),
                    "confidence": market_analysis["ml_predictions"].get("confidence", 0)
                }
            
            # Send through websocket
            await websocket_manager.send_market_update(broadcast_data)
            
        except Exception as e:
            logger.error(f"❌ Error broadcasting market updates: {e}")
    
    async def _update_position_prices(self, position: PositionManager):
        """Update position with current prices"""
        try:
            for leg in position.legs:
                # Get current option price
                current_price = self._estimate_option_price(
                    position.underlying,
                    leg.strike_price,
                    leg.expiry_date,
                    leg.option_type
                )
                
                if current_price > 0:
                    leg.current_price = current_price
            
            position.last_update = datetime.now()
            
        except Exception as e:
            logger.error(f"❌ Error updating position prices: {e}")
    
    async def _adjust_position(self, position: PositionManager, reason: str, details: Dict[str, Any]):
        """Adjust a position based on Greeks or risk metrics"""
        try:
            logger.info(f"🔧 Adjusting position {position.position_id} - Reason: {reason}")
            
            position.add_journal_entry("ADJUSTMENT_NEEDED", {
                "reason": reason,
                "details": details
            })
            
            if reason == "HIGH_DELTA_EXPOSURE":
                # Add delta hedge
                await self._add_delta_hedge(position, details)
                
            elif reason == "HIGH_GAMMA_EXPOSURE_NEAR_EXPIRY":
                # Roll position to next expiry
                await self._roll_position(position, details)
                
            elif reason == "HIGH_VEGA_IN_HIGH_IV":
                # Add vega hedge
                await self._add_vega_hedge(position, details)
                
            elif reason == "PROFIT_DRAWDOWN_PROTECTION":
                # Take partial profits
                await self._take_partial_profits(position, details)
                
            elif reason == "EXCESSIVE_THETA_DECAY":
                # Roll to next expiry
                await self._roll_position(position, details)
                
            elif reason == "DELTA_LIMIT":
                # Add delta hedge for risk limit breach
                await self._add_delta_hedge(position, details, is_emergency=True)
                
            # Update position after adjustment
            await self._update_position_prices(position)
            underlying_price = await self._get_underlying_price(position.underlying)
            position.update_greeks(underlying_price, self.volatility_surface)
            position.update_pnl()
            
            # Add journal entry
            position.add_journal_entry("ADJUSTMENT_COMPLETED", {
                "reason": reason,
                "new_delta": position.greeks.get("delta", 0),
                "new_gamma": position.greeks.get("gamma", 0),
                "new_vega": position.greeks.get("vega", 0)
            })
            
        except Exception as e:
            logger.error(f"❌ Error adjusting position {position.position_id}: {e}")
    
    async def _add_delta_hedge(self, position: PositionManager, details: Dict[str, Any], is_emergency: bool = False):
        """Add a delta hedge to the position"""
        try:
            # Get delta and target delta
            current_delta = position.greeks.get("delta", 0)
            target_delta = details.get("target_delta", 0)
            
            # If emergency, target zero delta
            if is_emergency:
                target_delta = 0
            
            # Calculate how much delta to hedge
            delta_to_hedge = current_delta - target_delta
            
            if abs(delta_to_hedge) < 0.1:
                logger.info(f"Delta adjustment too small, skipping: {delta_to_hedge:.2f}")
                return
            
            # Determine hedge direction
            hedge_side = "BUY" if delta_to_hedge < 0 else "SELL"
            hedge_option_type = "CE" if delta_to_hedge < 0 else "PE"  # Buy calls for negative delta, puts for positive
            
            # Get ATM strike
            underlying_price = await self._get_underlying_price(position.underlying)
            atm_strike = round(underlying_price / 50) * 50
            
            # Get expiry date (use nearest expiry)
            option_chain = await self._get_option_chain(position.underlying)
            if not option_chain or len(option_chain) == 0:
                logger.error("❌ Failed to get option chain for hedge")
                return
                
            expiry_date = list(option_chain.keys())[0]
            
            # Find option instrument
            option_instrument = await self._find_option_instrument(
                position.underlying,
                atm_strike,
                hedge_option_type,
                expiry_date
            )
            
            if not option_instrument:
                logger.error(f"❌ Hedge instrument not found: {atm_strike} {hedge_option_type}")
                return
            
            # Calculate option delta
            option_delta = 0.5  # Default approximation for ATM options
            try:
                option = OptionGreeks(
                    spot=underlying_price,
                    strike=atm_strike,
                    expiry_days=(datetime.strptime(expiry_date, "%Y-%m-%d") - datetime.now()).days,
                    interest_rate=DEFAULT_RISK_FREE_RATE,
                    dividend_yield=DEFAULT_DIVIDEND_YIELD,
                    option_type=hedge_option_type,
                    volatility=0.3
                )
                option_delta = abs(option.calculate_greeks()["delta"])
            except:
                pass
            
            if option_delta == 0:
                option_delta = 0.5  # Fallback
            
            # Calculate quantity needed for hedge
            hedge_quantity = max(1, round(abs(delta_to_hedge) / option_delta))
            
            # Get current price
            entry_price = self._estimate_option_price(
                position.underlying,
                atm_strike,
                expiry_date,
                hedge_option_type
            )
            
            # Place hedge order
            order_result = await self._place_option_order(
                option_instrument,
                hedge_side,
                hedge_quantity,
                entry_price
            )
            
            if order_result:
                # Create hedge leg
                hedge_leg = PositionLeg(
                    instrument=option_instrument,
                    quantity=hedge_quantity,
                    entry_price=entry_price,
                    current_price=entry_price,
                    side=hedge_side,
                    option_type=hedge_option_type,
                    strike_price=atm_strike,
                    expiry_date=expiry_date,
                    leg_pnl=0.0,
                    greeks={},
                    orders=[order_result],
                    leg_type="HEDGE"
                )
                
                # Add hedge leg to position
                position.legs.append(hedge_leg)
                
                logger.info(f"✅ Delta hedge added: {hedge_side} {hedge_quantity} x {position.underlying} {atm_strike} {hedge_option_type}")
            else:
                logger.error(f"❌ Failed to add delta hedge")
                
        except Exception as e:
            logger.error(f"❌ Error adding delta hedge: {e}")
    
    async def _roll_position(self, position: PositionManager, details: Dict[str, Any]):
        """Roll position to next expiry date"""
        try:
            # Get option chain
            option_chain = await self._get_option_chain(position.underlying)
            if not option_chain or len(option_chain) < 2:
                logger.error("❌ Insufficient expiries for position roll")
                return
                
            # Find current expiry legs
            current_expiry = min(leg.expiry_date for leg in position.legs)
            
            # Find next expiry date
            expiry_dates = sorted(list(option_chain.keys()))
            next_expiry_index = expiry_dates.index(current_expiry) + 1 if current_expiry in expiry_dates else 0
            
            if next_expiry_index >= len(expiry_dates):
                logger.error("❌ No next expiry date available")
                return
                
            next_expiry = expiry_dates[next_expiry_index]
            
            # Roll each leg with current expiry
            for leg in list(position.legs):  # Create a copy to iterate while modifying
                if leg.expiry_date == current_expiry:
                    # Close current leg
                    close_order = await self._place_option_order(
                        leg.instrument,
                        "SELL" if leg.side == "BUY" else "BUY",  # Opposite side
                        leg.quantity,
                        leg.current_price
                    )
                    
                    if not close_order:
                        logger.error(f"❌ Failed to close leg for roll: {leg.strike_price} {leg.option_type}")
                        continue
                    
                    # Open new leg with next expiry
                    new_instrument = await self._find_option_instrument(
                        position.underlying,
                        leg.strike_price,
                        leg.option_type,
                        next_expiry
                    )
                    
                    if not new_instrument:
                        logger.error(f"❌ Failed to find new instrument for roll: {leg.strike_price} {leg.option_type}")
                        continue
                    
                    # Get new price
                    entry_price = self._estimate_option_price(
                        position.underlying,
                        leg.strike_price,
                        next_expiry,
                        leg.option_type
                    )
                    
                    # Place new order
                    new_order = await self._place_option_order(
                        new_instrument,
                        leg.side,
                        leg.quantity,
                        entry_price
                    )
                    
                    if not new_order:
                        logger.error(f"❌ Failed to open new leg for roll: {leg.strike_price} {leg.option_type}")
                        continue
                    
                    # Create new leg
                    new_leg = PositionLeg(
                        instrument=new_instrument,
                        quantity=leg.quantity,
                        entry_price=entry_price,
                        current_price=entry_price,
                        side=leg.side,
                        option_type=leg.option_type,
                        strike_price=leg.strike_price,
                        expiry_date=next_expiry,
                        leg_pnl=0.0,
                        greeks={},
                        orders=[new_order],
                        leg_type=leg.leg_type
                    )
                    
                    # Remove old leg and add new one
                    position.legs.remove(leg)
                    position.legs.append(new_leg)
                    
                    logger.info(f"✅ Rolled leg from {current_expiry} to {next_expiry}: {leg.strike_price} {leg.option_type}")
            
            # Add journal entry
            position.add_journal_entry("POSITION_ROLLED", {
                "from_expiry": current_expiry,
                "to_expiry": next_expiry,
                "reason": details.get("reason", "EXPIRY_APPROACHING")
            })
            
        except Exception as e:
            logger.error(f"❌ Error rolling position: {e}")
    
    async def _add_vega_hedge(self, position: PositionManager, details: Dict[str, Any]):
        """Add a vega hedge to the position"""
        try:
            # Get vega exposure
            current_vega = position.greeks.get("vega", 0)
            
            if abs(current_vega) < 0.1:
                logger.info(f"Vega exposure too small to hedge: {current_vega:.2f}")
                return
            
            # Determine hedge direction
            hedge_side = "SELL" if current_vega > 0 else "BUY"  # Sell options if positive vega, buy if negative
            
            # Get ATM strike
            underlying_price = await self._get_underlying_price(position.underlying)
            atm_strike = round(underlying_price / 50) * 50
            
            # For vega hedge, use both call and put (to reduce delta impact)
            option_types = ["CE", "PE"]
            
            # Get expiry date (use farther expiry for more vega)
            option_chain = await self._get_option_chain(position.underlying)
            if not option_chain or len(option_chain) == 0:
                logger.error("❌ Failed to get option chain for vega hedge")
                return
                
            expiry_dates = sorted(list(option_chain.keys()))
            if len(expiry_dates) > 1:
                expiry_date = expiry_dates[1]  # Use second expiry for more vega
            else:
                expiry_date = expiry_dates[0]
            
            for option_type in option_types:
                # Find option instrument
                option_instrument = await self._find_option_instrument(
                    position.underlying,
                    atm_strike,
                    option_type,
                    expiry_date
                )
                
                if not option_instrument:
                    logger.error(f"❌ Vega hedge instrument not found: {atm_strike} {option_type}")
                    continue
                
                # Calculate option vega
                option_vega = 0.2  # Default approximation
                try:
                    option = OptionGreeks(
                        spot=underlying_price,
                        strike=atm_strike,
                        expiry_days=(datetime.strptime(expiry_date, "%Y-%m-%d") - datetime.now()).days,
                        interest_rate=DEFAULT_RISK_FREE_RATE,
                        dividend_yield=DEFAULT_DIVIDEND_YIELD,
                        option_type=option_type,
                        volatility=0.3
                    )
                    option_vega = abs(option.calculate_greeks()["vega"])
                except:
                    pass
                
                if option_vega == 0:
                    option_vega = 0.2  # Fallback
                
                # Calculate quantity needed for hedge (divide by 2 since we're using both call and put)
                hedge_quantity = max(1, round(abs(current_vega) / option_vega / 2))
                
                # Get current price
                entry_price = self._estimate_option_price(
                    position.underlying,
                    atm_strike,
                    expiry_date,
                    option_type
                )
                
                # Place hedge order
                order_result = await self._place_option_order(
                    option_instrument,
                    hedge_side,
                    hedge_quantity,
                    entry_price
                )
                
                if order_result:
                    # Create hedge leg
                    hedge_leg = PositionLeg(
                        instrument=option_instrument,
                        quantity=hedge_quantity,
                        entry_price=entry_price,
                        current_price=entry_price,
                        side=hedge_side,
                        option_type=option_type,
                        strike_price=atm_strike,
                        expiry_date=expiry_date,
                        leg_pnl=0.0,
                        greeks={},
                        orders=[order_result],
                        leg_type="VEGA_HEDGE"
                    )
                    
                    # Add hedge leg to position
                    position.legs.append(hedge_leg)
                    
                    logger.info(f"✅ Vega hedge added: {hedge_side} {hedge_quantity} x {position.underlying} {atm_strike} {option_type}")
                else:
                    logger.error(f"❌ Failed to add vega hedge for {option_type}")
            
        except Exception as e:
            logger.error(f"❌ Error adding vega hedge: {e}")
    
    async def _take_partial_profits(self, position: PositionManager, details: Dict[str, Any]):
        """Take partial profits on a profitable position"""
        try:
            # Check if position is in profit
            if position.unrealized_pnl <= 0:
                logger.info(f"Position {position.position_id} not in profit, skipping partial exit")
                return
            
            # Calculate drawdown
            drawdown = details.get("drawdown", 0)
            max_profit = details.get("max_profit", 0)
            
            # Determine what percentage to exit
            exit_percentage = min(0.5, drawdown * 2)  # 50% max exit
            
            logger.info(f"Taking partial profits on {position.position_id}: {exit_percentage:.0%} of position")
            
            # Close a portion of each leg
            for leg in position.legs:
                # Calculate quantity to close
                qty_to_close = max(1, round(leg.quantity * exit_percentage))
                
                if qty_to_close >= leg.quantity:
                    qty_to_close = leg.quantity // 2  # At least leave half
                
                if qty_to_close == 0:
                    continue
                
                # Place closing order
                close_order = await self._place_option_order(
                    leg.instrument,
                    "SELL" if leg.side == "BUY" else "BUY",  # Opposite side
                    qty_to_close,
                    leg.current_price
                )
                
                if close_order:
                    # Update leg quantity
                    leg.quantity -= qty_to_close
                    
                    # Calculate realized P&L
                    realized_pnl = (leg.current_price - leg.entry_price) * qty_to_close
                    if leg.side == "SELL":
                        realized_pnl = -realized_pnl
                    
                    logger.info(f"✅ Partial exit: {qty_to_close} of {leg.strike_price} {leg.option_type}, P&L: {realized_pnl:.2f}")
                else:
                    logger.error(f"❌ Failed to execute partial exit for {leg.strike_price} {leg.option_type}")
            
            # Add journal entry
            position.add_journal_entry("PARTIAL_PROFIT_TAKEN", {
                "exit_percentage": exit_percentage,
                "drawdown_from_max": drawdown,
                "max_profit": max_profit,
                "current_pnl": position.unrealized_pnl
            })
            
        except Exception as e:
            logger.error(f"❌ Error taking partial profits: {e}")
    
    async def _close_position(self, position_id: str, reason: str):
        """Close an entire position"""
        try:
            if position_id not in self.active_positions:
                logger.error(f"❌ Position not found: {position_id}")
                return
            
            position = self.active_positions[position_id]
            
            if not position.is_active:
                logger.warning(f"⚠️ Position already closed: {position_id}")
                return
            
            logger.info(f"🔴 Closing position {position_id} - Reason: {reason}")
            
            total_pnl = 0
            
            # Close each leg
            for leg in position.legs:
                if leg.quantity <= 0:
                    continue
                
                # Place closing order
                close_order = await self._place_option_order(
                    leg.instrument,
                    "SELL" if leg.side == "BUY" else "BUY",  # Opposite side
                    leg.quantity,
                    leg.current_price
                )
                
                if close_order:
                    # Calculate realized P&L
                    leg_pnl = (leg.current_price - leg.entry_price) * leg.quantity
                    if leg.side == "SELL":
                        leg_pnl = -leg_pnl
                    
                    total_pnl += leg_pnl
                    logger.info(f"✅ Closed leg: {leg.quantity} x {leg.strike_price} {leg.option_type}, P&L: {leg_pnl:.2f}")
                else:
                    logger.error(f"❌ Failed to close leg: {leg.strike_price} {leg.option_type}")
            
            # Mark position as inactive
            position.is_active = False
            position.current_pnl = total_pnl
            
            # Add to trade statistics
            self.total_trades += 1
            if total_pnl > 0:
                self.winning_trades += 1
                self.total_profit += total_pnl
            else:
                self.losing_trades += 1
                self.total_loss += abs(total_pnl)
            
            self.daily_pnl += total_pnl
            
            # Add journal entry
            position.add_journal_entry("POSITION_CLOSED", {
                "reason": reason,
                "total_pnl": total_pnl,
                "duration_hours": (datetime.now() - position.entry_time).total_seconds() / 3600,
                "win": total_pnl > 0
            })
            
            # Send notification
            await websocket_manager.send_trade_alert({
                "type": "POSITION_CLOSED",
                "position_id": position_id,
                "reason": reason,
                "pnl": total_pnl,
                "win": total_pnl > 0,
                "timestamp": datetime.now().isoformat()
            })
            
            # Log to trade journal
            trade_logger.info(f"CLOSED: {position_id} | PnL: ${total_pnl:.2f} | Reason: {reason} | {'WIN' if total_pnl > 0 else 'LOSS'} | Duration: {(datetime.now() - position.entry_time).total_seconds() / 3600:.1f}h")
            
        except Exception as e:
            logger.error(f"❌ Error closing position {position_id}: {e}")
    
    async def _emergency_close_all_positions(self, reason: str):
        """Close all positions in emergency situations"""
        try:
            logger.warning(f"🚨 EMERGENCY POSITION CLOSURE: {reason}")
            
            # Close all active positions
            for position_id in list(self.active_positions.keys()):
                position = self.active_positions[position_id]
                
                if position.is_active:
                    await self._close_position(position_id, f"EMERGENCY_{reason}")
            
            # Send emergency notification
            await websocket_manager.send_system_alert({
                "type": "EMERGENCY",
                "message": f"Emergency closure of all positions: {reason}",
                "timestamp": datetime.now().isoformat(),
                "daily_pnl": self.daily_pnl
            }, "critical")
            
            # Log to trade journal
            trade_logger.warning(f"EMERGENCY: All positions closed due to {reason} | Daily PnL: ${self.daily_pnl:.2f}")
            
        except Exception as e:
            logger.error(f"❌ Error in emergency position closure: {e}")
    
    async def _calculate_portfolio_risk(self):
        """Calculate portfolio level risk metrics"""
        try:
            if not self.active_positions:
                self.portfolio_var = 0
                self.portfolio_beta = 1
                return
            
            # Get underlying price
            nifty_price = await self._get_underlying_price("NIFTY")
            if nifty_price == 0:
                return
            
            # Calculate total delta and vega exposure
            total_delta = 0
            total_vega = 0
            position_values = []
            
            for position in self.active_positions.values():
                if not position.is_active:
                    continue
                    
                total_delta += position.greeks.get("delta", 0)
                total_vega += position.greeks.get("vega", 0)
                
                # Sum of all leg values for position size
                position_value = sum(
                    leg.current_price * leg.quantity 
                    for leg in position.legs
                )
                position_values.append(position_value)
            
            # Calculate Value at Risk (simple approach)
            total_position_value = sum(position_values)
            # Assuming 2 standard deviations (95% confidence) and 20% annual volatility
            daily_vol = 0.2 / math.sqrt(252)  # Convert annual vol to daily
            self.portfolio_var = total_position_value * daily_vol * 2
            
            # Calculate beta (delta exposure relative to position size)
            if total_position_value > 0:
                delta_dollars = total_delta * nifty_price
                self.portfolio_beta = delta_dollars / total_position_value
            else:
                self.portfolio_beta = 0
            
            # Update portfolio risk metrics
            self.risk_metrics = {
                "total_delta": total_delta,
                "delta_dollars": total_delta * nifty_price,
                "total_vega": total_vega,
                "var_95": self.portfolio_var,
                "beta": self.portfolio_beta,
                "position_count": len([p for p in self.active_positions.values() if p.is_active]),
                "position_value": total_position_value
            }
            
        except Exception as e:
            logger.error(f"❌ Error calculating portfolio risk: {e}")
    
    async def _reduce_portfolio_risk(self):
        """Reduce portfolio risk by adjusting or closing positions"""
        try:
            # Get active positions sorted by risk
            active_positions = [(pid, pos) for pid, pos in self.active_positions.items() if pos.is_active]
            
            if not active_positions:
                return
            
            # Sort by absolute delta exposure
            active_positions.sort(key=lambda x: abs(x[1].greeks.get("delta", 0)), reverse=True)
            
            # Start with highest delta position
            position_id, position = active_positions[0]
            
            logger.warning(f"🚨 Reducing portfolio risk - adjusting position {position_id}")
            
            # Add hedge to reduce exposure
            await self._adjust_position(position, "PORTFOLIO_RISK_REDUCTION", {
                "current_delta": position.greeks.get("delta", 0),
                "target_delta": position.greeks.get("delta", 0) * 0.3,  # Reduce by 70%
                "portfolio_var": self.portfolio_var,
                "portfolio_beta": self.portfolio_beta
            })
            
            # If still too high, close smallest position
            if len(active_positions) > 1 and self.portfolio_var > self.risk_limits["max_position_count"]:
                # Sort by unrealized P&L
                active_positions.sort(key=lambda x: x[1].unrealized_pnl)
                
                # Close worst performing position
                position_id, _ = active_positions[0]
                await self._close_position(position_id, "PORTFOLIO_RISK_REDUCTION")
                
        except Exception as e:
            logger.error(f"❌ Error reducing portfolio risk: {e}")
    
    async def _predict_price_movement(self, symbol: str) -> Dict[str, Any]:
        """Predict future price movement using ML models"""
        try:
            prediction = {
                "direction": 0,
                "magnitude": 0,
                "predicted_move": 0,
                "confidence": 0.5,
                "direction_str": "NEUTRAL",
                "timeframe": "SHORT_TERM"
            }
            
            # Check if we have the features and models
            if symbol not in self.feature_store or "price_prediction" not in self.models:
                return prediction
            
            # Get features
            features = self.feature_store[symbol]
            if isinstance(features, dict):  # Multi-timeframe
                if TimeFrame.FIVE_MINUTE.value in features:
                    features_df = features[TimeFrame.FIVE_MINUTE.value]
                else:
                    return prediction
            else:  # Single timeframe
                features_df = features
            
            if features_df.empty:
                return prediction
            
            # Extract last row for prediction
            last_features = features_df.iloc[-1].values.reshape(1, -1)
            
            # Standardize features
            scaler = StandardScaler()
            last_features_scaled = scaler.fit_transform(last_features)
            
            # Traditional ML prediction
            if self.models["price_prediction"]:
                try:
                    price_pred = self.models["price_prediction"].predict(last_features_scaled)[0]
                    current_price = self.market_data_cache.get(symbol.lower(), {}).get('last_price', 0)
                    
                    if current_price > 0:
                        predicted_move = (price_pred - current_price) / current_price * 100
                        
                        # Set direction and magnitude
                        direction = 1 if predicted_move > 0 else (-1 if predicted_move < 0 else 0)
                        magnitude = min(1.0, abs(predicted_move) / 2)  # Scale to 0-1
                        
                        prediction.update({
                            "direction": direction,
                            "magnitude": magnitude,
                            "predicted_move": predicted_move,
                            "direction_str": "BULLISH" if direction > 0 else ("BEARISH" if direction < 0 else "NEUTRAL")
                        })
                except:
                    pass
            
            # Deep learning prediction if available
            if TF_AVAILABLE and "transformer_price" in self.models and self.models["transformer_price"].model:
                try:
                    # Get sequence data
                    sequence_data = np.array([features_df.iloc[-60:].values])
                    
                    # Make prediction
                    dl_prediction = self.models["transformer_price"].predict(sequence_data)
                    if dl_prediction is not None:
                        dl_predicted_move = dl_prediction[0][0]
                        
                        # Combine predictions (70% traditional, 30% deep learning)
                        combined_move = prediction["predicted_move"] * 0.7 + dl_predicted_move * 0.3
                        prediction["predicted_move"] = combined_move
                        prediction["direction"] = 1 if combined_move > 0 else (-1 if combined_move < 0 else 0)
                        prediction["magnitude"] = min(1.0, abs(combined_move) / 2)
                        prediction["direction_str"] = "BULLISH" if prediction["direction"] > 0 else ("BEARISH" if prediction["direction"] < 0 else "NEUTRAL")
                except:
                    pass
            
            # Calculate confidence based on feature importance
            if "price" in self.feature_importance and len(last_features[0]) == len(self.feature_importance["price"]):
                # Weight prediction by importance of top features
                feature_weights = self.feature_importance["price"]
                top_features_weight = sum(sorted(feature_weights, reverse=True)[:5])  # Sum top 5 features
                prediction["confidence"] = min(0.9, 0.4 + top_features_weight * 2)  # Scale to confidence
            
            return prediction
            
        except Exception as e:
            logger.error(f"❌ Error predicting price movement: {e}")
            return {"direction": 0, "magnitude": 0, "predicted_move": 0, "confidence": 0.5, "direction_str": "NEUTRAL"}
    
    async def _predict_volatility(self, symbol: str) -> Dict[str, Any]:
        """Predict future volatility using ML models"""
        try:
            prediction = {
                "forecast": 0,
                "iv_forecast": 0,
                "volatility_regime": "NORMAL",
                "expected_range": {},
                "confidence": 0.5
            }
            
            # Check if we have the features and models
            if symbol not in self.feature_store or "volatility_prediction" not in self.models:
                return prediction
            
            # Get features
            features = self.feature_store[symbol]
            if isinstance(features, dict):  # Multi-timeframe
                if TimeFrame.FIVE_MINUTE.value in features:
                    features_df = features[TimeFrame.FIVE_MINUTE.value]
                else:
                    return prediction
            else:  # Single timeframe
                features_df = features
            
            if features_df.empty:
                return prediction
            
            # Extract last row for prediction
            last_features = features_df.iloc[-1].values.reshape(1, -1)
            
            # Standardize features
            scaler = StandardScaler()
            last_features_scaled = scaler.fit_transform(last_features)
            
            # Traditional ML prediction
            if self.models["volatility_prediction"]:
                try:
                    vol_pred = self.models["volatility_prediction"].predict(last_features_scaled)[0]
                    
                    # Convert to annualized volatility
                    annual_vol = vol_pred * math.sqrt(252)
                    
                    # Get current underlying price
                    current_price = self.market_data_cache.get(symbol.lower(), {}).get('last_price', 0)
                    
                    # Calculate expected range
                    expected_range = {}
                    for days, label in [(1, "daily"), (7, "weekly")]:
                        range_value = current_price * annual_vol * math.sqrt(days/252)
                        expected_range[label] = {
                            "lower": current_price - range_value,
                            "upper": current_price + range_value,
                            "percentage": annual_vol * math.sqrt(days/252) * 100
                        }
                    
                    # Determine volatility regime
                    if annual_vol > 0.3:
                        vol_regime = "HIGH"
                    elif annual_vol < 0.15:
                        vol_regime = "LOW"
                    else:
                        vol_regime = "NORMAL"
                    
                    # Set predictions
                    prediction.update({
                        "forecast": annual_vol,
                        "volatility_regime": vol_regime,
                        "expected_range": expected_range
                    })
                except:
                    pass
            
            # Get IV forecast from volatility surface
            if self.volatility_surface and self.volatility_surface.term_structure:
                # Use current ATM IV
                prediction["iv_forecast"] = self.volatility_surface.term_structure.get(30, 0)  # 30-day IV
                
                # Get IV percentile
                prediction["iv_percentile"] = self.volatility_surface.iv_percentile.get(30, 0.5)
            
            # Deep learning prediction if available
            if TF_AVAILABLE and "lstm_volatility" in self.models and self.models["lstm_volatility"].model:
                try:
                    # Get sequence data
                    sequence_data = np.array([features_df.iloc[-30:].values])
                    
                    # Make prediction
                    dl_prediction = self.models["lstm_volatility"].predict(sequence_data)
                    if dl_prediction is not None:
                        dl_vol_pred = dl_prediction[0][0]
                        
                        # Combine predictions (60% traditional, 40% deep learning)
                        combined_vol = prediction["forecast"] * 0.6 + dl_vol_pred * 0.4
                        prediction["forecast"] = combined_vol
                except:
                    pass
            
            return prediction
            
        except Exception as e:
            logger.error(f"❌ Error predicting volatility: {e}")
            return {"forecast": 0, "iv_forecast": 0, "volatility_regime": "NORMAL"}
    
    async def _predict_regime_change(self, symbol: str) -> Dict[str, Any]:
        """Predict potential market regime changes"""
        try:
            prediction = {
                "current_regime": self.current_market_regime.value,
                "next_regime": self.current_market_regime.value,
                "probability": 0.0,
                "timeframe": "SHORT_TERM"
            }
            
            # Check if we have the features and model
            if symbol not in self.feature_store or "regime_classification" not in self.models:
                return prediction
            
            # Get features
            features = self.feature_store[symbol]
            if isinstance(features, dict):  # Multi-timeframe
                if TimeFrame.DAILY.value in features:
                    features_df = features[TimeFrame.DAILY.value]
                else:
                    return prediction
            else:  # Single timeframe
                features_df = features
            
            if features_df.empty:
                return prediction
            
            # Extract last row for prediction
            last_features = features_df.iloc[-1].values.reshape(1, -1)
            
            # Standardize features
            scaler = StandardScaler()
            last_features_scaled = scaler.fit_transform(last_features)
            
            # Traditional ML prediction
            if self.models["regime_classification"]:
                try:
                    regime_pred = self.models["regime_classification"].predict(last_features_scaled)[0]
                    regime_proba = self.models["regime_classification"].predict_proba(last_features_scaled)[0]
                    
                    # Map numeric prediction to regime
                    regime_map = {
                        0: MarketRegime.BEAR_TREND.value,
                        1: MarketRegime.SIDEWAYS.value,
                        2: MarketRegime.BULL_TREND.value,
                        3: MarketRegime.HIGH_VOLATILITY.value,
                        4: MarketRegime.REGIME_TRANSITION.value
                    }
                    
                    # Get predicted regime
                    predicted_regime = regime_map.get(int(regime_pred), MarketRegime.SIDEWAYS.value)
                    
                    # Calculate probability of change
                    current_idx = list(regime_map.values()).index(self.current_market_regime.value) if self.current_market_regime.value in regime_map.values() else 1
                    change_probability = regime_proba[int(regime_pred)] if int(regime_pred) != current_idx else 0
                    
                    prediction.update({
                        "next_regime": predicted_regime,
                        "probability": float(change_probability)
                    })
                except:
                    pass
            
            return prediction
            
        except Exception as e:
            logger.error(f"❌ Error predicting regime change: {e}")
            return {"current_regime": self.current_market_regime.value, "next_regime": self.current_market_regime.value, "probability": 0.0}
    
    async def _update_portfolio_metrics(self):
        """Update portfolio metrics and performance statistics"""
        try:
            # Calculate active positions P&L
            active_pnl = sum(p.unrealized_pnl for p in self.active_positions.values() if p.is_active)
            
            # Calculate daily return
            total_pnl = self.daily_pnl + active_pnl
            daily_return = total_pnl / settings.ACCOUNT_SIZE
            self.daily_returns.append(daily_return)
            
            # Calculate Sharpe ratio (if we have enough data)
            if len(self.daily_returns) > 5:
                avg_return = np.mean(self.daily_returns)
                std_return = np.std(self.daily_returns) if np.std(self.daily_returns) > 0 else 0.001
                self.sharpe_ratio = avg_return / std_return * np.sqrt(252)
            
            # Calculate drawdown
            if self.daily_pnl > 0:
                max_balance = settings.ACCOUNT_SIZE + self.daily_pnl
                current_balance = max_balance + active_pnl
                current_drawdown = (max_balance - current_balance) / max_balance if max_balance > 0 else 0
                self.max_drawdown = max(self.max_drawdown, current_drawdown)
            
            # Calculate position-level metrics
            active_count = len([p for p in self.active_positions.values() if p.is_active])
            
            # Update Redis cache
            metrics = {
                "timestamp": datetime.now().isoformat(),
                "daily_pnl": self.daily_pnl,
                "unrealized_pnl": active_pnl,
                "total_pnl": total_pnl,
                "win_rate": self.winning_trades / max(1, self.total_trades) * 100,
                "active_positions": active_count,
                "sharpe_ratio": self.sharpe_ratio,
                "max_drawdown": self.max_drawdown * 100,
                "portfolio_beta": self.portfolio_beta
            }
            
            await redis_client.set("trading_engine:metrics", json.dumps(metrics), ttl=60)
            
            # Broadcast through websocket (if significant changes)
            if active_count > 0 or abs(active_pnl) > 100:
                await websocket_manager.send_metrics_update(metrics)
            
        except Exception as e:
            logger.error(f"❌ Error updating portfolio metrics: {e}")
    
    async def shutdown(self):
        """Graceful shutdown of the trading engine"""
        try:
            logger.info("🛑 Shutting down Institutional-Grade AI Trading Engine...")
            
            self.is_running = False
            
            # Close all active positions if configured to do so
            if settings.CLOSE_POSITIONS_ON_SHUTDOWN:
                await self._emergency_close_all_positions("SYSTEM_SHUTDOWN")
            
            # Save models
            if TF_AVAILABLE:
                for name, model in self.models.items():
                    if hasattr(model, 'save'):
                        try:
                            model.save(f"models/{name}_{datetime.now().strftime('%Y%m%d')}.h5")
                        except:
                            pass
            
            # Save trading statistics
            stats = {
                "total_trades": self.total_trades,
                "winning_trades": self.winning_trades,
                "losing_trades": self.losing_trades,
                "total_profit": self.total_profit,
                "total_loss": self.total_loss,
                "sharpe_ratio": self.sharpe_ratio,
                "max_drawdown": self.max_drawdown,
                "shutdown_time": datetime.now().isoformat()
            }
            
            with open(f"stats/trading_stats_{datetime.now().strftime('%Y%m%d')}.json", 'w') as f:
                json.dump(stats, f, indent=2)
            
            logger.info("✅ AI Trading Engine shutdown completed successfully")
            
        except Exception as e:
            logger.error(f"❌ Error during shutdown: {e}")
    
    def get_status(self) -> Dict[str, Any]:
        """Get current status of the trading engine"""
        return {
            "is_running": self.is_running,
            "market_regime": self.current_market_regime.value,
            "active_positions": len([p for p in self.active_positions.values() if p.is_active]),
            "daily_pnl": self.daily_pnl,
            "win_rate": self.winning_trades / max(1, self.total_trades) * 100,
            "system_health": self.system_health,
            "initialization_time": self.initialization_timestamp.isoformat() if self.initialization_timestamp else None,
            "uptime_hours": (datetime.now() - self.initialization_timestamp).total_seconds() / 3600 if self.initialization_timestamp else 0
        }


# Create a singleton instance
trading_engine = AITradingEngine()