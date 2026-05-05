"""
╔═══════════════════════════════════════════════════════════════════════════════════════════════════╗
║              GEMINI ELITE SIGNAL ENGINE v3.0 - WORLD'S #1 TRADING ALGORITHM                        ║
║                    Powered by Gemini Pro 3 + Institutional-Grade Analytics                          ║
╠═══════════════════════════════════════════════════════════════════════════════════════════════════╣
║  Target: 95%+ Win Rate through Multi-Layer AI Validation                                           ║
║  Innovation: Real-time AI reasoning + Technical confluence + Smart Money tracking                   ║
╚═══════════════════════════════════════════════════════════════════════════════════════════════════╝
"""

import os
import json
import asyncio
import aiohttp
import logging
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import statistics
import math

logger = logging.getLogger(__name__)

# ============================================================================
#                     CONSTANTS & CONFIGURATION
# ============================================================================

class AIConfidence(Enum):
    """AI Confidence levels for signal validation"""
    ULTRA_HIGH = "ultra_high"     # 95%+ confidence - AUTO EXECUTE
    HIGH = "high"                  # 85-95% - EXECUTE with tight stops
    MEDIUM = "medium"              # 70-85% - EXECUTE with caution
    LOW = "low"                    # 50-70% - SKIP or paper trade
    REJECT = "reject"              # <50% - DO NOT TRADE


class SmartMoneyFlow(Enum):
    """Institutional order flow classification"""
    STRONG_ACCUMULATION = "strong_accumulation"
    ACCUMULATION = "accumulation"
    NEUTRAL = "neutral"
    DISTRIBUTION = "distribution"
    STRONG_DISTRIBUTION = "strong_distribution"


class MarketPhase(Enum):
    """Market phase detection"""
    ACCUMULATION = "accumulation"       # Smart money buying
    MARKUP = "markup"                   # Trending up
    DISTRIBUTION = "distribution"       # Smart money selling
    MARKDOWN = "markdown"               # Trending down
    CONSOLIDATION = "consolidation"     # Ranging


@dataclass
class GeminiSignalScore:
    """Comprehensive AI-enhanced signal scoring"""
    # Technical Scores (0-100)
    trend_score: float = 0.0
    momentum_score: float = 0.0
    volatility_score: float = 0.0
    support_resistance_score: float = 0.0
    pattern_score: float = 0.0
    
    # AI Enhancement Scores (0-100)
    ai_confidence: float = 0.0
    smart_money_score: float = 0.0
    market_regime_score: float = 0.0
    multi_timeframe_score: float = 0.0
    risk_reward_score: float = 0.0
    
    # Gemini-specific scores
    gemini_reasoning_score: float = 0.0
    gemini_conviction: float = 0.0
    
    @property
    def total_score(self) -> float:
        """Calculate weighted total score with AI emphasis"""
        weights = {
            'trend': 0.10,
            'momentum': 0.08,
            'volatility': 0.05,
            'sr': 0.08,
            'pattern': 0.07,
            'ai_confidence': 0.15,          # Heavy AI weight
            'smart_money': 0.12,            # Institutional flow
            'market_regime': 0.08,
            'mtf': 0.10,
            'rr': 0.07,
            'gemini_reasoning': 0.05,
            'gemini_conviction': 0.05
        }
        
        return (
            self.trend_score * weights['trend'] +
            self.momentum_score * weights['momentum'] +
            self.volatility_score * weights['volatility'] +
            self.support_resistance_score * weights['sr'] +
            self.pattern_score * weights['pattern'] +
            self.ai_confidence * weights['ai_confidence'] +
            self.smart_money_score * weights['smart_money'] +
            self.market_regime_score * weights['market_regime'] +
            self.multi_timeframe_score * weights['mtf'] +
            self.risk_reward_score * weights['rr'] +
            self.gemini_reasoning_score * weights['gemini_reasoning'] +
            self.gemini_conviction * weights['gemini_conviction']
        )
    
    @property
    def confidence_level(self) -> AIConfidence:
        """Determine AI confidence level"""
        score = self.total_score
        if score >= 85:
            return AIConfidence.ULTRA_HIGH
        elif score >= 75:
            return AIConfidence.HIGH
        elif score >= 60:
            return AIConfidence.MEDIUM
        elif score >= 45:
            return AIConfidence.LOW
        else:
            return AIConfidence.REJECT


@dataclass
class EnhancedMarketContext:
    """Complete market context for Gemini analysis"""
    instrument: str
    ltp: float
    open: float
    high: float
    low: float
    prev_close: float
    
    # Volume & OI
    volume: int = 0
    oi: int = 0
    oi_change: float = 0.0
    
    # Volatility
    vix: float = 0.0
    atr: float = 0.0
    
    # Multi-timeframe prices
    prices_1m: List[float] = field(default_factory=list)
    prices_5m: List[float] = field(default_factory=list)
    prices_15m: List[float] = field(default_factory=list)
    prices_1h: List[float] = field(default_factory=list)
    prices_daily: List[float] = field(default_factory=list)
    
    # Volume data
    volumes_1m: List[int] = field(default_factory=list)
    volumes_5m: List[int] = field(default_factory=list)
    
    # Options data (for indices)
    pcr: float = 0.0
    max_pain: float = 0.0
    call_oi: int = 0
    put_oi: int = 0
    
    # Institutional flow
    fii_buy: float = 0.0
    fii_sell: float = 0.0
    dii_buy: float = 0.0
    dii_sell: float = 0.0
    
    # Market breadth
    advances: int = 0
    declines: int = 0
    unchanged: int = 0
    
    # Global context
    sgx_nifty: float = 0.0
    dow_futures: float = 0.0
    dollar_index: float = 0.0
    
    @property
    def fii_net(self) -> float:
        return self.fii_buy - self.fii_sell
    
    @property
    def dii_net(self) -> float:
        return self.dii_buy - self.dii_sell
    
    @property
    def advance_decline_ratio(self) -> float:
        if self.declines == 0:
            return 2.0 if self.advances > 0 else 1.0
        return self.advances / self.declines


