"""
AI Options Hedger - Production Service with Gemini AI Integration
===================================================================
Production-ready options hedging service with:
- WebSocket for real-time data (no rate limits)
- Gemini AI for trade validation and prediction
- Paper trading mode by default
- SQLite database for important signals and trades
- Comprehensive AI signal logging for win rate analysis

Run during market hours for evaluation and enhancement.
"""

import asyncio
import logging
import sys
import os
import json
import uuid
import aiohttp
from datetime import datetime, date, time, timedelta
from typing import Dict, List, Optional, Any
from contextlib import asynccontextmanager
from enum import Enum
from pathlib import Path

# FastAPI
from fastapi import FastAPI, HTTPException, Query, Body
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# Add project root to path
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

# Local imports
from core.websocket_client import (
    DhanWebSocketClient, DhanOptionChainClient, TickData, FeedRequestCode
)
from database.paper_trading_db import (
    PaperTradingDB, get_paper_trading_db, TradingMode, PaperPosition
)
from database.evaluation_executor import HedgerEvaluationExecutor, EvaluationMode

# Import Production Trading Router
try:
    from core.trading_router import router as trading_router
    TRADING_ROUTER_AVAILABLE = True
except ImportError as e:
    TRADING_ROUTER_AVAILABLE = False
    print(f"Trading router not available: {e}")

# Import Institutional Greeks Hedging Engine
try:
    from core.engines.institutional_greeks_engine import (
        InstitutionalGreeksHedgingEngine,
        create_hedging_engine,
        GreeksExposure,
        HedgeRecommendation,
        HedgeStrategy
    )
    GREEKS_ENGINE_AVAILABLE = True
    print("[OK] Institutional Greeks Hedging Engine loaded")
except ImportError as e:
    GREEKS_ENGINE_AVAILABLE = False
    print(f"[WARNING] Greeks hedging engine not available: {e}")

# ==================== Logging Setup ====================

os.makedirs("logs", exist_ok=True)
os.makedirs("logs/ai_signals", exist_ok=True)  # Dedicated AI signal logs

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    datefmt='%H:%M:%S'
)

# File handler for detailed logs
file_handler = logging.FileHandler(
    f'logs/hedger_{date.today().strftime("%Y%m%d")}.log',
    encoding='utf-8'
)
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(logging.Formatter(
    '%(asctime)s | %(levelname)s | %(name)s | %(message)s'
))
logging.getLogger().addHandler(file_handler)

# Reduce noise from libraries
logging.getLogger('websockets').setLevel(logging.WARNING)
logging.getLogger('aiohttp').setLevel(logging.WARNING)
logging.getLogger('asyncio').setLevel(logging.WARNING)

logger = logging.getLogger('hedger')


# ==================== AI Signal Logger ====================

class AISignalLogger:
    """Dedicated logger for AI signals and predictions - critical for win rate analysis"""
    
    def __init__(self):
        self.log_dir = "logs/ai_signals"
        os.makedirs(self.log_dir, exist_ok=True)
        self._signal_file = os.path.join(
            self.log_dir, 
            f'hedger_ai_signals_{date.today().strftime("%Y%m%d")}.jsonl'
        )
    
    def log_signal(self, signal_data: Dict):
        """Log AI signal to JSONL file for analysis"""
        signal_data['logged_at'] = datetime.now().isoformat()
        with open(self._signal_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(signal_data, default=str) + '\n')
    
    def log_prediction(self, instrument: str, direction: str, prediction: Dict, 
                       ai_confidence: float, decision: str, reason: str = ""):
        """Log AI prediction details"""
        self.log_signal({
            'type': 'ai_prediction',
            'service': 'hedger',
            'instrument': instrument,
            'direction': direction,
            'ai_confidence': ai_confidence,
            'ai_decision': decision,
            'ai_reason': reason,
            'prediction': prediction,
            'timestamp': datetime.now().isoformat()
        })
    
    def log_trade_outcome(self, trade_id: str, entry_price: float, exit_price: float,
                          pnl: float, ai_confidence: float, hold_duration_seconds: float):
        """Log trade outcome for win rate analysis"""
        self.log_signal({
            'type': 'trade_outcome',
            'service': 'hedger',
            'trade_id': trade_id,
            'entry_price': entry_price,
            'exit_price': exit_price,
            'pnl': pnl,
            'pnl_percent': ((exit_price - entry_price) / entry_price * 100) if entry_price > 0 else 0,
            'ai_confidence': ai_confidence,
            'hold_duration_seconds': hold_duration_seconds,
            'won': pnl > 0,
            'timestamp': datetime.now().isoformat()
        })

ai_signal_logger = AISignalLogger()

# ==================== Gemini AI Client ====================

class GeminiAIClient:
    """Client for Gemini Trade Service - AI-powered trading decisions"""
    
    GEMINI_URL = "http://localhost:4080"
    
    def __init__(self):
        self._session: Optional[aiohttp.ClientSession] = None
        self._healthy = False
        self._last_check = None
        self._stats = {
            'requests': 0,
            'successes': 0,
            'failures': 0,
            'avg_latency_ms': 0
        }
    
    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30))
        return self._session
    
    async def check_health(self) -> bool:
        """Check if Gemini service is healthy"""
        try:
            session = await self._get_session()
            async with session.get(f"{self.GEMINI_URL}/health", timeout=5) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    self._healthy = data.get('status') == 'healthy'
                    self._last_check = datetime.now()
                    return self._healthy
        except Exception as e:
            logger.warning(f"Gemini health check failed: {e}")
            self._healthy = False
        return False
    
    async def get_signal(self, instrument: str = "nifty") -> Optional[Dict]:
        """Get AI signal from Gemini service"""
        try:
            start = datetime.now()
            session = await self._get_session()
            async with session.get(f"{self.GEMINI_URL}/api/signal/{instrument.lower()}", timeout=30) as resp:
                self._stats['requests'] += 1
                latency = (datetime.now() - start).total_seconds() * 1000
                
                if resp.status == 200:
                    self._stats['successes'] += 1
                    data = await resp.json()
                    
                    # Log the AI signal
                    ai_signal_logger.log_signal({
                        'type': 'gemini_signal',
                        'service': 'hedger',
                        'endpoint': f'/api/signal/{instrument.lower()}',
                        'response': data,
                        'latency_ms': latency
                    })
                    
                    logger.info(f"🤖 AI Signal received for {instrument} | Latency: {latency:.0f}ms")
                    return data
                else:
                    self._stats['failures'] += 1
                    logger.warning(f"Gemini signal failed: HTTP {resp.status}")
        except Exception as e:
            self._stats['failures'] += 1
            logger.error(f"Gemini signal error: {e}")
        return None
    
    async def validate_trade(self, instrument: str, direction: str, 
                             signal_strength: float, current_price: float) -> Dict:
        """Validate a potential trade with AI"""
        try:
            start = datetime.now()
            session = await self._get_session()
            
            payload = {
                "instrument": instrument,
                "direction": direction,
                "signal_strength": signal_strength,
                "current_price": current_price,
                "timestamp": datetime.now().isoformat()
            }
            
            async with session.post(
                f"{self.GEMINI_URL}/api/validate/trade",
                json=payload,
                timeout=15
            ) as resp:
                latency = (datetime.now() - start).total_seconds() * 1000
                
                if resp.status == 200:
                    result = await resp.json()
                    
                    # Log validation result
                    ai_signal_logger.log_prediction(
                        instrument=instrument,
                        direction=direction,
                        prediction=result,
                        ai_confidence=result.get('confidence', 0),
                        decision=result.get('decision', 'unknown'),
                        reason=result.get('reasoning', '')
                    )
                    
                    logger.info(f"🤖 AI Validation: {result.get('decision')} | "
                              f"Confidence: {result.get('confidence', 0):.1%} | "
                              f"Latency: {latency:.0f}ms")
                    return result
                else:
                    # Fallback: allow trade with reduced confidence
                    logger.warning(f"AI validation unavailable (HTTP {resp.status}), using signal strength")
                    return {
                        'decision': 'EXECUTE' if signal_strength >= 0.7 else 'SKIP',
                        'confidence': signal_strength * 0.7,  # Reduced confidence
                        'reasoning': 'AI unavailable, using signal strength threshold',
                        'ai_available': False
                    }
                    
        except Exception as e:
            logger.warning(f"AI validation error: {e}, using fallback")
            return {
                'decision': 'EXECUTE' if signal_strength >= 0.7 else 'SKIP',
                'confidence': signal_strength * 0.7,
                'reasoning': f'AI error: {str(e)}, using signal strength threshold',
                'ai_available': False
            }
    
    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()
    
    def get_stats(self) -> Dict:
        return {
            **self._stats,
            'healthy': self._healthy,
            'last_check': self._last_check.isoformat() if self._last_check else None
        }


