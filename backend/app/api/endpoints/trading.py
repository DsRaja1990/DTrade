"""
Trading endpoints for order management, positions, and trade execution
"""
from fastapi import APIRouter, HTTPException, Depends, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
import json
import uuid

from ...core.config import get_settings
from ...core.database import get_db
from ...models.user import User
from ...models.trading import Order, Position, Trade, OrderType, OrderSide, ProductType, OrderStatus
from ...services.dhan_service import DhanHQService
from ...ai_engine.trading_engine import AITradingEngine
from ..endpoints.auth import get_current_user

settings = get_settings()
router = APIRouter()

# Pydantic models for request/response
class OrderRequest(BaseModel):
    security_id: str
    exchange_segment: str
    trading_symbol: str
    order_type: str  # MARKET, LIMIT, SL, SL-M, BO, CO
    order_side: str  # BUY, SELL
    product_type: str  # CNC, INTRADAY, MARGIN, CO, BO
    quantity: int
    price: Optional[float] = None
    trigger_price: Optional[float] = None
    disclosed_quantity: Optional[int] = 0
    is_amo: Optional[bool] = False
    validity: Optional[str] = "DAY"

class SuperOrderRequest(BaseModel):
    orders: List[OrderRequest]
    strategy_name: Optional[str] = None

class ModifyOrderRequest(BaseModel):
    order_id: str
    quantity: Optional[int] = None
    price: Optional[float] = None
    trigger_price: Optional[float] = None
    validity: Optional[str] = None

class AITradeRequest(BaseModel):
    instruments: List[str]  # List of security IDs or symbols
    strategy_type: Optional[str] = "momentum"
    risk_level: Optional[str] = "medium"
    max_position_size: Optional[float] = 50000
    stop_loss_percent: Optional[float] = 2.0
    take_profit_percent: Optional[float] = 4.0
    enable_hedging: Optional[bool] = True

class OrderResponse(BaseModel):
    order_id: str
    dhan_order_id: Optional[str]
    status: str
    message: str
    timestamp: datetime

class PositionResponse(BaseModel):
    id: int
    security_id: str
    trading_symbol: str
    position_type: str
    net_quantity: int
    buy_average: float
    sell_average: float
    last_price: float
    unrealized_pnl: float
    day_pnl: float
    is_open: bool

class TradeResponse(BaseModel):
    id: int
    trade_id: str
    security_id: str
    trading_symbol: str
    trade_side: str
    quantity: int
    price: float
    value: float
    net_amount: float
    trade_time: datetime

