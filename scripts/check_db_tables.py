#!/usr/bin/env python3
"""Check database tables in all services"""
import sqlite3
import os

dbs = [
    ('AI Scalping Data', 'ai_scalping_service/database/scalping_data.db'),
    ('AI Scalping Evaluation', 'ai_scalping_service/database/evaluation_data.db'),
    ('AI Options Hedger Data', 'ai_options_hedger/database/hedger_data.db'),
    ('AI Options Hedger Eval', 'ai_options_hedger/database/hedger_evaluation.db'),
    ('AI Options Hedger Perf', 'ai_options_hedger/performance_tracker.db'),
    ('Paper Trades Test', 'ai_options_hedger/logs/test/paper_trades.db'),
    ('Equity HV Trades', 'equity_hv_service/database/elite_trades.db'),
    ('Equity HV Strategy', 'equity_hv_service/strategy/database/trading_data.db'),
    ('Signal Engine', 'signal_engine_service/signals.db'),
    ('Backend Paper Trading', 'backend/papertest/paper_trading.db'),
]

os.chdir(r'c:\Users\Dhanasimmaraja\Documents\TradeApp\DTrade')

print("=" * 60)
print("DATABASE TABLES ANALYSIS")
print("=" * 60)

for name, db in dbs:
    print(f"\n{name} ({db}):")
    if os.path.exists(db):
        try:
            c = sqlite3.connect(db)
            tables = [r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
            for t in tables:
                count = c.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
                print(f"  - {t}: {count} rows")
            c.close()
        except Exception as e:
            print(f"  ERROR: {e}")
    else:
        print(f"  FILE NOT FOUND")

print("\n" + "=" * 60)
