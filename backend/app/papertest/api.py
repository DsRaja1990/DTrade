"""
Paper Trading API Endpoints

This module provides REST API endpoints for managing paper trading strategies,
including starting/stopping strategies and retrieving performance data.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from fastapi import APIRouter, HTTPException, status, BackgroundTasks
from pydantic import BaseModel, Field

from .strategy_engine import paper_trading_engine, StrategyStatus
from .ratio_strategy_paper import RatioStrategyPaperTrader

# Import QSBP Strategy
try:
    from ..strategies.qsbp_strategy.paper_trading_adapter import QSBPPaperTradingAdapter
    QSBP_AVAILABLE = True
except ImportError as e:
    import logging
    logging.getLogger(__name__).warning(f"QSBP strategy not available: {e}")
    QSBP_AVAILABLE = False

logger = logging.getLogger(__name__)

# Create API router
papertest_router = APIRouter(prefix="/api/papertest", tags=["Paper Trading"])

# Pydantic models for API
class StrategyConfig(BaseModel):
    """Strategy configuration model"""
    strategy_type: str = Field(..., description="Type of strategy (e.g., 'ratio_strategy', 'qsbp_strategy')")
    
    # Ratio Strategy Config
    nifty_lots: int = Field(default=20, description="Number of NIFTY lots")
    banknifty_lots: int = Field(default=30, description="Number of BANKNIFTY lots")
    sensex_lots: int = Field(default=50, description="Number of SENSEX lots")
    virtual_capital: float = Field(default=1000000.0, description="Virtual trading capital")
    max_position_risk: float = Field(default=0.02, description="Maximum risk per position (2%)")
    max_total_risk: float = Field(default=0.10, description="Maximum total portfolio risk (10%)")
    
    # QSBP Strategy Config
    capital: Optional[float] = Field(default=400000.0, description="QSBP capital allocation")
    base_long_ratio: Optional[float] = Field(default=0.65, description="Base long allocation ratio")
    base_short_ratio: Optional[float] = Field(default=0.35, description="Base short allocation ratio")
    max_daily_loss: Optional[float] = Field(default=0.03, description="Maximum daily loss percentage")
    paper_trading: Optional[bool] = Field(default=True, description="Enable paper trading mode")
    dhan_access_token: Optional[str] = Field(default=None, description="Dhan API access token")

class StrategyToggleRequest(BaseModel):
    """Strategy toggle request model"""
    strategy_name: str = Field(..., description="Name of the strategy")
    action: str = Field(..., description="Action: 'start', 'stop', 'pause', 'resume'")

class StrategyResponse(BaseModel):
    """Strategy response model"""
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None

class PerformanceMetrics(BaseModel):
    """Performance metrics model"""
    strategy_name: str
    status: str
    current_capital: float
    total_pnl: float
    daily_pnl: float
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    profit_factor: float
    max_drawdown: float
    active_positions: int
    start_time: Optional[datetime]
    end_time: Optional[datetime]

@papertest_router.get("/strategies", response_model=Dict[str, Any])
async def get_all_strategies():
    """Get all registered strategies and their status"""
    try:
        strategies = paper_trading_engine.get_all_strategies()
        return {
            "success": True,
            "message": "Strategies retrieved successfully",
            "data": {
                "strategies": strategies,
                "total_count": len(strategies)
            }
        }
    except Exception as e:
        logger.error(f"Error getting strategies: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve strategies: {str(e)}"
        )

@papertest_router.post("/strategies/register", response_model=StrategyResponse)
async def register_strategy(config: StrategyConfig):
    """Register a new strategy for paper trading"""
    try:
        # Validate strategy type
        if config.strategy_type == "ratio_strategy":
            # Create ratio strategy instance
            strategy = RatioStrategyPaperTrader(config.dict())
            
            # Register with engine
            if paper_trading_engine.register_strategy(strategy):
                return StrategyResponse(
                    success=True,
                    message=f"Strategy '{strategy.name}' registered successfully",
                    data={"strategy_name": strategy.name, "status": strategy.status.value}
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Failed to register strategy"
                )
        
        elif config.strategy_type == "qsbp_strategy" and QSBP_AVAILABLE:
            # Create QSBP strategy instance
            qsbp_config = {
                "capital": config.capital,
                "base_long_ratio": config.base_long_ratio,
                "base_short_ratio": config.base_short_ratio,
                "max_daily_loss": config.max_daily_loss,
                "paper_trading": config.paper_trading,
                "dhan_access_token": config.dhan_access_token
            }
            
            strategy = QSBPPaperTradingAdapter(qsbp_config)
            
            # Register with engine
            if paper_trading_engine.register_strategy(strategy):
                return StrategyResponse(
                    success=True,
                    message=f"QSBP Strategy '{strategy.name}' registered successfully",
                    data={"strategy_name": strategy.name, "status": strategy.status.value}
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Failed to register QSBP strategy"
                )
        
        else:
            available_types = ["ratio_strategy"]
            if QSBP_AVAILABLE:
                available_types.append("qsbp_strategy")
            
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported strategy type: {config.strategy_type}. Available types: {available_types}"
            )
            
    except Exception as e:
        logger.error(f"Error registering strategy: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to register strategy: {str(e)}"
        )

@papertest_router.post("/strategies/toggle", response_model=StrategyResponse)
async def toggle_strategy(request: StrategyToggleRequest, background_tasks: BackgroundTasks):
    """Toggle strategy execution (start/stop/pause/resume)"""
    try:
        strategy_name = request.strategy_name
        action = request.action.lower()
        
        # Validate strategy exists
        if strategy_name not in paper_trading_engine.strategies:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Strategy '{strategy_name}' not found"
            )
        
        # Execute action
        success = False
        message = ""
        
        if action == "start":
            success = await paper_trading_engine.start_strategy(strategy_name)
            message = f"Strategy '{strategy_name}' started" if success else "Failed to start strategy"
            
        elif action == "stop":
            success = await paper_trading_engine.stop_strategy(strategy_name)
            message = f"Strategy '{strategy_name}' stopped" if success else "Failed to stop strategy"
            
        elif action == "pause":
            success = await paper_trading_engine.pause_strategy(strategy_name)
            message = f"Strategy '{strategy_name}' paused" if success else "Failed to pause strategy"
            
        elif action == "resume":
            success = await paper_trading_engine.resume_strategy(strategy_name)
            message = f"Strategy '{strategy_name}' resumed" if success else "Failed to resume strategy"
            
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid action: {action}. Supported actions: start, stop, pause, resume"
            )
        
        if success:
            current_status = paper_trading_engine.get_strategy_status(strategy_name)
            return StrategyResponse(
                success=True,
                message=message,
                data={
                    "strategy_name": strategy_name,
                    "action": action,
                    "new_status": current_status.value if current_status else "unknown"
                }
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=message
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error toggling strategy: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to toggle strategy: {str(e)}"
        )

@papertest_router.get("/strategies/{strategy_name}/status")
async def get_strategy_status(strategy_name: str):
    """Get status of a specific strategy"""
    try:
        if strategy_name not in paper_trading_engine.strategies:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Strategy '{strategy_name}' not found"
            )
        
        strategy = paper_trading_engine.strategies[strategy_name]
        
        # Get detailed status if it's a ratio strategy
        if isinstance(strategy, RatioStrategyPaperTrader):
            status_data = strategy.get_status_summary()
        else:
            status_data = {
                "strategy_name": strategy.name,
                "status": strategy.status.value,
                "total_trades": strategy.metrics.total_trades,
                "win_rate": strategy.metrics.win_rate
            }
        
        return {
            "success": True,
            "message": "Strategy status retrieved successfully",
            "data": status_data
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting strategy status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get strategy status: {str(e)}"
        )

@papertest_router.get("/strategies/{strategy_name}/performance")
async def get_strategy_performance(strategy_name: str):
    """Get performance metrics for a specific strategy"""
    try:
        if strategy_name not in paper_trading_engine.strategies:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Strategy '{strategy_name}' not found"
            )
        
        strategy = paper_trading_engine.strategies[strategy_name]
        
        # Build performance data
        performance_data = {
            "strategy_name": strategy.name,
            "status": strategy.status.value,
            "metrics": {
                "total_trades": strategy.metrics.total_trades,
                "winning_trades": strategy.metrics.winning_trades,
                "losing_trades": strategy.metrics.losing_trades,
                "total_pnl": strategy.metrics.total_pnl,
                "win_rate": strategy.metrics.win_rate,
                "profit_factor": strategy.metrics.profit_factor,
                "max_drawdown": strategy.metrics.max_drawdown,
                "sharpe_ratio": strategy.metrics.sharpe_ratio,
                "start_time": strategy.metrics.start_time.isoformat() if strategy.metrics.start_time else None,
                "end_time": strategy.metrics.end_time.isoformat() if strategy.metrics.end_time else None
            }
        }
        
        # Add strategy-specific data for ratio strategy
        if isinstance(strategy, RatioStrategyPaperTrader):
            performance_data["ratio_strategy_data"] = {
                "current_capital": strategy.current_capital,
                "virtual_capital": strategy.virtual_capital,
                "daily_pnl": strategy.daily_pnl,
                "active_setups": len(strategy.active_setups),
                "peak_capital": strategy.peak_capital,
                "subscribed_instruments": list(strategy.subscribed_instruments)
            }
        
        return {
            "success": True,
            "message": "Performance metrics retrieved successfully",
            "data": performance_data
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting strategy performance: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get strategy performance: {str(e)}"
        )

@papertest_router.get("/strategies/{strategy_name}/trades")
async def get_strategy_trades(strategy_name: str, limit: int = 50):
    """Get recent trades for a specific strategy"""
    try:
        if strategy_name not in paper_trading_engine.strategies:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Strategy '{strategy_name}' not found"
            )
        
        strategy = paper_trading_engine.strategies[strategy_name]
        
        # Get recent trades (limited)
        recent_trades = strategy.trades[-limit:] if len(strategy.trades) > limit else strategy.trades
        
        trades_data = []
        for trade in recent_trades:
            trades_data.append({
                "id": trade.id,
                "instrument": trade.instrument,
                "direction": trade.direction.value,
                "quantity": trade.quantity,
                "price": trade.price,
                "timestamp": trade.timestamp.isoformat(),
                "order_type": trade.order_type,
                "status": trade.status,
                "pnl": trade.pnl,
                "fees": trade.fees
            })
        
        return {
            "success": True,
            "message": f"Retrieved {len(trades_data)} trades",
            "data": {
                "trades": trades_data,
                "total_trades": len(strategy.trades),
                "showing_recent": limit
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting strategy trades: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get strategy trades: {str(e)}"
        )

@papertest_router.get("/strategies/{strategy_name}/positions")
async def get_strategy_positions(strategy_name: str):
    """Get current positions for a specific strategy"""
    try:
        if strategy_name not in paper_trading_engine.strategies:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Strategy '{strategy_name}' not found"
            )
        
        strategy = paper_trading_engine.strategies[strategy_name]
        
        positions_data = []
        for instrument, position in strategy.positions.items():
            if position.quantity != 0:  # Only show active positions
                positions_data.append({
                    "instrument": position.instrument,
                    "quantity": position.quantity,
                    "average_price": position.average_price,
                    "current_price": position.current_price,
                    "unrealized_pnl": position.unrealized_pnl,
                    "realized_pnl": position.realized_pnl,
                    "timestamp": position.timestamp.isoformat()
                })
        
        return {
            "success": True,
            "message": f"Retrieved {len(positions_data)} active positions",
            "data": {
                "positions": positions_data,
                "total_positions": len(positions_data)
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting strategy positions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get strategy positions: {str(e)}"
        )

@papertest_router.delete("/strategies/{strategy_name}")
async def unregister_strategy(strategy_name: str):
    """Unregister a strategy"""
    try:
        if paper_trading_engine.unregister_strategy(strategy_name):
            return StrategyResponse(
                success=True,
                message=f"Strategy '{strategy_name}' unregistered successfully"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Strategy '{strategy_name}' not found"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error unregistering strategy: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to unregister strategy: {str(e)}"
        )

@papertest_router.get("/status")
async def get_system_status():
    """Get system status"""
    return {
        "success": True,
        "message": "Paper trading system status",
        "data": {
            "engine_status": "running",
            "total_strategies": len(paper_trading_engine.strategies),
            "running_strategies": len(paper_trading_engine.running_tasks),
            "timestamp": datetime.now().isoformat()
        }
    }

@papertest_router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "success": True,
        "message": "Paper trading engine is healthy",
        "data": {
            "engine_status": "running",
            "total_strategies": len(paper_trading_engine.strategies),
            "running_strategies": len(paper_trading_engine.running_tasks),
            "timestamp": datetime.now().isoformat()
        }
    }

# Auto-register ratio strategy on startup
async def auto_register_ratio_strategy():
    """Auto-register the ratio strategy for immediate use"""
    try:
        if "ratio_strategy" not in paper_trading_engine.strategies:
            config = StrategyConfig(strategy_type="ratio_strategy")
            strategy = RatioStrategyPaperTrader(config.dict())
            paper_trading_engine.register_strategy(strategy)
            logger.info("Auto-registered ratio strategy for paper trading")
    except Exception as e:
        logger.error(f"Failed to auto-register ratio strategy: {e}")

# Initialize on module import
import asyncio
try:
    loop = asyncio.get_event_loop()
    if loop.is_running():
        asyncio.create_task(auto_register_ratio_strategy())
    else:
        loop.run_until_complete(auto_register_ratio_strategy())
except Exception:
    # Handle case where no event loop is running
    pass
