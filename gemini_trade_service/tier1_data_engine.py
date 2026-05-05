"""
TIER 1: Data Preparation Engine (The Clean Up Crew)

Model: Gemini 2.5 Flash-Lite
Purpose: Fast data collection and cleaning for all 50 Nifty stocks + Index technicals
Output: Clean JSON of Market Breadth - NO sentiment/news analysis

Key Responsibilities:
- Collect LTP, Volume, 10-period RSI for all 50 Nifty stocks
- Calculate how many stocks are positive, negative, neutral
- Get Index: Nifty Spot/Futures Price, VWAP, 5-day Trend Direction
- Provide standardized, factual data for Tier 2
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from google import genai
from google.genai import types

logger = logging.getLogger(__name__)

# ============================================================================
# TIER 1 SYSTEM PROMPT - Data Preparation (NO Sentiment Analysis)
# ============================================================================
TIER_1_SYSTEM_PROMPT = """
ROLE: You are a Market Data Aggregator and Technical Calculator.
YOUR JOB: Process raw stock data and calculate simple statistics. NO analysis, NO opinions.

STRICT RULES:
1. DO NOT analyze sentiment or news
2. DO NOT make predictions
3. DO NOT suggest trades
4. ONLY count and categorize data factually

INPUT: Raw data for 50 Nifty stocks with price, volume, RSI, MACD values.

TASK:
1. Count stocks by category:
   - POSITIVE: Stocks with price change > 0.3%
   - NEGATIVE: Stocks with price change < -0.3%
   - NEUTRAL: Stocks between -0.3% and +0.3%

2. Count by RSI zones:
   - OVERBOUGHT: RSI > 70
   - OVERSOLD: RSI < 30
   - BULLISH_ZONE: RSI between 55-70
   - BEARISH_ZONE: RSI between 30-45
   - NEUTRAL_ZONE: RSI between 45-55

3. Calculate weighted contribution (by weightage) for:
   - Top 5 heavyweights contribution
   - Sector-wise count (Banking, IT, Energy, Auto, FMCG, Others)

4. Identify top 3 gainers and top 3 losers by % change

