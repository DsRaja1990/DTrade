"""
Equity HV Service Backtest Runner
Tests strategy performance with real historical market data
"""

import asyncio
import sys
import os
from datetime import datetime, timedelta

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from equity_hv_service.strategy.equity_hv_engine import EnhancedEquityHVEngine
from equity_hv_service.strategy.equity_hv_config import EquityHVConfig

async def run_backtest():
    """Run backtest on last week's data"""
    
    print("=" * 80)
    print("EQUITY HV SERVICE - BACKTEST ANALYSIS")
    print("Using Last Week's Real Market Data")
    print("=" * 80)
    print()
    
    # Create config
    config = EquityHVConfig()
    config.paper_trading = True  # Ensure paper trading mode
    
    # Initialize engine
    print("📊 Initializing Equity HV Engine...")
    engine = EnhancedEquityHVEngine(config=config)
    
    try:
        # Initialize
        await engine.initialize()
        print("✅ Engine initialized successfully")
        print()
        
        # Run backtest
        print("🔄 Running backtest on last 7 days of data...")
        print(f"Start Date: {(datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')}")
        print(f" End Date: {datetime.now().strftime('%Y-%m-%d')}")
        print()
        
        # The engine has backtest capabilities built-in
        # Check if backtest method exists
        if hasattr(engine, 'run_backtest'):
            results = await engine.run_backtest(
                start_date=datetime.now() - timedelta(days=7),
                end_date=datetime.now()
            )
            
            print("\n" + "=" * 80)
            print("BACKTEST RESULTS")
            print("=" * 80)
            print(f"Total Trades: {results.get('total_trades', 0)}")
            print(f"Winning Trades: {results.get('winning_trades', 0)}")
            print(f"Losing Trades: {results.get('losing_trades', 0)}")
            print(f"Win Rate: {results.get('win_rate', 0):.2%}")
            print(f"Total Return: {results.get('total_return', 0):.2%}")
            print(f"Sharpe Ratio: {results.get('sharpe_ratio', 0):.2f}")
            print(f"Max Drawdown: {results.get('max_drawdown', 0):.2%}")
            print("=" * 80)
            
            # Performance assessment
            win_rate = results.get('win_rate', 0)
            total_return = results.get('total_return', 0)
            
            print("\n📈 PERFORMANCE ASSESSMENT:")
            if win_rate >= 0.75 and total_return >= 0.03:
                print("✅ EXCELLENT - Ready for production")
            elif win_rate >= 0.60 and total_return >= 0.01:
                print("⚠️  GOOD - Needs minor improvements")  
            else:
                print("❌ NEEDS WORK - Optimize before deployment")
            
        else:
            # Simulate with current statistics
            print("⚠️  Backtest method not found, using current engine statistics...")
            stats = engine.get_statistics()
            
            print("\n" + "=" * 80)
            print("ENGINE STATISTICS")
            print("=" * 80)
            print(f"Total Trades: {stats.get('total_trades', 0)}")
            print(f"Win Rate: {stats.get('win_rate', 0):.2%}")
            print(f"Total P&L: ${stats.get('total_pnl', 0):,.2f}")
            print(f"Current Positions: {stats.get('open_positions', 0)}")
            print("=" * 80)
            
            if stats.get('total_trades', 0) == 0:
                print("\n⚠️  NO HISTORICAL TRADES FOUND")
                print("This service hasn't been run with real market data yet.")
                print("Recommendation: Run paper trading during next market session.")
        
    except Exception as e:
        print(f"\n❌ Error during backtest: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Cleanup
        if hasattr(engine, 'cleanup'):
            await engine.cleanup()
        print("\n✅ Backtest completed")

if __name__ == "__main__":
    print(f"🕐 Current Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"📅 Market Status: {'CLOSED' if datetime.now().hour < 9 or datetime.now().hour > 15 else 'OPEN'}")
    print()
    
    asyncio.run(run_backtest())
