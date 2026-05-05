"""
Performance Analyzer for Backtesting

This module provides comprehensive performance analysis and reporting
for the time-based execution strategy backtest.
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
import json
import logging
from scipy import stats
from pathlib import Path

logger = logging.getLogger(__name__)

@dataclass
class PerformanceMetrics:
    """Comprehensive performance metrics"""
    # Return metrics
    total_return: float
    annualized_return: float
    volatility: float
    sharpe_ratio: float
    sortino_ratio: float
    calmar_ratio: float
    
    # Risk metrics
    max_drawdown: float
    var_95: float
    cvar_95: float
    beta: float
    
    # Trade metrics
    win_rate: float
    profit_factor: float
    avg_trade: float
    best_trade: float
    worst_trade: float
    
    # Execution metrics
    avg_slippage: float
    avg_execution_time: float
    fill_rate: float

class PerformanceAnalyzer:
    """
    Comprehensive performance analysis toolkit for backtesting results
    """

    def __init__(self, benchmark_return: float = 0.12):  # 12% benchmark return
        self.benchmark_return = benchmark_return
        self.risk_free_rate = 0.06  # 6% risk-free rate
        
    def analyze_performance(self, 
                          trades: List[Any],
                          daily_pnl: Dict[str, float],
                          initial_capital: float) -> PerformanceMetrics:
        """
        Comprehensive performance analysis
        
        Args:
            trades: List of trade objects
            daily_pnl: Dictionary of daily P&L
            initial_capital: Starting capital
            
        Returns:
            PerformanceMetrics object with all calculated metrics
        """
        
        # Convert daily P&L to returns
        daily_returns = self._calculate_daily_returns(daily_pnl, initial_capital)
        
        # Calculate return metrics
        total_return = self._calculate_total_return(daily_returns)
        annualized_return = self._calculate_annualized_return(daily_returns)
        volatility = self._calculate_volatility(daily_returns)
        
        # Risk-adjusted returns
        sharpe_ratio = self._calculate_sharpe_ratio(daily_returns)
        sortino_ratio = self._calculate_sortino_ratio(daily_returns)
        calmar_ratio = self._calculate_calmar_ratio(daily_returns)
        
        # Risk metrics
        max_drawdown = self._calculate_max_drawdown(daily_returns)
        var_95 = self._calculate_var(daily_returns, 0.05)
        cvar_95 = self._calculate_cvar(daily_returns, 0.05)
        beta = self._calculate_beta(daily_returns)
        
        # Trade analysis
        trade_metrics = self._analyze_trades(trades)
        
        # Execution analysis
        execution_metrics = self._analyze_execution(trades)
        
        return PerformanceMetrics(
            total_return=total_return,
            annualized_return=annualized_return,
            volatility=volatility,
            sharpe_ratio=sharpe_ratio,
            sortino_ratio=sortino_ratio,
            calmar_ratio=calmar_ratio,
            max_drawdown=max_drawdown,
            var_95=var_95,
            cvar_95=cvar_95,
            beta=beta,
            win_rate=trade_metrics['win_rate'],
            profit_factor=trade_metrics['profit_factor'],
            avg_trade=trade_metrics['avg_trade'],
            best_trade=trade_metrics['best_trade'],
            worst_trade=trade_metrics['worst_trade'],
            avg_slippage=execution_metrics['avg_slippage'],
            avg_execution_time=execution_metrics['avg_execution_time'],
            fill_rate=execution_metrics['fill_rate']
        )

    def _calculate_daily_returns(self, daily_pnl: Dict[str, float], initial_capital: float) -> np.ndarray:
        """Convert daily P&L to returns"""
        
        if not daily_pnl:
            return np.array([])
        
        # Sort by date
        sorted_dates = sorted(daily_pnl.keys())
        pnl_values = [daily_pnl[date] for date in sorted_dates]
        
        # Calculate cumulative capital
        capital = initial_capital
        returns = []
        
        for pnl in pnl_values:
            daily_return = pnl / capital if capital > 0 else 0
            returns.append(daily_return)
            capital += pnl
        
        return np.array(returns)

    def _calculate_total_return(self, daily_returns: np.ndarray) -> float:
        """Calculate total return"""
        if len(daily_returns) == 0:
            return 0.0
        
        cumulative_return = np.prod(1 + daily_returns) - 1
        return cumulative_return

    def _calculate_annualized_return(self, daily_returns: np.ndarray) -> float:
        """Calculate annualized return"""
        if len(daily_returns) == 0:
            return 0.0
        
        total_return = self._calculate_total_return(daily_returns)
        n_years = len(daily_returns) / 252  # 252 trading days per year
        
        if n_years <= 0:
            return 0.0
        
        annualized_return = (1 + total_return) ** (1 / n_years) - 1
        return annualized_return

    def _calculate_volatility(self, daily_returns: np.ndarray) -> float:
        """Calculate annualized volatility"""
        if len(daily_returns) <= 1:
            return 0.0
        
        return np.std(daily_returns) * np.sqrt(252)

    def _calculate_sharpe_ratio(self, daily_returns: np.ndarray) -> float:
        """Calculate Sharpe ratio"""
        if len(daily_returns) <= 1:
            return 0.0
        
        excess_returns = daily_returns - (self.risk_free_rate / 252)
        
        if np.std(excess_returns) == 0:
            return 0.0
        
        return np.mean(excess_returns) / np.std(excess_returns) * np.sqrt(252)

    def _calculate_sortino_ratio(self, daily_returns: np.ndarray) -> float:
        """Calculate Sortino ratio (downside deviation)"""
        if len(daily_returns) <= 1:
            return 0.0
        
        excess_returns = daily_returns - (self.risk_free_rate / 252)
        downside_returns = excess_returns[excess_returns < 0]
        
        if len(downside_returns) == 0 or np.std(downside_returns) == 0:
            return float('inf') if np.mean(excess_returns) > 0 else 0.0
        
        downside_deviation = np.std(downside_returns) * np.sqrt(252)
        return (np.mean(excess_returns) * 252) / downside_deviation

    def _calculate_calmar_ratio(self, daily_returns: np.ndarray) -> float:
        """Calculate Calmar ratio (annualized return / max drawdown)"""
        if len(daily_returns) == 0:
            return 0.0
        
        annualized_return = self._calculate_annualized_return(daily_returns)
        max_drawdown = self._calculate_max_drawdown(daily_returns)
        
        if max_drawdown == 0:
            return float('inf') if annualized_return > 0 else 0.0
        
        return annualized_return / max_drawdown

    def _calculate_max_drawdown(self, daily_returns: np.ndarray) -> float:
        """Calculate maximum drawdown"""
        if len(daily_returns) == 0:
            return 0.0
        
        cumulative_returns = np.cumprod(1 + daily_returns)
        running_max = np.maximum.accumulate(cumulative_returns)
        drawdown = (cumulative_returns - running_max) / running_max
        
        return abs(np.min(drawdown))

    def _calculate_var(self, daily_returns: np.ndarray, alpha: float = 0.05) -> float:
        """Calculate Value at Risk"""
        if len(daily_returns) == 0:
            return 0.0
        
        return np.percentile(daily_returns, alpha * 100)

    def _calculate_cvar(self, daily_returns: np.ndarray, alpha: float = 0.05) -> float:
        """Calculate Conditional Value at Risk (Expected Shortfall)"""
        if len(daily_returns) == 0:
            return 0.0
        
        var = self._calculate_var(daily_returns, alpha)
        return np.mean(daily_returns[daily_returns <= var])

    def _calculate_beta(self, daily_returns: np.ndarray) -> float:
        """Calculate beta vs benchmark (simplified)"""
        if len(daily_returns) <= 1:
            return 0.0
        
        # Simulate benchmark returns (for demonstration)
        benchmark_daily = self.benchmark_return / 252
        benchmark_returns = np.random.normal(benchmark_daily, 0.01, len(daily_returns))
        
        if np.var(benchmark_returns) == 0:
            return 0.0
        
        return np.cov(daily_returns, benchmark_returns)[0, 1] / np.var(benchmark_returns)

    def _analyze_trades(self, trades: List[Any]) -> Dict[str, float]:
        """Analyze trade-level performance"""
        
        if not trades:
            return {
                'win_rate': 0.0,
                'profit_factor': 0.0,
                'avg_trade': 0.0,
                'best_trade': 0.0,
                'worst_trade': 0.0
            }
        
        trade_pnls = [trade.pnl for trade in trades]
        
        winning_trades = [pnl for pnl in trade_pnls if pnl > 0]
        losing_trades = [pnl for pnl in trade_pnls if pnl < 0]
        
        win_rate = len(winning_trades) / len(trades) if trades else 0.0
        
        gross_profit = sum(winning_trades) if winning_trades else 0.0
        gross_loss = abs(sum(losing_trades)) if losing_trades else 0.0
        
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
        
        return {
            'win_rate': win_rate,
            'profit_factor': profit_factor,
            'avg_trade': np.mean(trade_pnls),
            'best_trade': max(trade_pnls) if trade_pnls else 0.0,
            'worst_trade': min(trade_pnls) if trade_pnls else 0.0
        }

    def _analyze_execution(self, trades: List[Any]) -> Dict[str, float]:
        """Analyze execution quality"""
        
        if not trades:
            return {
                'avg_slippage': 0.0,
                'avg_execution_time': 0.0,
                'fill_rate': 0.0
            }
        
        slippages = [getattr(trade, 'slippage', 0) for trade in trades]
        execution_times = [getattr(trade, 'execution_time', 0) for trade in trades]
        
        # Fill rate is always 1.0 for completed trades in our simulation
        fill_rate = 1.0
        
        return {
            'avg_slippage': np.mean(slippages),
            'avg_execution_time': np.mean(execution_times),
            'fill_rate': fill_rate
        }

    def generate_performance_report(self, 
                                  metrics: PerformanceMetrics,
                                  trades: List[Any],
                                  initial_capital: float) -> str:
        """Generate detailed performance report"""
        
        report = f"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                         PERFORMANCE ANALYSIS REPORT                             ║
╚══════════════════════════════════════════════════════════════════════════════╝

📊 RETURN METRICS
═══════════════════════════════════════════════════════════════════════════════
Total Return:                {metrics.total_return:.2%}
Annualized Return:           {metrics.annualized_return:.2%}
Volatility (Annualized):     {metrics.volatility:.2%}
Sharpe Ratio:               {metrics.sharpe_ratio:.2f}
Sortino Ratio:              {metrics.sortino_ratio:.2f}
Calmar Ratio:               {metrics.calmar_ratio:.2f}

⚠️  RISK METRICS
═══════════════════════════════════════════════════════════════════════════════
Maximum Drawdown:           {metrics.max_drawdown:.2%}
Value at Risk (95%):        {metrics.var_95:.2%}
Conditional VaR (95%):      {metrics.cvar_95:.2%}
Beta (vs Benchmark):        {metrics.beta:.2f}

📈 TRADE PERFORMANCE
═══════════════════════════════════════════════════════════════════════════════
Win Rate:                   {metrics.win_rate:.2%}
Profit Factor:              {metrics.profit_factor:.2f}
Average Trade P&L:          ₹{metrics.avg_trade:,.2f}
Best Trade:                 ₹{metrics.best_trade:,.2f}
Worst Trade:                ₹{metrics.worst_trade:,.2f}

⚡ EXECUTION QUALITY
═══════════════════════════════════════════════════════════════════════════════
Average Slippage:           {metrics.avg_slippage:.4%}
Average Execution Time:     {metrics.avg_execution_time:.1f} seconds
Fill Rate:                  {metrics.fill_rate:.2%}

💼 PORTFOLIO SUMMARY
═══════════════════════════════════════════════════════════════════════════════
Initial Capital:            ₹{initial_capital:,.2f}
Final Capital:              ₹{initial_capital * (1 + metrics.total_return):,.2f}
Total P&L:                  ₹{initial_capital * metrics.total_return:,.2f}
Total Trades:               {len(trades):,}
"""
        
        # Risk assessment
        if metrics.sharpe_ratio > 1.5:
            risk_assessment = "EXCELLENT - Strong risk-adjusted returns"
        elif metrics.sharpe_ratio > 1.0:
            risk_assessment = "GOOD - Solid risk-adjusted performance"
        elif metrics.sharpe_ratio > 0.5:
            risk_assessment = "MODERATE - Acceptable performance"
        else:
            risk_assessment = "POOR - Needs improvement"
        
        report += f"""
🎯 PERFORMANCE ASSESSMENT
═══════════════════════════════════════════════════════════════════════════════
Risk-Adjusted Performance:  {risk_assessment}
Maximum Drawdown:           {"ACCEPTABLE" if metrics.max_drawdown < 0.15 else "HIGH RISK"}
Win Rate:                   {"STRONG" if metrics.win_rate > 0.6 else "NEEDS IMPROVEMENT"}
Execution Quality:          {"EXCELLENT" if metrics.avg_slippage < 0.01 else "GOOD"}
"""
        
        return report

    def create_performance_charts(self, 
                                trades: List[Any],
                                daily_pnl: Dict[str, float],
                                output_dir: str = "charts") -> List[str]:
        """Create performance visualization charts"""
        
        # Create output directory
        Path(output_dir).mkdir(exist_ok=True)
        
        chart_files = []
        
        # Set style
        plt.style.use('seaborn-v0_8')
        
        # 1. Equity Curve
        fig, ax = plt.subplots(figsize=(12, 8))
        
        if daily_pnl:
            dates = sorted(daily_pnl.keys())
            cumulative_pnl = np.cumsum([daily_pnl[date] for date in dates])
            
            ax.plot([datetime.strptime(d, "%Y-%m-%d") for d in dates], cumulative_pnl, 
                   linewidth=2, color='blue')
            ax.set_title('Equity Curve', fontsize=16, fontweight='bold')
            ax.set_xlabel('Date')
            ax.set_ylabel('Cumulative P&L (₹)')
            ax.grid(True, alpha=0.3)
            
            # Format y-axis
            ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'₹{x:,.0f}'))
            
            equity_file = f"{output_dir}/equity_curve.png"
            plt.savefig(equity_file, dpi=300, bbox_inches='tight')
            plt.close()
            chart_files.append(equity_file)
        
        # 2. Monthly Returns Heatmap
        if daily_pnl:
            fig, ax = plt.subplots(figsize=(12, 8))
            
            # Convert to monthly returns
            monthly_returns = self._calculate_monthly_returns(daily_pnl)
            
            if monthly_returns:
                # Create heatmap data
                heatmap_data = {}
                for month, return_val in monthly_returns.items():
                    year = month[:4]
                    month_name = datetime.strptime(month, "%Y-%m").strftime("%b")
                    
                    if year not in heatmap_data:
                        heatmap_data[year] = {}
                    heatmap_data[year][month_name] = return_val * 100  # Convert to percentage
                
                if heatmap_data:
                    df_heatmap = pd.DataFrame(heatmap_data).T
                    
                    sns.heatmap(df_heatmap, annot=True, fmt='.1f', cmap='RdYlGn', 
                               center=0, ax=ax, cbar_kws={'label': 'Return (%)'})
                    ax.set_title('Monthly Returns Heatmap', fontsize=16, fontweight='bold')
                    
                    heatmap_file = f"{output_dir}/monthly_returns_heatmap.png"
                    plt.savefig(heatmap_file, dpi=300, bbox_inches='tight')
                    chart_files.append(heatmap_file)
            
            plt.close()
        
        # 3. Trade Distribution
        if trades:
            fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))
            
            trade_pnls = [trade.pnl for trade in trades]
            
            # Histogram
            ax1.hist(trade_pnls, bins=30, alpha=0.7, color='skyblue', edgecolor='black')
            ax1.set_title('Trade P&L Distribution', fontweight='bold')
            ax1.set_xlabel('Trade P&L (₹)')
            ax1.set_ylabel('Frequency')
            ax1.axvline(0, color='red', linestyle='--', alpha=0.7)
            ax1.grid(True, alpha=0.3)
            
            # Box plot
            ax2.boxplot(trade_pnls, vert=True)
            ax2.set_title('Trade P&L Box Plot', fontweight='bold')
            ax2.set_ylabel('Trade P&L (₹)')
            ax2.grid(True, alpha=0.3)
            
            trade_dist_file = f"{output_dir}/trade_distribution.png"
            plt.savefig(trade_dist_file, dpi=300, bbox_inches='tight')
            plt.close()
            chart_files.append(trade_dist_file)
        
        # 4. Instrument Performance
        if trades:
            fig, ax = plt.subplots(figsize=(10, 6))
            
            instrument_pnl = {}
            for trade in trades:
                instrument = trade.instrument
                if instrument not in instrument_pnl:
                    instrument_pnl[instrument] = 0
                instrument_pnl[instrument] += trade.pnl
            
            if instrument_pnl:
                instruments = list(instrument_pnl.keys())
                pnls = list(instrument_pnl.values())
                colors = ['green' if pnl >= 0 else 'red' for pnl in pnls]
                
                bars = ax.bar(instruments, pnls, color=colors, alpha=0.7)
                ax.set_title('Performance by Instrument', fontweight='bold')
                ax.set_ylabel('Total P&L (₹)')
                ax.grid(True, alpha=0.3)
                
                # Add value labels on bars
                for bar, pnl in zip(bars, pnls):
                    height = bar.get_height()
                    ax.text(bar.get_x() + bar.get_width()/2., height + (height*0.01),
                           f'₹{pnl:,.0f}', ha='center', va='bottom', fontweight='bold')
                
                instrument_file = f"{output_dir}/instrument_performance.png"
                plt.savefig(instrument_file, dpi=300, bbox_inches='tight')
                chart_files.append(instrument_file)
            
            plt.close()
        
        logger.info(f"Created {len(chart_files)} performance charts in {output_dir}/")
        return chart_files

    def _calculate_monthly_returns(self, daily_pnl: Dict[str, float]) -> Dict[str, float]:
        """Calculate monthly returns from daily P&L"""
        
        monthly_pnl = {}
        
        for date_str, pnl in daily_pnl.items():
            month_key = date_str[:7]  # YYYY-MM
            if month_key not in monthly_pnl:
                monthly_pnl[month_key] = 0
            monthly_pnl[month_key] += pnl
        
        # Convert to returns (simplified)
        monthly_returns = {}
        initial_capital = 5000000  # Assuming initial capital
        
        for month, pnl in monthly_pnl.items():
            monthly_returns[month] = pnl / initial_capital
        
        return monthly_returns

    def export_detailed_results(self, 
                              trades: List[Any],
                              metrics: PerformanceMetrics,
                              output_file: str = "detailed_results.json") -> str:
        """Export detailed results to JSON"""
        
        # Prepare trade data
        trade_data = []
        for trade in trades:
            trade_dict = {
                'timestamp': trade.timestamp.isoformat(),
                'instrument': trade.instrument,
                'lots': trade.lots,
                'entry_price': trade.entry_price,
                'exit_price': trade.exit_price,
                'phase': trade.phase,
                'execution_type': trade.execution_type,
                'slippage': trade.slippage,
                'execution_time': trade.execution_time,
                'pnl': trade.pnl,
                'cumulative_pnl': trade.cumulative_pnl
            }
            trade_data.append(trade_dict)
        
        # Prepare metrics data
        metrics_dict = {
            'total_return': metrics.total_return,
            'annualized_return': metrics.annualized_return,
            'volatility': metrics.volatility,
            'sharpe_ratio': metrics.sharpe_ratio,
            'sortino_ratio': metrics.sortino_ratio,
            'calmar_ratio': metrics.calmar_ratio,
            'max_drawdown': metrics.max_drawdown,
            'var_95': metrics.var_95,
            'cvar_95': metrics.cvar_95,
            'beta': metrics.beta,
            'win_rate': metrics.win_rate,
            'profit_factor': metrics.profit_factor,
            'avg_trade': metrics.avg_trade,
            'best_trade': metrics.best_trade,
            'worst_trade': metrics.worst_trade,
            'avg_slippage': metrics.avg_slippage,
            'avg_execution_time': metrics.avg_execution_time,
            'fill_rate': metrics.fill_rate
        }
        
        # Combine results
        results = {
            'metadata': {
                'analysis_timestamp': datetime.now().isoformat(),
                'total_trades': len(trades),
                'analysis_version': '1.0'
            },
            'performance_metrics': metrics_dict,
            'trades': trade_data
        }
        
        # Export to JSON
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2)
        
        logger.info(f"Detailed results exported to {output_file}")
        return output_file
