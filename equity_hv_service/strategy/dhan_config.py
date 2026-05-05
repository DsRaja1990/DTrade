"""
Dhan API Configuration and Real Market Data Integration
Production-ready Dhan API manager with comprehensive market data capabilities
Implements real-time data fetching, VIX monitoring, and order management
"""

import asyncio
import aiohttp
import json
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Union
import logging

class DhanAPIManager:
    """
    Centralized Dhan API Manager for Real Market Data Integration
    Provides real-time data, VIX monitoring, option chains, and order management
    """
    
    def __init__(self, access_token: str = None):
        """Initialize Dhan API Manager with real credentials"""
        # Real Dhan API Access Token (Updated: 2025-12-13)
        self.access_token = access_token or "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzUxMiJ9.eyJpc3MiOiJkaGFuIiwicGFydG5lcklkIjoiIiwiZXhwIjoxNzY2MjEyMzAxLCJpYXQiOjE3NjYxMjU5MDEsInRva2VuQ29uc3VtZXJUeXBlIjoiU0VMRiIsIndlYmhvb2tVcmwiOiIiLCJkaGFuQ2xpZW50SWQiOiIxMTAxMzE3NTcyIn0.oTZr9N5p6wj8givgxWSwctGF8SnYVJtXY2aBw7lOwJccnBQmyQhAGAo_07L3MZspj7IedKZe5e0IytO6cmPxJQ"
        
        # Dhan API Endpoints
        self.base_url = "https://api.dhan.co"
        self.headers = {
            "access-token": self.access_token,
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        
        # Market data cache
        self.market_data_cache = {}
        self.vix_cache = {}
        self.option_chains_cache = {}
        
        # Initialize session
        self.session = None
        
        # Logging
        self.logger = logging.getLogger(__name__)
    
    def update_access_token(self, new_token: str):
        """Update access token and reset session for hot-reload"""
        self.access_token = new_token
        self.headers["access-token"] = new_token
        # Close existing session so new one is created with updated token
        if self.session:
            import asyncio
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    asyncio.create_task(self.close())
                else:
                    loop.run_until_complete(self.close())
            except:
                pass
            self.session = None
        self.logger.info("Access token updated - session will reinitialize on next request")
        
    async def initialize(self):
        """Initialize async session"""
        if not self.session:
            self.session = aiohttp.ClientSession(headers=self.headers)
            
    async def close(self):
        """Close async session"""
        if self.session:
            await self.session.close()
            self.session = None
            
    async def get_market_data(self, symbols: List[str]) -> Dict[str, Any]:
        """
        Get real-time market data for symbols
        """
        try:
            await self.initialize()
            
            # Prepare request for market data
            endpoint = f"{self.base_url}/v2/marketfeed/ltp"
            
            market_data = {}
            
            for symbol in symbols:
                try:
                    # Format symbol for Dhan API
                    security_id = self._get_security_id(symbol)
                    
                    payload = {
                        "NSE_EQ": [security_id]  # NSE Equity segment
                    }
                    
                    async with self.session.post(endpoint, json=payload) as response:
                        if response.status == 200:
                            data = await response.json()
                            if data.get('status') == 'success':
                                ltp_data = data.get('data', {}).get('NSE_EQ', {})
                                if str(security_id) in ltp_data:
                                    market_data[symbol] = {
                                        'ltp': ltp_data[str(security_id)].get('LTP', 0),
                                        'volume': ltp_data[str(security_id)].get('volume', 0),
                                        'change': ltp_data[str(security_id)].get('change', 0),
                                        'change_percent': ltp_data[str(security_id)].get('change_percent', 0),
                                        'timestamp': datetime.now()
                                    }
                        
                except Exception as e:
                    self.logger.error(f"Error fetching data for {symbol}: {e}")
                    market_data[symbol] = {
                        'ltp': 0, 'volume': 0, 'change': 0, 'change_percent': 0,
                        'timestamp': datetime.now()
                    }
                    
            # Cache the data
            self.market_data_cache.update(market_data)
            return market_data
            
        except Exception as e:
            self.logger.error(f"Market data fetch error: {e}")
            return {}
            
    async def get_vix_data(self) -> Dict[str, float]:
        """
        Get real-time VIX data from Dhan API
        """
        try:
            await self.initialize()
            
            # VIX symbol on NSE
            vix_security_id = "1333"  # India VIX security ID
            
            endpoint = f"{self.base_url}/v2/marketfeed/ltp"
            payload = {
                "NSE_INDEX": [vix_security_id]
            }
            
            async with self.session.post(endpoint, json=payload) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get('status') == 'success':
                        vix_data = data.get('data', {}).get('NSE_INDEX', {})
                        if vix_security_id in vix_data:
                            vix_value = vix_data[vix_security_id].get('LTP', 0)
                            
                            vix_info = {
                                'vix': vix_value,
                                'vix_change': vix_data[vix_security_id].get('change', 0),
                                'vix_change_percent': vix_data[vix_security_id].get('change_percent', 0),
                                'timestamp': datetime.now(),
                                'high_volatility': vix_value > 35.0,  # Enhanced threshold
                                'extreme_volatility': vix_value > 45.0
                            }
                            
                            # Cache VIX data
                            self.vix_cache = vix_info
                            return vix_info
                            
        except Exception as e:
            self.logger.error(f"VIX data fetch error: {e}")
            
        # Return default if error
        return {
            'vix': 15.0, 'vix_change': 0, 'vix_change_percent': 0,
            'timestamp': datetime.now(), 'high_volatility': False, 'extreme_volatility': False
        }
        
    async def get_option_chain(self, underlying: str, expiry_date: str = None) -> Dict[str, Any]:
        """
        Get option chain data for underlying symbol
        """
        try:
            await self.initialize()
            
            # Get security ID for underlying
            security_id = self._get_security_id(underlying)
            
            # If no expiry specified, get nearest expiry
            if not expiry_date:
                expiry_date = self._get_nearest_expiry()
                
            endpoint = f"{self.base_url}/v2/optionchain/{security_id}"
            
            async with self.session.get(endpoint) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get('status') == 'success':
                        option_chain = data.get('data', {})
                        
                        # Process and cache option chain
                        processed_chain = self._process_option_chain(option_chain, underlying)
                        self.option_chains_cache[underlying] = processed_chain
                        
                        return processed_chain
                        
        except Exception as e:
            self.logger.error(f"Option chain fetch error for {underlying}: {e}")
            
        return {}
        
    async def get_historical_data(self, symbol: str, timeframe: str = "1D", days: int = 30) -> pd.DataFrame:
        """
        Get historical data for symbol
        """
        try:
            await self.initialize()
            
            security_id = self._get_security_id(symbol)
            
            # Calculate date range
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            
            endpoint = f"{self.base_url}/v2/charts/historical"
            payload = {
                "symbol": security_id,
                "exchangeSegment": "NSE_EQ",
                "instrument": "EQUITY",
                "expiryCode": 0,
                "fromDate": start_date.strftime("%Y-%m-%d"),
                "toDate": end_date.strftime("%Y-%m-%d")
            }
            
            async with self.session.post(endpoint, json=payload) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get('status') == 'success':
                        historical_data = data.get('data', [])
                        
                        # Convert to DataFrame
                        if historical_data:
                            df = pd.DataFrame(historical_data)
                            df['timestamp'] = pd.to_datetime(df['timestamp'])
                            df.set_index('timestamp', inplace=True)
                            return df
                            
        except Exception as e:
            self.logger.error(f"Historical data fetch error for {symbol}: {e}")
            
        return pd.DataFrame()
        
    async def place_order(self, order_details: Dict[str, Any]) -> Dict[str, Any]:
        """
        Place order through Dhan API
        """
        try:
            await self.initialize()
            
            endpoint = f"{self.base_url}/v2/orders"
            
            # Prepare order payload
            order_payload = {
                "dhanClientId": "1101317572",  # Real client ID
                "correlationId": order_details.get('correlation_id', f"ORDER_{datetime.now().strftime('%Y%m%d_%H%M%S')}"),
                "transactionType": order_details.get('transaction_type', 'BUY'),
                "exchangeSegment": order_details.get('exchange_segment', 'NSE_EQ'),
                "productType": order_details.get('product_type', 'INTRADAY'),
                "orderType": order_details.get('order_type', 'MARKET'),
                "validity": order_details.get('validity', 'DAY'),
                "securityId": str(self._get_security_id(order_details.get('symbol', ''))),
                "quantity": order_details.get('quantity', 1),
                "disclosedQuantity": order_details.get('disclosed_quantity', 0),
                "price": order_details.get('price', 0),
                "triggerPrice": order_details.get('trigger_price', 0),
                "afterMarketOrder": order_details.get('after_market_order', False),
                "boProfitValue": order_details.get('bo_profit_value', 0),
                "boStopLossValue": order_details.get('bo_stop_loss_value', 0)
            }
            
            async with self.session.post(endpoint, json=order_payload) as response:
                response_data = await response.json()
                
                if response.status == 200 and response_data.get('status') == 'success':
                    return {
                        'success': True,
                        'order_id': response_data.get('data', {}).get('orderId'),
                        'message': 'Order placed successfully',
                        'data': response_data.get('data', {})
                    }
                else:
                    return {
                        'success': False,
                        'error': response_data.get('remarks', 'Order placement failed'),
                        'data': response_data
                    }
                    
        except Exception as e:
            self.logger.error(f"Order placement error: {e}")
            return {
                'success': False,
                'error': str(e),
                'data': {}
            }
            
    async def get_positions(self) -> List[Dict[str, Any]]:
        """
        Get current positions
        """
        try:
            await self.initialize()
            
            endpoint = f"{self.base_url}/v2/positions"
            
            async with self.session.get(endpoint) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get('status') == 'success':
                        return data.get('data', [])
                        
        except Exception as e:
            self.logger.error(f"Positions fetch error: {e}")
            
        return []
        
    async def get_holdings(self) -> List[Dict[str, Any]]:
        """
        Get current holdings
        """
        try:
            await self.initialize()
            
            endpoint = f"{self.base_url}/v2/holdings"
            
            async with self.session.get(endpoint) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get('status') == 'success':
                        return data.get('data', [])
                        
        except Exception as e:
            self.logger.error(f"Holdings fetch error: {e}")
            
        return []
        
    async def get_funds(self) -> Dict[str, float]:
        """
        Get account fund information
        """
        try:
            await self.initialize()
            
            endpoint = f"{self.base_url}/v2/fundlimit"
            
            async with self.session.get(endpoint) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get('status') == 'success':
                        fund_data = data.get('data', {})
                        return {
                            'available_balance': fund_data.get('availabelBalance', 0),
                            'used_balance': fund_data.get('blockedBalance', 0),
                            'total_balance': fund_data.get('totalBalance', 0),
                            'margin_used': fund_data.get('marginUsed', 0),
                            'margin_available': fund_data.get('marginAvailable', 0)
                        }
                        
        except Exception as e:
            self.logger.error(f"Funds fetch error: {e}")
            
        return {'available_balance': 0, 'used_balance': 0, 'total_balance': 0, 'margin_used': 0, 'margin_available': 0}
        
    def _get_security_id(self, symbol: str) -> str:
        """
        Convert symbol to Dhan security ID
        Common NSE symbols to security IDs
        """
        symbol_map = {
            'NIFTY': '26000',
            'BANKNIFTY': '26009',
            'FINNIFTY': '26037',
            'RELIANCE': '2885',
            'TCS': '3456',
            'INFY': '1594',
            'HDFCBANK': '1333',
            'ICICIBANK': '4963',
            'SBIN': '3045',
            'BHARTIARTL': '10604',
            'ITC': '424',
            'HINDUNILVR': '1394',
            'LT': '2939',
            'ASIANPAINT': '236',
            'MARUTI': '10999'
        }
        
        return symbol_map.get(symbol.upper(), '26000')  # Default to NIFTY
        
    def _get_nearest_expiry(self) -> str:
        """
        Get nearest Thursday expiry for options
        """
        today = datetime.now()
        days_ahead = 3 - today.weekday()  # Thursday is 3
        
        if days_ahead <= 0:  # Today is Thursday or past Thursday
            days_ahead += 7
            
        nearest_thursday = today + timedelta(days=days_ahead)
        return nearest_thursday.strftime("%Y-%m-%d")
        
    def _process_option_chain(self, raw_chain: Dict, underlying: str) -> Dict[str, Any]:
        """
        Process raw option chain data into structured format
        """
        processed = {
            'underlying': underlying,
            'spot_price': raw_chain.get('spotPrice', 0),
            'calls': [],
            'puts': [],
            'timestamp': datetime.now()
        }
        
        # Process option data
        for option in raw_chain.get('options', []):
            option_data = {
                'strike': option.get('strikePrice', 0),
                'ltp': option.get('LTP', 0),
                'bid': option.get('bidPrice', 0),
                'ask': option.get('askPrice', 0),
                'volume': option.get('volume', 0),
                'oi': option.get('openInterest', 0),
                'iv': option.get('impliedVolatility', 0),
                'delta': option.get('delta', 0),
                'gamma': option.get('gamma', 0),
                'theta': option.get('theta', 0),
                'vega': option.get('vega', 0)
            }
            
            if option.get('optionType') == 'CALL':
                processed['calls'].append(option_data)
            elif option.get('optionType') == 'PUT':
                processed['puts'].append(option_data)
                
        return processed

# Global instance for easy access
dhan_api = DhanAPIManager()

# Async context manager for proper session handling
class DhanAPIContext:
    def __init__(self, access_token: str = None):
        self.api = DhanAPIManager(access_token)
        
    async def __aenter__(self):
        await self.api.initialize()
        return self.api
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.api.close()
