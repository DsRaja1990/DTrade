"""
Strategy management endpoints
"""
from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
import json
import uuid

from ...core.database import get_db
from ...models.user import User
from ...models.ai_strategy import Strategy, StrategyType, StrategyStatus, RiskLevel
from ..endpoints.auth import get_current_user

router = APIRouter()

class StrategyCreateRequest(BaseModel):
    name: str
    description: Optional[str] = None
    strategy_type: str
    config: Dict[str, Any]
    instruments: List[str]
    timeframes: List[str]
    max_position_size: Optional[float] = 50000
    max_daily_loss: Optional[float] = 10000
    stop_loss_percent: Optional[float] = 2.0
    take_profit_percent: Optional[float] = 4.0
    risk_level: Optional[str] = "medium"

class StrategyResponse(BaseModel):
    id: int
    strategy_id: str
    name: str
    description: Optional[str]
    strategy_type: str
    status: str
    risk_level: str
    total_trades: int
    win_rate: float
    total_pnl: float
    max_drawdown: float
    is_running: bool
    created_at: datetime
    last_run_at: Optional[datetime]

@router.get("/", response_model=List[StrategyResponse])
async def get_strategies(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get all user strategies"""
    
    result = await db.execute(
        select(Strategy).where(Strategy.user_id == current_user.id)
        .order_by(Strategy.created_at.desc())
    )
    strategies = result.scalars().all()
    
    return [
        StrategyResponse(
            id=strategy.id,
            strategy_id=strategy.strategy_id,
            name=strategy.name,
            description=strategy.description,
            strategy_type=strategy.strategy_type.value,
            status=strategy.status.value,
            risk_level=strategy.risk_level.value,
            total_trades=strategy.total_trades,
            win_rate=strategy.win_rate,
            total_pnl=strategy.total_pnl,
            max_drawdown=strategy.max_drawdown,
            is_running=strategy.is_running,
            created_at=strategy.created_at,
            last_run_at=strategy.last_run_at
        )
        for strategy in strategies
    ]

@router.post("/", response_model=StrategyResponse, status_code=status.HTTP_201_CREATED)
async def create_strategy(
    strategy_request: StrategyCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new trading strategy"""
    
    try:
        strategy = Strategy(
            user_id=current_user.id,
            strategy_id=str(uuid.uuid4()),
            name=strategy_request.name,
            description=strategy_request.description,
            strategy_type=StrategyType(strategy_request.strategy_type),
            config_json=json.dumps(strategy_request.config),
            instruments=json.dumps(strategy_request.instruments),
            timeframes=json.dumps(strategy_request.timeframes),
            max_position_size=strategy_request.max_position_size,
            max_daily_loss=strategy_request.max_daily_loss,
            stop_loss_percent=strategy_request.stop_loss_percent,
            take_profit_percent=strategy_request.take_profit_percent,
            risk_level=RiskLevel(strategy_request.risk_level)
        )
        
        db.add(strategy)
        await db.commit()
        await db.refresh(strategy)
        
        return StrategyResponse(
            id=strategy.id,
            strategy_id=strategy.strategy_id,
            name=strategy.name,
            description=strategy.description,
            strategy_type=strategy.strategy_type.value,
            status=strategy.status.value,
            risk_level=strategy.risk_level.value,
            total_trades=strategy.total_trades,
            win_rate=strategy.win_rate,
            total_pnl=strategy.total_pnl,
            max_drawdown=strategy.max_drawdown,
            is_running=strategy.is_running,
            created_at=strategy.created_at,
            last_run_at=strategy.last_run_at
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create strategy: {str(e)}"
        )

@router.get("/{strategy_id}", response_model=StrategyResponse)
async def get_strategy(
    strategy_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get a specific strategy"""
    
    result = await db.execute(
        select(Strategy).where(
            Strategy.strategy_id == strategy_id,
            Strategy.user_id == current_user.id
        )
    )
    strategy = result.scalar_one_or_none()
    
    if not strategy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Strategy not found"
        )
    
    return StrategyResponse(
        id=strategy.id,
        strategy_id=strategy.strategy_id,
        name=strategy.name,
        description=strategy.description,
        strategy_type=strategy.strategy_type.value,
        status=strategy.status.value,
        risk_level=strategy.risk_level.value,
        total_trades=strategy.total_trades,
        win_rate=strategy.win_rate,
        total_pnl=strategy.total_pnl,
        max_drawdown=strategy.max_drawdown,
        is_running=strategy.is_running,
        created_at=strategy.created_at,
        last_run_at=strategy.last_run_at
    )

@router.post("/{strategy_id}/start")
async def start_strategy(
    strategy_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Start a trading strategy"""
    
    result = await db.execute(
        select(Strategy).where(
            Strategy.strategy_id == strategy_id,
            Strategy.user_id == current_user.id
        )
    )
    strategy = result.scalar_one_or_none()
    
    if not strategy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Strategy not found"
        )
    
    if strategy.is_running:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Strategy is already running"
        )
    
    try:
        strategy.is_running = True
        strategy.status = StrategyStatus.ACTIVE
        strategy.last_run_at = datetime.utcnow()
        
        await db.commit()
        
        return {
            "status": "success",
            "message": f"Strategy '{strategy.name}' started successfully",
            "strategy_id": strategy_id
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start strategy: {str(e)}"
        )

@router.post("/{strategy_id}/stop")
async def stop_strategy(
    strategy_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Stop a trading strategy"""
    
    result = await db.execute(
        select(Strategy).where(
            Strategy.strategy_id == strategy_id,
            Strategy.user_id == current_user.id
        )
    )
    strategy = result.scalar_one_or_none()
    
    if not strategy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Strategy not found"
        )
    
    if not strategy.is_running:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Strategy is not running"
        )
    
    try:
        strategy.is_running = False
        strategy.status = StrategyStatus.INACTIVE
        
        await db.commit()
        
        return {
            "status": "success",
            "message": f"Strategy '{strategy.name}' stopped successfully",
            "strategy_id": strategy_id
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to stop strategy: {str(e)}"
        )

@router.delete("/{strategy_id}")
async def delete_strategy(
    strategy_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete a trading strategy"""
    
    result = await db.execute(
        select(Strategy).where(
            Strategy.strategy_id == strategy_id,
            Strategy.user_id == current_user.id
        )
    )
    strategy = result.scalar_one_or_none()
    
    if not strategy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Strategy not found"
        )
    
    if strategy.is_running:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete a running strategy. Stop it first."
        )
    
    try:
        await db.delete(strategy)
        await db.commit()
        
        return {
            "status": "success",
            "message": f"Strategy '{strategy.name}' deleted successfully"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete strategy: {str(e)}"
        )
