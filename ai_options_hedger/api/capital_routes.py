"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                    CAPITAL MANAGEMENT API ENDPOINTS v2.0                     ║
║              Dynamic Fund Management REST API for Trading                    ║
╚══════════════════════════════════════════════════════════════════════════════╝

FastAPI Endpoints for Capital Management:
- POST /capital/update - Update allocated capital
- GET /capital/status - Get current capital status
- POST /capital/calculate-quantity - Calculate optimal quantity for trade
- POST /capital/sync-funds - Sync with Dhan account
- POST /capital/validate-trade - Validate trade before execution
"""

import logging
import sys
import os
from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field

from fastapi import APIRouter, HTTPException

# Add parent directory to path for imports
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

logger = logging.getLogger(__name__)

# Create FastAPI Router
router = APIRouter(prefix="/api", tags=["Capital Management"])

# Global capital manager instance
_capital_manager = None


# ==================== Request/Response Models ====================

class CapitalUpdateRequest(BaseModel):
    """Request model for updating capital"""
    allocated_capital: float = Field(..., gt=0, description="Amount to allocate for trading")
    max_single_trade_pct: Optional[float] = Field(None, ge=1, le=100, description="Max % per single trade (1-100)")
    max_daily_loss_pct: Optional[float] = Field(None, ge=1, le=50, description="Max daily loss (%) (1-50)")
    risk_level: Optional[str] = Field(None, description="Risk level: CONSERVATIVE, MODERATE, AGGRESSIVE, ULTRA")


class CapitalStatusResponse(BaseModel):
    """Response model for capital status"""
    total_capital: float
    current_exposure: float
    available_for_trading: float
    max_trade_amount: float
    daily_pnl: float
    open_positions: int
    max_positions: int
    can_trade: bool
    risk_level: str
    # Instrument configuration
    enabled_instruments: List[str]
    all_instruments: List[str]
    instrument_count: int
    capital_per_instrument: float
    # Fund status
    fund_status: Optional[Dict[str, Any]] = None
    last_updated: str


class QuantityCalculationRequest(BaseModel):
    """Request model for quantity calculation"""
    underlying: str = Field(..., description="Underlying instrument (NIFTY, BANKNIFTY, etc.)")
    premium: float = Field(..., gt=0, description="Option premium per share")
    confidence: float = Field(..., ge=0, le=100, description="Signal confidence (0-100)")
    option_type: str = Field("CE", description="Option type (CE or PE)")


class QuantityCalculationResponse(BaseModel):
    """Response model for quantity calculation"""
    quantity: int
    total_lots: int
    lot_size: int
    total_qty: int
    premium_per_lot: float
    total_investment: float
    max_loss: float
    position_size_pct: float
    can_afford: bool
    reason: str
    # Order slicing info (for large orders)
    need_slicing: bool = False
    max_lots_per_order: int = 0
    num_orders: int = 1
    freeze_quantity: int = 0


class TradeValidationRequest(BaseModel):
    """Request model for trade validation"""
    underlying: str
    option_type: str
    quantity: int
    premium: float
    stop_loss: float
    target: float


class TradeValidationResponse(BaseModel):
    """Response model for trade validation"""
    is_valid: bool
    reason: str
    position_value: float
    risk_amount: float
    risk_reward_ratio: float
    funds_available: bool


# ==================== Helper Functions ====================

def get_manager():
    """Get capital manager instance, create if not exists"""
    global _capital_manager
    
    if _capital_manager is None:
        try:
            from capital_manager import CapitalManager
            
            # Try to initialize with Dhan connector for real-time fund data
            try:
                from dhan_connector import DhanConnector
                dhan_connector = DhanConnector()
                _capital_manager = CapitalManager(dhan_connector=dhan_connector)
                logger.info("✓ Capital manager initialized with Dhan connector")
            except Exception as conn_err:
                logger.warning(f"Dhan connector not available, using standalone mode: {conn_err}")
                _capital_manager = CapitalManager()
                logger.info("✓ Capital manager initialized (standalone mode)")
                
        except ImportError as e:
            logger.error(f"Capital manager import error: {e}")
            raise HTTPException(
                status_code=503,
                detail=f"Capital manager not available: {str(e)}"
            )
        except Exception as e:
            logger.error(f"Capital manager initialization error: {e}")
            raise HTTPException(
                status_code=503,
                detail=f"Capital manager initialization failed: {str(e)}"
            )
    
    return _capital_manager


# ==================== Endpoints ====================

@router.post("/capital/update")
async def update_capital(request: CapitalUpdateRequest):
    """
    Update allocated trading capital.
    
    This endpoint allows dynamic capital allocation for trading.
    The allocated capital is used to calculate position sizes and risk limits.
    """
    try:
        manager = get_manager()
        
        # Store old capital for response
        old_capital = manager.allocation.total_capital
        
        # Use the update_capital method from CapitalManager
        result = manager.update_capital(request.allocated_capital)
        
        # Update additional settings if provided
        if request.max_single_trade_pct is not None:
            manager.allocation.max_single_trade_pct = request.max_single_trade_pct / 100
        
        if request.max_daily_loss_pct is not None:
            manager.allocation.max_daily_loss_pct = request.max_daily_loss_pct / 100
        
        if request.risk_level is not None:
            from capital_manager import RiskLevel
            try:
                manager.allocation.risk_level = RiskLevel[request.risk_level.upper()]
            except KeyError:
                pass  # Ignore invalid risk levels
        
        # Save updated config
        manager.save_config()
        
        # Return updated values
        return {
            "success": True,
            "old_capital": old_capital,
            "new_capital": manager.allocation.total_capital,
            "available_for_trading": manager.allocation.available_for_trading,
            "max_trade_amount": manager.allocation.max_trade_amount,
            "max_single_trade_pct": manager.allocation.max_single_trade_pct * 100,
            "message": "Capital updated successfully",
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating capital: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/capital/status")
async def get_capital_status():
    """
    Get current capital status and trading limits.
    
    Returns comprehensive information about:
    - Available capital
    - Position limits
    - Daily P&L
    - Fund status from Dhan
    """
    try:
        manager = get_manager()
        status = manager.get_status()
        
        from capital_manager import ALL_INDEX_INSTRUMENTS
        
        return CapitalStatusResponse(
            total_capital=status.get("total_capital", 0),
            current_exposure=status.get("current_exposure", 0),
            available_for_trading=status.get("available_for_trading", 0),
            max_trade_amount=status.get("max_trade_amount", 0),
            daily_pnl=status.get("daily_pnl", 0),
            open_positions=status.get("open_positions", 0),
            max_positions=status.get("max_positions", 10),
            can_trade=status.get("can_trade", True),
            risk_level=status.get("risk_level", "MODERATE"),
            # Instrument configuration
            enabled_instruments=status.get("enabled_instruments", ["NIFTY", "BANKNIFTY"]),
            all_instruments=ALL_INDEX_INSTRUMENTS,
            instrument_count=status.get("instrument_count", 2),
            capital_per_instrument=status.get("capital_per_instrument", 0),
            # Fund status
            fund_status=status.get("fund_status"),
            last_updated=status.get("last_updated", datetime.now().isoformat())
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting capital status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/capital/calculate-quantity")
async def calculate_quantity(request: QuantityCalculationRequest):
    """
    Calculate optimal quantity for a trade based on signal confidence and capital.
    
    Uses sophisticated position sizing based on:
    - Signal confidence level
    - Available capital
    - Risk per trade limits
    - Lot size requirements
    """
    try:
        manager = get_manager()
        
        # Use the async calculate_quantity method
        result = await manager.calculate_quantity(
            underlying=request.underlying,
            premium=request.premium,
            confidence=request.confidence,
            option_type=request.option_type
        )
        
        return QuantityCalculationResponse(
            quantity=result.quantity,
            total_lots=result.total_lots,
            lot_size=result.lot_size,
            total_qty=result.total_qty,
            premium_per_lot=result.premium_per_lot,
            total_investment=result.total_investment,
            max_loss=result.max_loss,
            position_size_pct=result.position_size_pct,
            can_afford=result.can_afford,
            reason=result.reason,
            # Order slicing info
            need_slicing=result.need_slicing,
            max_lots_per_order=result.max_lots_per_order,
            num_orders=result.num_orders,
            freeze_quantity=result.freeze_quantity
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error calculating quantity: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/capital/sync-funds")
async def sync_funds():
    """
    Sync capital with Dhan account fund limits.
    
    Fetches real-time fund information from Dhan and updates available capital.
    """
    try:
        manager = get_manager()
        
        # Fetch fund status from Dhan (force refresh)
        fund_status = await manager.fetch_fund_status(force=True)
        
        return {
            "success": True,
            "fund_status": {
                "available_balance": fund_status.available_balance if fund_status else 0,
                "utilized_amount": fund_status.utilized_amount if fund_status else 0,
                "total_balance": fund_status.total_balance if fund_status else 0,
                "tradeable_balance": fund_status.tradeable_balance if fund_status else 0,
                "withdrawable_balance": fund_status.withdrawable_balance if fund_status else 0
            },
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error syncing funds: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/capital/validate-trade")
async def validate_trade(request: TradeValidationRequest):
    """
    Validate a trade before execution.
    
    Checks:
    - Sufficient funds available
    - Within risk limits
    - Position size acceptable
    - Risk-reward ratio
    """
    try:
        manager = get_manager()
        status = manager.get_status()
        
        # Get lot size for underlying
        from capital_manager import INDEX_LOT_SIZES
        lot_size = INDEX_LOT_SIZES.get(request.underlying.upper(), 75)
        
        # Calculate position metrics
        position_value = request.quantity * lot_size * request.premium
        risk_amount = request.quantity * lot_size * abs(request.premium - request.stop_loss)
        reward = request.quantity * lot_size * abs(request.target - request.premium)
        risk_reward = reward / risk_amount if risk_amount > 0 else 0
        
        # Check if trade is valid
        available = status.get("available_for_trading", 0)
        max_trade = status.get("max_trade_amount", 0)
        can_trade = status.get("can_trade", False)
        
        is_valid = True
        reasons = []
        
        # Check if trading is allowed
        if not can_trade:
            is_valid = False
            reasons.append("Trading is currently disabled (risk limits reached)")
        
        # Check funds
        if position_value > available:
            is_valid = False
            reasons.append(f"Insufficient funds: need ₹{position_value:,.2f}, have ₹{available:,.2f}")
        
        # Check position size
        if position_value > max_trade:
            is_valid = False
            reasons.append(f"Position too large: max ₹{max_trade:,.2f}")
        
        # Check risk-reward
        if risk_reward < 1.5:
            reasons.append(f"Low risk-reward: {risk_reward:.2f}:1 (recommended 1.5:1+)")
        
        reason = "; ".join(reasons) if reasons else "Trade validated successfully"
        
        return TradeValidationResponse(
            is_valid=is_valid,
            reason=reason,
            position_value=position_value,
            risk_amount=risk_amount,
            risk_reward_ratio=round(risk_reward, 2),
            funds_available=position_value <= available
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error validating trade: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/capital/record-pnl")
async def record_trade_pnl(pnl: float):
    """
    Record a completed trade's P&L.
    
    Updates daily statistics and exposure tracking.
    """
    try:
        manager = get_manager()
        
        # Update P&L
        manager.update_pnl(pnl)
        
        status = manager.get_status()
        
        return {
            "success": True,
            "pnl_recorded": pnl,
            "daily_pnl": status.get("daily_pnl", 0),
            "can_trade": status.get("can_trade", True),
            "available_for_trading": status.get("available_for_trading", 0)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error recording P&L: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/capital/update-exposure")
async def update_exposure(amount: float, is_new_position: bool = True):
    """
    Update current exposure when opening/closing positions.
    
    Args:
        amount: Position value (positive for opening, negative for closing)
        is_new_position: True if opening new position, False if closing
    """
    try:
        manager = get_manager()
        
        # Update exposure
        manager.update_exposure(amount, is_new_position)
        
        status = manager.get_status()
        
        return {
            "success": True,
            "exposure_change": amount,
            "current_exposure": status.get("current_exposure", 0),
            "open_positions": status.get("open_positions", 0),
            "available_for_trading": status.get("available_for_trading", 0)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating exposure: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/capital/reset-daily")
async def reset_daily_stats():
    """
    Reset daily trading statistics.
    
    Called at the start of each trading day to reset:
    - Daily P&L
    - Exposure tracking
    - Position count
    """
    try:
        manager = get_manager()
        manager.reset_daily_stats()
        
        return {
            "success": True,
            "message": "Daily statistics reset",
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error resetting daily stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Instrument Selection Endpoints ====================

class InstrumentSelectionRequest(BaseModel):
    """Request model for instrument selection"""
    instruments: List[str] = Field(
        ..., 
        description="List of instruments to enable for trading",
        example=["NIFTY", "BANKNIFTY"]
    )


class InstrumentStatusResponse(BaseModel):
    """Response model for instrument status"""
    enabled_instruments: List[str]
    all_instruments: List[str]
    instrument_count: int
    capital_per_instrument: float
    total_available: float
    correlations: Optional[Dict[str, float]] = None


@router.get("/instruments/status")
async def get_instrument_status():
    """
    Get current instrument configuration.
    
    Returns which instruments are enabled for trading and capital allocation per instrument.
    """
    try:
        manager = get_manager()
        status = manager.get_status()
        
        from capital_manager import ALL_INDEX_INSTRUMENTS, INSTRUMENT_CORRELATIONS
        
        # Build correlation info for enabled instruments
        enabled = status.get("enabled_instruments", [])
        correlations = {}
        for i, inst1 in enumerate(enabled):
            for inst2 in enabled[i+1:]:
                key = f"{inst1}-{inst2}"
                # Check both orderings in the correlation dict
                corr = INSTRUMENT_CORRELATIONS.get((inst1, inst2)) or INSTRUMENT_CORRELATIONS.get((inst2, inst1))
                if corr:
                    correlations[key] = corr
        
        return {
            "enabled_instruments": enabled,
            "all_instruments": ALL_INDEX_INSTRUMENTS,
            "instrument_count": len(enabled),
            "capital_per_instrument": status.get("capital_per_instrument", 0),
            "total_available": status.get("available_for_trading", 0),
            "correlations": correlations if correlations else None,
            "can_trade": status.get("can_trade", False)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting instrument status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/instruments/set")
async def set_instruments(request: InstrumentSelectionRequest):
    """
    Set which instruments are enabled for trading.
    
    Choose from: NIFTY, BANKNIFTY, FINNIFTY, SENSEX, BANKEX
    
    Examples:
    - Single: ["NIFTY"]
    - Two: ["NIFTY", "BANKNIFTY"]
    - All NSE: ["NIFTY", "BANKNIFTY", "FINNIFTY"]
    - All: ["NIFTY", "BANKNIFTY", "FINNIFTY", "SENSEX", "BANKEX"]
    
    Note: NIFTY and SENSEX are highly correlated (0.95).
          BANKNIFTY and BANKEX are highly correlated (0.92).
    """
    try:
        manager = get_manager()
        result = manager.set_enabled_instruments(request.instruments)
        
        if not result.get("success"):
            raise HTTPException(
                status_code=400,
                detail=result.get("error", "Invalid instruments")
            )
        
        return {
            "success": True,
            "old_instruments": result.get("old_instruments"),
            "new_instruments": result.get("new_instruments"),
            "invalid_instruments": result.get("invalid_instruments"),
            "capital_per_instrument": result.get("capital_per_instrument"),
            "total_available": result.get("total_available"),
            "instrument_count": result.get("instrument_count"),
            "message": f"Now trading: {', '.join(result.get('new_instruments', []))}"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error setting instruments: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/instruments/add")
async def add_instrument(instrument: str):
    """
    Add a single instrument to the trading list.
    """
    try:
        manager = get_manager()
        current = manager.get_enabled_instruments()
        
        instrument = instrument.upper()
        if instrument in current:
            return {
                "success": True,
                "message": f"{instrument} is already enabled",
                "enabled_instruments": current
            }
        
        new_list = current + [instrument]
        result = manager.set_enabled_instruments(new_list)
        
        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error"))
        
        return {
            "success": True,
            "added": instrument,
            "enabled_instruments": result.get("new_instruments"),
            "capital_per_instrument": result.get("capital_per_instrument")
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding instrument: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/instruments/remove")
async def remove_instrument(instrument: str):
    """
    Remove a single instrument from the trading list.
    """
    try:
        manager = get_manager()
        current = manager.get_enabled_instruments()
        
        instrument = instrument.upper()
        if instrument not in current:
            return {
                "success": True,
                "message": f"{instrument} is not in the list",
                "enabled_instruments": current
            }
        
        if len(current) == 1:
            raise HTTPException(
                status_code=400,
                detail="Cannot remove last instrument. At least one must be enabled."
            )
        
        new_list = [i for i in current if i != instrument]
        result = manager.set_enabled_instruments(new_list)
        
        return {
            "success": True,
            "removed": instrument,
            "enabled_instruments": result.get("new_instruments"),
            "capital_per_instrument": result.get("capital_per_instrument")
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error removing instrument: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/instruments/check/{instrument}")
async def check_instrument(instrument: str):
    """
    Check if a specific instrument is enabled and can be traded.
    """
    try:
        manager = get_manager()
        can_trade, reason = manager.is_instrument_tradeable(instrument)
        
        from capital_manager import INDEX_LOT_SIZES, get_instrument_cost_profile
        lot_size = INDEX_LOT_SIZES.get(instrument.upper(), 0)
        
        # Get intelligent allocation for this instrument
        intelligent_alloc = manager.allocation.get_intelligent_allocation()
        inst_alloc = intelligent_alloc.get(instrument.upper(), {})
        
        return {
            "instrument": instrument.upper(),
            "is_enabled": manager.allocation.is_instrument_enabled(instrument),
            "can_trade": can_trade,
            "reason": reason,
            "lot_size": lot_size,
            # Intelligent allocation details
            "intelligent_capital": inst_alloc.get("allocated_capital", 0),
            "allocation_pct": inst_alloc.get("allocation_pct", 0),
            "cost_per_lot": inst_alloc.get("cost_per_lot", 0),
            "lots_affordable": inst_alloc.get("lots_affordable", 0),
            "max_lots_per_order": inst_alloc.get("max_lots_per_order", 0),
            "need_slicing": inst_alloc.get("need_slicing", False),
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error checking instrument: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/instruments/refresh-premiums")
async def refresh_live_premiums():
    """
    Refresh ATM premiums from live options chain.
    
    Call this before trading to get current day's premiums for intelligent
    capital allocation. Fetches ATM option prices from Dhan API.
    
    Returns:
    - Live premiums for each instrument
    - Cache status and timestamp
    """
    try:
        from capital_manager import (
            fetch_live_atm_premiums,
            get_premium_cache_status,
            ALL_INDEX_INSTRUMENTS
        )
        
        manager = get_manager()
        enabled = manager._get_config_value("enabled_instruments") or ALL_INDEX_INSTRUMENTS
        
        # Fetch live premiums
        live_premiums = await fetch_live_atm_premiums(enabled)
        
        # Get updated cache status
        cache_status = get_premium_cache_status()
        
        return {
            "success": True,
            "message": "Live ATM premiums refreshed from options chain",
            "live_premiums": live_premiums,
            "cache_status": cache_status,
            "instruments_refreshed": list(live_premiums.keys()),
        }
        
    except Exception as e:
        logger.error(f"Error refreshing premiums: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/instruments/premium-status")
async def get_premium_status():
    """
    Get current premium cache status.
    
    Shows whether live premiums are being used or default fallback values.
    
    Returns:
    - Live vs default premiums
    - Cache freshness status
    """
    try:
        from capital_manager import get_premium_cache_status
        
        cache_status = get_premium_cache_status()
        
        return {
            "success": True,
            "premium_status": cache_status,
            "using_live_data": cache_status.get("cache_fresh", False),
            "recommendation": "Call /instruments/refresh-premiums before trading to use live premiums" 
                if not cache_status.get("cache_fresh", False) else "Live premiums are active"
        }
        
    except Exception as e:
        logger.error(f"Error getting premium status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/instruments/intelligent-allocation")
async def get_intelligent_allocation(mode: str = "priority"):
    """
    Get intelligent capital allocation for all enabled instruments.
    
    Two allocation modes available:
    
    1. mode="priority" (DEFAULT):
       - Allocates in priority order: NIFTY → SENSEX → FINNIFTY → BANKEX → BANKNIFTY
       - BANKNIFTY gets remaining capital (LAST priority due to high premiums)
       - Equal split among non-BANKNIFTY instruments
    
    2. mode="weighted":
       - Allocates proportionally by premium per share
       - Higher premium instruments get more capital
       - Results in equal SHARES per instrument
    
    Query Params:
    - mode: "priority" (default) or "weighted"
    
    Returns:
    - Per-instrument capital allocation
    - Cost per lot and affordable lots
    - Order slicing requirements (if lots > freeze limit)
    - Premium source (live or default)
    """
    try:
        manager = get_manager()
        status = manager.get_status()
        
        from capital_manager import (
            get_instrument_cost_profile,
            calculate_intelligent_allocation,
            get_premium_cache_status,
            FREEZE_QUANTITIES,
            DEFAULT_ATM_PREMIUM_PER_SHARE,
            INDEX_APPROXIMATE_VALUES,
            INSTRUMENT_ALLOCATION_PRIORITY
        )
        
        enabled_instruments = status.get("enabled_instruments", [])
        available_capital = status.get("available_for_trading", 0)
        
        # Calculate allocation with specified mode
        intelligent_alloc = calculate_intelligent_allocation(
            available_capital,
            enabled_instruments,
            allocation_mode=mode
        )
        
        # Add cost profiles for reference
        cost_profiles = {}
        for inst in enabled_instruments:
            cost_profiles[inst] = get_instrument_cost_profile(inst)
        
        # Get premium status
        premium_status = get_premium_cache_status()
        
        return {
            "total_available": available_capital,
            "enabled_instruments": enabled_instruments,
            "allocation_mode": mode,
            "allocation_description": (
                "Priority-based: NIFTY→SENSEX→FINNIFTY→BANKEX→BANKNIFTY (last)"
                if mode == "priority"
                else "Weighted by premium per share (higher premium = more capital)"
            ),
            "using_live_premiums": premium_status.get("cache_fresh", False),
            # Per-instrument intelligent allocation
            "allocations": intelligent_alloc,
            # Cost reference data
            "cost_profiles": cost_profiles,
            # Priority reference
            "allocation_priorities": INSTRUMENT_ALLOCATION_PRIORITY,
            # Market data reference
            "reference_data": {
                "freeze_quantities": FREEZE_QUANTITIES,
                "default_premiums": DEFAULT_ATM_PREMIUM_PER_SHARE,
                "live_premiums": premium_status.get("live_premiums", {}),
                "index_values": INDEX_APPROXIMATE_VALUES,
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting intelligent allocation: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Export router
__all__ = ["router"]
