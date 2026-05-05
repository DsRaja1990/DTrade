"""
Execution Simulator for Backtesting

This module simulates realistic order execution with market microstructure effects.
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum
import logging

logger = logging.getLogger(__name__)

class OrderType(Enum):
    MARKET = "market"
    LIMIT = "limit"
    ICEBERG = "iceberg"
    VWAP = "vwap"
    TWAP = "twap"

@dataclass
class OrderExecution:
    """Result of order execution simulation"""
    executed_quantity: int
    avg_execution_price: float
    total_cost: float
    market_impact: float
    timing_cost: float
    commission: float
    execution_time: float
    slippage_bps: float
    fill_rate: float

class ExecutionSimulator:
    """
    Realistic execution simulator that accounts for:
    - Market impact
    - Timing costs
    - Partial fills
    - Execution delays
    - Commission costs
    """

    def __init__(self):
        self.commission_rates = {
            "NIFTY": 20.0,      # ₹20 per lot
            "BANKNIFTY": 25.0,  # ₹25 per lot
            "SENSEX": 22.0      # ₹22 per lot
        }
        
        self.exchange_fees = {
            "NIFTY": 0.0005,    # 0.05% of turnover
            "BANKNIFTY": 0.0005,
            "SENSEX": 0.0005
        }

    async def simulate_order_execution(self,
                                     instrument: str,
                                     order_type: OrderType,
                                     quantity: int,
                                     target_price: float,
                                     market_data: pd.DataFrame,
                                     execution_start: datetime,
                                     execution_end: Optional[datetime] = None) -> OrderExecution:
        """
        Simulate realistic order execution
        
        Args:
            instrument: Trading instrument
            order_type: Type of order execution
            quantity: Number of lots to execute
            target_price: Target execution price
            market_data: Market data during execution period
            execution_start: Start time for execution
            execution_end: End time for execution (for VWAP/TWAP)
            
        Returns:
            OrderExecution result with all execution details
        """
        
        if order_type == OrderType.MARKET:
            return await self._simulate_market_order(
                instrument, quantity, target_price, market_data, execution_start
            )
        elif order_type == OrderType.ICEBERG:
            return await self._simulate_iceberg_order(
                instrument, quantity, target_price, market_data, execution_start
            )
        elif order_type == OrderType.VWAP:
            return await self._simulate_vwap_order(
                instrument, quantity, target_price, market_data, execution_start, execution_end
            )
        elif order_type == OrderType.TWAP:
            return await self._simulate_twap_order(
                instrument, quantity, target_price, market_data, execution_start, execution_end
            )
        else:
            return await self._simulate_limit_order(
                instrument, quantity, target_price, market_data, execution_start
            )

    async def _simulate_market_order(self,
                                   instrument: str,
                                   quantity: int,
                                   target_price: float,
                                   market_data: pd.DataFrame,
                                   execution_time: datetime) -> OrderExecution:
        """Simulate immediate market order execution"""
        
        # Find closest market data point
        execution_data = self._get_execution_data(market_data, execution_time)
        
        if execution_data is None:
            # No market data available - assume failed execution
            return OrderExecution(
                executed_quantity=0,
                avg_execution_price=0.0,
                total_cost=0.0,
                market_impact=0.0,
                timing_cost=0.0,
                commission=0.0,
                execution_time=0.0,
                slippage_bps=0.0,
                fill_rate=0.0
            )
        
        market_price = execution_data['price']
        volume = execution_data['volume']
        
        # Calculate market impact based on order size vs available volume
        volume_participation = min(quantity / max(volume, 1), 0.5)  # Max 50% participation
        
        # Market impact model (square root law)
        base_impact = self._get_base_impact(instrument)
        market_impact = base_impact * np.sqrt(volume_participation) * 1.5  # Market orders have higher impact
        
        # Apply market impact to execution price
        execution_price = market_price * (1 + market_impact)
        
        # Simulate execution time (market orders are fast)
        execution_time_seconds = np.random.uniform(0.5, 2.0)
        
        # Calculate costs
        total_cost = self._calculate_total_cost(instrument, quantity, execution_price)
        commission = self._calculate_commission(instrument, quantity, execution_price)
        
        # Calculate slippage vs target price
        slippage_bps = abs(execution_price - target_price) / target_price * 10000
        
        return OrderExecution(
            executed_quantity=quantity,
            avg_execution_price=execution_price,
            total_cost=total_cost,
            market_impact=market_impact * 10000,  # in bps
            timing_cost=0.0,  # No timing cost for immediate execution
            commission=commission,
            execution_time=execution_time_seconds,
            slippage_bps=slippage_bps,
            fill_rate=1.0  # Market orders typically fill completely
        )

    async def _simulate_iceberg_order(self,
                                    instrument: str,
                                    quantity: int,
                                    target_price: float,
                                    market_data: pd.DataFrame,
                                    execution_start: datetime) -> OrderExecution:
        """Simulate iceberg order execution with hidden quantity"""
        
        # Iceberg parameters
        visible_size = min(5, quantity)  # Show max 5 lots at a time
        child_orders = []
        total_executed = 0
        total_cost = 0.0
        execution_times = []
        
        # Execute in chunks
        remaining_quantity = quantity
        current_time = execution_start
        
        while remaining_quantity > 0 and total_executed < quantity:
            chunk_size = min(visible_size, remaining_quantity)
            
            # Get market data for current time
            execution_data = self._get_execution_data(market_data, current_time)
            
            if execution_data is None:
                break
            
            market_price = execution_data['price']
            volume = execution_data['volume']
            
            # Check if we can execute at favorable price
            price_tolerance = 0.001  # 0.1% tolerance
            if abs(market_price - target_price) / target_price <= price_tolerance:
                
                # Calculate execution for this chunk
                volume_participation = chunk_size / max(volume, 1)
                base_impact = self._get_base_impact(instrument)
                chunk_impact = base_impact * np.sqrt(volume_participation) * 0.8  # Lower impact due to hidden size
                
                execution_price = market_price * (1 + chunk_impact)
                
                # Record execution
                child_orders.append({
                    'quantity': chunk_size,
                    'price': execution_price,
                    'time': current_time
                })
                
                total_executed += chunk_size
                remaining_quantity -= chunk_size
                total_cost += chunk_size * execution_price
                
                # Random delay between chunks (anti-gaming)
                delay_seconds = np.random.uniform(5, 15)
                execution_times.append(delay_seconds)
                
                current_time += timedelta(seconds=delay_seconds)
            else:
                # Price moved away, wait for better opportunity
                current_time += timedelta(minutes=1)
            
            # Safety break - don't execute forever
            if (current_time - execution_start).total_seconds() > 1800:  # 30 minutes max
                break
        
        if total_executed > 0:
            avg_execution_price = total_cost / total_executed
            total_execution_time = sum(execution_times)
            commission = self._calculate_commission(instrument, total_executed, avg_execution_price)
            total_cost_with_commission = self._calculate_total_cost(instrument, total_executed, avg_execution_price)
            
            # Calculate overall market impact
            overall_impact = (avg_execution_price - target_price) / target_price
            slippage_bps = abs(overall_impact) * 10000
            
            return OrderExecution(
                executed_quantity=total_executed,
                avg_execution_price=avg_execution_price,
                total_cost=total_cost_with_commission,
                market_impact=abs(overall_impact) * 10000,
                timing_cost=0.0,
                commission=commission,
                execution_time=total_execution_time,
                slippage_bps=slippage_bps,
                fill_rate=total_executed / quantity
            )
        else:
            # Failed to execute
            return OrderExecution(
                executed_quantity=0,
                avg_execution_price=0.0,
                total_cost=0.0,
                market_impact=0.0,
                timing_cost=0.0,
                commission=0.0,
                execution_time=0.0,
                slippage_bps=0.0,
                fill_rate=0.0
            )

    async def _simulate_vwap_order(self,
                                 instrument: str,
                                 quantity: int,
                                 target_price: float,
                                 market_data: pd.DataFrame,
                                 execution_start: datetime,
                                 execution_end: datetime) -> OrderExecution:
        """Simulate VWAP order execution"""
        
        # Get execution window data
        window_data = market_data[
            (market_data.index >= execution_start) & 
            (market_data.index <= execution_end)
        ]
        
        if window_data.empty:
            return OrderExecution(
                executed_quantity=0, avg_execution_price=0.0, total_cost=0.0,
                market_impact=0.0, timing_cost=0.0, commission=0.0,
                execution_time=0.0, slippage_bps=0.0, fill_rate=0.0
            )
        
        # Calculate theoretical VWAP
        theoretical_vwap = (window_data['price'] * window_data['volume']).sum() / window_data['volume'].sum()
        
        # Simulate execution across the window
        total_volume = window_data['volume'].sum()
        executions = []
        total_executed = 0
        
        for timestamp, row in window_data.iterrows():
            if total_executed >= quantity:
                break
            
            # Determine execution size based on volume participation
            target_participation = 0.15  # 15% volume participation
            available_quantity = int(row['volume'] * target_participation)
            
            execution_quantity = min(
                available_quantity,
                quantity - total_executed,
                max(1, quantity // len(window_data))  # Spread execution evenly
            )
            
            if execution_quantity > 0:
                # Price improvement vs theoretical VWAP
                vwap_tolerance = 0.0002  # 0.02% tolerance
                execution_price = theoretical_vwap * (1 + np.random.uniform(-vwap_tolerance, vwap_tolerance))
                
                executions.append({
                    'quantity': execution_quantity,
                    'price': execution_price,
                    'timestamp': timestamp
                })
                
                total_executed += execution_quantity
        
        if executions:
            # Calculate weighted average execution price
            total_cost = sum(ex['quantity'] * ex['price'] for ex in executions)
            avg_execution_price = total_cost / total_executed
            
            # Calculate metrics
            commission = self._calculate_commission(instrument, total_executed, avg_execution_price)
            total_cost_with_commission = self._calculate_total_cost(instrument, total_executed, avg_execution_price)
            
            # VWAP execution typically has low market impact
            market_impact = abs(avg_execution_price - theoretical_vwap) / theoretical_vwap * 10000
            
            # Timing cost (execution price vs target price)
            timing_cost = abs(avg_execution_price - target_price) / target_price * 10000
            
            execution_time = (execution_end - execution_start).total_seconds()
            slippage_bps = abs(avg_execution_price - target_price) / target_price * 10000
            
            return OrderExecution(
                executed_quantity=total_executed,
                avg_execution_price=avg_execution_price,
                total_cost=total_cost_with_commission,
                market_impact=market_impact,
                timing_cost=timing_cost,
                commission=commission,
                execution_time=execution_time,
                slippage_bps=slippage_bps,
                fill_rate=total_executed / quantity
            )
        else:
            return OrderExecution(
                executed_quantity=0, avg_execution_price=0.0, total_cost=0.0,
                market_impact=0.0, timing_cost=0.0, commission=0.0,
                execution_time=0.0, slippage_bps=0.0, fill_rate=0.0
            )

    async def _simulate_twap_order(self,
                                 instrument: str,
                                 quantity: int,
                                 target_price: float,
                                 market_data: pd.DataFrame,
                                 execution_start: datetime,
                                 execution_end: datetime) -> OrderExecution:
        """Simulate TWAP order execution"""
        
        # Get execution window data
        window_data = market_data[
            (market_data.index >= execution_start) & 
            (market_data.index <= execution_end)
        ]
        
        if window_data.empty:
            return OrderExecution(
                executed_quantity=0, avg_execution_price=0.0, total_cost=0.0,
                market_impact=0.0, timing_cost=0.0, commission=0.0,
                execution_time=0.0, slippage_bps=0.0, fill_rate=0.0
            )
        
        # Spread execution evenly across time
        n_intervals = min(len(window_data), 20)  # Max 20 execution points
        interval_size = len(window_data) // n_intervals
        quantity_per_interval = quantity // n_intervals
        
        executions = []
        total_executed = 0
        
        for i in range(0, len(window_data), interval_size):
            if total_executed >= quantity:
                break
            
            interval_data = window_data.iloc[i:i+interval_size]
            if interval_data.empty:
                continue
            
            # Execute at average price of interval
            interval_avg_price = interval_data['price'].mean()
            
            # Determine execution quantity
            remaining_quantity = quantity - total_executed
            execution_quantity = min(quantity_per_interval, remaining_quantity)
            
            if execution_quantity > 0:
                # Small random price improvement/deterioration
                price_noise = np.random.normal(0, 0.0001)  # 0.01% noise
                execution_price = interval_avg_price * (1 + price_noise)
                
                executions.append({
                    'quantity': execution_quantity,
                    'price': execution_price,
                    'timestamp': interval_data.index[0]
                })
                
                total_executed += execution_quantity
        
        if executions:
            # Calculate metrics
            total_cost = sum(ex['quantity'] * ex['price'] for ex in executions)
            avg_execution_price = total_cost / total_executed
            
            commission = self._calculate_commission(instrument, total_executed, avg_execution_price)
            total_cost_with_commission = self._calculate_total_cost(instrument, total_executed, avg_execution_price)
            
            # TWAP typically has minimal market impact
            theoretical_twap = window_data['price'].mean()
            market_impact = abs(avg_execution_price - theoretical_twap) / theoretical_twap * 10000
            
            timing_cost = abs(avg_execution_price - target_price) / target_price * 10000
            execution_time = (execution_end - execution_start).total_seconds()
            slippage_bps = timing_cost
            
            return OrderExecution(
                executed_quantity=total_executed,
                avg_execution_price=avg_execution_price,
                total_cost=total_cost_with_commission,
                market_impact=market_impact,
                timing_cost=timing_cost,
                commission=commission,
                execution_time=execution_time,
                slippage_bps=slippage_bps,
                fill_rate=total_executed / quantity
            )
        else:
            return OrderExecution(
                executed_quantity=0, avg_execution_price=0.0, total_cost=0.0,
                market_impact=0.0, timing_cost=0.0, commission=0.0,
                execution_time=0.0, slippage_bps=0.0, fill_rate=0.0
            )

    async def _simulate_limit_order(self,
                                  instrument: str,
                                  quantity: int,
                                  target_price: float,
                                  market_data: pd.DataFrame,
                                  execution_start: datetime) -> OrderExecution:
        """Simulate limit order execution"""
        
        # Look for opportunities to execute at or better than target price
        execution_window = timedelta(minutes=30)  # 30 minute window
        end_time = execution_start + execution_window
        
        window_data = market_data[
            (market_data.index >= execution_start) & 
            (market_data.index <= end_time)
        ]
        
        total_executed = 0
        executions = []
        
        for timestamp, row in window_data.iterrows():
            if total_executed >= quantity:
                break
            
            # Check if market price touches our limit price
            market_price = row['price']
            
            # For sell orders, execute when market price >= limit price
            if market_price >= target_price:
                # Determine fill quantity based on volume
                available_volume = row['volume']
                max_fill = min(quantity - total_executed, available_volume // 10)  # Conservative fill rate
                
                if max_fill > 0:
                    # Price improvement probability
                    improvement_prob = 0.3
                    if np.random.random() < improvement_prob:
                        execution_price = target_price * (1 + np.random.uniform(0, 0.0005))
                    else:
                        execution_price = target_price
                    
                    executions.append({
                        'quantity': max_fill,
                        'price': execution_price,
                        'timestamp': timestamp
                    })
                    
                    total_executed += max_fill
        
        if executions:
            total_cost = sum(ex['quantity'] * ex['price'] for ex in executions)
            avg_execution_price = total_cost / total_executed
            
            commission = self._calculate_commission(instrument, total_executed, avg_execution_price)
            total_cost_with_commission = self._calculate_total_cost(instrument, total_executed, avg_execution_price)
            
            # Limit orders typically have negative market impact (price improvement)
            market_impact = (avg_execution_price - target_price) / target_price * 10000
            
            execution_time = (executions[-1]['timestamp'] - execution_start).total_seconds()
            slippage_bps = abs(market_impact)
            
            return OrderExecution(
                executed_quantity=total_executed,
                avg_execution_price=avg_execution_price,
                total_cost=total_cost_with_commission,
                market_impact=abs(market_impact),
                timing_cost=0.0,  # No timing cost for limit orders
                commission=commission,
                execution_time=execution_time,
                slippage_bps=slippage_bps,
                fill_rate=total_executed / quantity
            )
        else:
            # Order didn't fill
            return OrderExecution(
                executed_quantity=0, avg_execution_price=0.0, total_cost=0.0,
                market_impact=0.0, timing_cost=0.0, commission=0.0,
                execution_time=execution_window.total_seconds(), slippage_bps=0.0, fill_rate=0.0
            )

    def _get_execution_data(self, market_data: pd.DataFrame, execution_time: datetime) -> Optional[pd.Series]:
        """Get market data closest to execution time"""
        
        if market_data.empty:
            return None
        
        # Find closest timestamp
        time_diffs = abs(market_data.index - execution_time)
        closest_idx = time_diffs.argmin()
        
        # Only use data within 5 minutes
        if time_diffs.iloc[closest_idx] <= timedelta(minutes=5):
            return market_data.iloc[closest_idx]
        else:
            return None

    def _get_base_impact(self, instrument: str) -> float:
        """Get base market impact for instrument"""
        return {
            "NIFTY": 0.0002,     # 0.02%
            "BANKNIFTY": 0.0003, # 0.03%
            "SENSEX": 0.0002     # 0.02%
        }.get(instrument, 0.0002)

    def _calculate_commission(self, instrument: str, quantity: int, price: float) -> float:
        """Calculate commission costs"""
        
        # Per-lot commission
        per_lot_commission = self.commission_rates[instrument]
        
        # Exchange fees (percentage of turnover)
        turnover = quantity * price
        exchange_fees = turnover * self.exchange_fees[instrument]
        
        # STT (Securities Transaction Tax) - 0.125% for options
        stt = turnover * 0.00125
        
        # GST on brokerage (18%)
        gst = per_lot_commission * quantity * 0.18
        
        total_commission = (per_lot_commission * quantity) + exchange_fees + stt + gst
        
        return total_commission

    def _calculate_total_cost(self, instrument: str, quantity: int, price: float) -> float:
        """Calculate total cost including all charges"""
        
        gross_cost = quantity * price
        commission = self._calculate_commission(instrument, quantity, price)
        
        return gross_cost + commission

    def get_execution_statistics(self, executions: List[OrderExecution]) -> Dict[str, float]:
        """Calculate aggregate execution statistics"""
        
        if not executions:
            return {}
        
        total_quantity = sum(ex.executed_quantity for ex in executions)
        total_cost = sum(ex.total_cost for ex in executions)
        
        if total_quantity == 0:
            return {}
        
        weighted_avg_price = total_cost / total_quantity
        avg_market_impact = np.mean([ex.market_impact for ex in executions])
        avg_slippage = np.mean([ex.slippage_bps for ex in executions])
        avg_execution_time = np.mean([ex.execution_time for ex in executions])
        avg_fill_rate = np.mean([ex.fill_rate for ex in executions])
        
        return {
            "total_quantity": total_quantity,
            "weighted_avg_price": weighted_avg_price,
            "avg_market_impact_bps": avg_market_impact,
            "avg_slippage_bps": avg_slippage,
            "avg_execution_time_seconds": avg_execution_time,
            "avg_fill_rate": avg_fill_rate,
            "total_commission": sum(ex.commission for ex in executions)
        }
