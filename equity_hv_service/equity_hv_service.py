#!/usr/bin/env python3
"""
Equity High-Velocity (HV) Trading Service - Production Ready
Integrated with Gemini AI Trading Engine for F&O Stock Screening
SQLite Database for Signal/Trade Storage and ML Enhancement

Port: 5080
"""

import asyncio
import json
import logging
import os
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# Setup paths
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)
if current_dir in sys.path:
    sys.path.remove(current_dir)

# Create necessary directories
Path("logs").mkdir(exist_ok=True)
Path("data").mkdir(exist_ok=True)

# State file for persistence
STATE_FILE = Path("data") / "equity_strategy_state.json"

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/equity_hv_service.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ============================================================================
# CONFIGURATION
# ============================================================================

# Elite F&O stocks for trading
ELITE_STOCKS = {
    'RELIANCE': {'priority': 1, 'lot_size': 250},
    'TCS': {'priority': 2, 'lot_size': 175},
    'HDFCBANK': {'priority': 3, 'lot_size': 550},
    'INFY': {'priority': 4, 'lot_size': 400},
    'ICICIBANK': {'priority': 5, 'lot_size': 1375},
    'KOTAKBANK': {'priority': 6, 'lot_size': 400},
    'BHARTIARTL': {'priority': 7, 'lot_size': 475},
    'ITC': {'priority': 8, 'lot_size': 1600},
    'SBIN': {'priority': 9, 'lot_size': 1500},
    'BAJFINANCE': {'priority': 10, 'lot_size': 125}
}

SERVICE_CONFIG = {
    "name": "equity-hv-trading",
    "version": "3.0.0",
    "build": "gemini-integrated",
    "port": 5080,
    "gemini_service_url": "http://localhost:4080",
    "capital": 500000,
    "max_positions": 5,
    "stop_loss_pct": 2.0,
    "target_pct": 3.0
}

# ============================================================================
# STATE PERSISTENCE
# ============================================================================

def load_strategy_state() -> bool:
    """Load strategy enabled state from file"""
    try:
        if STATE_FILE.exists():
            with open(STATE_FILE, 'r') as f:
                data = json.load(f)
                return data.get('strategy_enabled', True)  # Default: enabled
        return True  # Default: enabled
    except Exception as e:
        logger.warning(f"Could not load strategy state: {e}. Defaulting to enabled.")
        return True

def save_strategy_state(enabled: bool):
    """Persist strategy enabled state to file"""
    try:
        with open(STATE_FILE, 'w') as f:
            json.dump({'strategy_enabled': enabled}, f)
        logger.info(f"Strategy state saved: {'enabled' if enabled else 'disabled'}")
    except Exception as e:
        logger.error(f"Failed to save strategy state: {e}")

# Service state
service_state = {
    "is_running": False,
    "strategy_enabled": load_strategy_state(),  # Load persisted state
    "start_time": None,
    "gemini_connected": False,
    "database_connected": False,
    "auto_trader_running": False,
    "alpha_engine": None  # Institutional Alpha Engine
}

# ============================================================================
# IMPORT ROUTERS
# ============================================================================

# Import Gemini Engine Router
try:
    from gemini_engine_router import router as gemini_engine_router
    GEMINI_ROUTER_AVAILABLE = True
    logger.info("[OK] Gemini AI Trading Engine router loaded")
except ImportError as e:
    GEMINI_ROUTER_AVAILABLE = False
    logger.warning(f"Gemini Engine router not available: {e}")

# Import Production Auto-Trader Router
try:
    from strategy.auto_trader_router import router as auto_trader_router
    AUTO_TRADER_AVAILABLE = True
    logger.info("[OK] Production Auto-Trader router loaded")
except ImportError as e:
    AUTO_TRADER_AVAILABLE = False
    logger.warning(f"Auto-Trader router not available: {e}")

# Import Legendary Live Trading Engine Router
try:
    from strategy.legendary_live_engine import router as legendary_router
    LEGENDARY_AVAILABLE = True
    logger.info("[OK] Legendary Live Trading Engine router loaded (83.3% WR)")
except ImportError as e:
    LEGENDARY_AVAILABLE = False
    logger.warning(f"Legendary Engine router not available: {e}")

# Import Legendary Production Engine Router (v2.0 - Multi-Position + Full AI)
try:
    from strategy.legendary_production_engine import router as production_router
    PRODUCTION_AVAILABLE = True
    logger.info("[OK] Legendary Production Engine v2.0 loaded (Multi-Position + 3-Tier AI)")
except ImportError as e:
    PRODUCTION_AVAILABLE = False
    logger.warning(f"Production Engine router not available: {e}")

# Import Analytics Database Router
try:
    from database.analytics_router import router as analytics_router
    ANALYTICS_AVAILABLE = True
    logger.info("[OK] Analytics Database router loaded")
