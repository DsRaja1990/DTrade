"""
Trade Executor - Advanced Trade Execution Engine with Smart Order Management
Handles intelligent order placement, execution optimization, and risk management
"""

import asyncio
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import logging
from enum import Enum
import uuid
import threading
from concurrent.futures import ThreadPoolExecutor
import time

logger = logging.getLogger(__name__)

class OrderType(Enum):
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"
    BRACKET = "bracket"
    ICEBERG = "iceberg"
    TWAP = "twap"
    VWAP = "vwap"

class OrderStatus(Enum):
    PENDING = "pending"
    SUBMITTED = "submitted"
    PARTIALLY_FILLED = "partially_filled"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    EXPIRED = "expired"

class TradeAction(Enum):
    BUY = "buy"
    SELL = "sell"
    BUY_TO_OPEN = "buy_to_open"
    BUY_TO_CLOSE = "buy_to_close"
    SELL_TO_OPEN = "sell_to_open"
    SELL_TO_CLOSE = "sell_to_close"

class ExecutionAlgorithm(Enum):
    AGGRESSIVE = "aggressive"
    PASSIVE = "passive"
    ICEBERG = "iceberg"
    TWAP = "twap"
    VWAP = "vwap"
    SMART = "smart"
    DARK_POOL = "dark_pool"

@dataclass
class TradeOrder:
    """Individual trade order"""
    order_id: str
    symbol: str
    action: TradeAction
    quantity: int
    order_type: OrderType
    price: Optional[float] = None
    stop_price: Optional[float] = None
    time_in_force: str = "DAY"
    execution_algorithm: ExecutionAlgorithm = ExecutionAlgorithm.SMART
    
    # Order metadata
    strategy_id: str = ""
    parent_order_id: Optional[str] = None
    child_orders: List[str] = field(default_factory=list)
    
    # Status tracking
    status: OrderStatus = OrderStatus.PENDING
    filled_quantity: int = 0
    avg_fill_price: float = 0.0
    commission: float = 0.0
    
    # Timestamps
    created_at: datetime = field(default_factory=datetime.now)
    submitted_at: Optional[datetime] = None
    filled_at: Optional[datetime] = None
    
    # Risk management
    max_slippage: float = 0.02  # 2%
    urgency: float = 0.5  # 0-1 scale
    iceberg_size: Optional[int] = None
    
    # Execution tracking
    execution_attempts: int = 0
    last_attempt_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None

@dataclass
class ExecutionResult:
    """Result of trade execution"""
    order_id: str
    success: bool
    filled_quantity: int
    avg_fill_price: float
    total_commission: float
    execution_time: float
    slippage: float
    market_impact: float
    error_message: Optional[str] = None

@dataclass
class TradeStrategy:
    """Complete trade strategy with multiple legs"""
    strategy_id: str
    strategy_name: str
    orders: List[TradeOrder]
    total_cost: float
    max_risk: float
    expected_return: float
    confidence: float
    created_at: datetime = field(default_factory=datetime.now)
    status: str = "pending"

