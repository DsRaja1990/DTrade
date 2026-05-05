"""
Dhan WebSocket Live Market Feed Client
Real-time market data via WebSocket - NO RATE LIMITS
Based on Dhan API v2 documentation
"""

import asyncio
import websockets
import struct
import logging
import json
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Callable, Any, Set
from dataclasses import dataclass, field
from enum import IntEnum
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logger = logging.getLogger(__name__)


class FeedRequestCode(IntEnum):
    """Request codes for subscribing to data modes"""
    TICKER = 15      # LTP + LTT only
    QUOTE = 17       # Full quote data
    FULL = 21        # Full data with market depth
    DISCONNECT = 12  # Disconnect


class FeedResponseCode(IntEnum):
    """Response codes from WebSocket"""
    TICKER = 2
    QUOTE = 4
    OI_DATA = 5
    PREV_CLOSE = 6
    FULL = 8
    DISCONNECT = 50


class ExchangeSegment(IntEnum):
    """Exchange segment codes from Dhan API"""
    IDX_I = 0       # Index (NIFTY, BANKNIFTY, SENSEX etc)
    NSE_EQ = 1      # NSE Equity Cash
    NSE_FNO = 2     # NSE Futures & Options
    NSE_CURR = 3    # NSE Currency
    BSE_EQ = 4      # BSE Equity Cash
    MCX_COMM = 5    # MCX Commodity
    BSE_CURR = 7    # BSE Currency
    BSE_FNO = 8     # BSE Futures & Options


SEGMENT_MAP = {
    "IDX_I": ExchangeSegment.IDX_I,
    "NSE_EQ": ExchangeSegment.NSE_EQ,
    "NSE_FNO": ExchangeSegment.NSE_FNO,
    "BSE_EQ": ExchangeSegment.BSE_EQ,
    "BSE_FNO": ExchangeSegment.BSE_FNO,
}

SEGMENT_NAMES = {v: k for k, v in SEGMENT_MAP.items()}


@dataclass
class TickData:
    """Parsed tick data from WebSocket"""
    security_id: int
    exchange_segment: str
    ltp: float
    ltt: datetime
    volume: int = 0
    oi: int = 0
    total_buy_qty: int = 0
    total_sell_qty: int = 0
    open: float = 0.0
    high: float = 0.0
    low: float = 0.0
    close: float = 0.0
    prev_close: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)


