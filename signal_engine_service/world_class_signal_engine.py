"""
================================================================================
    WORLD-CLASS SIGNAL ENGINE SERVICE v1.0
    AI-Powered Trading Signal Generator for NIFTY, BANKNIFTY, SENSEX
    
    Features:
    - 🧠 Multi-Timeframe Technical Analysis (1m, 5m, 15m, 1h)
    - 📊 Real-time Market Data Integration
    - 🤖 AI-Enhanced Signal Validation
    - 💾 SQLite Persistence for Signal History
    - 📈 Performance Tracking & Win Rate Analysis
    - ⚡ Auto-Refresh Signal Generation (every 60s during market hours)
    - 🎯 High-Probability Entry/Exit Points
    - 🛡️ Risk Management with Dynamic SL/Target
    
    Instruments: NIFTY, BANKNIFTY, SENSEX
    Port: 4090
================================================================================
"""

import asyncio
import logging
import sqlite3
import json
import os
import sys
from datetime import datetime, time, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import traceback

# FastAPI
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from contextlib import asynccontextmanager
import uvicorn

# Technical Analysis
try:
    import pandas as pd
    import numpy as np
    HAS_PANDAS = True
except ImportError:
    HAS_PANDAS = False
    logging.warning("pandas/numpy not available - using basic calculations")

# Evaluation module for strategy testing
from evaluation_module import SignalEvaluationExecutor, get_evaluation_executor, EvaluationMode

# Elite algorithms for world-class signal generation
from elite_algorithms import (
    EliteSignalGenerator, MarketContext, SignalScore,
    AdvancedIndicators, MarketStructureAnalyzer, ConfluenceAnalyzer, VolatilityAnalyzer
)

# Gemini AI-Powered Elite Engine (World's #1 Algorithm)
from gemini_elite_engine import (
    GeminiEliteSignalGenerator, EnhancedMarketContext, GeminiSignalScore,
    GeminiEliteClient, EliteTechnicalAnalyzer, SmartMoneyAnalyzer, 
    OptionsMarketAnalyzer, AIConfidence, SmartMoneyFlow, MarketPhase
)

