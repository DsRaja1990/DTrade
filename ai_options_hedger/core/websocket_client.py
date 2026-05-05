"""
Dhan WebSocket Client for AI Options Hedger
============================================
Real-time market data via WebSocket - UNLIMITED requests (no rate limits)

Dhan WebSocket Protocol:
- URL: wss://api-feed.dhan.co?version=2&token={token}&clientId={clientId}&authType=2
- Binary response format (Little Endian)
- Request codes: 15=ticker, 17=quote, 21=full, 12=disconnect
- Up to 5000 instruments per connection, 5 connections per user
"""

import asyncio
import struct
import logging
import json
from datetime import datetime
from typing import Callable, Optional, Dict, List, Any, Set
from dataclasses import dataclass, field
from enum import IntEnum
import aiohttp

logger = logging.getLogger(__name__)


class FeedRequestCode(IntEnum):
    """WebSocket subscription request codes"""
    TICKER = 15      # LTP + LTT only
    QUOTE = 17       # LTP + volume + OHLC
    FULL = 21        # Full data with depth
    DISCONNECT = 12


class FeedResponseCode(IntEnum):
    """WebSocket response packet types"""
    TICKER = 2
    QUOTE = 4
    OI = 5
    PREV_CLOSE = 6
    FULL = 8
    DISCONNECT = 50


class ExchangeSegment(IntEnum):
    """Exchange segment codes for Dhan API"""
    IDX_I = 0       # Index (for NIFTY, BANKNIFTY etc)
    NSE_CM = 1      # NSE Cash
    NSE_FNO = 2     # NSE F&O
    NSE_CURR = 3    # NSE Currency
    BSE_CM = 4      # BSE Cash  
    BSE_FNO = 8     # BSE F&O (SENSEX, BANKEX options) - corrected to 8
    MCX_COMM = 5    # MCX Commodity


@dataclass
class TickData:
    """Tick data from WebSocket"""
    security_id: int
    ltp: float
    ltt: datetime
    exchange_segment: int = 0
    volume: int = 0
    open: float = 0.0
    high: float = 0.0
    low: float = 0.0
    close: float = 0.0
    oi: int = 0
    prev_oi: int = 0
    avg_price: float = 0.0
    turnover: float = 0.0


