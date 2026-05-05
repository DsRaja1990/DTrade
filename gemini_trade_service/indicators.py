"""
Technical Indicators Module
Calculates RSI, MACD, VWAP, ATR, Vol/OI changes for stock analysis

Enhanced for 3-Tier Architecture:
- 10-period RSI (faster response)
- VWAP for intraday context
- ATR for volatility measurement
- Enhanced S/R calculations
"""
import numpy as np
import pandas as pd
from typing import List, Dict, Any, Tuple
import logging

logger = logging.getLogger(__name__)

def calculate_rsi(prices: List[float], period: int = 14) -> float:
    """
    Calculate Relative Strength Index (RSI)
    
    Args:
        prices: List of prices (most recent last)
        period: RSI period (default 14)
    
    Returns:
        RSI value (0-100)
    """
    if len(prices) < period + 1:
        return 50.0  # Neutral if insufficient data
    
    try:
        prices_array = np.array(prices)
        deltas = np.diff(prices_array)
        
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        
        avg_gain = np.mean(gains[-period:])
        avg_loss = np.mean(losses[-period:])
        
        if avg_loss == 0:
            return 100.0
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return round(rsi, 2)
    
    except Exception as e:
        logger.error(f"Error calculating RSI: {e}")
        return 50.0

def calculate_macd(prices: List[float], 
                   fast_period: int = 12, 
                   slow_period: int = 26, 
                   signal_period: int = 9) -> Dict[str, float]:
    """
    Calculate MACD (Moving Average Convergence Divergence)
    
    Args:
        prices: List of prices (most recent last)
        fast_period: Fast EMA period (default 12)
        slow_period: Slow EMA period (default 26)
        signal_period: Signal line period (default 9)
    
    Returns:
        Dictionary with macd, signal, histogram
    """
    if len(prices) < slow_period + signal_period:
        return {"macd": 0.0, "signal": 0.0, "histogram": 0.0, "trend": "NEUTRAL"}
    
    try:
        prices_array = np.array(prices)
        
        # Calculate EMAs
        ema_fast = _calculate_ema(prices_array, fast_period)
        ema_slow = _calculate_ema(prices_array, slow_period)
        
        # MACD line
        macd_line = ema_fast - ema_slow
        
        # Signal line (EMA of MACD)
        # Create array of MACD values
        macd_values = []
        for i in range(slow_period, len(prices_array)):
            fast_ema = _calculate_ema(prices_array[:i+1], fast_period)
            slow_ema = _calculate_ema(prices_array[:i+1], slow_period)
            macd_values.append(fast_ema - slow_ema)
        
        signal_line = _calculate_ema(np.array(macd_values), signal_period)
        
        # Histogram
        histogram = macd_line - signal_line
        
        # Determine trend
        if histogram > 0 and macd_line > 0:
            trend = "BULLISH"
        elif histogram < 0 and macd_line < 0:
            trend = "BEARISH"
        else:
            trend = "NEUTRAL"
        
        return {
            "macd": round(macd_line, 4),
            "signal": round(signal_line, 4),
            "histogram": round(histogram, 4),
            "trend": trend
        }
    
    except Exception as e:
        logger.error(f"Error calculating MACD: {e}")
        return {"macd": 0.0, "signal": 0.0, "histogram": 0.0, "trend": "NEUTRAL"}

def _calculate_ema(prices: np.ndarray, period: int) -> float:
    """Calculate Exponential Moving Average"""
    if len(prices) < period:
        return np.mean(prices)
    
    multiplier = 2 / (period + 1)
    ema = np.mean(prices[:period])
    
    for price in prices[period:]:
        ema = (price - ema) * multiplier + ema
    
    return ema

def calculate_volume_change(current_volume: int, 
                            previous_volumes: List[int], 
                            period: int = 20) -> Dict[str, Any]:
    """
    Calculate volume change percentage
    
    Args:
        current_volume: Current volume
        previous_volumes: List of previous volumes
        period: Period for average calculation
    
    Returns:
        Dictionary with volume metrics
    """
    if not previous_volumes or len(previous_volumes) < period:
        return {
            "volume_change_pct": 0.0,
            "vs_avg_volume": 1.0,
            "volume_trend": "NEUTRAL"
        }
    
    try:
        avg_volume = np.mean(previous_volumes[-period:])
        
        if avg_volume == 0:
            return {
                "volume_change_pct": 0.0,
                "vs_avg_volume": 1.0,
                "volume_trend": "NEUTRAL"
            }
        
        volume_ratio = current_volume / avg_volume
        volume_change_pct = ((current_volume - avg_volume) / avg_volume) * 100
        
        # Determine trend
        if volume_ratio > 1.5:
            trend = "SURGE"
        elif volume_ratio > 1.2:
            trend = "HIGH"
        elif volume_ratio < 0.7:
            trend = "LOW"
        else:
            trend = "NORMAL"
        
        return {
            "volume_change_pct": round(volume_change_pct, 2),
            "vs_avg_volume": round(volume_ratio, 2),
            "volume_trend": trend
        }
    
    except Exception as e:
        logger.error(f"Error calculating volume change: {e}")
        return {
            "volume_change_pct": 0.0,
            "vs_avg_volume": 1.0,
            "volume_trend": "NEUTRAL"
        }

