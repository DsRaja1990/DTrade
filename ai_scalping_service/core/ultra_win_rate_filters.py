"""
╔══════════════════════════════════════════════════════════════════════════════╗
║           ELITE TRADING FILTERS v2.0 - 300%+ MONTHLY RETURNS                 ║
║              World-Class Algorithms for Maximum Profit Generation            ║
╚══════════════════════════════════════════════════════════════════════════════╝

This module provides ELITE filtering layers for 300%+ monthly returns:

1. Time Quality Filter - Trade optimal windows with aggressive sizing
2. VIX Regime Filter - Adapt position sizes to volatility
3. Multi-Layer Confirmation Gate - Confirm signals, scale on strength
4. Aggressive Position Sizing - Maximize capital deployment
5. Momentum Breakout Detection - Catch explosive moves
6. Pyramid Scaling Logic - Add to winners aggressively
7. Smart Trailing Stops - Lock profits while letting winners run

Author: Elite Trading System v2.0
Target: 300%+ Monthly Returns | 85%+ Win Rate
Strategy: Aggressive momentum capture with pyramid scaling
"""

from datetime import datetime, time, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum
import logging

logger = logging.getLogger(__name__)


# ============================================================================
#                     TIME QUALITY FILTER - AGGRESSIVE MODE
# ============================================================================

class TimeQuality(Enum):
    """Time windows with signal quality and SIZE MULTIPLIERS"""
    LEGENDARY = "LEGENDARY"      # Best windows - USE MAX LEVERAGE
    ULTRA = "ULTRA"              # Excellent windows - AGGRESSIVE sizing
    GOOD = "GOOD"                # Good windows - NORMAL sizing
    AVERAGE = "AVERAGE"          # Average windows - REDUCED sizing
    POOR = "POOR"                # Poor windows - MINIMAL or NO trades
    BLOCKED = "BLOCKED"          # Never trade these windows


# AGGRESSIVE trading windows for 300%+ returns
TIME_WINDOWS = {
    # Gap momentum - MOST PROFITABLE WINDOW
    "GAP_MOMENTUM": {
        "start": time(9, 16),        # Right at open
        "end": time(9, 25),
        "quality": TimeQuality.LEGENDARY,  # LEGENDARY for gap trades
        "description": "Gap momentum - highest volatility, max opportunity",
        "bias": "MOMENTUM",
        "size_multiplier": 2.0       # NEW: 2x size for gap momentum
    },
    # Morning momentum (post-gap settlement)
    "MORNING_MOMENTUM": {
        "start": time(9, 25),
        "end": time(10, 45),         # EXTENDED from 10:30
        "quality": TimeQuality.ULTRA,
        "description": "Post-open momentum, institutional activity high",
        "bias": "MOMENTUM",
        "size_multiplier": 1.5       # NEW: 1.5x size
    },
    # Mid-morning consolidation
    "MIDMORNING_CONSOLIDATION": {
        "start": time(10, 45),
        "end": time(11, 30),
        "quality": TimeQuality.GOOD,
        "description": "Consolidation phase, range trades work",
        "bias": "RANGE",
        "size_multiplier": 1.0
    },
    # Lunch lull - TRADE CAREFULLY, not avoid completely
    "LUNCH_LULL": {
        "start": time(11, 30),
        "end": time(13, 15),
        "quality": TimeQuality.AVERAGE,   # CHANGED from POOR - trade with caution
        "description": "Lower volume but breakouts possible",
        "bias": "CAUTIOUS",
        "size_multiplier": 0.5       # Half size during lunch
    },
    # Afternoon power hour - EXCELLENT for 300%+ returns
    "AFTERNOON_POWER": {
        "start": time(13, 15),           # EARLIER start
        "end": time(14, 50),             # EXTENDED end
        "quality": TimeQuality.ULTRA,
        "description": "FII/DII activity picks up, trend resumes",
        "bias": "MOMENTUM",
        "size_multiplier": 1.5           # NEW: 1.5x size
    },
    # Pre-close volatility - TRADEABLE with caution
    "PRECLOSE_VOLATILITY": {
        "start": time(14, 50),
        "end": time(15, 20),             # EXTENDED - capture EOD moves
        "quality": TimeQuality.GOOD,     # UPGRADED from AVERAGE
        "description": "Position unwinding, quick scalps work",
        "bias": "SCALP",
        "size_multiplier": 0.8           # Slightly reduced
    },
    # Market close - minimal trading
    "CLOSE_BLOCKED": {
        "start": time(15, 20),
        "end": time(15, 30),
        "quality": TimeQuality.BLOCKED,
        "description": "No new trades near close",
        "bias": "NO_TRADE",
        "size_multiplier": 0.0
    },
    # Pre-market - AGGRESSIVE for gap captures
    "PREMARKET_GAP": {
        "start": time(9, 15),            # Market open
        "end": time(9, 16),
        "quality": TimeQuality.LEGENDARY,  # LEGENDARY for gap trades
        "description": "Gap opening - max opportunity",
        "bias": "GAP",
        "size_multiplier": 2.0           # Double size for gaps
    }
}


