#!/usr/bin/env python3
"""
Auto-Trader API Router
======================

FastAPI router for controlling the production auto-trading system.
Provides endpoints for:
- Starting/stopping the auto-trader
- Monitoring status and positions
- Viewing screened stocks
- Manual trade execution
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field

# Import auto-trader
from .production_auto_trader import (
    ProductionAutoTrader,
    AutoTraderConfig,
    TradingMode,
    SignalQuality
)

# Configure logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(tags=["auto-trader"])

# Global auto-trader instance
_auto_trader: Optional[ProductionAutoTrader] = None
_is_initialized = False


# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================

class StartAutoTraderRequest(BaseModel):
    """Request to start auto-trader"""
    mode: str = Field(default="paper", description="Trading mode: 'paper' or 'live'")
    capital: float = Field(default=500000.0, description="Trading capital in INR")
    max_positions: int = Field(default=5, description="Maximum concurrent positions")
    max_daily_trades: int = Field(default=20, description="Maximum trades per day")
    min_combined_score: float = Field(default=75.0, description="Minimum score to trade (0-100)")
    min_ai_confidence: float = Field(default=7.5, description="Minimum AI confidence (0-10)")
    screening_interval_seconds: int = Field(default=300, description="Screening interval in seconds")


class ManualTradeRequest(BaseModel):
    """Request for manual trade execution"""
    symbol: str = Field(..., description="Stock symbol (e.g., RELIANCE.NS)")
    direction: str = Field(..., description="CALL or PUT")
    lots: int = Field(default=1, description="Number of lots")


class StatusResponse(BaseModel):
    """Auto-trader status response"""
    is_running: bool
    mode: str
    is_market_hours: bool
    can_take_new_trades: bool
    active_positions: int
    daily_pnl: float
    daily_trades: int
    statistics: Dict
    positions: List[Dict]
    error_counts: Dict
    last_errors: List[Dict]


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_auto_trader() -> ProductionAutoTrader:
    """Get the auto-trader instance"""
    global _auto_trader
    if _auto_trader is None:
        raise HTTPException(
            status_code=503,
            detail="Auto-trader not initialized. Call /api/auto-trader/start first."
        )
    return _auto_trader


# ============================================================================
# ENDPOINTS
# ============================================================================

@router.post("/start")
async def start_auto_trader(request: StartAutoTraderRequest, background_tasks: BackgroundTasks):
    """
    Start the production auto-trading system
    
    The auto-trader will:
    1. Run continuously during market hours (9:15 AM - 3:30 PM IST)
    2. Screen F&O stocks every 5 minutes (configurable)
    3. Use multi-factor scoring (AI + Technical + Market Structure)
    4. Auto-execute trades meeting quality thresholds
    5. Manage positions with stop-loss and trailing stops
    """
    global _auto_trader, _is_initialized
    
    if _auto_trader is not None and _auto_trader.is_running:
        raise HTTPException(
            status_code=400,
            detail="Auto-trader is already running"
        )
    
    try:
        # Create configuration
        config = AutoTraderConfig(
            mode=TradingMode.LIVE if request.mode.lower() == "live" else TradingMode.PAPER,
            capital=request.capital,
            max_positions=request.max_positions,
            max_daily_trades=request.max_daily_trades,
            min_combined_score=request.min_combined_score,
            min_ai_confidence=request.min_ai_confidence,
            screening_interval_seconds=request.screening_interval_seconds
        )
        
        # Create auto-trader
        _auto_trader = ProductionAutoTrader(config)
        _is_initialized = True
        
        # Start in background
        background_tasks.add_task(_auto_trader.start)
        
        logger.info(f"Auto-trader starting in {request.mode} mode with ₹{request.capital:,.2f} capital")
        
        return {
            "status": "success",
            "message": f"Auto-trader starting in {request.mode} mode",
            "config": {
                "mode": request.mode,
                "capital": request.capital,
                "max_positions": request.max_positions,
                "screening_interval_seconds": request.screening_interval_seconds,
                "min_combined_score": request.min_combined_score,
                "min_ai_confidence": request.min_ai_confidence
            },
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to start auto-trader: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/stop")
async def stop_auto_trader():
    """
    Stop the auto-trading system gracefully
    
    This will:
    1. Stop screening for new opportunities
    2. Close all open positions (in paper mode)
    3. Log final trading statistics
    """
    global _auto_trader
    
    auto_trader = get_auto_trader()
    
    if not auto_trader.is_running:
        return {
            "status": "success",
            "message": "Auto-trader was not running",
            "timestamp": datetime.now().isoformat()
        }
    
    try:
        await auto_trader.stop()
        
        return {
            "status": "success",
            "message": "Auto-trader stopped successfully",
            "final_statistics": auto_trader.get_status()["statistics"],
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error stopping auto-trader: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status", response_model=StatusResponse)
async def get_auto_trader_status():
    """
    Get current status of the auto-trading system
    
    Returns:
    - Running state and mode
    - Market hours status
    - Active positions with P&L
    - Daily trading statistics
    - Recent errors
    """
    auto_trader = get_auto_trader()
    return auto_trader.get_status()


@router.get("/positions")
async def get_active_positions():
    """
    Get all active positions with real-time P&L
    
    Returns detailed information for each position including:
    - Entry and current price
    - Stop loss and target levels
    - Unrealized P&L
    """
    auto_trader = get_auto_trader()
    
    status = auto_trader.get_status()
    
    return {
        "status": "success",
        "count": len(status["positions"]),
        "total_pnl": sum(p["pnl"] for p in status["positions"]),
        "positions": status["positions"],
        "timestamp": datetime.now().isoformat()
    }


@router.get("/screened-stocks")
async def get_screened_stocks():
    """
    Get recently screened stocks with multi-factor scores
    
    Shows the last screening results including:
    - Combined score (0-100)
    - Signal quality rating
    - AI confidence
    - Trade setup (entry, stop loss, target)
    """
    auto_trader = get_auto_trader()
    
    stocks = auto_trader.get_screened_stocks()
    
    return {
        "status": "success",
        "count": len(stocks),
        "stocks": stocks,
        "timestamp": datetime.now().isoformat()
    }


@router.get("/statistics")
async def get_trading_statistics():
    """
    Get detailed trading statistics
    
    Returns comprehensive performance metrics including:
    - Win rate and profit factor
    - Total profit and loss
    - Trade count and success rate
    """
    auto_trader = get_auto_trader()
    
    status = auto_trader.get_status()
    stats = status["statistics"]
    
    profit_factor = (stats["total_profit"] / stats["total_loss"]) if stats["total_loss"] > 0 else float('inf')
    
    return {
        "status": "success",
        "statistics": {
            **stats,
            "profit_factor": profit_factor,
            "average_win": stats["total_profit"] / stats["wins"] if stats["wins"] > 0 else 0,
            "average_loss": stats["total_loss"] / stats["losses"] if stats["losses"] > 0 else 0
        },
        "daily": {
            "pnl": status["daily_pnl"],
            "trades": status["daily_trades"]
        },
        "timestamp": datetime.now().isoformat()
    }


@router.post("/manual-trade")
async def execute_manual_trade(request: ManualTradeRequest):
    """
    Execute a manual trade bypassing the screening criteria
    
    Use this for:
    - Testing specific stocks
    - Taking trades based on external analysis
    - Emergency position adjustments
    """
    auto_trader = get_auto_trader()
    
    if not auto_trader.is_running:
        raise HTTPException(
            status_code=400,
            detail="Auto-trader must be running to execute trades"
        )
    
    if request.direction.upper() not in ["CALL", "PUT"]:
        raise HTTPException(
            status_code=400,
            detail="Direction must be 'CALL' or 'PUT'"
        )
    
    # This would need additional implementation for manual trade execution
    # For now, return a placeholder response
    return {
        "status": "pending",
        "message": "Manual trade feature coming soon",
        "request": {
            "symbol": request.symbol,
            "direction": request.direction,
            "lots": request.lots
        },
        "timestamp": datetime.now().isoformat()
    }


@router.post("/close-position/{symbol}")
async def close_position(symbol: str, reason: str = "Manual close"):
    """
    Manually close a specific position
    
    Args:
        symbol: Stock symbol to close (e.g., RELIANCE.NS)
        reason: Reason for closing the position
    """
    auto_trader = get_auto_trader()
    
    if symbol not in auto_trader.active_positions:
        raise HTTPException(
            status_code=404,
            detail=f"No active position found for {symbol}"
        )
    
    try:
        await auto_trader._close_position(symbol, reason)
        
        return {
            "status": "success",
            "message": f"Position {symbol} closed: {reason}",
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error closing position {symbol}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/close-all")
async def close_all_positions(reason: str = "Manual close all"):
    """
    Close all active positions
    
    Use with caution - this will immediately close all positions
    """
    auto_trader = get_auto_trader()
    
    if not auto_trader.active_positions:
        return {
            "status": "success",
            "message": "No active positions to close",
            "timestamp": datetime.now().isoformat()
        }
    
    try:
        position_count = len(auto_trader.active_positions)
        await auto_trader._close_all_positions(reason)
        
        return {
            "status": "success",
            "message": f"Closed {position_count} positions",
            "reason": reason,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error closing all positions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def health_check():
    """
    Health check endpoint for the auto-trader
    
    Returns service health status and key metrics
    """
    global _auto_trader, _is_initialized
    
    if not _is_initialized or _auto_trader is None:
        return {
            "status": "not_initialized",
            "message": "Auto-trader not started",
            "timestamp": datetime.now().isoformat()
        }
    
    try:
        status = _auto_trader.get_status()
        
        return {
            "status": "healthy" if _auto_trader.is_running else "stopped",
            "is_running": _auto_trader.is_running,
            "mode": status["mode"],
            "is_market_hours": status["is_market_hours"],
            "active_positions": status["active_positions"],
            "daily_pnl": status["daily_pnl"],
            "error_count": sum(status["error_counts"].values()),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }


@router.get("/config")
async def get_current_config():
    """
    Get current auto-trader configuration
    """
    auto_trader = get_auto_trader()
    
    config = auto_trader.config
    
    return {
        "status": "success",
        "config": {
            "mode": config.mode.value,
            "capital": config.capital,
            "max_positions": config.max_positions,
            "max_daily_trades": config.max_daily_trades,
            "screening_interval_seconds": config.screening_interval_seconds,
            "min_combined_score": config.min_combined_score,
            "min_ai_confidence": config.min_ai_confidence,
            "min_technical_confluences": config.min_technical_confluences,
            "position_stop_loss_pct": config.position_stop_loss_pct,
            "position_target_pct": config.position_target_pct,
            "trailing_stop_pct": config.trailing_stop_pct,
            "max_daily_loss_pct": config.max_daily_loss_pct,
            "market_hours": {
                "open": config.market_open.isoformat(),
                "close": config.market_close.isoformat(),
                "no_new_trades_after": config.no_new_trades_after.isoformat()
            }
        },
        "timestamp": datetime.now().isoformat()
    }