# Order Management Endpoints
@router.post("/orders", response_model=OrderResponse)
async def place_order(
    order_request: OrderRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Place a new trading order"""
    
    if not current_user.trading_enabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Trading is not enabled for this account"
        )
    
    try:
        # Initialize DhanHQ service
        dhan_service = DhanHQService(
            client_id=current_user.dhan_client_id,
            access_token=current_user.dhan_access_token
        )
        
        # Create order in database first
        order = Order(
            user_id=current_user.id,
            correlation_id=str(uuid.uuid4()),
            security_id=order_request.security_id,
            exchange_segment=order_request.exchange_segment,
            trading_symbol=order_request.trading_symbol,
            order_type=OrderType(order_request.order_type),
            order_side=OrderSide(order_request.order_side),
            product_type=ProductType(order_request.product_type),
            quantity=order_request.quantity,
            price=order_request.price,
            trigger_price=order_request.trigger_price,
            disclosed_quantity=order_request.disclosed_quantity,
            is_amo=order_request.is_amo,
            validity=order_request.validity,
            pending_quantity=order_request.quantity
        )
        
        db.add(order)
        await db.commit()
        await db.refresh(order)
        
        # Place order with DhanHQ
        dhan_response = await dhan_service.place_order(
            security_id=order_request.security_id,
            exchange_segment=order_request.exchange_segment,
            transaction_type=order_request.order_side,
            quantity=order_request.quantity,
            order_type=order_request.order_type,
            product_type=order_request.product_type,
            price=order_request.price,
            trigger_price=order_request.trigger_price,
            disclosed_quantity=order_request.disclosed_quantity,
            validity=order_request.validity,
            is_amo=order_request.is_amo
        )
        
        if dhan_response.get("status") == "success":
            # Update order with DhanHQ order ID
            order.dhan_order_id = dhan_response["data"]["orderId"]
            order.status = OrderStatus.OPEN
            await db.commit()
            
            return OrderResponse(
                order_id=str(order.id),
                dhan_order_id=order.dhan_order_id,
                status="success",
                message="Order placed successfully",
                timestamp=order.order_time
            )
        else:
            # Update order status to rejected
            order.status = OrderStatus.REJECTED
            order.rejection_reason = dhan_response.get("remarks", "Order rejected by exchange")
            await db.commit()
            
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Order rejected: {dhan_response.get('remarks', 'Unknown error')}"
            )
            
    except Exception as e:
        # Update order status to rejected if it exists
        if 'order' in locals():
            order.status = OrderStatus.REJECTED
            order.rejection_reason = str(e)
            await db.commit()
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to place order: {str(e)}"
        )

@router.post("/super-orders", response_model=List[OrderResponse])
async def place_super_order(
    super_order_request: SuperOrderRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Place multiple orders in a single request (Super Order)"""
    
    if not current_user.trading_enabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Trading is not enabled for this account"
        )
    
    try:
        dhan_service = DhanHQService(
            client_id=current_user.dhan_client_id,
            access_token=current_user.dhan_access_token
        )
        
        # Prepare super order data for DhanHQ
        super_order_data = []
        db_orders = []
        
        for order_req in super_order_request.orders:
            # Create order in database
            order = Order(
                user_id=current_user.id,
                correlation_id=str(uuid.uuid4()),
                security_id=order_req.security_id,
                exchange_segment=order_req.exchange_segment,
                trading_symbol=order_req.trading_symbol,
                order_type=OrderType(order_req.order_type),
                order_side=OrderSide(order_req.order_side),
                product_type=ProductType(order_req.product_type),
                quantity=order_req.quantity,
                price=order_req.price,
                trigger_price=order_req.trigger_price,
                disclosed_quantity=order_req.disclosed_quantity,
                is_amo=order_req.is_amo,
                validity=order_req.validity,
                pending_quantity=order_req.quantity
            )
            
            db.add(order)
            db_orders.append(order)
            
            # Prepare for DhanHQ super order
            super_order_data.append({
                "drvExpiryDate": None,
                "drvOptionType": None,
                "drvStrikePrice": 0,
                "exchange": order_req.exchange_segment,
                "securityId": order_req.security_id,
                "transactionType": order_req.order_side,
                "quantity": order_req.quantity,
                "disclosedQuantity": order_req.disclosed_quantity or 0,
                "price": order_req.price or 0,
                "triggerPrice": order_req.trigger_price or 0,
                "orderType": order_req.order_type,
                "validity": order_req.validity,
                "productType": order_req.product_type,
                "orderFlag": "SINGLE",
                "tradingSymbol": order_req.trading_symbol,
                "correlationId": order.correlation_id
            })
        
        await db.commit()
        
        # Place super order with DhanHQ
        dhan_response = await dhan_service.place_super_order(super_order_data)
        
        responses = []
        
        if dhan_response.get("status") == "success":
            order_results = dhan_response.get("data", [])
            
            for i, order_result in enumerate(order_results):
                db_order = db_orders[i]
                
                if order_result.get("status") == "success":
                    db_order.dhan_order_id = order_result.get("orderId")
                    db_order.status = OrderStatus.OPEN
                    status_msg = "success"
                    message = "Order placed successfully"
                else:
                    db_order.status = OrderStatus.REJECTED
                    db_order.rejection_reason = order_result.get("remarks", "Order rejected")
                    status_msg = "failed"
                    message = order_result.get("remarks", "Order rejected")
                
                responses.append(OrderResponse(
                    order_id=str(db_order.id),
                    dhan_order_id=db_order.dhan_order_id,
                    status=status_msg,
                    message=message,
                    timestamp=db_order.order_time
                ))
            
            await db.commit()
            
        return responses
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to place super order: {str(e)}"
        )

