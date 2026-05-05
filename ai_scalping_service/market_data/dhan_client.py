"""
Dhan API Client for Index Scalping Strategy
Handles real-time data feeds, order management, and market data
"""

import asyncio
import aiohttp
import json
import logging
import websockets
import struct
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, time
from dataclasses import dataclass
from config.settings import config

logger = logging.getLogger(__name__)

@dataclass
class TickData:
    """Real-time tick data structure"""
    symbol: str
    exchange: str
    timestamp: datetime
    ltp: float
    volume: int
    oi: int
    bid: float
    ask: float
    bid_qty: int
    ask_qty: int

@dataclass
class OptionChainData:
    """Option chain data structure"""
    strike: float
    ce_ltp: float
    ce_volume: int
    ce_oi: int
    pe_ltp: float
    pe_volume: int
    pe_oi: int
    timestamp: datetime

@dataclass
class OrderRequest:
    """Order placement request"""
    symbol: str
    exchange: str
    transaction_type: str  # "BUY" or "SELL"
    order_type: str  # "MARKET" or "LIMIT"
    quantity: int
    price: Optional[float] = None
    product_type: str = "INTRADAY"
    validity: str = "DAY"

class DhanAPIClient:
    """Dhan API client for real-time trading and data"""
    
    def __init__(self):
        self.access_token = config.dhan.access_token
        self.client_id = config.dhan.client_id
        self.base_url = config.dhan.base_url
        self.session: Optional[aiohttp.ClientSession] = None
        self.websocket: Optional[websockets.WebSocketServerProtocol] = None
        
        # Data callbacks
        self.tick_callbacks: List[Callable] = []
        self.option_chain_callbacks: List[Callable] = []
        
        # Market data cache
        self.tick_cache: Dict[str, TickData] = {}
        self.option_chains: Dict[str, Dict[float, OptionChainData]] = {}
        
        # Connection status
        self.is_connected = False
        self.websocket_connected = False
        self.market_status = "unknown"  # "online", "offline", "api_only"
        
        # Logger
        import logging
        self.logger = logging.getLogger(__name__)
        
    async def initialize(self):
        """Initialize API client and connections"""
        try:
            # Create HTTP session with proper Dhan API headers
            self.session = aiohttp.ClientSession(
                headers={
                    "Content-Type": "application/json",
                    "access-token": self.access_token
                },
                timeout=aiohttp.ClientTimeout(total=10.0)
            )
            
            # Test connection
            await self._test_connection()
            
            # Check market status
            await self._check_market_status()
            
            # Start WebSocket connection for live data (only if market is online)
            if self.market_status in ["online", "api_only"]:
                websocket_success = await self._connect_websocket()
                self.websocket_connected = websocket_success
            else:
                self.logger.info("Market is offline, skipping WebSocket connection")
                self.websocket_connected = False
            
            self.is_connected = True
            self.logger.info(f"🚀 Dhan API client initialized - Market: {self.market_status}, WebSocket: {self.websocket_connected}")
            
        except Exception as e:
            self.logger.error(f"❌ Failed to initialize Dhan API client: {e}")
            # Set offline mode if initialization fails
            self.market_status = "offline"
            self.websocket_connected = False
            self.is_connected = True  # Still allow API-only operations
            raise
    
    async def _test_connection(self):
        """Test API connection"""
        try:
            # Test with funds endpoint as per Dhan API v2
            url = f"{self.base_url}/v2/fundlimit"
            headers = {
                "Content-Type": "application/json",
                "access-token": self.access_token
            }
            
            async with self.session.get(url, headers=headers) as response:
                response_text = await response.text()
                logger.info(f"API test response status: {response.status}")
                logger.info(f"API test response: {response_text[:200]}")
                
                if response.status == 200:
                    data = await response.json()
                    logger.info(f"✅ API connection successful. Fund details received")
                    return True
                else:
                    # Log error details for debugging
                    logger.error(f"❌ API test failed with status {response.status}: {response_text}")
                    raise Exception(f"API test failed with status {response.status}")
                    
        except Exception as e:
            logger.error(f"❌ API connection test failed: {e}")
            raise
            
    async def _check_market_status(self):
        """Check current market status"""
        try:
            from datetime import datetime, time
            import pytz
            
            # Get current time in India timezone
            india_tz = pytz.timezone('Asia/Kolkata')
            now = datetime.now(india_tz)
            current_time = now.time()
            
            # Market hours: 9:15 AM to 3:30 PM IST
            market_open = time(9, 15)
            market_close = time(15, 30)
            
            # Check if today is a weekday (Monday=0, Sunday=6)
            is_weekday = now.weekday() < 5
            
            if is_weekday and market_open <= current_time <= market_close:
                self.market_status = "online"
                self.logger.info("✅ Market is ONLINE - Live trading hours")
            else:
                self.market_status = "offline"
                if not is_weekday:
                    self.logger.info("📅 Market is OFFLINE - Weekend")
                else:
                    self.logger.info(f"🕒 Market is OFFLINE - Outside trading hours (Current: {current_time.strftime('%H:%M')})")
                    
        except Exception as e:
            self.logger.warning(f"Could not determine market status: {e}")
            self.market_status = "api_only"
    
    async def _connect_websocket(self):
        """Connect to Dhan WebSocket for live market data"""
        try:
            # WebSocket URL for live market feed as per Dhan API v2
            ws_url = "wss://api-feed.dhan.co"
            
            # Create headers for WebSocket connection
            headers = {
                "access-token": self.access_token,
                "client-id": self.client_id,
                "User-Agent": "DTrade-IndexScalping/1.0"
            }
            
            # Connect to WebSocket with proper headers - use create_connection for compatibility
            import websockets.client
            import websockets.exceptions
            
            try:
                # Try modern websockets library first
                self.websocket = await websockets.connect(
                    ws_url,
                    additional_headers=headers  # Use additional_headers instead of extra_headers
                )
            except (TypeError, websockets.exceptions.InvalidMessage) as e:
                self.logger.warning(f"Modern WebSocket connection failed, trying legacy mode: {e}")
                
                # Fallback for older websockets library
                try:
                    self.websocket = await websockets.connect(ws_url)
                    # Send authentication via message after connection
                    auth_msg = {
                        "RequestCode": 10,  # Authentication
                        "access_token": self.access_token,
                        "client_id": self.client_id
                    }
                    await self.websocket.send(json.dumps(auth_msg))
                except Exception as fallback_error:
                    self.logger.error(f"WebSocket fallback connection failed: {fallback_error}")
                    self.websocket_connected = False
                    return False
            
            # Send connection request as per Dhan protocol
            connect_request = {
                "RequestCode": 11,  # Connect Feed
                "InstrumentCount": 0,
                "InstrumentList": []
            }
            
            await self.websocket.send(json.dumps(connect_request))
            
            # Start listening for messages
            asyncio.create_task(self._websocket_listener())
            
            self.logger.info("🔗 WebSocket connection established with Dhan feed")
            self.websocket_connected = True
            return True
            
        except Exception as e:
            self.logger.error(f"❌ WebSocket connection failed: {e}")
            # Don't raise here - WebSocket is optional for basic functionality
            self.logger.warning("📡 Continuing without live WebSocket feed")
            self.websocket = None
            self.websocket_connected = False
            return False
    
    async def _websocket_listener(self):
        """Listen for WebSocket messages - handles both JSON and binary packets"""
        try:
            if not self.websocket:
                return
                
            async for message in self.websocket:
                try:
                    if isinstance(message, bytes):
                        # Handle binary packet as per Dhan API specification
                        await self._process_binary_packet(message)
                    else:
                        # Handle JSON message (responses to requests)
                        data = json.loads(message)
                        await self._process_websocket_message(data)
                        
                except Exception as e:
                    logger.error(f"❌ Error processing WebSocket message: {e}")
                    continue
                
        except websockets.exceptions.ConnectionClosed:
            logger.warning("🔌 WebSocket connection closed")
            await self._reconnect_websocket()
        except Exception as e:
            logger.error(f"❌ WebSocket listener error: {e}")
            
    async def _process_binary_packet(self, packet: bytes):
        """Process binary packet from Dhan WebSocket feed"""
        try:
            if len(packet) < 4:
                return
                
            # Parse header to get response code (first 4 bytes)
            response_code = struct.unpack('<I', packet[:4])[0]
            
            if response_code == 2:  # Ticker Packet
                tick_data = self._parse_ticker_packet(packet)
                if tick_data:
                    await self._notify_tick_callbacks(tick_data)
                    
            elif response_code == 4:  # Quote Packet
                quote_data = self._parse_quote_packet(packet)
                if quote_data:
                    await self._notify_tick_callbacks(quote_data)
                    
            elif response_code == 8:  # Full Packet
                full_data = self._parse_full_packet(packet)
                if full_data:
                    await self._notify_tick_callbacks(full_data)
                    
        except Exception as e:
            logger.error(f"❌ Error processing binary packet: {e}")
            
    def _parse_ticker_packet(self, packet: bytes) -> Optional[TickData]:
        """Parse ticker packet format"""
        try:
            if len(packet) < 16:
                return None
                
            # Basic ticker packet structure (simplified)
            security_id = struct.unpack('<I', packet[4:8])[0]
            ltp = struct.unpack('<f', packet[8:12])[0]
            volume = struct.unpack('<I', packet[12:16])[0]
            
            return TickData(
                symbol=f"ID_{security_id}",
                exchange="NSE",  # Default for now
                timestamp=datetime.now(),
                ltp=float(ltp),
                volume=int(volume),
                oi=0,  # Not in ticker packet
                bid=0.0,
                ask=0.0,
                bid_qty=0,
                ask_qty=0
            )
            
        except Exception as e:
            logger.error(f"❌ Error parsing ticker packet: {e}")
            return None
    
    async def _process_websocket_message(self, data: Dict):
        """Process incoming WebSocket messages"""
        try:
            message_type = data.get("type")
            
            if message_type == "tick":
                tick_data = self._parse_tick_data(data)
                await self._notify_tick_callbacks(tick_data)
                
            elif message_type == "option_chain":
                chain_data = self._parse_option_chain_data(data)
                await self._notify_option_chain_callbacks(chain_data)
                
        except Exception as e:
            logger.error(f"❌ Error processing WebSocket message: {e}")
    
    def _parse_tick_data(self, data: Dict) -> TickData:
        """Parse tick data from WebSocket message"""
        return TickData(
            symbol=data.get("symbol"),
            exchange=data.get("exchange"),
            timestamp=datetime.now(),
            ltp=float(data.get("ltp", 0)),
            volume=int(data.get("volume", 0)),
            oi=int(data.get("oi", 0)),
            bid=float(data.get("bid", 0)),
            ask=float(data.get("ask", 0)),
            bid_qty=int(data.get("bid_qty", 0)),
            ask_qty=int(data.get("ask_qty", 0))
        )
    
    def _parse_option_chain_data(self, data: Dict) -> OptionChainData:
        """Parse option chain data from WebSocket message"""
        return OptionChainData(
            strike=float(data.get("strike")),
            ce_ltp=float(data.get("ce_ltp", 0)),
            ce_volume=int(data.get("ce_volume", 0)),
            ce_oi=int(data.get("ce_oi", 0)),
            pe_ltp=float(data.get("pe_ltp", 0)),
            pe_volume=int(data.get("pe_volume", 0)),
            pe_oi=int(data.get("pe_oi", 0)),
            timestamp=datetime.now()
        )
    
    async def _notify_tick_callbacks(self, tick_data: TickData):
        """Notify all tick data callbacks"""
        self.tick_cache[f"{tick_data.symbol}_{tick_data.exchange}"] = tick_data
        
        for callback in self.tick_callbacks:
            try:
                await callback(tick_data)
            except Exception as e:
                logger.error(f"❌ Error in tick callback: {e}")
    
    async def _notify_option_chain_callbacks(self, chain_data: OptionChainData):
        """Notify all option chain callbacks"""
        symbol_key = f"{chain_data.strike}"
        if symbol_key not in self.option_chains:
            self.option_chains[symbol_key] = {}
        
        self.option_chains[symbol_key][chain_data.strike] = chain_data
        
        for callback in self.option_chain_callbacks:
            try:
                await callback(chain_data)
            except Exception as e:
                logger.error(f"❌ Error in option chain callback: {e}")
    
    async def _reconnect_websocket(self):
        """Reconnect WebSocket on disconnection"""
        logger.info("🔄 Attempting WebSocket reconnection...")
        await asyncio.sleep(5)  # Wait before reconnecting
        try:
            await self._connect_websocket()
            logger.info("✅ WebSocket reconnected successfully")
        except Exception as e:
            logger.error(f"❌ WebSocket reconnection failed: {e}")
            # Schedule another reconnection attempt
            asyncio.create_task(self._reconnect_websocket())
    
    async def subscribe_to_symbol(self, symbol: str, exchange: str):
        """Subscribe to real-time data for a symbol"""
        try:
            if not self.websocket:
                raise Exception("WebSocket not connected")
                
            subscription_message = {
                "type": "subscribe",
                "symbol": symbol,
                "exchange": exchange
            }
            
            await self.websocket.send(json.dumps(subscription_message))
            logger.info(f"📡 Subscribed to {symbol} on {exchange}")
            
        except Exception as e:
            logger.error(f"❌ Failed to subscribe to {symbol}: {e}")
    
    async def get_option_chain(self, underlying_scrip: int, underlying_seg: str = "IDX_I", expiry: str = None) -> Dict[float, OptionChainData]:
        """Get current option chain data using Dhan API v2"""
        try:
            url = f"{self.base_url}/v2/optionchain"
            
            request_data = {
                "UnderlyingScrip": underlying_scrip,  # Security ID like 13 for NIFTY
                "UnderlyingSeg": underlying_seg,      # "IDX_I" for indices
            }
            
            if expiry:
                request_data["Expiry"] = expiry  # Format: "2024-12-26"
            
            headers = {
                "Content-Type": "application/json",
                "access-token": self.access_token,
                "client-id": self.client_id
            }
            
            async with self.session.post(url, json=request_data, headers=headers) as response:
                response_text = await response.text()
                
                if response.status == 200:
                    data = await response.json()
                    return self._process_option_chain_response(data)
                else:
                    logger.error(f"❌ Option chain request failed: Status {response.status}, Response: {response_text}")
                    return {}
                    
        except Exception as e:
            logger.error(f"❌ Failed to get option chain: {e}")
            return {}
    
    def _process_option_chain_response(self, data: Dict) -> Dict[float, OptionChainData]:
        """Process option chain API response from Dhan API v2"""
        option_chain = {}
        
        try:
            chain_data = data.get("data", {})
            option_data = chain_data.get("oc", {})
            
            for strike_str, strike_info in option_data.items():
                strike = float(strike_str)
                
                ce_data = strike_info.get("ce", {})
                pe_data = strike_info.get("pe", {})
                
                option_chain[strike] = OptionChainData(
                    strike=strike,
                    ce_ltp=float(ce_data.get("last_price", 0)),
                    ce_volume=int(ce_data.get("volume", 0)),
                    ce_oi=int(ce_data.get("oi", 0)),
                    pe_ltp=float(pe_data.get("last_price", 0)),
                    pe_volume=int(pe_data.get("volume", 0)),
                    pe_oi=int(pe_data.get("oi", 0)),
                    timestamp=datetime.now()
                )
                
        except Exception as e:
            logger.error(f"❌ Error processing option chain response: {e}")
            
        return option_chain
            
        return option_chain
    
    async def place_order(self, order: OrderRequest) -> Dict:
        """Place an order using Dhan API v2"""
        try:
            url = f"{self.base_url}/v2/orders"
            
            # Format order request according to Dhan API v2 specification
            order_data = {
                "dhanClientId": self.client_id,
                "correlationId": f"IS_{int(datetime.now().timestamp())}",  # Index Scalping correlation ID
                "transactionType": order.transaction_type,  # "BUY" or "SELL"
                "exchangeSegment": order.exchange,  # e.g., "NSE_FNO"
                "productType": order.product_type,  # "INTRADAY"
                "orderType": order.order_type,  # "MARKET" or "LIMIT"
                "validity": order.validity,  # "DAY"
                "securityId": order.symbol,  # Security ID (to be resolved from symbol)
                "quantity": str(order.quantity),
                "disclosedQuantity": "",
                "price": str(order.price) if order.price else "",
                "triggerPrice": "",
                "afterMarketOrder": False,
                "amoTime": "",
                "boProfitValue": "",
                "boStopLossValue": ""
            }
            
            headers = {
                "Content-Type": "application/json",
                "access-token": self.access_token
            }
            
            async with self.session.post(url, json=order_data, headers=headers) as response:
                response_text = await response.text()
                
                if response.status == 200:
                    result = await response.json()
                    order_id = result.get("orderId")
                    logger.info(f"✅ Order placed successfully: {order_id}")
                    return result
                else:
                    logger.error(f"❌ Order placement failed: Status {response.status}, Response: {response_text}")
                    raise Exception(f"Order placement failed: {response_text}")
                    
        except Exception as e:
            logger.error(f"❌ Failed to place order: {e}")
            raise
    
    async def get_positions(self) -> List[Dict]:
        """Get current positions"""
        try:
            url = f"{self.base_url}/v2/positions"
            headers = {
                "Content-Type": "application/json",
                "access-token": self.access_token
            }
            
            async with self.session.get(url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get("data", [])
                else:
                    response_text = await response.text()
                    logger.error(f"❌ Positions request failed: Status {response.status}, Response: {response_text}")
                    return []
                    
        except Exception as e:
            logger.error(f"❌ Failed to get positions: {e}")
            return []
    
    async def get_funds(self) -> Dict:
        """Get fund limits"""
        try:
            url = f"{self.base_url}/v2/fundlimit"
            headers = {
                "Content-Type": "application/json",
                "access-token": self.access_token
            }
            
            async with self.session.get(url, headers=headers) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    response_text = await response.text()
                    logger.error(f"❌ Funds request failed: Status {response.status}, Response: {response_text}")
                    return {}
                    
        except Exception as e:
            logger.error(f"❌ Failed to get funds: {e}")
            return {}
    
    async def get_market_quote(self, security_id: str, exchange_segment: str) -> Dict:
        """Get market quote for a security using Dhan API v2"""
        try:
            url = f"{self.base_url}/v2/marketfeed/quote"
            
            request_data = {
                "NSE_EQ": [security_id] if exchange_segment == "NSE_EQ" else [],
                "NSE_FNO": [security_id] if exchange_segment == "NSE_FNO" else [],
                "BSE_EQ": [security_id] if exchange_segment == "BSE_EQ" else [],
                "MCX_COMM": [security_id] if exchange_segment == "MCX_COMM" else []
            }
            
            headers = {
                "Content-Type": "application/json",
                "access-token": self.access_token
            }
            
            async with self.session.post(url, json=request_data, headers=headers) as response:
                response_text = await response.text()
                
                if response.status == 200:
                    data = await response.json()
                    return data.get("data", {})
                else:
                    logger.error(f"❌ Market quote request failed: Status {response.status}, Response: {response_text}")
                    return {}
                    
        except Exception as e:
            logger.error(f"❌ Failed to get market quote: {e}")
            return {}
    
    async def get_ticker_data(self, security_id: str, exchange_segment: str) -> Dict:
        """Get ticker data for a security using Dhan API v2"""
        try:
            url = f"{self.base_url}/v2/marketfeed/ltp"
            
            request_data = {
                "NSE_EQ": [security_id] if exchange_segment == "NSE_EQ" else [],
                "NSE_FNO": [security_id] if exchange_segment == "NSE_FNO" else [],
                "BSE_EQ": [security_id] if exchange_segment == "BSE_EQ" else [],
                "MCX_COMM": [security_id] if exchange_segment == "MCX_COMM" else []
            }
            
            headers = {
                "Content-Type": "application/json",
                "access-token": self.access_token
            }
            
            async with self.session.post(url, json=request_data, headers=headers) as response:
                response_text = await response.text()
                
                if response.status == 200:
                    data = await response.json()
                    return data.get("data", {})
                else:
                    logger.error(f"❌ Ticker data request failed: Status {response.status}, Response: {response_text}")
                    return {}
                    
        except Exception as e:
            logger.error(f"❌ Failed to get ticker data: {e}")
            return {}

    def add_tick_callback(self, callback: Callable):
        """Add callback for tick data"""
        self.tick_callbacks.append(callback)
    
    def add_option_chain_callback(self, callback: Callable):
        """Add callback for option chain data"""
        self.option_chain_callbacks.append(callback)
    
    async def close(self):
        """Close all connections"""
        try:
            if self.websocket:
                await self.websocket.close()
            
            if self.session:
                await self.session.close()
                
            self.is_connected = False
            logger.info("🔌 Dhan API client closed successfully")
            
        except Exception as e:
            logger.error(f"❌ Error closing Dhan API client: {e}")

# Global API client instance
dhan_client = DhanAPIClient()
