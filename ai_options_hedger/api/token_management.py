"""
Token Management API Endpoint
Provides endpoint for manual daily Dhan token updates
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/token", tags=["token"])

class TokenUpdate(BaseModel):
    """Token update request model"""
    dhan_access_token: str

@router.post("/update")
async def update_dhan_token(token_update: TokenUpdate):
    """
    Update Dhan access token (manual daily update)
    
    Args:
        token_update: New Dhan access token
    
    Returns:
        Success/failure status
    """
    try:
        # Path to dhan_config.json
        config_path = Path(__file__).parent.parent / "dhan_config.json"
        
        # Read current config
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        # Update token
        old_token = config.get('dhan_access_token', '')[:50] + "..."  # Log first 50 chars only
        config['dhan_access_token'] = token_update.dhan_access_token
        
        # Write updated config
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)
        
        logger.info(f"Dhan token updated successfully. Old: {old_token}")
        
        return {
            "status": "success",
            "message": "Dhan access token updated successfully",
            "timestamp": str(Path(config_path).stat().st_mtime)
        }
    
    except FileNotFoundError:
        logger.error(f"Config file not found: {config_path}")
        raise HTTPException(
            status_code=404,
            detail="Dhan config file not found"
        )
    
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in config file: {e}")
        raise HTTPException(
            status_code=500,
            detail="Invalid JSON in config file"
        )
    
    except Exception as e:
        logger.error(f"Error updating Dhan token: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update token: {str(e)}"
        )

@router.get("/status")
async def get_token_status():
    """
    Get current token status (without exposing full token)
    
    Returns:
        Token status information
    """
    try:
        config_path = Path(__file__).parent.parent / "dhan_config.json"
        
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        token = config.get('dhan_access_token', '')
        
        # Extract token metadata (JWT)
        import base64
        try:
            # JWT format: header.payload.signature
            parts = token.split('.')
            if len(parts) == 3:
                # Decode payload (add padding if needed)
                payload = parts[1]
                payload += '=' * (4 - len(payload) % 4)
                decoded = base64.b64decode(payload).decode('utf-8')
                payload_data = json.loads(decoded)
                
                exp_timestamp = payload_data.get('exp', 0)
                iat_timestamp = payload_data.get('iat', 0)
                
                from datetime import datetime
                exp_date = datetime.fromtimestamp(exp_timestamp) if exp_timestamp else None
                iat_date = datetime.fromtimestamp(iat_timestamp) if iat_timestamp else None
                
                return {
                    "status": "success",
                    "token_prefix": token[:30] + "...",
                    "issued_at": str(iat_date) if iat_date else "Unknown",
                    "expires_at": str(exp_date) if exp_date else "Unknown",
                    "is_expired": datetime.now().timestamp() > exp_timestamp if exp_timestamp else False,
                    "client_id": payload_data.get('dhanClientId', 'Unknown')
                }
        except Exception as e:
            logger.warning(f"Could not decode token: {e}")
        
        return {
            "status": "success",
            "token_prefix": token[:30] + "..." if token else "No token",
            "has_token": bool(token)
        }
    
    except Exception as e:
        logger.error(f"Error getting token status: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get token status: {str(e)}"
        )