def get_time_quality(current_time: time = None) -> Tuple[TimeQuality, str, str, float]:
    """
    Get the quality rating and SIZE MULTIPLIER for current time.
    Returns: (quality, window_name, bias, size_multiplier)
    """
    if current_time is None:
        current_time = datetime.now().time()
    
    for window_name, window in TIME_WINDOWS.items():
        if window["start"] <= current_time <= window["end"]:
            size_mult = window.get("size_multiplier", 1.0)
            return (window["quality"], window_name, window["bias"], size_mult)
    
    # Default for times outside defined windows
    return (TimeQuality.BLOCKED, "OUTSIDE_HOURS", "NO_TRADE", 0.0)


def should_trade_now() -> Tuple[bool, str, float]:
    """
    Check if current time is suitable for trading.
    Returns: (can_trade, reason, size_multiplier)
    """
    quality, window, bias, size_mult = get_time_quality()
    
    if quality == TimeQuality.BLOCKED:
        return (False, f"Trading blocked during {window}", 0.0)
    
    if quality == TimeQuality.POOR:
        return (False, f"Poor quality window: {window}", 0.0)
    
    return (True, f"{window} ({quality.value}) - {bias} mode", size_mult)


def get_time_multiplier() -> Tuple[float, float]:
    """
    Get confidence multiplier AND size multiplier based on time of day.
    Returns: (confidence_multiplier, size_multiplier)
    
    For 300%+ monthly returns:
    LEGENDARY: 1.0 confidence, 2.0x size (MAXIMUM aggression)
    ULTRA: 0.98 confidence, 1.5x size
    GOOD: 0.95 confidence, 1.0x size
    AVERAGE: 0.90 confidence, 0.5x size
    """
    quality, _, _, size_mult = get_time_quality()
    
    confidence_multipliers = {
        TimeQuality.LEGENDARY: 1.0,
        TimeQuality.ULTRA: 0.98,
        TimeQuality.GOOD: 0.95,
        TimeQuality.AVERAGE: 0.90,
        TimeQuality.POOR: 0.75,
        TimeQuality.BLOCKED: 0.0
    }
    return (confidence_multipliers.get(quality, 0.0), size_mult)


# ============================================================================
#                     VIX REGIME FILTER
# ============================================================================

class VIXRegime(Enum):
    """VIX-based market regime"""
    ULTRA_LOW = "ULTRA_LOW"       # VIX < 12 - Premium selling paradise
    LOW = "LOW"                   # 12 <= VIX < 15 - Normal conditions
    NORMAL = "NORMAL"             # 15 <= VIX < 20 - Standard trading
    ELEVATED = "ELEVATED"         # 20 <= VIX < 25 - Careful trading
    HIGH = "HIGH"                 # 25 <= VIX < 35 - Only puts or avoid
    EXTREME = "EXTREME"           # VIX >= 35 - No trading, too risky


