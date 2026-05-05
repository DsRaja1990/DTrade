#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║              COMPREHENSIVE TRADING SYSTEM ANALYZER                           ║
║          Analyzes all services for win rate enhancement                      ║
╚══════════════════════════════════════════════════════════════════════════════╝

Analyzes:
1. Equity HV Service - AI Validations, Signal Engine data
2. AI Scalping Service - Momentum patterns, trade signals
3. AI Options Hedger - Hedge positions, P&L
4. Signal Engine - Elite signals generated
5. Gemini Trade Service - AI predictions made

Run this script to get insights for win rate enhancement.
"""

import sqlite3
import os
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
import requests

# Database paths
BASE_DIR = Path(__file__).parent

DATABASES = {
    "equity_hv": BASE_DIR / "equity_hv_service" / "strategy" / "trading_data.db",
    "scalping": BASE_DIR / "ai_scalping_service" / "data" / "trading_data.db",
    "options_hedger": BASE_DIR / "ai_options_hedger" / "data" / "trades.db",
    "signal_engine": BASE_DIR / "signal_engine_service" / "data" / "signals.db",
}

# Service endpoints
SERVICES = {
    "gemini_trade": "http://localhost:4080",
    "signal_engine": "http://localhost:4090",
    "scalping": "http://localhost:4002",
    "options_hedger": "http://localhost:4003",
    "equity_hv": "http://localhost:5080",
}

def check_service_health(name: str, url: str) -> Dict:
    """Check service health status"""
    try:
        resp = requests.get(f"{url}/health", timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            return {"status": "✅ HEALTHY", "data": data}
        return {"status": "⚠️ UNHEALTHY", "code": resp.status_code}
    except Exception as e:
        return {"status": "❌ OFFLINE", "error": str(e)}

def analyze_equity_hv_database(db_path: Path) -> Dict:
    """Analyze Equity HV trading database with Signal Engine focus"""
    if not db_path.exists():
        return {"error": "Database not found"}
    
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    results = {}
    
    # AI Validations with Signal Engine analysis
    try:
        cursor.execute('''
            SELECT 
                COUNT(*) as total,
                SUM(ai_approved) as approved,
                SUM(signal_engine_aligned) as se_aligned,
                AVG(ai_confidence_score) as avg_score,
                AVG(signal_engine_confidence_boost) as avg_se_boost
            FROM ai_validations 
            WHERE timestamp > datetime('now', '-7 days')
        ''')
        row = cursor.fetchone()
        if row and row['total']:
            results['ai_validations'] = dict(row)
            results['ai_validations']['approval_rate'] = (row['approved'] or 0) / row['total'] * 100
            results['ai_validations']['se_alignment_rate'] = (row['se_aligned'] or 0) / row['total'] * 100
    except Exception as e:
        results['ai_validations_error'] = str(e)
    
    # Signal Engine breakdown by signal type
    try:
        cursor.execute('''
            SELECT 
                signal_engine_nifty_signal as nifty_signal,
                COUNT(*) as count,
                AVG(ai_confidence_score) as avg_score,
                SUM(ai_approved) as approved
            FROM ai_validations 
            WHERE timestamp > datetime('now', '-7 days')
            GROUP BY signal_engine_nifty_signal
        ''')
        results['nifty_signal_breakdown'] = [dict(row) for row in cursor.fetchall()]
    except Exception as e:
        results['nifty_breakdown_error'] = str(e)
    
    # Trade performance
    try:
        cursor.execute('''
            SELECT 
                COUNT(*) as total_trades,
                SUM(CASE WHEN realized_pnl > 0 THEN 1 ELSE 0 END) as wins,
                SUM(CASE WHEN realized_pnl < 0 THEN 1 ELSE 0 END) as losses,
                SUM(realized_pnl) as total_pnl,
                AVG(realized_pnl) as avg_pnl,
                MAX(realized_pnl) as best_trade,
                MIN(realized_pnl) as worst_trade
            FROM trades 
            WHERE status != 'OPEN' AND entry_time > datetime('now', '-30 days')
        ''')
        row = cursor.fetchone()
        if row and row['total_trades']:
            results['trade_performance'] = dict(row)
            results['trade_performance']['win_rate'] = (row['wins'] or 0) / row['total_trades'] * 100
    except Exception as e:
        results['trade_error'] = str(e)
    
    # Recent signals
    try:
        cursor.execute('SELECT COUNT(*) as count FROM signals WHERE timestamp > datetime("now", "-1 day")')
        results['signals_24h'] = cursor.fetchone()['count']
    except:
        pass
    
    conn.close()
    return results

def analyze_scalping_database(db_path: Path) -> Dict:
    """Analyze AI Scalping database"""
    if not db_path.exists():
        return {"error": "Database not found"}
    
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    results = {}
    
    # Get tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    results['tables'] = [row['name'] for row in cursor.fetchall()]
    
    # Momentum patterns
    try:
        cursor.execute('SELECT COUNT(*) as count FROM momentum_snapshots WHERE timestamp > datetime("now", "-24 hours")')
        results['momentum_snapshots_24h'] = cursor.fetchone()['count']
    except:
        pass
    
    # Trades
    try:
        cursor.execute('''
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN exit_reason = 'TARGET' THEN 1 ELSE 0 END) as target_hits,
                SUM(CASE WHEN exit_reason = 'STOPLOSS' THEN 1 ELSE 0 END) as stoploss_hits
            FROM trades WHERE entry_time > datetime('now', '-7 days')
        ''')
        row = cursor.fetchone()
        if row and row['total']:
            results['trades_7d'] = dict(row)
    except:
        pass
    
    conn.close()
    return results

def analyze_options_hedger_database(db_path: Path) -> Dict:
    """Analyze Options Hedger database"""
    if not db_path.exists():
        return {"error": "Database not found"}
    
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    results = {}
    
    # Get tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    results['tables'] = [row['name'] for row in cursor.fetchall()]
    
    # Hedge trades
    try:
        cursor.execute('''
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) as profitable,
                SUM(pnl) as total_pnl
            FROM hedge_trades WHERE entry_time > datetime('now', '-7 days')
        ''')
        row = cursor.fetchone()
        if row and row['total']:
            results['hedge_trades_7d'] = dict(row)
    except:
        pass
    
    conn.close()
    return results

def get_gemini_stats(url: str) -> Dict:
    """Get Gemini Trade Service statistics"""
    try:
        resp = requests.get(f"{url}/api/stats", timeout=5)
        if resp.status_code == 200:
            return resp.json()
    except:
        pass
    return {"error": "Could not fetch stats"}

def print_section(title: str):
    """Print section header"""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print('='*60)

def main():
    print("""
