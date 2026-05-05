"""
Equity HV Service API Router
Basic strategy endpoints
"""

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from typing import List, Dict, Any, Optional
import logging
from datetime import datetime
import pytz

logger = logging.getLogger(__name__)
INDIAN_TZ = pytz.timezone('Asia/Kolkata')

router = APIRouter(tags=["strategy"])


# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                pass


manager = ConnectionManager()


@router.get("/status")
async def get_strategy_status():
    """Get current strategy status"""
    return {
        "status": "ready",
        "timestamp": datetime.now(INDIAN_TZ).isoformat(),
        "message": "Strategy router active - Use /api/auto-trader for trading operations"
    }


@router.get("/market-hours")
async def check_market_hours():
    """Check if market is open"""
    now = datetime.now(INDIAN_TZ)
    
    # Market hours: 9:15 AM to 3:30 PM IST, Monday to Friday
    is_weekday = now.weekday() < 5
    market_open = now.replace(hour=9, minute=15, second=0, microsecond=0)
    market_close = now.replace(hour=15, minute=30, second=0, microsecond=0)
    
    is_market_hours = is_weekday and market_open <= now <= market_close
    
    return {
        "is_market_open": is_market_hours,
        "current_time": now.isoformat(),
        "market_open_time": "09:15 IST",
        "market_close_time": "15:30 IST",
        "is_weekday": is_weekday
    }


@router.websocket("/ws/signals")
async def websocket_signals(websocket: WebSocket):
    """WebSocket for real-time signal updates"""
    await manager.connect(websocket)
    try:
        while True:
            # Wait for messages or keep connection alive
            data = await websocket.receive_text()
            # Echo back for now
            await websocket.send_json({"received": data, "timestamp": datetime.now().isoformat()})
    except WebSocketDisconnect:
        manager.disconnect(websocket)
