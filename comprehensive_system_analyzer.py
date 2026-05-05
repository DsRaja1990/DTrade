#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║           COMPREHENSIVE TRADING SYSTEM ANALYZER v2.0                         ║
║       Deep Analysis of All Services, Databases & Integration                 ║
╚══════════════════════════════════════════════════════════════════════════════╝

Analyzes:
1. All Windows Services Health & Status
2. Database Contents & Schema
3. Live Signal Generation
4. Tick Forwarding & Data Flow
5. Gemini AI Integration
6. Evaluation/Paper Trading Performance
7. Integration Points & Data Consistency

Run: python comprehensive_system_analyzer.py
"""

import sqlite3
import os
import json
import asyncio
import aiohttp
import requests
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
import traceback

# ============================================================================
#                          CONFIGURATION
# ============================================================================

BASE_DIR = Path(__file__).parent

# Service Endpoints
SERVICES = {
    "dhan_backend": {"url": "http://localhost:8000", "name": "DhanHQ Backend", "port": 8000},
    "scalping": {"url": "http://localhost:4002", "name": "AI Scalping Service", "port": 4002},
    "hedger": {"url": "http://localhost:4003", "name": "AI Options Hedger", "port": 4003},
    "gemini": {"url": "http://localhost:4080", "name": "Gemini Trade Service", "port": 4080},
    "equity_hv": {"url": "http://localhost:5080", "name": "Equity HV Service", "port": 5080},
}

# Database Paths
DATABASES = {
    "scalping_main": BASE_DIR / "ai_scalping_service" / "database" / "scalping_data.db",
    "scalping_eval": BASE_DIR / "ai_scalping_service" / "database" / "evaluation_data.db",
    "hedger_main": BASE_DIR / "ai_options_hedger" / "database" / "hedger_data.db",
    "hedger_eval": BASE_DIR / "ai_options_hedger" / "database" / "hedger_evaluation.db",
    "equity_elite": BASE_DIR / "equity_hv_service" / "database" / "elite_trades.db",
    "equity_eval": BASE_DIR / "equity_hv_service" / "database" / "equity_evaluation.db",
    "equity_data": BASE_DIR / "equity_hv_service" / "data" / "trading_data.db",
}

# ============================================================================
#                          HELPER FUNCTIONS
# ============================================================================

def print_header(title: str, char: str = "="):
    """Print section header"""
    print(f"\n{char*70}")
    print(f"  {title}")
    print(f"{char*70}")

def print_subheader(title: str):
    """Print subsection header"""
    print(f"\n  ┌{'─'*60}")
    print(f"  │ {title}")
    print(f"  └{'─'*60}")

def safe_request(url: str, timeout: int = 5) -> Optional[Dict]:
    """Make safe HTTP request with error handling"""
    try:
        resp = requests.get(url, timeout=timeout)
        if resp.status_code == 200:
            return resp.json()
        return {"error": f"HTTP {resp.status_code}"}
    except requests.exceptions.ConnectionError:
        return {"error": "Connection refused - Service offline"}
    except requests.exceptions.Timeout:
        return {"error": "Request timed out"}
    except Exception as e:
        return {"error": str(e)}

def safe_post(url: str, data: Dict, timeout: int = 5) -> Optional[Dict]:
    """Make safe HTTP POST request"""
    try:
        resp = requests.post(url, json=data, timeout=timeout)
        return resp.json()
    except Exception as e:
        return {"error": str(e)}

# ============================================================================
#                     1. SERVICE HEALTH ANALYSIS
# ============================================================================

def analyze_service_health() -> Dict:
    """Analyze all service health and status"""
    print_header("🔍 SERVICE HEALTH ANALYSIS")
    
    results = {}
    
    for service_id, config in SERVICES.items():
        url = config["url"]
        name = config["name"]
        
        print(f"\n  📡 {name} (:{config['port']})")
        
        # Health check
        health = safe_request(f"{url}/health")
        if "error" not in health:
            print(f"      ✅ Status: HEALTHY")
            results[service_id] = {"status": "healthy", "data": health}
            
            # Get detailed status
            status = safe_request(f"{url}/status")
            if "error" not in status:
                if "strategy_enabled" in status:
                    print(f"      📊 Strategy Enabled: {status.get('strategy_enabled')}")
                if "mode" in status:
                    print(f"      📋 Mode: {status.get('mode', 'N/A')}")
                if "running" in status:
                    print(f"      ▶️  Running: {status.get('running')}")
                if "signals" in status:
                    signals = status["signals"]
                    for inst, sig in signals.items():
                        ticks = sig.get("ticks_received", sig.get("ticks", 0))
                        price = sig.get("current_price", 0)
                        print(f"      📈 {inst}: ₹{price:,.2f} ({ticks} ticks)")
                if "tick_forwarding" in status:
                    tf = status["tick_forwarding"]
                    print(f"      🔄 Tick Forwarding: {'✅ ON' if tf.get('enabled') else '❌ OFF'} (errors: {tf.get('error_count', 0)})")
                if "momentum" in status:
                    for inst, mom in status.get("momentum", {}).items():
                        if mom.get("price", 0) > 0:
                            print(f"      ⚡ {inst} Momentum: {mom.get('momentum_score', 0):.1f} ({mom.get('phase', 'N/A')})")
                            
                results[service_id]["status_data"] = status
        else:
            print(f"      ❌ Status: OFFLINE - {health.get('error')}")
            results[service_id] = {"status": "offline", "error": health.get("error")}
    
    return results

# ============================================================================
#                     2. DATABASE ANALYSIS
# ============================================================================

def analyze_database(db_path: Path, name: str) -> Dict:
    """Analyze a single database"""
    results = {"exists": False, "tables": {}, "stats": {}}
    
    if not db_path.exists():
        return results
    
    results["exists"] = True
    results["size_kb"] = db_path.stat().st_size / 1024
    
    try:
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        
        # Get tables
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
        tables = [t[0] for t in cur.fetchall()]
        
        for table in tables:
            cur.execute(f"SELECT COUNT(*) FROM [{table}]")
            count = cur.fetchone()[0]
            results["tables"][table] = count
            
            # Get recent records for important tables
            if count > 0 and table in ['trades', 'evaluation_trades', 'paper_trades', 'signals', 
                                        'evaluation_orders', 'momentum_snapshots', 'signal_decisions']:
                try:
                    cur.execute(f"SELECT * FROM [{table}] ORDER BY rowid DESC LIMIT 3")
                    rows = [dict(row) for row in cur.fetchall()]
                    results["stats"][table] = {"count": count, "recent": rows}
                except:
                    results["stats"][table] = {"count": count}
        
        conn.close()
    except Exception as e:
        results["error"] = str(e)
    
    return results

def analyze_all_databases() -> Dict:
    """Analyze all databases"""
    print_header("💾 DATABASE ANALYSIS")
    
    all_results = {}
    total_trades = 0
    total_signals = 0
    
    for db_id, db_path in DATABASES.items():
        print_subheader(f"{db_id}")
        
        result = analyze_database(db_path, db_id)
        all_results[db_id] = result
        
        if not result["exists"]:
            print(f"    ❌ Database not found: {db_path}")
            continue
        
        print(f"    📁 Size: {result['size_kb']:.1f} KB")
        print(f"    📊 Tables: {len(result['tables'])}")
        
        for table, count in result["tables"].items():
            indicator = "✅" if count > 0 else "⚪"
            print(f"       {indicator} {table}: {count} rows")
            
            # Track totals
            if 'trade' in table.lower():
                total_trades += count
            if 'signal' in table.lower():
                total_signals += count
    
    print_subheader("📋 SUMMARY")
    print(f"    Total Trades Recorded: {total_trades}")
    print(f"    Total Signals Recorded: {total_signals}")
    
    return all_results

# ============================================================================
#                     3. LIVE SIGNAL ANALYSIS
# ============================================================================

def analyze_live_signals() -> Dict:
    """Test live signal generation from all services"""
    print_header("⚡ LIVE SIGNAL ANALYSIS")
    
    results = {}
    
    # Test Options Hedger signals
    print_subheader("AI Options Hedger - Signal Engine")
    hedger_signals = safe_request("http://localhost:4003/signals")
    if "error" not in hedger_signals:
        results["hedger"] = hedger_signals
        signals = hedger_signals.get("signals", {})
        for inst, sig in signals.items():
            print(f"    📊 {inst}:")
            print(f"       Price: ₹{sig.get('current_price', 0):,.2f}")
            print(f"       Trend: {sig.get('trend', 'N/A')}")
            print(f"       Strength: {sig.get('signal_strength', 0):.2f}")
            print(f"       AI Confidence: {sig.get('ai_confidence', 0):.2f}")
            print(f"       Should Enter: {'✅ YES' if sig.get('should_enter') else '❌ NO'}")
        best = hedger_signals.get("best", {})
        if best and isinstance(best, dict):
            print(f"\n    🎯 Best Opportunity: {best.get('instrument')} ({best.get('direction')})")
    else:
        print(f"    ❌ Could not fetch: {hedger_signals.get('error')}")
    
    # Test Scalping momentum
    print_subheader("AI Scalping - Momentum Status")
    scalping_status = safe_request("http://localhost:4002/status")
    if "error" not in scalping_status:
        results["scalping"] = scalping_status
        momentum = scalping_status.get("momentum", {})
        for inst, mom in momentum.items():
            if mom.get("price", 0) > 0:
                print(f"    📊 {inst}:")
                print(f"       Price: ₹{mom.get('price', 0):,.2f}")
                print(f"       Momentum Score: {mom.get('momentum_score', 0):.1f}/100")
                print(f"       Velocity: {mom.get('velocity', 0):.4f}%")
                print(f"       Phase: {mom.get('phase', 'N/A')}")
                print(f"       Trend: {mom.get('trend', 'N/A')}")
    else:
        print(f"    ❌ Could not fetch: {scalping_status.get('error')}")
    
    # Test Gemini AI signal generation
    print_subheader("Gemini AI - Signal Generation Test")
    gemini_signal = safe_post("http://localhost:4080/api/signal/nifty", {
        "current_price": 26000,
        "change_percent": 0.5,
        "volume_ratio": 1.2
    })
    if "error" not in gemini_signal:
        results["gemini_signal"] = gemini_signal
        print(f"    🤖 AI Signal: {gemini_signal.get('signal', 'N/A')}")
        print(f"    📊 Confidence: {gemini_signal.get('confidence', 0):.2f}")
        print(f"    🎯 Direction: {gemini_signal.get('direction', 'N/A')}")
        print(f"    💡 Reasoning: {gemini_signal.get('reasoning', 'N/A')[:100]}...")
    else:
        print(f"    ❌ Could not generate: {gemini_signal.get('error')}")
    
    # Test trade validation
    print_subheader("Gemini AI - Trade Validation Test")
    validation = safe_post("http://localhost:4080/api/validate/trade", {
        "instrument": "NIFTY",
        "direction": "CE",
        "entry_price": 150.0,
        "stop_loss": 140.0,
        "target": 180.0,
        "signal_strength": 0.75,
        "market_context": {"trend": "bullish", "vix": 15}
    })
    if "error" not in validation:
        results["gemini_validation"] = validation
        print(f"    📋 Decision: {validation.get('decision', 'N/A')}")
        print(f"    📊 Confidence: {validation.get('confidence', 0):.2f}")
        print(f"    🤖 AI Model: {validation.get('ai_model', 'N/A')}")
        print(f"    💡 Reasoning: {validation.get('reasoning', 'N/A')[:100]}...")
    else:
        print(f"    ❌ Could not validate: {validation.get('error')}")
    
    return results

# ============================================================================
#                     4. EVALUATION MODE ANALYSIS
# ============================================================================

def analyze_evaluation_modes() -> Dict:
    """Check evaluation mode status across all services"""
    print_header("📝 EVALUATION MODE ANALYSIS")
    
    results = {}
    
    services_to_check = [
        ("scalping", "http://localhost:4002/evaluation/status", "AI Scalping"),
        ("hedger", "http://localhost:4003/evaluation/status", "AI Options Hedger"),
        ("equity_hv", "http://localhost:5080/evaluation/status", "Equity HV"),
    ]
    
    for service_id, url, name in services_to_check:
        print_subheader(name)
        status = safe_request(url)
        
        if "error" not in status:
            results[service_id] = status
            # Check for is_evaluation_mode or enabled field
            is_enabled = status.get('is_evaluation_mode', status.get('enabled', False))
            print(f"    📊 Enabled: {'✅ YES' if is_enabled else '❌ NO'}")
            print(f"    📋 Mode: {status.get('mode', status.get('execution_mode', 'N/A'))}")
            
            # Show session info
            session_trades = status.get('session_trades', 0)
            open_positions = status.get('open_positions', 0)
            session_pnl = status.get('session_pnl', 0)
            if session_trades > 0 or open_positions > 0:
                print(f"    📈 Session Trades: {session_trades}")
                print(f"    📊 Open Positions: {open_positions}")
                print(f"    💰 Session P&L: ₹{session_pnl:,.2f}")
            
            # Check for overall stats
            overall = status.get('overall_stats', {})
            if overall and overall.get('total_trades', 0) > 0:
                print(f"    📈 Total Trades: {overall.get('total_trades', 0)}")
                print(f"    💰 Total P&L: ₹{overall.get('total_pnl', 0):,.2f}")
                print(f"    🎯 Win Rate: {overall.get('win_rate', 0):.1f}%")
            
            # Check for trades/stats (legacy)
            if "stats" in status:
                stats = status["stats"]
                print(f"    📈 Total Trades: {stats.get('total_trades', 0)}")
                print(f"    💰 Total P&L: ₹{stats.get('total_pnl', 0):,.2f}")
                print(f"    🎯 Win Rate: {stats.get('win_rate', 0):.1f}%")
            if "session" in status:
                session = status["session"]
                print(f"    ⏱️ Session Duration: {session.get('duration_minutes', 0):.1f} mins")
                print(f"    📊 Signals Evaluated: {session.get('signals_evaluated', 0)}")
        else:
            print(f"    ❌ Could not fetch: {status.get('error')}")
            results[service_id] = {"error": status.get("error")}
    
    return results

# ============================================================================
#                     5. INTEGRATION ANALYSIS
# ============================================================================

def analyze_integration() -> Dict:
    """Analyze integration between services"""
    print_header("🔗 INTEGRATION ANALYSIS")
    
    results = {"tick_flow": {}, "ai_integration": {}, "issues": []}
    
    # Check tick forwarding
    print_subheader("Tick Data Flow")
    
    # Options Hedger -> Scalping
    hedger_status = safe_request("http://localhost:4003/tick-forwarding")
    if "error" not in hedger_status:
        enabled = hedger_status.get("enabled", False)
        reachable = hedger_status.get("scalping_service", {}).get("reachable", False)
        errors = hedger_status.get("error_count", 0)
        
        print(f"    Hedger → Scalping:")
        print(f"       Forwarding: {'✅ Enabled' if enabled else '❌ Disabled'}")
        print(f"       Scalping Reachable: {'✅ Yes' if reachable else '❌ No'}")
        print(f"       Errors: {errors}")
        
        results["tick_flow"]["hedger_to_scalping"] = {
            "enabled": enabled,
            "reachable": reachable,
            "errors": errors
        }
        
        if not enabled:
            results["issues"].append("Tick forwarding disabled from Hedger to Scalping")
        if not reachable:
            results["issues"].append("Scalping service not reachable from Hedger")
    
    # Check AI integration
    print_subheader("Gemini AI Integration")
    
    # Check hedger AI status
    hedger_ai = safe_request("http://localhost:4003/ai-status")
    if "error" not in hedger_ai:
        gemini = hedger_ai.get("gemini_service", {})
        print(f"    Hedger → Gemini:")
        print(f"       AI Enabled: {hedger_ai.get('ai_enabled', False)}")
        print(f"       Gemini Status: {gemini.get('status', 'N/A')}")
        print(f"       Min Confidence: {hedger_ai.get('min_ai_confidence', 0)}")
        
        results["ai_integration"]["hedger"] = hedger_ai
        
        if gemini.get("status") != "connected":
            results["issues"].append("Hedger not connected to Gemini AI")
    
    # Check equity HV Gemini connection
    equity_health = safe_request("http://localhost:5080/health")
    if "error" not in equity_health:
        gemini_connected = equity_health.get("gemini_connected", False)
        print(f"    Equity HV → Gemini:")
        print(f"       Connected: {'✅ Yes' if gemini_connected else '❌ No'}")
        
        results["ai_integration"]["equity_hv"] = {"connected": gemini_connected}
        
        if not gemini_connected:
            results["issues"].append("Equity HV not connected to Gemini AI")
    
    # Summary of issues
    print_subheader("Integration Issues")
    if results["issues"]:
        for i, issue in enumerate(results["issues"], 1):
            print(f"    ⚠️ {i}. {issue}")
    else:
        print(f"    ✅ No integration issues detected!")
    
    return results

# ============================================================================
#                     6. RECOMMENDATIONS
# ============================================================================

def generate_recommendations(service_results: Dict, db_results: Dict, 
                             signal_results: Dict, eval_results: Dict,
                             integration_results: Dict) -> List[str]:
    """Generate actionable recommendations"""
    print_header("💡 RECOMMENDATIONS")
    
    recommendations = []
    
    # Check for offline services
    for service_id, data in service_results.items():
        if data.get("status") == "offline":
            recommendations.append(f"🔴 Start {SERVICES[service_id]['name']} - currently offline")
    
    # Check for empty databases
    trade_tables = ["trades", "evaluation_trades", "paper_trades"]
    has_trades = False
    for db_id, data in db_results.items():
        if data.get("exists"):
            for table in trade_tables:
                if data.get("tables", {}).get(table, 0) > 0:
                    has_trades = True
                    break
    
    if not has_trades:
        recommendations.append("🟡 No trades recorded - Consider running strategies during market hours")
    
    # Check evaluation mode
    for service_id, data in eval_results.items():
        is_enabled = data.get("is_evaluation_mode", data.get("enabled", False))
        if "error" not in data and not is_enabled:
            recommendations.append(f"🟡 Enable evaluation mode on {service_id} to record simulated trades")
    
    # Check integration issues
    for issue in integration_results.get("issues", []):
        recommendations.append(f"🟠 Fix: {issue}")
    
    # Check signal generation
    if signal_results.get("gemini_validation", {}).get("decision") == "SKIP":
        recommendations.append("🟡 Current market conditions may not favor trading - AI recommending to skip")
    
    # Print recommendations
    if recommendations:
        for i, rec in enumerate(recommendations, 1):
            print(f"  {i}. {rec}")
    else:
        print("  ✅ System is operating optimally! No immediate actions required.")
    
    return recommendations

# ============================================================================
#                          MAIN EXECUTION
# ============================================================================

def main():
    print("""
