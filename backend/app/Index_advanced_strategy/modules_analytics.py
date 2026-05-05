"""
Performance Analytics module for tracking and analyzing trading performance
"""
import logging
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import threading
import time
import json
import os

logger = logging.getLogger(__name__)

class PerformanceAnalytics:
    def __init__(self):
        self.metrics = {
            'daily_pnl': [],
            'cumulative_pnl': [],
            'drawdowns': [],
            'sharpe_ratio': None,
            'sortino_ratio': None,
            'win_rate': None,
            'profit_factor': None,
            'max_drawdown': None
        }
        
        self.trades = []
        self.daily_snapshots = []
        self.start_date = datetime.now().date()
        
        # Track daily metrics
        self.today_date = datetime.now().date()
        self.today_trades = []
        self.today_starting_equity = 0
        self.today_ending_equity = 0
        
        self.lock = threading.RLock()
    
    def add_trade(self, trade_data):
        """Add a completed trade to analytics"""
        with self.lock:
            self.trades.append(trade_data)
            
            # Add to today's trades if applicable
            if trade_data.get('exit_time').date() == self.today_date:
                self.today_trades.append(trade_data)
                
            # Recalculate metrics when new trade is added
            self._calculate_metrics()
    
    def update_daily_snapshot(self, account_value, positions=None):
        """Update daily account snapshot"""
        today = datetime.now().date()
        
        with self.lock:
            # Check if this is a new day
            if today != self.today_date:
                # Save previous day's snapshot
                if self.today_ending_equity > 0:
                    daily_pnl = self.today_ending_equity - self.today_starting_equity
                    daily_pnl_pct = daily_pnl / self.today_starting_equity if self.today_starting_equity > 0 else 0
                    
                    snapshot = {
                        'date': self.today_date,
                        'starting_equity': self.today_starting_equity,
                        'ending_equity': self.today_ending_equity,
                        'daily_pnl': daily_pnl,
                        'daily_pnl_pct': daily_pnl_pct,
                        'trade_count': len(self.today_trades),
                        'win_count': sum(1 for t in self.today_trades if t.get('pnl', 0) >= 0),
                        'loss_count': sum(1 for t in self.today_trades if t.get('pnl', 0) < 0)
                    }
                    
                    self.daily_snapshots.append(snapshot)
                
                # Reset for new day
                self.today_date = today
                self.today_starting_equity = account_value
                self.today_trades = []
            
            # Update today's ending equity
            self.today_ending_equity = account_value
            
            # Calculate daily P&L
            if self.today_starting_equity > 0:
                daily_pnl = self.today_ending_equity - self.today_starting_equity
                daily_pnl_pct = daily_pnl / self.today_starting_equity
                
                # Add to metrics
                if len(self.metrics['daily_pnl']) == 0 or self.metrics['daily_pnl'][-1]['date'] != today:
                    self.metrics['daily_pnl'].append({
                        'date': today,
                        'pnl': daily_pnl,
                        'pnl_pct': daily_pnl_pct
                    })
                else:
                    # Update today's entry
                    self.metrics['daily_pnl'][-1]['pnl'] = daily_pnl
                    self.metrics['daily_pnl'][-1]['pnl_pct'] = daily_pnl_pct
                
                # Recalculate cumulative P&L
                self._calculate_cumulative_pnl()
    
    def reset_daily_metrics(self):
        """Reset daily metrics for a new trading day"""
        with self.lock:
            # Save current daily snapshot if needed
            self.update_daily_snapshot(self.today_ending_equity)
            
            # Reset daily tracking
            self.today_trades = []
            self.today_starting_equity = self.today_ending_equity
    
    def update_performance_metrics(self):
        """Update all performance metrics"""
        with self.lock:
            self._calculate_metrics()
            
            # Log current performance summary
            self._log_performance_summary()
    
    def _calculate_metrics(self):
        """Calculate all performance metrics"""
        self._calculate_win_rate()
        self._calculate_profit_factor()
        self._calculate_drawdowns()
        self._calculate_sharpe_ratio()
        self._calculate_sortino_ratio()
    
    def _calculate_win_rate(self):
        """Calculate win rate from trades"""
        if not self.trades:
            self.metrics['win_rate'] = None
            return
            
        win_count = sum(1 for trade in self.trades if trade.get('pnl', 0) >= 0)
        total_trades = len(self.trades)
        
        self.metrics['win_rate'] = win_count / total_trades if total_trades > 0 else 0
    
    def _calculate_profit_factor(self):
        """Calculate profit factor (gross profit / gross loss)"""
        if not self.trades:
            self.metrics['profit_factor'] = None
            return
            
        gross_profit = sum(trade.get('pnl', 0) for trade in self.trades if trade.get('pnl', 0) > 0)
        gross_loss = sum(abs(trade.get('pnl', 0)) for trade in self.trades if trade.get('pnl', 0) < 0)
        
        self.metrics['profit_factor'] = gross_profit / gross_loss if gross_loss > 0 else float('inf')
    
    def _calculate_drawdowns(self):
        """Calculate drawdowns from equity curve"""
        if not self.metrics['cumulative_pnl']:
            self.metrics['drawdowns'] = []
            self.metrics['max_drawdown'] = None
            return
            
        # Extract equity values
        equity_curve = [point['equity'] for point in self.metrics['cumulative_pnl']]
        
        # Calculate drawdowns
        max_so_far = equity_curve[0]
        drawdowns = []
        
        for i, equity in enumerate(equity_curve):
            if equity > max_so_far:
                max_so_far = equity
            
            drawdown = (max_so_far - equity) / max_so_far if max_so_far > 0 else 0
            drawdowns.append(drawdown)
        
        # Store drawdown curve
        self.metrics['drawdowns'] = [
            {'date': self.metrics['cumulative_pnl'][i]['date'], 'drawdown': dd}
            for i, dd in enumerate(drawdowns)
        ]
        
        # Calculate max drawdown
        self.metrics['max_drawdown'] = max(drawdowns) if drawdowns else 0
    
    def _calculate_sharpe_ratio(self):
        """Calculate Sharpe ratio from daily returns"""
        if len(self.metrics['daily_pnl']) < 5:  # Need some data for meaningful calculation
            self.metrics['sharpe_ratio'] = None
            return
            
        # Extract daily returns
        daily_returns = [day['pnl_pct'] for day in self.metrics['daily_pnl']]
        
        # Calculate annualized Sharpe ratio
        # Assuming 252 trading days in a year
        mean_return = np.mean(daily_returns)
        std_return = np.std(daily_returns)
        
        if std_return > 0:
            sharpe = mean_return / std_return * np.sqrt(252)
        else:
            sharpe = 0
            
        self.metrics['sharpe_ratio'] = sharpe
    
    def _calculate_sortino_ratio(self):
        """Calculate Sortino ratio from daily returns (only penalizes downside deviation)"""
        if len(self.metrics['daily_pnl']) < 5:  # Need some data for meaningful calculation
            self.metrics['sortino_ratio'] = None
            return
            
        # Extract daily returns
        daily_returns = [day['pnl_pct'] for day in self.metrics['daily_pnl']]
        
        # Calculate downside returns
        downside_returns = [r for r in daily_returns if r < 0]
        
        # Calculate annualized Sortino ratio
        mean_return = np.mean(daily_returns)
        downside_std = np.std(downside_returns) if downside_returns else 0
        
        if downside_std > 0:
            sortino = mean_return / downside_std * np.sqrt(252)
        else:
            sortino = 0
            
        self.metrics['sortino_ratio'] = sortino
    
    def _calculate_cumulative_pnl(self):
        """Calculate cumulative P&L from daily P&L"""
        if not self.metrics['daily_pnl']:
            return
            
        # Start with initial equity
        if not self.metrics['cumulative_pnl']:
            initial_equity = self.today_starting_equity - self.metrics['daily_pnl'][0]['pnl']
        else:
            initial_equity = self.metrics['cumulative_pnl'][0]['equity']
        
        # Recalculate the entire equity curve
        cumulative = []
        current_equity = initial_equity
        
        for day in self.metrics['daily_pnl']:
            current_equity += day['pnl']
            cumulative.append({
                'date': day['date'],
                'equity': current_equity,
                'daily_pnl': day['pnl'],
                'daily_pnl_pct': day['pnl_pct']
            })
        
        self.metrics['cumulative_pnl'] = cumulative
    
    def _log_performance_summary(self):
        """Log a summary of current performance"""
        summary = {
            'win_rate': f"{self.metrics['win_rate'] * 100:.1f}%" if self.metrics['win_rate'] is not None else "N/A",
            'profit_factor': f"{self.metrics['profit_factor']:.2f}" if self.metrics['profit_factor'] is not None else "N/A",
            'max_drawdown': f"{self.metrics['max_drawdown'] * 100:.1f}%" if self.metrics['max_drawdown'] is not None else "N/A",
            'sharpe_ratio': f"{self.metrics['sharpe_ratio']:.2f}" if self.metrics['sharpe_ratio'] is not None else "N/A",
            'sortino_ratio': f"{self.metrics['sortino_ratio']:.2f}" if self.metrics['sortino_ratio'] is not None else "N/A",
            'total_trades': len(self.trades),
            'days_active': (datetime.now().date() - self.start_date).days + 1
        }
        
        if self.metrics['cumulative_pnl']:
            latest = self.metrics['cumulative_pnl'][-1]
            start = self.metrics['cumulative_pnl'][0]['equity']
            end = latest['equity']
            
            summary['current_equity'] = end
            summary['total_return'] = f"{(end - start) / start * 100:.1f}%"
        
        logger.info(f"Performance Summary: {json.dumps(summary)}")
    
    def get_performance_metrics(self):
        """Get current performance metrics"""
        with self.lock:
            return {
                'win_rate': self.metrics['win_rate'],
                'profit_factor': self.metrics['profit_factor'],
                'max_drawdown': self.metrics['max_drawdown'],
                'sharpe_ratio': self.metrics['sharpe_ratio'],
                'sortino_ratio': self.metrics['sortino_ratio'],
                'total_trades': len(self.trades),
                'equity_curve': self.metrics['cumulative_pnl'][-10:] if self.metrics['cumulative_pnl'] else [],
                'daily_pnl': self.metrics['daily_pnl'][-10:] if self.metrics['daily_pnl'] else []
            }
    
    def save_analytics_data(self, directory="analytics"):
        """Save analytics data to files"""
        try:
            # Create directory if it doesn't exist
            os.makedirs(directory, exist_ok=True)
            
            with self.lock:
                # Save trades
                trades_file = os.path.join(directory, "trades.json")
                with open(trades_file, 'w') as f:
                    json.dump(self.trades, f, default=str, indent=4)
                
                # Save daily snapshots
                snapshots_file = os.path.join(directory, "daily_snapshots.json")
                with open(snapshots_file, 'w') as f:
                    json.dump(self.daily_snapshots, f, default=str, indent=4)
                
                # Save metrics
                metrics_file = os.path.join(directory, "metrics.json")
                with open(metrics_file, 'w') as f:
                    json.dump(self.metrics, f, default=str, indent=4)
            
            logger.info(f"Analytics data saved to {directory} directory")
            return True
        
        except Exception as e:
            logger.error(f"Error saving analytics data: {e}", exc_info=True)
            return False