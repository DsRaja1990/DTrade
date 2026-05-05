"""
================================================================================
    DHAN MARKET DATA CLIENT FOR SIGNAL ENGINE
    Real-time market data subscription using DhanHQ API
    
    Features:
    - REST API for market quotes
    - WebSocket subscription for real-time data
    - Multi-instrument support (NIFTY, BANKNIFTY, SENSEX)
    - Historical data fetching for technical analysis
    - Token management and refresh
================================================================================
"""

import asyncio
import json
import logging
import os
import aiohttp
import websockets
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, asdict
from enum import Enum
import threading

# Configure logging
logger = logging.getLogger(__name__)


class Exchange(Enum):
    NSE = "NSE"
    BSE = "BSE"
    MCX = "MCX"
    NSE_FO = "NSE_FO"
    BSE_FO = "BSE_FO"


@dataclass
class MarketQuote:
    """Real-time market quote"""
    instrument: str
    security_id: str
    exchange: str
    ltp: float
    open: float
    high: float
    low: float
    close: float
    volume: int
    bid: float
    ask: float
    oi: int
    change: float
    change_percent: float
    timestamp: str
    
    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class HistoricalCandle:
    """OHLCV candle data"""
    timestamp: str
    open: float
    high: float
    low: float
    close: float
    volume: int


