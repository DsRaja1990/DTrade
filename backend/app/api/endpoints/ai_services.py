"""
AI Trading Services Proxy Routes
Routes to proxy requests to our 4 AI trading Windows services:
- Gemini AI Signal Service (port 4080)
- AI Scalping Service (port 4002)
- AI Options Hedger (port 4003)
- Equity Elite Service (port 8003)
"""

import logging
from typing import Optional
import httpx
from fastapi import APIRouter, HTTPException, Query

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/ai-services", tags=["AI Trading Services"])

# Service Endpoints
GEMINI_SERVICE_URL = "http://localhost:4080"
AI_SCALPING_URL = "http://localhost:4002"
AI_HEDGER_URL = "http://localhost:4003"
EQUITY_ELITE_URL = "http://localhost:8003"

# Timeout settings
TIMEOUT = httpx.Timeout(30.0, connect=5.0)

# ============================================================================
# GEMINI AI SIGNAL SERVICE ROUTES
# ============================================================================

@router.get("/gemini/health")
async def gemini_health():
    """Check Gemini AI Signal Service health"""
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            response = await client.get(f"{GEMINI_SERVICE_URL}/health")
            return response.json()
    except httpx.RequestError as e:
        logger.error(f"Gemini service unreachable: {e}")
        raise HTTPException(status_code=503, detail="Gemini AI Service is offline")

@router.get("/gemini/signal/{index}")
async def get_gemini_signal(index: str):
    """Get AI trading signal for an index"""
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(120.0, connect=5.0)) as client:
            response = await client.get(f"{GEMINI_SERVICE_URL}/api/signal/{index}")
            return response.json()
    except httpx.RequestError as e:
        logger.error(f"Failed to get Gemini signal: {e}")
        raise HTTPException(status_code=503, detail="Failed to get AI signal")

@router.get("/gemini/screener/signals")
async def get_screener_signals():
    """Get stock screener signals"""
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            response = await client.get(f"{GEMINI_SERVICE_URL}/api/screener/signals")
            return response.json()
    except httpx.RequestError as e:
        logger.error(f"Failed to get screener signals: {e}")
        raise HTTPException(status_code=503, detail="Failed to get screener signals")

@router.get("/gemini/prediction/{prediction_type}")
async def get_prediction(prediction_type: str):
    """Get AI prediction (5min, momentum, trends, peak)"""
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            response = await client.get(f"{GEMINI_SERVICE_URL}/api/prediction/{prediction_type}")
            return response.json()
    except httpx.RequestError as e:
        logger.error(f"Failed to get prediction: {e}")
        raise HTTPException(status_code=503, detail="Failed to get prediction")

# ============================================================================
# AI SCALPING SERVICE ROUTES
# ============================================================================

@router.get("/scalping/health")
async def scalping_health():
    """Check AI Scalping Service health"""
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            response = await client.get(f"{AI_SCALPING_URL}/health")
            return response.json()
    except httpx.RequestError as e:
        logger.error(f"Scalping service unreachable: {e}")
        raise HTTPException(status_code=503, detail="AI Scalping Service is offline")

@router.get("/scalping/status")
async def scalping_status():
    """Get AI Scalping Service status"""
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            response = await client.get(f"{AI_SCALPING_URL}/status")
            return response.json()
    except httpx.RequestError as e:
        logger.error(f"Failed to get scalping status: {e}")
        raise HTTPException(status_code=503, detail="Failed to get scalping status")

@router.get("/scalping/momentum")
async def scalping_momentum():
    """Get current momentum data"""
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            response = await client.get(f"{AI_SCALPING_URL}/momentum")
            return response.json()
    except httpx.RequestError as e:
        logger.error(f"Failed to get momentum: {e}")
        raise HTTPException(status_code=503, detail="Failed to get momentum data")

@router.get("/scalping/position")
async def scalping_position():
    """Get current position"""
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            response = await client.get(f"{AI_SCALPING_URL}/position")
            return response.json()
    except httpx.RequestError as e:
        logger.error(f"Failed to get position: {e}")
        raise HTTPException(status_code=503, detail="Failed to get position")

@router.get("/scalping/trades")
async def scalping_trades():
    """Get today's trades"""
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            response = await client.get(f"{AI_SCALPING_URL}/trades")
            return response.json()
    except httpx.RequestError as e:
        logger.error(f"Failed to get trades: {e}")
        raise HTTPException(status_code=503, detail="Failed to get trades")

@router.post("/scalping/start")
async def scalping_start():
    """Start AI Scalping"""
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            response = await client.post(f"{AI_SCALPING_URL}/start")
            return response.json()
    except httpx.RequestError as e:
        logger.error(f"Failed to start scalping: {e}")
        raise HTTPException(status_code=503, detail="Failed to start scalping")

@router.post("/scalping/stop")
async def scalping_stop():
    """Stop AI Scalping"""
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            response = await client.post(f"{AI_SCALPING_URL}/stop")
            return response.json()
    except httpx.RequestError as e:
        logger.error(f"Failed to stop scalping: {e}")
        raise HTTPException(status_code=503, detail="Failed to stop scalping")

# ============================================================================
# AI OPTIONS HEDGER SERVICE ROUTES
# ============================================================================

@router.get("/hedger/health")
async def hedger_health():
    """Check AI Options Hedger Service health"""
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            response = await client.get(f"{AI_HEDGER_URL}/health")
            return response.json()
    except httpx.RequestError as e:
        logger.error(f"Hedger service unreachable: {e}")
        raise HTTPException(status_code=503, detail="AI Options Hedger is offline")

