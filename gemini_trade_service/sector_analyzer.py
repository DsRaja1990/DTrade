"""
Sector-Specific Stock Analyzer for BANKNIFTY and FINNIFTY
Analyzes constituent stocks to determine index sentiment
"""

import logging
from typing import Dict, List, Any
from datetime import datetime
import yfinance as yf
import numpy as np

logger = logging.getLogger(__name__)

# BANKNIFTY Constituents (12 stocks) with weightages
BANKNIFTY_STOCKS = {
    'HDFCBANK.NS': {'name': 'HDFC Bank', 'weight': 0.31, 'type': 'Private'},
    'ICICIBANK.NS': {'name': 'ICICI Bank', 'weight': 0.20, 'type': 'Private'},
    'SBIN.NS': {'name': 'State Bank of India', 'weight': 0.18, 'type': 'PSU'},
    'KOTAKBANK.NS': {'name': 'Kotak Mahindra Bank', 'weight': 0.09, 'type': 'Private'},
    'AXISBANK.NS': {'name': 'Axis Bank', 'weight': 0.08, 'type': 'Private'},
    'INDUSINDBK.NS': {'name': 'IndusInd Bank', 'weight': 0.04, 'type': 'Private'},
    'FEDERALBNK.NS': {'name': 'Federal Bank', 'weight': 0.03, 'type': 'Private'},
    'BANKBARODA.NS': {'name': 'Bank of Baroda', 'weight': 0.03, 'type': 'PSU'},
    'PNB.NS': {'name': 'Punjab National Bank', 'weight': 0.03, 'type': 'PSU'},
    'IDFCFIRSTB.NS': {'name': 'IDFC First Bank', 'weight': 0.03, 'type': 'Private'},
    'BANDHANBNK.NS': {'name': 'Bandhan Bank', 'weight': 0.02, 'type': 'Private'},
    'AUBANK.NS': {'name': 'AU Small Finance Bank', 'weight': 0.02, 'type': 'Private'}
}

# FINNIFTY Constituents (20 stocks)
FINNIFTY_STOCKS = {
    # Banks (overlap with BANKNIFTY)
    'HDFCBANK.NS': {'name': 'HDFC Bank', 'weight': 0.20, 'sector': 'Banking'},
    'ICICIBANK.NS': {'name': 'ICICI Bank', 'weight': 0.18, 'sector': 'Banking'},
    'SBIN.NS': {'name': 'State Bank of India', 'weight': 0.10, 'sector': 'Banking'},
    'KOTAKBANK.NS': {'name': 'Kotak Mahindra Bank', 'weight': 0.08, 'sector': 'Banking'},
    'AXISBANK.NS': {'name': 'Axis Bank', 'weight': 0.07, 'sector': 'Banking'},
    
    # NBFCs
    'BAJFINANCE.NS': {'name': 'Bajaj Finance', 'weight': 0.12, 'sector': 'NBFC'},
    'BAJAJFINSV.NS': {'name': 'Bajaj Finserv', 'weight': 0.06, 'sector': 'NBFC'},
    'CHOLAFIN.NS': {'name': 'Cholamandalam Investment', 'weight': 0.03, 'sector': 'NBFC'},
    'SHRIRAMFIN.NS': {'name': 'Shriram Finance', 'weight': 0.03, 'sector': 'NBFC'},
    'MUTHOOTFIN.NS': {'name': 'Muthoot Finance', 'weight': 0.02, 'sector': 'NBFC'},
    'LICHSGFIN.NS': {'name': 'LIC Housing Finance', 'weight': 0.02, 'sector': 'NBFC'},
    
    # Insurance
    'HDFCLIFE.NS': {'name': 'HDFC Life Insurance', 'weight': 0.05, 'sector': 'Insurance'},
    'SBILIFE.NS': {'name': 'SBI Life Insurance', 'weight': 0.04, 'sector': 'Insurance'},
    'ICICIGI.NS': {'name': 'ICICI Lombard GIC', 'weight': 0.03, 'sector': 'Insurance'},
    'ICICIPRULI.NS': {'name': 'ICICI Prudential Life', 'weight': 0.03, 'sector': 'Insurance'},
    
    # Others
    'HDFCAMC.NS': {'name': 'HDFC AMC', 'weight': 0.02, 'sector': 'AMC'},
    'SBICARD.NS': {'name': 'SBI Cards', 'weight': 0.02, 'sector': 'Payments'},
    'PFC.NS': {'name': 'Power Finance Corp', 'weight': 0.02, 'sector': 'NBFC'},
    'RECLTD.NS': {'name': 'REC Limited', 'weight': 0.02, 'sector': 'NBFC'},
    'MCX.NS': {'name': 'MCX', 'weight': 0.01, 'sector': 'Exchange'}
}

