#!/usr/bin/env python3
"""Check evaluation database structure"""
import sqlite3
import os

def check_db(db_path, name):
    print(f"\n{'='*50}")
    print(f"Checking: {name}")
    print(f"Path: {db_path}")
    
    if not os.path.exists(db_path):
        print(f"  ❌ Database file does not exist")
        return
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        print(f"  📋 Tables: {tables}")
        
        # Get row counts
        for table in tables:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            print(f"    - {table}: {count} rows")
        
        conn.close()
        print(f"  ✅ Database OK")
    except Exception as e:
        print(f"  ❌ Error: {e}")

# Check all evaluation databases
base = r"c:\Users\Dhanasimmaraja\Documents\TradeApp\DTrade"

check_db(
    os.path.join(base, "signal_engine_service", "database", "evaluation_signals.db"),
    "Signal Engine Evaluation DB"
)

check_db(
    os.path.join(base, "ai_scalping_service", "database", "evaluation_data.db"),
    "Scalping Service Evaluation DB"
)

check_db(
    os.path.join(base, "ai_options_hedger", "database", "hedger_evaluation.db"),
    "Options Hedger Evaluation DB"
)

# Also check paper trading DBs
check_db(
    os.path.join(base, "signal_engine_service", "database", "paper_trading.db"),
    "Signal Engine Paper Trading DB"
)

check_db(
    os.path.join(base, "ai_scalping_service", "database", "paper_trading.db"),
    "Scalping Service Paper Trading DB"
)

check_db(
    os.path.join(base, "ai_options_hedger", "database", "hedger_data.db"),
    "Options Hedger Paper Trading DB"
)

print("\n✅ Database check complete")