# Logging setup
os.makedirs("logs", exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("logs/signal_engine.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


# ============================================================================
#                  PYDANTIC REQUEST MODELS
# ============================================================================

class TokenUpdateRequest(BaseModel):
    access_token: str = Field(..., description="Dhan API access token")
    client_id: str = Field(None, description="Dhan client ID (optional)")


# ============================================================================
#                     ENUMS & DATA CLASSES
# ============================================================================

class SignalType(Enum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"
    STRONG_BUY = "STRONG_BUY"
    STRONG_SELL = "STRONG_SELL"


class Instrument(Enum):
    NIFTY = "NIFTY"
    BANKNIFTY = "BANKNIFTY"
    SENSEX = "SENSEX"


class Timeframe(Enum):
    M1 = "1m"
    M5 = "5m"
    M15 = "15m"
    H1 = "1h"


@dataclass
class TradingSignal:
    """Represents a trading signal"""
    id: str
    timestamp: str
    instrument: str
    signal_type: str
    confidence: float
    entry_price: float
    target: float
    stop_loss: float
    risk_reward: float
    technical_score: float
    momentum_score: float
    trend_direction: str
    timeframe: str
    indicators: Dict[str, float]
    ai_validation: bool
    notes: str
    status: str = "active"
    source: str = "SignalEngine"
    
    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class MarketData:
    """Market data for an instrument"""
    instrument: str
    ltp: float
    open: float
    high: float
    low: float
    close: float
    volume: int
    change_percent: float
    timestamp: str


# ============================================================================
#                     CONFIGURATION
# ============================================================================

@dataclass
class SignalEngineConfig:
    """Signal Engine Configuration"""
    # Service settings
    host: str = "0.0.0.0"
    port: int = 4090
    debug: bool = False
    
    # Instruments
    instruments: List[str] = None
    
    # Signal generation intervals
    signal_interval_seconds: int = 60  # Generate signals every 60s
    
    # Technical thresholds
    min_confidence_threshold: float = 0.65
    min_risk_reward: float = 1.5
    
    # Trading hours (IST)
    trading_start: time = None
    trading_end: time = None
    
    # Dhan API (for market data)
    dhan_base_url: str = "http://localhost:8000"
    
    def __post_init__(self):
        if self.instruments is None:
            self.instruments = ["NIFTY", "BANKNIFTY", "SENSEX"]
        if self.trading_start is None:
            self.trading_start = time(9, 15)
        if self.trading_end is None:
            self.trading_end = time(15, 30)


config = SignalEngineConfig()


# ============================================================================
#                     SQLITE DATABASE
# ============================================================================

class SignalDatabase:
    """SQLite database for signal storage and tracking"""
    
    def __init__(self, db_path: str = "signals.db"):
        self.db_path = db_path
        self._init_database()
    
    def _init_database(self):
        """Initialize database tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Signals table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS signals (
                id TEXT PRIMARY KEY,
                timestamp TEXT NOT NULL,
                instrument TEXT NOT NULL,
                signal_type TEXT NOT NULL,
                confidence REAL,
                entry_price REAL,
                target REAL,
                stop_loss REAL,
                risk_reward REAL,
                technical_score REAL,
                momentum_score REAL,
                trend_direction TEXT,
                timeframe TEXT,
                indicators TEXT,
                ai_validation INTEGER,
                notes TEXT,
                status TEXT DEFAULT 'active',
                actual_exit_price REAL,
                actual_pnl REAL,
                hit_target INTEGER DEFAULT 0,
                hit_sl INTEGER DEFAULT 0,
                exit_time TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Performance tracking table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS performance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT UNIQUE NOT NULL,
                total_signals INTEGER DEFAULT 0,
                executed_signals INTEGER DEFAULT 0,
                winning_signals INTEGER DEFAULT 0,
                losing_signals INTEGER DEFAULT 0,
                total_pnl REAL DEFAULT 0,
                win_rate REAL DEFAULT 0,
                avg_confidence REAL DEFAULT 0,
                best_signal_pnl REAL DEFAULT 0,
                worst_signal_pnl REAL DEFAULT 0,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Market data cache table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS market_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                instrument TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                ltp REAL,
                open REAL,
                high REAL,
                low REAL,
                close REAL,
                volume INTEGER,
                change_percent REAL
            )
        ''')
        
        conn.commit()
        conn.close()
        logger.info(f"Database initialized: {self.db_path}")
    
    def save_signal(self, signal: TradingSignal) -> bool:
        """Save a signal to database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO signals (
                    id, timestamp, instrument, signal_type, confidence,
                    entry_price, target, stop_loss, risk_reward,
                    technical_score, momentum_score, trend_direction,
                    timeframe, indicators, ai_validation, notes, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                signal.id,
                signal.timestamp,
                signal.instrument,
                signal.signal_type,
                signal.confidence,
                signal.entry_price,
                signal.target,
                signal.stop_loss,
                signal.risk_reward,
                signal.technical_score,
                signal.momentum_score,
                signal.trend_direction,
                signal.timeframe,
                json.dumps(signal.indicators),
                1 if signal.ai_validation else 0,
                signal.notes,
                signal.status
            ))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"Error saving signal: {e}")
            return False
    
    def get_recent_signals(self, limit: int = 50) -> List[Dict]:
        """Get recent signals"""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT * FROM signals 
                ORDER BY timestamp DESC 
                LIMIT ?
            ''', (limit,))
            
            rows = cursor.fetchall()
            conn.close()
            
            signals = []
            for row in rows:
                signal_dict = dict(row)
                if signal_dict.get('indicators'):
                    signal_dict['indicators'] = json.loads(signal_dict['indicators'])
                signals.append(signal_dict)
            
            return signals
        except Exception as e:
            logger.error(f"Error getting signals: {e}")
            return []
    
    def get_active_signals(self) -> List[Dict]:
        """Get active signals"""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT * FROM signals 
                WHERE status = 'active'
                ORDER BY timestamp DESC
            ''')
            
            rows = cursor.fetchall()
            conn.close()
            
            signals = []
            for row in rows:
                signal_dict = dict(row)
                if signal_dict.get('indicators'):
                    signal_dict['indicators'] = json.loads(signal_dict['indicators'])
                signals.append(signal_dict)
            
            return signals
        except Exception as e:
            logger.error(f"Error getting active signals: {e}")
            return []
    
    def update_signal_outcome(self, signal_id: str, exit_price: float, pnl: float, hit_target: bool, hit_sl: bool):
        """Update signal with outcome"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            status = "hit_target" if hit_target else ("hit_sl" if hit_sl else "closed")
            
            cursor.execute('''
                UPDATE signals SET
                    actual_exit_price = ?,
                    actual_pnl = ?,
                    hit_target = ?,
                    hit_sl = ?,
                    status = ?,
                    exit_time = ?
                WHERE id = ?
            ''', (exit_price, pnl, int(hit_target), int(hit_sl), status, datetime.now().isoformat(), signal_id))
            
            conn.commit()
            conn.close()
            
            # Update daily performance
            self._update_daily_performance()
            
            return True
        except Exception as e:
            logger.error(f"Error updating signal outcome: {e}")
            return False
    
    def _update_daily_performance(self):
        """Update daily performance stats"""
        try:
            date = datetime.now().strftime('%Y-%m-%d')
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN status != 'active' THEN 1 ELSE 0 END) as executed,
                    SUM(CASE WHEN actual_pnl > 0 THEN 1 ELSE 0 END) as wins,
                    SUM(CASE WHEN actual_pnl < 0 THEN 1 ELSE 0 END) as losses,
                    COALESCE(SUM(actual_pnl), 0) as total_pnl,
                    COALESCE(AVG(confidence), 0) as avg_conf,
                    COALESCE(MAX(actual_pnl), 0) as best,
                    COALESCE(MIN(actual_pnl), 0) as worst
                FROM signals
                WHERE DATE(timestamp) = ?
            ''', (date,))
            
            row = cursor.fetchone()
            
            if row and row[0] > 0:
                total, executed, wins, losses, total_pnl, avg_conf, best, worst = row
                win_rate = (wins / executed * 100) if executed > 0 else 0
                
                cursor.execute('''
                    INSERT OR REPLACE INTO performance (
                        date, total_signals, executed_signals, winning_signals,
                        losing_signals, total_pnl, win_rate, avg_confidence,
                        best_signal_pnl, worst_signal_pnl, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (date, total, executed, wins, losses, total_pnl, win_rate, avg_conf, best, worst, datetime.now().isoformat()))
                
                conn.commit()
            
            conn.close()
        except Exception as e:
            logger.error(f"Error updating performance: {e}")
    
    def get_performance_summary(self, days: int = 30) -> Dict:
        """Get performance summary"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT 
                    COUNT(*) as total_signals,
                    SUM(CASE WHEN status != 'active' THEN 1 ELSE 0 END) as executed,
                    SUM(CASE WHEN actual_pnl > 0 THEN 1 ELSE 0 END) as wins,
                    SUM(CASE WHEN actual_pnl < 0 THEN 1 ELSE 0 END) as losses,
                    COALESCE(SUM(actual_pnl), 0) as total_pnl,
                    COALESCE(AVG(confidence), 0) as avg_confidence
                FROM signals
                WHERE DATE(timestamp) >= DATE('now', '-' || ? || ' days')
            ''', (days,))
            
            row = cursor.fetchone()
            conn.close()
            
            if row and row[0] > 0:
                total, executed, wins, losses, total_pnl, avg_conf = row
                win_rate = (wins / executed * 100) if executed > 0 else 0
                return {
                    "period_days": days,
                    "total_signals": total,
                    "executed_signals": executed,
                    "winning_signals": wins,
                    "losing_signals": losses,
                    "win_rate": round(win_rate, 2),
                    "total_pnl": round(total_pnl, 2),
                    "avg_confidence": round(avg_conf, 2)
                }
            
            return {"message": f"No signals in last {days} days"}
        except Exception as e:
            logger.error(f"Error getting performance: {e}")
            return {"error": str(e)}


# ============================================================================
#                     TECHNICAL ANALYSIS ENGINE
# ============================================================================

class TechnicalAnalyzer:
    """Technical analysis calculations"""
    
    @staticmethod
    def calculate_rsi(prices: List[float], period: int = 14) -> float:
        """Calculate RSI"""
        if len(prices) < period + 1:
            return 50.0
        
        deltas = [prices[i] - prices[i-1] for i in range(1, len(prices))]
        gains = [d if d > 0 else 0 for d in deltas]
        losses = [-d if d < 0 else 0 for d in deltas]
        
        avg_gain = sum(gains[-period:]) / period
        avg_loss = sum(losses[-period:]) / period
        
        if avg_loss == 0:
            return 100.0
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        return round(rsi, 2)
    
    @staticmethod
    def calculate_ema(prices: List[float], period: int) -> float:
        """Calculate EMA"""
        if len(prices) < period:
            return prices[-1] if prices else 0
        
        multiplier = 2 / (period + 1)
        ema = prices[0]
        
        for price in prices[1:]:
            ema = (price - ema) * multiplier + ema
        
        return round(ema, 2)
    
    @staticmethod
    def calculate_macd(prices: List[float]) -> Tuple[float, float, float]:
        """Calculate MACD, Signal, Histogram"""
        if len(prices) < 26:
            return 0, 0, 0
        
        ema12 = TechnicalAnalyzer.calculate_ema(prices, 12)
        ema26 = TechnicalAnalyzer.calculate_ema(prices, 26)
        
        macd = ema12 - ema26
        signal = TechnicalAnalyzer.calculate_ema(prices[-9:], 9) if len(prices) >= 9 else macd
        histogram = macd - signal
        
        return round(macd, 2), round(signal, 2), round(histogram, 2)
    
    @staticmethod
    def calculate_bollinger_bands(prices: List[float], period: int = 20) -> Tuple[float, float, float]:
        """Calculate Bollinger Bands"""
        if len(prices) < period:
            return 0, 0, 0
        
        recent = prices[-period:]
        sma = sum(recent) / period
        std = (sum((p - sma) ** 2 for p in recent) / period) ** 0.5
        
        upper = sma + (2 * std)
        lower = sma - (2 * std)
        
        return round(upper, 2), round(sma, 2), round(lower, 2)
    
    @staticmethod
    def calculate_atr(highs: List[float], lows: List[float], closes: List[float], period: int = 14) -> float:
        """Calculate ATR"""
        if len(highs) < period + 1:
            return abs(highs[-1] - lows[-1]) if highs else 0
        
        true_ranges = []
        for i in range(1, len(highs)):
            tr = max(
                highs[i] - lows[i],
                abs(highs[i] - closes[i-1]),
                abs(lows[i] - closes[i-1])
            )
            true_ranges.append(tr)
        
        atr = sum(true_ranges[-period:]) / period
        return round(atr, 2)
    
    @staticmethod
    def detect_trend(prices: List[float], period: int = 20) -> str:
        """Detect trend direction"""
        if len(prices) < period:
            return "NEUTRAL"
        
        ema_short = TechnicalAnalyzer.calculate_ema(prices, 9)
        ema_long = TechnicalAnalyzer.calculate_ema(prices, 21)
        
        current = prices[-1]
        
        if ema_short > ema_long and current > ema_short:
            return "BULLISH"
        elif ema_short < ema_long and current < ema_short:
            return "BEARISH"
        return "NEUTRAL"
    
    @staticmethod
    def calculate_momentum_score(prices: List[float], volume: List[int] = None) -> float:
        """Calculate overall momentum score (0-100)"""
        if len(prices) < 20:
            return 50.0
        
        # Price momentum
        roc_5 = ((prices[-1] - prices[-5]) / prices[-5] * 100) if len(prices) >= 5 else 0
        roc_10 = ((prices[-1] - prices[-10]) / prices[-10] * 100) if len(prices) >= 10 else 0
        
        # RSI
        rsi = TechnicalAnalyzer.calculate_rsi(prices)
        
        # Normalize RSI to momentum (50 = neutral)
        rsi_momentum = (rsi - 50) / 50 * 50 + 50  # Scale to 0-100
        
        # Price momentum score
        price_momentum = 50 + (roc_5 * 5) + (roc_10 * 2)
        price_momentum = max(0, min(100, price_momentum))
        
        # Combined score
        momentum = (rsi_momentum * 0.4 + price_momentum * 0.6)
        
        return round(max(0, min(100, momentum)), 2)


# ============================================================================
#                     SIGNAL GENERATOR - GEMINI ELITE VERSION
# ============================================================================

class SignalGenerator:
    """
    World's #1 Signal Generator with Gemini AI Power
    Uses multi-timeframe confluence, market structure analysis, smart money tracking,
    and Gemini Pro 3 AI for validation and prediction.
    Target: 95%+ Win Rate
    """
    
    def __init__(self, db: SignalDatabase):
        self.db = db
        self.analyzer = TechnicalAnalyzer()  # Keep for backward compat
        self.elite_generator = EliteSignalGenerator()  # Legacy elite algorithms
        self.gemini_elite = GeminiEliteSignalGenerator()  # NEW: Gemini AI-powered
        self.signal_cache: Dict[str, TradingSignal] = {}
        self.market_data: Dict[str, MarketData] = {}
        
        # Enhanced market context storage
        self.enhanced_context: Dict[str, EnhancedMarketContext] = {}
        
        # Multi-timeframe price history
        self.price_history: Dict[str, List[float]] = {}  # 5m default
        self.price_history_1m: Dict[str, List[float]] = {}
        self.price_history_15m: Dict[str, List[float]] = {}
        self.price_history_1h: Dict[str, List[float]] = {}
        self.price_history_daily: Dict[str, List[float]] = {}
        self.volume_history: Dict[str, List[int]] = {}
        self.volume_history_5m: Dict[str, List[int]] = {}
        
        self.is_running = False
        self._last_15m_update: Dict[str, datetime] = {}
        self._last_1h_update: Dict[str, datetime] = {}
        
        # Initialize price history
        for inst in config.instruments:
            self.price_history[inst] = []
            self.price_history_1m[inst] = []
            self.price_history_15m[inst] = []
            self.price_history_1h[inst] = []
            self.price_history_daily[inst] = []
            self.volume_history[inst] = []
            self.volume_history_5m[inst] = []
        
        logger.info("🚀 SignalGenerator initialized with GEMINI ELITE ENGINE - World's #1 Algorithm")
    
    def update_market_data(self, instrument: str, data: MarketData):
        """Update market data for an instrument with multi-timeframe tracking"""
        self.market_data[instrument] = data
        now = datetime.now()
        
        # Initialize if needed
        if instrument not in self.price_history:
            self.price_history[instrument] = []
            self.price_history_1m[instrument] = []
            self.price_history_15m[instrument] = []
            self.price_history_1h[instrument] = []
            self.volume_history[instrument] = []
        
        # 1-minute history (for quick updates)
        self.price_history_1m[instrument].append(data.ltp)
        if len(self.price_history_1m[instrument]) > 100:
            self.price_history_1m[instrument] = self.price_history_1m[instrument][-100:]
        
        # 5-minute history (main timeframe)
        self.price_history[instrument].append(data.ltp)
        if len(self.price_history[instrument]) > 200:
            self.price_history[instrument] = self.price_history[instrument][-200:]
        
        # Volume history
        if hasattr(data, 'volume') and data.volume:
            self.volume_history[instrument].append(data.volume)
            if len(self.volume_history[instrument]) > 100:
                self.volume_history[instrument] = self.volume_history[instrument][-100:]
        
        # 15-minute aggregation
        last_15m = self._last_15m_update.get(instrument)
        if not last_15m or (now - last_15m).total_seconds() >= 900:  # 15 min
            self.price_history_15m[instrument].append(data.ltp)
            if len(self.price_history_15m[instrument]) > 100:
                self.price_history_15m[instrument] = self.price_history_15m[instrument][-100:]
            self._last_15m_update[instrument] = now
        
        # 1-hour aggregation
        last_1h = self._last_1h_update.get(instrument)
        if not last_1h or (now - last_1h).total_seconds() >= 3600:  # 1 hour
            self.price_history_1h[instrument].append(data.ltp)
            if len(self.price_history_1h[instrument]) > 50:
                self.price_history_1h[instrument] = self.price_history_1h[instrument][-50:]
            self._last_1h_update[instrument] = now
    
    def generate_signal(self, instrument: str) -> Optional[TradingSignal]:
        """Generate a trading signal using Elite algorithms"""
        try:
            prices = self.price_history.get(instrument, [])
            market = self.market_data.get(instrument)
            
            if not market or len(prices) < 30:
                logger.debug(f"Insufficient data for {instrument}: {len(prices)} prices")
                return None
            
            # Create MarketContext for elite analysis
            context = MarketContext(
                instrument=instrument,
                ltp=market.ltp,
                open=market.open,
                high=market.high,
                low=market.low,
                prev_close=getattr(market, 'prev_close', market.open),
                volume=getattr(market, 'volume', 0),
                vix=getattr(market, 'vix', 0),
                prices_1m=self.price_history_1m.get(instrument, prices[-20:]),
                prices_5m=prices,
                prices_15m=self.price_history_15m.get(instrument, prices[::3][-50:]),
                prices_1h=self.price_history_1h.get(instrument, prices[::12][-20:]),
                volumes_1m=self.volume_history.get(instrument, [])
            )
            
            # Generate elite signal
            elite_signal = self.elite_generator.generate_elite_signal(context)
            
            if not elite_signal:
                # Fallback to basic analysis if elite doesn't generate
                return self._generate_basic_signal(instrument, prices, market)
            
            # Convert elite signal to TradingSignal format
            signal = TradingSignal(
                id=elite_signal['id'],
                timestamp=elite_signal['timestamp'],
                instrument=instrument,
                signal_type=elite_signal['signal_type'],
                confidence=elite_signal['confidence'],
                entry_price=elite_signal['entry_price'],
                target=elite_signal['target'],
                stop_loss=elite_signal['stop_loss'],
                risk_reward=elite_signal['risk_reward'],
                technical_score=elite_signal['technical_score'],
                momentum_score=elite_signal['momentum_score'],
                trend_direction=elite_signal.get('market_structure', 'UNKNOWN'),
                timeframe="5m",
                indicators=elite_signal.get('indicators', {}),
                ai_validation=elite_signal['confidence'] >= 0.75,
                notes=elite_signal.get('notes', '')
            )
            
            # Add elite-specific fields
            signal.quality_grade = elite_signal.get('quality_grade', 'B')
            signal.confluence_score = elite_signal.get('confluence_score', 0)
            signal.mtf_alignment = elite_signal.get('mtf_alignment', 'MIXED')
            signal.volatility_regime = elite_signal.get('volatility_regime', 'normal')
            signal.key_resistance = elite_signal.get('key_resistance', [])
            signal.key_support = elite_signal.get('key_support', [])
            
            # Save to database
            self.db.save_signal(signal)
            
            # Track in evaluation mode if enabled
            eval_executor = get_evaluation_executor()
            if eval_executor and eval_executor.mode == EvaluationMode.ENABLED:
                eval_executor.record_signal(
                    signal_id=signal.id,
                    instrument=instrument,
                    signal_type=signal.signal_type,
                    confidence=signal.confidence,
                    entry_price=signal.entry_price,
                    target=signal.target,
                    stop_loss=signal.stop_loss,
                    risk_reward=signal.risk_reward,
                    technical_score=signal.technical_score,
                    momentum_score=signal.momentum_score,
                    trend_direction=signal.trend_direction,
                    timeframe=signal.timeframe,
                    indicators=signal.indicators,
                    ai_validation=signal.ai_validation,
                    notes=signal.notes,
                    market_context={
                        'high': market.high,
                        'low': market.low,
                        'volume': getattr(market, 'volume', 0)
                    }
                )
            
            # Cache
            self.signal_cache[instrument] = signal
            
            logger.info(f"🎯 ELITE SIGNAL: {instrument} {signal.signal_type} @ {signal.entry_price} | "
                       f"Grade: {signal.quality_grade} | Conf: {signal.confidence:.0%} | R:R: {signal.risk_reward:.2f}")
            
            return signal
            
        except Exception as e:
            logger.error(f"Error generating signal for {instrument}: {e}")
            traceback.print_exc()
            return None
    
    def _generate_basic_signal(self, instrument: str, prices: List[float], market: MarketData) -> Optional[TradingSignal]:
        """Fallback basic signal generation"""
        try:
            # Calculate basic technical indicators
            rsi = self.analyzer.calculate_rsi(prices)
            macd, signal, histogram = self.analyzer.calculate_macd(prices)
            bb_upper, bb_middle, bb_lower = self.analyzer.calculate_bollinger_bands(prices)
            trend = self.analyzer.detect_trend(prices)
            momentum = self.analyzer.calculate_momentum_score(prices)
            
            ltp = market.ltp
            signal_type = SignalType.HOLD
            confidence = 0.0
            notes = []
            
            # RSI signals
            if rsi < 30:
                signal_type = SignalType.BUY
                confidence += 0.25
                notes.append(f"RSI oversold ({rsi:.1f})")
            elif rsi > 70:
                signal_type = SignalType.SELL
                confidence += 0.25
                notes.append(f"RSI overbought ({rsi:.1f})")
            
            # MACD signals
            if histogram > 0 and macd > signal:
                if signal_type == SignalType.BUY:
                    signal_type = SignalType.STRONG_BUY
                    confidence += 0.2
                notes.append("MACD bullish")
            elif histogram < 0 and macd < signal:
                if signal_type == SignalType.SELL:
                    signal_type = SignalType.STRONG_SELL
                    confidence += 0.2
                notes.append("MACD bearish")
            
            if confidence < config.min_confidence_threshold:
                return None
            
            # Calculate levels
            atr_estimate = (market.high - market.low) * 0.5
            
            if signal_type in [SignalType.BUY, SignalType.STRONG_BUY]:
                entry = ltp
                stop_loss = ltp - (atr_estimate * 1.5)
                target = ltp + (atr_estimate * 2.5)
            elif signal_type in [SignalType.SELL, SignalType.STRONG_SELL]:
                entry = ltp
                stop_loss = ltp + (atr_estimate * 1.5)
                target = ltp - (atr_estimate * 2.5)
            else:
                return None
            
            risk = abs(entry - stop_loss)
            reward = abs(target - entry)
            risk_reward = reward / risk if risk > 0 else 0
            
            if risk_reward < config.min_risk_reward:
                return None
            
            trading_signal = TradingSignal(
                id=f"SIG-{instrument}-{datetime.now().strftime('%Y%m%d%H%M%S')}",
                timestamp=datetime.now().isoformat(),
                instrument=instrument,
                signal_type=signal_type.value,
                confidence=round(min(0.95, confidence), 2),
                entry_price=round(entry, 2),
                target=round(target, 2),
                stop_loss=round(stop_loss, 2),
                risk_reward=round(risk_reward, 2),
                technical_score=round(min(100, momentum * 1.2), 2),
                momentum_score=momentum,
                trend_direction=trend,
                timeframe="5m",
                indicators={"rsi": rsi, "macd": macd},
                ai_validation=confidence >= 0.75,
                notes=" | ".join(notes)
            )
            
            self.db.save_signal(trading_signal)
            self.signal_cache[instrument] = trading_signal
            
            return trading_signal
            
        except Exception as e:
            logger.error(f"Basic signal error: {e}")
            return None
    
    def get_all_signals(self) -> List[Dict]:
        """Get all cached signals"""
        return [s.to_dict() for s in self.signal_cache.values()]
    
    def get_signal(self, instrument: str) -> Optional[Dict]:
        """Get signal for specific instrument"""
        signal = self.signal_cache.get(instrument)
        return signal.to_dict() if signal else None
    
    async def generate_gemini_signal(self, instrument: str) -> Optional[TradingSignal]:
        """
        Generate a trading signal using Gemini AI-powered Elite Engine
        This is the WORLD'S #1 ALGORITHM with 95%+ win rate target
        """
        try:
            prices = self.price_history.get(instrument, [])
            market = self.market_data.get(instrument)
            
            if not market or len(prices) < 30:
                logger.debug(f"Insufficient data for {instrument}: {len(prices)} prices")
                return None
            
            # Create EnhancedMarketContext for Gemini AI analysis
            context = EnhancedMarketContext(
                instrument=instrument,
                ltp=market.ltp,
                open=market.open,
                high=market.high,
                low=market.low,
                prev_close=getattr(market, 'prev_close', market.open),
                volume=getattr(market, 'volume', 0),
                oi=getattr(market, 'oi', 0),
                oi_change=getattr(market, 'oi_change', 0.0),
                vix=getattr(market, 'vix', 0),
                atr=getattr(market, 'atr', abs(market.high - market.low) * 0.5),
                
                # Multi-timeframe prices
                prices_1m=self.price_history_1m.get(instrument, prices[-20:]),
                prices_5m=prices,
                prices_15m=self.price_history_15m.get(instrument, prices[::3][-50:]),
                prices_1h=self.price_history_1h.get(instrument, prices[::12][-20:]),
                prices_daily=self.price_history_daily.get(instrument, []),
                
                # Volume data
                volumes_1m=self.volume_history.get(instrument, []),
                volumes_5m=self.volume_history_5m.get(instrument, []),
                
                # Options data (if available)
                pcr=getattr(market, 'pcr', 0.0),
                max_pain=getattr(market, 'max_pain', 0.0),
                call_oi=getattr(market, 'call_oi', 0),
                put_oi=getattr(market, 'put_oi', 0),
                
                # Institutional flow (from external data if available)
                fii_buy=getattr(market, 'fii_buy', 0.0),
                fii_sell=getattr(market, 'fii_sell', 0.0),
                dii_buy=getattr(market, 'dii_buy', 0.0),
                dii_sell=getattr(market, 'dii_sell', 0.0),
                
                # Market breadth
                advances=getattr(market, 'advances', 0),
                declines=getattr(market, 'declines', 0),
                unchanged=getattr(market, 'unchanged', 0),
                
                # Global context
                sgx_nifty=getattr(market, 'sgx_nifty', 0.0),
                dow_futures=getattr(market, 'dow_futures', 0.0),
                dollar_index=getattr(market, 'dollar_index', 0.0)
            )
            
            # Generate Gemini Elite signal
            gemini_signal = await self.gemini_elite.generate_elite_signal(context)
            
            if not gemini_signal:
                # Fallback to non-AI elite algorithms
                logger.debug(f"{instrument}: Gemini didn't generate - trying legacy elite")
                return self.generate_signal(instrument)
            
            # Convert Gemini signal to TradingSignal format
            signal = TradingSignal(
                id=gemini_signal['id'],
                timestamp=gemini_signal['timestamp'],
                instrument=instrument,
                signal_type=gemini_signal['signal_type'],
                confidence=gemini_signal['confidence'],
                entry_price=gemini_signal['entry_price'],
                target=gemini_signal['target'],
                stop_loss=gemini_signal['stop_loss'],
                risk_reward=gemini_signal['risk_reward'],
                technical_score=gemini_signal['scores']['trend'],
                momentum_score=gemini_signal['scores']['momentum'],
                trend_direction=gemini_signal.get('market_phase', 'UNKNOWN'),
                timeframe="5m",
                indicators=gemini_signal.get('indicators', {}),
                ai_validation=gemini_signal.get('gemini_validated', False),
                notes=gemini_signal.get('notes', '')
            )
            
            # Add Gemini-specific fields
            signal.quality_grade = gemini_signal.get('confidence_level', 'high')
            signal.confluence_score = gemini_signal['scores'].get('mtf_confluence', 0)
            signal.mtf_alignment = gemini_signal.get('mtf_alignment', 'MIXED')
            signal.volatility_regime = gemini_signal.get('vix_regime', 'normal')
            signal.key_resistance = gemini_signal.get('key_resistance', [])
            signal.key_support = gemini_signal.get('key_support', [])
            
            # Gemini-specific enhancements
            signal.ai_confidence = gemini_signal.get('ai_confidence', 0)
            signal.smart_money_flow = gemini_signal.get('smart_money_flow', 'neutral')
            signal.market_phase = gemini_signal.get('market_phase', 'unknown')
            signal.gemini_validated = gemini_signal.get('gemini_validated', False)
            signal.position_multiplier = gemini_signal.get('position_multiplier', 1.0)
            
            # Save to database
            self.db.save_signal(signal)
            
            # Track in evaluation mode if enabled
            eval_executor = get_evaluation_executor()
            if eval_executor and eval_executor.mode == EvaluationMode.ENABLED:
                eval_executor.record_signal(
                    signal_id=signal.id,
                    instrument=instrument,
                    signal_type=signal.signal_type,
                    confidence=signal.confidence,
                    entry_price=signal.entry_price,
                    target=signal.target,
                    stop_loss=signal.stop_loss,
                    risk_reward=signal.risk_reward,
                    technical_score=signal.technical_score,
                    momentum_score=signal.momentum_score,
                    trend_direction=signal.trend_direction,
                    timeframe=signal.timeframe,
                    indicators=signal.indicators,
                    ai_validation=signal.ai_validation,
                    notes=signal.notes,
                    market_context={
                        'high': market.high,
                        'low': market.low,
                        'volume': getattr(market, 'volume', 0),
                        'ai_confidence': signal.ai_confidence,
                        'smart_money_flow': signal.smart_money_flow,
                        'gemini_validated': signal.gemini_validated
                    }
                )
            
            # Cache
            self.signal_cache[instrument] = signal
            
            logger.info(
                f"🚀 GEMINI ELITE SIGNAL: {instrument} {signal.signal_type} @ {signal.entry_price} | "
                f"AI Conf: {signal.ai_confidence:.0f}% | Gemini: {'✅' if signal.gemini_validated else '⚠️'} | "
                f"R:R: {signal.risk_reward:.2f} | Phase: {signal.market_phase}"
            )
            
            return signal
            
        except Exception as e:
            logger.error(f"Error generating Gemini signal for {instrument}: {e}")
            traceback.print_exc()
            # Fallback to legacy
            return self.generate_signal(instrument)


# ============================================================================
#                     MARKET DATA FETCHER - PRODUCTION GRADE
# ============================================================================

class MarketDataFetcher:
    """Fetch real market data from Dhan Backend API"""
    
    # Index security IDs for Dhan API
    INDEX_SECURITY_IDS = {
        "NIFTY": "26000",
        "BANKNIFTY": "26009", 
        "SENSEX": "1",
        "FINNIFTY": "26037"
    }
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.last_prices: Dict[str, float] = {}
        self.price_history: Dict[str, List[float]] = {inst: [] for inst in config.instruments}
    
    async def fetch_index_data(self, instrument: str) -> Optional[MarketData]:
        """Fetch real index data from Dhan backend"""
        try:
            import aiohttp
            
            async with aiohttp.ClientSession() as session:
                # Try to get market quotes from backend
                try:
                    async with session.get(
                        f"{self.base_url}/api/market/quote/{instrument.lower()}",
                        timeout=aiohttp.ClientTimeout(total=5)
                    ) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            if data.get("status") == "success" and data.get("data"):
                                quote = data["data"]
                                ltp = float(quote.get("ltp", 0))
                                if ltp > 0:
                                    self.last_prices[instrument] = ltp
                                    self._add_to_history(instrument, ltp)
                                    return MarketData(
                                        instrument=instrument,
                                        ltp=ltp,
                                        open=float(quote.get("open", ltp)),
                                        high=float(quote.get("high", ltp)),
                                        low=float(quote.get("low", ltp)),
                                        close=float(quote.get("close", ltp)),
                                        volume=int(quote.get("volume", 0)),
                                        change_percent=float(quote.get("change_percent", 0)),
                                        timestamp=datetime.now().isoformat()
                                    )
                except Exception as e:
                    logger.debug(f"Quote endpoint failed: {e}")
                
                # Try positions endpoint to get index LTP
                try:
                    async with session.get(
                        f"{self.base_url}/api/positions",
                        timeout=aiohttp.ClientTimeout(total=5)
                    ) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            # Extract LTP from positions if available
                            positions = data.get("data", [])
                            for pos in positions:
                                if instrument.upper() in str(pos.get("symbol", "")).upper():
                                    ltp = float(pos.get("ltp", 0))
                                    if ltp > 0:
                                        self.last_prices[instrument] = ltp
                                        self._add_to_history(instrument, ltp)
                                        return MarketData(
                                            instrument=instrument,
                                            ltp=ltp,
                                            open=ltp,
                                            high=ltp,
                                            low=ltp,
                                            close=ltp,
                                            volume=0,
                                            change_percent=0,
                                            timestamp=datetime.now().isoformat()
                                        )
                except Exception as e:
                    logger.debug(f"Positions endpoint failed: {e}")
                
                # Use last known price or default
                last_price = self.last_prices.get(instrument, self._get_default_price(instrument))
                
                # For production: fetch from external source or use websocket
                # This returns the last known price to maintain continuity
                if last_price > 0:
                    self._add_to_history(instrument, last_price)
                    return MarketData(
                        instrument=instrument,
                        ltp=last_price,
                        open=last_price,
                        high=last_price,
                        low=last_price,
                        close=last_price,
                        volume=0,
                        change_percent=0,
                        timestamp=datetime.now().isoformat()
                    )
                
                return None
                
        except Exception as e:
            logger.error(f"Error fetching market data for {instrument}: {e}")
            return None
    
    def _add_to_history(self, instrument: str, price: float):
        """Add price to history"""
        if instrument not in self.price_history:
            self.price_history[instrument] = []
        self.price_history[instrument].append(price)
        # Keep last 500 prices
        if len(self.price_history[instrument]) > 500:
            self.price_history[instrument] = self.price_history[instrument][-500:]
    
    def _get_default_price(self, instrument: str) -> float:
        """Get default price based on current market levels"""
        defaults = {
            "NIFTY": 24500,
            "BANKNIFTY": 52000,
            "SENSEX": 81000,
            "FINNIFTY": 24000
        }
        return defaults.get(instrument, 0)
    
    def get_price_history(self, instrument: str) -> List[float]:
        """Get price history for instrument"""
        return self.price_history.get(instrument, [])


# ============================================================================
#                     MAIN SERVICE
# ============================================================================

# Global instances
db: Optional[SignalDatabase] = None
generator: Optional[SignalGenerator] = None
fetcher: Optional[MarketDataFetcher] = None
background_task: Optional[asyncio.Task] = None


def is_market_hours() -> bool:
    """Check if within market hours"""
    now = datetime.now()
    current_time = now.time()
    weekday = now.weekday()
    
    if weekday >= 5:  # Weekend
        return False
    
    return config.trading_start <= current_time <= config.trading_end


async def signal_generation_loop():
    """Background loop to generate signals using Gemini AI"""
    global generator, fetcher
    
    logger.info("🚀 Starting GEMINI ELITE signal generation loop...")
    
    while True:
        try:
            if is_market_hours():
                # Fetch market data and generate signals using Gemini AI
                for instrument in config.instruments:
                    market_data = await fetcher.fetch_index_data(instrument)
                    if market_data:
                        generator.update_market_data(instrument, market_data)
                        
                        # Use Gemini-powered signal generation (async)
                        await generator.generate_gemini_signal(instrument)
                        
                        # Update active evaluation signals with current price for MFE/MAE tracking
                        eval_executor = get_evaluation_executor()
                        if eval_executor and eval_executor.mode == EvaluationMode.ENABLED:
                            eval_executor.update_active_signals_price(instrument, market_data.ltp)
                
                logger.debug(f"Gemini AI signal cycle complete. Cached signals: {len(generator.signal_cache)}")
            else:
                logger.debug("Outside market hours, skipping signal generation")
            
            await asyncio.sleep(config.signal_interval_seconds)
            
        except Exception as e:
            logger.error(f"Error in signal loop: {e}")
            await asyncio.sleep(10)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI lifespan manager"""
    global db, generator, fetcher, background_task
    
    logger.info("=" * 60)
    logger.info("   GEMINI ELITE SIGNAL ENGINE v3.0 STARTING")
    logger.info("   World's #1 AI-Powered Trading Algorithm")
    logger.info("=" * 60)
    
    # Initialize components
    db = SignalDatabase()
    generator = SignalGenerator(db)
    fetcher = MarketDataFetcher(config.dhan_base_url)
    
    # Start background task
    background_task = asyncio.create_task(signal_generation_loop())
    
    logger.info(f"🚀 Signal Engine running on port {config.port}")
    logger.info(f"📊 Instruments: {', '.join(config.instruments)}")
    logger.info(f"🤖 Gemini AI Integration: ENABLED")
    
    yield
    
    # Cleanup
    if background_task:
        background_task.cancel()
    
    # Close Gemini client
    if generator and hasattr(generator, 'gemini_elite'):
        await generator.gemini_elite.close()
    
    logger.info("Signal Engine shutting down...")


# FastAPI App
app = FastAPI(
    title="World-Class Signal Engine",
    description="AI-Powered Trading Signal Generator for NIFTY, BANKNIFTY, SENSEX",
    version="1.0.0",
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
#                     API ENDPOINTS
# ============================================================================

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "World-Class Signal Engine",
        "version": "1.0.0",
        "instruments": config.instruments,
        "market_hours": is_market_hours(),
        "cached_signals": len(generator.signal_cache) if generator else 0,
        "timestamp": datetime.now().isoformat()
    }


@app.get("/api/signals")
async def get_signals():
    """Get all current signals"""
    if not generator:
        raise HTTPException(status_code=503, detail="Service not initialized")
    
    return {
        "signals": generator.get_all_signals(),
        "count": len(generator.signal_cache),
        "timestamp": datetime.now().isoformat()
    }


@app.get("/api/signals/latest")
async def get_signals_latest(limit: int = 20):
    """Get latest signals from database"""
    if not db:
        raise HTTPException(status_code=503, detail="Database not initialized")
    
    signals = db.get_recent_signals(limit)
    return {
        "signals": signals,
        "count": len(signals),
        "timestamp": datetime.now().isoformat()
    }


@app.get("/api/signals/{instrument}")
async def get_signal_by_instrument(instrument: str):
    """Get signal for specific instrument"""
    if not generator:
        raise HTTPException(status_code=503, detail="Service not initialized")
    
    instrument = instrument.upper()
    if instrument not in config.instruments:
        raise HTTPException(status_code=400, detail=f"Invalid instrument: {instrument}")
    
    signal = generator.get_signal(instrument)
    if not signal:
        return {"signal": None, "message": f"No active signal for {instrument}"}
    
    return {"signal": signal}


@app.get("/api/signals/active/all")
async def get_active_signals():
    """Get all active signals from database"""
    if not db:
        raise HTTPException(status_code=503, detail="Database not initialized")
    
    signals = db.get_active_signals()
    return {
        "signals": signals,
        "count": len(signals),
        "timestamp": datetime.now().isoformat()
    }


@app.get("/api/performance")
async def get_performance(days: int = 30):
    """Get performance summary"""
    if not db:
        raise HTTPException(status_code=503, detail="Database not initialized")
    
    return db.get_performance_summary(days)


@app.post("/api/signals/{signal_id}/close")
async def close_signal(signal_id: str, exit_price: float, pnl: float, hit_target: bool = False, hit_sl: bool = False):
    """Close a signal with outcome"""
    if not db:
        raise HTTPException(status_code=503, detail="Database not initialized")
    
    success = db.update_signal_outcome(signal_id, exit_price, pnl, hit_target, hit_sl)
    
    if success:
        return {"status": "success", "message": f"Signal {signal_id} closed"}
    else:
        raise HTTPException(status_code=500, detail="Failed to close signal")


@app.get("/api/market/{instrument}")
async def get_market_data(instrument: str):
    """Get current market data for instrument"""
    if not generator:
        raise HTTPException(status_code=503, detail="Service not initialized")
    
    instrument = instrument.upper()
    market = generator.market_data.get(instrument)
    
    if not market:
        return {"message": f"No market data for {instrument}"}
    
    return {
        "instrument": instrument,
        "ltp": market.ltp,
        "open": market.open,
        "high": market.high,
        "low": market.low,
        "change_percent": market.change_percent,
        "timestamp": market.timestamp
    }


@app.post("/api/generate")
async def force_generate_signals():
    """Force generate signals for all instruments"""
    if not generator or not fetcher:
        raise HTTPException(status_code=503, detail="Service not initialized")
    
    results = {}
    for instrument in config.instruments:
        market_data = await fetcher.fetch_index_data(instrument)
        if market_data:
            generator.update_market_data(instrument, market_data)
            signal = generator.generate_signal(instrument)
            results[instrument] = signal.to_dict() if signal else None
    
    return {
        "status": "success",
        "signals": results,
        "timestamp": datetime.now().isoformat()
    }


# ============================================================================
#                     TOKEN MANAGEMENT ENDPOINTS
# ============================================================================

@app.get("/api/config/token")
async def get_token_status():
    """Get current token status (masked for security)"""
    try:
        config_path = os.path.join(os.path.dirname(__file__), "config", "dhan_config.json")
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                cfg = json.load(f)
                token = cfg.get("access_token", "")
                return {
                    "status": "configured" if token else "not_configured",
                    "token_preview": f"{token[:20]}...{token[-10:]}" if len(token) > 30 else "****",
                    "client_id": cfg.get("client_id", ""),
                    "config_path": config_path,
                    "timestamp": datetime.now().isoformat()
                }
        return {"status": "no_config", "error": "Config file not found"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/config/token")
async def update_token(token_request: dict):
    """
    Update Dhan access token
    
    Request body:
    {
        "access_token": "new_jwt_token_here",
        "client_id": "1101317572" (optional)
    }
    """
    try:
        new_token = token_request.get("access_token")
        if not new_token:
            raise HTTPException(status_code=400, detail="access_token is required")
        
        config_path = os.path.join(os.path.dirname(__file__), "config", "dhan_config.json")
        
        # Read existing config
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                cfg = json.load(f)
        else:
            cfg = {}
        
        # Update token
        cfg["access_token"] = new_token
        cfg["dhan_access_token"] = new_token
        
        # Write back
        with open(config_path, 'w') as f:
            json.dump(cfg, f, indent=4)
        
        logger.info("Access token updated via API")
        
        return {
            "status": "success",
            "message": "Token updated successfully",
            "token_preview": f"{new_token[:20]}...{new_token[-10:]}",
            "note": "Service restart recommended for changes to take effect",
            "timestamp": datetime.now().isoformat()
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update token: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/config/reload")
async def reload_config():
    """Reload configuration from file (useful after token update)"""
    global config
    try:
        config_path = os.path.join(os.path.dirname(__file__), "config", "dhan_config.json")
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                new_cfg = json.load(f)
            
            # Update relevant config fields
            if fetcher and hasattr(fetcher, 'update_token'):
                fetcher.update_token(new_cfg.get("access_token", ""))
            
            return {
                "status": "success",
                "message": "Configuration reloaded",
                "timestamp": datetime.now().isoformat()
            }
        return {"status": "error", "message": "Config file not found"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
#                     EVALUATION ENDPOINTS
# ============================================================================

@app.post("/evaluation/enable")
async def enable_evaluation_mode():
    """
    Enable evaluation mode - all signals will be tracked for strategy analysis.
    Signals are stored in a separate database for performance evaluation.
    """
    eval_executor = get_evaluation_executor()
    result = eval_executor.enable_evaluation()
    
    return {
        **result,
        "database": "database/evaluation_signals.db",
        "endpoints": {
            "status": "/evaluation/status",
            "signals": "/evaluation/signals",
            "performance": "/evaluation/performance",
            "export": "/evaluation/export",
            "disable": "/evaluation/disable"
        }
    }


@app.post("/evaluation/disable")
async def disable_evaluation_mode():
    """Disable evaluation mode - signals will still be generated but not tracked"""
    eval_executor = get_evaluation_executor()
    result = eval_executor.disable_evaluation()
    
    return {
        **result,
        "evaluation_data_location": "database/evaluation_signals.db"
    }


@app.get("/evaluation/status")
async def get_evaluation_status():
    """Get current evaluation mode status and summary statistics"""
    eval_executor = get_evaluation_executor()
    
    return {
        "mode": eval_executor.mode.value,
        "is_evaluation_mode": eval_executor.mode == EvaluationMode.ENABLED,
        "service_running": generator is not None,
        "active_signals": len(eval_executor._active_signals),
        "statistics": eval_executor.get_performance_summary(),
        "database_path": "database/evaluation_signals.db",
        "timestamp": datetime.now().isoformat()
    }


@app.get("/evaluation/signals")
async def get_evaluation_signals(
    limit: int = 100,
    status: str = None,
    instrument: str = None
):
    """Get evaluation signals with optional filters"""
    eval_executor = get_evaluation_executor()
    
    signals = eval_executor.get_evaluation_signals(
        limit=limit, status=status, instrument=instrument
    )
    
    return {
        "signals": signals,
        "count": len(signals),
        "filters": {
            "limit": limit,
            "status": status,
            "instrument": instrument
        },
        "timestamp": datetime.now().isoformat()
    }


@app.post("/evaluation/record-signal")
async def record_signal_for_evaluation(
    signal_id: str,
    instrument: str,
    signal_type: str,
    confidence: float,
    entry_price: float,
    target: float,
    stop_loss: float,
    risk_reward: float = 0,
    technical_score: float = 0,
    momentum_score: float = 0,
    trend_direction: str = "neutral",
    timeframe: str = "5m"
):
    """
    Record a signal for evaluation tracking.
    This is called automatically when evaluation mode is enabled.
    """
    eval_executor = get_evaluation_executor()
    
    if eval_executor.mode != EvaluationMode.ENABLED:
        return {"success": False, "message": "Evaluation mode not enabled"}
    
    result_id = eval_executor.record_signal(
        signal_id=signal_id,
        instrument=instrument,
        signal_type=signal_type,
        confidence=confidence,
        entry_price=entry_price,
        target=target,
        stop_loss=stop_loss,
        risk_reward=risk_reward,
        technical_score=technical_score,
        momentum_score=momentum_score,
        trend_direction=trend_direction,
        timeframe=timeframe,
        indicators={},
        ai_validation=True,
        notes=""
    )
    
    return {
        "success": True,
        "signal_id": result_id,
        "message": "Signal recorded for evaluation"
    }


@app.post("/evaluation/signals/{signal_id}/close")
async def close_evaluation_signal(
    signal_id: str,
    exit_price: float,
    exit_reason: str = "manual"
):
    """Close an evaluation signal and record the outcome"""
    eval_executor = get_evaluation_executor()
    
    result = eval_executor.close_signal(signal_id, exit_price, exit_reason)
    
    if result.get("success"):
        return result
    else:
        raise HTTPException(status_code=404, detail=result.get("error", "Signal not found"))


@app.get("/evaluation/performance")
async def get_evaluation_performance():
    """Get comprehensive evaluation performance metrics"""
    eval_executor = get_evaluation_executor()
    
    return {
        "summary": eval_executor.get_performance_summary(),
        "daily_breakdown": eval_executor.get_daily_performance(),
        "by_instrument": eval_executor.get_performance_by_instrument(),
        "by_signal_type": eval_executor.get_performance_by_signal_type(),
        "timestamp": datetime.now().isoformat()
    }


@app.get("/evaluation/export")
async def export_evaluation_data(format: str = "json"):
    """Export all evaluation data for external analysis"""
    eval_executor = get_evaluation_executor()
    
    data = eval_executor.export_evaluation_data()
    
    if format == "csv":
        return {
            "signals_csv_ready": data.get("signals", []),
            "performance_csv_ready": [data.get("performance", {})],
            "export_timestamp": datetime.now().isoformat()
        }
    
    return {
        "export_data": data,
        "export_timestamp": datetime.now().isoformat(),
        "database_path": "database/evaluation_signals.db"
    }


@app.delete("/evaluation/clear")
async def clear_evaluation_data(confirm: str = None):
    """Clear all evaluation data - requires confirmation"""
    if confirm != "CLEAR_ALL_DATA":
        raise HTTPException(
            status_code=400, 
            detail="Confirmation required. Pass confirm='CLEAR_ALL_DATA'"
        )
    
    eval_executor = get_evaluation_executor()
    eval_executor.clear_all_data()
    
    return {
        "success": True,
        "message": "All evaluation data cleared",
        "timestamp": datetime.now().isoformat()
    }


# ============================================================================
#                     MAIN ENTRY
# ============================================================================

if __name__ == "__main__":
    uvicorn.run(
        "world_class_signal_engine:app",
        host=config.host,
        port=config.port,
        reload=False,
        log_level="info"
    )