def calculate_oi_change(current_oi: int, previous_oi: int) -> Dict[str, Any]:
    """
    Calculate Open Interest (OI) change
    
    Args:
        current_oi: Current Open Interest
        previous_oi: Previous Open Interest
    
    Returns:
        Dictionary with OI metrics
    """
    if previous_oi == 0:
        return {
            "oi_change": 0,
            "oi_change_pct": 0.0,
            "oi_trend": "NEUTRAL"
        }
    
    try:
        oi_change = current_oi - previous_oi
        oi_change_pct = (oi_change / previous_oi) * 100
        
        # Determine trend
        if oi_change_pct > 20:
            trend = "STRONG_BUILD"
        elif oi_change_pct > 10:
            trend = "BUILD"
        elif oi_change_pct < -20:
            trend = "STRONG_UNWINDING"
        elif oi_change_pct < -10:
            trend = "UNWINDING"
        else:
            trend = "STABLE"
        
        return {
            "oi_change": oi_change,
            "oi_change_pct": round(oi_change_pct, 2),
            "oi_trend": trend
        }
    
    except Exception as e:
        logger.error(f"Error calculating OI change: {e}")
        return {
            "oi_change": 0,
            "oi_change_pct": 0.0,
            "oi_trend": "NEUTRAL"
        }

def calculate_support_resistance(prices: List[float], 
                                 highs: List[float], 
                                 lows: List[float],
                                 period: int = 20) -> Dict[str, float]:
    """
    Calculate support and resistance levels
    
    Args:
        prices: List of closing prices
        highs: List of high prices
        lows: List of low prices
        period: Lookback period
    
    Returns:
        Dictionary with support and resistance levels
    """
    if len(prices) < period:
        current_price = prices[-1] if prices else 0
        return {
            "support": current_price * 0.98,
            "resistance": current_price * 1.02,
            "pivot": current_price
        }
    
    try:
        recent_highs = highs[-period:]
        recent_lows = lows[-period:]
        recent_closes = prices[-period:]
        
        # Calculate Pivot Point
        pivot = (recent_highs[-1] + recent_lows[-1] + recent_closes[-1]) / 3
        
        # Support and Resistance
        resistance = 2 * pivot - recent_lows[-1]
        support = 2 * pivot - recent_highs[-1]
        
        return {
            "support": round(support, 2),
            "resistance": round(resistance, 2),
            "pivot": round(pivot, 2)
        }
    
    except Exception as e:
        logger.error(f"Error calculating support/resistance: {e}")
        current_price = prices[-1] if prices else 0
        return {
            "support": current_price * 0.98,
            "resistance": current_price * 1.02,
            "pivot": current_price
        }

def analyze_stock_momentum(price_data: Dict[str, List[float]], 
                           volume_data: List[int]) -> Dict[str, Any]:
    """
    Comprehensive momentum analysis combining all indicators
    
    Args:
        price_data: Dictionary with 'close', 'high', 'low' price lists
        volume_data: List of volumes
    
    Returns:
        Dictionary with comprehensive analysis
    """
    try:
        closes = price_data.get('close', [])
        highs = price_data.get('high', closes)
        lows = price_data.get('low', closes)
        
        rsi = calculate_rsi(closes)
        macd = calculate_macd(closes)
        volume = calculate_volume_change(
            volume_data[-1] if volume_data else 0,
            volume_data[:-1] if volume_data else []
        )
        sr = calculate_support_resistance(closes, highs, lows)
        
        # Overall sentiment
        bullish_signals = 0
        bearish_signals = 0
        
        if rsi > 50:
            bullish_signals += 1
        elif rsi < 50:
            bearish_signals += 1
        
        if macd['trend'] == 'BULLISH':
            bullish_signals += 1
        elif macd['trend'] == 'BEARISH':
            bearish_signals += 1
        
        if volume['volume_trend'] in ['SURGE', 'HIGH']:
            bullish_signals += 1
        
        # Determine overall signal
        if bullish_signals > bearish_signals:
            overall_signal = "BULLISH"
        elif bearish_signals > bullish_signals:
            overall_signal = "BEARISH"
        else:
            overall_signal = "NEUTRAL"
        
        return {
            "rsi": rsi,
            "macd": macd,
            "volume": volume,
            "support_resistance": sr,
            "overall_signal": overall_signal,
            "signal_strength": abs(bullish_signals - bearish_signals)
        }
    
    except Exception as e:
        logger.error(f"Error in momentum analysis: {e}")
        return {
            "rsi": 50.0,
            "macd": {"macd": 0.0, "signal": 0.0, "histogram": 0.0, "trend": "NEUTRAL"},
            "volume": {"volume_change_pct": 0.0, "vs_avg_volume": 1.0, "volume_trend": "NEUTRAL"},
            "support_resistance": {"support": 0, "resistance": 0, "pivot": 0},
            "overall_signal": "NEUTRAL",
            "signal_strength": 0
        }


