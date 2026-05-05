"""
Main API router that includes all endpoint routers
"""
from fastapi import APIRouter
from .endpoints import (
    auth,
    users,
    trading,
    market_data,
    portfolio,
    strategies,
    signals,
    backtesting,
    analytics,
    webhooks,
    admin,
    ratio_strategy
)

api_router = APIRouter()

# Authentication routes
api_router.include_router(
    auth.router,
    prefix="/auth",
    tags=["authentication"]
)

# User management routes
api_router.include_router(
    users.router,
    prefix="/users",
    tags=["users"]
)

# Trading routes
api_router.include_router(
    trading.router,
    prefix="/trading",
    tags=["trading"]
)

# Market data routes
api_router.include_router(
    market_data.router,
    prefix="/market-data",
    tags=["market-data"]
)

# Portfolio management routes
api_router.include_router(
    portfolio.router,
    prefix="/portfolio",
    tags=["portfolio"]
)

# Strategy management routes
api_router.include_router(
    strategies.router,
    prefix="/strategies",
    tags=["strategies"]
)

# Trading signals routes
api_router.include_router(
    signals.router,
    prefix="/signals",
    tags=["signals"]
)

# Backtesting routes
api_router.include_router(
    backtesting.router,
    prefix="/backtesting",
    tags=["backtesting"]
)

# Analytics routes
api_router.include_router(
    analytics.router,
    prefix="/analytics",
    tags=["analytics"]
)

# Webhook routes
api_router.include_router(
    webhooks.router,
    prefix="/webhooks",
    tags=["webhooks"]
)

# Admin routes
api_router.include_router(
    admin.router,
    prefix="/admin",
    tags=["admin"]
)

# Ratio Strategy routes (Real-time integration)
api_router.include_router(
    ratio_strategy.router,
    prefix="/strategies",
    tags=["ratio-strategy"]
)

# QSBP Strategy routes
try:
    from ..strategies.qsbp_strategy.api import router as qsbp_router
    api_router.include_router(
        qsbp_router,
        prefix="/strategies",
        tags=["qsbp-strategy"]
    )
except ImportError as e:
    import logging
    logging.getLogger(__name__).warning(f"QSBP strategy router not available: {e}")

# QSBP Production Options Trading routes
try:
    from ..strategies.qsbp_strategy.production_api import router as qsbp_options_router
    api_router.include_router(
        qsbp_options_router,
        tags=["qsbp-options-trading"]
    )
except ImportError as e:
    import logging
    logging.getLogger(__name__).warning(f"QSBP options trading router not available: {e}")
