"""
Advanced Stock Screener & Prediction Engine
============================================
ChartInk-like intelligent stock scanner with AI prediction layers

Features:
- Volume Spike Detection
- VWAP Position Analysis
- SuperTrend Calculation
- CPR (Central Pivot Range) Analysis
- Candlestick Pattern Recognition
- OI (Open Interest) Analysis
- PCR (Put-Call Ratio) Monitoring
- 5-Minute Momentum Prediction
- Opening Range Breakout (9:15-10:45 Strategy)
- F&O ELIGIBILITY SCREENING (NEW)

F&O Eligibility Criteria:
- Market Cap: > ₹12,000 Cr
- Avg Daily Volume: > 20 lakh shares
- Cash Turnover: > ₹300-500 Cr/day
- Option OI Near ATM: > 50k-100k contracts
- Futures OI: > ₹500-1000 Cr
- Delivery %: 10-30%
- Volatility: Moderate (not illogically high)
- Free Float: Large & stable

3-Tier AI Architecture:
- Tier 1 (Flash-Lite): Volume, VWAP, Candle Structure
- Tier 2 (Flash): OI, CPR, Trend Coherence, Breakout Score
- Tier 3 (Gemini 3 Pro): Macro, VIX, FII/DII, Prediction

Author: DTrade AI System
"""

import logging
import json
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)

# ============================================================================
# F&O ELIGIBILITY CRITERIA CONFIGURATION
# ============================================================================

@dataclass
class FOEligibilityCriteria:
    """
    Practical Screening Formula for F&O Stocks
    These thresholds determine if a stock is suitable for F&O trading
    """
    # Market Cap in Crores (₹)
    min_market_cap_cr: float = 12000  # > ₹12,000 Cr
    
    # Average Daily Volume in shares
    min_avg_daily_volume: int = 2000000  # > 20 lakh (2 million) shares
    
    # Cash Turnover in Crores (₹) per day
    min_cash_turnover_cr: float = 300  # > ₹300-500 Cr/day
    max_cash_turnover_cr: float = 50000  # Upper limit to avoid manipulation
    
    # Option OI Near ATM in contracts
    min_option_oi_atm: int = 50000  # > 50k-100k contracts
    
    # Futures OI in Crores (₹)
    min_futures_oi_cr: float = 500  # > ₹500-1000 Cr
    
    # Delivery Percentage
    min_delivery_pct: float = 10  # Minimum 10%
    max_delivery_pct: float = 30  # Maximum 30% (too high = illiquid)
    
    # Volatility - Annualized
    min_volatility_pct: float = 15  # Minimum for decent moves
    max_volatility_pct: float = 80  # Not illogically high
    
    # Free Float - as percentage of total shares
    min_free_float_pct: float = 25  # Large & stable free float
    
    # Price Range
    min_price: float = 50  # Minimum stock price
    max_price: float = 50000  # Maximum stock price

# Default criteria instance
FO_ELIGIBILITY = FOEligibilityCriteria()

@dataclass
class FOEligibilityResult:
    """Result of F&O eligibility check"""
    is_eligible: bool
    score: float  # 0-100 eligibility score
    passed_criteria: List[str]
    failed_criteria: List[str]
    warnings: List[str]
    
    # Actual values
    market_cap_cr: float = 0
    avg_daily_volume: int = 0
    cash_turnover_cr: float = 0
    option_oi_atm: int = 0
    futures_oi_cr: float = 0
    delivery_pct: float = 0
    volatility_pct: float = 0
    free_float_pct: float = 0

# ============================================================================
# ENUMS AND DATA CLASSES
# ============================================================================

class SignalType(Enum):
    STRONG_BUY = "STRONG_BUY"
    BUY = "BUY"
    WEAK_BUY = "WEAK_BUY"
    NEUTRAL = "NEUTRAL"
    WEAK_SELL = "WEAK_SELL"
    SELL = "SELL"
    STRONG_SELL = "STRONG_SELL"
    AVOID = "AVOID"
    NOT_FO_ELIGIBLE = "NOT_FO_ELIGIBLE"  # New: Stock not eligible for F&O

class TrendDirection(Enum):
    STRONG_UP = "STRONG_UP"
    UP = "UP"
    SIDEWAYS = "SIDEWAYS"
    DOWN = "DOWN"
    STRONG_DOWN = "STRONG_DOWN"

class MomentumPhase(Enum):
    OPENING_RUSH = "OPENING_RUSH"       # 9:15 - 9:30
    TREND_FORMATION = "TREND_FORMATION"  # 9:30 - 10:00
    BREAKOUT_ZONE = "BREAKOUT_ZONE"      # 10:00 - 10:45
    CONSOLIDATION = "CONSOLIDATION"       # 10:45 - 14:00
    CLOSING_MOVE = "CLOSING_MOVE"         # 14:00 - 15:30

class FOEligibilityStatus(Enum):
    """F&O Eligibility Status"""
    HIGHLY_ELIGIBLE = "HIGHLY_ELIGIBLE"      # Score > 85
    ELIGIBLE = "ELIGIBLE"                     # Score 70-85
    MARGINALLY_ELIGIBLE = "MARGINALLY_ELIGIBLE"  # Score 50-70
    NOT_ELIGIBLE = "NOT_ELIGIBLE"             # Score < 50

@dataclass
class StockScreenResult:
    """Result from stock screening"""
    symbol: str
    name: str
    sector: str
    
    # F&O Eligibility (NEW)
    fo_eligible: bool = True
    fo_eligibility_score: float = 100.0
    fo_eligibility_status: str = "ELIGIBLE"
    fo_eligibility_details: Dict = field(default_factory=dict)
    
    # Price Data
    current_price: float = 0.0
    prev_close: float = 0.0
    day_high: float = 0.0
    day_low: float = 0.0
    change_pct: float = 0.0
    
    # Market Data for F&O Eligibility
    market_cap_cr: float = 0.0
    avg_daily_volume: int = 0
    cash_turnover_cr: float = 0.0
    delivery_pct: float = 0.0
    volatility_pct: float = 0.0
    free_float_pct: float = 0.0
    
    # Volume Analysis
    current_volume: int = 0
    avg_volume: int = 0
    volume_spike_ratio: float = 1.0
    has_volume_spike: bool = False
    
    # VWAP Analysis
    vwap: float = 0.0
    vwap_position: str = "AT_VWAP"  # ABOVE | BELOW | AT_VWAP
    vwap_distance_pct: float = 0.0
    
    # SuperTrend
    supertrend_signal: str = "NEUTRAL"  # BUY | SELL | NEUTRAL
    supertrend_value: float = 0.0
    
    # CPR Analysis
    cpr_top: float = 0.0
    cpr_pivot: float = 0.0
    cpr_bottom: float = 0.0
    cpr_position: str = "INSIDE"  # ABOVE | BELOW | INSIDE
    cpr_width_pct: float = 0.0
    
    # Candlestick
    candle_type: str = "NEUTRAL"  # BULLISH | BEARISH | DOJI | HAMMER | etc.
    candle_body_pct: float = 0.0
    
    # OI Analysis (for F&O stocks)
    call_oi_change: float = 0.0
    put_oi_change: float = 0.0
    oi_interpretation: str = "NEUTRAL"  # CALL_UNWINDING | PUT_UNWINDING | LONG_BUILD | SHORT_BUILD
    pcr: float = 1.0
    option_oi_atm: int = 0
    futures_oi_cr: float = 0.0
    
    # Signals
    buy_signals: List[str] = field(default_factory=list)
    sell_signals: List[str] = field(default_factory=list)
    avoid_reasons: List[str] = field(default_factory=list)
    
    # Final Signal
    signal: SignalType = SignalType.NEUTRAL
    signal_strength: int = 0  # 0-100
    
    # Prediction
    predicted_direction: str = "NEUTRAL"
    predicted_move_pct: float = 0.0
    predicted_duration_mins: int = 0
    prediction_confidence: int = 0
    
    # Trend
    trend_5min: TrendDirection = TrendDirection.SIDEWAYS
    trend_15min: TrendDirection = TrendDirection.SIDEWAYS
    trend_1hour: TrendDirection = TrendDirection.SIDEWAYS
    continuous_trend_bars: int = 0
    
    # Timestamps
    timestamp: str = ""
    momentum_phase: MomentumPhase = MomentumPhase.CONSOLIDATION

# ============================================================================
# NSE F&O ELIGIBLE STOCKS (Updated Dec 2024)
# Only stocks meeting SEBI F&O eligibility criteria
# Source: NSE F&O Stock List
# ============================================================================

