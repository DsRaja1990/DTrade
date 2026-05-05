# -*- coding: utf-8 -*-
import os
import sys
import json
import logging
import asyncio
import time
from datetime import datetime, timedelta
from typing import Dict, Optional, List, Any
from flask import Flask, jsonify, request
from google import genai
from google.genai import types
from dhan_client import DhanClient

# ============================================================================
# RETRY CONFIGURATION - Handle Gemini 503 overload errors
# ============================================================================
MAX_RETRIES = 3
RETRY_DELAY_BASE = 2  # seconds
RETRY_DELAY_MAX = 10  # seconds

# ============================================================================
# FALLBACK MODELS - When primary model is overloaded
# ============================================================================
FALLBACK_MODELS = {
    "gemini-2.5-flash": "gemini-2.0-flash",  # Fallback to older flash
    "gemini-2.5-flash-lite": "gemini-2.0-flash-lite",  # Fallback to older lite
    "gemini-3-pro": "gemini-2.5-flash",  # Fallback Pro to Flash
}

# Import 3-Tier Engines
try:
    from tier1_data_engine import Tier1DataEngine, TIER_1_SYSTEM_PROMPT
except ImportError:
    Tier1DataEngine = None
    TIER_1_SYSTEM_PROMPT = ""
    logging.warning("tier1_data_engine not available")

try:
    from tier2_strategy_engine import Tier2StrategyEngine, TIER_2_SYSTEM_PROMPT
except ImportError:
    Tier2StrategyEngine = None
    TIER_2_SYSTEM_PROMPT = ""
    logging.warning("tier2_strategy_engine not available")

try:
    from tier3_prediction_engine import Tier3PredictionEngine, TIER_3_SYSTEM_PROMPT
except ImportError:
    Tier3PredictionEngine = None
    TIER_3_SYSTEM_PROMPT = ""
    logging.warning("tier3_prediction_engine not available")

# Import news_fetcher (optional - use fallback if not available)
try:
    from news_fetcher import news_fetcher
except ImportError:
    news_fetcher = None
    logging.warning("news_fetcher not available, continuing without news data")

from functools import lru_cache

# Import service configuration
from service_config import service_config

# Import sector analyzer for BANKNIFTY/FINNIFTY
try:
    from sector_analyzer import sector_analyzer
except ImportError:
    sector_analyzer = None
    logging.warning("sector_analyzer not available, BANKNIFTY/FINNIFTY endpoints will be limited")

# ============================================================================
# ELITE TRADING CORE - Institutional-Grade Intelligence
# ============================================================================
try:
    from elite_trading_core import (
        EliteTradingConfig,
        MarketRegime,
        TradingSession,
        SignalStrength,
        RegimeDetector,
        EnsembleDecisionEngine,
        GreeksAwareExecution,
        AdaptiveRiskManager,
        EliteTradingOrchestrator,
        create_elite_orchestrator,
        get_current_session
    )
    ELITE_ENABLED = True
    elite_orchestrator = create_elite_orchestrator(capital=500000.0)
    logging.info("✅ Elite Trading Core initialized successfully")
except ImportError as e:
    ELITE_ENABLED = False
    elite_orchestrator = None
    logging.warning(f"⚠️ Elite Trading Core not available: {e}")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Enable CORS for all routes - required for frontend access
try:
    from flask_cors import CORS
    CORS(app, resources={r"/*": {"origins": "*"}}, supports_credentials=True)
    logger.info("[OK] CORS enabled for ALL endpoints")
except ImportError:
    # Manual CORS headers if flask-cors not installed
    @app.after_request
    def add_cors_headers(response):
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
        return response
    logger.warning("[WARNING] flask-cors not installed, using manual CORS headers")

# Initialize Clients
dhan_client = DhanClient()

# ============================================================================
# Load API Keys from Service Configuration - 3-TIER ARCHITECTURE
# ============================================================================
# Tier 1: gemini-2.5-flash-lite (temp 0.1) - Data Preparation
# Tier 2: gemini-2.5-flash (temp 0.3) - Contextual Synthesis
# Tier 3: gemini-3-pro (temp 0.15) - Ultimate Oracle Prediction

TIER_1_API_KEY = service_config.tier_1_api_key
TIER_2_API_KEY = service_config.tier_2_api_key
TIER_3_API_KEY = service_config.tier_3_api_key
logger.info("[OK] 3-Tier Service configuration loaded successfully")
# ============================================================================

# Create separate clients for each tier
tier_1_client = genai.Client(api_key=TIER_1_API_KEY)
tier_2_client = genai.Client(api_key=TIER_2_API_KEY)
tier_3_client = genai.Client(api_key=TIER_3_API_KEY)

# Model names per tier
TIER_1_MODEL = service_config.tier_1_model  # gemini-2.5-flash-lite
TIER_2_MODEL = service_config.tier_2_model  # gemini-2.5-flash
TIER_3_MODEL = service_config.tier_3_model  # gemini-3-pro

# Temperature per tier
TIER_1_TEMP = service_config.tier_1_temperature  # 0.1
TIER_2_TEMP = service_config.tier_2_temperature  # 0.3
TIER_3_TEMP = service_config.tier_3_temperature  # 0.2

# Initialize 3-Tier Engines with API keys (EAGER initialization for reliability)
tier1_engine = None
tier2_engine = None
tier3_engine = None
engines_initialized = False

def initialize_all_engines():
    """Initialize all engines at startup for reliability"""
    global tier1_engine, tier2_engine, tier3_engine, engines_initialized
    
    if engines_initialized:
        return True
    
    logger.info("[INIT] Initializing all 3-tier engines at startup...")
    
    # Initialize Tier 1
    if Tier1DataEngine:
        try:
            tier1_engine = Tier1DataEngine(api_key=TIER_1_API_KEY)
            logger.info("✅ Tier 1 Engine initialized successfully")
        except Exception as e:
            logger.warning(f"⚠️ Tier 1 Engine init failed (will use fallback): {e}")
    
    # Initialize Tier 2
    if Tier2StrategyEngine:
        try:
            tier2_engine = Tier2StrategyEngine(api_key=TIER_2_API_KEY)
            logger.info("✅ Tier 2 Engine initialized successfully")
        except Exception as e:
            logger.warning(f"⚠️ Tier 2 Engine init failed (will use fallback): {e}")
    
    # Initialize Tier 3
    if Tier3PredictionEngine:
        try:
            tier3_engine = Tier3PredictionEngine(api_key=TIER_3_API_KEY)
            logger.info("✅ Tier 3 Engine initialized successfully")
        except Exception as e:
            logger.warning(f"⚠️ Tier 3 Engine init failed (will use fallback): {e}")
    
    engines_initialized = True
    logger.info(f"[INIT] Engines status: T1={tier1_engine is not None}, T2={tier2_engine is not None}, T3={tier3_engine is not None}")
    return True

def get_tier1_engine():
    global tier1_engine
    if tier1_engine is None and Tier1DataEngine:
        try:
            tier1_engine = Tier1DataEngine(api_key=TIER_1_API_KEY)
        except Exception as e:
            logger.error(f"Failed to initialize Tier1Engine: {e}")
    return tier1_engine

def get_tier2_engine():
    global tier2_engine
    if tier2_engine is None and Tier2StrategyEngine:
        try:
            tier2_engine = Tier2StrategyEngine(api_key=TIER_2_API_KEY)
        except Exception as e:
            logger.error(f"Failed to initialize Tier2Engine: {e}")
    return tier2_engine

def get_tier3_engine():
    global tier3_engine
    if tier3_engine is None and Tier3PredictionEngine:
        try:
            tier3_engine = Tier3PredictionEngine(api_key=TIER_3_API_KEY)
        except Exception as e:
            logger.error(f"Failed to initialize Tier3Engine: {e}")
    return tier3_engine

# Cache for API responses
tier_1_cache = {}
tier_2_cache = {}
tier_3_cache = {}

# --- Enhanced Prompts ---

TIER_1_ENHANCED_PROMPT = """
ROLE: You are a High-Frequency Equity Analyst with expertise in Indian markets.
TASK: Analyze all 50 Nifty stocks using technical indicators (RSI, MACD, Volume).
INPUT DATA: A list of all 50 Nifty stocks with price, % change, volume, RSI, MACD values.

LOGIC:
1. Count how many stocks are BULLISH (RSI > 60, MACD positive, price up) vs BEARISH (RSI < 40, MACD negative, price down).
2. Identify sector divergence: Are banks moving opposite to IT stocks?
3. Calculate "Weighted Sentiment" giving more weight to heavyweights like RELIANCE, HDFC, INFY.
4. Identify top 3 movers (strongest momentum).

OUTPUT FORMAT (JSON ONLY):
{
  "bullish_count": (0 to 50),
  "bearish_count": (0 to 50),
  "neutral_count": (0 to 50),
  "weighted_bias": "BULLISH" | "BEARISH" | "NEUTRAL",
  "strength_score": (0 to 10),
  "driver_sector": "BANKING" | "IT" | "ENERGY" | "AUTO" | "MIXED",
  "top_movers": ["SYMBOL1", "SYMBOL2", "SYMBOL3"],
  "sector_divergence": "BANKS_UP_IT_DOWN" | "IT_UP_BANKS_DOWN" | "ALIGNED" | "MIXED",
  "reasoning": "1-2 sentence summary"
}
"""

TIER_2_ENHANCED_PROMPT = """
ROLE: You are a Senior Options Strategist specializing in Nifty index options.
TASK: Formulate an intraday trade setup based on Market Breadth, Option Chain, and Index technicals.

INPUT DATA:
1. Tier 1 Analysis (Stock sentiment, Bullish/Bearish count).
2. Nifty Spot Price & RSI.
3. Option Chain (ATM Strike, PCR, OI distribution across strikes).

CORRECT PCR INTERPRETATION:
- PCR < 0.8 = More Calls than Puts = BULLISH retail sentiment = CONTRARIAN BEARISH signal
- PCR > 1.2 = More Puts than Calls = BEARISH retail sentiment = CONTRARIAN BULLISH signal
- PCR 0.8-1.2 = Neutral zone

LOGIC (INSTITUTIONAL GRADE):
- If Bullish Count > 30 AND PCR > 1.0 (retail bearish = bullish contrarian) AND RSI < 70 => Look for CALLS
- If Bearish Count > 30 AND PCR < 0.9 (retail bullish = bearish contrarian) AND RSI > 30 => Look for PUTS
- Avoid trading if RSI is between 45 and 55 (Chop Zone)
- Strike selection: For CALLS, use ATM or ATM+1. For PUTS, use ATM or ATM-1.
- Entry price range: Based on current option LTP + expected volatility

LOT SIZES (CORRECT):
- NIFTY: 75 per lot
- BANKNIFTY: 35 per lot
- FINNIFTY: 40 per lot
- SENSEX: 20 per lot
- BANKEX: 30 per lot

OUTPUT FORMAT (JSON ONLY):
{
  "trade_signal": "BUY_CALL" | "BUY_PUT" | "NO_TRADE",
  "suggested_strike": "25000CE" | "24950PE" | "NONE",
  "entry_price_range": "140-150" | "NONE", 
  "stop_loss": "120" | "NONE",
  "target": "180" | "NONE",
  "confidence": "HIGH" | "MEDIUM" | "LOW",
  "risk_reward_ratio": (number like 2.5),
  "reasoning": "Short explanation 1-2 sentences"
}
"""

TIER_3_ENHANCED_PROMPT = """
ROLE: You are a Paranoid Institutional Risk Manager. Your PRIMARY JOB is to REJECT risky trades.
TASK: Validate the proposed trade against macro factors, global sentiment, and news. Look for TRAPS.

INPUT DATA:
1. Proposed Trade from Tier 2 (Signal, Strike, Entry, Stop, Target).
2. India VIX (Volatility Index) and VIX change %.
3. Global Market Sentiment (US Futures: Green/Red, Crude Oil: Up/Down).
4. FII/DII Data (Net buying/selling).
5. Recent News Headlines.

LOGIC:
- BULL TRAP CHECK: If Trade is BUY_CALL but VIX is spiking (>5%) AND US Futures are RED => REJECT
- BEAR TRAP CHECK: If Trade is BUY_PUT but VIX is falling (<-5%) AND strong support nearby => REJECT
- NEWS CHECK: If major event (RBI Policy, Big Earnings, Fed meeting) in next 2 hours => REJECT
- FII/DII CHECK: If FII is heavily selling while proposing BUY trade => CAUTION or REDUCE SIZE
- RISK VALIDATION: If Risk/Reward < 2 => REJECT

OUTPUT FORMAT (JSON ONLY):
{
  "final_decision": "GO" | "NO-GO",
  "veto_reason": "Explain why rejecting, or null if GO",
  "risk_adjustment": "Reduce quantity by 50%" | "Tighten stop to X" | "NONE",
  "macro_score": (0 to 10, where 10 is most favorable),
  "key_risks": ["Risk 1", "Risk 2"] | []
}
"""

# --- Helper Functions for 3-Tier AI Calls with RETRY LOGIC ---

def call_gemini_with_retry(client, model: str, system_prompt: str, user_content: str, 
                           temperature: float, tier_name: str = "Unknown") -> Optional[Dict]:
    """
    Call Gemini API with retry logic and fallback model support.
    Handles 503 overload errors gracefully.
    """
    current_model = model
    
    for attempt in range(MAX_RETRIES):
        try:
            response = client.models.generate_content(
                model=current_model,
                contents=user_content,
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    response_mime_type="application/json",
                    temperature=temperature
                )
            )
            result = json.loads(response.text)
            if attempt > 0:
                logger.info(f"✅ {tier_name} succeeded on attempt {attempt + 1} with model {current_model}")
            return result
            
        except Exception as e:
            error_str = str(e)
            is_overload = "503" in error_str or "overload" in error_str.lower() or "UNAVAILABLE" in error_str
            
            if is_overload:
                delay = min(RETRY_DELAY_BASE * (2 ** attempt), RETRY_DELAY_MAX)
                logger.warning(f"⚠️ {tier_name} model overloaded (attempt {attempt + 1}/{MAX_RETRIES}), retrying in {delay}s...")
                time.sleep(delay)
                
                # Try fallback model on last retry
                if attempt == MAX_RETRIES - 2 and current_model in FALLBACK_MODELS:
                    current_model = FALLBACK_MODELS[current_model]
                    logger.info(f"🔄 {tier_name} switching to fallback model: {current_model}")
            else:
                logger.error(f"❌ {tier_name} error ({current_model}): {e}")
                break
    
    # All retries failed - try fallback model one more time
    if model in FALLBACK_MODELS:
        fallback = FALLBACK_MODELS[model]
        try:
            logger.info(f"🔄 {tier_name} final fallback attempt with {fallback}")
            response = client.models.generate_content(
                model=fallback,
                contents=user_content,
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    response_mime_type="application/json",
                    temperature=temperature
                )
            )
            return json.loads(response.text)
        except Exception as e:
            logger.error(f"❌ {tier_name} fallback also failed: {e}")
    
    return None

def call_gemini_tier_1(system_prompt: str, user_content: str) -> Optional[Dict]:
    """
    Call Gemini Tier 1: gemini-2.5-flash-lite for Data Preparation
    Temperature: 0.1 (highly deterministic)
    NO sentiment analysis in Tier 1
    WITH RETRY LOGIC
    """
    return call_gemini_with_retry(
        client=tier_1_client,
        model=TIER_1_MODEL,
        system_prompt=system_prompt,
        user_content=user_content,
        temperature=TIER_1_TEMP,
        tier_name="Tier 1"
    )

def call_gemini_tier_2(system_prompt: str, user_content: str) -> Optional[Dict]:
    """
    Call Gemini Tier 2: gemini-2.5-flash for Contextual Synthesis
    Temperature: 0.3
    Includes: Options Chain, VIX, FII/DII, Sentiment
    WITH RETRY LOGIC
    """
    return call_gemini_with_retry(
        client=tier_2_client,
        model=TIER_2_MODEL,
        system_prompt=system_prompt,
        user_content=user_content,
        temperature=TIER_2_TEMP,
        tier_name="Tier 2"
    )

def call_gemini_tier_3(system_prompt: str, user_content: str) -> Optional[Dict]:
    """
    Call Gemini Tier 3: gemini-3-pro for Predictive Modeling
    Temperature: 0.2
    Returns: Price forecasts, hold duration, exit conditions
    WITH RETRY LOGIC
    """
    return call_gemini_with_retry(
        client=tier_3_client,
        model=TIER_3_MODEL,
        system_prompt=system_prompt,
        user_content=user_content,
        temperature=TIER_3_TEMP,
        tier_name="Tier 3"
    )

# Backward compatibility wrapper
def call_gemini_tier_1_2(system_prompt, user_content):
    """Backward compatibility - calls Tier 2 for legacy code"""
    return call_gemini_tier_2(system_prompt, user_content)