except ImportError as e:
    ANALYTICS_AVAILABLE = False
    logger.warning(f"Analytics router not available: {e}")

# Import Elite Options Scanner Router (NEW - F&O Screener-Based Trading)
try:
    from strategy.scanner_api_router import router as scanner_router, initialize_scanner, shutdown_scanner
    SCANNER_AVAILABLE = True
    logger.info("[OK] Elite Options Scanner router loaded (Screener-Based F&O Trading)")
except ImportError as e:
    SCANNER_AVAILABLE = False
    logger.warning(f"Elite Options Scanner router not available: {e}")

# Import Probe-Scale Trading Router (NEW - 10% Probe + 90% Scale with Gemini 3 Pro)
try:
    from api.probe_scale_router import router as probe_scale_router, set_executor as set_probe_executor
    from strategy.probe_scale_executor import ProbeScaleExecutor
    PROBE_SCALE_AVAILABLE = True
    logger.info("[OK] Probe-Scale Trading router loaded (10% Probe + 50% Wide SL)")
except ImportError as e:
    PROBE_SCALE_AVAILABLE = False
    logger.warning(f"Probe-Scale Trading router not available: {e}")

# Import API Router
try:
    from api.equity_hv_router import router as api_router
    API_ROUTER_AVAILABLE = True
    logger.info("[OK] API router loaded")
except ImportError as e:
    API_ROUTER_AVAILABLE = False
    logger.warning(f"API router not available: {e}")

# Import Production Trading Router (NEW - Probe-Scale + Paper/Live mode)
try:
    from strategy.trading_router import router as production_trading_router
    PRODUCTION_TRADING_AVAILABLE = True
    logger.info("[OK] Production Trading Engine router loaded (Probe-Scale + Paper/Live mode)")
except ImportError as e:
    PRODUCTION_TRADING_AVAILABLE = False
    logger.warning(f"Production Trading router not available: {e}")

# Import Institutional Alpha Engine (Statistical Arbitrage, Multi-Factor, Order Flow)
try:
    from strategy.institutional_alpha_engine import (
        InstitutionalEquityAlphaEngine,
        create_alpha_engine,
        AlphaSignal,
        MarketRegime,
        AlphaType
    )
    ALPHA_ENGINE_AVAILABLE = True
    logger.info("[OK] Institutional Alpha Engine loaded (Stat Arb, Multi-Factor, Order Flow)")
except ImportError as e:
    ALPHA_ENGINE_AVAILABLE = False
    logger.warning(f"Institutional Alpha Engine not available: {e}")

# Import Evaluation Executor (Paper Trading Evaluation without Real Money)
try:
    from database.evaluation_executor import (
        EquityEvaluationExecutor,
        get_equity_evaluation_executor
    )
    EVALUATION_EXECUTOR_AVAILABLE = True
    logger.info("[OK] Evaluation Executor loaded (Paper Trading Evaluation)")
except ImportError as e:
    EVALUATION_EXECUTOR_AVAILABLE = False
    logger.warning(f"Evaluation Executor not available: {e}")

# ============================================================================
# LIFESPAN MANAGEMENT
# ============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    try:
        logger.info("=" * 60)
        logger.info("Starting Equity HV Trading Service")
        logger.info(f"Version: {SERVICE_CONFIG['version']} | Build: {SERVICE_CONFIG['build']}")
        logger.info("=" * 60)
        
        service_state["is_running"] = True
        service_state["start_time"] = datetime.now()
        
        # Initialize database connection
        try:
            from database.db_manager import get_database
            db = get_database()
            service_state["database_connected"] = True
            logger.info(f"[OK] Database connected: {db.db_path}")
        except Exception as e:
            logger.warning(f"Database not available: {e}")
        
        # Check Gemini service connectivity
        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{SERVICE_CONFIG['gemini_service_url']}/health", timeout=aiohttp.ClientTimeout(total=5)) as resp:
                    if resp.status == 200:
                        service_state["gemini_connected"] = True
                        logger.info("[OK] Gemini Trade Service connected")
        except Exception as e:
            logger.warning(f"Gemini service not reachable: {e}")
        
        # Initialize Elite Options Scanner (NEW)
        if SCANNER_AVAILABLE:
            try:
                await initialize_scanner()
                logger.info("[OK] Elite Options Scanner initialized")
            except Exception as e:
                logger.warning(f"Elite Options Scanner initialization failed: {e}")
        
        # Initialize Institutional Alpha Engine (Stat Arb, Multi-Factor, Order Flow)
        if ALPHA_ENGINE_AVAILABLE:
            try:
                service_state["alpha_engine"] = create_alpha_engine({
                    'elite_stocks': list(ELITE_STOCKS.keys()),
                    'max_position_pct': 20.0,
                    'max_sector_exposure': 40.0,
                    'min_alpha_threshold': 0.01,
                    'rebalance_threshold': 0.05
                })
                logger.info("[OK] Institutional Alpha Engine initialized (Multi-Factor + Stat Arb)")
            except Exception as e:
                logger.warning(f"Alpha Engine initialization failed: {e}")
        
        logger.info(f"Elite Stocks Configured: {len(ELITE_STOCKS)}")
        logger.info(f"Capital: Rs.{SERVICE_CONFIG['capital']:,.2f}")
        logger.info("=" * 60)
        
        yield
        
    except Exception as e:
        logger.error(f"Critical error during startup: {e}")
        raise
    finally:
        logger.info("Shutting down Equity HV Trading Service")
        
        # Shutdown Elite Options Scanner (NEW)
        if SCANNER_AVAILABLE:
            try:
                await shutdown_scanner()
                logger.info("[OK] Elite Options Scanner shutdown complete")
            except Exception as e:
                logger.warning(f"Elite Options Scanner shutdown error: {e}")
        
        service_state["is_running"] = False