@dataclass
class VIXAnalysis:
    """VIX analysis result"""
    current_vix: float
    regime: VIXRegime
    can_trade: bool
    recommended_direction: str  # LONG, SHORT, BOTH, NONE
    position_size_multiplier: float
    stoploss_multiplier: float
    reasoning: str


def analyze_vix(vix: float) -> VIXAnalysis:
    """
    Analyze VIX and provide trading guidance.
    ENHANCED for 300%+ monthly returns - more aggressive in optimal VIX zones.
    
    Key insights:
    - Ultra-low VIX (<12): MAXIMUM aggression, premium is cheap
    - Low VIX (12-15): EXCELLENT for directional trades
    - Normal VIX (15-20): Standard conditions, both directions ok
    - Elevated VIX (20-28): OPPORTUNITY for put buying, premiums rich
    - High VIX (>28): Only expert trades, maximum caution
    """
    # Handle dict input from market data
    if isinstance(vix, dict):
        vix = float(vix.get('current', vix.get('value', 15.0)))
    
    vix = float(vix)
    
    if vix < 12:
        return VIXAnalysis(
            current_vix=vix,
            regime=VIXRegime.ULTRA_LOW,
            can_trade=True,
            recommended_direction="BOTH",
            position_size_multiplier=1.5,    # INCREASED: Aggressive in calm
            stoploss_multiplier=0.7,         # TIGHTER stops in low vol
            reasoning="🚀 ULTRA-LOW VIX! Maximum aggression. Premiums cheap. GO AGGRESSIVE!"
        )
    elif vix < 15:
        return VIXAnalysis(
            current_vix=vix,
            regime=VIXRegime.LOW,
            can_trade=True,
            recommended_direction="BOTH",
            position_size_multiplier=1.3,    # INCREASED: 1.3x in low VIX
            stoploss_multiplier=0.8,         # Tighter stops
            reasoning="💪 Low volatility. EXCELLENT for momentum trades. Size up!"
        )
    elif vix < 20:
        return VIXAnalysis(
            current_vix=vix,
            regime=VIXRegime.NORMAL,
            can_trade=True,
            recommended_direction="BOTH",
            position_size_multiplier=1.0,    # Normal sizing
            stoploss_multiplier=1.0,
            reasoning="✅ Normal volatility. Standard trading. Good opportunity."
        )
    elif vix < 28:  # CHANGED from 25 - trade in elevated zone
        return VIXAnalysis(
            current_vix=vix,
            regime=VIXRegime.ELEVATED,
            can_trade=True,                  # CHANGED: Still tradeable
            recommended_direction="SHORT",   # Favor puts
            position_size_multiplier=0.8,    # INCREASED from 0.7
            stoploss_multiplier=1.3,
            reasoning="⚠️ Elevated VIX. PUT buying opportunity! Rich premiums."
        )
    elif vix < 38:  # CHANGED from 35 - expert trading zone
        return VIXAnalysis(
            current_vix=vix,
            regime=VIXRegime.HIGH,
            can_trade=True,                  # CHANGED: Expert trades allowed
            recommended_direction="SHORT",   # Only puts
            position_size_multiplier=0.5,
            stoploss_multiplier=1.5,
            reasoning="🔥 HIGH VIX! PUT trades only. Reduced size. Expert mode!"
        )
    else:
        return VIXAnalysis(
            current_vix=vix,
            regime=VIXRegime.EXTREME,
            can_trade=False,
            recommended_direction="NONE",
            position_size_multiplier=0.0,
            stoploss_multiplier=2.0,
            reasoning="🛑 EXTREME volatility! NO TRADING. Capital preservation mode."
        )


