import requests
import pandas as pd
from dhan_token_manager import get_token
from datetime import datetime

BASE_URL = "https://api.dhan.co"

# --- Helper for headers ---
def get_headers():
    return {
        "access-token": get_token(),
        "Content-Type": "application/json"
    }

# --- Instrument Lookup ---
def lookup_instrument(symbol, segment):
    url = f"{BASE_URL}/instruments"
    params = {"segment": segment, "search": symbol}
    resp = requests.get(url, headers=get_headers(), params=params)
    resp.raise_for_status()
    return resp.json()

# --- Market Quote ---
def get_market_quote(instrument_token, segment):
    url = f"{BASE_URL}/market/quote"
    params = {"instrument_token": instrument_token, "exchange_segment": segment}
    resp = requests.get(url, headers=get_headers(), params=params)
    resp.raise_for_status()
    return resp.json()

# --- Option Chain ---
def get_option_chain(symbol, segment):
    url = f"{BASE_URL}/option-chain"
    params = {"symbol": symbol, "exchange_segment": segment}
    resp = requests.get(url, headers=get_headers(), params=params)
    resp.raise_for_status()
    return resp.json()

# --- Historical Data ---
def get_historical_data(instrument_token, segment, interval, from_date, to_date):
    url = f"{BASE_URL}/historical"
    params = {
        "instrument_token": instrument_token,
        "exchange_segment": segment,
        "interval": interval,
        "from_date": from_date,
        "to_date": to_date
    }
    resp = requests.get(url, headers=get_headers(), params=params)
    resp.raise_for_status()
    return pd.DataFrame(resp.json()["data"])

# --- Live Market Feed (WebSocket, not REST) ---
# For live feed, use websocket-client or similar library in your main app.
# This is a placeholder for REST-only usage.