class DhanMarketDataClient:
    """
    Dhan Market Data Client for Signal Engine
    Provides real-time and historical market data
    """
    
    # API Endpoints
    BASE_URL = "https://api.dhan.co/v2"
    WS_URL = "wss://api-feed.dhan.co"
    
    # Segment IDs
    SEGMENTS = {
        "NSE": "NSE_EQ",
        "BSE": "BSE_EQ",
        "NSE_FO": "NSE_FO",
        "BSE_FO": "BSE_FO",
        "MCX": "MCX_COMM"
    }
    
    def __init__(self, config_path: str = None):
        """Initialize Dhan market data client"""
        self.config_path = config_path or os.path.join(
            os.path.dirname(__file__), "config", "dhan_config.json"
        )
        self.config = self._load_config()
        
        # API credentials
        self.access_token = self.config.get("access_token", "")
        self.client_id = self.config.get("client_id", "")
        
        # Instrument mappings
        self.instruments = self.config.get("instruments", {})
        
        # WebSocket state
        self._ws_connection = None
        self._ws_running = False
        self._subscriptions: Dict[str, Callable] = {}
        
        # Cache for quotes
        self._quote_cache: Dict[str, MarketQuote] = {}
        self._last_update: Dict[str, datetime] = {}
        
        # Session
        self._session: Optional[aiohttp.ClientSession] = None
        
        logger.info(f"DhanMarketDataClient initialized with {len(self.instruments)} instruments")
    
    def _load_config(self) -> Dict:
        """Load configuration from JSON file"""
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r') as f:
                    return json.load(f)
            else:
                logger.warning(f"Config file not found: {self.config_path}")
                return {}
        except Exception as e:
            logger.error(f"Error loading config: {e}")
            return {}
    
    def reload_config(self) -> Dict:
        """Reload configuration (useful after token update)"""
        self.config = self._load_config()
        self.access_token = self.config.get("access_token", "")
        self.client_id = self.config.get("client_id", "")
        logger.info("Configuration reloaded")
        return self.config
    
    def update_token(self, new_token: str) -> bool:
        """Update access token in config file"""
        try:
            self.config["access_token"] = new_token
            self.config["dhan_access_token"] = new_token
            self.access_token = new_token
            
            with open(self.config_path, 'w') as f:
                json.dump(self.config, f, indent=4)
            
            logger.info("Access token updated successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to update token: {e}")
            return False
    
    def get_token(self) -> str:
        """Get current access token"""
        return self.access_token
    
    @property
    def _headers(self) -> Dict[str, str]:
        """Get API headers with authentication"""
        return {
            "access-token": self.access_token,
            "client-id": self.client_id,
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
    
    async def _ensure_session(self):
        """Ensure aiohttp session exists"""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
    
    async def close(self):
        """Close client and cleanup resources"""
        self._ws_running = False
        
        if self._ws_connection:
            await self._ws_connection.close()
            self._ws_connection = None
        
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None
        
        logger.info("DhanMarketDataClient closed")
    
    # =========================================================================
    #                     REST API METHODS
    # =========================================================================
    
    async def get_market_quote(self, instrument: str) -> Optional[MarketQuote]:
        """
        Get market quote for an instrument
        
        Args:
            instrument: Instrument name (NIFTY, BANKNIFTY, SENSEX)
        
        Returns:
            MarketQuote object or None if failed
        """
        await self._ensure_session()
        
        if instrument not in self.instruments:
            logger.warning(f"Unknown instrument: {instrument}")
            return None
        
        inst_config = self.instruments[instrument]
        security_id = inst_config["security_id"]
        exchange = inst_config["exchange"]
        
        try:
            url = f"{self.BASE_URL}/marketfeed/ltp"
            payload = {
                "NSE_EQ" if exchange == "NSE" else "BSE_EQ": [security_id]
            }
            
            async with self._session.post(
                url, headers=self._headers, json=payload, timeout=10
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    # Parse response
                    if data.get("status") == "success" and "data" in data:
                        quote_data = data["data"].get(security_id, {})
                        
                        quote = MarketQuote(
                            instrument=instrument,
                            security_id=security_id,
                            exchange=exchange,
                            ltp=float(quote_data.get("last_price", 0)),
                            open=float(quote_data.get("open_price", 0)),
                            high=float(quote_data.get("high_price", 0)),
                            low=float(quote_data.get("low_price", 0)),
                            close=float(quote_data.get("close_price", 0)),
                            volume=int(quote_data.get("volume", 0)),
                            bid=float(quote_data.get("bid_price", 0)),
                            ask=float(quote_data.get("ask_price", 0)),
                            oi=int(quote_data.get("oi", 0)),
                            change=float(quote_data.get("change", 0)),
                            change_percent=float(quote_data.get("change_percent", 0)),
                            timestamp=datetime.now().isoformat()
                        )
                        
                        # Cache the quote
                        self._quote_cache[instrument] = quote
                        self._last_update[instrument] = datetime.now()
                        
                        return quote
                else:
                    logger.warning(f"API error {response.status}: {await response.text()}")
                    
        except asyncio.TimeoutError:
            logger.warning(f"Timeout fetching quote for {instrument}")
        except Exception as e:
            logger.error(f"Error fetching quote for {instrument}: {e}")
        
        # Return cached quote if available
        return self._quote_cache.get(instrument)
    
    async def get_all_quotes(self) -> Dict[str, MarketQuote]:
        """Get quotes for all configured instruments"""
        quotes = {}
        for instrument in self.instruments:
            quote = await self.get_market_quote(instrument)
            if quote:
                quotes[instrument] = quote
        return quotes
    
    async def get_historical_data(
        self,
        instrument: str,
        interval: str = "1",  # 1, 5, 15, 60 minutes
        days: int = 5
    ) -> List[HistoricalCandle]:
        """
        Get historical OHLCV data for technical analysis
        
        Args:
            instrument: Instrument name
            interval: Candle interval in minutes (1, 5, 15, 60)
            days: Number of days of historical data
        
        Returns:
            List of HistoricalCandle objects
        """
        await self._ensure_session()
        
        if instrument not in self.instruments:
            logger.warning(f"Unknown instrument: {instrument}")
            return []
        
        inst_config = self.instruments[instrument]
        security_id = inst_config["security_id"]
        exchange = inst_config["exchange"]
        
        try:
            url = f"{self.BASE_URL}/charts/intraday"
            
            # Calculate date range
            to_date = datetime.now()
            from_date = to_date - timedelta(days=days)
            
            payload = {
                "securityId": security_id,
                "exchangeSegment": "NSE_EQ" if exchange == "NSE" else "BSE_EQ",
                "instrument": "INDEX",
                "interval": interval,
                "fromDate": from_date.strftime("%Y-%m-%d"),
                "toDate": to_date.strftime("%Y-%m-%d")
            }
            
            async with self._session.post(
                url, headers=self._headers, json=payload, timeout=15
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    candles = []
                    if "data" in data:
                        for candle in data["data"]:
                            candles.append(HistoricalCandle(
                                timestamp=candle.get("timestamp", ""),
                                open=float(candle.get("open", 0)),
                                high=float(candle.get("high", 0)),
                                low=float(candle.get("low", 0)),
                                close=float(candle.get("close", 0)),
                                volume=int(candle.get("volume", 0))
                            ))
                    
                    logger.info(f"Fetched {len(candles)} candles for {instrument}")
                    return candles
                else:
                    logger.warning(f"Historical API error: {response.status}")
                    
        except Exception as e:
            logger.error(f"Error fetching historical data: {e}")
        
        return []
    
    async def get_option_chain(
        self,
        underlying: str,
        expiry_date: str = None
    ) -> Dict[str, Any]:
        """
        Get option chain data for index options
        
        Args:
            underlying: NIFTY or BANKNIFTY
            expiry_date: Expiry date in YYYY-MM-DD format
        
        Returns:
            Option chain data dictionary
        """
        await self._ensure_session()
        
        try:
            url = f"{self.BASE_URL}/option/chain"
            
            payload = {
                "underlying": underlying,
                "expiryDate": expiry_date or self._get_nearest_expiry()
            }
            
            async with self._session.post(
                url, headers=self._headers, json=payload, timeout=15
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    return data
                else:
                    logger.warning(f"Option chain API error: {response.status}")
                    
        except Exception as e:
            logger.error(f"Error fetching option chain: {e}")
        
        return {}
    
    def _get_nearest_expiry(self) -> str:
        """Get nearest weekly expiry date (Thursday)"""
        today = datetime.now()
        days_until_thursday = (3 - today.weekday()) % 7
        if days_until_thursday == 0 and today.hour >= 15:
            days_until_thursday = 7
        expiry = today + timedelta(days=days_until_thursday)
        return expiry.strftime("%Y-%m-%d")
    
    # =========================================================================
    #                     WEBSOCKET STREAMING
    # =========================================================================
    
    async def start_websocket(self, callback: Callable[[Dict], None]):
        """
        Start WebSocket connection for real-time data
        
        Args:
            callback: Function to call when new data arrives
        """
        self._ws_running = True
        
        while self._ws_running:
            try:
                async with websockets.connect(
                    self.WS_URL,
                    extra_headers={
                        "Authorization": f"Bearer {self.access_token}",
                        "client-id": self.client_id
                    }
                ) as ws:
                    self._ws_connection = ws
                    logger.info("WebSocket connected to Dhan")
                    
                    # Subscribe to instruments
                    await self._subscribe_instruments(ws)
                    
                    # Listen for messages
                    async for message in ws:
                        try:
                            data = json.loads(message)
                            
                            # Update cache
                            if "security_id" in data:
                                self._update_cache_from_ws(data)
                            
                            # Call callback
                            if callback:
                                callback(data)
                                
                        except json.JSONDecodeError:
                            logger.warning("Invalid WebSocket message")
                            
            except websockets.exceptions.ConnectionClosed:
                logger.warning("WebSocket disconnected, reconnecting...")
                await asyncio.sleep(5)
            except Exception as e:
                logger.error(f"WebSocket error: {e}")
                await asyncio.sleep(5)
    
    async def _subscribe_instruments(self, ws):
        """Subscribe to instrument feeds"""
        for instrument, config in self.instruments.items():
            subscribe_msg = {
                "RequestCode": 21,  # Subscribe
                "InstrumentCount": 1,
                "InstrumentList": [{
                    "ExchangeSegment": "NSE_EQ" if config["exchange"] == "NSE" else "BSE_EQ",
                    "SecurityId": config["security_id"]
                }]
            }
            await ws.send(json.dumps(subscribe_msg))
            logger.info(f"Subscribed to {instrument}")
    
    def _update_cache_from_ws(self, data: Dict):
        """Update quote cache from WebSocket data"""
        security_id = str(data.get("security_id", ""))
        
        # Find instrument by security_id
        for instrument, config in self.instruments.items():
            if config["security_id"] == security_id:
                quote = MarketQuote(
                    instrument=instrument,
                    security_id=security_id,
                    exchange=config["exchange"],
                    ltp=float(data.get("ltp", 0)),
                    open=float(data.get("open", 0)),
                    high=float(data.get("high", 0)),
                    low=float(data.get("low", 0)),
                    close=float(data.get("close", 0)),
                    volume=int(data.get("volume", 0)),
                    bid=float(data.get("bid", 0)),
                    ask=float(data.get("ask", 0)),
                    oi=int(data.get("oi", 0)),
                    change=float(data.get("change", 0)),
                    change_percent=float(data.get("change_percent", 0)),
                    timestamp=datetime.now().isoformat()
                )
                self._quote_cache[instrument] = quote
                self._last_update[instrument] = datetime.now()
                break
    
    def stop_websocket(self):
        """Stop WebSocket connection"""
        self._ws_running = False
        logger.info("WebSocket stopped")
    
    # =========================================================================
    #                     UTILITY METHODS
    # =========================================================================
    
    def get_cached_quote(self, instrument: str) -> Optional[MarketQuote]:
        """Get cached quote without API call"""
        return self._quote_cache.get(instrument)
    
    def get_all_cached_quotes(self) -> Dict[str, MarketQuote]:
        """Get all cached quotes"""
        return self._quote_cache.copy()
    
    def is_cache_fresh(self, instrument: str, max_age_seconds: int = 5) -> bool:
        """Check if cached quote is fresh"""
        if instrument not in self._last_update:
            return False
        age = (datetime.now() - self._last_update[instrument]).total_seconds()
        return age < max_age_seconds
    
    def is_market_open(self) -> bool:
        """Check if market is currently open (9:15 AM - 3:30 PM IST)"""
        now = datetime.now()
        
        # Check if weekday
        if now.weekday() >= 5:  # Saturday or Sunday
            return False
        
        # Market hours (IST)
        market_open = now.replace(hour=9, minute=15, second=0, microsecond=0)
        market_close = now.replace(hour=15, minute=30, second=0, microsecond=0)
        
        return market_open <= now <= market_close


# Singleton instance
_dhan_client: Optional[DhanMarketDataClient] = None


def get_dhan_client() -> DhanMarketDataClient:
    """Get singleton Dhan market data client"""
    global _dhan_client
    if _dhan_client is None:
        _dhan_client = DhanMarketDataClient()
    return _dhan_client


# =========================================================================
#                     TESTING
# =========================================================================

if __name__ == "__main__":
    import asyncio
    
    async def test():
        client = get_dhan_client()
        
        print("\n=== Testing Dhan Market Data Client ===\n")
        
        # Test get quote
        print("Fetching NIFTY quote...")
        quote = await client.get_market_quote("NIFTY")
        if quote:
            print(f"  LTP: {quote.ltp}")
            print(f"  Change: {quote.change_percent}%")
        else:
            print("  Failed to fetch quote")
        
        # Test historical data
        print("\nFetching historical data...")
        candles = await client.get_historical_data("NIFTY", interval="5", days=1)
        print(f"  Fetched {len(candles)} candles")
        
        await client.close()
        print("\n=== Test Complete ===")
    
    asyncio.run(test())
