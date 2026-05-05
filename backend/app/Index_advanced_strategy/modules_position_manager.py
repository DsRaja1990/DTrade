"""
Position Manager for tracking and executing orders
"""
import logging
import uuid
from datetime import datetime, timedelta
import threading
import time
import json

logger = logging.getLogger(__name__)

class PositionManager:
    def __init__(self, api_connector):
        self.api = api_connector
        self.positions = {}  # All active positions
        self.strategy_positions = {}  # Positions grouped by strategy
        self.pending_orders = {}  # Orders that are pending execution
        self.filled_orders = {}  # Orders that have been filled
        self.position_history = []  # History of closed positions
        
        self.lock = threading.RLock()
        
        # Start position management thread
        self.managing = False
        self.management_thread = None
    
    def start_management(self):
        """Start position management thread"""
        if self.managing:
            return
            
        self.managing = True
        self.management_thread = threading.Thread(target=self._management_loop)
        self.management_thread.daemon = True
        self.management_thread.start()
        logger.info("Position management started")
    
    def stop_management(self):
        """Stop position management"""
        self.managing = False
        if self.management_thread:
            self.management_thread.join(timeout=5)
            self.management_thread = None
        logger.info("Position management stopped")
    
    def _management_loop(self):
        """Main position management loop"""
        while self.managing:
            try:
                # Sync positions with broker
                self._sync_positions()
                
                # Update order status
                self._update_order_status()
                
                # Manage existing positions
                self._manage_positions()
                
                # Sleep to prevent excessive API calls
                time.sleep(5)
            
            except Exception as e:
                logger.error(f"Error in position management loop: {e}", exc_info=True)
                time.sleep(10)  # Longer sleep on error
    
    def _sync_positions(self):
        """Synchronize positions with broker"""
        try:
            # Get positions from broker
            broker_positions = self.api.get_account_positions()
            
            if not broker_positions or 'data' not in broker_positions:
                return
            
            broker_positions = broker_positions['data']
            
            with self.lock:
                # Update positions based on broker data
                current_position_ids = set(self.positions.keys())
                broker_position_ids = set()
                
                for bp in broker_positions:
                    position_id = bp.get('exchange_order_id')
                    if not position_id:
                        continue
                        
                    broker_position_ids.add(position_id)
                    
                    if position_id in self.positions:
                        # Update existing position
                        self.positions[position_id].update({
                            'current_value': float(bp.get('market_value', 0)),
                            'quantity': int(bp.get('quantity', 0)),
                            'average_price': float(bp.get('average_price', 0)),
                            'pnl': float(bp.get('pnl', 0)),
                            'last_updated': datetime.now()
                        })
                    else:
                        # New position from broker not tracked by us
                        self.positions[position_id] = {
                            'position_id': position_id,
                            'instrument_id': bp.get('instrument_id'),
                            'symbol': bp.get('trading_symbol', ''),
                            'exchange': bp.get('exchange', ''),
                            'quantity': int(bp.get('quantity', 0)),
                            'average_price': float(bp.get('average_price', 0)),
                            'current_value': float(bp.get('market_value', 0)),
                            'pnl': float(bp.get('pnl', 0)),
                            'position_type': 'unknown',  # We don't know which strategy created this
                            'entry_time': datetime.now(),
                            'last_updated': datetime.now()
                        }
                
                # Remove positions that no longer exist at broker
                for position_id in current_position_ids - broker_position_ids:
                    # Position was closed at broker but we don't know about it
                    position = self.positions.pop(position_id, None)
                    if position:
                        # Move to history
                        position['exit_time'] = datetime.now()
                        self.position_history.append(position)
                        
                        # Remove from strategy positions
                        for strategy, positions in self.strategy_positions.items():
                            if position_id in positions:
                                positions.remove(position_id)
                
                # Update strategy position stats
                for strategy, position_ids in self.strategy_positions.items():
                    valid_position_ids = [pid for pid in position_ids if pid in self.positions]
                    self.strategy_positions[strategy] = valid_position_ids
        
        except Exception as e:
            logger.error(f"Error syncing positions: {e}", exc_info=True)
    
    def _update_order_status(self):
        """Update status of pending orders"""
        try:
            with self.lock:
                # Make a copy to avoid modifying during iteration
                pending_order_ids = list(self.pending_orders.keys())
            
            for order_id in pending_order_ids:
                try:
                    order_status = self.api.get_order_status(order_id)
                    
                    if not order_status or 'data' not in order_status:
                        continue
                    
                    order_data = order_status['data']
                    status = order_data.get('status', '')
                    
                    with self.lock:
                        if order_id in self.pending_orders:
                            # Update order status
                            self.pending_orders[order_id]['status'] = status
                            self.pending_orders[order_id]['last_updated'] = datetime.now()
                            
                            # If order is filled, move to filled orders
                            if status in ['COMPLETED', 'FILLED']:
                                order = self.pending_orders.pop(order_id)
                                self.filled_orders[order_id] = order
                                
                                # Update position if this created one
                                position_id = order.get('position_id')
                                if position_id and position_id in self.positions:
                                    self.positions[position_id]['order_filled'] = True
                                    self.positions[position_id]['fill_time'] = datetime.now()
                            
                            # If order is rejected or canceled, remove from pending
                            elif status in ['REJECTED', 'CANCELLED', 'CANCELED']:
                                order = self.pending_orders.pop(order_id)
                                
                                # Log the rejection
                                logger.warning(f"Order rejected or canceled: {order}")
                                
                                # Release allocated capital
                                strategy = order.get('strategy')
                                if strategy and 'allocated_capital' in order:
                                    # This would need a reference to the capital allocator
                                    pass
                
                except Exception as e:
                    logger.error(f"Error updating order status for {order_id}: {e}")
        
        except Exception as e:
            logger.error(f"Error in order status update: {e}", exc_info=True)
    
    def _manage_positions(self):
        """Manage existing positions based on their rules"""
        try:
            with self.lock:
                # Make a copy of position IDs to avoid modifying during iteration
                position_ids = list(self.positions.keys())
            
            for position_id in position_ids:
                try:
                    with self.lock:
                        if position_id not in self.positions:
                            continue
                            
                        position = self.positions[position_id]
                    
                    # Skip positions without management rules
                    if 'management_rules' not in position:
                        continue
                    
                    # Apply position management rules
                    self._apply_management_rules(position)
                
                except Exception as e:
                    logger.error(f"Error managing position {position_id}: {e}")
        
        except Exception as e:
            logger.error(f"Error in position management: {e}", exc_info=True)
    
    def _apply_management_rules(self, position):
        """Apply management rules to a position"""
        # Skip if position doesn't have necessary data
        if not position.get('order_filled', False) or not position.get('management_rules'):
            return
        
        position_id = position['position_id']
        rules = position['management_rules']
        current_price = self._get_current_price(position['instrument_id'])
        
        if not current_price:
            return
        
        # Calculate current P&L
        entry_price = position['average_price']
        quantity = position['quantity']
        position_direction = 1 if position.get('action', 'BUY') == 'BUY' else -1
        
        pnl_points = (current_price - entry_price) * position_direction
        pnl_percentage = pnl_points / entry_price
        
        # Check stop loss
        if 'stop_loss' in rules and pnl_percentage < -rules['stop_loss']:
            logger.info(f"Stop loss triggered for position {position_id}: {pnl_percentage:.1%}")
            self._close_position(position_id, "Stop loss triggered")
            return
        
        # Check profit target
        if 'profit_target' in rules and pnl_percentage > rules['profit_target']:
            logger.info(f"Profit target reached for position {position_id}: {pnl_percentage:.1%}")
            self._close_position(position_id, "Profit target reached")
            return
        
        # Check time stop
        if 'time_stop' in rules:
            time_held = (datetime.now() - position['entry_time']).total_seconds() / 3600  # hours
            if time_held > rules['time_stop']:
                logger.info(f"Time stop triggered for position {position_id}: {time_held:.1f} hours")
                self._close_position(position_id, "Time stop triggered")
                return
        
        # Check for trailing stop
        if 'trailing_stop' in rules:
            # Update high water mark
            if 'high_water_mark' not in position:
                position['high_water_mark'] = current_price if position_direction > 0 else -current_price
            else:
                hwm = position['high_water_mark']
                if (position_direction > 0 and current_price > hwm) or (position_direction < 0 and -current_price > hwm):
                    position['high_water_mark'] = current_price if position_direction > 0 else -current_price
            
            # Check if price has fallen below trailing stop level
            hwm = position['high_water_mark']
            trail_amount = hwm * rules['trailing_stop']
            
            if position_direction > 0:
                stop_level = hwm - trail_amount
                if current_price < stop_level:
                    logger.info(f"Trailing stop triggered for position {position_id}")
                    self._close_position(position_id, "Trailing stop triggered")
            else:
                stop_level = -hwm + trail_amount
                if -current_price < stop_level:
                    logger.info(f"Trailing stop triggered for position {position_id}")
                    self._close_position(position_id, "Trailing stop triggered")
    
    def execute_order(self, signal):
        """Execute a trading signal as an order"""
        try:
            # Generate a unique ID for this order
            order_id = str(uuid.uuid4())
            
            # Create order parameters
            if signal['action'] in ['BUY', 'SELL']:
                # Single-leg order
                order_params = {
                    'instrument_id': signal['instrument_id'],
                    'quantity': signal['quantity'],
                    'order_type': 'MARKET',  # Use market orders for simplicity
                    'side': signal['action'],
                    'product': 'MIS',  # Intraday
                    'validity': 'DAY'
                }
                
                # Place the order
                response = self.api.place_order(order_params)
                
                if not response or 'data' not in response or 'order_id' not in response['data']:
                    logger.error(f"Failed to place order: {response}")
                    return {'success': False, 'error': 'Failed to place order'}
                
                broker_order_id = response['data']['order_id']
                
                # Create position record
                position_id = broker_order_id
                
                position = {
                    'position_id': position_id,
                    'order_id': broker_order_id,
                    'signal': signal,
                    'instrument_id': signal['instrument_id'],
                    'symbol': signal['symbol'],
                    'quantity': signal['quantity'],
                    'action': signal['action'],
                    'strategy': signal['strategy'],
                    'entry_time': datetime.now(),
                    'average_price': signal.get('price', 0),
                    'current_value': 0,
                    'pnl': 0,
                    'order_filled': False,
                    'management_rules': signal.get('management_rules', {}),
                    'allocated_capital': signal.get('allocated_capital', 0)
                }
                
                # Track order
                order_record = {
                    'order_id': broker_order_id,
                    'client_order_id': order_id,
                    'position_id': position_id,
                    'instrument_id': signal['instrument_id'],
                    'symbol': signal['symbol'],
                    'quantity': signal['quantity'],
                    'action': signal['action'],
                    'strategy': signal['strategy'],
                    'time': datetime.now(),
                    'status': 'PENDING',
                    'last_updated': datetime.now(),
                    'allocated_capital': signal.get('allocated_capital', 0)
                }
                
                with self.lock:
                    # Store position and order records
                    self.positions[position_id] = position
                    self.pending_orders[broker_order_id] = order_record
                    
                    # Add to strategy positions
                    if signal['strategy'] not in self.strategy_positions:
                        self.strategy_positions[signal['strategy']] = []
                    self.strategy_positions[signal['strategy']].append(position_id)
                
                logger.info(f"Order placed: {broker_order_id} for {signal['symbol']}")
                
                return {'success': True, 'order_id': broker_order_id, 'position_id': position_id}
            
            elif signal['action'] in ['IRON_CONDOR', 'CALENDAR_SPREAD', 'SHORT_STRADDLE', 'LONG_STRANGLE']:
                # Multi-leg order
                position_id = str(uuid.uuid4())
                broker_order_ids = []
                
                # Place each leg as a separate order
                for leg in signal['legs']:
                    leg_order_params = {
                        'instrument_id': leg['instrument_id'],
                        'quantity': leg['quantity'],
                        'order_type': 'MARKET',
                        'side': leg['action'],
                        'product': 'MIS',
                        'validity': 'DAY'
                    }
                    
                    # Place the leg order
                    leg_response = self.api.place_order(leg_order_params)
                    
                    if not leg_response or 'data' not in leg_response or 'order_id' not in leg_response['data']:
                        logger.error(f"Failed to place leg order: {leg_response}")
                        # Should handle partial fills and cleanup here
                        return {'success': False, 'error': 'Failed to place multi-leg order'}
                    
                    broker_order_id = leg_response['data']['order_id']
                    broker_order_ids.append(broker_order_id)
                    
                    # Track each leg order
                    leg_order_record = {
                        'order_id': broker_order_id,
                        'client_order_id': f"{order_id}_{len(broker_order_ids)}",
                        'position_id': position_id,
                        'instrument_id': leg['instrument_id'],
                        'symbol': leg['symbol'],
                        'quantity': leg['quantity'],
                        'action': leg['action'],
                        'strategy': signal['strategy'],
                        'time': datetime.now(),
                        'status': 'PENDING',
                        'last_updated': datetime.now(),
                        'is_leg': True,
                        'parent_strategy': signal['action']
                    }
                    
                    with self.lock:
                        self.pending_orders[broker_order_id] = leg_order_record
                
                # Create position record for the entire strategy
                position = {
                    'position_id': position_id,
                    'order_ids': broker_order_ids,
                    'signal': signal,
                    'symbol': signal['underlying'],
                    'strategy': signal['strategy'],
                    'entry_time': datetime.now(),
                    'legs': signal['legs'],
                    'current_value': 0,
                    'pnl': 0,
                    'order_filled': False,
                    'management_rules': signal.get('management_rules', {}),
                    'allocated_capital': signal.get('allocated_capital', 0),
                    'position_type': signal['action']
                }
                
                with self.lock:
                    self.positions[position_id] = position
                    
                    # Add to strategy positions
                    if signal['strategy'] not in self.strategy_positions:
                        self.strategy_positions[signal['strategy']] = []
                    self.strategy_positions[signal['strategy']].append(position_id)
                
                logger.info(f"Multi-leg order placed: {position_id} for {signal['underlying']}")
                
                return {'success': True, 'position_id': position_id, 'order_ids': broker_order_ids}
            
            else:
                logger.error(f"Unsupported order action: {signal['action']}")
                return {'success': False, 'error': f"Unsupported order action: {signal['action']}"}
        
        except Exception as e:
            logger.error(f"Error executing order: {e}", exc_info=True)
            return {'success': False, 'error': str(e)}
    
    def _close_position(self, position_id, reason):
        """Close a position"""
        try:
            with self.lock:
                if position_id not in self.positions:
                    logger.warning(f"Cannot close position {position_id}: not found")
                    return False
                
                position = self.positions[position_id]
            
            # For multi-leg strategies, close each leg
            if position.get('position_type') in ['IRON_CONDOR', 'CALENDAR_SPREAD', 'SHORT_STRADDLE', 'LONG_STRANGLE']:
                for leg in position.get('legs', []):
                    # Create opposite action
                    opposite_action = 'BUY' if leg['action'] == 'SELL' else 'SELL'
                    
                    # Create order parameters
                    order_params = {
                        'instrument_id': leg['instrument_id'],
                        'quantity': leg['quantity'],
                        'order_type': 'MARKET',
                        'side': opposite_action,
                        'product': 'MIS',
                        'validity': 'DAY'
                    }
                    
                    # Place the closing order
                    response = self.api.place_order(order_params)
                    
                    if not response or 'data' not in response or 'order_id' not in response['data']:
                        logger.error(f"Failed to close leg: {response}")
                        # Continue with other legs
                    else:
                        logger.info(f"Closed leg for position {position_id}")
            
            else:
                # Single-leg position
                # Create opposite action
                action = position.get('action', 'BUY')
                opposite_action = 'SELL' if action == 'BUY' else 'BUY'
                
                # Create order parameters
                order_params = {
                    'instrument_id': position['instrument_id'],
                    'quantity': position['quantity'],
                    'order_type': 'MARKET',
                    'side': opposite_action,
                    'product': 'MIS',
                    'validity': 'DAY'
                }
                
                # Place the closing order
                response = self.api.place_order(order_params)
                
                if not response or 'data' not in response or 'order_id' not in response['data']:
                    logger.error(f"Failed to close position: {response}")
                    return False
                
                logger.info(f"Closed position {position_id}: {reason}")
            
            with self.lock:
                # Mark position as closing
                if position_id in self.positions:
                    self.positions[position_id]['closing'] = True
                    self.positions[position_id]['closing_reason'] = reason
                    self.positions[position_id]['closing_time'] = datetime.now()
            
            return True
        
        except Exception as e:
            logger.error(f"Error closing position {position_id}: {e}", exc_info=True)
            return False
    
    def close_all_positions(self):
        """Close all open positions"""
        try:
            with self.lock:
                position_ids = list(self.positions.keys())
            
            for position_id in position_ids:
                self._close_position(position_id, "Closing all positions")
            
            return True
        
        except Exception as e:
            logger.error(f"Error closing all positions: {e}", exc_info=True)
            return False
    
    def get_positions_by_strategy(self, strategy):
        """Get all positions for a specific strategy"""
        with self.lock:
            position_ids = self.strategy_positions.get(strategy, [])
            return [self.positions[pid] for pid in position_ids if pid in self.positions]
    
    def get_all_positions(self):
        """Get all current positions"""
        with self.lock:
            return list(self.positions.values())
    
    def get_position_history(self):
        """Get history of closed positions"""
        with self.lock:
            return self.position_history
    
    def get_account_value(self):
        """Get current account value"""
        try:
            account = self.api.get_account_balance()
            # Extract and return account value
            if account and 'data' in account and 'available_cash' in account['data']:
                return float(account['data']['available_cash'])
        except Exception as e:
            logger.error(f"Error getting account value: {e}")
        
        return 0
    
    def _get_current_price(self, instrument_id):
        """Get current price for an instrument"""
        try:
            quote = self.api.get_quote(instrument_id)
            if quote and 'last_price' in quote:
                return quote['last_price']
        except Exception as e:
            logger.error(f"Error getting current price: {e}")
        
        return None
    
    def register_strategy_position(self, position):
        """Register a new strategy position for management"""
        try:
            position_id = position.get('order_details', {}).get('position_id')
            if not position_id:
                logger.error("Cannot register position without position_id")
                return False
            
            strategy = position.get('strategy')
            
            with self.lock:
                # Update position if it exists
                if position_id in self.positions:
                    self.positions[position_id].update(position)
                else:
                    # Create new position
                    self.positions[position_id] = position
                
                # Add to strategy positions
                if strategy:
                    if strategy not in self.strategy_positions:
                        self.strategy_positions[strategy] = []
                    if position_id not in self.strategy_positions[strategy]:
                        self.strategy_positions[strategy].append(position_id)
            
            return True
        
        except Exception as e:
            logger.error(f"Error registering strategy position: {e}", exc_info=True)
            return False