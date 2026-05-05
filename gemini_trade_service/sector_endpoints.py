"""
BANKNIFTY and FINNIFTY Gemini AI Endpoints
Sector-specific analysis for banking and financial services indices
"""

import json
import logging
import asyncio
from datetime import datetime
from typing import Dict, Optional
from flask import jsonify

logger = logging.getLogger(__name__)

# ============================================================================
# BANKNIFTY-Specific Prompts
# ============================================================================

BANKNIFTY_TIER_1_PROMPT = """
ROLE: Banking Sector Analyst specializing in Indian banking stocks and BANKNIFTY index.
TASK: Analyze 12 major banking stocks that constitute BANKNIFTY index.

INPUT DATA: List of 12 banking stocks with price, % change, volume, RSI, MACD, and bank type (PSU/Private).

LOGIC:
1. Count BULLISH (RSI > 60, price up, positive momentum) vs BEARISH (RSI < 40, price down) vs NEUTRAL banks
2. Calculate WEIGHTED SENTIMENT giving more weight to top 3: HDFC Bank (31%), ICICI Bank (20%), SBI (18%)
3. Identify PSU vs Private bank divergence:
   - PSU banks: SBI, Bank of Baroda, PNB
   - Private banks: HDFC, ICICI, Kotak, Axis, IndusInd, Federal, IDFC First, Bandhan, AU
4. Detect credit cycle signals:
   - If PSU banks outperforming = Government lending push
   - If Private banks outperforming = Credit growth cycle
5. Identify top 3 momentum leaders

OUTPUT FORMAT (JSON ONLY):
{
  "bullish_count": (0 to 12),
  "bearish_count": (0 to 12),
  "neutral_count": (0 to 12),
  "weighted_bias": "BULLISH" | "BEARISH" | "NEUTRAL",
  "strength_score": (0 to 10),
  "psu_sentiment": "BULLISH" | "BEARISH" | "NEUTRAL",
  "private_sentiment": "BULLISH" | "BEARISH" | "NEUTRAL",
  "divergence": "PSU_UP_PRIVATE_DOWN" | "PRIVATE_UP_PSU_DOWN" | "ALIGNED" | "MIXED",
  "top_movers": ["BANK1", "BANK2", "BANK3"],
  "credit_cycle_signal": "EXPANSION" | "CONTRACTION" | "NEUTRAL",
  "reasoning": "1-2 sentence summary focusing on PSU vs Private divergence and credit signals"
}
"""

BANKNIFTY_TIER_2_PROMPT = """
ROLE: BANKNIFTY Options Strategist with expertise in banking sector volatility.
TASK: Formulate intraday BANKNIFTY option trade setup.

INPUT DATA:
1. Tier 1 Analysis (Banking sector sentiment, PSU vs Private divergence)
2. BANKNIFTY Spot Price & RSI
3. Option Chain (ATM Strike, PCR, OI distribution)

LOGIC:
- BANKNIFTY is 1.5x more volatile than NIFTY (wider strikes, faster moves)
- If Bullish Count > 8 AND Private Banks leading AND PCR < 0.8 => Look for CALLS
- If Bearish Count > 8 AND PSU Banks weak AND PCR > 1.2 => Look for PUTS
- Avoid if RSI between 45-55 (choppy zone)
- Strike selection: ATM ± 100 points (BANKNIFTY moves in 100-point increments)
- PSU bank strength = bullish for BANKNIFTY
- Private bank weakness = caution signal

OUTPUT FORMAT (JSON ONLY):
{
  "trade_signal": "BUY_CALL" | "BUY_PUT" | "NO_TRADE",
  "suggested_strike": "45000CE" | "44900PE" | "NONE",
  "entry_price_range": "200-220" | "NONE",
  "stop_loss": "160" | "NONE",
  "target": "300" | "NONE",
  "confidence": "HIGH" | "MEDIUM" | "LOW",
  "risk_reward_ratio": (number like 2.5),
  "volatility_note": "BANKNIFTY volatility is HIGH/MEDIUM/LOW",
  "reasoning": "Short explanation focusing on PSU/Private divergence and banking sector momentum"
}
"""

