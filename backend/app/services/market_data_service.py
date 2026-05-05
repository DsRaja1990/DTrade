"""
Market data service for handling real-time and historical market data
"""
import asyncio
import json
import websockets
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from ..core.config import get_settings
from ..core.redis_client import RedisClient
from ..core.websocket_manager import ConnectionManager
from ..models.market_data import Instrument, MarketQuote, HistoricalData, OptionChain
from .dhan_service import DhanHQService

settings = get_settings()

class MarketDataService:
    """Service for managing market data operations"""
    
    def __init__(self, redis_client: RedisClient):
        self.redis_client = redis_client
        self.websocket_manager = ConnectionManager()
        self.dhan_service = None
        self.subscriptions: Dict[str, List[Callable]] = {}
        self.running = False
        self.websocket_connection = None
        
    async def initialize(self, dhan_client_id: str, dhan_access_token: str):
        """Initialize the market data service"""
        self.dhan_service = DhanHQService(dhan_client_id, dhan_access_token)
        
    async def start_data_feed(self):
        """Start the real-time market data feed"""
        if not self.dhan_service:
            raise Exception("DhanService not initialized")
            
        self.running = True
        
        # Start WebSocket connection to DhanHQ
        asyncio.create_task(self._connect_dhan_websocket())
        
        # Start data processing tasks
        asyncio.create_task(self._process_market_data())
        asyncio.create_task(self._update_option_chains())
        
    async def stop_data_feed(self):
        """Stop the market data feed"""
        self.running = False
        
        if self.websocket_connection:
            await self.websocket_connection.close()
    
    async def subscribe_to_symbol(self, security_id: str, callback: Callable[[Dict], None]):
        """Subscribe to real-time data for a symbol"""
        if security_id not in self.subscriptions:
            self.subscriptions[security_id] = []
            
            # Subscribe to DhanHQ feed
            if self.dhan_service:
                await self.dhan_service.subscribe_to_feed([security_id])
        
        self.subscriptions[security_id].append(callback)
        
    async def unsubscribe_from_symbol(self, security_id: str, callback: Callable[[Dict], None]):
        """Unsubscribe from real-time data for a symbol"""
        if security_id in self.subscriptions:
            try:
                self.subscriptions[security_id].remove(callback)
                
                # If no more callbacks, unsubscribe from DhanHQ
                if not self.subscriptions[security_id]:
                    del self.subscriptions[security_id]
                    if self.dhan_service:
                        await self.dhan_service.unsubscribe_from_feed([security_id])
            except ValueError:
                pass
    
    async def get_live_quote(self, security_id: str) -> Optional[Dict[str, Any]]:
        """Get live quote for a security"""
        try:
            # First try to get from Redis cache
            cached_quote = await self.redis_client.get(f"quote:{security_id}")
            if cached_quote:
                return json.loads(cached_quote)
            
            # If not in cache, fetch from DhanHQ
            if self.dhan_service:
                quote_data = await self.dhan_service.get_market_quote(security_id)
                if quote_data.get("status") == "success":
                    data = quote_data["data"]
                    
                    # Cache the quote
                    await self.redis_client.setex(
                        f"quote:{security_id}",
                        30,  # Cache for 30 seconds
                        json.dumps(data)
                    )
                    
                    return data
            
            return None
            
        except Exception as e:
            print(f"Error getting live quote for {security_id}: {e}")
            return None
    
    async def get_historical_data(
        self,
        security_id: str,
        exchange_segment: str,
        instrument_type: str,
        from_date: str,
        to_date: str,
        timeframe: str = "1day"
    ) -> List[Dict[str, Any]]:
        """Get historical data for a security"""
        try:
            cache_key = f"historical:{security_id}:{timeframe}:{from_date}:{to_date}"
            
            # Try to get from cache first
            cached_data = await self.redis_client.get(cache_key)
            if cached_data:
                return json.loads(cached_data)
            
            # Fetch from DhanHQ
            if self.dhan_service:
                historical_data = await self.dhan_service.get_historical_data(
                    security_id=security_id,
                    exchange_segment=exchange_segment,
                    instrument_type=instrument_type,
                    from_date=from_date,
                    to_date=to_date
                )
                
                if historical_data.get("status") == "success":
                    data = historical_data["data"]
                    
                    # Cache for 1 hour
                    await self.redis_client.setex(
                        cache_key,
                        3600,
                        json.dumps(data)
                    )
                    
                    return data
            
            return []
            
        except Exception as e:
            print(f"Error getting historical data for {security_id}: {e}")
            return []
    
    async def get_option_chain(
        self,
        underlying_symbol: str,
        expiry_date: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get option chain for an underlying symbol"""
        try:
            cache_key = f"option_chain:{underlying_symbol}:{expiry_date or 'current'}"
            
            # Try cache first
            cached_data = await self.redis_client.get(cache_key)
            if cached_data:
                return json.loads(cached_data)
            
            # Fetch from DhanHQ
            if self.dhan_service:
                option_data = await self.dhan_service.get_option_chain(
                    underlying_symbol=underlying_symbol,
                    expiry_date=expiry_date
                )
                
                if option_data.get("status") == "success":
                    data = option_data["data"]
                    
                    # Cache for 1 minute
                    await self.redis_client.setex(
                        cache_key,
                        60,
                        json.dumps(data)
                    )
                    
                    return data
            
            return []
            
        except Exception as e:
            print(f"Error getting option chain for {underlying_symbol}: {e}")
            return []
    
    async def search_instruments(
        self,
        query: str,
        exchange: Optional[str] = None,
        instrument_type: Optional[str] = None,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """Search for instruments"""
        try:
            cache_key = f"search:{query}:{exchange or 'all'}:{instrument_type or 'all'}:{limit}"
            
            # Try cache first
            cached_results = await self.redis_client.get(cache_key)
            if cached_results:
                return json.loads(cached_results)
            
            # In real implementation, this would search the instruments database
            # For now, return mock data
            results = [
                {
                    "security_id": "11536",
                    "trading_symbol": "TCS",
                    "company_name": "Tata Consultancy Services Ltd",
                    "exchange_segment": "NSE_EQ",
                    "instrument_type": "EQUITY"
                },
                {
                    "security_id": "1333",
                    "trading_symbol": "INFY",
                    "company_name": "Infosys Ltd",
                    "exchange_segment": "NSE_EQ",
                    "instrument_type": "EQUITY"
                }
            ]
            
            # Cache for 10 minutes
            await self.redis_client.setex(
                cache_key,
                600,
                json.dumps(results)
            )
            
            return results
            
        except Exception as e:
            print(f"Error searching instruments: {e}")
            return []
    
    async def get_market_status(self) -> Dict[str, Any]:
        """Get current market status"""
        try:
            # Check cache first
            cached_status = await self.redis_client.get("market_status")
            if cached_status:
                return json.loads(cached_status)
            
            # Calculate market status
            now = datetime.now()
            market_open = now.replace(hour=9, minute=15, second=0, microsecond=0)
            market_close = now.replace(hour=15, minute=30, second=0, microsecond=0)
            
            is_weekday = now.weekday() < 5  # Monday=0, Friday=4
            is_market_hours = market_open <= now <= market_close
            
            if is_weekday and is_market_hours:
                status = "OPEN"
            else:
                status = "CLOSED"
            
            market_status = {
                "status": status,
                "current_time": now.isoformat(),
                "market_open": market_open.isoformat(),
                "market_close": market_close.isoformat(),
                "is_weekend": not is_weekday
            }
            
            # Cache for 1 minute
            await self.redis_client.setex(
                "market_status",
                60,
                json.dumps(market_status)
            )
            
            return market_status
            
        except Exception as e:
            print(f"Error getting market status: {e}")
            return {"status": "UNKNOWN", "error": str(e)}
    
    async def calculate_technical_indicators(
        self,
        security_id: str,
        period: int = 20
    ) -> Dict[str, float]:
        """Calculate technical indicators for a security"""
        try:
            # Get historical data
            end_date = datetime.now().strftime("%Y-%m-%d")
            start_date = (datetime.now() - timedelta(days=period * 2)).strftime("%Y-%m-%d")
            
            historical_data = await self.get_historical_data(
                security_id=security_id,
                exchange_segment="NSE_EQ",
                instrument_type="EQUITY",
                from_date=start_date,
                to_date=end_date
            )
            
            if not historical_data or len(historical_data) < period:
                return {}
            
            # Extract closing prices
            closes = [float(candle["close"]) for candle in historical_data[-period:]]
            
            # Calculate indicators
            indicators = {}
            
            # Simple Moving Average
            indicators["sma"] = sum(closes) / len(closes)
            
            # RSI (simplified calculation)
            if len(closes) >= 14:
                gains = []
                losses = []
                for i in range(1, len(closes)):
                    change = closes[i] - closes[i-1]
                    if change > 0:
                        gains.append(change)
                        losses.append(0)
                    else:
                        gains.append(0)
                        losses.append(abs(change))
                
                avg_gain = sum(gains[-14:]) / 14
                avg_loss = sum(losses[-14:]) / 14
                
                if avg_loss > 0:
                    rs = avg_gain / avg_loss
                    indicators["rsi"] = 100 - (100 / (1 + rs))
                else:
                    indicators["rsi"] = 100
            
            # Bollinger Bands
            sma = indicators["sma"]
            variance = sum((price - sma) ** 2 for price in closes) / len(closes)
            std_dev = variance ** 0.5
            
            indicators["bollinger_upper"] = sma + (2 * std_dev)
            indicators["bollinger_lower"] = sma - (2 * std_dev)
            
            return indicators
            
        except Exception as e:
            print(f"Error calculating technical indicators: {e}")
            return {}
    
    async def _connect_dhan_websocket(self):
        """Connect to DhanHQ WebSocket feed"""
        try:
            # This would connect to DhanHQ's WebSocket endpoint
            # For now, we'll simulate with a mock connection
            print("Connecting to DhanHQ WebSocket...")
            
            while self.running:
                try:
                    # Mock WebSocket connection
                    await asyncio.sleep(1)
                    
                    # Simulate receiving market data
                    await self._simulate_market_data()
                    
                except Exception as e:
                    print(f"WebSocket error: {e}")
                    await asyncio.sleep(5)  # Retry after 5 seconds
                    
        except Exception as e:
            print(f"Failed to connect to WebSocket: {e}")
    
    async def _simulate_market_data(self):
        """Simulate market data updates"""
        import random
        
        # Simulate data for subscribed symbols
        for security_id in self.subscriptions.keys():
            mock_data = {
                "security_id": security_id,
                "last_price": round(random.uniform(100, 3000), 2),
                "change": round(random.uniform(-50, 50), 2),
                "change_percent": round(random.uniform(-5, 5), 2),
                "volume": random.randint(1000, 100000),
                "timestamp": datetime.now().isoformat()
            }
            
            # Notify subscribers
            await self._notify_subscribers(security_id, mock_data)
    
    async def _notify_subscribers(self, security_id: str, data: Dict[str, Any]):
        """Notify all subscribers of market data updates"""
        if security_id in self.subscriptions:
            for callback in self.subscriptions[security_id]:
                try:
                    await callback(data)
                except Exception as e:
                    print(f"Error in callback: {e}")
        
        # Cache the latest data
        await self.redis_client.setex(
            f"quote:{security_id}",
            30,
            json.dumps(data)
        )
        
        # Broadcast via WebSocket
        await self.websocket_manager.broadcast_market_data(security_id, {
            "type": "market_data",
            "data": data
        })
    
    async def _process_market_data(self):
        """Background task to process market data"""
        while self.running:
            try:
                # Process any queued market data updates
                await asyncio.sleep(0.1)  # Small delay to prevent busy waiting
                
            except Exception as e:
                print(f"Error processing market data: {e}")
                await asyncio.sleep(1)
    
    async def _update_option_chains(self):
        """Background task to update option chains"""
        while self.running:
            try:
                # Update option chains for major indices
                major_symbols = ["NIFTY", "BANKNIFTY", "FINNIFTY"]
                
                for symbol in major_symbols:
                    option_chain = await self.get_option_chain(symbol)
                    # Option chain is automatically cached in get_option_chain
                
                # Update every 30 seconds
                await asyncio.sleep(30)
                
            except Exception as e:
                print(f"Error updating option chains: {e}")
                await asyncio.sleep(60)  # Wait longer on error
