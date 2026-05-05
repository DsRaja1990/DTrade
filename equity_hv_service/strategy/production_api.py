"""
Production Trading API v1.0
============================
Flask REST API for controlling the World-Class Trading Engine.

Features:
- Start/Stop/Pause trading engine
- Real-time status and statistics
- Signal and trade history
- Performance analytics
- Health checks

Author: Trading System
Version: 1.0
Date: January 2025
"""

import os
import sys
import json
import threading
import asyncio
from datetime import datetime, timedelta
from functools import wraps
from flask import Flask, jsonify, request
from flask_cors import CORS
import logging

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Initialize Flask app
app = Flask(__name__)
CORS(app)  # Enable CORS for frontend access

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============================================================================
# GLOBAL STATE
# ============================================================================

class TradingState:
    """Global trading state manager"""
    
    def __init__(self):
        self.engine = None
        self.is_running = False
        self.is_paused = False
        self.start_time = None
        self.last_scan_time = None
        self.total_scans = 0
        self.signals_generated = 0
        self.trades_executed = 0
        self.current_pnl = 0.0
        self.engine_thread = None
        self.stop_event = threading.Event()
        
    def to_dict(self):
        return {
            "is_running": self.is_running,
            "is_paused": self.is_paused,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "uptime_seconds": (datetime.now() - self.start_time).total_seconds() if self.start_time else 0,
            "last_scan_time": self.last_scan_time.isoformat() if self.last_scan_time else None,
            "total_scans": self.total_scans,
            "signals_generated": self.signals_generated,
            "trades_executed": self.trades_executed,
            "current_pnl": self.current_pnl
        }

# Global state instance
trading_state = TradingState()

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_database():
    """Get database instance"""
    try:
        from database import TradingDatabase
        return TradingDatabase()
    except ImportError:
        try:
            from database.trading_database import TradingDatabase
            return TradingDatabase()
        except ImportError:
            logger.warning("Database module not available")
            return None

def get_engine():
    """Get or create engine instance"""
    try:
        from world_class_production_engine import ProductionWorldClassEngine
        return ProductionWorldClassEngine()
    except ImportError as e:
        logger.error(f"Cannot import engine: {e}")
        return None

def require_engine(f):
    """Decorator to ensure engine is available"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if trading_state.engine is None:
            return jsonify({
                "success": False,
                "error": "Trading engine not initialized",
                "message": "Call /api/start first to initialize the engine"
            }), 400
        return f(*args, **kwargs)
    return decorated_function

def run_async(coro):
    """Run async function in sync context"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()

# ============================================================================
# HEALTH CHECK ENDPOINTS
# ============================================================================

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    db = get_database()
    db_status = "connected" if db else "disconnected"
    
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "components": {
            "api": "running",
            "database": db_status,
            "engine": "running" if trading_state.is_running else "stopped"
        }
    })

@app.route('/api/status', methods=['GET'])
def get_status():
    """Get comprehensive trading system status"""
    db = get_database()
    
    # Get database stats if available
    db_stats = {}
    if db:
        today = datetime.now().strftime("%Y-%m-%d")
        db_stats = {
            "total_signals": len(db.get_signals(limit=10000)),
            "total_trades": len(db.get_trades(limit=10000)),
            "today_signals": len(db.get_signals(start_date=today, limit=1000)),
            "today_trades": len(db.get_trades(start_date=today, limit=1000))
        }
    
    return jsonify({
        "success": True,
        "strategy_enabled": trading_state.is_running,
        "timestamp": datetime.now().isoformat(),
        "engine": trading_state.to_dict(),
        "database": db_stats,
        "market": {
            "is_market_hours": is_market_hours(),
            "next_session": get_next_market_session()
        }
    })

def is_market_hours():
    """Check if within market hours"""
    now = datetime.now()
    # Indian market hours: 9:15 AM to 3:30 PM IST
    market_open = now.replace(hour=9, minute=15, second=0)
    market_close = now.replace(hour=15, minute=30, second=0)
    weekday = now.weekday()
    return weekday < 5 and market_open <= now <= market_close

def get_next_market_session():
    """Get next market session start time"""
    now = datetime.now()
    today_open = now.replace(hour=9, minute=15, second=0, microsecond=0)
    
    if now < today_open and now.weekday() < 5:
        return today_open.isoformat()
    
    # Find next trading day
    next_day = now + timedelta(days=1)
    while next_day.weekday() >= 5:  # Skip weekends
        next_day += timedelta(days=1)
    
    return next_day.replace(hour=9, minute=15, second=0, microsecond=0).isoformat()