class TradeExecutor:
    """Advanced trade execution engine"""
    
    def __init__(self, config: Dict[str, Any], dhan_connector):
        self.config = config
        self.dhan_connector = dhan_connector
        
        # Order management
        self.active_orders: Dict[str, TradeOrder] = {}
        self.order_history: List[TradeOrder] = []
        self.execution_results: List[ExecutionResult] = []
        
        # Strategy tracking
        self.active_strategies: Dict[str, TradeStrategy] = {}
        self.strategy_history: List[TradeStrategy] = []
        
        # Execution parameters
        self.max_slippage_tolerance = config.get('max_slippage_tolerance', 0.02)
        self.order_timeout_seconds = config.get('order_timeout_seconds', 300)
        self.max_order_attempts = config.get('max_order_attempts', 3)
        self.position_size_limits = config.get('position_size_limits', {})
        
        # Market data for execution optimization
        self.market_data_cache: Dict[str, Dict] = {}
        self.last_market_update: Dict[str, datetime] = {}
        
        # Threading
        self.lock = threading.Lock()
        self.executor_pool = ThreadPoolExecutor(max_workers=5)
        self.execution_queue = asyncio.Queue()
        
        # Risk management
        self.daily_loss_limit = config.get('daily_loss_limit', 50000)
        self.max_position_value = config.get('max_position_value', 500000)
        self.current_daily_pnl = 0.0
        
        # Performance tracking
        self.execution_stats = {
            'total_orders': 0,
            'successful_orders': 0,
            'avg_execution_time': 0.0,
            'avg_slippage': 0.0,
            'total_commission': 0.0
        }
        
        logger.info("Trade Executor initialized")
    
    async def execute_strategy(self, strategy: TradeStrategy) -> bool:
        """Execute a complete trading strategy"""
        try:
            logger.info(f"Executing strategy: {strategy.strategy_name} with {len(strategy.orders)} orders")
            
            # Pre-execution risk checks
            if not await self._validate_strategy_risk(strategy):
                logger.warning(f"Strategy {strategy.strategy_id} failed risk validation")
                return False
            
            # Store strategy
            with self.lock:
                self.active_strategies[strategy.strategy_id] = strategy
                strategy.status = "executing"
            
            # Execute orders based on strategy requirements
            execution_success = await self._execute_strategy_orders(strategy)
            
            # Update strategy status
            with self.lock:
                if execution_success:
                    strategy.status = "completed"
                    logger.info(f"Strategy {strategy.strategy_name} executed successfully")
                else:
                    strategy.status = "failed"
                    logger.error(f"Strategy {strategy.strategy_name} execution failed")
                
                # Move to history
                self.strategy_history.append(strategy)
                if strategy.strategy_id in self.active_strategies:
                    del self.active_strategies[strategy.strategy_id]
            
            return execution_success
            
        except Exception as e:
            logger.error(f"Error executing strategy {strategy.strategy_name}: {e}")
            return False
    
    async def execute_order(self, order: TradeOrder) -> ExecutionResult:
        """Execute a single trade order with intelligent routing"""
        start_time = time.time()
        
        try:
            logger.info(f"Executing order {order.order_id}: {order.action.value} {order.quantity} {order.symbol}")
            
            # Pre-execution validation
            if not await self._validate_order(order):
                return ExecutionResult(
                    order_id=order.order_id,
                    success=False,
                    filled_quantity=0,
                    avg_fill_price=0.0,
                    total_commission=0.0,
                    execution_time=time.time() - start_time,
                    slippage=0.0,
                    market_impact=0.0,
                    error_message="Order validation failed"
                )
            
            # Store order
            with self.lock:
                self.active_orders[order.order_id] = order
                order.status = OrderStatus.SUBMITTED
                order.submitted_at = datetime.now()
            
            # Get optimal execution strategy
            execution_plan = await self._get_execution_plan(order)
            
            # Execute based on algorithm
            result = await self._execute_with_algorithm(order, execution_plan)
            
            # Update statistics
            self._update_execution_stats(result)
            
            # Store result
            self.execution_results.append(result)
            
            # Update order status
            with self.lock:
                if result.success:
                    order.status = OrderStatus.FILLED
                    order.filled_quantity = result.filled_quantity
                    order.avg_fill_price = result.avg_fill_price
                    order.commission = result.total_commission
                    order.filled_at = datetime.now()
                else:
                    order.status = OrderStatus.REJECTED
                    order.rejection_reason = result.error_message
                
                # Move to history
                self.order_history.append(order)
                if order.order_id in self.active_orders:
                    del self.active_orders[order.order_id]
            
            return result
            
        except Exception as e:
            logger.error(f"Error executing order {order.order_id}: {e}")
            return ExecutionResult(
                order_id=order.order_id,
                success=False,
                filled_quantity=0,
                avg_fill_price=0.0,
                total_commission=0.0,
                execution_time=time.time() - start_time,
                slippage=0.0,
                market_impact=0.0,
                error_message=str(e)
            )
    
    async def _validate_strategy_risk(self, strategy: TradeStrategy) -> bool:
        """Validate strategy against risk limits"""
        try:
            # Check daily loss limit
            if self.current_daily_pnl < -self.daily_loss_limit:
                logger.warning("Daily loss limit exceeded")
                return False
            
            # Check total strategy cost
            if strategy.total_cost > self.max_position_value:
                logger.warning(f"Strategy cost {strategy.total_cost} exceeds limit {self.max_position_value}")
                return False
            
            # Check maximum risk
            if strategy.max_risk > strategy.total_cost * 0.5:  # Max 50% risk
                logger.warning(f"Strategy risk {strategy.max_risk} too high")
                return False
            
            # Validate each order
            for order in strategy.orders:
                if not await self._validate_order_risk(order):
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error validating strategy risk: {e}")
            return False
    
    async def _validate_order(self, order: TradeOrder) -> bool:
        """Validate individual order"""
        try:
            # Basic validation
            if order.quantity <= 0:
                logger.warning(f"Invalid quantity: {order.quantity}")
                return False
            
            if not order.symbol:
                logger.warning("Empty symbol")
                return False
            
            # Market hours check
            if not await self._is_market_open():
                logger.warning("Market is closed")
                return False
            
            # Position size limits
            if not await self._check_position_limits(order):
                return False
            
            # Price validation for limit orders
            if order.order_type in [OrderType.LIMIT, OrderType.STOP_LIMIT]:
                if not order.price or order.price <= 0:
                    logger.warning("Invalid price for limit order")
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error validating order: {e}")
            return False
    
    async def _validate_order_risk(self, order: TradeOrder) -> bool:
        """Validate order against risk parameters"""
        try:
            # Get current market price
            market_price = await self._get_market_price(order.symbol)
            
            if not market_price:
                logger.warning(f"Cannot get market price for {order.symbol}")
                return False
            
            # Calculate order value
            order_value = order.quantity * market_price
            
            # Check against position limits
            symbol_limit = self.position_size_limits.get(order.symbol, self.max_position_value * 0.1)
            if order_value > symbol_limit:
                logger.warning(f"Order value {order_value} exceeds symbol limit {symbol_limit}")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error validating order risk: {e}")
            return False
    
    async def _get_execution_plan(self, order: TradeOrder) -> Dict[str, Any]:
        """Get optimal execution plan for order"""
        try:
            # Get market conditions
            market_data = await self._get_market_data(order.symbol)
            
            # Calculate market impact
            estimated_impact = await self._estimate_market_impact(order, market_data)
            
            # Determine execution strategy
            if order.execution_algorithm == ExecutionAlgorithm.SMART:
                algorithm = await self._choose_smart_algorithm(order, market_data, estimated_impact)
            else:
                algorithm = order.execution_algorithm
            
            # Create execution plan
            plan = {
                'algorithm': algorithm,
                'estimated_impact': estimated_impact,
                'market_data': market_data,
                'chunk_size': await self._calculate_optimal_chunk_size(order, market_data),
                'timing_strategy': await self._get_timing_strategy(order, market_data),
                'price_strategy': await self._get_price_strategy(order, market_data)
            }
            
            return plan
            
        except Exception as e:
            logger.error(f"Error creating execution plan: {e}")
            return {'algorithm': ExecutionAlgorithm.AGGRESSIVE}
    
    async def _execute_with_algorithm(self, order: TradeOrder, execution_plan: Dict[str, Any]) -> ExecutionResult:
        """Execute order with specified algorithm"""
        algorithm = execution_plan.get('algorithm', ExecutionAlgorithm.AGGRESSIVE)
        
        try:
            if algorithm == ExecutionAlgorithm.AGGRESSIVE:
                return await self._execute_aggressive(order, execution_plan)
            elif algorithm == ExecutionAlgorithm.PASSIVE:
                return await self._execute_passive(order, execution_plan)
            elif algorithm == ExecutionAlgorithm.ICEBERG:
                return await self._execute_iceberg(order, execution_plan)
            elif algorithm == ExecutionAlgorithm.TWAP:
                return await self._execute_twap(order, execution_plan)
            elif algorithm == ExecutionAlgorithm.VWAP:
                return await self._execute_vwap(order, execution_plan)
            else:
                return await self._execute_aggressive(order, execution_plan)
                
        except Exception as e:
            logger.error(f"Error executing with algorithm {algorithm}: {e}")
            return ExecutionResult(
                order_id=order.order_id,
                success=False,
                filled_quantity=0,
                avg_fill_price=0.0,
                total_commission=0.0,
                execution_time=0.0,
                slippage=0.0,
                market_impact=0.0,
                error_message=str(e)
            )
    
    async def _execute_aggressive(self, order: TradeOrder, execution_plan: Dict[str, Any]) -> ExecutionResult:
        """Execute order aggressively (market order)"""
        start_time = time.time()
        
        try:
            # Prepare order data for DhanHQ
            order_data = {
                'symbol': order.symbol,
                'action': order.action.value,
                'quantity': order.quantity,
                'order_type': 'MARKET',
                'price': 0.0,  # Market order
                'time_in_force': order.time_in_force
            }
            
            # Submit to broker
            broker_response = await self.dhan_connector.place_order(order_data)
            
            if broker_response.get('success'):
                # Get fill details
                fill_price = broker_response.get('avg_price', 0.0)
                filled_qty = broker_response.get('filled_quantity', order.quantity)
                commission = broker_response.get('commission', 0.0)
                
                # Calculate slippage
                market_price = execution_plan.get('market_data', {}).get('price', fill_price)
                slippage = abs(fill_price - market_price) / market_price if market_price > 0 else 0.0
                
                return ExecutionResult(
                    order_id=order.order_id,
                    success=True,
                    filled_quantity=filled_qty,
                    avg_fill_price=fill_price,
                    total_commission=commission,
                    execution_time=time.time() - start_time,
                    slippage=slippage,
                    market_impact=execution_plan.get('estimated_impact', 0.0),
                    error_message=None
                )
            else:
                return ExecutionResult(
                    order_id=order.order_id,
                    success=False,
                    filled_quantity=0,
                    avg_fill_price=0.0,
                    total_commission=0.0,
                    execution_time=time.time() - start_time,
                    slippage=0.0,
                    market_impact=0.0,
                    error_message=broker_response.get('error', 'Unknown error')
                )
                
        except Exception as e:
            logger.error(f"Error in aggressive execution: {e}")
            return ExecutionResult(
                order_id=order.order_id,
                success=False,
                filled_quantity=0,
                avg_fill_price=0.0,
                total_commission=0.0,
                execution_time=time.time() - start_time,
                slippage=0.0,
                market_impact=0.0,
                error_message=str(e)
            )
    
    async def _execute_passive(self, order: TradeOrder, execution_plan: Dict[str, Any]) -> ExecutionResult:
        """Execute order passively (limit order)"""
        start_time = time.time()
        
        try:
            market_data = execution_plan.get('market_data', {})
            current_price = market_data.get('price', 0.0)
            
            # Set limit price with small improvement
            if order.action in [TradeAction.BUY, TradeAction.BUY_TO_OPEN, TradeAction.BUY_TO_CLOSE]:
                limit_price = current_price * 0.998  # 0.2% below market
            else:
                limit_price = current_price * 1.002  # 0.2% above market
            
            order_data = {
                'symbol': order.symbol,
                'action': order.action.value,
                'quantity': order.quantity,
                'order_type': 'LIMIT',
                'price': limit_price,
                'time_in_force': order.time_in_force
            }
            
            # Submit limit order
            broker_response = await self.dhan_connector.place_order(order_data)
            
            if broker_response.get('success'):
                # Wait for fill or timeout
                order_id = broker_response.get('order_id')
                fill_result = await self._wait_for_fill(order_id, self.order_timeout_seconds)
                
                if fill_result['filled']:
                    slippage = abs(fill_result['avg_price'] - current_price) / current_price if current_price > 0 else 0.0
                    
                    return ExecutionResult(
                        order_id=order.order_id,
                        success=True,
                        filled_quantity=fill_result['filled_quantity'],
                        avg_fill_price=fill_result['avg_price'],
                        total_commission=fill_result['commission'],
                        execution_time=time.time() - start_time,
                        slippage=slippage,
                        market_impact=execution_plan.get('estimated_impact', 0.0),
                        error_message=None
                    )
                else:
                    # Cancel unfilled order
                    await self.dhan_connector.cancel_order(order_id)
                    
                    return ExecutionResult(
                        order_id=order.order_id,
                        success=False,
                        filled_quantity=0,
                        avg_fill_price=0.0,
                        total_commission=0.0,
                        execution_time=time.time() - start_time,
                        slippage=0.0,
                        market_impact=0.0,
                        error_message="Order not filled within timeout"
                    )
            else:
                return ExecutionResult(
                    order_id=order.order_id,
                    success=False,
                    filled_quantity=0,
                    avg_fill_price=0.0,
                    total_commission=0.0,
                    execution_time=time.time() - start_time,
                    slippage=0.0,
                    market_impact=0.0,
                    error_message=broker_response.get('error', 'Order submission failed')
                )
                
        except Exception as e:
            logger.error(f"Error in passive execution: {e}")
            return ExecutionResult(
                order_id=order.order_id,
                success=False,
                filled_quantity=0,
                avg_fill_price=0.0,
                total_commission=0.0,
                execution_time=time.time() - start_time,
                slippage=0.0,
                market_impact=0.0,
                error_message=str(e)
            )
    
    async def _execute_iceberg(self, order: TradeOrder, execution_plan: Dict[str, Any]) -> ExecutionResult:
        """Execute large order using iceberg strategy"""
        start_time = time.time()
        
        try:
            chunk_size = execution_plan.get('chunk_size', order.quantity // 5)
            chunk_size = max(1, min(chunk_size, order.quantity))
            
            total_filled = 0
            total_commission = 0.0
            weighted_avg_price = 0.0
            
            remaining_quantity = order.quantity
            
            while remaining_quantity > 0 and total_filled < order.quantity:
                current_chunk = min(chunk_size, remaining_quantity)
                
                # Create chunk order
                chunk_order = TradeOrder(
                    order_id=f"{order.order_id}_chunk_{total_filled}",
                    symbol=order.symbol,
                    action=order.action,
                    quantity=current_chunk,
                    order_type=OrderType.LIMIT,
                    parent_order_id=order.order_id
                )
                
                # Execute chunk
                chunk_result = await self._execute_passive(chunk_order, execution_plan)
                
                if chunk_result.success:
                    total_filled += chunk_result.filled_quantity
                    total_commission += chunk_result.total_commission
                    
                    # Update weighted average price
                    if total_filled > 0:
                        weighted_avg_price = (
                            (weighted_avg_price * (total_filled - chunk_result.filled_quantity) +
                             chunk_result.avg_fill_price * chunk_result.filled_quantity) / total_filled
                        )
                    
                    remaining_quantity -= chunk_result.filled_quantity
                    
                    # Wait between chunks to reduce market impact
                    await asyncio.sleep(2)
                else:
                    logger.warning(f"Chunk execution failed: {chunk_result.error_message}")
                    break
            
            # Calculate overall slippage
            market_price = execution_plan.get('market_data', {}).get('price', weighted_avg_price)
            slippage = abs(weighted_avg_price - market_price) / market_price if market_price > 0 else 0.0
            
            success = total_filled > 0
            
            return ExecutionResult(
                order_id=order.order_id,
                success=success,
                filled_quantity=total_filled,
                avg_fill_price=weighted_avg_price,
                total_commission=total_commission,
                execution_time=time.time() - start_time,
                slippage=slippage,
                market_impact=execution_plan.get('estimated_impact', 0.0),
                error_message=None if success else "Iceberg execution failed"
            )
            
        except Exception as e:
            logger.error(f"Error in iceberg execution: {e}")
            return ExecutionResult(
                order_id=order.order_id,
                success=False,
                filled_quantity=0,
                avg_fill_price=0.0,
                total_commission=0.0,
                execution_time=time.time() - start_time,
                slippage=0.0,
                market_impact=0.0,
                error_message=str(e)
            )
    
    async def _execute_twap(self, order: TradeOrder, execution_plan: Dict[str, Any]) -> ExecutionResult:
        """Execute order using Time-Weighted Average Price strategy"""
        start_time = time.time()
        
        try:
            # TWAP parameters
            execution_window_minutes = 30  # Execute over 30 minutes
            slice_interval_minutes = 2    # Execute every 2 minutes
            num_slices = execution_window_minutes // slice_interval_minutes
            
            slice_size = order.quantity // num_slices
            if slice_size == 0:
                slice_size = 1
                num_slices = order.quantity
            
            total_filled = 0
            total_commission = 0.0
            weighted_avg_price = 0.0
            
            for i in range(num_slices):
                if total_filled >= order.quantity:
                    break
                
                current_slice = min(slice_size, order.quantity - total_filled)
                
                # Create slice order
                slice_order = TradeOrder(
                    order_id=f"{order.order_id}_twap_{i}",
                    symbol=order.symbol,
                    action=order.action,
                    quantity=current_slice,
                    order_type=OrderType.LIMIT,
                    parent_order_id=order.order_id
                )
                
                # Execute slice
                slice_result = await self._execute_passive(slice_order, execution_plan)
                
                if slice_result.success:
                    total_filled += slice_result.filled_quantity
                    total_commission += slice_result.total_commission
                    
                    # Update weighted average price
                    if total_filled > 0:
                        weighted_avg_price = (
                            (weighted_avg_price * (total_filled - slice_result.filled_quantity) +
                             slice_result.avg_fill_price * slice_result.filled_quantity) / total_filled
                        )
                
                # Wait for next slice time
                if i < num_slices - 1:
                    await asyncio.sleep(slice_interval_minutes * 60)
            
            # Execute remaining quantity if any
            if total_filled < order.quantity:
                remaining_qty = order.quantity - total_filled
                final_order = TradeOrder(
                    order_id=f"{order.order_id}_final",
                    symbol=order.symbol,
                    action=order.action,
                    quantity=remaining_qty,
                    order_type=OrderType.MARKET,
                    parent_order_id=order.order_id
                )
                
                final_result = await self._execute_aggressive(final_order, execution_plan)
                if final_result.success:
                    total_filled += final_result.filled_quantity
                    total_commission += final_result.total_commission
                    
                    if total_filled > 0:
                        weighted_avg_price = (
                            (weighted_avg_price * (total_filled - final_result.filled_quantity) +
                             final_result.avg_fill_price * final_result.filled_quantity) / total_filled
                        )
            
            # Calculate slippage
            market_price = execution_plan.get('market_data', {}).get('price', weighted_avg_price)
            slippage = abs(weighted_avg_price - market_price) / market_price if market_price > 0 else 0.0
            
            success = total_filled > 0
            
            return ExecutionResult(
                order_id=order.order_id,
                success=success,
                filled_quantity=total_filled,
                avg_fill_price=weighted_avg_price,
                total_commission=total_commission,
                execution_time=time.time() - start_time,
                slippage=slippage,
                market_impact=execution_plan.get('estimated_impact', 0.0),
                error_message=None if success else "TWAP execution failed"
            )
            
        except Exception as e:
            logger.error(f"Error in TWAP execution: {e}")
            return ExecutionResult(
                order_id=order.order_id,
                success=False,
                filled_quantity=0,
                avg_fill_price=0.0,
                total_commission=0.0,
                execution_time=time.time() - start_time,
                slippage=0.0,
                market_impact=0.0,
                error_message=str(e)
            )
    
    async def _execute_vwap(self, order: TradeOrder, execution_plan: Dict[str, Any]) -> ExecutionResult:
        """Execute order using Volume-Weighted Average Price strategy"""
        # For simplicity, using TWAP implementation
        # In production, this would use volume data to weight execution
        return await self._execute_twap(order, execution_plan)
    
    # Helper methods
    async def _execute_strategy_orders(self, strategy: TradeStrategy) -> bool:
        """Execute all orders in a strategy"""
        try:
            # Sort orders by priority (assuming orders are already prioritized)
            orders = strategy.orders.copy()
            
            # Execute orders sequentially or in parallel based on strategy type
            results = []
            
            for order in orders:
                result = await self.execute_order(order)
                results.append(result)
                
                # Stop if critical order fails
                if not result.success and order.urgency > 0.8:
                    logger.error(f"Critical order failed: {order.order_id}")
                    return False
            
            # Check overall success rate
            successful_orders = sum(1 for r in results if r.success)
            success_rate = successful_orders / len(results) if results else 0
            
            # Strategy succeeds if > 80% of orders succeed
            return success_rate > 0.8
            
        except Exception as e:
            logger.error(f"Error executing strategy orders: {e}")
            return False
    
    async def _is_market_open(self) -> bool:
        """Check if market is open"""
        try:
            # Simple market hours check (9:15 AM to 3:30 PM IST)
            now = datetime.now()
            market_open = now.replace(hour=9, minute=15, second=0, microsecond=0)
            market_close = now.replace(hour=15, minute=30, second=0, microsecond=0)
            
            # Check if it's a weekday
            if now.weekday() >= 5:  # Saturday = 5, Sunday = 6
                return False
            
            return market_open <= now <= market_close
            
        except Exception as e:
            logger.error(f"Error checking market hours: {e}")
            return False
    
    async def _check_position_limits(self, order: TradeOrder) -> bool:
        """Check position size limits"""
        try:
            current_positions = await self.dhan_connector.get_positions()
            
            # Calculate current exposure for symbol
            current_exposure = 0
            for position in current_positions.get('positions', []):
                if position.get('symbol') == order.symbol:
                    current_exposure += abs(position.get('quantity', 0)) * position.get('price', 0)
            
            # Calculate new exposure
            market_price = await self._get_market_price(order.symbol)
            new_exposure = order.quantity * market_price
            total_exposure = current_exposure + new_exposure
            
            # Check limits
            symbol_limit = self.position_size_limits.get(order.symbol, self.max_position_value * 0.1)
            
            return total_exposure <= symbol_limit
            
        except Exception as e:
            logger.error(f"Error checking position limits: {e}")
            return True  # Allow order if check fails
    
    async def _get_market_price(self, symbol: str) -> float:
        """Get current market price for symbol"""
        try:
            market_data = await self.dhan_connector.get_quotes([symbol])
            return market_data.get(symbol, {}).get('price', 0.0)
        except Exception as e:
            logger.error(f"Error getting market price for {symbol}: {e}")
            return 0.0
    
    async def _get_market_data(self, symbol: str) -> Dict[str, Any]:
        """Get comprehensive market data for symbol"""
        try:
            # Check cache first
            if symbol in self.market_data_cache:
                last_update = self.last_market_update.get(symbol, datetime.min)
                if datetime.now() - last_update < timedelta(seconds=30):
                    return self.market_data_cache[symbol]
            
            # Fetch fresh data
            quotes = await self.dhan_connector.get_quotes([symbol])
            market_data = quotes.get(symbol, {})
            
            # Cache the data
            self.market_data_cache[symbol] = market_data
            self.last_market_update[symbol] = datetime.now()
            
            return market_data
            
        except Exception as e:
            logger.error(f"Error getting market data for {symbol}: {e}")
            return {}
    
    async def _estimate_market_impact(self, order: TradeOrder, market_data: Dict[str, Any]) -> float:
        """Estimate market impact of order"""
        try:
            # Simple impact model based on order size vs average volume
            avg_volume = market_data.get('avg_volume', 1000000)
            order_value = order.quantity * market_data.get('price', 100)
            
            # Impact as percentage of order value vs daily volume
            volume_impact = (order_value / avg_volume) * 0.1  # 10% of volume ratio
            
            # Add liquidity impact
            bid_ask_spread = market_data.get('spread', 0.01)
            liquidity_impact = bid_ask_spread * 0.5
            
            total_impact = volume_impact + liquidity_impact
            return min(0.05, max(0.0001, total_impact))  # Cap between 0.01% and 5%
            
        except Exception as e:
            logger.error(f"Error estimating market impact: {e}")
            return 0.001  # Default 0.1% impact
    
    async def _choose_smart_algorithm(self, order: TradeOrder, market_data: Dict[str, Any], estimated_impact: float) -> ExecutionAlgorithm:
        """Choose optimal execution algorithm based on conditions"""
        try:
            # Factors to consider
            order_size = order.quantity
            avg_volume = market_data.get('avg_volume', 1000000)
            volatility = market_data.get('volatility', 0.02)
            spread = market_data.get('spread', 0.01)
            urgency = order.urgency
            
            # Calculate relative order size
            relative_size = order_size / avg_volume if avg_volume > 0 else 0.1
            
            # Decision logic
            if urgency > 0.8:
                return ExecutionAlgorithm.AGGRESSIVE
            elif relative_size > 0.1:  # Large order
                return ExecutionAlgorithm.ICEBERG
            elif spread > 0.02:  # Wide spread
                return ExecutionAlgorithm.PASSIVE
            elif volatility > 0.03:  # High volatility
                return ExecutionAlgorithm.TWAP
            else:
                return ExecutionAlgorithm.PASSIVE
                
        except Exception as e:
            logger.error(f"Error choosing smart algorithm: {e}")
            return ExecutionAlgorithm.AGGRESSIVE
    
    async def _calculate_optimal_chunk_size(self, order: TradeOrder, market_data: Dict[str, Any]) -> int:
        """Calculate optimal chunk size for iceberg orders"""
        try:
            avg_volume = market_data.get('avg_volume', 1000000)
            
            # Aim for chunks that are ~1% of daily volume
            optimal_chunk = int(avg_volume * 0.01)
            
            # Ensure chunk is reasonable size
            min_chunk = max(1, order.quantity // 20)  # Max 20 chunks
            max_chunk = order.quantity // 2          # Min 2 chunks
            
            return max(min_chunk, min(optimal_chunk, max_chunk))
            
        except Exception as e:
            logger.error(f"Error calculating chunk size: {e}")
            return max(1, order.quantity // 5)
    
    async def _get_timing_strategy(self, order: TradeOrder, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Get optimal timing strategy"""
        return {
            'immediate': order.urgency > 0.7,
            'spread_over_time': order.urgency < 0.3,
            'market_close_rush': False  # Would check time until market close
        }
    
    async def _get_price_strategy(self, order: TradeOrder, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Get optimal pricing strategy"""
        return {
            'aggressive_pricing': order.urgency > 0.8,
            'mid_point_pricing': 0.3 <= order.urgency <= 0.7,
            'passive_pricing': order.urgency < 0.3
        }
    
    async def _wait_for_fill(self, broker_order_id: str, timeout_seconds: int) -> Dict[str, Any]:
        """Wait for order to fill"""
        try:
            start_time = time.time()
            
            while time.time() - start_time < timeout_seconds:
                order_status = await self.dhan_connector.get_order_status(broker_order_id)
                
                if order_status.get('status') == 'COMPLETE':
                    return {
                        'filled': True,
                        'filled_quantity': order_status.get('filled_quantity', 0),
                        'avg_price': order_status.get('avg_price', 0.0),
                        'commission': order_status.get('commission', 0.0)
                    }
                elif order_status.get('status') in ['REJECTED', 'CANCELLED']:
                    return {'filled': False}
                
                await asyncio.sleep(1)  # Check every second
            
            return {'filled': False}  # Timeout
            
        except Exception as e:
            logger.error(f"Error waiting for fill: {e}")
            return {'filled': False}
    
    def _update_execution_stats(self, result: ExecutionResult) -> None:
        """Update execution statistics"""
        try:
            with self.lock:
                self.execution_stats['total_orders'] += 1
                
                if result.success:
                    self.execution_stats['successful_orders'] += 1
                
                # Update averages
                total = self.execution_stats['total_orders']
                
                # Execution time
                old_avg_time = self.execution_stats['avg_execution_time']
                self.execution_stats['avg_execution_time'] = (
                    (old_avg_time * (total - 1) + result.execution_time) / total
                )
                
                # Slippage
                old_avg_slippage = self.execution_stats['avg_slippage']
                self.execution_stats['avg_slippage'] = (
                    (old_avg_slippage * (total - 1) + result.slippage) / total
                )
                
                # Commission
                self.execution_stats['total_commission'] += result.total_commission
                
        except Exception as e:
            logger.error(f"Error updating execution stats: {e}")
    
    # Public methods for monitoring and control
    def get_active_orders(self) -> List[TradeOrder]:
        """Get list of active orders"""
        with self.lock:
            return list(self.active_orders.values())
    
    def get_active_strategies(self) -> List[TradeStrategy]:
        """Get list of active strategies"""
        with self.lock:
            return list(self.active_strategies.values())
    
    def get_execution_stats(self) -> Dict[str, Any]:
        """Get execution statistics"""
        with self.lock:
            stats = self.execution_stats.copy()
            stats['success_rate'] = (
                stats['successful_orders'] / stats['total_orders'] 
                if stats['total_orders'] > 0 else 0
            )
            return stats
    
    async def cancel_order(self, order_id: str) -> bool:
        """Cancel an active order"""
        try:
            with self.lock:
                if order_id not in self.active_orders:
                    return False
                
                order = self.active_orders[order_id]
            
            # Cancel with broker if submitted
            if hasattr(order, 'broker_order_id'):
                await self.dhan_connector.cancel_order(order.broker_order_id)
            
            # Update status
            with self.lock:
                order.status = OrderStatus.CANCELLED
                self.order_history.append(order)
                del self.active_orders[order_id]
            
            logger.info(f"Order {order_id} cancelled")
            return True
            
        except Exception as e:
            logger.error(f"Error cancelling order {order_id}: {e}")
            return False
    
    async def cancel_strategy(self, strategy_id: str) -> bool:
        """Cancel an active strategy"""
        try:
            with self.lock:
                if strategy_id not in self.active_strategies:
                    return False
                
                strategy = self.active_strategies[strategy_id]
            
            # Cancel all associated orders
            cancelled_orders = 0
            for order in strategy.orders:
                if await self.cancel_order(order.order_id):
                    cancelled_orders += 1
            
            # Update strategy status
            with self.lock:
                strategy.status = "cancelled"
                self.strategy_history.append(strategy)
                del self.active_strategies[strategy_id]
            
            logger.info(f"Strategy {strategy_id} cancelled, {cancelled_orders} orders cancelled")
            return True
            
        except Exception as e:
            logger.error(f"Error cancelling strategy {strategy_id}: {e}")
            return False

# Factory function
def create_trade_executor(config: Dict[str, Any], dhan_connector) -> TradeExecutor:
    """Factory function to create trade executor"""
    return TradeExecutor(config, dhan_connector)
