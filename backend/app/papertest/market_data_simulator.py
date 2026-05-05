"""
Market Data Simulator for Paper Trading

This module simulates real-time market data for paper trading environments.
It generates realistic price movements for indices and options.
"""

import asyncio
import logging
import random
import math
from datetime import datetime, timezone, time
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
import json

logger = logging.getLogger(__name__)

@dataclass
class MarketDataPoint:
    """Market data point structure"""
    instrument: str
    ltp: float  # Last traded price
    volume: int
    open: float
    high: float
    low: float
    close: float
    timestamp: datetime
    bid: float
    ask: float
    bid_qty: int
    ask_qty: int

class MarketDataSimulator:
    """
    Market Data Simulator for Paper Trading
    
    Generates realistic market data with:
    - Intraday price movements
    - Volatility clustering
    - Market microstructure effects
    - Options pricing simulation
    """
    
    def __init__(self):
        self.is_running = False
        self.subscribers: List[callable] = []
        self.current_prices: Dict[str, MarketDataPoint] = {}
        
        # Market parameters
        self.market_open_time = time(9, 15)  # 9:15 AM
        self.market_close_time = time(15, 30)  # 3:30 PM
        
        # Base prices for indices
        self.base_prices = {
            "NIFTY": 19500.0,
            "BANKNIFTY": 45000.0,
            "SENSEX": 65000.0
        }
        
        # Initialize current prices
        self._initialize_prices()
        
        # Market state
        self.market_trend = "sideways"  # bullish, bearish, sideways
        self.volatility_regime = "normal"  # low, normal, high
        
        logger.info("Market data simulator initialized")
    
    def _initialize_prices(self):
        """Initialize current prices for all instruments"""
        for instrument, base_price in self.base_prices.items():
            # Add some random variation to base price
            current_price = base_price * (1 + random.uniform(-0.02, 0.02))
            
            self.current_prices[instrument] = MarketDataPoint(
                instrument=instrument,
                ltp=current_price,
                volume=0,
                open=current_price,
                high=current_price,
                low=current_price,
                close=current_price,
                timestamp=datetime.now(timezone.utc),
                bid=current_price * 0.9995,
                ask=current_price * 1.0005,
                bid_qty=random.randint(50, 500),
                ask_qty=random.randint(50, 500)
            )
    
    def subscribe(self, callback: callable):
        """Subscribe to market data updates"""
        if callback not in self.subscribers:
            self.subscribers.append(callback)
            logger.info(f"New subscriber added. Total subscribers: {len(self.subscribers)}")
    
    def unsubscribe(self, callback: callable):
        """Unsubscribe from market data updates"""
        if callback in self.subscribers:
            self.subscribers.remove(callback)
            logger.info(f"Subscriber removed. Total subscribers: {len(self.subscribers)}")
    
    async def start(self):
        """Start the market data simulation"""
        if self.is_running:
            logger.warning("Market data simulator already running")
            return
        
        self.is_running = True
        logger.info("Starting market data simulation")
        
        try:
            while self.is_running:
                if self._is_market_hours():
                    await self._generate_market_data()
                    await self._notify_subscribers()
                
                # Update every second during market hours, every 10 seconds otherwise
                sleep_duration = 1 if self._is_market_hours() else 10
                await asyncio.sleep(sleep_duration)
        
        except Exception as e:
            logger.error(f"Error in market data simulation: {e}")
        finally:
            self.is_running = False
            logger.info("Market data simulation stopped")
    
    async def stop(self):
        """Stop the market data simulation"""
        self.is_running = False
        logger.info("Stopping market data simulation")
    
    def _is_market_hours(self) -> bool:
        """Check if market is currently open"""
        now = datetime.now().time()
        return self.market_open_time <= now <= self.market_close_time
    
    async def _generate_market_data(self):
        """Generate new market data points"""
        try:
            for instrument in self.base_prices.keys():
                await self._update_instrument_price(instrument)
        
        except Exception as e:
            logger.error(f"Error generating market data: {e}")
    
    async def _update_instrument_price(self, instrument: str):
        """Update price for a specific instrument"""
        try:
            current_data = self.current_prices[instrument]
            
            # Generate price movement
            new_price = self._generate_price_movement(current_data.ltp, instrument)
            
            # Update data point
            updated_data = MarketDataPoint(
                instrument=instrument,
                ltp=new_price,
                volume=current_data.volume + random.randint(1, 100),
                open=current_data.open,
                high=max(current_data.high, new_price),
                low=min(current_data.low, new_price),
                close=new_price,
                timestamp=datetime.now(timezone.utc),
                bid=new_price * (1 - random.uniform(0.0001, 0.0005)),
                ask=new_price * (1 + random.uniform(0.0001, 0.0005)),
                bid_qty=random.randint(50, 500),
                ask_qty=random.randint(50, 500)
            )
            
            self.current_prices[instrument] = updated_data
        
        except Exception as e:
            logger.error(f"Error updating price for {instrument}: {e}")
    
    def _generate_price_movement(self, current_price: float, instrument: str) -> float:
        """Generate realistic price movement"""
        try:
            # Base volatility for different instruments
            base_volatilities = {
                "NIFTY": 0.0001,      # 0.01% per tick
                "BANKNIFTY": 0.00015,  # 0.015% per tick
                "SENSEX": 0.00008     # 0.008% per tick
            }
            
            base_vol = base_volatilities.get(instrument, 0.0001)
            
            # Adjust volatility based on regime
            vol_multipliers = {
                "low": 0.5,
                "normal": 1.0,
                "high": 2.0
            }
            
            volatility = base_vol * vol_multipliers.get(self.volatility_regime, 1.0)
            
            # Generate random walk with trend bias
            trend_bias = self._get_trend_bias()
            random_component = random.gauss(0, 1) * volatility
            
            # Add some mean reversion
            distance_from_base = (current_price - self.base_prices[instrument]) / self.base_prices[instrument]
            mean_reversion = -distance_from_base * 0.0001
            
            # Calculate price change
            price_change = trend_bias + random_component + mean_reversion
            
            # Apply price change
            new_price = current_price * (1 + price_change)
            
            # Ensure price doesn't go negative or too extreme
            min_price = self.base_prices[instrument] * 0.95
            max_price = self.base_prices[instrument] * 1.05
            
            return max(min_price, min(max_price, new_price))
        
        except Exception as e:
            logger.error(f"Error generating price movement: {e}")
            return current_price
    
    def _get_trend_bias(self) -> float:
        """Get trend bias based on current market trend"""
        trend_biases = {
            "bullish": 0.00005,   # Slight upward bias
            "bearish": -0.00005,  # Slight downward bias
            "sideways": 0.0       # No bias
        }
        
        return trend_biases.get(self.market_trend, 0.0)
    
    async def _notify_subscribers(self):
        """Notify all subscribers with new market data"""
        try:
            if not self.subscribers:
                return
            
            # Prepare market data dictionary
            market_data = {}
            for instrument, data in self.current_prices.items():
                market_data[instrument] = {
                    "ltp": data.ltp,
                    "volume": data.volume,
                    "open": data.open,
                    "high": data.high,
                    "low": data.low,
                    "close": data.close,
                    "timestamp": data.timestamp.isoformat(),
                    "bid": data.bid,
                    "ask": data.ask,
                    "bid_qty": data.bid_qty,
                    "ask_qty": data.ask_qty
                }
            
            # Notify all subscribers
            for callback in self.subscribers[:]:  # Create a copy to avoid modification during iteration
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(market_data)
                    else:
                        callback(market_data)
                except Exception as e:
                    logger.error(f"Error notifying subscriber: {e}")
                    # Remove problematic subscriber
                    if callback in self.subscribers:
                        self.subscribers.remove(callback)
        
        except Exception as e:
            logger.error(f"Error notifying subscribers: {e}")
    
    def get_current_data(self, instrument: str = None) -> Dict[str, Any]:
        """Get current market data"""
        if instrument:
            if instrument in self.current_prices:
                data = self.current_prices[instrument]
                return {
                    "instrument": data.instrument,
                    "ltp": data.ltp,
                    "volume": data.volume,
                    "open": data.open,
                    "high": data.high,
                    "low": data.low,
                    "close": data.close,
                    "timestamp": data.timestamp.isoformat(),
                    "bid": data.bid,
                    "ask": data.ask,
                    "bid_qty": data.bid_qty,
                    "ask_qty": data.ask_qty
                }
            return {}
        else:
            # Return all instruments
            result = {}
            for instrument, data in self.current_prices.items():
                result[instrument] = {
                    "ltp": data.ltp,
                    "volume": data.volume,
                    "open": data.open,
                    "high": data.high,
                    "low": data.low,
                    "close": data.close,
                    "timestamp": data.timestamp.isoformat(),
                    "bid": data.bid,
                    "ask": data.ask,
                    "bid_qty": data.bid_qty,
                    "ask_qty": data.ask_qty
                }
            return result
    
    def set_market_regime(self, trend: str = "sideways", volatility: str = "normal"):
        """Set market regime parameters"""
        valid_trends = ["bullish", "bearish", "sideways"]
        valid_volatilities = ["low", "normal", "high"]
        
        if trend in valid_trends:
            self.market_trend = trend
            logger.info(f"Market trend set to: {trend}")
        
        if volatility in valid_volatilities:
            self.volatility_regime = volatility
            logger.info(f"Volatility regime set to: {volatility}")
    
    async def inject_event(self, event_type: str, magnitude: float = 0.01):
        """Inject market events for testing"""
        try:
            logger.info(f"Injecting market event: {event_type} with magnitude {magnitude}")
            
            if event_type == "spike_up":
                # Sudden price increase
                for instrument in self.current_prices:
                    current_data = self.current_prices[instrument]
                    new_price = current_data.ltp * (1 + magnitude)
                    self.current_prices[instrument].ltp = new_price
                    self.current_prices[instrument].high = max(current_data.high, new_price)
            
            elif event_type == "spike_down":
                # Sudden price decrease
                for instrument in self.current_prices:
                    current_data = self.current_prices[instrument]
                    new_price = current_data.ltp * (1 - magnitude)
                    self.current_prices[instrument].ltp = new_price
                    self.current_prices[instrument].low = min(current_data.low, new_price)
            
            elif event_type == "volatility_burst":
                # Increase volatility temporarily
                original_regime = self.volatility_regime
                self.volatility_regime = "high"
                await asyncio.sleep(60)  # High volatility for 1 minute
                self.volatility_regime = original_regime
            
            # Notify subscribers of the event
            await self._notify_subscribers()
        
        except Exception as e:
            logger.error(f"Error injecting market event: {e}")

# Global market data simulator instance
market_data_simulator = MarketDataSimulator()

class MarketDataFeed:
    """Market data feed interface for strategies"""
    
    def __init__(self):
        self.simulator = market_data_simulator
    
    async def get_data(self) -> Dict[str, Any]:
        """Get current market data"""
        return self.simulator.get_current_data()
    
    def subscribe(self, callback: callable):
        """Subscribe to market data updates"""
        self.simulator.subscribe(callback)
    
    def unsubscribe(self, callback: callable):
        """Unsubscribe from market data updates"""
        self.simulator.unsubscribe(callback)

# Global market data feed instance
market_data_feed = MarketDataFeed()
