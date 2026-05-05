"""
User management endpoints
"""
from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr

from ...core.database import get_db
from ...models.user import User, UserRole, UserStatus
from ..endpoints.auth import get_current_user

router = APIRouter()

class UserUpdateRequest(BaseModel):
    full_name: Optional[str] = None
    phone: Optional[str] = None
    risk_tolerance: Optional[str] = None
    max_daily_loss: Optional[int] = None
    max_position_size: Optional[int] = None
    max_open_positions: Optional[int] = None
    ai_trading_enabled: Optional[bool] = None

class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    full_name: Optional[str]
    phone: Optional[str]
    role: str
    status: str
    trading_enabled: bool
    ai_trading_enabled: bool
    risk_tolerance: str
    max_daily_loss: int
    max_position_size: int
    max_open_positions: int
    created_at: datetime
    last_login: Optional[datetime]

@router.get("/profile", response_model=UserResponse)
async def get_user_profile(current_user: User = Depends(get_current_user)):
    """Get current user profile"""
    
    return UserResponse(
        id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        full_name=current_user.full_name,
        phone=current_user.phone,
        role=current_user.role.value,
        status=current_user.status.value,
        trading_enabled=current_user.trading_enabled,
        ai_trading_enabled=current_user.ai_trading_enabled,
        risk_tolerance=current_user.risk_tolerance,
        max_daily_loss=current_user.max_daily_loss,
        max_position_size=current_user.max_position_size,
        max_open_positions=current_user.max_open_positions,
        created_at=current_user.created_at,
        last_login=current_user.last_login
    )

@router.put("/profile", response_model=UserResponse)
async def update_user_profile(
    update_data: UserUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update user profile"""
    
    # Update user fields
    if update_data.full_name is not None:
        current_user.full_name = update_data.full_name
    if update_data.phone is not None:
        current_user.phone = update_data.phone
    if update_data.risk_tolerance is not None:
        current_user.risk_tolerance = update_data.risk_tolerance
    if update_data.max_daily_loss is not None:
        current_user.max_daily_loss = update_data.max_daily_loss
    if update_data.max_position_size is not None:
        current_user.max_position_size = update_data.max_position_size
    if update_data.max_open_positions is not None:
        current_user.max_open_positions = update_data.max_open_positions
    if update_data.ai_trading_enabled is not None:
        current_user.ai_trading_enabled = update_data.ai_trading_enabled
    
    current_user.updated_at = datetime.utcnow()
    
    await db.commit()
    await db.refresh(current_user)
    
    return UserResponse(
        id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        full_name=current_user.full_name,
        phone=current_user.phone,
        role=current_user.role.value,
        status=current_user.status.value,
        trading_enabled=current_user.trading_enabled,
        ai_trading_enabled=current_user.ai_trading_enabled,
        risk_tolerance=current_user.risk_tolerance,
        max_daily_loss=current_user.max_daily_loss,
        max_position_size=current_user.max_position_size,
        max_open_positions=current_user.max_open_positions,
        created_at=current_user.created_at,
        last_login=current_user.last_login
    )