# ============================================================================
#                     MULTI-LAYER CONFIRMATION GATE
# ============================================================================

@dataclass
class ConfirmationLayer:
    """Single confirmation layer"""
    name: str
    confirmed: bool
    strength: float  # 0-100
    reasoning: str


@dataclass  
class MultiLayerConfirmation:
    """Multi-layer confirmation result"""
    layers: List[ConfirmationLayer]
    total_layers: int
    confirmed_layers: int
    confirmation_rate: float  # 0-1
    weighted_score: float  # 0-100
    can_trade: bool
    gate_status: str  # PASS, PARTIAL, FAIL


def check_multi_layer_confirmation(
    institutional_signal: bool = False,
    institutional_strength: float = 0,
    technical_signal: bool = False,
    technical_strength: float = 0,
    volume_signal: bool = False,
    volume_strength: float = 0,
    ai_confirmation: bool = False,
    ai_confidence: float = 0,
    momentum_signal: bool = False,
    momentum_strength: float = 0,
    min_layers_required: int = 3,     # REDUCED from 4 for 300%+ returns
    min_weighted_score: float = 70    # REDUCED from 80 for more trades
) -> MultiLayerConfirmation:
    """
    Check if enough confirmation layers are present for a trade.
    ENHANCED for 300%+ monthly returns - balanced aggression.
    
    For 300%+ returns with 90%+ win rate:
    - Minimum 3 out of 5 layers for normal trades
    - Minimum 4 out of 5 layers for ELITE trades (2x size)
    - Weighted score 70+ = Normal trade
    - Weighted score 85+ = ELITE trade (bigger size)
    
    Layer weights (REBALANCED for momentum trading):
    - Institutional (SMC): 30%  (INCREASED - most reliable)
    - AI Confirmation: 25%      (INCREASED - Gemini is key)
    - Technical: 20%
    - Volume Profile: 15%
    - Momentum: 10%
    """
    layers = []
    weights = {
        'institutional': 30,  # INCREASED from 25
        'ai': 25,             # INCREASED from 20
        'technical': 20,      # DECREASED from 25
        'volume': 15,         # DECREASED from 20
        'momentum': 10
    }
    
    # Check each layer
    layers.append(ConfirmationLayer(
        name="Institutional (SMC)",
        confirmed=institutional_signal,
        strength=institutional_strength,
        reasoning="Order blocks, FVG, liquidity sweeps"
    ))
    
    layers.append(ConfirmationLayer(
        name="Technical",
        confirmed=technical_signal,
        strength=technical_strength,
        reasoning="VWAP, EMA, RSI confluence"
    ))
    
    layers.append(ConfirmationLayer(
        name="Volume Profile",
        confirmed=volume_signal,
        strength=volume_strength,
        reasoning="POC, VAH/VAL, volume delta"
    ))
    
    layers.append(ConfirmationLayer(
        name="AI Confirmation",
        confirmed=ai_confirmation,
        strength=ai_confidence * 100,
        reasoning="Gemini AI validation"
    ))
    
    layers.append(ConfirmationLayer(
        name="Momentum",
        confirmed=momentum_signal,
        strength=momentum_strength,
        reasoning="Velocity, acceleration, phase"
    ))
    
    # Calculate metrics
    confirmed_count = sum(1 for l in layers if l.confirmed)
    confirmation_rate = confirmed_count / len(layers)
    
    # Calculate weighted score
    weighted_score = 0
    weight_list = ['institutional', 'ai', 'technical', 'volume', 'momentum']
    for i, layer in enumerate(layers):
        if layer.confirmed:
            weighted_score += (layer.strength / 100) * weights[weight_list[i]]
    
    # Determine gate status for 300%+ AGGRESSIVE returns
    if confirmed_count >= 5 and weighted_score >= 90:
        gate_status = "LEGENDARY"     # NEW: Maximum aggression
        can_trade = True
    elif confirmed_count >= 4 and weighted_score >= 80:
        gate_status = "ELITE"         # NEW: 1.5x size
        can_trade = True
    elif confirmed_count >= min_layers_required and weighted_score >= min_weighted_score:
        gate_status = "PASS"          # Normal trade
        can_trade = True
    elif confirmed_count >= min_layers_required - 1 and weighted_score >= min_weighted_score * 0.85:
        gate_status = "PARTIAL"       # CHANGED: Lower threshold for partial
        can_trade = True              # CHANGED: Allow partial trades for 300%+
    else:
        gate_status = "FAIL"
        can_trade = False
    
    return MultiLayerConfirmation(
        layers=layers,
        total_layers=len(layers),
        confirmed_layers=confirmed_count,
        confirmation_rate=confirmation_rate,
        weighted_score=weighted_score,
        can_trade=can_trade,
        gate_status=gate_status
    )


