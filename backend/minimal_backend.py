"""
DTrade - Minimal Backend for Index Scalping Integration Test
Quick start script that bypasses AI engine for compatibility testing
"""

import asyncio
import logging
import sys
from datetime import datetime
from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Add the project root to Python path
sys.path.append(str(Path(__file__).parent))

# Import only the strategies module
from app.strategies.Index_advanced_strategy.routes import router as index_scalping_router

# Create minimal FastAPI app
app = FastAPI(
    title="DTrade - Minimal Backend",
    description="Minimal backend for Index Scalping integration testing",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include only Index Scalping routes
app.include_router(index_scalping_router, prefix="/api/strategies/index-scalping", tags=["Index Scalping"])

@app.get("/")
async def root():
    return {"message": "DTrade Minimal Backend - Index Scalping Integration", "status": "running"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

def main():
    """Run the minimal backend server"""
    print("🚀 Starting DTrade Minimal Backend...")
    print("📊 Index Scalping Integration Test Mode")
    print("🌐 Server will start on: http://localhost:8000")
    print("📋 Available endpoints:")
    print("   - GET  /                                      : Root endpoint")
    print("   - GET  /health                                : Health check")
    print("   - GET  /api/strategies/index-scalping/status  : Get Index Scalping status")
    print("   - POST /api/strategies/index-scalping/start   : Start Index Scalping")
    print("   - POST /api/strategies/index-scalping/stop    : Stop Index Scalping")
    print("   - POST /api/strategies/index-scalping/config  : Update configuration")
    print("⚡ Press Ctrl+C to stop")
    print("-" * 80)
    
    try:
        uvicorn.run(
            "minimal_backend:app",
            host="0.0.0.0",
            port=8000,
            reload=False,
            log_level="info"
        )
    except KeyboardInterrupt:
        print("\n🛑 Server stopped by user")
    except Exception as e:
        print(f"❌ Server error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