# Complete list of NSE F&O eligible stocks with lot sizes and sector info
FO_ELIGIBLE_STOCKS = {
    # NIFTY 50 - All F&O Eligible (Highest liquidity)
    'RELIANCE.NS': {'name': 'Reliance Industries', 'sector': 'Energy', 'lot_size': 250, 'market_cap_cr': 1700000, 'avg_vol_lakh': 150},
    'TCS.NS': {'name': 'TCS', 'sector': 'IT', 'lot_size': 150, 'market_cap_cr': 1350000, 'avg_vol_lakh': 45},
    'HDFCBANK.NS': {'name': 'HDFC Bank', 'sector': 'Banking', 'lot_size': 550, 'market_cap_cr': 1180000, 'avg_vol_lakh': 120},
    'INFY.NS': {'name': 'Infosys', 'sector': 'IT', 'lot_size': 300, 'market_cap_cr': 620000, 'avg_vol_lakh': 85},
    'ICICIBANK.NS': {'name': 'ICICI Bank', 'sector': 'Banking', 'lot_size': 700, 'market_cap_cr': 820000, 'avg_vol_lakh': 180},
    'HINDUNILVR.NS': {'name': 'HUL', 'sector': 'FMCG', 'lot_size': 300, 'market_cap_cr': 550000, 'avg_vol_lakh': 35},
    'ITC.NS': {'name': 'ITC', 'sector': 'FMCG', 'lot_size': 1600, 'market_cap_cr': 560000, 'avg_vol_lakh': 280},
    'SBIN.NS': {'name': 'SBI', 'sector': 'Banking', 'lot_size': 750, 'market_cap_cr': 720000, 'avg_vol_lakh': 350},
    'BHARTIARTL.NS': {'name': 'Bharti Airtel', 'sector': 'Telecom', 'lot_size': 475, 'market_cap_cr': 850000, 'avg_vol_lakh': 95},
    'KOTAKBANK.NS': {'name': 'Kotak Bank', 'sector': 'Banking', 'lot_size': 400, 'market_cap_cr': 350000, 'avg_vol_lakh': 65},
    'LT.NS': {'name': 'L&T', 'sector': 'Infrastructure', 'lot_size': 150, 'market_cap_cr': 480000, 'avg_vol_lakh': 55},
    'AXISBANK.NS': {'name': 'Axis Bank', 'sector': 'Banking', 'lot_size': 600, 'market_cap_cr': 340000, 'avg_vol_lakh': 180},
    'BAJFINANCE.NS': {'name': 'Bajaj Finance', 'sector': 'NBFC', 'lot_size': 125, 'market_cap_cr': 450000, 'avg_vol_lakh': 75},
    'ASIANPAINT.NS': {'name': 'Asian Paints', 'sector': 'Consumer', 'lot_size': 300, 'market_cap_cr': 280000, 'avg_vol_lakh': 28},
    'MARUTI.NS': {'name': 'Maruti', 'sector': 'Auto', 'lot_size': 100, 'market_cap_cr': 380000, 'avg_vol_lakh': 22},
    'TITAN.NS': {'name': 'Titan', 'sector': 'Consumer', 'lot_size': 375, 'market_cap_cr': 320000, 'avg_vol_lakh': 35},
    'SUNPHARMA.NS': {'name': 'Sun Pharma', 'sector': 'Pharma', 'lot_size': 700, 'market_cap_cr': 420000, 'avg_vol_lakh': 65},
    'TATAMOTORS.NS': {'name': 'Tata Motors', 'sector': 'Auto', 'lot_size': 575, 'market_cap_cr': 320000, 'avg_vol_lakh': 380},
    'TATASTEEL.NS': {'name': 'Tata Steel', 'sector': 'Metal', 'lot_size': 425, 'market_cap_cr': 180000, 'avg_vol_lakh': 320},
    'WIPRO.NS': {'name': 'Wipro', 'sector': 'IT', 'lot_size': 1500, 'market_cap_cr': 250000, 'avg_vol_lakh': 120},
    'HCLTECH.NS': {'name': 'HCL Tech', 'sector': 'IT', 'lot_size': 350, 'market_cap_cr': 420000, 'avg_vol_lakh': 55},
    'POWERGRID.NS': {'name': 'Power Grid', 'sector': 'Power', 'lot_size': 2700, 'market_cap_cr': 280000, 'avg_vol_lakh': 180},
    'NTPC.NS': {'name': 'NTPC', 'sector': 'Power', 'lot_size': 1575, 'market_cap_cr': 380000, 'avg_vol_lakh': 220},
    'ONGC.NS': {'name': 'ONGC', 'sector': 'Energy', 'lot_size': 1925, 'market_cap_cr': 320000, 'avg_vol_lakh': 250},
    'COALINDIA.NS': {'name': 'Coal India', 'sector': 'Mining', 'lot_size': 2100, 'market_cap_cr': 280000, 'avg_vol_lakh': 180},
    'BAJAJFINSV.NS': {'name': 'Bajaj Finserv', 'sector': 'NBFC', 'lot_size': 500, 'market_cap_cr': 270000, 'avg_vol_lakh': 45},
    'ADANIENT.NS': {'name': 'Adani Ent', 'sector': 'Conglomerate', 'lot_size': 250, 'market_cap_cr': 380000, 'avg_vol_lakh': 120},
    'JSWSTEEL.NS': {'name': 'JSW Steel', 'sector': 'Metal', 'lot_size': 450, 'market_cap_cr': 220000, 'avg_vol_lakh': 150},
    'TECHM.NS': {'name': 'Tech Mahindra', 'sector': 'IT', 'lot_size': 400, 'market_cap_cr': 160000, 'avg_vol_lakh': 85},
    'INDUSINDBK.NS': {'name': 'IndusInd Bank', 'sector': 'Banking', 'lot_size': 400, 'market_cap_cr': 110000, 'avg_vol_lakh': 95},
    
    # BANKNIFTY Components
    'BANKBARODA.NS': {'name': 'Bank of Baroda', 'sector': 'Banking', 'lot_size': 2500, 'market_cap_cr': 125000, 'avg_vol_lakh': 350},
    'PNB.NS': {'name': 'Punjab National Bank', 'sector': 'Banking', 'lot_size': 4000, 'market_cap_cr': 130000, 'avg_vol_lakh': 450},
    'FEDERALBNK.NS': {'name': 'Federal Bank', 'sector': 'Banking', 'lot_size': 3000, 'market_cap_cr': 42000, 'avg_vol_lakh': 180},
    'IDFCFIRSTB.NS': {'name': 'IDFC First Bank', 'sector': 'Banking', 'lot_size': 6000, 'market_cap_cr': 55000, 'avg_vol_lakh': 280},
    'BANDHANBNK.NS': {'name': 'Bandhan Bank', 'sector': 'Banking', 'lot_size': 2400, 'market_cap_cr': 30000, 'avg_vol_lakh': 150},
    
    # High Volume F&O Stocks
    'ZOMATO.NS': {'name': 'Zomato', 'sector': 'Tech', 'lot_size': 2600, 'market_cap_cr': 220000, 'avg_vol_lakh': 550},
    'PAYTM.NS': {'name': 'Paytm', 'sector': 'Fintech', 'lot_size': 600, 'market_cap_cr': 45000, 'avg_vol_lakh': 180},
    'NYKAA.NS': {'name': 'Nykaa', 'sector': 'Retail', 'lot_size': 2750, 'market_cap_cr': 42000, 'avg_vol_lakh': 85},
    'POLICYBZR.NS': {'name': 'Policy Bazaar', 'sector': 'Fintech', 'lot_size': 375, 'market_cap_cr': 30000, 'avg_vol_lakh': 65},
    
    # Auto Sector
    'M&M.NS': {'name': 'M&M', 'sector': 'Auto', 'lot_size': 350, 'market_cap_cr': 380000, 'avg_vol_lakh': 120},
    'BAJAJ-AUTO.NS': {'name': 'Bajaj Auto', 'sector': 'Auto', 'lot_size': 125, 'market_cap_cr': 240000, 'avg_vol_lakh': 35},
    'EICHERMOT.NS': {'name': 'Eicher Motors', 'sector': 'Auto', 'lot_size': 175, 'market_cap_cr': 130000, 'avg_vol_lakh': 28},
    'HEROMOTOCO.NS': {'name': 'Hero MotoCorp', 'sector': 'Auto', 'lot_size': 150, 'market_cap_cr': 95000, 'avg_vol_lakh': 35},
    'TVSMOTOR.NS': {'name': 'TVS Motor', 'sector': 'Auto', 'lot_size': 175, 'market_cap_cr': 110000, 'avg_vol_lakh': 45},
    'ASHOKLEY.NS': {'name': 'Ashok Leyland', 'sector': 'Auto', 'lot_size': 2500, 'market_cap_cr': 65000, 'avg_vol_lakh': 180},
    'BALKRISIND.NS': {'name': 'Balkrishna Ind', 'sector': 'Auto', 'lot_size': 200, 'market_cap_cr': 52000, 'avg_vol_lakh': 25},
    'MOTHERSON.NS': {'name': 'Motherson Sumi', 'sector': 'Auto', 'lot_size': 3500, 'market_cap_cr': 95000, 'avg_vol_lakh': 220},
    
    # IT Sector
    'LTIM.NS': {'name': 'LTIMindtree', 'sector': 'IT', 'lot_size': 100, 'market_cap_cr': 160000, 'avg_vol_lakh': 25},
    'COFORGE.NS': {'name': 'Coforge', 'sector': 'IT', 'lot_size': 75, 'market_cap_cr': 45000, 'avg_vol_lakh': 15},
    'PERSISTENT.NS': {'name': 'Persistent', 'sector': 'IT', 'lot_size': 100, 'market_cap_cr': 75000, 'avg_vol_lakh': 18},
    'MPHASIS.NS': {'name': 'Mphasis', 'sector': 'IT', 'lot_size': 200, 'market_cap_cr': 48000, 'avg_vol_lakh': 22},
    'LTTS.NS': {'name': 'L&T Tech', 'sector': 'IT', 'lot_size': 100, 'market_cap_cr': 52000, 'avg_vol_lakh': 18},
    
    # Pharma Sector
    'DRREDDY.NS': {'name': "Dr Reddy's", 'sector': 'Pharma', 'lot_size': 125, 'market_cap_cr': 105000, 'avg_vol_lakh': 28},
    'CIPLA.NS': {'name': 'Cipla', 'sector': 'Pharma', 'lot_size': 325, 'market_cap_cr': 120000, 'avg_vol_lakh': 35},
    'DIVISLAB.NS': {'name': "Divi's Labs", 'sector': 'Pharma', 'lot_size': 100, 'market_cap_cr': 95000, 'avg_vol_lakh': 22},
    'APOLLOHOSP.NS': {'name': 'Apollo Hospitals', 'sector': 'Healthcare', 'lot_size': 125, 'market_cap_cr': 95000, 'avg_vol_lakh': 18},
    'BIOCON.NS': {'name': 'Biocon', 'sector': 'Pharma', 'lot_size': 1800, 'market_cap_cr': 38000, 'avg_vol_lakh': 65},
    'AUROPHARMA.NS': {'name': 'Aurobindo Pharma', 'sector': 'Pharma', 'lot_size': 425, 'market_cap_cr': 72000, 'avg_vol_lakh': 55},
    'LUPIN.NS': {'name': 'Lupin', 'sector': 'Pharma', 'lot_size': 425, 'market_cap_cr': 95000, 'avg_vol_lakh': 48},
    
    # Metal & Mining
    'HINDALCO.NS': {'name': 'Hindalco', 'sector': 'Metal', 'lot_size': 925, 'market_cap_cr': 145000, 'avg_vol_lakh': 180},
    'VEDL.NS': {'name': 'Vedanta', 'sector': 'Metal', 'lot_size': 1050, 'market_cap_cr': 165000, 'avg_vol_lakh': 250},
    'NMDC.NS': {'name': 'NMDC', 'sector': 'Mining', 'lot_size': 2250, 'market_cap_cr': 62000, 'avg_vol_lakh': 120},
    'SAIL.NS': {'name': 'SAIL', 'sector': 'Metal', 'lot_size': 3750, 'market_cap_cr': 55000, 'avg_vol_lakh': 320},
    'JINDALSTEL.NS': {'name': 'Jindal Steel', 'sector': 'Metal', 'lot_size': 500, 'market_cap_cr': 95000, 'avg_vol_lakh': 85},
    'NATIONALUM.NS': {'name': 'NALCO', 'sector': 'Metal', 'lot_size': 2750, 'market_cap_cr': 38000, 'avg_vol_lakh': 180},
    
    # FMCG
    'BRITANNIA.NS': {'name': 'Britannia', 'sector': 'FMCG', 'lot_size': 100, 'market_cap_cr': 130000, 'avg_vol_lakh': 18},
    'NESTLEIND.NS': {'name': 'Nestle India', 'sector': 'FMCG', 'lot_size': 20, 'market_cap_cr': 220000, 'avg_vol_lakh': 8},
    'DABUR.NS': {'name': 'Dabur', 'sector': 'FMCG', 'lot_size': 750, 'market_cap_cr': 95000, 'avg_vol_lakh': 45},
    'MARICO.NS': {'name': 'Marico', 'sector': 'FMCG', 'lot_size': 800, 'market_cap_cr': 78000, 'avg_vol_lakh': 55},
    'GODREJCP.NS': {'name': 'Godrej Consumer', 'sector': 'FMCG', 'lot_size': 500, 'market_cap_cr': 115000, 'avg_vol_lakh': 35},
    'COLPAL.NS': {'name': 'Colgate', 'sector': 'FMCG', 'lot_size': 175, 'market_cap_cr': 78000, 'avg_vol_lakh': 18},
    'TATACONSUM.NS': {'name': 'Tata Consumer', 'sector': 'FMCG', 'lot_size': 450, 'market_cap_cr': 105000, 'avg_vol_lakh': 65},
    
    # Energy & Power
    'ADANIGREEN.NS': {'name': 'Adani Green', 'sector': 'Power', 'lot_size': 450, 'market_cap_cr': 280000, 'avg_vol_lakh': 85},
    'ADANIPOWER.NS': {'name': 'Adani Power', 'sector': 'Power', 'lot_size': 1100, 'market_cap_cr': 220000, 'avg_vol_lakh': 120},
    'TATAPOWER.NS': {'name': 'Tata Power', 'sector': 'Power', 'lot_size': 1125, 'market_cap_cr': 145000, 'avg_vol_lakh': 350},
    'GAIL.NS': {'name': 'GAIL', 'sector': 'Energy', 'lot_size': 2750, 'market_cap_cr': 135000, 'avg_vol_lakh': 180},
    'IOC.NS': {'name': 'Indian Oil', 'sector': 'Energy', 'lot_size': 3250, 'market_cap_cr': 195000, 'avg_vol_lakh': 220},
    'BPCL.NS': {'name': 'BPCL', 'sector': 'Energy', 'lot_size': 1800, 'market_cap_cr': 135000, 'avg_vol_lakh': 150},
    'HINDPETRO.NS': {'name': 'HPCL', 'sector': 'Energy', 'lot_size': 1350, 'market_cap_cr': 72000, 'avg_vol_lakh': 180},
    
    # Infrastructure & Construction
    'ADANIPORTS.NS': {'name': 'Adani Ports', 'sector': 'Infrastructure', 'lot_size': 400, 'market_cap_cr': 310000, 'avg_vol_lakh': 95},
    'DLF.NS': {'name': 'DLF', 'sector': 'Real Estate', 'lot_size': 550, 'market_cap_cr': 185000, 'avg_vol_lakh': 75},
    'GODREJPROP.NS': {'name': 'Godrej Properties', 'sector': 'Real Estate', 'lot_size': 325, 'market_cap_cr': 75000, 'avg_vol_lakh': 45},
    'OBEROIRLTY.NS': {'name': 'Oberoi Realty', 'sector': 'Real Estate', 'lot_size': 325, 'market_cap_cr': 65000, 'avg_vol_lakh': 28},
    'PRESTIGE.NS': {'name': 'Prestige Estates', 'sector': 'Real Estate', 'lot_size': 375, 'market_cap_cr': 58000, 'avg_vol_lakh': 35},
    'LODHA.NS': {'name': 'Macrotech Developers', 'sector': 'Real Estate', 'lot_size': 475, 'market_cap_cr': 115000, 'avg_vol_lakh': 55},
    
    # Financials (NBFC & Insurance)
    'HDFCLIFE.NS': {'name': 'HDFC Life', 'sector': 'Insurance', 'lot_size': 700, 'market_cap_cr': 145000, 'avg_vol_lakh': 65},
    'SBILIFE.NS': {'name': 'SBI Life', 'sector': 'Insurance', 'lot_size': 375, 'market_cap_cr': 145000, 'avg_vol_lakh': 48},
    'ICICIPRULI.NS': {'name': 'ICICI Pru Life', 'sector': 'Insurance', 'lot_size': 750, 'market_cap_cr': 85000, 'avg_vol_lakh': 55},
    'ICICIGI.NS': {'name': 'ICICI Lombard', 'sector': 'Insurance', 'lot_size': 275, 'market_cap_cr': 85000, 'avg_vol_lakh': 35},
    'SBICARD.NS': {'name': 'SBI Cards', 'sector': 'NBFC', 'lot_size': 700, 'market_cap_cr': 72000, 'avg_vol_lakh': 65},
    'CHOLAFIN.NS': {'name': 'Cholamandalam', 'sector': 'NBFC', 'lot_size': 500, 'market_cap_cr': 105000, 'avg_vol_lakh': 42},
    'MUTHOOTFIN.NS': {'name': 'Muthoot Finance', 'sector': 'NBFC', 'lot_size': 375, 'market_cap_cr': 72000, 'avg_vol_lakh': 35},
    'SHRIRAMFIN.NS': {'name': 'Shriram Finance', 'sector': 'NBFC', 'lot_size': 250, 'market_cap_cr': 105000, 'avg_vol_lakh': 55},
    'M&MFIN.NS': {'name': 'M&M Finance', 'sector': 'NBFC', 'lot_size': 2000, 'market_cap_cr': 35000, 'avg_vol_lakh': 85},
    'POONAWALLA.NS': {'name': 'Poonawalla Fincorp', 'sector': 'NBFC', 'lot_size': 1000, 'market_cap_cr': 32000, 'avg_vol_lakh': 120},
    
    # Telecom & Media
    'IDEA.NS': {'name': 'Vodafone Idea', 'sector': 'Telecom', 'lot_size': 52000, 'market_cap_cr': 78000, 'avg_vol_lakh': 1200},
    'ZEEL.NS': {'name': 'Zee Entertainment', 'sector': 'Media', 'lot_size': 4500, 'market_cap_cr': 12000, 'avg_vol_lakh': 180},
    'PVR.NS': {'name': 'PVR INOX', 'sector': 'Media', 'lot_size': 407, 'market_cap_cr': 13500, 'avg_vol_lakh': 35},
    
    # Chemicals & Fertilizers
    'PIDILITIND.NS': {'name': 'Pidilite', 'sector': 'Chemicals', 'lot_size': 175, 'market_cap_cr': 145000, 'avg_vol_lakh': 22},
    'SRF.NS': {'name': 'SRF', 'sector': 'Chemicals', 'lot_size': 188, 'market_cap_cr': 72000, 'avg_vol_lakh': 28},
    'ATUL.NS': {'name': 'Atul', 'sector': 'Chemicals', 'lot_size': 50, 'market_cap_cr': 22000, 'avg_vol_lakh': 8},
    'DEEPAKNTR.NS': {'name': 'Deepak Nitrite', 'sector': 'Chemicals', 'lot_size': 250, 'market_cap_cr': 28000, 'avg_vol_lakh': 35},
    'CHAMBLFERT.NS': {'name': 'Chambal Fert', 'sector': 'Fertilizers', 'lot_size': 1000, 'market_cap_cr': 25000, 'avg_vol_lakh': 65},
    'GNFC.NS': {'name': 'GNFC', 'sector': 'Chemicals', 'lot_size': 700, 'market_cap_cr': 15000, 'avg_vol_lakh': 45},
    'COROMANDEL.NS': {'name': 'Coromandel Intl', 'sector': 'Fertilizers', 'lot_size': 375, 'market_cap_cr': 48000, 'avg_vol_lakh': 25},
    
    # Cement
    'ULTRACEMCO.NS': {'name': 'UltraTech Cement', 'sector': 'Cement', 'lot_size': 50, 'market_cap_cr': 320000, 'avg_vol_lakh': 18},
    'SHREECEM.NS': {'name': 'Shree Cement', 'sector': 'Cement', 'lot_size': 25, 'market_cap_cr': 95000, 'avg_vol_lakh': 8},
    'AMBUJACEM.NS': {'name': 'Ambuja Cement', 'sector': 'Cement', 'lot_size': 900, 'market_cap_cr': 135000, 'avg_vol_lakh': 85},
    'ACC.NS': {'name': 'ACC', 'sector': 'Cement', 'lot_size': 250, 'market_cap_cr': 42000, 'avg_vol_lakh': 28},
    'DALBHARAT.NS': {'name': 'Dalmia Bharat', 'sector': 'Cement', 'lot_size': 275, 'market_cap_cr': 35000, 'avg_vol_lakh': 22},
    'RAMCOCEM.NS': {'name': 'Ramco Cement', 'sector': 'Cement', 'lot_size': 550, 'market_cap_cr': 22000, 'avg_vol_lakh': 18},
    
    # Miscellaneous High Volume F&O
    'HAL.NS': {'name': 'HAL', 'sector': 'Defence', 'lot_size': 150, 'market_cap_cr': 280000, 'avg_vol_lakh': 35},
    'BEL.NS': {'name': 'BEL', 'sector': 'Defence', 'lot_size': 1950, 'market_cap_cr': 220000, 'avg_vol_lakh': 180},
    'BHEL.NS': {'name': 'BHEL', 'sector': 'Capital Goods', 'lot_size': 1575, 'market_cap_cr': 95000, 'avg_vol_lakh': 550},
    'SIEMENS.NS': {'name': 'Siemens', 'sector': 'Capital Goods', 'lot_size': 75, 'market_cap_cr': 225000, 'avg_vol_lakh': 15},
    'ABB.NS': {'name': 'ABB India', 'sector': 'Capital Goods', 'lot_size': 125, 'market_cap_cr': 155000, 'avg_vol_lakh': 18},
    'HAVELLS.NS': {'name': 'Havells', 'sector': 'Consumer Durables', 'lot_size': 350, 'market_cap_cr': 105000, 'avg_vol_lakh': 35},
    'VOLTAS.NS': {'name': 'Voltas', 'sector': 'Consumer Durables', 'lot_size': 350, 'market_cap_cr': 58000, 'avg_vol_lakh': 55},
    'WHIRLPOOL.NS': {'name': 'Whirlpool', 'sector': 'Consumer Durables', 'lot_size': 400, 'market_cap_cr': 18000, 'avg_vol_lakh': 15},
    'CROMPTON.NS': {'name': 'Crompton Greaves', 'sector': 'Consumer Durables', 'lot_size': 1400, 'market_cap_cr': 28000, 'avg_vol_lakh': 65},
    'DIXON.NS': {'name': 'Dixon Tech', 'sector': 'Electronics', 'lot_size': 50, 'market_cap_cr': 95000, 'avg_vol_lakh': 22},
    'PAGEIND.NS': {'name': 'Page Industries', 'sector': 'Textiles', 'lot_size': 15, 'market_cap_cr': 42000, 'avg_vol_lakh': 5},
    'TRENT.NS': {'name': 'Trent', 'sector': 'Retail', 'lot_size': 100, 'market_cap_cr': 245000, 'avg_vol_lakh': 28},
    'DMART.NS': {'name': 'DMart', 'sector': 'Retail', 'lot_size': 125, 'market_cap_cr': 245000, 'avg_vol_lakh': 18},
    'CANBK.NS': {'name': 'Canara Bank', 'sector': 'Banking', 'lot_size': 4500, 'market_cap_cr': 95000, 'avg_vol_lakh': 420},
    'UNIONBANK.NS': {'name': 'Union Bank', 'sector': 'Banking', 'lot_size': 4000, 'market_cap_cr': 95000, 'avg_vol_lakh': 380},
    'INDIANB.NS': {'name': 'Indian Bank', 'sector': 'Banking', 'lot_size': 1000, 'market_cap_cr': 72000, 'avg_vol_lakh': 180},
    'RECLTD.NS': {'name': 'REC Ltd', 'sector': 'NBFC', 'lot_size': 1000, 'market_cap_cr': 145000, 'avg_vol_lakh': 180},
    'PFC.NS': {'name': 'PFC', 'sector': 'NBFC', 'lot_size': 1650, 'market_cap_cr': 165000, 'avg_vol_lakh': 220},
    'IRFC.NS': {'name': 'IRFC', 'sector': 'NBFC', 'lot_size': 3800, 'market_cap_cr': 195000, 'avg_vol_lakh': 650},
    'IRCTC.NS': {'name': 'IRCTC', 'sector': 'Travel', 'lot_size': 625, 'market_cap_cr': 72000, 'avg_vol_lakh': 85},
    'INDIGO.NS': {'name': 'Indigo', 'sector': 'Aviation', 'lot_size': 150, 'market_cap_cr': 175000, 'avg_vol_lakh': 55},
    'CONCOR.NS': {'name': 'Container Corp', 'sector': 'Logistics', 'lot_size': 625, 'market_cap_cr': 52000, 'avg_vol_lakh': 45},
    'EXIDEIND.NS': {'name': 'Exide Industries', 'sector': 'Auto Ancillary', 'lot_size': 1200, 'market_cap_cr': 38000, 'avg_vol_lakh': 85},
    'ESCORTS.NS': {'name': 'Escorts Kubota', 'sector': 'Auto', 'lot_size': 150, 'market_cap_cr': 42000, 'avg_vol_lakh': 28},
    'GRASIM.NS': {'name': 'Grasim', 'sector': 'Cement', 'lot_size': 250, 'market_cap_cr': 165000, 'avg_vol_lakh': 35},
    'INDUSTOWER.NS': {'name': 'Indus Towers', 'sector': 'Telecom', 'lot_size': 1400, 'market_cap_cr': 95000, 'avg_vol_lakh': 120},
    'PETRONET.NS': {'name': 'Petronet LNG', 'sector': 'Energy', 'lot_size': 2000, 'market_cap_cr': 55000, 'avg_vol_lakh': 85},
    'MFSL.NS': {'name': 'Max Financial', 'sector': 'Insurance', 'lot_size': 500, 'market_cap_cr': 38000, 'avg_vol_lakh': 45},
    'NAUKRI.NS': {'name': 'Info Edge', 'sector': 'Tech', 'lot_size': 100, 'market_cap_cr': 85000, 'avg_vol_lakh': 18},
    'LICI.NS': {'name': 'LIC', 'sector': 'Insurance', 'lot_size': 700, 'market_cap_cr': 585000, 'avg_vol_lakh': 180},
    'JIOFIN.NS': {'name': 'Jio Financial', 'sector': 'NBFC', 'lot_size': 1500, 'market_cap_cr': 195000, 'avg_vol_lakh': 280},
    'MANKIND.NS': {'name': 'Mankind Pharma', 'sector': 'Pharma', 'lot_size': 200, 'market_cap_cr': 95000, 'avg_vol_lakh': 22},
    'TORNTPHARM.NS': {'name': 'Torrent Pharma', 'sector': 'Pharma', 'lot_size': 225, 'market_cap_cr': 95000, 'avg_vol_lakh': 18},
}