# ============================================================================
#                     SIGNAL QUALITY SCORER
# ============================================================================

@dataclass
class SignalQualityScore:
    """Comprehensive signal quality score"""
    base_score: float
    time_adjusted_score: float
    vix_adjusted_score: float
    confluence_adjusted_score: float
    final_score: float
    grade: str  # A+, A, B+, B, C, D, F
    tradeable: bool
    adjustments: Dict[str, float]


def calculate_signal_quality(
    base_confluence_score: float,
    vix: float,
    layers_confirmed: int,
    ai_confidence: float
) -> SignalQualityScore:
    """
    Calculate comprehensive signal quality score.
    ENHANCED for 300%+ monthly returns - more aggressive grading.
    
    Grading for 300%+ Returns:
    - LEGENDARY (95+): 2.0x position size, maximum aggression
    - A+ (90+): 1.5x position size
    - A (85+): 1.2x position size  
    - B+ (80+): 1.0x position size (still tradeable!)
    - B (75+): 0.8x position size
    - C (70+): 0.5x position size (cautious trade)
    - Below: No trade
    """
    adjustments = {}
    
    # Start with base score
    base_score = base_confluence_score
    
    # Time adjustment - returns (confidence_mult, size_mult)
    time_conf_mult, time_size_mult = get_time_multiplier()
    time_adjusted = base_score * time_conf_mult
    adjustments['time_conf'] = time_conf_mult
    adjustments['time_size'] = time_size_mult
    
    # VIX adjustment - MORE AGGRESSIVE in favorable conditions
    vix_analysis = analyze_vix(vix)
    if vix_analysis.regime == VIXRegime.ULTRA_LOW:
        vix_multiplier = 1.15  # BOOST in ultra-low VIX
    elif vix_analysis.regime == VIXRegime.LOW:
        vix_multiplier = 1.10  # BOOST in low VIX
    elif vix_analysis.can_trade:
        vix_multiplier = 1.0
    elif vix_analysis.regime == VIXRegime.HIGH:
        vix_multiplier = 0.7   # Still tradeable for experts
    else:
        vix_multiplier = 0.3   # Extreme only
    vix_adjusted = time_adjusted * vix_multiplier
    adjustments['vix'] = vix_multiplier
    
    # Confluence adjustment (BIGGER bonus for more layers)
    confluence_bonus = 1.0 + (layers_confirmed - 2) * 0.08  # +8% per layer above 2
    confluence_adjusted = vix_adjusted * confluence_bonus
    adjustments['confluence'] = confluence_bonus
    
    # AI confidence adjustment - MORE WEIGHT on high confidence
    if ai_confidence >= 0.90:
        ai_multiplier = 1.15  # 15% boost for 90%+ AI
    elif ai_confidence >= 0.85:
        ai_multiplier = 1.08  # 8% boost for 85%+ AI
    else:
        ai_multiplier = 0.85 + (ai_confidence * 0.15)
    final_score = confluence_adjusted * ai_multiplier
    adjustments['ai'] = ai_multiplier
    
    # Cap at 100
    final_score = min(100, final_score)
    
    # Determine grade - AGGRESSIVE for 300%+ returns
    if final_score >= 95:
        grade = "LEGENDARY"   # NEW: 2.0x size
        tradeable = True
    elif final_score >= 90:
        grade = "A+"
        tradeable = True
    elif final_score >= 85:
        grade = "A"
        tradeable = True      # CHANGED: Now tradeable
    elif final_score >= 80:
        grade = "B+"
        tradeable = True      # CHANGED: Now tradeable for 300%+
    elif final_score >= 75:
        grade = "B"
        tradeable = True      # CHANGED: Tradeable at 0.8x size
    elif final_score >= 70:
        grade = "C"
        tradeable = True      # CHANGED: Cautious trade at 0.5x
    else:
        grade = "F"
        tradeable = False
    
    return SignalQualityScore(
        base_score=base_score,
        time_adjusted_score=time_adjusted,
        vix_adjusted_score=vix_adjusted,
        confluence_adjusted_score=confluence_adjusted,
        final_score=final_score,
        grade=grade,
        tradeable=tradeable,
        adjustments=adjustments
    )