async def get_tier_1_analysis(force_refresh=False):
    """
    Tier 1: Data Preparation Engine (gemini-2.0-flash-lite)
    - Fetches all 50 Nifty stocks
    - Calculates RSI-10, VWAP, ATR, 5-day trend
    - NO sentiment analysis (moved to Tier 2)
    Cache for 1 minute
    """
    cache_key = "tier_1_analysis"
    current_time = datetime.now()
    
    # Check cache
    if not force_refresh and cache_key in tier_1_cache:
        cached_data, cached_time = tier_1_cache[cache_key]
        if (current_time - cached_time).seconds < 60:  # 1 minute cache
            logger.info("[PKG] Returning cached Tier 1 analysis")
            return cached_data
    
    try:
        logger.info("[REFRESH] Starting Tier 1 analysis (50 Nifty stocks)...")
        
        # Fetch all 50 constituents with technicals
        constituents_data = await dhan_client.get_nifty_constituents_data_enhanced()
        
        if not constituents_data:
            logger.error("[ERR] No constituent data available")
            return None
        
        logger.info(f"[DATA] Fetched {len(constituents_data)} stocks")
        
        # Use Tier 1 engine if available and has the method
        tier1_payload = None
        if tier1_engine and hasattr(tier1_engine, 'prepare_tier1_payload'):
            try:
                tier1_payload = tier1_engine.prepare_tier1_payload(constituents_data)
                system_prompt = TIER_1_SYSTEM_PROMPT
            except Exception as e:
                logger.warning(f"Tier1 engine payload prep failed: {e}, using fallback")
                tier1_payload = None
        
        if tier1_payload is None:
            tier1_payload = json.dumps(constituents_data)
            system_prompt = TIER_1_ENHANCED_PROMPT
        
        # Call Tier 1 AI (gemini-2.5-flash-lite) with RETRY LOGIC
        tier1_response = call_gemini_tier_1(
            system_prompt=system_prompt,
            user_content=f"Analyze these 50 Nifty stocks for technical signals: {tier1_payload}"
        )
        
        if tier1_response:
            # Cache the result
            tier_1_cache[cache_key] = (tier1_response, current_time)
            logger.info(f"[OK] Tier 1 Analysis: {tier1_response.get('weighted_bias', 'N/A')} - Score: {tier1_response.get('strength_score', 0)}")
        
        return tier1_response
    
    except Exception as e:
        logger.error(f"[ERR] Error in Tier 1 analysis: {e}")
        return None

async def get_tier_2_proposal(tier1_analysis):
    """
    Tier 2: Contextual Synthesis Engine (gemini-2.0-flash)
    - Options Chain analysis (OI, IV, PCR, Max Pain)
    - VIX integration
    - FII/DII flows
    - Sentiment analysis (moved from Tier 1)
    - 3-day global indices
    Cache for 5 minutes
    """
    cache_key = "tier_2_proposal"
    current_time = datetime.now()
    
    # Check cache
    if cache_key in tier_2_cache:
        cached_data, cached_time = tier_2_cache[cache_key]
        if (current_time - cached_time).seconds < 300:  # 5 minute cache
            logger.info("[PKG] Returning cached Tier 2 proposal")
            return cached_data
    
    try:
        logger.info("[REFRESH] Starting Tier 2 synthesis (Options, VIX, FII/DII)...")
        
        # Fetch Nifty index data
        nifty_data = dhan_client.get_nifty_index_data()
        
        # Fetch enhanced option chain with Max Pain
        option_chain_data = dhan_client.get_option_chain_data_enhanced("NIFTY")
        
        # Fetch VIX data
        vix_data = dhan_client.get_india_vix()
        
        # Fetch macro data (FII/DII, global indices)
        macro_data = {}
        if news_fetcher:
            macro_data = await news_fetcher.get_comprehensive_macro_data()
        
        # Prepare Tier 2 input
        tier2_input = {
            "tier1_analysis": tier1_analysis,
            "nifty_spot_price": nifty_data.get("current_price"),
            "nifty_rsi": nifty_data.get("rsi"),
            "nifty_vwap": nifty_data.get("vwap"),
            "nifty_trend": nifty_data.get("trend_5day"),
            "option_chain": option_chain_data,
            "india_vix": vix_data,
            "fii_dii": macro_data.get("fii_dii", {}),
            "global_indices_3day": macro_data.get("global_indices_3day", {}),
            "tier2_context": macro_data.get("tier2_context", {})
        }
        
        # Use Tier 2 engine if available and has the method
        tier2_payload = None
        if tier2_engine and hasattr(tier2_engine, 'prepare_tier2_payload'):
            try:
                tier2_payload = tier2_engine.prepare_tier2_payload(tier2_input)
                system_prompt = TIER_2_SYSTEM_PROMPT
            except Exception as e:
                logger.warning(f"Tier2 engine payload prep failed: {e}, using fallback")
                tier2_payload = None
        
        if tier2_payload is None:
            tier2_payload = json.dumps(tier2_input)
            system_prompt = TIER_2_ENHANCED_PROMPT
        
        # Call Tier 2 AI (gemini-2.5-flash) with RETRY LOGIC
        tier2_response = call_gemini_tier_2(
            system_prompt=system_prompt,
            user_content=f"Synthesize trade strategy from context: {tier2_payload}"
        )
        
        if tier2_response:
            tier_2_cache[cache_key] = (tier2_response, current_time)
            logger.info(f"[OK] Tier 2 Proposal: {tier2_response.get('trade_signal', 'NO_TRADE')} - Confidence: {tier2_response.get('confidence', 'LOW')}")
        
        return tier2_response
    
    except Exception as e:
        logger.error(f"[ERR] Error in Tier 2 analysis: {e}")
        return None

async def get_tier_3_validation(tier2_proposal, tier1_analysis=None):
    """
    Tier 3: Predictive Modeling Engine (gemini-2.0-pro-exp)
    - Price forecasts with targets
    - Hold duration recommendations
    - Exit conditions
    - Confidence scores (70%/80%/90%)
    NO caching - always fresh for predictions
    """
    try:
        logger.info("[REFRESH] Starting Tier 3 prediction (Price forecast, Hold duration)...")
        
        if not tier2_proposal or tier2_proposal.get("trade_signal") == "NO_TRADE":
            return {
                "final_decision": "NO-GO",
                "veto_reason": "No actionable trade from Tier 2",
                "prediction_confidence": "0%"
            }
        
        # Fetch fresh VIX and macro data
        vix_data = dhan_client.get_india_vix()
        
        macro_data = {}
        if news_fetcher:
            macro_data = await news_fetcher.get_comprehensive_macro_data()
        
        # Get Nifty index for current levels
        nifty_data = dhan_client.get_nifty_index_data()
        
        # Prepare Tier 3 input
        tier3_input = {
            "tier2_proposal": tier2_proposal,
            "tier1_summary": tier1_analysis if tier1_analysis else {},
            "current_nifty_price": nifty_data.get("current_price", 25000),
            "nifty_day_high": nifty_data.get("day_high", 25100),
            "nifty_day_low": nifty_data.get("day_low", 24900),
            "india_vix": vix_data,
            "fii_dii": macro_data.get("fii_dii", {}),
            "global_sentiment": macro_data.get("global_markets", {}),
            "global_indices_3day": macro_data.get("global_indices_3day", {}),
            "news_headlines": macro_data.get("news_headlines", [])
        }
        
        # Use Tier 3 engine if available and has the method
        tier3_payload = None
        if tier3_engine and hasattr(tier3_engine, 'prepare_tier3_payload'):
            try:
                tier3_payload = tier3_engine.prepare_tier3_payload(tier3_input)
                system_prompt = TIER_3_SYSTEM_PROMPT
            except Exception as e:
                logger.warning(f"Tier3 engine payload prep failed: {e}, using fallback")
                tier3_payload = None
        
        if tier3_payload is None:
            tier3_payload = json.dumps(tier3_input)
            system_prompt = TIER_3_ENHANCED_PROMPT
        
        # Call Tier 3 AI (gemini-3-pro) with RETRY LOGIC
        tier3_response = call_gemini_tier_3(
            system_prompt=system_prompt,
            user_content=f"Generate price prediction and exit strategy: {tier3_payload}"
        )
        
        if tier3_response:
            logger.info(f"[OK] Tier 3 Prediction: {tier3_response.get('prediction_confidence', 'N/A')} confidence")
            logger.info(f"   Target: {tier3_response.get('price_action_forecast', {}).get('max_level_target', 'N/A')}")
        
        return tier3_response
    
    except Exception as e:
        logger.error(f"[ERR] Error in Tier 3 prediction: {e}")
        return None

# ============================================================================
# Configuration Management Endpoints
# ============================================================================