# Create a subset for quick scanning (top 100 most liquid)
SCREENER_STOCKS = FO_ELIGIBLE_STOCKS  # Use all F&O stocks

# Legacy compatibility mapping
NIFTY_50_STOCKS = {k: v for k, v in list(FO_ELIGIBLE_STOCKS.items())[:50]}

# ============================================================================
# F&O ELIGIBILITY CHECKER
# ============================================================================

def check_fo_eligibility(
    symbol: str,
    market_cap_cr: float,
    avg_daily_volume: int,
    current_price: float,
    volatility_pct: float = 30.0,
    cash_turnover_cr: float = 0,
    delivery_pct: float = 15.0,
    option_oi_atm: int = 0,
    futures_oi_cr: float = 0,
    free_float_pct: float = 50.0,
    criteria: FOEligibilityCriteria = FO_ELIGIBILITY
) -> FOEligibilityResult:
    """
    Check if a stock meets F&O eligibility criteria
    
    Practical Screening Formula:
    - Market Cap: > ₹12,000 Cr
    - Avg Daily Volume: > 20 lakh shares
    - Cash Turnover: > ₹300-500 Cr/day
    - Option OI Near ATM: > 50k-100k contracts
    - Futures OI: > ₹500-1000 Cr
    - Delivery %: 10-30%
    - Volatility: Moderate (15-80%)
    - Free Float: Large & stable (>25%)
    """
    passed = []
    failed = []
    warnings = []
    score = 0
    max_score = 100
    
    # 1. Market Cap Check (25 points)
    if market_cap_cr >= criteria.min_market_cap_cr:
        passed.append(f"Market Cap: ₹{market_cap_cr:,.0f} Cr (> ₹{criteria.min_market_cap_cr:,.0f} Cr)")
        score += 25
    else:
        failed.append(f"Market Cap: ₹{market_cap_cr:,.0f} Cr (Required: > ₹{criteria.min_market_cap_cr:,.0f} Cr)")
    
    # 2. Avg Daily Volume Check (20 points)
    avg_vol_lakh = avg_daily_volume / 100000
    if avg_daily_volume >= criteria.min_avg_daily_volume:
        passed.append(f"Avg Volume: {avg_vol_lakh:.1f} lakh (> 20 lakh)")
        score += 20
    else:
        failed.append(f"Avg Volume: {avg_vol_lakh:.1f} lakh (Required: > 20 lakh)")
    
    # 3. Cash Turnover Check (15 points)
    if cash_turnover_cr == 0:
        # Estimate from volume and price
        cash_turnover_cr = (avg_daily_volume * current_price) / 10000000  # Convert to Cr
    
    if cash_turnover_cr >= criteria.min_cash_turnover_cr:
        passed.append(f"Cash Turnover: ₹{cash_turnover_cr:.0f} Cr (> ₹{criteria.min_cash_turnover_cr:.0f} Cr)")
        score += 15
    else:
        failed.append(f"Cash Turnover: ₹{cash_turnover_cr:.0f} Cr (Required: > ₹{criteria.min_cash_turnover_cr:.0f} Cr)")
    
    if cash_turnover_cr > criteria.max_cash_turnover_cr:
        warnings.append(f"Very high turnover: ₹{cash_turnover_cr:.0f} Cr - Check for manipulation")
    
    # 4. Option OI Near ATM (10 points)
    if option_oi_atm > 0:
        if option_oi_atm >= criteria.min_option_oi_atm:
            passed.append(f"Option OI ATM: {option_oi_atm:,} contracts (> 50k)")
            score += 10
        else:
            failed.append(f"Option OI ATM: {option_oi_atm:,} contracts (Required: > 50k)")
    else:
        # If no OI data, give partial score for F&O listed stocks
        if symbol in FO_ELIGIBLE_STOCKS:
            score += 7
            warnings.append("Option OI data not available - Stock is in F&O list")
    
    # 5. Futures OI Check (10 points)
    if futures_oi_cr > 0:
        if futures_oi_cr >= criteria.min_futures_oi_cr:
            passed.append(f"Futures OI: ₹{futures_oi_cr:.0f} Cr (> ₹{criteria.min_futures_oi_cr:.0f} Cr)")
            score += 10
        else:
            failed.append(f"Futures OI: ₹{futures_oi_cr:.0f} Cr (Required: > ₹{criteria.min_futures_oi_cr:.0f} Cr)")
    else:
        # If no OI data, give partial score for F&O listed stocks
        if symbol in FO_ELIGIBLE_STOCKS:
            score += 7
            warnings.append("Futures OI data not available - Stock is in F&O list")
    
    # 6. Delivery Percentage (5 points)
    if criteria.min_delivery_pct <= delivery_pct <= criteria.max_delivery_pct:
        passed.append(f"Delivery %: {delivery_pct:.1f}% (10-30%)")
        score += 5
    elif delivery_pct < criteria.min_delivery_pct:
        warnings.append(f"Low Delivery %: {delivery_pct:.1f}% (May indicate speculation)")
        score += 2
    else:
        warnings.append(f"High Delivery %: {delivery_pct:.1f}% (May be illiquid)")
        score += 3
    
    # 7. Volatility Check (10 points)
    if criteria.min_volatility_pct <= volatility_pct <= criteria.max_volatility_pct:
        passed.append(f"Volatility: {volatility_pct:.1f}% (Moderate)")
        score += 10
    elif volatility_pct < criteria.min_volatility_pct:
        warnings.append(f"Low Volatility: {volatility_pct:.1f}% (Limited movement)")
        score += 5
    else:
        failed.append(f"High Volatility: {volatility_pct:.1f}% (Illogically high - Risky)")
    
    # 8. Free Float Check (5 points)
    if free_float_pct >= criteria.min_free_float_pct:
        passed.append(f"Free Float: {free_float_pct:.1f}% (> 25%)")
        score += 5
    else:
        warnings.append(f"Low Free Float: {free_float_pct:.1f}% (< 25% - Limited liquidity)")
        score += 2
    
    # Determine eligibility
    is_eligible = score >= 50 and len(failed) <= 2
    
    # Bonus for being in NSE F&O list
    if symbol in FO_ELIGIBLE_STOCKS and score < 100:
        score = min(100, score + 10)
        passed.append("NSE F&O Listed Stock (Bonus)")
    
    return FOEligibilityResult(
        is_eligible=is_eligible,
        score=score,
        passed_criteria=passed,
        failed_criteria=failed,
        warnings=warnings,
        market_cap_cr=market_cap_cr,
        avg_daily_volume=avg_daily_volume,
        cash_turnover_cr=cash_turnover_cr,
        option_oi_atm=option_oi_atm,
        futures_oi_cr=futures_oi_cr,
        delivery_pct=delivery_pct,
        volatility_pct=volatility_pct,
        free_float_pct=free_float_pct
    )