@router.get("/hedger/status")
async def hedger_status():
    """Get AI Options Hedger status"""
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            response = await client.get(f"{AI_HEDGER_URL}/status")
            return response.json()
    except httpx.RequestError as e:
        logger.error(f"Failed to get hedger status: {e}")
        raise HTTPException(status_code=503, detail="Failed to get hedger status")

@router.get("/hedger/positions")
async def hedger_positions():
    """Get current positions"""
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            response = await client.get(f"{AI_HEDGER_URL}/positions")
            return response.json()
    except httpx.RequestError as e:
        logger.error(f"Failed to get positions: {e}")
        raise HTTPException(status_code=503, detail="Failed to get positions")

@router.get("/hedger/signals")
async def hedger_signals():
    """Get recent signals"""
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            response = await client.get(f"{AI_HEDGER_URL}/signals")
            return response.json()
    except httpx.RequestError as e:
        logger.error(f"Failed to get signals: {e}")
        raise HTTPException(status_code=503, detail="Failed to get signals")

@router.get("/hedger/trades/today")
async def hedger_trades_today():
    """Get today's trades"""
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            response = await client.get(f"{AI_HEDGER_URL}/trades/today")
            return response.json()
    except httpx.RequestError as e:
        logger.error(f"Failed to get today's trades: {e}")
        raise HTTPException(status_code=503, detail="Failed to get trades")

@router.get("/hedger/daily-summary")
async def hedger_daily_summary():
    """Get daily summary"""
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            response = await client.get(f"{AI_HEDGER_URL}/daily-summary")
            return response.json()
    except httpx.RequestError as e:
        logger.error(f"Failed to get daily summary: {e}")
        raise HTTPException(status_code=503, detail="Failed to get daily summary")

@router.post("/hedger/trading-mode")
async def hedger_set_trading_mode(mode: str = Query(..., description="Trading mode: paper or live")):
    """Set trading mode"""
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            response = await client.post(f"{AI_HEDGER_URL}/trading-mode", json={"mode": mode})
            return response.json()
    except httpx.RequestError as e:
        logger.error(f"Failed to set trading mode: {e}")
        raise HTTPException(status_code=503, detail="Failed to set trading mode")

@router.post("/hedger/exit-all")
async def hedger_exit_all():
    """Exit all positions"""
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            response = await client.post(f"{AI_HEDGER_URL}/exit-all")
            return response.json()
    except httpx.RequestError as e:
        logger.error(f"Failed to exit all: {e}")
        raise HTTPException(status_code=503, detail="Failed to exit all positions")

# ============================================================================
# EQUITY ELITE SERVICE ROUTES
# ============================================================================

@router.get("/equity-elite/health")
async def elite_health():
    """Check Equity Elite Service health"""
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            response = await client.get(f"{EQUITY_ELITE_URL}/health")
            return response.json()
    except httpx.RequestError as e:
        logger.error(f"Equity Elite service unreachable: {e}")
        raise HTTPException(status_code=503, detail="Equity Elite Service is offline")

@router.get("/equity-elite/status")
async def elite_status():
    """Get Equity Elite status"""
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            response = await client.get(f"{EQUITY_ELITE_URL}/status")
            return response.json()
    except httpx.RequestError as e:
        logger.error(f"Failed to get elite status: {e}")
        raise HTTPException(status_code=503, detail="Failed to get elite status")

@router.post("/equity-elite/trading/start")
async def elite_start(mode: str = Query("paper", description="Trading mode: paper or live")):
    """Start Equity Elite trading"""
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            response = await client.post(f"{EQUITY_ELITE_URL}/api/trading/start", json={"mode": mode})
            return response.json()
    except httpx.RequestError as e:
        logger.error(f"Failed to start elite trading: {e}")
        raise HTTPException(status_code=503, detail="Failed to start trading")

@router.post("/equity-elite/trading/stop")
async def elite_stop(mode: str = Query("paper", description="Trading mode: paper or live")):
    """Stop Equity Elite trading"""
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            response = await client.post(f"{EQUITY_ELITE_URL}/api/trading/stop", json={"mode": mode})
            return response.json()
    except httpx.RequestError as e:
        logger.error(f"Failed to stop elite trading: {e}")
        raise HTTPException(status_code=503, detail="Failed to stop trading")

# ============================================================================
# AGGREGATE STATUS ENDPOINT
# ============================================================================

@router.get("/status/all")
async def all_services_status():
    """Get status of all AI trading services"""
    results = {
        "gemini_ai": {"status": "offline", "port": 4080},
        "ai_scalping": {"status": "offline", "port": 4002},
        "ai_hedger": {"status": "offline", "port": 4003},
        "equity_elite": {"status": "offline", "port": 8003},
    }
    
    async with httpx.AsyncClient(timeout=httpx.Timeout(5.0, connect=2.0)) as client:
        # Check Gemini
        try:
            resp = await client.get(f"{GEMINI_SERVICE_URL}/health")
            if resp.status_code == 200:
                results["gemini_ai"] = {"status": "healthy", "port": 4080, "data": resp.json()}
        except:
            pass
        
        # Check Scalping
        try:
            resp = await client.get(f"{AI_SCALPING_URL}/health")
            if resp.status_code == 200:
                results["ai_scalping"] = {"status": "healthy", "port": 4002, "data": resp.json()}
        except:
            pass
        
        # Check Hedger
        try:
            resp = await client.get(f"{AI_HEDGER_URL}/health")
            if resp.status_code == 200:
                results["ai_hedger"] = {"status": "healthy", "port": 4003, "data": resp.json()}
        except:
            pass
        
        # Check Elite
        try:
            resp = await client.get(f"{EQUITY_ELITE_URL}/health")
            if resp.status_code == 200:
                results["equity_elite"] = {"status": "healthy", "port": 8003, "data": resp.json()}
        except:
            pass
    
    return results