class DhanWebSocketClient:
    """
    Dhan WebSocket Client for real-time market data
    
    Features:
    - UNLIMITED data (no rate limits)
    - Binary response parsing
    - Auto-reconnection
    - Callback-based data delivery
    """
    
    WS_URL = "wss://api-feed.dhan.co"
    
    # Security IDs for major indices (IDX_I segment)
    INDEX_SECURITY_IDS = {
        "NIFTY": 13,         # Nifty 50 index
        "BANKNIFTY": 25,     # Bank Nifty index
        "FINNIFTY": 27,      # Fin Nifty index
        "SENSEX": 51,        # Sensex index
        "BANKEX": 52,        # Bankex index
    }
    
    # All indices use IDX_I segment (code 0)
    EXCHANGE_FOR_INDEX = {
        "NIFTY": ExchangeSegment.IDX_I,
        "BANKNIFTY": ExchangeSegment.IDX_I,
        "FINNIFTY": ExchangeSegment.IDX_I,
        "SENSEX": ExchangeSegment.IDX_I,
        "BANKEX": ExchangeSegment.IDX_I,
    }
    
    def __init__(
        self,
        access_token: str,
        client_id: str,
        on_tick: Optional[Callable] = None,
        on_quote: Optional[Callable] = None,
        on_error: Optional[Callable] = None,
        on_connect: Optional[Callable] = None,
        on_disconnect: Optional[Callable] = None
    ):
        self._access_token = access_token
        self._client_id = client_id
        
        # Callbacks
        self._on_tick = on_tick
        self._on_quote = on_quote
        self._on_error = on_error
        self._on_connect = on_connect
        self._on_disconnect = on_disconnect
        
        # Connection state
        self._ws: Optional[aiohttp.ClientWebSocketResponse] = None
        self._session: Optional[aiohttp.ClientSession] = None
        self._connected = False
        self._reconnect_count = 0
        self._max_reconnects = 10
        
        # Subscriptions
        self._subscribed: Set[tuple] = set()  # (security_id, exchange_segment)
        
        # Security ID to symbol mapping for logging
        self._security_to_symbol: Dict[int, str] = {}
        
        logger.info(f"DhanWebSocketClient initialized for client {client_id}")
    
    @property
    def is_connected(self) -> bool:
        return self._connected and self._ws is not None
    
    def _build_ws_url(self) -> str:
        """Build WebSocket connection URL"""
        return f"{self.WS_URL}?version=2&token={self._access_token}&clientId={self._client_id}&authType=2"
    
    async def connect(self) -> bool:
        """Connect to WebSocket"""
        try:
            if self._session is None:
                self._session = aiohttp.ClientSession()
            
            url = self._build_ws_url()
            self._ws = await self._session.ws_connect(
                url,
                heartbeat=30,
                receive_timeout=60
            )
            
            self._connected = True
            self._reconnect_count = 0
            logger.info("WebSocket connected successfully")
            
            if self._on_connect:
                await self._on_connect()
            
            return True
            
        except Exception as e:
            logger.error(f"WebSocket connection failed: {e}")
            self._connected = False
            if self._on_error:
                await self._on_error(str(e))
            return False
    
    async def disconnect(self):
        """Disconnect from WebSocket"""
        self._connected = False
        
        if self._ws:
            try:
                # Send disconnect request
                await self._send_subscription_request([], [], FeedRequestCode.DISCONNECT)
                await self._ws.close()
            except:
                pass
            self._ws = None
        
        if self._session:
            await self._session.close()
            self._session = None
        
        logger.info("WebSocket disconnected")
        
        if self._on_disconnect:
            await self._on_disconnect()
    
    async def _send_subscription_request(
        self,
        idx_ids: List[int],
        _unused_ids: List[int],  # Keep signature but use IDX_I for all indices
        mode: FeedRequestCode
    ):
        """Send subscription request for indices using IDX_I segment"""
        if not self._ws:
            return
        
        try:
            # Build subscription packet - use IDX_I (0) for all indices
            packet = {
                "RequestCode": int(mode),
                "InstrumentCount": len(idx_ids),
                "InstrumentList": []
            }
            
            # Add all indices with IDX_I segment
            for sec_id in idx_ids:
                packet["InstrumentList"].append({
                    "ExchangeSegment": "IDX_I",
                    "SecurityId": str(sec_id)
                })
            
            await self._ws.send_json(packet)
            
        except Exception as e:
            logger.error(f"Subscription request failed: {e}")
    
    async def subscribe_indices(
        self,
        indices: List[str],
        mode: FeedRequestCode = FeedRequestCode.QUOTE
    ):
        """Subscribe to index price feeds using IDX_I segment"""
        idx_ids = []
        
        for idx in indices:
            idx_upper = idx.upper()
            if idx_upper in self.INDEX_SECURITY_IDS:
                sec_id = self.INDEX_SECURITY_IDS[idx_upper]
                exchange = self.EXCHANGE_FOR_INDEX.get(idx_upper, ExchangeSegment.IDX_I)
                
                self._security_to_symbol[sec_id] = idx_upper
                self._subscribed.add((sec_id, exchange))
                idx_ids.append(sec_id)
        
        await self._send_subscription_request(idx_ids, [], mode)
        logger.info(f"Subscribed to {len(indices)} indices (mode: {mode.name})")
    
    async def subscribe_options(
        self,
        instruments: List[Dict],
        mode: FeedRequestCode = FeedRequestCode.QUOTE
    ):
        """
        Subscribe to option price feeds
        
        Args:
            instruments: List of dicts with 'security_id' and 'exchange_segment'
            mode: Feed request mode
        """
        nse_ids = []
        bse_ids = []
        
        for inst in instruments:
            sec_id = inst.get('security_id')
            exchange = inst.get('exchange_segment', ExchangeSegment.NSE_FNO)
            
            self._subscribed.add((sec_id, exchange))
            
            if exchange == ExchangeSegment.BSE_FNO:
                bse_ids.append(sec_id)
            else:
                nse_ids.append(sec_id)
        
        await self._send_subscription_request(nse_ids, bse_ids, mode)
        logger.info(f"Subscribed to {len(instruments)} options (mode: {mode.name})")
    
    def _parse_ticker_packet(self, data: bytes) -> Optional[TickData]:
        """Parse ticker packet (8 byte header + LTP + LTT)"""
        try:
            if len(data) < 16:
                return None
            
            # Header: 8 bytes
            response_code = data[0]
            exchange_segment = data[1]
            security_id = struct.unpack('<I', data[4:8])[0]
            
            # Ticker data
            ltp = struct.unpack('<f', data[8:12])[0]
            ltt_epoch = struct.unpack('<I', data[12:16])[0]
            
            return TickData(
                security_id=security_id,
                exchange_segment=exchange_segment,
                ltp=ltp,
                ltt=datetime.fromtimestamp(ltt_epoch)
            )
        except Exception as e:
            logger.debug(f"Ticker parse error: {e}")
            return None
    
    def _parse_quote_packet(self, data: bytes) -> Optional[TickData]:
        """Parse quote packet with OHLC and volume"""
        try:
            if len(data) < 48:
                return None
            
            # Header
            response_code = data[0]
            exchange_segment = data[1]
            security_id = struct.unpack('<I', data[4:8])[0]
            
            # Quote data (after 8-byte header)
            offset = 8
            ltp = struct.unpack('<f', data[offset:offset+4])[0]; offset += 4
            ltt_epoch = struct.unpack('<I', data[offset:offset+4])[0]; offset += 4
            volume = struct.unpack('<I', data[offset:offset+4])[0]; offset += 4
            open_price = struct.unpack('<f', data[offset:offset+4])[0]; offset += 4
            high_price = struct.unpack('<f', data[offset:offset+4])[0]; offset += 4
            low_price = struct.unpack('<f', data[offset:offset+4])[0]; offset += 4
            close_price = struct.unpack('<f', data[offset:offset+4])[0]; offset += 4
            
            return TickData(
                security_id=security_id,
                exchange_segment=exchange_segment,
                ltp=ltp,
                ltt=datetime.fromtimestamp(ltt_epoch),
                volume=volume,
                open=open_price,
                high=high_price,
                low=low_price,
                close=close_price
            )
        except Exception as e:
            logger.debug(f"Quote parse error: {e}")
            return None
    
    async def _process_message(self, data: bytes):
        """Process incoming binary message"""
        if len(data) < 8:
            return
        
        response_code = data[0]
        
        try:
            if response_code == FeedResponseCode.TICKER:
                tick = self._parse_ticker_packet(data)
                if tick and self._on_tick:
                    await self._on_tick(tick)
            
            elif response_code == FeedResponseCode.QUOTE:
                tick = self._parse_quote_packet(data)
                if tick:
                    if self._on_quote:
                        await self._on_quote(tick)
                    elif self._on_tick:
                        await self._on_tick(tick)
            
            elif response_code == FeedResponseCode.FULL:
                tick = self._parse_quote_packet(data)  # Full has same base structure
                if tick:
                    if self._on_quote:
                        await self._on_quote(tick)
                    elif self._on_tick:
                        await self._on_tick(tick)
            
            elif response_code == FeedResponseCode.OI:
                # OI update - parse and include in tick
                pass
            
            elif response_code == FeedResponseCode.DISCONNECT:
                logger.warning("Server requested disconnect")
                await self._handle_reconnect()
                
        except Exception as e:
            logger.error(f"Message processing error: {e}")
    
    async def _handle_reconnect(self):
        """Handle reconnection with exponential backoff"""
        if self._reconnect_count >= self._max_reconnects:
            logger.error("Max reconnection attempts reached")
            return
        
        self._reconnect_count += 1
        delay = min(30, 2 ** self._reconnect_count)
        
        logger.info(f"Reconnecting in {delay}s (attempt {self._reconnect_count})")
        await asyncio.sleep(delay)
        
        if await self.connect():
            # Resubscribe
            nse_ids = []
            bse_ids = []
            for sec_id, exchange in self._subscribed:
                if exchange == ExchangeSegment.BSE_FNO:
                    bse_ids.append(sec_id)
                else:
                    nse_ids.append(sec_id)
            
            if nse_ids or bse_ids:
                await self._send_subscription_request(nse_ids, bse_ids, FeedRequestCode.QUOTE)
    
    async def run(self):
        """Main message loop"""
        while self._connected:
            try:
                if not self._ws:
                    await self._handle_reconnect()
                    continue
                
                msg = await self._ws.receive(timeout=30)
                
                if msg.type == aiohttp.WSMsgType.BINARY:
                    await self._process_message(msg.data)
                
                elif msg.type == aiohttp.WSMsgType.CLOSED:
                    logger.warning("WebSocket closed")
                    await self._handle_reconnect()
                
                elif msg.type == aiohttp.WSMsgType.ERROR:
                    logger.error(f"WebSocket error: {msg.data}")
                    await self._handle_reconnect()
                    
            except asyncio.TimeoutError:
                # Send ping to keep alive
                if self._ws and not self._ws.closed:
                    try:
                        await self._ws.ping()
                    except:
                        await self._handle_reconnect()
            
            except asyncio.CancelledError:
                break
            
            except Exception as e:
                logger.error(f"WebSocket run error: {e}")
                await asyncio.sleep(1)


