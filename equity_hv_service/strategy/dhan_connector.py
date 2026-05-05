"""
Dhan API Connector for Equity High-Velocity Trading
Enhanced API client with real-time market data and order execution
"""

import asyncio
import aiohttp
import websockets
import json
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable, Tuple
import pandas as pd
from dataclasses import dataclass
import uuid

logger = logging.getLogger(__name__)

@dataclass
class MarketData:
    """Real-time market data structure"""
    symbol: str
    timestamp: datetime
    price: float
    volume: int
    open: float
    high: float
    low: float
    close: float
    bid: float = 0
    ask: float = 0
    vwap: float = 0
    open_interest: int = 0
    total_buy_quantity: int = 0
    total_sell_quantity: int = 0
    day_high: float = 0
    day_low: float = 0
    last_trade_time: datetime = None
    
    # Enhanced metrics for hyper edition
    buy_sell_ratio: float = 1.0
    price_velocity: float = 0
    price_acceleration: float = 0
    volume_surge_factor: float = 1.0
    bid_ask_imbalance: float = 0
    
    @property
    def spread(self) -> float:
        """Calculate bid-ask spread"""
        if self.ask > 0 and self.bid > 0:
            return self.ask - self.bid
        return 0
    
    @property
    def spread_pct(self) -> float:
        """Calculate percentage bid-ask spread"""
        if self.ask > 0 and self.bid > 0:
            return (self.ask - self.bid) / ((self.ask + self.bid) / 2) * 100
        return 0
    
    @property
    def is_momentum_burst(self) -> bool:
        """Detect if current tick represents a momentum burst"""
        return (self.volume_surge_factor > 2.5 and 
                abs(self.price_velocity) > 0.01 and 
                abs(self.price_acceleration) > 0.002)

@dataclass
class OptionChainData:
    """Enhanced option chain data structure"""
    underlying: str
    expiry: str
    strike: float
    option_type: str  # CE/PE
    price: float
    bid: float
    ask: float
    volume: int
    open_interest: int
    iv: float = 0
    delta: float = 0
    gamma: float = 0
    theta: float = 0
    vega: float = 0
    timestamp: datetime = None
    
    # Enhanced fields for hyper edition
    iv_percentile: float = 50
    iv_rank: float = 50
    skew_score: float = 0
    volume_oi_ratio: float = 0
    gamma_exposure: float = 0
    liquidity_score: float = 0
    premium_decay_rate: float = 0
    theoretical_edge: float = 0
    
    @property
    def days_to_expiry(self) -> float:
        """Calculate days to expiry"""
        if not self.timestamp:
            self.timestamp = datetime.now()
        expiry_date = datetime.strptime(self.expiry, "%Y-%m-%d")
        return (expiry_date - self.timestamp).total_seconds() / 86400
    
    @property
    def is_otm(self) -> bool:
        """Check if option is out of the money"""
        return (self.option_type == "CE" and self.strike > self.price) or \
               (self.option_type == "PE" and self.strike < self.price)
    
    @property
    def moneyness(self) -> float:
        """Calculate option moneyness as percentage"""
        if self.price > 0:
            return (self.strike / self.price - 1) * 100
        return 0

