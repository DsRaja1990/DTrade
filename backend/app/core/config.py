"""
Core configuration settings for DTrade
"""

import os
from typing import List, Optional, ClassVar, Dict, Any
from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings"""
    
    # API Configuration
    API_HOST: str = Field(default="0.0.0.0", env="API_HOST")
    API_PORT: int = Field(default=8000, env="API_PORT")
    DEBUG: bool = Field(default=True, env="DEBUG")
    
    # Security
    SECRET_KEY: str = Field(env="SECRET_KEY")
    JWT_SECRET: str = Field(env="JWT_SECRET")
    JWT_ALGORITHM: str = Field(default="HS256", env="JWT_ALGORITHM")
    JWT_EXPIRATION_HOURS: int = Field(default=24, env="JWT_EXPIRATION_HOURS")
    
    # Database
    DATABASE_URL: str = Field(env="DATABASE_URL")
    
    # Redis
    REDIS_URL: str = Field(env="REDIS_URL")
    
    # DhanHQ API Configuration
    DHAN_CLIENT_ID: str = Field(default="1101317572", env="DHAN_CLIENT_ID")
    DHAN_ACCESS_TOKEN: str = Field(
        default="eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzUxMiJ9.eyJpc3MiOiJkaGFuIiwicGFydG5lcklkIjoiIiwiZXhwIjoxNzUzNjE0MzgyLCJ0b2tlbkNvbnN1bWVyVHlwZSI6IlNFTEYiLCJ3ZWJob29rVXJsIjoiIiwiZGhhbkNsaWVudElkIjoiMTEwMTMxNzU3MiJ9.8Yc6ocmXMwVDOnQn351_ePKwxat76ozpKMoULK0a20-ycLlMC0pQzxPVQ7mMdKGM_cO19-JmNQM52Y2acTyisg",
        env="DHAN_ACCESS_TOKEN"
    )
    DHAN_API_BASE_URL: str = Field(default="https://api.dhan.co/v2", env="DHAN_API_BASE_URL")
    DHAN_FEED_URL: str = Field(default="wss://api-feed.dhan.co", env="DHAN_FEED_URL")
    DHAN_TIMEOUT: int = Field(default=30, env="DHAN_TIMEOUT")
    DHAN_RETRY_COUNT: int = Field(default=3, env="DHAN_RETRY_COUNT")
    DHAN_RETRY_DELAY: float = Field(default=1.0, env="DHAN_RETRY_DELAY")
    
    # AI Trading Configuration
    AI_ENABLED: bool = Field(default=True, env="AI_ENABLED")
    MAX_POSITION_SIZE: float = Field(default=100000.0, env="MAX_POSITION_SIZE")
    MAX_DAILY_LOSS: float = Field(default=50000.0, env="MAX_DAILY_LOSS")
    RISK_PERCENTAGE: float = Field(default=2.0, env="RISK_PERCENTAGE")
    TRAILING_STOP_PERCENTAGE: float = Field(default=1.0, env="TRAILING_STOP_PERCENTAGE")
    
    # Trading Parameters
    DEFAULT_QUANTITY: int = Field(default=25, env="DEFAULT_QUANTITY")
    DEFAULT_PRODUCT_TYPE: str = Field(default="INTRADAY", env="DEFAULT_PRODUCT_TYPE")
    DEFAULT_ORDER_TYPE: str = Field(default="MARKET", env="DEFAULT_ORDER_TYPE")
    ENABLE_PAPER_TRADING: bool = Field(default=True, env="ENABLE_PAPER_TRADING")
    
    # Market Data Configuration
    MARKET_DATA_ENABLED: bool = Field(default=True, env="MARKET_DATA_ENABLED")
    HISTORICAL_DATA_ENABLED: bool = Field(default=True, env="HISTORICAL_DATA_ENABLED")
    LIVE_FEED_ENABLED: bool = Field(default=True, env="LIVE_FEED_ENABLED")
    
    # Performance Configuration
    CACHE_TTL: int = Field(default=300, env="CACHE_TTL")
    MAX_CONCURRENT_REQUESTS: int = Field(default=100, env="MAX_CONCURRENT_REQUESTS")
    REQUEST_TIMEOUT: int = Field(default=30, env="REQUEST_TIMEOUT")
    
    # Logging Configuration
    LOG_LEVEL: str = Field(default="INFO", env="LOG_LEVEL")
    LOG_FILE: str = Field(default="logs/dtrade.log", env="LOG_FILE")
    
    # CORS Configuration
    ALLOWED_ORIGINS: List[str] = Field(
        default=[
            "http://localhost:3000",
            "http://localhost:3001",
            "http://127.0.0.1:3000",
            "http://127.0.0.1:3001"
        ]
    )
    
    # Email Configuration (Optional)
    EMAIL_ENABLED: bool = Field(default=False, env="EMAIL_ENABLED")
    SMTP_SERVER: Optional[str] = Field(default=None, env="SMTP_SERVER")
    SMTP_PORT: Optional[int] = Field(default=587, env="SMTP_PORT")
    EMAIL_USERNAME: Optional[str] = Field(default=None, env="EMAIL_USERNAME")
    EMAIL_PASSWORD: Optional[str] = Field(default=None, env="EMAIL_PASSWORD")
    
    # Notification Configuration
    TELEGRAM_BOT_TOKEN: Optional[str] = Field(default=None, env="TELEGRAM_BOT_TOKEN")
    TELEGRAM_CHAT_ID: Optional[str] = Field(default=None, env="TELEGRAM_CHAT_ID")
    
    # Exchange Segments
    EXCHANGE_SEGMENTS: ClassVar[Dict[str, Dict[str, Any]]] = {
        "IDX_I": {"name": "Index", "code": 0},
        "NSE_EQ": {"name": "NSE Equity", "code": 1},
        "NSE_FNO": {"name": "NSE F&O", "code": 2},
        "NSE_CURRENCY": {"name": "NSE Currency", "code": 3},
        "BSE_EQ": {"name": "BSE Equity", "code": 4},
        "MCX_COMM": {"name": "MCX Commodity", "code": 5},
        "BSE_CURRENCY": {"name": "BSE Currency", "code": 7},
        "BSE_FNO": {"name": "BSE F&O", "code": 8}
    }
    
    # Product Types
    PRODUCT_TYPES: ClassVar[Dict[str, str]] = {
        "CNC": "Cash & Carry",
        "INTRADAY": "Intraday",
        "MARGIN": "Margin",
        "CO": "Cover Order",
        "BO": "Bracket Order"
    }
    
    # Order Types
    ORDER_TYPES: ClassVar[Dict[str, str]] = {
        "LIMIT": "Limit Order",
        "MARKET": "Market Order",
        "STOP_LOSS": "Stop Loss",
        "STOP_LOSS_MARKET": "Stop Loss Market"
    }
    
    # Order Status
    ORDER_STATUS: ClassVar[Dict[str, str]] = {
        "TRANSIT": "Transit",
        "PENDING": "Pending",
        "REJECTED": "Rejected",
        "CANCELLED": "Cancelled",
        "PART_TRADED": "Partially Traded",
        "TRADED": "Traded",
        "EXPIRED": "Expired"
    }
    
    # Feed Request Codes
    FEED_REQUEST_CODES: ClassVar[Dict[str, int]] = {
        "CONNECT": 11,
        "DISCONNECT": 12,
        "SUBSCRIBE_TICKER": 15,
        "UNSUBSCRIBE_TICKER": 16,
        "SUBSCRIBE_QUOTE": 17,
        "UNSUBSCRIBE_QUOTE": 18,
        "SUBSCRIBE_FULL": 21,
        "UNSUBSCRIBE_FULL": 22,
        "SUBSCRIBE_DEPTH": 23,
        "UNSUBSCRIBE_DEPTH": 24
    }
    
    # Feed Response Codes
    FEED_RESPONSE_CODES: ClassVar[Dict[int, str]] = {
        1: "Index Packet",
        2: "Ticker Packet",
        4: "Quote Packet",
        5: "OI Packet",
        6: "Prev Close Packet",
        7: "Market Status Packet",
        8: "Full Packet",
        50: "Feed Disconnect"
    }
    
    class Config:
        env_file = ".env"
        case_sensitive = True


# Create settings instance
settings = Settings()

def get_settings() -> Settings:
    """Get the application settings instance"""
    return settings
