#!/usr/bin/env python3
"""
Analytics API Router for Trading Database
==========================================

Provides REST endpoints for:
1. Performance analytics and reporting
2. Signal accuracy analysis
3. Indicator correlation studies
4. Market regime performance
5. Trade history and export

Author: DTrade Systems
Version: 1.0.0
"""

import logging
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
import json

from .db_manager import get_database, SignalRecord, TradeRecord

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(tags=["analytics"])


# ============================================================================
# RESPONSE MODELS
# ============================================================================

class PerformanceSummary(BaseModel):
    period_days: int
    total_trades: int
    total_wins: int
    total_losses: int
    win_rate: float
    gross_profit: float
    gross_loss: float
    net_pnl: float
    profit_factor: float
    avg_daily_pnl: float


class SignalAccuracyResponse(BaseModel):
    score_range: str
    total_signals: int
    traded: int
    correct: int
    accuracy_pct: float


class SymbolPerformance(BaseModel):
    symbol: str
    trades: int
    wins: int
    losses: int
    win_rate: float
    total_pnl: float
    avg_pnl: float
    best_trade: float
    worst_trade: float


# ============================================================================
# PERFORMANCE ENDPOINTS
# ============================================================================

@router.get("/performance/summary")
async def get_performance_summary(days: int = Query(default=30, ge=1, le=365)):
    """
    Get comprehensive performance summary for the last N days.
    
    Returns:
    - Total trades, wins, losses
    - Win rate and profit factor
    - Net P&L and daily averages
    - Best and worst days
    """
    try:
        db = get_database()
        summary = db.get_performance_summary(days)
        
        return {
            "status": "success",
            "data": summary,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting performance summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/performance/daily")
async def get_daily_performance(
    start_date: Optional[str] = Query(default=None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(default=None, description="End date (YYYY-MM-DD)")
):
    """
    Get daily performance breakdown for a date range.
    """
    try:
        db = get_database()
        
        # Parse dates
        if start_date:
            start = datetime.strptime(start_date, "%Y-%m-%d").date()
        else:
            start = date.today() - timedelta(days=30)
        
        if end_date:
            end = datetime.strptime(end_date, "%Y-%m-%d").date()
        else:
            end = date.today()
        
        # Get data for each day
        current = start
        daily_data = []
        
        while current <= end:
            perf = db.calculate_daily_performance(current)
            daily_data.append({
                "date": current.isoformat(),
                "trades": perf.total_trades,
                "wins": perf.wins,
                "losses": perf.losses,
                "win_rate": perf.win_rate,
                "net_pnl": perf.net_pnl,
                "profit_factor": perf.profit_factor,
                "signals_generated": perf.signals_generated
            })
            current += timedelta(days=1)
        
        return {
            "status": "success",
            "date_range": {"start": start.isoformat(), "end": end.isoformat()},
            "data": daily_data,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting daily performance: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/performance/symbols")
async def get_symbol_performance():
    """
    Get performance breakdown by trading symbol.
    
    Useful for identifying:
    - Most profitable symbols
    - Symbols to avoid
    - Win rate by symbol
    """
    try:
        db = get_database()
        data = db.get_symbol_performance()
        
        return {
            "status": "success",
            "count": len(data),
            "data": data,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting symbol performance: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/performance/hours")
async def get_hourly_performance():
    """
    Get performance breakdown by trading hour.
    
    Useful for identifying:
    - Best hours to trade
    - Hours to avoid
    """
    try:
        db = get_database()
        data = db.get_best_trading_hours()
        
        return {
            "status": "success",
            "data": data,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting hourly performance: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/performance/market-regime")
async def get_market_regime_performance():
    """
    Get performance by market regime.
    
    Helps understand:
    - Which regimes are most profitable
    - When to be more/less aggressive
    """
    try:
        db = get_database()
        data = db.get_market_regime_performance()
        
        return {
            "status": "success",
            "data": data,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting market regime performance: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# SIGNAL ANALYSIS ENDPOINTS
# ============================================================================

@router.get("/signals/accuracy-by-score")
async def get_signal_accuracy_by_score():
    """
    Analyze signal accuracy by combined score ranges.
    
    Critical for:
    - Optimizing minimum score threshold
    - Understanding score-to-success correlation
    """
    try:
        db = get_database()
        data = db.get_signal_accuracy_by_score()
        
        return {
            "status": "success",
            "data": data,
            "insight": "Higher scores generally correlate with better accuracy",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting signal accuracy: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/signals/accuracy-by-indicator")
async def get_signal_accuracy_by_indicator():
    """
    Analyze which technical indicators correlate with successful trades.
    
    Helps optimize:
    - Indicator weights in scoring
    - Which indicators to prioritize
    """
    try:
        db = get_database()
        data = db.get_signal_accuracy_by_indicator()
        
        return {
            "status": "success",
            "data": data,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting indicator accuracy: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/signals/ai-confidence-accuracy")
async def get_ai_confidence_accuracy():
    """
    Analyze AI confidence vs actual outcomes.
    
    Critical for:
    - Validating AI model performance
    - Adjusting confidence thresholds
    """
    try:
        db = get_database()
        data = db.get_ai_confidence_accuracy()
        
        return {
            "status": "success",
            "data": data,
            "insight": "Compare AI confidence with actual hit rate to calibrate model",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting AI accuracy: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/signals/recent")
async def get_recent_signals(
    limit: int = Query(default=50, ge=1, le=500),
    symbol: Optional[str] = None,
    min_score: Optional[float] = None
):
    """
    Get recent signals with optional filters.
    """
    try:
        db = get_database()
        
        if symbol:
            data = db.get_signals_by_symbol(symbol, limit)
        elif min_score:
            data = db.get_high_score_signals(min_score, limit)
        else:
            data = db.get_signals_by_date(date.today())
        
        return {
            "status": "success",
            "count": len(data),
            "data": data,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting recent signals: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# TRADE HISTORY ENDPOINTS
# ============================================================================

@router.get("/trades/recent")
async def get_recent_trades(
    limit: int = Query(default=50, ge=1, le=500),
    status: Optional[str] = Query(default=None, description="Filter by status: OPEN, CLOSED")
):
    """
    Get recent trades with optional status filter.
    """
    try:
        db = get_database()
        
        if status == "OPEN":
            data = db.get_open_trades()
        else:
            data = db.get_trades_by_date(date.today())
        
        return {
            "status": "success",
            "count": len(data),
            "data": data[:limit],
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting recent trades: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/trades/open")
async def get_open_trades():
    """
    Get all currently open trades.
    """
    try:
        db = get_database()
        data = db.get_open_trades()
        
        return {
            "status": "success",
            "count": len(data),
            "data": data,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting open trades: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# ERROR ANALYSIS ENDPOINTS
# ============================================================================

@router.get("/errors/summary")
async def get_error_summary(days: int = Query(default=7, ge=1, le=30)):
    """
    Get error summary for debugging and reliability improvement.
    """
    try:
        db = get_database()
        data = db.get_error_summary(days)
        
        return {
            "status": "success",
            "period_days": days,
            "data": data,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting error summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# ENHANCEMENT RECOMMENDATIONS
# ============================================================================

@router.get("/recommendations")
async def get_enhancement_recommendations():
    """
    Get data-driven recommendations for system enhancement.
    
    Analyzes:
    - Score thresholds
    - Indicator weights
    - Trading hours
    - Symbol selection
    """
    try:
        db = get_database()
        
        recommendations = []
        
        # Analyze score accuracy
        score_data = db.get_signal_accuracy_by_score()
        if score_data:
            best_range = max(score_data, key=lambda x: x.get('accuracy_pct', 0) if x.get('traded', 0) > 5 else 0)
            if best_range:
                recommendations.append({
                    "category": "SCORE_THRESHOLD",
                    "recommendation": f"Focus on signals in {best_range['score_range']} range",
                    "data": best_range
                })
        
        # Analyze AI confidence
        ai_data = db.get_ai_confidence_accuracy()
        if ai_data:
            best_confidence = max(ai_data, key=lambda x: x.get('accuracy_pct', 0) if x.get('total', 0) > 5 else 0)
            if best_confidence:
                recommendations.append({
                    "category": "AI_CONFIDENCE",
                    "recommendation": f"AI confidence {best_confidence['confidence_range']} shows best accuracy",
                    "data": best_confidence
                })
        
        # Analyze trading hours
        hour_data = db.get_best_trading_hours()
        if hour_data:
            best_hours = sorted(hour_data, key=lambda x: x.get('win_rate', 0), reverse=True)[:3]
            recommendations.append({
                "category": "TRADING_HOURS",
                "recommendation": f"Best trading hours: {', '.join([h['hour'] + ':00' for h in best_hours])}",
                "data": best_hours
            })
        
        # Analyze symbols
        symbol_data = db.get_symbol_performance()
        if symbol_data:
            # Best performers
            best_symbols = sorted([s for s in symbol_data if s.get('trades', 0) >= 5], 
                                 key=lambda x: x.get('win_rate', 0), reverse=True)[:5]
            # Worst performers
            worst_symbols = sorted([s for s in symbol_data if s.get('trades', 0) >= 5], 
                                  key=lambda x: x.get('win_rate', 0))[:3]
            
            if best_symbols:
                recommendations.append({
                    "category": "BEST_SYMBOLS",
                    "recommendation": f"Top performing symbols: {', '.join([s['symbol'] for s in best_symbols])}",
                    "data": best_symbols
                })
            
            if worst_symbols and worst_symbols[0].get('win_rate', 100) < 40:
                recommendations.append({
                    "category": "AVOID_SYMBOLS",
                    "recommendation": f"Consider avoiding: {', '.join([s['symbol'] for s in worst_symbols])}",
                    "data": worst_symbols
                })
        
        # Analyze market regimes
        regime_data = db.get_market_regime_performance()
        if regime_data:
            best_regime = max(regime_data, key=lambda x: x.get('win_rate', 0) if x.get('trades', 0) > 5 else 0)
            worst_regime = min(regime_data, key=lambda x: x.get('win_rate', 100) if x.get('trades', 0) > 5 else 100)
            
            if best_regime:
                recommendations.append({
                    "category": "MARKET_REGIME",
                    "recommendation": f"Best performance in {best_regime['regime']} regime ({best_regime['win_rate']}% win rate)",
                    "data": {"best": best_regime, "worst": worst_regime}
                })
        
        return {
            "status": "success",
            "recommendations": recommendations,
            "recommendation_count": len(recommendations),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error generating recommendations: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# DATA EXPORT
# ============================================================================

@router.get("/export/signals")
async def export_signals(
    start_date: str = Query(..., description="Start date (YYYY-MM-DD)"),
    end_date: str = Query(..., description="End date (YYYY-MM-DD)"),
    format: str = Query(default="json", description="Export format: json or csv")
):
    """
    Export signals data for external analysis.
    """
    try:
        db = get_database()
        
        start = datetime.strptime(start_date, "%Y-%m-%d").date()
        end = datetime.strptime(end_date, "%Y-%m-%d").date()
        
        all_signals = []
        current = start
        
        while current <= end:
            signals = db.get_signals_by_date(current)
            all_signals.extend(signals)
            current += timedelta(days=1)
        
        if format == "csv":
            # Convert to CSV format
            if not all_signals:
                return {"status": "success", "message": "No data to export"}
            
            import csv
            from io import StringIO
            
            output = StringIO()
            writer = csv.DictWriter(output, fieldnames=all_signals[0].keys())
            writer.writeheader()
            writer.writerows(all_signals)
            
            return {
                "status": "success",
                "format": "csv",
                "data": output.getvalue(),
                "record_count": len(all_signals)
            }
        else:
            return {
                "status": "success",
                "format": "json",
                "data": all_signals,
                "record_count": len(all_signals)
            }
            
    except Exception as e:
        logger.error(f"Error exporting signals: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def database_health():
    """
    Check database health and statistics.
    """
    try:
        db = get_database()
        
        with db.get_cursor() as cursor:
            # Get table counts
            cursor.execute("SELECT COUNT(*) as count FROM signals")
            signal_count = cursor.fetchone()['count']
            
            cursor.execute("SELECT COUNT(*) as count FROM trades")
            trade_count = cursor.fetchone()['count']
            
            cursor.execute("SELECT COUNT(*) as count FROM daily_performance")
            perf_count = cursor.fetchone()['count']
            
            cursor.execute("SELECT COUNT(*) as count FROM error_logs WHERE resolved = 0")
            error_count = cursor.fetchone()['count']
        
        return {
            "status": "healthy",
            "database_path": str(db.db_path),
            "statistics": {
                "signals": signal_count,
                "trades": trade_count,
                "daily_records": perf_count,
                "unresolved_errors": error_count
            },
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }
