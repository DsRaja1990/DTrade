"""
Ratio Strategy API Endpoints for Backend Integration
Real-time integration between frontend toggle and ratio service
"""

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from fastapi.responses import StreamingResponse
from typing import Dict, List, Optional, Any
from datetime import datetime
import asyncio
import json
import httpx
import logging
from pydantic import BaseModel

from ...core.database import get_db
from ...models.user import User
from ..endpoints.auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter()

# Pydantic models for requests/responses
class RatioStrategyConfig(BaseModel):
    enabled: bool
    execution_mode: str  # "paper" or "live"
    capital: float = 1000000
    max_daily_loss: float = 50000
    nifty_lots: int = 20
    banknifty_lots: int = 30
    sensex_lots: int = 50
    dhan_access_token: Optional[str] = None

class RatioServiceResponse(BaseModel):
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None

class RatioServiceClient:
    """Client for communicating with ratio service"""
    
    def __init__(self, service_url: str = "http://localhost:8002"):
        self.service_url = service_url.rstrip('/')
        self.timeout = httpx.Timeout(30.0)
        
    async def check_health(self) -> bool:
        """Check if ratio service is healthy"""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.service_url}/health")
                if response.status_code == 200:
                    data = response.json()
                    return data.get("status") == "healthy"
                return False
        except Exception as e:
            logger.warning(f"Ratio service health check failed: {e}")
            return False
    
    async def start_strategy(self, config: RatioStrategyConfig) -> Dict[str, Any]:
        """Start ratio strategy on service"""
        try:
            # Configure DHAN credentials if provided
            if config.dhan_access_token:
                await self.configure_dhan(config.dhan_access_token)
            
            # Update quantities
            await self.update_quantities({
                "NIFTY": config.nifty_lots,
                "BANKNIFTY": config.banknifty_lots,
                "SENSEX": config.sensex_lots
            })
            
            # Start the engine
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.service_url}/start/{config.execution_mode}",
                    json={
                        "capital": config.capital,
                        "max_daily_loss": config.max_daily_loss
                    }
                )
                response.raise_for_status()
                return response.json()
                
        except httpx.ConnectError:
            raise HTTPException(
                status_code=503,
                detail="Cannot connect to ratio service. Please ensure the service is running."
            )
        except httpx.HTTPStatusError as e:
            raise HTTPException(
                status_code=e.response.status_code,
                detail=f"Ratio service error: {e.response.text}"
            )
    
    async def stop_strategy(self, execution_mode: str) -> Dict[str, Any]:
        """Stop ratio strategy on service"""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(f"{self.service_url}/stop/{execution_mode}")
                response.raise_for_status()
                return response.json()
                
        except httpx.ConnectError:
            raise HTTPException(
                status_code=503,
                detail="Cannot connect to ratio service"
            )
    
    async def get_status(self, execution_mode: str) -> Dict[str, Any]:
        """Get strategy status from service"""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(f"{self.service_url}/status/{execution_mode}")
                response.raise_for_status()
                return response.json()
                
        except httpx.ConnectError:
            return {
                "success": False,
                "message": "Ratio service not available",
                "data": {"status": "service_unavailable", "is_running": False}
            }
    
    async def configure_dhan(self, access_token: str) -> Dict[str, Any]:
        """Configure DHAN credentials"""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.service_url}/dhan/configure",
                    json={"access_token": access_token}
                )
                response.raise_for_status()
                return response.json()
        except Exception as e:
            logger.error(f"Error configuring DHAN: {e}")
            return {"success": False, "message": str(e)}
    
    async def update_quantities(self, quantities: Dict[str, int]) -> Dict[str, Any]:
        """Update trading quantities"""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.service_url}/quantities/update",
                    json=quantities
                )
                response.raise_for_status()
                return response.json()
        except Exception as e:
            logger.error(f"Error updating quantities: {e}")
            return {"success": False, "message": str(e)}
    
    async def execute_signal(self, execution_mode: str, signal_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute trading signal"""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.service_url}/execute/{execution_mode}",
                    json=signal_data
                )
                response.raise_for_status()
                return response.json()
        except Exception as e:
            logger.error(f"Error executing signal: {e}")
            return {"success": False, "message": str(e)}
    
    async def get_dark_pool_analysis(self, execution_mode: str, symbols: str = "NIFTY,BANKNIFTY,SENSEX") -> Dict[str, Any]:
        """Get dark pool analysis"""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.service_url}/dark-pool/{execution_mode}",
                    params={"symbols": symbols}
                )
                response.raise_for_status()
                return response.json()
        except Exception as e:
            logger.error(f"Error getting dark pool analysis: {e}")
            return {"success": False, "message": str(e)}
    
    async def get_technical_indicators(self, execution_mode: str) -> Dict[str, Any]:
        """Get technical indicators"""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(f"{self.service_url}/technical-indicators/{execution_mode}")
                response.raise_for_status()
                return response.json()
        except Exception as e:
            logger.error(f"Error getting technical indicators: {e}")
            return {"success": False, "message": str(e)}

# Global service client
ratio_service_client = RatioServiceClient()

# API Endpoints

@router.get("/ratio/health")
async def check_ratio_service_health():
    """Check ratio service health"""
    is_healthy = await ratio_service_client.check_health()
    return {
        "service": "ratio",
        "healthy": is_healthy,
        "timestamp": datetime.now().isoformat()
    }

@router.post("/ratio/toggle", response_model=RatioServiceResponse)
async def toggle_ratio_strategy(
    config: RatioStrategyConfig,
    current_user: User = Depends(get_current_user)
):
    """
    Toggle ratio strategy on/off from frontend
    This is the main endpoint triggered by the frontend strategy page
    """
    try:
        logger.info(f"User {current_user.email} toggling ratio strategy: {config.enabled}")
        
        # Check service health first
        if not await ratio_service_client.check_health():
            raise HTTPException(
                status_code=503,
                detail="Ratio service is not available. Please check if the service is running."
            )
        
        if config.enabled:
            # Start strategy
            result = await ratio_service_client.start_strategy(config)
            
            # Log the activation
            logger.info(f"Ratio strategy started for user {current_user.email}: {result}")
            
            return RatioServiceResponse(
                success=True,
                message="Ratio strategy started successfully",
                data={
                    "status": "started",
                    "execution_mode": config.execution_mode,
                    "service_response": result
                }
            )
        else:
            # Stop strategy
            result = await ratio_service_client.stop_strategy(config.execution_mode)
            
            # Log the deactivation
            logger.info(f"Ratio strategy stopped for user {current_user.email}: {result}")
            
            return RatioServiceResponse(
                success=True,
                message="Ratio strategy stopped successfully",
                data={
                    "status": "stopped",
                    "execution_mode": config.execution_mode,
                    "service_response": result
                }
            )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error toggling ratio strategy: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/ratio/status/{execution_mode}")
async def get_ratio_strategy_status(
    execution_mode: str,
    current_user: User = Depends(get_current_user)
):
    """Get current status of ratio strategy"""
    try:
        status = await ratio_service_client.get_status(execution_mode)
        return {
            "success": True,
            "execution_mode": execution_mode,
            "status": status,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting ratio strategy status: {e}")
        return {
            "success": False,
            "message": str(e),
            "status": {"is_running": False}
        }

@router.post("/ratio/signal/{execution_mode}")
async def execute_ratio_signal(
    execution_mode: str,
    signal_data: Dict[str, Any],
    current_user: User = Depends(get_current_user)
):
    """Execute a trading signal on ratio strategy"""
    try:
        logger.info(f"Executing ratio signal for user {current_user.email}: {signal_data}")
        
        result = await ratio_service_client.execute_signal(execution_mode, signal_data)
        
        return {
            "success": True,
            "message": "Signal executed successfully",
            "execution_mode": execution_mode,
            "result": result,
            "timestamp": datetime.now().isoformat()
        }
    
    except Exception as e:
        logger.error(f"Error executing ratio signal: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/ratio/dark-pool/{execution_mode}")
async def get_dark_pool_analysis(
    execution_mode: str,
    symbols: str = "NIFTY,BANKNIFTY,SENSEX",
    current_user: User = Depends(get_current_user)
):
    """Get dark pool analysis for symbols"""
    try:
        analysis = await ratio_service_client.get_dark_pool_analysis(execution_mode, symbols)
        return {
            "success": True,
            "analysis": analysis,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting dark pool analysis: {e}")
        return {"success": False, "message": str(e)}

@router.get("/ratio/technical-indicators/{execution_mode}")
async def get_technical_indicators(
    execution_mode: str,
    current_user: User = Depends(get_current_user)
):
    """Get technical indicators from ratio service"""
    try:
        indicators = await ratio_service_client.get_technical_indicators(execution_mode)
        return {
            "success": True,
            "indicators": indicators,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting technical indicators: {e}")
        return {"success": False, "message": str(e)}

@router.post("/ratio/quantities/update")
async def update_trading_quantities(
    quantities: Dict[str, int],
    current_user: User = Depends(get_current_user)
):
    """Update trading quantities for ratio strategy"""
    try:
        result = await ratio_service_client.update_quantities(quantities)
        
        logger.info(f"Updated quantities for user {current_user.email}: {quantities}")
        
        return {
            "success": True,
            "message": "Trading quantities updated successfully",
            "quantities": quantities,
            "result": result,
            "timestamp": datetime.now().isoformat()
        }
    
    except Exception as e:
        logger.error(f"Error updating quantities: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/ratio/live-stream/{execution_mode}")
async def ratio_live_stream(
    execution_mode: str,
    current_user: User = Depends(get_current_user)
):
    """
    Server-sent events stream for real-time ratio strategy updates
    """
    async def event_stream():
        """Generate real-time events"""
        try:
            while True:
                # Get current status
                status = await ratio_service_client.get_status(execution_mode)
                
                # Get technical indicators
                indicators = await ratio_service_client.get_technical_indicators(execution_mode)
                
                # Get dark pool analysis
                dark_pool = await ratio_service_client.get_dark_pool_analysis(execution_mode)
                
                # Combine all data
                combined_data = {
                    "timestamp": datetime.now().isoformat(),
                    "execution_mode": execution_mode,
                    "status": status,
                    "indicators": indicators,
                    "dark_pool": dark_pool
                }
                
                yield f"data: {json.dumps(combined_data)}\n\n"
                
                # Wait before next update
                await asyncio.sleep(5)  # 5-second updates
                
        except Exception as e:
            logger.error(f"Error in ratio live stream: {e}")
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
    
    return StreamingResponse(
        event_stream(),
        media_type="text/plain",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Content-Type": "text/event-stream"
        }
    )

@router.post("/ratio/configure")
async def configure_ratio_strategy(
    config: Dict[str, Any],
    current_user: User = Depends(get_current_user)
):
    """Configure ratio strategy parameters"""
    try:
        # Configure quantities if provided
        if "quantities" in config:
            await ratio_service_client.update_quantities(config["quantities"])
        
        # Configure DHAN if provided
        if "dhan_access_token" in config:
            await ratio_service_client.configure_dhan(config["dhan_access_token"])
        
        logger.info(f"Configured ratio strategy for user {current_user.email}: {config}")
        
        return {
            "success": True,
            "message": "Ratio strategy configured successfully",
            "config": config,
            "timestamp": datetime.now().isoformat()
        }
    
    except Exception as e:
        logger.error(f"Error configuring ratio strategy: {e}")
        raise HTTPException(status_code=500, detail=str(e))
