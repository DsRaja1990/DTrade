"""
Test Legendary API - Standalone
Run on port 5090 for testing
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import uvicorn
from fastapi import FastAPI
from strategy.legendary_live_engine import router as legendary_router

app = FastAPI(title="Legendary Engine API Test", version="1.0")

# Add the legendary router
app.include_router(legendary_router, prefix="/api/legendary", tags=["legendary-engine"])

@app.get("/health")
async def health():
    return {"status": "healthy", "service": "legendary-api-test"}

if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("🏆 LEGENDARY API TEST SERVER")
    print("   Running on http://localhost:5090")
    print("   Endpoints: /api/legendary/status, /api/legendary/scan, /api/legendary/signals")
    print("=" * 70 + "\n")
    uvicorn.run(app, host="0.0.0.0", port=5090, reload=False)