# ============================================================================
# NEW INDICATORS FOR 3-TIER ARCHITECTURE
# ============================================================================

def calculate_rsi_10(prices: List[float]) -> float:
    """
    Calculate 10-period RSI (faster response for intraday)
    
    Args:
        prices: List of prices (most recent last)
    
    Returns:
        RSI value (0-100)
    """
    return calculate_rsi(prices, period=10)


def calculate_vwap(
    prices: List[float],
    volumes: List[int],
    highs: List[float] = None,
    lows: List[float] = None
) -> Dict[str, float]:
    """
    Calculate Volume Weighted Average Price (VWAP)
    
    Args:
        prices: List of close prices
        volumes: List of volumes
        highs: List of high prices (optional, uses prices if not provided)
        lows: List of low prices (optional, uses prices if not provided)
    
    Returns:
        Dictionary with VWAP, upper/lower bands, and price position
    """
    if not prices or not volumes or len(prices) != len(volumes):
        return {
            "vwap": 0.0,
            "upper_band": 0.0,
            "lower_band": 0.0,
            "price_vs_vwap": "AT_VWAP",
            "deviation_pct": 0.0
        }
    
    try:
        # Use typical price if highs/lows provided
        if highs and lows and len(highs) == len(prices) and len(lows) == len(prices):
            typical_prices = [(h + l + c) / 3 for h, l, c in zip(highs, lows, prices)]
        else:
            typical_prices = prices
        
        # Calculate VWAP
        cumulative_tp_vol = 0.0
        cumulative_vol = 0
        squared_deviation_sum = 0.0
        
        for i, (tp, vol) in enumerate(zip(typical_prices, volumes)):
            cumulative_tp_vol += tp * vol
            cumulative_vol += vol
        
        if cumulative_vol == 0:
            return {
                "vwap": prices[-1] if prices else 0.0,
                "upper_band": prices[-1] if prices else 0.0,
                "lower_band": prices[-1] if prices else 0.0,
                "price_vs_vwap": "AT_VWAP",
                "deviation_pct": 0.0
            }
        
        vwap = cumulative_tp_vol / cumulative_vol
        
        # Calculate standard deviation for bands
        for i, (tp, vol) in enumerate(zip(typical_prices, volumes)):
            squared_deviation_sum += vol * ((tp - vwap) ** 2)
        
        std_dev = np.sqrt(squared_deviation_sum / cumulative_vol)
        
        # VWAP Bands (1 standard deviation)
        upper_band = vwap + std_dev
        lower_band = vwap - std_dev
        
        # Current price position relative to VWAP
        current_price = prices[-1]
        if current_price > upper_band:
            position = "ABOVE_UPPER"
        elif current_price > vwap:
            position = "ABOVE_VWAP"
        elif current_price < lower_band:
            position = "BELOW_LOWER"
        elif current_price < vwap:
            position = "BELOW_VWAP"
        else:
            position = "AT_VWAP"
        
        deviation_pct = ((current_price - vwap) / vwap * 100) if vwap > 0 else 0
        
        return {
            "vwap": round(vwap, 2),
            "upper_band": round(upper_band, 2),
            "lower_band": round(lower_band, 2),
            "price_vs_vwap": position,
            "deviation_pct": round(deviation_pct, 2)
        }
    
    except Exception as e:
        logger.error(f"Error calculating VWAP: {e}")
        return {
            "vwap": prices[-1] if prices else 0.0,
            "upper_band": 0.0,
            "lower_band": 0.0,
            "price_vs_vwap": "AT_VWAP",
            "deviation_pct": 0.0
        }