@router.put("/orders/{order_id}", response_model=OrderResponse)
async def modify_order(
    order_id: str,
    modify_request: ModifyOrderRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Modify an existing order"""
    
    try:
        # Get order from database
        result = await db.execute(
            select(Order).where(
                and_(Order.id == int(order_id), Order.user_id == current_user.id)
            )
        )
        order = result.scalar_one_or_none()
        
        if not order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Order not found"
            )
        
        if order.status not in [OrderStatus.OPEN, OrderStatus.PARTIAL]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Order cannot be modified in current status"
            )
        
        dhan_service = DhanHQService(
            client_id=current_user.dhan_client_id,
            access_token=current_user.dhan_access_token
        )
        
        # Modify order with DhanHQ
        dhan_response = await dhan_service.modify_order(
            order_id=order.dhan_order_id,
            quantity=modify_request.quantity or order.quantity,
            price=modify_request.price if modify_request.price is not None else order.price,
            trigger_price=modify_request.trigger_price if modify_request.trigger_price is not None else order.trigger_price,
            validity=modify_request.validity or order.validity
        )
        
        if dhan_response.get("status") == "success":
            # Update order in database
            if modify_request.quantity:
                order.quantity = modify_request.quantity
                order.pending_quantity = modify_request.quantity - order.filled_quantity
            if modify_request.price is not None:
                order.price = modify_request.price
            if modify_request.trigger_price is not None:
                order.trigger_price = modify_request.trigger_price
            if modify_request.validity:
                order.validity = modify_request.validity
            
            order.updated_at = datetime.utcnow()
            await db.commit()
            
            return OrderResponse(
                order_id=order_id,
                dhan_order_id=order.dhan_order_id,
                status="success",
                message="Order modified successfully",
                timestamp=order.updated_at
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to modify order: {dhan_response.get('remarks', 'Unknown error')}"
            )
            
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to modify order: {str(e)}"
        )

@router.delete("/orders/{order_id}", response_model=OrderResponse)
async def cancel_order(
    order_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Cancel an existing order"""
    
    try:
        # Get order from database
        result = await db.execute(
            select(Order).where(
                and_(Order.id == int(order_id), Order.user_id == current_user.id)
            )
        )
        order = result.scalar_one_or_none()
        
        if not order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Order not found"
            )
        
        if order.status not in [OrderStatus.OPEN, OrderStatus.PARTIAL]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Order cannot be cancelled in current status"
            )
        
        dhan_service = DhanHQService(
            client_id=current_user.dhan_client_id,
            access_token=current_user.dhan_access_token
        )
        
        # Cancel order with DhanHQ
        dhan_response = await dhan_service.cancel_order(order.dhan_order_id)
        
        if dhan_response.get("status") == "success":
            # Update order status in database
            order.status = OrderStatus.CANCELLED
            order.updated_at = datetime.utcnow()
            await db.commit()
            
            return OrderResponse(
                order_id=order_id,
                dhan_order_id=order.dhan_order_id,
                status="success",
                message="Order cancelled successfully",
                timestamp=order.updated_at
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to cancel order: {dhan_response.get('remarks', 'Unknown error')}"
            )
            
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to cancel order: {str(e)}"
        )

