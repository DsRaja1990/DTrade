# -*- coding: utf-8 -*-
"""
Dhan WebSocket Client for AI Scalping Service
==============================================
Real-time market data via WebSocket - UNLIMITED requests (no rate limits)

Dhan WebSocket Protocol:
- URL: wss://api-feed.dhan.co?version=2&token={token}&clientId={clientId}&authType=2
- Binary response format (Little Endian)
- Request codes: 15=ticker, 17=quote, 21=full, 12=disconnect
- Up to 5000 instruments per connection, 5 connections per user

This is the PREFERRED method for getting market data - direct WebSocket 
subscription rather than polling HTTP endpoints.
"""

import asyncio
import struct
import logging
import json
from datetime import datetime
from typing import Callable, Optional, Dict, List, Any, Set
from dataclasses import dataclass, field
from enum import IntEnum
from pathlib import Path
import aiohttp

logger = logging.getLogger(__name__)


class FeedRequestCode(IntEnum):
    """WebSocket subscription request codes"""
    CONNECT = 11        # Connect feed
    DISCONNECT = 12     # Disconnect feed
    TICKER = 15         # Subscribe ticker (LTP + LTT only)
    UNSUB_TICKER = 16   # Unsubscribe ticker
    QUOTE = 17          # Subscribe quote (LTP + volume + OHLC)
    UNSUB_QUOTE = 18    # Unsubscribe quote
    FULL = 21           # Subscribe full data with depth
    UNSUB_FULL = 22     # Unsubscribe full


class FeedResponseCode(IntEnum):
    """WebSocket response packet types"""
    INDEX = 1           # Index packet
    TICKER = 2          # Ticker packet
    QUOTE = 4           # Quote packet
    OI = 5              # Open Interest packet
    PREV_CLOSE = 6      # Previous close packet
    MARKET_STATUS = 7   # Market status packet
    FULL = 8            # Full packet with depth
    DISCONNECT = 50     # Disconnection packet


class ExchangeSegment(IntEnum):
    """Exchange segment codes for Dhan API"""
    IDX_I = 0           # Index (NIFTY, BANKNIFTY, SENSEX, BANKEX etc.)
    NSE_EQ = 1          # NSE Equity Cash
    NSE_FNO = 2         # NSE Futures & Options
    NSE_CURRENCY = 3    # NSE Currency
    BSE_EQ = 4          # BSE Equity Cash
    MCX_COMM = 5        # MCX Commodity
    BSE_CURRENCY = 7    # BSE Currency
    BSE_FNO = 8         # BSE Futures & Options


@dataclass
class TickData:
    """Tick data from WebSocket"""
    security_id: int
    symbol: str
    ltp: float
    ltt: datetime
    exchange_segment: int = 0
    volume: int = 0
    open: float = 0.0
    high: float = 0.0
    low: float = 0.0
    close: float = 0.0
    oi: int = 0
    prev_close: float = 0.0
    avg_price: float = 0.0
    total_buy_qty: int = 0
    total_sell_qty: int = 0