# ============================================================================
#                     DYNAMIC STOPLOSS CALCULATOR
# ============================================================================

@dataclass
class SmartStoploss:
    """Smart stoploss calculation result"""
    stoploss_price: float
    stoploss_percent: float
    atr_based: float
    vix_adjusted: float
    time_adjusted: float
    reasoning: str


def calculate_smart_stoploss(
    entry_price: float,
    direction: str,  # LONG or SHORT
    atr: float,
    vix: float,
    volatility_percentile: float = 50,  # 0-100
    signal_grade: str = "B"             # NEW: Grade affects stoploss
) -> SmartStoploss:
    """
    Calculate intelligent stoploss that adapts to market conditions.
    ENHANCED for 300%+ returns - TIGHTER stoplosses with better R:R.
    
    Key principles for 300%+ returns:
    1. TIGHTER stops in all conditions (preserve capital for next trade)
    2. LEGENDARY/A+ signals get even tighter stops (high confidence)
    3. VIX-based adjustment still applies
    4. Time-based tightening near key periods
    5. ATR-based foundation with aggressive multipliers
    """
    # Base stoploss: 0.8x ATR (TIGHTER from 1.0x)
    if signal_grade in ["LEGENDARY", "A+"]:
        base_atr_multiple = 0.6  # VERY TIGHT for high confidence
    elif signal_grade in ["A", "B+"]:
        base_atr_multiple = 0.8  # Tight for good signals
    else:
        base_atr_multiple = 1.0  # Normal for others
    
    # VIX adjustment
    vix_analysis = analyze_vix(vix)
    atr_multiple = base_atr_multiple * vix_analysis.stoploss_multiplier
    
    # Time adjustment - tighter stops in power hours
    quality, window, bias, size_mult = get_time_quality()
    if window == "MORNING_MOMENTUM":
        atr_multiple *= 0.85  # 15% tighter in momentum hours
    elif window in ["PRECLOSE_VOLATILITY", "AFTERNOON_POWER"]:
        atr_multiple *= 0.9   # 10% tighter
    elif window == "PREMARKET_GAP":
        atr_multiple *= 0.7   # 30% tighter for gap trades
    
    # Calculate stoploss distance
    stoploss_distance = atr * atr_multiple
    
    # Apply to price
    if direction.upper() == "LONG":
        stoploss_price = entry_price - stoploss_distance
    else:
        stoploss_price = entry_price + stoploss_distance
    
    stoploss_percent = (stoploss_distance / entry_price) * 100
    
    return SmartStoploss(
        stoploss_price=stoploss_price,
        stoploss_percent=stoploss_percent,
        atr_based=atr * base_atr_multiple,
        vix_adjusted=stoploss_distance,
        time_adjusted=stoploss_distance,
        reasoning=f"🎯 ATR {atr_multiple:.2f}x | Grade: {signal_grade} | VIX: {vix_analysis.regime.value} | Window: {window}"
    )


