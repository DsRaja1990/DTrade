"""
DhanHQ API Connector for Indian Markets Trading System
"""
import requests
import json
import logging
import websocket
import threading
import time
import pandas as pd
from datetime import datetime

logger = logging.getLogger(__name__)

class DhanConnector:
    def __init__(self, api_key, client_id, access_token):
        self.api_key = api_key
        self.client_id = client_id
        self.access_token = access_token
        self.base_url = "https://api.dhan.co"
        self.ws_url = "wss://feed.dhan.co"
        self.ws = None
        self.ws_connected = False
        self.callbacks = {}
        self.instrument_cache = {}
        
    def connect(self):
        """Establish connection and authenticate with DhanHQ"""
        try:
            # Test connection with a simple request
            self.get_user_profile()
            
            # Initialize websocket connection
            self._connect_websocket()
            
            logger.info("Successfully connected to DhanHQ API")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to DhanHQ API: {e}", exc_info=True)
            return False
    
    def disconnect(self):
        """Disconnect from DhanHQ API"""
        if self.ws and self.ws_connected:
            self.ws.close()
            self.ws_connected = False
        logger.info("Disconnected from DhanHQ API")
    
    def _connect_websocket(self):
        """Establish WebSocket connection for real-time data"""
        def on_message(ws, message):
            data = json.loads(message)
            
            # Process based on message type
            if "type" in data:
                if data["type"] in self.callbacks:
                    for callback in self.callbacks[data["type"]]:
                        try:
                            callback(data)
                        except Exception as e:
                            logger.error(f"Error in callback: {e}", exc_info=True)
        
        def on_error(ws, error):
            logger.error(f"WebSocket error: {error}")
        
        def on_close(ws, close_status_code, close_msg):
            self.ws_connected = False
            logger.info(f"WebSocket connection closed: {close_status_code}, {close_msg}")
            
            # Attempt to reconnect after a delay
            if hasattr(self, '_reconnect_attempt') and self._reconnect_attempt < 5:
                self._reconnect_attempt += 1
                time.sleep(5 * self._reconnect_attempt)
                threading.Thread(target=self._connect_websocket).start()
        
        def on_open(ws):
            self.ws_connected = True
            self._reconnect_attempt = 0
            logger.info("WebSocket connection established")
            
            # Authenticate websocket
            auth_message = {
                "type": "authenticate",
                "apiKey": self.api_key,
                "accessToken": self.access_token
            }
            ws.send(json.dumps(auth_message))
        
        self._reconnect_attempt = 0
        self.ws = websocket.WebSocketApp(
            self.ws_url,
            on_message=on_message,
            on_error=on_error,
            on_close=on_close,
            on_open=on_open
        )
        
        # Start WebSocket connection in a separate thread
        self.ws_thread = threading.Thread(target=self.ws.run_forever)
        self.ws_thread.daemon = True
        self.ws_thread.start()
        
        # Wait for connection to establish
        timeout = 10
        start_time = time.time()
        while not self.ws_connected and (time.time() - start_time) < timeout:
            time.sleep(0.1)
        
        if not self.ws_connected:
            raise ConnectionError("Failed to establish WebSocket connection")
    
    def register_callback(self, message_type, callback):
        """Register a callback for specific message type"""
        if message_type not in self.callbacks:
            self.callbacks[message_type] = []
        self.callbacks[message_type].append(callback)
    
    def subscribe_ticker(self, instrument_id):
        """Subscribe to ticker data for an instrument"""
        if not self.ws_connected:
            raise ConnectionError("WebSocket not connected")
            
        message = {
            "type": "subscribe",
            "instrument_id": instrument_id
        }
        self.ws.send(json.dumps(message))
        logger.info(f"Subscribed to instrument: {instrument_id}")
    
    def unsubscribe_ticker(self, instrument_id):
        """Unsubscribe from ticker data"""
        if not self.ws_connected:
            return
            
        message = {
            "type": "unsubscribe",
            "instrument_id": instrument_id
        }
        self.ws.send(json.dumps(message))
        logger.info(f"Unsubscribed from instrument: {instrument_id}")
    
    def _make_request(self, method, endpoint, params=None, data=None):
        """Make HTTP request to DhanHQ API"""
        url = f"{self.base_url}/{endpoint}"
        headers = {
            "Content-Type": "application/json",
            "client_id": self.client_id,
            "access-token": self.access_token
        }
        
        try:
            if method == "GET":
                response = requests.get(url, headers=headers, params=params)
            elif method == "POST":
                response = requests.post(url, headers=headers, json=data)
            elif method == "PUT":
                response = requests.put(url, headers=headers, json=data)
            elif method == "DELETE":
                response = requests.delete(url, headers=headers)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
            
            if response.status_code in [200, 201]:
                return response.json()
            else:
                logger.error(f"API request failed: {response.status_code}, {response.text}")
                response.raise_for_status()
        
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error: {e}", exc_info=True)
            raise
    
    # User and Account Methods
    def get_user_profile(self):
        """Get user profile information"""
        return self._make_request("GET", "v2/user/profile")
    
    def get_account_holdings(self):
        """Get account holdings"""
        return self._make_request("GET", "v2/portfolio/holdings")
    
    def get_account_positions(self):
        """Get current open positions"""
        return self._make_request("GET", "v2/portfolio/positions")
    
    def get_account_balance(self):
        """Get account balance and funds"""
        return self._make_request("GET", "v2/user/funds")
    
    # Market Data Methods
    def get_option_chain(self, symbol, expiry_date=None):
        """Get option chain for a symbol"""
        params = {"symbol": symbol}
        if expiry_date:
            params["expiryDate"] = expiry_date
        return self._make_request("GET", "v2/markets/option-chain", params=params)
    
    def get_historical_data(self, instrument_id, from_date, to_date, interval="1D"):
        """Get historical data for an instrument"""
        params = {
            "instrumentId": instrument_id,
            "fromDate": from_date,
            "toDate": to_date,
            "interval": interval
        }
        return self._make_request("GET", "v1/historical-data", params=params)
    
    def get_instrument_by_symbol(self, symbol, exchange_segment):
        """Get instrument details by symbol"""
        if f"{symbol}_{exchange_segment}" in self.instrument_cache:
            return self.instrument_cache[f"{symbol}_{exchange_segment}"]
            
        params = {
            "symbol": symbol,
            "exchangeSegment": exchange_segment
        }
        result = self._make_request("GET", "v2/instruments/search", params=params)
        
        # Cache the result
        if result and "data" in result and result["data"]:
            self.instrument_cache[f"{symbol}_{exchange_segment}"] = result["data"][0]
            return result["data"][0]
        return None
    
    def load_all_instruments(self):
        """Load and cache all instruments"""
        url = "https://images.dhan.co/api-data/api-scrip-master-detailed.csv"
        try:
            instruments_df = pd.read_csv(url)
            
            # Create a lookup dictionary for faster access
            for _, row in instruments_df.iterrows():
                key = f"{row['tradingsymbol']}_{row['exchange_segment']}"
                self.instrument_cache[key] = {
                    "tradingSymbol": row['tradingsymbol'],
                    "exchangeSegment": row['exchange_segment'],
                    "instrumentId": row['instrument_key'],
                    "tickSize": row['tick_size'],
                    "lotSize": row['lot_size']
                }
                
            logger.info(f"Loaded {len(instruments_df)} instruments into cache")
            return instruments_df
        except Exception as e:
            logger.error(f"Failed to load instruments: {e}", exc_info=True)
            return None
    
    # Order Management Methods
    def place_order(self, order_params):
        """Place a new order"""
        return self._make_request("POST", "v2/orders", data=order_params)
    
    def modify_order(self, order_id, order_params):
        """Modify an existing order"""
        return self._make_request("PUT", f"v2/orders/{order_id}", data=order_params)
    
    def cancel_order(self, order_id):
        """Cancel an order"""
        return self._make_request("DELETE", f"v2/orders/{order_id}")
    
    def get_order_status(self, order_id):
        """Get status of an order"""
        return self._make_request("GET", f"v2/orders/{order_id}")
    
    def get_order_history(self):
        """Get order history"""
        return self._make_request("GET", "v2/orders")
    
    def check_market_status(self):
        """Check if the market is currently open"""
        now = datetime.now()
        
        # Check if it's a weekday (0 = Monday, 6 = Sunday)
        if now.weekday() >= 5:
            return False
        
        # Check if current time is between 9:15 AM and 3:30 PM IST
        # Adjust the time check based on your local timezone if needed
        market_open = now.replace(hour=9, minute=15, second=0, microsecond=0)
        market_close = now.replace(hour=15, minute=30, second=0, microsecond=0)
        
        return market_open <= now <= market_close