class DhanWebSocketClient:
    """
    Dhan WebSocket Client for real-time market data
    
    Features:
    - UNLIMITED data (no rate limits like REST API)
    - Binary response parsing (high performance)
    - Auto-reconnection with exponential backoff
    - Callback-based data delivery
    - Ping-pong keep-alive handling
    
    Usage:
        client = DhanWebSocketClient(
            access_token="your_token",
            client_id="your_client_id",
            on_tick=async_tick_handler
        )
        await client.connect()
        await client.subscribe_indices(["NIFTY", "BANKNIFTY", "SENSEX"])
        await client.run()  # Blocking - runs message loop
    """
    
    WS_URL = "wss://api-feed.dhan.co"
    
    # Security IDs for major indices (IDX_I segment)
    INDEX_SECURITY_IDS = {
        "NIFTY": 13,         # Nifty 50 index
        "BANKNIFTY": 25,     # Bank Nifty index
        "FINNIFTY": 27,      # Fin Nifty index
        "SENSEX": 51,        # Sensex index (BSE)
        "BANKEX": 52,        # Bankex index (BSE)
        "NIFTY50": 13,       # Alias
        "NIFTYBANK": 25,     # Alias
    }
    
    # Reverse mapping for symbol lookup
    SECURITY_ID_TO_SYMBOL = {v: k for k, v in INDEX_SECURITY_IDS.items() if k == k.upper() and len(k) <= 10}
    
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
        self._should_run = False
        
        # Subscriptions tracking
        self._subscribed: Set[tuple] = set()  # (security_id, exchange_segment)
        self._security_to_symbol: Dict[int, str] = {}
        
        # Stats
        self._tick_count = 0
        self._last_tick_time: Optional[datetime] = None
        self._connect_time: Optional[datetime] = None
        
        logger.info(f"DhanWebSocketClient initialized for client {client_id}")
    
    @property
    def is_connected(self) -> bool:
        return self._connected and self._ws is not None
    
    @property
    def stats(self) -> Dict[str, Any]:
        """Get client statistics"""
        return {
            "connected": self.is_connected,
            "tick_count": self._tick_count,
            "last_tick": self._last_tick_time.isoformat() if self._last_tick_time else None,
            "connect_time": self._connect_time.isoformat() if self._connect_time else None,
            "subscribed_count": len(self._subscribed),
            "reconnect_count": self._reconnect_count
        }
    
    def _build_ws_url(self) -> str:
        """Build WebSocket connection URL"""
        return f"{self.WS_URL}?version=2&token={self._access_token}&clientId={self._client_id}&authType=2"
    
    async def connect(self) -> bool:
        """Connect to Dhan WebSocket"""
        try:
            if self._session is None:
                self._session = aiohttp.ClientSession()
            
            url = self._build_ws_url()
            logger.info(f"Connecting to Dhan WebSocket...")
            
            self._ws = await self._session.ws_connect(
                url,
                heartbeat=30,
                receive_timeout=60
            )
            
            self._connected = True
            self._reconnect_count = 0
            self._connect_time = datetime.now()
            
            logger.info("[OK] WebSocket connected to Dhan successfully")
            
            if self._on_connect:
                try:
                    await self._on_connect()
                except Exception as e:
                    logger.error(f"on_connect callback error: {e}")
            
            return True
            
        except Exception as e:
            logger.error(f"WebSocket connection failed: {e}")
            self._connected = False
            
            if self._on_error:
                try:
                    await self._on_error(str(e))
                except:
                    pass
            
            return False
    
    async def disconnect(self):
        """Disconnect from WebSocket"""
        self._connected = False
        self._should_run = False
        
        if self._ws:
            try:
                # Send disconnect request
                disconnect_msg = {"RequestCode": FeedRequestCode.DISCONNECT}
                await self._ws.send_json(disconnect_msg)
                await self._ws.close()
            except:
                pass
            self._ws = None
        
        if self._session:
            try:
                await self._session.close()
            except:
                pass
            self._session = None
        
        logger.info("[STOP] WebSocket disconnected")
        
        if self._on_disconnect:
            try:
                await self._on_disconnect()
            except:
                pass
    
    async def subscribe_indices(
        self,
        indices: List[str],
        mode: FeedRequestCode = FeedRequestCode.QUOTE
    ) -> bool:
        """
        Subscribe to index price feeds using IDX_I segment
        
        Args:
            indices: List of index names like ["NIFTY", "BANKNIFTY", "SENSEX"]
            mode: FeedRequestCode.TICKER, QUOTE, or FULL
        
        Returns:
            True if subscription sent successfully
        """
        if not self._ws or not self._connected:
            logger.error("Cannot subscribe - not connected")
            return False
        
        try:
            instrument_list = []
            
            for idx in indices:
                idx_upper = idx.upper()
                if idx_upper in self.INDEX_SECURITY_IDS:
                    sec_id = self.INDEX_SECURITY_IDS[idx_upper]
                    
                    # Track subscription
                    self._subscribed.add((sec_id, ExchangeSegment.IDX_I))
                    self._security_to_symbol[sec_id] = idx_upper
                    
                    instrument_list.append({
                        "ExchangeSegment": "IDX_I",
                        "SecurityId": str(sec_id)
                    })
                else:
                    logger.warning(f"Unknown index: {idx}")
            
            if not instrument_list:
                logger.warning("No valid indices to subscribe")
                return False
            
            # Build subscription packet
            packet = {
                "RequestCode": int(mode),
                "InstrumentCount": len(instrument_list),
                "InstrumentList": instrument_list
            }
            
            await self._ws.send_json(packet)
            logger.info(f"[OK] Subscribed to {len(instrument_list)} indices: {[i.upper() for i in indices]} (mode: {mode.name})")
            
            return True
            
        except Exception as e:
            logger.error(f"Subscription failed: {e}")
            return False
    
    async def unsubscribe_indices(
        self,
        indices: List[str],
        mode: FeedRequestCode = FeedRequestCode.UNSUB_QUOTE
    ):
        """Unsubscribe from index feeds"""
        if not self._ws or not self._connected:
            return
        
        try:
            instrument_list = []
            
            for idx in indices:
                idx_upper = idx.upper()
                if idx_upper in self.INDEX_SECURITY_IDS:
                    sec_id = self.INDEX_SECURITY_IDS[idx_upper]
                    
                    # Remove from tracking
                    self._subscribed.discard((sec_id, ExchangeSegment.IDX_I))
                    
                    instrument_list.append({
                        "ExchangeSegment": "IDX_I",
                        "SecurityId": str(sec_id)
                    })
            
            if instrument_list:
                packet = {
                    "RequestCode": int(mode),
                    "InstrumentCount": len(instrument_list),
                    "InstrumentList": instrument_list
                }
                await self._ws.send_json(packet)
                logger.info(f"Unsubscribed from {len(instrument_list)} indices")
                
        except Exception as e:
            logger.error(f"Unsubscribe failed: {e}")
    
    def _get_symbol_for_security(self, security_id: int) -> str:
        """Get symbol name from security ID"""
        if security_id in self._security_to_symbol:
            return self._security_to_symbol[security_id]
        if security_id in self.SECURITY_ID_TO_SYMBOL:
            return self.SECURITY_ID_TO_SYMBOL[security_id]
        return str(security_id)
    
    def _parse_header(self, data: bytes) -> tuple:
        """
        Parse response header (8 bytes)
        Returns: (response_code, message_length, exchange_segment, security_id)
        """
        if len(data) < 8:
            return None, None, None, None
        
        response_code = data[0]
        message_length = struct.unpack('<H', data[1:3])[0]  # int16
        exchange_segment = data[3]
        security_id = struct.unpack('<I', data[4:8])[0]  # int32
        
        return response_code, message_length, exchange_segment, security_id
    
    def _parse_ticker_packet(self, data: bytes) -> Optional[TickData]:
        """
        Parse ticker packet (Header + LTP + LTT)
        Bytes: 0-7 header, 8-11 LTP (float32), 12-15 LTT (int32)
        """
        try:
            if len(data) < 16:
                return None
            
            response_code, msg_len, exchange_segment, security_id = self._parse_header(data)
            
            # Parse LTP and LTT
            ltp = struct.unpack('<f', data[8:12])[0]
            ltt_epoch = struct.unpack('<I', data[12:16])[0]
            
            return TickData(
                security_id=security_id,
                symbol=self._get_symbol_for_security(security_id),
                exchange_segment=exchange_segment,
                ltp=ltp,
                ltt=datetime.fromtimestamp(ltt_epoch) if ltt_epoch > 0 else datetime.now()
            )
        except Exception as e:
            logger.debug(f"Ticker parse error: {e}")
            return None
    
    def _parse_quote_packet(self, data: bytes) -> Optional[TickData]:
        """
        Parse quote packet with OHLC and volume
        Bytes: 0-7 header, then quote data
        """
        try:
            if len(data) < 52:  # Minimum quote packet size
                return None
            
            response_code, msg_len, exchange_segment, security_id = self._parse_header(data)
            
            offset = 8
            ltp = struct.unpack('<f', data[offset:offset+4])[0]; offset += 4
            ltq = struct.unpack('<H', data[offset:offset+2])[0]; offset += 2  # Last traded qty
            ltt_epoch = struct.unpack('<I', data[offset:offset+4])[0]; offset += 4
            avg_price = struct.unpack('<f', data[offset:offset+4])[0]; offset += 4
            volume = struct.unpack('<I', data[offset:offset+4])[0]; offset += 4
            total_sell_qty = struct.unpack('<I', data[offset:offset+4])[0]; offset += 4
            total_buy_qty = struct.unpack('<I', data[offset:offset+4])[0]; offset += 4
            open_price = struct.unpack('<f', data[offset:offset+4])[0]; offset += 4
            close_price = struct.unpack('<f', data[offset:offset+4])[0]; offset += 4
            high_price = struct.unpack('<f', data[offset:offset+4])[0]; offset += 4
            low_price = struct.unpack('<f', data[offset:offset+4])[0]; offset += 4
            
            return TickData(
                security_id=security_id,
                symbol=self._get_symbol_for_security(security_id),
                exchange_segment=exchange_segment,
                ltp=ltp,
                ltt=datetime.fromtimestamp(ltt_epoch) if ltt_epoch > 0 else datetime.now(),
                volume=volume,
                open=open_price,
                high=high_price,
                low=low_price,
                close=close_price,
                avg_price=avg_price,
                total_buy_qty=total_buy_qty,
                total_sell_qty=total_sell_qty
            )
        except Exception as e:
            logger.debug(f"Quote parse error: {e}")
            return None
    
    def _parse_index_packet(self, data: bytes) -> Optional[TickData]:
        """Parse index-specific packet (response code 1)"""
        # Index packets follow similar structure to ticker
        return self._parse_ticker_packet(data)
    
    def _parse_prev_close_packet(self, data: bytes) -> Optional[Dict]:
        """Parse previous close packet"""
        try:
            if len(data) < 16:
                return None
            
            response_code, msg_len, exchange_segment, security_id = self._parse_header(data)
            
            prev_close = struct.unpack('<f', data[8:12])[0]
            prev_oi = struct.unpack('<I', data[12:16])[0]
            
            return {
                "security_id": security_id,
                "prev_close": prev_close,
                "prev_oi": prev_oi
            }
        except:
            return None
    
    async def _process_message(self, data: bytes):
        """Process incoming binary message"""
        if len(data) < 8:
            return
        
        response_code = data[0]
        
        try:
            tick = None
            
            if response_code == FeedResponseCode.INDEX:
                tick = self._parse_index_packet(data)
            
            elif response_code == FeedResponseCode.TICKER:
                tick = self._parse_ticker_packet(data)
            
            elif response_code == FeedResponseCode.QUOTE:
                tick = self._parse_quote_packet(data)
            
            elif response_code == FeedResponseCode.FULL:
                tick = self._parse_quote_packet(data)  # Full has same base structure
            
            elif response_code == FeedResponseCode.PREV_CLOSE:
                prev_data = self._parse_prev_close_packet(data)
                if prev_data:
                    # Update prev_close in our symbol tracking
                    sec_id = prev_data["security_id"]
                    logger.debug(f"Prev close for {sec_id}: {prev_data['prev_close']}")
                return
            
            elif response_code == FeedResponseCode.OI:
                # OI update - log but don't process as tick
                logger.debug(f"OI update received")
                return
            
            elif response_code == FeedResponseCode.DISCONNECT:
                logger.warning("Server requested disconnect")
                disconnect_code = struct.unpack('<H', data[8:10])[0] if len(data) >= 10 else 0
                logger.warning(f"Disconnect reason code: {disconnect_code}")
                await self._handle_reconnect()
                return
            
            else:
                logger.debug(f"Unknown response code: {response_code}")
                return
            
            # Deliver tick to callbacks
            if tick:
                self._tick_count += 1
                self._last_tick_time = datetime.now()
                
                if self._on_quote and response_code in (FeedResponseCode.QUOTE, FeedResponseCode.FULL):
                    await self._on_quote(tick)
                elif self._on_tick:
                    await self._on_tick(tick)
                
        except Exception as e:
            logger.error(f"Message processing error: {e}")
    
    async def _handle_reconnect(self):
        """Handle reconnection with exponential backoff"""
        if self._reconnect_count >= self._max_reconnects:
            logger.error("Max reconnection attempts reached - giving up")
            self._should_run = False
            return
        
        self._reconnect_count += 1
        delay = min(30, 2 ** self._reconnect_count)  # Max 30 seconds
        
        logger.info(f"Reconnecting in {delay}s (attempt {self._reconnect_count}/{self._max_reconnects})")
        await asyncio.sleep(delay)
        
        # Close existing connections
        if self._ws:
            try:
                await self._ws.close()
            except:
                pass
            self._ws = None
        
        # Reconnect
        if await self.connect():
            # Resubscribe to all instruments
            idx_list = []
            for sec_id, segment in self._subscribed:
                if segment == ExchangeSegment.IDX_I and sec_id in self._security_to_symbol:
                    idx_list.append(self._security_to_symbol[sec_id])
            
            if idx_list:
                await self.subscribe_indices(idx_list, FeedRequestCode.QUOTE)
                logger.info(f"Resubscribed to {len(idx_list)} indices after reconnect")
    
    async def run(self):
        """
        Main message loop - runs indefinitely until disconnected
        Call this after connect() and subscribe_*()
        """
        self._should_run = True
        
        while self._should_run and self._connected:
            try:
                if not self._ws:
                    await self._handle_reconnect()
                    continue
                
                # Receive message with timeout
                msg = await asyncio.wait_for(
                    self._ws.receive(),
                    timeout=30
                )
                
                if msg.type == aiohttp.WSMsgType.BINARY:
                    await self._process_message(msg.data)
                
                elif msg.type == aiohttp.WSMsgType.CLOSED:
                    logger.warning("WebSocket connection closed by server")
                    self._connected = False
                    if self._should_run:
                        await self._handle_reconnect()
                
                elif msg.type == aiohttp.WSMsgType.ERROR:
                    logger.error(f"WebSocket error: {msg.data}")
                    if self._should_run:
                        await self._handle_reconnect()
                
                elif msg.type == aiohttp.WSMsgType.PING:
                    # Respond to ping with pong
                    if self._ws:
                        await self._ws.pong()
                        
            except asyncio.TimeoutError:
                # No message received - send ping to keep alive
                if self._ws and not self._ws.closed:
                    try:
                        await self._ws.ping()
                    except:
                        logger.warning("Ping failed - reconnecting")
                        await self._handle_reconnect()
            
            except asyncio.CancelledError:
                logger.info("WebSocket run cancelled")
                break
            
            except Exception as e:
                logger.error(f"WebSocket run error: {e}")
                await asyncio.sleep(1)
        
        logger.info("WebSocket run loop ended")
    
    def stop(self):
        """Stop the run loop"""
        self._should_run = False