class DhanWebSocketClient:
    """
    WebSocket client for Dhan Live Market Feed
    
    Features:
    - Real-time tick data without rate limits
    - Auto-reconnection
    - Binary message parsing
    - Subscription management
    """
    
    WS_URL = "wss://api-feed.dhan.co"
    
    # Index security IDs (from Dhan instrument list)
    INDEX_SECURITY_IDS = {
        "NIFTY": 13,        # Nifty 50 index
        "BANKNIFTY": 25,    # Bank Nifty index
        "FINNIFTY": 27,     # Fin Nifty index
        "SENSEX": 51,       # Sensex index
        "BANKEX": 52        # Bankex index
    }
    
    # Exchange segments for indices - IDX_I for all indices (segment code 0)
    INDEX_SEGMENTS = {
        "NIFTY": "IDX_I",
        "BANKNIFTY": "IDX_I",
        "FINNIFTY": "IDX_I",
        "SENSEX": "IDX_I",
        "BANKEX": "IDX_I"
    }
    
    def __init__(self, access_token: str, client_id: str, on_tick: Callable[[TickData], None] = None):
        self.access_token = access_token
        self.client_id = client_id
        self.on_tick = on_tick
        
        self._ws = None
        self._running = False
        self._connected = False
        self._subscribed: Set[str] = set()  # Set of "segment:security_id"
        
        # Data cache
        self._ticks: Dict[int, TickData] = {}
        self._prev_closes: Dict[int, float] = {}
        
        # Reconnection
        self._reconnect_delay = 1
        self._max_reconnect_delay = 60
        
        logger.info(f"DhanWebSocketClient initialized for client {client_id}")
    
    def _build_ws_url(self) -> str:
        """Build WebSocket URL with auth params"""
        return f"{self.WS_URL}?version=2&token={self.access_token}&clientId={self.client_id}&authType=2"
    
    async def connect(self):
        """Establish WebSocket connection"""
        url = self._build_ws_url()
        
        try:
            self._ws = await websockets.connect(
                url,
                ping_interval=10,
                ping_timeout=30,
                close_timeout=5
            )
            self._connected = True
            self._reconnect_delay = 1  # Reset delay on successful connect
            logger.info("WebSocket connected successfully")
            return True
        except Exception as e:
            logger.error(f"WebSocket connection failed: {e}")
            self._connected = False
            return False
    
    async def disconnect(self):
        """Disconnect WebSocket"""
        self._running = False
        
        if self._ws:
            try:
                # Send disconnect request
                await self._ws.send(json.dumps({"RequestCode": FeedRequestCode.DISCONNECT}))
                await self._ws.close()
            except:
                pass
        
        self._connected = False
        logger.info("WebSocket disconnected")
    
    async def subscribe(self, instruments: List[Dict[str, Any]], mode: FeedRequestCode = FeedRequestCode.QUOTE):
        """
        Subscribe to instruments
        
        Args:
            instruments: List of {"segment": "NSE_EQ", "security_id": "26000"}
            mode: TICKER (LTP only), QUOTE (full quote), FULL (with depth)
        """
        if not self._connected or not self._ws:
            logger.error("Not connected. Cannot subscribe.")
            return False
        
        # Dhan allows max 100 instruments per message
        for i in range(0, len(instruments), 100):
            batch = instruments[i:i+100]
            
            instrument_list = []
            for inst in batch:
                segment = inst.get("segment", "NSE_EQ")
                security_id = str(inst.get("security_id"))
                
                instrument_list.append({
                    "ExchangeSegment": segment,
                    "SecurityId": security_id
                })
                
                self._subscribed.add(f"{segment}:{security_id}")
            
            request = {
                "RequestCode": int(mode),
                "InstrumentCount": len(instrument_list),
                "InstrumentList": instrument_list
            }
            
            try:
                await self._ws.send(json.dumps(request))
                logger.info(f"Subscribed to {len(instrument_list)} instruments (mode: {mode.name})")
            except Exception as e:
                logger.error(f"Subscribe error: {e}")
                return False
        
        return True
    
    async def subscribe_indices(self, symbols: List[str] = None, mode: FeedRequestCode = FeedRequestCode.QUOTE):
        """Subscribe to index instruments"""
        if symbols is None:
            symbols = list(self.INDEX_SECURITY_IDS.keys())
        
        instruments = []
        for symbol in symbols:
            if symbol in self.INDEX_SECURITY_IDS:
                instruments.append({
                    "segment": self.INDEX_SEGMENTS[symbol],
                    "security_id": self.INDEX_SECURITY_IDS[symbol]
                })
        
        return await self.subscribe(instruments, mode)
    
    def _parse_header(self, data: bytes) -> tuple:
        """Parse 8-byte response header"""
        if len(data) < 8:
            return None, None, None, None
        
        # Little endian format
        response_code = data[0]
        message_length = struct.unpack('<H', data[1:3])[0]
        exchange_segment = data[3]
        security_id = struct.unpack('<I', data[4:8])[0]
        
        return response_code, message_length, exchange_segment, security_id
    
    def _parse_ticker(self, data: bytes, security_id: int, exchange_segment: int) -> TickData:
        """Parse ticker packet (LTP + LTT)"""
        # Header (8) + LTP (4) + LTT (4) = 16 bytes
        if len(data) < 16:
            return None
        
        ltp = struct.unpack('<f', data[8:12])[0]
        ltt_epoch = struct.unpack('<I', data[12:16])[0]
        ltt = datetime.fromtimestamp(ltt_epoch) if ltt_epoch > 0 else datetime.now()
        
        segment_name = SEGMENT_NAMES.get(exchange_segment, f"UNKNOWN_{exchange_segment}")
        
        return TickData(
            security_id=security_id,
            exchange_segment=segment_name,
            ltp=ltp,
            ltt=ltt,
            prev_close=self._prev_closes.get(security_id, 0)
        )
    
    def _parse_quote(self, data: bytes, security_id: int, exchange_segment: int) -> TickData:
        """Parse quote packet (full quote data)"""
        # Header (8) + payload
        if len(data) < 50:
            return None
        
        segment_name = SEGMENT_NAMES.get(exchange_segment, f"UNKNOWN_{exchange_segment}")
        
        ltp = struct.unpack('<f', data[8:12])[0]
        ltq = struct.unpack('<H', data[12:14])[0]
        ltt_epoch = struct.unpack('<I', data[14:18])[0]
        ltt = datetime.fromtimestamp(ltt_epoch) if ltt_epoch > 0 else datetime.now()
        atp = struct.unpack('<f', data[18:22])[0]
        volume = struct.unpack('<I', data[22:26])[0]
        total_sell_qty = struct.unpack('<I', data[26:30])[0]
        total_buy_qty = struct.unpack('<I', data[30:34])[0]
        day_open = struct.unpack('<f', data[34:38])[0]
        day_close = struct.unpack('<f', data[38:42])[0]
        day_high = struct.unpack('<f', data[42:46])[0]
        day_low = struct.unpack('<f', data[46:50])[0]
        
        return TickData(
            security_id=security_id,
            exchange_segment=segment_name,
            ltp=ltp,
            ltt=ltt,
            volume=volume,
            total_buy_qty=total_buy_qty,
            total_sell_qty=total_sell_qty,
            open=day_open,
            high=day_high,
            low=day_low,
            close=day_close,
            prev_close=self._prev_closes.get(security_id, 0)
        )
    
    def _parse_prev_close(self, data: bytes, security_id: int):
        """Parse previous close packet"""
        if len(data) < 16:
            return
        
        prev_close = struct.unpack('<f', data[8:12])[0]
        self._prev_closes[security_id] = prev_close
        logger.debug(f"Prev close for {security_id}: {prev_close}")
    
    def _parse_oi(self, data: bytes, security_id: int):
        """Parse OI data packet"""
        if len(data) < 12:
            return
        
        oi = struct.unpack('<I', data[8:12])[0]
        
        if security_id in self._ticks:
            self._ticks[security_id].oi = oi
    
    async def _process_message(self, data: bytes):
        """Process incoming binary message"""
        if len(data) < 8:
            return
        
        response_code, msg_len, exchange_segment, security_id = self._parse_header(data)
        
        if response_code is None:
            return
        
        tick = None
        
        if response_code == FeedResponseCode.TICKER:
            tick = self._parse_ticker(data, security_id, exchange_segment)
        
        elif response_code == FeedResponseCode.QUOTE:
            tick = self._parse_quote(data, security_id, exchange_segment)
        
        elif response_code == FeedResponseCode.PREV_CLOSE:
            self._parse_prev_close(data, security_id)
        
        elif response_code == FeedResponseCode.OI_DATA:
            self._parse_oi(data, security_id)
        
        elif response_code == FeedResponseCode.DISCONNECT:
            if len(data) >= 10:
                disconnect_code = struct.unpack('<H', data[8:10])[0]
                logger.warning(f"Disconnected with code: {disconnect_code}")
        
        if tick:
            self._ticks[security_id] = tick
            
            if self.on_tick:
                try:
                    await self.on_tick(tick) if asyncio.iscoroutinefunction(self.on_tick) else self.on_tick(tick)
                except Exception as e:
                    logger.error(f"Error in on_tick callback: {e}")
    
    async def run(self):
        """Run WebSocket client with auto-reconnection"""
        self._running = True
        
        while self._running:
            try:
                if not self._connected:
                    if not await self.connect():
                        logger.info(f"Reconnecting in {self._reconnect_delay}s...")
                        await asyncio.sleep(self._reconnect_delay)
                        self._reconnect_delay = min(self._reconnect_delay * 2, self._max_reconnect_delay)
                        continue
                    
                    # Resubscribe after reconnection
                    if self._subscribed:
                        instruments = []
                        for sub in self._subscribed:
                            segment, security_id = sub.split(":")
                            instruments.append({"segment": segment, "security_id": security_id})
                        await self.subscribe(instruments)
                
                # Read messages
                try:
                    message = await asyncio.wait_for(self._ws.recv(), timeout=30)
                    
                    if isinstance(message, bytes):
                        await self._process_message(message)
                    
                except asyncio.TimeoutError:
                    # No message in 30s, connection might be stale
                    logger.debug("No message received, checking connection...")
                    continue
                
            except websockets.ConnectionClosed as e:
                logger.warning(f"WebSocket closed: {e}")
                self._connected = False
                
            except Exception as e:
                logger.error(f"WebSocket error: {e}")
                self._connected = False
                await asyncio.sleep(1)
    
    def get_tick(self, security_id: int) -> Optional[TickData]:
        """Get cached tick for a security"""
        return self._ticks.get(security_id)
    
    def get_index_tick(self, symbol: str) -> Optional[TickData]:
        """Get cached tick for an index by symbol"""
        security_id = self.INDEX_SECURITY_IDS.get(symbol)
        if security_id:
            return self._ticks.get(security_id)
        return None
    
    def get_all_ticks(self) -> Dict[int, TickData]:
        """Get all cached ticks"""
        return dict(self._ticks)


