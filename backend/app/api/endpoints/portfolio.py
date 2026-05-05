"""
Portfolio management endpoints
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime, timedelta
from typing import List, Dict, Any
from pydantic import BaseModel

from ...core.database import get_db
from ...models.user import User
from ...models.trading import Position, Trade, Portfolio
from ...services.dhan_service import DhanHQService
from ..endpoints.auth import get_current_user

router = APIRouter()

class PortfolioSummary(BaseModel):
    total_value: float
    total_investment: float
    total_pnl: float
    day_pnl: float
    available_balance: float
    utilized_margin: float
    total_positions: int
    open_positions: int

class HoldingResponse(BaseModel):
    security_id: str
    trading_symbol: str
    quantity: int
    average_price: float
    current_price: float
    market_value: float
    pnl: float
    pnl_percent: float

@router.get("/summary", response_model=PortfolioSummary)
async def get_portfolio_summary(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get portfolio summary"""
    
    try:
        # Get DhanHQ portfolio data
        dhan_service = DhanHQService(
            client_id=current_user.dhan_client_id,
            access_token=current_user.dhan_access_token
        )
        
        # Get funds
        funds_data = await dhan_service.get_fund_limits()
        available_balance = 0
        utilized_margin = 0
        
        if funds_data.get("status") == "success":
            funds = funds_data.get("data", {})
            available_balance = funds.get("availableBalance", 0)
            utilized_margin = funds.get("utilizedMargin", 0)
        
        # Get positions count
        positions_result = await db.execute(
            select(func.count(Position.id)).where(
                Position.user_id == current_user.id,
                Position.is_open == True
            )
        )
        open_positions = positions_result.scalar() or 0
        
        # Calculate portfolio metrics from database
        portfolio_result = await db.execute(
            select(Portfolio).where(Portfolio.user_id == current_user.id)
        )
        portfolio = portfolio_result.scalar_one_or_none()
        
        if portfolio:
            return PortfolioSummary(
                total_value=portfolio.total_holdings_value,
                total_investment=portfolio.total_investment,
                total_pnl=portfolio.total_pnl,
                day_pnl=portfolio.day_pnl,
                available_balance=available_balance,
                utilized_margin=utilized_margin,
                total_positions=portfolio.total_trades,
                open_positions=open_positions
            )
        else:
            # Create default portfolio if doesn't exist
            return PortfolioSummary(
                total_value=0,
                total_investment=0,
                total_pnl=0,
                day_pnl=0,
                available_balance=available_balance,
                utilized_margin=utilized_margin,
                total_positions=0,
                open_positions=open_positions
            )
    
    except Exception as e:
        # Return default values if error occurs
        return PortfolioSummary(
            total_value=0,
            total_investment=0,
            total_pnl=0,
            day_pnl=0,
            available_balance=0,
            utilized_margin=0,
            total_positions=0,
            open_positions=0
        )

@router.get("/holdings", response_model=List[HoldingResponse])
async def get_holdings(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get portfolio holdings"""
    
    try:
        dhan_service = DhanHQService(
            client_id=current_user.dhan_client_id,
            access_token=current_user.dhan_access_token
        )
        
        # Get holdings from DhanHQ
        holdings_data = await dhan_service.get_holdings()
        
        if holdings_data.get("status") == "success":
            holdings = holdings_data.get("data", [])
            
            return [
                HoldingResponse(
                    security_id=holding.get("securityId", ""),
                    trading_symbol=holding.get("tradingSymbol", ""),
                    quantity=holding.get("quantity", 0),
                    average_price=holding.get("averagePrice", 0),
                    current_price=holding.get("currentPrice", 0),
                    market_value=holding.get("marketValue", 0),
                    pnl=holding.get("pnl", 0),
                    pnl_percent=holding.get("pnlPercent", 0)
                )
                for holding in holdings
            ]
        else:
            return []
    
    except Exception as e:
        return []

@router.get("/funds")
async def get_fund_limits(
    current_user: User = Depends(get_current_user)
):
    """Get fund limits and available balance"""
    
    try:
        dhan_service = DhanHQService(
            client_id=current_user.dhan_client_id,
            access_token=current_user.dhan_access_token
        )
        
        funds_data = await dhan_service.get_fund_limits()
        
        if funds_data.get("status") == "success":
            return funds_data["data"]
        else:
            return {"error": "Failed to fetch fund limits"}
    
    except Exception as e:
        return {"error": f"Failed to fetch fund limits: {str(e)}"}

@router.get("/performance")
async def get_performance_metrics(
    days: int = 30,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get portfolio performance metrics"""
    
    try:
        # Get trades from the last N days
        from_date = datetime.utcnow() - timedelta(days=days)
        
        trades_result = await db.execute(
            select(Trade).where(
                Trade.user_id == current_user.id,
                Trade.trade_time >= from_date
            ).order_by(Trade.trade_time)
        )
        trades = trades_result.scalars().all()
        
        if not trades:
            return {
                "period_days": days,
                "total_trades": 0,
                "winning_trades": 0,
                "losing_trades": 0,
                "win_rate": 0,
                "total_pnl": 0,
                "avg_profit": 0,
                "avg_loss": 0,
                "largest_win": 0,
                "largest_loss": 0
            }
        
        # Calculate metrics
        total_trades = len(trades)
        total_pnl = sum(trade.net_amount for trade in trades)
        winning_trades = len([t for t in trades if t.net_amount > 0])
        losing_trades = len([t for t in trades if t.net_amount < 0])
        
        profits = [t.net_amount for t in trades if t.net_amount > 0]
        losses = [t.net_amount for t in trades if t.net_amount < 0]
        
        return {
            "period_days": days,
            "total_trades": total_trades,
            "winning_trades": winning_trades,
            "losing_trades": losing_trades,
            "win_rate": (winning_trades / total_trades * 100) if total_trades > 0 else 0,
            "total_pnl": total_pnl,
            "avg_profit": sum(profits) / len(profits) if profits else 0,
            "avg_loss": sum(losses) / len(losses) if losses else 0,
            "largest_win": max(profits) if profits else 0,
            "largest_loss": min(losses) if losses else 0
        }
    
    except Exception as e:
        return {"error": f"Failed to calculate performance metrics: {str(e)}"}

@router.get("/pnl-chart")
async def get_pnl_chart(
    days: int = 30,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get daily P&L chart data"""
    
    try:
        from_date = datetime.utcnow() - timedelta(days=days)
        
        # Get daily P&L data
        trades_result = await db.execute(
            select(Trade).where(
                Trade.user_id == current_user.id,
                Trade.trade_time >= from_date
            ).order_by(Trade.trade_time)
        )
        trades = trades_result.scalars().all()
        
        # Group trades by date and calculate daily P&L
        daily_pnl = {}
        cumulative_pnl = 0
        
        for trade in trades:
            date_key = trade.trade_time.date().isoformat()
            if date_key not in daily_pnl:
                daily_pnl[date_key] = 0
            daily_pnl[date_key] += trade.net_amount
        
        # Create chart data
        chart_data = []
        for date_str, pnl in sorted(daily_pnl.items()):
            cumulative_pnl += pnl
            chart_data.append({
                "date": date_str,
                "daily_pnl": round(pnl, 2),
                "cumulative_pnl": round(cumulative_pnl, 2)
            })
        
        return chart_data
    
    except Exception as e:
        return {"error": f"Failed to generate P&L chart: {str(e)}"}

router = APIRouter()
