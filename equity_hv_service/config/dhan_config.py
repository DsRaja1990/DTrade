"""
Centralized Dhan API Configuration and Real Data Integration
"""
import os
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
import asyncio
import aiohttp
from dataclasses import dataclass

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class DhanCredentials:
    """Dhan API credentials"""
    access_token: str
    client_id: str
    base_url: str = "https://api.dhan.co"
    
class DhanAPIManager:
    """
    Centralized Dhan API Manager for Real Data Integration
    """
    
    def __init__(self):
        self.credentials = None
        self.session = None
        self.base_headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
        self.market_data_cache = {}
        self.option_chains_cache = {}
        self.vix_data = None
        self.last_vix_update = None
        
    def set_credentials(self, access_token: str, client_id: str = "1101317572"):
        """Set Dhan API credentials"""
        self.credentials = DhanCredentials(
            access_token=access_token,
            client_id=client_id
        )
        self.base_headers['Authorization'] = f'Bearer {access_token}'
        logger.info("✅ Dhan API credentials configured")
    
    def update_access_token(self, new_token: str):
        """Update access token centrally"""
        if self.credentials:
            self.credentials.access_token = new_token
            self.base_headers['Authorization'] = f'Bearer {new_token}'
            logger.info("✅ Dhan access token updated")
        else:
            logger.error("❌ No credentials configured")
    
    async def initialize(self):
        """Initialize HTTP session and validate credentials"""
        try:
            self.session = aiohttp.ClientSession(headers=self.base_headers)
            
            # Validate credentials by fetching user profile
            success = await self.validate_credentials()
            if success:
                logger.info("🚀 Dhan API Manager initialized successfully")
                return True
            else:
                logger.error("❌ Failed to validate Dhan credentials")
                return False
                
        except Exception as e:
            logger.error(f"❌ Failed to initialize Dhan API Manager: {e}")
            return False
    
    async def validate_credentials(self) -> bool:
        """Validate Dhan API credentials"""
        try:
            url = f"{self.credentials.base_url}/profile"
            async with self.session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    logger.info(f"✅ Dhan API validated for client: {data.get('clientId', 'Unknown')}")
                    return True
                else:
                    logger.error(f"❌ Credential validation failed: {response.status}")
                    return False
                    
        except Exception as e:
            logger.error(f"❌ Error validating credentials: {e}")
            return False
    
    async def get_market_data(self, symbol: str, exchange: str = "NSE") -> Optional[Dict[str, Any]]:
        """Get real-time market data for a symbol"""
        try:
            # Check cache first (valid for 5 seconds)
            cache_key = f"{exchange}:{symbol}"
            if cache_key in self.market_data_cache:
                cached_data, timestamp = self.market_data_cache[cache_key]
                if (datetime.now() - timestamp).total_seconds() < 5:
                    return cached_data
            
            url = f"{self.credentials.base_url}/marketdata/ltp"
            payload = {
                "exchangeSegment": exchange,
                "securityId": symbol
            }
            
            async with self.session.post(url, json=payload) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    # Cache the data
                    self.market_data_cache[cache_key] = (data, datetime.now())
                    
                    return {
                        'symbol': symbol,
                        'ltp': data.get('data', {}).get('LTP', 0),
                        'open': data.get('data', {}).get('open', 0),
                        'high': data.get('data', {}).get('high', 0),
                        'low': data.get('data', {}).get('low', 0),
                        'close': data.get('data', {}).get('close', 0),
                        'volume': data.get('data', {}).get('volume', 0),
                        'timestamp': datetime.now()
                    }
                else:
                    logger.error(f"❌ Failed to get market data for {symbol}: {response.status}")
                    return None
                    
        except Exception as e:
            logger.error(f"❌ Error getting market data for {symbol}: {e}")
            return None
    
    async def get_vix_data(self) -> Optional[float]:
        """Get current VIX data"""
        try:
            # Update VIX data every 60 seconds
            if (self.last_vix_update is None or 
                (datetime.now() - self.last_vix_update).total_seconds() > 60):
                
                # Get VIX data from NSE
                vix_data = await self.get_market_data("INDIA VIX", "NSE")
                if vix_data:
                    self.vix_data = vix_data.get('ltp', 25.0)  # Default to 25 if unavailable
                    self.last_vix_update = datetime.now()
                    logger.info(f"📊 VIX updated: {self.vix_data:.2f}")
            
            return self.vix_data
            
        except Exception as e:
            logger.error(f"❌ Error getting VIX data: {e}")
            return 25.0  # Conservative default
    
    async def get_option_chain(self, underlying: str, expiry: str = None) -> Optional[List[Dict[str, Any]]]:
        """Get option chain data for an underlying"""
        try:
            cache_key = f"options:{underlying}:{expiry}"
            if cache_key in self.option_chains_cache:
                cached_data, timestamp = self.option_chains_cache[cache_key]
                if (datetime.now() - timestamp).total_seconds() < 30:  # Cache for 30 seconds
                    return cached_data
            
            url = f"{self.credentials.base_url}/optionchain"
            payload = {
                "underlyingSymbol": underlying,
                "exchangeSegment": "NSE"
            }
            
            if expiry:
                payload["expiryCode"] = expiry
            
            async with self.session.post(url, json=payload) as response:
                if response.status == 200:
                    data = await response.json()
                    option_chain = data.get('data', [])
                    
                    # Cache the data
                    self.option_chains_cache[cache_key] = (option_chain, datetime.now())
                    
                    return option_chain
                else:
                    logger.error(f"❌ Failed to get option chain for {underlying}: {response.status}")
                    return None
                    
        except Exception as e:
            logger.error(f"❌ Error getting option chain for {underlying}: {e}")
            return None
    
    async def get_historical_data(self, symbol: str, timeframe: str = "1D", 
                                count: int = 100) -> Optional[List[Dict[str, Any]]]:
        """Get historical data for technical analysis"""
        try:
            url = f"{self.credentials.base_url}/charts/historical"
            payload = {
                "symbol": symbol,
                "exchangeSegment": "NSE",
                "instrument": "EQUITY",
                "expiryCode": 0,
                "fromDate": (datetime.now() - timedelta(days=count)).strftime("%Y-%m-%d"),
                "toDate": datetime.now().strftime("%Y-%m-%d")
            }
            
            async with self.session.post(url, json=payload) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get('data', [])
                else:
                    logger.error(f"❌ Failed to get historical data for {symbol}: {response.status}")
                    return None
                    
        except Exception as e:
            logger.error(f"❌ Error getting historical data for {symbol}: {e}")
            return None
    
    async def place_order(self, order_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Place order through Dhan API"""
        try:
            url = f"{self.credentials.base_url}/orders"
            
            async with self.session.post(url, json=order_data) as response:
                if response.status == 200:
                    data = await response.json()
                    logger.info(f"✅ Order placed successfully: {data.get('orderId')}")
                    return data
                else:
                    error_data = await response.json()
                    logger.error(f"❌ Failed to place order: {response.status} - {error_data}")
                    return None
                    
        except Exception as e:
            logger.error(f"❌ Error placing order: {e}")
            return None
    
    async def get_positions(self) -> Optional[List[Dict[str, Any]]]:
        """Get current positions"""
        try:
            url = f"{self.credentials.base_url}/positions"
            
            async with self.session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get('data', [])
                else:
                    logger.error(f"❌ Failed to get positions: {response.status}")
                    return None
                    
        except Exception as e:
            logger.error(f"❌ Error getting positions: {e}")
            return None
    
    async def get_funds(self) -> Optional[Dict[str, Any]]:
        """Get account funds information"""
        try:
            url = f"{self.credentials.base_url}/fundlimit"
            
            async with self.session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get('data', {})
                else:
                    logger.error(f"❌ Failed to get funds: {response.status}")
                    return None
                    
        except Exception as e:
            logger.error(f"❌ Error getting funds: {e}")
            return None
    
    async def get_orders(self) -> Optional[List[Dict[str, Any]]]:
        """Get order book"""
        try:
            url = f"{self.credentials.base_url}/orders"
            
            async with self.session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get('data', [])
                else:
                    logger.error(f"❌ Failed to get orders: {response.status}")
                    return None
                    
        except Exception as e:
            logger.error(f"❌ Error getting orders: {e}")
            return None
    
    async def close(self):
        """Close the HTTP session"""
        if self.session:
            await self.session.close()

# Global instance
dhan_api = DhanAPIManager()

def initialize_dhan_api(access_token: str, client_id: str = "1101317572"):
    """Initialize Dhan API with credentials"""
    dhan_api.set_credentials(access_token, client_id)
    return dhan_api

def get_dhan_api() -> DhanAPIManager:
    """Get the global Dhan API instance"""
    return dhan_api

# API endpoint for updating token
async def update_dhan_token(new_token: str):
    """API endpoint to update Dhan access token"""
    dhan_api.update_access_token(new_token)
    return {"status": "success", "message": "Token updated successfully"}
