"""
Gemini AI Trading Engine API Router
====================================

FastAPI endpoints for the Gemini AI-Enhanced Trading Engine
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any
from datetime import datetime
import logging

try:
    from equity_hv_service.strategy.gemini_ai_trading_engine import (
        GeminiAITradingEngine,
        create_gemini_trading_engine,
        get_or_create_engine,
        EnhancedTradeSetup,
        TradeExecution
    )
except ImportError:
    # Fallback for local imports
    from strategy.gemini_ai_trading_engine import (
        GeminiAITradingEngine,
        create_gemini_trading_engine,
        get_or_create_engine,
        EnhancedTradeSetup,
        TradeExecution
    )

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Gemini AI Engine"])

# Module-level engine instance
_engine: Optional[GeminiAITradingEngine] = None


# Request/Response Models
class EngineInitRequest(BaseModel):
    gemini_url: str = Field(default="http://localhost:4080", description="Gemini Trade Service URL")
    capital: float = Field(default=500000, description="Allocated capital in INR")
    min_ai_confidence: float = Field(default=7.5, ge=0, le=10, description="Minimum AI confidence (0-10)")
    min_tier3_forecast: float = Field(default=75, ge=0, le=100, description="Minimum Tier3 forecast %")
    min_confluences: int = Field(default=4, ge=0, le=8, description="Minimum technical confluences (0-8)")
    risk_per_trade_pct: float = Field(default=0.02, ge=0.01, le=0.10, description="Risk per trade %")


class TradeSetupResponse(BaseModel):
    symbol: str
    direction: str
    option_type: str
    strike: float
    expiry: str
    entry_premium: float
    stop_loss_premium: float
    target_1_premium: float
    target_2_premium: float
    lot_size: int
    num_lots: int
    margin_required: float
    risk_amount: float
    ai_confidence: float
    tier3_forecast: float
    signal_strength: str
    confluence_count: int
    combined_score: float
    is_valid: bool


class ExecuteTradeRequest(BaseModel):
    symbol: str = Field(..., description="Stock symbol to trade")


class CloseTradeRequest(BaseModel):
    symbol: str = Field(..., description="Symbol to close")
    exit_price: float = Field(..., description="Exit price")
    exit_reason: str = Field(default="MANUAL", description="Exit reason")


class PerformanceResponse(BaseModel):
    capital: Dict[str, float]
    trades: Dict[str, Any]
    pnl: Dict[str, float]
    filters: Dict[str, int]
    win_rate: float
    profit_factor: float


@router.post("/initialize", summary="Initialize Gemini AI Trading Engine")
async def initialize_engine(request: EngineInitRequest):
    """
    Initialize the Gemini AI Trading Engine with specified parameters
    """
    global _engine
    
    try:
        _engine = create_gemini_trading_engine(
            gemini_url=request.gemini_url,
            capital=request.capital,
            min_confidence=request.min_ai_confidence,
            min_confluences=request.min_confluences
        )
        _engine.min_tier3_forecast = request.min_tier3_forecast
        _engine.risk_per_trade_pct = request.risk_per_trade_pct
        
        await _engine.initialize()
        
        logger.info(f"🤖 Gemini AI Engine initialized with capital ₹{request.capital:,.2f}")
        
        return {
            "status": "initialized",
            "config": {
                "gemini_url": request.gemini_url,
                "capital": request.capital,
                "min_ai_confidence": request.min_ai_confidence,
                "min_tier3_forecast": request.min_tier3_forecast,
                "min_confluences": request.min_confluences,
                "risk_per_trade_pct": request.risk_per_trade_pct
            },
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Failed to initialize engine: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status", summary="Get engine status")
async def get_engine_status():
    """Get current status of the trading engine"""
    global _engine
    
    if _engine is None:
        return {
            "status": "not_initialized",
            "message": "Engine not initialized. Call POST /api/gemini-engine/initialize first."
        }
    
    return {
        "status": "running",
        "capital": _engine.capital,
        "allocated_capital": _engine.allocated_capital,
        "daily_pnl": _engine.daily_pnl,
        "daily_loss_limit_hit": _engine.daily_loss_limit_hit,
        "open_positions": len(_engine.open_positions),
        "total_trades": _engine.total_trades,
        "win_rate": (_engine.winning_trades / _engine.total_trades * 100) if _engine.total_trades > 0 else 0,
        "filters": {
            "ai_filtered": _engine.ai_filtered_count,
            "tech_filtered": _engine.tech_filtered_count,
            "executed": _engine.executed_count
        },
        "timestamp": datetime.now().isoformat()
    }


@router.get("/scan", summary="Scan F&O universe for trade setups")
async def scan_fo_universe():
    """
    Scan the F&O stock universe for valid trade setups
    
    Returns setups that pass both AI and Technical filters, sorted by combined score
    """
    global _engine
    
    if _engine is None:
        raise HTTPException(status_code=400, detail="Engine not initialized")
    
    try:
        setups = await _engine.scan_fo_universe()
        
        return {
            "count": len(setups),
            "setups": [s.to_dict() for s in setups],
            "filters": {
                "ai_filtered": _engine.ai_filtered_count,
                "tech_filtered": _engine.tech_filtered_count,
                "passed": len(setups)
            },
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Scan failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/analyze/{symbol}", summary="Analyze a specific symbol")
async def analyze_symbol(symbol: str):
    """
    Analyze a specific symbol for trading opportunity
    
    Returns the trade setup if it passes filters, otherwise explains why it was rejected
    """
    global _engine
    
    if _engine is None:
        raise HTTPException(status_code=400, detail="Engine not initialized")
    
    try:
        # Reset counters for clean tracking
        ai_before = _engine.ai_filtered_count
        tech_before = _engine.tech_filtered_count
        
        setup = await _engine.create_trade_setup(symbol)
        
        if setup:
            return {
                "status": "valid_setup",
                "setup": setup.to_dict(),
                "recommendation": "TRADE",
                "timestamp": datetime.now().isoformat()
            }
        else:
            # Determine rejection reason
            ai_filtered = _engine.ai_filtered_count > ai_before
            tech_filtered = _engine.tech_filtered_count > tech_before
            
            reason = "Unknown"
            if ai_filtered:
                reason = "AI confidence or forecast below threshold"
            elif tech_filtered:
                reason = "Technical confluences below threshold"
            
            return {
                "status": "rejected",
                "symbol": symbol,
                "reason": reason,
                "recommendation": "NO_TRADE",
                "timestamp": datetime.now().isoformat()
            }
    except Exception as e:
        logger.error(f"Analysis failed for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/execute", summary="Execute a trade")
async def execute_trade(request: ExecuteTradeRequest):
    """
    Execute a trade for the specified symbol
    
    Creates setup, validates it, and executes if valid
    """
    global _engine
    
    if _engine is None:
        raise HTTPException(status_code=400, detail="Engine not initialized")
    
    try:
        # Create and validate setup
        setup = await _engine.create_trade_setup(request.symbol)
        
        if not setup:
            return {
                "status": "rejected",
                "symbol": request.symbol,
                "message": "Setup did not pass AI+Technical filters",
                "timestamp": datetime.now().isoformat()
            }
        
        # Execute
        execution = await _engine.execute_trade(setup)
        
        if execution:
            return {
                "status": "executed",
                "trade_id": execution.trade_id,
                "symbol": setup.symbol,
                "direction": setup.direction.value,
                "entry_price": execution.entry_price,
                "quantity": execution.quantity,
                "stop_loss": setup.stop_loss_premium,
                "target_1": setup.target_1_premium,
                "target_2": setup.target_2_premium,
                "ai_confidence": setup.ai_signal.confidence_score,
                "confluences": setup.confluences.count,
                "combined_score": setup.combined_score,
                "timestamp": datetime.now().isoformat()
            }
        else:
            return {
                "status": "failed",
                "message": "Execution failed",
                "timestamp": datetime.now().isoformat()
            }
    except Exception as e:
        logger.error(f"Execution failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/close", summary="Close a trade")
async def close_trade(request: CloseTradeRequest):
    """Close an open trade"""
    global _engine
    
    if _engine is None:
        raise HTTPException(status_code=400, detail="Engine not initialized")
    
    try:
        execution = await _engine.close_trade(
            request.symbol,
            request.exit_price,
            request.exit_reason
        )
        
        if execution:
            return {
                "status": "closed",
                "trade_id": execution.trade_id,
                "symbol": request.symbol,
                "exit_price": execution.exit_price,
                "exit_reason": execution.exit_reason,
                "gross_pnl": execution.gross_pnl,
                "net_pnl": execution.net_pnl,
                "pnl_pct": execution.pnl_pct,
                "is_winner": execution.is_winner,
                "timestamp": datetime.now().isoformat()
            }
        else:
            raise HTTPException(status_code=404, detail=f"No open position for {request.symbol}")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Close failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/positions", summary="Get open positions")
async def get_open_positions():
    """Get all open positions"""
    global _engine
    
    if _engine is None:
        raise HTTPException(status_code=400, detail="Engine not initialized")
    
    positions = []
    for symbol, execution in _engine.open_positions.items():
        positions.append({
            "trade_id": execution.trade_id,
            "symbol": symbol,
            "direction": execution.setup.direction.value,
            "entry_time": execution.entry_time.isoformat(),
            "entry_price": execution.entry_price,
            "quantity": execution.quantity,
            "stop_loss": execution.setup.stop_loss_premium,
            "target_1": execution.setup.target_1_premium,
            "ai_confidence": execution.setup.ai_signal.confidence_score,
            "confluences": execution.setup.confluences.count
        })
    
    return {
        "count": len(positions),
        "positions": positions,
        "timestamp": datetime.now().isoformat()
    }


@router.get("/trades", summary="Get closed trades history")
async def get_trade_history(limit: int = 50):
    """Get closed trades history"""
    global _engine
    
    if _engine is None:
        raise HTTPException(status_code=400, detail="Engine not initialized")
    
    trades = []
    for execution in _engine.closed_trades[-limit:]:
        trades.append({
            "trade_id": execution.trade_id,
            "symbol": execution.setup.symbol,
            "direction": execution.setup.direction.value,
            "entry_time": execution.entry_time.isoformat(),
            "exit_time": execution.exit_time.isoformat() if execution.exit_time else None,
            "entry_price": execution.entry_price,
            "exit_price": execution.exit_price,
            "net_pnl": execution.net_pnl,
            "pnl_pct": execution.pnl_pct,
            "is_winner": execution.is_winner,
            "exit_reason": execution.exit_reason,
            "ai_confidence": execution.setup.ai_signal.confidence_score,
            "confluences": execution.setup.confluences.count,
            "combined_score": execution.setup.combined_score
        })
    
    return {
        "count": len(trades),
        "trades": trades,
        "timestamp": datetime.now().isoformat()
    }


@router.get("/performance", summary="Get performance metrics")
async def get_performance():
    """Get comprehensive performance metrics"""
    global _engine
    
    if _engine is None:
        raise HTTPException(status_code=400, detail="Engine not initialized")
    
    metrics = _engine.get_performance_metrics()
    
    # Add additional computed metrics
    metrics["win_rate"] = metrics["trades"]["win_rate"]
    metrics["profit_factor"] = metrics["pnl"]["profit_factor"]
    metrics["timestamp"] = datetime.now().isoformat()
    
    return metrics


@router.post("/reset-daily", summary="Reset daily counters")
async def reset_daily():
    """Reset daily tracking counters (call at start of each trading day)"""
    global _engine
    
    if _engine is None:
        raise HTTPException(status_code=400, detail="Engine not initialized")
    
    _engine.reset_daily_counters()
    
    return {
        "status": "reset",
        "daily_pnl": _engine.daily_pnl,
        "daily_loss_limit_hit": _engine.daily_loss_limit_hit,
        "timestamp": datetime.now().isoformat()
    }


@router.get("/config", summary="Get engine configuration")
async def get_config():
    """Get current engine configuration"""
    global _engine
    
    if _engine is None:
        return {
            "status": "not_initialized",
            "message": "Engine not initialized"
        }
    
    return {
        "gemini_url": _engine.gemini_url,
        "allocated_capital": _engine.allocated_capital,
        "min_ai_confidence": _engine.min_ai_confidence,
        "min_tier3_forecast": _engine.min_tier3_forecast,
        "min_confluences": _engine.min_confluences,
        "risk_per_trade_pct": _engine.risk_per_trade_pct,
        "max_daily_loss_pct": _engine.max_daily_loss_pct,
        "strong_sectors": _engine.strong_sectors,
        "timestamp": datetime.now().isoformat()
    }