class DhanOptionChainClient:
    """
    REST client for option chain data
    Used for getting strike prices and expiries (one-time calls, not continuous)
    """
    
    BASE_URL = "https://api.dhan.co/v2"
    
    UNDERLYING_IDS = {
        "NIFTY": 13,
        "BANKNIFTY": 25,
        "FINNIFTY": 27,
        "SENSEX": 51,
        "BANKEX": 52,
    }
    
    def __init__(self, access_token: str, client_id: str):
        self._access_token = access_token
        self._client_id = client_id
    
    def _get_headers(self) -> Dict:
        return {
            "access-token": self._access_token,
            "client-id": self._client_id,
            "Content-Type": "application/json"
        }
    
    async def get_option_chain(self, symbol: str, expiry: str = None) -> List[Dict]:
        """
        Get option chain for a symbol
        Returns list of strikes with CE and PE data
        """
        underlying_id = self.UNDERLYING_IDS.get(symbol.upper())
        if not underlying_id:
            logger.warning(f"Unknown symbol: {symbol}")
            return []
        
        url = f"{self.BASE_URL}/optionchain"
        
        params = {
            "UnderlyingScrip": underlying_id,
            "ExpiryDate": expiry  # YYYY-MM-DD format
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url,
                    headers=self._get_headers(),
                    params={k: v for k, v in params.items() if v}
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data.get("data", [])
                    else:
                        logger.warning(f"Option chain API error: {response.status}")
                        return []
        except Exception as e:
            logger.error(f"Option chain request failed: {e}")
            return []
    
    async def get_expiries(self, symbol: str) -> List[str]:
        """Get available expiry dates for a symbol"""
        underlying_id = self.UNDERLYING_IDS.get(symbol.upper())
        if not underlying_id:
            return []
        
        url = f"{self.BASE_URL}/optionchain/expiry"
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url,
                    headers=self._get_headers(),
                    params={"UnderlyingScrip": underlying_id}
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data.get("data", [])
                    else:
                        return []
        except Exception as e:
            logger.error(f"Expiry request failed: {e}")
            return []
