"""
Authentication endpoints for login, logout, registration, and token management
"""
from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timedelta
from typing import Optional
import jwt
import bcrypt
from pydantic import BaseModel, EmailStr

from ...core.config import get_settings
from ...core.database import get_db
from ...models.user import User, UserSession

settings = get_settings()
router = APIRouter()
security = HTTPBearer()

# Pydantic models for request/response
class UserRegistration(BaseModel):
    username: str
    email: EmailStr
    password: str
    full_name: Optional[str] = None
    phone: Optional[str] = None
    dhan_client_id: Optional[str] = None

class UserLogin(BaseModel):
    username: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int

class UserProfile(BaseModel):
    id: int
    username: str
    email: str
    full_name: Optional[str]
    phone: Optional[str]
    role: str
    status: str
    trading_enabled: bool
    ai_trading_enabled: bool
    created_at: datetime
    last_login: Optional[datetime]

# Utility functions
def hash_password(password: str) -> str:
    """Hash a password using bcrypt"""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

def verify_password(password: str, hashed: str) -> bool:
    """Verify a password against its hash"""
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

def create_access_token(user_id: int, username: str) -> str:
    """Create JWT access token"""
    payload = {
        "user_id": user_id,
        "username": username,
        "exp": datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
        "iat": datetime.utcnow(),
        "type": "access"
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

def create_refresh_token(user_id: int, username: str) -> str:
    """Create JWT refresh token"""
    payload = {
        "user_id": user_id,
        "username": username,
        "exp": datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
        "iat": datetime.utcnow(),
        "type": "refresh"
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> User:
    """Get current authenticated user from JWT token"""
    try:
        payload = jwt.decode(
            credentials.credentials, 
            settings.SECRET_KEY, 
            algorithms=[settings.ALGORITHM]
        )
        user_id: int = payload.get("user_id")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user

# Authentication endpoints
@router.post("/register", response_model=UserProfile, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserRegistration, db: AsyncSession = Depends(get_db)):
    """Register a new user"""
    
    # Check if username or email already exists
    result = await db.execute(
        select(User).where(
            (User.username == user_data.username) | (User.email == user_data.email)
        )
    )
    existing_user = result.scalar_one_or_none()
    
    if existing_user:
        if existing_user.username == user_data.username:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already registered"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
    
    # Create new user
    hashed_password = hash_password(user_data.password)
    new_user = User(
        username=user_data.username,
        email=user_data.email,
        hashed_password=hashed_password,
        full_name=user_data.full_name,
        phone=user_data.phone,
        dhan_client_id=user_data.dhan_client_id
    )
    
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    
    return UserProfile(
        id=new_user.id,
        username=new_user.username,
        email=new_user.email,
        full_name=new_user.full_name,
        phone=new_user.phone,
        role=new_user.role.value,
        status=new_user.status.value,
        trading_enabled=new_user.trading_enabled,
        ai_trading_enabled=new_user.ai_trading_enabled,
        created_at=new_user.created_at,
        last_login=new_user.last_login
    )

@router.post("/login", response_model=TokenResponse)
async def login(user_data: UserLogin, db: AsyncSession = Depends(get_db)):
    """Authenticate user and return tokens"""
    
    # Find user by username
    result = await db.execute(select(User).where(User.username == user_data.username))
    user = result.scalar_one_or_none()
    
    if not user or not verify_password(user_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if user.status.value != "active":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account is not active"
        )
    
    # Create tokens
    access_token = create_access_token(user.id, user.username)
    refresh_token = create_refresh_token(user.id, user.username)
    
    # Create session record
    session = UserSession(
        user_id=user.id,
        session_token=access_token,
        refresh_token=refresh_token,
        expires_at=datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    db.add(session)
    
    # Update last login
    user.last_login = datetime.utcnow()
    
    await db.commit()
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )

@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(refresh_token: str, db: AsyncSession = Depends(get_db)):
    """Refresh access token using refresh token"""
    
    try:
        payload = jwt.decode(refresh_token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id: int = payload.get("user_id")
        username: str = payload.get("username")
        token_type: str = payload.get("type")
        
        if token_type != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type"
            )
            
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )
    
    # Verify user exists and is active
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user or user.status.value != "active":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive"
        )
    
    # Create new tokens
    new_access_token = create_access_token(user.id, user.username)
    new_refresh_token = create_refresh_token(user.id, user.username)
    
    return TokenResponse(
        access_token=new_access_token,
        refresh_token=new_refresh_token,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )

@router.post("/logout")
async def logout(
    current_user: User = Depends(get_current_user),
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
):
    """Logout user and invalidate session"""
    
    # Invalidate session
    result = await db.execute(
        select(UserSession).where(
            UserSession.user_id == current_user.id,
            UserSession.session_token == credentials.credentials,
            UserSession.is_active == True
        )
    )
    session = result.scalar_one_or_none()
    
    if session:
        session.is_active = False
        await db.commit()
    
    return {"message": "Successfully logged out"}

@router.get("/me", response_model=UserProfile)
async def get_current_user_profile(current_user: User = Depends(get_current_user)):
    """Get current user profile"""
    
    return UserProfile(
        id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        full_name=current_user.full_name,
        phone=current_user.phone,
        role=current_user.role.value,
        status=current_user.status.value,
        trading_enabled=current_user.trading_enabled,
        ai_trading_enabled=current_user.ai_trading_enabled,
        created_at=current_user.created_at,
        last_login=current_user.last_login
    )

@router.get("/verify-token")
async def verify_token(current_user: User = Depends(get_current_user)):
    """Verify if token is valid"""
    return {"valid": True, "user_id": current_user.id, "username": current_user.username}
