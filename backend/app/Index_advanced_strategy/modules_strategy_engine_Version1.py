"""
Strategy Engine implementing multiple sophisticated trading strategies
"""
import logging
import threading
import time
import numpy as np
import pandas as pd
from datetime import datetime, time as dt_time
from queue import Queue
import json
import copy

logger = logging.getLogger(__name__)

class StrategyEngine:
    def __init__(self, api_connector, market_data, risk_manager, position_manager, capital_allocator):
        self.api = api_connector
        self.market_data = market_data
        self.risk_manager = risk_manager
        self.position_manager = position_manager
        self.capital_allocator = capital_allocator
        
        self.strategies = []
        self.signal_queue = Queue()
        self.executing = False
        self.lock = threading.RLock()
        
        # Initialize strategy registry
        self._register_strategies()
        
        # Strategy execution thread
        self.execution_thread = None
        
        # Strategy parameters
        self.params = self._load_strategy_parameters()
    
    def _load_strategy_parameters(self):
        """Load strategy parameters"""
        # In a real system, these would be loaded from a config file or database
        return {
            'volatility_arbitrage': {
                'min_iv_percentile': 80,            # Minimum IV percentile to trigger entry
                'max_iv_percentile': 95,            # Maximum IV percentile to consider
                'min_strike_distance': 0.5,         # Minimum distance from ATM as % of spot
                'max_strike_distance': 2.0,         # Maximum distance from ATM as % of spot
                'days_to_expiry': [3, 10],          # Range of days to expiry
                'position_sizing': 0.15,            # Position size as % of capital
                'stop_loss': 0.3,                   # Stop loss as % of premium
                'profit_target': 0.4,               # Profit target as % of premium
                'vix_threshold': 18                 # Minimum VIX level
            },
            'gamma_scalper': {
                'min_gamma': 0.05,                  # Minimum gamma exposure
                'max_gamma': 0.15,                  # Maximum gamma exposure
                'hedge_interval': 0.5,              # Spot move % to trigger hedge
                'position_sizing': 0.1,             # Position size as % of capital
                'min_theta': 0.001,                 # Minimum theta exposure
                'min_days_to_expiry': 1,            # Minimum days to expiry
                'max_days_to_expiry': 5             # Maximum days to expiry
            },
            'mean_reversion': {
                'lookback_period': 20,              # Lookback period for mean calculation
                'entry_threshold': 2.0,             # Standard deviations from mean to enter
                'exit_threshold': 0.5,              # Standard deviations from mean to exit
                'position_sizing': 0.2,             # Position size as % of capital
                'stop_loss': 1.5,                   # Stop loss as % of position
                'max_positions': 3                  # Maximum number of concurrent positions
            },
            'event_momentum': {
                'pre_event_window': 2,              # Days before event
                'post_event_window': 3,             # Days after event
                'momentum_threshold': 1.5,          # Momentum threshold (z-score)
                'position_sizing': 0.15,            # Position size as % of capital
                'stop_loss': 2.0,                   # Stop loss as % of position
                'profit_target': 3.0,               # Profit target as % of position
                'max_positions': 2                  # Maximum number of concurrent positions
            },
            'options_chain_imbalance': {
                'min_pcr_entry': 0.7,               # Minimum put-call ratio for bullish entry
                'max_pcr_entry': 1.5,               # Maximum put-call ratio for bearish entry
                'min_volume': 100000,               # Minimum option volume
                'min_oi_change': 0.15,              # Minimum OI change % for significance
                'position_sizing': 0.12,            # Position size as % of capital
                'stop_loss': 0.3,                   # Stop loss as % of premium
                'profit_target': 0.5                # Profit target as % of premium
            },
            'vix_regime_switch': {
                'vix_low_threshold': 15,            # VIX low threshold
                'vix_high_threshold': 25,           # VIX high threshold
                'vix_extreme_threshold': 35,        # VIX extreme threshold
                'vix_ma_period': 10,                # VIX moving average period
                'position_sizing': {
                    'low': 0.08,                    # Position size in low VIX regime
                    'medium': 0.15,                 # Position size in medium VIX regime
                    'high': 0.05,                   # Position size in high VIX regime
                    'extreme': 0.02                 # Position size in extreme VIX regime
                }
            },
            'calendar_spread': {
                'min_iv_skew': 3.0,                 # Minimum IV skew between months
                'position_sizing': 0.15,            # Position size as % of capital
                'stop_loss': 0.25,                  # Stop loss as % of premium
                'profit_target': 0.4,               # Profit target as % of premium
                'max_positions': 2                  # Maximum number of concurrent positions
            },
            'dynamic_iron_condor': {
                'width_factor': 1.5,                # Width of wings as factor of ATR
                'iv_rank_min': 40,                  # Minimum IV rank for entry
                'days_to_expiry': [15, 45],         # Range of days to expiry
                'position_sizing': 0.1,             # Position size as % of capital
                'stop_loss': 1.5,                   # Stop loss as multiple of credit received
                'profit_target': 0.5,               # Profit target as % of max profit
                'adjustment_threshold': 0.15        # Move % to trigger adjustment
            },
            'implied_vs_realized_vol': {
                'lookback_period': 30,              # Lookback for realized volatility
                'iv_vs_rv_threshold': 1.3,          # Implied/Realized vol ratio threshold
                'position_sizing': 0.15,            # Position size as % of capital
                'min_days_to_expiry': 20,           # Minimum days to expiry
                'max_days_to_expiry': 60,           # Maximum days to expiry
                'stop_loss': 0.3,                   # Stop loss as % of premium
                'profit_target': 0.4                # Profit target as % of premium
            }
        }
    
    def _register_strategies(self):
        """Register all trading strategies"""
        self.strategies = [
            {
                'name': 'volatility_arbitrage',
                'type': 'options',
                'execute_func': self._execute_volatility_arbitrage,
                'description': 'Exploits mispricing in implied volatility across the option chain',
                'enabled': True
            },
            {
                'name': 'gamma_scalper',
                'type': 'options',
                'execute_func': self._execute_gamma_scalping,
                'description': 'Uses gamma exposure to scalp profits through dynamic hedging',
                'enabled': True
            },
            {
                'name': 'mean_reversion',
                'type': 'equity',
                'execute_func': self._execute_mean_reversion,
                'description': 'Takes advantage of temporary price deviations from statistical norms',
                'enabled': True
            },
            {
                'name': 'event_momentum',
                'type': 'event',
                'execute_func': self._execute_event_momentum,
                'description': 'Captures price momentum around significant market events',
                'enabled': True
            },
            {
                'name': 'options_chain_imbalance',
                'type': 'options',
                'execute_func': self._execute_options_chain_imbalance,
                'description': 'Exploits supply/demand imbalances in the options chain',
                'enabled': True
            },
            {
                'name': 'vix_regime_switch',
                'type': 'volatility',
                'execute_func': self._execute_vix_regime_switch,
                'description': 'Adapts strategy based on volatility regime changes',
                'enabled': True
            },
            {
                'name': 'calendar_spread',
                'type': 'options',
                'execute_func': self._execute_calendar_spread,
                'description': 'Exploits term structure of implied volatility',
                'enabled': True
            },
            {
                'name': 'dynamic_iron_condor',
                'type': 'options',
                'execute_func': self._execute_dynamic_iron_condor,
                'description': 'Creates dynamic income strategy with adjustable wings',
                'enabled': True
            },
            {
                'name': 'implied_vs_realized_vol',
                'type': 'volatility',
                'execute_func': self._execute_implied_vs_realized_vol,
                'description': 'Exploits difference between implied and realized volatility',
                'enabled': True
            }
        ]
        
        logger.info(f"Registered {len(self.strategies)} strategies")
    
    def start(self):
        """Start the strategy engine"""
        if self.execution_thread is not None and self.execution_thread.is_alive():
            logger.warning("Strategy engine is already running")
            return False
        
        self.executing = True
        self.execution_thread = threading.Thread(target=self._execution_loop)
        self.execution_thread.daemon = True
        self.execution_thread.start()
        logger.info("Strategy engine started")
        return True
    
    def stop(self):
        """Stop the strategy engine"""
        self.executing = False
        if self.execution_thread is not None:
            self.execution_thread.join(timeout=10)
        logger.info("Strategy engine stopped")
    
    def execute_strategies(self):
        """Execute all enabled strategies"""
        with self.lock:
            for strategy in self.strategies:
                if not strategy['enabled']:
                    continue
                
                try:
                    # Execute strategy and get signals
                    signals = strategy['execute_func']()
                    
                    if signals:
                        for signal in signals:
                            # Add strategy name to signal
                            signal['strategy'] = strategy['name']
                            # Queue the signal for execution
                            self.signal_queue.put(signal)
                            logger.info(f"Generated signal: {strategy['name']} - {signal['action']} {signal['symbol']}")
                
                except Exception as e:
                    logger.error(f"Error executing strategy {strategy['name']}: {e}", exc_info=True)
    
    def _execution_loop(self):
        """Main execution loop for processing signals"""
        logger.info("Starting strategy execution loop")
        
        while self.executing:
            try:
                # Check if we have any signals to process
                while not self.signal_queue.empty():
                    signal = self.signal_queue.get()
                    
                    # Check if we can take this trade (risk, capital, etc.)
                    if self._validate_signal(signal):
                        # Execute the trade
                        self._execute_signal(signal)
                    
                    self.signal_queue.task_done()
                
                # Sleep briefly to prevent CPU hogging
                time.sleep(0.1)
                
            except Exception as e:
                logger.error(f"Error in execution loop: {e}", exc_info=True)
    
    def _validate_signal(self, signal):
        """Validate if a signal should be executed based on risk and capital"""
        # Check if we have enough capital
        required_capital = signal.get('capital_required', 0)
        if required_capital > 0 and required_capital > self.capital_allocator.get_available_capital():
            logger.warning(f"Insufficient capital for signal: {signal}")
            return False
        
        # Check if the signal passes risk validation
        if not self.risk_manager.validate_trade(signal):
            logger.warning(f"Signal failed risk validation: {signal}")
            return False
        
        # Check market conditions
        if signal.get('market_condition_check') and not self._check_market_conditions(signal):
            logger.warning(f"Market conditions not suitable for signal: {signal}")
            return False
        
        return True
    
    def _check_market_conditions(self, signal):
        """Check if market conditions are suitable for the signal"""
        # Get VIX value
        vix_instrument_id = None
        for inst_id, inst in self.market_data.subscribed_instruments.items():
            if inst['symbol'] == 'INDIA VIX':
                vix_instrument_id = inst_id
                break
        
        if vix_instrument_id and vix_instrument_id in self.market_data.subscribed_instruments:
            current_vix = self.market_data.subscribed_instruments[vix_instrument_id].get('last_price', 0)
            
            # Different strategies have different VIX thresholds
            strategy = signal.get('strategy')
            if strategy == 'volatility_arbitrage' and current_vix < self.params['volatility_arbitrage']['vix_threshold']:
                return False
            elif strategy == 'vix_regime_switch':
                # This strategy adapts to different VIX regimes, so always valid
                return True
            elif strategy == 'dynamic_iron_condor' and current_vix < 15:
                # Iron condor requires some volatility to be profitable
                return False
        
        # Check if it's near market open or close
        now = datetime.now().time()
        market_open = dt_time(9, 15)
        market_close = dt_time(15, 30)
        
        # Avoid trading in first 15 minutes after open or last 15 minutes before close
        if (now < dt_time(9, 30)) or (now > dt_time(15, 15)):
            return False
        
        return True
    
    def _execute_signal(self, signal):
        """Execute a trading signal"""
        try:
            # Allocate capital for this trade
            allocated_capital = self.capital_allocator.allocate_capital(
                signal['strategy'], 
                signal.get('capital_required', 0)
            )
            
            if allocated_capital <= 0:
                logger.warning(f"Failed to allocate capital for signal: {signal}")
                return
            
            # Adjust the signal with the allocated capital
            signal['allocated_capital'] = allocated_capital
            
            # Execute the order
            order_result = self.position_manager.execute_order(signal)
            
            if order_result and order_result.get('success'):
                logger.info(f"Successfully executed signal: {signal}")
                
                # Store strategy position details for management
                self._register_strategy_position(signal, order_result)
            else:
                logger.error(f"Failed to execute signal: {signal}, result: {order_result}")
                # Return allocated capital since trade failed
                self.capital_allocator.release_capital(signal['strategy'], allocated_capital)
        
        except Exception as e:
            logger.error(f"Error executing signal: {e}", exc_info=True)
            # Make sure to release capital on error
            if 'allocated_capital' in signal:
                self.capital_allocator.release_capital(signal['strategy'], signal['allocated_capital'])
    
    def _register_strategy_position(self, signal, order_result):
        """Register a new position for strategy management"""
        position = {
            'strategy': signal['strategy'],
            'entry_time': datetime.now(),
            'signal': copy.deepcopy(signal),
            'order_details': copy.deepcopy(order_result),
            'capital': signal.get('allocated_capital', 0),
            'status': 'active',
            'management_rules': signal.get('management_rules', {}),
        }
        
        # Store position for management
        self.position_manager.register_strategy_position(position)

    # === Strategy Implementations ===
    
    def _execute_volatility_arbitrage(self):
        """
        Volatility arbitrage strategy
        - Sells overpriced options when implied volatility is high
        - Buys options when implied volatility is low relative to historical patterns
        """
        signals = []
        
        try:
            # Check if we have VIX data
            vix_value = self._get_vix_value()
            if vix_value is None or vix_value < self.params['volatility_arbitrage']['vix_threshold']:
                return signals
            
            # Get Nifty and BankNifty option chains
            indices = ['NIFTY 50', 'NIFTY BANK']
            for index_name in indices:
                # Get option chain data
                option_chain = self.market_data.get_option_chain_snapshot(index_name.replace(" ", ""))
                if not option_chain:
                    continue
                
                # Get underlying price
                underlying_price = self._get_index_price(index_name)
                if not underlying_price:
                    continue
                
                # Find overpriced options based on IV percentile
                for option in option_chain['data']:
                    strike = option['strike']
                    
                    # Calculate strike distance as % from current price
                    strike_distance = abs(strike - underlying_price) / underlying_price * 100
                    
                    min_dist = self.params['volatility_arbitrage']['min_strike_distance']
                    max_dist = self.params['volatility_arbitrage']['max_strike_distance']
                    
                    # Skip if strike is too close or too far from current price
                    if strike_distance < min_dist or strike_distance > max_dist:
                        continue
                    
                    # Check call options
                    if option['call_id'] and option['call_price']:
                        # Calculate IV percentile (in a real system, would use historical data)
                        iv_percentile = self._calculate_iv_percentile(option['call_id'])
                        
                        if iv_percentile > self.params['volatility_arbitrage']['min_iv_percentile']:
                            # Generate sell signal for overpriced call
                            signal = {
                                'action': 'SELL',
                                'symbol': self._get_instrument_symbol(option['call_id']),
                                'instrument_id': option['call_id'],
                                'option_type': 'CE',
                                'quantity': self._calculate_quantity(option['call_price'], self.params['volatility_arbitrage']['position_sizing']),
                                'price': option['call_price'],
                                'strategy_type': 'volatility_arbitrage',
                                'iv_percentile': iv_percentile,
                                'reason': f"Call IV percentile: {iv_percentile:.1f}% > threshold {self.params['volatility_arbitrage']['min_iv_percentile']}%",
                                'management_rules': {
                                    'stop_loss': self.params['volatility_arbitrage']['stop_loss'],
                                    'profit_target': self.params['volatility_arbitrage']['profit_target'],
                                    'time_stop': self._get_days_to_expiry(option_chain['expiry'])
                                },
                                'capital_required': self._calculate_margin_requirement(option['call_id'], 'SELL', option['call_price'])
                            }
                            signals.append(signal)
                    
                    # Check put options
                    if option['put_id'] and option['put_price']:
                        # Calculate IV percentile
                        iv_percentile = self._calculate_iv_percentile(option['put_id'])
                        
                        if iv_percentile > self.params['volatility_arbitrage']['min_iv_percentile']:
                            # Generate sell signal for overpriced put
                            signal = {
                                'action': 'SELL',
                                'symbol': self._get_instrument_symbol(option['put_id']),
                                'instrument_id': option['put_id'],
                                'option_type': 'PE',
                                'quantity': self._calculate_quantity(option['put_price'], self.params['volatility_arbitrage']['position_sizing']),
                                'price': option['put_price'],
                                'strategy_type': 'volatility_arbitrage',
                                'iv_percentile': iv_percentile,
                                'reason': f"Put IV percentile: {iv_percentile:.1f}% > threshold {self.params['volatility_arbitrage']['min_iv_percentile']}%",
                                'management_rules': {
                                    'stop_loss': self.params['volatility_arbitrage']['stop_loss'],
                                    'profit_target': self.params['volatility_arbitrage']['profit_target'],
                                    'time_stop': self._get_days_to_expiry(option_chain['expiry'])
                                },
                                'capital_required': self._calculate_margin_requirement(option['put_id'], 'SELL', option['put_price'])
                            }
                            signals.append(signal)
        
        except Exception as e:
            logger.error(f"Error in volatility arbitrage strategy: {e}", exc_info=True)
        
        return signals
    
    def _execute_gamma_scalping(self):
        """
        Gamma scalping strategy
        - Buys ATM options to get positive gamma exposure
        - Hedges delta exposure by dynamically trading the underlying
        - Profits from price movement while maintaining overall delta neutrality
        """
        signals = []
        
        try:
            # Only focus on liquid indices like NIFTY and BankNifty
            indices = ['NIFTY 50', 'NIFTY BANK']
            
            for index_name in indices:
                # Get option chain data
                option_chain = self.market_data.get_option_chain_snapshot(index_name.replace(" ", ""))
                if not option_chain:
                    continue
                
                # Get underlying price
                underlying_price = self._get_index_price(index_name)
                if not underlying_price:
                    continue
                
                # Find ATM options with good gamma exposure
                atm_options = self._find_atm_options(option_chain, underlying_price)
                if not atm_options:
                    continue
                
                # Calculate days to expiry
                days_to_expiry = self._get_days_to_expiry(option_chain['expiry'])
                
                # Check if days to expiry is within our range
                min_days = self.params['gamma_scalper']['min_days_to_expiry']
                max_days = self.params['gamma_scalper']['max_days_to_expiry']
                if days_to_expiry < min_days or days_to_expiry > max_days:
                    continue
                
                # Find the option with highest gamma
                best_option = self._find_highest_gamma_option(atm_options, underlying_price)
                if not best_option:
                    continue
                
                # Calculate position size
                position_sizing = self.params['gamma_scalper']['position_sizing']
                
                # Generate signal for buying the option
                if best_option['type'] == 'call':
                    signal = {
                        'action': 'BUY',
                        'symbol': self._get_instrument_symbol(best_option['instrument_id']),
                        'instrument_id': best_option['instrument_id'],
                        'option_type': 'CE',
                        'quantity': self._calculate_quantity(best_option['price'], position_sizing),
                        'price': best_option['price'],
                        'strategy_type': 'gamma_scalping',
                        'reason': f"High gamma exposure ({best_option['gamma']:.4f}) with {days_to_expiry} days to expiry",
                        'management_rules': {
                            'hedge_interval': self.params['gamma_scalper']['hedge_interval'],
                            'max_gamma': self.params['gamma_scalper']['max_gamma'],
                            'min_gamma': self.params['gamma_scalper']['min_gamma'],
                            'delta_target': 0.0,  # Target delta-neutral position
                            'underlying': index_name
                        },
                        'capital_required': best_option['price'] * self._calculate_quantity(best_option['price'], position_sizing) * self._get_lot_size(best_option['instrument_id'])
                    }
                    signals.append(signal)
                else:
                    signal = {
                        'action': 'BUY',
                        'symbol': self._get_instrument_symbol(best_option['instrument_id']),
                        'instrument_id': best_option['instrument_id'],
                        'option_type': 'PE',
                        'quantity': self._calculate_quantity(best_option['price'], position_sizing),
                        'price': best_option['price'],
                        'strategy_type': 'gamma_scalping',
                        'reason': f"High gamma exposure ({best_option['gamma']:.4f}) with {days_to_expiry} days to expiry",
                        'management_rules': {
                            'hedge_interval': self.params['gamma_scalper']['hedge_interval'],
                            'max_gamma': self.params['gamma_scalper']['max_gamma'],
                            'min_gamma': self.params['gamma_scalper']['min_gamma'],
                            'delta_target': 0.0,  # Target delta-neutral position
                            'underlying': index_name
                        },
                        'capital_required': best_option['price'] * self._calculate_quantity(best_option['price'], position_sizing) * self._get_lot_size(best_option['instrument_id'])
                    }
                    signals.append(signal)
        
        except Exception as e:
            logger.error(f"Error in gamma scalping strategy: {e}", exc_info=True)
        
        return signals
    
        def _execute_mean_reversion(self):
        """
        Mean reversion strategy
        - Identifies when a security has deviated significantly from its historical mean
        - Takes positions expecting price to revert back to the mean
        """
        signals = []
        
        try:
            # Get the top liquid stocks to analyze
            top_stocks = self.market_data.get_top_liquid_stocks(10)
            
            # Get parameters
            lookback = self.params['mean_reversion']['lookback_period']
            entry_threshold = self.params['mean_reversion']['entry_threshold']
            position_sizing = self.params['mean_reversion']['position_sizing']
            max_positions = self.params['mean_reversion']['max_positions']
            
            # Check how many mean reversion positions we already have
            current_positions = self.position_manager.get_positions_by_strategy('mean_reversion')
            if len(current_positions) >= max_positions:
                return signals
            
            # Analyze each stock
            for stock in top_stocks:
                # Get instrument ID
                instrument = self.api.get_instrument_by_symbol(stock, "NSE")
                if not instrument:
                    continue
                
                instrument_id = instrument["instrumentId"]
                
                # Get historical data (using 15-min timeframe)
                if instrument_id in self.market_data.timeframes['15m']:
                    df = pd.DataFrame({
                        'close': self.market_data.timeframes['15m'][instrument_id]['close']
                    }, index=self.market_data.timeframes['15m'][instrument_id]['timestamps'])
                    
                    if len(df) < lookback:
                        continue
                    
                    # Calculate mean and standard deviation
                    mean = df['close'].rolling(window=lookback).mean().iloc[-1]
                    std = df['close'].rolling(window=lookback).std().iloc[-1]
                    
                    if pd.isna(mean) or pd.isna(std):
                        continue
                    
                    # Get current price
                    current_price = df['close'].iloc[-1]
                    
                    # Calculate z-score (distance from mean in standard deviations)
                    z_score = (current_price - mean) / std
                    
                    # Generate signals based on z-score
                    if z_score < -entry_threshold:  # Price is significantly below mean
                        # Generate buy signal
                        signal = {
                            'action': 'BUY',
                            'symbol': stock,
                            'instrument_id': instrument_id,
                            'quantity': self._calculate_quantity(current_price, position_sizing),
                            'price': current_price,
                            'strategy_type': 'mean_reversion',
                            'z_score': z_score,
                            'reason': f"Price below mean by {abs(z_score):.2f} standard deviations",
                            'management_rules': {
                                'target_z_score': self.params['mean_reversion']['exit_threshold'],
                                'stop_loss_z_score': -entry_threshold * 1.5,  # 50% more deviation
                                'max_holding_days': 5,
                                'lookback_period': lookback
                            },
                            'capital_required': current_price * self._calculate_quantity(current_price, position_sizing)
                        }
                        signals.append(signal)
                    
                    elif z_score > entry_threshold:  # Price is significantly above mean
                        # Generate sell signal
                        signal = {
                            'action': 'SELL',
                            'symbol': stock,
                            'instrument_id': instrument_id,
                            'quantity': self._calculate_quantity(current_price, position_sizing),
                            'price': current_price,
                            'strategy_type': 'mean_reversion',
                            'z_score': z_score,
                            'reason': f"Price above mean by {z_score:.2f} standard deviations",
                            'management_rules': {
                                'target_z_score': self.params['mean_reversion']['exit_threshold'],
                                'stop_loss_z_score': entry_threshold * 1.5,  # 50% more deviation
                                'max_holding_days': 5,
                                'lookback_period': lookback
                            },
                            'capital_required': self._calculate_margin_requirement(instrument_id, 'SELL', current_price)
                        }
                        signals.append(signal)
            
            # Sort signals by abs(z-score) to prioritize the most extreme deviations
            if signals:
                signals.sort(key=lambda x: abs(x['z_score']), reverse=True)
                # Limit to available position slots
                signals = signals[:max_positions - len(current_positions)]
        
        except Exception as e:
            logger.error(f"Error in mean reversion strategy: {e}", exc_info=True)
        
        return signals
    
    def _execute_event_momentum(self):
        """
        Event momentum strategy
        - Identifies stocks with significant price movement around market events
        - Takes positions to capture the continuation of momentum
        """
        signals = []
        
        try:
            # Get upcoming events (earnings, dividends, etc.)
            # In a real system, this would come from a market events database/API
            events = self._get_upcoming_events()
            if not events:
                return signals
            
            # Get parameters
            pre_window = self.params['event_momentum']['pre_event_window']
            momentum_threshold = self.params['event_momentum']['momentum_threshold']
            position_sizing = self.params['event_momentum']['position_sizing']
            max_positions = self.params['event_momentum']['max_positions']
            
            # Check how many event momentum positions we already have
            current_positions = self.position_manager.get_positions_by_strategy('event_momentum')
            if len(current_positions) >= max_positions:
                return signals
            
            # Today's date
            today = datetime.now().date()
            
            # Analyze each event
            for event in events:
                # Skip if event is too far out
                event_date = event['date']
                days_until_event = (event_date - today).days
                
                # Focus on events within our window
                if days_until_event > pre_window:
                    continue
                
                # Get the stock symbol
                stock = event['symbol']
                event_type = event['type']
                
                # Get instrument ID
                instrument = self.api.get_instrument_by_symbol(stock, "NSE")
                if not instrument:
                    continue
                    
                instrument_id = instrument["instrumentId"]
                
                # Check if we already have a position on this event
                existing_position = False
                for pos in current_positions:
                    if pos['signal'].get('event_id') == event['id']:
                        existing_position = True
                        break
                
                if existing_position:
                    continue
                
                # Analyze momentum using daily timeframe
                if instrument_id in self.market_data.timeframes['D']:
                    df = pd.DataFrame({
                        'close': self.market_data.timeframes['D'][instrument_id]['close'],
                        'volume': self.market_data.timeframes['D'][instrument_id]['volume']
                    }, index=self.market_data.timeframes['D'][instrument_id]['timestamps'])
                    
                    if len(df) < 20:  # Need sufficient history
                        continue
                    
                    # Calculate momentum indicators
                    df['returns'] = df['close'].pct_change()
                    df['volume_change'] = df['volume'].pct_change()
                    
                    # Calculate z-scores
                    returns_mean = df['returns'].rolling(window=20).mean().iloc[-1]
                    returns_std = df['returns'].rolling(window=20).std().iloc[-1]
                    
                    recent_returns = df['returns'].iloc[-5:].mean()  # Last 5 days
                    
                    if pd.isna(returns_mean) or pd.isna(returns_std) or pd.isna(recent_returns):
                        continue
                    
                    returns_z = (recent_returns - returns_mean) / returns_std
                    
                    # Check for significant momentum
                    current_price = df['close'].iloc[-1]
                    
                    if abs(returns_z) > momentum_threshold:
                        # Determine direction
                        direction = 'BUY' if returns_z > 0 else 'SELL'
                        
                        signal = {
                            'action': direction,
                            'symbol': stock,
                            'instrument_id': instrument_id,
                            'quantity': self._calculate_quantity(current_price, position_sizing),
                            'price': current_price,
                            'strategy_type': 'event_momentum',
                            'momentum_z': returns_z,
                            'event_id': event['id'],
                            'event_type': event_type,
                            'event_date': event_date.strftime('%Y-%m-%d'),
                            'days_to_event': days_until_event,
                            'reason': f"{direction} momentum (z={returns_z:.2f}) before {event_type} on {event_date}",
                            'management_rules': {
                                'stop_loss': self.params['event_momentum']['stop_loss'],
                                'profit_target': self.params['event_momentum']['profit_target'],
                                'exit_days_after_event': self.params['event_momentum']['post_event_window']
                            },
                            'capital_required': (
                                current_price * self._calculate_quantity(current_price, position_sizing)
                                if direction == 'BUY'
                                else self._calculate_margin_requirement(instrument_id, 'SELL', current_price)
                            )
                        }
                        signals.append(signal)
            
            # Sort signals by absolute momentum z-score
            if signals:
                signals.sort(key=lambda x: abs(x['momentum_z']), reverse=True)
                # Limit to available position slots
                signals = signals[:max_positions - len(current_positions)]
        
        except Exception as e:
            logger.error(f"Error in event momentum strategy: {e}", exc_info=True)
        
        return signals
    
    def _execute_options_chain_imbalance(self):
        """
        Options chain imbalance strategy
        - Analyzes put-call ratios and open interest changes
        - Identifies unusual options activity that may predict price moves
        """
        signals = []
        
        try:
            # Focus on liquid indices
            indices = ['NIFTY 50', 'NIFTY BANK']
            
            for index_name in indices:
                symbol = index_name.replace(" ", "")
                
                # Get option chain data
                option_chain = self.market_data.get_option_chain_snapshot(symbol)
                if not option_chain:
                    continue
                
                # Get underlying price
                underlying_price = self._get_index_price(index_name)
                if not underlying_price:
                    continue
                
                # Calculate Put-Call Ratio (PCR) based on volume and OI
                pcr_volume, pcr_oi, total_call_volume, total_put_volume = self._calculate_pcr(option_chain)
                
                if not pcr_volume or not pcr_oi:
                    continue
                
                # Check if volume meets minimum threshold
                min_volume = self.params['options_chain_imbalance']['min_volume']
                if (total_call_volume + total_put_volume) < min_volume:
                    continue
                
                # Get PCR entry thresholds
                min_pcr = self.params['options_chain_imbalance']['min_pcr_entry']
                max_pcr = self.params['options_chain_imbalance']['max_pcr_entry']
                position_sizing = self.params['options_chain_imbalance']['position_sizing']
                
                # Check for PCR-based signals
                if pcr_volume < min_pcr:
                    # Bullish signal (low put-call ratio)
                    # Find slightly OTM call options
                    for option in option_chain['data']:
                        strike = option['strike']
                        
                        # Look for strikes 1-3% above current price
                        if 1.01 * underlying_price <= strike <= 1.03 * underlying_price and option['call_id'] and option['call_price']:
                            signal = {
                                'action': 'BUY',
                                'symbol': self._get_instrument_symbol(option['call_id']),
                                'instrument_id': option['call_id'],
                                'option_type': 'CE',
                                'quantity': self._calculate_quantity(option['call_price'], position_sizing),
                                'price': option['call_price'],
                                'strategy_type': 'options_chain_imbalance',
                                'pcr_volume': pcr_volume,
                                'pcr_oi': pcr_oi,
                                'reason': f"Bullish signal: low PCR ({pcr_volume:.2f}) with high call activity",
                                'management_rules': {
                                    'stop_loss': self.params['options_chain_imbalance']['stop_loss'],
                                    'profit_target': self.params['options_chain_imbalance']['profit_target'],
                                    'max_holding_days': 3
                                },
                                'capital_required': option['call_price'] * self._calculate_quantity(option['call_price'], position_sizing) * self._get_lot_size(option['call_id'])
                            }
                            signals.append(signal)
                            break  # Only take one signal
                
                elif pcr_volume > max_pcr:
                    # Bearish signal (high put-call ratio)
                    # Find slightly OTM put options
                    for option in option_chain['data']:
                        strike = option['strike']
                        
                        # Look for strikes 1-3% below current price
                        if 0.97 * underlying_price <= strike <= 0.99 * underlying_price and option['put_id'] and option['put_price']:
                            signal = {
                                'action': 'BUY',
                                'symbol': self._get_instrument_symbol(option['put_id']),
                                'instrument_id': option['put_id'],
                                'option_type': 'PE',
                                'quantity': self._calculate_quantity(option['put_price'], position_sizing),
                                'price': option['put_price'],
                                'strategy_type': 'options_chain_imbalance',
                                'pcr_volume': pcr_volume,
                                'pcr_oi': pcr_oi,
                                'reason': f"Bearish signal: high PCR ({pcr_volume:.2f}) with high put activity",
                                'management_rules': {
                                    'stop_loss': self.params['options_chain_imbalance']['stop_loss'],
                                    'profit_target': self.params['options_chain_imbalance']['profit_target'],
                                    'max_holding_days': 3
                                },
                                'capital_required': option['put_price'] * self._calculate_quantity(option['put_price'], position_sizing) * self._get_lot_size(option['put_id'])
                            }
                            signals.append(signal)
                            break  # Only take one signal
        
        except Exception as e:
            logger.error(f"Error in options chain imbalance strategy: {e}", exc_info=True)
        
        return signals
    
    def _execute_vix_regime_switch(self):
        """
        VIX regime switch strategy
        - Adapts trading approach based on volatility regime
        - Different volatility environments require different strategies
        """
        signals = []
        
        try:
            # Get current VIX value
            vix_value = self._get_vix_value()
            if vix_value is None:
                return signals
            
            # Get VIX moving average
            vix_ma_period = self.params['vix_regime_switch']['vix_ma_period']
            vix_ma = self._calculate_vix_ma(vix_ma_period)
            if vix_ma is None:
                return signals
            
            # Determine VIX regime
            low_threshold = self.params['vix_regime_switch']['vix_low_threshold']
            high_threshold = self.params['vix_regime_switch']['vix_high_threshold']
            extreme_threshold = self.params['vix_regime_switch']['vix_extreme_threshold']
            
            if vix_value < low_threshold:
                regime = 'low'
            elif vix_value < high_threshold:
                regime = 'medium'
            elif vix_value < extreme_threshold:
                regime = 'high'
            else:
                regime = 'extreme'
            
            # Get regime-specific position sizing
            position_sizing = self.params['vix_regime_switch']['position_sizing'][regime]
            
            # Different strategies for different regimes
            if regime == 'low':
                # Low volatility: focus on momentum and trend strategies
                signals.extend(self._low_vol_regime_strategy(position_sizing))
            
            elif regime == 'medium':
                # Medium volatility: balanced approach with premium selling
                signals.extend(self._medium_vol_regime_strategy(position_sizing))
            
            elif regime == 'high':
                # High volatility: focus on mean reversion and VIX decay
                signals.extend(self._high_vol_regime_strategy(position_sizing))
            
            else:  # extreme
                # Extreme volatility: defensive posture, hedge existing positions
                signals.extend(self._extreme_vol_regime_strategy(position_sizing))
        
        except Exception as e:
            logger.error(f"Error in VIX regime switch strategy: {e}", exc_info=True)
        
        return signals
    
    def _execute_calendar_spread(self):
        """
        Calendar spread strategy
        - Exploits term structure of implied volatility
        - Sells near-term options and buys longer-term options
        """
        signals = []
        
        try:
            # Focus on liquid indices
            indices = ['NIFTY 50', 'NIFTY BANK']
            position_sizing = self.params['calendar_spread']['position_sizing']
            min_iv_skew = self.params['calendar_spread']['min_iv_skew']
            
            for index_name in indices:
                symbol = index_name.replace(" ", "")
                
                # Get option chain for current expiry
                near_chain = self.market_data.get_option_chain_snapshot(symbol)
                if not near_chain:
                    continue
                
                # Get underlying price
                underlying_price = self._get_index_price(index_name)
                if not underlying_price:
                    continue
                
                # Get next expiry (would need to implement a way to get this)
                next_expiry = self._get_next_expiry(symbol, near_chain['expiry'])
                if not next_expiry:
                    continue
                
                # Get option chain for next expiry (this is a simplified implementation)
                # In a real system, you'd need to fetch the next month's option chain
                far_chain = self._get_option_chain_by_expiry(symbol, next_expiry)
                if not far_chain:
                    continue
                
                # Find ATM options
                near_atm = self._find_atm_option(near_chain, underlying_price)
                far_atm = self._find_atm_option(far_chain, underlying_price)
                
                if not near_atm or not far_atm:
                    continue
                
                # Calculate IV skew between months
                # In a real system, you'd calculate actual IV from option prices
                # Here we're using a simplified approach
                near_iv = self._estimate_iv(near_atm['price'], underlying_price, near_atm['strike'], self._get_days_to_expiry(near_chain['expiry']))
                far_iv = self._estimate_iv(far_atm['price'], underlying_price, far_atm['strike'], self._get_days_to_expiry(next_expiry))
                
                iv_skew = far_iv - near_iv
                
                # Check if IV skew is sufficient
                if iv_skew > min_iv_skew:
                    # Create calendar spread signal (sell near-term, buy far-term)
                    signal = {
                        'action': 'CALENDAR_SPREAD',
                        'strategy_type': 'calendar_spread',
                        'underlying': symbol,
                        'reason': f"IV skew: {iv_skew:.1f}% between {self._get_days_to_expiry(near_chain['expiry'])} and {self._get_days_to_expiry(next_expiry)} days",
                        'legs': [
                            {
                                'action': 'SELL',
                                'symbol': self._get_instrument_symbol(near_atm['instrument_id']),
                                'instrument_id': near_atm['instrument_id'],
                                'option_type': near_atm['type'].upper(),
                                'quantity': self._calculate_quantity(near_atm['price'], position_sizing),
                                'price': near_atm['price']
                            },
                            {
                                'action': 'BUY',
                                'symbol': self._get_instrument_symbol(far_atm['instrument_id']),
                                'instrument_id': far_atm['instrument_id'],
                                'option_type': far_atm['type'].upper(),
                                'quantity': self._calculate_quantity(far_atm['price'], position_sizing),
                                'price': far_atm['price']
                            }
                        ],
                        'management_rules': {
                            'stop_loss': self.params['calendar_spread']['stop_loss'],
                            'profit_target': self.params['calendar_spread']['profit_target'],
                            'exit_days_before_near_expiry': 1
                        },
                        'capital_required': (
                            far_atm['price'] * self._calculate_quantity(far_atm['price'], position_sizing) * self._get_lot_size(far_atm['instrument_id'])
                        )
                    }
                    signals.append(signal)
        
        except Exception as e:
            logger.error(f"Error in calendar spread strategy: {e}", exc_info=True)
        
        return signals
    
    def _execute_dynamic_iron_condor(self):
        """
        Dynamic iron condor strategy
        - Creates a multi-leg options position to profit from range-bound markets
        - Dynamically adjusts width based on volatility
        """
        signals = []
        
        try:
            # Focus on liquid indices
            indices = ['NIFTY 50', 'NIFTY BANK']
            
            for index_name in indices:
                symbol = index_name.replace(" ", "")
                
                # Get option chain data
                option_chain = self.market_data.get_option_chain_snapshot(symbol)
                if not option_chain:
                    continue
                
                # Get underlying price
                underlying_price = self._get_index_price(index_name)
                if not underlying_price:
                    continue
                
                # Calculate days to expiry
                days_to_expiry = self._get_days_to_expiry(option_chain['expiry'])
                min_days = self.params['dynamic_iron_condor']['days_to_expiry'][0]
                max_days = self.params['dynamic_iron_condor']['days_to_expiry'][1]
                
                # Check if days to expiry is within our range
                if days_to_expiry < min_days or days_to_expiry > max_days:
                    continue
                
                # Calculate IV rank (would need historical data in a real system)
                iv_rank = self._calculate_iv_rank(symbol)
                min_iv_rank = self.params['dynamic_iron_condor']['iv_rank_min']
                
                # Only proceed if IV rank is high enough for premium selling
                if iv_rank < min_iv_rank:
                    continue
                
                # Calculate ATR to determine wing width
                atr = self._calculate_atr_for_underlying(symbol)
                if not atr:
                    continue
                
                # Determine wing width based on ATR and our factor
                width_factor = self.params['dynamic_iron_condor']['width_factor']
                wing_width = round(atr * width_factor)
                
                # Round to appropriate strike intervals
                if symbol == "NIFTY":
                    wing_width = round(wing_width / 50) * 50  # Round to nearest 50
                elif symbol == "BANKNIFTY":
                    wing_width = round(wing_width / 100) * 100  # Round to nearest 100
                
                # Ensure minimum width
                wing_width = max(wing_width, 500 if symbol == "NIFTY" else 1000)
                
                # Calculate strikes for the iron condor
                short_call_strike = round(underlying_price / 50) * 50 + 50  # Slightly OTM
                short_put_strike = round(underlying_price / 50) * 50 - 50   # Slightly OTM
                long_call_strike = short_call_strike + wing_width
                long_put_strike = short_put_strike - wing_width
                
                # Find the corresponding options in the chain
                short_call, short_put, long_call, long_put = None, None, None, None
                
                for option in option_chain['data']:
                    if option['strike'] == short_call_strike and option['call_id']:
                        short_call = {
                            'id': option['call_id'],
                            'price': option['call_price'],
                            'strike': short_call_strike,
                            'type': 'CE'
                        }
                    
                    if option['strike'] == short_put_strike and option['put_id']:
                        short_put = {
                            'id': option['put_id'],
                            'price': option['put_price'],
                            'strike': short_put_strike,
                            'type': 'PE'
                        }
                    
                    if option['strike'] == long_call_strike and option['call_id']:
                        long_call = {
                            'id': option['call_id'],
                            'price': option['call_price'],
                            'strike': long_call_strike,
                            'type': 'CE'
                        }
                    
                    if option['strike'] == long_put_strike and option['put_id']:
                        long_put = {
                            'id': option['put_id'],
                            'price': option['put_price'],
                            'strike': long_put_strike,
                            'type': 'PE'
                        }
                
                # Make sure we have all the options needed
                if not all([short_call, short_put, long_call, long_put]):
                    continue
                
                # Calculate net credit received
                credit = (short_call['price'] + short_put['price'] - long_call['price'] - long_put['price'])
                
                # Check if credit is positive
                if credit <= 0:
                    continue
                
                # Calculate position size
                position_sizing = self.params['dynamic_iron_condor']['position_sizing']
                quantity = self._calculate_quantity(credit * 2, position_sizing)  # Using 2x credit as a base for sizing
                
                # Create iron condor signal
                signal = {
                    'action': 'IRON_CONDOR',
                    'strategy_type': 'dynamic_iron_condor',
                    'underlying': symbol,
                    'credit': credit,
                    'width': wing_width,
                    'iv_rank': iv_rank,
                    'days_to_expiry': days_to_expiry,
                    'reason': f"IV rank: {iv_rank}%, width: {wing_width}, credit: {credit:.1f}",
                    'legs': [
                        {
                            'action': 'SELL',
                            'symbol': self._get_instrument_symbol(short_call['id']),
                            'instrument_id': short_call['id'],
                            'option_type': 'CE',
                            'quantity': quantity,
                            'price': short_call['price'],
                            'strike': short_call_strike
                        },
                        {
                            'action': 'SELL',
                            'symbol': self._get_instrument_symbol(short_put['id']),
                            'instrument_id': short_put['id'],
                            'option_type': 'PE',
                            'quantity': quantity,
                            'price': short_put['price'],
                            'strike': short_put_strike
                        },
                        {
                            'action': 'BUY',
                            'symbol': self._get_instrument_symbol(long_call['id']),
                            'instrument_id': long_call['id'],
                            'option_type': 'CE',
                            'quantity': quantity,
                            'price': long_call['price'],
                            'strike': long_call_strike
                        },
                        {
                            'action': 'BUY',
                            'symbol': self._get_instrument_symbol(long_put['id']),
                            'instrument_id': long_put['id'],
                            'option_type': 'PE',
                            'quantity': quantity,
                            'price': long_put['price'],
                            'strike': long_put_strike
                        }
                    ],
                    'management_rules': {
                        'stop_loss': self.params['dynamic_iron_condor']['stop_loss'],
                        'profit_target': self.params['dynamic_iron_condor']['profit_target'],
                        'adjustment_threshold': self.params['dynamic_iron_condor']['adjustment_threshold'],
                        'max_adjustments': 2
                    },
                    'capital_required': (
                        wing_width * quantity * self._get_lot_size(short_call['id']) - credit * quantity * self._get_lot_size(short_call['id'])
                    )
                }
                signals.append(signal)
        
        except Exception as e:
            logger.error(f"Error in dynamic iron condor strategy: {e}", exc_info=True)
        
        return signals
    
    def _execute_implied_vs_realized_vol(self):
        """
        Implied vs Realized Volatility strategy
        - Compares implied volatility to historical realized volatility
        - Trades options when there's a significant discrepancy
        """
        signals = []
        
        try:
            # Focus on liquid indices
            indices = ['NIFTY 50', 'NIFTY BANK']
            
            for index_name in indices:
                symbol = index_name.replace(" ", "")
                
                # Get option chain data
                option_chain = self.market_data.get_option_chain_snapshot(symbol)
                if not option_chain:
                    continue
                
                # Get underlying price
                underlying_price = self._get_index_price(index_name)
                if not underlying_price:
                    continue
                
                # Calculate implied volatility (weighted average of ATM options)
                implied_volatility = self._calculate_weighted_iv(option_chain, underlying_price)
                if not implied_volatility:
                    continue
                
                # Calculate historical realized volatility
                lookback = self.params['implied_vs_realized_vol']['lookback_period']
                realized_volatility = self._calculate_realized_volatility(symbol, lookback)
                if not realized_volatility:
                    continue
                
                # Calculate the ratio of IV to RV
                iv_rv_ratio = implied_volatility / realized_volatility
                threshold = self.params['implied_vs_realized_vol']['iv_vs_rv_threshold']
                
                # Days to expiry requirements
                min_days = self.params['implied_vs_realized_vol']['min_days_to_expiry']
                max_days = self.params['implied_vs_realized_vol']['max_days_to_expiry']
                days_to_expiry = self._get_days_to_expiry(option_chain['expiry'])
                
                if days_to_expiry < min_days or days_to_expiry > max_days:
                    continue
                
                # Position sizing
                position_sizing = self.params['implied_vs_realized_vol']['position_sizing']
                
                # Case 1: IV is significantly higher than RV (overpriced options)
                if iv_rv_ratio > threshold:
                    # Find ATM straddle to sell
                    atm_call, atm_put = self._find_atm_straddle(option_chain, underlying_price)
                    
                    if not atm_call or not atm_put:
                        continue
                    
                    # Calculate premium received from straddle
                    premium = atm_call['price'] + atm_put['price']
                    
                    # Generate signal for short straddle
                    signal = {
                        'action': 'SHORT_STRADDLE',
                        'strategy_type': 'implied_vs_realized_vol',
                        'underlying': symbol,
                        'iv': implied_volatility,
                        'rv': realized_volatility,
                        'iv_rv_ratio': iv_rv_ratio,
                        'days_to_expiry': days_to_expiry,
                        'reason': f"IV/RV ratio: {iv_rv_ratio:.2f} > {threshold} (IV: {implied_volatility:.1f}%, RV: {realized_volatility:.1f}%)",
                        'legs': [
                            {
                                'action': 'SELL',
                                'symbol': self._get_instrument_symbol(atm_call['id']),
                                'instrument_id': atm_call['id'],
                                'option_type': 'CE',
                                'quantity': self._calculate_quantity(atm_call['price'], position_sizing),
                                'price': atm_call['price'],
                                'strike': atm_call['strike']
                            },
                            {
                                'action': 'SELL',
                                'symbol': self._get_instrument_symbol(atm_put['id']),
                                'instrument_id': atm_put['id'],
                                'option_type': 'PE',
                                'quantity': self._calculate_quantity(atm_put['price'], position_sizing),
                                'price': atm_put['price'],
                                'strike': atm_put['strike']
                            }
                        ],
                        'management_rules': {
                            'stop_loss': self.params['implied_vs_realized_vol']['stop_loss'],
                            'profit_target': self.params['implied_vs_realized_vol']['profit_target'],
                            'max_days_held': min(days_to_expiry - 5, 14)  # Exit at least 5 days before expiry
                        },
                        'capital_required': self._calculate_margin_requirement_for_straddle(atm_call['id'], atm_put['id'], self._calculate_quantity(premium, position_sizing))
                    }
                    signals.append(signal)
                
                # Case 2: IV is significantly lower than RV (underpriced options)
                elif iv_rv_ratio < 1 / threshold:
                    # Find slightly OTM options to buy
                    otm_call, otm_put = self._find_otm_options(option_chain, underlying_price)
                    
                    if not otm_call or not otm_put:
                        continue
                    
                    # Generate signal for long strangle
                    signal = {
                        'action': 'LONG_STRANGLE',
                        'strategy_type': 'implied_vs_realized_vol',
                        'underlying': symbol,
                        'iv': implied_volatility,
                        'rv': realized_volatility,
                        'iv_rv_ratio': iv_rv_ratio,
                        'days_to_expiry': days_to_expiry,
                        'reason': f"IV/RV ratio: {iv_rv_ratio:.2f} < {1/threshold:.2f} (IV: {implied_volatility:.1f}%, RV: {realized_volatility:.1f}%)",
                        'legs': [
                            {
                                'action': 'BUY',
                                'symbol': self._get_instrument_symbol(otm_call['id']),
                                'instrument_id': otm_call['id'],
                                'option_type': 'CE',
                                'quantity': self._calculate_quantity(otm_call['price'], position_sizing),
                                'price': otm_call['price'],
                                'strike': otm_call['strike']
                            },
                            {
                                'action': 'BUY',
                                'symbol': self._get_instrument_symbol(otm_put['id']),
                                'instrument_id': otm_put['id'],
                                'option_type': 'PE',
                                'quantity': self._calculate_quantity(otm_put['price'], position_sizing),
                                'price': otm_put['price'],
                                'strike': otm_put['strike']
                            }
                        ],
                        'management_rules': {
                            'stop_loss': self.params['implied_vs_realized_vol']['stop_loss'],
                            'profit_target': self.params['implied_vs_realized_vol']['profit_target'],
                            'max_days_held': min(days_to_expiry - 5, 14)  # Exit at least 5 days before expiry
                        },
                        'capital_required': (
                            otm_call['price'] * self._calculate_quantity(otm_call['price'], position_sizing) * self._get_lot_size(otm_call['id']) +
                            otm_put['price'] * self._calculate_quantity(otm_put['price'], position_sizing) * self._get_lot_size(otm_put['id'])
                        )
                    }
                    signals.append(signal)
        
        except Exception as e:
            logger.error(f"Error in implied vs realized volatility strategy: {e}", exc_info=True)
        
        return signals

    # === Helper Methods ===
    
    def _get_vix_value(self):
        """Get current VIX value"""
        # Check if VIX is in our subscribed instruments
        for instrument_id, instrument in self.market_data.subscribed_instruments.items():
            if instrument['symbol'] == 'INDIA VIX':
                return instrument.get('last_price')
        return None
    
    def _get_index_price(self, index_name):
        """Get current price of an index"""
        for instrument_id, instrument in self.market_data.subscribed_instruments.items():
            if instrument['symbol'] == index_name:
                return instrument.get('last_price')
        return None
    
    def _calculate_iv_percentile(self, instrument_id):
        """
        Calculate IV percentile using historical data
        Note: In a real implementation, this would use actual historical IV data
        """
        # Simplified implementation - in reality would use historical IV data
        # Returns random value between 50-100 for demo purposes
        import random
        return random.uniform(50, 100)
    
    def _calculate_quantity(self, price, position_sizing_factor):
        """Calculate quantity based on position sizing"""
        available_capital = self.capital_allocator.get_available_capital()
        allocated_capital = available_capital * position_sizing_factor
        
        # Ensure minimum quantity of 1
        quantity = max(1, int(allocated_capital / price))
        return quantity
    
    def _calculate_margin_requirement(self, instrument_id, action, price):
        """
        Calculate margin requirement for a trade
        Note: Simplified implementation - real margin calculation is more complex
        """
        # Get lot size
        lot_size = self._get_lot_size(instrument_id)
        
        if action == 'BUY':
            # For long options, margin is the premium
            return price * lot_size
        else:  # SELL
            # For short options, use a simplified margin calculation
            # In reality, this would be more complex based on exchange rules
            return price * lot_size * 3  # Approximate margin requirement
    
    def _get_lot_size(self, instrument_id):
        """Get lot size for an instrument"""
        # In a real implementation, this would fetch the actual lot size from instrument details
        # For simplicity, using standard lot sizes for Nifty and BankNifty
        for _, instrument in self.market_data.subscribed_instruments.items():
            if instrument_id == instrument.get('instrument_id'):
                symbol = instrument.get('symbol', '')
                if 'NIFTY' in symbol and 'BANK' not in symbol:
                    return 50
                elif 'BANKNIFTY' in symbol or 'BANK' in symbol:
                    return 25
        return 50  # Default lot size
    
    def _get_instrument_symbol(self, instrument_id):
        """Get symbol for an instrument ID"""
        for id_, instrument in self.market_data.subscribed_instruments.items():
            if id_ == instrument_id:
                return instrument.get('symbol', 'UNKNOWN')
        return 'UNKNOWN'
    
    def _get_days_to_expiry(self, expiry_date):
        """Calculate days to expiry"""
        if isinstance(expiry_date, str):
            expiry_date = datetime.strptime(expiry_date, '%Y-%m-%d').date()
        today = datetime.now().date()
        return (expiry_date - today).days
    
    def _find_atm_options(self, option_chain, underlying_price):
        """Find ATM options in the chain"""
        result = []
        
        # Find the strike closest to current price
        closest_strike = min(option_chain['data'], key=lambda x: abs(x['strike'] - underlying_price))['strike']
        
        for option in option_chain['data']:
            if option['strike'] == closest_strike:
                if option['call_id'] and option['call_price']:
                    result.append({
                        'type': 'call',
                        'instrument_id': option['call_id'],
                        'price': option['call_price'],
                        'strike': option['strike']
                    })
                if option['put_id'] and option['put_price']:
                    result.append({
                        'type': 'put',
                        'instrument_id': option['put_id'],
                        'price': option['put_price'],
                        'strike': option['strike']
                    })
        
        return result
    
    def _find_highest_gamma_option(self, options, underlying_price):
        """Find option with highest gamma"""
        # In a real implementation, this would calculate actual gamma values
        # Here we use a simple heuristic: closest to ATM has highest gamma
        return min(options, key=lambda x: abs(x['strike'] - underlying_price)) if options else None
    
    def _get_upcoming_events(self):
        """
        Get upcoming market events
        Note: In a real implementation, this would fetch from an events API or database
        """
        # Simplified implementation with mock data
        today = datetime.now().date()
        events = [
            {
                'id': 'E001',
                'symbol': 'RELIANCE',
                'date': today + timedelta(days=2),
                'type': 'Earnings'
            },
            {
                'id': 'E002',
                'symbol': 'INFY',
                'date': today + timedelta(days=1),
                'type': 'Earnings'
            },
            {
                'id': 'E003',
                'symbol': 'HDFCBANK',
                'date': today + timedelta(days=3),
                'type': 'Dividend'
            }
        ]
        return events
    
    def _calculate_pcr(self, option_chain):
        """Calculate put-call ratio from option chain"""
        total_call_volume = 0
        total_put_volume = 0
        total_call_oi = 0
        total_put_oi = 0
        
        # This is a simplified implementation
        # In a real system, you would have volume and OI data
        # Simulate this with random values for demo
        import random
        for option in option_chain['data']:
            if option['call_id']:
                # Simulated volume and OI for calls
                call_volume = random.randint(100, 10000)
                call_oi = random.randint(1000, 100000)
                total_call_volume += call_volume
                total_call_oi += call_oi
            
            if option['put_id']:
                # Simulated volume and OI for puts
                put_volume = random.randint(100, 10000)
                put_oi = random.randint(1000, 100000)
                total_put_volume += put_volume
                total_put_oi += put_oi
        
        # Calculate PCR
        pcr_volume = total_put_volume / total_call_volume if total_call_volume > 0 else 0
        pcr_oi = total_put_oi / total_call_oi if total_call_oi > 0 else 0
        
        return pcr_volume, pcr_oi, total_call_volume, total_put_volume
    
    def _calculate_vix_ma(self, period):
        """Calculate VIX moving average"""
        # In a real implementation, this would use historical VIX data
        # Simplified version - just return current VIX
        return self._get_vix_value()
    
    def _low_vol_regime_strategy(self, position_sizing):
        """Strategy for low volatility regime"""
        signals = []
        
        try:
            # In low volatility, focus on trend following strategies
            # Example: Buy call options on strongest trending stocks
            top_stocks = self.market_data.get_top_liquid_stocks(5)
            
            for stock in top_stocks:
                # Get instrument ID
                instrument = self.api.get_instrument_by_symbol(stock, "NSE")
                if not instrument:
                    continue
                    
                instrument_id = instrument["instrumentId"]
                
                # Check if we have technical indicators for this stock
                if instrument_id not in self.market_data.indicators:
                    continue
                
                # Get indicators
                indicators = self.market_data.get_technical_indicators(instrument_id, '1h')
                if not indicators:
                    continue
                
                # Look for strong uptrend
                # Check if all EMAs are aligned (short above long)
                if ('ema9' in indicators and 'ema21' in indicators and 'ema50' in indicators and
                    indicators['ema9'] > indicators['ema21'] > indicators['ema50'] and
                    'rsi' in indicators and indicators['rsi'] > 60):
                    
                    # Strong uptrend detected - buy call options
                    # In a real implementation, you'd look up the appropriate options
                    # Simplified implementation here
                    
                    # Get current stock price
                    current_price = None
                    for _, ins in self.market_data.subscribed_instruments.items():
                        if ins['symbol'] == stock:
                            current_price = ins['last_price']
                            break
                    
                    if not current_price:
                        continue
                    
                    # Generate signal for buying call option
                    signal = {
                        'action': 'BUY',
                        'symbol': stock,
                        'instrument_id': instrument_id,  # This would be the option's instrument ID in reality
                        'quantity': self._calculate_quantity(current_price * 0.05, position_sizing),  # Option premium estimate
                        'price': current_price * 0.05,  # Simplified option price estimate
                        'strategy_type': 'trend_following',
                        'reason': f"Strong uptrend in low volatility regime (RSI: {indicators['rsi']:.1f})",
                        'management_rules': {
                            'stop_loss': 0.3,  # 30% stop loss
                            'profit_target': 0.5,  # 50% profit target
                            'max_holding_days': 10
                        },
                        'capital_required': current_price * 0.05 * self._calculate_quantity(current_price * 0.05, position_sizing)
                    }
                    signals.append(signal)
        
        except Exception as e:
            logger.error(f"Error in low volatility regime strategy: {e}", exc_info=True)
        
        return signals
    
    def _medium_vol_regime_strategy(self, position_sizing):
        """Strategy for medium volatility regime"""
        signals = []
        
        try:
            # In medium volatility, premium selling strategies work well
            # Example: Sell put spreads on strong stocks
            
            # Focus on Nifty and BankNifty
            indices = ['NIFTY 50', 'NIFTY BANK']
            
            for index_name in indices:
                symbol = index_name.replace(" ", "")
                
                # Get option chain
                option_chain = self.market_data.get_option_chain_snapshot(symbol)
                if not option_chain:
                    continue
                
                # Get underlying price
                underlying_price = self._get_index_price(index_name)
                if not underlying_price:
                    continue
                
                # Find slightly OTM put options
                otm_put_strike = None
                otm_put = None
                further_otm_put_strike = None
                further_otm_put = None
                
                # Find strikes that are 2-3% OTM
                target_put_strike = underlying_price * 0.97
                target_further_strike = underlying_price * 0.94
                
                for option in option_chain['data']:
                    if not option['put_id'] or not option['put_price']:
                        continue
                        
                    # Find closest OTM put
                    if option['strike'] < underlying_price and (otm_put_strike is None or 
                                                              abs(option['strike'] - target_put_strike) < abs(otm_put_strike - target_put_strike)):
                        otm_put_strike = option['strike']
                        otm_put = {
                            'id': option['put_id'],
                            'price': option['put_price'],
                            'strike': option['strike']
                        }
                    
                    # Find further OTM put
                    if option['strike'] < underlying_price and option['strike'] < target_put_strike and (
                            further_otm_put_strike is None or 
                            abs(option['strike'] - target_further_strike) < abs(further_otm_put_strike - target_further_strike)):
                        further_otm_put_strike = option['strike']
                        further_otm_put = {
                            'id': option['put_id'],
                            'price': option['put_price'],
                            'strike': option['strike']
                        }
                
                if not otm_put or not further_otm_put:
                    continue
                
                # Create put spread signal (sell higher strike, buy lower strike)
                credit = otm_put['price'] - further_otm_put['price']
                
                if credit <= 0:
                    continue
                
                signal = {
                    'action': 'PUT_CREDIT_SPREAD',
                    'strategy_type': 'premium_selling',
                    'underlying': symbol,
                    'credit': credit,
                    'reason': f"Medium volatility regime: selling put spread for {credit:.1f} credit",
                    'legs': [
                        {
                            'action': 'SELL',
                            'symbol': self._get_instrument_symbol(otm_put['id']),
                            'instrument_id': otm_put['id'],
                            'option_type': 'PE',
                            'quantity': self._calculate_quantity(credit, position_sizing),
                            'price': otm_put['price'],
                            'strike': otm_put['strike']
                        },
                        {
                            'action': 'BUY',
                            'symbol': self._get_instrument_symbol(further_otm_put['id']),
                            'instrument_id': further_otm_put['id'],
                            'option_type': 'PE',
                            'quantity': self._calculate_quantity(credit, position_sizing),
                            'price': further_otm_put['price'],
                            'strike': further_otm_put['strike']
                        }
                    ],
                    'management_rules': {
                        'stop_loss': 2.0,  # Stop at 2x credit
                        'profit_target': 0.5,  # Take profit at 50% of max profit
                        'days_to_close': 5  # Close 5 days before expiry regardless
                    },
                    'capital_required': (otm_put['strike'] - further_otm_put['strike']) * self._calculate_quantity(credit, position_sizing) * self._get_lot_size(otm_put['id']) - credit * self._calculate_quantity(credit, position_sizing) * self._get_lot_size(otm_put['id'])
                }
                signals.append(signal)
        
        except Exception as e:
            logger.error(f"Error in medium volatility regime strategy: {e}", exc_info=True)
        
        return signals
    
    def _high_vol_regime_strategy(self, position_sizing):
        """Strategy for high volatility regime"""
        signals = []
        
        try:
            # In high volatility, focus on mean reversion and volatility selling
            # Example: Sell Iron Condors with wider wings
            
            # Focus on Nifty
            index_name = 'NIFTY 50'
            symbol = 'NIFTY'
            
            # Get option chain
            option_chain = self.market_data.get_option_chain_snapshot(symbol)
            if not option_chain:
                return signals
            
            # Get underlying price
            underlying_price = self._get_index_price(index_name)
            if not underlying_price:
                return signals
            
            # In high volatility, use wider wings (5-7%)
            upper_wing = underlying_price * 1.07
            lower_wing = underlying_price * 0.93
            
            # Round to nearest 50
            upper_wing = round(upper_wing / 50) * 50
            lower_wing = round(lower_wing / 50) * 50
            
            # Find options for our iron condor
            short_call_strike = round(underlying_price / 50) * 50 + 150  # Further OTM in high vol
            short_put_strike = round(underlying_price / 50) * 50 - 150
            long_call_strike = short_call_strike + 300  # Wider wing
            long_put_strike = short_put_strike - 300
            
            # Find the corresponding options in the chain
            short_call, short_put, long_call, long_put = None, None, None, None
            
            for option in option_chain['data']:
                if option['strike'] == short_call_strike and option['call_id']:
                    short_call = {
                        'id': option['call_id'],
                        'price': option['call_price'],
                        'strike': short_call_strike
                    }
                
                if option['strike'] == short_put_strike and option['put_id']:
                    short_put = {
                        'id': option['put_id'],
                        'price': option['put_price'],
                        'strike': short_put_strike
                    }
                
                if option['strike'] == long_call_strike and option['call_id']:
                    long_call = {
                        'id': option['call_id'],
                        'price': option['call_price'],
                        'strike': long_call_strike
                    }
                
                if option['strike'] == long_put_strike and option['put_id']:
                    long_put = {
                        'id': option['put_id'],
                        'price': option['put_price'],
                        'strike': long_put_strike
                    }
            
            # Make sure we have all the options needed
            if not all([short_call, short_put, long_call, long_put]):
                return signals
            
            # Calculate net credit
            credit = short_call['price'] + short_put['price'] - long_call['price'] - long_put['price']
            
            if credit <= 0:
                return signals
            
            # Create iron condor signal with wider wings for high volatility
            signal = {
                'action': 'IRON_CONDOR',
                'strategy_type': 'high_vol_iron_condor',
                'underlying': symbol,
                'credit': credit,
                'reason': f"High volatility regime: wide-wing iron condor for {credit:.1f} credit",
                'legs': [
                    {
                        'action': 'SELL',
                        'symbol': self._get_instrument_symbol(short_call['id']),
                        'instrument_id': short_call['id'],
                        'option_type': 'CE',
                        'quantity': self._calculate_quantity(credit, position_sizing),
                        'price': short_call['price'],
                        'strike': short_call['strike']
                    },
                    {
                        'action': 'SELL',
                        'symbol': self._get_instrument_symbol(short_put['id']),
                        'instrument_id': short_put['id'],
                        'option_type': 'PE',
                        'quantity': self._calculate_quantity(credit, position_sizing),
                        'price': short_put['price'],
                        'strike': short_put['strike']
                    },
                    {
                        'action': 'BUY',
                        'symbol': self._get_instrument_symbol(long_call['id']),
                        'instrument_id': long_call['id'],
                        'option_type': 'CE',
                        'quantity': self._calculate_quantity(credit, position_sizing),
                        'price': long_call['price'],
                        'strike': long_call['strike']
                    },
                    {
                        'action': 'BUY',
                        'symbol': self._get_instrument_symbol(long_put['id']),
                        'instrument_id': long_put['id'],
                        'option_type': 'PE',
                        'quantity': self._calculate_quantity(credit, position_sizing),
                        'price': long_put['price'],
                        'strike': long_put['strike']
                    }
                ],
                'management_rules': {
                    'stop_loss': 2.0,  # Stop at 2x credit
                    'profit_target': 0.5,  # Take profit at 50% of max profit
                    'days_to_close': 5,  # Close 5 days before expiry regardless
                    'vix_exit_threshold': 0.85  # Exit if VIX drops below 85% of entry level
                },
                'capital_required': (
                    (long_call['strike'] - short_call['strike']) * self._calculate_quantity(credit, position_sizing) * self._get_lot_size(short_call['id']) - 
                    credit * self._calculate_quantity(credit, position_sizing) * self._get_lot_size(short_call['id'])
                )
            }
            signals.append(signal)
        
        except Exception as e:
            logger.error(f"Error in high volatility regime strategy: {e}", exc_info=True)
        
        return signals
    
    def _extreme_vol_regime_strategy(self, position_sizing):
        """Strategy for extreme volatility regime"""
        signals = []
        
        try:
            # In extreme volatility, focus on hedging and defensive positions
            # Example: Buy protective puts for existing positions
            
            # Check for existing positions that need hedging
            current_positions = self.position_manager.get_all_positions()
            
            # Filter for equity positions
            equity_positions = [pos for pos in current_positions if pos.get('position_type') == 'equity' and pos.get('action') == 'BUY']
            
            for position in equity_positions:
                # Check if position is already hedged
                if position.get('hedged', False):
                    continue
                
                symbol = position.get('symbol')
                if not symbol:
                    continue
                
                # Get instrument details
                instrument = self.api.get_instrument_by_symbol(symbol, "NSE")
                if not instrument:
                    continue
                
                # Find appropriate put options
                # In a real implementation, you'd look up actual options
                # Simplified implementation here
                
                # Generate signal for buying protective put
                signal = {
                    'action': 'BUY_HEDGE',
                    'strategy_type': 'protective_put',
                    'for_position_id': position.get('position_id'),
                    'symbol': symbol,
                    'reason': f"Extreme volatility protection for {symbol} position",
                    'management_rules': {
                        'hedge_delta': 0.8,  # Hedge 80% of position
                        'exit_on_vol_decrease': True,
                        'vix_exit_threshold': 0.7  # Exit hedge if VIX drops below 70% of current
                    },
                    'capital_required': position.get('current_value', 0) * 0.05  # Approximate cost of hedge
                }
                signals.append(signal)
        
        except Exception as e:
            logger.error(f"Error in extreme volatility regime strategy: {e}", exc_info=True)
        
        return signals
    
    def _get_next_expiry(self, symbol, current_expiry):
        """Get the next expiry date after the current one"""
        # In a real implementation, this would fetch from the exchange calendar
        # Simplified implementation - just add a month to current expiry
        if isinstance(current_expiry, str):
            current_expiry = datetime.strptime(current_expiry, '%Y-%m-%d').date()
        
        # Add approximately a month
        if current_expiry.month == 12:
            next_month = 1
            next_year = current_expiry.year + 1
        else:
            next_month = current_expiry.month + 1
            next_year = current_expiry.year
        
        # Find last Thursday of next month
        if next_month == 12:
            next_month_days = 31
        elif next_month in [4, 6, 9, 11]:
            next_month_days = 30
        elif next_month == 2:
            if next_year % 4 == 0 and (next_year % 100 != 0 or next_year % 400 == 0):
                                next_month_days = 28
        
        # Find the last Thursday of the month
        last_day = next_month_days
        last_thursday = None
        
        while last_thursday is None:
            try:
                candidate = datetime(next_year, next_month, last_day)
                if candidate.weekday() == 3:  # Thursday is 3 (0-based, Monday is 0)
                    last_thursday = candidate.date()
                else:
                    last_day -= 1
            except ValueError:
                last_day -= 1
        
        return last_thursday
    
    def _get_option_chain_by_expiry(self, symbol, expiry):
        """Get option chain for a specific expiry date"""
        # In a real implementation, this would fetch from the API
        # This is a simplified mock implementation
        
        # For now, just return a copy of the nearest expiry with modified expiry date
        nearest_chain = self.market_data.get_option_chain_snapshot(symbol)
        if not nearest_chain:
            return None
            
        # Create a copy and update expiry
        far_chain = copy.deepcopy(nearest_chain)
        far_chain['expiry'] = expiry
        
        # Adjust prices to simulate higher IV for farther expiry
        for option in far_chain['data']:
            if option['call_price']:
                option['call_price'] *= 1.15  # 15% higher premium for farther expiry
            if option['put_price']:
                option['put_price'] *= 1.15
        
        return far_chain
    
    def _find_atm_option(self, option_chain, underlying_price):
        """Find the ATM option in an option chain"""
        closest_strike = min(option_chain['data'], key=lambda x: abs(x['strike'] - underlying_price))['strike']
        
        for option in option_chain['data']:
            if option['strike'] == closest_strike:
                if option['call_id'] and option['call_price']:
                    return {
                        'instrument_id': option['call_id'],
                        'price': option['call_price'],
                        'strike': option['strike'],
                        'type': 'ce'
                    }
        
        return None
    
    def _estimate_iv(self, option_price, underlying_price, strike, days_to_expiry):
        """
        Estimate implied volatility from option price
        Note: This is a simplified approximation - real IV calculation would use options pricing models
        """
        # Very simplified IV approximation
        # In a real system, you would use Black-Scholes or other pricing models
        moneyness = abs(underlying_price - strike) / underlying_price
        time_factor = math.sqrt(days_to_expiry / 365)
        
        if time_factor == 0:
            return 0
            
        # Rough approximation
        iv_estimate = (option_price / (underlying_price * 0.4)) * (1 + moneyness) / time_factor
        
        # Clamp to reasonable values
        return min(max(iv_estimate * 100, 10), 100)  # Return as percentage between 10 and 100
    
    def _find_atm_straddle(self, option_chain, underlying_price):
        """Find ATM straddle (call and put at the same strike closest to underlying price)"""
        closest_strike = min(option_chain['data'], key=lambda x: abs(x['strike'] - underlying_price))['strike']
        
        atm_call = None
        atm_put = None
        
        for option in option_chain['data']:
            if option['strike'] == closest_strike:
                if option['call_id'] and option['call_price']:
                    atm_call = {
                        'id': option['call_id'],
                        'price': option['call_price'],
                        'strike': option['strike']
                    }
                
                if option['put_id'] and option['put_price']:
                    atm_put = {
                        'id': option['put_id'],
                        'price': option['put_price'],
                        'strike': option['strike']
                    }
                
                break
        
        return atm_call, atm_put
    
    def _find_otm_options(self, option_chain, underlying_price):
        """Find slightly OTM options for a strangle"""
        # Calculate strikes about 2-3% OTM
        call_target_strike = underlying_price * 1.025
        put_target_strike = underlying_price * 0.975
        
        # Find closest strikes to targets
        otm_call = None
        otm_put = None
        
        for option in option_chain['data']:
            # Find call option
            if option['strike'] > underlying_price and option['call_id'] and option['call_price']:
                if otm_call is None or abs(option['strike'] - call_target_strike) < abs(otm_call['strike'] - call_target_strike):
                    otm_call = {
                        'id': option['call_id'],
                        'price': option['call_price'],
                        'strike': option['strike']
                    }
            
            # Find put option
            if option['strike'] < underlying_price and option['put_id'] and option['put_price']:
                if otm_put is None or abs(option['strike'] - put_target_strike) < abs(otm_put['strike'] - put_target_strike):
                    otm_put = {
                        'id': option['put_id'],
                        'price': option['put_price'],
                        'strike': option['strike']
                    }
        
        return otm_call, otm_put
    
    def _calculate_weighted_iv(self, option_chain, underlying_price):
        """Calculate weighted implied volatility from ATM options"""
        # Find ATM and near-ATM options
        atm_options = []
        
        for option in option_chain['data']:
            # Consider options within 2% of current price
            if abs(option['strike'] - underlying_price) / underlying_price <= 0.02:
                if option['call_id'] and option['call_price']:
                    iv = self._estimate_iv(option['call_price'], underlying_price, option['strike'], 
                                          self._get_days_to_expiry(option_chain['expiry']))
                    weight = 1 - abs(option['strike'] - underlying_price) / underlying_price / 0.02
                    atm_options.append((iv, weight))
                
                if option['put_id'] and option['put_price']:
                    iv = self._estimate_iv(option['put_price'], underlying_price, option['strike'], 
                                          self._get_days_to_expiry(option_chain['expiry']))
                    weight = 1 - abs(option['strike'] - underlying_price) / underlying_price / 0.02
                    atm_options.append((iv, weight))
        
        if not atm_options:
            return None
            
        # Calculate weighted average
        total_weight = sum(weight for _, weight in atm_options)
        weighted_iv = sum(iv * weight for iv, weight in atm_options) / total_weight if total_weight > 0 else 0
        
        return weighted_iv
    
    def _calculate_realized_volatility(self, symbol, lookback_days):
        """Calculate historical realized volatility"""
        # In a real implementation, this would use actual historical price data
        # This is a simplified mock implementation
        
        # Get instrument ID
        for instrument_id, instrument in self.market_data.subscribed_instruments.items():
            if instrument['symbol'] == symbol:
                if instrument_id in self.market_data.timeframes['D']:
                    # Calculate daily returns
                    closes = self.market_data.timeframes['D'][instrument_id]['close']
                    if len(closes) < lookback_days:
                        return None
                        
                    returns = np.diff(np.log(closes[-lookback_days:]))
                    
                    # Annualized volatility
                    return np.std(returns) * np.sqrt(252) * 100  # Convert to percentage
                break
                
        # If we don't have sufficient data, estimate based on VIX
        vix_value = self._get_vix_value()
        if vix_value is not None:
            # Adjust VIX based on asset (Nifty usually slightly less volatile than VIX)
            if symbol == "NIFTY":
                return vix_value * 0.9
            elif symbol == "BANKNIFTY":
                return vix_value * 1.1
            else:
                return vix_value
        
        return 20  # Default value if all else fails
    
    def _calculate_iv_rank(self, symbol):
        """Calculate IV Rank (current IV percentile within its 52-week range)"""
        # In a real implementation, this would use actual historical IV data
        # For now, return a random value between 0-100 for demonstration
        import random
        return random.uniform(30, 80)
    
    def _calculate_atr_for_underlying(self, symbol):
        """Calculate Average True Range for underlying"""
        # Find instrument ID for the symbol
        instrument_id = None
        for id_, instrument in self.market_data.subscribed_instruments.items():
            if instrument['symbol'] == symbol:
                instrument_id = id_
                break
        
        if not instrument_id:
            return None
        
        # Check if we have daily data
        if instrument_id not in self.market_data.timeframes['D']:
            return None
        
        # Get OHLC data
        high = self.market_data.timeframes['D'][instrument_id]['high']
        low = self.market_data.timeframes['D'][instrument_id]['low']
        close = self.market_data.timeframes['D'][instrument_id]['close']
        
        if len(high) < 14:  # Need at least 14 days of data
            return None
        
        # Calculate true range
        tr = []
        for i in range(1, len(high)):
            tr1 = high[i] - low[i]
            tr2 = abs(high[i] - close[i-1])
            tr3 = abs(low[i] - close[i-1])
            tr.append(max(tr1, tr2, tr3))
        
        # Calculate ATR (14-day average)
        atr = sum(tr[-14:]) / 14
        
        return atr
    
        def _calculate_margin_requirement_for_straddle(self, call_id, put_id, quantity):
        """Calculate margin requirement for a straddle position"""
        # In a real implementation, this would calculate actual margin based on exchange rules
        # This is a simplified approximation
        
        call_price = 0
        put_price = 0
        
        # Get prices from market data
        for instrument_id, instrument in self.market_data.subscribed_instruments.items():
            if instrument_id == call_id:
                call_price = instrument.get('last_price', 0)
            elif instrument_id == put_id:
                put_price = instrument.get('last_price', 0)
        
        # For short straddle, use a conservative estimate (approximately 3x the premium)
        return (call_price + put_price) * quantity * self._get_lot_size(call_id) * 3
    
    def _log_system_status(self):
        """Log current system status"""
        try:
            # Get key metrics
            active_strategies = [s['name'] for s in self.strategies if s['enabled']]
            capital_info = self.capital_allocator.get_allocation_report()
            risk_metrics = self.risk_manager.get_risk_metrics()
            
            # Create status log
            status = {
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'active_strategies': len(active_strategies),
                'capital_available': capital_info['available_capital'],
                'capital_allocated': capital_info['allocated_capital'],
                'capital_utilization': f"{capital_info['allocation_percentage']:.1f}%",
                'risk_level': "High" if risk_metrics['risk_breached'] else "Normal",
                'pending_signals': self.signal_queue.qsize()
            }
            
            logger.info(f"Status: {json.dumps(status)}")
        
        except Exception as e:
            logger.error(f"Error logging system status: {e}")
    
    def _get_market_regime(self):
        """Determine current market regime based on VIX and other indicators"""
        try:
            # Get VIX value
            vix_value = self._get_vix_value()
            if not vix_value:
                return "unknown"
            
            # Get market trend data (simplified using Nifty)
            trend = "neutral"
            nifty_price = self._get_index_price("NIFTY 50")
            
            if nifty_price:
                # Check if we have indicators for Nifty
                for inst_id, inst in self.market_data.subscribed_instruments.items():
                    if inst['symbol'] == "NIFTY 50" and inst_id in self.market_data.indicators:
                        indicators = self.market_data.indicators[inst_id]
                        
                        # Use EMAs to determine trend
                        if 'ema9_1h' in indicators and 'ema21_1h' in indicators:
                            if indicators['ema9_1h'] > indicators['ema21_1h']:
                                trend = "bullish"
                            elif indicators['ema9_1h'] < indicators['ema21_1h']:
                                trend = "bearish"
            
            # Determine volatility regime
            if vix_value < 15:
                vol_regime = "low"
            elif vix_value < 25:
                vol_regime = "medium"
            elif vix_value < 35:
                vol_regime = "high"
            else:
                vol_regime = "extreme"
            
            # Combine trend and volatility to get market regime
            regime = f"{trend}_{vol_regime}"
            
            return regime
        
        except Exception as e:
            logger.error(f"Error determining market regime: {e}")
            return "unknown"
    
    def _calculate_strategy_effectiveness(self):
        """Calculate the effectiveness of each strategy based on historical performance"""
        try:
            # Get closed position history
            positions = self.position_manager.get_position_history()
            
            # Group by strategy
            strategy_stats = {}
            
            for position in positions:
                strategy = position.get('strategy', 'unknown')
                
                if strategy not in strategy_stats:
                    strategy_stats[strategy] = {
                        'win_count': 0,
                        'loss_count': 0,
                        'total_profit': 0,
                        'total_loss': 0,
                        'max_profit': 0,
                        'max_loss': 0,
                        'avg_holding_time': []
                    }
                
                # Calculate P&L
                pnl = position.get('pnl', 0)
                
                # Calculate holding time
                entry_time = position.get('entry_time')
                exit_time = position.get('exit_time')
                
                if entry_time and exit_time:
                    holding_time = (exit_time - entry_time).total_seconds() / 3600  # hours
                    strategy_stats[strategy]['avg_holding_time'].append(holding_time)
                
                # Update stats based on P&L
                if pnl >= 0:
                    strategy_stats[strategy]['win_count'] += 1
                    strategy_stats[strategy]['total_profit'] += pnl
                    strategy_stats[strategy]['max_profit'] = max(strategy_stats[strategy]['max_profit'], pnl)
                else:
                    strategy_stats[strategy]['loss_count'] += 1
                    strategy_stats[strategy]['total_loss'] += abs(pnl)
                    strategy_stats[strategy]['max_loss'] = max(strategy_stats[strategy]['max_loss'], abs(pnl))
            
            # Calculate effectiveness metrics
            strategy_effectiveness = {}
            
            for strategy, stats in strategy_stats.items():
                total_trades = stats['win_count'] + stats['loss_count']
                
                if total_trades == 0:
                    continue
                
                win_rate = stats['win_count'] / total_trades if total_trades > 0 else 0
                
                # Profit factor: total profit / total loss
                profit_factor = stats['total_profit'] / stats['total_loss'] if stats['total_loss'] > 0 else float('inf')
                
                # Calculate average holding time
                avg_holding_time = sum(stats['avg_holding_time']) / len(stats['avg_holding_time']) if stats['avg_holding_time'] else 0
                
                # Calculate Sharpe-like ratio
                if stats['total_profit'] > 0 and len(stats['avg_holding_time']) > 0:
                    reward_to_time_ratio = stats['total_profit'] / sum(stats['avg_holding_time'])
                else:
                    reward_to_time_ratio = 0
                
                # Calculate effectiveness score (custom metric)
                if profit_factor == float('inf'):
                    effectiveness_score = win_rate * 100
                else:
                    effectiveness_score = win_rate * profit_factor * 100
                
                strategy_effectiveness[strategy] = {
                    'win_rate': win_rate,
                    'profit_factor': profit_factor,
                    'avg_holding_time': avg_holding_time,
                    'reward_to_time_ratio': reward_to_time_ratio,
                    'effectiveness_score': effectiveness_score,
                    'total_trades': total_trades
                }
            
            return strategy_effectiveness
        
        except Exception as e:
            logger.error(f"Error calculating strategy effectiveness: {e}")
            return {}
    
    def adjust_strategy_weights(self):
        """Dynamically adjust strategy weights based on performance"""
        try:
            # Get strategy effectiveness
            effectiveness = self._calculate_strategy_effectiveness()
            
            if not effectiveness:
                return
            
            # Get current market regime
            market_regime = self._get_market_regime()
            
            # Adjust strategy enablement based on effectiveness and market regime
            for strategy in self.strategies:
                strategy_name = strategy['name']
                
                # Skip if no data
                if strategy_name not in effectiveness:
                    continue
                
                metrics = effectiveness[strategy_name]
                
                # Basic rules for strategy enablement
                # 1. Disable strategies with very poor performance
                if metrics['total_trades'] >= 10 and metrics['effectiveness_score'] < 20:
                    strategy['enabled'] = False
                    logger.info(f"Disabled {strategy_name} due to poor performance (score: {metrics['effectiveness_score']:.1f})")
                
                # 2. Enable high-performing strategies
                elif metrics['total_trades'] >= 5 and metrics['effectiveness_score'] > 80:
                    strategy['enabled'] = True
                    logger.info(f"Enabled {strategy_name} due to strong performance (score: {metrics['effectiveness_score']:.1f})")
                
                # 3. Market regime specific adjustments
                if "low" in market_regime and strategy_name in ['volatility_arbitrage', 'dynamic_iron_condor']:
                    # Low volatility isn't good for volatility selling strategies
                    strategy['enabled'] = False
                    logger.info(f"Disabled {strategy_name} due to low volatility regime")
                
                elif "extreme" in market_regime and strategy_name in ['mean_reversion']:
                    # Extreme volatility isn't good for mean reversion
                    strategy['enabled'] = False
                    logger.info(f"Disabled {strategy_name} due to extreme volatility regime")
                
                elif "bullish" in market_regime and strategy_name in ['options_chain_imbalance']:
                    # Enable trend-following strategies in clear trends
                    strategy['enabled'] = True
                    logger.info(f"Enabled {strategy_name} in bullish regime")
        
        except Exception as e:
            logger.error(f"Error adjusting strategy weights: {e}")
    
    def get_active_strategies(self):
        """Get list of currently active strategies"""
        return [s for s in self.strategies if s['enabled']]
    
    def enable_strategy(self, strategy_name):
        """Enable a specific strategy by name"""
        for strategy in self.strategies:
            if strategy['name'] == strategy_name:
                strategy['enabled'] = True
                logger.info(f"Enabled strategy: {strategy_name}")
                return True
        return False
    
    def disable_strategy(self, strategy_name):
        """Disable a specific strategy by name"""
        for strategy in self.strategies:
            if strategy['name'] == strategy_name:
                strategy['enabled'] = False
                logger.info(f"Disabled strategy: {strategy_name}")
                return True
        return False
    
    def get_strategy_stats(self):
        """Get statistics for all strategies"""
        effectiveness = self._calculate_strategy_effectiveness()
        
        stats = {}
        for strategy in self.strategies:
            name = strategy['name']
            stats[name] = {
                'enabled': strategy['enabled'],
                'type': strategy['type'],
                'description': strategy['description']
            }
            
            # Add effectiveness metrics if available
            if name in effectiveness:
                stats[name].update(effectiveness[name])
        
        return stats