def calculate_atr(
    highs: List[float],
    lows: List[float],
    closes: List[float],
    period: int = 14
) -> Dict[str, float]:
    """
    Calculate Average True Range (ATR) for volatility measurement
    
    Args:
        highs: List of high prices
        lows: List of low prices
        closes: List of close prices
        period: ATR period (default 14)
    
    Returns:
        Dictionary with ATR value, normalized ATR, and volatility classification
    """
    if len(highs) < period + 1 or len(lows) < period + 1 or len(closes) < period + 1:
        return {
            "atr": 0.0,
            "atr_percent": 0.0,
            "volatility": "UNKNOWN"
        }
    
    try:
        true_ranges = []
        
        for i in range(1, len(closes)):
            high = highs[i]
            low = lows[i]
            prev_close = closes[i - 1]
            
            tr = max(
                high - low,
                abs(high - prev_close),
                abs(low - prev_close)
            )
            true_ranges.append(tr)
        
        # Calculate ATR (simple moving average of true range)
        if len(true_ranges) < period:
            atr = np.mean(true_ranges)
        else:
            atr = np.mean(true_ranges[-period:])
        
        # Calculate ATR as percentage of current price
        current_price = closes[-1]
        atr_percent = (atr / current_price * 100) if current_price > 0 else 0
        
        # Classify volatility
        if atr_percent > 2.0:
            volatility = "VERY_HIGH"
        elif atr_percent > 1.5:
            volatility = "HIGH"
        elif atr_percent > 1.0:
            volatility = "MEDIUM"
        elif atr_percent > 0.5:
            volatility = "LOW"
        else:
            volatility = "VERY_LOW"
        
        return {
            "atr": round(atr, 2),
            "atr_percent": round(atr_percent, 2),
            "volatility": volatility
        }
    
    except Exception as e:
        logger.error(f"Error calculating ATR: {e}")
        return {
            "atr": 0.0,
            "atr_percent": 0.0,
            "volatility": "UNKNOWN"
        }


def calculate_trend_direction(
    closes: List[float],
    period: int = 5
) -> Dict[str, Any]:
    """
    Calculate 5-day trend direction
    
    Args:
        closes: List of close prices
        period: Lookback period (default 5)
    
    Returns:
        Dictionary with trend direction and strength
    """
    if len(closes) < period:
        return {
            "direction": "SIDEWAYS",
            "strength": "WEAK",
            "change_pct": 0.0,
            "consecutive_up": 0,
            "consecutive_down": 0
        }
    
    try:
        recent_closes = closes[-period:]
        
        # Calculate overall change
        start_price = recent_closes[0]
        end_price = recent_closes[-1]
        change_pct = ((end_price - start_price) / start_price * 100) if start_price > 0 else 0
        
        # Count consecutive up/down days
        consecutive_up = 0
        consecutive_down = 0
        current_streak = 0
        streak_type = None
        
        for i in range(1, len(recent_closes)):
            if recent_closes[i] > recent_closes[i-1]:
                if streak_type == "up":
                    current_streak += 1
                else:
                    streak_type = "up"
                    current_streak = 1
                consecutive_up = max(consecutive_up, current_streak)
            elif recent_closes[i] < recent_closes[i-1]:
                if streak_type == "down":
                    current_streak += 1
                else:
                    streak_type = "down"
                    current_streak = 1
                consecutive_down = max(consecutive_down, current_streak)
            else:
                streak_type = None
                current_streak = 0
        
        # Determine trend direction
        if change_pct > 1.5:
            direction = "UP"
        elif change_pct < -1.5:
            direction = "DOWN"
        elif change_pct > 0.5:
            direction = "SLIGHT_UP"
        elif change_pct < -0.5:
            direction = "SLIGHT_DOWN"
        else:
            direction = "SIDEWAYS"
        
        # Determine strength
        if abs(change_pct) > 3:
            strength = "STRONG"
        elif abs(change_pct) > 1.5:
            strength = "MODERATE"
        else:
            strength = "WEAK"
        
        return {
            "direction": direction,
            "strength": strength,
            "change_pct": round(change_pct, 2),
            "consecutive_up": consecutive_up,
            "consecutive_down": consecutive_down
        }
    
    except Exception as e:
        logger.error(f"Error calculating trend direction: {e}")
        return {
            "direction": "SIDEWAYS",
            "strength": "WEAK",
            "change_pct": 0.0,
            "consecutive_up": 0,
            "consecutive_down": 0
        }