# ============================================================================
# FINNIFTY-Specific Prompts
# ============================================================================

FINNIFTY_TIER_1_PROMPT = """
ROLE: Financial Services Analyst specializing in FINNIFTY index constituents.
TASK: Analyze 20 financial sector stocks (Banks + NBFCs + Insurance + AMCs).

INPUT DATA: List of 20 financial stocks with price, % change, RSI, and sector classification.

LOGIC:
1. Segment analysis across 4 sectors:
   - Banking: HDFC Bank, ICICI, SBI, Kotak, Axis (50% weight)
   - NBFC: Bajaj Finance, Bajaj Finserv, Cholamandalam, Shriram, Muthoot (30% weight)
   - Insurance: HDFC Life, SBI Life, ICICI Lombard, ICICI Prudential (15% weight)
   - Others: HDFC AMC, SBI Cards, PFC, REC, MCX (5% weight)
2. Identify which segment is LEADING the move
3. Detect sector rotation:
   - Banks up + NBFCs down = Credit tightening
   - NBFCs up + Banks down = Credit expansion
   - Insurance up = Premium growth cycle
4. Calculate weighted sentiment (Banks 50%, NBFCs 30%, Insurance 15%, Others 5%)
5. Identify top 3 momentum stocks

OUTPUT FORMAT (JSON ONLY):
{
  "bullish_count": (0 to 20),
  "bearish_count": (0 to 20),
  "neutral_count": (0 to 20),
  "weighted_bias": "BULLISH" | "BEARISH" | "NEUTRAL",
  "strength_score": (0 to 10),
  "leading_sector": "BANKING" | "NBFC" | "INSURANCE" | "MIXED",
  "banking_sentiment": "BULLISH" | "BEARISH" | "NEUTRAL",
  "nbfc_sentiment": "BULLISH" | "BEARISH" | "NEUTRAL",
  "insurance_sentiment": "BULLISH" | "BEARISH" | "NEUTRAL",
  "divergence": "BANKS_UP_NBFC_DOWN" | "NBFC_UP_BANKS_DOWN" | "INSURANCE_LEADING" | "MIXED",
  "top_movers": ["STOCK1", "STOCK2", "STOCK3"],
  "credit_signal": "EXPANSION" | "TIGHTENING" | "NEUTRAL",
  "reasoning": "1-2 sentence summary focusing on sector rotation and credit cycle"
}
"""

FINNIFTY_TIER_2_PROMPT = """
ROLE: FINNIFTY Options Strategist with expertise in financial services volatility.
TASK: Formulate intraday FINNIFTY option trade setup.

INPUT DATA:
1. Tier 1 Analysis (Financial sector sentiment, Banking vs NBFC vs Insurance)
2. FINNIFTY Spot Price & RSI
3. Option Chain (ATM Strike, PCR, OI distribution)

LOGIC:
- FINNIFTY volatility is 1.3x NIFTY (moderate volatility)
- If Bullish Count > 12 AND Banking+NBFC aligned AND PCR < 0.8 => Look for CALLS
- If Bearish Count > 12 AND Credit tightening signal AND PCR > 1.2 => Look for PUTS
- If Insurance leading but Banks/NBFCs weak => CAUTION (divergence)
- Avoid if RSI between 45-55
- Strike selection: ATM ± 50 points
- NBFC strength = bullish for FINNIFTY
- Banking weakness = caution signal

OUTPUT FORMAT (JSON ONLY):
{
  "trade_signal": "BUY_CALL" | "BUY_PUT" | "NO_TRADE",
  "suggested_strike": "22000CE" | "21950PE" | "NONE",
  "entry_price_range": "120-140" | "NONE",
  "stop_loss": "90" | "NONE",
  "target": "200" | "NONE",
  "confidence": "HIGH" | "MEDIUM" | "LOW",
  "risk_reward_ratio": (number like 2.5),
  "sector_alignment": "ALIGNED" | "DIVERGENT",
  "reasoning": "Short explanation focusing on sector rotation and financial services momentum"
}
"""