╔══════════════════════════════════════════════════════════════════════════════╗
║           COMPREHENSIVE TRADING SYSTEM ANALYZER v2.0                         ║
║       Deep Analysis of All Services, Databases & Integration                 ║
╚══════════════════════════════════════════════════════════════════════════════╝
    """)
    print(f"📅 Analysis Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"📂 Base Directory: {BASE_DIR}")
    
    # Run all analyses
    service_results = analyze_service_health()
    db_results = analyze_all_databases()
    signal_results = analyze_live_signals()
    eval_results = analyze_evaluation_modes()
    integration_results = analyze_integration()
    
    # Generate recommendations
    recommendations = generate_recommendations(
        service_results, db_results, signal_results, 
        eval_results, integration_results
    )
    
    # Final summary
    print_header("📊 FINAL SUMMARY")
    
    healthy_services = sum(1 for s in service_results.values() if s.get("status") == "healthy")
    total_services = len(service_results)
    
    print(f"  Services Online: {healthy_services}/{total_services}")
    print(f"  Databases Active: {sum(1 for d in db_results.values() if d.get('exists'))}/{len(db_results)}")
    print(f"  Integration Issues: {len(integration_results.get('issues', []))}")
    print(f"  Recommendations: {len(recommendations)}")
    
    print(f"\n{'='*70}")
    print("  Analysis Complete!")
    print(f"{'='*70}\n")
    
    return {
        "services": service_results,
        "databases": db_results,
        "signals": signal_results,
        "evaluation": eval_results,
        "integration": integration_results,
        "recommendations": recommendations
    }

if __name__ == "__main__":
    main()