OUTPUT FORMAT (STRICT JSON - NO EXTRA TEXT):
{
  "market_breadth": {
    "positive_count": 0,
    "negative_count": 0,
    "neutral_count": 0,
    "advance_decline_ratio": 0.0
  },
  "rsi_distribution": {
    "overbought_count": 0,
    "oversold_count": 0,
    "bullish_zone_count": 0,
    "bearish_zone_count": 0,
    "neutral_zone_count": 0
  },
  "sector_breakdown": {
    "banking": {"positive": 0, "negative": 0, "neutral": 0},
    "it": {"positive": 0, "negative": 0, "neutral": 0},
    "energy": {"positive": 0, "negative": 0, "neutral": 0},
    "auto": {"positive": 0, "negative": 0, "neutral": 0},
    "fmcg": {"positive": 0, "negative": 0, "neutral": 0},
    "others": {"positive": 0, "negative": 0, "neutral": 0}
  },
  "heavyweight_contribution": {
    "reliance": {"change_pct": 0.0, "weight": 0.0},
    "hdfc_bank": {"change_pct": 0.0, "weight": 0.0},
    "icici_bank": {"change_pct": 0.0, "weight": 0.0},
    "infosys": {"change_pct": 0.0, "weight": 0.0},
    "tcs": {"change_pct": 0.0, "weight": 0.0}
  },
  "top_gainers": ["SYMBOL1", "SYMBOL2", "SYMBOL3"],
  "top_losers": ["SYMBOL1", "SYMBOL2", "SYMBOL3"],
  "index_data": {
    "nifty_spot": 0.0,
    "nifty_change_pct": 0.0,
    "vwap": 0.0,
    "trend_5day": "UP" | "DOWN" | "SIDEWAYS"
  },
  "data_quality": {
    "stocks_processed": 50,
    "missing_data_count": 0,
    "timestamp": "ISO_TIMESTAMP"
  }
}
"""


class Tier1DataEngine:
    """
    Tier 1: Data Preparation Engine
    Uses Gemini 2.5 Flash-Lite for fast, cheap data processing
    """
    
    def __init__(self, api_key: str, model: str = "gemini-2.0-flash-lite"):
        """
        Initialize Tier 1 Engine
        
        Args:
            api_key: Gemini API key for Tier 1
            model: Model name (default: gemini-2.0-flash-lite)
        """
        self.client = genai.Client(api_key=api_key)
        self.model = model
        self.cache = {}
        self.cache_duration = 60  # 1 minute cache
        
        logger.info(f"✅ Tier 1 Data Engine initialized with model: {model}")
    
    async def process_market_data(
        self,
        stocks_data: List[Dict],
        index_data: Dict,
        force_refresh: bool = False
    ) -> Optional[Dict]:
        """
        Process raw market data through Tier 1 AI
        
        Args:
            stocks_data: List of 50 Nifty stock data with technicals
            index_data: Nifty index data (spot, VWAP, trend)
            force_refresh: Skip cache if True
            
        Returns:
            Clean market breadth JSON or None
        """
        cache_key = "tier1_market_breadth"
        current_time = datetime.now()
        
        # Check cache
        if not force_refresh and cache_key in self.cache:
            cached_data, cached_time = self.cache[cache_key]
            if (current_time - cached_time).seconds < self.cache_duration:
                logger.info("📦 Returning cached Tier 1 data")
                return cached_data
        
        try:
            # Prepare input payload
            input_payload = {
                "stocks": stocks_data,
                "index": index_data,
                "request_time": current_time.isoformat()
            }
            
            # Call Gemini Tier 1
            logger.info("🔄 Tier 1: Processing market data...")
            
            response = self.client.models.generate_content(
                model=self.model,
                contents=f"Process this market data and return clean statistics:\n{json.dumps(input_payload)}",
                config=types.GenerateContentConfig(
                    system_instruction=TIER_1_SYSTEM_PROMPT,
                    response_mime_type="application/json",
                    temperature=0.1  # Very low for factual data
                )
            )
            
            result = json.loads(response.text)
            
            # Cache the result
            self.cache[cache_key] = (result, current_time)
            
            logger.info(f"✅ Tier 1 Complete: {result.get('market_breadth', {}).get('positive_count', 0)} positive, "
                       f"{result.get('market_breadth', {}).get('negative_count', 0)} negative")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Tier 1 Error: {e}")
            return self._get_fallback_data(stocks_data, index_data)
    
    def _get_fallback_data(self, stocks_data: List[Dict], index_data: Dict) -> Dict:
        """
        Calculate fallback data without AI if API fails
        Uses simple Python calculations
        """
        try:
            positive_count = 0
            negative_count = 0
            neutral_count = 0
            
            overbought = 0
            oversold = 0
            bullish_zone = 0
            bearish_zone = 0
            neutral_zone = 0
            
            gainers = []
            losers = []
            
            for stock in stocks_data:
                change = stock.get('percent_change', 0)
                rsi = stock.get('rsi', 50)
                
                # Count by price change
                if change > 0.3:
                    positive_count += 1
                elif change < -0.3:
                    negative_count += 1
                else:
                    neutral_count += 1
                
                # Count by RSI
                if rsi > 70:
                    overbought += 1
                elif rsi < 30:
                    oversold += 1
                elif rsi >= 55:
                    bullish_zone += 1
                elif rsi <= 45:
                    bearish_zone += 1
                else:
                    neutral_zone += 1
                
                gainers.append((stock.get('symbol', 'UNKNOWN'), change))
                losers.append((stock.get('symbol', 'UNKNOWN'), change))
            
            # Sort for top gainers/losers
            gainers.sort(key=lambda x: x[1], reverse=True)
            losers.sort(key=lambda x: x[1])
            
            total = positive_count + negative_count + neutral_count
            ad_ratio = positive_count / negative_count if negative_count > 0 else positive_count
            
            return {
                "market_breadth": {
                    "positive_count": positive_count,
                    "negative_count": negative_count,
                    "neutral_count": neutral_count,
                    "advance_decline_ratio": round(ad_ratio, 2)
                },
                "rsi_distribution": {
                    "overbought_count": overbought,
                    "oversold_count": oversold,
                    "bullish_zone_count": bullish_zone,
                    "bearish_zone_count": bearish_zone,
                    "neutral_zone_count": neutral_zone
                },
                "sector_breakdown": {
                    "banking": {"positive": 0, "negative": 0, "neutral": 0},
                    "it": {"positive": 0, "negative": 0, "neutral": 0},
                    "energy": {"positive": 0, "negative": 0, "neutral": 0},
                    "auto": {"positive": 0, "negative": 0, "neutral": 0},
                    "fmcg": {"positive": 0, "negative": 0, "neutral": 0},
                    "others": {"positive": 0, "negative": 0, "neutral": 0}
                },
                "heavyweight_contribution": {},
                "top_gainers": [g[0] for g in gainers[:3]],
                "top_losers": [l[0] for l in losers[:3]],
                "index_data": index_data,
                "data_quality": {
                    "stocks_processed": len(stocks_data),
                    "missing_data_count": 0,
                    "timestamp": datetime.now().isoformat(),
                    "source": "fallback_calculation"
                }
            }
            
        except Exception as e:
            logger.error(f"Fallback calculation error: {e}")
            return self._get_empty_response()
    
    def _get_empty_response(self) -> Dict:
        """Return empty response structure"""
        return {
            "market_breadth": {
                "positive_count": 0,
                "negative_count": 0,
                "neutral_count": 0,
                "advance_decline_ratio": 0.0
            },
            "rsi_distribution": {
                "overbought_count": 0,
                "oversold_count": 0,
                "bullish_zone_count": 0,
                "bearish_zone_count": 0,
                "neutral_zone_count": 0
            },
            "sector_breakdown": {},
            "heavyweight_contribution": {},
            "top_gainers": [],
            "top_losers": [],
            "index_data": {},
            "data_quality": {
                "stocks_processed": 0,
                "missing_data_count": 0,
                "timestamp": datetime.now().isoformat(),
                "error": "No data available"
            }
        }
    
    def clear_cache(self):
        """Clear all cached data"""
        self.cache = {}
        logger.info("🗑️ Tier 1 cache cleared")


# ============================================================================
# NIFTY 50 CONSTITUENTS with Sector & Weightage
# ============================================================================
NIFTY_50_STOCKS = {
    # Banking Sector (~35% weight)
    'HDFCBANK.NS': {'name': 'HDFC Bank', 'weight': 0.135, 'sector': 'Banking'},
    'ICICIBANK.NS': {'name': 'ICICI Bank', 'weight': 0.078, 'sector': 'Banking'},
    'SBIN.NS': {'name': 'State Bank of India', 'weight': 0.035, 'sector': 'Banking'},
    'KOTAKBANK.NS': {'name': 'Kotak Mahindra Bank', 'weight': 0.034, 'sector': 'Banking'},
    'AXISBANK.NS': {'name': 'Axis Bank', 'weight': 0.029, 'sector': 'Banking'},
    'INDUSINDBK.NS': {'name': 'IndusInd Bank', 'weight': 0.012, 'sector': 'Banking'},
    
    # IT Sector (~15% weight)
    'TCS.NS': {'name': 'TCS', 'weight': 0.042, 'sector': 'IT'},
    'INFY.NS': {'name': 'Infosys', 'weight': 0.062, 'sector': 'IT'},
    'WIPRO.NS': {'name': 'Wipro', 'weight': 0.012, 'sector': 'IT'},
    'HCLTECH.NS': {'name': 'HCL Technologies', 'weight': 0.037, 'sector': 'IT'},
    'TECHM.NS': {'name': 'Tech Mahindra', 'weight': 0.011, 'sector': 'IT'},
    'LTIM.NS': {'name': 'LTIMindtree', 'weight': 0.015, 'sector': 'IT'},
    
    # Energy Sector (~15% weight)
    'RELIANCE.NS': {'name': 'Reliance Industries', 'weight': 0.102, 'sector': 'Energy'},
    'ONGC.NS': {'name': 'ONGC', 'weight': 0.011, 'sector': 'Energy'},
    'NTPC.NS': {'name': 'NTPC', 'weight': 0.018, 'sector': 'Energy'},
    'POWERGRID.NS': {'name': 'Power Grid', 'weight': 0.015, 'sector': 'Energy'},
    'ADANIPORTS.NS': {'name': 'Adani Ports', 'weight': 0.012, 'sector': 'Energy'},
    'COALINDIA.NS': {'name': 'Coal India', 'weight': 0.011, 'sector': 'Energy'},
    
    # Auto Sector (~8% weight)
    'MARUTI.NS': {'name': 'Maruti Suzuki', 'weight': 0.018, 'sector': 'Auto'},
    'TATAMOTORS.NS': {'name': 'Tata Motors', 'weight': 0.016, 'sector': 'Auto'},
    'M&M.NS': {'name': 'Mahindra & Mahindra', 'weight': 0.021, 'sector': 'Auto'},
    'BAJAJ-AUTO.NS': {'name': 'Bajaj Auto', 'weight': 0.012, 'sector': 'Auto'},
    'HEROMOTOCO.NS': {'name': 'Hero MotoCorp', 'weight': 0.008, 'sector': 'Auto'},
    'EICHERMOT.NS': {'name': 'Eicher Motors', 'weight': 0.009, 'sector': 'Auto'},
    
    # FMCG Sector (~10% weight)
    'HINDUNILVR.NS': {'name': 'Hindustan Unilever', 'weight': 0.028, 'sector': 'FMCG'},
    'ITC.NS': {'name': 'ITC', 'weight': 0.045, 'sector': 'FMCG'},
    'NESTLEIND.NS': {'name': 'Nestle India', 'weight': 0.012, 'sector': 'FMCG'},
    'BRITANNIA.NS': {'name': 'Britannia', 'weight': 0.008, 'sector': 'FMCG'},
    'TATACONSUM.NS': {'name': 'Tata Consumer', 'weight': 0.010, 'sector': 'FMCG'},
    
    # Pharma & Healthcare (~5% weight)
    'SUNPHARMA.NS': {'name': 'Sun Pharma', 'weight': 0.022, 'sector': 'Pharma'},
    'DRREDDY.NS': {'name': "Dr Reddy's Labs", 'weight': 0.011, 'sector': 'Pharma'},
    'CIPLA.NS': {'name': 'Cipla', 'weight': 0.010, 'sector': 'Pharma'},
    'APOLLOHOSP.NS': {'name': 'Apollo Hospitals', 'weight': 0.009, 'sector': 'Pharma'},
    
    # Financials (Non-Bank) (~8% weight)
    'BAJFINANCE.NS': {'name': 'Bajaj Finance', 'weight': 0.022, 'sector': 'NBFC'},
    'BAJAJFINSV.NS': {'name': 'Bajaj Finserv', 'weight': 0.010, 'sector': 'NBFC'},
    'HDFCLIFE.NS': {'name': 'HDFC Life Insurance', 'weight': 0.011, 'sector': 'Insurance'},
    'SBILIFE.NS': {'name': 'SBI Life Insurance', 'weight': 0.009, 'sector': 'Insurance'},
    
    # Others (~9% weight)
    'LT.NS': {'name': 'Larsen & Toubro', 'weight': 0.042, 'sector': 'Infrastructure'},
    'TITAN.NS': {'name': 'Titan Company', 'weight': 0.018, 'sector': 'Consumer'},
    'ASIANPAINT.NS': {'name': 'Asian Paints', 'weight': 0.017, 'sector': 'Consumer'},
    'ULTRACEMCO.NS': {'name': 'UltraTech Cement', 'weight': 0.015, 'sector': 'Cement'},
    'GRASIM.NS': {'name': 'Grasim Industries', 'weight': 0.013, 'sector': 'Cement'},
    'SHREECEM.NS': {'name': 'Shree Cement', 'weight': 0.006, 'sector': 'Cement'},
    'JSWSTEEL.NS': {'name': 'JSW Steel', 'weight': 0.011, 'sector': 'Metals'},
    'TATASTEEL.NS': {'name': 'Tata Steel', 'weight': 0.011, 'sector': 'Metals'},
    'HINDALCO.NS': {'name': 'Hindalco', 'weight': 0.009, 'sector': 'Metals'},
    'ADANIENT.NS': {'name': 'Adani Enterprises', 'weight': 0.010, 'sector': 'Conglomerate'},
    'BPCL.NS': {'name': 'BPCL', 'weight': 0.008, 'sector': 'Energy'},
    'DIVISLAB.NS': {'name': "Divi's Laboratories", 'weight': 0.008, 'sector': 'Pharma'},
}


def get_nifty_50_symbols() -> List[str]:
    """Get list of all Nifty 50 symbols"""
    return list(NIFTY_50_STOCKS.keys())


def get_stock_info(symbol: str) -> Dict:
    """Get stock info (name, weight, sector) for a symbol"""
    return NIFTY_50_STOCKS.get(symbol, {'name': 'Unknown', 'weight': 0.0, 'sector': 'Others'})
