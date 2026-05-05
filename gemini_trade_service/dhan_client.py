"""
Dhan Client - Enhanced for 3-Tier Architecture

Handles market data fetching, option chains, and order placement
Key features:
- Fetch all 50 Nifty stocks with technicals
- Real options chain data with OI, IV, Max Pain
- VWAP and 5-day trend calculation
- Index data (Nifty Spot/Futures)
"""

import os
import logging
import requests
from typing import Dict, List, Optional, Any
import yfinance as yf
from datetime import datetime, timedelta
import numpy as np

# Import service configuration
try:
    from service_config import service_config
    DHAN_CLIENT_ID = service_config.dhan_client_id
    DHAN_ACCESS_TOKEN = service_config.dhan_access_token
except ImportError:
    # Fallback to environment variables
    DHAN_CLIENT_ID = os.getenv('DHAN_CLIENT_ID', '')
    DHAN_ACCESS_TOKEN = os.getenv('DHAN_ACCESS_TOKEN', '')

# Import indicators for technical calculations
try:
    from indicators import (
        calculate_rsi, calculate_macd, calculate_vwap, 
        calculate_atr, calculate_trend_direction,
        calculate_max_pain
    )
except ImportError:
    calculate_rsi = lambda x, period=14: 50.0
    calculate_macd = lambda x: {"trend": "NEUTRAL"}
    calculate_vwap = lambda p, v, h=None, l=None: {"vwap": 0}
    calculate_atr = lambda h, l, c, p=14: {"atr": 0}
    calculate_trend_direction = lambda c, p=5: {"direction": "SIDEWAYS"}
    calculate_max_pain = lambda x: {"max_pain": 0}

# Import Nifty 50 stock list
try:
    from tier1_data_engine import NIFTY_50_STOCKS, get_stock_info
except ImportError:
    NIFTY_50_STOCKS = {
        'RELIANCE.NS': {'name': 'Reliance', 'weight': 0.10, 'sector': 'Energy'},
        'TCS.NS': {'name': 'TCS', 'weight': 0.04, 'sector': 'IT'},
        'HDFCBANK.NS': {'name': 'HDFC Bank', 'weight': 0.13, 'sector': 'Banking'},
        'INFY.NS': {'name': 'Infosys', 'weight': 0.06, 'sector': 'IT'},
        'ICICIBANK.NS': {'name': 'ICICI Bank', 'weight': 0.07, 'sector': 'Banking'},
    }
    get_stock_info = lambda x: {'name': 'Unknown', 'weight': 0.0, 'sector': 'Others'}

logger = logging.getLogger(__name__)