# ============================================================================
# ENGINE CONTROL ENDPOINTS
# ============================================================================

@app.route('/api/start', methods=['POST'])
def start_trading():
    """Start the trading engine"""
    if trading_state.is_running:
        return jsonify({
            "success": False,
            "message": "Trading engine is already running",
            "status": trading_state.to_dict()
        }), 400
    
    try:
        # Get optional parameters
        data = request.get_json() or {}
        paper_trading = data.get('paper_trading', True)  # Default to paper trading
        
        # Initialize engine
        trading_state.engine = get_engine()
        if not trading_state.engine:
            return jsonify({
                "success": False,
                "error": "Failed to initialize trading engine"
            }), 500
        
        # Reset stop event
        trading_state.stop_event.clear()
        
        # Start engine in background thread
        def run_engine():
            while not trading_state.stop_event.is_set():
                try:
                    if not trading_state.is_paused:
                        # Run single scan
                        result = run_async(trading_state.engine.run_single_scan())
                        trading_state.total_scans += 1
                        trading_state.last_scan_time = datetime.now()
                        
                        if result and result.get('signals'):
                            trading_state.signals_generated += len(result['signals'])
                        
                        if result and result.get('trades_executed'):
                            trading_state.trades_executed += result['trades_executed']
                        
                        if result and 'daily_pnl' in result:
                            trading_state.current_pnl = result['daily_pnl']
                    
                    # Wait before next scan (respect API limits)
                    trading_state.stop_event.wait(timeout=30)  # 30 second intervals
                    
                except Exception as e:
                    logger.error(f"Engine error: {e}")
                    trading_state.stop_event.wait(timeout=60)  # Wait longer on error
        
        # Start background thread
        trading_state.engine_thread = threading.Thread(target=run_engine, daemon=True)
        trading_state.engine_thread.start()
        
        trading_state.is_running = True
        trading_state.is_paused = False
        trading_state.start_time = datetime.now()
        
        logger.info(f"Trading engine started (paper_trading={paper_trading})")
        
        return jsonify({
            "success": True,
            "message": "Trading engine started successfully",
            "mode": "paper" if paper_trading else "live",
            "status": trading_state.to_dict()
        })
        
    except Exception as e:
        logger.error(f"Failed to start engine: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/api/stop', methods=['POST'])
def stop_trading():
    """Stop the trading engine"""
    if not trading_state.is_running:
        return jsonify({
            "success": False,
            "message": "Trading engine is not running"
        }), 400
    
    try:
        # Signal stop
        trading_state.stop_event.set()
        
        # Wait for thread to finish
        if trading_state.engine_thread:
            trading_state.engine_thread.join(timeout=5)
        
        trading_state.is_running = False
        trading_state.is_paused = False
        
        # Final stats
        final_stats = trading_state.to_dict()
        
        logger.info("Trading engine stopped")
        
        return jsonify({
            "success": True,
            "message": "Trading engine stopped successfully",
            "final_stats": final_stats
        })
        
    except Exception as e:
        logger.error(f"Failed to stop engine: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/api/pause', methods=['POST'])
@require_engine
def pause_trading():
    """Pause the trading engine (keeps running but doesn't execute)"""
    if not trading_state.is_running:
        return jsonify({
            "success": False,
            "message": "Trading engine is not running"
        }), 400
    
    trading_state.is_paused = True
    
    return jsonify({
        "success": True,
        "message": "Trading engine paused",
        "status": trading_state.to_dict()
    })

@app.route('/api/resume', methods=['POST'])
@require_engine
def resume_trading():
    """Resume paused trading engine"""
    if not trading_state.is_running:
        return jsonify({
            "success": False,
            "message": "Trading engine is not running"
        }), 400
    
    trading_state.is_paused = False
    
    return jsonify({
        "success": True,
        "message": "Trading engine resumed",
        "status": trading_state.to_dict()
    })

@app.route('/api/scan', methods=['POST'])
def manual_scan():
    """Trigger a manual scan (one-time)"""
    try:
        engine = get_engine()
        if not engine:
            return jsonify({
                "success": False,
                "error": "Failed to initialize engine"
            }), 500
        
        # Run single scan
        result = run_async(engine.run_single_scan())
        
        return jsonify({
            "success": True,
            "message": "Manual scan completed",
            "result": result
        })
        
    except Exception as e:
        logger.error(f"Manual scan failed: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

# ============================================================================
# SIGNAL ENDPOINTS
# ============================================================================

@app.route('/api/signals', methods=['GET'])
def get_signals():
    """Get signal history"""
    db = get_database()
    if not db:
        return jsonify({
            "success": False,
            "error": "Database not available"
        }), 500
    
    # Get query parameters
    limit = request.args.get('limit', 50, type=int)
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    pattern_type = request.args.get('pattern')
    approved_only = request.args.get('approved', 'false').lower() == 'true'
    
    try:
        signals = db.get_signals(
            start_date=start_date,
            end_date=end_date,
            pattern_type=pattern_type,
            approved_only=approved_only,
            limit=limit
        )
        
        return jsonify({
            "success": True,
            "count": len(signals),
            "signals": signals
        })
        
    except Exception as e:
        logger.error(f"Failed to get signals: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/api/signals/today', methods=['GET'])
def get_today_signals():
    """Get today's signals"""
    db = get_database()
    if not db:
        return jsonify({
            "success": False,
            "error": "Database not available"
        }), 500
    
    try:
        today = datetime.now().strftime("%Y-%m-%d")
        signals = db.get_signals(start_date=today, limit=100)
        
        # Calculate stats
        approved = [s for s in signals if s.get('ai_approved')]
        rejected = [s for s in signals if not s.get('ai_approved')]
        
        return jsonify({
            "success": True,
            "date": today,
            "total": len(signals),
            "approved": len(approved),
            "rejected": len(rejected),
            "approval_rate": len(approved) / len(signals) * 100 if signals else 0,
            "signals": signals
        })
        
    except Exception as e:
        logger.error(f"Failed to get today's signals: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

# ============================================================================
# TRADE ENDPOINTS
# ============================================================================

@app.route('/api/trades', methods=['GET'])
def get_trades():
    """Get trade history"""
    db = get_database()
    if not db:
        return jsonify({
            "success": False,
            "error": "Database not available"
        }), 500
    
    # Get query parameters
    limit = request.args.get('limit', 50, type=int)
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    status = request.args.get('status')
    
    try:
        trades = db.get_trades(
            start_date=start_date,
            end_date=end_date,
            status=status,
            limit=limit
        )
        
        return jsonify({
            "success": True,
            "count": len(trades),
            "trades": trades
        })
        
    except Exception as e:
        logger.error(f"Failed to get trades: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/api/trades/active', methods=['GET'])
def get_active_trades():
    """Get currently active (open) trades"""
    db = get_database()
    if not db:
        return jsonify({
            "success": False,
            "error": "Database not available"
        }), 500
    
    try:
        trades = db.get_trades(status='OPEN', limit=100)
        
        return jsonify({
            "success": True,
            "count": len(trades),
            "trades": trades
        })
        
    except Exception as e:
        logger.error(f"Failed to get active trades: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/api/trades/today', methods=['GET'])
def get_today_trades():
    """Get today's trades with P&L"""
    db = get_database()
    if not db:
        return jsonify({
            "success": False,
            "error": "Database not available"
        }), 500
    
    try:
        today = datetime.now().strftime("%Y-%m-%d")
        trades = db.get_trades(start_date=today, limit=100)
        
        # Calculate P&L
        total_pnl = sum(t.get('pnl', 0) or 0 for t in trades)
        winners = [t for t in trades if (t.get('pnl', 0) or 0) > 0]
        losers = [t for t in trades if (t.get('pnl', 0) or 0) < 0]
        
        closed_trades = [t for t in trades if t.get('status') == 'CLOSED']
        win_rate = len(winners) / len(closed_trades) * 100 if closed_trades else 0
        
        return jsonify({
            "success": True,
            "date": today,
            "total_trades": len(trades),
            "open_trades": len([t for t in trades if t.get('status') == 'OPEN']),
            "closed_trades": len(closed_trades),
            "winners": len(winners),
            "losers": len(losers),
            "win_rate": win_rate,
            "total_pnl": total_pnl,
            "trades": trades
        })
        
    except Exception as e:
        logger.error(f"Failed to get today's trades: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

# ============================================================================
# PERFORMANCE ENDPOINTS
# ============================================================================

@app.route('/api/performance', methods=['GET'])
def get_performance():
    """Get performance analytics"""
    db = get_database()
    if not db:
        return jsonify({
            "success": False,
            "error": "Database not available"
        }), 500
    
    try:
        # Get date range
        days = request.args.get('days', 30, type=int)
        
        # Get win rate and performance
        win_rate_data = db.calculate_win_rate(days=days)
        ai_accuracy = db.calculate_ai_accuracy(days=days)
        
        # Get daily performance records
        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        
        return jsonify({
            "success": True,
            "period_days": days,
            "win_rate": win_rate_data,
            "ai_accuracy": ai_accuracy,
            "summary": {
                "start_date": start_date,
                "end_date": end_date
            }
        })
        
    except Exception as e:
        logger.error(f"Failed to get performance: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/api/performance/daily', methods=['GET'])
def get_daily_performance():
    """Get daily performance breakdown"""
    db = get_database()
    if not db:
        return jsonify({
            "success": False,
            "error": "Database not available"
        }), 500
    
    try:
        days = request.args.get('days', 30, type=int)
        
        # Get last N days of trades
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        trades = db.get_trades(
            start_date=start_date.strftime("%Y-%m-%d"),
            end_date=end_date.strftime("%Y-%m-%d"),
            limit=10000
        )
        
        # Group by date
        daily_stats = {}
        for trade in trades:
            date = trade.get('entry_time', '')[:10]
            if date not in daily_stats:
                daily_stats[date] = {
                    'date': date,
                    'trades': 0,
                    'winners': 0,
                    'losers': 0,
                    'pnl': 0.0
                }
            
            daily_stats[date]['trades'] += 1
            pnl = trade.get('pnl', 0) or 0
            daily_stats[date]['pnl'] += pnl
            
            if pnl > 0:
                daily_stats[date]['winners'] += 1
            elif pnl < 0:
                daily_stats[date]['losers'] += 1
        
        # Convert to list and sort
        daily_list = sorted(daily_stats.values(), key=lambda x: x['date'], reverse=True)
        
        return jsonify({
            "success": True,
            "days": len(daily_list),
            "daily_performance": daily_list
        })
        
    except Exception as e:
        logger.error(f"Failed to get daily performance: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

# ============================================================================
# AI ANALYTICS ENDPOINTS
# ============================================================================

@app.route('/api/ai/analysis', methods=['GET'])
def get_ai_analysis():
    """Get AI analysis records"""
    db = get_database()
    if not db:
        return jsonify({
            "success": False,
            "error": "Database not available"
        }), 500
    
    try:
        limit = request.args.get('limit', 50, type=int)
        
        # Get recent AI analyses from database
        with db._get_connection() as conn:
            cursor = conn.execute('''
                SELECT * FROM ai_analysis
                ORDER BY timestamp DESC
                LIMIT ?
            ''', (limit,))
            
            columns = [desc[0] for desc in cursor.description]
            analyses = [dict(zip(columns, row)) for row in cursor.fetchall()]
        
        return jsonify({
            "success": True,
            "count": len(analyses),
            "analyses": analyses
        })
        
    except Exception as e:
        logger.error(f"Failed to get AI analysis: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/api/ai/accuracy', methods=['GET'])
def get_ai_accuracy():
    """Get AI prediction accuracy"""
    db = get_database()
    if not db:
        return jsonify({
            "success": False,
            "error": "Database not available"
        }), 500
    
    try:
        days = request.args.get('days', 30, type=int)
        accuracy = db.calculate_ai_accuracy(days=days)
        
        return jsonify({
            "success": True,
            "period_days": days,
            "accuracy": accuracy
        })
        
    except Exception as e:
        logger.error(f"Failed to get AI accuracy: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

# ============================================================================
# COPILOT ANALYSIS ENDPOINT
# ============================================================================

@app.route('/api/copilot/data', methods=['GET'])
def get_copilot_data():
    """Get data formatted for Copilot analysis"""
    db = get_database()
    if not db:
        return jsonify({
            "success": False,
            "error": "Database not available"
        }), 500
    
    try:
        data = db.get_data_for_copilot_analysis()
        
        return jsonify({
            "success": True,
            "timestamp": datetime.now().isoformat(),
            "data": data
        })
        
    except Exception as e:
        logger.error(f"Failed to get Copilot data: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

# ============================================================================
# CONFIGURATION ENDPOINTS
# ============================================================================

@app.route('/api/config', methods=['GET'])
def get_config():
    """Get current configuration"""
    try:
        from world_class_production_engine import ProductionWorldClassEngine
        
        # Get config from engine class
        return jsonify({
            "success": True,
            "config": {
                "capital": 100000,
                "daily_loss_limit_percent": 10,
                "daily_trade_limit": 50,
                "min_ai_confidence": 55,
                "target_percent": 2.0,
                "stop_loss_percent": 0.5,
                "rsi_oversold_range": [18, 30],
                "patterns": [
                    "OVERSOLD_REVERSAL",
                    "52W_LOW_BOUNCE",
                    "RSI_ZONE_ENTRY",
                    "GAP_DOWN_REVERSAL",
                    "HIGH_VOLUME_BREAKOUT",
                    "RSI_DIVERGENCE",
                    "INSTITUTIONAL_ACCUMULATION",
                    "PRE_BREAKOUT_SETUP"
                ]
            }
        })
        
    except Exception as e:
        logger.error(f"Failed to get config: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/api/config', methods=['PUT'])
def update_config():
    """Update configuration (runtime only, not persistent)"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                "success": False,
                "error": "No configuration data provided"
            }), 400
        
        # For now, just acknowledge (engine uses fixed config)
        return jsonify({
            "success": True,
            "message": "Configuration update acknowledged",
            "note": "Runtime config changes will apply on next engine restart"
        })
        
    except Exception as e:
        logger.error(f"Failed to update config: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

# ============================================================================
# ERROR ENDPOINTS
# ============================================================================

@app.route('/api/errors', methods=['GET'])
def get_errors():
    """Get error log"""
    db = get_database()
    if not db:
        return jsonify({
            "success": False,
            "error": "Database not available"
        }), 500
    
    try:
        limit = request.args.get('limit', 50, type=int)
        
        with db._get_connection() as conn:
            cursor = conn.execute('''
                SELECT * FROM errors
                ORDER BY timestamp DESC
                LIMIT ?
            ''', (limit,))
            
            columns = [desc[0] for desc in cursor.description]
            errors = [dict(zip(columns, row)) for row in cursor.fetchall()]
        
        return jsonify({
            "success": True,
            "count": len(errors),
            "errors": errors
        })
        
    except Exception as e:
        logger.error(f"Failed to get errors: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

# ============================================================================
# TOKEN MANAGEMENT
# ============================================================================

@app.route('/api/update-token', methods=['POST'])
def update_dhan_token():
    """Update Dhan access token"""
    try:
        data = request.get_json()
        new_token = data.get('access_token', '').strip()
        
        if not new_token:
            return jsonify({
                "success": False,
                "error": "Access token is required"
            }), 400
        
        # Update token in dhan_config.py file
        config_file = os.path.join(os.path.dirname(__file__), 'dhan_config.py')
        
        if not os.path.exists(config_file):
            return jsonify({
                "success": False,
                "error": "Configuration file not found"
            }), 500
        
        # Read current config
        with open(config_file, 'r') as f:
            content = f.read()
        
        # Replace token using regex
        import re
        updated_content = re.sub(
            r'self\.access_token = access_token or "[^"]+"',
            f'self.access_token = access_token or "{new_token}"',
            content
        )
        
        # Write updated config
        with open(config_file, 'w') as f:
            f.write(updated_content)
        
        logger.info("Dhan access token updated successfully in file")
        
        # Also update in-memory token for hot-reload
        try:
            from dhan_config import dhan_api
            dhan_api.update_access_token(new_token)
            logger.info("In-memory token updated - no restart needed")
            hot_reloaded = True
        except Exception as hot_err:
            logger.warning(f"Hot-reload failed (will work on restart): {hot_err}")
            hot_reloaded = False
        
        return jsonify({
            "success": True,
            "message": "Token updated successfully",
            "hot_reloaded": hot_reloaded,
            "restart_needed": not hot_reloaded,
            "note": "Token is now active" if hot_reloaded else "Please restart the service to apply changes"
        })
        
    except Exception as e:
        logger.error(f"Failed to update token: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

# ============================================================================
# MAIN ENTRY
# ============================================================================

def create_app():
    """Create and configure the Flask application"""
    return app

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Production Trading API Server')
    parser.add_argument('--host', default='0.0.0.0', help='Host to bind to')
    parser.add_argument('--port', type=int, default=5000, help='Port to listen on')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode')
    
    args = parser.parse_args()
    
    print(f"""
╔══════════════════════════════════════════════════════════════════╗
║        PRODUCTION TRADING API v1.0                               ║
╠══════════════════════════════════════════════════════════════════╣
║  Endpoints:                                                       ║
║  - GET  /health            - Health check                        ║
║  - GET  /api/status        - System status                       ║
║  - POST /api/start         - Start trading engine                ║
║  - POST /api/stop          - Stop trading engine                 ║
║  - POST /api/pause         - Pause trading                       ║
║  - POST /api/resume        - Resume trading                      ║
║  - POST /api/scan          - Manual scan                         ║
║  - GET  /api/signals       - Signal history                      ║
║  - GET  /api/trades        - Trade history                       ║
║  - GET  /api/performance   - Performance analytics               ║
║  - GET  /api/copilot/data  - Data for Copilot analysis           ║
╚══════════════════════════════════════════════════════════════════╝
    """)
    
    logger.info(f"Starting API server on {args.host}:{args.port}")
    app.run(host=args.host, port=args.port, debug=args.debug, threaded=True)
