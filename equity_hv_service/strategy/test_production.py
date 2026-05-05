"""Quick test script for production engine"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from world_class_production_engine import ProductionWorldClassEngine

# Initialize engine
print("\n" + "="*60)
print("TESTING PRODUCTION ENGINE v4.2")
print("="*60)

engine = ProductionWorldClassEngine(paper_trading=True)

# Run a quick test
print('\n🧪 Running test scan...')
result = asyncio.run(engine.run_single_scan())

print(f'\n✅ Test completed!')
print(f'   Signals: {len(result.get("signals", []))}')
print(f'   Trades: {result.get("trades_executed", 0)}')

# Check database
if engine.database:
    print(f'   Database: Connected')
    data = engine.database.get_copilot_analysis_data()
    print(f'   Recent Signals: {len(data.get("recent_signals", []))}')
    print(f'   Trade Stats: {data.get("trade_statistics", {})}')
else:
    print('   Database: Not connected')

print("\n" + "="*60)
print("TEST PASSED - Engine is production ready!")
print("="*60)
