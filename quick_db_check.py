#!/usr/bin/env python3
"""Quick database analysis script"""
import sqlite3
import os

db_paths = [
    'backend/signals_performance.db',
    'ai_scalping_service/data/trades.db',
    'ai_options_hedger/database/trades.db',
    'equity_hv_service/database/trades.db',
    'data/trading_data.db',
    'backend/backtest_results.db'
]

for db_path in db_paths:
    if os.path.exists(db_path):
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [t[0] for t in cursor.fetchall()]
            print(f"\n=== {db_path} ===")
            print(f"Tables: {tables}")
            
            for table in tables[:5]:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]
                print(f"  {table}: {count} rows")
                
                if count > 0 and count < 100:
                    cursor.execute(f"SELECT * FROM {table} LIMIT 3")
                    rows = cursor.fetchall()
                    cursor.execute(f"PRAGMA table_info({table})")
                    cols = [c[1] for c in cursor.fetchall()]
                    print(f"    Columns: {cols[:8]}...")
                    for row in rows:
                        print(f"    Sample: {row[:6]}...")
            conn.close()
        except Exception as e:
            print(f"{db_path}: Error - {e}")
    else:
        print(f"\n{db_path}: Not found")
