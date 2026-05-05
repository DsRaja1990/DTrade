"""
Enhanced Real Market Data Client with Database Integration
Fetches live data and stores to SQLite for analysis
"""

import asyncio
import aiohttp
import logging
from datetime import datetime, date, time, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
import json
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.models import (
    ScalpingDatabase, get_database, MarketTick, MomentumSnapshot, Signal
)

logger = logging.getLogger(__name__)


@dataclass
class LiveQuote:
    """Live market quote"""
    security_id: str
    symbol: str
    instrument: str  # NIFTY, BANKNIFTY, etc.
    quote_type: str  # INDEX, CE, PE
    strike: float = 0.0
    expiry: Optional[date] = None
    ltp: float = 0.0
    open: float = 0.0
    high: float = 0.0
    low: float = 0.0
    close: float = 0.0
    volume: int = 0
    oi: int = 0
    bid: float = 0.0
    ask: float = 0.0
    bid_qty: int = 0
    ask_qty: int = 0
    change: float = 0.0
    change_pct: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)


class RealMarketDataClient:
    """
    Real-time market data client using Dhan API
    - Fetches live quotes, option chains
    - Stores data to SQLite for analysis
    - Supports streaming mode for continuous updates
    """
    
    # Dhan security IDs for indices
    INDEX_SECURITY_IDS = {
        "NIFTY": "26000",
        "BANKNIFTY": "26009",
        "FINNIFTY": "26037",
        "SENSEX": "1",
        "BANKEX": "12"
    }
    
    # Exchange segments
    SEGMENTS = {
        "NIFTY": "NSE_EQ",
        "BANKNIFTY": "NSE_EQ",
        "FINNIFTY": "NSE_EQ",
        "SENSEX": "BSE_EQ",
        "BANKEX": "BSE_EQ"
    }
    
    FNO_SEGMENTS = {
        "NIFTY": "NSE_FNO",
        "BANKNIFTY": "NSE_FNO",
        "FINNIFTY": "NSE_FNO",
        "SENSEX": "BSE_FNO",
        "BANKEX": "BSE_FNO"
    }
    
    # Strike gaps for each index
    STRIKE_GAPS = {
        "NIFTY": 50,
        "BANKNIFTY": 100,
        "FINNIFTY": 50,
        "SENSEX": 100,
        "BANKEX": 100
    }
    
    # Lot sizes
    LOT_SIZES = {
        "NIFTY": 75,
        "BANKNIFTY": 35,
        "FINNIFTY": 65,
        "SENSEX": 20,
        "BANKEX": 30
    }
    
    def __init__(self, access_token: str, client_id: str, store_to_db: bool = True):
        self.access_token = access_token
        self.client_id = client_id
        self.base_url = "https://api.dhan.co/v2"
        self.store_to_db = store_to_db
        
        self._session: Optional[aiohttp.ClientSession] = None
        self._headers = {
            "access-token": access_token,
            "client-id": client_id,
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        
        # Quote cache
        self._quotes: Dict[str, LiveQuote] = {}
        self._option_chains: Dict[str, List[LiveQuote]] = {}
        self._last_update: Dict[str, datetime] = {}
        
        # Database
        self._db: Optional[ScalpingDatabase] = None
        if store_to_db:
            self._db = get_database()
        
        # Tick buffer for batch inserts
        self._tick_buffer: List[MarketTick] = []
        self._buffer_size = 100
        
        logger.info(f"RealMarketDataClient initialized for client {client_id}")
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create HTTP session"""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(headers=self._headers)
        return self._session
    
    async def close(self):
        """Close HTTP session and flush buffer"""
        await self._flush_tick_buffer()
        if self._session and not self._session.closed:
            await self._session.close()
    
    async def _request(self, method: str, endpoint: str, data: Dict = None) -> Dict:
        """Make API request with error handling"""
        session = await self._get_session()
        url = f"{self.base_url}/{endpoint}"
        
        try:
            if method == "GET":
                async with session.get(url, params=data, timeout=10) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        error = await response.text()
                        logger.warning(f"API {response.status}: {error[:200]}")
                        return {"error": error, "status": response.status}
            else:
                async with session.post(url, json=data, timeout=10) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        error = await response.text()
                        logger.warning(f"API {response.status}: {error[:200]}")
                        return {"error": error, "status": response.status}
        except asyncio.TimeoutError:
            logger.error(f"Request timeout: {endpoint}")
            return {"error": "timeout"}
        except Exception as e:
            logger.error(f"Request error: {e}")
            return {"error": str(e)}
    
    async def _flush_tick_buffer(self):
        """Flush tick buffer to database"""
        if self._tick_buffer and self._db:
            try:
                self._db.insert_ticks_batch(self._tick_buffer)
                logger.debug(f"Flushed {len(self._tick_buffer)} ticks to database")
                self._tick_buffer = []
            except Exception as e:
                logger.error(f"Error flushing ticks: {e}")
    
    def _store_tick(self, quote: LiveQuote):
        """Store tick to buffer"""
        if not self._db:
            return
        
        tick = MarketTick(
            timestamp=quote.timestamp,
            instrument=quote.instrument,
            symbol=quote.symbol,
            ltp=quote.ltp,
            open=quote.open,
            high=quote.high,
            low=quote.low,
            close=quote.close,
            volume=quote.volume,
            oi=quote.oi,
            bid=quote.bid,
            ask=quote.ask,
            bid_qty=quote.bid_qty,
            ask_qty=quote.ask_qty
        )
        
        self._tick_buffer.append(tick)
        
        if len(self._tick_buffer) >= self._buffer_size:
            asyncio.create_task(self._flush_tick_buffer())
    
    async def get_index_quote(self, symbol: str) -> Optional[LiveQuote]:
        """Get live quote for an index"""
        security_id = self.INDEX_SECURITY_IDS.get(symbol)
        if not security_id:
            logger.warning(f"Unknown index: {symbol}")
            return None
        
        segment = self.SEGMENTS.get(symbol, "NSE_EQ")
        
        try:
            # Get LTP
            ltp_data = await self._request("POST", "marketfeed/ltp", {segment: [security_id]})
            
            if "data" in ltp_data and security_id in ltp_data.get("data", {}):
                quote_data = ltp_data["data"][security_id]
                
                quote = LiveQuote(
                    security_id=security_id,
                    symbol=symbol,
                    instrument=symbol,
                    quote_type="INDEX",
                    ltp=quote_data.get("last_price", 0),
                    timestamp=datetime.now()
                )
                
                self._quotes[f"{symbol}_INDEX"] = quote
                self._last_update[f"{symbol}_INDEX"] = datetime.now()
                
                if self.store_to_db:
                    self._store_tick(quote)
                
                return quote
            else:
                logger.warning(f"No data for {symbol}: {ltp_data}")
                
        except Exception as e:
            logger.error(f"Error getting index quote {symbol}: {e}")
        
        return None
    
    async def get_option_chain(self, symbol: str, expiry: date = None, 
                                strikes_around_atm: int = 5) -> List[LiveQuote]:
        """
        Get option chain around ATM
        
        Args:
            symbol: Index symbol
            expiry: Expiry date (defaults to nearest)
            strikes_around_atm: Number of strikes above/below ATM
        """
        # Get spot price first
        index_quote = await self.get_index_quote(symbol)
        if not index_quote:
            return []
        
        spot = index_quote.ltp
        gap = self.STRIKE_GAPS.get(symbol, 50)
        atm_strike = round(spot / gap) * gap
        
        if expiry is None:
            expiry = self._get_nearest_expiry(symbol)
        
        segment = self.FNO_SEGMENTS.get(symbol, "NSE_FNO")
        
        # Build list of option security IDs to fetch
        # Note: We need to get security IDs from option chain API
        options = []
        
        try:
            # Get option chain from Dhan
            result = await self._request("POST", "optionchain", {
                "UnderlyingScrip": self.INDEX_SECURITY_IDS.get(symbol),
                "ExpiryDate": expiry.strftime("%Y-%m-%d")
            })
            
            if "data" in result:
                for chain_item in result.get("data", []):
                    strike = chain_item.get("strike", 0)
                    
                    # Only get strikes around ATM
                    if abs(strike - atm_strike) > (strikes_around_atm * gap):
                        continue
                    
                    for opt_type in ["CE", "PE"]:
                        opt_data = chain_item.get(opt_type, {})
                        if opt_data:
                            quote = LiveQuote(
                                security_id=str(opt_data.get("securityId", "")),
                                symbol=f"{symbol}{expiry.strftime('%d%b%y').upper()}{strike}{opt_type}",
                                instrument=symbol,
                                quote_type=opt_type,
                                strike=strike,
                                expiry=expiry,
                                ltp=opt_data.get("lastPrice", 0),
                                open=opt_data.get("open", 0),
                                high=opt_data.get("high", 0),
                                low=opt_data.get("low", 0),
                                close=opt_data.get("close", 0),
                                volume=opt_data.get("volume", 0),
                                oi=opt_data.get("openInterest", 0),
                                bid=opt_data.get("bestBidPrice", 0),
                                ask=opt_data.get("bestAskPrice", 0),
                                timestamp=datetime.now()
                            )
                            options.append(quote)
                            
                            if self.store_to_db:
                                self._store_tick(quote)
                
                self._option_chains[symbol] = options
                self._last_update[f"{symbol}_CHAIN"] = datetime.now()
                
        except Exception as e:
            logger.error(f"Error getting option chain {symbol}: {e}")
        
        return options
    
    async def get_atm_options(self, symbol: str, spot: float = None) -> Tuple[Optional[LiveQuote], Optional[LiveQuote]]:
        """Get ATM Call and Put options"""
        if spot is None:
            index_quote = await self.get_index_quote(symbol)
            if index_quote:
                spot = index_quote.ltp
            else:
                return None, None
        
        gap = self.STRIKE_GAPS.get(symbol, 50)
        atm_strike = round(spot / gap) * gap
        
        chain = await self.get_option_chain(symbol, strikes_around_atm=2)
        
        atm_ce = None
        atm_pe = None
        
        for opt in chain:
            if opt.strike == atm_strike:
                if opt.quote_type == "CE":
                    atm_ce = opt
                elif opt.quote_type == "PE":
                    atm_pe = opt
        
        return atm_ce, atm_pe
    
    def _get_nearest_expiry(self, symbol: str) -> date:
        """Get nearest weekly expiry"""
        today = date.today()
        
        expiry_days = {
            "NIFTY": 3,      # Thursday
            "BANKNIFTY": 2,  # Wednesday
            "FINNIFTY": 1,   # Tuesday
            "SENSEX": 4,     # Friday
            "BANKEX": 0      # Monday
        }
        
        weekday = expiry_days.get(symbol, 3)
        days_ahead = (weekday - today.weekday()) % 7
        
        if days_ahead == 0:
            now = datetime.now()
            if now.hour >= 15 and now.minute >= 30:
                days_ahead = 7
        
        return today + timedelta(days=days_ahead)
    
    async def get_all_indices(self) -> Dict[str, LiveQuote]:
        """Get quotes for all tracked indices"""
        quotes = {}
        symbols = ["NIFTY", "BANKNIFTY", "SENSEX", "BANKEX"]
        
        for symbol in symbols:
            quote = await self.get_index_quote(symbol)
            if quote:
                quotes[symbol] = quote
        
        return quotes
    
    def get_cached_quote(self, symbol: str, quote_type: str = "INDEX") -> Optional[LiveQuote]:
        """Get cached quote without API call"""
        return self._quotes.get(f"{symbol}_{quote_type}")
    
    def get_cache_age(self, symbol: str, quote_type: str = "INDEX") -> float:
        """Get age of cached quote in seconds"""
        key = f"{symbol}_{quote_type}"
        if key in self._last_update:
            return (datetime.now() - self._last_update[key]).total_seconds()
        return float('inf')


class MockRealDataClient:
    """
    Mock client for testing when market is closed
    Generates realistic simulated data
    """
    
    BASE_PRICES = {
        "NIFTY": 24500,
        "BANKNIFTY": 52000,
        "FINNIFTY": 24000,
        "SENSEX": 81500,
        "BANKEX": 55000
    }
    
    LOT_SIZES = {
        "NIFTY": 75,
        "BANKNIFTY": 35,
        "FINNIFTY": 65,
        "SENSEX": 20,
        "BANKEX": 30
    }
    
    STRIKE_GAPS = {
        "NIFTY": 50,
        "BANKNIFTY": 100,
        "FINNIFTY": 50,
        "SENSEX": 100,
        "BANKEX": 100
    }
    
    def __init__(self, store_to_db: bool = True):
        import random
        self._random = random
        self._tick_count = 0
        self._prices = dict(self.BASE_PRICES)
        self._trends = {s: 0 for s in self.BASE_PRICES}
        
        self.store_to_db = store_to_db
        self._db = get_database() if store_to_db else None
        self._tick_buffer: List[MarketTick] = []
        
        logger.info("MockRealDataClient initialized (market closed mode)")
    
    async def _flush_tick_buffer(self):
        """Flush tick buffer to database"""
        if self._tick_buffer and self._db:
            try:
                self._db.insert_ticks_batch(self._tick_buffer)
                self._tick_buffer = []
            except Exception as e:
                logger.error(f"Error flushing ticks: {e}")
    
    def _store_tick(self, quote: LiveQuote):
        """Store tick to buffer"""
        if not self._db:
            return
        
        tick = MarketTick(
            timestamp=quote.timestamp,
            instrument=quote.instrument,
            symbol=quote.symbol,
            ltp=quote.ltp,
            volume=quote.volume,
            oi=quote.oi
        )
        self._tick_buffer.append(tick)
        
        if len(self._tick_buffer) >= 50:
            asyncio.create_task(self._flush_tick_buffer())
    
    async def get_index_quote(self, symbol: str) -> Optional[LiveQuote]:
        """Generate realistic mock quote"""
        if symbol not in self.BASE_PRICES:
            return None
        
        self._tick_count += 1
        
        # Random walk with mean reversion
        current = self._prices[symbol]
        trend = self._trends[symbol]
        
        # Add momentum
        momentum = self._random.gauss(0, 0.0005)  # 0.05% std dev
        trend = trend * 0.95 + momentum  # Decay trend
        self._trends[symbol] = trend
        
        # Apply change
        change = current * (trend + self._random.gauss(0, 0.0003))
        new_price = current + change
        
        # Mean reversion
        base = self.BASE_PRICES[symbol]
        if new_price > base * 1.02:
            new_price -= base * 0.001
        elif new_price < base * 0.98:
            new_price += base * 0.001
        
        self._prices[symbol] = new_price
        
        quote = LiveQuote(
            security_id=f"MOCK_{symbol}",
            symbol=symbol,
            instrument=symbol,
            quote_type="INDEX",
            ltp=round(new_price, 2),
            open=base,
            high=max(base, new_price),
            low=min(base, new_price),
            close=base,
            volume=self._random.randint(100000, 500000),
            change=round(new_price - base, 2),
            change_pct=round((new_price - base) / base * 100, 2),
            timestamp=datetime.now()
        )
        
        if self.store_to_db:
            self._store_tick(quote)
        
        return quote
    
    async def get_atm_options(self, symbol: str, spot: float = None) -> Tuple[Optional[LiveQuote], Optional[LiveQuote]]:
        """Generate mock ATM options"""
        if spot is None:
            index_quote = await self.get_index_quote(symbol)
            if index_quote:
                spot = index_quote.ltp
            else:
                spot = self.BASE_PRICES.get(symbol, 25000)
        
        gap = self.STRIKE_GAPS.get(symbol, 50)
        atm_strike = round(spot / gap) * gap
        expiry = date.today() + timedelta(days=7)
        
        # Option pricing (simplified)
        time_value = self._random.uniform(30, 80)
        intrinsic_ce = max(0, spot - atm_strike)
        intrinsic_pe = max(0, atm_strike - spot)
        
        ce_price = intrinsic_ce + time_value + self._random.uniform(-5, 5)
        pe_price = intrinsic_pe + time_value + self._random.uniform(-5, 5)
        
        atm_ce = LiveQuote(
            security_id=f"MOCK_CE_{symbol}_{atm_strike}",
            symbol=f"{symbol}{expiry.strftime('%d%b%y').upper()}{int(atm_strike)}CE",
            instrument=symbol,
            quote_type="CE",
            strike=atm_strike,
            expiry=expiry,
            ltp=round(max(5, ce_price), 2),
            volume=self._random.randint(50000, 200000),
            oi=self._random.randint(500000, 2000000),
            bid=round(max(4.5, ce_price - 0.5), 2),
            ask=round(max(5.5, ce_price + 0.5), 2),
            timestamp=datetime.now()
        )
        
        atm_pe = LiveQuote(
            security_id=f"MOCK_PE_{symbol}_{atm_strike}",
            symbol=f"{symbol}{expiry.strftime('%d%b%y').upper()}{int(atm_strike)}PE",
            instrument=symbol,
            quote_type="PE",
            strike=atm_strike,
            expiry=expiry,
            ltp=round(max(5, pe_price), 2),
            volume=self._random.randint(50000, 200000),
            oi=self._random.randint(500000, 2000000),
            bid=round(max(4.5, pe_price - 0.5), 2),
            ask=round(max(5.5, pe_price + 0.5), 2),
            timestamp=datetime.now()
        )
        
        if self.store_to_db:
            self._store_tick(atm_ce)
            self._store_tick(atm_pe)
        
        return atm_ce, atm_pe
    
    async def get_option_chain(self, symbol: str, expiry: date = None, 
                                strikes_around_atm: int = 5) -> List[LiveQuote]:
        """Generate mock option chain"""
        index_quote = await self.get_index_quote(symbol)
        if not index_quote:
            return []
        
        spot = index_quote.ltp
        gap = self.STRIKE_GAPS.get(symbol, 50)
        atm_strike = round(spot / gap) * gap
        
        if expiry is None:
            expiry = date.today() + timedelta(days=7)
        
        options = []
        
        for i in range(-strikes_around_atm, strikes_around_atm + 1):
            strike = atm_strike + (i * gap)
            
            # Generate CE
            intrinsic_ce = max(0, spot - strike)
            time_value = self._random.uniform(20, 60) * (1 - abs(i) * 0.1)
            ce_price = intrinsic_ce + max(5, time_value)
            
            options.append(LiveQuote(
                security_id=f"MOCK_CE_{symbol}_{strike}",
                symbol=f"{symbol}{expiry.strftime('%d%b%y').upper()}{int(strike)}CE",
                instrument=symbol,
                quote_type="CE",
                strike=strike,
                expiry=expiry,
                ltp=round(ce_price, 2),
                volume=self._random.randint(10000, 100000),
                oi=self._random.randint(100000, 500000),
                timestamp=datetime.now()
            ))
            
            # Generate PE
            intrinsic_pe = max(0, strike - spot)
            pe_price = intrinsic_pe + max(5, time_value)
            
            options.append(LiveQuote(
                security_id=f"MOCK_PE_{symbol}_{strike}",
                symbol=f"{symbol}{expiry.strftime('%d%b%y').upper()}{int(strike)}PE",
                instrument=symbol,
                quote_type="PE",
                strike=strike,
                expiry=expiry,
                ltp=round(pe_price, 2),
                volume=self._random.randint(10000, 100000),
                oi=self._random.randint(100000, 500000),
                timestamp=datetime.now()
            ))
        
        return options
    
    async def get_all_indices(self) -> Dict[str, LiveQuote]:
        """Get all index quotes"""
        quotes = {}
        for symbol in ["NIFTY", "BANKNIFTY", "SENSEX", "BANKEX"]:
            quote = await self.get_index_quote(symbol)
            if quote:
                quotes[symbol] = quote
        return quotes
    
    async def close(self):
        await self._flush_tick_buffer()


def is_market_hours() -> bool:
    """Check if Indian market is open"""
    now = datetime.now()
    
    # Check weekday (0=Monday, 6=Sunday)
    if now.weekday() >= 5:
        return False
    
    # Market hours: 9:15 AM to 3:30 PM IST
    market_open = time(9, 15)
    market_close = time(15, 30)
    
    return market_open <= now.time() <= market_close


def create_data_client(access_token: str = None, client_id: str = None, 
                       force_mock: bool = False, store_to_db: bool = True):
    """
    Factory to create appropriate data client
    
    Args:
        access_token: Dhan access token
        client_id: Dhan client ID
        force_mock: Force mock client even during market hours
        store_to_db: Store data to SQLite database
    """
    if force_mock:
        logger.info("Using mock client (forced)")
        return MockRealDataClient(store_to_db=store_to_db)
    
    if not access_token or not client_id:
        logger.info("Using mock client (no credentials)")
        return MockRealDataClient(store_to_db=store_to_db)
    
    if is_market_hours():
        logger.info("Using real Dhan client (market open)")
        return RealMarketDataClient(access_token, client_id, store_to_db=store_to_db)
    else:
        logger.info("Using mock client (market closed)")
        return MockRealDataClient(store_to_db=store_to_db)
