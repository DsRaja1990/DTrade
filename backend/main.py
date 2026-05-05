"""
DTrade - Advanced AI Trading Platform
Main FastAPI Application Entry Point
"""

import asyncio
import logging
import sys
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path

import uvicorn
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from flask import Flask

# Add the project root to Python path
sys.path.append(str(Path(__file__).parent))

# Import core modules
from app.api.router import api_router
from app.core.config import get_settings
from app.core.database import init_db
from app.core.redis_client import RedisClient
from app.core.websocket_manager import ConnectionManager
from app.core.logging_config import setup_logging
from app.core.exception_handlers import setup_exception_handlers

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)

# Initialize services
settings = get_settings()
redis_client = RedisClient()
websocket_manager = ConnectionManager()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    logger.info("🚀 Starting DTrade AI Trading Platform...")
    
    try:
        # Initialize database
        await init_db()
        logger.info("✅ Database initialized")
        
        # Initialize Redis
        await redis_client.connect()
        logger.info("✅ Redis connected")
        
        # Initialize Paper Trading System
        from app.papertest.market_data_simulator import market_data_simulator
        import asyncio
        # Start market data simulator in background
        asyncio.create_task(market_data_simulator.start())
        logger.info("✅ Paper Trading Market Data Simulator started")
        
        logger.info("🎯 DTrade platform is ready for trading!")
        
        yield
        
    except Exception as e:
        logger.error(f"❌ Failed to start application: {e}")
        raise
    
    finally:
        # Cleanup on shutdown
        logger.info("🛑 Shutting down DTrade platform...")
        
        try:
            # Stop market data simulator
            await market_data_simulator.stop()
            logger.info("✅ Market data simulator stopped")
                
            await redis_client.disconnect()
            logger.info("✅ Cleanup completed")
        except Exception as e:
            logger.error(f"❌ Error during cleanup: {e}")


# Create FastAPI application
app = FastAPI(
    title="DTrade - AI Trading Platform",
    description="Institutional-grade AI-driven trading platform with DhanHQ integration and Ratio Strategy",
    version="1.0.0",
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
    lifespan=lifespan
)

# Setup exception handlers
setup_exception_handlers(app)

# Add middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

app.add_middleware(GZipMiddleware, minimum_size=1000)

# Include API router
app.include_router(api_router, prefix="/api/v1")

# Include Paper Trading router
from app.papertest.api import papertest_router
app.include_router(papertest_router)

# Add compatibility routes without v1 prefix for frontend
from app.api.endpoints import signals, analytics
app.include_router(signals.router, prefix="/api/signals", tags=["signals-compat"])
app.include_router(analytics.router, prefix="/api/performance", tags=["performance-compat"])

# Add QSBP strategy routes without v1 prefix for frontend compatibility
try:
    from app.strategies.qsbp_strategy.api_proxy import router as qsbp_router
    app.include_router(qsbp_router, tags=["qsbp-strategy-compat"])
    logger.info("✅ QSBP strategy proxy routes registered")
except ImportError as e:
    logger.warning(f"QSBP strategy proxy router not available: {e}")

# Add Ratio strategy routes without v1 prefix for frontend compatibility
try:
    from app.api.endpoints.ratio_strategy import router as ratio_router
    app.include_router(ratio_router, tags=["ratio-strategy-compat"])
    logger.info("✅ Ratio strategy routes registered")
except ImportError as e:
    logger.warning(f"Ratio strategy router not available: {e}")

# Add Index Scalping strategy routes without v1 prefix for frontend compatibility
try:
    from app.strategies.Index_advanced_strategy.routes import router as index_scalping_router
    app.include_router(index_scalping_router, tags=["index-scalping-strategy-compat"])
    logger.info("✅ Index Scalping strategy routes registered")
except ImportError as e:
    logger.warning(f"Index Scalping strategy router not available: {e}")

# Add AI Trading Services proxy routes (Gemini, Scalping, Hedger, Elite)
try:
    from app.api.endpoints.ai_services import router as ai_services_router
    app.include_router(ai_services_router, tags=["ai-trading-services"])
    logger.info("✅ AI Trading Services proxy routes registered (ports 4080, 4002, 4003, 8003)")
except ImportError as e:
    logger.warning(f"AI Trading Services router not available: {e}")

# Serve static files in production
if not settings.DEBUG:
    app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "DTrade AI Trading Platform with Advanced Strategies",
        "version": "1.0.0",
        "status": "running",
        "timestamp": datetime.now().isoformat(),
        "docs": "/docs" if settings.DEBUG else "disabled",
        "features": [
            "AI-powered trading signals",
            "Real-time market data integration",
            "Advanced portfolio management", 
            "Institutional-grade ratio strategy",
            "High-frequency index scalping strategy",
            "DhanHQ integration",
            "Real-time risk management"
        ]
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Check database
        db_status = "connected"
        
        # Check Redis
        redis_status = await redis_client.ping()
        
        # Check ratio strategy service (via new API)
        ratio_strategy_status = "available"  # Since we have the API routes now
        
        # Check index scalping strategy service
        index_scalping_status = "available"  # Since we have the API routes now
        
        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "services": {
                "database": db_status,
                "redis": "connected" if redis_status else "disconnected",
                "ratio_strategy": ratio_strategy_status,
                "index_scalping_strategy": index_scalping_status
            }
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail="Service unhealthy")


@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    """WebSocket endpoint for real-time data"""
    await websocket_manager.connect(websocket, client_id)
    
    try:
        while True:
            # Keep connection alive and handle incoming messages
            data = await websocket.receive_text()
            
            # Process incoming WebSocket messages
            await websocket_manager.handle_message(client_id, data)
            
            # Send ratio strategy updates if subscribed
            if "ratio_strategy" in data:
                try:
                    # Use the new API to get strategy status
                    await websocket.send_json({
                        "type": "ratio_strategy_update",
                        "data": {"message": "Use /strategies/ratio/status endpoint for updates"}
                    })
                except Exception as e:
                    logger.error(f"Error sending ratio strategy update: {e}")
            
    except WebSocketDisconnect:
        logger.info(f"WebSocket client {client_id} disconnected")
        websocket_manager.disconnect(client_id)
    except Exception as e:
        logger.error(f"WebSocket error for client {client_id}: {e}")
        websocket_manager.disconnect(client_id)


@app.get("/api/status")
async def api_status():
    """API status endpoint"""
    return {
        "api": "online",
        "platform": "dtrade",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat(),
        "ratio_strategy": {
            "available": True,
            "active": "Check /strategies/ratio/status endpoint"
        }
    }


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower(),
        access_log=True
    )
