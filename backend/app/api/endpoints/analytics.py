"""
Analytics endpoints
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta
from typing import List, Dict, Any
from pydantic import BaseModel

from ...core.database import get_db
from ...models.user import User
from ..endpoints.auth import get_current_user

router = APIRouter()

class PerformanceMetrics(BaseModel):
    total_pnl: float
    win_rate: float
    sharpe_ratio: float
    max_drawdown: float
    total_trades: int
    avg_profit: float
    avg_loss: float

@router.get("/performance")
async def get_performance_analytics(
    days: int = 30,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get comprehensive performance analytics"""
    
    # Mock data - in real implementation, calculate from actual trades
    return {
        "period_days": days,
        "metrics": {
            "total_pnl": 25430.50,
            "total_return_percent": 12.5,
            "win_rate": 68.2,
            "profit_factor": 1.8,
            "sharpe_ratio": 1.45,
            "max_drawdown": -8.2,
            "avg_profit": 1250.30,
            "avg_loss": -680.50,
            "largest_win": 4500.00,
            "largest_loss": -2100.00
        },
        "daily_pnl": [
            {"date": "2025-01-01", "pnl": 450.30},
            {"date": "2025-01-02", "pnl": -120.50},
            {"date": "2025-01-03", "pnl": 780.20}
        ],
        "monthly_breakdown": {
            "current_month": 15230.50,
            "previous_month": 8950.20,
            "month_over_month_change": 70.2
        }
    }

@router.get("/risk-metrics")
async def get_risk_analytics(
    current_user: User = Depends(get_current_user)
):
    """Get risk management analytics"""
    
    return {
        "current_exposure": {
            "total_exposure": 125000.00,
            "max_allowed": current_user.max_position_size,
            "utilization_percent": 62.5
        },
        "risk_limits": {
            "daily_loss_limit": current_user.max_daily_loss,
            "current_daily_loss": -1250.00,
            "remaining_capacity": current_user.max_daily_loss - 1250.00
        },
        "var_metrics": {
            "var_95": -2450.00,
            "cvar_95": -3120.00,
            "stress_test_loss": -5200.00
        },
        "concentration_risk": {
            "top_position_percent": 15.2,
            "sector_concentration": {
                "technology": 35.5,
                "finance": 25.2,
                "healthcare": 18.8,
                "other": 20.5
            }
        }
    }

@router.get("/trading-insights")
async def get_trading_insights(
    current_user: User = Depends(get_current_user)
):
    """Get AI-driven trading insights and recommendations"""
    
    return {
        "market_sentiment": {
            "overall": "bullish",
            "confidence": 72.5,
            "key_factors": [
                "Strong institutional buying",
                "Positive earnings growth",
                "Favorable technical indicators"
            ]
        },
        "ai_recommendations": [
            {
                "type": "position_sizing",
                "message": "Consider reducing position size in NIFTY options due to high volatility",
                "confidence": 85.2,
                "impact": "medium"
            },
            {
                "type": "sector_rotation", 
                "message": "Technology sector showing strong momentum, consider increasing allocation",
                "confidence": 78.6,
                "impact": "high"
            }
        ],
        "optimal_strategies": [
            {
                "strategy": "momentum_breakout",
                "success_rate": 73.2,
                "avg_return": 4.5,
                "recommended_instruments": ["NIFTY", "BANKNIFTY"]
            },
            {
                "strategy": "mean_reversion",
                "success_rate": 65.8,
                "avg_return": 2.8,
                "recommended_instruments": ["RELIANCE", "TCS"]
            }
        ]
    }

@router.get("/market-analysis")
async def get_market_analysis():
    """Get comprehensive market analysis"""
    
    return {
        "market_overview": {
            "trend": "uptrend",
            "strength": "strong",
            "volatility": "moderate",
            "volume": "above_average"
        },
        "technical_indicators": {
            "rsi": 65.2,
            "macd": "bullish_crossover",
            "bollinger_bands": "middle_range",
            "moving_averages": "above_all_major"
        },
        "support_resistance": {
            "nifty": {
                "support": [19500, 19350, 19200],
                "resistance": [19800, 19950, 20100]
            },
            "bank_nifty": {
                "support": [44500, 44200, 43900],
                "resistance": [45000, 45300, 45600]
            }
        },
        "sectoral_performance": [
            {"sector": "IT", "change_percent": 2.1, "trend": "bullish"},
            {"sector": "Banking", "change_percent": 1.8, "trend": "bullish"},
            {"sector": "Auto", "change_percent": -0.5, "trend": "bearish"},
            {"sector": "Pharma", "change_percent": 0.8, "trend": "neutral"}
        ],
        "options_data": {
            "put_call_ratio": 0.85,
            "max_pain": 19650,
            "implied_volatility": 18.5,
            "option_flow": "call_buying"
        }
    }

@router.get("/strategy-performance")
async def get_strategy_performance(
    strategy_id: str = None,
    current_user: User = Depends(get_current_user)
):
    """Get strategy-specific performance analytics"""
    
    return {
        "strategy_comparison": [
            {
                "strategy_name": "AI Momentum",
                "total_return": 15.2,
                "win_rate": 72.5,
                "sharpe_ratio": 1.8,
                "max_drawdown": -6.5,
                "total_trades": 125
            },
            {
                "strategy_name": "Options Scalping",
                "total_return": 8.7,
                "win_rate": 65.2,
                "sharpe_ratio": 1.2,
                "max_drawdown": -4.2,
                "total_trades": 89
            }
        ],
        "monthly_performance": {
            "current_month": 4.2,
            "last_month": 3.8,
            "3_month_avg": 4.5,
            "ytd": 15.2
        },
        "risk_adjusted_returns": {
            "information_ratio": 1.35,
            "treynor_ratio": 0.082,
            "jensen_alpha": 2.1
        }
    }

@router.get("/performance/stats")
async def get_performance_stats():
    """Get performance statistics (public endpoint for demo)"""
    import random
    
    # Generate realistic performance stats
    return {
        "total_signals": random.randint(150, 300),
        "successful_trades": random.randint(100, 200),
        "win_rate": round(random.uniform(65, 85), 1),
        "avg_profit": round(random.uniform(1200, 2500), 2),
        "total_pnl": round(random.uniform(15000, 50000), 2),
        "sharpe_ratio": round(random.uniform(1.2, 2.1), 2),
        "max_drawdown": round(random.uniform(-5, -12), 1),
        "profit_factor": round(random.uniform(1.4, 2.2), 2),
        "updated_at": datetime.now().isoformat()
    }