def get_fo_eligibility_status(score: float) -> FOEligibilityStatus:
    """Get F&O eligibility status based on score"""
    if score >= 85:
        return FOEligibilityStatus.HIGHLY_ELIGIBLE
    elif score >= 70:
        return FOEligibilityStatus.ELIGIBLE
    elif score >= 50:
        return FOEligibilityStatus.MARGINALLY_ELIGIBLE
    else:
        return FOEligibilityStatus.NOT_ELIGIBLE


def calculate_volatility(closes: List[float], period: int = 20) -> float:
    """Calculate annualized volatility percentage"""
    if len(closes) < period:
        return 30.0  # Default moderate volatility
    
    returns = []
    for i in range(1, len(closes)):
        if closes[i-1] > 0:
            ret = (closes[i] - closes[i-1]) / closes[i-1]
            returns.append(ret)
    
    if not returns:
        return 30.0
    
    daily_vol = np.std(returns)
    annualized_vol = daily_vol * np.sqrt(252) * 100  # Convert to percentage
    
    return min(100, max(5, annualized_vol))


# ============================================================================
# TECHNICAL INDICATOR CALCULATIONS
# ============================================================================

def calculate_vwap(highs: List[float], lows: List[float], closes: List[float], volumes: List[int]) -> float:
    """Calculate Volume Weighted Average Price"""
    if not volumes or sum(volumes) == 0:
        return closes[-1] if closes else 0
    
    typical_prices = [(h + l + c) / 3 for h, l, c in zip(highs, lows, closes)]
    cumulative_tp_vol = sum(tp * vol for tp, vol in zip(typical_prices, volumes))
    cumulative_vol = sum(volumes)
    
    return cumulative_tp_vol / cumulative_vol if cumulative_vol > 0 else 0

