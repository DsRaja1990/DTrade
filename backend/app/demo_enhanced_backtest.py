"""
Quick Demo of Enhanced Backtest System

This script demonstrates the enhanced backtest capabilities with
different market configurations.
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add backend app to Python path
current_dir = Path(__file__).parent
backend_dir = current_dir.parent
sys.path.append(str(backend_dir))

from backtest.backtest_config import BacktestConfig, BacktestScenario, DEFAULT_CONFIG
from run_enhanced_backtest import EnhancedBacktestRunner

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def demo_enhanced_backtest():
    """Demonstrate enhanced backtest features"""
    
    logger.info("🎯 Starting Enhanced Backtest Demo")
    
    # Create custom configuration
    config = BacktestConfig()
    
    # Add a quick demo scenario
    demo_scenario = BacktestScenario(
        name="Demo Test",
        start_date="2024-01-01",
        end_date="2024-01-15",  # Just 2 weeks for quick demo
        initial_capital=2000000,  # 20 Lakh
        instruments=["NIFTY", "BANKNIFTY"],
        description="Quick demo of enhanced backtest system"
    )
    
    config.add_custom_scenario(demo_scenario)
    
    # Update market conditions for demo
    config.update_market_conditions(volatility="medium", correlation=0.85)
    config.update_execution_quality(slippage_bps=1.5, fill_rate=0.96)
    
    # Initialize runner
    runner = EnhancedBacktestRunner(config)
    
    # Run the demo scenario
    logger.info("Running demo scenario...")
    result = await runner.run_scenario(demo_scenario)
    
    # Display results
    metrics = result["metrics"]
    
    print("\n" + "="*60)
    print("ENHANCED BACKTEST DEMO RESULTS")
    print("="*60)
    print(f"Scenario: {demo_scenario.name}")
    print(f"Period: {demo_scenario.start_date} to {demo_scenario.end_date}")
    print(f"Instruments: {', '.join(demo_scenario.instruments)}")
    print(f"Initial Capital: Rs{demo_scenario.initial_capital:,}")
    print("-"*60)
    print(f"Total Return: {metrics.total_return_percentage:.2f}%")
    print(f"Total Trades: {metrics.total_trades}")
    print(f"Win Rate: {metrics.win_rate:.2f}%")
    print(f"Sharpe Ratio: {metrics.sharpe_ratio:.2f}")
    print(f"Max Drawdown: {metrics.max_drawdown:.2f}%")
    print(f"Avg Slippage: {metrics.avg_slippage:.4f}%")
    print(f"Execution Time: {result['execution_time']:.1f} seconds")
    print("-"*60)
    
    # Show available scenarios
    print("\nAvailable Scenarios in Config:")
    for scenario in config.scenarios:
        print(f"• {scenario.name}: {scenario.description}")
    
    print("\n🎉 Enhanced backtest demo completed!")
    
    return result

if __name__ == "__main__":
    asyncio.run(demo_enhanced_backtest())
