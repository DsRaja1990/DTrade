"""
Webhook endpoints for receiving market data and order updates
"""
from fastapi import APIRouter, HTTPException, Depends, Request, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
from typing import Dict, Any
from pydantic import BaseModel
import json

from ...core.database import get_db
from ...core.websocket_manager import ConnectionManager
from ...models.trading import Order, Trade, Position, OrderStatus
from ...models.market_data import MarketQuote

router = APIRouter()

class DhanOrderUpdate(BaseModel):
    orderId: str
    correlationId: str
    orderStatus: str
    transactionType: str
    exchangeSegment: str
    productType: str
    orderType: str
    validity: str
    tradingSymbol: str
    securityId: str
    quantity: int
    disclosedQuantity: int
    price: float
    triggerPrice: float
    afterMarketOrder: bool
    boProfitValue: float
    boStopLossValue: float
    legName: str
    createTime: str
    updateTime: str
    exchangeTime: str
    drvExpiryDate: str
    drvOptionType: str
    drvStrikePrice: float
    omsErrorCode: str
    omsErrorDescription: str
    filled: int
    algoId: str
    remarks: str

class DhanTradeUpdate(BaseModel):
    clientId: str
    orderId: str
    tradeId: str
    exchangeSegment: str
    tradingSymbol: str
    transactionType: str
    quantity: int
    price: float
    tradeValue: float
    tradeTime: str
    exchangeTime: str
    securityId: str

class DhanMarketData(BaseModel):
    securityId: str
    lastPrice: float
    openPrice: float
    highPrice: float
    lowPrice: float
    closePrice: float
    change: float
    changePercent: float
    volume: int
    timestamp: str

