"""
╔══════════════════════════════════════════════════════════════════════════════════════╗
║                     ELITE OPTIONS SCANNER API v1.0                                   ║
║        REST API Endpoints for Screener-Based F&O Options Trading                     ║
║══════════════════════════════════════════════════════════════════════════════════════║
║                                                                                      ║
║  ENDPOINTS:                                                                          ║
║  ──────────                                                                          ║
║  POST /api/scanner/scan           - Trigger full market scan                         ║
║  GET  /api/scanner/opportunities  - Get ranked opportunities                         ║
║  POST /api/scanner/execute        - Execute trades for opportunities                 ║
║  GET  /api/scanner/trades         - Get active trades                                ║
║  GET  /api/scanner/trade/{id}     - Get specific trade                               ║
║  POST /api/scanner/exit/{id}      - Manual exit a trade                              ║
║  GET  /api/scanner/stats          - Get trading statistics                           ║
║  GET  /api/scanner/history        - Get trade history                                ║
║  GET  /api/scanner/chain/{symbol} - Get option chain analysis                        ║
║                                                                                      ║
╚══════════════════════════════════════════════════════════════════════════════════════╝
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse

# Import World Class Engine for advanced direction determination
try:
    from strategy.world_class_engine import WorldClassEngine, WorldClassConfig, WorldClassIndicators, WorldClassPatternDetector
    WORLD_CLASS_ENGINE_AVAILABLE = True
except ImportError:
    try:
        from world_class_engine import WorldClassEngine, WorldClassConfig, WorldClassIndicators, WorldClassPatternDetector
        WORLD_CLASS_ENGINE_AVAILABLE = True
    except ImportError:
        WORLD_CLASS_ENGINE_AVAILABLE = False

logger = logging.getLogger(__name__ + '.scanner_api')

router = APIRouter(prefix="/api/scanner", tags=["elite-options-scanner"])

# ============================================================================
# PYDANTIC MODELS
# ============================================================================

class ScanRequest(BaseModel):
    """Request to trigger a scan"""
    min_confidence: float = Field(default=80, description="Minimum confidence score (0-100)")
    max_results: int = Field(default=10, description="Maximum opportunities to return")
    sectors: Optional[List[str]] = Field(default=None, description="Filter by sectors")
    capital: float = Field(default=100000, description="Available capital for allocation")


class ExecuteRequest(BaseModel):
    """Request to execute trades"""
    symbols: List[str] = Field(..., description="Symbols to execute trades for")
    capital_per_trade: Optional[float] = Field(default=None, description="Capital per trade (optional)")
    paper_trading: bool = Field(default=True, description="Use paper trading mode")


class ExitRequest(BaseModel):
    """Request to exit a trade"""
    reason: str = Field(default="manual", description="Reason for exit")
    exit_pct: float = Field(default=100, description="Percentage to exit (0-100)")


class ChainAnalysisRequest(BaseModel):
    """Request for option chain analysis"""
    spot_price: Optional[float] = Field(default=None, description="Current spot price")
    expiry: Optional[str] = Field(default=None, description="Expiry date (YYYY-MM-DD)")
    capital: float = Field(default=100000, description="Available capital")


class OpportunityResponse(BaseModel):
    """Single opportunity in response"""
    symbol: str
    direction: str
    confidence: float
    rank: int
    momentum_type: str
    breakout_strength: float
    recommended_strike: float
    premium_per_lot: float
    lot_size: int
    max_lots: int
    entry_range: List[float]
    stoploss: float
    target_1: float
    target_2: float
    ai_thesis: str
    catalysts: List[str]
    signal_time: str


# ============================================================================
# GLOBAL STATE
# ============================================================================

# Will be initialized when service starts
scanner_instance = None
chain_analyzer_instance = None
trade_executor_instance = None

# Cached opportunities from last scan
last_scan_results = {
    "opportunities": [],
    "scan_time": None,
    "total_scanned": 0,
    "shortlisted": 0,
}

# Configuration
scanner_config = {
    "available_capital": 100000,
    "paper_trading": True,
    "auto_execute": False,
    "max_active_trades": 5,
    "min_confidence": 80,
}


# ============================================================================
# INITIALIZATION
# ============================================================================

async def initialize_scanner():
    """Initialize scanner components"""
    global scanner_instance, chain_analyzer_instance, trade_executor_instance
    
    try:
        # Import components
        from strategy.elite_options_scanner import EliteOptionsScanner
        from strategy.options_chain_analyzer import OptionsChainAnalyzer
        from strategy.trade_executor import EliteTradeExecutor
        
        # Initialize scanner
        scanner_instance = EliteOptionsScanner()
        await scanner_instance.initialize()
        
        # Initialize chain analyzer
        chain_analyzer_instance = OptionsChainAnalyzer()
        await chain_analyzer_instance.initialize()
        
        # Initialize trade executor
        trade_executor_instance = EliteTradeExecutor(
            scanner=scanner_instance,
            chain_analyzer=chain_analyzer_instance,
        )
        await trade_executor_instance.initialize()
        
        logger.info("✅ Elite Options Scanner components initialized")
        return True
        
    except Exception as e:
        logger.error(f"Failed to initialize scanner: {e}")
        return False


async def shutdown_scanner():
    """Shutdown scanner components"""
    global scanner_instance, chain_analyzer_instance, trade_executor_instance
    
    if scanner_instance:
        await scanner_instance.close()
    
    if chain_analyzer_instance:
        await chain_analyzer_instance.close()
    
    if trade_executor_instance:
        await trade_executor_instance.close()
    
    logger.info("✅ Scanner components shutdown complete")


# ============================================================================
# HEALTH & STATUS ENDPOINTS
# ============================================================================

@router.get("/health")
async def scanner_health():
    """Health check for scanner"""
    return {
        "status": "healthy",
        "scanner_initialized": scanner_instance is not None,
        "chain_analyzer_initialized": chain_analyzer_instance is not None,
        "trade_executor_initialized": trade_executor_instance is not None,
        "timestamp": datetime.now().isoformat(),
    }


@router.get("/status")
async def scanner_status():
    """Get scanner status"""
    active_trades = []
    stats = {}
    
    if trade_executor_instance:
        active_trades = trade_executor_instance.get_active_trades()
        stats = trade_executor_instance.get_stats()
    
    return {
        "status": "running" if scanner_instance else "not_initialized",
        "config": scanner_config,
        "last_scan": last_scan_results.get("scan_time"),
        "opportunities_found": len(last_scan_results.get("opportunities", [])),
        "active_trades": len(active_trades),
        "stats": stats,
        "timestamp": datetime.now().isoformat(),
    }


@router.get("/config")
async def get_scanner_config():
    """Get scanner configuration"""
    return {
        "config": scanner_config,
        "success": True,
    }


@router.put("/config")
async def update_scanner_config(request: Dict[str, Any]):
    """Update scanner configuration"""
    try:
        if "available_capital" in request:
            scanner_config["available_capital"] = float(request["available_capital"])
        if "paper_trading" in request:
            scanner_config["paper_trading"] = bool(request["paper_trading"])
        if "auto_execute" in request:
            scanner_config["auto_execute"] = bool(request["auto_execute"])
        if "max_active_trades" in request:
            scanner_config["max_active_trades"] = int(request["max_active_trades"])
        if "min_confidence" in request:
            scanner_config["min_confidence"] = float(request["min_confidence"])
        
        logger.info(f"Scanner config updated: {scanner_config}")
        
        return {
            "success": True,
            "config": scanner_config,
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ============================================================================
# SCANNING ENDPOINTS
# ============================================================================

# Gemini Trade Service URL for centralized scanning
GEMINI_SERVICE_URL = "http://localhost:4080"

@router.post("/scan")
async def trigger_scan(request: ScanRequest = None):
    """
    Trigger a full market scan for F&O opportunities
    
    This endpoint:
    1. First tries centralized Gemini Service (more reliable)
    2. Falls back to local scanner if Gemini service unavailable
    3. Ranks opportunities by confidence and capital efficiency
    """
    global last_scan_results
    
    try:
        import aiohttp
        
        # Default request values
        if request is None:
            request = ScanRequest()
        
        min_conf = request.min_confidence
        max_results = request.max_results
        capital = request.capital or scanner_config["available_capital"]
        
        logger.info(f"🔍 Starting F&O scan via Gemini Service (min_conf={min_conf}, max={max_results})")
        
        # Try centralized Gemini Service first (more reliable with retry logic)
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{GEMINI_SERVICE_URL}/api/equity/scanner",
                    params={
                        "min_confidence": min_conf / 10,  # Convert to 0-10 scale
                        "max_results": max_results,
                    },
                    timeout=aiohttp.ClientTimeout(total=60)
                ) as resp:
                    if resp.status == 200:
                        gemini_result = await resp.json()
                        
                        if gemini_result.get("status") == "success":
                            # Convert Gemini format to our format
                            opportunities = []
                            for opp in gemini_result.get("opportunities", []):
                                opportunities.append({
                                    "symbol": opp.get("symbol"),
                                    "direction": "LONG" if opp.get("signal") == "BUY_CALL" else "SHORT",
                                    "option_type": "CE" if opp.get("signal") == "BUY_CALL" else "PE",
                                    "confidence": opp.get("confidence", 0) * 10,  # Scale to 0-100
                                    "momentum_score": opp.get("momentum_score", 0),
                                    "volume_score": opp.get("volume_score", 0),
                                    "sector": opp.get("sector", "Unknown"),
                                    "sector_bias": opp.get("sector_bias", "NEUTRAL"),
                                    "entry_range": opp.get("entry_range", ""),
                                    "stop_loss": opp.get("stop_loss", ""),
                                    "target": opp.get("target", ""),
                                    "thesis": opp.get("thesis", ""),
                                    "lot_size": opp.get("lot_size", 1),
                                    "risk_factors": opp.get("risk_factors", []),
                                    "source": "gemini_centralized",
                                })
                            
                            last_scan_results = {
                                "opportunities": opportunities,
                                "scan_time": datetime.now().isoformat(),
                                "total_scanned": gemini_result.get("total_scanned", 0),
                                "shortlisted": len(opportunities),
                            }
                            
                            logger.info(f"✅ Gemini scan complete: {len(opportunities)} opportunities found")
                            
                            return {
                                "success": True,
                                "opportunities": opportunities,
                                "scan_time": last_scan_results["scan_time"],
                                "total_scanned": last_scan_results["total_scanned"],
                                "shortlisted": last_scan_results["shortlisted"],
                                "source": "gemini_centralized",
                            }
        except Exception as e:
            logger.warning(f"Gemini service unavailable: {e}, falling back to local scanner")
        
        # Fallback to local scanner
        if not scanner_instance:
            success = await initialize_scanner()
            if not success:
                raise HTTPException(
                    status_code=503, 
                    detail="Scanner not initialized and Gemini service unavailable."
                )
        
        # Local scanner fallback
        logger.info("🔍 Using local scanner fallback...")
        
        min_conf = request.min_confidence
        max_results = request.max_results
        capital = request.capital or scanner_config["available_capital"]
        
        # Perform scan
        # Tier 1: Rapid screening
        shortlisted = await scanner_instance.tier1_rapid_screening()
        
        opportunities = []
        
        for stock in shortlisted[:max_results * 2]:  # Scan more to get enough after filtering
            # Tier 2: Deep analysis (simulated for now)
            momentum_score = stock.momentum_score * 100
            
            if momentum_score >= min_conf:
                # Tier 3: Gemini Pro confirmation
                confirmation = await scanner_instance.tier3_gemini_confirmation(
                    stock.symbol,
                    stock.current_price,
                    stock.momentum_score
                ) if hasattr(scanner_instance, 'tier3_gemini_confirmation') else {
                    "confirmed": True,
                    "confidence": momentum_score,
                    "thesis": f"Strong momentum detected in {stock.symbol}",
                    "catalysts": ["Volume surge", "Pattern breakout"],
                }
                
                if confirmation.get("confirmed", False):
                    # ========================================
                    # ADVANCED DIRECTION DETERMINATION
                    # Uses World Class Engine for proper CE/PE selection
                    # ========================================
                    direction = "CE"  # Default to CE
                    option_type = "CE"
                    
                    # Use World Class Engine if available
                    if WORLD_CLASS_ENGINE_AVAILABLE:
                        try:
                            import yfinance as yf
                            import pandas as pd
                            
                            # Get market data for the stock
                            symbol_yf = f"{stock.symbol}.NS"
                            df = yf.download(symbol_yf, period="3mo", progress=False)
                            
                            if df is not None and len(df) >= 50:
                                # Flatten MultiIndex if present
                                if isinstance(df.columns, pd.MultiIndex):
                                    df.columns = df.columns.get_level_values(0)
                                
                                # Calculate indicators
                                indicator_calc = WorldClassIndicators()
                                df = indicator_calc.calculate_all(df)
                                
                                if df is not None:
                                    # Detect patterns for direction
                                    config = WorldClassConfig()
                                    pattern_detector = WorldClassPatternDetector(config)
                                    analysis = pattern_detector.detect_all_patterns(df, symbol_yf)
                                    
                                    if analysis:
                                        direction = analysis.get('direction', 'LONG')
                                        option_type = analysis.get('option_type', 'CE')
                                        # Map LONG/SHORT to CE/PE
                                        if direction == 'SHORT':
                                            option_type = 'PE'
                                        elif direction == 'LONG':
                                            option_type = 'CE'
                                        
                                        logger.info(f"World Class Engine: {stock.symbol} → {direction} ({option_type})")
                        except Exception as e:
                            logger.debug(f"World Class direction error for {stock.symbol}: {e}")
                            # Fallback to simple logic
                            direction = "LONG" if stock.change_pct > 0 else "SHORT"
                            option_type = "CE" if stock.change_pct > 0 else "PE"
                    else:
                        # Simple fallback if World Class Engine not available
                        direction = "LONG" if stock.change_pct > 0 else "SHORT"
                        option_type = "CE" if stock.change_pct > 0 else "PE"
                    
                    opportunities.append({
                        "symbol": stock.symbol,
                        "direction": direction,
                        "option_type": option_type,
                        "confidence": confirmation.get("confidence", momentum_score),
                        "rank": len(opportunities) + 1,
                        "current_price": stock.current_price,
                        "change_pct": stock.change_pct,
                        "volume_ratio": stock.volume_ratio,
                        "rsi": stock.rsi,
                        "momentum_type": stock.momentum_type.value if stock.momentum_type else "momentum_surge",
                        "breakout_strength": stock.breakout_strength,
                        "sector": stock.sector,
                        "lot_size": stock.lot_size,
                        "ai_thesis": confirmation.get("thesis", ""),
                        "catalysts": confirmation.get("catalysts", []),
                        "signal_time": datetime.now().isoformat(),
                    })
        
        # Sort by confidence
        opportunities.sort(key=lambda x: x["confidence"], reverse=True)
        
        # Limit to max results
        opportunities = opportunities[:max_results]
        
        # Update rank after sorting
        for i, opp in enumerate(opportunities):
            opp["rank"] = i + 1
        
        # Cache results
        last_scan_results = {
            "opportunities": opportunities,
            "scan_time": datetime.now().isoformat(),
            "total_scanned": len(shortlisted),
            "shortlisted": len(opportunities),
            "capital": capital,
        }
        
        logger.info(f"✅ Scan complete: {len(opportunities)} opportunities found")
        
        return {
            "success": True,
            "opportunities": opportunities,
            "scan_time": last_scan_results["scan_time"],
            "total_scanned": last_scan_results["total_scanned"],
            "shortlisted": last_scan_results["shortlisted"],
        }
        
    except Exception as e:
        logger.error(f"Scan error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/opportunities")
async def get_opportunities(
    min_confidence: float = Query(default=80, description="Minimum confidence"),
    limit: int = Query(default=10, description="Max results"),
):
    """Get cached opportunities from last scan"""
    opportunities = last_scan_results.get("opportunities", [])
    
    # Filter by confidence
    filtered = [o for o in opportunities if o.get("confidence", 0) >= min_confidence]
    
    return {
        "opportunities": filtered[:limit],
        "count": len(filtered),
        "last_scan": last_scan_results.get("scan_time"),
        "total_scanned": last_scan_results.get("total_scanned", 0),
    }


# ============================================================================
# TRADE EXECUTION ENDPOINTS
# ============================================================================

@router.post("/execute")
async def execute_trades(request: ExecuteRequest):
    """
    Execute trades for specified opportunities
    
    This endpoint:
    1. Gets optimal strikes from chain analyzer
    2. Calculates position sizes based on capital
    3. Executes orders via Dhan (or paper trading)
    4. Creates trade records for monitoring
    """
    if not trade_executor_instance:
        raise HTTPException(status_code=503, detail="Trade executor not initialized")
    
    try:
        executed_trades = []
        
        # Get opportunities to execute
        opportunities = last_scan_results.get("opportunities", [])
        
        for symbol in request.symbols:
            # Find opportunity
            opp = next((o for o in opportunities if o["symbol"] == symbol), None)
            
            if not opp:
                logger.warning(f"No opportunity found for {symbol}")
                continue
            
            # Calculate capital
            capital = request.capital_per_trade or (
                scanner_config["available_capital"] / len(request.symbols)
            )
            
            # Execute
            trade = await trade_executor_instance.execute_signal(
                symbol=symbol,
                direction=opp["direction"],
                confidence=opp["confidence"],
                gemini_confirmation=opp.get("ai_thesis", ""),
                available_capital=capital,
                spot_price=opp.get("current_price"),
            )
            
            if trade:
                executed_trades.append(trade.to_dict())
        
        return {
            "success": True,
            "trades_executed": len(executed_trades),
            "trades": executed_trades,
            "paper_trading": request.paper_trading,
        }
        
    except Exception as e:
        logger.error(f"Execution error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/trades")
async def get_active_trades():
    """Get all active trades"""
    if not trade_executor_instance:
        return {"trades": [], "count": 0}
    
    trades = trade_executor_instance.get_active_trades()
    
    return {
        "trades": trades,
        "count": len(trades),
        "timestamp": datetime.now().isoformat(),
    }


@router.get("/trade/{trade_id}")
async def get_trade(trade_id: str):
    """Get specific trade by ID"""
    if not trade_executor_instance:
        raise HTTPException(status_code=503, detail="Trade executor not initialized")
    
    trade = trade_executor_instance.get_trade(trade_id)
    
    if not trade:
        raise HTTPException(status_code=404, detail=f"Trade {trade_id} not found")
    
    return {"trade": trade}


@router.post("/exit/{trade_id}")
async def exit_trade(trade_id: str, request: ExitRequest = None):
    """Manually exit a trade"""
    if not trade_executor_instance:
        raise HTTPException(status_code=503, detail="Trade executor not initialized")
    
    if request is None:
        request = ExitRequest()
    
    try:
        success = await trade_executor_instance.manual_exit(
            trade_id=trade_id,
            reason=request.reason,
        )
        
        if success:
            return {
                "success": True,
                "message": f"Trade {trade_id} exit initiated",
                "reason": request.reason,
            }
        else:
            raise HTTPException(status_code=404, detail=f"Trade {trade_id} not found or already exited")
            
    except Exception as e:
        logger.error(f"Exit error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# STATISTICS & HISTORY ENDPOINTS
# ============================================================================

@router.get("/stats")
async def get_stats():
    """Get trading statistics"""
    if not trade_executor_instance:
        return {
            "stats": {
                "total_trades": 0,
                "winning_trades": 0,
                "losing_trades": 0,
                "win_rate": 0,
                "total_pnl": 0,
                "active_trades": 0,
            }
        }
    
    stats = trade_executor_instance.get_stats()
    
    return {
        "stats": stats,
        "timestamp": datetime.now().isoformat(),
    }


@router.get("/history")
async def get_trade_history(
    limit: int = Query(default=50, description="Max results"),
):
    """Get trade history"""
    if not trade_executor_instance:
        return {"trades": [], "count": 0}
    
    trades = trade_executor_instance.get_trade_history(limit=limit)
    
    return {
        "trades": trades,
        "count": len(trades),
    }


# ============================================================================
# OPTION CHAIN ANALYSIS ENDPOINTS
# ============================================================================

@router.get("/chain/{symbol}")
async def get_chain_analysis(
    symbol: str,
    spot_price: float = Query(default=None, description="Current spot price"),
    capital: float = Query(default=100000, description="Available capital"),
    expiry: str = Query(default=None, description="Expiry date (YYYY-MM-DD)"),
):
    """Get option chain analysis for a symbol"""
    if not chain_analyzer_instance:
        # Try to initialize
        success = await initialize_scanner()
        if not success or not chain_analyzer_instance:
            raise HTTPException(status_code=503, detail="Chain analyzer not initialized")
    
    try:
        analysis = await chain_analyzer_instance.analyze_chain(
            symbol=symbol,
            spot_price=spot_price,
            available_capital=capital,
            expiry=expiry,
        )
        
        if not analysis:
            raise HTTPException(status_code=404, detail=f"No option chain data for {symbol}")
        
        # Format response
        response = {
            "symbol": analysis.symbol,
            "spot_price": analysis.spot_price,
            "expiry": analysis.expiry,
            "atm_strike": analysis.atm_strike,
            "atm_ce_premium": analysis.atm_ce_premium,
            "atm_pe_premium": analysis.atm_pe_premium,
            "pcr": analysis.pcr,
            "iv_skew": analysis.iv_skew,
            "analysis_time": analysis.analysis_time.isoformat(),
        }
        
        # Add recommendations
        if analysis.ce_recommendation:
            response["ce_recommendation"] = {
                "strike": analysis.ce_recommendation.primary_strike.strike,
                "premium": analysis.ce_recommendation.primary_strike.ltp,
                "premium_per_lot": analysis.ce_recommendation.min_capital_required,
                "optimal_lots": analysis.ce_recommendation.optimal_lots,
                "capital_needed": analysis.ce_recommendation.capital_for_optimal,
                "delta": analysis.ce_recommendation.primary_strike.delta,
                "gamma": analysis.ce_recommendation.primary_strike.gamma,
                "liquidity_grade": analysis.ce_recommendation.primary_strike.liquidity_grade.value,
                "momentum_score": analysis.ce_recommendation.primary_strike.momentum_score,
                "selection_reason": analysis.ce_recommendation.selection_reason,
                "risk_notes": analysis.ce_recommendation.risk_notes,
            }
        
        if analysis.pe_recommendation:
            response["pe_recommendation"] = {
                "strike": analysis.pe_recommendation.primary_strike.strike,
                "premium": analysis.pe_recommendation.primary_strike.ltp,
                "premium_per_lot": analysis.pe_recommendation.min_capital_required,
                "optimal_lots": analysis.pe_recommendation.optimal_lots,
                "capital_needed": analysis.pe_recommendation.capital_for_optimal,
                "delta": analysis.pe_recommendation.primary_strike.delta,
                "gamma": analysis.pe_recommendation.primary_strike.gamma,
                "liquidity_grade": analysis.pe_recommendation.primary_strike.liquidity_grade.value,
                "momentum_score": analysis.pe_recommendation.primary_strike.momentum_score,
                "selection_reason": analysis.pe_recommendation.selection_reason,
                "risk_notes": analysis.pe_recommendation.risk_notes,
            }
        
        return response
        
    except Exception as e:
        logger.error(f"Chain analysis error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/chain/{symbol}/recommend")
async def get_strike_recommendation(
    symbol: str,
    request: ChainAnalysisRequest,
):
    """Get recommended strike for a trade"""
    if not chain_analyzer_instance:
        raise HTTPException(status_code=503, detail="Chain analyzer not initialized")
    
    try:
        # Analyze chain
        analysis = await chain_analyzer_instance.analyze_chain(
            symbol=symbol,
            spot_price=request.spot_price,
            available_capital=request.capital,
            expiry=request.expiry,
        )
        
        if not analysis:
            raise HTTPException(status_code=404, detail=f"No data for {symbol}")
        
        return {
            "symbol": symbol,
            "spot_price": analysis.spot_price,
            "ce": chain_analyzer_instance.format_recommendation(analysis.ce_recommendation),
            "pe": chain_analyzer_instance.format_recommendation(analysis.pe_recommendation),
        }
        
    except Exception as e:
        logger.error(f"Recommendation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# MONITORING CONTROL ENDPOINTS
# ============================================================================

@router.post("/monitoring/start")
async def start_monitoring():
    """Start position monitoring"""
    if not trade_executor_instance:
        raise HTTPException(status_code=503, detail="Trade executor not initialized")
    
    await trade_executor_instance.start_monitoring()
    
    return {
        "success": True,
        "message": "Position monitoring started",
    }


@router.post("/monitoring/stop")
async def stop_monitoring():
    """Stop position monitoring"""
    if not trade_executor_instance:
        raise HTTPException(status_code=503, detail="Trade executor not initialized")
    
    trade_executor_instance.is_running = False
    
    return {
        "success": True,
        "message": "Position monitoring stopped",
    }


# ============================================================================
# QUICK ACTIONS
# ============================================================================

@router.post("/quick/scan-and-execute")
async def quick_scan_and_execute(
    max_trades: int = Query(default=3, description="Maximum trades to execute"),
    capital: float = Query(default=100000, description="Total capital"),
    min_confidence: float = Query(default=90, description="Minimum confidence"),
):
    """
    Quick action: Scan and execute top opportunities in one call
    
    This is a convenience endpoint that:
    1. Triggers a market scan
    2. Filters by confidence
    3. Executes top N trades automatically
    """
    try:
        # Scan
        scan_result = await trigger_scan(ScanRequest(
            min_confidence=min_confidence,
            max_results=max_trades * 2,
            capital=capital,
        ))
        
        opportunities = scan_result.get("opportunities", [])
        
        if not opportunities:
            return {
                "success": True,
                "message": "No opportunities found meeting criteria",
                "trades_executed": 0,
            }
        
        # Execute top trades
        symbols = [o["symbol"] for o in opportunities[:max_trades]]
        
        execute_result = await execute_trades(ExecuteRequest(
            symbols=symbols,
            capital_per_trade=capital / len(symbols),
            paper_trading=scanner_config["paper_trading"],
        ))
        
        return {
            "success": True,
            "scan_results": {
                "total_scanned": scan_result.get("total_scanned"),
                "opportunities_found": len(opportunities),
            },
            "execution_results": execute_result,
        }
        
    except Exception as e:
        logger.error(f"Quick action error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/quick/exit-all")
async def quick_exit_all():
    """Emergency exit all active trades"""
    if not trade_executor_instance:
        return {"success": True, "message": "No active trades"}
    
    try:
        trades = trade_executor_instance.get_active_trades()
        exited = 0
        
        for trade in trades:
            success = await trade_executor_instance.manual_exit(
                trade_id=trade["trade_id"],
                reason="emergency_exit",
            )
            if success:
                exited += 1
        
        return {
            "success": True,
            "trades_exited": exited,
            "total_trades": len(trades),
        }
        
    except Exception as e:
        logger.error(f"Exit all error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
