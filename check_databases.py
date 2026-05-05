#!/usr/bin/env python3
"""Quick script to check all trading databases"""
import sqlite3
import os
from datetime import datetime

def check_db(db_path, db_name):
    """Check a database and print statistics"""
    if not os.path.exists(db_path):
        print(f"\n❌ {db_name}: File not found")
        return
    
    print(f"\n{'='*60}")
    print(f"📊 {db_name}")
    print(f"   Path: {db_path}")
    print(f"   Size: {os.path.getsize(db_path):,} bytes")
    print(f"   Modified: {datetime.fromtimestamp(os.path.getmtime(db_path))}")
    print('='*60)
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [t[0] for t in cursor.fetchall()]
        
        for table in tables:
            try:
                cursor = conn.execute(f"SELECT COUNT(*) FROM [{table}]")
                count = cursor.fetchone()[0]
                print(f"   📋 {table}: {count} records")
                
                # Show last few records for trade tables
                if count > 0 and ('trade' in table.lower() or 'position' in table.lower() or 'signal' in table.lower()):
                    try:
                        cursor = conn.execute(f"SELECT * FROM [{table}] ORDER BY rowid DESC LIMIT 3")
                        cols = [d[0] for d in cursor.description]
                        rows = cursor.fetchall()
                        print(f"      Columns: {cols}")
                        for row in rows:
                            print(f"      → {dict(zip(cols, row))}")
                    except Exception as e:
                        print(f"      (Could not fetch details: {e})")
            except Exception as e:
                print(f"   ❌ {table}: Error - {e}")
        
        conn.close()
    except Exception as e:
        print(f"   ❌ Error opening database: {e}")

# Check all trading databases
base = r"C:\Users\Dhanasimmaraja\Documents\TradeApp\DTrade"

print("\n" + "="*60)
print("TRADING SERVICES DATABASE ANALYSIS")
print("="*60)

# AI Scalping
check_db(f"{base}/ai_scalping_service/database/evaluation_data.db", "AI Scalping - Evaluation")
check_db(f"{base}/ai_scalping_service/database/scalping_data.db", "AI Scalping - Main")

# AI Options Hedger
check_db(f"{base}/ai_options_hedger/database/hedger_data.db", "AI Hedger - Main")
check_db(f"{base}/ai_options_hedger/database/hedger_evaluation.db", "AI Hedger - Evaluation")

# Elite Equity HV
check_db(f"{base}/equity_hv_service/database/elite_trades.db", "Elite Equity - Trades")
check_db(f"{base}/equity_hv_service/database/equity_evaluation.db", "Elite Equity - Evaluation")

print("\n" + "="*60)
print("ANALYSIS COMPLETE")
print("="*60)