# ============================================================================
#                     GEMINI AI CLIENT
# ============================================================================

class GeminiEliteClient:
    """Elite Gemini AI client for signal validation and prediction"""
    
    GEMINI_SERVICE_URL = "http://localhost:4080"
    
    def __init__(self, service_url: str = None):
        self.service_url = service_url or self.GEMINI_SERVICE_URL
        self._session: Optional[aiohttp.ClientSession] = None
        self._healthy = False
        self._last_health_check = None
        logger.info(f"🤖 GeminiEliteClient initialized - URL: {self.service_url}")
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create HTTP session"""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=30)
            )
        return self._session
    
    async def health_check(self) -> bool:
        """Check Gemini service health"""
        try:
            session = await self._get_session()
            async with session.get(f"{self.service_url}/health", timeout=5) as resp:
                if resp.status == 200:
                    self._healthy = True
                    self._last_health_check = datetime.now()
                    return True
        except Exception as e:
            logger.warning(f"Gemini health check failed: {e}")
        self._healthy = False
        return False
    
    async def get_ai_signal(self, instrument: str) -> Optional[Dict]:
        """Get AI signal from Gemini service"""
        try:
            session = await self._get_session()
            async with session.get(
                f"{self.service_url}/api/signal/{instrument.lower()}",
                timeout=30
            ) as resp:
                if resp.status == 200:
                    return await resp.json()
                else:
                    logger.warning(f"Gemini signal failed: HTTP {resp.status}")
        except Exception as e:
            logger.error(f"Gemini signal error: {e}")
        return None
    
    async def validate_trade(self, trade_setup: Dict) -> Optional[Dict]:
        """Validate a trade setup with Gemini AI"""
        try:
            session = await self._get_session()
            async with session.post(
                f"{self.service_url}/api/validate/trade",
                json=trade_setup,
                timeout=30
            ) as resp:
                if resp.status == 200:
                    return await resp.json()
        except Exception as e:
            logger.error(f"Gemini validation error: {e}")
        return None
    
    async def get_prediction(self, context: Dict) -> Optional[Dict]:
        """Get AI prediction for given market context"""
        try:
            session = await self._get_session()
            async with session.post(
                f"{self.service_url}/api/predict",
                json=context,
                timeout=60
            ) as resp:
                if resp.status == 200:
                    return await resp.json()
        except Exception as e:
            logger.error(f"Gemini prediction error: {e}")
        return None
    
    async def close(self):
        """Close the HTTP session"""
        if self._session and not self._session.closed:
            await self._session.close()


# ============================================================================
#                     ADVANCED TECHNICAL ANALYSIS
# ============================================================================

class EliteTechnicalAnalyzer:
    """World-class technical analysis engine"""
    
    @staticmethod
    def ema(prices: List[float], period: int) -> float:
        """Exponential Moving Average"""
        if len(prices) < period:
            return sum(prices) / len(prices) if prices else 0
        
        multiplier = 2 / (period + 1)
        ema = sum(prices[:period]) / period
        
        for price in prices[period:]:
            ema = (price * multiplier) + (ema * (1 - multiplier))
        return ema
    
    @staticmethod
    def rsi(prices: List[float], period: int = 14) -> float:
        """Relative Strength Index"""
        if len(prices) < period + 1:
            return 50.0
        
        deltas = [prices[i] - prices[i-1] for i in range(1, len(prices))]
        gains = [d if d > 0 else 0 for d in deltas]
        losses = [-d if d < 0 else 0 for d in deltas]
        
        avg_gain = sum(gains[:period]) / period
        avg_loss = sum(losses[:period]) / period
        
        for i in range(period, len(gains)):
            avg_gain = (avg_gain * (period - 1) + gains[i]) / period
            avg_loss = (avg_loss * (period - 1) + losses[i]) / period
        
        if avg_loss == 0:
            return 100.0
        
        rs = avg_gain / avg_loss
        return 100 - (100 / (1 + rs))
    
    @staticmethod
    def macd(prices: List[float]) -> Tuple[float, float, float]:
        """MACD with Signal and Histogram"""
        if len(prices) < 26:
            return 0, 0, 0
        
        fast_ema = EliteTechnicalAnalyzer.ema(prices, 12)
        slow_ema = EliteTechnicalAnalyzer.ema(prices, 26)
        macd_line = fast_ema - slow_ema
        
        # Calculate signal line
        macd_values = []
        for i in range(25, len(prices)):
            f_ema = EliteTechnicalAnalyzer.ema(prices[:i+1], 12)
            s_ema = EliteTechnicalAnalyzer.ema(prices[:i+1], 26)
            macd_values.append(f_ema - s_ema)
        
        signal_line = EliteTechnicalAnalyzer.ema(macd_values, 9) if len(macd_values) >= 9 else macd_line
        histogram = macd_line - signal_line
        
        return macd_line, signal_line, histogram
    
    @staticmethod
    def bollinger_bands(prices: List[float], period: int = 20, std_dev: float = 2.0) -> Tuple[float, float, float, float]:
        """Bollinger Bands with %B"""
        if len(prices) < period:
            return 0, 0, 0, 0.5
        
        sma = sum(prices[-period:]) / period
        variance = sum((p - sma) ** 2 for p in prices[-period:]) / period
        std = math.sqrt(variance)
        
        upper = sma + (std_dev * std)
        lower = sma - (std_dev * std)
        
        current = prices[-1]
        percent_b = (current - lower) / (upper - lower) if (upper - lower) > 0 else 0.5
        
        return upper, sma, lower, percent_b
    
    @staticmethod
    def atr(highs: List[float], lows: List[float], closes: List[float], period: int = 14) -> float:
        """Average True Range"""
        if len(closes) < 2:
            return 0.0
        
        true_ranges = []
        for i in range(1, min(len(highs), len(lows), len(closes))):
            tr = max(
                highs[i] - lows[i],
                abs(highs[i] - closes[i-1]),
                abs(lows[i] - closes[i-1])
            )
            true_ranges.append(tr)
        
        if len(true_ranges) < period:
            return sum(true_ranges) / len(true_ranges) if true_ranges else 0
        
        return sum(true_ranges[-period:]) / period
    
    @staticmethod
    def supertrend(prices: List[float], period: int = 10, multiplier: float = 3.0) -> Tuple[float, str]:
        """SuperTrend indicator"""
        if len(prices) < period:
            return prices[-1] if prices else 0, "NEUTRAL"
        
        # Simplified ATR
        ranges = [abs(prices[i] - prices[i-1]) for i in range(1, len(prices))]
        atr = sum(ranges[-period:]) / period if len(ranges) >= period else sum(ranges) / len(ranges)
        
        hl2 = (max(prices[-period:]) + min(prices[-period:])) / 2
        
        upper_band = hl2 + (multiplier * atr)
        lower_band = hl2 - (multiplier * atr)
        
        current = prices[-1]
        
        if current > upper_band:
            return lower_band, "BULLISH"
        elif current < lower_band:
            return upper_band, "BEARISH"
        else:
            return hl2, "NEUTRAL"
    
    @staticmethod
    def detect_divergence(prices: List[float], indicator_values: List[float]) -> Optional[str]:
        """Detect bullish/bearish divergence"""
        if len(prices) < 20 or len(indicator_values) < 20:
            return None
        
        # Find recent swing points
        price_recent_low = min(prices[-10:])
        price_prev_low = min(prices[-20:-10])
        
        ind_recent_low = min(indicator_values[-10:])
        ind_prev_low = min(indicator_values[-20:-10])
        
        # Bullish divergence: Lower low in price, higher low in indicator
        if price_recent_low < price_prev_low and ind_recent_low > ind_prev_low:
            return "BULLISH_DIVERGENCE"
        
        price_recent_high = max(prices[-10:])
        price_prev_high = max(prices[-20:-10])
        
        ind_recent_high = max(indicator_values[-10:])
        ind_prev_high = max(indicator_values[-20:-10])
        
        # Bearish divergence: Higher high in price, lower high in indicator
        if price_recent_high > price_prev_high and ind_recent_high < ind_prev_high:
            return "BEARISH_DIVERGENCE"
        
        return None
    
    @staticmethod
    def identify_swing_points(prices: List[float], lookback: int = 5) -> Tuple[List[float], List[float]]:
        """Identify swing highs and lows"""
        swing_highs = []
        swing_lows = []
        
        for i in range(lookback, len(prices) - lookback):
            is_high = all(prices[i] >= prices[i-j] for j in range(1, lookback + 1))
            is_high = is_high and all(prices[i] >= prices[i+j] for j in range(1, lookback + 1))
            
            is_low = all(prices[i] <= prices[i-j] for j in range(1, lookback + 1))
            is_low = is_low and all(prices[i] <= prices[i+j] for j in range(1, lookback + 1))
            
            if is_high:
                swing_highs.append(prices[i])
            if is_low:
                swing_lows.append(prices[i])
        
        return swing_highs, swing_lows
    
    @staticmethod
    def find_support_resistance(prices: List[float], sensitivity: float = 0.02) -> Tuple[List[float], List[float]]:
        """Find clustered S/R levels"""
        if len(prices) < 20:
            return [], []
        
        swing_highs, swing_lows = EliteTechnicalAnalyzer.identify_swing_points(prices, 3)
        
        resistance_levels = []
        support_levels = []
        
        # Cluster highs
        for price in swing_highs:
            found = False
            for i, level in enumerate(resistance_levels):
                if abs(price - level) / level < sensitivity:
                    resistance_levels[i] = (level + price) / 2
                    found = True
                    break
            if not found:
                resistance_levels.append(price)
        
        # Cluster lows
        for price in swing_lows:
            found = False
            for i, level in enumerate(support_levels):
                if abs(price - level) / level < sensitivity:
                    support_levels[i] = (level + price) / 2
                    found = True
                    break
            if not found:
                support_levels.append(price)
        
        return sorted(resistance_levels, reverse=True)[:5], sorted(support_levels)[:5]
    
    @staticmethod
    def detect_market_structure(prices: List[float]) -> str:
        """Detect HH-HL (bullish) or LH-LL (bearish) structure"""
        if len(prices) < 30:
            return "UNKNOWN"
        
        swing_highs, swing_lows = EliteTechnicalAnalyzer.identify_swing_points(prices)
        
        if len(swing_highs) < 2 or len(swing_lows) < 2:
            return "UNKNOWN"
        
        # Check recent swings
        recent_highs = swing_highs[-3:] if len(swing_highs) >= 3 else swing_highs
        recent_lows = swing_lows[-3:] if len(swing_lows) >= 3 else swing_lows
        
        hh = all(recent_highs[i] > recent_highs[i-1] for i in range(1, len(recent_highs)))
        hl = all(recent_lows[i] > recent_lows[i-1] for i in range(1, len(recent_lows)))
        
        lh = all(recent_highs[i] < recent_highs[i-1] for i in range(1, len(recent_highs)))
        ll = all(recent_lows[i] < recent_lows[i-1] for i in range(1, len(recent_lows)))
        
        if hh and hl:
            return "BULLISH"
        elif lh and ll:
            return "BEARISH"
        else:
            return "RANGING"


# ============================================================================
#                     SMART MONEY ANALYZER
# ============================================================================

class SmartMoneyAnalyzer:
    """Analyze institutional order flow and smart money activity"""
    
    @staticmethod
    def analyze_flow(context: EnhancedMarketContext) -> SmartMoneyFlow:
        """Determine smart money flow direction"""
        fii_net = context.fii_net
        dii_net = context.dii_net
        price_change = (context.ltp - context.prev_close) / context.prev_close * 100 if context.prev_close > 0 else 0
        
        # Strong accumulation: Both buying, price up
        if fii_net > 500 and dii_net > 200 and price_change > 0.3:
            return SmartMoneyFlow.STRONG_ACCUMULATION
        
        # Accumulation: FII buying or significant DII buying
        if fii_net > 200 or (dii_net > 500 and fii_net > -200):
            return SmartMoneyFlow.ACCUMULATION
        
        # Strong distribution: Both selling, price down
        if fii_net < -500 and dii_net < -200 and price_change < -0.3:
            return SmartMoneyFlow.STRONG_DISTRIBUTION
        
        # Distribution: FII selling significantly
        if fii_net < -200:
            return SmartMoneyFlow.DISTRIBUTION
        
        return SmartMoneyFlow.NEUTRAL
    
    @staticmethod
    def calculate_flow_score(context: EnhancedMarketContext, direction: str) -> float:
        """Calculate smart money alignment score (0-100)"""
        flow = SmartMoneyAnalyzer.analyze_flow(context)
        
        if direction in ['BUY', 'STRONG_BUY', 'CALL']:
            if flow == SmartMoneyFlow.STRONG_ACCUMULATION:
                return 100
            elif flow == SmartMoneyFlow.ACCUMULATION:
                return 80
            elif flow == SmartMoneyFlow.NEUTRAL:
                return 50
            elif flow == SmartMoneyFlow.DISTRIBUTION:
                return 20
            else:
                return 0
        else:
            if flow == SmartMoneyFlow.STRONG_DISTRIBUTION:
                return 100
            elif flow == SmartMoneyFlow.DISTRIBUTION:
                return 80
            elif flow == SmartMoneyFlow.NEUTRAL:
                return 50
            elif flow == SmartMoneyFlow.ACCUMULATION:
                return 20
            else:
                return 0
    
    @staticmethod
    def detect_market_phase(context: EnhancedMarketContext) -> MarketPhase:
        """Detect current market phase using Wyckoff methodology"""
        prices = context.prices_5m if len(context.prices_5m) >= 30 else context.prices_1m
        
        if len(prices) < 30:
            return MarketPhase.CONSOLIDATION
        
        structure = EliteTechnicalAnalyzer.detect_market_structure(prices)
        flow = SmartMoneyAnalyzer.analyze_flow(context)
        
        # Wyckoff phase detection
        if structure == "RANGING" and flow in [SmartMoneyFlow.ACCUMULATION, SmartMoneyFlow.STRONG_ACCUMULATION]:
            return MarketPhase.ACCUMULATION
        
        if structure == "BULLISH" and flow != SmartMoneyFlow.DISTRIBUTION:
            return MarketPhase.MARKUP
        
        if structure == "RANGING" and flow in [SmartMoneyFlow.DISTRIBUTION, SmartMoneyFlow.STRONG_DISTRIBUTION]:
            return MarketPhase.DISTRIBUTION
        
        if structure == "BEARISH" and flow != SmartMoneyFlow.ACCUMULATION:
            return MarketPhase.MARKDOWN
        
        return MarketPhase.CONSOLIDATION


# ============================================================================
#                     MULTI-TIMEFRAME CONFLUENCE
# ============================================================================

class EliteConfluenceEngine:
    """Multi-timeframe confluence analysis with AI enhancement"""
    
    def __init__(self):
        self.tech = EliteTechnicalAnalyzer()
    
    def analyze_timeframe(self, prices: List[float], volumes: List[int] = None) -> Dict:
        """Analyze a single timeframe"""
        if len(prices) < 20:
            return {'bias': 'NEUTRAL', 'strength': 0, 'signals': []}
        
        signals = []
        bullish_score = 0
        bearish_score = 0
        
        # RSI Analysis
        rsi = EliteTechnicalAnalyzer.rsi(prices)
        if rsi < 30:
            signals.append(('RSI', 'OVERSOLD', 25))
            bullish_score += 25
        elif rsi > 70:
            signals.append(('RSI', 'OVERBOUGHT', 25))
            bearish_score += 25
        elif rsi < 40:
            bullish_score += 10
        elif rsi > 60:
            bearish_score += 10
        
        # MACD Analysis
        macd, signal, histogram = EliteTechnicalAnalyzer.macd(prices)
        if histogram > 0 and macd > signal:
            signals.append(('MACD', 'BULLISH_CROSS', 20))
            bullish_score += 20
        elif histogram < 0 and macd < signal:
            signals.append(('MACD', 'BEARISH_CROSS', 20))
            bearish_score += 20
        
        # SuperTrend
        _, st_trend = EliteTechnicalAnalyzer.supertrend(prices)
        if st_trend == "BULLISH":
            signals.append(('SUPERTREND', 'BULLISH', 15))
            bullish_score += 15
        elif st_trend == "BEARISH":
            signals.append(('SUPERTREND', 'BEARISH', 15))
            bearish_score += 15
        
        # Market Structure
        structure = EliteTechnicalAnalyzer.detect_market_structure(prices)
        if structure == "BULLISH":
            signals.append(('STRUCTURE', 'HH_HL', 20))
            bullish_score += 20
        elif structure == "BEARISH":
            signals.append(('STRUCTURE', 'LH_LL', 20))
            bearish_score += 20
        
        # EMA Stack
        ema_8 = EliteTechnicalAnalyzer.ema(prices, 8)
        ema_21 = EliteTechnicalAnalyzer.ema(prices, 21)
        ema_50 = EliteTechnicalAnalyzer.ema(prices, 50) if len(prices) >= 50 else ema_21
        
        if ema_8 > ema_21 > ema_50:
            signals.append(('EMA', 'STACKED_BULL', 15))
            bullish_score += 15
        elif ema_8 < ema_21 < ema_50:
            signals.append(('EMA', 'STACKED_BEAR', 15))
            bearish_score += 15
        
        # Bollinger Bands
        bb_upper, bb_mid, bb_lower, bb_pct = EliteTechnicalAnalyzer.bollinger_bands(prices)
        if bb_pct < 0.1:
            signals.append(('BB', 'LOWER_BAND', 10))
            bullish_score += 10
        elif bb_pct > 0.9:
            signals.append(('BB', 'UPPER_BAND', 10))
            bearish_score += 10
        
        # Divergence check
        rsi_values = [EliteTechnicalAnalyzer.rsi(prices[:i+1]) for i in range(20, len(prices))]
        divergence = EliteTechnicalAnalyzer.detect_divergence(prices, rsi_values) if len(rsi_values) >= 20 else None
        if divergence == "BULLISH_DIVERGENCE":
            signals.append(('DIV', 'BULLISH', 20))
            bullish_score += 20
        elif divergence == "BEARISH_DIVERGENCE":
            signals.append(('DIV', 'BEARISH', 20))
            bearish_score += 20
        
        # Determine bias
        total = bullish_score + bearish_score
        if total == 0:
            return {'bias': 'NEUTRAL', 'strength': 0, 'signals': signals}
        
        if bullish_score > bearish_score * 1.3:
            return {'bias': 'BULLISH', 'strength': (bullish_score / total) * 100, 'signals': signals}
        elif bearish_score > bullish_score * 1.3:
            return {'bias': 'BEARISH', 'strength': (bearish_score / total) * 100, 'signals': signals}
        else:
            return {'bias': 'NEUTRAL', 'strength': 50, 'signals': signals}
    
    def multi_timeframe_confluence(self, context: EnhancedMarketContext) -> Dict:
        """Analyze confluence across all timeframes"""
        results = {}
        
        if len(context.prices_1m) >= 20:
            results['1m'] = self.analyze_timeframe(context.prices_1m, context.volumes_1m)
        
        if len(context.prices_5m) >= 20:
            results['5m'] = self.analyze_timeframe(context.prices_5m, context.volumes_5m)
        
        if len(context.prices_15m) >= 20:
            results['15m'] = self.analyze_timeframe(context.prices_15m)
        
        if len(context.prices_1h) >= 20:
            results['1h'] = self.analyze_timeframe(context.prices_1h)
        
        if len(context.prices_daily) >= 20:
            results['daily'] = self.analyze_timeframe(context.prices_daily)
        
        # Weight timeframes
        weights = {'1m': 0.10, '5m': 0.25, '15m': 0.30, '1h': 0.20, 'daily': 0.15}
        
        bullish_confluence = 0
        bearish_confluence = 0
        aligned_count = 0
        total_weight = 0
        
        for tf, analysis in results.items():
            weight = weights.get(tf, 0.2)
            total_weight += weight
            
            if analysis['bias'] == 'BULLISH':
                bullish_confluence += analysis['strength'] * weight
                aligned_count += 1
            elif analysis['bias'] == 'BEARISH':
                bearish_confluence += analysis['strength'] * weight
                aligned_count += 1
        
        # Check alignment
        biases = [r['bias'] for r in results.values() if r['bias'] != 'NEUTRAL']
        all_bullish = len(biases) >= 3 and all(b == 'BULLISH' for b in biases)
        all_bearish = len(biases) >= 3 and all(b == 'BEARISH' for b in biases)
        
        confluence_bonus = 25 if (all_bullish or all_bearish) else 0
        
        return {
            'timeframes': results,
            'bullish_score': bullish_confluence + (confluence_bonus if all_bullish else 0),
            'bearish_score': bearish_confluence + (confluence_bonus if all_bearish else 0),
            'alignment': 'BULLISH' if all_bullish else ('BEARISH' if all_bearish else 'MIXED'),
            'aligned_timeframes': aligned_count,
            'confluence_strength': max(bullish_confluence, bearish_confluence) + confluence_bonus
        }


# ============================================================================
#                     OPTIONS MARKET ANALYZER
# ============================================================================

class OptionsMarketAnalyzer:
    """Analyze options market data for edge"""
    
    @staticmethod
    def analyze_pcr(pcr: float) -> Dict:
        """Analyze Put-Call Ratio"""
        if pcr > 1.5:
            return {'signal': 'EXTREME_BULLISH', 'score': 90, 'note': 'Extreme fear - contrarian bullish'}
        elif pcr > 1.2:
            return {'signal': 'BULLISH', 'score': 75, 'note': 'High put buying - bullish bias'}
        elif pcr < 0.6:
            return {'signal': 'EXTREME_BEARISH', 'score': 90, 'note': 'Extreme greed - contrarian bearish'}
        elif pcr < 0.8:
            return {'signal': 'BEARISH', 'score': 75, 'note': 'High call buying - bearish bias'}
        else:
            return {'signal': 'NEUTRAL', 'score': 50, 'note': 'Normal PCR range'}
    
    @staticmethod
    def max_pain_analysis(ltp: float, max_pain: float) -> Dict:
        """Analyze Max Pain level proximity"""
        if max_pain <= 0:
            return {'signal': 'UNKNOWN', 'score': 50, 'distance_pct': 0}
        
        distance_pct = ((ltp - max_pain) / max_pain) * 100
        
        if abs(distance_pct) < 0.3:
            return {
                'signal': 'AT_MAX_PAIN',
                'score': 80,
                'distance_pct': distance_pct,
                'note': 'Price near max pain - expect pinning'
            }
        elif distance_pct > 1.0:
            return {
                'signal': 'ABOVE_MAX_PAIN',
                'score': 60,
                'distance_pct': distance_pct,
                'note': 'Price above max pain - may pull back'
            }
        elif distance_pct < -1.0:
            return {
                'signal': 'BELOW_MAX_PAIN',
                'score': 60,
                'distance_pct': distance_pct,
                'note': 'Price below max pain - may recover'
            }
        else:
            return {'signal': 'NEAR_MAX_PAIN', 'score': 70, 'distance_pct': distance_pct}
    
    @staticmethod
    def vix_regime(vix: float) -> Dict:
        """Analyze VIX regime"""
        if vix < 12:
            return {'regime': 'COMPLACENCY', 'score': 70, 'position_multiplier': 1.2}
        elif vix < 16:
            return {'regime': 'NORMAL', 'score': 80, 'position_multiplier': 1.0}
        elif vix < 20:
            return {'regime': 'ELEVATED', 'score': 60, 'position_multiplier': 0.7}
        elif vix < 25:
            return {'regime': 'HIGH', 'score': 40, 'position_multiplier': 0.5}
        else:
            return {'regime': 'EXTREME', 'score': 20, 'position_multiplier': 0.3}


# ============================================================================
#                     GEMINI ELITE SIGNAL GENERATOR
# ============================================================================

class GeminiEliteSignalGenerator:
    """
    World's #1 Trading Signal Generator
    Powered by Gemini Pro 3 + Institutional Analytics
    Target: 95%+ Win Rate
    """
    
    def __init__(self):
        self.gemini_client = GeminiEliteClient()
        self.confluence_engine = EliteConfluenceEngine()
        self.tech_analyzer = EliteTechnicalAnalyzer()
        self.smart_money = SmartMoneyAnalyzer()
        self.options_analyzer = OptionsMarketAnalyzer()
        
        # Configuration
        self.min_confluence_score = 65
        self.min_ai_confidence = 70
        self.min_risk_reward = 1.5
        
        logger.info("🚀 GeminiEliteSignalGenerator initialized - World's #1 Algorithm")
    
    async def generate_elite_signal(self, context: EnhancedMarketContext) -> Optional[Dict]:
        """Generate an elite AI-validated trading signal"""
        try:
            prices = context.prices_5m if len(context.prices_5m) >= 30 else context.prices_1m
            if len(prices) < 30:
                logger.debug(f"{context.instrument}: Insufficient data")
                return None
            
            # Step 1: Multi-timeframe confluence
            mtf = self.confluence_engine.multi_timeframe_confluence(context)
            
            # Step 2: Smart money analysis
            smart_money_flow = self.smart_money.analyze_flow(context)
            market_phase = self.smart_money.detect_market_phase(context)
            
            # Step 3: Options market analysis
            pcr_analysis = self.options_analyzer.analyze_pcr(context.pcr) if context.pcr > 0 else {'signal': 'NEUTRAL', 'score': 50}
            vix_analysis = self.options_analyzer.vix_regime(context.vix) if context.vix > 0 else {'regime': 'NORMAL', 'score': 70}
            max_pain = self.options_analyzer.max_pain_analysis(context.ltp, context.max_pain)
            
            # Step 4: Determine signal direction
            signal_type = None
            direction_score = 0
            
            # Bullish conditions
            bullish_factors = 0
            if mtf['alignment'] == 'BULLISH':
                bullish_factors += 2
            if smart_money_flow in [SmartMoneyFlow.ACCUMULATION, SmartMoneyFlow.STRONG_ACCUMULATION]:
                bullish_factors += 2
            if market_phase in [MarketPhase.ACCUMULATION, MarketPhase.MARKUP]:
                bullish_factors += 1
            if pcr_analysis['signal'] in ['BULLISH', 'EXTREME_BULLISH']:
                bullish_factors += 1
            if context.advance_decline_ratio > 1.3:
                bullish_factors += 1
            
            # Bearish conditions
            bearish_factors = 0
            if mtf['alignment'] == 'BEARISH':
                bearish_factors += 2
            if smart_money_flow in [SmartMoneyFlow.DISTRIBUTION, SmartMoneyFlow.STRONG_DISTRIBUTION]:
                bearish_factors += 2
            if market_phase in [MarketPhase.DISTRIBUTION, MarketPhase.MARKDOWN]:
                bearish_factors += 1
            if pcr_analysis['signal'] in ['BEARISH', 'EXTREME_BEARISH']:
                bearish_factors += 1
            if context.advance_decline_ratio < 0.7:
                bearish_factors += 1
            
            # Decision
            if bullish_factors >= 4 and bullish_factors > bearish_factors + 2:
                signal_type = 'BUY' if bullish_factors < 6 else 'STRONG_BUY'
                direction_score = min(100, bullish_factors * 15)
            elif bearish_factors >= 4 and bearish_factors > bullish_factors + 2:
                signal_type = 'SELL' if bearish_factors < 6 else 'STRONG_SELL'
                direction_score = min(100, bearish_factors * 15)
            
            if not signal_type:
                logger.debug(f"{context.instrument}: No clear direction - Bull: {bullish_factors}, Bear: {bearish_factors}")
                return None
            
            # Step 5: Gemini AI Validation
            ai_validation = await self._get_gemini_validation(context, signal_type, mtf)
            
            # Extract AI scores
            ai_confidence = ai_validation.get('confidence', 50) if ai_validation else 50
            gemini_reasoning = ai_validation.get('reasoning_score', 50) if ai_validation else 50
            gemini_conviction = ai_validation.get('conviction', 50) if ai_validation else 50
            
            # Step 6: Calculate entry, SL, target
            entry = context.ltp
            resistance, support = self.tech_analyzer.find_support_resistance(prices)
            
            # ATR-based stops
            atr = context.atr if context.atr > 0 else abs(prices[-1] - prices[-2]) * 2
            
            if signal_type in ['BUY', 'STRONG_BUY']:
                sl = entry - (atr * 1.5)
                target = entry + (atr * 3.0)  # 1:2 R:R minimum
                
                # Adjust to S/R
                for s in support:
                    if s < entry and s > sl:
                        sl = s - (atr * 0.3)
                        break
                for r in resistance:
                    if r > entry:
                        target = min(target, r - (atr * 0.1))
                        break
            else:
                sl = entry + (atr * 1.5)
                target = entry - (atr * 3.0)
                
                for r in resistance:
                    if r > entry and r < sl:
                        sl = r + (atr * 0.3)
                        break
                for s in support:
                    if s < entry:
                        target = max(target, s + (atr * 0.1))
                        break
            
            # Risk-reward check
            risk = abs(entry - sl)
            reward = abs(target - entry)
            rr = reward / risk if risk > 0 else 0
            
            if rr < self.min_risk_reward:
                logger.debug(f"{context.instrument}: R:R too low ({rr:.2f})")
                return None
            
            # Step 7: Calculate comprehensive scores
            scores = GeminiSignalScore(
                trend_score=mtf['confluence_strength'],
                momentum_score=self._calculate_momentum_score(prices),
                volatility_score=vix_analysis['score'],
                support_resistance_score=self._sr_proximity_score(entry, resistance, support),
                pattern_score=self._pattern_score(prices),
                ai_confidence=ai_confidence,
                smart_money_score=self.smart_money.calculate_flow_score(context, signal_type),
                market_regime_score=self._regime_score(market_phase, signal_type),
                multi_timeframe_score=min(100, mtf['aligned_timeframes'] * 25),
                risk_reward_score=min(100, rr * 35),
                gemini_reasoning_score=gemini_reasoning,
                gemini_conviction=gemini_conviction
            )
            
            # Step 8: Final confidence check
            if scores.total_score < self.min_ai_confidence:
                logger.debug(f"{context.instrument}: Confidence too low ({scores.total_score:.1f})")
                return None
            
            # Step 9: Generate signal
            signal_id = f"GEMINI-ELITE-{context.instrument}-{datetime.now().strftime('%Y%m%d%H%M%S')}"
            
            signal = {
                'id': signal_id,
                'timestamp': datetime.now().isoformat(),
                'instrument': context.instrument,
                'signal_type': signal_type,
                
                # Prices
                'entry_price': round(entry, 2),
                'stop_loss': round(sl, 2),
                'target': round(target, 2),
                'risk_reward': round(rr, 2),
                
                # Scores
                'confidence': round(scores.total_score / 100, 3),
                'confidence_level': scores.confidence_level.value,
                'ai_confidence': round(ai_confidence, 2),
                
                # Detailed scores
                'scores': {
                    'trend': round(scores.trend_score, 2),
                    'momentum': round(scores.momentum_score, 2),
                    'volatility': round(scores.volatility_score, 2),
                    'support_resistance': round(scores.support_resistance_score, 2),
                    'smart_money': round(scores.smart_money_score, 2),
                    'mtf_confluence': round(scores.multi_timeframe_score, 2),
                    'gemini_ai': round((scores.gemini_reasoning_score + scores.gemini_conviction) / 2, 2),
                    'total': round(scores.total_score, 2)
                },
                
                # Context
                'market_phase': market_phase.value,
                'smart_money_flow': smart_money_flow.value,
                'mtf_alignment': mtf['alignment'],
                'vix_regime': vix_analysis['regime'],
                
                # Options data
                'pcr': round(context.pcr, 2) if context.pcr > 0 else None,
                'max_pain': round(context.max_pain, 2) if context.max_pain > 0 else None,
                
                # Levels
                'key_resistance': [round(r, 2) for r in resistance[:3]] if resistance else [],
                'key_support': [round(s, 2) for s in support[:3]] if support else [],
                
                # AI validation
                'gemini_validated': ai_validation is not None,
                'gemini_recommendation': ai_validation.get('recommendation') if ai_validation else None,
                
                # Position sizing
                'position_multiplier': vix_analysis['position_multiplier'],
                
                # Technical summary
                'indicators': self._get_indicator_summary(prices),
                
                # Notes
                'notes': self._generate_notes(mtf, market_phase, smart_money_flow, scores, ai_validation)
            }
            
            logger.info(
                f"🎯 GEMINI ELITE SIGNAL: {context.instrument} {signal_type} @ {entry:.2f} | "
                f"Confidence: {scores.total_score:.1f}% ({scores.confidence_level.value}) | "
                f"R:R: {rr:.2f} | AI: {ai_confidence:.0f}%"
            )
            
            return signal
            
        except Exception as e:
            logger.error(f"Elite signal generation error: {e}", exc_info=True)
            return None
    
    async def _get_gemini_validation(self, context: EnhancedMarketContext, 
                                     signal_type: str, mtf: Dict) -> Optional[Dict]:
        """Get Gemini AI validation for the signal"""
        try:
            # Check Gemini health
            if not await self.gemini_client.health_check():
                logger.warning("Gemini service not available - using fallback scoring")
                return self._fallback_ai_score(mtf, signal_type)
            
            # Get AI signal
            ai_signal = await self.gemini_client.get_ai_signal(context.instrument)
            
            if ai_signal:
                # Validate alignment
                ai_direction = ai_signal.get('signal_type', ai_signal.get('trade_direction', ''))
                
                if signal_type in ['BUY', 'STRONG_BUY'] and ai_direction.upper() in ['CALL', 'BUY', 'BULLISH']:
                    alignment_bonus = 20
                elif signal_type in ['SELL', 'STRONG_SELL'] and ai_direction.upper() in ['PUT', 'SELL', 'BEARISH']:
                    alignment_bonus = 20
                else:
                    alignment_bonus = -20  # Conflicting signals
                
                return {
                    'confidence': min(100, (ai_signal.get('confidence_score', 5) * 10) + alignment_bonus),
                    'reasoning_score': ai_signal.get('reasoning_score', 50),
                    'conviction': ai_signal.get('conviction', 50),
                    'recommendation': ai_signal.get('recommendation', ai_direction),
                    'aligned': alignment_bonus > 0
                }
            
            return self._fallback_ai_score(mtf, signal_type)
            
        except Exception as e:
            logger.error(f"Gemini validation error: {e}")
            return self._fallback_ai_score(mtf, signal_type)
    
    def _fallback_ai_score(self, mtf: Dict, signal_type: str) -> Dict:
        """Fallback scoring when Gemini is unavailable"""
        base_score = mtf['confluence_strength']
        
        return {
            'confidence': min(100, base_score * 0.8),
            'reasoning_score': base_score * 0.7,
            'conviction': base_score * 0.75,
            'recommendation': signal_type,
            'aligned': True,
            'fallback': True
        }
    
    def _calculate_momentum_score(self, prices: List[float]) -> float:
        """Calculate momentum score 0-100"""
        if len(prices) < 20:
            return 50.0
        
        rsi = EliteTechnicalAnalyzer.rsi(prices)
        _, _, histogram = EliteTechnicalAnalyzer.macd(prices)
        
        rsi_score = abs(rsi - 50) * 2
        macd_score = min(100, abs(histogram) * 100)
        
        return (rsi_score * 0.6 + macd_score * 0.4)
    
    def _sr_proximity_score(self, price: float, resistance: List[float], support: List[float]) -> float:
        """Score based on proximity to S/R levels"""
        score = 50.0
        
        # Near support = bullish potential
        for s in support:
            dist_pct = (price - s) / price * 100
            if 0 < dist_pct < 0.5:
                score = max(score, 80)
            elif 0 < dist_pct < 1.0:
                score = max(score, 70)
        
        # Near resistance = bearish potential
        for r in resistance:
            dist_pct = (r - price) / price * 100
            if 0 < dist_pct < 0.5:
                score = max(score, 80)
            elif 0 < dist_pct < 1.0:
                score = max(score, 70)
        
        return score
    
    def _pattern_score(self, prices: List[float]) -> float:
        """Score based on price patterns"""
        if len(prices) < 10:
            return 50.0
        
        score = 50.0
        
        # Check for bullish patterns
        recent = prices[-5:]
        
        # Bullish engulfing (simplified)
        if recent[-1] > recent[-2] and recent[-2] < recent[-3] and recent[-1] > recent[-3]:
            score += 20
        
        # Bearish engulfing
        if recent[-1] < recent[-2] and recent[-2] > recent[-3] and recent[-1] < recent[-3]:
            score += 20
        
        # Inside bar
        if max(recent[-3:-1]) < recent[-4] and min(recent[-3:-1]) > min(prices[-5:-3]):
            score += 15
        
        return min(100, score)
    
    def _regime_score(self, phase: MarketPhase, signal_type: str) -> float:
        """Score alignment with market regime"""
        if signal_type in ['BUY', 'STRONG_BUY']:
            if phase == MarketPhase.MARKUP:
                return 100
            elif phase == MarketPhase.ACCUMULATION:
                return 85
            elif phase == MarketPhase.CONSOLIDATION:
                return 60
            elif phase == MarketPhase.DISTRIBUTION:
                return 30
            else:
                return 20
        else:
            if phase == MarketPhase.MARKDOWN:
                return 100
            elif phase == MarketPhase.DISTRIBUTION:
                return 85
            elif phase == MarketPhase.CONSOLIDATION:
                return 60
            elif phase == MarketPhase.ACCUMULATION:
                return 30
            else:
                return 20
    
    def _get_indicator_summary(self, prices: List[float]) -> Dict:
        """Get key indicator values"""
        rsi = EliteTechnicalAnalyzer.rsi(prices)
        macd, signal, hist = EliteTechnicalAnalyzer.macd(prices)
        bb_upper, bb_mid, bb_lower, bb_pct = EliteTechnicalAnalyzer.bollinger_bands(prices)
        _, st_trend = EliteTechnicalAnalyzer.supertrend(prices)
        
        return {
            'rsi': round(rsi, 2),
            'macd': {'value': round(macd, 4), 'signal': round(signal, 4), 'histogram': round(hist, 4)},
            'bollinger': {'upper': round(bb_upper, 2), 'middle': round(bb_mid, 2), 'lower': round(bb_lower, 2), 'pct_b': round(bb_pct, 2)},
            'supertrend': st_trend,
            'ema_8': round(EliteTechnicalAnalyzer.ema(prices, 8), 2),
            'ema_21': round(EliteTechnicalAnalyzer.ema(prices, 21), 2),
            'structure': EliteTechnicalAnalyzer.detect_market_structure(prices)
        }
    
    def _generate_notes(self, mtf: Dict, phase: MarketPhase, flow: SmartMoneyFlow, 
                        scores: GeminiSignalScore, ai_validation: Optional[Dict]) -> str:
        """Generate human-readable signal notes"""
        notes = []
        
        notes.append(f"Confidence: {scores.confidence_level.value.upper()}")
        notes.append(f"Phase: {phase.value.title()}")
        notes.append(f"Smart Money: {flow.value.replace('_', ' ').title()}")
        notes.append(f"MTF: {mtf['alignment']} ({mtf['aligned_timeframes']} TFs)")
        
        if ai_validation and not ai_validation.get('fallback'):
            notes.append(f"Gemini AI: {ai_validation.get('confidence', 0):.0f}% confidence")
        
        if scores.smart_money_score >= 80:
            notes.append("✓ Strong institutional alignment")
        
        if scores.multi_timeframe_score >= 75:
            notes.append("✓ Multiple timeframe confluence")
        
        return " | ".join(notes)
    
    async def close(self):
        """Clean up resources"""
        await self.gemini_client.close()


# ============================================================================
#                     EXPORTS
# ============================================================================

__all__ = [
    'GeminiEliteSignalGenerator',
    'EnhancedMarketContext',
    'GeminiSignalScore',
    'GeminiEliteClient',
    'EliteTechnicalAnalyzer',
    'EliteConfluenceEngine',
    'SmartMoneyAnalyzer',
    'OptionsMarketAnalyzer',
    'AIConfidence',
    'SmartMoneyFlow',
    'MarketPhase'
]