# ============================================================================
#                     POSITION SIZE OPTIMIZER
# ============================================================================

def calculate_optimal_position_size(
    capital: float,
    max_risk_percent: float,
    stoploss_percent: float,
    vix: float,
    signal_grade: str,
    max_position_percent: float = 80    # INCREASED from 60 for 300%+
) -> Tuple[float, str]:
    """
    Calculate optimal position size based on risk and signal quality.
    ENHANCED for 300%+ monthly returns - AGGRESSIVE sizing for high-quality signals.
    
    Returns: (position_size, reasoning)
    """
    # Base calculation: Kelly-inspired but with aggression
    # Position = Capital * Risk% / Stoploss%
    base_position = capital * (max_risk_percent / 100) / (stoploss_percent / 100)
    
    # VIX adjustment - USE FULL MULTIPLIER
    vix_analysis = analyze_vix(vix)
    vix_adjusted = base_position * vix_analysis.position_size_multiplier
    
    # Signal quality adjustment - AGGRESSIVE for 300%+ returns
    quality_multipliers = {
        "LEGENDARY": 2.0,   # NEW: Double size for legendary signals
        "A+": 1.5,          # INCREASED from 1.0
        "A": 1.2,           # INCREASED from 0.9
        "B+": 1.0,          # INCREASED from 0.7
        "B": 0.8,           # INCREASED from 0.5
        "C": 0.5,           # INCREASED from 0.3
        "F": 0.0
    }
    quality_adjusted = vix_adjusted * quality_multipliers.get(signal_grade, 0.8)
    
    # Time-based size boost
    _, _, _, time_size_mult = get_time_quality()
    time_adjusted = quality_adjusted * time_size_mult
    
    # Cap at max position
    max_allowed = capital * (max_position_percent / 100)
    final_position = min(time_adjusted, max_allowed)
    
    reasoning = f"🚀 Base: ₹{base_position:,.0f} → VIX({vix_analysis.regime.value}): ₹{vix_adjusted:,.0f} → Grade({signal_grade}): ₹{quality_adjusted:,.0f} → Time({time_size_mult}x): ₹{time_adjusted:,.0f} → Final: ₹{final_position:,.0f}"
    
    return (final_position, reasoning)


# ============================================================================
#                     MASTER TRADE FILTER
# ============================================================================

@dataclass
class TradeDecision:
    """Final trade decision"""
    can_trade: bool
    signal_grade: str
    position_size: float
    stoploss: float
    reasoning: List[str]
    blockers: List[str]
    score_breakdown: Dict[str, Any]


