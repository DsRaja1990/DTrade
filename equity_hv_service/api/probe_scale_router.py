"""
╔══════════════════════════════════════════════════════════════════════════════════════╗
║            PROBE-SCALE API ROUTER v1.0                                               ║
║    REST Endpoints for Probe-Scale Trading System                                     ║
╠══════════════════════════════════════════════════════════════════════════════════════╣
║                                                                                      ║
║  Endpoints:                                                                          ║
║    POST /api/probe/enter         - Enter probe position (10% capital)               ║
║    POST /api/probe/scale         - Scale up position (add 90%)                      ║
║    POST /api/probe/exit          - Exit position                                    ║
║    GET  /api/probe/positions     - Get all active positions                         ║
║    GET  /api/probe/position/{id} - Get specific position                            ║
║    GET  /api/probe/history       - Get trade history                                ║
║    GET  /api/probe/status        - Get service status                               ║
║    POST /api/probe/consult-exit  - Consult Gemini for exit                          ║
║                                                                                      ║
╚══════════════════════════════════════════════════════════════════════════════════════╝
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
import asyncio
import logging
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/probe", tags=["Probe-Scale Trading"])


# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================

class ProbeEntryRequest(BaseModel):
    """Request to enter a probe position"""
    symbol: str = Field(..., description="Stock symbol")
    option_type: str = Field(..., description="CE or PE")
    strike: float = Field(..., description="Strike price")
    expiry: str = Field(..., description="Expiry date")
    entry_price: float = Field(..., description="Entry price")
    lot_size: int = Field(default=50, description="Lot size")
    capital_allocation: float = Field(default=50000.0, description="Capital for this trade")
    reason: str = Field(default="Manual Entry", description="Entry reason")
    
    class Config:
        json_schema_extra = {
            "example": {
                "symbol": "NIFTY",
                "option_type": "CE",
                "strike": 25000,
                "expiry": "2025-01-30",
                "entry_price": 150.0,
                "lot_size": 50,
                "capital_allocation": 50000.0,
                "reason": "Strong momentum breakout"
            }
        }


class ScaleRequest(BaseModel):
    """Request to scale up a position"""
    trade_id: str = Field(..., description="Trade ID to scale")
    scale_percent: float = Field(default=90.0, description="Percentage of remaining capital to deploy")
    bypass_gemini: bool = Field(default=False, description="Skip Gemini confirmation")


class ExitRequest(BaseModel):
    """Request to exit a position"""
    trade_id: str = Field(..., description="Trade ID to exit")
    exit_percent: float = Field(default=100.0, description="Percentage to exit")
    reason: str = Field(default="Manual Exit", description="Exit reason")


class ConsultExitRequest(BaseModel):
    """Request Gemini consultation for exit"""
    trade_id: str = Field(..., description="Trade ID")
    current_price: float = Field(..., description="Current market price")


class ProbePositionResponse(BaseModel):
    """Probe position response"""
    trade_id: str
    symbol: str
    option_type: str
    strike: float
    phase: str
    probe_entry_price: float
    current_price: float
    pnl_percent: float
    probe_quantity: int
    scale_quantity: Optional[int] = 0
    scaled: bool
    trailing_activated: bool
    trailing_stop: float
    stoploss: float
    gemini_checks: int
    momentum_status: str
    last_gemini_decision: str


class ServiceStatusResponse(BaseModel):
    """Service status response"""
    running: bool
    total_capital: float
    available_capital: float
    deployed_capital: float
    daily_pnl: float
    active_trades: int
    paper_trading: bool
    uptime_seconds: float


# ============================================================================
# GLOBAL SERVICE INSTANCE
# ============================================================================

# Will be initialized by the main service
_probe_scale_executor = None
_service_start_time = datetime.now()


def set_executor(executor):
    """Set the global executor instance"""
    global _probe_scale_executor
    _probe_scale_executor = executor
    logger.info("ProbeScaleExecutor registered with API router")


def get_executor():
    """Get the executor instance"""
    if _probe_scale_executor is None:
        raise HTTPException(status_code=503, detail="Probe-Scale executor not initialized")
    return _probe_scale_executor


# ============================================================================
# ENDPOINTS
# ============================================================================

@router.post("/enter", response_model=Dict[str, Any])
async def enter_probe_position(request: ProbeEntryRequest, background_tasks: BackgroundTasks):
    """
    Enter a probe position with 10% of allocated capital
    
    - Uses 50% wide stoploss for high-confidence entries
    - Monitors for scale-up confirmation
    - Returns trade ID for tracking
    """
    executor = get_executor()
    
    try:
        opportunity = {
            'symbol': request.symbol,
            'option_type': request.option_type,
            'strike': request.strike,
            'expiry': request.expiry,
            'entry_price': request.entry_price,
            'lot_size': request.lot_size,
            'reason': request.reason
        }
        
        # Create the probe entry
        result = await executor.enter_probe_position(
            opportunity=opportunity,
            allocated_capital=request.capital_allocation
        )
        
        if result:
            # Start monitoring in background
            background_tasks.add_task(_monitor_position, result['trade_id'])
            
            return {
                'success': True,
                'trade_id': result['trade_id'],
                'message': f"Probe entered: {request.symbol} {request.option_type} @ ₹{request.entry_price:.2f}",
                'probe_details': {
                    'quantity': result.get('quantity', 0),
                    'capital_deployed': result.get('capital_deployed', 0),
                    'stoploss': result.get('stoploss', 0)
                }
            }
        else:
            raise HTTPException(status_code=400, detail="Failed to enter probe position")
            
    except Exception as e:
        logger.error(f"Probe entry error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/scale", response_model=Dict[str, Any])
async def scale_position(request: ScaleRequest):
    """
    Scale up a position after Gemini confirmation
    
    - Adds remaining 90% capital
    - Tightens stoploss to 30%
    - Activates trailing stop
    """
    executor = get_executor()
    
    try:
        position = executor.get_position(request.trade_id)
        if not position:
            raise HTTPException(status_code=404, detail=f"Position {request.trade_id} not found")
        
        if position.get('scaled'):
            raise HTTPException(status_code=400, detail="Position already scaled")
        
        result = await executor.scale_position(
            trade_id=request.trade_id,
            scale_percent=request.scale_percent,
            bypass_confirmation=request.bypass_gemini
        )
        
        return {
            'success': result.get('success', False),
            'trade_id': request.trade_id,
            'message': result.get('message', 'Scale operation complete'),
            'scale_details': result.get('details', {})
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Scale error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/exit", response_model=Dict[str, Any])
async def exit_position(request: ExitRequest):
    """
    Exit a position (full or partial)
    
    - Full exit (100%) closes the entire position
    - Partial exit reduces position size
    """
    executor = get_executor()
    
    try:
        position = executor.get_position(request.trade_id)
        if not position:
            raise HTTPException(status_code=404, detail=f"Position {request.trade_id} not found")
        
        result = await executor.exit_position(
            trade_id=request.trade_id,
            exit_percent=request.exit_percent,
            reason=request.reason
        )
        
        return {
            'success': result.get('success', False),
            'trade_id': request.trade_id,
            'exit_percent': request.exit_percent,
            'realized_pnl': result.get('pnl', 0),
            'exit_price': result.get('exit_price', 0),
            'message': f"Position {request.trade_id} exited: {request.reason}"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Exit error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/positions", response_model=List[Dict[str, Any]])
async def get_active_positions():
    """
    Get all active probe-scale positions
    """
    executor = get_executor()
    
    try:
        positions = executor.get_all_positions()
        return [
            {
                'trade_id': p.get('trade_id'),
                'symbol': p.get('symbol'),
                'option_type': p.get('option_type'),
                'strike': p.get('strike'),
                'phase': p.get('phase'),
                'entry_price': p.get('probe_entry_price'),
                'current_price': p.get('current_price'),
                'pnl_percent': p.get('pnl_percent'),
                'probe_quantity': p.get('probe_quantity'),
                'scale_quantity': p.get('scale_quantity', 0),
                'scaled': p.get('scaled', False),
                'trailing_activated': p.get('trailing_activated', False),
                'trailing_stop': p.get('trailing_stop', 0),
                'stoploss': p.get('scale_stoploss') if p.get('scaled') else p.get('probe_stoploss'),
                'gemini_checks': p.get('gemini_checks', 0),
                'momentum_status': p.get('momentum_status', 'UNKNOWN'),
                'last_gemini_decision': p.get('last_gemini_decision', '')
            }
            for p in positions
        ]
        
    except Exception as e:
        logger.error(f"Get positions error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/position/{trade_id}", response_model=Dict[str, Any])
async def get_position(trade_id: str):
    """
    Get a specific position by trade ID
    """
    executor = get_executor()
    
    try:
        position = executor.get_position(trade_id)
        if not position:
            raise HTTPException(status_code=404, detail=f"Position {trade_id} not found")
        
        return position
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get position error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history", response_model=List[Dict[str, Any]])
async def get_trade_history(limit: int = 50):
    """
    Get trade history (closed positions)
    """
    executor = get_executor()
    
    try:
        history = executor.get_history(limit=limit)
        return history
        
    except Exception as e:
        logger.error(f"Get history error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status", response_model=Dict[str, Any])
async def get_service_status():
    """
    Get probe-scale service status
    """
    executor = get_executor()
    
    try:
        status = executor.get_status()
        uptime = (datetime.now() - _service_start_time).total_seconds()
        
        return {
            **status,
            'uptime_seconds': uptime,
            'uptime_formatted': _format_uptime(uptime)
        }
        
    except Exception as e:
        logger.error(f"Get status error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/consult-exit", response_model=Dict[str, Any])
async def consult_gemini_exit(request: ConsultExitRequest):
    """
    Consult Gemini 3 Pro for exit decision
    
    Returns:
    - decision: HOLD, PARTIAL_EXIT, FULL_EXIT
    - confidence: 0-100
    - momentum_status: STRONG, MODERATE, WEAK, EXHAUSTED, REVERSING
    - reasoning: AI explanation
    """
    executor = get_executor()
    
    try:
        position = executor.get_position(request.trade_id)
        if not position:
            raise HTTPException(status_code=404, detail=f"Position {request.trade_id} not found")
        
        # Update current price
        position['current_price'] = request.current_price
        
        result = await executor.consult_gemini_exit(position)
        
        return {
            'trade_id': request.trade_id,
            'decision': result.get('decision', 'HOLD'),
            'confidence': result.get('confidence', 50),
            'momentum_status': result.get('momentum_status', 'MODERATE'),
            'reasoning': result.get('reasoning', ''),
            'recommended_action': result.get('recommended_action', 'Monitor'),
            'suggested_exit_percent': result.get('exit_percent', 0)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Gemini consultation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/validate-probe", response_model=Dict[str, Any])
async def validate_probe_entry(request: ProbeEntryRequest):
    """
    Validate a potential probe entry with Gemini
    
    Returns whether entry is recommended without actually entering
    """
    executor = get_executor()
    
    try:
        opportunity = {
            'symbol': request.symbol,
            'option_type': request.option_type,
            'strike': request.strike,
            'entry_price': request.entry_price,
            'reason': request.reason
        }
        
        result = await executor.validate_probe_entry(opportunity)
        
        return {
            'symbol': request.symbol,
            'valid': result.get('valid', False),
            'confidence': result.get('confidence', 0),
            'recommendation': result.get('recommendation', 'SKIP'),
            'reasoning': result.get('reasoning', ''),
            'adjusted_stoploss': result.get('suggested_stoploss'),
            'market_conditions': result.get('market_conditions', {})
        }
        
    except Exception as e:
        logger.error(f"Probe validation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/capital-summary", response_model=Dict[str, Any])
async def get_capital_summary():
    """
    Get detailed capital allocation summary
    """
    executor = get_executor()
    
    try:
        status = executor.get_status()
        positions = executor.get_all_positions()
        
        # Calculate breakdowns
        probe_capital = sum(p.get('probe_capital', 0) for p in positions)
        scale_capital = sum(p.get('scale_quantity', 0) * p.get('scale_entry_price', 0) * p.get('lot_size', 50) 
                          for p in positions if p.get('scaled'))
        
        return {
            'total_capital': status.get('total_capital', 0),
            'available_capital': status.get('available_capital', 0),
            'deployed_capital': status.get('deployed_capital', 0),
            'breakdown': {
                'probe_positions': probe_capital,
                'scaled_positions': scale_capital,
                'reserved': status.get('total_capital', 0) * 0.1  # 10% reserve
            },
            'utilization_percent': (status.get('deployed_capital', 0) / status.get('total_capital', 1)) * 100,
            'daily_pnl': status.get('daily_pnl', 0),
            'positions_count': {
                'probe': len([p for p in positions if not p.get('scaled')]),
                'scaled': len([p for p in positions if p.get('scaled')])
            }
        }
        
    except Exception as e:
        logger.error(f"Capital summary error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# BACKGROUND TASKS
# ============================================================================

async def _monitor_position(trade_id: str):
    """Background task to monitor a position"""
    try:
        executor = get_executor()
        
        while True:
            position = executor.get_position(trade_id)
            if not position or position.get('phase') in ['EXITED', 'ABORTED']:
                break
            
            # Executor handles monitoring
            await executor.monitor_position(trade_id)
            await asyncio.sleep(30)  # Check every 30 seconds
            
    except asyncio.CancelledError:
        pass
    except Exception as e:
        logger.error(f"Position monitoring error: {e}")


# ============================================================================
# HELPERS
# ============================================================================

def _format_uptime(seconds: float) -> str:
    """Format uptime in human-readable format"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    return f"{hours}h {minutes}m {secs}s"


# ============================================================================
# ROUTER INITIALIZATION
# ============================================================================

def initialize_router(app):
    """Initialize the router with the FastAPI app"""
    app.include_router(router)
    logger.info("Probe-Scale router initialized")
    logger.info("Endpoints available at /api/probe/*")
