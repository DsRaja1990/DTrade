"""
Capital Allocator for managing trading capital
"""
import logging
import threading
import time
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class CapitalAllocator:
    def __init__(self, initial_capital):
        self.initial_capital = initial_capital
        self.available_capital = initial_capital
        self.allocated_capital = 0
        self.strategy_allocations = {}  # Capital allocated to each strategy
        self.max_strategy_allocation = 0.25  # Max 25% of capital to a single strategy
        self.max_total_allocation = 0.90  # Max 90% of capital allocated at once
        
        # Track allocation history for analysis
        self.allocation_history = []
        
        self.lock = threading.RLock()
    
    def update_available_capital(self, new_capital):
        """Update the available capital"""
        with self.lock:
            old_capital = self.initial_capital
            self.initial_capital = new_capital
            
            # Adjust available capital proportionally
            if old_capital > 0:
                ratio = new_capital / old_capital
                self.available_capital *= ratio
            else:
                self.available_capital = new_capital - self.allocated_capital
            
            logger.info(f"Updated capital: {new_capital:.2f}, available: {self.available_capital:.2f}")
    
    def allocate_capital(self, strategy, required_capital):
        """
        Allocate capital to a strategy
        Returns the amount allocated (may be less than requested)
        """
        with self.lock:
            # Check if we have enough available capital
            if required_capital > self.available_capital:
                logger.warning(f"Insufficient capital for {strategy}: required={required_capital:.2f}, available={self.available_capital:.2f}")
                return 0
            
            # Check strategy allocation limits
            strategy_allocated = self.strategy_allocations.get(strategy, 0)
            strategy_limit = self.initial_capital * self.max_strategy_allocation
            
            if strategy_allocated + required_capital > strategy_limit:
                logger.warning(f"Strategy allocation limit exceeded for {strategy}: {strategy_allocated + required_capital:.2f} > {strategy_limit:.2f}")
                
                # Allocate only what's allowed
                allowed_additional = max(0, strategy_limit - strategy_allocated)
                if allowed_additional == 0:
                    return 0
                
                required_capital = min(required_capital, allowed_additional)
            
            # Check total allocation limit
            total_limit = self.initial_capital * self.max_total_allocation
            if self.allocated_capital + required_capital > total_limit:
                logger.warning(f"Total allocation limit exceeded: {self.allocated_capital + required_capital:.2f} > {total_limit:.2f}")
                
                # Allocate only what's allowed
                allowed_additional = max(0, total_limit - self.allocated_capital)
                if allowed_additional == 0:
                    return 0
                
                required_capital = min(required_capital, allowed_additional)
            
            # Allocate capital
            self.available_capital -= required_capital
            self.allocated_capital += required_capital
            
            # Update strategy allocation
            self.strategy_allocations[strategy] = strategy_allocated + required_capital
            
            # Record allocation
            self.allocation_history.append({
                'timestamp': datetime.now(),
                'strategy': strategy,
                'amount': required_capital,
                'type': 'allocate',
                'available_after': self.available_capital,
                'allocated_after': self.allocated_capital
            })
            
            logger.info(f"Allocated {required_capital:.2f} to {strategy}, available: {self.available_capital:.2f}")
            
            return required_capital
    
    def release_capital(self, strategy, amount):
        """Release capital back to the pool"""
        with self.lock:
            # Check strategy allocation
            strategy_allocated = self.strategy_allocations.get(strategy, 0)
            
            if strategy_allocated < amount:
                logger.warning(f"Cannot release more capital than allocated for {strategy}: {amount:.2f} > {strategy_allocated:.2f}")
                amount = strategy_allocated
            
            # Release capital
            self.available_capital += amount
            self.allocated_capital -= amount
            
            # Update strategy allocation
            self.strategy_allocations[strategy] = strategy_allocated - amount
            
            # Record allocation
            self.allocation_history.append({
                'timestamp': datetime.now(),
                'strategy': strategy,
                'amount': amount,
                'type': 'release',
                'available_after': self.available_capital,
                'allocated_after': self.allocated_capital
            })
            
            logger.info(f"Released {amount:.2f} from {strategy}, available: {self.available_capital:.2f}")
            
            return amount
    
    def get_available_capital(self):
        """Get available capital"""
        with self.lock:
            return self.available_capital
    
    def get_allocated_capital(self):
        """Get total allocated capital"""
        with self.lock:
            return self.allocated_capital
    
    def get_strategy_allocation(self, strategy):
        """Get capital allocated to a strategy"""
        with self.lock:
            return self.strategy_allocations.get(strategy, 0)
    
    def get_allocation_report(self):
        """Get a report of current allocations"""
        with self.lock:
            report = {
                'initial_capital': self.initial_capital,
                'available_capital': self.available_capital,
                'allocated_capital': self.allocated_capital,
                'allocation_percentage': self.allocated_capital / self.initial_capital * 100 if self.initial_capital > 0 else 0,
                'strategy_allocations': {
                    strategy: {
                        'amount': amount,
                        'percentage': amount / self.initial_capital * 100 if self.initial_capital > 0 else 0
                    }
                    for strategy, amount in self.strategy_allocations.items() if amount > 0
                }
            }
            
            return report