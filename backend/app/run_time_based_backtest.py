"""
Run Time-Based Execution Strategy Backtest

This script executes a comprehensive backtest of the time-based 
execution strategy for NIFTY, BANKNIFTY, and SENSEX.
"""

import asyncio
import logging
import sys
import os
from datetime import datetime
from pathlib import Path

# Add backend app to Python path
current_dir = Path(__file__).parent
backend_dir = current_dir.parent
sys.path.append(str(backend_dir))

from backtest.time_based_backtest import TimeBasedBacktestEngine
from backtest.performance_analyzer import PerformanceAnalyzer

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('time_based_backtest.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

async def run_comprehensive_backtest():
    """Run comprehensive backtest with multiple scenarios"""
    
    logger.info("=" * 80)
    logger.info("STARTING TIME-BASED EXECUTION STRATEGY BACKTEST")
    logger.info("=" * 80)
    
    # Backtest scenarios
    scenarios = [
        {
            "name": "3-Month Test",
            "start_date": "2024-01-01",
            "end_date": "2024-03-31",
            "capital": 5000000,  # 50 Lakh
            "instruments": ["NIFTY", "BANKNIFTY", "SENSEX"]
        },
        {
            "name": "6-Month Test", 
            "start_date": "2024-01-01",
            "end_date": "2024-06-30",
            "capital": 10000000,  # 1 Crore
            "instruments": ["NIFTY", "BANKNIFTY", "SENSEX"]
        },
        {
            "name": "Single Instrument - NIFTY",
            "start_date": "2024-01-01",
            "end_date": "2024-06-30",
            "capital": 5000000,
            "instruments": ["NIFTY"]
        }
    ]
    
    results = {}
    
    for scenario in scenarios:
        logger.info(f"\n{'='*60}")
        logger.info(f"RUNNING SCENARIO: {scenario['name']}")
        logger.info(f"{'='*60}")
        
        try:
            # Initialize backtest engine
            engine = TimeBasedBacktestEngine(
                initial_capital=scenario['capital'],
                start_date=scenario['start_date'],
                end_date=scenario['end_date']
            )
            
            logger.info(f"Period: {scenario['start_date']} to {scenario['end_date']}")
            logger.info(f"Capital: ₹{scenario['capital']:,}")
            logger.info(f"Instruments: {', '.join(scenario['instruments'])}")
            
            # Run backtest
            metrics = await engine.run_backtest(
                instruments=scenario['instruments'],
                use_synthetic_data=True
            )
            
            # Analyze performance
            analyzer = PerformanceAnalyzer()
            performance_metrics = analyzer.analyze_performance(
                trades=engine.trades,
                daily_pnl=engine.daily_pnl,
                initial_capital=scenario['capital']
            )
            
            # Generate reports
            backtest_report = engine.generate_report(metrics)
            performance_report = analyzer.generate_performance_report(
                performance_metrics, engine.trades, scenario['capital']
            )
            
            # Save reports
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            scenario_name = scenario['name'].replace(' ', '_').replace('-', '_')
            
            backtest_file = f"backtest_report_{scenario_name}_{timestamp}.txt"
            performance_file = f"performance_report_{scenario_name}_{timestamp}.txt"
            
            with open(backtest_file, 'w', encoding='utf-8') as f:
                f.write(backtest_report)
            
            with open(performance_file, 'w', encoding='utf-8') as f:
                f.write(performance_report)
            
            # Create charts
            chart_dir = f"charts_{scenario_name}_{timestamp}"
            chart_files = analyzer.create_performance_charts(
                trades=engine.trades,
                daily_pnl=engine.daily_pnl,
                output_dir=chart_dir
            )
            
            # Export detailed results
            detailed_file = f"detailed_results_{scenario_name}_{timestamp}.json"
            analyzer.export_detailed_results(
                trades=engine.trades,
                metrics=performance_metrics,
                output_file=detailed_file
            )
            
            # Store results
            results[scenario['name']] = {
                'metrics': metrics,
                'performance_metrics': performance_metrics,
                'trades_count': len(engine.trades),
                'final_capital': engine.current_capital,
                'files': {
                    'backtest_report': backtest_file,
                    'performance_report': performance_file,
                    'detailed_results': detailed_file,
                    'charts': chart_files
                }
            }
            
            # Print summary
            logger.info(f"\n✅ SCENARIO COMPLETED: {scenario['name']}")
            logger.info(f"Total Trades: {len(engine.trades):,}")
            logger.info(f"Total P&L: ₹{metrics.total_pnl:,.2f}")
            logger.info(f"Return: {metrics.total_return_percentage:.2f}%")
            logger.info(f"Sharpe Ratio: {performance_metrics.sharpe_ratio:.2f}")
            logger.info(f"Max Drawdown: {performance_metrics.max_drawdown:.2%}")
            logger.info(f"Win Rate: {metrics.win_rate:.2%}")
            logger.info(f"Avg Slippage: {metrics.avg_slippage:.4%}")
            
            logger.info(f"\nFiles generated:")
            logger.info(f"  - Backtest Report: {backtest_file}")
            logger.info(f"  - Performance Report: {performance_file}")
            logger.info(f"  - Detailed Results: {detailed_file}")
            logger.info(f"  - Charts Directory: {chart_dir}/")
            
        except Exception as e:
            logger.error(f"❌ SCENARIO FAILED: {scenario['name']}")
            logger.error(f"Error: {e}")
            results[scenario['name']] = {'error': str(e)}
    
    # Generate summary report
    generate_summary_report(results)
    
    logger.info(f"\n{'='*80}")
    logger.info("BACKTEST ANALYSIS COMPLETED")
    logger.info(f"{'='*80}")
    
    return results

def generate_summary_report(results: dict):
    """Generate summary report across all scenarios"""
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    summary_file = f"backtest_summary_{timestamp}.txt"
    
    summary = f"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                    TIME-BASED STRATEGY BACKTEST SUMMARY                         ║
╚══════════════════════════════════════════════════════════════════════════════╝

Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

"""
    
    for scenario_name, result in results.items():
        if 'error' in result:
            summary += f"""
❌ {scenario_name}
═══════════════════════════════════════════════════════════════════════════════
Status: FAILED
Error: {result['error']}
"""
        else:
            metrics = result['metrics']
            perf_metrics = result['performance_metrics']
            
            summary += f"""
✅ {scenario_name}
═══════════════════════════════════════════════════════════════════════════════
Total Trades:           {result['trades_count']:,}
Total Return:           {metrics.total_return_percentage:.2f}%
Annualized Return:      {perf_metrics.annualized_return:.2%}
Sharpe Ratio:          {perf_metrics.sharpe_ratio:.2f}
Maximum Drawdown:      {perf_metrics.max_drawdown:.2%}
Win Rate:              {metrics.win_rate:.2%}
Profit Factor:         {perf_metrics.profit_factor:.2f}
Average Slippage:      {metrics.avg_slippage:.4%}
Final Capital:         ₹{result['final_capital']:,.2f}
"""
    
    # Best performing scenario
    successful_results = {k: v for k, v in results.items() if 'error' not in v}
    
    if successful_results:
        best_scenario = max(
            successful_results.items(),
            key=lambda x: x[1]['performance_metrics'].sharpe_ratio
        )
        
        summary += f"""

🏆 BEST PERFORMING SCENARIO
═══════════════════════════════════════════════════════════════════════════════
Scenario: {best_scenario[0]}
Sharpe Ratio: {best_scenario[1]['performance_metrics'].sharpe_ratio:.2f}
Total Return: {best_scenario[1]['metrics'].total_return_percentage:.2f}%

📝 RECOMMENDATIONS
═══════════════════════════════════════════════════════════════════════════════
Based on the backtest results:

1. Strategy Performance: {"EXCELLENT" if best_scenario[1]['performance_metrics'].sharpe_ratio > 1.5 else "GOOD" if best_scenario[1]['performance_metrics'].sharpe_ratio > 1.0 else "NEEDS IMPROVEMENT"}
2. Risk Management: {"STRONG" if best_scenario[1]['performance_metrics'].max_drawdown < 0.15 else "REVIEW REQUIRED"}
3. Execution Quality: {"OPTIMAL" if best_scenario[1]['metrics'].avg_slippage < 0.005 else "ACCEPTABLE"}
4. Diversification: {"BALANCED" if len(best_scenario[1]['metrics'].trades_by_instrument) > 1 else "SINGLE INSTRUMENT"}

💡 NEXT STEPS
═══════════════════════════════════════════════════════════════════════════════
1. Review detailed performance reports for each scenario
2. Analyze trade-level execution data
3. Consider parameter optimization based on results
4. Plan live trading deployment strategy
"""
    
    with open(summary_file, 'w', encoding='utf-8') as f:
        f.write(summary)
    
    logger.info(f"\n📋 Summary report saved to: {summary_file}")
    print(summary)

def main():
    """Main execution function"""
    
    try:
        # Ensure we're in the correct directory
        os.chdir(current_dir)
        
        # Run backtest
        results = asyncio.run(run_comprehensive_backtest())
        
        print(f"\n🎉 BACKTEST ANALYSIS COMPLETED SUCCESSFULLY!")
        print(f"Total scenarios run: {len(results)}")
        print(f"Check the generated files for detailed results and charts.")
        
    except KeyboardInterrupt:
        logger.info("\n❌ Backtest interrupted by user")
    except Exception as e:
        logger.error(f"\n❌ Backtest failed with error: {e}")
        raise

if __name__ == "__main__":
    main()
