"""
Admin endpoints for user management and system administration
"""
from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime, timedelta
from typing import List, Optional
from pydantic import BaseModel

from ...core.database import get_db
from ...models.user import User, UserRole, UserStatus
from ..endpoints.auth import get_current_user

router = APIRouter()

class AdminUserResponse(BaseModel):
    id: int
    username: str
    email: str
    full_name: Optional[str]
    role: str
    status: str
    trading_enabled: bool
    ai_trading_enabled: bool
    created_at: datetime
    last_login: Optional[datetime]
    last_trade_at: Optional[datetime]

class SystemStats(BaseModel):
    total_users: int
    active_users: int
    total_trades_today: int
    system_uptime: str
    api_response_time: float

def require_admin(current_user: User = Depends(get_current_user)):
    """Dependency to ensure user has admin role"""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user

@router.get("/users", response_model=List[AdminUserResponse])
async def get_all_users(
    skip: int = 0,
    limit: int = 100,
    status_filter: Optional[str] = None,
    admin_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """Get all users (admin only)"""
    
    query = select(User)
    
    if status_filter:
        query = query.where(User.status == UserStatus(status_filter))
    
    query = query.offset(skip).limit(limit).order_by(User.created_at.desc())
    
    result = await db.execute(query)
    users = result.scalars().all()
    
    return [
        AdminUserResponse(
            id=user.id,
            username=user.username,
            email=user.email,
            full_name=user.full_name,
            role=user.role.value,
            status=user.status.value,
            trading_enabled=user.trading_enabled,
            ai_trading_enabled=user.ai_trading_enabled,
            created_at=user.created_at,
            last_login=user.last_login,
            last_trade_at=user.last_trade_at
        )
        for user in users
    ]

@router.put("/users/{user_id}/status")
async def update_user_status(
    user_id: int,
    new_status: str,
    admin_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """Update user status (admin only)"""
    
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    try:
        user.status = UserStatus(new_status)
        user.updated_at = datetime.utcnow()
        await db.commit()
        
        return {
            "message": f"User status updated to {new_status}",
            "user_id": user_id,
            "new_status": new_status
        }
    
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid status value"
        )

@router.put("/users/{user_id}/trading")
async def toggle_trading_access(
    user_id: int,
    enable_trading: bool,
    admin_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """Enable/disable trading for a user (admin only)"""
    
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    user.trading_enabled = enable_trading
    user.updated_at = datetime.utcnow()
    await db.commit()
    
    return {
        "message": f"Trading {'enabled' if enable_trading else 'disabled'} for user",
        "user_id": user_id,
        "trading_enabled": enable_trading
    }

@router.put("/users/{user_id}/ai-trading")
async def toggle_ai_trading_access(
    user_id: int,
    enable_ai_trading: bool,
    admin_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """Enable/disable AI trading for a user (admin only)"""
    
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    user.ai_trading_enabled = enable_ai_trading
    user.updated_at = datetime.utcnow()
    await db.commit()
    
    return {
        "message": f"AI trading {'enabled' if enable_ai_trading else 'disabled'} for user",
        "user_id": user_id,
        "ai_trading_enabled": enable_ai_trading
    }

@router.get("/system-stats", response_model=SystemStats)
async def get_system_stats(
    admin_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """Get system statistics (admin only)"""
    
    # Get total users
    total_users_result = await db.execute(select(func.count(User.id)))
    total_users = total_users_result.scalar() or 0
    
    # Get active users (logged in within last 24 hours)
    yesterday = datetime.utcnow() - timedelta(hours=24)
    active_users_result = await db.execute(
        select(func.count(User.id)).where(User.last_login >= yesterday)
    )
    active_users = active_users_result.scalar() or 0
    
    # Mock other stats
    return SystemStats(
        total_users=total_users,
        active_users=active_users,
        total_trades_today=150,  # Mock data
        system_uptime="5 days, 12 hours",  # Mock data
        api_response_time=85.5  # Mock data in ms
    )

@router.get("/audit-logs")
async def get_audit_logs(
    limit: int = 100,
    admin_user: User = Depends(require_admin)
):
    """Get system audit logs (admin only)"""
    
    # Mock audit logs - in real implementation, this would come from logging system
    return [
        {
            "timestamp": "2025-01-01T10:30:00Z",
            "user_id": 123,
            "action": "user_login",
            "details": "User logged in from IP 192.168.1.100",
            "severity": "info"
        },
        {
            "timestamp": "2025-01-01T10:25:00Z",
            "user_id": 456,
            "action": "order_placed",
            "details": "NIFTY CE order placed for quantity 100",
            "severity": "info"
        },
        {
            "timestamp": "2025-01-01T10:20:00Z",
            "user_id": 789,
            "action": "login_failed",
            "details": "Failed login attempt from IP 203.124.45.67",
            "severity": "warning"
        }
    ]

@router.post("/maintenance-mode")
async def toggle_maintenance_mode(
    enable: bool,
    admin_user: User = Depends(require_admin)
):
    """Enable/disable maintenance mode (admin only)"""
    
    # In real implementation, this would update a configuration flag
    # that other parts of the system would check
    
    return {
        "message": f"Maintenance mode {'enabled' if enable else 'disabled'}",
        "maintenance_mode": enable,
        "timestamp": datetime.utcnow()
    }

@router.post("/broadcast-message")
async def broadcast_system_message(
    message: str,
    message_type: str = "info",
    admin_user: User = Depends(require_admin)
):
    """Broadcast a system message to all users (admin only)"""
    
    # In real implementation, this would send the message via WebSocket
    # to all connected users
    
    return {
        "message": "System message broadcasted successfully",
        "broadcast_message": message,
        "message_type": message_type,
        "timestamp": datetime.utcnow()
    }