def calculate_max_pain(option_chain: Dict) -> Dict[str, Any]:
    """
    Calculate Max Pain from options chain data
    Max Pain is the strike price where maximum number of options expire worthless
    
    Args:
        option_chain: Dictionary with calls and puts OI by strike
    
    Returns:
        Dictionary with max pain level and nearby levels
    """
    try:
        strikes = option_chain.get("strikes", [])
        if not strikes:
            return {
                "max_pain": 0,
                "pain_range": {"low": 0, "high": 0},
                "put_wall": 0,
                "call_wall": 0
            }
        
        # Calculate pain at each strike
        pain_values = {}
        total_call_oi = 0
        total_put_oi = 0
        max_call_oi_strike = None
        max_put_oi_strike = None
        max_call_oi = 0
        max_put_oi = 0
        
        for strike_data in strikes:
            strike = strike_data.get("strike", 0)
            call_oi = strike_data.get("call_oi", 0)
            put_oi = strike_data.get("put_oi", 0)
            
            total_call_oi += call_oi
            total_put_oi += put_oi
            
            # Track max OI strikes
            if call_oi > max_call_oi:
                max_call_oi = call_oi
                max_call_oi_strike = strike
            if put_oi > max_put_oi:
                max_put_oi = put_oi
                max_put_oi_strike = strike
        
        # Calculate pain at each strike
        for strike_data in strikes:
            strike = strike_data.get("strike", 0)
            total_pain = 0
            
            for other_strike_data in strikes:
                other_strike = other_strike_data.get("strike", 0)
                other_call_oi = other_strike_data.get("call_oi", 0)
                other_put_oi = other_strike_data.get("put_oi", 0)
                
                # Call pain: intrinsic value * OI
                if strike > other_strike:
                    call_pain = (strike - other_strike) * other_call_oi
                else:
                    call_pain = 0
                
                # Put pain: intrinsic value * OI
                if strike < other_strike:
                    put_pain = (other_strike - strike) * other_put_oi
                else:
                    put_pain = 0
                
                total_pain += call_pain + put_pain
            
            pain_values[strike] = total_pain
        
        # Find max pain strike (minimum total pain)
        if pain_values:
            max_pain_strike = min(pain_values, key=pain_values.get)
        else:
            max_pain_strike = 0
        
        return {
            "max_pain": max_pain_strike,
            "pain_range": {
                "low": max_pain_strike - 100,
                "high": max_pain_strike + 100
            },
            "put_wall": max_put_oi_strike or 0,  # Highest put OI = support
            "call_wall": max_call_oi_strike or 0,  # Highest call OI = resistance
            "pcr": round(total_put_oi / total_call_oi, 2) if total_call_oi > 0 else 0
        }
    
    except Exception as e:
        logger.error(f"Error calculating max pain: {e}")
        return {
            "max_pain": 0,
            "pain_range": {"low": 0, "high": 0},
            "put_wall": 0,
            "call_wall": 0,
            "pcr": 0
        }


def comprehensive_technical_analysis(
    closes: List[float],
    highs: List[float],
    lows: List[float],
    volumes: List[int]
) -> Dict[str, Any]:
    """
    Comprehensive technical analysis combining all indicators
    Designed for 3-Tier Architecture Tier 1 processing
    
    Args:
        closes: List of close prices
        highs: List of high prices
        lows: List of low prices
        volumes: List of volumes
    
    Returns:
        Complete technical analysis dictionary
    """
    try:
        return {
            "rsi_14": calculate_rsi(closes, period=14),
            "rsi_10": calculate_rsi(closes, period=10),
            "macd": calculate_macd(closes),
            "vwap": calculate_vwap(closes, volumes, highs, lows),
            "atr": calculate_atr(highs, lows, closes),
            "trend": calculate_trend_direction(closes, period=5),
            "volume": calculate_volume_change(
                volumes[-1] if volumes else 0,
                volumes[:-1] if volumes else []
            ),
            "support_resistance": calculate_support_resistance(closes, highs, lows),
            "timestamp": pd.Timestamp.now().isoformat()
        }
    
    except Exception as e:
        logger.error(f"Error in comprehensive analysis: {e}")
        return {
            "rsi_14": 50.0,
            "rsi_10": 50.0,
            "macd": {"macd": 0.0, "signal": 0.0, "histogram": 0.0, "trend": "NEUTRAL"},
            "vwap": {"vwap": 0.0, "price_vs_vwap": "AT_VWAP"},
            "atr": {"atr": 0.0, "volatility": "UNKNOWN"},
            "trend": {"direction": "SIDEWAYS", "strength": "WEAK"},
            "volume": {"volume_trend": "NEUTRAL"},
            "support_resistance": {"support": 0, "resistance": 0, "pivot": 0},
            "timestamp": pd.Timestamp.now().isoformat()
        }