class DhanOptionChainClient:
    """
    REST API client for option chain data
    Used sparingly to get option security IDs, then subscribe via WebSocket
    """
    
    def __init__(self, access_token: str, client_id: str):
        self.access_token = access_token
        self.client_id = client_id
        self.base_url = "https://api.dhan.co/v2"
        
        self._headers = {
            "access-token": access_token,
            "client-id": client_id,
            "Content-Type": "application/json"
        }
        
        # Cache option chain to avoid repeated API calls
        self._option_cache: Dict[str, List[Dict]] = {}
        self._cache_time: Dict[str, datetime] = {}
        self._cache_ttl = 300  # 5 minutes cache
    
    async def get_option_chain(self, symbol: str, expiry: date = None) -> List[Dict]:
        """Get option chain (cached)"""
        import aiohttp
        
        cache_key = f"{symbol}_{expiry}"
        
        # Check cache
        if cache_key in self._option_cache:
            cache_age = (datetime.now() - self._cache_time.get(cache_key, datetime.min)).total_seconds()
            if cache_age < self._cache_ttl:
                return self._option_cache[cache_key]
        
        # Fetch from API
        underlying_ids = {
            "NIFTY": "26000",
            "BANKNIFTY": "26009",
            "FINNIFTY": "26037",
            "SENSEX": "1",
            "BANKEX": "12"
        }
        
        if expiry is None:
            expiry = self._get_nearest_expiry(symbol)
        
        try:
            async with aiohttp.ClientSession(headers=self._headers) as session:
                async with session.post(
                    f"{self.base_url}/optionchain",
                    json={
                        "UnderlyingScrip": underlying_ids.get(symbol, "26000"),
                        "ExpiryDate": expiry.strftime("%Y-%m-%d")
                    },
                    timeout=10
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        options = data.get("data", [])
                        
                        # Cache result
                        self._option_cache[cache_key] = options
                        self._cache_time[cache_key] = datetime.now()
                        
                        return options
                    else:
                        logger.warning(f"Option chain API error: {response.status}")
                        return []
        except Exception as e:
            logger.error(f"Option chain fetch error: {e}")
            return []
    
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


# ==================== Test ====================

async def test_websocket():
    """Test WebSocket connection"""
    from config.settings import IndexScalpingConfig
    
    config = IndexScalpingConfig()
    
    def on_tick(tick: TickData):
        print(f"[{tick.ltt.strftime('%H:%M:%S')}] {tick.security_id} | LTP: {tick.ltp:.2f} | Vol: {tick.volume}")
    
    client = DhanWebSocketClient(
        access_token=config.dhan.access_token,
        client_id=config.dhan.client_id,
        on_tick=on_tick
    )
    
    # Connect and subscribe
    if await client.connect():
        await client.subscribe_indices(["NIFTY", "BANKNIFTY", "SENSEX"])
        
        # Run for 30 seconds
        try:
            await asyncio.wait_for(client.run(), timeout=30)
        except asyncio.TimeoutError:
            pass
        
        await client.disconnect()
    else:
        print("Failed to connect")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(test_websocket())
