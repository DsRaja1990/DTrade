"""
Market data endpoints for instruments, quotes, historical data, and option chains
"""
from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from pydantic import BaseModel

from ...core.database import get_db
from ...models.user import User
from ...models.market_data import Instrument, MarketQuote, HistoricalData, OptionChain, MarketIndex
from ...services.dhan_service import DhanHQService
from ..endpoints.auth import get_current_user

router = APIRouter()

# Pydantic models
class InstrumentResponse(BaseModel):
    security_id: str
    trading_symbol: str
    exchange_segment: str
    instrument_type: str
    company_name: Optional[str]
    last_price: Optional[float]
    change_percent: Optional[float]

class QuoteResponse(BaseModel):
    security_id: str
    last_price: float
    open_price: float
    high_price: float
    low_price: float
    close_price: float
    change: float
    change_percent: float
    volume: int
    bid_price: Optional[float]
    ask_price: Optional[float]
    quote_time: datetime

class HistoricalDataResponse(BaseModel):
    timestamp: datetime
    open_price: float
    high_price: float
    low_price: float
    close_price: float
    volume: int
    
class OptionChainResponse(BaseModel):
    strike_price: float
    call_data: Optional[Dict[str, Any]]
    put_data: Optional[Dict[str, Any]]

@router.get("/instruments/search")
async def search_instruments(
    query: str = Query(..., min_length=2),
    exchange: Optional[str] = None,
    instrument_type: Optional[str] = None,
    limit: int = Query(20, le=100),
    db: AsyncSession = Depends(get_db)
):
    """Search for instruments by symbol or name"""
    
    search_query = select(Instrument).where(
        or_(
            Instrument.trading_symbol.ilike(f"%{query}%"),
            Instrument.company_name.ilike(f"%{query}%")
        )
    )
    
    if exchange:
        search_query = search_query.where(Instrument.exchange_segment == exchange)
    
    if instrument_type:
        search_query = search_query.where(Instrument.instrument_type == instrument_type)
    
    search_query = search_query.where(Instrument.is_active == True).limit(limit)
    
    result = await db.execute(search_query)
    instruments = result.scalars().all()
    
    return [
        InstrumentResponse(
            security_id=inst.security_id,
            trading_symbol=inst.trading_symbol,
            exchange_segment=inst.exchange_segment,
            instrument_type=inst.instrument_type,
            company_name=inst.company_name,
            last_price=inst.last_price,
            change_percent=((inst.last_price - inst.close_price) / inst.close_price * 100) if inst.last_price and inst.close_price else None
        )
        for inst in instruments
    ]