# ============================================================================
# Helper Functions
# ============================================================================

async def get_banknifty_tier_1_analysis(sector_analyzer, gemini_client, force_refresh=False):
    """
    Tier 1: BANKNIFTY Stock Screener
    """
    try:
        # Get banking stocks data
        banking_data = await sector_analyzer.analyze_banknifty_stocks()
        
        if not banking_data or 'stocks' not in banking_data:
            logger.error("No BANKNIFTY data available")
            return None
        
        # Call Gemini AI
        tier1_payload = json.dumps(banking_data)
        tier1_response = gemini_client(
            system_prompt=BANKNIFTY_TIER_1_PROMPT,
            user_content=f"Analyze these 12 BANKNIFTY banking stocks: {tier1_payload}"
        )
        
        if tier1_response:
            logger.info(f"BANKNIFTY Tier 1: {tier1_response.get('weighted_bias', 'N/A')} - "
                       f"Score: {tier1_response.get('strength_score', 0)} - "
                       f"Divergence: {tier1_response.get('divergence', 'N/A')}")
        
        return tier1_response
    
    except Exception as e:
        logger.error(f"Error in BANKNIFTY Tier 1 analysis: {e}")
        return None

async def get_finnifty_tier_1_analysis(sector_analyzer, gemini_client, force_refresh=False):
    """
    Tier 1: FINNIFTY Stock Screener
    """
    try:
        # Get financial stocks data
        financial_data = await sector_analyzer.analyze_finnifty_stocks()
        
        if not financial_data or 'stocks' not in financial_data:
            logger.error("No FINNIFTY data available")
            return None
        
        # Call Gemini AI
        tier1_payload = json.dumps(financial_data)
        tier1_response = gemini_client(
            system_prompt=FINNIFTY_TIER_1_PROMPT,
            user_content=f"Analyze these 20 FINNIFTY financial stocks: {tier1_payload}"
        )
        
        if tier1_response:
            logger.info(f"FINNIFTY Tier 1: {tier1_response.get('weighted_bias', 'N/A')} - "
                       f"Score: {tier1_response.get('strength_score', 0)} - "
                       f"Leading: {tier1_response.get('leading_sector', 'N/A')}")
        
        return tier1_response
    
    except Exception as e:
        logger.error(f"Error in FINNIFTY Tier 1 analysis: {e}")
        return None

async def get_banknifty_tier_2_proposal(tier1_analysis, dhan_client, gemini_client):
    """
    Tier 2: BANKNIFTY Strategy Engine
    """
    try:
        # Get BANKNIFTY data (placeholder - would use real Dhan API)
        banknifty_data = {
            'current_price': 45000.0,  # Placeholder
            'rsi': 55.0
        }
        
        # Get option chain (placeholder)
        option_chain_data = {
            'atm_strike': 45000,
            'pcr': 1.0,
            'strikes': []
        }
        
        tier2_input = {
            "tier1_analysis": tier1_analysis,
            "banknifty_spot_price": banknifty_data.get("current_price"),
            "banknifty_rsi": banknifty_data.get("rsi"),
            "option_chain": option_chain_data
        }
        
        # Call Tier 2 AI
        tier2_response = gemini_client(
            system_prompt=BANKNIFTY_TIER_2_PROMPT,
            user_content=f"Formulate BANKNIFTY trade setup: {json.dumps(tier2_input)}"
        )
        
        return tier2_response
    
    except Exception as e:
        logger.error(f"Error in BANKNIFTY Tier 2 analysis: {e}")
        return None