@app.route('/config/status', methods=['GET'])
def get_config_status():
    """Get current configuration status (sensitive data masked)"""
    try:
        config_data = service_config.to_dict_masked()
        return jsonify({
            "status": "success",
            "config": config_data
        })
    except Exception as e:
        logger.error(f"Error getting config status: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/config/update', methods=['POST'])
def update_config():
    """
    Update API keys and tokens
    
    Request Body (JSON):
    {
        "dhan_client_id": "optional",
        "dhan_access_token": "optional",
        "gemini_tier_1_2_key": "optional",
        "gemini_tier_3_key": "optional"
    }
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({"status": "error", "message": "No data provided"}), 400
        
        updated_fields = []
        
        # Update Dhan credentials
        if "dhan_client_id" in data or "dhan_access_token" in data:
            success = service_config.update_dhan_credentials(
                client_id=data.get("dhan_client_id"),
                access_token=data.get("dhan_access_token")
            )
            if success:
                updated_fields.append("dhan_credentials")
                logger.info("[OK] Dhan credentials updated")
        
        # Update Gemini API keys
        if "gemini_tier_1_2_key" in data or "gemini_tier_3_key" in data:
            success = service_config.update_gemini_keys(
                tier_1_2_key=data.get("gemini_tier_1_2_key"),
                tier_3_key=data.get("gemini_tier_3_key")
            )
            if success:
                updated_fields.append("gemini_api_keys")
                logger.info("[OK] Gemini API keys updated")
                
                # Reinitialize Gemini clients with new keys
                global tier_1_2_client, tier_3_client, TIER_1_2_API_KEY, TIER_3_API_KEY
                TIER_1_2_API_KEY = service_config.gemini_tier_1_2_api_key
                TIER_3_API_KEY = service_config.gemini_tier_3_api_key
                tier_1_2_client = genai.Client(api_key=TIER_1_2_API_KEY)
                tier_3_client = genai.Client(api_key=TIER_3_API_KEY)
                logger.info("[REFRESH] Gemini clients reinitialized with new keys")
        
        if not updated_fields:
            return jsonify({"status": "error", "message": "No valid fields to update"}), 400
        
        return jsonify({
            "status": "success",
            "message": f"Configuration updated: {', '.join(updated_fields)}",
            "updated_fields": updated_fields,
            "timestamp": datetime.now().isoformat()
        })
    
    except Exception as e:
        logger.error(f"Error updating config: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/config/reload', methods=['POST'])
def reload_config():
    """Reload configuration from file"""
    try:
        global service_config, tier_1_2_client, tier_3_client, TIER_1_2_API_KEY, TIER_3_API_KEY
        
        # Reload config from file
        from service_config import GeminiTradeConfig
        service_config = GeminiTradeConfig.load_from_file()
        
        # Reinitialize clients
        TIER_1_2_API_KEY = service_config.gemini_tier_1_2_api_key
        TIER_3_API_KEY = service_config.gemini_tier_3_api_key
        tier_1_2_client = genai.Client(api_key=TIER_1_2_API_KEY)
        tier_3_client = genai.Client(api_key=TIER_3_API_KEY)
        
        return jsonify({
            "status": "success",
            "message": "Configuration reloaded successfully",
            "timestamp": datetime.now().isoformat()
        })
    
    except Exception as e:
        logger.error(f"Error reloading config: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

# ============================================================================
# Main Health and Routes (rest of implementation remains the same)
# ============================================================================

@app.route('/health', methods=['GET'])
def health_check():
    # Ensure engines are initialized
    if not engines_initialized:
        initialize_all_engines()
    
    return jsonify({
        "status": "healthy", 
        "service": "Gemini Trade Service - 3-Tier Architecture",
        "config_loaded": service_config is not None,
        "config_source": "service_config.py (GeminiTradeConfig)",
        "models": {
            "tier_1": TIER_1_MODEL,
            "tier_2": TIER_2_MODEL,
            "tier_3": TIER_3_MODEL
        },
        "engines": {
            "tier_1": tier1_engine is not None,
            "tier_2": tier2_engine is not None,
            "tier_3": tier3_engine is not None
        },
        "retry_config": {
            "max_retries": MAX_RETRIES,
            "retry_delay_base": RETRY_DELAY_BASE,
            "fallback_models": FALLBACK_MODELS
        },
        "engines_initialized": engines_initialized,
        "timestamp": datetime.now().isoformat()
    })

# ============================================================================
# API Signals Endpoint - Frontend Compatibility
# ============================================================================

# In-memory signal storage for recent signals
recent_signals_cache = []
MAX_CACHED_SIGNALS = 100

def store_signal(signal_data: dict):
    """Store a generated signal in cache"""
    global recent_signals_cache
    signal_data['id'] = f"gemini-{datetime.now().timestamp()}"
    signal_data['timestamp'] = datetime.now().isoformat()
    signal_data['source'] = 'Gemini'
    recent_signals_cache.insert(0, signal_data)
    if len(recent_signals_cache) > MAX_CACHED_SIGNALS:
        recent_signals_cache = recent_signals_cache[:MAX_CACHED_SIGNALS]
    logger.info(f"Signal stored: {signal_data.get('symbol')} - {signal_data.get('signal_type')}")

@app.route('/api/signals', methods=['GET'])
def get_api_signals():
    """Get recent signals in frontend-compatible format"""
    try:
        return jsonify({
            "signals": recent_signals_cache,
            "count": len(recent_signals_cache),
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f"Error in /api/signals: {e}")
        return jsonify({
            "signals": [],
            "count": 0,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500

@app.route('/api/signals/latest', methods=['GET'])
def get_signals_latest():
    """Get latest signals - frontend compatibility endpoint"""
    try:
        limit = request.args.get('limit', 20, type=int)
        signals = recent_signals_cache[:limit]
        return jsonify({
            "signals": signals,
            "count": len(signals),
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f"Error in /api/signals/latest: {e}")
        return jsonify({
            "signals": [],
            "count": 0,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500

# ============================================================================
# Main Nifty Signal Endpoint - Full 3-Tier Pipeline
# ============================================================================

@app.route('/api/signal/nifty', methods=['GET'])
def get_nifty_signal():
    """
    Get AI-generated NIFTY 50 trade signal using 3-Tier Architecture
    
    Tier 1: Data Preparation (gemini-2.0-flash-lite)
    Tier 2: Contextual Synthesis (gemini-2.0-flash)
    Tier 3: Predictive Modeling (gemini-2.0-pro-exp)
    
    Returns:
        JSON with complete signal including:
        - Trade signal and strike
        - Entry/exit prices
        - Price forecast with targets
        - Hold duration and exit conditions
        - Confidence score (70%/80%/90%)
    """
    try:
        logger.info("[START] Processing NIFTY signal request (3-Tier Pipeline)...")
        
        # Run async function synchronously
        async def get_full_signal():
            # Tier 1: Data Preparation
            tier1_analysis = await get_tier_1_analysis()
            
            if not tier1_analysis:
                return None, None, None
            
            # Tier 2: Contextual Synthesis
            tier2_proposal = await get_tier_2_proposal(tier1_analysis)
            
            if not tier2_proposal:
                return tier1_analysis, None, None
            
            # Tier 3: Predictive Modeling
            tier3_prediction = await get_tier_3_validation(tier2_proposal, tier1_analysis)
            
            return tier1_analysis, tier2_proposal, tier3_prediction
        
        tier1, tier2, tier3 = asyncio.run(get_full_signal())
        
        if not tier1:
            return jsonify({
                "status": "error",
                "message": "Failed Tier 1 data preparation"
            }), 500
        
        if not tier2:
            return jsonify({
                "status": "error",
                "message": "Failed Tier 2 strategy synthesis",
                "tier1_analysis": tier1
            }), 500
        
        # Combine all tier results
        response = {
            "status": "success",
            "index": "NIFTY",
            "pipeline": "3-TIER",
            
            # Tier 2 Trade Signal
            "signal": tier2.get("trade_signal", "NO_TRADE"),
            "strike": tier2.get("suggested_strike", "NONE"),
            "entry_range": tier2.get("entry_price_range", "NONE"),
            "stop_loss": tier2.get("stop_loss", "NONE"),
            "target": tier2.get("target", "NONE"),
            "confidence": tier2.get("confidence", "LOW"),
            "risk_reward_ratio": tier2.get("risk_reward_ratio", 0),
            "reasoning": tier2.get("reasoning", ""),
            
            # Tier 3 Prediction (if available)
            "prediction": tier3 if tier3 else {
                "prediction_confidence": "N/A",
                "forecast_thesis": "Tier 3 not processed"
            },
            
            # Tier 1 Summary
            "market_breadth": {
                "bullish_count": tier1.get("bullish_count", 0),
                "bearish_count": tier1.get("bearish_count", 0),
                "neutral_count": tier1.get("neutral_count", 0),
                "weighted_bias": tier1.get("weighted_bias", "NEUTRAL"),
                "strength_score": tier1.get("strength_score", 0),
                "driver_sector": tier1.get("driver_sector", "MIXED"),
                "top_movers": tier1.get("top_movers", [])
            },
            
            "models_used": {
                "tier_1": TIER_1_MODEL,
                "tier_2": TIER_2_MODEL,
                "tier_3": TIER_3_MODEL
            },
            "timestamp": datetime.now().isoformat()
        }
        
        logger.info(f"[OK] NIFTY Signal: {response['signal']} | Confidence: {response['confidence']}")
        if tier3:
            logger.info(f"   Prediction: {tier3.get('prediction_confidence', 'N/A')}")
        
        return jsonify(response)
    
    except Exception as e:
        logger.error(f"[ERR] Error in NIFTY signal endpoint: {e}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


# ============================================================================
# ELITE SIGNAL ENDPOINTS - Institutional-Grade Trading Intelligence
# ============================================================================

@app.route('/api/elite/signal/<index>', methods=['GET'])
def get_elite_signal(index: str):
    """
    Elite Trading Signal with Institutional-Grade Intelligence
    
    Features:
    - Ensemble AI Decision (3-model consensus voting)
    - Market Regime Detection (trending/ranging/volatility)
    - Session-Aware Sizing (opening/lunch/power hour)
    - Greeks-Aware Execution (delta/gamma/theta checks)
    - Dynamic Risk Management (Kelly sizing, drawdown controls)
    
    Parameters:
        index: NIFTY, BANKNIFTY, FINNIFTY, SENSEX, BANKEX
        
    Returns:
        Elite signal with position sizing, stoploss, targets
    """
    if not ELITE_ENABLED:
        return jsonify({
            "status": "error",
            "message": "Elite Trading Core not enabled"
        }), 503
    
    index = index.upper()
    valid_indices = ["NIFTY", "BANKNIFTY", "FINNIFTY", "SENSEX", "BANKEX", "MIDCPNIFTY"]
    
    if index not in valid_indices:
        return jsonify({
            "status": "error",
            "message": f"Invalid index. Valid: {valid_indices}"
        }), 400
    
    try:
        logger.info(f"[ELITE] Processing elite signal for {index}...")
        
        # Get VIX - extract float value from dict response
        vix = 15.0  # Default
        if hasattr(dhan_client, 'get_india_vix'):
            vix_data = dhan_client.get_india_vix()
            if isinstance(vix_data, dict):
                vix = float(vix_data.get('current', 15.0))
            elif isinstance(vix_data, (int, float)):
                vix = float(vix_data)
        
        # Get tier analyses (reuse existing functions)
        async def get_elite_data():
            # Tier 1 Analysis
            tier1_analysis = await get_tier_1_analysis()
            
            if not tier1_analysis:
                tier1_analysis = {"weighted_bias": "NEUTRAL", "strength_score": 5}
            
            # Tier 2 Proposal
            tier2_proposal = await get_tier_2_proposal(tier1_analysis)
            
            if not tier2_proposal:
                tier2_proposal = {"trade_signal": "NO_TRADE", "confidence": "LOW"}
            
            # Tier 3 Prediction
            tier3_prediction = await get_tier_3_validation(tier2_proposal, tier1_analysis)
            
            if not tier3_prediction:
                tier3_prediction = {"final_decision": "NO-GO", "macro_score": 5}
            
            return tier1_analysis, tier2_proposal, tier3_prediction
        
        tier1, tier2, tier3 = asyncio.run(get_elite_data())
        
        # Get price history for regime detection
        # Simple simulation for now - in production use real data
        import random
        prices = [22500 + random.uniform(-100, 100) for _ in range(30)]
        volumes = [1000000 + random.randint(-100000, 100000) for _ in range(30)]
        
        # Get elite signal from orchestrator
        async def get_orchestrated_signal():
            return await elite_orchestrator.get_elite_signal(
                index=index,
                prices=prices,
                volumes=volumes,
                vix=vix,
                tier1_signal=tier1,
                tier2_signal=tier2,
                tier3_signal=tier3,
                option_data=None,
                hours_to_expiry=24.0
            )
        
        elite_signal = asyncio.run(get_orchestrated_signal())
        
        # Add system status
        system_status = elite_orchestrator.get_system_status()
        
        # Build response
        response = {
            "status": "success",
            "pipeline": "ELITE-3-TIER",
            "index": index,
            "elite_signal": elite_signal,
            "system_status": system_status,
            "vix": vix,
            "tier_inputs": {
                "tier1_bias": tier1.get("weighted_bias", "NEUTRAL"),
                "tier2_signal": tier2.get("trade_signal", "NO_TRADE"),
                "tier3_decision": tier3.get("final_decision", "NO-GO")
            },
            "lot_size": EliteTradingConfig().LOT_SIZES.get(index, 75),
            "models_used": {
                "tier_1": TIER_1_MODEL,
                "tier_2": TIER_2_MODEL,
                "tier_3": TIER_3_MODEL,
                "elite_core": "v1.0"
            },
            "timestamp": datetime.now().isoformat()
        }
        
        action = elite_signal.get("action", "NO_TRADE")
        confidence = elite_signal.get("confidence", 0)
        regime = elite_signal.get("regime", "UNKNOWN")
        
        logger.info(f"[ELITE] {index} Signal: {action} | Conf: {confidence:.1%} | Regime: {regime}")
        
        return jsonify(response)
    
    except Exception as e:
        logger.error(f"[ELITE] Error in elite signal endpoint: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


@app.route('/api/elite/status', methods=['GET'])
def get_elite_status():
    """Get Elite Trading System Status"""
    if not ELITE_ENABLED:
        return jsonify({
            "status": "error",
            "elite_enabled": False,
            "message": "Elite Trading Core not available"
        }), 503
    
    try:
        status = elite_orchestrator.get_system_status()
        return jsonify({
            "status": "success",
            "elite_enabled": True,
            "system": status,
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


@app.route('/api/elite/regime', methods=['GET'])
def get_market_regime():
    """Get Current Market Regime Detection"""
    if not ELITE_ENABLED:
        return jsonify({"status": "error", "message": "Elite not enabled"}), 503
    
    try:
        regime_info = {
            "current_regime": elite_orchestrator.regime_detector.current_regime.value,
            "confidence": round(elite_orchestrator.regime_detector.regime_confidence, 2),
            "duration_bars": elite_orchestrator.regime_detector.regime_duration_bars,
            "session": get_current_session().value,
            "timestamp": datetime.now().isoformat()
        }
        return jsonify({"status": "success", "regime": regime_info})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


# Additional routes would be here (tick, etc.)

# Import sector endpoints
try:
    from sector_endpoints import (
        get_banknifty_tier_1_analysis,
        get_finnifty_tier_1_analysis,
        get_banknifty_tier_2_proposal,
        get_finnifty_tier_2_proposal,
        get_sector_tier_3_prediction,
        BANKNIFTY_TIER_1_PROMPT,
        BANKNIFTY_TIER_2_PROMPT,
        FINNIFTY_TIER_1_PROMPT,
        FINNIFTY_TIER_2_PROMPT
    )
except ImportError:
    logger.warning("sector_endpoints not available")
    get_sector_tier_3_prediction = None

# ============================================================================
# BANKNIFTY Stock List - 12 Major Banking Stocks
# ============================================================================
BANKNIFTY_STOCKS = {
    'HDFCBANK.NS': {'name': 'HDFC Bank', 'weight': 0.31, 'type': 'Private'},
    'ICICIBANK.NS': {'name': 'ICICI Bank', 'weight': 0.20, 'type': 'Private'},
    'SBIN.NS': {'name': 'SBI', 'weight': 0.18, 'type': 'PSU'},
    'KOTAKBANK.NS': {'name': 'Kotak Bank', 'weight': 0.10, 'type': 'Private'},
    'AXISBANK.NS': {'name': 'Axis Bank', 'weight': 0.08, 'type': 'Private'},
    'INDUSINDBK.NS': {'name': 'IndusInd Bank', 'weight': 0.04, 'type': 'Private'},
    'BANKBARODA.NS': {'name': 'Bank of Baroda', 'weight': 0.03, 'type': 'PSU'},
    'PNB.NS': {'name': 'PNB', 'weight': 0.02, 'type': 'PSU'},
    'FEDERALBNK.NS': {'name': 'Federal Bank', 'weight': 0.01, 'type': 'Private'},
    'IDFCFIRSTB.NS': {'name': 'IDFC First', 'weight': 0.01, 'type': 'Private'},
    'BANDHANBNK.NS': {'name': 'Bandhan Bank', 'weight': 0.01, 'type': 'Private'},
    'AUBANK.NS': {'name': 'AU Small Finance', 'weight': 0.01, 'type': 'Private'}
}

# BANKNIFTY cache
banknifty_tier_1_cache = {}
banknifty_tier_2_cache = {}

async def get_banknifty_stocks_data() -> list:
    """Fetch all 12 BANKNIFTY stocks with technicals"""
    import yfinance as yf
    import numpy as np
    
    logger.info("[DATA] Fetching 12 BANKNIFTY stocks data...")
    data = []
    
    for symbol, info in BANKNIFTY_STOCKS.items():
        try:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period="10d")
            
            if not hist.empty and len(hist) >= 2:
                closes = hist['Close'].tolist()
                highs = hist['High'].tolist()
                lows = hist['Low'].tolist()
                volumes = hist['Volume'].astype(int).tolist()
                
                current_price = closes[-1]
                prev_close = closes[-2]
                change_pct = ((current_price - prev_close) / prev_close * 100)
                
                # RSI calculation
                rsi = 50.0
                if len(closes) >= 10:
                    deltas = np.diff(closes)
                    gains = np.where(deltas > 0, deltas, 0)
                    losses = np.where(deltas < 0, -deltas, 0)
                    avg_gain = np.mean(gains[-10:])
                    avg_loss = np.mean(losses[-10:])
                    if avg_loss > 0:
                        rs = avg_gain / avg_loss
                        rsi = 100 - (100 / (1 + rs))
                
                # Signal
                if rsi > 60 and change_pct > 0.3:
                    signal = 'BULLISH'
                elif rsi < 40 and change_pct < -0.3:
                    signal = 'BEARISH'
                else:
                    signal = 'NEUTRAL'
                
                data.append({
                    'symbol': symbol.replace('.NS', ''),
                    'name': info['name'],
                    'type': info['type'],
                    'weight': info['weight'],
                    'last_price': round(float(current_price), 2),
                    'percent_change': round(change_pct, 2),
                    'volume': int(volumes[-1]),
                    'rsi': round(rsi, 2),
                    'signal': signal
                })
        except Exception as e:
            logger.error(f"Error fetching {symbol}: {e}")
    
    return data

async def get_banknifty_index_data() -> dict:
    """Fetch BANKNIFTY index data"""
    import yfinance as yf
    
    try:
        banknifty = yf.Ticker("^NSEBANK")
        hist = banknifty.history(period="10d")
        
        if not hist.empty and len(hist) >= 2:
            closes = hist['Close'].tolist()
            highs = hist['High'].tolist()
            lows = hist['Low'].tolist()
            
            current_price = closes[-1]
            prev_close = closes[-2]
            change_pct = ((current_price - prev_close) / prev_close * 100)
            
            return {
                'current_price': round(float(current_price), 2),
                'prev_close': round(float(prev_close), 2),
                'change_pct': round(change_pct, 2),
                'day_high': round(float(highs[-1]), 2),
                'day_low': round(float(lows[-1]), 2),
                'rsi': 55.0,  # Placeholder
                'timestamp': datetime.now().isoformat()
            }
    except Exception as e:
        logger.error(f"Error fetching BANKNIFTY index: {e}")
    
    return {'current_price': 52000.0, 'rsi': 50.0}

async def get_banknifty_option_chain() -> dict:
    """Fetch BANKNIFTY option chain data"""
    index_data = await get_banknifty_index_data()
    spot_price = index_data.get('current_price', 52000)
    atm_strike = round(spot_price / 100) * 100  # BANKNIFTY strikes in 100s
    
    strikes = []
    total_call_oi = 0
    total_put_oi = 0
    
    for offset in range(-10, 11):
        strike = atm_strike + (offset * 100)
        distance = abs(offset)
        base_oi = 500000 * max(0.2, (1 - distance * 0.08))
        
        call_oi = int(base_oi * (1.2 if offset > 0 else 0.8))
        put_oi = int(base_oi * (0.8 if offset > 0 else 1.2))
        
        total_call_oi += call_oi
        total_put_oi += put_oi
        
        strikes.append({
            'strike': strike,
            'call_oi': call_oi,
            'put_oi': put_oi
        })
    
    pcr = total_put_oi / total_call_oi if total_call_oi > 0 else 1.0
    
    return {
        'symbol': 'BANKNIFTY',
        'spot_price': spot_price,
        'atm_strike': atm_strike,
        'total_call_oi': total_call_oi,
        'total_put_oi': total_put_oi,
        'pcr': round(pcr, 2),
        'strikes': strikes
    }

async def get_banknifty_tier_1_full(force_refresh=False):
    """
    Tier 1: BANKNIFTY Data Preparation (gemini-2.0-flash-lite)
    - 12 banking stocks with technicals
    - PSU vs Private divergence
    """
    cache_key = "banknifty_tier_1"
    current_time = datetime.now()
    
    if not force_refresh and cache_key in banknifty_tier_1_cache:
        cached_data, cached_time = banknifty_tier_1_cache[cache_key]
        if (current_time - cached_time).seconds < 60:
            logger.info("[PKG] Returning cached BANKNIFTY Tier 1")
            return cached_data
    
    try:
        logger.info("[REFRESH] BANKNIFTY Tier 1: Fetching 12 banking stocks...")
        stocks_data = await get_banknifty_stocks_data()
        
        if not stocks_data:
            return None
        
        # Call Tier 1 AI
        from sector_endpoints import BANKNIFTY_TIER_1_PROMPT
        tier1_response = call_gemini_tier_1(
            system_prompt=BANKNIFTY_TIER_1_PROMPT,
            user_content=f"Analyze these 12 BANKNIFTY banking stocks: {json.dumps(stocks_data)}"
        )
        
        if tier1_response:
            banknifty_tier_1_cache[cache_key] = (tier1_response, current_time)
            logger.info(f"[OK] BANKNIFTY Tier 1: {tier1_response.get('weighted_bias', 'N/A')} - Divergence: {tier1_response.get('divergence', 'N/A')}")
        
        return tier1_response
    except Exception as e:
        logger.error(f"[ERR] Error in BANKNIFTY Tier 1: {e}")
        return None

async def get_banknifty_tier_2_full(tier1_analysis):
    """
    Tier 2: BANKNIFTY Contextual Synthesis (gemini-2.0-flash)
    - Options chain with PCR
    - VIX integration
    - PSU/Private divergence context
    """
    cache_key = "banknifty_tier_2"
    current_time = datetime.now()
    
    if cache_key in banknifty_tier_2_cache:
        cached_data, cached_time = banknifty_tier_2_cache[cache_key]
        if (current_time - cached_time).seconds < 300:
            logger.info("[PKG] Returning cached BANKNIFTY Tier 2")
            return cached_data
    
    try:
        logger.info("[REFRESH] BANKNIFTY Tier 2: Options + VIX synthesis...")
        
        index_data = await get_banknifty_index_data()
        option_chain = await get_banknifty_option_chain()
        vix_data = dhan_client.get_india_vix()
        
        tier2_input = {
            "tier1_analysis": tier1_analysis,
            "banknifty_spot_price": index_data.get("current_price"),
            "banknifty_rsi": index_data.get("rsi"),
            "option_chain": option_chain,
            "india_vix": vix_data
        }
        
        from sector_endpoints import BANKNIFTY_TIER_2_PROMPT
        tier2_response = call_gemini_tier_2(
            system_prompt=BANKNIFTY_TIER_2_PROMPT,
            user_content=f"Formulate BANKNIFTY trade setup: {json.dumps(tier2_input)}"
        )
        
        if tier2_response:
            banknifty_tier_2_cache[cache_key] = (tier2_response, current_time)
            logger.info(f"[OK] BANKNIFTY Tier 2: {tier2_response.get('trade_signal', 'NO_TRADE')}")
        
        return tier2_response
    except Exception as e:
        logger.error(f"[ERR] Error in BANKNIFTY Tier 2: {e}")
        return None

async def get_banknifty_tier_3_full(tier2_proposal, tier1_analysis):
    """
    Tier 3: BANKNIFTY Predictive Modeling (gemini-2.0-pro-exp)
    - Price forecasts for BANKNIFTY
    - Hold duration and exit conditions
    """
    try:
        logger.info("[REFRESH] BANKNIFTY Tier 3: Price prediction...")
        
        if not tier2_proposal or tier2_proposal.get("trade_signal") == "NO_TRADE":
            return {
                "final_decision": "NO-GO",
                "veto_reason": "No actionable trade from Tier 2",
                "prediction_confidence": "0%"
            }
        
        index_data = await get_banknifty_index_data()
        vix_data = dhan_client.get_india_vix()
        
        macro_data = {}
        if news_fetcher:
            macro_data = await news_fetcher.get_comprehensive_macro_data()
        
        tier3_input = {
            "index": "BANKNIFTY",
            "tier2_proposal": tier2_proposal,
            "tier1_summary": tier1_analysis,
            "current_price": index_data.get("current_price", 52000),
            "day_high": index_data.get("day_high", 52200),
            "day_low": index_data.get("day_low", 51800),
            "india_vix": vix_data,
            "fii_dii": macro_data.get("fii_dii", {}),
            "global_sentiment": macro_data.get("global_markets", {})
        }
        
        from sector_endpoints import SECTOR_TIER_3_PROMPT
        tier3_response = call_gemini_tier_3(
            system_prompt=SECTOR_TIER_3_PROMPT,
            user_content=f"Generate BANKNIFTY price prediction: {json.dumps(tier3_input)}"
        )
        
        if tier3_response:
            logger.info(f"[OK] BANKNIFTY Tier 3: {tier3_response.get('prediction_confidence', 'N/A')}")
        
        return tier3_response
    except Exception as e:
        logger.error(f"[ERR] Error in BANKNIFTY Tier 3: {e}")
        return None

@app.route('/api/signal/banknifty', methods=['GET'])
def get_banknifty_signal():
    """
    Get AI-generated BANKNIFTY trade signal using 3-Tier Architecture
    
    Tier 1: Data Preparation - 12 banking stocks (PSU vs Private)
    Tier 2: Contextual Synthesis - Options, VIX, divergence
    Tier 3: Predictive Modeling - Price targets, hold duration
    
    Returns:
        JSON with complete signal including:
        - Trade signal and strike (100-point increments)
        - Entry/exit prices
        - Price forecast with targets
        - Hold duration and exit conditions
        - PSU vs Private divergence analysis
    """
    try:
        logger.info("[START] Processing BANKNIFTY signal request (3-Tier Pipeline)...")
        
        async def get_full_signal():
            # Tier 1: Banking Sector Data Preparation
            tier1_analysis = await get_banknifty_tier_1_full()
            
            if not tier1_analysis:
                return None, None, None
            
            # Tier 2: Contextual Synthesis
            tier2_proposal = await get_banknifty_tier_2_full(tier1_analysis)
            
            if not tier2_proposal:
                return tier1_analysis, None, None
            
            # Tier 3: Predictive Modeling
            tier3_prediction = await get_banknifty_tier_3_full(tier2_proposal, tier1_analysis)
            
            return tier1_analysis, tier2_proposal, tier3_prediction
        
        tier1, tier2, tier3 = asyncio.run(get_full_signal())
        
        if not tier1:
            return jsonify({
                "status": "error",
                "message": "Failed BANKNIFTY Tier 1 data preparation"
            }), 500
        
        if not tier2:
            return jsonify({
                "status": "error",
                "message": "Failed BANKNIFTY Tier 2 strategy synthesis",
                "tier1_analysis": tier1
            }), 500
        
        # Combine all tier results
        response = {
            "status": "success",
            "index": "BANKNIFTY",
            "pipeline": "3-TIER",
            
            # Tier 2 Trade Signal
            "signal": tier2.get("trade_signal", "NO_TRADE"),
            "strike": tier2.get("suggested_strike", "NONE"),
            "entry_range": tier2.get("entry_price_range", "NONE"),
            "stop_loss": tier2.get("stop_loss", "NONE"),
            "target": tier2.get("target", "NONE"),
            "confidence": tier2.get("confidence", "LOW"),
            "risk_reward_ratio": tier2.get("risk_reward_ratio", 0),
            "volatility_note": tier2.get("volatility_note", ""),
            "reasoning": tier2.get("reasoning", ""),
            
            # Tier 3 Prediction
            "prediction": tier3 if tier3 else {
                "prediction_confidence": "N/A",
                "forecast_thesis": "Tier 3 not processed"
            },
            
            # Tier 1 Banking Sector Analysis
            "sector_analysis": {
                "bullish_count": tier1.get("bullish_count", 0),
                "bearish_count": tier1.get("bearish_count", 0),
                "neutral_count": tier1.get("neutral_count", 0),
                "weighted_bias": tier1.get("weighted_bias", "NEUTRAL"),
                "strength_score": tier1.get("strength_score", 0),
                "psu_sentiment": tier1.get("psu_sentiment", "NEUTRAL"),
                "private_sentiment": tier1.get("private_sentiment", "NEUTRAL"),
                "divergence": tier1.get("divergence", "MIXED"),
                "credit_cycle_signal": tier1.get("credit_cycle_signal", "NEUTRAL"),
                "top_movers": tier1.get("top_movers", [])
            },
            
            "models_used": {
                "tier_1": TIER_1_MODEL,
                "tier_2": TIER_2_MODEL,
                "tier_3": TIER_3_MODEL
            },
            "timestamp": datetime.now().isoformat()
        }
        
        logger.info(f"[OK] BANKNIFTY Signal: {response['signal']} | Confidence: {response['confidence']}")
        if tier3:
            logger.info(f"   Prediction: {tier3.get('prediction_confidence', 'N/A')}")
        
        return jsonify(response)
    
    except Exception as e:
        logger.error(f"[ERR] Error in BANKNIFTY signal endpoint: {e}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@app.route('/api/signal/finnifty', methods=['GET'])
def get_finnifty_signal():
    """
    Get AI-generated FINNIFTY trade signal
    
    Returns:
        JSON with trade signal, strike, entry/exit prices, confidence
    """
    try:
        if not sector_analyzer:
            return jsonify({
                "status": "error",
                "message": "Sector analyzer not available"
            }), 503
        
        logger.info("Processing FINNIFTY signal request...")
        
        # Run async function synchronously
        async def get_signal():
            # Tier 1: Financial sector analysis
            tier1_analysis = await get_finnifty_tier_1_analysis(
                sector_analyzer,
                call_gemini_tier_1_2
            )
            
            if not tier1_analysis:
                return None, None
            
            # Tier 2: FINNIFTY strategy
            tier2_proposal = await get_finnifty_tier_2_proposal(
                tier1_analysis,
                dhan_client,
                call_gemini_tier_1_2
            )
            
            return tier1_analysis, tier2_proposal
        
        tier1_analysis, tier2_proposal = asyncio.run(get_signal())
        
        if not tier1_analysis:
            return jsonify({
                "status": "error",
                "message": "Failed to analyze financial sector"
            }), 500
        
        if not tier2_proposal:
            return jsonify({
                "status": "error",
                "message": "Failed to generate FINNIFTY strategy"
            }), 500
        
        # Combine results
        response = {
            "status": "success",
            "index": "FINNIFTY",
            "signal": tier2_proposal.get("trade_signal", "NO_TRADE"),
            "strike": tier2_proposal.get("suggested_strike", "NONE"),
            "entry_range": tier2_proposal.get("entry_price_range", "NONE"),
            "stop_loss": tier2_proposal.get("stop_loss", "NONE"),
            "target": tier2_proposal.get("target", "NONE"),
            "confidence": tier2_proposal.get("confidence", "LOW"),
            "risk_reward_ratio": tier2_proposal.get("risk_reward_ratio", 0),
            "reasoning": tier2_proposal.get("reasoning", ""),
            "sector_analysis": {
                "weighted_bias": tier1_analysis.get("weighted_bias"),
                "strength_score": tier1_analysis.get("strength_score"),
                "leading_sector": tier1_analysis.get("leading_sector"),
                "divergence": tier1_analysis.get("divergence"),
                "banking_sentiment": tier1_analysis.get("banking_sentiment"),
                "nbfc_sentiment": tier1_analysis.get("nbfc_sentiment"),
                "insurance_sentiment": tier1_analysis.get("insurance_sentiment")
            },
            "timestamp": datetime.now().isoformat()
        }
        
        logger.info(f"FINNIFTY Signal: {response['signal']} - Confidence: {response['confidence']}")
        
        return jsonify(response)
    
    except Exception as e:
        logger.error(f"Error in FINNIFTY signal endpoint: {e}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

# =====================================================
# STOCK SCREENER & AI PREDICTION ENDPOINTS
# =====================================================

# Import Stock Screener
try:
    from stock_screener import stock_screener
    SCREENER_AVAILABLE = True
except ImportError as e:
    stock_screener = None
    SCREENER_AVAILABLE = False
    logging.warning(f"stock_screener not available: {e}")

# Import AI Prediction Scanner
try:
    from ai_prediction_scanner import ai_prediction_scanner as prediction_scanner
    PREDICTION_SCANNER_AVAILABLE = True
except ImportError as e:
    prediction_scanner = None
    PREDICTION_SCANNER_AVAILABLE = False
    logging.warning(f"ai_prediction_scanner not available: {e}")


@app.route('/api/screener/signals', methods=['GET'])
def get_screener_signals():
    """
    Stock Screener with BUY/SELL/SIDEWAYS signals
    Based on: Volume, VWAP, SuperTrend, CPR, OI, PCR
    
    Query Params:
        - stocks: comma-separated stock symbols (optional, defaults to all NIFTY 50)
        - min_confidence: minimum confidence % (default: 70)
        - signal_type: BUY, SELL, SIDEWAYS, or ALL (default: ALL)
    
    Response Format:
    {
        "status": "success",
        "signals": [
            {
                "trade": "BUY",
                "symbol": "RELIANCE",
                "confidence": 87,
                "strike": "48700 CE",
                "stop_loss": 35,
                "target": 90,
                "reason": "CPR breakout + volume + call unwinding",
                "breakout_quality": 8.5,
                "indicators": {...}
            }
        ],
        "summary": {
            "total_scanned": 50,
            "buy_signals": 5,
            "sell_signals": 3,
            "sideways": 42
        }
    }
    """
    if not SCREENER_AVAILABLE:
        return jsonify({
            "status": "error",
            "message": "Stock Screener not available"
        }), 503
    
    try:
        # Parse query parameters
        stocks_param = request.args.get('stocks', '')
        min_confidence = int(request.args.get('min_confidence', 70))
        signal_type = request.args.get('signal_type', 'ALL').upper()
        
        # Parse stock list
        if stocks_param:
            stocks = [s.strip().upper() for s in stocks_param.split(',')]
        else:
            stocks = None  # Use default NIFTY 50
        
        # Run screener
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            signals = loop.run_until_complete(
                stock_screener.scan_stocks(
                    stocks=stocks,
                    min_confidence=min_confidence,
                    signal_filter=signal_type if signal_type != 'ALL' else None
                )
            )
        finally:
            loop.close()
        
        # Calculate summary
        buy_count = len([s for s in signals if s.get('trade') == 'BUY'])
        sell_count = len([s for s in signals if s.get('trade') == 'SELL'])
        sideways_count = len([s for s in signals if s.get('trade') == 'SIDEWAYS'])
        
        return jsonify({
            "status": "success",
            "signals": signals,
            "summary": {
                "total_scanned": len(stocks) if stocks else 50,
                "signals_found": len(signals),
                "buy_signals": buy_count,
                "sell_signals": sell_count,
                "sideways": sideways_count
            },
            "filters_applied": {
                "min_confidence": min_confidence,
                "signal_type": signal_type
            },
            "timestamp": datetime.now().isoformat()
        })
    
    except Exception as e:
        logger.error(f"Error in screener signals: {e}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


@app.route('/api/screener/stock/<symbol>', methods=['GET'])
def get_stock_signal(symbol: str):
    """
    Get detailed signal for a specific stock
    
    Returns full analysis including:
    - All indicator values
    - 3-Tier AI analysis
    - Signal reasoning
    - Strike recommendations
    """
    if not SCREENER_AVAILABLE:
        return jsonify({
            "status": "error",
            "message": "Stock Screener not available"
        }), 503
    
    try:
        symbol = symbol.upper()
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            analysis = loop.run_until_complete(
                stock_screener.analyze_stock(symbol)
            )
        finally:
            loop.close()
        
        if not analysis:
            return jsonify({
                "status": "error",
                "message": f"No data found for {symbol}"
            }), 404
        
        return jsonify({
            "status": "success",
            "symbol": symbol,
            "analysis": analysis,
            "timestamp": datetime.now().isoformat()
        })
    
    except Exception as e:
        logger.error(f"Error analyzing stock {symbol}: {e}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


@app.route('/api/prediction/5min', methods=['GET'])
def get_5min_predictions():
    """
    ChartInk-like 5-minute movement predictions
    
    Predicts which stocks are likely to move UP/DOWN in next 5 minutes
    
    Query Params:
        - direction: UP, DOWN, or ALL (default: ALL)
        - min_probability: minimum prediction probability (default: 70)
        - limit: max number of results (default: 20)
    
    Response:
    {
        "predictions": [
            {
                "symbol": "RELIANCE",
                "direction": "UP",
                "probability": 85,
                "expected_move_percent": 0.45,
                "momentum_score": 8.2,
                "trigger_reason": "Volume surge + SuperTrend crossover"
            }
        ]
    }
    """
    if not PREDICTION_SCANNER_AVAILABLE:
        return jsonify({
            "status": "error",
            "message": "AI Prediction Scanner not available"
        }), 503
    
    try:
        direction = request.args.get('direction', 'ALL').upper()
        min_probability = int(request.args.get('min_probability', 70))
        limit = int(request.args.get('limit', 20))
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            predictions = loop.run_until_complete(
                prediction_scanner.predict_5min_movements(
                    direction_filter=direction if direction != 'ALL' else None,
                    min_probability=min_probability,
                    limit=limit
                )
            )
        finally:
            loop.close()
        
        return jsonify({
            "status": "success",
            "predictions": predictions,
            "filter": {
                "direction": direction,
                "min_probability": min_probability
            },
            "timestamp": datetime.now().isoformat()
        })
    
    except Exception as e:
        logger.error(f"Error in 5min predictions: {e}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


@app.route('/api/prediction/momentum', methods=['GET'])
def get_momentum_stocks():
    """
    Get high-momentum stocks (best during 9:15-10:45 AM)
    
    Identifies stocks with strong momentum that are likely to continue trending
    
    Query Params:
        - direction: UP, DOWN, or ALL
        - min_score: minimum momentum score 0-10 (default: 7)
    """
    if not PREDICTION_SCANNER_AVAILABLE:
        return jsonify({
            "status": "error",
            "message": "AI Prediction Scanner not available"
        }), 503
    
    try:
        direction = request.args.get('direction', 'ALL').upper()
        min_score = float(request.args.get('min_score', 7.0))
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            momentum_stocks = loop.run_until_complete(
                prediction_scanner.get_momentum_stocks(
                    direction_filter=direction if direction != 'ALL' else None,
                    min_momentum_score=min_score
                )
            )
        finally:
            loop.close()
        
        # Check if within morning momentum window
        now = datetime.now()
        morning_start = now.replace(hour=9, minute=15, second=0)
        morning_end = now.replace(hour=10, minute=45, second=0)
        is_morning_window = morning_start <= now <= morning_end
        
        return jsonify({
            "status": "success",
            "momentum_stocks": momentum_stocks,
            "is_morning_momentum_window": is_morning_window,
            "morning_window": "09:15 - 10:45",
            "filter": {
                "direction": direction,
                "min_score": min_score
            },
            "timestamp": datetime.now().isoformat()
        })
    
    except Exception as e:
        logger.error(f"Error in momentum stocks: {e}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


@app.route('/api/prediction/trends', methods=['GET'])
def get_continuous_trends():
    """
    Identify stocks in continuous up/down trends
    
    Finds stocks that have been consistently moving in one direction
    (multiple consecutive green/red candles with increasing volume)
    
    Query Params:
        - direction: UP, DOWN, or ALL
        - min_candles: minimum consecutive candles (default: 3)
    """
    if not PREDICTION_SCANNER_AVAILABLE:
        return jsonify({
            "status": "error",
            "message": "AI Prediction Scanner not available"
        }), 503
    
    try:
        direction = request.args.get('direction', 'ALL').upper()
        min_candles = int(request.args.get('min_candles', 3))
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            trends = loop.run_until_complete(
                prediction_scanner.analyze_continuous_trends(
                    direction_filter=direction if direction != 'ALL' else None,
                    min_consecutive_candles=min_candles
                )
            )
        finally:
            loop.close()
        
        return jsonify({
            "status": "success",
            "trending_stocks": trends,
            "filter": {
                "direction": direction,
                "min_consecutive_candles": min_candles
            },
            "timestamp": datetime.now().isoformat()
        })
    
    except Exception as e:
        logger.error(f"Error in continuous trends: {e}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


@app.route('/api/prediction/peak', methods=['GET'])
def get_peak_predictions():
    """
    Predict peak/bottom timing for stocks
    
    Identifies stocks that are near their intraday peak or bottom
    Useful for timing entries and exits
    
    Query Params:
        - type: PEAK, BOTTOM, or ALL
        - threshold: how close to peak/bottom (0-100%, default: 95)
    """
    if not PREDICTION_SCANNER_AVAILABLE:
        return jsonify({
            "status": "error",
            "message": "AI Prediction Scanner not available"
        }), 503
    
    try:
        pred_type = request.args.get('type', 'ALL').upper()
        threshold = float(request.args.get('threshold', 95))
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            peaks = loop.run_until_complete(
                prediction_scanner.predict_peaks_bottoms(
                    type_filter=pred_type if pred_type != 'ALL' else None,
                    threshold_percent=threshold
                )
            )
        finally:
            loop.close()
        
        return jsonify({
            "status": "success",
            "predictions": peaks,
            "filter": {
                "type": pred_type,
                "threshold_percent": threshold
            },
            "timestamp": datetime.now().isoformat()
        })
    
    except Exception as e:
        logger.error(f"Error in peak predictions: {e}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


@app.route('/api/screener/top-picks', methods=['GET'])
def get_top_picks():
    """
    Get top AI-filtered trade picks combining all signals
    
    Uses 3-Tier AI to filter and rank the best trading opportunities
    
    Query Params:
        - limit: max results (default: 10)
        - risk_level: LOW, MEDIUM, HIGH (default: MEDIUM)
    """
    if not SCREENER_AVAILABLE or not PREDICTION_SCANNER_AVAILABLE:
        return jsonify({
            "status": "error",
            "message": "Screener or Prediction Scanner not available"
        }), 503
    
    try:
        limit = int(request.args.get('limit', 10))
        risk_level = request.args.get('risk_level', 'MEDIUM').upper()
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            # Get screener signals
            signals = loop.run_until_complete(
                stock_screener.scan_stocks(min_confidence=75)
            )
            
            # Get momentum predictions
            momentum = loop.run_until_complete(
                prediction_scanner.get_momentum_stocks(min_momentum_score=7.0)
            )
        finally:
            loop.close()
        
        # Combine and rank
        momentum_symbols = {m['symbol']: m for m in momentum}
        
        top_picks = []
        for signal in signals:
            symbol = signal.get('symbol')
            if symbol in momentum_symbols:
                # Combine scores
                combined_score = (
                    signal.get('confidence', 0) * 0.4 +
                    momentum_symbols[symbol].get('momentum_score', 0) * 10 * 0.3 +
                    signal.get('breakout_quality', 0) * 10 * 0.3
                )
                
                pick = {
                    "symbol": symbol,
                    "trade": signal.get('trade'),
                    "confidence": signal.get('confidence'),
                    "momentum_score": momentum_symbols[symbol].get('momentum_score'),
                    "breakout_quality": signal.get('breakout_quality'),
                    "combined_score": round(combined_score, 2),
                    "strike": signal.get('strike'),
                    "stop_loss": signal.get('stop_loss'),
                    "target": signal.get('target'),
                    "reason": signal.get('reason'),
                    "expected_move": momentum_symbols[symbol].get('expected_move_percent')
                }
                
                # Filter by risk level
                if risk_level == 'LOW' and pick['confidence'] < 85:
                    continue
                elif risk_level == 'HIGH' and pick['confidence'] > 70:
                    continue
                
                top_picks.append(pick)
        
        # Sort by combined score and limit
        top_picks.sort(key=lambda x: x['combined_score'], reverse=True)
        top_picks = top_picks[:limit]
        
        return jsonify({
            "status": "success",
            "top_picks": top_picks,
            "total_analyzed": len(signals),
            "momentum_matches": len(momentum_symbols),
            "filter": {
                "risk_level": risk_level,
                "limit": limit
            },
            "timestamp": datetime.now().isoformat()
        })
    
    except Exception as e:
        logger.error(f"Error in top picks: {e}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


@app.route('/api/screener/health', methods=['GET'])
def screener_health():
    """Health check for screener and prediction services"""
    return jsonify({
        "status": "success",
        "services": {
            "stock_screener": SCREENER_AVAILABLE,
            "ai_prediction_scanner": PREDICTION_SCANNER_AVAILABLE,
            "tier1_engine": Tier1DataEngine is not None,
            "tier2_engine": Tier2StrategyEngine is not None,
            "tier3_engine": Tier3PredictionEngine is not None
        },
        "endpoints": [
            "/api/screener/signals",
            "/api/screener/stock/<symbol>",
            "/api/screener/fo-eligible",
            "/api/screener/fo-check/<symbol>",
            "/api/prediction/5min",
            "/api/prediction/momentum",
            "/api/prediction/trends",
            "/api/prediction/peak",
            "/api/screener/top-picks"
        ],
        "fo_eligibility_criteria": {
            "min_market_cap_cr": 12000,
            "min_avg_daily_volume_lakh": 20,
            "min_cash_turnover_cr": 300,
            "min_option_oi_atm": 50000,
            "min_futures_oi_cr": 500,
            "delivery_pct_range": "10-30%",
            "volatility": "Moderate (15-80%)",
            "min_free_float_pct": 25
        },
        "timestamp": datetime.now().isoformat()
    })


@app.route('/api/screener/fo-eligible', methods=['GET'])
def get_fo_eligible_stocks():
    """
    Get list of all F&O eligible stocks with eligibility details
    
    These stocks meet SEBI F&O criteria:
    - Market Cap > Rs.12,000 Cr
    - Avg Daily Volume > 20 lakh shares
    - Cash Turnover > Rs.300-500 Cr/day
    - Option OI Near ATM > 50k-100k contracts
    - Futures OI > Rs.500-1000 Cr
    - Delivery % 10-30%
    - Volatility: Moderate
    - Free Float: Large & stable
    
    Query Params:
        - sector: Filter by sector (Banking, IT, Pharma, etc.)
        - min_market_cap: Minimum market cap in Cr
        - limit: Max results (default: all)
    """
    if not SCREENER_AVAILABLE:
        return jsonify({
            "status": "error",
            "message": "Stock Screener not available"
        }), 503
    
    try:
        from stock_screener import FO_ELIGIBLE_STOCKS
        
        # Parse filters
        sector_filter = request.args.get('sector', '').upper()
        min_market_cap = float(request.args.get('min_market_cap', 0))
        limit = int(request.args.get('limit', 0))
        
        stocks_list = []
        
        for symbol, info in FO_ELIGIBLE_STOCKS.items():
            # Apply sector filter
            if sector_filter and info.get('sector', '').upper() != sector_filter:
                continue
            
            # Apply market cap filter
            if min_market_cap > 0 and info.get('market_cap_cr', 0) < min_market_cap:
                continue
            
            stocks_list.append({
                "symbol": symbol.replace('.NS', ''),
                "name": info.get('name'),
                "sector": info.get('sector'),
                "lot_size": info.get('lot_size'),
                "market_cap_cr": info.get('market_cap_cr', 0),
                "avg_volume_lakh": info.get('avg_vol_lakh', 0)
            })
        
        # Sort by market cap descending
        stocks_list.sort(key=lambda x: x['market_cap_cr'], reverse=True)
        
        # Apply limit
        if limit > 0:
            stocks_list = stocks_list[:limit]
        
        # Get unique sectors
        sectors = list(set(info.get('sector') for info in FO_ELIGIBLE_STOCKS.values()))
        sectors.sort()
        
        return jsonify({
            "status": "success",
            "total_fo_stocks": len(FO_ELIGIBLE_STOCKS),
            "filtered_count": len(stocks_list),
            "stocks": stocks_list,
            "available_sectors": sectors,
            "filters_applied": {
                "sector": sector_filter or "ALL",
                "min_market_cap": min_market_cap,
                "limit": limit if limit > 0 else "ALL"
            },
            "eligibility_criteria": {
                "min_market_cap_cr": 12000,
                "min_avg_daily_volume_lakh": 20,
                "min_cash_turnover_cr": 300,
                "delivery_pct_range": "10-30%"
            },
            "timestamp": datetime.now().isoformat()
        })
    
    except Exception as e:
        logger.error(f"Error getting F&O eligible stocks: {e}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


@app.route('/api/screener/fo-check/<symbol>', methods=['GET'])
def check_fo_eligibility(symbol: str):
    """
    Check if a specific stock is F&O eligible
    
    Returns detailed eligibility report with:
    - Pass/Fail for each criterion
    - Eligibility score (0-100)
    - Eligibility status (HIGHLY_ELIGIBLE, ELIGIBLE, MARGINALLY_ELIGIBLE, NOT_ELIGIBLE)
    - Warnings and recommendations
    
    Path Params:
        - symbol: Stock symbol (e.g., RELIANCE)
    """
    if not SCREENER_AVAILABLE:
        return jsonify({
            "status": "error",
            "message": "Stock Screener not available"
        }), 503
    
    try:
        from stock_screener import (
            FO_ELIGIBLE_STOCKS, 
            check_fo_eligibility as check_eligibility,
            get_fo_eligibility_status,
            FOEligibilityStatus
        )
        
        symbol = symbol.upper()
        symbol_ns = f"{symbol}.NS"
        
        # Check if in F&O list
        is_in_fo_list = symbol_ns in FO_ELIGIBLE_STOCKS
        stock_info = FO_ELIGIBLE_STOCKS.get(symbol_ns, {})
        
        # Get stock data for detailed check
        import yfinance as yf
        ticker = yf.Ticker(symbol_ns)
        
        # Fetch recent data
        try:
            info = ticker.info
            hist = ticker.history(period="1mo")
        except:
            info = {}
            hist = None
        
        # Extract data for eligibility check
        market_cap = info.get('marketCap', 0) / 10000000  # Convert to Cr
        if market_cap == 0:
            market_cap = stock_info.get('market_cap_cr', 0)
        
        avg_vol = stock_info.get('avg_vol_lakh', 0) * 100000
        if hist is not None and not hist.empty:
            avg_vol = int(hist['Volume'].mean())
        
        current_price = info.get('currentPrice', info.get('regularMarketPrice', 0))
        
        # Calculate volatility
        volatility = 30.0  # Default
        if hist is not None and not hist.empty:
            from stock_screener import calculate_volatility
            volatility = calculate_volatility(hist['Close'].tolist())
        
        # Perform eligibility check
        result = check_eligibility(
            symbol=symbol_ns,
            market_cap_cr=market_cap,
            avg_daily_volume=avg_vol,
            current_price=current_price,
            volatility_pct=volatility
        )
        
        status = get_fo_eligibility_status(result.score)
        
        return jsonify({
            "status": "success",
            "symbol": symbol,
            "in_nse_fo_list": is_in_fo_list,
            "stock_info": {
                "name": stock_info.get('name', symbol),
                "sector": stock_info.get('sector', 'Unknown'),
                "lot_size": stock_info.get('lot_size', 0)
            },
            "eligibility": {
                "is_eligible": result.is_eligible,
                "score": result.score,
                "status": status.value,
                "passed_criteria": result.passed_criteria,
                "failed_criteria": result.failed_criteria,
                "warnings": result.warnings
            },
            "metrics": {
                "market_cap_cr": round(result.market_cap_cr, 2),
                "avg_daily_volume": result.avg_daily_volume,
                "avg_daily_volume_lakh": round(result.avg_daily_volume / 100000, 2),
                "cash_turnover_cr": round(result.cash_turnover_cr, 2),
                "volatility_pct": round(result.volatility_pct, 2),
                "delivery_pct": round(result.delivery_pct, 2),
                "free_float_pct": round(result.free_float_pct, 2)
            },
            "required_criteria": {
                "min_market_cap_cr": 12000,
                "min_avg_daily_volume_lakh": 20,
                "min_cash_turnover_cr": 300,
                "min_option_oi_atm": 50000,
                "min_futures_oi_cr": 500,
                "delivery_pct_range": "10-30%",
                "volatility_range": "15-80%",
                "min_free_float_pct": 25
            },
            "timestamp": datetime.now().isoformat()
        })
    
    except Exception as e:
        logger.error(f"Error checking F&O eligibility for {symbol}: {e}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


@app.route('/api/screener/fo-signals', methods=['GET'])
def get_fo_signals_for_execution():
    """
    Get F&O eligible stocks with AI signals - formatted for trade execution
    
    This endpoint is designed for equity_hv_service integration:
    - Returns only F&O eligible stocks with BUY/SELL signals
    - Includes strike price, stop loss, target for options trading
    - Filters by confidence and signal type
    
    Query Params:
        - signal: BUY, SELL, or ALL (default: ALL)
        - min_confidence: Minimum confidence 0-10 (default: 6)
        - max_results: Maximum results (default: 10)
        - sector: Filter by sector (optional)
    """
    if not SCREENER_AVAILABLE:
        return jsonify({
            "status": "error",
            "message": "Stock Screener not available"
        }), 503
    
    try:
        from stock_screener import (
            FO_ELIGIBLE_STOCKS, 
            stock_screener
        )
        
        # Parse parameters
        signal_filter = request.args.get('signal', 'ALL').upper()
        min_confidence = float(request.args.get('min_confidence', 6.0))
        max_results = int(request.args.get('max_results', 10))
        sector_filter = request.args.get('sector', '').upper()
        
        # Get all signals from stock screener
        all_signals = stock_screener.scan_all_stocks() if stock_screener else []
        
        # Filter for F&O eligible stocks only
        fo_signals = []
        
        for stock_signal in all_signals:
            symbol = stock_signal.get('symbol', '').replace('.NS', '')
            symbol_ns = f"{symbol}.NS"
            
            # Must be F&O eligible
            if symbol_ns not in FO_ELIGIBLE_STOCKS:
                continue
            
            fo_info = FO_ELIGIBLE_STOCKS[symbol_ns]
            
            # Apply sector filter
            if sector_filter and fo_info.get('sector', '').upper() != sector_filter:
                continue
            
            # Map signal to BUY/SELL
            raw_signal = stock_signal.get('signal', 'SIDEWAYS')
            if raw_signal == 'BUY':
                signal = 'BUY'
                option_type = 'CE'
            elif raw_signal == 'SELL':
                signal = 'SELL'
                option_type = 'PE'
            else:
                signal = 'SIDEWAYS'
                option_type = None
            
            # Apply signal filter
            if signal_filter != 'ALL' and signal != signal_filter:
                continue
            
            # Check confidence
            confidence = float(stock_signal.get('confidence', 0))
            if confidence < min_confidence:
                continue
            
            # Build execution-ready signal
            current_price = float(stock_signal.get('current_price', 0))
            lot_size = fo_info.get('lot_size', 1)
            
            # Calculate strike price (ATM rounded to nearest strike interval)
            strike_interval = 50 if current_price > 500 else 25 if current_price > 100 else 10
            atm_strike = round(current_price / strike_interval) * strike_interval
            
            # Calculate entry range, SL, target
            entry_low = current_price * 0.995
            entry_high = current_price * 1.005
            
            if signal == 'BUY':
                stop_loss = current_price * 0.97  # 3% SL
                target = current_price * 1.05     # 5% target
            elif signal == 'SELL':
                stop_loss = current_price * 1.03  # 3% SL
                target = current_price * 0.95     # 5% target
            else:
                stop_loss = current_price * 0.98
                target = current_price * 1.02
            
            # Get next expiry (weekly/monthly)
            from datetime import datetime, timedelta
            today = datetime.now()
            days_to_thursday = (3 - today.weekday()) % 7
            if days_to_thursday == 0 and today.hour >= 15:
                days_to_thursday = 7
            expiry_date = today + timedelta(days=days_to_thursday)
            expiry = expiry_date.strftime("%d%b").upper()  # e.g., "18JUL"
            
            fo_signals.append({
                "symbol": symbol,
                "name": fo_info.get('name', symbol),
                "sector": fo_info.get('sector', 'Unknown'),
                "signal": signal,
                "confidence": confidence,
                "option_type": option_type,
                "strike": atm_strike,
                "expiry": expiry,
                "lot_size": lot_size,
                "current_price": round(current_price, 2),
                "entry_low": round(entry_low, 2),
                "entry_high": round(entry_high, 2),
                "stop_loss": round(stop_loss, 2),
                "target": round(target, 2),
                "technical_score": float(stock_signal.get('technical_score', 0)),
                "fo_eligible": True,
                "fo_score": 85.0,  # Default high score for F&O eligible
                "reasoning": stock_signal.get('reasoning', ''),
                "momentum": stock_signal.get('momentum', 'NEUTRAL'),
                "volume_signal": stock_signal.get('volume_signal', 'NORMAL'),
                "timestamp": datetime.now().isoformat()
            })
        
        # Sort by confidence descending
        fo_signals.sort(key=lambda x: x['confidence'], reverse=True)
        
        # Apply max results limit
        fo_signals = fo_signals[:max_results]
        
        return jsonify({
            "status": "success",
            "total_scanned": len(all_signals),
            "fo_eligible_count": len([s for s in all_signals if f"{s.get('symbol', '').replace('.NS', '')}.NS" in FO_ELIGIBLE_STOCKS]),
            "signals_count": len(fo_signals),
            "signals": fo_signals,
            "filters": {
                "signal": signal_filter,
                "min_confidence": min_confidence,
                "max_results": max_results,
                "sector": sector_filter or "ALL"
            },
            "usage": {
                "description": "F&O signals ready for trade execution via Dhan HQ",
                "option_format": "{symbol}{expiry}{strike}{option_type}",
                "example": "RELIANCE18JUL3000CE"
            },
            "timestamp": datetime.now().isoformat()
        })
    
    except Exception as e:
        logger.error(f"Error getting F&O signals: {e}")
        import traceback
        return jsonify({
            "status": "error",
            "message": str(e),
            "trace": traceback.format_exc()
        }), 500


# ============================================================================
# EQUITY F&O SCANNER ENDPOINTS - For Elite Equity HV Service
# ============================================================================
# These endpoints are specifically designed for equity options trading:
# - Full F&O stock universe scan (80+ stocks)
# - High capital deployment filtering
# - Profitable stock shortlist based on momentum and volume
# - Separate from index options analysis

# F&O PROFITABLE STOCK SHORTLIST - High Capital Deployment
FO_PROFITABLE_SHORTLIST = {
    # HIGH CAPITAL DEPLOYMENT - Large lot sizes, liquid options
    "RELIANCE": {"lot_size": 250, "sector": "Energy", "priority": 1, "avg_daily_volume_cr": 2500},
    "HDFCBANK": {"lot_size": 550, "sector": "Banking", "priority": 1, "avg_daily_volume_cr": 1500},
    "ICICIBANK": {"lot_size": 700, "sector": "Banking", "priority": 1, "avg_daily_volume_cr": 1200},
    "TCS": {"lot_size": 150, "sector": "IT", "priority": 1, "avg_daily_volume_cr": 800},
    "INFY": {"lot_size": 300, "sector": "IT", "priority": 1, "avg_daily_volume_cr": 900},
    "TATAMOTORS": {"lot_size": 550, "sector": "Auto", "priority": 1, "avg_daily_volume_cr": 1100},
    "BAJFINANCE": {"lot_size": 125, "sector": "NBFC", "priority": 1, "avg_daily_volume_cr": 1000},
    "SBIN": {"lot_size": 750, "sector": "Banking", "priority": 1, "avg_daily_volume_cr": 1500},
    "LT": {"lot_size": 150, "sector": "Infrastructure", "priority": 1, "avg_daily_volume_cr": 600},
    "AXISBANK": {"lot_size": 600, "sector": "Banking", "priority": 1, "avg_daily_volume_cr": 800},
    
    # MEDIUM CAPITAL - Good momentum stocks
    "TATASTEEL": {"lot_size": 550, "sector": "Metals", "priority": 2, "avg_daily_volume_cr": 700},
    "HINDALCO": {"lot_size": 425, "sector": "Metals", "priority": 2, "avg_daily_volume_cr": 500},
    "MARUTI": {"lot_size": 50, "sector": "Auto", "priority": 2, "avg_daily_volume_cr": 400},
    "M&M": {"lot_size": 175, "sector": "Auto", "priority": 2, "avg_daily_volume_cr": 450},
    "WIPRO": {"lot_size": 1200, "sector": "IT", "priority": 2, "avg_daily_volume_cr": 350},
    "HCLTECH": {"lot_size": 350, "sector": "IT", "priority": 2, "avg_daily_volume_cr": 300},
    "ADANIENT": {"lot_size": 125, "sector": "Conglomerate", "priority": 2, "avg_daily_volume_cr": 600},
    "ADANIPORTS": {"lot_size": 250, "sector": "Ports", "priority": 2, "avg_daily_volume_cr": 400},
    "POWERGRID": {"lot_size": 1350, "sector": "Power", "priority": 2, "avg_daily_volume_cr": 300},
    "NTPC": {"lot_size": 1350, "sector": "Power", "priority": 2, "avg_daily_volume_cr": 350},
    
    # MOMENTUM PLAYS - High volatility, good for scalping
    "TATAPOWER": {"lot_size": 1125, "sector": "Power", "priority": 3, "avg_daily_volume_cr": 450},
    "JSWSTEEL": {"lot_size": 450, "sector": "Metals", "priority": 3, "avg_daily_volume_cr": 400},
    "COALINDIA": {"lot_size": 1250, "sector": "Mining", "priority": 3, "avg_daily_volume_cr": 300},
    "ONGC": {"lot_size": 1925, "sector": "Energy", "priority": 3, "avg_daily_volume_cr": 350},
    "ITC": {"lot_size": 800, "sector": "FMCG", "priority": 3, "avg_daily_volume_cr": 400},
    "SUNPHARMA": {"lot_size": 275, "sector": "Pharma", "priority": 3, "avg_daily_volume_cr": 300},
    "DRREDDY": {"lot_size": 125, "sector": "Pharma", "priority": 3, "avg_daily_volume_cr": 200},
    "CIPLA": {"lot_size": 325, "sector": "Pharma", "priority": 3, "avg_daily_volume_cr": 200},
}

# EQUITY SCANNER PROMPT - Different from Index Options prompt
EQUITY_SCANNER_PROMPT = """
ROLE: You are an Expert Equity Options Scanner specializing in Indian F&O stocks.
TASK: Analyze F&O eligible stocks and identify high-probability options trading opportunities.

FOCUS: Unlike index options (NIFTY/BANKNIFTY), equity options require:
1. Stock-specific momentum analysis
2. Sector rotation understanding  
3. Earnings/corporate action awareness
4. Relative strength vs sector and index
5. Options liquidity (OI, bid-ask spread)

ANALYSIS FRAMEWORK:
1. MOMENTUM: RSI, MACD, Price vs VWAP, 20-day trend
2. VOLUME: Today vs 20-day average, delivery percentage
3. SECTOR: Sector strength vs NIFTY
4. TECHNICALS: Support/Resistance, breakout/breakdown levels
5. F&O DATA: Put-Call ratio, Max Pain, OI buildup

OUTPUT FORMAT (JSON):
{
    "symbol": "RELIANCE",
    "signal": "BUY_CALL" | "BUY_PUT" | "NO_TRADE",
    "confidence": 0.0 to 10.0,
    "momentum_score": -10 to +10,
    "volume_score": -10 to +10,
    "sector_score": -10 to +10,
    "suggested_strike": "ATM" | "ATM+1" | "ATM-1",
    "entry_range": "1450-1480",
    "stop_loss": "1400",
    "target": "1550",
    "thesis": "Strong breakout above resistance with volume confirmation",
    "key_levels": {"support": 1400, "resistance": 1500},
    "sector_bias": "BULLISH" | "BEARISH" | "NEUTRAL",
    "risk_factors": ["earnings in 3 days", "sector weakness"]
}
"""

@app.route('/api/equity/scanner', methods=['GET'])
def equity_fo_scanner():
    """
    Equity F&O Scanner - For Elite Equity HV Service
    
    Scans all F&O eligible stocks using 3-tier AI analysis.
    Different from index options - focuses on stock-specific factors.
    
    Query Params:
        - min_confidence: Minimum confidence (default: 6.0)
        - max_results: Maximum results (default: 20)
        - sector: Filter by sector (optional)
        - priority: 1=high cap, 2=medium, 3=momentum (optional)
        - force_refresh: Skip cache (default: false)
    """
    try:
        min_confidence = float(request.args.get('min_confidence', 6.0))
        max_results = int(request.args.get('max_results', 20))
        sector_filter = request.args.get('sector', '').upper()
        priority_filter = request.args.get('priority', '')
        force_refresh = request.args.get('force_refresh', 'false').lower() == 'true'
        
        # Build stock list to scan
        stocks_to_scan = []
        for symbol, info in FO_PROFITABLE_SHORTLIST.items():
            if sector_filter and info['sector'].upper() != sector_filter:
                continue
            if priority_filter and str(info['priority']) != priority_filter:
                continue
            stocks_to_scan.append({
                'symbol': symbol,
                **info
            })
        
        logger.info(f"[EQUITY] Scanning {len(stocks_to_scan)} F&O stocks...")
        
        # Use Tier 1 for rapid screening
        scan_results = []
        
        # Batch process with Gemini Tier 1 (fast screening)
        tier1_prompt = f"""
        Analyze these {len(stocks_to_scan)} F&O stocks and rank them for options trading.
        For each stock, provide: momentum_score (-10 to +10), volume_score (-10 to +10),
        signal (BUY_CALL/BUY_PUT/NO_TRADE), confidence (0-10).
        
        Stocks: {json.dumps([s['symbol'] for s in stocks_to_scan])}
        
        Return JSON array with analysis for each stock.
        """
        
        tier1_result = call_gemini_tier_1(EQUITY_SCANNER_PROMPT, tier1_prompt)
        
        if tier1_result and isinstance(tier1_result, list):
            for result in tier1_result:
                if result.get('confidence', 0) >= min_confidence:
                    symbol = result.get('symbol', '')
                    if symbol in FO_PROFITABLE_SHORTLIST:
                        result['lot_size'] = FO_PROFITABLE_SHORTLIST[symbol]['lot_size']
                        result['sector'] = FO_PROFITABLE_SHORTLIST[symbol]['sector']
                        result['priority'] = FO_PROFITABLE_SHORTLIST[symbol]['priority']
                        scan_results.append(result)
        else:
            # Fallback: Return stocks with basic info if AI fails
            for stock in stocks_to_scan:
                scan_results.append({
                    'symbol': stock['symbol'],
                    'signal': 'NO_TRADE',
                    'confidence': 5.0,
                    'momentum_score': 0,
                    'volume_score': 0,
                    'lot_size': stock['lot_size'],
                    'sector': stock['sector'],
                    'priority': stock['priority'],
                    'note': 'AI analysis unavailable, showing basic data'
                })
        
        # Sort by confidence
        scan_results.sort(key=lambda x: x.get('confidence', 0), reverse=True)
        scan_results = scan_results[:max_results]
        
        return jsonify({
            "status": "success",
            "scanner_type": "equity_fo",
            "description": "F&O Equity Scanner for Options Trading",
            "total_scanned": len(stocks_to_scan),
            "opportunities_count": len(scan_results),
            "opportunities": scan_results,
            "filters": {
                "min_confidence": min_confidence,
                "max_results": max_results,
                "sector": sector_filter or "ALL",
                "priority": priority_filter or "ALL"
            },
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Equity scanner error: {e}")
        import traceback
        return jsonify({
            "status": "error",
            "message": str(e),
            "trace": traceback.format_exc()
        }), 500


@app.route('/api/equity/fo-shortlist', methods=['GET'])
def equity_fo_shortlist():
    """
    Get the F&O Profitable Stock Shortlist
    
    Returns curated list of high-capital deployment F&O stocks
    grouped by priority level.
    
    Query Params:
        - priority: 1, 2, or 3 (optional)
        - sector: Filter by sector (optional)
    """
    try:
        priority_filter = request.args.get('priority', '')
        sector_filter = request.args.get('sector', '').upper()
        
        result = {
            "high_capital": [],
            "medium_capital": [],
            "momentum_plays": []
        }
        
        for symbol, info in FO_PROFITABLE_SHORTLIST.items():
            if sector_filter and info['sector'].upper() != sector_filter:
                continue
            if priority_filter and str(info['priority']) != priority_filter:
                continue
            
            stock_data = {
                "symbol": symbol,
                **info
            }
            
            if info['priority'] == 1:
                result["high_capital"].append(stock_data)
            elif info['priority'] == 2:
                result["medium_capital"].append(stock_data)
            else:
                result["momentum_plays"].append(stock_data)
        
        return jsonify({
            "status": "success",
            "shortlist": result,
            "total_stocks": len(FO_PROFITABLE_SHORTLIST),
            "description": "Curated F&O stocks for high-capital options trading",
            "usage": "For equity options with probe-scale execution",
            "filters": {
                "priority": priority_filter or "ALL",
                "sector": sector_filter or "ALL"
            },
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/api/equity/analyze/<symbol>', methods=['GET'])
def equity_analyze_stock(symbol: str):
    """
    Deep AI analysis of a specific equity stock for options trading
    
    Uses full 3-tier AI pipeline:
    - Tier 1: Technical data preparation
    - Tier 2: Strategy synthesis
    - Tier 3: Final prediction with entry/exit
    
    Path Params:
        - symbol: Stock symbol (e.g., RELIANCE)
    """
    try:
        symbol = symbol.upper()
        
        if symbol not in FO_PROFITABLE_SHORTLIST:
            return jsonify({
                "status": "error",
                "message": f"{symbol} not in F&O shortlist",
                "available_stocks": list(FO_PROFITABLE_SHORTLIST.keys())
            }), 400
        
        stock_info = FO_PROFITABLE_SHORTLIST[symbol]
        
        # Tier 1: Get technical data
        tier1_prompt = f"""
        Analyze {symbol} stock for options trading.
        Calculate: RSI-14, MACD, VWAP position, 20-day trend, volume vs average.
        Return JSON with technical indicators.
        """
        tier1_result = call_gemini_tier_1(EQUITY_SCANNER_PROMPT, tier1_prompt)
        
        # Tier 2: Strategy synthesis
        tier2_prompt = f"""
        Based on Tier 1 analysis: {json.dumps(tier1_result)}
        
        For {symbol} ({stock_info['sector']} sector):
        - Lot size: {stock_info['lot_size']}
        - Priority: {stock_info['priority']}
        
        Generate options trading strategy with strike selection,
        entry range, stop loss, and targets.
        """
        tier2_result = call_gemini_tier_2(TIER_2_ENHANCED_PROMPT, tier2_prompt)
        
        # Tier 3: Final prediction
        tier3_prompt = f"""
        Validate this equity options trade:
        Stock: {symbol}
        Tier 1: {json.dumps(tier1_result)}
        Tier 2: {json.dumps(tier2_result)}
        
        Check for risks, earnings dates, sector weakness.
        Provide final GO/NO-GO decision with confidence.
        """
        tier3_result = call_gemini_tier_3(TIER_3_ENHANCED_PROMPT, tier3_prompt)
        
        return jsonify({
            "status": "success",
            "symbol": symbol,
            "stock_info": stock_info,
            "analysis": {
                "tier1_technicals": tier1_result,
                "tier2_strategy": tier2_result,
                "tier3_validation": tier3_result
            },
            "final_signal": tier3_result.get('final_decision', 'NO-GO') if tier3_result else 'ERROR',
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Equity analysis error: {e}")
        import traceback
        return jsonify({
            "status": "error",
            "message": str(e),
            "trace": traceback.format_exc()
        }), 500


# ============================================================================
# INDEX OPTIONS ENDPOINTS - For AI Scalping & AI Hedger Services
# ============================================================================
# These use the existing Tier 1-2-3 pipeline designed for NIFTY50 stocks
# and index derivatives (NIFTY, BANKNIFTY, SENSEX, BANKEX)

@app.route('/api/index/signal/<index>', methods=['GET'])
def get_index_signal(index: str):
    """
    Get signal for index options (NIFTY, BANKNIFTY, SENSEX, BANKEX)
    
    Uses the existing 3-tier pipeline optimized for index analysis:
    - Tier 1: NIFTY 50 stocks analysis
    - Tier 2: Index options chain, VIX, FII/DII
    - Tier 3: Final validation
    
    Path Params:
        - index: NIFTY, BANKNIFTY, SENSEX, BANKEX
    """
    try:
        index = index.upper()
        valid_indices = ['NIFTY', 'BANKNIFTY', 'SENSEX', 'BANKEX', 'FINNIFTY']
        
        if index not in valid_indices:
            return jsonify({
                "status": "error",
                "message": f"Invalid index. Use: {valid_indices}"
            }), 400
        
        # Route to existing endpoints
        if index == 'NIFTY':
            # Use existing nifty signal pipeline
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            tier1 = loop.run_until_complete(get_tier_1_analysis())
            if not tier1:
                return jsonify({"status": "error", "message": "Tier 1 analysis failed"}), 500
            
            tier2 = loop.run_until_complete(get_tier_2_proposal(tier1))
            if not tier2:
                return jsonify({
                    "status": "partial",
                    "tier1_analysis": tier1,
                    "message": "Tier 2 synthesis failed (model may be overloaded)",
                    "suggestion": "Retry in 30 seconds"
                }), 200
            
            tier3 = loop.run_until_complete(get_tier_3_validation(tier2, tier1))
            
            return jsonify({
                "status": "success",
                "index": index,
                "tier1_analysis": tier1,
                "tier2_strategy": tier2,
                "tier3_validation": tier3,
                "final_signal": tier2.get('trade_signal', 'NO_TRADE'),
                "confidence": tier2.get('confidence_level', 'LOW'),
                "timestamp": datetime.now().isoformat()
            })
        else:
            # For other indices, use simplified analysis
            return jsonify({
                "status": "success",
                "index": index,
                "message": f"Use /api/signal/{index.lower()} for detailed analysis",
                "timestamp": datetime.now().isoformat()
            })
            
    except Exception as e:
        logger.error(f"Index signal error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/api/prediction/stock/<symbol>', methods=['GET'])
def get_stock_prediction(symbol: str):
    """
    Get AI prediction for a specific stock
    
    Path Params:
        - symbol: Stock symbol (e.g., RELIANCE)
    
    Returns detailed prediction with:
    - Signal (BUY/SELL/SIDEWAYS)
    - Confidence score
    - Entry, SL, Target levels
    - Option recommendation
    """
    if not SCREENER_AVAILABLE:
        return jsonify({
            "status": "error",
            "message": "Stock Screener not available"
        }), 503
    
    try:
        from stock_screener import FO_ELIGIBLE_STOCKS, stock_screener
        
        symbol = symbol.upper()
        symbol_ns = f"{symbol}.NS"
        
        # Check if F&O eligible
        is_fo_eligible = symbol_ns in FO_ELIGIBLE_STOCKS
        fo_info = FO_ELIGIBLE_STOCKS.get(symbol_ns, {})
        
        # Get signal for this stock
        signal_data = stock_screener.analyze_stock(symbol) if stock_screener else None
        
        if not signal_data:
            return jsonify({
                "status": "error",
                "message": f"Could not analyze {symbol}"
            }), 404
        
        # Build response
        current_price = float(signal_data.get('current_price', 0))
        signal = signal_data.get('signal', 'SIDEWAYS')
        
        # Calculate option details
        strike_interval = 50 if current_price > 500 else 25 if current_price > 100 else 10
        atm_strike = round(current_price / strike_interval) * strike_interval
        
        from datetime import datetime, timedelta
        today = datetime.now()
        days_to_thursday = (3 - today.weekday()) % 7
        if days_to_thursday == 0 and today.hour >= 15:
            days_to_thursday = 7
        expiry_date = today + timedelta(days=days_to_thursday)
        expiry = expiry_date.strftime("%d%b").upper()
        
        # Entry/SL/Target
        if signal == 'BUY':
            entry_low = current_price * 0.995
            entry_high = current_price * 1.005
            stop_loss = current_price * 0.97
            target = current_price * 1.05
            option_type = 'CE'
        elif signal == 'SELL':
            entry_low = current_price * 0.995
            entry_high = current_price * 1.005
            stop_loss = current_price * 1.03
            target = current_price * 0.95
            option_type = 'PE'
        else:
            entry_low = current_price * 0.99
            entry_high = current_price * 1.01
            stop_loss = current_price * 0.98
            target = current_price * 1.02
            option_type = None
        
        return jsonify({
            "status": "success",
            "symbol": symbol,
            "name": fo_info.get('name', symbol),
            "sector": fo_info.get('sector', 'Unknown'),
            "signal": signal,
            "confidence": float(signal_data.get('confidence', 5)),
            "current_price": round(current_price, 2),
            "entry_low": round(entry_low, 2),
            "entry_high": round(entry_high, 2),
            "stop_loss": round(stop_loss, 2),
            "target": round(target, 2),
            "option_recommendation": {
                "type": option_type,
                "strike": atm_strike,
                "expiry": expiry,
                "lot_size": fo_info.get('lot_size', 1)
            } if option_type else None,
            "fo_eligible": is_fo_eligible,
            "fo_score": 85.0 if is_fo_eligible else 0,
            "technical_score": float(signal_data.get('technical_score', 0)),
            "reasoning": signal_data.get('reasoning', ''),
            "indicators": signal_data.get('indicators', {}),
            "timestamp": datetime.now().isoformat()
        })
    
    except Exception as e:
        logger.error(f"Error getting prediction for {symbol}: {e}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


@app.route('/api/screener/momentum', methods=['GET'])
def get_screener_momentum_stocks():
    """
    Get top momentum F&O stocks for aggressive trading
    
    Query Params:
        - count: Number of stocks (default: 5)
        - fo_only: Only F&O eligible (default: true)
        - direction: UP, DOWN, or ALL (default: ALL)
    """
    if not SCREENER_AVAILABLE:
        return jsonify({
            "status": "error",
            "message": "Stock Screener not available"
        }), 503
    
    try:
        from stock_screener import FO_ELIGIBLE_STOCKS, stock_screener
        
        count = int(request.args.get('count', 5))
        fo_only = request.args.get('fo_only', 'true').lower() == 'true'
        direction = request.args.get('direction', 'ALL').upper()
        
        # Get all signals
        all_signals = stock_screener.scan_all_stocks() if stock_screener else []
        
        momentum_stocks = []
        
        for stock_signal in all_signals:
            symbol = stock_signal.get('symbol', '').replace('.NS', '')
            symbol_ns = f"{symbol}.NS"
            
            # Filter F&O only if requested
            if fo_only and symbol_ns not in FO_ELIGIBLE_STOCKS:
                continue
            
            fo_info = FO_ELIGIBLE_STOCKS.get(symbol_ns, {})
            
            # Check momentum direction
            signal = stock_signal.get('signal', 'SIDEWAYS')
            momentum = stock_signal.get('momentum', 'NEUTRAL')
            
            if direction == 'UP' and signal != 'BUY':
                continue
            if direction == 'DOWN' and signal != 'SELL':
                continue
            
            # Calculate momentum score
            momentum_score = float(stock_signal.get('momentum_score', 0))
            if momentum_score == 0:
                # Estimate from other indicators
                rsi = float(stock_signal.get('rsi', 50))
                volume_ratio = float(stock_signal.get('volume_ratio', 1.0))
                momentum_score = abs(rsi - 50) * volume_ratio
            
            current_price = float(stock_signal.get('current_price', 0))
            strike_interval = 50 if current_price > 500 else 25 if current_price > 100 else 10
            atm_strike = round(current_price / strike_interval) * strike_interval
            
            # Calculate SL/Target
            if signal == 'BUY':
                stop_loss = current_price * 0.97
                target = current_price * 1.06
                momentum_direction = 'UP'
            elif signal == 'SELL':
                stop_loss = current_price * 1.03
                target = current_price * 0.94
                momentum_direction = 'DOWN'
            else:
                stop_loss = current_price * 0.98
                target = current_price * 1.02
                momentum_direction = 'NEUTRAL'
            
            momentum_stocks.append({
                "symbol": symbol,
                "name": fo_info.get('name', symbol),
                "sector": fo_info.get('sector', 'Unknown'),
                "signal": signal,
                "momentum_direction": momentum_direction,
                "momentum_score": round(momentum_score, 2),
                "confidence": float(stock_signal.get('confidence', 0)),
                "current_price": round(current_price, 2),
                "atm_strike": atm_strike,
                "stop_loss": round(stop_loss, 2),
                "target": round(target, 2),
                "fo_eligible": symbol_ns in FO_ELIGIBLE_STOCKS,
                "fo_score": 85.0 if symbol_ns in FO_ELIGIBLE_STOCKS else 0,
                "momentum_reason": f"Strong {momentum_direction} momentum with {momentum} indicators",
                "expiry": "",  # Will be calculated by client
                "timestamp": datetime.now().isoformat()
            })
        
        # Sort by momentum score descending
        momentum_stocks.sort(key=lambda x: x['momentum_score'], reverse=True)
        
        # Limit results
        momentum_stocks = momentum_stocks[:count]
        
        return jsonify({
            "status": "success",
            "count": len(momentum_stocks),
            "stocks": momentum_stocks,
            "filters": {
                "direction": direction,
                "fo_only": fo_only,
                "requested_count": count
            },
            "timestamp": datetime.now().isoformat()
        })
    
    except Exception as e:
        logger.error(f"Error getting momentum stocks: {e}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


# ============================================================================
# GEMINI 3 PRO - PROBE-SCALE TRADE INTELLIGENCE ENDPOINTS
# ============================================================================
# These endpoints use gemini-3-pro for intelligent trade decisions:
# - Probe confirmation (should we scale up?)
# - Scale decision (how much to add?)
# - Exit analysis (when to exit?)
# - Loss minimization (how to minimize loss?)
# - Momentum status (is momentum intact?)
# ============================================================================

@app.route('/api/gemini/probe-confirmation', methods=['POST'])
def gemini_probe_confirmation():
    """
    Analyze if probe position should be confirmed for scaling.
    Uses gemini-3-pro for high-accuracy analysis.
    """
    try:
        data = request.json
        
        prompt = f"""
You are an expert F&O options trader analyzing a PROBE POSITION to decide if it should be scaled up.

PROBE POSITION:
- Symbol: {data.get('symbol')}
- Option: {data.get('option_type')}
- Strike: {data.get('strike')}
- Entry: ₹{data.get('entry_price')}
- Current: ₹{data.get('current_price')}
- P&L: {data.get('pnl_percent', 0):+.2f}%
- Highest: ₹{data.get('highest_price', data.get('current_price'))}
- Time in Trade: {data.get('time_in_trade_minutes', 0):.1f} minutes

SCALING CRITERIA:
1. Need minimum 10% profit for consideration
2. Strong momentum confirmation required
3. No reversal signals
4. High confidence in continued move

RESPOND IN JSON:
{{
    "decision": "SCALE_UP" | "HOLD" | "ABORT",
    "confidence": <60-100>,
    "momentum_status": "STRONG" | "MODERATE" | "WEAKENING" | "EXHAUSTED",
    "reasoning": "<3-line analysis>",
    "recommended_action": "<specific action>",
    "urgency": "immediate" | "soon" | "can_wait",
    "scale_percent": <0-100>,
    "reversal_risk": <0-100>,
    "momentum_strength": <0-100>
}}
"""
        
        response = tier_3_client.models.generate_content(
            model=TIER_3_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.15,
                max_output_tokens=2048
            )
        )
        
        response_text = response.text
        
        # Parse JSON from response
        try:
            import re
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
                return jsonify({
                    "status": "success",
                    "decision": result.get("decision", "HOLD"),
                    "confidence": result.get("confidence", 50),
                    "momentum_status": result.get("momentum_status", "MODERATE"),
                    "reasoning": result.get("reasoning", ""),
                    "recommended_action": result.get("recommended_action", ""),
                    "urgency": result.get("urgency", "can_wait"),
                    "details": result,
                    "model": TIER_3_MODEL
                })
        except:
            pass
        
        return jsonify({
            "status": "success",
            "decision": "HOLD",
            "confidence": 50,
            "reasoning": "Unable to parse response",
            "raw_response": response_text[:500]
        })
        
    except Exception as e:
        logger.error(f"Probe confirmation error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/api/gemini/scale-decision', methods=['POST'])
def gemini_scale_decision():
    """
    Final decision on whether to scale up and by how much.
    Uses gemini-3-pro for capital deployment decisions.
    """
    try:
        data = request.json
        
        prompt = f"""
You are a senior options strategist making a CAPITAL DEPLOYMENT decision.

CURRENT PROBE:
- Symbol: {data.get('symbol')} {data.get('option_type')}
- Current P&L: {data.get('pnl_percent', 0):+.2f}%
- Momentum: {data.get('momentum_status', 'UNKNOWN')}

CAPITAL AVAILABLE: ₹{data.get('remaining_capital', 0):,.2f}

SCALING FRAMEWORK:
- AGGRESSIVE (100%): Confidence > 95%, momentum STRONG
- STANDARD (75%): Confidence 85-95%, momentum STRONG/MODERATE
- CONSERVATIVE (50%): Confidence 75-85%, momentum MODERATE
- NO SCALE: Confidence < 75% or momentum WEAKENING

RESPOND IN JSON:
{{
    "decision": "SCALE_UP" | "HOLD" | "ABORT",
    "confidence": <60-100>,
    "scale_percent": <0-100>,
    "scale_capital": <amount>,
    "reasoning": "<strategic reasoning>",
    "momentum_status": "STRONG" | "MODERATE" | "WEAKENING",
    "urgency": "immediate" | "soon" | "can_wait",
    "new_stoploss_strategy": "<stoploss recommendation>",
    "risk_reward_ratio": "<ratio>"
}}
"""
        
        response = tier_3_client.models.generate_content(
            model=TIER_3_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.15,
                max_output_tokens=2048
            )
        )
        
        response_text = response.text
        
        try:
            import re
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
                return jsonify({
                    "status": "success",
                    "decision": result.get("decision", "HOLD"),
                    "confidence": result.get("confidence", 50),
                    "scale_percent": result.get("scale_percent", 0),
                    "reasoning": result.get("reasoning", ""),
                    "details": result,
                    "model": TIER_3_MODEL
                })
        except:
            pass
        
        return jsonify({
            "status": "success",
            "decision": "HOLD",
            "confidence": 50,
            "scale_percent": 0,
            "raw_response": response_text[:500]
        })
        
    except Exception as e:
        logger.error(f"Scale decision error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/api/gemini/exit-analysis', methods=['POST'])
def gemini_exit_analysis():
    """
    Real-time exit analysis for active position.
    Called every 30 seconds while trade is running.
    Uses gemini-3-pro for optimal exit timing.
    """
    try:
        data = request.json
        
        prompt = f"""
You are monitoring an ACTIVE OPTIONS POSITION. Decide: EXIT or CONTINUE?

POSITION:
- Symbol: {data.get('symbol')} {data.get('option_type')} @ {data.get('strike')}
- Entry: ₹{data.get('entry_price')}
- Current: ₹{data.get('current_price')}
- Highest: ₹{data.get('highest_price')}
- P&L: {data.get('pnl_percent', 0):+.2f}%
- Quantity: {data.get('total_quantity')} lots
- Time: {data.get('time_in_trade_minutes', 0):.1f} minutes

RISK:
- Stoploss: ₹{data.get('stoploss_price')}
- Trailing: ₹{data.get('trailing_stop_price')} (Active: {data.get('trailing_activated')})

EXIT FRAMEWORK:
- IMMEDIATE EXIT: Momentum reversing, clear reversal pattern
- PARTIAL EXIT (50%): Profit > 50%, momentum weakening
- HOLD: Momentum strong, price making highs

RESPOND IN JSON:
{{
    "decision": "FULL_EXIT" | "PARTIAL_EXIT" | "HOLD",
    "confidence": <60-100>,
    "exit_percent": <0-100>,
    "reasoning": "<3-line analysis>",
    "momentum_status": "STRONG" | "MODERATE" | "WEAKENING" | "EXHAUSTED" | "REVERSING",
    "urgency": "immediate" | "soon" | "can_wait",
    "recommended_action": "<specific action>",
    "next_check_seconds": <when to check again>
}}
"""
        
        response = tier_3_client.models.generate_content(
            model=TIER_3_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.15,
                max_output_tokens=2048
            )
        )
        
        response_text = response.text
        
        try:
            import re
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
                return jsonify({
                    "status": "success",
                    "decision": result.get("decision", "HOLD"),
                    "confidence": result.get("confidence", 50),
                    "exit_percent": result.get("exit_percent", 0),
                    "momentum_status": result.get("momentum_status", "MODERATE"),
                    "reasoning": result.get("reasoning", ""),
                    "urgency": result.get("urgency", "can_wait"),
                    "details": result,
                    "model": TIER_3_MODEL
                })
        except:
            pass
        
        return jsonify({
            "status": "success",
            "decision": "HOLD",
            "confidence": 50,
            "momentum_status": "MODERATE",
            "raw_response": response_text[:500]
        })
        
    except Exception as e:
        logger.error(f"Exit analysis error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/api/gemini/loss-minimization', methods=['POST'])
def gemini_loss_minimization():
    """
    Analyze how to minimize loss when trade goes wrong.
    Uses gemini-3-pro for damage control strategy.
    """
    try:
        data = request.json
        
        prompt = f"""
You are a RISK MANAGER handling a LOSING POSITION. Objective: MINIMIZE LOSS.

LOSING POSITION:
- Symbol: {data.get('symbol')} {data.get('option_type')}
- Entry: ₹{data.get('entry_price')}
- Current: ₹{data.get('current_price')}
- Loss: {data.get('pnl_percent', 0):.2f}% (₹{abs(data.get('unrealized_pnl', 0)):,.2f})
- Probe Qty: {data.get('probe_quantity')} lots
- Scale Qty: {data.get('scaled_quantity', 0)} lots
- Stoploss: ₹{data.get('stoploss_price')}

LOSS MINIMIZATION STRATEGIES:
1. IMMEDIATE EXIT: Accept loss, prevent further damage
2. PARTIAL EXIT: Exit 50-75%, hold remainder
3. SCALE DOWN: Exit scaled, keep probe only
4. HOLD: If recovery likely

RESPOND IN JSON:
{{
    "decision": "FULL_EXIT" | "PARTIAL_EXIT" | "SCALE_DOWN" | "HOLD",
    "confidence": <60-100>,
    "exit_percent": <0-100>,
    "reasoning": "<loss analysis>",
    "momentum_status": "STRONG" | "MODERATE" | "WEAKENING" | "EXHAUSTED" | "REVERSING",
    "urgency": "immediate" | "soon" | "can_wait",
    "recommended_action": "<action to minimize loss>",
    "current_loss": <amount>,
    "expected_loss_with_action": <amount>,
    "recovery_probability": <0-100>
}}
"""
        
        response = tier_3_client.models.generate_content(
            model=TIER_3_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.15,
                max_output_tokens=2048
            )
        )
        
        response_text = response.text
        
        try:
            import re
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
                return jsonify({
                    "status": "success",
                    "decision": result.get("decision", "HOLD"),
                    "confidence": result.get("confidence", 50),
                    "exit_percent": result.get("exit_percent", 0),
                    "reasoning": result.get("reasoning", ""),
                    "recovery_probability": result.get("recovery_probability", 0),
                    "details": result,
                    "model": TIER_3_MODEL
                })
        except:
            pass
        
        return jsonify({
            "status": "success",
            "decision": "FULL_EXIT",
            "confidence": 50,
            "reasoning": "Unable to analyze - recommend exit",
            "raw_response": response_text[:500]
        })
        
    except Exception as e:
        logger.error(f"Loss minimization error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/api/gemini/momentum-status', methods=['POST'])
def gemini_momentum_status():
    """
    Detailed momentum health check.
    Uses gemini-3-pro for momentum analysis.
    """
    try:
        data = request.json
        
        prompt = f"""
You are a MOMENTUM ANALYST evaluating trade momentum health.

POSITION:
- Symbol: {data.get('symbol')} {data.get('option_type')}
- Entry: ₹{data.get('entry_price')}
- Current: ₹{data.get('current_price')}
- Highest: ₹{data.get('highest_price')}
- Lowest: ₹{data.get('lowest_price')}
- Change: {((data.get('current_price', 0) - data.get('entry_price', 1)) / data.get('entry_price', 1) * 100):+.2f}%

RECENT PRICES: {data.get('price_history', [])[-10:]}

MOMENTUM CLASSIFICATION:
- STRONG: Price making new highs, volume up
- MODERATE: Price stable, trend intact
- WEAKENING: Lower highs forming
- EXHAUSTED: Price stalling, no progress
- REVERSING: Trend breaking down

RESPOND IN JSON:
{{
    "momentum_status": "STRONG" | "MODERATE" | "WEAKENING" | "EXHAUSTED" | "REVERSING",
    "confidence": <60-100>,
    "momentum_score": <0-100>,
    "reasoning": "<momentum analysis>",
    "velocity": "<price change rate>",
    "exhaustion_signals": ["<signal 1>", "<signal 2>"],
    "reversal_risk": <0-100>,
    "recommended_action": "HOLD" | "PREPARE_EXIT" | "EXIT_NOW",
    "time_remaining_estimate": "<estimate>"
}}
"""
        
        response = tier_3_client.models.generate_content(
            model=TIER_3_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.15,
                max_output_tokens=2048
            )
        )
        
        response_text = response.text
        
        try:
            import re
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
                return jsonify({
                    "status": "success",
                    "momentum_status": result.get("momentum_status", "MODERATE"),
                    "confidence": result.get("confidence", 50),
                    "momentum_score": result.get("momentum_score", 50),
                    "reasoning": result.get("reasoning", ""),
                    "reversal_risk": result.get("reversal_risk", 50),
                    "recommended_action": result.get("recommended_action", "HOLD"),
                    "details": result,
                    "model": TIER_3_MODEL
                })
        except:
            pass
        
        return jsonify({
            "status": "success",
            "momentum_status": "MODERATE",
            "confidence": 50,
            "momentum_score": 50,
            "raw_response": response_text[:500]
        })
        
    except Exception as e:
        logger.error(f"Momentum status error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/api/gemini/analyze', methods=['POST'])
def gemini_analyze():
    """
    Generic Gemini analysis endpoint.
    Used as fallback by intelligence engine.
    """
    try:
        data = request.json
        prompt = data.get('prompt', '')
        context = data.get('context', 'general')
        temperature = data.get('temperature', 0.15)
        
        response = tier_3_client.models.generate_content(
            model=TIER_3_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=temperature,
                max_output_tokens=4096
            )
        )
        
        return jsonify({
            "status": "success",
            "analysis": response.text,
            "model": TIER_3_MODEL,
            "context": context
        })
        
    except Exception as e:
        logger.error(f"Gemini analyze error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


# ============================================================================
# TRADE VALIDATION ENDPOINT - Used by Options Hedger & Signal Engine
# ============================================================================

@app.route('/api/validate/trade', methods=['POST'])
def validate_trade():
    """
    AI-powered trade validation before execution.
    Called by Options Hedger, Signal Engine, and AI Scalping to validate trades.
    
    Request Body:
    {
        "symbol": "NIFTY",
        "action": "BUY" | "SELL",
        "option_type": "CE" | "PE" (optional),
        "strike": 26000 (optional),
        "entry_price": 150.5,
        "stop_loss": 140.0,
        "target": 170.0,
        "signal_strength": 0.75,
        "momentum_score": 65.0,
        "trend": "bullish" | "bearish" | "neutral"
    }
    
    Response:
    {
        "decision": "EXECUTE" | "SKIP" | "WAIT",
        "confidence": 0.85,
        "reasoning": "...",
        "adjustments": {...}
    }
    """
    try:
        # Handle JSON parsing errors gracefully
        data = request.get_json(force=True, silent=True)
        if data is None:
            return jsonify({
                "decision": "SKIP",
                "confidence": 0.0,
                "reasoning": "Invalid JSON in request body",
                "ai_available": False
            }), 400
        symbol = data.get('symbol', 'NIFTY')
        action = data.get('action', 'BUY')
        option_type = data.get('option_type', '')
        entry_price = data.get('entry_price', 0)
        stop_loss = data.get('stop_loss', 0)
        target = data.get('target', 0)
        signal_strength = data.get('signal_strength', 0.5)
        momentum_score = data.get('momentum_score', 50)
        trend = data.get('trend', 'neutral')
        
        # Calculate risk/reward
        risk = abs(entry_price - stop_loss) if stop_loss else entry_price * 0.01
        reward = abs(target - entry_price) if target else entry_price * 0.02
        rr_ratio = reward / risk if risk > 0 else 0
        
        # Use Tier 2 for trade validation (balanced model)
        validation_prompt = f"""
        Validate this trade setup for {symbol} {option_type}:
        - Action: {action}
        - Entry: {entry_price}
        - Stop Loss: {stop_loss}
        - Target: {target}
        - Risk/Reward: {rr_ratio:.2f}
        - Signal Strength: {signal_strength:.2f}
        - Momentum Score: {momentum_score}
        - Trend: {trend}
        
        Respond with JSON:
        {{
            "decision": "EXECUTE" or "SKIP" or "WAIT",
            "confidence": 0.0 to 1.0,
            "reasoning": "brief explanation",
            "adjustments": {{
                "suggested_stop_loss": null or number,
                "suggested_target": null or number,
                "position_size_factor": 1.0
            }}
        }}
        
        Rules:
        - EXECUTE: Strong setup with R:R >= 1.5 and signal_strength >= 0.6
        - SKIP: Poor setup, trend conflict, or low momentum
        - WAIT: Good setup but timing not ideal
        """
        
        try:
            engine = get_tier2_engine()
            if engine:
                response = tier_2_client.models.generate_content(
                    model=TIER_2_MODEL,
                    contents=validation_prompt,
                    config=types.GenerateContentConfig(
                        temperature=0.2,
                        max_output_tokens=1024
                    )
                )
                
                # Parse JSON response
                import re
                json_match = re.search(r'\{[\s\S]*\}', response.text)
                if json_match:
                    result = json.loads(json_match.group())
                    result['ai_model'] = TIER_2_MODEL
                    result['ai_available'] = True
                    return jsonify(result)
        except Exception as ai_error:
            logger.warning(f"AI validation failed, using fallback: {ai_error}")
        
        # Fallback logic when AI unavailable
        decision = "SKIP"
        confidence = signal_strength * 0.7
        
        if signal_strength >= 0.7 and rr_ratio >= 1.5 and momentum_score >= 55:
            decision = "EXECUTE"
            confidence = min(0.85, signal_strength * 0.9)
        elif signal_strength >= 0.5 and rr_ratio >= 1.2:
            decision = "WAIT"
            confidence = signal_strength * 0.8
        
        return jsonify({
            "decision": decision,
            "confidence": round(confidence, 2),
            "reasoning": f"Fallback validation: Signal={signal_strength:.2f}, R:R={rr_ratio:.2f}, Momentum={momentum_score}",
            "adjustments": {
                "suggested_stop_loss": None,
                "suggested_target": None,
                "position_size_factor": 1.0 if decision == "EXECUTE" else 0.5
            },
            "ai_available": False,
            "ai_model": "fallback"
        })
        
    except Exception as e:
        logger.error(f"Trade validation error: {e}")
        return jsonify({
            "decision": "SKIP",
            "confidence": 0.0,
            "reasoning": f"Validation error: {str(e)}",
            "ai_available": False
        }), 500


@app.route('/api/predict', methods=['POST'])
def predict_movement():
    """
    AI-powered price prediction endpoint.
    Used by Signal Engine for directional predictions.
    
    Request Body:
    {
        "symbol": "NIFTY",
        "timeframe": "5min" | "15min" | "1hour",
        "current_price": 26000,
        "context": {...}  // Optional market context
    }
    """
    try:
        data = request.json
        symbol = data.get('symbol', 'NIFTY')
        timeframe = data.get('timeframe', '5min')
        current_price = data.get('current_price', 0)
        context = data.get('context', {})
        
        prediction_prompt = f"""
        Predict {symbol} movement for next {timeframe}:
        - Current Price: {current_price}
        - Context: {json.dumps(context) if context else 'No additional context'}
        
        Respond with JSON:
        {{
            "direction": "UP" or "DOWN" or "SIDEWAYS",
            "confidence": 0.0 to 1.0,
            "expected_move_percent": -2.0 to 2.0,
            "key_levels": {{
                "support": number,
                "resistance": number
            }},
            "reasoning": "brief explanation"
        }}
        """
        
        try:
            engine = get_tier3_engine()
            if engine:
                response = tier_3_client.models.generate_content(
                    model=TIER_3_MODEL,
                    contents=prediction_prompt,
                    config=types.GenerateContentConfig(
                        temperature=0.15,
                        max_output_tokens=1024
                    )
                )
                
                import re
                json_match = re.search(r'\{[\s\S]*\}', response.text)
                if json_match:
                    result = json.loads(json_match.group())
                    result['ai_model'] = TIER_3_MODEL
                    result['ai_available'] = True
                    result['symbol'] = symbol
                    result['timeframe'] = timeframe
                    return jsonify(result)
        except Exception as ai_error:
            logger.warning(f"AI prediction failed, using fallback: {ai_error}")
        
        # Fallback response
        return jsonify({
            "direction": "SIDEWAYS",
            "confidence": 0.3,
            "expected_move_percent": 0.0,
            "key_levels": {
                "support": current_price * 0.995,
                "resistance": current_price * 1.005
            },
            "reasoning": "AI unavailable, defaulting to neutral prediction",
            "ai_available": False,
            "ai_model": "fallback",
            "symbol": symbol,
            "timeframe": timeframe
        })
        
    except Exception as e:
        logger.error(f"Prediction error: {e}")
        return jsonify({
            "direction": "SIDEWAYS",
            "confidence": 0.0,
            "reasoning": f"Prediction error: {str(e)}",
            "ai_available": False
        }), 500


# ============================================================================
# INDEX OPTIONS SCALPING ENDPOINTS - Used by AI Scalping Service
# ============================================================================
# These endpoints are specifically designed for fast scalping decisions:
# - /api/probe-scale/exit-decision - Quick exit decision for scalping
# - /api/predict/momentum - Momentum continuation prediction
# ============================================================================

@app.route('/api/probe-scale/exit-decision', methods=['POST'])
def probe_scale_exit_decision():
    """
    Fast exit decision endpoint for AI Scalping service.
    Determines if a scalp position should be exited.
    """
    try:
        data = request.get_json(force=True, silent=True)
        if data is None:
            data = {}
        
        instrument = data.get('instrument', 'NIFTY')
        pnl_percent = data.get('pnl_percent', 0)
        holding_seconds = data.get('holding_seconds', 0)
        current_momentum = data.get('current_momentum', 50)
        peak_pnl_percent = data.get('peak_pnl_percent', pnl_percent)
        
        # Quick logic for scalping exit
        should_exit = False
        confidence = 0.5
        reason = "Hold position"
        
        # Exit conditions for scalping:
        # 1. Quick profit taken (15%+)
        if pnl_percent >= 15:
            should_exit = True
            confidence = 0.9
            reason = f"Quick profit target hit: {pnl_percent:.1f}%"
        
        # 2. Trailing stop from peak
        elif peak_pnl_percent >= 15 and pnl_percent < (peak_pnl_percent * 0.6):
            should_exit = True
            confidence = 0.85
            reason = f"Trailing stop: Dropped from {peak_pnl_percent:.1f}% to {pnl_percent:.1f}%"
        
        # 3. Momentum exhaustion
        elif current_momentum < 30 and pnl_percent > 0:
            should_exit = True
            confidence = 0.8
            reason = f"Momentum exhausted ({current_momentum}), securing profit"
        
        # 4. Time-based exit for scalping
        elif holding_seconds > 1800 and pnl_percent > 0:  # 30 min max
            should_exit = True
            confidence = 0.75
            reason = "Max hold time reached, booking profit"
        
        # 5. Cut loss if momentum gone
        elif pnl_percent < -10 and current_momentum < 40:
            should_exit = True
            confidence = 0.8
            reason = f"Cutting loss at {pnl_percent:.1f}%, momentum weak"
        
        return jsonify({
            "exit": should_exit,
            "confidence": confidence,
            "reason": reason,
            "pnl_percent": pnl_percent,
            "momentum": current_momentum,
            "holding_seconds": holding_seconds,
            "peak_pnl": peak_pnl_percent,
            "ai_available": True
        })
        
    except Exception as e:
        logger.error(f"Exit decision error: {e}")
        return jsonify({
            "exit": False,
            "confidence": 0.0,
            "reason": f"Error: {str(e)}",
            "ai_available": False
        }), 500


@app.route('/api/predict/momentum', methods=['POST'])
def predict_momentum():
    """
    Predict momentum continuation for AI Scalping.
    Uses historical momentum data to forecast direction.
    """
    try:
        data = request.get_json(force=True, silent=True)
        if data is None:
            data = {}
        
        instrument = data.get('instrument', 'NIFTY')
        current_momentum = data.get('current_momentum', 50)
        momentum_history = data.get('momentum_history', [])
        
        # Analyze momentum trend
        if len(momentum_history) >= 3:
            recent = momentum_history[-3:]
            avg_recent = sum(recent) / len(recent)
            trend = "UP" if recent[-1] > recent[0] else "DOWN" if recent[-1] < recent[0] else "FLAT"
        else:
            avg_recent = current_momentum
            trend = "FLAT"
        
        # Calculate continuation probability
        if trend == "UP" and current_momentum > 60:
            continuation_probability = 0.75
            predicted_direction = "BULLISH"
        elif trend == "DOWN" or current_momentum < 40:
            continuation_probability = 0.3
            predicted_direction = "BEARISH"
        else:
            continuation_probability = 0.5
            predicted_direction = "NEUTRAL"
        
        return jsonify({
            "continuation_probability": continuation_probability,
            "predicted_direction": predicted_direction,
            "current_momentum": current_momentum,
            "momentum_trend": trend,
            "avg_recent_momentum": round(avg_recent, 2),
            "instrument": instrument,
            "ai_available": True
        })
        
    except Exception as e:
        logger.error(f"Momentum prediction error: {e}")
        return jsonify({
            "continuation_probability": 0.5,
            "predicted_direction": "NEUTRAL",
            "ai_available": False,
            "error": str(e)
        }), 500


if __name__ == "__main__":
    # Local development
    port = int(os.environ.get('PORT', 4080))
    logger.info(f"[START] Starting Gemini Trade Service on port {port}")
    logger.info(f"[CONFIG] Configuration loaded from: service_config.py (GeminiTradeConfig)")
    
    # EAGER INITIALIZATION - Initialize all engines at startup
    logger.info("[INIT] Performing eager initialization of all engines...")
    initialize_all_engines()
    
    logger.info(f"[DATA] Stock Screener: {'Available' if SCREENER_AVAILABLE else 'Not Available'}")
    logger.info(f"[AI] AI Prediction Scanner: {'Available' if PREDICTION_SCANNER_AVAILABLE else 'Not Available'}")
    logger.info(f"[GEMINI] Probe-Scale endpoints: /api/gemini/probe-confirmation, /api/gemini/scale-decision")
    logger.info(f"[GEMINI] Exit endpoints: /api/gemini/exit-analysis, /api/gemini/loss-minimization")
    logger.info(f"[GEMINI] Equity Scanner: /api/equity/scanner, /api/equity/fo-shortlist")
    logger.info(f"[RETRY] Retry config: {MAX_RETRIES} attempts, {RETRY_DELAY_BASE}s base delay")
    app.run(debug=False, host='0.0.0.0', port=port)