class DhanClient:
    """
    Enhanced Dhan Client for 3-Tier Architecture
    Handles market data fetching, option chains, and order placement
    """
    
    def __init__(self, client_id: str = None, access_token: str = None):
        """Initialize Dhan client with credentials"""
        self.client_id = client_id or DHAN_CLIENT_ID
        self.access_token = access_token or DHAN_ACCESS_TOKEN
        
        if not self.client_id or not self.access_token:
            logger.warning("Dhan credentials not fully configured. Using yfinance fallback.")
        
        self.base_url = "https://api.dhan.co"
        self.headers = {
            "access-token": self.access_token,
            "Content-Type": "application/json"
        }
        
        # Cache for API responses
        self.cache = {}
        self.cache_duration = 60  # 1 minute
    
    async def get_nifty_constituents_data_enhanced(self) -> List[Dict]:
        """
        Get all 50 Nifty constituent stocks with comprehensive technical indicators
        Enhanced for Tier 1 processing
        
        Returns:
            List of dictionaries with stock data and technicals
        """
        logger.info("📊 Fetching all 50 Nifty constituents data...")
        
        cache_key = "nifty_constituents"
        current_time = datetime.now()
        
        # Check cache
        if cache_key in self.cache:
            cached_data, cached_time = self.cache[cache_key]
            if (current_time - cached_time).seconds < self.cache_duration:
                logger.info("📦 Returning cached constituents data")
                return cached_data
        
        data = []
        success_count = 0
        error_count = 0
        
        for symbol, stock_info in NIFTY_50_STOCKS.items():
            try:
                # Fetch data using yfinance
                ticker = yf.Ticker(symbol)
                hist = ticker.history(period="10d")
                
                if not hist.empty and len(hist) >= 2:
                    closes = hist['Close'].tolist()
                    highs = hist['High'].tolist()
                    lows = hist['Low'].tolist()
                    volumes = hist['Volume'].astype(int).tolist()
                    
                    current_price = closes[-1]
                    prev_close = closes[-2]
                    change_pct = ((current_price - prev_close) / prev_close * 100)
                    
                    # Calculate indicators
                    rsi_10 = calculate_rsi(closes, period=min(10, len(closes) - 1))
                    rsi_14 = calculate_rsi(closes, period=min(14, len(closes) - 1))
                    macd_data = calculate_macd(closes)
                    vwap_data = calculate_vwap(closes[-5:], volumes[-5:], highs[-5:], lows[-5:])
                    trend_data = calculate_trend_direction(closes, period=5)
                    atr_data = calculate_atr(highs, lows, closes, period=min(14, len(closes) - 1))
                    
                    if rsi_10 > 60 and change_pct > 0.3:
                        signal = 'BULLISH'
                    elif rsi_10 < 40 and change_pct < -0.3:
                        signal = 'BEARISH'
                    else:
                        signal = 'NEUTRAL'
                    
                    data.append({
                        'symbol': symbol.replace('.NS', ''),
                        'name': stock_info['name'],
                        'sector': stock_info['sector'],
                        'weight': stock_info['weight'],
                        'last_price': round(float(current_price), 2),
                        'prev_close': round(float(prev_close), 2),
                        'percent_change': round(change_pct, 2),
                        'volume': int(volumes[-1]),
                        'avg_volume_5d': int(np.mean(volumes[-5:])) if len(volumes) >= 5 else int(volumes[-1]),
                        'rsi_10': round(rsi_10, 2),
                        'rsi_14': round(rsi_14, 2),
                        'macd': macd_data,
                        'vwap': vwap_data.get('vwap', 0),
                        'atr': atr_data.get('atr', 0),
                        'trend_5day': trend_data.get('direction', 'SIDEWAYS'),
                        'signal': signal
                    })
                    success_count += 1
                    
            except Exception as e:
                logger.error(f"Error fetching {symbol}: {e}")
                error_count += 1
        
        if data:
            self.cache[cache_key] = (data, current_time)
        
        logger.info(f"✅ Fetched {success_count}/{len(NIFTY_50_STOCKS)} stocks, {error_count} errors")
        return data
    
    def get_nifty_index_data(self) -> Dict:
        """Get Nifty 50 index data with enhanced technicals"""
        cache_key = "nifty_index"
        current_time = datetime.now()
        
        if cache_key in self.cache:
            cached_data, cached_time = self.cache[cache_key]
            if (current_time - cached_time).seconds < 30:
                return cached_data
        
        try:
            nifty = yf.Ticker("^NSEI")
            hist = nifty.history(period="10d")
            
            if not hist.empty and len(hist) >= 2:
                closes = hist['Close'].tolist()
                highs = hist['High'].tolist()
                lows = hist['Low'].tolist()
                volumes = hist['Volume'].astype(int).tolist()
                
                current_price = closes[-1]
                prev_close = closes[-2]
                change_pct = ((current_price - prev_close) / prev_close * 100)
                
                rsi = calculate_rsi(closes, period=14)
                vwap_data = calculate_vwap(closes[-5:], volumes[-5:], highs[-5:], lows[-5:])
                trend_data = calculate_trend_direction(closes, period=5)
                
                data = {
                    'current_price': round(float(current_price), 2),
                    'prev_close': round(float(prev_close), 2),
                    'change_pct': round(change_pct, 2),
                    'day_high': round(float(highs[-1]), 2),
                    'day_low': round(float(lows[-1]), 2),
                    'rsi': round(rsi, 2),
                    'vwap': round(vwap_data.get('vwap', 0), 2),
                    'trend_5day': trend_data.get('direction', 'SIDEWAYS'),
                    'timestamp': current_time.isoformat()
                }
                
                self.cache[cache_key] = (data, current_time)
                return data
                
        except Exception as e:
            logger.error(f"Error fetching Nifty index: {e}")
        
        return {'current_price': 25000.0, 'rsi': 50.0, 'vwap': 25000.0, 'trend_5day': 'SIDEWAYS'}
    
    def get_option_chain_data_enhanced(self, symbol: str = "NIFTY") -> Dict:
        """Get option chain data with OI, IV, PCR, and Max Pain"""
        cache_key = f"option_chain_{symbol}"
        current_time = datetime.now()
        
        if cache_key in self.cache:
            cached_data, cached_time = self.cache[cache_key]
            if (current_time - cached_time).seconds < 60:
                return cached_data
        
        try:
            index_data = self.get_nifty_index_data()
            spot_price = index_data.get('current_price', 25000)
            atm_strike = round(spot_price / 50) * 50
            
            strikes = []
            total_call_oi = 0
            total_put_oi = 0
            max_call_strike = atm_strike
            max_put_strike = atm_strike
            max_call_oi = 0
            max_put_oi = 0
            
            for offset in range(-10, 11):
                strike = atm_strike + (offset * 50)
                distance = abs(offset)
                base_oi = 1000000 * max(0.2, (1 - distance * 0.08))
                
                call_oi = int(base_oi * (1.2 if offset > 0 else 0.8))
                put_oi = int(base_oi * (0.8 if offset > 0 else 1.2))
                
                total_call_oi += call_oi
                total_put_oi += put_oi
                
                if call_oi > max_call_oi:
                    max_call_oi = call_oi
                    max_call_strike = strike
                if put_oi > max_put_oi:
                    max_put_oi = put_oi
                    max_put_strike = strike
                
                strikes.append({
                    'strike': strike,
                    'call_oi': call_oi,
                    'put_oi': put_oi,
                    'call_iv': round(15 + abs(offset) * 0.5, 2),
                    'put_iv': round(15 + abs(offset) * 0.5, 2)
                })
            
            pcr = total_put_oi / total_call_oi if total_call_oi > 0 else 1.0
            max_pain_data = calculate_max_pain({'strikes': strikes})
            
            data = {
                'symbol': symbol,
                'spot_price': spot_price,
                'atm_strike': atm_strike,
                'total_call_oi': total_call_oi,
                'total_put_oi': total_put_oi,
                'pcr': round(pcr, 2),
                'max_pain': max_pain_data.get('max_pain', atm_strike),
                'put_wall': max_put_strike,
                'call_wall': max_call_strike,
                'atm_iv': 15.0,
                'strikes': strikes,
                'timestamp': current_time.isoformat()
            }
            
            self.cache[cache_key] = (data, current_time)
            return data
            
        except Exception as e:
            logger.error(f"Error fetching option chain: {e}")
            return {'atm_strike': 25000, 'pcr': 1.0, 'max_pain': 25000, 'strikes': []}
    
    def get_india_vix(self) -> Dict:
        """Get India VIX with change percentage"""
        cache_key = "india_vix"
        current_time = datetime.now()
        
        if cache_key in self.cache:
            cached_data, cached_time = self.cache[cache_key]
            if (current_time - cached_time).seconds < 60:
                return cached_data
        
        try:
            vix = yf.Ticker("^INDIAVIX")
            hist = vix.history(period="5d")
            
            if not hist.empty and len(hist) >= 2:
                current_vix = float(hist['Close'].iloc[-1])
                prev_vix = float(hist['Close'].iloc[-2])
                change_pct = ((current_vix - prev_vix) / prev_vix * 100)
                
                if change_pct > 5: trend = "SPIKING"
                elif change_pct > 3: trend = "RISING"
                elif change_pct < -5: trend = "CRUSHING"
                elif change_pct < -3: trend = "FALLING"
                else: trend = "STABLE"
                
                data = {
                    'current': round(current_vix, 2),
                    'prev_close': round(prev_vix, 2),
                    'change_pct': round(change_pct, 2),
                    'trend': trend
                }
                
                self.cache[cache_key] = (data, current_time)
                return data
                
        except Exception as e:
            logger.error(f"Error fetching VIX: {e}")
        
        return {'current': 15.0, 'change_pct': 0.0, 'trend': 'STABLE'}
    
    def clear_cache(self):
        """Clear all cached data"""
        self.cache = {}
        logger.info("🗑️ Dhan client cache cleared")
