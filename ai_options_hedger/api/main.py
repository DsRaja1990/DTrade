import sys
import os
import json
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
from dhan_token_manager import get_token, set_token
from dhan_backtest_engine import run_backtest, NIFTY_SYMBOL, SENSEX_SYMBOL, NSE_SEGMENT, BSE_SEGMENT

app = FastAPI()

class TokenRequest(BaseModel):
    access_token: str

class StrategyRequest(BaseModel):
    symbol: str
    segment: str
    order_quantity: int
    interval: Optional[str] = "1d"
    days: Optional[int] = 30

@app.post("/update_token")
def update_token(req: TokenRequest):
    set_token(req.access_token)
    return {"status": "success"}

@app.get("/get_token")
def read_token():
    token = get_token()
    if not token:
        raise HTTPException(status_code=404, detail="Token not set")
    return {"access_token": token}

@app.post("/run_strategy")
def run_strategy(req: StrategyRequest):
    result = run_backtest(req.symbol, req.segment, req.order_quantity, req.interval, req.days)
    return result

@app.post("/run_nifty_sensex")
def run_nifty_sensex(order_quantity: int):
    nifty_result = run_backtest(NIFTY_SYMBOL, NSE_SEGMENT, order_quantity)
    sensex_result = run_backtest(SENSEX_SYMBOL, BSE_SEGMENT, order_quantity)
    return {"nifty": nifty_result, "sensex": sensex_result}
