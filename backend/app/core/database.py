"""
Database configuration and models
"""

import asyncio
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from app.core.config import settings

# Create declarative base
Base = declarative_base()

# Create async engine
if settings.DATABASE_URL.startswith("sqlite"):
    # For SQLite
    engine = create_async_engine(
        settings.DATABASE_URL.replace("sqlite://", "sqlite+aiosqlite://"),
        echo=settings.DEBUG,
        future=True
    )
else:
    # For PostgreSQL
    engine = create_async_engine(
        settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://"),
        echo=settings.DEBUG,
        future=True,
        pool_size=20,
        max_overflow=0
    )

# Create async session maker
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Get database session"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db():
    """Initialize database"""
    async with engine.begin() as conn:
        # Import all models to ensure they are registered
        from app.models import user, trading, market_data, ai_strategy
        
        # Create all tables
        await conn.run_sync(Base.metadata.create_all)


@asynccontextmanager
async def get_db_context():
    """Database context manager"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