def load_dhan_config(config_path: Optional[Path] = None) -> Dict:
    """
    Load Dhan configuration from JSON file
    
    Looks for dhan_config.json in:
    1. Provided path
    2. ai_scalping_service directory
    3. ai_options_hedger directory (shared config)
    """
    search_paths = []
    
    if config_path:
        search_paths.append(config_path)
    
    # AI Scalping service directory
    scalping_dir = Path(__file__).parent.parent
    search_paths.append(scalping_dir / "dhan_config.json")
    
    # AI Options Hedger directory (shared config)
    hedger_dir = scalping_dir.parent / "ai_options_hedger"
    search_paths.append(hedger_dir / "dhan_config.json")
    
    for path in search_paths:
        if path.exists():
            try:
                with open(path, 'r') as f:
                    config = json.load(f)
                    logger.info(f"Loaded Dhan config from: {path}")
                    return config
            except Exception as e:
                logger.warning(f"Failed to load {path}: {e}")
    
    logger.error("No dhan_config.json found!")
    return {}


def save_dhan_config(config: Dict, config_path: Optional[Path] = None) -> bool:
    """Save Dhan configuration to JSON file"""
    if config_path is None:
        config_path = Path(__file__).parent.parent / "dhan_config.json"
    
    try:
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=4)
        logger.info(f"Saved Dhan config to: {config_path}")
        return True
    except Exception as e:
        logger.error(f"Failed to save config: {e}")
        return False
