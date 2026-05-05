"""
╔══════════════════════════════════════════════════════════════════════════════════════╗
║        AI SCALPING SERVICE - TRADING ENGINE API ROUTER                               ║
║                FastAPI Router for Production Scalping Engine                         ║
╠══════════════════════════════════════════════════════════════════════════════════════╣
║                                                                                      ║
║  ENDPOINTS:                                                                          ║
║  ═══════════════════════════════════════════════════════════════════════════════    ║
║                                                                                      ║
║  GET  /scalping/status         - Get engine status and active position              ║
║  POST /scalping/mode           - Switch between PAPER and LIVE modes                ║
║  POST /scalping/entry          - Enter scalp position                               ║
║  POST /scalping/exit           - Exit active position                               ║
║  GET  /scalping/momentum       - Get momentum data for all instruments              ║
║  GET  /scalping/stats          - Get scalping statistics                            ║
║  POST /scalping/update-price   - Update instrument price                            ║
║                                                                                      ║
╚══════════════════════════════════════════════════════════════════════════════════════╝
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from fastapi import APIRouter, HTTPException, Body
from pydantic import BaseModel, Field

from .production_trading_engine import (
    ProductionScalpingEngine,
    ScalpingEngineConfig,
    TradingMode,
    TradeDirection,
    create_scalping_engine
)

logger = logging.getLogger(__name__ + '.scalping_router')

router = APIRouter(prefix="/scalping", tags=["Scalping Engine"])

# Global engine instance
_engine: Optional[ProductionScalpingEngine] = None


# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================

class SwitchModeRequest(BaseModel):
    mode: str = Field(..., description="PAPER or LIVE")


class ScalpEntryRequest(BaseModel):
    instrument: str = Field(..., description="NIFTY, BANKNIFTY, SENSEX, or BANKEX")
    direction: str = Field(..., description="BULLISH or BEARISH")
    strike: float = Field(..., description="Strike price")
    option_type: str = Field(..., description="CE or PE")
    expiry: str = Field(..., description="Expiry date")
    current_price: float = Field(..., description="Current option price")


class UpdatePriceRequest(BaseModel):
    instrument: str = Field(..., description="Instrument name")
    price: float = Field(..., description="Current price")
    volume: int = Field(0, description="Current volume")


class ExitRequest(BaseModel):
    reason: str = Field("USER_MANUAL", description="Exit reason")


class APIResponse(BaseModel):
    success: bool
    message: str
    data: Optional[Dict] = None
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_engine() -> ProductionScalpingEngine:
    global _engine
    if _engine is None:
        raise HTTPException(status_code=503, detail="Scalping engine not initialized")
    return _engine


def init_engine(config: Optional[ScalpingEngineConfig] = None) -> ProductionScalpingEngine:
    global _engine
    _engine = create_scalping_engine(config)
    return _engine


async def start_engine():
    engine = get_engine()
    await engine.start()


async def stop_engine():
    global _engine
    if _engine:
        await _engine.stop()


# ============================================================================
# ENDPOINTS
# ============================================================================

@router.get("/status")
async def get_status() -> APIResponse:
    """Get scalping engine status"""
    try:
        engine = get_engine()
        status = engine.get_status()
        return APIResponse(
            success=True,
            message="Scalping engine status retrieved",
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


@router.post("/entry")
async def enter_scalp(request: ScalpEntryRequest) -> APIResponse:
    """Enter a scalp position"""
    try:
        engine = get_engine()
        
        if request.direction.upper() not in ["BULLISH", "BEARISH"]:
            raise HTTPException(status_code=400, detail="Direction must be BULLISH or BEARISH")
        
        direction = TradeDirection.BULLISH if request.direction.upper() == "BULLISH" else TradeDirection.BEARISH
        
        valid_instruments = ["NIFTY", "BANKNIFTY", "SENSEX", "BANKEX"]
        if request.instrument.upper() not in valid_instruments:
            raise HTTPException(status_code=400, detail=f"Instrument must be one of: {valid_instruments}")
        
        position = await engine.enter_scalp(
            instrument=request.instrument.upper(),
            direction=direction,
            strike=request.strike,
            option_type=request.option_type.upper(),
            expiry=request.expiry,
            current_price=request.current_price
        )
        
        if position is None:
            return APIResponse(
                success=False,
                message="Scalp entry rejected (check logs for reason)",
                data=None
            )
        
        return APIResponse(
            success=True,
            message=f"Scalp entered: {request.instrument} {request.strike}{request.option_type}",
            data=position.to_dict()
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error entering scalp: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/exit")
async def exit_position(request: ExitRequest = Body(default=None)) -> APIResponse:
    """Exit active scalp position"""
    try:
        engine = get_engine()
        
        if engine.active_position is None:
            raise HTTPException(status_code=404, detail="No active position to exit")
        
        position = engine.active_position
        
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
            message=f"Position exited: {position.position_id}",
            data=position.to_dict()
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error exiting position: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/momentum")
async def get_momentum() -> APIResponse:
    """Get momentum data for all instruments"""
    try:
        engine = get_engine()
        
        momentum_data = {}
        for instrument, data in engine.momentum_data.items():
            momentum_data[instrument] = data.to_dict()
        
        return APIResponse(
            success=True,
            message="Momentum data retrieved",
            data=momentum_data
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting momentum: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
async def get_stats() -> APIResponse:
    """Get scalping statistics"""
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
                'quick_exits': engine.stats.quick_exits,
                'momentum_exits': engine.stats.momentum_exits
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
    """Update instrument price (recalculates momentum)"""
    try:
        engine = get_engine()
        
        engine.update_price(
            instrument=request.instrument.upper(),
            price=request.price,
            volume=request.volume
        )
        
        momentum = engine.momentum_data.get(request.instrument.upper())
        momentum_score = momentum.momentum_score if momentum else 0
        
        return APIResponse(
            success=True,
            message=f"Price updated: {request.instrument} = ₹{request.price} | Momentum: {momentum_score:.1f}",
            data={'momentum_score': momentum_score}
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating price: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/position")
async def get_active_position() -> APIResponse:
    """Get active position details"""
    try:
        engine = get_engine()
        
        if engine.active_position is None:
            return APIResponse(
                success=True,
                message="No active position",
                data={'position': None}
            )
        
        return APIResponse(
            success=True,
            message="Active position retrieved",
            data={'position': engine.active_position.to_dict()}
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting position: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/closed")
async def get_closed_positions() -> APIResponse:
    """Get closed positions from current session"""
    try:
        engine = get_engine()
        closed = [p.to_dict() for p in engine.closed_positions[-20:]]
        
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
            'quick_profit_pct': engine.config.quick_profit_pct,
            'trailing_activation_points': engine.config.trailing_activation_points,
            'trailing_distance_points': engine.config.trailing_distance_points,
            'min_momentum_for_entry': engine.config.min_momentum_for_entry,
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