╔══════════════════════════════════════════════════════════════════════════════╗
║              COMPREHENSIVE TRADING SYSTEM ANALYZER                           ║
║                    Win Rate Enhancement Report                               ║
╚══════════════════════════════════════════════════════════════════════════════╝
    """)
    
    print(f"📅 Analysis Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Check service health
    print_section("🔍 SERVICE HEALTH CHECK")
    for name, url in SERVICES.items():
        health = check_service_health(name, url)
        print(f"  {name}: {health['status']}")
        if 'data' in health:
            data = health['data']
            if 'models' in data:
                print(f"      Models: {data.get('models', {})}")
            if 'market_hours' in data:
                print(f"      Market Hours: {data.get('market_hours')}")
    
    # Analyze Equity HV
    print_section("📊 EQUITY HV SERVICE ANALYSIS")
    equity_data = analyze_equity_hv_database(DATABASES['equity_hv'])
    
    if 'ai_validations' in equity_data:
        av = equity_data['ai_validations']
        print(f"  AI Validations (7 days):")
        print(f"    Total: {av.get('total', 0)}")
        print(f"    Approved: {av.get('approved', 0)} ({av.get('approval_rate', 0):.1f}%)")
        print(f"    Signal Engine Aligned: {av.get('se_aligned', 0)} ({av.get('se_alignment_rate', 0):.1f}%)")
        print(f"    Avg AI Score: {av.get('avg_score', 0):.1f}/100")
        print(f"    Avg SE Boost: {av.get('avg_se_boost', 0):.3f}")
    
    if 'nifty_signal_breakdown' in equity_data:
        print(f"\n  NIFTY Signal Distribution:")
        for item in equity_data['nifty_signal_breakdown']:
            sig = item.get('nifty_signal') or 'N/A'
            print(f"    {sig}: {item.get('count', 0)} validations, {item.get('approved', 0)} approved")
    
    if 'trade_performance' in equity_data:
        tp = equity_data['trade_performance']
        print(f"\n  Trade Performance (30 days):")
        print(f"    Total: {tp.get('total_trades', 0)}")
        print(f"    Wins: {tp.get('wins', 0)} | Losses: {tp.get('losses', 0)}")
        print(f"    Win Rate: {tp.get('win_rate', 0):.1f}%")
        print(f"    Total P&L: ₹{tp.get('total_pnl', 0):,.2f}")
        print(f"    Best Trade: ₹{tp.get('best_trade', 0):,.2f}")
        print(f"    Worst Trade: ₹{tp.get('worst_trade', 0):,.2f}")
    else:
        print("  No trade data found (outside market hours)")
    
    print(f"  Signals (24h): {equity_data.get('signals_24h', 0)}")
    
    # Analyze Scalping
    print_section("📊 AI SCALPING SERVICE ANALYSIS")
    scalping_data = analyze_scalping_database(DATABASES['scalping'])
    print(f"  Tables: {scalping_data.get('tables', [])}")
    print(f"  Momentum Snapshots (24h): {scalping_data.get('momentum_snapshots_24h', 0)}")
    if 'trades_7d' in scalping_data:
        t = scalping_data['trades_7d']
        print(f"  Trades (7d): {t.get('total', 0)} (Targets: {t.get('target_hits', 0)}, SL: {t.get('stoploss_hits', 0)})")
    
    # Analyze Options Hedger
    print_section("📊 OPTIONS HEDGER ANALYSIS")
    hedger_data = analyze_options_hedger_database(DATABASES['options_hedger'])
    print(f"  Tables: {hedger_data.get('tables', [])}")
    if 'hedge_trades_7d' in hedger_data:
        h = hedger_data['hedge_trades_7d']
        print(f"  Hedge Trades (7d): {h.get('total', 0)} (Profitable: {h.get('profitable', 0)}, P&L: ₹{h.get('total_pnl', 0):,.2f})")
    
    # Gemini stats
    print_section("🤖 GEMINI AI SERVICE STATS")
    gemini_stats = get_gemini_stats(SERVICES['gemini_trade'])
    if 'error' not in gemini_stats:
        print(f"  {json.dumps(gemini_stats, indent=4)}")
    else:
        print(f"  {gemini_stats}")
    
    # Recommendations
    print_section("💡 ENHANCEMENT RECOMMENDATIONS")
    
    print("""
  Based on the analysis:
  
  1. 📈 Signal Engine Alignment
     - Monitor win rate when SE aligned vs not aligned
     - Consider requiring SE alignment for all trades
     
  2. 🎯 AI Confidence Thresholds
     - Track performance by confidence level
     - Adjust min thresholds based on actual win rates
     
  3. ⏰ Market Hours Data
     - Most data collected during 9:15-15:30 IST
     - Review data after market close for patterns
     
  4. 🔄 Database Sync
     - Ensure all services log to their databases
     - Run this analyzer daily for insights
    """)
    
    print(f"\n{'='*60}")
    print("  Analysis Complete!")
    print(f"{'='*60}\n")

if __name__ == "__main__":
    main()
