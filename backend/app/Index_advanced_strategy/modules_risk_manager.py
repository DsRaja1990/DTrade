"""
Risk Manager for controlling trading risk parameters
"""
import logging
import numpy as np
from datetime import datetime, time as dt_time
import threading
import time

logger = logging.getLogger(__name__)

class RiskManager:
    def __init__(self, api_connector, max_capital_at_risk=0.05, max_position_size=0.15, 
                 max_correlated_risk=0.2, daily_loss_limit=0.03, overnight_limit=0.5):
        self.api = api_connector
        self.max_capital_at_risk = max_capital_at_risk  # Max % of capital at risk at any time
        self.max_position_size = max_position_size      # Max % of capital in single position
        self.max_correlated_risk = max_correlated_risk  # Max % in correlated positions
        self.daily_loss_limit = daily_loss_limit        # Daily stop loss as % of capital
        self.overnight_limit = overnight_limit          # Max % of capital to hold overnight
        
        self.starting_capital = 0  # Will be updated at start of day
        self.current_capital = 0   # Will be updated regularly
        self.daily_pnl = 0         # Running P&L for the day
        self.positions_risk = {}   # Risk metrics for each position
        
        self.lock = threading.RLock()
        self.risk_breached = False  # Flag to indicate if risk parameters have been breached
        
        # Correlation matrix for instruments
        # Will be populated with calculated values in a real implementation
        self.correlation_matrix = {}
        
        # Risk monitoring thread
        self.monitoring = False
        self.monitor_thread = None
    
    def initialize(self, capital):
        """Initialize risk manager with starting capital"""
        with self.lock:
            self.starting_capital = capital
            self.current_capital = capital
            self.daily_pnl = 0
            self.risk_breached = False
            logger.info(f"Risk manager initialized with {capital} capital")
    
    def start_monitoring(self):
        """Start risk monitoring in a separate thread"""
        if self.monitoring:
            return
            
        self.monitoring = True
        self.monitor_thread = threading.Thread(target=self._risk_monitor_loop)
        self.monitor_thread.daemon = True
        self.monitor_thread.start()
        logger.info("Risk monitoring started")
    
    def stop_monitoring(self):
        """Stop risk monitoring"""
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
            self.monitor_thread = None
        logger.info("Risk monitoring stopped")
    
    def _risk_monitor_loop(self):
        """Continuous risk monitoring loop"""
        while self.monitoring:
            try:
                self.check_risk_parameters()
                time.sleep(5)  # Check every 5 seconds
            except Exception as e:
                logger.error(f"Error in risk monitoring: {e}", exc_info=True)
    
    def check_risk_parameters(self):
        """Check all risk parameters and take actions if limits are breached"""
        with self.lock:
            # Update current capital from account value
            account_value = self._get_account_value()
            if account_value > 0:
                self.current_capital = account_value
            
            # Update daily P&L
            self.daily_pnl = self.current_capital - self.starting_capital
            
            # Check risk limits
            risk_status = {
                'capital_at_risk': self._check_capital_at_risk(),
                'daily_loss_limit': self._check_daily_loss_limit(),
                'position_size': self._check_position_sizes(),
                'correlated_risk': self._check_correlated_risk()
            }
            
            # Check if any risk parameters are breached
            any_breached = any(risk_status.values())
            
            # If risk state changes, log it
            if any_breached != self.risk_breached:
                if any_breached:
                    logger.warning("Risk parameters breached!")
                    for param, breached in risk_status.items():
                        if breached:
                            logger.warning(f"Risk breach: {param}")
                else:
                    logger.info("Risk parameters returned to acceptable levels")
                
                self.risk_breached = any_breached
    
    def _check_capital_at_risk(self):
        """Check if total capital at risk exceeds limit"""
        total_risk = sum(pos.get('current_risk', 0) for pos in self.positions_risk.values())
        risk_percentage = total_risk / self.current_capital if self.current_capital > 0 else 0
        
        return risk_percentage > self.max_capital_at_risk
    
    def _check_daily_loss_limit(self):
        """Check if daily loss limit is exceeded"""
        daily_loss_percentage = -self.daily_pnl / self.starting_capital if self.starting_capital > 0 else 0
        
        return daily_loss_percentage > self.daily_loss_limit
    
    def _check_position_sizes(self):
        """Check if any position size exceeds limit"""
        for pos_id, position in self.positions_risk.items():
            position_size = position.get('position_size', 0)
            if position_size > self.max_position_size:
                return True
        
        return False
    
    def _check_correlated_risk(self):
        """Check if correlated positions exceed risk limit"""
        # This is a simplified implementation
        # In a real system, you would use actual correlation calculations
        
        # Group positions by underlying or sector
        groups = {}
        for pos_id, position in self.positions_risk.items():
            underlying = position.get('underlying', 'unknown')
            if underlying not in groups:
                groups[underlying] = 0
            groups[underlying] += position.get('position_size', 0)
        
        # Check if any group exceeds the limit
        for underlying, size in groups.items():
            if size > self.max_correlated_risk:
                return True
        
        return False
    
    def validate_trade(self, signal):
        """Validate if a trade should be executed based on risk parameters"""
        with self.lock:
            # Check if risk limits are already breached
            if self.risk_breached:
                logger.warning(f"Trade rejected - risk parameters already breached: {signal}")
                return False
            
            # Check position sizing
            if signal.get('capital_required'):
                position_size_pct = signal['capital_required'] / self.current_capital
                if position_size_pct > self.max_position_size:
                    logger.warning(f"Trade rejected - position size too large ({position_size_pct:.1%}): {signal}")
                    return False
            
            # Check time of day (avoid trading near market close)
            now = datetime.now().time()
            if now > dt_time(15, 15):  # After 3:15 PM
                logger.warning(f"Trade rejected - too close to market close: {signal}")
                return False
            
            # Strategy-specific risk checks
            strategy_type = signal.get('strategy_type', '')
            
            if strategy_type == 'volatility_arbitrage':
                # Additional checks for volatility arbitrage
                pass
                
            elif strategy_type == 'options_chain_imbalance':
                # Additional checks for options chain imbalance
                pass
            
            return True
    
    def update_position_risk(self, position_id, risk_metrics):
        """Update risk metrics for a position"""
        with self.lock:
            self.positions_risk[position_id] = risk_metrics
    
    def remove_position_risk(self, position_id):
        """Remove a position from risk tracking"""
        with self.lock:
            if position_id in self.positions_risk:
                del self.positions_risk[position_id]
    
    def should_close_positions(self):
        """Determine if positions should be closed based on risk parameters"""
        with self.lock:
            # Close positions if daily loss limit is breached
            if self._check_daily_loss_limit():
                logger.warning("Daily loss limit breached - should close positions")
                return True
            
            # Close positions if total risk exceeds threshold by 20%
            total_risk = sum(pos.get('current_risk', 0) for pos in self.positions_risk.values())
            risk_percentage = total_risk / self.current_capital if self.current_capital > 0 else 0
            
            if risk_percentage > self.max_capital_at_risk * 1.2:
                logger.warning(f"Total risk ({risk_percentage:.1%}) exceeds limit - should close positions")
                return True
            
            return False
    
    def should_close_eod_positions(self):
        """Check if end-of-day positions should be closed"""
        with self.lock:
            # Calculate total value of positions
            total_position_value = sum(pos.get('current_value', 0) for pos in self.positions_risk.values())
            position_percentage = total_position_value / self.current_capital if self.current_capital > 0 else 0
            
            # Check if positions exceed overnight limit
            if position_percentage > self.overnight_limit:
                logger.warning(f"Positions ({position_percentage:.1%}) exceed overnight limit - should close EOD")
                return True
            
            # Check time of day (close positions after 3:20 PM)
            now = datetime.now().time()
            if now > dt_time(15, 20):  # After 3:20 PM
                # Only close if positions exceed 50% of overnight limit
                if position_percentage > self.overnight_limit * 0.5:
                    logger.info("Market closing soon - should close remaining positions")
                    return True
            
            return False
    
    def get_risk_metrics(self):
        """Get current risk metrics"""
        with self.lock:
            return {
                'current_capital': self.current_capital,
                'daily_pnl': self.daily_pnl,
                'daily_pnl_percentage': self.daily_pnl / self.starting_capital if self.starting_capital > 0 else 0,
                'capital_at_risk': sum(pos.get('current_risk', 0) for pos in self.positions_risk.values()),
                'capital_at_risk_percentage': sum(pos.get('current_risk', 0) for pos in self.positions_risk.values()) / self.current_capital if self.current_capital > 0 else 0,
                'position_count': len(self.positions_risk),
                'risk_breached': self.risk_breached
            }
    
    def _get_account_value(self):
        """Get current account value from API"""
        try:
            account = self.api.get_account_balance()
            # Extract and return account value
            if account and 'data' in account and 'available_cash' in account['data']:
                return float(account['data']['available_cash'])
        except Exception as e:
            logger.error(f"Error getting account value: {e}")
        
        # If there's an error, return current value
        return self.current_capital