# ============================================================================
# CREATE FASTAPI APP
# ============================================================================

app = FastAPI(
    title="Equity HV Trading Service",
    description="High-Velocity F&O Trading with Gemini AI Integration",
    version=SERVICE_CONFIG["version"],
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================================
# REGISTER ROUTERS
# ============================================================================

if GEMINI_ROUTER_AVAILABLE:
    app.include_router(gemini_engine_router, prefix="/api/gemini-engine", tags=["gemini-engine"])
    logger.info("[OK] Gemini Engine endpoints registered at /api/gemini-engine")

if AUTO_TRADER_AVAILABLE:
    app.include_router(auto_trader_router, prefix="/api/auto-trader", tags=["auto-trader"])
    logger.info("[OK] Auto-Trader endpoints registered at /api/auto-trader")

if LEGENDARY_AVAILABLE:
    app.include_router(legendary_router, tags=["legendary-engine"])
    logger.info("[OK] Legendary Engine endpoints registered at /api/legendary-engine")

if PRODUCTION_AVAILABLE:
    app.include_router(production_router, tags=["legendary-production"])
    logger.info("[OK] Production Engine v2.0 endpoints registered at /api/legendary-engine (Multi-Position)")

if ANALYTICS_AVAILABLE:
    app.include_router(analytics_router, prefix="/api/analytics", tags=["analytics"])
    logger.info("[OK] Analytics endpoints registered at /api/analytics")

if API_ROUTER_AVAILABLE:
    app.include_router(api_router, prefix="/api/strategy", tags=["strategy"])
    logger.info("[OK] Strategy endpoints registered at /api/strategy")

# Register Elite Options Scanner Router (NEW - Screener-Based F&O Trading)
if SCANNER_AVAILABLE:
    app.include_router(scanner_router, tags=["elite-options-scanner"])
    logger.info("[OK] Elite Options Scanner endpoints registered at /api/scanner")

# Register Probe-Scale Trading Router (NEW - 10% Probe + 90% Scale)
if PROBE_SCALE_AVAILABLE:
    try:
        # Initialize the probe-scale executor
        probe_executor = ProbeScaleExecutor()
        set_probe_executor(probe_executor)
        app.include_router(probe_scale_router, tags=["probe-scale-trading"])
        logger.info("[OK] Probe-Scale Trading endpoints registered at /api/probe")
        logger.info("     → Probe: 10% capital | Scale: 90% on confirmation")
        logger.info("     → Stoploss: 50% wide | Trailing: 50pt after 50pt profit")
    except Exception as e:
        logger.warning(f"Probe-Scale Trading initialization failed: {e}")

# Register Production Trading Router (NEW - Paper/Live mode with full engine)
if PRODUCTION_TRADING_AVAILABLE:
    app.include_router(production_trading_router, prefix="/api/trading", tags=["production-trading"])
    logger.info("[OK] Production Trading Engine endpoints registered at /api/trading")
    logger.info("     → Paper mode (default) | Live mode switchable")
    logger.info("     → Probe-Scale: 10% probe + 90% on Gemini confirmation")


# ============================================================================
# CORE ENDPOINTS
# ============================================================================

@app.get("/health")
async def health_check():
    """Service health check"""
    uptime = None
    if service_state["start_time"]:
        uptime = str(datetime.now() - service_state["start_time"])
    
    return {
        "status": "healthy",
        "service": SERVICE_CONFIG["name"],
        "version": SERVICE_CONFIG["version"],
        "build": SERVICE_CONFIG["build"],
        "uptime": uptime,
        "timestamp": datetime.now().isoformat(),
        "connections": {
            "database": service_state["database_connected"],
            "gemini_service": service_state["gemini_connected"]
        },
        "config": {
            "elite_stocks": len(ELITE_STOCKS),
            "capital": SERVICE_CONFIG["capital"],
            "gemini_url": SERVICE_CONFIG["gemini_service_url"]
        }
    }


@app.get("/alpha-signals")
async def get_alpha_signals():
    """
    Get institutional-grade alpha signals.
    
    Uses:
    - Statistical Arbitrage (Pairs Trading, Mean Reversion)
    - Multi-Factor Model (Momentum, Value, Quality, Volatility)
    - Order Flow Analysis (OFI, VPIN, Iceberg Detection)
    - Regime Detection (Market State Classification)
    """
    if not service_state["alpha_engine"]:
        return {
            "success": False,
            "message": "Alpha engine not initialized",
            "signals": []
        }
    
    try:
        alpha_engine = service_state["alpha_engine"]
        summary = alpha_engine.get_summary()
        
        return {
            "success": True,
            "regime": summary.get('current_regime', 'UNKNOWN'),
            "signals": summary.get('recent_signals', []),
            "factor_exposures": summary.get('factor_exposures', {}),
            "stat_arb_pairs": summary.get('active_pairs', []),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting alpha signals: {e}")
        raise HTTPException(500, str(e))


@app.get("/market-regime")
async def get_market_regime():
    """Get current detected market regime (TRENDING/MEAN_REVERTING/VOLATILE/CRISIS)"""
    if not service_state["alpha_engine"]:
        return {"regime": "UNKNOWN", "message": "Alpha engine not initialized"}
    
    try:
        alpha_engine = service_state["alpha_engine"]
        regime = alpha_engine.regime_detector.current_regime
        params = alpha_engine.regime_detector.get_regime_adjusted_params()
        
        return {
            "regime": regime.value if hasattr(regime, 'value') else str(regime),
            "parameters": params,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting market regime: {e}")
        return {"regime": "UNKNOWN", "error": str(e)}


@app.get("/factor-scores/{symbol}")
async def get_factor_scores(symbol: str):
    """Get multi-factor alpha scores for a specific stock"""
    if not service_state["alpha_engine"]:
        raise HTTPException(503, "Alpha engine not initialized")
    
    try:
        alpha_engine = service_state["alpha_engine"]
        factor_model = alpha_engine.factor_model
        
        # Note: This requires price data - for now return structure
        return {
            "symbol": symbol.upper(),
            "factors": {
                "momentum": "Requires price data",
                "value": "Requires fundamental data",
                "quality": "Requires fundamental data",
                "volatility": "Requires price data"
            },
            "message": "Pass price data via /alpha-signals/analyze endpoint",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting factor scores: {e}")
        raise HTTPException(500, str(e))


@app.get("/config")
@app.get("/api/config")
async def get_config():
    """Get service configuration"""
    return {
        "capital": SERVICE_CONFIG.get("capital", 100000),
        "max_daily_loss": SERVICE_CONFIG.get("max_daily_loss_pct", 0.05),
        "paper_trading": True,
        "service": SERVICE_CONFIG,
        "elite_stocks": ELITE_STOCKS,
        "trading_params": {
            "max_positions": SERVICE_CONFIG["max_positions"],
            "stop_loss_pct": SERVICE_CONFIG["stop_loss_pct"],
            "target_pct": SERVICE_CONFIG["target_pct"]
        }
    }


@app.get("/status")
async def get_status():
    """Get detailed service status"""
    return {
        "status": "running" if service_state["is_running"] else "stopped",
        "state": service_state,
        "routers": {
            "gemini_engine": GEMINI_ROUTER_AVAILABLE,
            "auto_trader": AUTO_TRADER_AVAILABLE,
            "analytics": ANALYTICS_AVAILABLE,
            "api": API_ROUTER_AVAILABLE,
            "elite_scanner": SCANNER_AVAILABLE
        },
        "endpoints_available": {
            "/api/gemini-engine/*": GEMINI_ROUTER_AVAILABLE,
            "/api/auto-trader/*": AUTO_TRADER_AVAILABLE,
            "/api/analytics/*": ANALYTICS_AVAILABLE,
            "/api/strategy/*": API_ROUTER_AVAILABLE,
            "/api/scanner/*": SCANNER_AVAILABLE
        }
    }


@app.get("/stocks")
async def get_stocks():
    """Get configured elite stocks"""
    return {
        "count": len(ELITE_STOCKS),
        "stocks": ELITE_STOCKS
    }


@app.get("/api/signals")
async def get_api_signals():
    """Get trading signals in frontend-compatible format"""
    try:
        # This service monitors elite stocks for HV opportunities
        # Returns empty for now, can be expanded to store signal history
        return {
            "signals": [],
            "count": 0,
            "message": "Elite Equity HV service monitors stocks via Gemini engine and auto-trader",
            "timestamp": datetime.now().isoformat(),
            "stocks_monitored": len(ELITE_STOCKS)
        }
    except Exception as e:
        logger.error(f"Error in /api/signals: {e}")
        return {
            "signals": [],
            "count": 0,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }


@app.put("/config")
@app.put("/api/config")
async def update_config(request: dict):
    """Update service configuration"""
    try:
        if 'capital' in request:
            SERVICE_CONFIG['capital'] = float(request['capital'])
            logger.info(f"Capital updated to: ₹{SERVICE_CONFIG['capital']:,.0f}")
        
        if 'max_daily_loss' in request:
            SERVICE_CONFIG['max_daily_loss_pct'] = float(request['max_daily_loss'])
            logger.info(f"Max daily loss updated to: {SERVICE_CONFIG['max_daily_loss_pct']*100:.1f}%")
        
        return {
            "success": True,
            "capital": SERVICE_CONFIG['capital'],
            "max_daily_loss": SERVICE_CONFIG.get('max_daily_loss_pct', 0.05),
            "message": "Configuration updated successfully"
        }
    except Exception as e:
        logger.error(f"Failed to update config: {e}")
        return JSONResponse(
            status_code=400,
            content={"success": False, "error": str(e)}
        )


# ==================== TOKEN UPDATE ENDPOINT (HOT-RELOAD) ====================
@app.post("/update-token")
@app.post("/api/update-token")
async def update_dhan_token(request: dict):
    """
    Update Dhan API token at runtime WITHOUT requiring service restart.
    This enables seamless daily token updates.
    """
    try:
        new_token = request.get('access_token', '').strip()
        client_id = request.get('client_id', '1101317572')
        
        if not new_token:
            return JSONResponse(
                status_code=400,
                content={"success": False, "error": "access_token is required"}
            )
        
        # Update config file for persistence
        config_file = Path(current_dir) / "strategy" / "dhan_config.py"
        if config_file.exists():
            import re
            content = config_file.read_text()
            updated_content = re.sub(
                r'self\.access_token = access_token or "[^"]+"',
                f'self.access_token = access_token or "{new_token}"',
                content
            )
            config_file.write_text(updated_content)
            logger.info("Token updated in dhan_config.py")
        
        # Try to update in-memory token
        hot_reloaded = False
        try:
            from strategy.dhan_config import dhan_api
            dhan_api.update_access_token(new_token)
            hot_reloaded = True
            logger.info("In-memory token hot-reloaded successfully")
        except Exception as hot_err:
            logger.warning(f"Hot-reload failed (will work on restart): {hot_err}")
        
        return {
            "success": True,
            "message": "Token updated successfully",
            "hot_reloaded": hot_reloaded,
            "restart_required": not hot_reloaded
        }
        
    except Exception as e:
        logger.error(f"Failed to update token: {e}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )


@app.post("/start")
@app.post("/api/start")
async def start_service(request: dict = None):
    """Enable the Elite Equity HV strategy"""
    try:
        # Update config if provided
        if request:
            if 'capital' in request:
                SERVICE_CONFIG['capital'] = float(request['capital'])
            if 'max_daily_loss' in request:
                SERVICE_CONFIG['max_daily_loss_pct'] = float(request['max_daily_loss'])
        
        # Enable strategy state (persisted)
        save_strategy_state(True)
        service_state["strategy_enabled"] = True
        service_state["is_running"] = True
        logger.info("Elite Equity HV strategy enabled")
        
        return {
            "success": True,
            "message": "Strategy enabled",
            "running": True,
            "strategy_enabled": True
        }
    except Exception as e:
        logger.error(f"Failed to enable strategy: {e}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )


@app.post("/stop")
@app.post("/api/stop")
async def stop_service():
    """Disable the Elite Equity HV strategy"""
    try:
        # Disable strategy state (persisted)
        save_strategy_state(False)
        service_state["strategy_enabled"] = False
        service_state["is_running"] = False
        logger.info("Elite Equity HV strategy disabled")
        
        return {
            "success": True,
            "message": "Strategy disabled",
            "running": False,
            "strategy_enabled": False
        }
    except Exception as e:
        logger.error(f"Failed to disable strategy: {e}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )


@app.get("/api/status")
async def get_api_status():
    """Get status in API format for frontend"""
    return {
        "running": service_state["is_running"],
        "strategy_enabled": service_state["strategy_enabled"],
        "mode": "paper",
        "is_trading_time": True,
        "timestamp": datetime.now().isoformat(),
        "database_connected": service_state["database_connected"],
        "gemini_connected": service_state["gemini_connected"]
    }


# ============================================================================
# TICK FORWARDING & AUTO-EXECUTION ENDPOINTS
# ============================================================================

@app.post("/api/tick-data")
async def receive_tick_data(request: dict):
    """
    Receive tick data from backend for STOCK OPTIONS auto-execution.
    Processes exits and evaluates new entry opportunities.
    
    IMPORTANT: This service trades STOCK OPTIONS (CE/PE), not spot equity.
    - LONG direction = Buy CE (Call) options (bullish on stock)
    - SHORT direction = Buy PE (Put) options (bearish on stock)
    
    Expected format:
    {
        "ticks": [
            {"symbol": "RELIANCE", "ltp": 1234.50, "option_price": 45.50, "option_type": "CE", ...},
            {"symbol": "TCS", "ltp": 3456.00, "option_price": 78.25, "option_type": "PE", ...}
        ]
    }
    """
    try:
        if not EVALUATION_EXECUTOR_AVAILABLE:
            return {"success": False, "error": "Evaluation executor not available"}
        
        if not service_state.get("strategy_enabled", False):
            return {"success": False, "error": "Strategy not enabled", "ticks_processed": 0}
        
        ticks = request.get("ticks", [])
        if not ticks:
            return {"success": True, "ticks_processed": 0}
        
        # Build price map from ticks
        current_prices = {}
        for tick in ticks:
            symbol = tick.get("symbol", "")
            if symbol and symbol in ELITE_STOCKS:
                current_prices[symbol] = tick.get("ltp", 0) or tick.get("last_price", 0)
        
        # Get alpha signals if available
        alpha_signals = {}
        if ALPHA_ENGINE_AVAILABLE and service_state.get("alpha_engine"):
            try:
                alpha_engine = service_state["alpha_engine"]
                summary = alpha_engine.get_summary()
                for signal in summary.get('recent_signals', []):
                    symbol = signal.get('symbol', '')
                    if symbol:
                        alpha_signals[symbol] = {
                            'direction': signal.get('direction', 'neutral'),
                            'strength': signal.get('strength', 0),
                            'alpha_type': signal.get('type', '')
                        }
            except Exception as e:
                logger.warning(f"Failed to get alpha signals: {e}")
        
        # Process exits with intelligent logic
        executor = get_equity_evaluation_executor()
        exit_results = executor.check_exits(current_prices, alpha_signals)
        
        # Track ticks received
        service_state['ticks_received'] = service_state.get('ticks_received', 0) + len(ticks)
        
        return {
            "success": True,
            "ticks_processed": len(current_prices),
            "exit_actions": len(exit_results),
            "exits": exit_results,
            "open_positions": len(executor.get_open_positions()),
            "timestamp": datetime.now().isoformat()
        }
    
    except Exception as e:
        logger.error(f"Error processing tick data: {e}")
        return {"success": False, "error": str(e)}


@app.post("/api/auto-execute")
async def auto_execute_trade(request: dict):
    """
    Auto-execute a STOCK OPTIONS trade from alpha signals.
    
    IMPORTANT: This service trades STOCK OPTIONS (CE/PE):
    - LONG direction = Buy CE (Call) - Bullish on underlying stock
    - SHORT direction = Buy PE (Put) - Bearish on underlying stock
    
    Expected format:
    {
        "symbol": "RELIANCE",
        "direction": "LONG" or "SHORT",  # LONG=CE, SHORT=PE
        "quantity": 250,                   # Number of lots
        "entry_price": 45.50,              # Option premium price
        "option_type": "CE" or "PE",       # Explicit option type
        "strike": 2750,                    # Strike price
        "expiry": "2025-01-02",            # Expiry date
        "signal_strength": 0.85,
        "ai_confidence": 0.9,
        "entry_reason": "Multi-factor alpha signal",
        "strategy_type": "stat_arb" or "momentum" or "pairs"
    }
    """
    try:
        if not EVALUATION_EXECUTOR_AVAILABLE:
            return {"success": False, "error": "Evaluation executor not available"}
        
        if not service_state.get("strategy_enabled", False):
            return {"success": False, "error": "Strategy not enabled"}
        
        symbol = request.get("symbol", "").upper()
        direction = request.get("direction", "LONG").upper()
        quantity = request.get("quantity", 0)
        entry_price = request.get("entry_price", 0)
        
        # Validate elite stock
        if symbol not in ELITE_STOCKS:
            return {"success": False, "error": f"Symbol {symbol} not in elite stocks list"}
        
        # Get lot size if quantity not specified
        if quantity <= 0:
            stock_info = ELITE_STOCKS.get(symbol, {})
            quantity = stock_info.get('lot_size', 100)
        
        executor = get_equity_evaluation_executor()
        
        # Check max positions
        open_positions = executor.get_open_positions()
        max_positions = 5  # Configurable
        if len(open_positions) >= max_positions:
            return {
                "success": False, 
                "error": f"Max positions ({max_positions}) reached",
                "open_positions": len(open_positions)
            }
        
        # Check if already have position in this symbol
        for pos in open_positions:
            if pos.get('symbol') == symbol:
                return {
                    "success": False,
                    "error": f"Already have position in {symbol}",
                    "existing_position": pos
                }
        
        # Enter position
        trade_id = executor.enter_position(
            symbol=symbol,
            direction=direction,
            quantity=quantity,
            entry_price=entry_price,
            signal_strength=request.get("signal_strength", 0),
            ai_confidence=request.get("ai_confidence", 0),
            gemini_decision=request.get("gemini_decision", ""),
            gemini_reasoning=request.get("gemini_reasoning", ""),
            entry_reason=request.get("entry_reason", "API trade"),
            strategy_type=request.get("strategy_type", "manual")
        )
        
        if trade_id:
            logger.info(f"Auto-executed: {direction} {symbol} @ {entry_price} | ID: {trade_id}")
            return {
                "success": True,
                "trade_id": trade_id,
                "symbol": symbol,
                "direction": direction,
                "quantity": quantity,
                "entry_price": entry_price,
                "timestamp": datetime.now().isoformat()
            }
        else:
            return {"success": False, "error": "Failed to enter position"}
    
    except Exception as e:
        logger.error(f"Error in auto-execute: {e}")
        return {"success": False, "error": str(e)}


@app.post("/api/manual-exit")
async def manual_exit_position(request: dict):
    """
    Manually exit a position.
    
    Expected format:
    {
        "trade_id": "EQ-EVAL-xxxx-0001",
        "exit_price": 1250.00,
        "exit_reason": "manual_exit"
    }
    """
    try:
        if not EVALUATION_EXECUTOR_AVAILABLE:
            return {"success": False, "error": "Evaluation executor not available"}
        
        trade_id = request.get("trade_id", "")
        exit_price = request.get("exit_price", 0)
        exit_reason = request.get("exit_reason", "manual_exit")
        
        if not trade_id:
            return {"success": False, "error": "trade_id required"}
        
        executor = get_equity_evaluation_executor()
        pnl = executor.exit_position(trade_id, exit_price, exit_reason)
        
        if pnl is not None:
            return {
                "success": True,
                "trade_id": trade_id,
                "exit_price": exit_price,
                "pnl": pnl,
                "reason": exit_reason,
                "timestamp": datetime.now().isoformat()
            }
        else:
            return {"success": False, "error": f"Trade {trade_id} not found"}
    
    except Exception as e:
        logger.error(f"Error in manual exit: {e}")
        return {"success": False, "error": str(e)}


@app.get("/api/open-positions")
async def get_open_positions_api():
    """Get all open evaluation positions"""
    try:
        if not EVALUATION_EXECUTOR_AVAILABLE:
            return {"success": False, "error": "Evaluation executor not available", "positions": []}
        
        executor = get_equity_evaluation_executor()
        positions = executor.get_open_positions()
        summary = executor.get_position_summary()
        
        return {
            "success": True,
            "positions": positions,
            "count": len(positions),
            "session_pnl": summary.get('session_pnl', 0),
            "current_capital": summary.get('current_capital', 0),
            "timestamp": datetime.now().isoformat()
        }
    
    except Exception as e:
        logger.error(f"Error getting open positions: {e}")
        return {"success": False, "error": str(e), "positions": []}


# ============================================================================
# EVALUATION ENDPOINTS - Paper Trading Evaluation Infrastructure
# ============================================================================

@app.post("/evaluation/enable")
async def enable_evaluation_mode():
    """Enable evaluation mode - track all signals and simulated trades"""
    try:
        if not EVALUATION_EXECUTOR_AVAILABLE:
            return JSONResponse(
                status_code=503,
                content={"success": False, "error": "Evaluation executor not available"}
            )
        
        executor = get_equity_evaluation_executor()
        result = executor.enable_evaluation()
        
        return {
            "success": True,
            "message": "Evaluation mode enabled - tracking all signals and simulated trades",
            "mode": "evaluation",
            "database": "database/evaluation_data.db",
            "endpoints": {
                "status": "/evaluation/status",
                "trades": "/evaluation/trades",
                "performance": "/evaluation/performance",
                "signals": "/evaluation/signals",
                "export": "/evaluation/export",
                "disable": "/evaluation/disable"
            },
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Failed to enable evaluation mode: {e}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )


@app.post("/evaluation/disable")
async def disable_evaluation_mode():
    """Disable evaluation mode - return to paper trading"""
    try:
        if not EVALUATION_EXECUTOR_AVAILABLE:
            return JSONResponse(
                status_code=503,
                content={"success": False, "error": "Evaluation executor not available"}
            )
        
        executor = get_equity_evaluation_executor()
        result = executor.disable_evaluation("paper")
        
        return {
            "success": True,
            "message": "Evaluation mode disabled - returned to paper trading",
            "mode": "paper",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Failed to disable evaluation mode: {e}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )


@app.get("/evaluation/status")
async def get_evaluation_status():
    """Get current evaluation status and summary"""
    try:
        if not EVALUATION_EXECUTOR_AVAILABLE:
            return {
                "evaluation_available": False,
                "mode": "paper",
                "message": "Evaluation executor not available",
                "timestamp": datetime.now().isoformat()
            }
        
        executor = get_equity_evaluation_executor()
        summary = executor.get_evaluation_summary()
        
        return {
            "mode": summary.get('mode', 'paper'),
            "is_evaluation_mode": summary.get('mode') == 'evaluation',
            "evaluation_available": True,
            "service_running": service_state["is_running"],
            "session_id": summary.get('session_id'),
            "session_trades": summary.get('session_trades', 0),
            "session_pnl": summary.get('session_pnl', 0),
            "open_positions": summary.get('open_positions', 0),
            "overall_stats": summary.get('overall', {}),
            "today_stats": summary.get('today', {}),
            "database_path": "database/evaluation_data.db",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Failed to get evaluation status: {e}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )


@app.get("/evaluation/trades")
async def get_evaluation_trades(limit: int = 100, symbol: Optional[str] = None):
    """Get evaluation trades history"""
    try:
        if not EVALUATION_EXECUTOR_AVAILABLE:
            return JSONResponse(
                status_code=503,
                content={"success": False, "error": "Evaluation executor not available"}
            )
        
        executor = get_equity_evaluation_executor()
        if symbol:
            trades = executor._db.get_trades_by_symbol(symbol, limit)
        else:
            trades = executor._db.get_recent_trades(limit)
        
        return {
            "success": True,
            "trades": trades,
            "count": len(trades),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Failed to get evaluation trades: {e}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )


@app.get("/evaluation/performance")
async def get_evaluation_performance():
    """Get detailed evaluation performance metrics"""
    try:
        if not EVALUATION_EXECUTOR_AVAILABLE:
            return JSONResponse(
                status_code=503,
                content={"success": False, "error": "Evaluation executor not available"}
            )
        
        executor = get_equity_evaluation_executor()
        performance = executor._db.get_performance_metrics()
        
        return {
            "success": True,
            "performance": performance,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Failed to get evaluation performance: {e}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )


@app.get("/evaluation/signals")
async def get_evaluation_signals(limit: int = 100):
    """Get tracked signals for evaluation"""
    try:
        if not EVALUATION_EXECUTOR_AVAILABLE:
            return JSONResponse(
                status_code=503,
                content={"success": False, "error": "Evaluation executor not available"}
            )
        
        executor = get_equity_evaluation_executor()
        signals = executor._db.get_signal_decisions(limit)
        
        return {
            "success": True,
            "signals": signals,
            "count": len(signals),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Failed to get evaluation signals: {e}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )


@app.get("/evaluation/export")
async def export_evaluation_data():
    """Export all evaluation data for analysis"""
    try:
        if not EVALUATION_EXECUTOR_AVAILABLE:
            return JSONResponse(
                status_code=503,
                content={"success": False, "error": "Evaluation executor not available"}
            )
        
        executor = get_equity_evaluation_executor()
        # Get all data for export
        export_data = {
            "summary": executor.get_evaluation_summary(),
            "trades": executor._db.get_recent_trades(limit=1000),
            "signals": executor._db.get_signal_decisions(limit=1000),
            "performance": executor._db.get_performance_metrics(),
            "daily_summary": executor._db.get_daily_summary()
        }
        
        return {
            "success": True,
            "export": export_data,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Failed to export evaluation data: {e}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )


@app.post("/evaluation/clear")
async def clear_evaluation_data():
    """Clear all evaluation data - use with caution"""
    try:
        if not EVALUATION_EXECUTOR_AVAILABLE:
            return JSONResponse(
                status_code=503,
                content={"success": False, "error": "Evaluation executor not available"}
            )
        
        executor = get_equity_evaluation_executor()
        executor._db.clear_all_data()
        
        return {
            "success": True,
            "message": "Evaluation data cleared",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Failed to clear evaluation data: {e}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )


# ============================================================================
# ERROR HANDLERS
# ============================================================================

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "detail": str(exc)}
    )


# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    uvicorn.run(
        "equity_hv_service:app",
        host="0.0.0.0",
        port=SERVICE_CONFIG["port"],
        reload=True,
        log_level="info"
    )
