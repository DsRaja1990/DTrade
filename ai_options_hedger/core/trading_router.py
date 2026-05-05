"""
╔══════════════════════════════════════════════════════════════════════════════════════╗
║        AI OPTIONS HEDGER - TRADING ENGINE API ROUTER                                 ║
║                FastAPI Router for Production Trading Engine                          ║
╠══════════════════════════════════════════════════════════════════════════════════════╣
║                                                                                      ║
║  ENDPOINTS:                                                                          ║
║  ═══════════════════════════════════════════════════════════════════════════════    ║
║                                                                                      ║
║  GET  /trading/status          - Get engine status and positions                    ║
║  POST /trading/mode            - Switch between PAPER and LIVE modes                ║
║  POST /trading/probe           - Enter probe position                               ║
║  POST /trading/exit/{id}       - Exit specific position                            ║
║  GET  /trading/positions       - List all active positions                          ║
║  GET  /trading/stats           - Get trading statistics                             ║
║  POST /trading/update-price    - Update option price                                ║
║                                                                                      ║
╚══════════════════════════════════════════════════════════════════════════════════════╝
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from fastapi import APIRouter, HTTPException, Body
from pydantic import BaseModel, Field

from .production_trading_engine import (
    ProductionTradingEngine,
    HedgerEngineConfig,
    TradingMode,
    TradeDirection,
    create_hedger_engine
)

logger = logging.getLogger(__name__ + '.trading_router')

router = APIRouter(prefix="/trading", tags=["Trading Engine"])

# Global engine instance (initialized in lifespan)
_engine: Optional[ProductionTradingEngine] = None


# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================

class SwitchModeRequest(BaseModel):
    """Request to switch trading mode"""
    mode: str = Field(..., description="PAPER or LIVE")


class ProbeEntryRequest(BaseModel):
    """Request to enter probe position"""
    instrument: str = Field(..., description="NIFTY or BANKNIFTY")
    direction: str = Field(..., description="BULLISH or BEARISH")
    strike: float = Field(..., description="Strike price")
    option_type: str = Field(..., description="CE or PE")
    expiry: str = Field(..., description="Expiry date (e.g., 2024-01-25)")
    current_price: float = Field(..., description="Current option price")
    signal_strength: float = Field(0.8, description="Signal strength 0-1")


class UpdatePriceRequest(BaseModel):
    """Request to update option price"""
    instrument: str = Field(..., description="NIFTY or BANKNIFTY")
    option_type: str = Field(..., description="CE or PE")
    strike: float = Field(..., description="Strike price")
    price: float = Field(..., description="Current price")


class ExitPositionRequest(BaseModel):
    """Request to manually exit position"""
    reason: str = Field("USER_MANUAL", description="Exit reason")


class APIResponse(BaseModel):
    """Standard API response"""
    success: bool
    message: str
    data: Optional[Dict] = None
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_engine() -> ProductionTradingEngine:
    """Get the trading engine instance"""
    global _engine
    if _engine is None:
        raise HTTPException(status_code=503, detail="Trading engine not initialized")
    return _engine


def init_engine(config: Optional[HedgerEngineConfig] = None) -> ProductionTradingEngine:
    """Initialize the trading engine"""
    global _engine
    _engine = create_hedger_engine(config)
    return _engine


async def start_engine():
    """Start the trading engine"""
    engine = get_engine()
    await engine.start()


async def stop_engine():
    """Stop the trading engine"""
    global _engine
    if _engine:
        await _engine.stop()


# ============================================================================
# ENDPOINTS
# ============================================================================

@router.get("/status")
async def get_status() -> APIResponse:
    """Get trading engine status"""
    try:
        engine = get_engine()
        status = engine.get_status()
        return APIResponse(
            success=True,
            message="Engine status retrieved",
            data=status
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/mode")
async def switch_mode(request: SwitchModeRequest) -> APIResponse:
    """Switch trading mode between PAPER and LIVE"""
    try:
        engine = get_engine()
        
        if request.mode.upper() not in ["PAPER", "LIVE"]:
            raise HTTPException(status_code=400, detail="Mode must be PAPER or LIVE")
        
        mode = TradingMode.PAPER if request.mode.upper() == "PAPER" else TradingMode.LIVE
        result = engine.switch_mode(mode)
        
        if not result['success']:
            raise HTTPException(status_code=400, detail=result.get('error', 'Mode switch failed'))
        
        return APIResponse(
            success=True,
            message=f"Trading mode switched to {mode.value}",
            data=result
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error switching mode: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/probe")
async def enter_probe(request: ProbeEntryRequest) -> APIResponse:
    """Enter a probe position"""
    try:
        engine = get_engine()
        
        # Validate direction
        if request.direction.upper() not in ["BULLISH", "BEARISH"]:
            raise HTTPException(status_code=400, detail="Direction must be BULLISH or BEARISH")
        
        direction = TradeDirection.BULLISH if request.direction.upper() == "BULLISH" else TradeDirection.BEARISH
        
        # Validate instrument
        if request.instrument.upper() not in ["NIFTY", "BANKNIFTY"]:
            raise HTTPException(status_code=400, detail="Instrument must be NIFTY or BANKNIFTY")
        
        position = await engine.enter_probe(
            instrument=request.instrument.upper(),
            direction=direction,
            strike=request.strike,
            option_type=request.option_type.upper(),
            expiry=request.expiry,
            current_price=request.current_price,
            signal_strength=request.signal_strength
        )
        
        if position is None:
            return APIResponse(
                success=False,
                message="Probe entry rejected (check logs for reason)",
                data=None
            )
        
        return APIResponse(
            success=True,
            message=f"Probe entered: {request.instrument} {request.strike}{request.option_type}",
            data=position.to_dict()
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error entering probe: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/exit/{position_id}")
async def exit_position(position_id: str, request: ExitPositionRequest = Body(default=None)) -> APIResponse:
    """Exit a specific position"""
    try:
        engine = get_engine()
        
        if position_id not in engine.active_positions:
            raise HTTPException(status_code=404, detail=f"Position not found: {position_id}")
        
        position = engine.active_positions[position_id]
        
        from .production_trading_engine import ExitReason
        
        reason = ExitReason.USER_MANUAL
        if request and request.reason:
            try:
                reason = ExitReason(request.reason)
            except ValueError:
                reason = ExitReason.USER_MANUAL
        
        await engine._exit_position(position, reason)
        
        return APIResponse(
            success=True,
            message=f"Position exited: {position_id}",
            data=position.to_dict()
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error exiting position: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/positions")
async def get_positions() -> APIResponse:
    """Get all active positions"""
    try:
        engine = get_engine()
        positions = [p.to_dict() for p in engine.active_positions.values()]
        
        return APIResponse(
            success=True,
            message=f"Found {len(positions)} active positions",
            data={'positions': positions}
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting positions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
async def get_stats() -> APIResponse:
    """Get trading statistics"""
    try:
        engine = get_engine()
        
        stats = {
            'today': engine.database.get_today_stats(),
            'session': {
                'total_trades': engine.stats.total_trades,
                'winning_trades': engine.stats.winning_trades,
                'losing_trades': engine.stats.losing_trades,
                'win_rate': round(engine.stats.win_rate, 2),
                'total_pnl': round(engine.stats.total_pnl, 2),
                'probes_taken': engine.stats.probes_taken,
                'probes_scaled': engine.stats.probes_scaled,
                'scale_rate': round(engine.stats.scale_rate, 2),
                'largest_win': round(engine.stats.largest_win, 2),
                'largest_loss': round(engine.stats.largest_loss, 2)
            }
        }
        
        return APIResponse(
            success=True,
            message="Statistics retrieved",
            data=stats
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/update-price")
async def update_price(request: UpdatePriceRequest) -> APIResponse:
    """Update option price for position tracking"""
    try:
        engine = get_engine()
        
        engine.update_price(
            instrument=request.instrument.upper(),
            option_type=request.option_type.upper(),
            strike=request.strike,
            price=request.price
        )
        
        return APIResponse(
            success=True,
            message=f"Price updated: {request.instrument} {request.strike}{request.option_type} = ₹{request.price}",
            data=None
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating price: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/closed")
async def get_closed_positions() -> APIResponse:
    """Get closed positions from current session"""
    try:
        engine = get_engine()
        closed = [p.to_dict() for p in engine.closed_positions[-20:]]  # Last 20
        
        return APIResponse(
            success=True,
            message=f"Found {len(engine.closed_positions)} closed positions",
            data={'positions': closed}
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting closed positions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/config")
async def get_config() -> APIResponse:
    """Get engine configuration"""
    try:
        engine = get_engine()
        
        config = {
            'service_name': engine.config.service_name,
            'service_port': engine.config.service_port,
            'trading_mode': engine.trading_mode.value,
            'total_capital': engine.config.total_capital,
            'probe_capital_pct': engine.config.probe_capital_pct,
            'scale_capital_pct': engine.config.scale_capital_pct,
            'probe_stoploss_pct': engine.config.probe_stoploss_pct,
            'scaled_stoploss_pct': engine.config.scaled_stoploss_pct,
            'trailing_activation_points': engine.config.trailing_activation_points,
            'trailing_distance_points': engine.config.trailing_distance_points,
            'min_gemini_confidence': engine.config.min_gemini_confidence,
            'instruments': engine.config.instruments,
            'lot_sizes': engine.config.lot_sizes
        }
        
        return APIResponse(
            success=True,
            message="Configuration retrieved",
            data=config
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting config: {e}")
        raise HTTPException(status_code=500, detail=str(e))