def calculate_supertrend(highs: List[float], lows: List[float], closes: List[float], 
                         period: int = 10, multiplier: float = 3.0) -> Tuple[str, float]:
    """
    Calculate SuperTrend indicator
    Returns: (signal: BUY/SELL/NEUTRAL, supertrend_value)
    """
    if len(closes) < period + 1:
        return "NEUTRAL", closes[-1] if closes else 0
    
    # Calculate ATR
    tr_list = []
    for i in range(1, len(closes)):
        tr = max(
            highs[i] - lows[i],
            abs(highs[i] - closes[i-1]),
            abs(lows[i] - closes[i-1])
        )
        tr_list.append(tr)
    
    if len(tr_list) < period:
        return "NEUTRAL", closes[-1]
    
    atr = np.mean(tr_list[-period:])
    
    # Calculate bands
    hl2 = (highs[-1] + lows[-1]) / 2
    upper_band = hl2 + (multiplier * atr)
    lower_band = hl2 - (multiplier * atr)
    
    # Determine trend
    close = closes[-1]
    prev_close = closes[-2] if len(closes) > 1 else close
    
    if close > upper_band:
        return "BUY", lower_band
    elif close < lower_band:
        return "SELL", upper_band
    else:
        # Continue previous trend
        if close > prev_close:
            return "BUY", lower_band
        else:
            return "SELL", upper_band

