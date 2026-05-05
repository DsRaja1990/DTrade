"""
Production Trading System Runner
================================
Start the complete trading system with API and Engine.

Usage:
    python run_production_system.py [--port 5000] [--mode paper|live]
    
Endpoints:
    GET  /health            - Health check
    GET  /api/status        - System status
    POST /api/start         - Start trading engine
    POST /api/stop          - Stop trading engine
    POST /api/pause         - Pause trading
    POST /api/resume        - Resume trading
    POST /api/scan          - Manual scan
    GET  /api/signals       - Signal history
    GET  /api/trades        - Trade history
    GET  /api/performance   - Performance analytics
    GET  /api/copilot/data  - Data for Copilot analysis
"""

import sys
import os
import argparse

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def main():
    parser = argparse.ArgumentParser(description='Production Trading System')
    parser.add_argument('--port', type=int, default=5000, help='API port')
    parser.add_argument('--host', default='0.0.0.0', help='Host to bind')
    parser.add_argument('--mode', choices=['paper', 'live'], default='paper', 
                        help='Trading mode')
    parser.add_argument('--debug', action='store_true', help='Debug mode')
    
    args = parser.parse_args()
    
    print(f"""
╔══════════════════════════════════════════════════════════════════════╗
║         PRODUCTION TRADING SYSTEM v4.2                               ║
╠══════════════════════════════════════════════════════════════════════╣
║  API Server: http://{args.host}:{args.port}                          
║  Mode: {args.mode.upper()} TRADING                                   
║  Engine: World-Class v4.2 + Gemini AI Full Integration              ║
║  Database: SQLite (strategy/database/trading_data.db)               ║
╚══════════════════════════════════════════════════════════════════════╝
    """)
    
    # Import and start API
    from production_api import app
    
    print(f"\n🚀 Starting API server on {args.host}:{args.port}...")
    print("   Press Ctrl+C to stop\n")
    
    app.run(
        host=args.host, 
        port=args.port, 
        debug=args.debug,
        threaded=True
    )

if __name__ == '__main__':
    main()