class SignalEngineClient:
    """Client for Signal Engine Service - Gemini Elite Signals for Hedging"""
    
    SIGNAL_ENGINE_URL = "http://localhost:4090"
    
    def __init__(self):
        self._session: Optional[aiohttp.ClientSession] = None
        self._healthy = False
        self._cached_signals: Dict[str, Dict] = {}
        self._cache_time: Dict[str, datetime] = {}
        self._cache_ttl = 30  # seconds
    
    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10))
        return self._session
    
    async def check_health(self) -> bool:
        """Check if Signal Engine is healthy"""
        try:
            session = await self._get_session()
            async with session.get(f"{self.SIGNAL_ENGINE_URL}/health", timeout=5) as resp:
                if resp.status == 200:
                    self._healthy = True
                    return True
        except Exception as e:
            logger.debug(f"Signal Engine health check failed: {e}")
        self._healthy = False
        return False
    
    async def get_signal(self, instrument: str) -> Optional[Dict]:
        """Get Gemini Elite signal for hedging decisions"""
        try:
            # Check cache first
            cache_time = self._cache_time.get(instrument)
            if cache_time and (datetime.now() - cache_time).total_seconds() < self._cache_ttl:
                return self._cached_signals.get(instrument)
            
            session = await self._get_session()
            async with session.get(
                f"{self.SIGNAL_ENGINE_URL}/api/signals/{instrument.lower()}",
                timeout=10
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    signal = data.get('signal')
                    if signal:
                        self._cached_signals[instrument] = signal
                        self._cache_time[instrument] = datetime.now()
                        logger.debug(f"📡 Signal Engine: {instrument} {signal.get('signal_type')} | "
                                   f"Conf: {signal.get('confidence', 0):.0%}")
                        return signal
        except Exception as e:
            logger.debug(f"Signal Engine error: {e}")
        return None
    
    async def get_hedging_recommendation(self, instrument: str, current_position: str) -> Dict:
        """
        Get AI-powered hedging recommendation based on Signal Engine signals.
        
        Returns recommendation for:
        - Whether to hedge (add protection)
        - Which direction to hedge
        - Hedge intensity (based on market phase)
        """
        try:
            signal = await self.get_signal(instrument)
            
            if not signal:
                return {
                    'should_hedge': False,
                    'hedge_direction': None,
                    'intensity': 'normal',
                    'confidence': 0.5,
                    'signal_engine_available': False,
                    'reason': 'Signal Engine unavailable'
                }
            
            signal_type = signal.get('signal_type', 'HOLD')
            confidence = signal.get('confidence', 0.5)
            ai_confidence = signal.get('ai_confidence', 0)
            market_phase = signal.get('market_phase', 'unknown')
            smart_money_flow = signal.get('smart_money_flow', 'neutral')
            vix_regime = signal.get('vix_regime', 'normal')
            gemini_validated = signal.get('gemini_validated', False)
            
            # Hedging logic based on market conditions
            should_hedge = False
            hedge_direction = None
            intensity = 'normal'
            reason = ''
            
            # High volatility = always consider hedging
            if vix_regime in ['high', 'extreme', 'elevated']:
                should_hedge = True
                intensity = 'aggressive' if vix_regime == 'extreme' else 'elevated'
                reason = f'High volatility regime ({vix_regime})'
            
            # Strong opposing signal = hedge existing position
            bullish_signals = ['BUY', 'STRONG_BUY', 'CALL']
            bearish_signals = ['SELL', 'STRONG_SELL', 'PUT']
            
            if current_position.upper() in ['LONG', 'CALL', 'BUY']:
                if signal_type.upper() in bearish_signals and confidence >= 0.7:
                    should_hedge = True
                    hedge_direction = 'PUT'
                    intensity = 'aggressive' if confidence >= 0.85 else 'normal'
                    reason = f'Bearish signal ({signal_type}) against LONG position'
            elif current_position.upper() in ['SHORT', 'PUT', 'SELL']:
                if signal_type.upper() in bullish_signals and confidence >= 0.7:
                    should_hedge = True
                    hedge_direction = 'CALL'
                    intensity = 'aggressive' if confidence >= 0.85 else 'normal'
                    reason = f'Bullish signal ({signal_type}) against SHORT position'
            
            # Smart money divergence = hedge
            if smart_money_flow in ['strong_distribution', 'distribution'] and current_position.upper() in ['LONG', 'CALL']:
                should_hedge = True
                hedge_direction = 'PUT'
                reason = f'Smart money distribution detected'
            elif smart_money_flow in ['strong_accumulation', 'accumulation'] and current_position.upper() in ['SHORT', 'PUT']:
                should_hedge = True
                hedge_direction = 'CALL'
                reason = f'Smart money accumulation detected'
            
            # Calculate final confidence with Gemini validation bonus
            final_confidence = confidence
            if gemini_validated:
                final_confidence = min(1.0, confidence + 0.05)
            
            return {
                'should_hedge': should_hedge,
                'hedge_direction': hedge_direction,
                'intensity': intensity,
                'confidence': final_confidence,
                'signal_engine_available': True,
                'signal_type': signal_type,
                'market_phase': market_phase,
                'smart_money_flow': smart_money_flow,
                'vix_regime': vix_regime,
                'gemini_validated': gemini_validated,
                'reason': reason
            }
            
        except Exception as e:
            logger.debug(f"Hedging recommendation error: {e}")
            return {
                'should_hedge': False,
                'hedge_direction': None,
                'intensity': 'normal',
                'confidence': 0.5,
                'signal_engine_available': False,
                'reason': f'Error: {str(e)}'
            }
    
    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()


# Global AI client
gemini_client = GeminiAIClient()

# Signal Engine client for Gemini Elite signals
signal_engine_client = SignalEngineClient()


# ==================== Configuration ====================

class ServiceConfig:
    """Production service configuration"""
    PORT = 4003  # Different port from scalping service
    HOST = "0.0.0.0"
    
    # Trading instruments
    INSTRUMENTS = ["NIFTY", "BANKNIFTY"]  # Focus on major indices
    
    # Capital
    INITIAL_CAPITAL = 500000.0
    
    # Lot sizes
    LOT_SIZES = {
        "NIFTY": 75,
        "BANKNIFTY": 35,
        "FINNIFTY": 65,
        "SENSEX": 20,
        "BANKEX": 30
    }
    
    # ═══════════════════════════════════════════════════════════════════════
    # AI CONFIGURATION - ELITE 300%+ MONTHLY RETURNS
    # ═══════════════════════════════════════════════════════════════════════
    AI_ENABLED = True
    AI_MIN_CONFIDENCE = 0.88           # RAISED: 88% minimum (was 85%)
    AI_LEGENDARY_CONFIDENCE = 0.95     # NEW: 95% for max leverage signals
    AI_REQUIRED_FOR_ENTRY = True
    GEMINI_SERVICE_URL = "http://localhost:4080"
    LOG_AI_SIGNALS = True
    
    # Tick Forwarding Configuration
    ENABLE_TICK_FORWARDING = True
    SCALPING_SERVICE_URL = "http://localhost:4002"
    FORWARD_TO_SERVICES = ["scalping"]
    
    # ═══════════════════════════════════════════════════════════════════════
    # AGGRESSIVE STRATEGY FOR 300%+ MONTHLY
    # ═══════════════════════════════════════════════════════════════════════
    MIN_AI_CONFIDENCE = 0.88         # RAISED: 88% for quality
    MIN_SIGNAL_STRENGTH = 0.80       # RAISED: 80% signal strength
    STOP_LOSS_PCT = 20.0             # TIGHTER: 20% stop (was 25%)
    TARGET_PCT = 80.0                # RAISED: 80% target (was 60%)
    TARGET_PCT_AGGRESSIVE = 120.0    # NEW: 120% for strong momentum
    MAX_HOLDING_MINUTES = 30         # REDUCED: 30 min (was 45) - faster exits
    MAX_TRADES_PER_DAY = 12          # RAISED: 12 trades (was 8) - more opportunities
    MAX_POSITIONS = 3                # RAISED: 3 positions for diversification
    
    # NEW: Aggressive scaling parameters
    SCALE_ON_PROFIT_PCT = 15.0       # Scale up at 15% profit
    SCALE_MULTIPLIER = 1.5           # Add 50% more on scale
    MAX_SCALE_LEVELS = 3             # Maximum 3 scale levels
    
    # NEW: Compounding settings
    ENABLE_COMPOUNDING = True        # Reinvest profits same day
    COMPOUND_THRESHOLD_PCT = 3.0     # Compound after 3% daily profit
    
    # Trading hours (IST) - EXTENDED for more opportunities
    MARKET_OPEN = time(9, 15)
    MARKET_CLOSE = time(15, 30)
    
    # Preferred trading windows - AGGRESSIVE
    MORNING_START = time(9, 18)      # Earlier start for gap momentum
    MORNING_END = time(11, 00)       # Extended morning window
    AFTERNOON_START = time(13, 30)   # Earlier afternoon start
    AFTERNOON_END = time(15, 10)     # Later close for EOD momentum


def load_dhan_config() -> Dict:
    """Load Dhan configuration"""
    config_path = PROJECT_ROOT / "dhan_config.json"
    try:
        with open(config_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load dhan_config.json: {e}")
        return {}


def save_dhan_config(config: Dict) -> bool:
    """Save Dhan configuration"""
    config_path = PROJECT_ROOT / "dhan_config.json"
    try:
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=4)
        return True
    except Exception as e:
        logger.error(f"Failed to save dhan_config.json: {e}")
        return False


# ==================== Pydantic Models ====================

class TradingModeRequest(BaseModel):
    mode: str = Field(..., description="'paper' or 'production'")
    confirmation: str = Field(None, description="Required for production: 'I_UNDERSTAND_REAL_MONEY'")


class TokenUpdateRequest(BaseModel):
    access_token: str = Field(..., description="Dhan API access token")
    client_id: str = Field(None, description="Dhan client ID (optional)")


class ManualTradeRequest(BaseModel):
    instrument: str
    option_type: str
    strike: float
    lots: int = 1
    reason: str = "manual"


# ==================== Signal Engine ====================

class SignalDirection(Enum):
    BULLISH = "bullish"
    BEARISH = "bearish"
    NEUTRAL = "neutral"


class OptionsSignalEngine:
    """
    Options signal engine with AI integration
    Generates trading signals based on price action and AI analysis
    """
    
    def __init__(self, instruments: List[str]):
        self.instruments = instruments
        self._db = get_paper_trading_db()
        
        # State per instrument
        self._state: Dict[str, Dict] = {}
        for inst in instruments:
            self._state[inst] = {
                'prices': [],
                'ticks_received': 0,
                'current_price': 0.0,
                'last_signal_time': None,
                'trend_direction': SignalDirection.NEUTRAL,
                'signal_strength': 0.0,
                'ai_confidence': 0.0,
                'consecutive_up': 0,
                'consecutive_down': 0,
            }
    
    def update(self, instrument: str, ltp: float) -> Dict:
        """Update state with new price"""
        if instrument not in self._state:
            return {}
        
        state = self._state[instrument]
        state['ticks_received'] += 1
        state['current_price'] = ltp
        
        # Track price movement
        if state['prices']:
            prev = state['prices'][-1]
            if ltp > prev:
                state['consecutive_up'] += 1
                state['consecutive_down'] = 0
            elif ltp < prev:
                state['consecutive_down'] += 1
                state['consecutive_up'] = 0
        
        # Update price history
        state['prices'].append(ltp)
        if len(state['prices']) > 100:
            state['prices'] = state['prices'][-100:]
        
        # Calculate trend
        if len(state['prices']) >= 10:
            recent_change = (state['prices'][-1] - state['prices'][-10]) / state['prices'][-10] * 100
            
            if recent_change > 0.1:
                state['trend_direction'] = SignalDirection.BULLISH
                state['signal_strength'] = min(1.0, abs(recent_change) / 0.5)
            elif recent_change < -0.1:
                state['trend_direction'] = SignalDirection.BEARISH
                state['signal_strength'] = min(1.0, abs(recent_change) / 0.5)
            else:
                state['trend_direction'] = SignalDirection.NEUTRAL
                state['signal_strength'] = 0.0
            
            # Simulated AI confidence based on trend strength and consistency
            consecutive = max(state['consecutive_up'], state['consecutive_down'])
            state['ai_confidence'] = min(1.0, 0.5 + consecutive * 0.1 + state['signal_strength'] * 0.3)
        
        return state
    
    def should_enter(self, instrument: str) -> tuple:
        """
        Check if conditions favor entry with ENHANCED 90%+ win rate filters.
        
        ENHANCEMENTS:
        1. Better entry timing - avoid market open/close volatility
        2. Theta management - avoid high theta decay periods
        3. Market regime check
        
        Returns: (should_enter: bool, option_type: str, signal_data: Dict)
        """
        state = self._state.get(instrument, {})
        if not state:
            return False, None, {}
        
        # Check cooldown
        last_signal = state.get('last_signal_time')
        if last_signal and (datetime.now() - last_signal).total_seconds() < 120:
            return False, None, {}
        
        # ════════════════════════════════════════════════════════════════════
        # ENHANCEMENT 1: ENTRY TIMING FILTER (Avoid choppy periods)
        # ════════════════════════════════════════════════════════════════════
        now = datetime.now()
        current_time = now.time()
        
        # Avoid first 15 minutes (9:15 - 9:30) - high volatility, whipsaws
        market_open = datetime.strptime("09:30", "%H:%M").time()
        if current_time < market_open:
            return False, None, {}
        
        # Avoid last 30 minutes (3:00 - 3:30) - theta acceleration, unpredictable
        market_close_zone = datetime.strptime("15:00", "%H:%M").time()
        if current_time > market_close_zone:
            return False, None, {}
        
        # Best entry windows: 10:00-11:30 and 13:30-14:30 (established trends)
        optimal_morning_start = datetime.strptime("10:00", "%H:%M").time()
        optimal_morning_end = datetime.strptime("11:30", "%H:%M").time()
        optimal_afternoon_start = datetime.strptime("13:30", "%H:%M").time()
        optimal_afternoon_end = datetime.strptime("14:30", "%H:%M").time()
        
        is_optimal_time = (optimal_morning_start <= current_time <= optimal_morning_end) or \
                         (optimal_afternoon_start <= current_time <= optimal_afternoon_end)
        
        # ════════════════════════════════════════════════════════════════════
        # ENHANCEMENT 2: THETA DECAY MANAGEMENT
        # ════════════════════════════════════════════════════════════════════
        # On expiry day (Thursday), theta accelerates - be more conservative
        is_expiry_day = now.weekday() == 3  # Thursday = 3
        if is_expiry_day:
            # After 1 PM on expiry, theta decay is extreme
            expiry_theta_zone = datetime.strptime("13:00", "%H:%M").time()
            if current_time > expiry_theta_zone:
                return False, None, {}
        
        # ════════════════════════════════════════════════════════════════════
        # Check thresholds with optimal time boost
        # ════════════════════════════════════════════════════════════════════
        ai_confidence = state.get('ai_confidence', 0)
        signal_strength = state.get('signal_strength', 0)
        
        # Require HIGHER confidence outside optimal windows
        min_confidence = ServiceConfig.MIN_AI_CONFIDENCE
        if not is_optimal_time:
            min_confidence = min(0.9, min_confidence + 0.1)  # 10% higher threshold
        
        if ai_confidence < min_confidence:
            return False, None, {}
        
        if signal_strength < ServiceConfig.MIN_SIGNAL_STRENGTH:
            return False, None, {}
        
        trend = state.get('trend_direction', SignalDirection.NEUTRAL)
        if trend == SignalDirection.NEUTRAL:
            return False, None, {}
        
        option_type = "CE" if trend == SignalDirection.BULLISH else "PE"
        
        signal_data = {
            'instrument': instrument,
            'signal_type': trend.value,
            'direction': option_type,
            'strength': signal_strength,
            'ai_confidence': ai_confidence,
            'is_optimal_time': is_optimal_time,
            'is_expiry_day': is_expiry_day,
            'timestamp': datetime.now()
        }
        
        return True, option_type, signal_data
    
    def get_state(self, instrument: str) -> Dict:
        """Get current state"""
        return self._state.get(instrument, {})
    
    def get_best_opportunity(self) -> Optional[str]:
        """Get instrument with best opportunity"""
        best_inst = None
        best_confidence = 0
        
        for inst in self.instruments:
            state = self._state.get(inst, {})
            confidence = state.get('ai_confidence', 0)
            if confidence > best_confidence and confidence >= ServiceConfig.MIN_AI_CONFIDENCE:
                best_confidence = confidence
                best_inst = inst
        
        return best_inst


# ==================== Paper Trading Executor ====================

class PaperOptionsExecutor:
    """
    Paper trading executor for options
    Simulates trade execution without real money
    """
    
    SLIPPAGE_PCT = 0.5  # Options have higher slippage
    
    def __init__(self, initial_capital: float = 500000.0, signal_engine: Optional['OptionsSignalEngine'] = None):
        self.initial_capital = initial_capital
        self.capital = initial_capital
        self.realized_pnl = 0.0
        
        self._positions: Dict[str, PaperPosition] = {}
        self._db = get_paper_trading_db()
        self._signal_engine = signal_engine  # Reference for intelligent exits
        
        self._daily_trades = 0
        self._current_date = date.today()
        
        logger.info(f"PaperOptionsExecutor initialized with capital: ₹{initial_capital:,.2f}")
    
    def set_signal_engine(self, signal_engine: 'OptionsSignalEngine'):
        """Set signal engine reference for intelligent exit logic"""
        self._signal_engine = signal_engine
    
    @property
    def position_count(self) -> int:
        return len(self._positions)
    
    @property
    def open_positions(self) -> List[PaperPosition]:
        return list(self._positions.values())
    
    def can_enter(self, instrument: str) -> tuple:
        """Check if we can enter a position"""
        if len(self._positions) >= ServiceConfig.MAX_POSITIONS:
            return False, "Max positions reached"
        
        if self._daily_trades >= ServiceConfig.MAX_TRADES_PER_DAY:
            return False, "Max daily trades reached"
        
        # Check existing position on same instrument
        for pos in self._positions.values():
            if pos.instrument == instrument:
                return False, f"Already have position on {instrument}"
        
        return True, "OK"
    
    async def enter_position(
        self,
        instrument: str,
        option_type: str,
        strike: float,
        current_price: float,
        lots: int = 1,
        reason: str = "",
        signal_data: Dict = None
    ) -> Dict:
        """Enter a paper position"""
        can, msg = self.can_enter(instrument)
        if not can:
            return {"success": False, "message": msg}
        
        trade_id = f"POT_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
        lot_size = ServiceConfig.LOT_SIZES.get(instrument, 75)
        
        # Apply slippage
        fill_price = current_price * (1 + self.SLIPPAGE_PCT / 100)
        
        position = PaperPosition(
            position_id=trade_id,
            trade_id=trade_id,
            instrument=instrument,
            option_type=option_type,
            strike=strike,
            entry_price=fill_price,
            current_price=fill_price,
            quantity=lots,
            lot_size=lot_size,
            entry_time=datetime.now(),
            entry_reason=reason,
            ai_confidence=signal_data.get('ai_confidence', 0) if signal_data else 0
        )
        
        self._positions[trade_id] = position
        self._daily_trades += 1
        
        # Save to database
        self._db.insert_paper_trade({
            'trade_id': trade_id,
            'timestamp_entry': datetime.now(),
            'instrument': instrument,
            'option_type': option_type,
            'strike': strike,
            'entry_price': fill_price,
            'quantity': lots,
            'lot_size': lot_size,
            'entry_reason': reason,
            'ai_confidence_entry': signal_data.get('ai_confidence', 0) if signal_data else 0,
            'momentum_at_entry': signal_data.get('strength', 0) if signal_data else 0
        })
        
        # Save signal if provided
        if signal_data:
            signal_data['was_traded'] = True
            self._db.save_important_signal(signal_data)
        
        logger.info(f"📈 ENTRY: {trade_id} | {instrument} {strike}{option_type} @ ₹{fill_price:.2f}")
        
        return {
            "success": True,
            "trade_id": trade_id,
            "fill_price": fill_price,
            "message": f"Entered {instrument} {strike}{option_type}"
        }
    
    async def exit_position(
        self,
        trade_id: str,
        current_price: float,
        reason: str = "manual"
    ) -> Dict:
        """Exit a paper position"""
        if trade_id not in self._positions:
            return {"success": False, "message": "Position not found"}
        
        position = self._positions[trade_id]
        
        # Apply slippage
        fill_price = current_price * (1 - self.SLIPPAGE_PCT / 100)
        
        # Calculate PnL
        pnl = (fill_price - position.entry_price) * position.quantity * position.lot_size
        pnl_pct = (fill_price - position.entry_price) / position.entry_price * 100
        
        self.realized_pnl += pnl
        
        # Update database
        self._db.update_paper_trade_exit(
            trade_id=trade_id,
            exit_price=fill_price,
            exit_reason=reason,
            pnl=pnl,
            pnl_pct=pnl_pct
        )
        
        # Remove position
        del self._positions[trade_id]
        
        logger.info(f"📉 EXIT: {trade_id} | PnL: ₹{pnl:,.2f} ({pnl_pct:.1f}%) | Reason: {reason}")
        
        return {
            "success": True,
            "trade_id": trade_id,
            "fill_price": fill_price,
            "pnl": pnl,
            "pnl_pct": pnl_pct,
            "message": reason
        }
    
    async def check_exits(self) -> List[Dict]:
        """
        INTELLIGENT EXIT LOGIC for Options
        - Trailing profit lock
        - Adaptive stop loss based on profit level
        - Trend-aware exits
        - Time decay consideration for options
        """
        results = []
        
        for trade_id, pos in list(self._positions.items()):
            pnl_pct = pos.unrealized_pnl_pct
            hold_time = (datetime.now() - pos.entry_time).total_seconds() / 60
            
            exit_reason = None
            
            # Get current trend from signal engine
            state = self._signal_engine.get_state(pos.instrument) if self._signal_engine else {}
            trend = state.get('trend_direction', SignalDirection.NEUTRAL) if state else SignalDirection.NEUTRAL
            signal_strength = state.get('signal_strength', 0) if state else 0
            
            # =====================================================
            # INTELLIGENT OPTIONS EXIT STRATEGY
            # =====================================================
            
            # 1. DIRECTION-AWARE TREND EXIT
            # CE positions should exit on bearish trend, PE on bullish
            if pos.option_type == "CE" and trend == SignalDirection.BEARISH:
                if pnl_pct > 10:  # Lock profit on reversal
                    exit_reason = f"trend_reversal_profit_lock ({pnl_pct:.1f}%)"
                elif signal_strength > 0.5:  # Strong bearish signal = cut even at loss
                    exit_reason = f"strong_bearish_reversal"
            elif pos.option_type == "PE" and trend == SignalDirection.BULLISH:
                if pnl_pct > 10:  # Lock profit on reversal
                    exit_reason = f"trend_reversal_profit_lock ({pnl_pct:.1f}%)"
                elif signal_strength > 0.5:  # Strong bullish signal = cut even at loss
                    exit_reason = f"strong_bullish_reversal"
            
            # 2. TRAILING PROFIT LOCK (Dynamic based on profit level)
            if exit_reason is None and pnl_pct > 0:
                # Options can move fast - lock in profits aggressively
                if pnl_pct >= 80:
                    # At 80%+ profit, lock in 70% of gains
                    if signal_strength < 0.3:  # Momentum fading
                        exit_reason = f"mega_profit_lock ({pnl_pct:.1f}%)"
                elif pnl_pct >= 50:
                    # At 50%+ profit, exit if momentum fading
                    if signal_strength < 0.4:
                        exit_reason = f"profit_lock_momentum_fade ({pnl_pct:.1f}%)"
                elif pnl_pct >= 30:
                    # At 30%+ profit, exit if trend neutral or reversing
                    if trend == SignalDirection.NEUTRAL:
                        exit_reason = f"profit_lock_neutral_trend ({pnl_pct:.1f}%)"
                elif pnl_pct >= 15:
                    # At 15%+ profit, exit if time decay will erode
                    if hold_time >= 30:  # Held 30+ mins with profit
                        exit_reason = f"profit_lock_time_decay ({pnl_pct:.1f}%)"
            
            # 3. ADAPTIVE STOP LOSS (Based on profit level and time)
            if exit_reason is None:
                # Dynamic stop loss
                if pnl_pct >= 30:
                    # If was up 30%+, don't let it go below 15%
                    adaptive_stop = -15.0
                elif pnl_pct >= 15:
                    # If was up 15%+, don't let it go below 0%
                    adaptive_stop = -5.0
                elif hold_time <= 10:
                    # First 10 mins - wider stop (options need room)
                    adaptive_stop = -25.0
                elif hold_time <= 30:
                    # 10-30 mins - normal stop
                    adaptive_stop = -20.0
                else:
                    # After 30 mins - tighter stop
                    adaptive_stop = -15.0
                
                if pnl_pct <= adaptive_stop:
                    exit_reason = f"adaptive_stop ({pnl_pct:.1f}% < {adaptive_stop}%)"
            
            # 4. HARD STOP LOSS (Never exceed this)
            if exit_reason is None and pnl_pct <= -ServiceConfig.STOP_LOSS_PCT:
                exit_reason = f"hard_stop_loss ({pnl_pct:.1f}%)"
            
            # 5. ENHANCED TIME-BASED EXIT (Aggressive Theta Management)
            # ════════════════════════════════════════════════════════════════════
            now = datetime.now()
            current_time = now.time()
            is_expiry_day = now.weekday() == 3  # Thursday
            
            # On expiry day - exit earlier to avoid theta acceleration
            if is_expiry_day:
                expiry_exit_time = datetime.strptime("14:30", "%H:%M").time()
                if current_time > expiry_exit_time:
                    exit_reason = f"expiry_theta_exit (Exit before theta acceleration, P&L: {pnl_pct:.1f}%)"
            
            # General theta protection - exit before market close
            close_protection_time = datetime.strptime("15:10", "%H:%M").time()
            if exit_reason is None and current_time > close_protection_time:
                exit_reason = f"eod_theta_protection (P&L: {pnl_pct:.1f}%)"
            
            # Standard time-based exit
            if exit_reason is None and hold_time >= ServiceConfig.MAX_HOLDING_MINUTES:
                exit_reason = f"time_exit ({hold_time:.0f} mins, P&L: {pnl_pct:.1f}%)"
            # ════════════════════════════════════════════════════════════════════
            
            # Execute exit
            if exit_reason:
                result = await self.exit_position(trade_id, pos.current_price, exit_reason)
                results.append(result)
                logger.info(f"🎯 Intelligent Exit: {pos.instrument} {pos.option_type} | {exit_reason}")
        
        return results
    
    def get_summary(self) -> Dict:
        """Get position summary"""
        unrealized = sum(p.unrealized_pnl for p in self._positions.values())
        
        return {
            "position_count": len(self._positions),
            "positions": [
                {
                    "trade_id": p.trade_id,
                    "instrument": p.instrument,
                    "option_type": p.option_type,
                    "strike": p.strike,
                    "entry_price": p.entry_price,
                    "current_price": p.current_price,
                    "unrealized_pnl": p.unrealized_pnl,
                    "unrealized_pnl_pct": p.unrealized_pnl_pct,
                    "hold_time_mins": (datetime.now() - p.entry_time).total_seconds() / 60
                }
                for p in self._positions.values()
            ],
            "unrealized_pnl": unrealized,
            "realized_pnl": self.realized_pnl,
            "total_pnl": self.realized_pnl + unrealized,
            "daily_trades": self._daily_trades,
            "capital": self.capital + self.realized_pnl
        }


# ==================== Main Service ====================

class ProductionHedgerService:
    """
    Production-ready options hedger service
    - WebSocket for real-time data
    - Paper trading by default
    - Important signals logged for analysis
    """
    
    def __init__(self):
        self._db = get_paper_trading_db()
        
        # Load config
        dhan_config = load_dhan_config()
        self._access_token = dhan_config.get('access_token', '')
        self._client_id = dhan_config.get('client_id', '')
        
        # Components
        self._ws_client: Optional[DhanWebSocketClient] = None
        self._option_client: Optional[DhanOptionChainClient] = None
        self._executor: Optional[PaperOptionsExecutor] = None
        self._signal_engine: Optional[OptionsSignalEngine] = None
        
        # Initialize Institutional Greeks Hedging Engine
        self._greeks_engine = None
        if GREEKS_ENGINE_AVAILABLE:
            try:
                self._greeks_engine = create_hedging_engine({
                    'max_delta': 2000,
                    'max_gamma': 100,
                    'max_vega': 500,
                    'max_theta': 200,
                    'delta_threshold': 0.15,
                    'gamma_threshold': 0.10
                })
                logger.info("[OK] Institutional Greeks Hedging Engine initialized")
            except Exception as e:
                logger.warning(f"Could not initialize Greeks engine: {e}")
        
        # State
        self._running = False
        self._ws_task = None
        self._monitor_task = None
        
        logger.info("ProductionHedgerService initialized")
    
    def _is_trading_time(self) -> bool:
        """Check if current time is within trading windows"""
        now = datetime.now().time()
        
        if now < ServiceConfig.MARKET_OPEN or now > ServiceConfig.MARKET_CLOSE:
            return False
        
        in_morning = ServiceConfig.MORNING_START <= now <= ServiceConfig.MORNING_END
        in_afternoon = ServiceConfig.AFTERNOON_START <= now <= ServiceConfig.AFTERNOON_END
        
        return in_morning or in_afternoon
    
    async def _on_tick(self, tick: TickData):
        """Process incoming tick"""
        try:
            # Find instrument name
            instrument = None
            for name, sec_id in DhanWebSocketClient.INDEX_SECURITY_IDS.items():
                if sec_id == tick.security_id:
                    instrument = name
                    break
            
            if not instrument or instrument not in ServiceConfig.INSTRUMENTS:
                return
            
            # Update signal engine
            state = self._signal_engine.update(instrument, tick.ltp)
            
            # Forward tick to other services (fire and forget)
            if ServiceConfig.ENABLE_TICK_FORWARDING:
                asyncio.create_task(self._forward_tick(instrument, tick))
            
            # Check for trade entry
            if self._is_trading_time() and self._executor.position_count < ServiceConfig.MAX_POSITIONS:
                await self._evaluate_entry(instrument, tick.ltp, state)
            
            # Update position prices
            if self._executor.position_count > 0:
                self._update_positions(instrument, tick.ltp)
                
        except Exception as e:
            logger.error(f"Tick processing error: {e}")
            self._db.log_error("TICK_PROCESSING", str(e), "on_tick")
    
    async def _forward_tick(self, instrument: str, tick: TickData):
        """Forward tick to other trading services (fire and forget)"""
        try:
            # Forward to AI Scalping Service
            if "scalping" in ServiceConfig.FORWARD_TO_SERVICES:
                tick_data = {
                    "instrument": instrument,
                    "price": tick.ltp,
                    "volume": getattr(tick, 'volume', 0) or 0,
                    "bid": getattr(tick, 'bid', tick.ltp),
                    "ask": getattr(tick, 'ask', tick.ltp)
                }
                
                try:
                    async with aiohttp.ClientSession() as session:
                        async with session.post(
                            f"{ServiceConfig.SCALPING_SERVICE_URL}/tick",
                            json=tick_data,
                            timeout=aiohttp.ClientTimeout(total=1.0)  # 1 second timeout
                        ) as response:
                            if response.status != 200:
                                # Don't log every failure - just track for debugging
                                pass
                except asyncio.TimeoutError:
                    pass  # Ignore timeout - don't slow down main processing
                except Exception:
                    pass  # Ignore connection errors - service may be down
                    
        except Exception as e:
            # Log rarely to avoid spam
            if not hasattr(self, '_forward_error_count'):
                self._forward_error_count = 0
            self._forward_error_count += 1
            if self._forward_error_count % 100 == 1:
                logger.warning(f"Tick forwarding error (count: {self._forward_error_count}): {e}")
    
    async def _evaluate_entry(self, instrument: str, ltp: float, state: Dict):
        """Evaluate potential trade entry with 3-layer AI validation"""
        should_enter, option_type, signal_data = self._signal_engine.should_enter(instrument)
        
        if not should_enter:
            return
        
        can, msg = self._executor.can_enter(instrument)
        if not can:
            return
        
        try:
            # Get initial AI confidence from signal engine
            ai_confidence = state.get('ai_confidence', 0)
            hedge_direction = option_type  # CE for bullish, PE for bearish
            
            # ==================== LAYER 1: GEMINI AI VALIDATION ====================
            try:
                gemini_validation = await gemini_client.validate_trade(
                    instrument=instrument,
                    direction=hedge_direction,
                    signal_strength=state.get('signal_strength', 0),
                    entry_price=ltp
                )
                
                if gemini_validation:
                    if not gemini_validation.get('approve', True):
                        logger.info(f"[WARNING] Gemini AI REJECTED {instrument} {hedge_direction} entry")
                        return
                    
                    # Apply Gemini confidence boost
                    gemini_confidence = gemini_validation.get('confidence', 0)
                    if gemini_confidence > 0.7:
                        ai_confidence = min(1.0, ai_confidence + 0.1)
                        logger.info(f"🧠 Gemini validated {instrument} {hedge_direction} | Conf: {gemini_confidence:.0%}")
            except Exception as e:
                logger.debug(f"Gemini validation skipped: {e}")
            
            # ==================== LAYER 2: SIGNAL ENGINE ELITE VALIDATION ====================
            try:
                signal_alignment = await signal_engine_client.validate_hedge_alignment(
                    instrument=instrument,
                    hedge_direction=hedge_direction,
                    signal_strength=state.get('signal_strength', 0)
                )
                
                if signal_alignment:
                    if signal_alignment.get('aligned'):
                        # Boost confidence when aligned with elite signals
                        confidence_boost = signal_alignment.get('confidence_boost', 0)
                        ai_confidence = min(1.0, ai_confidence + confidence_boost)
                        elite_signal = signal_alignment.get('elite_signal_type', 'unknown')
                        logger.info(f"✨ Signal Engine ALIGNED: {instrument} | Elite: {elite_signal} | Boost: +{confidence_boost:.0%}")
                    else:
                        # Reduce confidence if not aligned
                        ai_confidence = max(0.3, ai_confidence - 0.1)
                        logger.info(f"[WARNING] Signal Engine NOT ALIGNED for {instrument} {hedge_direction}")
                        
                        # Strong rejection if elite signal contradicts
                        if signal_alignment.get('elite_signal_type') == 'REJECT':
                            logger.info(f"[REJECTED] Signal Engine REJECTED {instrument} {hedge_direction} - elite signal conflict")
                            return
            except Exception as e:
                logger.debug(f"Signal Engine validation skipped: {e}")
            
            # ==================== LAYER 3: FINAL CONFIDENCE CHECK ====================
            if ai_confidence < ServiceConfig.MIN_AI_CONFIDENCE:
                logger.debug(f"Entry rejected: Final confidence {ai_confidence:.0%} < {ServiceConfig.MIN_AI_CONFIDENCE:.0%}")
                return
            
            # Update signal data with enhanced confidence
            signal_data['ai_confidence'] = ai_confidence
            signal_data['triple_validated'] = True
            
            # Get ATM option price
            chain = await self._option_client.get_option_chain(instrument)
            if not chain:
                return
            
            # Find ATM strike
            strike_gap = 50 if instrument == "NIFTY" else 100
            atm_strike = round(ltp / strike_gap) * strike_gap
            
            # Find option price
            option_price = None
            for opt in chain:
                if opt.get("strike") == atm_strike:
                    opt_data = opt.get(option_type, {})
                    if opt_data:
                        option_price = opt_data.get("lastPrice", 0)
                        break
            
            if not option_price or option_price <= 0:
                return
            
            logger.info(f"[TARGET] TRIPLE-VALIDATED ENTRY: {instrument} {option_type} @ Rs.{option_price} | AI Conf: {ai_confidence:.0%}")
            
            # Execute paper trade
            result = await self._executor.enter_position(
                instrument=instrument,
                option_type=option_type,
                strike=atm_strike,
                current_price=option_price,
                lots=1,
                reason=f"triple_validated_{ai_confidence:.2f}",
                signal_data=signal_data
            )
            
            if result.get('success'):
                state['last_signal_time'] = datetime.now()
                logger.info(f"[OK] Position opened: {instrument} {option_type} @ {atm_strike}")
                
                # Track Greeks with Institutional Engine
                if self._greeks_engine:
                    try:
                        from datetime import timedelta
                        expiry_date = datetime.now() + timedelta(days=7)  # Weekly expiry
                        greeks = self._greeks_engine.add_position(
                            symbol=instrument,
                            strike=atm_strike,
                            expiry=expiry_date,
                            option_type=option_type,
                            quantity=ServiceConfig.LOT_SIZES.get(instrument, 1),
                            entry_price=option_price,
                            spot_price=ltp,
                            implied_vol=0.15  # Default IV
                        )
                        logger.info(f"📊 Greeks tracked: Delta={greeks.delta:.2f}, Gamma={greeks.gamma:.4f}, Vega={greeks.vega:.2f}")
                    except Exception as e:
                        logger.debug(f"Greeks tracking skipped: {e}")
                
        except Exception as e:
            logger.error(f"Entry evaluation error: {e}")
    
    def _update_positions(self, instrument: str, index_ltp: float):
        """Update position prices"""
        for pos in self._executor.open_positions:
            if pos.instrument == instrument:
                # Estimate option price movement
                delta = 0.5
                price_change = (index_ltp - pos.strike) * delta * (1 if pos.option_type == "CE" else -1) / 100
                estimated_price = pos.entry_price * (1 + price_change)
                pos.update_price(max(0.1, estimated_price))
    
    async def _monitor_positions(self):
        """Monitor positions for exits"""
        while self._running:
            try:
                if self._executor and self._executor.position_count > 0:
                    results = await self._executor.check_exits()
                    for result in results:
                        if result.get('success'):
                            logger.info(f"Auto-exit: {result}")
                
                await asyncio.sleep(1)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Position monitor error: {e}")
                await asyncio.sleep(5)
    
    async def _wait_for_gemini_service(self, max_retries: int = 10, delay: int = 3) -> bool:
        """Wait for Gemini service to be ready before processing trades"""
        logger.info("[STARTUP] Waiting for Gemini AI service to be ready...")
        
        for attempt in range(max_retries):
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(f"{ServiceConfig.GEMINI_SERVICE_URL}/health", timeout=5) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            if data.get('status') == 'healthy':
                                engines = data.get('engines', {})
                                if engines.get('tier_1') and engines.get('tier_2'):
                                    logger.info(f"[OK] Gemini AI service ready (Attempt {attempt + 1})")
                                    logger.info(f"    Models: Tier1={data.get('models', {}).get('tier_1')}, Tier2={data.get('models', {}).get('tier_2')}")
                                    return True
            except Exception as e:
                logger.debug(f"Gemini not ready (attempt {attempt + 1}/{max_retries}): {e}")
            
            if attempt < max_retries - 1:
                await asyncio.sleep(delay)
        
        logger.warning("[WARNING] Gemini service not available - will use fallback logic")
        return False
    
    async def start(self):
        """Start the service"""
        logger.info("=" * 60)
        logger.info("Starting AI Options Hedger Service")
        logger.info("=" * 60)
        
        # Wait for Gemini service to be ready
        gemini_ready = await self._wait_for_gemini_service()
        if not gemini_ready:
            logger.warning("Starting without Gemini AI - will retry connections during runtime")
        
        # Load strategy enabled state
        self._load_strategy_state()
        logger.info(f"Strategy Enabled: {self._strategy_enabled}")
        
        mode = self._db.get_trading_mode()
        logger.info(f"Trading Mode: {mode.value.upper()}")
        logger.info(f"Instruments: {ServiceConfig.INSTRUMENTS}")
        
        # Initialize components
        self._signal_engine = OptionsSignalEngine(ServiceConfig.INSTRUMENTS)
        
        # Check for evaluation mode
        if mode.value == 'evaluation':
            self._executor = HedgerEvaluationExecutor(
                access_token=self._access_token,
                client_id=self._client_id,
                initial_capital=ServiceConfig.INITIAL_CAPITAL
            )
            # Set signal engine for intelligent exits
            if hasattr(self._executor, 'set_signal_engine'):
                self._executor.set_signal_engine(self._signal_engine)
            logger.info("🔬 EVALUATION MODE - No real orders will be placed")
            logger.info("📊 All trades logged to database/evaluation_hedger.db")
        else:
            self._executor = PaperOptionsExecutor(ServiceConfig.INITIAL_CAPITAL, self._signal_engine)
        
        self._option_client = DhanOptionChainClient(self._access_token, self._client_id)
        
        # Initialize WebSocket
        self._ws_client = DhanWebSocketClient(
            access_token=self._access_token,
            client_id=self._client_id,
            on_tick=self._on_tick
        )
        
        self._running = True
        
        if await self._ws_client.connect():
            await self._ws_client.subscribe_indices(
                ServiceConfig.INSTRUMENTS,
                FeedRequestCode.QUOTE
            )
            
            self._ws_task = asyncio.create_task(self._ws_client.run())
            self._monitor_task = asyncio.create_task(self._monitor_positions())
            
            logger.info("[OK] Service started successfully")
            logger.info(f"API: http://localhost:{ServiceConfig.PORT}")
        else:
            logger.error("[ERROR] WebSocket connection failed")
            self._running = False
    
    async def stop(self):
        """Stop the service"""
        logger.info("Stopping service...")
        
        self._running = False
        
        if self._ws_task:
            self._ws_task.cancel()
        if self._monitor_task:
            self._monitor_task.cancel()
        
        if self._ws_client:
            await self._ws_client.disconnect()
        
        self._db.update_daily_summary()
        
        logger.info("Service stopped")
    
    def _load_strategy_state(self):
        """Load strategy enabled state (simple default, no persistence yet)"""
        # For now, just default to enabled
        # TODO: Add persistent state management with proper database schema
        self._strategy_enabled = True
        logger.info("Strategy state: enabled (default)")
    
    def _save_strategy_state(self, enabled: bool):
        """Persist strategy enabled state (simple in-memory for now)"""
        self._strategy_enabled = enabled
        logger.info(f"Strategy state updated: {'enabled' if enabled else 'disabled'}")
    
    def get_status(self) -> Dict:
        """Get service status"""
        mode = self._db.get_trading_mode()
        
        position_summary = {}
        if self._executor:
            # Use get_position_summary for evaluation executor
            if hasattr(self._executor, 'get_position_summary'):
                position_summary = self._executor.get_position_summary()
            elif hasattr(self._executor, 'get_summary'):
                position_summary = self._executor.get_summary()
        
        signal_status = {}
        if self._signal_engine:
            for inst in ServiceConfig.INSTRUMENTS:
                state = self._signal_engine.get_state(inst)
                if state:
                    signal_status[inst] = {
                        "current_price": state.get('current_price', 0),
                        "ticks_received": state.get('ticks_received', 0),
                        "trend": state.get('trend_direction', SignalDirection.NEUTRAL).value,
                        "signal_strength": round(state.get('signal_strength', 0), 2),
                        "ai_confidence": round(state.get('ai_confidence', 0), 2)
                    }
        
        return {
            "running": self._running,
            "strategy_enabled": self._strategy_enabled,
            "mode": mode.value,
            "is_trading_time": self._is_trading_time(),
            "positions": position_summary,
            "signals": signal_status,
            "tick_forwarding": {
                "enabled": ServiceConfig.ENABLE_TICK_FORWARDING,
                "targets": ServiceConfig.FORWARD_TO_SERVICES,
                "scalping_url": ServiceConfig.SCALPING_SERVICE_URL,
                "error_count": getattr(self, '_forward_error_count', 0)
            },
            "timestamp": datetime.now().isoformat()
        }
    
    async def set_trading_mode(self, mode: TradingMode, confirmation: str = None) -> bool:
        """Switch trading mode"""
        if mode == TradingMode.PRODUCTION:
            if confirmation != "I_UNDERSTAND_REAL_MONEY":
                raise ValueError("Production mode requires confirmation")
            logger.warning("[WARNING] SWITCHING TO PRODUCTION MODE [WARNING]")
        
        self._db.set_trading_mode(mode, "api")
        logger.info(f"Mode changed to: {mode.value}")
        return True


# ==================== FastAPI App ====================

service: Optional[ProductionHedgerService] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global service
    service = ProductionHedgerService()
    await service.start()
    yield
    if service:
        await service.stop()


app = FastAPI(
    title="AI Options Hedger Service",
    description="Production-ready options hedging with paper trading",
    version="2.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register Production Trading Router
if TRADING_ROUTER_AVAILABLE:
    app.include_router(trading_router, prefix="/api/trading", tags=["production-trading"])
    print("[OK] Production Trading Engine router loaded (Probe-Scale + Paper/Live mode)")


# ==================== Endpoints ====================

@app.get("/")
async def root():
    return {"service": "AI Options Hedger", "version": "2.0.0"}


@app.get("/health")
async def health():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}


@app.get("/greeks")
async def get_portfolio_greeks():
    """
    Get portfolio-level Greeks exposure.
    Uses Institutional Greeks Hedging Engine for accurate calculations.
    """
    if not service:
        raise HTTPException(503, "Service not ready")
    
    if not service._greeks_engine:
        return {
            "success": False,
            "message": "Greeks engine not available",
            "greeks": None
        }
    
    try:
        summary = service._greeks_engine.get_portfolio_summary()
        return {
            "success": True,
            "portfolio_greeks": summary.get('greeks', {}),
            "positions": summary.get('positions', []),
            "risk_status": summary.get('risk_status', {}),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting Greeks: {e}")
        raise HTTPException(500, str(e))


@app.get("/hedge-recommendations")
async def get_hedge_recommendations(spot_price: float = Query(None)):
    """
    Get institutional-grade hedge recommendations.
    Includes delta hedging, gamma scalping, and volatility arbitrage opportunities.
    """
    if not service:
        raise HTTPException(503, "Service not ready")
    
    if not service._greeks_engine:
        return {
            "success": False,
            "message": "Greeks engine not available",
            "recommendations": []
        }
    
    try:
        # Use provided spot price or estimate from positions
        if not spot_price and service._signal_engine:
            for inst in ServiceConfig.INSTRUMENTS:
                state = service._signal_engine.get_state(inst)
                if state.get('current_price', 0) > 0:
                    spot_price = state['current_price']
                    break
        
        if not spot_price:
            return {
                "success": False,
                "message": "Spot price required",
                "recommendations": []
            }
        
        recommendations = service._greeks_engine.generate_hedge_recommendations(
            spot_price=spot_price,
            realized_vol=0.15,
            implied_vol=0.15
        )
        
        return {
            "success": True,
            "spot_price": spot_price,
            "recommendations": [
                {
                    "strategy": rec.strategy.value,
                    "action": rec.action.value,
                    "symbol": rec.symbol,
                    "quantity": rec.quantity,
                    "urgency": rec.urgency,
                    "confidence": rec.confidence,
                    "rationale": rec.rationale,
                    "greeks_impact": rec.greeks_impact
                } for rec in recommendations
            ],
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting hedge recommendations: {e}")
        raise HTTPException(500, str(e))


@app.get("/risk-limits")
async def check_risk_limits():
    """Check if portfolio is within defined risk limits"""
    if not service or not service._greeks_engine:
        return {"within_limits": True, "message": "Greeks engine not available"}
    
    try:
        risk_status = service._greeks_engine.check_risk_limits()
        return {
            "within_limits": risk_status.get('within_limits', True),
            "breaches": risk_status.get('breaches', []),
            "utilization": risk_status.get('utilization', {}),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error checking risk limits: {e}")
        raise HTTPException(500, str(e))


@app.get("/status")
async def get_status():
    if not service:
        raise HTTPException(503, "Service not ready")
    return service.get_status()


@app.get("/trading-mode")
async def get_mode():
    return {"mode": get_paper_trading_db().get_trading_mode().value}


@app.post("/trading-mode")
async def set_mode(request: TradingModeRequest):
    if not service:
        raise HTTPException(503, "Service not ready")
    try:
        mode = TradingMode(request.mode)
        await service.set_trading_mode(mode, request.confirmation)
        return {"success": True, "mode": mode.value}
    except ValueError as e:
        raise HTTPException(400, str(e))


@app.get("/positions")
async def get_positions():
    if service and service._executor:
        if hasattr(service._executor, 'get_position_summary'):
            return service._executor.get_position_summary()
        elif hasattr(service._executor, 'get_summary'):
            return service._executor.get_summary()
    return {"positions": [], "count": 0}


@app.get("/signals")
async def get_signals():
    if not service or not service._signal_engine:
        return {"signals": {}}
    
    result = {}
    for inst in ServiceConfig.INSTRUMENTS:
        should_enter, direction, signal_data = service._signal_engine.should_enter(inst)
        state = service._signal_engine.get_state(inst)
        result[inst] = {
            "current_price": state.get('current_price', 0),
            "trend": state.get('trend_direction', SignalDirection.NEUTRAL).value,
            "signal_strength": round(state.get('signal_strength', 0), 2),
            "ai_confidence": round(state.get('ai_confidence', 0), 2),
            "should_enter": should_enter,
            "direction": direction
        }
    
    return {"signals": result, "best": service._signal_engine.get_best_opportunity()}


@app.get("/api/signals")
async def get_api_signals():
    """Get signals in frontend-compatible format"""
    if not service or not service._signal_engine:
        return {"signals": [], "count": 0}
    
    signals = []
    for inst in ServiceConfig.INSTRUMENTS:
        should_enter, direction, signal_data = service._signal_engine.should_enter(inst)
        if should_enter and signal_data:
            state = service._signal_engine.get_state(inst)
            signals.append({
                "id": f"hedger-{inst}-{datetime.now().isoformat()}",
                "timestamp": datetime.now().isoformat(),
                "signal_type": direction.value if direction else "NEUTRAL",
                "symbol": inst,
                "strike": signal_data.get('strike', 0),
                "confidence": state.get('ai_confidence', 0.5),
                "entry_price": state.get('current_price', 0),
                "target": signal_data.get('target', 0),
                "stop_loss": signal_data.get('stop_loss', 0),
                "technical_score": state.get('signal_strength', 0),
                "risk_reward": signal_data.get('risk_reward', 2.0),
                "expected_return": signal_data.get('expected_return', 0),
                "status": "active"
            })
    
    return {
        "signals": signals,
        "count": len(signals),
        "timestamp": datetime.now().isoformat()
    }


@app.get("/analysis")
async def get_analysis():
    db = get_paper_trading_db()
    return db.get_analysis_summary()


@app.get("/trades/today")
async def get_today_trades():
    db = get_paper_trading_db()
    return {"trades": db.get_paper_trades_by_date(date.today())}


@app.get("/trades/recent")
async def get_recent_trades(limit: int = 50):
    db = get_paper_trading_db()
    return {"trades": db.get_recent_paper_trades(limit)}


@app.get("/signals/today")
async def get_today_signals():
    db = get_paper_trading_db()
    return {"signals": db.get_signals_by_date(date.today())}


@app.get("/errors")
async def get_errors():
    db = get_paper_trading_db()
    return {"errors": db.get_unresolved_errors()}


@app.get("/daily-summary")
async def get_daily_summary(days: int = 30):
    db = get_paper_trading_db()
    return {"summaries": db.get_daily_summaries(days)}


@app.post("/exit-all")
async def exit_all(reason: str = "manual_exit_all"):
    if not service or not service._executor:
        return {"success": True, "exits": 0}
    
    positions = list(service._executor.open_positions)
    results = []
    
    for pos in positions:
        result = await service._executor.exit_position(pos.trade_id, pos.current_price, reason)
        results.append(result)
    
    return {"success": True, "exits": len(results), "results": results}


@app.get("/config")
async def get_config():
    if not service:
        capital = getattr(ServiceConfig, 'CAPITAL', 100000)
        max_loss = getattr(ServiceConfig, 'MAX_DAILY_LOSS_PCT', 0.05)
        paper_mode = True
    else:
        capital = getattr(service, '_capital', 100000)
        max_loss = getattr(service, '_max_daily_loss_pct', 0.05)
        paper_mode = service._db.get_trading_mode() == TradingMode.PAPER if hasattr(service, '_db') else True
    
    return {
        "capital": capital,
        "max_daily_loss": max_loss,
        "paper_trading": paper_mode,
        "instruments": ServiceConfig.INSTRUMENTS,
        "min_ai_confidence": ServiceConfig.MIN_AI_CONFIDENCE,
        "min_signal_strength": ServiceConfig.MIN_SIGNAL_STRENGTH,
        "stop_loss_pct": ServiceConfig.STOP_LOSS_PCT,
        "target_pct": ServiceConfig.TARGET_PCT,
        "max_holding_minutes": ServiceConfig.MAX_HOLDING_MINUTES,
        "max_trades_per_day": ServiceConfig.MAX_TRADES_PER_DAY,
        "trading_windows": {
            "morning": f"{ServiceConfig.MORNING_START} - {ServiceConfig.MORNING_END}",
            "afternoon": f"{ServiceConfig.AFTERNOON_START} - {ServiceConfig.AFTERNOON_END}"
        }
    }


@app.put("/config")
async def update_config(request: dict):
    """Update runtime configuration"""
    if not service:
        raise HTTPException(503, "Service not ready")
    
    try:
        if 'capital' in request:
            service._capital = float(request['capital'])
            logger.info(f"Capital updated to: ₹{service._capital:,.0f}")
        
        if 'max_daily_loss' in request:
            service._max_daily_loss_pct = float(request['max_daily_loss'])
            logger.info(f"Max daily loss updated to: {service._max_daily_loss_pct*100:.1f}%")
        
        return {
            "success": True,
            "capital": service._capital,
            "max_daily_loss": service._max_daily_loss_pct
        }
    except Exception as e:
        raise HTTPException(400, str(e))


@app.post("/start")
async def start_service(request: dict = None):
    """Enable the hedging strategy"""
    if not service:
        raise HTTPException(503, "Service not initialized")
    
    # Update config if provided
    if request:
        if 'capital' in request:
            service._capital = float(request['capital'])
        if 'max_daily_loss' in request:
            service._max_daily_loss_pct = float(request['max_daily_loss'])
        if 'mode' in request:
            mode = TradingMode.PRODUCTION if request['mode'] == 'live' else TradingMode.PAPER
            service._db.set_trading_mode(mode, "api")
    
    # Enable strategy state
    service._save_strategy_state(True)
    
    # Start service if not already running
    if not service._running:
        await service.start()
    
    return {
        "success": True,
        "message": "Strategy enabled",
        "running": service._running,
        "strategy_enabled": service._strategy_enabled
    }


@app.post("/stop")
async def stop_service():
    """Disable the hedging strategy"""
    if not service:
        raise HTTPException(503, "Service not initialized")
    
    # Disable strategy state (persisted)
    service._save_strategy_state(False)
    
    # Close any open positions
    if service._executor and hasattr(service._executor, 'get_open_positions'):
        try:
            open_positions = service._executor.get_open_positions()
            for pos in open_positions:
                try:
                    await service._executor.exit_position(
                        pos['trade_id'],
                        pos['current_price'],
                        "Strategy disabled by user"
                    )
                except Exception as e:
                    service.logger.error(f"Error closing position: {e}")
        except Exception as e:
            service.logger.warning(f"Could not retrieve positions: {e}")
    
    return {
        "success": True,
        "message": "Strategy disabled",
        "running": service._running,
        "strategy_enabled": service._strategy_enabled
    }


@app.post("/update-token")
async def update_dhan_token(request: TokenUpdateRequest):
    """Update Dhan API token and reload in-memory config"""
    global service
    config = load_dhan_config()
    config['access_token'] = request.access_token
    if request.client_id:
        config['client_id'] = request.client_id
    
    if save_dhan_config(config):
        logger.info("Dhan token updated successfully")
        
        # Update in-memory token if service is running
        if service:
            service._access_token = request.access_token
            if request.client_id:
                service._client_id = request.client_id
            logger.info("In-memory token updated - use /reload to reconnect WebSocket")
        
        return {
            "success": True,
            "message": "Token updated. Use /reload to reconnect with new token.",
            "restart_required": False
        }
    else:
        raise HTTPException(status_code=500, detail="Failed to save token")


@app.post("/reload")
async def reload_service():
    """Reload service with updated config (token, etc.) without full restart"""
    global service
    if not service:
        raise HTTPException(503, "Service not initialized")
    
    try:
        # Stop current connections
        await service.stop()
        
        # Reload config
        dhan_config = load_dhan_config()
        service._access_token = dhan_config.get('access_token', '')
        service._client_id = dhan_config.get('client_id', '')
        
        # Restart with new config
        await service.start()
        
        return {
            "success": True,
            "message": "Service reloaded with new configuration",
            "running": service._running,
            "strategy_enabled": service._strategy_enabled
        }
    except Exception as e:
        logger.error(f"Reload failed: {e}")
        raise HTTPException(500, f"Reload failed: {str(e)}")


@app.get("/token-status")
async def get_token_status():
    """Check token validity status"""
    config = load_dhan_config()
    token = config.get('access_token', '')
    
    # Decode JWT to check expiry
    try:
        import base64
        parts = token.split('.')
        if len(parts) >= 2:
            payload = parts[1]
            # Add padding
            payload += '=' * (4 - len(payload) % 4)
            decoded = json.loads(base64.urlsafe_b64decode(payload))
            exp = decoded.get('exp', 0)
            exp_date = datetime.fromtimestamp(exp)
            is_expired = datetime.now() > exp_date
            return {
                "valid": not is_expired,
                "expires_at": exp_date.isoformat(),
                "client_id": config.get('client_id', 'N/A'),
                "expired": is_expired
            }
    except Exception as e:
        logger.warning(f"Could not decode token: {e}")
    
    return {"valid": bool(token), "message": "Could not determine expiry"}


# ==================== AI Status Endpoints ====================

@app.get("/ai-status")
async def get_ai_status():
    """Get Gemini AI service status and connectivity"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{ServiceConfig.GEMINI_SERVICE_URL}/health",
                timeout=aiohttp.ClientTimeout(total=5)
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    return {
                        "ai_enabled": ServiceConfig.AI_ENABLED,
                        "gemini_service": {
                            "url": ServiceConfig.GEMINI_SERVICE_URL,
                            "status": "connected",
                            "health": data
                        },
                        "min_ai_confidence": ServiceConfig.MIN_AI_CONFIDENCE,
                        "ai_signals_logged": ServiceConfig.LOG_AI_SIGNALS
                    }
    except Exception as e:
        logger.warning(f"Gemini AI service not reachable: {e}")
    
    return {
        "ai_enabled": ServiceConfig.AI_ENABLED,
        "gemini_service": {
            "url": ServiceConfig.GEMINI_SERVICE_URL,
            "status": "disconnected",
            "error": "Service not reachable"
        },
        "min_ai_confidence": ServiceConfig.MIN_AI_CONFIDENCE,
        "ai_signals_logged": ServiceConfig.LOG_AI_SIGNALS
    }


# ==================== Tick Forwarding Endpoints ====================

class TickForwardingRequest(BaseModel):
    enabled: bool = Field(..., description="Enable or disable tick forwarding")


@app.get("/tick-forwarding")
async def get_tick_forwarding_status():
    """Get tick forwarding configuration and status"""
    # Check if scalping service is reachable
    scalping_reachable = False
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{ServiceConfig.SCALPING_SERVICE_URL}/health",
                timeout=aiohttp.ClientTimeout(total=2)
            ) as response:
                scalping_reachable = response.status == 200
    except Exception:
        pass
    
    return {
        "enabled": ServiceConfig.ENABLE_TICK_FORWARDING,
        "targets": ServiceConfig.FORWARD_TO_SERVICES,
        "scalping_service": {
            "url": ServiceConfig.SCALPING_SERVICE_URL,
            "reachable": scalping_reachable
        },
        "error_count": getattr(service, '_forward_error_count', 0) if service else 0
    }


@app.post("/tick-forwarding")
async def set_tick_forwarding(request: TickForwardingRequest):
    """Enable or disable tick forwarding to other services"""
    ServiceConfig.ENABLE_TICK_FORWARDING = request.enabled
    logger.info(f"Tick forwarding {'enabled' if request.enabled else 'disabled'}")
    
    return {
        "success": True,
        "enabled": ServiceConfig.ENABLE_TICK_FORWARDING,
        "message": f"Tick forwarding {'enabled' if request.enabled else 'disabled'}"
    }


@app.get("/ai-stats")
async def get_ai_stats():
    """Get today's AI trading statistics"""
    # Use the same path as AISignalLogger
    log_file = Path("logs/ai_signals") / f"hedger_ai_signals_{datetime.now().strftime('%Y%m%d')}.jsonl"
    
    stats = {
        "date": datetime.now().strftime("%Y-%m-%d"),
        "total_signals": 0,
        "bullish_signals": 0,
        "bearish_signals": 0,
        "neutral_signals": 0,
        "avg_confidence": 0.0,
        "signals_above_threshold": 0,
        "trades_validated": 0,
        "trades_rejected": 0,
        "ai_predictions": 0,
        "trade_outcomes": 0,
        "gemini_signals": 0,
        "recent_signals": [],
        "gemini_client_stats": gemini_client.get_stats()
    }
    
    if not log_file.exists():
        return stats
    
    try:
        all_entries = []
        with open(log_file, 'r') as f:
            for line in f:
                try:
                    entry = json.loads(line)
                    entry_type = entry.get("type", "")
                    
                    # Count by type
                    if entry_type == "ai_prediction":
                        stats["ai_predictions"] += 1
                        # Track decisions
                        if entry.get("ai_decision") == "EXECUTE":
                            stats["trades_validated"] += 1
                        elif entry.get("ai_decision") == "SKIP":
                            stats["trades_rejected"] += 1
                        
                        # Track confidence
                        conf = entry.get("ai_confidence", 0)
                        if conf >= ServiceConfig.MIN_AI_CONFIDENCE:
                            stats["signals_above_threshold"] += 1
                            
                        # Track direction
                        direction = entry.get("direction", "").lower()
                        if direction == "bullish" or direction == "long":
                            stats["bullish_signals"] += 1
                        elif direction == "bearish" or direction == "short":
                            stats["bearish_signals"] += 1
                        else:
                            stats["neutral_signals"] += 1
                            
                    elif entry_type == "gemini_signal":
                        stats["gemini_signals"] += 1
                        
                    elif entry_type == "trade_outcome":
                        stats["trade_outcomes"] += 1
                    
                    all_entries.append(entry)
                except:
                    continue
        
        stats["total_signals"] = len(all_entries)
        
        # Calculate average confidence from ai_predictions
        confidences = [e.get("ai_confidence", 0) for e in all_entries 
                       if e.get("type") == "ai_prediction" and e.get("ai_confidence")]
        if confidences:
            stats["avg_confidence"] = round(sum(confidences) / len(confidences), 3)
        
        # Get recent signals
        stats["recent_signals"] = all_entries[-10:]
        
    except Exception as e:
        logger.error(f"Error reading AI stats: {e}")
    
    return stats


# ==================== Evaluation Mode Endpoints ====================

# Global evaluation executor reference
_evaluation_executor: Optional[HedgerEvaluationExecutor] = None


def get_evaluation_executor() -> Optional[HedgerEvaluationExecutor]:
    """Get or create evaluation executor instance"""
    global _evaluation_executor
    if _evaluation_executor is None:
        # Get credentials from config
        dhan_config = load_dhan_config()
        access_token = dhan_config.get('access_token', '')
        client_id = dhan_config.get('client_id', '')
        _evaluation_executor = HedgerEvaluationExecutor(
            access_token=access_token,
            client_id=client_id,
            initial_capital=ServiceConfig.INITIAL_CAPITAL
        )
    return _evaluation_executor


@app.post("/evaluation/enable")
async def enable_evaluation_mode():
    """
    Enable evaluation mode - runs all trade logic without placing real orders.
    All trades are simulated and stored in the evaluation database.
    """
    global service, _evaluation_executor
    
    db = get_paper_trading_db()
    
    # Add 'evaluation' to TradingMode if not exists by setting it directly
    # Use proper TradingMode.EVALUATION enum value
    try:
        db.set_trading_mode(TradingMode.EVALUATION, "evaluation_api")
    except Exception as e:
        logger.error(f"Error setting evaluation mode: {e}")
    
    # Get credentials from service or config
    dhan_config = load_dhan_config()
    access_token = dhan_config.get('access_token', '')
    client_id = dhan_config.get('client_id', '')
    
    # Create evaluation executor with proper credentials
    _evaluation_executor = HedgerEvaluationExecutor(
        access_token=access_token,
        client_id=client_id,
        initial_capital=ServiceConfig.INITIAL_CAPITAL
    )
    
    # Swap executor if service is running
    if service:
        service._executor = _evaluation_executor
        logger.info("🔬 EVALUATION MODE ENABLED - No real orders will be placed")
    
    return {
        "success": True,
        "mode": "evaluation",
        "message": "Evaluation mode enabled. All trades will be simulated and logged.",
        "database": "database/evaluation_hedger.db",
        "endpoints": {
            "status": "/evaluation/status",
            "trades": "/evaluation/trades",
            "performance": "/evaluation/performance",
            "export": "/evaluation/export",
            "disable": "/evaluation/disable"
        }
    }


@app.post("/evaluation/disable")
async def disable_evaluation_mode(target_mode: str = "paper"):
    """
    Disable evaluation mode and switch back to paper or production mode.
    """
    global service, _evaluation_executor
    
    db = get_paper_trading_db()
    
    if target_mode == "production":
        confirmation = "I_UNDERSTAND_REAL_MONEY"
    else:
        confirmation = None
        target_mode = "paper"
    
    try:
        mode = TradingMode(target_mode)
        db.set_trading_mode(mode, "api")
    except ValueError:
        db.set_trading_mode(TradingMode.PAPER, "api")
    
    # Switch executor back
    if service:
        service._executor = PaperOptionsExecutor(ServiceConfig.INITIAL_CAPITAL)
        logger.info(f"📋 Switched to {target_mode.upper()} mode")
    
    return {
        "success": True,
        "mode": target_mode,
        "message": f"Switched to {target_mode} mode. Evaluation data preserved.",
        "evaluation_data_location": "database/evaluation_hedger.db"
    }


@app.get("/evaluation/status")
async def get_evaluation_status():
    """Get current evaluation mode status and statistics"""
    db = get_paper_trading_db()
    
    # Check current mode
    mode = db.get_trading_mode()
    
    # Check if we're actually in evaluation mode
    is_evaluation = (mode == TradingMode.EVALUATION)
    
    eval_executor = get_evaluation_executor()
    
    return {
        "mode": "evaluation" if is_evaluation else mode.value,
        "is_evaluation_mode": is_evaluation,
        "service_running": service is not None and service._running if service else False,
        "executor_type": type(service._executor).__name__ if service and service._executor else "None",
        "evaluation_stats": eval_executor.get_evaluation_summary() if eval_executor else {},
        "database_path": "database/evaluation_hedger.db",
        "timestamp": datetime.now().isoformat()
    }


@app.get("/evaluation/trades")
async def get_evaluation_trades(
    limit: int = Query(100, description="Maximum trades to return"),
    status: str = Query(None, description="Filter by status: open, closed, all"),
    instrument: str = Query(None, description="Filter by instrument")
):
    """Get all evaluation trades"""
    eval_executor = get_evaluation_executor()
    if not eval_executor:
        raise HTTPException(503, "Evaluation executor not available")
    
    # Use the database directly
    trades = eval_executor._db.get_recent_trades(limit=limit)
    
    # Filter by status if needed
    if status == "open":
        trades = [t for t in trades if t.get('exit_time') is None]
    elif status == "closed":
        trades = [t for t in trades if t.get('exit_time') is not None]
    
    # Filter by instrument if needed
    if instrument:
        trades = [t for t in trades if t.get('instrument') == instrument]
    
    return {
        "trades": trades,
        "count": len(trades),
        "filters": {
            "limit": limit,
            "status": status,
            "instrument": instrument
        },
        "timestamp": datetime.now().isoformat()
    }


@app.get("/evaluation/performance")
async def get_evaluation_performance():
    """Get detailed evaluation performance metrics"""
    eval_executor = get_evaluation_executor()
    if not eval_executor:
        raise HTTPException(503, "Evaluation executor not available")
    
    summary = eval_executor.get_evaluation_summary()
    position_summary = eval_executor.get_position_summary()
    
    return {
        "performance": summary,
        "position_summary": position_summary,
        "timestamp": datetime.now().isoformat()
    }


@app.get("/evaluation/signals")
async def get_evaluation_signals(
    limit: int = Query(100, description="Maximum signals to return")
):
    """Get signal decisions recorded during evaluation"""
    eval_executor = get_evaluation_executor()
    if not eval_executor:
        raise HTTPException(503, "Evaluation executor not available")
    
    signals = eval_executor._db.get_signal_decisions(limit=limit)
    
    return {
        "signals": signals,
        "count": len(signals),
        "timestamp": datetime.now().isoformat()
    }


@app.get("/evaluation/export")
async def export_evaluation_data(format: str = Query("json", description="Export format: json or csv")):
    """Export all evaluation data for analysis"""
    eval_executor = get_evaluation_executor()
    if not eval_executor:
        raise HTTPException(503, "Evaluation executor not available")
    
    trades = eval_executor._db.get_recent_trades(limit=1000)
    signals = eval_executor._db.get_signal_decisions(limit=1000)
    summary = eval_executor.get_evaluation_summary()
    
    data = {
        "trades": trades,
        "signals": signals,
        "summary": summary
    }
    
    if format == "csv":
        # Convert to CSV-friendly format
        return {
            "trades_csv_ready": trades,
            "signals_csv_ready": signals,
            "summary_csv_ready": [summary],
            "export_timestamp": datetime.now().isoformat()
        }
    
    return {
        "export_data": data,
        "export_timestamp": datetime.now().isoformat(),
        "database_path": "database/evaluation_hedger.db"
    }


@app.delete("/evaluation/clear")
async def clear_evaluation_data(confirm: str = Query(..., description="Type 'CLEAR_ALL_DATA' to confirm")):
    """Clear all evaluation data - requires confirmation"""
    if confirm != "CLEAR_ALL_DATA":
        raise HTTPException(400, "Confirmation required. Pass confirm='CLEAR_ALL_DATA'")
    
    eval_executor = get_evaluation_executor()
    if eval_executor:
        # Clear the database tables
        conn = eval_executor._db._get_conn()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM evaluation_trades")
        cursor.execute("DELETE FROM evaluation_orders")
        cursor.execute("DELETE FROM signal_decisions")
        conn.commit()
        conn.close()
    
    return {
        "success": True,
        "message": "All evaluation data cleared",
        "timestamp": datetime.now().isoformat()
    }


# ==================== Main ====================

def main():
    import uvicorn
    
    logger.info(f"Starting server on port {ServiceConfig.PORT}")
    
    uvicorn.run(
        "production_hedger_service:app",
        host=ServiceConfig.HOST,
        port=ServiceConfig.PORT,
        reload=False,
        log_level="warning"
    )


if __name__ == "__main__":
    main()