def calculate_cpr(high: float, low: float, close: float) -> Tuple[float, float, float]:
    """
    Calculate Central Pivot Range
    Returns: (top_cpr, pivot, bottom_cpr)
    """
    pivot = (high + low + close) / 3
    bc = (high + low) / 2  # Bottom Central
    tc = (pivot - bc) + pivot  # Top Central
    
    top_cpr = max(tc, bc)
    bottom_cpr = min(tc, bc)
    
    return top_cpr, pivot, bottom_cpr

def identify_candle_pattern(open_price: float, high: float, low: float, close: float) -> Tuple[str, float]:
    """
    Identify candlestick pattern
    Returns: (pattern_name, body_percentage)
    """
    body = abs(close - open_price)
    total_range = high - low if high != low else 0.01
    body_pct = (body / total_range) * 100
    
    upper_wick = high - max(open_price, close)
    lower_wick = min(open_price, close) - low
    
    # Determine pattern
    if body_pct < 10:
        if upper_wick > body * 2 and lower_wick > body * 2:
            return "DOJI", body_pct
        elif lower_wick > body * 2:
            return "HAMMER", body_pct
        elif upper_wick > body * 2:
            return "SHOOTING_STAR", body_pct
        else:
            return "SPINNING_TOP", body_pct
    
    if close > open_price:
        if body_pct > 70:
            return "STRONG_BULLISH", body_pct
        elif lower_wick > body:
            return "BULLISH_HAMMER", body_pct
        else:
            return "BULLISH", body_pct
    else:
        if body_pct > 70:
            return "STRONG_BEARISH", body_pct
        elif upper_wick > body:
            return "BEARISH_SHOOTING_STAR", body_pct
        else:
            return "BEARISH", body_pct

def detect_volume_spike(current_volume: int, avg_volume: int, threshold: float = 1.5) -> Tuple[bool, float]:
    """
    Detect volume spike
    Returns: (is_spike, ratio)
    """
    if avg_volume == 0:
        return False, 1.0
    
    ratio = current_volume / avg_volume
    return ratio >= threshold, ratio

def calculate_trend_direction(closes: List[float], period: int = 5) -> Tuple[TrendDirection, int]:
    """
    Calculate trend direction and count of continuous bars
    Returns: (direction, continuous_bars)
    """
    if len(closes) < period:
        return TrendDirection.SIDEWAYS, 0
    
    recent = closes[-period:]
    
    # Count consecutive up/down bars
    up_count = 0
    down_count = 0
    
    for i in range(1, len(recent)):
        if recent[i] > recent[i-1]:
            up_count += 1
            down_count = 0
        elif recent[i] < recent[i-1]:
            down_count += 1
            up_count = 0
    
    # Calculate overall change
    change_pct = ((recent[-1] - recent[0]) / recent[0]) * 100 if recent[0] > 0 else 0
    
    if change_pct > 1.5:
        return TrendDirection.STRONG_UP, up_count
    elif change_pct > 0.5:
        return TrendDirection.UP, up_count
    elif change_pct < -1.5:
        return TrendDirection.STRONG_DOWN, down_count
    elif change_pct < -0.5:
        return TrendDirection.DOWN, down_count
    else:
        return TrendDirection.SIDEWAYS, 0

def get_momentum_phase() -> MomentumPhase:
    """Determine current market momentum phase based on time"""
    now = datetime.now()
    current_time = now.time()
    
    from datetime import time as dt_time
    
    if dt_time(9, 15) <= current_time < dt_time(9, 30):
        return MomentumPhase.OPENING_RUSH
    elif dt_time(9, 30) <= current_time < dt_time(10, 0):
        return MomentumPhase.TREND_FORMATION
    elif dt_time(10, 0) <= current_time < dt_time(10, 45):
        return MomentumPhase.BREAKOUT_ZONE
    elif dt_time(10, 45) <= current_time < dt_time(14, 0):
        return MomentumPhase.CONSOLIDATION
    else:
        return MomentumPhase.CLOSING_MOVE

# ============================================================================
# STOCK SCREENER CLASS
# ============================================================================

