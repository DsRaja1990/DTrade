"""
Database Analysis Script - Analyze all service databases for enhancement opportunities
"""
import sqlite3
import os
from datetime import datetime
from collections import defaultdict

def analyze_database(db_path, name):
    """Analyze a single database"""
    print(f"\n{'='*60}")
    print(f"📊 {name}")
    print(f"   Path: {db_path}")
    print('='*60)
    
    if not os.path.exists(db_path):
        print("   ❌ File not found")
        return {}
    
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        
        # Get tables
        cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [t[0] for t in cur.fetchall()]
        print(f"   Tables: {len(tables)}")
        
        stats = {}
        for table in tables:
            if table.startswith('sqlite_'):
                continue
            cur.execute(f"SELECT COUNT(*) FROM [{table}]")
            count = cur.fetchone()[0]
            stats[table] = count
            print(f"     - {table}: {count} rows")
        
        # Check for trades/signals with data
        for check_table in ['trades', 'signals', 'evaluation_trades', 'paper_trades']:
            if check_table in stats and stats[check_table] > 0:
                print(f"\n   📈 Recent {check_table}:")
                cur.execute(f"SELECT * FROM [{check_table}] ORDER BY rowid DESC LIMIT 3")
                rows = cur.fetchall()
                for row in rows:
                    print(f"     {dict(row)}")
        
        conn.close()
        return stats
        
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return {}

def main():
    base = r"C:\Users\Dhanasimmaraja\Documents\TradeApp\DTrade"
    
    databases = [
        # Signal Engine
        (os.path.join(base, "signal_engine_service", "database", "signals.db"), "Signal Engine - Signals DB"),
        (os.path.join(base, "signal_engine_service", "database", "evaluation_signals.db"), "Signal Engine - Evaluation DB"),
        
        # Scalping Service
        (os.path.join(base, "ai_scalping_service", "database", "scalping_data.db"), "Scalping Service - Main DB"),
        (os.path.join(base, "ai_scalping_service", "database", "evaluation_data.db"), "Scalping Service - Evaluation DB"),
        
        # Options Hedger
        (os.path.join(base, "ai_options_hedger", "database", "hedger_data.db"), "Options Hedger - Main DB"),
        (os.path.join(base, "ai_options_hedger", "database", "hedger_evaluation.db"), "Options Hedger - Evaluation DB"),
        
        # Equity HV Service
        (os.path.join(base, "equity_hv_service", "strategy", "trading_data.db"), "Equity HV - Trading DB"),
        (os.path.join(base, "equity_hv_service", "database", "trading_data.db"), "Equity HV - Database DB"),
        (os.path.join(base, "equity_hv_service", "data", "trading_data.db"), "Equity HV - Data DB"),
    ]
    
    print("\n" + "="*60)
    print("🔍 COMPREHENSIVE DATABASE ANALYSIS")
    print("="*60)
    print(f"Analysis Time: {datetime.now()}")
    
    all_stats = {}
    for db_path, name in databases:
        all_stats[name] = analyze_database(db_path, name)
    
    # Summary
    print("\n" + "="*60)
    print("📋 SUMMARY & ENHANCEMENT OPPORTUNITIES")
    print("="*60)
    
    total_signals = 0
    total_trades = 0
    
    for name, stats in all_stats.items():
        if stats:
            signals = stats.get('signals', 0) + stats.get('evaluation_signals', 0)
            trades = stats.get('trades', 0) + stats.get('evaluation_trades', 0) + stats.get('paper_trades', 0)
            total_signals += signals
            total_trades += trades
            if signals > 0 or trades > 0:
                print(f"\n{name}:")
                print(f"  Signals: {signals} | Trades: {trades}")
    
    print(f"\n{'='*60}")
    print(f"TOTAL: {total_signals} signals, {total_trades} trades")
    print("="*60)
    
    # Enhancement recommendations
    print("\n📝 ENHANCEMENT RECOMMENDATIONS:")
    print("-"*40)
    
    if total_trades == 0:
        print("1. ⚠️ No trades recorded - Services may not be generating signals")
        print("   - Check if market hours are active")
        print("   - Verify WebSocket connections are working")
        print("   - Ensure evaluation mode is correctly configured")
    
    if total_signals == 0:
        print("2. ⚠️ No signals generated - Check signal engine")
        print("   - Verify data feeds are active")
        print("   - Check RSI/indicator calculations")

if __name__ == "__main__":
    main()
