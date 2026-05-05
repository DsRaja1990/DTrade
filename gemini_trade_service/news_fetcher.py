"""
News and Macro Data Fetcher
Fetches FII/DII data, news headlines, and global market sentiment
"""
import aiohttp
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import json
from bs4 import BeautifulSoup
import yfinance as yf

logger = logging.getLogger(__name__)

class NewsFetcher:
    """Fetches news, FII/DII data, and global market sentiment"""
    
    def __init__(self):
        self.cache = {}
        self.cache_duration = 900  # 15 minutes
    
    async def get_fii_dii_data(self) -> Dict[str, Any]:
        """
        Fetch FII/DII data from NSE or cached source
        
        Returns:
            Dictionary with FII/DII net buy/sell data
        """
        cache_key = "fii_dii_data"
        
        # Check cache
        if cache_key in self.cache:
            cached_data, cached_time = self.cache[cache_key]
            if (datetime.now() - cached_time).seconds < self.cache_duration:
                return cached_data
        
        try:
            # NSE website scraping (simplified - in production use official API if available)
            # For MVP, returning sample structure
            data = {
                "date": datetime.now().strftime("%Y-%m-%d"),
                "fii": {
                    "buy_value": 0.0,
                    "sell_value": 0.0,
                    "net_value": 0.0,
                    "sentiment": "NEUTRAL"
                },
                "dii": {
                    "buy_value": 0.0,
                    "sell_value": 0.0,
                    "net_value": 0.0,
                    "sentiment": "NEUTRAL"
                },
                "overall_sentiment": "NEUTRAL"
            }
            
            # Cache the result
            self.cache[cache_key] = (data, datetime.now())
            
            return data
        
        except Exception as e:
            logger.error(f"Error fetching FII/DII data: {e}")
            return {
                "date": datetime.now().strftime("%Y-%m-%d"),
                "fii": {"net_value": 0.0, "sentiment": "NEUTRAL"},
                "dii": {"net_value": 0.0, "sentiment": "NEUTRAL"},
                "overall_sentiment": "NEUTRAL"
            }
    
    async def get_global_market_sentiment(self) -> Dict[str, Any]:
        """
        Fetch global market sentiment (US Futures, Crude Oil, etc.)
        
        Returns:
            Dictionary with global market data
        """
        cache_key = "global_sentiment"
        
        # Check cache
        if cache_key in self.cache:
            cached_data, cached_time = self.cache[cache_key]
            if (datetime.now() - cached_time).seconds < self.cache_duration:
                return cached_data
        
        try:
            # Fetch US Futures (S&P 500 Futures)
            sp_futures = yf.Ticker("ES=F")
            sp_data = sp_futures.history(period="1d")
            
            # Fetch Crude Oil
            crude = yf.Ticker("CL=F")
            crude_data = crude.history(period="1d")
            
            # Calculate changes
            sp_change = 0.0
            crude_change = 0.0
            
            if not sp_data.empty:
                sp_current = sp_data['Close'].iloc[-1]
                sp_prev = sp_data['Open'].iloc[0]
                sp_change = ((sp_current - sp_prev) / sp_prev * 100) if sp_prev > 0 else 0.0
            
            if not crude_data.empty:
                crude_current = crude_data['Close'].iloc[-1]
                crude_prev = crude_data['Open'].iloc[0]
                crude_change = ((crude_current - crude_prev) / crude_prev * 100) if crude_prev > 0 else 0.0
            
            # Determine sentiment
            if sp_change > 0.5:
                us_sentiment = "GREEN"
            elif sp_change < -0.5:
                us_sentiment = "RED"
            else:
                us_sentiment = "MIXED"
            
            data = {
                "us_futures": {
                    "change_pct": round(sp_change, 2),
                    "sentiment": us_sentiment
                },
                "crude_oil": {
                    "change_pct": round(crude_change, 2),
                    "trend": "UP" if crude_change > 1 else "DOWN" if crude_change < -1 else "STABLE"
                },
                "overall_sentiment": us_sentiment,
                "last_updated": datetime.now().isoformat()
            }
            
            # Cache the result
            self.cache[cache_key] = (data, datetime.now())
            
            return data
        
        except Exception as e:
            logger.error(f"Error fetching global market sentiment: {e}")
            return {
                "us_futures": {"change_pct": 0.0, "sentiment": "MIXED"},
                "crude_oil": {"change_pct": 0.0, "trend": "STABLE"},
                "overall_sentiment": "MIXED",
                "last_updated": datetime.now().isoformat()
            }
    
    async def get_global_indices_3day(self) -> Dict[str, Any]:
        """
        Get 3-day performance for global indices (US, Europe, Asia)
        Required for Tier 2 contextual synthesis
        
        Returns:
            Dictionary with 3-day global indices data
        """
        cache_key = "global_indices_3day"
        
        # Check cache
        if cache_key in self.cache:
            cached_data, cached_time = self.cache[cache_key]
            if (datetime.now() - cached_time).seconds < self.cache_duration:
                return cached_data
        
        # Global indices to track
        indices = {
            # US Markets
            "^GSPC": {"name": "S&P 500", "region": "US"},
            "^DJI": {"name": "Dow Jones", "region": "US"},
            "^IXIC": {"name": "Nasdaq", "region": "US"},
            # European Markets
            "^FTSE": {"name": "FTSE 100", "region": "Europe"},
            "^GDAXI": {"name": "DAX", "region": "Europe"},
            "^FCHI": {"name": "CAC 40", "region": "Europe"},
            # Asian Markets
            "^N225": {"name": "Nikkei 225", "region": "Asia"},
            "^HSI": {"name": "Hang Seng", "region": "Asia"},
            "000001.SS": {"name": "Shanghai Composite", "region": "Asia"}
        }
        
        result = {
            "us": {"trend": "NEUTRAL", "avg_change_3d": 0.0, "indices": []},
            "europe": {"trend": "NEUTRAL", "avg_change_3d": 0.0, "indices": []},
            "asia": {"trend": "NEUTRAL", "avg_change_3d": 0.0, "indices": []},
            "global_trend": "NEUTRAL"
        }
        
        regional_changes = {"US": [], "Europe": [], "Asia": []}
        
        try:
            for symbol, info in indices.items():
                try:
                    ticker = yf.Ticker(symbol)
                    hist = ticker.history(period="5d")
                    
                    if not hist.empty and len(hist) >= 3:
                        closes = hist['Close'].tolist()
                        # 3-day change (current vs 3 days ago)
                        change_3d = ((closes[-1] - closes[-4]) / closes[-4] * 100) if len(closes) > 3 else 0.0
                        # Today's change
                        change_1d = ((closes[-1] - closes[-2]) / closes[-2] * 100) if len(closes) > 1 else 0.0
                        
                        index_data = {
                            "name": info["name"],
                            "current": round(float(closes[-1]), 2),
                            "change_1d": round(change_1d, 2),
                            "change_3d": round(change_3d, 2),
                            "trend": "BULLISH" if change_3d > 1 else "BEARISH" if change_3d < -1 else "NEUTRAL"
                        }
                        
                        region_key = info["region"].lower()
                        result[region_key]["indices"].append(index_data)
                        regional_changes[info["region"]].append(change_3d)
                        
                except Exception as idx_error:
                    logger.warning(f"Error fetching {symbol}: {idx_error}")
            
            # Calculate regional averages
            for region, changes in regional_changes.items():
                if changes:
                    avg_change = sum(changes) / len(changes)
                    region_key = region.lower()
                    result[region_key]["avg_change_3d"] = round(avg_change, 2)
                    if avg_change > 1:
                        result[region_key]["trend"] = "BULLISH"
                    elif avg_change < -1:
                        result[region_key]["trend"] = "BEARISH"
                    else:
                        result[region_key]["trend"] = "NEUTRAL"
            
            # Calculate global trend
            all_changes = []
            for changes in regional_changes.values():
                all_changes.extend(changes)
            
            if all_changes:
                global_avg = sum(all_changes) / len(all_changes)
                if global_avg > 1:
                    result["global_trend"] = "BULLISH"
                elif global_avg < -1:
                    result["global_trend"] = "BEARISH"
                else:
                    result["global_trend"] = "NEUTRAL"
            
            result["timestamp"] = datetime.now().isoformat()
            
            # Cache the result
            self.cache[cache_key] = (result, datetime.now())
            
            return result
            
        except Exception as e:
            logger.error(f"Error fetching global indices: {e}")
            return result
    
    async def get_enhanced_fii_dii_data(self) -> Dict[str, Any]:
        """
        Fetch enhanced FII/DII data with multi-day trends
        Required for Tier 2 contextual synthesis
        
        Returns:
            Dictionary with detailed FII/DII data including 5-day trend
        """
        cache_key = "fii_dii_enhanced"
        
        # Check cache
        if cache_key in self.cache:
            cached_data, cached_time = self.cache[cache_key]
            if (datetime.now() - cached_time).seconds < self.cache_duration:
                return cached_data
        
        # Note: In production, scrape from NSE or use official API
        # For now, providing structured template
        try:
            data = {
                "date": datetime.now().strftime("%Y-%m-%d"),
                "fii": {
                    "today_net": 0.0,  # In crores
                    "5_day_net": 0.0,
                    "10_day_net": 0.0,
                    "trend": "NEUTRAL",  # BUYING | SELLING | NEUTRAL
                    "sentiment": "NEUTRAL"
                },
                "dii": {
                    "today_net": 0.0,
                    "5_day_net": 0.0,
                    "10_day_net": 0.0,
                    "trend": "NEUTRAL",
                    "sentiment": "NEUTRAL"
                },
                "combined": {
                    "net_flow": 0.0,
                    "dominant_player": "NONE",  # FII | DII | BALANCED
                    "market_implication": "Markets likely to remain range-bound with mixed institutional flows"
                },
                "timestamp": datetime.now().isoformat()
            }
            
            # Cache the result
            self.cache[cache_key] = (data, datetime.now())
            
            return data
            
        except Exception as e:
            logger.error(f"Error fetching enhanced FII/DII: {e}")
            return {
                "date": datetime.now().strftime("%Y-%m-%d"),
                "fii": {"today_net": 0.0, "trend": "NEUTRAL"},
                "dii": {"today_net": 0.0, "trend": "NEUTRAL"},
                "combined": {"dominant_player": "NONE"}
            }
    
    async def get_news_headlines(self, count: int = 5) -> List[Dict[str, str]]:
        """
        Fetch recent news headlines
        
        Args:
            count: Number of headlines to fetch
        
        Returns:
            List of news headlines with sentiment
        """
        cache_key = "news_headlines"
        
        # Check cache
        if cache_key in self.cache:
            cached_data, cached_time = self.cache[cache_key]
            if (datetime.now() - cached_time).seconds < self.cache_duration:
                return cached_data
        
        try:
            # In production, integrate with news APIs like NewsAPI, MoneyControl RSS, etc.
            # For MVP, returning sample structure
            headlines = [
                {
                    "title": "Markets show mixed signals amid global uncertainty",
                    "sentiment": "NEUTRAL",
                    "source": "Economic Times",
                    "timestamp": datetime.now().isoformat()
                }
            ]
            
            # Cache the result
            self.cache[cache_key] = (headlines, datetime.now())
            
            return headlines
        
        except Exception as e:
            logger.error(f"Error fetching news headlines: {e}")
            return []
    
    async def get_india_vix_change(self) -> Dict[str, float]:
        """
        Get India VIX change percentage
        
        Returns:
            Dictionary with VIX data
        """
        cache_key = "vix_change"
        
        # Check cache
        if cache_key in self.cache:
            cached_data, cached_time = self.cache[cache_key]
            if (datetime.now() - cached_time).seconds < 300:  # 5 min cache
                return cached_data
        
        try:
            # Fetch India VIX from yfinance
            vix = yf.Ticker("^INDIAVIX")
            vix_data = vix.history(period="2d")
            
            if len(vix_data) < 2:
                return {"current": 15.0, "change_pct": 0.0, "trend": "STABLE"}
            
            current_vix = vix_data['Close'].iloc[-1]
            prev_vix = vix_data['Close'].iloc[-2]
            change_pct = ((current_vix - prev_vix) / prev_vix * 100) if prev_vix > 0 else 0.0
            
            # Determine trend
            if change_pct > 5:
                trend = "SPIKING"
            elif change_pct > 3:
                trend = "RISING"
            elif change_pct < -5:
                trend = "CRUSHING"
            elif change_pct < -3:
                trend = "FALLING"
            else:
                trend = "STABLE"
            
            data = {
                "current": round(current_vix, 2),
                "change_pct": round(change_pct, 2),
                "trend": trend
            }
            
            # Cache the result
            self.cache[cache_key] = (data, datetime.now())
            
            return data
        
        except Exception as e:
            logger.error(f"Error fetching VIX data: {e}")
            return {"current": 15.0, "change_pct": 0.0, "trend": "STABLE"}
    
    async def get_comprehensive_macro_data(self) -> Dict[str, Any]:
        """
        Get comprehensive macro data for Tier 2 and Tier 3 analysis
        Includes: FII/DII, Global Indices 3-day, VIX, News
        
        Returns:
            Dictionary with all macro data for AI processing
        """
        try:
            # Fetch all data concurrently
            fii_dii_task = self.get_enhanced_fii_dii_data()
            global_task = self.get_global_market_sentiment()
            global_indices_task = self.get_global_indices_3day()
            news_task = self.get_news_headlines(count=3)
            vix_task = self.get_india_vix_change()
            
            fii_dii, global_sentiment, global_indices, news, vix = await asyncio.gather(
                fii_dii_task,
                global_task,
                global_indices_task,
                news_task,
                vix_task
            )
            
            return {
                "fii_dii": fii_dii,
                "global_markets": global_sentiment,
                "global_indices_3day": global_indices,
                "news_headlines": news,
                "india_vix": vix,
                "summary": self._generate_summary(fii_dii, global_sentiment, vix),
                "tier2_context": self._generate_tier2_context(fii_dii, global_indices, vix),
                "timestamp": datetime.now().isoformat()
            }
        
        except Exception as e:
            logger.error(f"Error getting comprehensive macro data: {e}")
            return {
                "fii_dii": {},
                "global_markets": {},
                "global_indices_3day": {},
                "news_headlines": [],
                "india_vix": {},
                "summary": "Data unavailable",
                "tier2_context": {}
            }
    
    def _generate_tier2_context(self, fii_dii: Dict, global_indices: Dict, vix: Dict) -> Dict:
        """
        Generate structured context for Tier 2 AI processing
        """
        context = {
            "institutional_flow": "NEUTRAL",
            "global_trend": global_indices.get("global_trend", "NEUTRAL"),
            "volatility_regime": "NORMAL",
            "market_bias": "NEUTRAL"
        }
        
        # Determine institutional flow direction
        fii_trend = fii_dii.get("fii", {}).get("trend", "NEUTRAL")
        dii_trend = fii_dii.get("dii", {}).get("trend", "NEUTRAL")
        
        if fii_trend == "BUYING" and dii_trend == "BUYING":
            context["institutional_flow"] = "STRONGLY_BULLISH"
        elif fii_trend == "BUYING":
            context["institutional_flow"] = "BULLISH"
        elif fii_trend == "SELLING" and dii_trend == "SELLING":
            context["institutional_flow"] = "STRONGLY_BEARISH"
        elif fii_trend == "SELLING":
            context["institutional_flow"] = "BEARISH"
        
        # Determine volatility regime
        vix_current = vix.get("current", 15.0)
        vix_trend = vix.get("trend", "STABLE")
        
        if vix_current > 25 or vix_trend == "SPIKING":
            context["volatility_regime"] = "HIGH"
        elif vix_current < 12 and vix_trend in ["STABLE", "FALLING", "CRUSHING"]:
            context["volatility_regime"] = "LOW"
        else:
            context["volatility_regime"] = "NORMAL"
        
        # Determine overall market bias
        global_trend = global_indices.get("global_trend", "NEUTRAL")
        inst_flow = context["institutional_flow"]
        
        bullish_signals = 0
        bearish_signals = 0
        
        if global_trend == "BULLISH":
            bullish_signals += 1
        elif global_trend == "BEARISH":
            bearish_signals += 1
        
        if inst_flow in ["BULLISH", "STRONGLY_BULLISH"]:
            bullish_signals += 1
        elif inst_flow in ["BEARISH", "STRONGLY_BEARISH"]:
            bearish_signals += 1
        
        if context["volatility_regime"] == "LOW":
            bullish_signals += 0.5  # Low VIX generally bullish
        elif context["volatility_regime"] == "HIGH":
            bearish_signals += 0.5  # High VIX generally bearish/uncertain
        
        if bullish_signals > bearish_signals + 0.5:
            context["market_bias"] = "BULLISH"
        elif bearish_signals > bullish_signals + 0.5:
            context["market_bias"] = "BEARISH"
        else:
            context["market_bias"] = "NEUTRAL"
        
        return context
    
    def _generate_summary(self, fii_dii: Dict, global_sentiment: Dict, vix: Dict) -> str:
        """Generate human-readable summary"""
        summary_parts = []
        
        # FII/DII
        if fii_dii.get("overall_sentiment") == "BULLISH":
            summary_parts.append("FII/DII are net buyers")
        elif fii_dii.get("overall_sentiment") == "BEARISH":
            summary_parts.append("FII/DII are net sellers")
        
        # Global markets
        us_sent = global_sentiment.get("overall_sentiment", "MIXED")
        if us_sent == "GREEN":
            summary_parts.append("US markets are positive")
        elif us_sent == "RED":
            summary_parts.append("US markets are negative")
        
        # VIX
        vix_trend = vix.get("trend", "STABLE")
        if vix_trend in ["SPIKING", "RISING"]:
            summary_parts.append(f"VIX is {vix_trend.lower()}")
        
        return ". ".join(summary_parts) + "." if summary_parts else "Markets are quiet"

# Global instance
news_fetcher = NewsFetcher()