class DhanAPIClient:
    """Enhanced Dhan API client for market data and order execution"""
    
    def __init__(self, config):
        self.config = config
        self.client_id = config.dhan_client_id
        self.access_token = config.dhan_access_token
        self.base_url = config.dhan_base_url
        self.ws_url = config.dhan_ws_url
        self.session = None
        self.ws_connection = None
        self.instruments_cache = {}
        self.subscription_callbacks = {}
        self.is_connected = False
        self.last_request_time = 0
        self.order_history = {}
        
        # Enhanced fields for hyper edition
        self.retry_count = 0
        self.max_retries = 3
        self.connection_health = 1.0  # 0.0 to 1.0
        self.recent_latencies = []
        self.live_data_cache = {}  # Cache for live market data
        
        # Rate limiting
        self.rate_limit_per_second = 10
        self.request_timestamps = []
        
        # Initialize logger
        self.logger = logging.getLogger(__name__ + ".DhanAPIClient")
    
    async def initialize(self):
        """Initialize API client"""
        try:
            self.logger.info("Initializing Dhan API client")
            await self._create_session()
            await self._load_instruments()
            if not self.config.paper_trading:
                await self._connect_websocket()
            return True
        except Exception as e:
            self.logger.error(f"Failed to initialize Dhan API: {str(e)}")
            return False
    
    async def _create_session(self):
        """Create aiohttp session"""
        timeout = aiohttp.ClientTimeout(total=30)
        self.session = aiohttp.ClientSession(
            timeout=timeout,
            headers={
                "Content-Type": "application/json",
                "client_id": self.client_id,
                "access-token": self.access_token
            }
        )
    
    async def _load_instruments(self):
        """Load instruments from Dhan instruments CSV"""
        try:
            instruments_url = "https://images.dhan.co/api-data/api-scrip-master-detailed.csv"
            
            # Use pandas to load the CSV
            df = pd.read_csv(instruments_url)
            
            # Cache instruments for quick lookup
            for _, row in df.iterrows():
                symbol = row.get('tradingsymbol', '')
                exchange = row.get('exchange_segment', '')
                
                if symbol and exchange:
                    key = f"{symbol}_{exchange}"
                    self.instruments_cache[key] = {
                        'security_id': row.get('instrument_key', ''),
                        'exchange_segment': exchange,
                        'tradingsymbol': symbol,
                        'lot_size': row.get('lot_size', 1),
                        'tick_size': row.get('tick_size', 0.05),
                        'instrument_type': row.get('instrument_type', ''),
                        'expiry': row.get('expiry', ''),
                        'strike': row.get('strike', 0),
                        'option_type': row.get('option_type', '')
                    }
            
            self.logger.info(f"Loaded {len(self.instruments_cache)} instruments")
            
        except Exception as e:
            self.logger.error(f"Failed to load instruments: {e}")
            # Load minimal instruments for testing
            self._load_minimal_instruments()
    
    def _load_minimal_instruments(self):
        """Load minimal instruments for testing"""
        elite_stocks = ["ADANIENT", "TRENT", "BAJFINANCE", "TATAMOTORS", 
                       "RELIANCE", "HDFCBANK", "ICICIBANK", "ZEEL", "PNB", "RBLBANK"]
        
        for symbol in elite_stocks:
            key = f"{symbol}_NSE_EQ"
            self.instruments_cache[key] = {
                'security_id': f"NSE_EQ|{symbol}",
                'exchange_segment': 'NSE_EQ',
                'tradingsymbol': symbol,
                'lot_size': 1,
                'tick_size': 0.05,
                'instrument_type': 'EQUITY',
                'expiry': '',
                'strike': 0,
                'option_type': ''
            }
    
    async def _connect_websocket(self):
        """Connect to Dhan WebSocket for real-time data"""
        try:
            self.ws_connection = await websockets.connect(
                self.ws_url,
                extra_headers={
                    "access-token": self.access_token,
                    "client_id": self.client_id
                }
            )
            self.is_connected = True
            self.logger.info("WebSocket connected successfully")
            
            # Start listening for messages
            asyncio.create_task(self._websocket_listener())
            
        except Exception as e:
            self.logger.error(f"Failed to connect WebSocket: {e}")
            self.is_connected = False
    
    async def _websocket_listener(self):
        """Listen for WebSocket messages"""
        try:
            async for message in self.ws_connection:
                try:
                    data = json.loads(message)
                    await self._process_websocket_message(data)
                except Exception as e:
                    self.logger.error(f"Error processing WebSocket message: {e}")
        except Exception as e:
            self.logger.error(f"WebSocket listener error: {e}")
            self.is_connected = False
    
    async def _process_websocket_message(self, data):
        """Process incoming WebSocket messages"""
        try:
            if data.get('type') == 'ticker':
                # Process ticker data
                symbol = data.get('symbol', '')
                market_data = MarketData(
                    symbol=symbol,
                    timestamp=datetime.now(),
                    price=data.get('last_price', 0),
                    volume=data.get('volume', 0),
                    open=data.get('open', 0),
                    high=data.get('high', 0),
                    low=data.get('low', 0),
                    close=data.get('close', 0),
                    bid=data.get('bid', 0),
                    ask=data.get('ask', 0),
                    vwap=data.get('vwap', 0),
                    open_interest=data.get('open_interest', 0)
                )
                
                # Cache the data
                self.live_data_cache[symbol] = market_data
                
                # Call registered callbacks
                for callback in self.subscription_callbacks.get(symbol, []):
                    try:
                        await callback(market_data)
                    except Exception as e:
                        self.logger.error(f"Error in subscription callback: {e}")
                        
        except Exception as e:
            self.logger.error(f"Error processing WebSocket message: {e}")
    
    async def _make_request(self, method: str, endpoint: str, params: Dict = None, data: Dict = None):
        """Make HTTP request to Dhan API with rate limiting"""
        start_time = time.time()
        
        # Rate limiting
        await self._check_rate_limit()
        
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        
        try:
            if method.upper() == "GET":
                async with self.session.get(url, params=params) as response:
                    result = await self._handle_response(response)
            elif method.upper() == "POST":
                async with self.session.post(url, json=data) as response:
                    result = await self._handle_response(response)
            elif method.upper() == "PUT":
                async with self.session.put(url, json=data) as response:
                    result = await self._handle_response(response)
            elif method.upper() == "DELETE":
                async with self.session.delete(url) as response:
                    result = await self._handle_response(response)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
            
            # Track latency
            latency = time.time() - start_time
            self._update_latency(latency)
            
            return result
            
        except Exception as e:
            self.logger.error(f"Request error for {method} {url}: {e}")
            self.connection_health -= 0.1
            raise
    
    async def _check_rate_limit(self):
        """Check and enforce rate limiting"""
        now = time.time()
        
        # Remove old timestamps
        self.request_timestamps = [ts for ts in self.request_timestamps if now - ts < 1.0]
        
        # Check if we need to wait
        if len(self.request_timestamps) >= self.rate_limit_per_second:
            sleep_time = 1.0 - (now - self.request_timestamps[0])
            if sleep_time > 0:
                await asyncio.sleep(sleep_time)
        
        # Add current timestamp
        self.request_timestamps.append(now)
    
    async def _handle_response(self, response):
        """Handle HTTP response"""
        if response.status in [200, 201]:
            try:
                return await response.json()
            except:
                return {"status": "success", "data": await response.text()}
        else:
            error_text = await response.text()
            self.logger.error(f"API error {response.status}: {error_text}")
            return {"status": "error", "message": error_text}
    
    def _update_latency(self, latency: float):
        """Track API latency for performance monitoring"""
        self.recent_latencies.append(latency)
        if len(self.recent_latencies) > 20:
            self.recent_latencies.pop(0)
        
        # Update connection health based on latency
        avg_latency = sum(self.recent_latencies) / len(self.recent_latencies)
        if avg_latency < 0.1:
            self.connection_health = min(1.0, self.connection_health + 0.01)
        elif avg_latency > 0.5:
            self.connection_health = max(0.0, self.connection_health - 0.02)
    
    async def place_hyper_order(self, order_data: Dict[str, Any], is_urgent: bool = False):
        """Place an order with enhanced error handling for hyper edition"""
        start_time = time.time()
        
        try:
            if self.config.paper_trading:
                self.logger.info(f"HYPER PAPER TRADE - Order placed: {json.dumps(order_data)}")
                # Simulate order response
                order_id = f"paper_{uuid.uuid4()}"
                self.order_history[order_id] = {
                    "order_data": order_data,
                    "status": "COMPLETE",
                    "filled_price": order_data.get("price", 0),
                    "timestamp": datetime.now().isoformat(),
                    "is_urgent": is_urgent
                }
                return {
                    "status": "success",
                    "data": {
                        "order_id": order_id,
                        "status": "COMPLETE"
                    }
                }
            
            # For urgent orders, use market price
            if is_urgent and order_data.get("order_type") == "LIMIT":
                self.logger.info("Converting urgent order to MARKET type")
                order_data["order_type"] = "MARKET"
                order_data.pop("price", None)
            
            # Enhanced retry logic
            retries = 0
            while retries < self.max_retries:
                try:
                    response = await self._make_request(
                        "POST",
                        "/v2/orders",
                        data=order_data
                    )
                    
                    if response.get("status") == "success":
                        order_id = response.get('data', {}).get('order_id')
                        self.logger.info(f"Order placed successfully: {order_id}")
                        
                        # Track order in history
                        self.order_history[order_id] = {
                            "order_data": order_data,
                            "status": "PENDING",
                            "timestamp": datetime.now().isoformat(),
                            "is_urgent": is_urgent
                        }
                        
                        # Update latency tracking
                        latency = time.time() - start_time
                        self._update_latency(latency)
                        
                        return response
                    else:
                        self.logger.error(f"Order placement failed: {response.get('message')}")
                        retries += 1
                        await asyncio.sleep(0.1)  # Small delay before retry
                
                except Exception as e:
                    self.logger.error(f"Error in order placement attempt {retries+1}: {str(e)}")
                    retries += 1
                    await asyncio.sleep(0.2)  # Slightly longer delay on exception
            
            # All retries failed
            self.connection_health -= 0.1  # Reduce connection health score
            return {"status": "error", "message": "All order placement retries failed"}
                
        except Exception as e:
            self.logger.error(f"Critical error placing order: {str(e)}")
            self.connection_health -= 0.2  # Larger reduction for critical errors
            return {"status": "error", "message": str(e)}
    
    async def get_quote(self, symbol: str, exchange: str = "NSE_EQ"):
        """Get market quote for a symbol"""
        try:
            # Check cache first for live data
            if symbol in self.live_data_cache:
                return self.live_data_cache[symbol]
            
            # Get instrument details
            instrument = self.get_instrument(symbol, exchange)
            if not instrument:
                return None
            
            if self.config.paper_trading:
                # Simulate quote for paper trading
                import random
                base_price = random.uniform(100, 2000)
                return MarketData(
                    symbol=symbol,
                    timestamp=datetime.now(),
                    price=base_price,
                    volume=random.randint(1000, 100000),
                    open=base_price * random.uniform(0.98, 1.02),
                    high=base_price * random.uniform(1.0, 1.05),
                    low=base_price * random.uniform(0.95, 1.0),
                    close=base_price,
                    bid=base_price * 0.999,
                    ask=base_price * 1.001
                )
            
            # Make API call for real data
            security_id = instrument.get('security_id')
            response = await self._make_request("GET", f"/v2/marketfeed/quote/{security_id}")
            
            if response.get("status") == "success":
                data = response.get("data", {})
                return MarketData(
                    symbol=symbol,
                    timestamp=datetime.now(),
                    price=data.get("last_price", 0),
                    volume=data.get("volume", 0),
                    open=data.get("open", 0),
                    high=data.get("high", 0),
                    low=data.get("low", 0),
                    close=data.get("close", 0),
                    bid=data.get("bid", 0),
                    ask=data.get("ask", 0)
                )
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error getting quote for {symbol}: {e}")
            return None
    
    async def get_option_chain(self, underlying: str, expiry: str = None):
        """Get option chain for underlying"""
        try:
            if self.config.paper_trading:
                # Simulate option chain for paper trading
                return self._simulate_option_chain(underlying, expiry)
            
            # Get real option chain from API
            params = {"symbol": underlying}
            if expiry:
                params["expiry"] = expiry
            
            response = await self._make_request("GET", "/v2/optionchain", params=params)
            
            if response.get("status") == "success":
                return self._parse_option_chain(response.get("data", []))
            
            return []
            
        except Exception as e:
            self.logger.error(f"Error getting option chain for {underlying}: {e}")
            return []
    
    def _simulate_option_chain(self, underlying: str, expiry: str = None):
        """Simulate option chain for paper trading"""
        import random
        from datetime import datetime, timedelta
        
        # Get base price
        base_price = random.uniform(1000, 3000)
        
        if not expiry:
            # Use weekly expiry (next Thursday)
            today = datetime.now()
            days_ahead = (3 - today.weekday()) % 7
            if days_ahead == 0:  # If today is Thursday
                days_ahead = 7  # Next Thursday
            expiry_date = today + timedelta(days=days_ahead)
            expiry = expiry_date.strftime("%Y-%m-%d")
        
        options = []
        
        # Generate strikes around ATM
        atm_strike = round(base_price / 50) * 50
        for i in range(-10, 11):  # 21 strikes
            strike = atm_strike + (i * 50)
            
            # Call option
            call_price = max(0.05, base_price - strike + random.uniform(-50, 50))
            options.append(OptionChainData(
                underlying=underlying,
                expiry=expiry,
                strike=strike,
                option_type="CE",
                price=call_price,
                bid=call_price * 0.995,
                ask=call_price * 1.005,
                volume=random.randint(100, 10000),
                open_interest=random.randint(1000, 100000),
                iv=random.uniform(0.15, 0.45),
                delta=max(0, min(1, (base_price - strike) / base_price + 0.5)),
                gamma=random.uniform(0.001, 0.01),
                theta=random.uniform(-2, -0.1),
                vega=random.uniform(0.1, 2.0),
                timestamp=datetime.now()
            ))
            
            # Put option
            put_price = max(0.05, strike - base_price + random.uniform(-50, 50))
            options.append(OptionChainData(
                underlying=underlying,
                expiry=expiry,
                strike=strike,
                option_type="PE",
                price=put_price,
                bid=put_price * 0.995,
                ask=put_price * 1.005,
                volume=random.randint(100, 10000),
                open_interest=random.randint(1000, 100000),
                iv=random.uniform(0.15, 0.45),
                delta=max(-1, min(0, (base_price - strike) / base_price - 0.5)),
                gamma=random.uniform(0.001, 0.01),
                theta=random.uniform(-2, -0.1),
                vega=random.uniform(0.1, 2.0),
                timestamp=datetime.now()
            ))
        
        return options
    
    def _parse_option_chain(self, data: List[Dict]) -> List[OptionChainData]:
        """Parse option chain data from API response"""
        options = []
        
        for item in data:
            try:
                option = OptionChainData(
                    underlying=item.get("underlying", ""),
                    expiry=item.get("expiry", ""),
                    strike=float(item.get("strike", 0)),
                    option_type=item.get("option_type", ""),
                    price=float(item.get("last_price", 0)),
                    bid=float(item.get("bid", 0)),
                    ask=float(item.get("ask", 0)),
                    volume=int(item.get("volume", 0)),
                    open_interest=int(item.get("open_interest", 0)),
                    iv=float(item.get("implied_volatility", 0)),
                    delta=float(item.get("delta", 0)),
                    gamma=float(item.get("gamma", 0)),
                    theta=float(item.get("theta", 0)),
                    vega=float(item.get("vega", 0)),
                    timestamp=datetime.now()
                )
                options.append(option)
            except Exception as e:
                self.logger.error(f"Error parsing option data: {e}")
                continue
        
        return options
    
    def get_instrument(self, symbol: str, exchange: str = "NSE_EQ"):
        """Get instrument details"""
        key = f"{symbol}_{exchange}"
        return self.instruments_cache.get(key)
    
    async def subscribe_symbol(self, symbol: str, callback: Callable):
        """Subscribe to real-time data for a symbol"""
        if symbol not in self.subscription_callbacks:
            self.subscription_callbacks[symbol] = []
        
        self.subscription_callbacks[symbol].append(callback)
        
        if self.is_connected and self.ws_connection:
            # Send subscription message
            message = {
                "type": "subscribe",
                "symbol": symbol
            }
            await self.ws_connection.send(json.dumps(message))
            self.logger.info(f"Subscribed to {symbol}")
    
    async def unsubscribe_symbol(self, symbol: str):
        """Unsubscribe from real-time data"""
        if symbol in self.subscription_callbacks:
            del self.subscription_callbacks[symbol]
        
        if self.is_connected and self.ws_connection:
            # Send unsubscription message
            message = {
                "type": "unsubscribe",
                "symbol": symbol
            }
            await self.ws_connection.send(json.dumps(message))
            self.logger.info(f"Unsubscribed from {symbol}")
    
    async def get_fund_limits(self) -> Dict[str, Any]:
        """
        Get fund limits from Dhan API
        
        Returns:
            Dictionary with fund limit details:
            - availabelBalance: Available amount to trade
            - sodLimit: Start of day balance
            - collateralAmount: Amount against collateral
            - utilizedAmount: Amount utilized today
            - withdrawableBalance: Amount available to withdraw
        """
        try:
            if self.config.paper_trading:
                # Simulate fund limits for paper trading
                return {
                    "dhanClientId": self.client_id,
                    "availabelBalance": 500000.0,  # ₹5 Lakh simulated
                    "sodLimit": 500000.0,
                    "collateralAmount": 0.0,
                    "receiveableAmount": 0.0,
                    "utilizedAmount": 0.0,
                    "blockedPayoutAmount": 0.0,
                    "withdrawableBalance": 500000.0
                }
            
            response = await self._make_request("GET", "/v2/fundlimit")
            
            if response.get("status") == "error":
                self.logger.error(f"Error getting fund limits: {response.get('message')}")
                return {}
            
            self.logger.info(f"Fund limits retrieved: ₹{response.get('availabelBalance', 0):,.2f} available")
            return response
            
        except Exception as e:
            self.logger.error(f"Error getting fund limits: {e}")
            return {}
    
    async def calculate_margin(self, 
                               security_id: str,
                               exchange_segment: str,
                               transaction_type: str,
                               quantity: int,
                               product_type: str,
                               price: float,
                               trigger_price: float = 0) -> Dict[str, Any]:
        """
        Calculate margin requirement for an order
        
        Args:
            security_id: Exchange security ID
            exchange_segment: NSE_FNO, NSE_EQ, etc.
            transaction_type: BUY/SELL
            quantity: Order quantity
            product_type: INTRADAY, CNC, MARGIN, etc.
            price: Order price
            trigger_price: Trigger price for SL orders
            
        Returns:
            Dictionary with margin details:
            - totalMargin: Total margin required
            - spanMargin: SPAN margin
            - exposureMargin: Exposure margin
            - availableBalance: Available balance
            - insufficientBalance: Shortfall amount
            - brokerage: Brokerage charges
            - leverage: Margin leverage
        """
        try:
            if self.config.paper_trading:
                # Simulate margin calculation for paper trading
                total_value = quantity * price
                return {
                    "totalMargin": total_value * 0.20,  # 20% margin
                    "spanMargin": total_value * 0.12,
                    "exposureMargin": total_value * 0.08,
                    "availableBalance": 500000.0,
                    "variableMargin": total_value * 0.05,
                    "insufficientBalance": 0.0,
                    "brokerage": 20.0,
                    "leverage": "5.00"
                }
            
            payload = {
                "dhanClientId": self.client_id,
                "exchangeSegment": exchange_segment,
                "transactionType": transaction_type,
                "quantity": quantity,
                "productType": product_type,
                "securityId": security_id,
                "price": price,
                "triggerPrice": trigger_price
            }
            
            response = await self._make_request("POST", "/v2/margincalculator", data=payload)
            
            if response.get("status") == "error":
                self.logger.error(f"Error calculating margin: {response.get('message')}")
                return {}
            
            self.logger.debug(f"Margin calculated: ₹{response.get('totalMargin', 0):,.2f} required")
            return response
            
        except Exception as e:
            self.logger.error(f"Error calculating margin: {e}")
            return {}
    
    async def validate_trade_capital(self,
                                      security_id: str,
                                      exchange_segment: str,
                                      quantity: int,
                                      price: float,
                                      product_type: str = "INTRADAY") -> Tuple[bool, Dict]:
        """
        Validate if sufficient capital exists for a trade
        
        Args:
            security_id: Exchange security ID
            exchange_segment: Exchange segment
            quantity: Order quantity
            price: Order price
            product_type: Product type
            
        Returns:
            Tuple of (is_valid, details_dict)
        """
        try:
            # Get current fund limits
            fund_limits = await self.get_fund_limits()
            available_balance = float(fund_limits.get("availabelBalance", 0))
            
            # Calculate margin requirement
            margin_req = await self.calculate_margin(
                security_id=security_id,
                exchange_segment=exchange_segment,
                transaction_type="BUY",
                quantity=quantity,
                product_type=product_type,
                price=price
            )
            
            total_margin = float(margin_req.get("totalMargin", 0))
            brokerage = float(margin_req.get("brokerage", 0))
            total_required = total_margin + brokerage
            
            is_valid = available_balance >= total_required
            
            details = {
                "available_balance": available_balance,
                "total_margin_required": total_margin,
                "brokerage": brokerage,
                "total_required": total_required,
                "shortfall": max(0, total_required - available_balance),
                "is_sufficient": is_valid,
                "utilization_pct": (total_required / available_balance * 100) if available_balance > 0 else 100
            }
            
            if is_valid:
                self.logger.info(f"✅ Capital validation passed: ₹{total_required:,.2f} required, "
                               f"₹{available_balance:,.2f} available")
            else:
                self.logger.warning(f"❌ Capital validation failed: ₹{total_required:,.2f} required, "
                                  f"₹{available_balance:,.2f} available, "
                                  f"Shortfall: ₹{details['shortfall']:,.2f}")
            
            return is_valid, details
            
        except Exception as e:
            self.logger.error(f"Error validating trade capital: {e}")
            return False, {"error": str(e)}
    
    async def close(self):
        """Close API client connections"""
        if self.ws_connection:
            await self.ws_connection.close()
        
        if self.session:
            await self.session.close()
        
        self.is_connected = False
        self.logger.info("Dhan API client closed")
