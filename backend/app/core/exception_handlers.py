"""
Exception handlers for DTrade platform
"""
import logging
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from sqlalchemy.exc import SQLAlchemyError
import traceback

logger = logging.getLogger(__name__)

def setup_exception_handlers(app: FastAPI):
    """Setup global exception handlers"""
    
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        """Handle HTTP exceptions"""
        logger.warning(f"HTTP {exc.status_code}: {exc.detail} - {request.url}")
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": exc.detail, "status_code": exc.status_code}
        )
    
    @app.exception_handler(StarletteHTTPException)
    async def starlette_http_exception_handler(request: Request, exc: StarletteHTTPException):
        """Handle Starlette HTTP exceptions"""
        logger.warning(f"Starlette HTTP {exc.status_code}: {exc.detail} - {request.url}")
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": exc.detail, "status_code": exc.status_code}
        )
    
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        """Handle request validation errors"""
        logger.warning(f"Validation error: {exc.errors()} - {request.url}")
        return JSONResponse(
            status_code=422,
            content={
                "error": "Validation error",
                "details": exc.errors(),
                "status_code": 422
            }
        )
    
    @app.exception_handler(SQLAlchemyError)
    async def sqlalchemy_exception_handler(request: Request, exc: SQLAlchemyError):
        """Handle SQLAlchemy database errors"""
        logger.error(f"Database error: {str(exc)} - {request.url}")
        return JSONResponse(
            status_code=500,
            content={
                "error": "Database error occurred",
                "status_code": 500
            }
        )
    
    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        """Handle all other exceptions"""
        logger.error(f"Unhandled exception: {str(exc)} - {request.url}")
        logger.error(traceback.format_exc())
        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal server error",
                "status_code": 500
            }
        )