class SectorAnalyzer:
    """Analyzes sector-specific stocks for index sentiment"""
    
    def __init__(self):
        self.cache = {}
        self.cache_duration = 300  # 5 minutes
    
    async def analyze_banknifty_stocks(self) -> Dict[str, Any]:
        """
        Analyze BANKNIFTY constituent stocks
        
        Returns:
            Comprehensive analysis of banking sector
        """
        cache_key = "banknifty_analysis"
        
        # Check cache
        if cache_key in self.cache:
            cached_data, cached_time = self.cache[cache_key]
            if (datetime.now() - cached_time).seconds < self.cache_duration:
                return cached_data
        
        try:
            stocks_data = []
            bullish_count = 0
            bearish_count = 0
            neutral_count = 0
            
            weighted_sentiment = 0.0
            psu_sentiment = 0.0
            private_sentiment = 0.0
            
            psu_count = 0
            private_count = 0
            
            for symbol, info in BANKNIFTY_STOCKS.items():
                try:
                    ticker = yf.Ticker(symbol)
                    hist = ticker.history(period="5d")
                    
                    if not hist.empty:
                        current_price = hist['Close'].iloc[-1]
                        prev_close = hist['Close'].iloc[-2] if len(hist) > 1 else current_price
                        change_pct = ((current_price - prev_close) / prev_close * 100)
                        
                        # Calculate RSI
                        rsi = self._calculate_rsi(hist['Close'])
                        
                        # Determine sentiment
                        if change_pct > 0.5 and rsi > 55:
                            sentiment = 'BULLISH'
                            bullish_count += 1
                            sentiment_score = 1.0
                        elif change_pct < -0.5 and rsi < 45:
                            sentiment = 'BEARISH'
                            bearish_count += 1
                            sentiment_score = -1.0
                        else:
                            sentiment = 'NEUTRAL'
                            neutral_count += 1
                            sentiment_score = 0.0
                        
                        # Track PSU vs Private
                        if info['type'] == 'PSU':
                            psu_sentiment += sentiment_score
                            psu_count += 1
                        else:
                            private_sentiment += sentiment_score
                            private_count += 1
                        
                        # Weighted sentiment
                        weighted_sentiment += sentiment_score * info['weight']
                        
                        stocks_data.append({
                            'symbol': symbol.replace('.NS', ''),
                            'name': info['name'],
                            'type': info['type'],
                            'weight': info['weight'],
                            'price': float(current_price),
                            'change_pct': round(change_pct, 2),
                            'rsi': round(rsi, 2),
                            'volume': int(hist['Volume'].iloc[-1]),
                            'sentiment': sentiment
                        })
                
                except Exception as e:
                    logger.error(f"Error fetching {symbol}: {e}")
            
            # Calculate divergence
            psu_avg = psu_sentiment / psu_count if psu_count > 0 else 0
            private_avg = private_sentiment / private_count if private_count > 0 else 0
            
            if psu_avg > 0.3 and private_avg < -0.3:
                divergence = "PSU_UP_PRIVATE_DOWN"
            elif private_avg > 0.3 and psu_avg < -0.3:
                divergence = "PRIVATE_UP_PSU_DOWN"
            elif abs(psu_avg - private_avg) < 0.2:
                divergence = "ALIGNED"
            else:
                divergence = "MIXED"
            
            # Overall bias
            if weighted_sentiment > 0.15:
                bias = "BULLISH"
            elif weighted_sentiment < -0.15:
                bias = "BEARISH"
            else:
                bias = "NEUTRAL"
            
            # Strength score (0-10)
            strength_score = min(10, max(0, 5 + weighted_sentiment * 10))
            
            # Top movers
            sorted_stocks = sorted(stocks_data, key=lambda x: abs(x['change_pct']), reverse=True)
            top_movers = [s['symbol'] for s in sorted_stocks[:3]]
            
            analysis = {
                'index': 'BANKNIFTY',
                'total_stocks': len(stocks_data),
                'bullish_count': bullish_count,
                'bearish_count': bearish_count,
                'neutral_count': neutral_count,
                'weighted_bias': bias,
                'strength_score': round(strength_score, 2),
                'divergence': divergence,
                'psu_sentiment': round(psu_avg, 2),
                'private_sentiment': round(private_avg, 2),
                'top_movers': top_movers,
                'stocks': stocks_data,
                'timestamp': datetime.now().isoformat()
            }
            
            # Cache result
            self.cache[cache_key] = (analysis, datetime.now())
            
            logger.info(f"BANKNIFTY Analysis: {bias} ({bullish_count}B/{bearish_count}B/{neutral_count}N)")
            
            return analysis
        
        except Exception as e:
            logger.error(f"Error analyzing BANKNIFTY stocks: {e}")
            return self._get_fallback_analysis('BANKNIFTY')
    
    async def analyze_finnifty_stocks(self) -> Dict[str, Any]:
        """
        Analyze FINNIFTY constituent stocks
        
        Returns:
            Comprehensive analysis of financial services sector
        """
        cache_key = "finnifty_analysis"
        
        # Check cache
        if cache_key in self.cache:
            cached_data, cached_time = self.cache[cache_key]
            if (datetime.now() - cached_time).seconds < self.cache_duration:
                return cached_data
        
        try:
            stocks_data = []
            bullish_count = 0
            bearish_count = 0
            neutral_count = 0
            
            weighted_sentiment = 0.0
            sector_sentiments = {
                'Banking': 0.0,
                'NBFC': 0.0,
                'Insurance': 0.0,
                'Others': 0.0
            }
            sector_counts = {
                'Banking': 0,
                'NBFC': 0,
                'Insurance': 0,
                'Others': 0
            }
            
            for symbol, info in FINNIFTY_STOCKS.items():
                try:
                    ticker = yf.Ticker(symbol)
                    hist = ticker.history(period="5d")
                    
                    if not hist.empty:
                        current_price = hist['Close'].iloc[-1]
                        prev_close = hist['Close'].iloc[-2] if len(hist) > 1 else current_price
                        change_pct = ((current_price - prev_close) / prev_close * 100)
                        
                        # Calculate RSI
                        rsi = self._calculate_rsi(hist['Close'])
                        
                        # Determine sentiment
                        if change_pct > 0.5 and rsi > 55:
                            sentiment = 'BULLISH'
                            bullish_count += 1
                            sentiment_score = 1.0
                        elif change_pct < -0.5 and rsi < 45:
                            sentiment = 'BEARISH'
                            bearish_count += 1
                            sentiment_score = -1.0
                        else:
                            sentiment = 'NEUTRAL'
                            neutral_count += 1
                            sentiment_score = 0.0
                        
                        # Track sector sentiment
                        sector = info.get('sector', 'Others')
                        if sector in sector_sentiments:
                            sector_sentiments[sector] += sentiment_score
                            sector_counts[sector] += 1
                        
                        # Weighted sentiment
                        weighted_sentiment += sentiment_score * info['weight']
                        
                        stocks_data.append({
                            'symbol': symbol.replace('.NS', ''),
                            'name': info['name'],
                            'sector': sector,
                            'weight': info['weight'],
                            'price': float(current_price),
                            'change_pct': round(change_pct, 2),
                            'rsi': round(rsi, 2),
                            'volume': int(hist['Volume'].iloc[-1]),
                            'sentiment': sentiment
                        })
                
                except Exception as e:
                    logger.error(f"Error fetching {symbol}: {e}")
            
            # Calculate sector averages
            sector_avg = {}
            for sector, total in sector_sentiments.items():
                count = sector_counts[sector]
                sector_avg[sector] = round(total / count, 2) if count > 0 else 0.0
            
            # Identify leading sector
            leading_sector = max(sector_avg, key=sector_avg.get)
            
            # Sector divergence
            if sector_avg['Banking'] > 0.3 and sector_avg['NBFC'] < -0.3:
                divergence = "BANKS_UP_NBFC_DOWN"
            elif sector_avg['NBFC'] > 0.3 and sector_avg['Banking'] < -0.3:
                divergence = "NBFC_UP_BANKS_DOWN"
            elif sector_avg['Insurance'] > 0.5:
                divergence = "INSURANCE_LEADING"
            else:
                divergence = "MIXED"
            
            # Overall bias
            if weighted_sentiment > 0.15:
                bias = "BULLISH"
            elif weighted_sentiment < -0.15:
                bias = "BEARISH"
            else:
                bias = "NEUTRAL"
            
            # Strength score
            strength_score = min(10, max(0, 5 + weighted_sentiment * 10))
            
            # Top movers
            sorted_stocks = sorted(stocks_data, key=lambda x: abs(x['change_pct']), reverse=True)
            top_movers = [s['symbol'] for s in sorted_stocks[:3]]
            
            analysis = {
                'index': 'FINNIFTY',
                'total_stocks': len(stocks_data),
                'bullish_count': bullish_count,
                'bearish_count': bearish_count,
                'neutral_count': neutral_count,
                'weighted_bias': bias,
                'strength_score': round(strength_score, 2),
                'divergence': divergence,
                'leading_sector': leading_sector,
                'sector_sentiments': sector_avg,
                'top_movers': top_movers,
                'stocks': stocks_data,
                'timestamp': datetime.now().isoformat()
            }
            
            # Cache result
            self.cache[cache_key] = (analysis, datetime.now())
            
            logger.info(f"FINNIFTY Analysis: {bias} ({bullish_count}B/{bearish_count}B/{neutral_count}N) - Led by {leading_sector}")
            
            return analysis
        
        except Exception as e:
            logger.error(f"Error analyzing FINNIFTY stocks: {e}")
            return self._get_fallback_analysis('FINNIFTY')
    
    def _calculate_rsi(self, prices, period=14):
        """Calculate RSI indicator"""
        try:
            delta = prices.diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs.iloc[-1]))
            return rsi if not np.isnan(rsi) else 50.0
        except:
            return 50.0
    
    def _get_fallback_analysis(self, index: str) -> Dict:
        """Fallback analysis when data unavailable"""
        return {
            'index': index,
            'total_stocks': 0,
            'bullish_count': 0,
            'bearish_count': 0,
            'neutral_count': 0,
            'weighted_bias': 'NEUTRAL',
            'strength_score': 5.0,
            'divergence': 'UNKNOWN',
            'top_movers': [],
            'stocks': [],
            'timestamp': datetime.now().isoformat(),
            'error': 'Data unavailable'
        }

# Global instance
sector_analyzer = SectorAnalyzer()
