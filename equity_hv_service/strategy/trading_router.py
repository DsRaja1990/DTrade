"""
╔══════════════════════════════════════════════════════════════════════════════════════╗
║        EQUITY HV SERVICE - TRADING ENGINE API ROUTER                                 ║
║                FastAPI Router for Production Equity Engine                           ║
╠══════════════════════════════════════════════════════════════════════════════════════╣
║                                                                                      ║
║  ENDPOINTS:                                                                          ║
║  ═══════════════════════════════════════════════════════════════════════════════    ║
║                                                                                      ║
║  GET  /equity/status           - Get engine status and positions                    ║
║  POST /equity/mode             - Switch between PAPER and LIVE modes                ║
║  POST /equity/probe            - Enter equity probe position                        ║
║  POST /equity/exit/{id}        - Exit specific position                            ║
║  GET  /equity/positions        - List all active positions                          ║
║  GET  /equity/stocks           - Get elite stocks with HV data                      ║
║  GET  /equity/stats            - Get trading statistics                             ║
║  POST /equity/update-stock     - Update stock price                                 ║
║  POST /equity/update-option    - Update option price                                ║
║                                                                                      ║
╚══════════════════════════════════════════════════════════════════════════════════════╝
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from fastapi import APIRouter, HTTPException, Body
from pydantic import BaseModel, Field

from .production_trading_engine import (
    ProductionEquityEngine,
    EquityEngineConfig,
    TradingMode,
    TradeDirection,
    ELITE_STOCKS,
    create_equity_engine
)

logger = logging.getLogger(__name__ + '.equity_router')

router = APIRouter(prefix="/equity", tags=["Equity Engine"])

# Global engine instance
_engine: Optional[ProductionEquityEngine] = None


# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================

class SwitchModeRequest(BaseModel):
    mode: str = Field(..., description="PAPER or LIVE")


class EquityProbeRequest(BaseModel):
    symbol: str = Field(..., description="Stock symbol (e.g., RELIANCE, TCS)")
    direction: str = Field(..., description="BULLISH or BEARISH")
    strike: float = Field(..., description="Strike price")
    option_type: str = Field(..., description="CE or PE")
    expiry: str = Field(..., description="Expiry date")
    option_price: float = Field(..., description="Current option price")
    underlying_price: float = Field(..., description="Current stock price")


class UpdateStockPriceRequest(BaseModel):
    symbol: str = Field(..., description="Stock symbol")
    price: float = Field(..., description="Current price")
    volume: int = Field(0, description="Current volume")


class UpdateOptionPriceRequest(BaseModel):
    symbol: str = Field(..., description="Stock symbol")
    option_type: str = Field(..., description="CE or PE")
    strike: float = Field(..., description="Strike price")
    price: float = Field(..., description="Current option price")


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

def get_engine() -> ProductionEquityEngine:
    global _engine
    if _engine is None:
        raise HTTPException(status_code=503, detail="Equity engine not initialized")
    return _engine


def init_engine(config: Optional[EquityEngineConfig] = None) -> ProductionEquityEngine:
    global _engine
    _engine = create_equity_engine(config)
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
    """Get equity engine status"""
    try:
        engine = get_engine()
        status = engine.get_status()
        return APIResponse(
            success=True,
            message="Equity engine status retrieved",
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
async def enter_equity_probe(request: EquityProbeRequest) -> APIResponse:
    """Enter an equity probe position"""
    try:
        engine = get_engine()
        
        if request.direction.upper() not in ["BULLISH", "BEARISH"]:
            raise HTTPException(status_code=400, detail="Direction must be BULLISH or BEARISH")
        
        direction = TradeDirection.BULLISH if request.direction.upper() == "BULLISH" else TradeDirection.BEARISH
        
        if request.symbol.upper() not in ELITE_STOCKS:
            raise HTTPException(
                status_code=400, 
                detail=f"Symbol must be one of: {list(ELITE_STOCKS.keys())}"
            )
        
        position = await engine.enter_equity_probe(
            symbol=request.symbol.upper(),
            direction=direction,
            strike=request.strike,
            option_type=request.option_type.upper(),
            expiry=request.expiry,
            option_price=request.option_price,
            underlying_price=request.underlying_price
        )
        
        if position is None:
            return APIResponse(
                success=False,
                message="Equity probe entry rejected (check logs for reason)",
                data=None
            )
        
        return APIResponse(
            success=True,
            message=f"Equity probe entered: {request.symbol} {request.strike}{request.option_type}",
            data=position.to_dict()
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error entering equity probe: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/exit/{position_id}")
async def exit_position(position_id: str, request: ExitRequest = Body(default=None)) -> APIResponse:
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


@router.get("/stocks")
async def get_elite_stocks() -> APIResponse:
    """Get elite stocks with current HV data"""
    try:
        engine = get_engine()
        stocks = engine.get_elite_stocks()
        
        return APIResponse(
            success=True,
            message=f"Retrieved {len(stocks)} elite stocks",
            data={'stocks': stocks}
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting stocks: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/hv")
async def get_hv_data() -> APIResponse:
    """Get Historical Volatility data for all stocks"""
    try:
        engine = get_engine()
        
        hv_data = {}
        for symbol, data in engine.hv_data.items():
            hv_data[symbol] = data.to_dict()
        
        return APIResponse(
            success=True,
            message="HV data retrieved",
            data=hv_data
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting HV data: {e}")
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
                'banking_trades': engine.stats.banking_trades,
                'it_trades': engine.stats.it_trades,
                'other_trades': engine.stats.other_trades
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


@router.post("/update-stock")
async def update_stock_price(request: UpdateStockPriceRequest) -> APIResponse:
    """Update stock price (recalculates HV)"""
    try:
        engine = get_engine()
        
        engine.update_stock_price(
            symbol=request.symbol.upper(),
            price=request.price,
            volume=request.volume
        )
        
        hv_data = engine.hv_data.get(request.symbol.upper())
        current_hv = hv_data.hv_current if hv_data else 0
        
        return APIResponse(
            success=True,
            message=f"Stock price updated: {request.symbol} = ₹{request.price} | HV: {current_hv:.2f}%",
            data={'current_hv': current_hv}
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating stock price: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/update-option")
async def update_option_price(request: UpdateOptionPriceRequest) -> APIResponse:
    """Update option price for position tracking"""
    try:
        engine = get_engine()
        
        engine.update_option_price(
            symbol=request.symbol.upper(),
            option_type=request.option_type.upper(),
            strike=request.strike,
            price=request.price
        )
        
        return APIResponse(
            success=True,
            message=f"Option price updated: {request.symbol} {request.strike}{request.option_type} = ₹{request.price}",
            data=None
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating option price: {e}")
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
            'max_concurrent_positions': engine.config.max_concurrent_positions,
            'probe_capital_pct': engine.config.probe_capital_pct,
            'scale_capital_pct': engine.config.scale_capital_pct,
            'trailing_activation_points': engine.config.trailing_activation_points,
            'trailing_distance_points': engine.config.trailing_distance_points,
            'min_hv_for_entry': engine.config.min_hv_for_entry,
            'max_hv_for_entry': engine.config.max_hv_for_entry,
            'elite_stocks': list(ELITE_STOCKS.keys())
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


@router.get("/sectors")
async def get_sectors() -> APIResponse:
    """Get sector breakdown of elite stocks"""
    try:
        sectors = {}
        for symbol, stock in ELITE_STOCKS.items():
            sector = stock.sector.value
            if sector not in sectors:
                sectors[sector] = []
            sectors[sector].append({
                'symbol': symbol,
                'lot_size': stock.lot_size,
                'beta': stock.beta
            })
        
        return APIResponse(
            success=True,
            message="Sector breakdown retrieved",
            data={'sectors': sectors}
        )
    except Exception as e:
        logger.error(f"Error getting sectors: {e}")
        raise HTTPException(status_code=500, detail=str(e))