async def get_finnifty_tier_2_proposal(tier1_analysis, dhan_client, gemini_client):
    """
    Tier 2: FINNIFTY Strategy Engine
    """
    try:
        # Get FINNIFTY data (placeholder)
        finnifty_data = {
            'current_price': 22000.0,
            'rsi': 55.0
        }
        
        # Get option chain (placeholder)
        option_chain_data = {
            'atm_strike': 22000,
            'pcr': 1.0,
            'strikes': []
        }
        
        tier2_input = {
            "tier1_analysis": tier1_analysis,
            "finnifty_spot_price": finnifty_data.get("current_price"),
            "finnifty_rsi": finnifty_data.get("rsi"),
            "option_chain": option_chain_data
        }
        
        # Call Tier 2 AI
        tier2_response = gemini_client(
            system_prompt=FINNIFTY_TIER_2_PROMPT,
            user_content=f"Formulate FINNIFTY trade setup: {json.dumps(tier2_input)}"
        )
        
        return tier2_response
    
    except Exception as e:
        logger.error(f"Error in FINNIFTY Tier 2 analysis: {e}")
        return None

# ============================================================================
# TIER 3: Prediction Prompts for BANKNIFTY/FINNIFTY
# ============================================================================

SECTOR_TIER_3_PROMPT = """
ROLE: You are a Price Forecaster for Indian Index Options. Your job is to predict:
1. Maximum price level the index can reach
2. Reversal point after the move
3. Subsequent support/resistance target
4. Hold duration for the trade
5. Exit conditions

INPUT DATA:
1. Tier 2 Trade Proposal (Signal, Strike, Entry, Stop, Target)
2. Tier 1 Sector Analysis (Sector sentiment, divergence)
3. Index technical data (RSI, VWAP, Day High/Low)
4. VIX and macro context

OUTPUT FORMAT (JSON ONLY):
{
  "prediction_confidence": "70%" | "80%" | "90%",
  "forecast_thesis": "2-3 sentence thesis explaining the predicted move",
  "price_action_forecast": {
    "max_level_target": (price number),
    "reversal_point": (price number),
    "subsequent_support_target": (price number if bullish) | "subsequent_resistance_target": (price number if bearish)
  },
  "strategic_recommendation": {
    "action": "HOLD" | "IMMEDIATE_PROFIT_TAKE" | "TRAILING_STOP",
    "hold_duration_minutes": (number 5-30),
    "exit_condition": "Specific condition to exit the trade"
  },
  "risk_factors": ["Risk 1", "Risk 2"]
}
"""

async def get_sector_tier_3_prediction(tier2_proposal, tier1_analysis, index_name, gemini_tier_3_client, dhan_client=None, news_fetcher=None):
    """
    Tier 3: Sector-specific Price Prediction Engine
    Works for BANKNIFTY and FINNIFTY
    """
    try:
        if not tier2_proposal or tier2_proposal.get("trade_signal") == "NO_TRADE":
            return {
                "final_decision": "NO-GO",
                "veto_reason": "No actionable trade from Tier 2",
                "prediction_confidence": "0%"
            }
        
        logger.info(f"[REFRESH] Starting Tier 3 prediction for {index_name}...")
        
        # Get VIX data
        vix_data = {"current": 15.0, "change_pct": 0.0, "trend": "STABLE"}
        if dhan_client:
            try:
                vix_data = dhan_client.get_india_vix()
            except:
                pass
        
        # Get macro data
        macro_data = {}
        if news_fetcher:
            try:
                macro_data = await news_fetcher.get_comprehensive_macro_data()
            except:
                pass
        
        # Prepare Tier 3 input
        tier3_input = {
            "index": index_name,
            "tier2_proposal": tier2_proposal,
            "tier1_summary": tier1_analysis if tier1_analysis else {},
            "india_vix": vix_data,
            "fii_dii": macro_data.get("fii_dii", {}),
            "global_sentiment": macro_data.get("global_markets", {})
        }
        
        # Call Tier 3 AI (gemini-2.0-pro-exp)
        tier3_response = gemini_tier_3_client(
            system_prompt=SECTOR_TIER_3_PROMPT,
            user_content=f"Generate {index_name} price prediction: {json.dumps(tier3_input)}"
        )
        
        if tier3_response:
            logger.info(f"[OK] {index_name} Tier 3 Prediction: {tier3_response.get('prediction_confidence', 'N/A')}")
        
        return tier3_response
    
    except Exception as e:
        logger.error(f"[ERROR] Error in {index_name} Tier 3 prediction: {e}")
        return None