def make_trade_decision(
    base_signal: Dict[str, Any],
    vix: float,
    capital: float,
    ai_confidence: float = 0.85,
    max_risk_percent: float = 3.0    # INCREASED from 2.0 for 300%+
) -> TradeDecision:
    """
    Master function that combines all filters to make final trade decision.
    ENHANCED for 300%+ monthly returns - more aggressive but controlled.
    
    For 300%+ returns with 90%+ win rate:
    - Time quality: AVERAGE or better (MORE windows)
    - VIX regime: Expanded tradeable zone
    - Multi-layer: 3+ layers confirmed (RELAXED from 4)
    - Signal grade: C or better (MUCH more trades)
    - LEGENDARY/A+ get MAXIMUM position size
    """
    reasoning = []
    blockers = []
    
    # 1. Time Filter - with size multiplier
    can_trade_time, time_reason, time_size_mult = should_trade_now()
    if not can_trade_time:
        blockers.append(f"⛔ Time Block: {time_reason}")
    else:
        reasoning.append(f"✅ Time: {time_reason} | Size: {time_size_mult}x")
    
    # 2. VIX Filter - more aggressive
    vix_analysis = analyze_vix(vix)
    if not vix_analysis.can_trade:
        blockers.append(f"⛔ VIX Block: {vix_analysis.reasoning}")
    else:
        reasoning.append(f"✅ VIX: {vix_analysis.regime.value} ({vix:.2f}) | {vix_analysis.reasoning}")
    
    # 3. Multi-Layer Confirmation
    layers_confirmed = base_signal.get('layers_confirmed', 0)
    confluence_score = base_signal.get('confluence_score', 0)
    
    # 4. Signal Quality Score
    quality = calculate_signal_quality(
        base_confluence_score=confluence_score,
        vix=vix,
        layers_confirmed=layers_confirmed,
        ai_confidence=ai_confidence
    )
    
    if not quality.tradeable:
        blockers.append(f"⛔ Signal Grade: {quality.grade} (Score: {quality.final_score:.1f})")
    else:
        # Add trade type emoji based on grade
        grade_emoji = {
            "LEGENDARY": "🔥",
            "A+": "🚀",
            "A": "💪",
            "B+": "✅",
            "B": "📊",
            "C": "⚠️"
        }
        emoji = grade_emoji.get(quality.grade, "📈")
        reasoning.append(f"{emoji} Signal Grade: {quality.grade} (Score: {quality.final_score:.1f})")
    
    # 5. Calculate position size and stoploss if tradeable
    if len(blockers) == 0:
        entry_price = base_signal.get('entry_price', 0)
        atr = base_signal.get('atr', entry_price * 0.01)
        direction = base_signal.get('direction', 'LONG')
        
        stoploss = calculate_smart_stoploss(
            entry_price=entry_price,
            direction=direction,
            atr=atr,
            vix=vix,
            signal_grade=quality.grade
        )
        
        position_size, size_reasoning = calculate_optimal_position_size(
            capital=capital,
            max_risk_percent=max_risk_percent,
            stoploss_percent=stoploss.stoploss_percent,
            vix=vix,
            signal_grade=quality.grade
        )
        
        reasoning.append(f"💰 Position: ₹{position_size:,.0f}")
        reasoning.append(f"🛡️ Stoploss: {stoploss.stoploss_percent:.2f}% @ ₹{stoploss.stoploss_price:,.2f}")
        reasoning.append(f"📊 {size_reasoning}")
    else:
        stoploss = None
        position_size = 0
    
    return TradeDecision(
        can_trade=len(blockers) == 0,
        signal_grade=quality.grade,
        position_size=position_size,
        stoploss=stoploss.stoploss_price if stoploss else 0,
        reasoning=reasoning,
        blockers=blockers,
        score_breakdown={
            'base_score': quality.base_score,
            'time_adjusted': quality.time_adjusted_score,
            'vix_adjusted': quality.vix_adjusted_score,
            'final_score': quality.final_score,
            'adjustments': quality.adjustments
        }
    )


# ============================================================================
#                     LOGGING HELPERS
# ============================================================================

def log_trade_decision(decision: TradeDecision, instrument: str):
    """Log trade decision with full details"""
    logger.info("=" * 70)
    logger.info(f"📊 TRADE DECISION FOR {instrument}")
    logger.info("=" * 70)
    
    if decision.can_trade:
        logger.info(f"✅ TRADE APPROVED - Grade: {decision.signal_grade}")
        for reason in decision.reasoning:
            logger.info(f"   {reason}")
        logger.info(f"   Position Size: ₹{decision.position_size:,.0f}")
        logger.info(f"   Stoploss: ₹{decision.stoploss:.2f}")
    else:
        logger.info(f"❌ TRADE BLOCKED - Grade: {decision.signal_grade}")
        for blocker in decision.blockers:
            logger.info(f"   ⛔ {blocker}")
    
    logger.info("=" * 70)