class StockScreener:
    """
    Advanced Stock Screener with AI Prediction
    Implements ChartInk-like scanning with 3-Tier AI filtering
    
    F&O ELIGIBILITY SCREENING:
    - Only screens stocks eligible for F&O trading
    - Applies practical screening formula:
      * Market Cap > ₹12,000 Cr
      * Avg Daily Volume > 20 lakh shares
      * Cash Turnover > ₹300-500 Cr/day
      * Option OI Near ATM > 50k-100k contracts
      * Futures OI > ₹500-1000 Cr
      * Delivery % 10-30%
      * Volatility: Moderate
      * Free Float: Large & stable
    """
    
    def __init__(self, fo_only: bool = True):
        """
        Initialize Stock Screener
        
        Args:
            fo_only: If True, only screen F&O eligible stocks (default: True)
        """
        self.cache = {}
        self.cache_duration = 30  # seconds
        self.fo_only = fo_only
        self.stocks = FO_ELIGIBLE_STOCKS if fo_only else SCREENER_STOCKS
        self.fo_eligibility_cache = {}
    
    def is_fo_eligible(self, symbol: str) -> bool:
        """Quick check if symbol is in F&O list"""
        return symbol in FO_ELIGIBLE_STOCKS
    
    async def check_stock_fo_eligibility(self, symbol: str, ticker_info: Dict = None) -> FOEligibilityResult:
        """
        Full F&O eligibility check for a stock
        """
        # Check cache first
        if symbol in self.fo_eligibility_cache:
            cache_time, result = self.fo_eligibility_cache[symbol]
            if (datetime.now() - cache_time).seconds < 3600:  # 1 hour cache
                return result
        
        # Get stock info from our database or fetch
        stock_data = self.stocks.get(symbol, {})
        
        market_cap_cr = stock_data.get('market_cap_cr', 0)
        avg_vol_lakh = stock_data.get('avg_vol_lakh', 0)
        avg_daily_volume = avg_vol_lakh * 100000
        
        # If we have ticker info from yfinance, use it
        current_price = 0
        volatility_pct = 30.0
        
        if ticker_info:
            try:
                market_cap = ticker_info.get('marketCap', 0)
                if market_cap:
                    market_cap_cr = market_cap / 10000000  # Convert to Cr
                
                current_price = ticker_info.get('currentPrice', ticker_info.get('regularMarketPrice', 0))
                
                # Calculate volatility if available
                if 'fiftyTwoWeekHigh' in ticker_info and 'fiftyTwoWeekLow' in ticker_info:
                    high = ticker_info['fiftyTwoWeekHigh']
                    low = ticker_info['fiftyTwoWeekLow']
                    if high > 0 and low > 0:
                        volatility_pct = ((high - low) / low) * 100 / 3.46  # Approximate annualized
            except Exception as e:
                logger.debug(f"Error extracting ticker info: {e}")
        
        # Perform eligibility check
        result = check_fo_eligibility(
            symbol=symbol,
            market_cap_cr=market_cap_cr,
            avg_daily_volume=int(avg_daily_volume),
            current_price=current_price,
            volatility_pct=volatility_pct
        )
        
        # Cache result
        self.fo_eligibility_cache[symbol] = (datetime.now(), result)
        
        return result
    
    async def scan_stock(self, symbol: str, skip_fo_check: bool = False) -> Optional[StockScreenResult]:
        """
        Scan a single stock for signals
        
        Args:
            symbol: Stock symbol (e.g., 'RELIANCE.NS')
            skip_fo_check: If True, skip F&O eligibility check (for known F&O stocks)
        """
        try:
            # F&O eligibility pre-check
            if self.fo_only and not skip_fo_check:
                if not self.is_fo_eligible(symbol):
                    logger.info(f"Skipping {symbol} - Not in F&O list")
                    return None
            
            info = self.stocks.get(symbol, {
                'name': symbol.replace('.NS', ''), 
                'sector': 'Unknown', 
                'lot_size': 1,
                'market_cap_cr': 0,
                'avg_vol_lakh': 0
            })
            
            # Fetch data
            ticker = yf.Ticker(symbol)
            
            # Get intraday data (5-minute candles for today)
            hist_1d = ticker.history(period="1d", interval="5m")
            hist_5d = ticker.history(period="5d")
            hist_1mo = ticker.history(period="1mo")  # For volatility calculation
            
            if hist_1d.empty or len(hist_1d) < 3:
                logger.warning(f"Insufficient data for {symbol}")
                return None
            
            # Extract data
            closes = hist_1d['Close'].tolist()
            opens = hist_1d['Open'].tolist()
            highs = hist_1d['High'].tolist()
            lows = hist_1d['Low'].tolist()
            volumes = hist_1d['Volume'].astype(int).tolist()
            
            current_price = closes[-1]
            prev_close = hist_5d['Close'].iloc[-2] if len(hist_5d) > 1 else closes[0]
            day_high = max(highs)
            day_low = min(lows)
            change_pct = ((current_price - prev_close) / prev_close * 100) if prev_close > 0 else 0
            
            # =====================================================
            # F&O ELIGIBILITY CHECK
            # =====================================================
            market_cap_cr = info.get('market_cap_cr', 0)
            avg_vol_lakh = info.get('avg_vol_lakh', 0)
            
            # Calculate avg daily volume from actual data
            avg_daily_volume = int(np.mean(hist_5d['Volume'].tolist())) if not hist_5d.empty else int(avg_vol_lakh * 100000)
            
            # Calculate cash turnover
            cash_turnover_cr = (avg_daily_volume * current_price) / 10000000
            
            # Calculate volatility from 1-month data
            volatility_pct = calculate_volatility(hist_1mo['Close'].tolist()) if not hist_1mo.empty else 30.0
            
            # Check F&O eligibility
            fo_result = await self.check_stock_fo_eligibility(symbol)
            fo_status = get_fo_eligibility_status(fo_result.score)
            
            # Skip non-eligible stocks if fo_only mode
            if self.fo_only and not fo_result.is_eligible:
                logger.info(f"Skipping {symbol} - F&O eligibility score: {fo_result.score}")
                return None
            
            # Volume Analysis
            current_volume = volumes[-1]
            avg_volume = int(np.mean(volumes[:-1])) if len(volumes) > 1 else current_volume
            has_volume_spike, volume_ratio = detect_volume_spike(current_volume, avg_volume)
            
            # VWAP
            vwap = calculate_vwap(highs, lows, closes, volumes)
            vwap_distance_pct = ((current_price - vwap) / vwap * 100) if vwap > 0 else 0
            
            if vwap_distance_pct > 0.3:
                vwap_position = "ABOVE"
            elif vwap_distance_pct < -0.3:
                vwap_position = "BELOW"
            else:
                vwap_position = "AT_VWAP"
            
            # SuperTrend
            supertrend_signal, supertrend_value = calculate_supertrend(highs, lows, closes)
            
            # CPR (using previous day's data)
            if len(hist_5d) > 1:
                prev_high = hist_5d['High'].iloc[-2]
                prev_low = hist_5d['Low'].iloc[-2]
                prev_close_cpr = hist_5d['Close'].iloc[-2]
            else:
                prev_high = day_high
                prev_low = day_low
                prev_close_cpr = prev_close
            
            cpr_top, cpr_pivot, cpr_bottom = calculate_cpr(prev_high, prev_low, prev_close_cpr)
            cpr_width_pct = ((cpr_top - cpr_bottom) / cpr_pivot * 100) if cpr_pivot > 0 else 0
            
            if current_price > cpr_top:
                cpr_position = "ABOVE"
            elif current_price < cpr_bottom:
                cpr_position = "BELOW"
            else:
                cpr_position = "INSIDE"
            
            # Candlestick Pattern
            candle_type, candle_body_pct = identify_candle_pattern(
                opens[-1], highs[-1], lows[-1], closes[-1]
            )
            
            # Trend Analysis
            trend_5min, continuous_bars_5 = calculate_trend_direction(closes, 5)
            trend_15min, _ = calculate_trend_direction(closes, 15) if len(closes) >= 15 else (TrendDirection.SIDEWAYS, 0)
            trend_1hour, _ = calculate_trend_direction(closes, 60) if len(closes) >= 60 else (TrendDirection.SIDEWAYS, 0)
            
            # Build signals
            buy_signals = []
            sell_signals = []
            avoid_reasons = []
            
            # BUY Signals
            if has_volume_spike:
                buy_signals.append("VOLUME_SPIKE")
            if vwap_position == "ABOVE":
                buy_signals.append("PRICE_ABOVE_VWAP")
            if supertrend_signal == "BUY":
                buy_signals.append("SUPERTREND_BUY")
            if cpr_position == "ABOVE":
                buy_signals.append("CPR_BREAKOUT_UP")
            if "BULLISH" in candle_type or candle_type == "HAMMER":
                buy_signals.append(f"CANDLE_{candle_type}")
            if trend_5min in [TrendDirection.UP, TrendDirection.STRONG_UP]:
                buy_signals.append("TREND_UP")
            
            # SELL Signals
            if has_volume_spike and change_pct < 0:
                sell_signals.append("VOLUME_SPIKE_DOWN")
            if vwap_position == "BELOW":
                sell_signals.append("PRICE_BELOW_VWAP")
            if supertrend_signal == "SELL":
                sell_signals.append("SUPERTREND_SELL")
            if cpr_position == "BELOW":
                sell_signals.append("CPR_BREAKDOWN")
            if "BEARISH" in candle_type or candle_type == "SHOOTING_STAR":
                sell_signals.append(f"CANDLE_{candle_type}")
            if trend_5min in [TrendDirection.DOWN, TrendDirection.STRONG_DOWN]:
                sell_signals.append("TREND_DOWN")
            
            # AVOID Reasons
            if cpr_position == "INSIDE":
                avoid_reasons.append("INSIDE_CPR")
            if not has_volume_spike and volume_ratio < 0.8:
                avoid_reasons.append("LOW_VOLUME")
            if vwap_position == "AT_VWAP":
                avoid_reasons.append("HUGGING_VWAP")
            if len(buy_signals) > 0 and len(sell_signals) > 0:
                avoid_reasons.append("CONFLICTING_SIGNALS")
            
            # Determine Final Signal
            buy_score = len(buy_signals)
            sell_score = len(sell_signals)
            
            if len(avoid_reasons) >= 2:
                signal = SignalType.AVOID
                signal_strength = 0
            elif buy_score >= 5:
                signal = SignalType.STRONG_BUY
                signal_strength = min(95, 60 + buy_score * 7)
            elif buy_score >= 3:
                signal = SignalType.BUY
                signal_strength = min(80, 40 + buy_score * 10)
            elif buy_score >= 2:
                signal = SignalType.WEAK_BUY
                signal_strength = 30 + buy_score * 5
            elif sell_score >= 5:
                signal = SignalType.STRONG_SELL
                signal_strength = min(95, 60 + sell_score * 7)
            elif sell_score >= 3:
                signal = SignalType.SELL
                signal_strength = min(80, 40 + sell_score * 10)
            elif sell_score >= 2:
                signal = SignalType.WEAK_SELL
                signal_strength = 30 + sell_score * 5
            else:
                signal = SignalType.NEUTRAL
                signal_strength = 20
            
            # Prediction (basic - will be enhanced by AI)
            if signal in [SignalType.STRONG_BUY, SignalType.BUY]:
                predicted_direction = "UP"
                predicted_move_pct = 0.5 + (signal_strength / 100) * 1.5
                predicted_duration_mins = 15 if get_momentum_phase() in [MomentumPhase.OPENING_RUSH, MomentumPhase.BREAKOUT_ZONE] else 30
            elif signal in [SignalType.STRONG_SELL, SignalType.SELL]:
                predicted_direction = "DOWN"
                predicted_move_pct = -(0.5 + (signal_strength / 100) * 1.5)
                predicted_duration_mins = 15 if get_momentum_phase() in [MomentumPhase.OPENING_RUSH, MomentumPhase.BREAKOUT_ZONE] else 30
            else:
                predicted_direction = "SIDEWAYS"
                predicted_move_pct = 0
                predicted_duration_mins = 0
            
            return StockScreenResult(
                symbol=symbol.replace('.NS', ''),
                name=info['name'],
                sector=info['sector'],
                # F&O Eligibility
                fo_eligible=fo_result.is_eligible,
                fo_eligibility_score=fo_result.score,
                fo_eligibility_status=fo_status.value,
                fo_eligibility_details={
                    'passed': fo_result.passed_criteria,
                    'failed': fo_result.failed_criteria,
                    'warnings': fo_result.warnings
                },
                # Market Data
                market_cap_cr=round(market_cap_cr, 2),
                avg_daily_volume=avg_daily_volume,
                cash_turnover_cr=round(cash_turnover_cr, 2),
                volatility_pct=round(volatility_pct, 2),
                # Price Data
                current_price=round(current_price, 2),
                prev_close=round(prev_close, 2),
                day_high=round(day_high, 2),
                day_low=round(day_low, 2),
                change_pct=round(change_pct, 2),
                current_volume=current_volume,
                avg_volume=avg_volume,
                volume_spike_ratio=round(volume_ratio, 2),
                has_volume_spike=has_volume_spike,
                vwap=round(vwap, 2),
                vwap_position=vwap_position,
                vwap_distance_pct=round(vwap_distance_pct, 2),
                supertrend_signal=supertrend_signal,
                supertrend_value=round(supertrend_value, 2),
                cpr_top=round(cpr_top, 2),
                cpr_pivot=round(cpr_pivot, 2),
                cpr_bottom=round(cpr_bottom, 2),
                cpr_position=cpr_position,
                cpr_width_pct=round(cpr_width_pct, 2),
                candle_type=candle_type,
                candle_body_pct=round(candle_body_pct, 2),
                buy_signals=buy_signals,
                sell_signals=sell_signals,
                avoid_reasons=avoid_reasons,
                signal=signal,
                signal_strength=signal_strength,
                predicted_direction=predicted_direction,
                predicted_move_pct=round(predicted_move_pct, 2),
                predicted_duration_mins=predicted_duration_mins,
                prediction_confidence=signal_strength,
                trend_5min=trend_5min,
                trend_15min=trend_15min,
                trend_1hour=trend_1hour,
                continuous_trend_bars=continuous_bars_5,
                timestamp=datetime.now().isoformat(),
                momentum_phase=get_momentum_phase()
            )
            
        except Exception as e:
            logger.error(f"Error scanning {symbol}: {e}")
            return None
    
    async def scan_all_stocks(self) -> Dict[str, List[StockScreenResult]]:
        """Scan all stocks and categorize by signal"""
        import asyncio
        
        results = {
            "strong_buy": [],
            "buy": [],
            "weak_buy": [],
            "neutral": [],
            "weak_sell": [],
            "sell": [],
            "strong_sell": [],
            "avoid": [],
            "momentum_up": [],      # Continuous uptrend
            "momentum_down": [],    # Continuous downtrend
            "breakout_candidates": [],  # CPR breakout potential
            "volume_movers": []     # High volume activity
        }
        
        for symbol in self.stocks.keys():
            result = await self.scan_stock(symbol)
            if result:
                # Categorize by signal
                if result.signal == SignalType.STRONG_BUY:
                    results["strong_buy"].append(result)
                elif result.signal == SignalType.BUY:
                    results["buy"].append(result)
                elif result.signal == SignalType.WEAK_BUY:
                    results["weak_buy"].append(result)
                elif result.signal == SignalType.STRONG_SELL:
                    results["strong_sell"].append(result)
                elif result.signal == SignalType.SELL:
                    results["sell"].append(result)
                elif result.signal == SignalType.WEAK_SELL:
                    results["weak_sell"].append(result)
                elif result.signal == SignalType.AVOID:
                    results["avoid"].append(result)
                else:
                    results["neutral"].append(result)
                
                # Additional categorization
                if result.trend_5min in [TrendDirection.STRONG_UP, TrendDirection.UP] and result.continuous_trend_bars >= 3:
                    results["momentum_up"].append(result)
                
                if result.trend_5min in [TrendDirection.STRONG_DOWN, TrendDirection.DOWN] and result.continuous_trend_bars >= 3:
                    results["momentum_down"].append(result)
                
                if result.cpr_position == "INSIDE" and result.has_volume_spike:
                    results["breakout_candidates"].append(result)
                
                if result.volume_spike_ratio >= 2.0:
                    results["volume_movers"].append(result)
        
        # Sort each list by signal strength
        for key in results:
            results[key].sort(key=lambda x: x.signal_strength, reverse=True)
        
        return results
    
    def result_to_dict(self, result: StockScreenResult) -> Dict:
        """Convert StockScreenResult to dictionary for JSON response"""
        return {
            "symbol": result.symbol,
            "name": result.name,
            "sector": result.sector,
            # F&O Eligibility (NEW)
            "fo_eligibility": {
                "is_eligible": result.fo_eligible,
                "score": result.fo_eligibility_score,
                "status": result.fo_eligibility_status,
                "details": result.fo_eligibility_details
            },
            # Market Data
            "market_data": {
                "market_cap_cr": result.market_cap_cr,
                "avg_daily_volume": result.avg_daily_volume,
                "cash_turnover_cr": result.cash_turnover_cr,
                "volatility_pct": result.volatility_pct,
                "delivery_pct": result.delivery_pct,
                "free_float_pct": result.free_float_pct
            },
            "price": {
                "current": result.current_price,
                "prev_close": result.prev_close,
                "day_high": result.day_high,
                "day_low": result.day_low,
                "change_pct": result.change_pct
            },
            "volume": {
                "current": result.current_volume,
                "average": result.avg_volume,
                "spike_ratio": result.volume_spike_ratio,
                "has_spike": result.has_volume_spike
            },
            "vwap": {
                "value": result.vwap,
                "position": result.vwap_position,
                "distance_pct": result.vwap_distance_pct
            },
            "supertrend": {
                "signal": result.supertrend_signal,
                "value": result.supertrend_value
            },
            "cpr": {
                "top": result.cpr_top,
                "pivot": result.cpr_pivot,
                "bottom": result.cpr_bottom,
                "position": result.cpr_position,
                "width_pct": result.cpr_width_pct
            },
            "candle": {
                "type": result.candle_type,
                "body_pct": result.candle_body_pct
            },
            "oi": {
                "call_change": result.call_oi_change,
                "put_change": result.put_oi_change,
                "interpretation": result.oi_interpretation,
                "pcr": result.pcr,
                "option_oi_atm": result.option_oi_atm,
                "futures_oi_cr": result.futures_oi_cr
            },
            "signals": {
                "buy": result.buy_signals,
                "sell": result.sell_signals,
                "avoid": result.avoid_reasons
            },
            "final_signal": {
                "signal": result.signal.value,
                "strength": result.signal_strength
            },
            "prediction": {
                "direction": result.predicted_direction,
                "move_pct": result.predicted_move_pct,
                "duration_mins": result.predicted_duration_mins,
                "confidence": result.prediction_confidence
            },
            "trend": {
                "5min": result.trend_5min.value,
                "15min": result.trend_15min.value,
                "1hour": result.trend_1hour.value,
                "continuous_bars": result.continuous_trend_bars
            },
            "momentum_phase": result.momentum_phase.value,
            "timestamp": result.timestamp
        }
    
    async def scan_stocks(
        self, 
        stocks: List[str] = None, 
        min_confidence: float = 60.0,
        signal_filter: str = None
    ) -> List[Dict]:
        """
        Scan stocks and return filtered results as dictionaries
        
        Args:
            stocks: List of stock symbols to scan (None = all stocks)
            min_confidence: Minimum confidence score (0-100)
            signal_filter: Filter by signal type (BUY, SELL, etc.)
        
        Returns:
            List of stock signal dictionaries
        """
        results = []
        target_stocks = stocks if stocks else list(self.stocks.keys())
        
        for symbol in target_stocks:
            try:
                result = await self.scan_stock(symbol)
                if result:
                    # Convert to dict
                    signal_dict = self.result_to_dict(result)
                    
                    # Apply filters
                    confidence = signal_dict.get('confidence', 0)
                    if confidence < min_confidence:
                        continue
                    
                    if signal_filter:
                        signal = signal_dict.get('signal', '')
                        if signal_filter.upper() not in signal.upper():
                            continue
                    
                    # Map signal to trade recommendation
                    signal = signal_dict.get('signal', 'NEUTRAL')
                    if 'BUY' in signal.upper():
                        signal_dict['trade'] = 'BUY'
                    elif 'SELL' in signal.upper():
                        signal_dict['trade'] = 'SELL'
                    else:
                        signal_dict['trade'] = 'SIDEWAYS'
                    
                    results.append(signal_dict)
            except Exception as e:
                logger.error(f"Error scanning {symbol}: {e}")
                continue
        
        # Sort by confidence
        results.sort(key=lambda x: x.get('confidence', 0), reverse=True)
        return results


# Global instance
stock_screener = StockScreener()
