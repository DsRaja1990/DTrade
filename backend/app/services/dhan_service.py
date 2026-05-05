"""
DhanHQ API Service Integration
Comprehensive integration with DhanHQ trading APIs
"""

import asyncio
import json
import logging
import struct
import websockets
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
from urllib.parse import urlencode

import httpx
from httpx import AsyncClient, Timeout

from app.core.config import settings
from app.core.redis_client import redis_client

logger = logging.getLogger(__name__)


class DhanHQService:
    """
    Comprehensive DhanHQ API service
    
    Features:
    - Order management
    - Market data
    - Live market feed
    - Historical data
    - Option chain
    - Portfolio management
    - WebSocket integration
    """
    
    def __init__(self):
        self.base_url = settings.DHAN_API_BASE_URL
        self.feed_url = settings.DHAN_FEED_URL
        self.client_id = settings.DHAN_CLIENT_ID
        self.access_token = settings.DHAN_ACCESS_TOKEN
        
        self.http_client: Optional[AsyncClient] = None
        self.websocket_connection = None
        self.is_connected = False
        
        # Request headers
        self.headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "access-token": self.access_token,
            "client-id": self.client_id
        }
        
        # Timeout configuration
        self.timeout = Timeout(
            connect=10.0,
            read=30.0,
            write=10.0,
            pool=None
        )
        
        # Cache for instruments and market data
        self.instruments_cache: Dict[str, List[Dict]] = {}
        self.market_data_cache: Dict[str, Dict] = {}
        
        # WebSocket subscriptions
        self.subscriptions: Dict[str, List[Dict]] = {}
    
    async def initialize(self):
        """Initialize DhanHQ service"""
        try:
            logger.info("🔌 Initializing DhanHQ service...")
            
            # Create HTTP client
            self.http_client = AsyncClient(
                timeout=self.timeout,
                headers=self.headers,
                limits=httpx.Limits(
                    max_keepalive_connections=20,
                    max_connections=100,
                    keepalive_expiry=30.0
                )
            )
            
            # Test API connection
            await self.health_check()
            
            # Load instruments cache
            await self._load_instruments_cache()
            
            # Start WebSocket connection for live data
            if settings.LIVE_FEED_ENABLED:
                asyncio.create_task(self._start_websocket_connection())
            
            logger.info("✅ DhanHQ service initialized successfully")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize DhanHQ service: {e}")
            raise
    
    async def health_check(self) -> bool:
        """Check DhanHQ API health"""
        try:
            response = await self._make_request("GET", "/fundlimit")
            return response is not None
        except Exception as e:
            logger.error(f"❌ DhanHQ health check failed: {e}")
            return False
    
    async def _make_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict] = None,
        params: Optional[Dict] = None
    ) -> Optional[Dict]:
        """Make HTTP request to DhanHQ API"""
        try:
            url = f"{self.base_url}{endpoint}"
            
            if method.upper() == "GET":
                response = await self.http_client.get(url, params=params)
            elif method.upper() == "POST":
                response = await self.http_client.post(url, json=data, params=params)
            elif method.upper() == "PUT":
                response = await self.http_client.put(url, json=data, params=params)
            elif method.upper() == "DELETE":
                response = await self.http_client.delete(url, params=params)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
            
            response.raise_for_status()
            
            # Handle different response types
            content_type = response.headers.get("content-type", "")
            
            if "application/json" in content_type:
                return response.json()
            elif "text/csv" in content_type:
                # For instrument downloads
                return {"csv_data": response.text}
            else:
                return {"data": response.text}
            
        except httpx.HTTPStatusError as e:
            logger.error(f"❌ HTTP error {e.response.status_code}: {e.response.text}")
            return None
        except Exception as e:
            logger.error(f"❌ Request error: {e}")
            return None
    
    # Order Management APIs
    
    async def place_order(self, order_data: Dict[str, Any]) -> Optional[Dict]:
        """Place a new order"""
        try:
            logger.info(f"📋 Placing order: {order_data}")
            
            response = await self._make_request("POST", "/orders", data=order_data)
            
            if response:
                logger.info(f"✅ Order placed successfully: {response}")
                
                # Cache order in Redis
                order_id = response.get("orderId")
                if order_id:
                    await redis_client.hset(
                        "orders",
                        order_id,
                        {**order_data, **response, "timestamp": datetime.now().isoformat()},
                        parse_json=True
                    )
            
            return response
            
        except Exception as e:
            logger.error(f"❌ Error placing order: {e}")
            return None
    
    # Freeze quantities for order slicing (max qty per single order)
    FREEZE_QUANTITIES = {
        "NIFTY": 1800,
        "BANKNIFTY": 1050,
        "FINNIFTY": 1300,
        "SENSEX": 1000,
        "BANKEX": 900,
        "MIDCPNIFTY": 2800,
    }
    
    async def place_order_with_slicing(self, order_data: Dict[str, Any]) -> Optional[Dict]:
        """
        Place order with automatic slicing for large quantities.
        
        If quantity exceeds freeze limit, splits into multiple orders.
        Uses Dhan's order slicing API endpoint.
        """
        try:
            symbol = order_data.get("tradingSymbol", "").split()[0]  # Get base symbol
            quantity = order_data.get("quantity", 0)
            
            # Get freeze limit for this instrument
            freeze_qty = self.FREEZE_QUANTITIES.get(symbol, 1800)  # Default to NIFTY limit
            
            if quantity <= freeze_qty:
                # Normal order - within freeze limit
                return await self.place_order(order_data)
            
            # Need to slice order
            logger.info(f"📊 Order quantity {quantity} exceeds freeze limit {freeze_qty}, slicing...")
            
            order_results = []
            remaining_qty = quantity
            slice_num = 1
            
            while remaining_qty > 0:
                slice_qty = min(remaining_qty, freeze_qty)
                slice_order = order_data.copy()
                slice_order["quantity"] = slice_qty
                
                logger.info(f"📋 Placing slice {slice_num}: {slice_qty} qty")
                result = await self.place_order(slice_order)
                
                if result:
                    order_results.append(result)
                else:
                    logger.error(f"❌ Slice {slice_num} failed, stopping")
                    break
                
                remaining_qty -= slice_qty
                slice_num += 1
                
                # Small delay between slices to avoid rate limiting
                if remaining_qty > 0:
                    await asyncio.sleep(0.1)
            
            # Return combined result
            if order_results:
                return {
                    "success": True,
                    "sliced": True,
                    "total_slices": len(order_results),
                    "order_ids": [r.get("orderId") for r in order_results],
                    "total_quantity": quantity,
                    "slices": order_results
                }
            return None
            
        except Exception as e:
            logger.error(f"❌ Error placing sliced order: {e}")
            return None
    
    async def modify_order(self, order_id: str, modify_data: Dict[str, Any]) -> Optional[Dict]:
        """Modify an existing order"""
        try:
            logger.info(f"✏️ Modifying order {order_id}: {modify_data}")
            
            response = await self._make_request("PUT", f"/orders/{order_id}", data=modify_data)
            
            if response:
                logger.info(f"✅ Order modified successfully: {response}")
                
                # Update cached order
                await redis_client.hset(
                    "orders",
                    order_id,
                    {**modify_data, **response, "modified_at": datetime.now().isoformat()},
                    parse_json=True
                )
            
            return response
            
        except Exception as e:
            logger.error(f"❌ Error modifying order: {e}")
            return None
    
    async def cancel_order(self, order_id: str) -> Optional[Dict]:
        """Cancel an order"""
        try:
            logger.info(f"❌ Cancelling order {order_id}")
            
            response = await self._make_request("DELETE", f"/orders/{order_id}")
            
            if response:
                logger.info(f"✅ Order cancelled successfully: {response}")
                
                # Update cached order
                await redis_client.hset(
                    "orders",
                    order_id,
                    {**response, "cancelled_at": datetime.now().isoformat()},
                    parse_json=True
                )
            
            return response
            
        except Exception as e:
            logger.error(f"❌ Error cancelling order: {e}")
            return None
    
    async def get_order_book(self) -> Optional[List[Dict]]:
        """Get order book"""
        try:
            response = await self._make_request("GET", "/orders")
            
            if response:
                # Cache order book
                await redis_client.set("order_book", response, ttl=30)
            
            return response
            
        except Exception as e:
            logger.error(f"❌ Error getting order book: {e}")
            return None
    
    async def get_order_by_id(self, order_id: str) -> Optional[Dict]:
        """Get order by ID"""
        try:
            # Try cache first
            cached_order = await redis_client.hget("orders", order_id, parse_json=True)
            if cached_order:
                return cached_order
            
            response = await self._make_request("GET", f"/orders/{order_id}")
            
            if response:
                # Cache the order
                await redis_client.hset("orders", order_id, response, parse_json=True)
            
            return response
            
        except Exception as e:
            logger.error(f"❌ Error getting order {order_id}: {e}")
            return None
    
    async def get_trade_book(self) -> Optional[List[Dict]]:
        """Get trade book"""
        try:
            response = await self._make_request("GET", "/trades")
            
            if response:
                # Cache trade book
                await redis_client.set("trade_book", response, ttl=30)
            
            return response
            
        except Exception as e:
            logger.error(f"❌ Error getting trade book: {e}")
            return None
    
    # Super Order APIs
    
    async def place_super_order(self, super_order_data: Dict[str, Any]) -> Optional[Dict]:
        """Place a super order"""
        try:
            logger.info(f"🎯 Placing super order: {super_order_data}")
            
            response = await self._make_request("POST", "/super/orders", data=super_order_data)
            
            if response:
                logger.info(f"✅ Super order placed successfully: {response}")
            
            return response
            
        except Exception as e:
            logger.error(f"❌ Error placing super order: {e}")
            return None
    
    async def get_super_orders(self) -> Optional[List[Dict]]:
        """Get super order book"""
        try:
            response = await self._make_request("GET", "/super/orders")
            
            if response:
                # Cache super orders
                await redis_client.set("super_orders", response, ttl=30)
            
            return response
            
        except Exception as e:
            logger.error(f"❌ Error getting super orders: {e}")
            return None
    
    # Market Data APIs
    
    async def get_market_quote(
        self,
        security_id: str,
        exchange_segment: str = "NSE_FNO"
    ) -> Dict[str, Any]:
        """
        Get real-time market quote for a security
        https://dhanhq.co/docs/v2/market-quote/
        """
        try:
            url = f"{self.base_url}/marketfeed/quote"
            payload = {
                "securityId": security_id,
                "exchangeSegment": exchange_segment
            }
            
            response = await self._make_request("POST", url, json=payload)
            
            if response and response.get("status") == "success":
                data = response.get("data", {})
                
                # Cache the market data
                cache_key = f"quote:{exchange_segment}:{security_id}"
                await self._cache_data(cache_key, data, ttl=30)  # Cache for 30 seconds
                
                return data
            else:
                logger.warning(f"Market quote API returned error: {response}")
                return {}
                
        except Exception as e:
            logger.error(f"Error getting market quote for {security_id}: {e}")
            return {}
    
    async def get_nifty_option_chain(self, expiry_date: Optional[str] = None) -> Dict[str, Any]:
        """
        Get Nifty option chain data
        https://dhanhq.co/docs/v2/option-chain/
        """
        try:
            # Use current weekly expiry if not specified
            if not expiry_date:
                expiry_date = self._get_current_expiry()
            
            url = f"{self.base_url}/optionchain"
            payload = {
                "securityId": "26000",  # Nifty 50 index security ID
                "exchangeSegment": "IDX_I",
                "expiryCode": expiry_date
            }
            
            response = await self._make_request("POST", url, json=payload)
            
            if response and response.get("status") == "success":
                data = response.get("data", {})
                
                # Cache the option chain data
                cache_key = f"option_chain:NIFTY:{expiry_date}"
                await self._cache_data(cache_key, data, ttl=60)  # Cache for 1 minute
                
                return data
            else:
                logger.warning(f"Option chain API returned error: {response}")
                return {}
                
        except Exception as e:
            logger.error(f"Error getting option chain: {e}")
            return {}
    
    async def get_live_nifty_data(self) -> Dict[str, Any]:
        """Get real-time Nifty 50 data"""
        try:
            # Get Nifty 50 market quote
            nifty_data = await self.get_market_quote("26000", "IDX_I")
            
            if not nifty_data:
                logger.warning("No Nifty data from DhanHQ, falling back to Yahoo Finance")
                return await self._get_yahoo_finance_fallback()
            
            # Extract relevant data
            current_price = float(nifty_data.get("LTP", 0))
            previous_close = float(nifty_data.get("prevClose", current_price))
            change_percent = ((current_price - previous_close) / previous_close * 100) if previous_close > 0 else 0
            
            # Get volume and other data
            volume = float(nifty_data.get("totTradedVol", 0))
            high = float(nifty_data.get("high", current_price))
            low = float(nifty_data.get("low", current_price))
            
            return {
                "current_price": current_price,
                "previous_close": previous_close,
                "change_percent": change_percent,
                "volume": volume,
                "high": high,
                "low": low,
                "timestamp": datetime.utcnow(),
                "data_source": "DhanHQ Live",
                "last_updated": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting live Nifty data: {e}")
            return await self._get_yahoo_finance_fallback()
    
    async def get_live_vix_data(self) -> float:
        """Get real-time India VIX data"""
        try:
            # India VIX security ID in DhanHQ
            vix_data = await self.get_market_quote("26001", "IDX_I")
            
            if vix_data and vix_data.get("LTP"):
                vix_value = float(vix_data.get("LTP", 20.0))
                
                # Sanity check for VIX
                if 5.0 <= vix_value <= 100.0:
                    return vix_value
            
            # Fallback to Yahoo Finance
            logger.warning("VIX data not available from DhanHQ, using Yahoo Finance")
            return await self._get_vix_from_yahoo()
            
        except Exception as e:
            logger.error(f"Error getting VIX data: {e}")
            return 20.0  # Default VIX value
    
    async def get_option_prices(self, strikes: List[int], expiry: str, option_type: str = "both") -> Dict[str, Dict]:
        """
        Get real-time option prices for multiple strikes
        
        Args:
            strikes: List of strike prices
            expiry: Expiry date string
            option_type: 'CE', 'PE', or 'both'
        """
        option_prices = {}
        
        try:
            for strike in strikes:
                if option_type in ["CE", "both"]:
                    # Get Call option data
                    ce_security_id = self._get_option_security_id(strike, expiry, "CE")
                    if ce_security_id:
                        ce_data = await self.get_market_quote(ce_security_id, "NSE_FNO")
                        if ce_data:
                            option_prices[f"{strike}CE"] = {
                                "ltp": float(ce_data.get("LTP", 0)),
                                "bid": float(ce_data.get("bidPrice", 0)),
                                "ask": float(ce_data.get("askPrice", 0)),
                                "volume": float(ce_data.get("totTradedVol", 0)),
                                "oi": float(ce_data.get("openInterest", 0)),
                                "change": float(ce_data.get("change", 0)),
                                "high": float(ce_data.get("high", 0)),
                                "low": float(ce_data.get("low", 0))
                            }
                
                if option_type in ["PE", "both"]:
                    # Get Put option data
                    pe_security_id = self._get_option_security_id(strike, expiry, "PE")
                    if pe_security_id:
                        pe_data = await self.get_market_quote(pe_security_id, "NSE_FNO")
                        if pe_data:
                            option_prices[f"{strike}PE"] = {
                                "ltp": float(pe_data.get("LTP", 0)),
                                "bid": float(pe_data.get("bidPrice", 0)),
                                "ask": float(pe_data.get("askPrice", 0)),
                                "volume": float(pe_data.get("totTradedVol", 0)),
                                "oi": float(pe_data.get("openInterest", 0)),
                                "change": float(pe_data.get("change", 0)),
                                "high": float(pe_data.get("high", 0)),
                                "low": float(pe_data.get("low", 0))
                            }
                
                # Small delay to avoid overwhelming the API
                await asyncio.sleep(0.1)
                
        except Exception as e:
            logger.error(f"Error getting option prices: {e}")
        
        return option_prices
    
    async def get_historical_data(self, security_id: str, exchange_segment: str, 
                                interval: str = "1", from_date: str = None, 
                                to_date: str = None) -> List[Dict]:
        """
        Get historical data for a security
        https://dhanhq.co/docs/v2/historical-data/
        """
        try:
            if not from_date:
                from_date = (datetime.now() - timedelta(days=100)).strftime("%Y-%m-%d")
            if not to_date:
                to_date = datetime.now().strftime("%Y-%m-%d")
            
            url = f"{self.base_url}/charts/historical"
            payload = {
                "securityId": security_id,
                "exchangeSegment": exchange_segment,
                "instrument": "INDEX" if exchange_segment == "IDX_I" else "EQUITY",
                "interval": interval,
                "fromDate": from_date,
                "toDate": to_date
            }
            
            response = await self._make_request("POST", url, json=payload)
            
            if response and response.get("status") == "success":
                return response.get("data", [])
            else:
                logger.warning(f"Historical data API returned error: {response}")
                return []
                
        except Exception as e:
            logger.error(f"Error getting historical data: {e}")
            return []
    
    # =============================================================================
    # HELPER METHODS
    # =============================================================================
    
    def _get_current_expiry(self) -> str:
        """Get current weekly expiry date for options"""
        today = datetime.now()
        
        # Find next Thursday (weekly expiry)
        days_ahead = 3 - today.weekday()  # Thursday is weekday 3
        if days_ahead <= 0:  # Target day already happened this week
            days_ahead += 7
        
        expiry_date = today + timedelta(days_ahead)
        return expiry_date.strftime("%d-%m-%Y")
    
    def _get_option_security_id(self, strike: int, expiry: str, option_type: str) -> Optional[str]:
        """
        Get security ID for Nifty options
        This is a simplified version - in production, use actual security master data
        """
        try:
            # This is a simplified mapping - in production, you'd need the actual security master
            # For now, we'll generate based on pattern, but ideally load from DhanHQ security master
            
            # Format: NIFTY{expiry}{strike}{CE/PE}
            # Note: This is a placeholder - actual security IDs should be fetched from DhanHQ
            # security master or maintain a mapping table
            
            if option_type == "CE":
                # Placeholder logic - replace with actual security ID mapping
                return f"nifty_{expiry}_{strike}_ce"
            else:
                return f"nifty_{expiry}_{strike}_pe"
            
        except Exception as e:
            logger.error(f"Error getting option security ID: {e}")
            return None
    
    async def _get_yahoo_finance_fallback(self) -> Dict[str, Any]:
        """Fallback to Yahoo Finance if DhanHQ data is not available"""
        try:
            import yfinance as yf
            
            nifty = yf.Ticker("^NSEI")
            hist = nifty.history(period="2d")
            
            if not hist.empty:
                current_price = float(hist['Close'].iloc[-1])
                previous_close = float(hist['Close'].iloc[-2]) if len(hist) > 1 else current_price
                change_percent = ((current_price - previous_close) / previous_close * 100) if previous_close > 0 else 0
                
                return {
                    "current_price": current_price,
                    "previous_close": previous_close,
                    "change_percent": change_percent,
                    "volume": float(hist['Volume'].iloc[-1]),
                    "high": float(hist['High'].iloc[-1]),
                    "low": float(hist['Low'].iloc[-1]),
                    "timestamp": datetime.utcnow(),
                    "data_source": "Yahoo Finance (Fallback)",
                    "last_updated": datetime.utcnow().isoformat()
                }
        except Exception as e:
            logger.error(f"Yahoo Finance fallback failed: {e}")
        
        # Ultimate fallback with realistic current data
        return {
            "current_price": 25400.0,
            "previous_close": 25350.0,
            "change_percent": 0.2,
            "volume": 500000,
            "high": 25450.0,
            "low": 25300.0,
            "timestamp": datetime.utcnow(),
            "data_source": "Fallback Data",
            "last_updated": datetime.utcnow().isoformat()
        }
    
    async def _get_vix_from_yahoo(self) -> float:
        """Get VIX from Yahoo Finance as fallback"""
        try:
            import yfinance as yf
            
            vix = yf.Ticker("^INDIAVIX")
            hist = vix.history(period="2d")
            
            if not hist.empty:
                vix_value = float(hist['Close'].iloc[-1])
                if 5.0 <= vix_value <= 100.0:
                    return vix_value
        except Exception as e:
            logger.error(f"VIX Yahoo Finance fallback failed: {e}")
        
        return 20.0  # Default VIX
    
    async def _cache_data(self, key: str, data: Any, ttl: int = 300):
        """Cache data in Redis"""
        try:
            if redis_client:
                await redis_client.setex(key, ttl, json.dumps(data, default=str))
        except Exception as e:
            logger.warning(f"Failed to cache data: {e}")
    
    async def _get_cached_data(self, key: str) -> Optional[Any]:
        """Get cached data from Redis"""
        try:
            if redis_client:
                cached = await redis_client.get(key)
                if cached:
                    return json.loads(cached)
        except Exception as e:
            logger.warning(f"Failed to get cached data: {e}")
        return None
    
    # =============================================================================
    # MARKET DATA METHODS
    # =============================================================================
    
    async def get_market_quote(self, security_id: str, exchange_segment: str = "NSE_FNO") -> Dict[str, Any]:
        """
        Get real-time market quote for a security
        https://dhanhq.co/docs/v2/market-quote/
        """
        try:
            url = f"{self.base_url}/marketfeed/quote"
            payload = {
                "securityId": security_id,
                "exchangeSegment": exchange_segment
            }
            
            response = await self._make_request("POST", url, json=payload)
            
            if response and response.get("status") == "success":
                data = response.get("data", {})
                
                # Cache the market data
                cache_key = f"quote:{exchange_segment}:{security_id}"
                await self._cache_data(cache_key, data, ttl=30)  # Cache for 30 seconds
                
                return data
            else:
                logger.warning(f"Market quote API returned error: {response}")
                return {}
                
        except Exception as e:
            logger.error(f"Error getting market quote for {security_id}: {e}")
            return {}
    
    async def get_nifty_option_chain(self, expiry_date: Optional[str] = None) -> Dict[str, Any]:
        """
        Get Nifty option chain data
        https://dhanhq.co/docs/v2/option-chain/
        """
        try:
            # Use current weekly expiry if not specified
            if not expiry_date:
                expiry_date = self._get_current_expiry()
            
            url = f"{self.base_url}/optionchain"
            payload = {
                "securityId": "26000",  # Nifty 50 index security ID
                "exchangeSegment": "IDX_I",
                "expiryCode": expiry_date
            }
            
            response = await self._make_request("POST", url, json=payload)
            
            if response and response.get("status") == "success":
                data = response.get("data", {})
                
                # Cache the option chain data
                cache_key = f"option_chain:NIFTY:{expiry_date}"
                await self._cache_data(cache_key, data, ttl=60)  # Cache for 1 minute
                
                return data
            else:
                logger.warning(f"Option chain API returned error: {response}")
                return {}
                
        except Exception as e:
            logger.error(f"Error getting option chain: {e}")
            return {}
    
    async def get_live_nifty_data(self) -> Dict[str, Any]:
        """Get real-time Nifty 50 data"""
        try:
            # Get Nifty 50 market quote
            nifty_data = await self.get_market_quote("26000", "IDX_I")
            
            if not nifty_data:
                logger.warning("No Nifty data from DhanHQ, falling back to Yahoo Finance")
                return await self._get_yahoo_finance_fallback()
            
            # Extract relevant data
            current_price = float(nifty_data.get("LTP", 0))
            previous_close = float(nifty_data.get("prevClose", current_price))
            change_percent = ((current_price - previous_close) / previous_close * 100) if previous_close > 0 else 0
            
            # Get volume and other data
            volume = float(nifty_data.get("totTradedVol", 0))
            high = float(nifty_data.get("high", current_price))
            low = float(nifty_data.get("low", current_price))
            
            return {
                "current_price": current_price,
                "previous_close": previous_close,
                "change_percent": change_percent,
                "volume": volume,
                "high": high,
                "low": low,
                "timestamp": datetime.utcnow(),
                "data_source": "DhanHQ Live",
                "last_updated": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting live Nifty data: {e}")
            return await self._get_yahoo_finance_fallback()
    
    async def get_live_vix_data(self) -> float:
        """Get real-time India VIX data"""
        try:
            # India VIX security ID in DhanHQ
            vix_data = await self.get_market_quote("26001", "IDX_I")
            
            if vix_data and vix_data.get("LTP"):
                vix_value = float(vix_data.get("LTP", 20.0))
                
                # Sanity check for VIX
                if 5.0 <= vix_value <= 100.0:
                    return vix_value
            
            # Fallback to Yahoo Finance
            logger.warning("VIX data not available from DhanHQ, using Yahoo Finance")
            return await self._get_vix_from_yahoo()
            
        except Exception as e:
            logger.error(f"Error getting VIX data: {e}")
            return 20.0  # Default VIX value
    
    async def get_option_prices(self, strikes: List[int], expiry: str, option_type: str = "both") -> Dict[str, Dict]:
        """
        Get real-time option prices for multiple strikes
        
        Args:
            strikes: List of strike prices
            expiry: Expiry date string
            option_type: 'CE', 'PE', or 'both'
        """
        option_prices = {}
        
        try:
            for strike in strikes:
                if option_type in ["CE", "both"]:
                    # Get Call option data
                    ce_security_id = self._get_option_security_id(strike, expiry, "CE")
                    if ce_security_id:
                        ce_data = await self.get_market_quote(ce_security_id, "NSE_FNO")
                        if ce_data:
                            option_prices[f"{strike}CE"] = {
                                "ltp": float(ce_data.get("LTP", 0)),
                                "bid": float(ce_data.get("bidPrice", 0)),
                                "ask": float(ce_data.get("askPrice", 0)),
                                "volume": float(ce_data.get("totTradedVol", 0)),
                                "oi": float(ce_data.get("openInterest", 0)),
                                "change": float(ce_data.get("change", 0)),
                                "high": float(ce_data.get("high", 0)),
                                "low": float(ce_data.get("low", 0))
                            }
                
                if option_type in ["PE", "both"]:
                    # Get Put option data
                    pe_security_id = self._get_option_security_id(strike, expiry, "PE")
                    if pe_security_id:
                        pe_data = await self.get_market_quote(pe_security_id, "NSE_FNO")
                        if pe_data:
                            option_prices[f"{strike}PE"] = {
                                "ltp": float(pe_data.get("LTP", 0)),
                                "bid": float(pe_data.get("bidPrice", 0)),
                                "ask": float(pe_data.get("askPrice", 0)),
                                "volume": float(pe_data.get("totTradedVol", 0)),
                                "oi": float(pe_data.get("openInterest", 0)),
                                "change": float(pe_data.get("change", 0)),
                                "high": float(pe_data.get("high", 0)),
                                "low": float(pe_data.get("low", 0))
                            }
                
                # Small delay to avoid overwhelming the API
                await asyncio.sleep(0.1)
                
        except Exception as e:
            logger.error(f"Error getting option prices: {e}")
        
        return option_prices
    
    async def get_historical_data(self, security_id: str, exchange_segment: str, 
                                interval: str = "1", from_date: str = None, 
                                to_date: str = None) -> List[Dict]:
        """
        Get historical data for a security
        https://dhanhq.co/docs/v2/historical-data/
        """
        try:
            if not from_date:
                from_date = (datetime.now() - timedelta(days=100)).strftime("%Y-%m-%d")
            if not to_date:
                to_date = datetime.now().strftime("%Y-%m-%d")
            
            url = f"{self.base_url}/charts/historical"
            payload = {
                "securityId": security_id,
                "exchangeSegment": exchange_segment,
                "instrument": "INDEX" if exchange_segment == "IDX_I" else "EQUITY",
                "interval": interval,
                "fromDate": from_date,
                "toDate": to_date
            }
            
            response = await self._make_request("POST", url, json=payload)
            
            if response and response.get("status") == "success":
                return response.get("data", [])
            else:
                logger.warning(f"Historical data API returned error: {response}")
                return []
                
        except Exception as e:
            logger.error(f"Error getting historical data: {e}")
            return []
    
    # =============================================================================
    # HELPER METHODS
    # =============================================================================
    
    def _get_current_expiry(self) -> str:
        """Get current weekly expiry date for options"""
        today = datetime.now()
        
        # Find next Thursday (weekly expiry)
        days_ahead = 3 - today.weekday()  # Thursday is weekday 3
        if days_ahead <= 0:  # Target day already happened this week
            days_ahead += 7
        
        expiry_date = today + timedelta(days_ahead)
        return expiry_date.strftime("%d-%m-%Y")
    
    def _get_option_security_id(self, strike: int, expiry: str, option_type: str) -> Optional[str]:
        """
        Get security ID for Nifty options
        This is a simplified version - in production, use actual security master data
        """
        try:
            # This is a simplified mapping - in production, you'd need the actual security master
            # For now, we'll generate based on pattern, but ideally load from DhanHQ security master
            
            # Format: NIFTY{expiry}{strike}{CE/PE}
            # Note: This is a placeholder - actual security IDs should be fetched from DhanHQ
            # security master or maintain a mapping table
            
            if option_type == "CE":
                # Placeholder logic - replace with actual security ID mapping
                return f"nifty_{expiry}_{strike}_ce"
            else:
                return f"nifty_{expiry}_{strike}_pe"
            
        except Exception as e:
            logger.error(f"Error getting option security ID: {e}")
            return None
    
    async def _get_yahoo_finance_fallback(self) -> Dict[str, Any]:
        """Fallback to Yahoo Finance if DhanHQ data is not available"""
        try:
            import yfinance as yf
            
            nifty = yf.Ticker("^NSEI")
            hist = nifty.history(period="2d")
            
            if not hist.empty:
                current_price = float(hist['Close'].iloc[-1])
                previous_close = float(hist['Close'].iloc[-2]) if len(hist) > 1 else current_price
                change_percent = ((current_price - previous_close) / previous_close * 100) if previous_close > 0 else 0
                
                return {
                    "current_price": current_price,
                    "previous_close": previous_close,
                    "change_percent": change_percent,
                    "volume": float(hist['Volume'].iloc[-1]),
                    "high": float(hist['High'].iloc[-1]),
                    "low": float(hist['Low'].iloc[-1]),
                    "timestamp": datetime.utcnow(),
                    "data_source": "Yahoo Finance (Fallback)",
                    "last_updated": datetime.utcnow().isoformat()
                }
        except Exception as e:
            logger.error(f"Yahoo Finance fallback failed: {e}")
        
        # Ultimate fallback with realistic current data
        return {
            "current_price": 25400.0,
            "previous_close": 25350.0,
            "change_percent": 0.2,
            "volume": 500000,
            "high": 25450.0,
            "low": 25300.0,
            "timestamp": datetime.utcnow(),
            "data_source": "Fallback Data",
            "last_updated": datetime.utcnow().isoformat()
        }
    
    async def _get_vix_from_yahoo(self) -> float:
        """Get VIX from Yahoo Finance as fallback"""
        try:
            import yfinance as yf
            
            vix = yf.Ticker("^INDIAVIX")
            hist = vix.history(period="2d")
            
            if not hist.empty:
                vix_value = float(hist['Close'].iloc[-1])
                if 5.0 <= vix_value <= 100.0:
                    return vix_value
        except Exception as e:
            logger.error(f"VIX Yahoo Finance fallback failed: {e}")
        
        return 20.0  # Default VIX
    
    async def _cache_data(self, key: str, data: Any, ttl: int = 300):
        """Cache data in Redis"""
        try:
            if redis_client:
                await redis_client.setex(key, ttl, json.dumps(data, default=str))
        except Exception as e:
            logger.warning(f"Failed to cache data: {e}")
    
    async def _get_cached_data(self, key: str) -> Optional[Any]:
        """Get cached data from Redis"""
        try:
            if redis_client:
                cached = await redis_client.get(key)
                if cached:
                    return json.loads(cached)
        except Exception as e:
            logger.warning(f"Failed to get cached data: {e}")
        return None
    
    # WebSocket Live Market Feed
    
    async def _start_websocket_connection(self):
        """Start WebSocket connection for live market data"""
        try:
            logger.info("🔗 Starting WebSocket connection...")
            
            # Construct WebSocket URL
            ws_url = f"{self.feed_url}?version=2&token={self.access_token}&clientId={self.client_id}&authType=2"
            
            while True:
                try:
                    async with websockets.connect(
                        ws_url,
                        ping_interval=30,
                        ping_timeout=10,
                        close_timeout=10
                    ) as websocket:
                        self.websocket_connection = websocket
                        self.is_connected = True
                        
                        logger.info("✅ WebSocket connected successfully")
                        
                        # Subscribe to default instruments
                        await self._subscribe_default_instruments()
                        
                        # Listen for messages
                        async for message in websocket:
                            if isinstance(message, bytes):
                                await self._process_binary_message(message)
                            else:
                                await self._process_text_message(message)
                                
                except websockets.exceptions.ConnectionClosed:
                    logger.warning("⚠️ WebSocket connection closed, reconnecting...")
                    self.is_connected = False
                    await asyncio.sleep(5)
                    
                except Exception as e:
                    logger.error(f"❌ WebSocket error: {e}")
                    self.is_connected = False
                    await asyncio.sleep(10)
                    
        except Exception as e:
            logger.error(f"❌ Error starting WebSocket connection: {e}")
    
    async def _subscribe_default_instruments(self):
        """Subscribe to default instruments"""
        try:
            # Subscribe to NIFTY and SENSEX
            instruments = [
                {"ExchangeSegment": "IDX_I", "SecurityId": "13"},    # NIFTY
                {"ExchangeSegment": "IDX_I", "SecurityId": "1"},     # SENSEX
            ]
            
            await self.subscribe_to_feed(instruments, "ticker")
            
            logger.info("✅ Subscribed to default instruments")
            
        except Exception as e:
            logger.error(f"❌ Error subscribing to default instruments: {e}")
    
    async def subscribe_to_feed(
        self,
        instruments: List[Dict[str, str]],
        feed_type: str = "ticker"
    ):
        """Subscribe to live market feed"""
        try:
            if not self.is_connected or not self.websocket_connection:
                logger.warning("⚠️ WebSocket not connected")
                return
            
            # Determine request code
            request_codes = {
                "ticker": settings.FEED_REQUEST_CODES["SUBSCRIBE_TICKER"],
                "quote": settings.FEED_REQUEST_CODES["SUBSCRIBE_QUOTE"],
                "full": settings.FEED_REQUEST_CODES["SUBSCRIBE_FULL"]
            }
            
            request_code = request_codes.get(feed_type, 15)
            
            # Prepare subscription message
            message = {
                "RequestCode": request_code,
                "InstrumentCount": len(instruments),
                "InstrumentList": instruments
            }
            
            # Send subscription
            await self.websocket_connection.send(json.dumps(message))
            
            # Store subscriptions
            if feed_type not in self.subscriptions:
                self.subscriptions[feed_type] = []
            
            self.subscriptions[feed_type].extend(instruments)
            
            logger.info(f"✅ Subscribed to {len(instruments)} instruments for {feed_type}")
            
        except Exception as e:
            logger.error(f"❌ Error subscribing to feed: {e}")
    
    async def _process_binary_message(self, message: bytes):
        """Process binary WebSocket message"""
        try:
            if len(message) < 8:
                return
            
            # Parse header (8 bytes)
            response_code = struct.unpack('B', message[0:1])[0]
            message_length = struct.unpack('>H', message[1:3])[0]
            exchange_segment = struct.unpack('B', message[3:4])[0]
            security_id = struct.unpack('>I', message[4:8])[0]
            
            # Process based on response code
            if response_code == 2:  # Ticker packet
                await self._process_ticker_packet(message[8:], security_id, exchange_segment)
            elif response_code == 4:  # Quote packet
                await self._process_quote_packet(message[8:], security_id, exchange_segment)
            elif response_code == 8:  # Full packet
                await self._process_full_packet(message[8:], security_id, exchange_segment)
            
        except Exception as e:
            logger.error(f"❌ Error processing binary message: {e}")
    
    async def _process_ticker_packet(self, data: bytes, security_id: int, exchange_segment: int):
        """Process ticker packet"""
        try:
            if len(data) < 8:
                return
            
            last_price = struct.unpack('>f', data[0:4])[0]
            last_trade_time = struct.unpack('>I', data[4:8])[0]
            
            ticker_data = {
                "security_id": str(security_id),
                "exchange_segment": exchange_segment,
                "last_price": last_price,
                "last_trade_time": last_trade_time,
                "timestamp": datetime.now().isoformat()
            }
            
            # Cache market data
            cache_key = f"live_ticker_{exchange_segment}_{security_id}"
            await redis_client.set(cache_key, ticker_data, ttl=10)
            
            # Broadcast to WebSocket clients
            from app.core.websocket_manager import websocket_manager
            await websocket_manager.send_market_data(ticker_data)
            
        except Exception as e:
            logger.error(f"❌ Error processing ticker packet: {e}")
    
    async def _process_quote_packet(self, data: bytes, security_id: int, exchange_segment: int):
        """Process quote packet"""
        try:
            if len(data) < 42:
                return
            
            # Parse quote data
            last_price = struct.unpack('>f', data[0:4])[0]
            last_quantity = struct.unpack('>H', data[4:6])[0]
            last_trade_time = struct.unpack('>I', data[6:10])[0]
            avg_price = struct.unpack('>f', data[10:14])[0]
            volume = struct.unpack('>I', data[14:18])[0]
            total_sell_qty = struct.unpack('>I', data[18:22])[0]
            total_buy_qty = struct.unpack('>I', data[22:26])[0]
            day_open = struct.unpack('>f', data[26:30])[0]
            day_close = struct.unpack('>f', data[30:34])[0]
            day_high = struct.unpack('>f', data[34:38])[0]
            day_low = struct.unpack('>f', data[38:42])[0]
            
            quote_data = {
                "security_id": str(security_id),
                "exchange_segment": exchange_segment,
                "last_price": last_price,
                "last_quantity": last_quantity,
                "last_trade_time": last_trade_time,
                "average_price": avg_price,
                "volume": volume,
                "total_sell_quantity": total_sell_qty,
                "total_buy_quantity": total_buy_qty,
                "ohlc": {
                    "open": day_open,
                    "high": day_high,
                    "low": day_low,
                    "close": day_close
                },
                "timestamp": datetime.now().isoformat()
            }
            
            # Cache market data
            cache_key = f"live_quote_{exchange_segment}_{security_id}"
            await redis_client.set(cache_key, quote_data, ttl=10)
            
            # Broadcast to WebSocket clients
            from app.core.websocket_manager import websocket_manager
            await websocket_manager.send_market_data(quote_data)
            
        except Exception as e:
            logger.error(f"❌ Error processing quote packet: {e}")
    
    async def _process_full_packet(self, data: bytes, security_id: int, exchange_segment: int):
        """Process full packet with market depth"""
        try:
            # Process quote part first
            await self._process_quote_packet(data[:42], security_id, exchange_segment)
            
            if len(data) >= 162:
                # Parse market depth (5 levels)
                depth_data = {"buy": [], "sell": []}
                
                for i in range(5):
                    offset = 42 + (i * 20)
                    
                    bid_qty = struct.unpack('>I', data[offset:offset+4])[0]
                    ask_qty = struct.unpack('>I', data[offset+4:offset+8])[0]
                    bid_orders = struct.unpack('>H', data[offset+8:offset+10])[0]
                    ask_orders = struct.unpack('>H', data[offset+10:offset+12])[0]
                    bid_price = struct.unpack('>f', data[offset+12:offset+16])[0]
                    ask_price = struct.unpack('>f', data[offset+16:offset+20])[0]
                    
                    depth_data["buy"].append({
                        "quantity": bid_qty,
                        "orders": bid_orders,
                        "price": bid_price
                    })
                    
                    depth_data["sell"].append({
                        "quantity": ask_qty,
                        "orders": ask_orders,
                        "price": ask_price
                    })
                
                # Cache depth data
                cache_key = f"live_depth_{exchange_segment}_{security_id}"
                await redis_client.set(cache_key, depth_data, ttl=10)
            
        except Exception as e:
            logger.error(f"❌ Error processing full packet: {e}")
    
    async def _process_text_message(self, message: str):
        """Process text WebSocket message"""
        try:
            data = json.loads(message)
            logger.info(f"📨 WebSocket text message: {data}")
            
        except Exception as e:
            logger.error(f"❌ Error processing text message: {e}")
    
    async def cleanup(self):
        """Cleanup DhanHQ service"""
        try:
            logger.info("🧹 Cleaning up DhanHQ service...")
            
            # Close WebSocket connection
            if self.websocket_connection:
                await self.websocket_connection.close()
                self.is_connected = False
            
            # Close HTTP client
            if self.http_client:
                await self.http_client.aclose()
            
            logger.info("✅ DhanHQ service cleanup completed")
            
        except Exception as e:
            logger.error(f"❌ Error during DhanHQ service cleanup: {e}")


# Create global DhanHQ service instance
dhan_service = DhanHQService()