@router.post("/dhan/order-update")
async def dhan_order_update(
    order_update: DhanOrderUpdate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """Receive order status updates from DhanHQ"""
    
    try:
        # Process order update
        background_tasks.add_task(process_order_update, order_update.dict(), db)
        
        return {"status": "success", "message": "Order update received"}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process order update: {str(e)}")

@router.post("/dhan/trade-update")
async def dhan_trade_update(
    trade_update: DhanTradeUpdate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """Receive trade confirmations from DhanHQ"""
    
    try:
        # Process trade update
        background_tasks.add_task(process_trade_update, trade_update.dict(), db)
        
        return {"status": "success", "message": "Trade update received"}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process trade update: {str(e)}")

@router.post("/dhan/market-data")
async def dhan_market_data(
    market_data: DhanMarketData,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """Receive real-time market data from DhanHQ"""
    
    try:
        # Process market data update
        background_tasks.add_task(process_market_data, market_data.dict(), db)
        
        return {"status": "success", "message": "Market data received"}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process market data: {str(e)}")

@router.post("/generic-webhook")
async def generic_webhook(request: Request):
    """Generic webhook endpoint for any external updates"""
    
    try:
        body = await request.body()
        headers = dict(request.headers)
        
        # Log webhook for debugging
        webhook_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "headers": headers,
            "body": body.decode('utf-8') if body else None,
            "url": str(request.url)
        }
        
        # Process based on source
        source = headers.get("x-webhook-source", "unknown")
        
        if source == "dhan":
            # Process DhanHQ webhook
            pass
        elif source == "zerodha":
            # Process Zerodha webhook if needed
            pass
        
        return {"status": "success", "message": "Webhook received", "source": source}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process webhook: {str(e)}")

async def process_order_update(order_data: Dict[str, Any], db: AsyncSession):
    """Background task to process order updates"""
    
    try:
        from sqlalchemy import select, update
        
        # Find order by DhanHQ order ID
        result = await db.execute(
            select(Order).where(Order.dhan_order_id == order_data["orderId"])
        )
        order = result.scalar_one_or_none()
        
        if order:
            # Update order status
            order.status = OrderStatus(order_data["orderStatus"])
            order.filled_quantity = order_data.get("filled", 0)
            order.pending_quantity = order.quantity - order.filled_quantity
            order.exchange_time = datetime.fromisoformat(order_data["exchangeTime"]) if order_data.get("exchangeTime") else None
            order.updated_at = datetime.utcnow()
            
            if order_data.get("omsErrorDescription"):
                order.rejection_reason = order_data["omsErrorDescription"]
            
            await db.commit()
            
            # Broadcast update via WebSocket
            websocket_manager = ConnectionManager()
            await websocket_manager.broadcast_to_user(
                order.user_id,
                {
                    "type": "order_update",
                    "data": {
                        "order_id": str(order.id),
                        "dhan_order_id": order.dhan_order_id,
                        "status": order.status.value,
                        "filled_quantity": order.filled_quantity,
                        "timestamp": datetime.utcnow().isoformat()
                    }
                }
            )
    
    except Exception as e:
        # Log error
        print(f"Error processing order update: {e}")

async def process_trade_update(trade_data: Dict[str, Any], db: AsyncSession):
    """Background task to process trade updates"""
    
    try:
        from sqlalchemy import select
        
        # Find order to link trade to
        result = await db.execute(
            select(Order).where(Order.dhan_order_id == trade_data["orderId"])
        )
        order = result.scalar_one_or_none()
        
        if order:
            # Create trade record
            trade = Trade(
                user_id=order.user_id,
                order_id=order.id,
                dhan_trade_id=trade_data["tradeId"],
                dhan_order_id=trade_data["orderId"],
                security_id=trade_data["securityId"],
                exchange_segment=trade_data["exchangeSegment"],
                trading_symbol=trade_data["tradingSymbol"],
                trade_side=order.order_side,
                quantity=trade_data["quantity"],
                price=trade_data["price"],
                value=trade_data["tradeValue"],
                trade_time=datetime.fromisoformat(trade_data["tradeTime"]),
                exchange_time=datetime.fromisoformat(trade_data["exchangeTime"]) if trade_data.get("exchangeTime") else None,
                net_amount=trade_data["tradeValue"]  # Will be updated with charges later
            )
            
            db.add(trade)
            await db.commit()
            
            # Update position
            await update_position(order.user_id, trade, db)
            
            # Broadcast trade update
            websocket_manager = ConnectionManager()
            await websocket_manager.broadcast_to_user(
                order.user_id,
                {
                    "type": "trade_update",
                    "data": {
                        "trade_id": trade_data["tradeId"],
                        "symbol": trade_data["tradingSymbol"],
                        "quantity": trade_data["quantity"],
                        "price": trade_data["price"],
                        "timestamp": datetime.utcnow().isoformat()
                    }
                }
            )
    
    except Exception as e:
        print(f"Error processing trade update: {e}")

async def process_market_data(market_data: Dict[str, Any], db: AsyncSession):
    """Background task to process market data updates"""
    
    try:
        # Store market quote in database
        quote = MarketQuote(
            security_id=market_data["securityId"],
            exchange_segment="NSE_EQ",  # Default, should be from data
            last_price=market_data["lastPrice"],
            open_price=market_data["openPrice"],
            high_price=market_data["highPrice"],
            low_price=market_data["lowPrice"],
            close_price=market_data["closePrice"],
            change=market_data["change"],
            change_percent=market_data["changePercent"],
            volume=market_data["volume"],
            quote_time=datetime.fromisoformat(market_data["timestamp"])
        )
        
        db.add(quote)
        await db.commit()
        
        # Broadcast market data to subscribed users
        websocket_manager = ConnectionManager()
        await websocket_manager.broadcast_market_data(
            market_data["securityId"],
            {
                "type": "market_data",
                "data": market_data
            }
        )
    
    except Exception as e:
        print(f"Error processing market data: {e}")

async def update_position(user_id: int, trade: Trade, db: AsyncSession):
    """Update user position based on trade"""
    
    try:
        from sqlalchemy import select
        
        # Find existing position
        result = await db.execute(
            select(Position).where(
                Position.user_id == user_id,
                Position.security_id == trade.security_id,
                Position.is_open == True
            )
        )
        position = result.scalar_one_or_none()
        
        if not position:
            # Create new position
            position = Position(
                user_id=user_id,
                security_id=trade.security_id,
                exchange_segment=trade.exchange_segment,
                trading_symbol=trade.trading_symbol,
                entry_time=trade.trade_time
            )
            db.add(position)
        
        # Update position quantities and averages
        if trade.trade_side.value == "BUY":
            position.buy_quantity += trade.quantity
            position.net_quantity += trade.quantity
            # Update buy average
            total_buy_value = (position.buy_average * (position.buy_quantity - trade.quantity)) + trade.value
            position.buy_average = total_buy_value / position.buy_quantity if position.buy_quantity > 0 else 0
        else:  # SELL
            position.sell_quantity += trade.quantity
            position.net_quantity -= trade.quantity
            # Update sell average
            total_sell_value = (position.sell_average * (position.sell_quantity - trade.quantity)) + trade.value
            position.sell_average = total_sell_value / position.sell_quantity if position.sell_quantity > 0 else 0
        
        # Close position if net quantity is zero
        if position.net_quantity == 0:
            position.is_open = False
            position.exit_time = trade.trade_time
        
        position.updated_at = datetime.utcnow()
        await db.commit()
    
    except Exception as e:
        print(f"Error updating position: {e}")
