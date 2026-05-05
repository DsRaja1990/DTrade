"""
Advanced Broker Interface for Intelligent Options Hedging Engine
Unified interface for multiple brokers with DhanHQ as primary
"""

import asyncio
import aiohttp
import json
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Union, Tuple
from enum import Enum
from dataclasses import dataclass, asdict
from abc import ABC, abstractmethod
import logging
import time
import hashlib
import hmac
import base64
from pathlib import Path

logger = logging.getLogger(__name__)

class OrderType(Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP_LOSS = "SL"
    STOP_LOSS_MARKET = "SL-M"
    BRACKET = "BO"
    COVER = "CO"

class OrderSide(Enum):
    BUY = "BUY"
    SELL = "SELL"

class OrderStatus(Enum):
    PENDING = "PENDING"
    OPEN = "OPEN"
    COMPLETE = "COMPLETE"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"
    PARTIAL = "PARTIAL"

class ProductType(Enum):
    CNC = "CNC"  # Cash and Carry
    NRML = "NRML"  # Normal
    MIS = "MIS"  # Margin Intraday Squareoff
    BO = "BO"  # Bracket Order
    CO = "CO"  # Cover Order

class ExchangeType(Enum):
    NSE = "NSE"
    BSE = "BSE"
    NFO = "NFO"  # NSE Futures & Options
    BFO = "BFO"  # BSE Futures & Options
    CDS = "CDS"  # Currency Derivatives
    MCX = "MCX"  # Multi Commodity Exchange

@dataclass
class OrderRequest:
    symbol: str
    quantity: int
    price: float
    order_type: OrderType
    side: OrderSide
    product_type: ProductType
    exchange: ExchangeType
    stop_loss: Optional[float] = None
    target: Optional[float] = None
    trailing_stop_loss: Optional[float] = None
    validity: str = "DAY"
    disclosed_quantity: int = 0
    
@dataclass
class Order:
    order_id: str
    symbol: str
    quantity: int
    price: float
    order_type: OrderType
    side: OrderSide
    product_type: ProductType
    exchange: ExchangeType
    status: OrderStatus
    filled_quantity: int = 0
    average_price: float = 0.0
    timestamp: Optional[datetime] = None
    message: str = ""
    
@dataclass
class Position:
    symbol: str
    quantity: int
    average_price: float
    current_price: float
    pnl: float
    product_type: ProductType
    exchange: ExchangeType
    timestamp: Optional[datetime] = None
    
@dataclass
class OptionChain:
    symbol: str
    strike_price: float
    expiry_date: str
    option_type: str  # CE or PE
    ltp: float
    bid: float
    ask: float
    volume: int
    open_interest: int
    implied_volatility: float
    delta: float
    gamma: float
    theta: float
    vega: float

class BrokerInterface(ABC):
    """Abstract base class for broker implementations"""
    
    @abstractmethod
    async def authenticate(self) -> bool:
        """Authenticate with broker"""
        pass
    
    @abstractmethod
    async def place_order(self, order_request: OrderRequest) -> str:
        """Place order and return order ID"""
        pass
    
    @abstractmethod
    async def modify_order(self, order_id: str, **kwargs) -> bool:
        """Modify existing order"""
        pass
    
    @abstractmethod
    async def cancel_order(self, order_id: str) -> bool:
        """Cancel order"""
        pass
    
    @abstractmethod
    async def get_order_status(self, order_id: str) -> Order:
        """Get order status"""
        pass
    
    @abstractmethod
    async def get_positions(self) -> List[Position]:
        """Get current positions"""
        pass
    
    @abstractmethod
    async def get_holdings(self) -> List[Dict[str, Any]]:
        """Get holdings"""
        pass
    
    @abstractmethod
    async def get_funds(self) -> Dict[str, float]:
        """Get account funds"""
        pass
    
    @abstractmethod
    async def get_ltp(self, symbol: str, exchange: ExchangeType) -> float:
        """Get last traded price"""
        pass
    
    @abstractmethod
    async def get_option_chain(self, underlying: str, expiry: str) -> List[OptionChain]:
        """Get option chain data"""
        pass

class DhanBroker(BrokerInterface):
    """DhanHQ broker implementation"""
    
    def __init__(self, config: Dict[str, Any]):
        self.client_id = config.get('client_id')
        self.access_token = config.get('access_token')
        self.base_url = config.get('base_url', 'https://api.dhan.co')
        self.session = None
        self.authenticated = False
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    def _get_headers(self) -> Dict[str, str]:
        """Get request headers"""
        return {
            'Content-Type': 'application/json',
            'access-token': self.access_token,
            'Accept': 'application/json'
        }
    
    async def authenticate(self) -> bool:
        """Authenticate with DhanHQ"""
        try:
            if not self.session:
                self.session = aiohttp.ClientSession()
                
            headers = self._get_headers()
            async with self.session.get(
                f"{self.base_url}/funds",
                headers=headers
            ) as response:
                if response.status == 200:
                    self.authenticated = True
                    logger.info("DhanHQ authentication successful")
                    return True
                else:
                    logger.error(f"DhanHQ authentication failed: {response.status}")
                    return False
                    
        except Exception as e:
            logger.error(f"DhanHQ authentication error: {e}")
            return False
    
    async def place_order(self, order_request: OrderRequest) -> str:
        """Place order with DhanHQ"""
        if not self.authenticated:
            await self.authenticate()
            
        try:
            order_data = {
                "dhanClientId": self.client_id,
                "correlationId": f"order_{int(time.time())}",
                "transactionType": order_request.side.value,
                "exchangeSegment": order_request.exchange.value,
                "productType": order_request.product_type.value,
                "orderType": order_request.order_type.value,
                "validity": order_request.validity,
                "securityId": await self._get_security_id(order_request.symbol, order_request.exchange),
                "quantity": order_request.quantity,
                "disclosedQuantity": order_request.disclosed_quantity,
                "price": order_request.price if order_request.order_type != OrderType.MARKET else 0,
                "triggerPrice": order_request.stop_loss if order_request.stop_loss else 0,
            }
            
            headers = self._get_headers()
            async with self.session.post(
                f"{self.base_url}/orders",
                headers=headers,
                json=order_data
            ) as response:
                result = await response.json()
                
                if response.status == 200 and result.get('status') == 'success':
                    order_id = result.get('data', {}).get('orderId')
                    logger.info(f"Order placed successfully: {order_id}")
                    return order_id
                else:
                    logger.error(f"Order placement failed: {result}")
                    raise Exception(f"Order placement failed: {result.get('message', 'Unknown error')}")
                    
        except Exception as e:
            logger.error(f"Error placing order: {e}")
            raise
    
    async def modify_order(self, order_id: str, **kwargs) -> bool:
        """Modify existing order"""
        try:
            modify_data = {
                "dhanClientId": self.client_id,
                "orderId": order_id,
                **kwargs
            }
            
            headers = self._get_headers()
            async with self.session.put(
                f"{self.base_url}/orders/{order_id}",
                headers=headers,
                json=modify_data
            ) as response:
                result = await response.json()
                
                if response.status == 200 and result.get('status') == 'success':
                    logger.info(f"Order modified successfully: {order_id}")
                    return True
                else:
                    logger.error(f"Order modification failed: {result}")
                    return False
                    
        except Exception as e:
            logger.error(f"Error modifying order: {e}")
            return False
    
    async def cancel_order(self, order_id: str) -> bool:
        """Cancel order"""
        try:
            headers = self._get_headers()
            async with self.session.delete(
                f"{self.base_url}/orders/{order_id}",
                headers=headers
            ) as response:
                result = await response.json()
                
                if response.status == 200 and result.get('status') == 'success':
                    logger.info(f"Order cancelled successfully: {order_id}")
                    return True
                else:
                    logger.error(f"Order cancellation failed: {result}")
                    return False
                    
        except Exception as e:
            logger.error(f"Error cancelling order: {e}")
            return False
    
    async def get_order_status(self, order_id: str) -> Order:
        """Get order status"""
        try:
            headers = self._get_headers()
            async with self.session.get(
                f"{self.base_url}/orders/{order_id}",
                headers=headers
            ) as response:
                result = await response.json()
                
                if response.status == 200 and result.get('status') == 'success':
                    order_data = result.get('data', {})
                    return self._parse_order_data(order_data)
                else:
                    logger.error(f"Failed to get order status: {result}")
                    raise Exception(f"Failed to get order status: {result.get('message', 'Unknown error')}")
                    
        except Exception as e:
            logger.error(f"Error getting order status: {e}")
            raise
    
    async def get_positions(self) -> List[Position]:
        """Get current positions"""
        try:
            headers = self._get_headers()
            async with self.session.get(
                f"{self.base_url}/positions",
                headers=headers
            ) as response:
                result = await response.json()
                
                if response.status == 200 and result.get('status') == 'success':
                    positions_data = result.get('data', [])
                    return [self._parse_position_data(pos) for pos in positions_data]
                else:
                    logger.error(f"Failed to get positions: {result}")
                    return []
                    
        except Exception as e:
            logger.error(f"Error getting positions: {e}")
            return []
    
    async def get_holdings(self) -> List[Dict[str, Any]]:
        """Get holdings"""
        try:
            headers = self._get_headers()
            async with self.session.get(
                f"{self.base_url}/holdings",
                headers=headers
            ) as response:
                result = await response.json()
                
                if response.status == 200 and result.get('status') == 'success':
                    return result.get('data', [])
                else:
                    logger.error(f"Failed to get holdings: {result}")
                    return []
                    
        except Exception as e:
            logger.error(f"Error getting holdings: {e}")
            return []
    
    async def get_funds(self) -> Dict[str, float]:
        """Get account funds"""
        try:
            headers = self._get_headers()
            async with self.session.get(
                f"{self.base_url}/funds",
                headers=headers
            ) as response:
                result = await response.json()
                
                if response.status == 200 and result.get('status') == 'success':
                    funds_data = result.get('data', {})
                    return {
                        'available_balance': float(funds_data.get('availabelBalance', 0)),
                        'used_margin': float(funds_data.get('utilizedAmount', 0)),
                        'total_balance': float(funds_data.get('totalBalance', 0)),
                        'collateral': float(funds_data.get('collateral', 0))
                    }
                else:
                    logger.error(f"Failed to get funds: {result}")
                    return {}
                    
        except Exception as e:
            logger.error(f"Error getting funds: {e}")
            return {}
    
    async def get_ltp(self, symbol: str, exchange: ExchangeType) -> float:
        """Get last traded price"""
        try:
            security_id = await self._get_security_id(symbol, exchange)
            
            headers = self._get_headers()
            async with self.session.get(
                f"{self.base_url}/marketfeed/ltp",
                headers=headers,
                params={'securityId': security_id}
            ) as response:
                result = await response.json()
                
                if response.status == 200 and result.get('status') == 'success':
                    return float(result.get('data', {}).get('LTP', 0))
                else:
                    logger.error(f"Failed to get LTP: {result}")
                    return 0.0
                    
        except Exception as e:
            logger.error(f"Error getting LTP: {e}")
            return 0.0
    
    async def get_option_chain(self, underlying: str, expiry: str) -> List[OptionChain]:
        """Get option chain data"""
        try:
            headers = self._get_headers()
            async with self.session.get(
                f"{self.base_url}/marketfeed/optionchain",
                headers=headers,
                params={
                    'underlying': underlying,
                    'expiry': expiry
                }
            ) as response:
                result = await response.json()
                
                if response.status == 200 and result.get('status') == 'success':
                    chain_data = result.get('data', [])
                    return [self._parse_option_data(option) for option in chain_data]
                else:
                    logger.error(f"Failed to get option chain: {result}")
                    return []
                    
        except Exception as e:
            logger.error(f"Error getting option chain: {e}")
            return []
    
    async def _get_security_id(self, symbol: str, exchange: ExchangeType) -> str:
        """Get security ID for symbol"""
        # This would typically involve a symbol lookup API
        # For now, return the symbol as-is
        return symbol
    
    def _parse_order_data(self, order_data: Dict[str, Any]) -> Order:
        """Parse order data from API response"""
        return Order(
            order_id=order_data.get('orderId', ''),
            symbol=order_data.get('tradingSymbol', ''),
            quantity=int(order_data.get('quantity', 0)),
            price=float(order_data.get('price', 0)),
            order_type=OrderType(order_data.get('orderType', 'MARKET')),
            side=OrderSide(order_data.get('transactionType', 'BUY')),
            product_type=ProductType(order_data.get('productType', 'MIS')),
            exchange=ExchangeType(order_data.get('exchangeSegment', 'NSE')),
            status=self._parse_order_status(order_data.get('orderStatus', '')),
            filled_quantity=int(order_data.get('filledQty', 0)),
            average_price=float(order_data.get('avgPrice', 0)),
            timestamp=datetime.now(),
            message=order_data.get('orderStatusMessage', '')
        )
    
    def _parse_order_status(self, status: str) -> OrderStatus:
        """Parse order status from API"""
        status_map = {
            'PENDING': OrderStatus.PENDING,
            'OPEN': OrderStatus.OPEN,
            'COMPLETE': OrderStatus.COMPLETE,
            'CANCELLED': OrderStatus.CANCELLED,
            'REJECTED': OrderStatus.REJECTED,
            'PARTIAL': OrderStatus.PARTIAL
        }
        return status_map.get(status, OrderStatus.PENDING)
    
    def _parse_position_data(self, pos_data: Dict[str, Any]) -> Position:
        """Parse position data from API response"""
        return Position(
            symbol=pos_data.get('tradingSymbol', ''),
            quantity=int(pos_data.get('positionType', 0)),
            average_price=float(pos_data.get('avgPrice', 0)),
            current_price=float(pos_data.get('ltp', 0)),
            pnl=float(pos_data.get('realizedPnl', 0)),
            product_type=ProductType(pos_data.get('productType', 'MIS')),
            exchange=ExchangeType(pos_data.get('exchangeSegment', 'NSE')),
            timestamp=datetime.now()
        )
    
    def _parse_option_data(self, option_data: Dict[str, Any]) -> OptionChain:
        """Parse option chain data from API response"""
        return OptionChain(
            symbol=option_data.get('tradingSymbol', ''),
            strike_price=float(option_data.get('strikePrice', 0)),
            expiry_date=option_data.get('expiryDate', ''),
            option_type=option_data.get('optionType', ''),
            ltp=float(option_data.get('LTP', 0)),
            bid=float(option_data.get('bidPrice', 0)),
            ask=float(option_data.get('askPrice', 0)),
            volume=int(option_data.get('volume', 0)),
            open_interest=int(option_data.get('openInterest', 0)),
            implied_volatility=float(option_data.get('impliedVolatility', 0)),
            delta=float(option_data.get('delta', 0)),
            gamma=float(option_data.get('gamma', 0)),
            theta=float(option_data.get('theta', 0)),
            vega=float(option_data.get('vega', 0))
        )

class MockBroker(BrokerInterface):
    """Mock broker for testing"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.orders = {}
        self.positions = []
        self.funds = {
            'available_balance': 100000.0,
            'used_margin': 0.0,
            'total_balance': 100000.0,
            'collateral': 0.0
        }
        self.order_counter = 1
        
    async def authenticate(self) -> bool:
        return True
    
    async def place_order(self, order_request: OrderRequest) -> str:
        order_id = f"MOCK_{self.order_counter:06d}"
        self.order_counter += 1
        
        order = Order(
            order_id=order_id,
            symbol=order_request.symbol,
            quantity=order_request.quantity,
            price=order_request.price,
            order_type=order_request.order_type,
            side=order_request.side,
            product_type=order_request.product_type,
            exchange=order_request.exchange,
            status=OrderStatus.COMPLETE,
            filled_quantity=order_request.quantity,
            average_price=order_request.price,
            timestamp=datetime.now()
        )
        
        self.orders[order_id] = order
        logger.info(f"Mock order placed: {order_id}")
        return order_id
    
    async def modify_order(self, order_id: str, **kwargs) -> bool:
        if order_id in self.orders:
            logger.info(f"Mock order modified: {order_id}")
            return True
        return False
    
    async def cancel_order(self, order_id: str) -> bool:
        if order_id in self.orders:
            self.orders[order_id].status = OrderStatus.CANCELLED
            logger.info(f"Mock order cancelled: {order_id}")
            return True
        return False
    
    async def get_order_status(self, order_id: str) -> Order:
        return self.orders.get(order_id)
    
    async def get_positions(self) -> List[Position]:
        return self.positions
    
    async def get_holdings(self) -> List[Dict[str, Any]]:
        return []
    
    async def get_funds(self) -> Dict[str, float]:
        return self.funds.copy()
    
    async def get_ltp(self, symbol: str, exchange: ExchangeType) -> float:
        # Return mock LTP based on symbol
        base_prices = {
            'NIFTY': 19500.0,
            'BANKNIFTY': 44000.0,
            'SENSEX': 65000.0
        }
        
        for base, price in base_prices.items():
            if base in symbol.upper():
                return price + (hash(symbol) % 1000 - 500)  # Add some variance
        
        return 100.0  # Default mock price
    
    async def get_option_chain(self, underlying: str, expiry: str) -> List[OptionChain]:
        # Return mock option chain
        base_price = await self.get_ltp(underlying, ExchangeType.NSE)
        option_chain = []
        
        for i in range(-5, 6):  # 11 strikes around current price
            strike = base_price + (i * 100)
            
            for option_type in ['CE', 'PE']:
                option_chain.append(OptionChain(
                    symbol=f"{underlying}{strike}{option_type}",
                    strike_price=strike,
                    expiry_date=expiry,
                    option_type=option_type,
                    ltp=abs(i * 50) + 10,  # Mock premium
                    bid=abs(i * 50) + 5,
                    ask=abs(i * 50) + 15,
                    volume=1000 - abs(i * 100),
                    open_interest=5000 - abs(i * 500),
                    implied_volatility=0.15 + abs(i * 0.01),
                    delta=0.5 if option_type == 'CE' else -0.5,
                    gamma=0.01,
                    theta=-0.05,
                    vega=0.1
                ))
        
        return option_chain

class BrokerManager:
    """Unified broker management interface"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.brokers = {}
        self.primary_broker = None
        self._initialize_brokers()
        
    def _initialize_brokers(self):
        """Initialize configured brokers"""
        broker_configs = self.config.get('brokers', {})
        
        for broker_name, broker_config in broker_configs.items():
            if broker_config.get('enabled', False):
                try:
                    if broker_name == 'dhan':
                        self.brokers[broker_name] = DhanBroker(broker_config)
                    elif broker_name == 'mock':
                        self.brokers[broker_name] = MockBroker(broker_config)
                    
                    if broker_config.get('primary', False):
                        self.primary_broker = self.brokers[broker_name]
                        
                except Exception as e:
                    logger.error(f"Failed to initialize broker {broker_name}: {e}")
        
        if not self.primary_broker and self.brokers:
            self.primary_broker = next(iter(self.brokers.values()))
    
    async def authenticate_all(self) -> Dict[str, bool]:
        """Authenticate all brokers"""
        results = {}
        for name, broker in self.brokers.items():
            try:
                results[name] = await broker.authenticate()
            except Exception as e:
                logger.error(f"Authentication failed for {name}: {e}")
                results[name] = False
        return results
    
    def get_broker(self, name: str = None) -> BrokerInterface:
        """Get specific broker or primary broker"""
        if name:
            return self.brokers.get(name)
        return self.primary_broker
    
    async def place_order_with_fallback(self, order_request: OrderRequest,
                                      preferred_broker: str = None) -> Tuple[str, str]:
        """Place order with broker fallback"""
        brokers_to_try = []
        
        if preferred_broker and preferred_broker in self.brokers:
            brokers_to_try.append((preferred_broker, self.brokers[preferred_broker]))
        
        # Add primary broker if not already included
        if self.primary_broker and (not preferred_broker or 
                                   self.primary_broker != self.brokers.get(preferred_broker)):
            primary_name = next(name for name, broker in self.brokers.items() 
                              if broker == self.primary_broker)
            brokers_to_try.append((primary_name, self.primary_broker))
        
        # Add other brokers
        for name, broker in self.brokers.items():
            if (name, broker) not in brokers_to_try:
                brokers_to_try.append((name, broker))
        
        for broker_name, broker in brokers_to_try:
            try:
                order_id = await broker.place_order(order_request)
                logger.info(f"Order placed successfully with {broker_name}: {order_id}")
                return order_id, broker_name
            except Exception as e:
                logger.warning(f"Order failed with {broker_name}: {e}")
                continue
        
        raise Exception("All brokers failed to place order")
    
    async def get_consolidated_positions(self) -> Dict[str, List[Position]]:
        """Get positions from all brokers"""
        all_positions = {}
        for name, broker in self.brokers.items():
            try:
                positions = await broker.get_positions()
                all_positions[name] = positions
            except Exception as e:
                logger.error(f"Failed to get positions from {name}: {e}")
                all_positions[name] = []
        return all_positions
    
    async def get_consolidated_funds(self) -> Dict[str, Dict[str, float]]:
        """Get funds from all brokers"""
        all_funds = {}
        for name, broker in self.brokers.items():
            try:
                funds = await broker.get_funds()
                all_funds[name] = funds
            except Exception as e:
                logger.error(f"Failed to get funds from {name}: {e}")
                all_funds[name] = {}
        return all_funds

# Global broker manager instance
_broker_manager = None

def setup_broker_manager(config: Dict[str, Any]) -> BrokerManager:
    """Setup global broker manager"""
    global _broker_manager
    _broker_manager = BrokerManager(config)
    return _broker_manager

def get_broker_manager() -> BrokerManager:
    """Get global broker manager"""
    if _broker_manager is None:
        raise RuntimeError("Broker manager not initialized. Call setup_broker_manager() first.")
    return _broker_manager