@router.get("/orders", response_model=List[Dict[str, Any]])
async def get_orders(
    status: Optional[str] = None,
    limit: Optional[int] = 100,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get user's orders with optional filtering"""
    
    query = select(Order).where(Order.user_id == current_user.id)
    
    if status:
        query = query.where(Order.status == OrderStatus(status))
    
    query = query.order_by(Order.order_time.desc()).limit(limit)
    
    result = await db.execute(query)
    orders = result.scalars().all()
    
    return [
        {
            "id": order.id,
            "dhan_order_id": order.dhan_order_id,
            "security_id": order.security_id,
            "trading_symbol": order.trading_symbol,
            "order_type": order.order_type.value,
            "order_side": order.order_side.value,
            "quantity": order.quantity,
            "filled_quantity": order.filled_quantity,
            "price": order.price,
            "average_price": order.average_price,
            "status": order.status.value,
            "order_time": order.order_time,
            "rejection_reason": order.rejection_reason
        }
        for order in orders
    ]

@router.get("/positions", response_model=List[PositionResponse])
async def get_positions(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get user's current positions"""
    
    result = await db.execute(
        select(Position).where(
            and_(Position.user_id == current_user.id, Position.is_open == True)
        )
    )
    positions = result.scalars().all()
    
    return [
        PositionResponse(
            id=position.id,
            security_id=position.security_id,
            trading_symbol=position.trading_symbol,
            position_type=position.position_type.value,
            net_quantity=position.net_quantity,
            buy_average=position.buy_average,
            sell_average=position.sell_average,
            last_price=position.last_price or 0.0,
            unrealized_pnl=position.unrealized_pnl,
            day_pnl=position.day_pnl,
            is_open=position.is_open
        )
        for position in positions
    ]

@router.get("/trades", response_model=List[TradeResponse])
async def get_trades(
    limit: Optional[int] = 100,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get user's trades"""
    
    result = await db.execute(
        select(Trade).where(Trade.user_id == current_user.id)
        .order_by(Trade.trade_time.desc())
        .limit(limit)
    )
    trades = result.scalars().all()
    
    return [
        TradeResponse(
            id=trade.id,
            trade_id=trade.dhan_trade_id,
            security_id=trade.security_id,
            trading_symbol=trade.trading_symbol,
            trade_side=trade.trade_side.value,
            quantity=trade.quantity,
            price=trade.price,
            value=trade.value,
            net_amount=trade.net_amount,
            trade_time=trade.trade_time
        )
        for trade in trades
    ]

# AI Trading Endpoints
@router.post("/ai-trade/start")
async def start_ai_trading(
    ai_request: AITradeRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Start AI-powered automated trading"""
    
    if not current_user.ai_trading_enabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="AI trading is not enabled for this account"
        )
    
    try:
        # Initialize trading engine
        trading_engine = AITradingEngine(
            user_id=current_user.id,
            dhan_service=DhanHQService(
                client_id=current_user.dhan_client_id,
                access_token=current_user.dhan_access_token
            )
        )
        
        # Configure AI trading parameters
        config = {
            "instruments": ai_request.instruments,
            "strategy_type": ai_request.strategy_type,
            "risk_level": ai_request.risk_level,
            "max_position_size": ai_request.max_position_size,
            "stop_loss_percent": ai_request.stop_loss_percent,
            "take_profit_percent": ai_request.take_profit_percent,
            "enable_hedging": ai_request.enable_hedging
        }
        
        # Start AI trading in background
        background_tasks.add_task(trading_engine.start_automated_trading, config)
        
        return {
            "status": "success",
            "message": "AI trading started successfully",
            "config": config,
            "timestamp": datetime.utcnow()
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start AI trading: {str(e)}"
        )

@router.post("/ai-trade/stop")
async def stop_ai_trading(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Stop AI-powered automated trading"""
    
    try:
        # Initialize trading engine
        trading_engine = AITradingEngine(
            user_id=current_user.id,
            dhan_service=DhanHQService(
                client_id=current_user.dhan_client_id,
                access_token=current_user.dhan_access_token
            )
        )
        
        # Stop AI trading
        await trading_engine.stop_automated_trading()
        
        return {
            "status": "success", 
            "message": "AI trading stopped successfully",
            "timestamp": datetime.utcnow()
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to stop AI trading: {str(e)}"
        )