@router.get("/quote/{security_id}")
async def get_quote(
    security_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get real-time quote for a security"""
    
    try:
        dhan_service = DhanHQService(
            client_id=current_user.dhan_client_id,
            access_token=current_user.dhan_access_token
        )
        
        # Get quote from DhanHQ
        quote_data = await dhan_service.get_market_quote(security_id)
        
        if quote_data.get("status") == "success":
            data = quote_data["data"]
            
            return QuoteResponse(
                security_id=security_id,
                last_price=data.get("lastPrice", 0),
                open_price=data.get("openPrice", 0),
                high_price=data.get("highPrice", 0),
                low_price=data.get("lowPrice", 0),
                close_price=data.get("closePrice", 0),
                change=data.get("change", 0),
                change_percent=data.get("changePercent", 0),
                volume=data.get("volume", 0),
                bid_price=data.get("bidPrice"),
                ask_price=data.get("askPrice"),
                quote_time=datetime.now()
            )
        else:
            raise HTTPException(status_code=404, detail="Quote not found")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get quote: {str(e)}")

@router.get("/historical/{security_id}")
async def get_historical_data(
    security_id: str,
    timeframe: str = Query(..., regex="^(1min|5min|15min|1hour|1day)$"),
    from_date: datetime = Query(...),
    to_date: datetime = Query(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get historical data for a security"""
    
    try:
        dhan_service = DhanHQService(
            client_id=current_user.dhan_client_id,
            access_token=current_user.dhan_access_token
        )
        
        # Get historical data from DhanHQ
        historical_data = await dhan_service.get_historical_data(
            security_id=security_id,
            exchange_segment="NSE_EQ",  # Default, should be parameterized
            instrument_type="EQUITY",
            from_date=from_date.strftime("%Y-%m-%d"),
            to_date=to_date.strftime("%Y-%m-%d")
        )
        
        if historical_data.get("status") == "success":
            data = historical_data["data"]
            
            return [
                HistoricalDataResponse(
                    timestamp=datetime.fromisoformat(candle["timestamp"]),
                    open_price=candle["open"],
                    high_price=candle["high"],
                    low_price=candle["low"],
                    close_price=candle["close"],
                    volume=candle["volume"]
                )
                for candle in data
            ]
        else:
            raise HTTPException(status_code=404, detail="Historical data not found")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get historical data: {str(e)}")

@router.get("/option-chain/{underlying_symbol}")
async def get_option_chain(
    underlying_symbol: str,
    expiry_date: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get option chain for an underlying symbol"""
    
    try:
        dhan_service = DhanHQService(
            client_id=current_user.dhan_client_id,
            access_token=current_user.dhan_access_token
        )
        
        # Get option chain from DhanHQ
        option_chain_data = await dhan_service.get_option_chain(
            underlying_symbol=underlying_symbol,
            expiry_date=expiry_date
        )
        
        if option_chain_data.get("status") == "success":
            data = option_chain_data["data"]
            
            option_chain = {}
            for strike_data in data:
                strike = strike_data["strikePrice"]
                
                if strike not in option_chain:
                    option_chain[strike] = {"strike_price": strike}
                
                if strike_data["optionType"] == "CE":
                    option_chain[strike]["call_data"] = {
                        "security_id": strike_data["securityId"],
                        "last_price": strike_data.get("lastPrice"),
                        "change": strike_data.get("change"),
                        "volume": strike_data.get("volume"),
                        "open_interest": strike_data.get("openInterest"),
                        "implied_volatility": strike_data.get("impliedVolatility")
                    }
                elif strike_data["optionType"] == "PE":
                    option_chain[strike]["put_data"] = {
                        "security_id": strike_data["securityId"],
                        "last_price": strike_data.get("lastPrice"),
                        "change": strike_data.get("change"),
                        "volume": strike_data.get("volume"),
                        "open_interest": strike_data.get("openInterest"),
                        "implied_volatility": strike_data.get("impliedVolatility")
                    }
            
            return [
                OptionChainResponse(
                    strike_price=data["strike_price"],
                    call_data=data.get("call_data"),
                    put_data=data.get("put_data")
                )
                for data in option_chain.values()
            ]
        else:
            raise HTTPException(status_code=404, detail="Option chain not found")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get option chain: {str(e)}")

@router.get("/indices")
async def get_market_indices():
    """Get major market indices"""
    
    # Mock data - in real implementation, this would come from DhanHQ or be stored in database
    indices = [
        {"name": "NIFTY 50", "value": 19674.25, "change": 145.80, "change_percent": 0.75},
        {"name": "SENSEX", "value": 66060.90, "change": 486.50, "change_percent": 0.74},
        {"name": "NIFTY BANK", "value": 44850.15, "change": 320.45, "change_percent": 0.72},
        {"name": "NIFTY IT", "value": 30245.80, "change": -125.30, "change_percent": -0.41}
    ]
    
    return indices

@router.get("/market-status")
async def get_market_status():
    """Get current market status"""
    
    now = datetime.now()
    
    # Simplified market hours (9:15 AM to 3:30 PM IST)
    market_open = now.replace(hour=9, minute=15, second=0, microsecond=0)
    market_close = now.replace(hour=15, minute=30, second=0, microsecond=0)
    
    if market_open <= now <= market_close and now.weekday() < 5:  # Monday=0, Friday=4
        status = "OPEN"
    else:
        status = "CLOSED"
    
    return {
        "status": status,
        "current_time": now,
        "market_open": market_open,
        "market_close": market_close,
        "next_open": market_open + timedelta(days=1) if status == "CLOSED" else None
    }

@router.get("/watchlist")
async def get_watchlist(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get user's watchlist"""
    
    # Mock watchlist - in real implementation, this would be stored in database
    watchlist = [
        "11536", "1333", "500325", "500034", "500209"  # Sample security IDs
    ]
    
    quotes = []
    try:
        dhan_service = DhanHQService(
            client_id=current_user.dhan_client_id,
            access_token=current_user.dhan_access_token
        )
        
        for security_id in watchlist:
            quote_data = await dhan_service.get_market_quote(security_id)
            if quote_data.get("status") == "success":
                data = quote_data["data"]
                quotes.append({
                    "security_id": security_id,
                    "symbol": data.get("tradingSymbol", ""),
                    "last_price": data.get("lastPrice", 0),
                    "change": data.get("change", 0),
                    "change_percent": data.get("changePercent", 0),
                    "volume": data.get("volume", 0)
                })
    except Exception as e:
        # Return empty list if error occurs
        pass
    
    return quotes
