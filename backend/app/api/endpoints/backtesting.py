"""
Backtesting endpoints
"""
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
import json
import uuid

from ...core.database import get_db
from ...models.user import User
from ...models.ai_strategy import BacktestResult, Strategy
from ..endpoints.auth import get_current_user

router = APIRouter()

class BacktestRequest(BaseModel):
    strategy_id: str
    start_date: datetime
    end_date: datetime
    initial_capital: float
    name: Optional[str] = None

class BacktestResponse(BaseModel):
    id: int
    backtest_id: str
    name: Optional[str]
    strategy_id: str
    start_date: datetime
    end_date: datetime
    initial_capital: float
    final_capital: Optional[float]
    total_return: Optional[float]
    max_drawdown: Optional[float]
    sharpe_ratio: Optional[float]
    total_trades: int
    win_rate: float
    is_completed: bool
    started_at: datetime
    completed_at: Optional[datetime]

@router.post("/", response_model=BacktestResponse, status_code=status.HTTP_201_CREATED)
async def start_backtest(
    backtest_request: BacktestRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Start a new backtest"""
    
    # Verify strategy exists and belongs to user
    strategy_result = await db.execute(
        select(Strategy).where(
            Strategy.strategy_id == backtest_request.strategy_id,
            Strategy.user_id == current_user.id
        )
    )
    strategy = strategy_result.scalar_one_or_none()
    
    if not strategy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Strategy not found"
        )
    
    # Create backtest record
    backtest = BacktestResult(
        backtest_id=str(uuid.uuid4()),
        strategy_id=backtest_request.strategy_id,
        user_id=current_user.id,
        name=backtest_request.name or f"Backtest {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        start_date=backtest_request.start_date,
        end_date=backtest_request.end_date,
        initial_capital=backtest_request.initial_capital,
        started_at=datetime.utcnow()
    )
    
    db.add(backtest)
    await db.commit()
    await db.refresh(backtest)
    
    # Run backtest in background
    background_tasks.add_task(run_backtest_task, backtest.backtest_id, strategy, db)
    
    return BacktestResponse(
        id=backtest.id,
        backtest_id=backtest.backtest_id,
        name=backtest.name,
        strategy_id=backtest.strategy_id,
        start_date=backtest.start_date,
        end_date=backtest.end_date,
        initial_capital=backtest.initial_capital,
        final_capital=backtest.final_capital,
        total_return=backtest.total_return,
        max_drawdown=backtest.max_drawdown,
        sharpe_ratio=backtest.sharpe_ratio,
        total_trades=backtest.total_trades,
        win_rate=backtest.win_rate,
        is_completed=backtest.is_completed,
        started_at=backtest.started_at,
        completed_at=backtest.completed_at
    )

@router.get("/", response_model=List[BacktestResponse])
async def get_backtests(
    strategy_id: Optional[str] = None,
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get user's backtests"""
    
    query = select(BacktestResult).where(BacktestResult.user_id == current_user.id)
    
    if strategy_id:
        query = query.where(BacktestResult.strategy_id == strategy_id)
    
    query = query.order_by(BacktestResult.started_at.desc()).limit(limit)
    
    result = await db.execute(query)
    backtests = result.scalars().all()
    
    return [
        BacktestResponse(
            id=bt.id,
            backtest_id=bt.backtest_id,
            name=bt.name,
            strategy_id=bt.strategy_id,
            start_date=bt.start_date,
            end_date=bt.end_date,
            initial_capital=bt.initial_capital,
            final_capital=bt.final_capital,
            total_return=bt.total_return,
            max_drawdown=bt.max_drawdown,
            sharpe_ratio=bt.sharpe_ratio,
            total_trades=bt.total_trades,
            win_rate=bt.win_rate,
            is_completed=bt.is_completed,
            started_at=bt.started_at,
            completed_at=bt.completed_at
        )
        for bt in backtests
    ]

@router.get("/{backtest_id}", response_model=BacktestResponse)
async def get_backtest(
    backtest_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get specific backtest results"""
    
    result = await db.execute(
        select(BacktestResult).where(
            BacktestResult.backtest_id == backtest_id,
            BacktestResult.user_id == current_user.id
        )
    )
    backtest = result.scalar_one_or_none()
    
    if not backtest:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Backtest not found"
        )
    
    return BacktestResponse(
        id=backtest.id,
        backtest_id=backtest.backtest_id,
        name=backtest.name,
        strategy_id=backtest.strategy_id,
        start_date=backtest.start_date,
        end_date=backtest.end_date,
        initial_capital=backtest.initial_capital,
        final_capital=backtest.final_capital,
        total_return=backtest.total_return,
        max_drawdown=backtest.max_drawdown,
        sharpe_ratio=backtest.sharpe_ratio,
        total_trades=backtest.total_trades,
        win_rate=backtest.win_rate,
        is_completed=backtest.is_completed,
        started_at=backtest.started_at,
        completed_at=backtest.completed_at
    )

@router.get("/{backtest_id}/details")
async def get_backtest_details(
    backtest_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get detailed backtest results including trades and equity curve"""
    
    result = await db.execute(
        select(BacktestResult).where(
            BacktestResult.backtest_id == backtest_id,
            BacktestResult.user_id == current_user.id
        )
    )
    backtest = result.scalar_one_or_none()
    
    if not backtest:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Backtest not found"
        )
    
    # Parse JSON fields
    equity_curve = json.loads(backtest.equity_curve) if backtest.equity_curve else []
    trade_log = json.loads(backtest.trade_log) if backtest.trade_log else []
    monthly_returns = json.loads(backtest.monthly_returns) if backtest.monthly_returns else {}
    
    return {
        "backtest_id": backtest.backtest_id,
        "name": backtest.name,
        "performance_metrics": {
            "total_return": backtest.total_return,
            "annualized_return": backtest.annualized_return,
            "max_drawdown": backtest.max_drawdown,
            "sharpe_ratio": backtest.sharpe_ratio,
            "calmar_ratio": backtest.calmar_ratio,
            "volatility": backtest.volatility,
            "var_95": backtest.var_95,
            "beta": backtest.beta,
            "alpha": backtest.alpha
        },
        "trade_statistics": {
            "total_trades": backtest.total_trades,
            "winning_trades": backtest.winning_trades,
            "losing_trades": backtest.losing_trades,
            "win_rate": backtest.win_rate,
            "avg_win": backtest.avg_win,
            "avg_loss": backtest.avg_loss,
            "largest_win": backtest.largest_win,
            "largest_loss": backtest.largest_loss,
            "profit_factor": backtest.profit_factor
        },
        "equity_curve": equity_curve,
        "trade_log": trade_log,
        "monthly_returns": monthly_returns
    }

@router.delete("/{backtest_id}")
async def delete_backtest(
    backtest_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete a backtest"""
    
    result = await db.execute(
        select(BacktestResult).where(
            BacktestResult.backtest_id == backtest_id,
            BacktestResult.user_id == current_user.id
        )
    )
    backtest = result.scalar_one_or_none()
    
    if not backtest:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Backtest not found"
        )
    
    await db.delete(backtest)
    await db.commit()
    
    return {"message": "Backtest deleted successfully"}

async def run_backtest_task(backtest_id: str, strategy: Strategy, db: AsyncSession):
    """Background task to run backtest"""
    
    try:
        # Mock backtest execution - in real implementation, this would
        # run the actual backtesting algorithm
        import time
        import random
        
        # Simulate backtest processing time
        time.sleep(5)
        
        # Get backtest record
        result = await db.execute(
            select(BacktestResult).where(BacktestResult.backtest_id == backtest_id)
        )
        backtest = result.scalar_one_or_none()
        
        if backtest:
            # Mock results
            total_trades = random.randint(50, 200)
            winning_trades = random.randint(int(total_trades * 0.4), int(total_trades * 0.7))
            losing_trades = total_trades - winning_trades
            
            backtest.final_capital = backtest.initial_capital * random.uniform(0.8, 1.5)
            backtest.total_return = (backtest.final_capital - backtest.initial_capital) / backtest.initial_capital * 100
            backtest.max_drawdown = random.uniform(-20, -5)
            backtest.sharpe_ratio = random.uniform(0.5, 2.5)
            backtest.total_trades = total_trades
            backtest.winning_trades = winning_trades
            backtest.losing_trades = losing_trades
            backtest.win_rate = winning_trades / total_trades * 100
            backtest.is_completed = True
            backtest.completed_at = datetime.utcnow()
            backtest.execution_time_seconds = 5.0
            
            # Mock equity curve data
            equity_curve = []
            equity = backtest.initial_capital
            for i in range(100):
                equity *= random.uniform(0.99, 1.01)
                equity_curve.append({"date": (backtest.start_date + timedelta(days=i)).isoformat(), "equity": equity})
            
            backtest.equity_curve = json.dumps(equity_curve)
            
            await db.commit()
        
    except Exception as e:
        # Log error and mark backtest as failed
        if backtest:
            backtest.is_completed = True
            backtest.completed_at = datetime.utcnow()
            await db.commit()
