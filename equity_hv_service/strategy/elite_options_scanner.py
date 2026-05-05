"""
Elite F&O Options Scanner v2.0 - Intelligent Momentum-Based Trading System
===========================================================================

This scanner implements a 3-tier AI-powered screening system for F&O equity options:

TIER 1 - High-Speed Screening (gemini-2.5-flash-lite):
    - Rapid market scan across 80+ F&O stocks
    - Initial momentum detection and filtering
    - Volume anomaly detection
    
TIER 2 - Deep Momentum Analysis (gemini-2.5-flash):
    - Detailed technical analysis
    - Greeks optimization (delta 0.4-0.7)
    - Capital efficiency scoring
    
TIER 3 - Final Confirmation (gemini-3-pro):
    - High-conviction trade validation
    - Risk-adjusted position sizing
    - Exit strategy planning

EXIT MONITORING (gemini-3-pro):
    - Real-time P&L monitoring
    - Intelligent exit decisions
    - Wide stoploss (no trailing) for momentum capture

Author: AI Trading System
Version: 2.0.0
"""

import asyncio
import aiohttp
import json
import logging
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple, Any
from enum import Enum
import os

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ============================================================================
# GEMINI MODEL CONFIGURATION
# ============================================================================

GEMINI_MODELS = {
    "tier1": "gemini-2.5-flash-lite",   # High-speed screening
    "tier2": "gemini-2.5-flash",         # Deep momentum analysis
    "tier3": "gemini-3-pro",             # Final confirmation
    "exit": "gemini-3-pro"               # Exit decisions
}

# Gemini API Configuration
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_API_BASE = "https://generativelanguage.googleapis.com/v1beta/models"

# Local Gemini Trade Service fallback
GEMINI_SERVICE_URL = "http://localhost:4080"


# ============================================================================
# FO STOCKS UNIVERSE - 80+ NSE F&O Eligible Stocks
# ============================================================================

FO_STOCKS = {
    # Banking & Financial Services
    "HDFCBANK": {"lot_size": 550, "sector": "Banking", "avg_premium": 15},
    "ICICIBANK": {"lot_size": 700, "sector": "Banking", "avg_premium": 12},
    "KOTAKBANK": {"lot_size": 400, "sector": "Banking", "avg_premium": 20},
    "AXISBANK": {"lot_size": 600, "sector": "Banking", "avg_premium": 10},
    "SBIN": {"lot_size": 750, "sector": "Banking", "avg_premium": 8},
    "INDUSINDBK": {"lot_size": 400, "sector": "Banking", "avg_premium": 12},
    "BANDHANBNK": {"lot_size": 600, "sector": "Banking", "avg_premium": 5},
    "FEDERALBNK": {"lot_size": 4000, "sector": "Banking", "avg_premium": 3},
    "IDFCFIRSTB": {"lot_size": 7500, "sector": "Banking", "avg_premium": 2},
    "PNB": {"lot_size": 6000, "sector": "Banking", "avg_premium": 2},
    "AUBANK": {"lot_size": 1000, "sector": "Banking", "avg_premium": 8},
    "BANKBARODA": {"lot_size": 2500, "sector": "Banking", "avg_premium": 3},
    
    # NBFC & Financial Services
    "BAJFINANCE": {"lot_size": 125, "sector": "NBFC", "avg_premium": 80},
    "BAJAJFINSV": {"lot_size": 50, "sector": "NBFC", "avg_premium": 150},
    "CHOLAFIN": {"lot_size": 500, "sector": "NBFC", "avg_premium": 15},
    "MUTHOOTFIN": {"lot_size": 450, "sector": "NBFC", "avg_premium": 15},
    "M&MFIN": {"lot_size": 2000, "sector": "NBFC", "avg_premium": 5},
    "LICHSGFIN": {"lot_size": 1000, "sector": "NBFC", "avg_premium": 5},
    "SBILIFE": {"lot_size": 600, "sector": "Insurance", "avg_premium": 12},
    "HDFCLIFE": {"lot_size": 1100, "sector": "Insurance", "avg_premium": 8},
    "ICICIGI": {"lot_size": 500, "sector": "Insurance", "avg_premium": 15},
    "ICICIPRULI": {"lot_size": 1500, "sector": "Insurance", "avg_premium": 5},
    
    # IT & Technology
    "TCS": {"lot_size": 150, "sector": "IT", "avg_premium": 35},
    "INFY": {"lot_size": 300, "sector": "IT", "avg_premium": 20},
    "WIPRO": {"lot_size": 1200, "sector": "IT", "avg_premium": 6},
    "HCLTECH": {"lot_size": 350, "sector": "IT", "avg_premium": 18},
    "TECHM": {"lot_size": 400, "sector": "IT", "avg_premium": 15},
    "LTIM": {"lot_size": 100, "sector": "IT", "avg_premium": 60},
    "MPHASIS": {"lot_size": 275, "sector": "IT", "avg_premium": 25},
    "COFORGE": {"lot_size": 100, "sector": "IT", "avg_premium": 70},
    "PERSISTENT": {"lot_size": 100, "sector": "IT", "avg_premium": 50},
    
    # Automobiles
    "TATAMOTORS": {"lot_size": 550, "sector": "Auto", "avg_premium": 10},
    "MARUTI": {"lot_size": 50, "sector": "Auto", "avg_premium": 200},
    "M&M": {"lot_size": 350, "sector": "Auto", "avg_premium": 20},
    "BAJAJ-AUTO": {"lot_size": 75, "sector": "Auto", "avg_premium": 80},
    "HEROMOTOCO": {"lot_size": 150, "sector": "Auto", "avg_premium": 35},
    "EICHERMOT": {"lot_size": 175, "sector": "Auto", "avg_premium": 40},
    "ASHOKLEY": {"lot_size": 3000, "sector": "Auto", "avg_premium": 4},
    "TVSMOTOR": {"lot_size": 175, "sector": "Auto", "avg_premium": 25},
    "BALKRISIND": {"lot_size": 200, "sector": "Auto", "avg_premium": 30},
    "MOTHERSON": {"lot_size": 4500, "sector": "Auto", "avg_premium": 3},
    "BHARATFORG": {"lot_size": 500, "sector": "Auto", "avg_premium": 12},
    
    # Oil & Gas
    "RELIANCE": {"lot_size": 250, "sector": "Oil & Gas", "avg_premium": 30},
    "ONGC": {"lot_size": 1925, "sector": "Oil & Gas", "avg_premium": 4},
    "BPCL": {"lot_size": 1800, "sector": "Oil & Gas", "avg_premium": 4},
    "IOC": {"lot_size": 3250, "sector": "Oil & Gas", "avg_premium": 3},
    "GAIL": {"lot_size": 2750, "sector": "Oil & Gas", "avg_premium": 4},
    "HINDPETRO": {"lot_size": 1350, "sector": "Oil & Gas", "avg_premium": 5},
    "PETRONET": {"lot_size": 1800, "sector": "Oil & Gas", "avg_premium": 4},
    
    # Pharma & Healthcare
    "SUNPHARMA": {"lot_size": 350, "sector": "Pharma", "avg_premium": 18},
    "DRREDDY": {"lot_size": 125, "sector": "Pharma", "avg_premium": 65},
    "CIPLA": {"lot_size": 325, "sector": "Pharma", "avg_premium": 18},
    "DIVISLAB": {"lot_size": 100, "sector": "Pharma", "avg_premium": 55},
    "APOLLOHOSP": {"lot_size": 125, "sector": "Healthcare", "avg_premium": 70},
    "BIOCON": {"lot_size": 1800, "sector": "Pharma", "avg_premium": 4},
    "AUROPHARMA": {"lot_size": 500, "sector": "Pharma", "avg_premium": 12},
    "LUPIN": {"lot_size": 425, "sector": "Pharma", "avg_premium": 18},
    "ZYDUSLIFE": {"lot_size": 650, "sector": "Pharma", "avg_premium": 12},
    "TORNTPHARM": {"lot_size": 200, "sector": "Pharma", "avg_premium": 40},
    
    # Metals & Mining
    "TATASTEEL": {"lot_size": 5500, "sector": "Metals", "avg_premium": 3},
    "JSWSTEEL": {"lot_size": 675, "sector": "Metals", "avg_premium": 12},
    "HINDALCO": {"lot_size": 1075, "sector": "Metals", "avg_premium": 7},
    "VEDL": {"lot_size": 1550, "sector": "Metals", "avg_premium": 4},
    "COALINDIA": {"lot_size": 1200, "sector": "Mining", "avg_premium": 5},
    "SAIL": {"lot_size": 4750, "sector": "Metals", "avg_premium": 2},
    "NMDC": {"lot_size": 2250, "sector": "Mining", "avg_premium": 4},
    "NATIONALUM": {"lot_size": 3750, "sector": "Metals", "avg_premium": 3},
    
    # FMCG
    "HINDUNILVR": {"lot_size": 300, "sector": "FMCG", "avg_premium": 25},
    "ITC": {"lot_size": 1600, "sector": "FMCG", "avg_premium": 5},
    "NESTLEIND": {"lot_size": 25, "sector": "FMCG", "avg_premium": 250},
    "BRITANNIA": {"lot_size": 100, "sector": "FMCG", "avg_premium": 65},
    "DABUR": {"lot_size": 1250, "sector": "FMCG", "avg_premium": 6},
    "MARICO": {"lot_size": 800, "sector": "FMCG", "avg_premium": 8},
    "COLPAL": {"lot_size": 200, "sector": "FMCG", "avg_premium": 35},
    "GODREJCP": {"lot_size": 500, "sector": "FMCG", "avg_premium": 15},
    "TATACONSUM": {"lot_size": 500, "sector": "FMCG", "avg_premium": 15},
    "UBL": {"lot_size": 350, "sector": "FMCG", "avg_premium": 25},
    
    # Infrastructure & Capital Goods
    "L&T": {"lot_size": 150, "sector": "Infrastructure", "avg_premium": 40},
    "ADANIENT": {"lot_size": 250, "sector": "Infrastructure", "avg_premium": 30},
    "ADANIPORTS": {"lot_size": 400, "sector": "Infrastructure", "avg_premium": 18},
    "SIEMENS": {"lot_size": 75, "sector": "Capital Goods", "avg_premium": 80},
    "ABB": {"lot_size": 125, "sector": "Capital Goods", "avg_premium": 65},
    "BHEL": {"lot_size": 2100, "sector": "Capital Goods", "avg_premium": 4},
    "CUMMINSIND": {"lot_size": 200, "sector": "Capital Goods", "avg_premium": 40},
    "HAVELLS": {"lot_size": 350, "sector": "Capital Goods", "avg_premium": 25},
    "VOLTAS": {"lot_size": 400, "sector": "Capital Goods", "avg_premium": 18},
    
    # Cement
    "ULTRACEMCO": {"lot_size": 50, "sector": "Cement", "avg_premium": 120},
    "SHREECEM": {"lot_size": 25, "sector": "Cement", "avg_premium": 280},
    "AMBUJACEM": {"lot_size": 950, "sector": "Cement", "avg_premium": 8},
    "ACC": {"lot_size": 250, "sector": "Cement", "avg_premium": 30},
    "DALBHARAT": {"lot_size": 200, "sector": "Cement", "avg_premium": 35},
    "RAMCOCEM": {"lot_size": 550, "sector": "Cement", "avg_premium": 15},
    
    # Power & Utilities
    "POWERGRID": {"lot_size": 1800, "sector": "Power", "avg_premium": 4},
    "NTPC": {"lot_size": 1500, "sector": "Power", "avg_premium": 5},
    "TATAPOWER": {"lot_size": 1350, "sector": "Power", "avg_premium": 5},
    "ADANIPOWER": {"lot_size": 1200, "sector": "Power", "avg_premium": 6},
    
    # Telecom & Media
    "BHARTIARTL": {"lot_size": 350, "sector": "Telecom", "avg_premium": 20},
    "ZEEL": {"lot_size": 3000, "sector": "Media", "avg_premium": 3},
    "PVR": {"lot_size": 500, "sector": "Media", "avg_premium": 15},
}


# ============================================================================
# DATA CLASSES
# ============================================================================

class SignalType(Enum):
    BULLISH = "BULLISH"
    BEARISH = "BEARISH"
    NEUTRAL = "NEUTRAL"


class ConfidenceLevel(Enum):
    HIGH = "HIGH"           # 80%+ confidence - Max allocation
    MEDIUM = "MEDIUM"       # 60-80% confidence - Standard allocation
    LOW = "LOW"             # 40-60% confidence - Minimum allocation


@dataclass
class ScanResult:
    """Result from Tier 1 initial screening"""
    symbol: str
    sector: str
    lot_size: int
    signal: SignalType
    momentum_score: float  # 0-100
    volume_surge: float    # Percentage above average
    price_change: float    # Intraday change %
    tier1_reasoning: str
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class MomentumCandidate:
    """Result from Tier 2 deep analysis"""
    scan_result: ScanResult
    momentum_strength: float       # 0-100
    technical_score: float         # 0-100
    recommended_option: str        # CE or PE
    strike_price: float
    premium_estimate: float
    delta: float
    lots_affordable: int           # Based on capital
    position_size: float
    tier2_reasoning: str
    priority_score: float = 0.0


@dataclass
class TradeSignal:
    """Final validated trade signal from Tier 3"""
    candidate: MomentumCandidate
    confidence: ConfidenceLevel
    entry_price: float
    stoploss_price: float          # Wide stoploss - no trailing
    target1_price: float           # First target (50% profit)
    target2_price: float           # Second target (100% profit)
    risk_reward_ratio: float
    allocated_capital: float
    quantity: int                  # Number of lots
    tier3_reasoning: str
    gemini_recommendation: str
    execution_priority: int
    timestamp: datetime = field(default_factory=datetime.now)


# ============================================================================
# GEMINI DIRECT CLIENT - Direct API Integration
# ============================================================================

class GeminiDirectClient:
    """
    Direct integration with Gemini API for AI-powered analysis.
    Uses specific models for each tier of analysis.
    """
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or GEMINI_API_KEY
        self.session: Optional[aiohttp.ClientSession] = None
        self.fallback_to_local = not bool(self.api_key)
        
    async def _ensure_session(self):
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=30)
            )
    
    async def close(self):
        if self.session and not self.session.closed:
            await self.session.close()
    
    async def generate_content(self, model: str, prompt: str) -> Dict[str, Any]:
        """
        Generate content using specified Gemini model.
        Falls back to local service if direct API fails.
        """
        await self._ensure_session()
        
        # Try direct Gemini API first
        if self.api_key:
            try:
                url = f"{GEMINI_API_BASE}/{model}:generateContent?key={self.api_key}"
                payload = {
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {
                        "temperature": 0.4,
                        "topK": 40,
                        "topP": 0.95,
                        "maxOutputTokens": 2048
                    }
                }
                
                async with self.session.post(url, json=payload) as response:
                    if response.status == 200:
                        result = await response.json()
                        if "candidates" in result:
                            text = result["candidates"][0]["content"]["parts"][0]["text"]
                            return {"success": True, "response": text, "model": model}
            except Exception as e:
                logger.warning(f"Direct Gemini API failed: {e}, falling back to local service")
        
        # Fallback to local Gemini service
        return await self._fallback_local_service(model, prompt)
    
    async def _fallback_local_service(self, model: str, prompt: str) -> Dict[str, Any]:
        """Fallback to local Gemini Trade Service"""
        try:
            url = f"{GEMINI_SERVICE_URL}/api/analyze/custom"
            payload = {
                "prompt": prompt,
                "model": model,
                "context": "options_screening"
            }
            
            async with self.session.post(url, json=payload) as response:
                if response.status == 200:
                    result = await response.json()
                    return {"success": True, "response": result.get("analysis", ""), "model": model}
        except Exception as e:
            logger.error(f"Local Gemini service also failed: {e}")
        
        return {"success": False, "response": "", "model": model}
    
    async def screen_tier1(self, stock: str, market_data: Dict) -> Dict[str, Any]:
        """
        TIER 1 Screening using gemini-2.5-flash-lite
        High-speed initial momentum detection
        """
        prompt = f"""
You are an expert F&O trader analyzing {stock} for momentum trades.

MARKET DATA:
{json.dumps(market_data, indent=2)}

TASK: Perform rapid momentum screening
- Check for volume surge (>1.5x average)
- Identify price momentum direction
- Detect any unusual activity patterns
- Rate momentum strength 0-100

RESPOND IN EXACT JSON FORMAT:
{{
    "signal": "BULLISH" | "BEARISH" | "NEUTRAL",
    "momentum_score": <0-100>,
    "volume_surge_pct": <percentage>,
    "price_change_pct": <percentage>,
    "pass_tier1": true | false,
    "reasoning": "<brief 2-line reasoning>"
}}
"""
        return await self.generate_content(GEMINI_MODELS["tier1"], prompt)
    
    async def analyze_tier2(self, stock: str, scan_result: ScanResult, 
                            option_chain: Dict) -> Dict[str, Any]:
        """
        TIER 2 Deep Analysis using gemini-2.5-flash
        Detailed technical and options analysis
        """
        prompt = f"""
You are an expert options trader performing deep momentum analysis on {stock}.

TIER 1 SCAN RESULT:
- Signal: {scan_result.signal.value}
- Momentum Score: {scan_result.momentum_score}
- Volume Surge: {scan_result.volume_surge}%
- Sector: {scan_result.sector}
- Lot Size: {scan_result.lot_size}

OPTION CHAIN DATA:
{json.dumps(option_chain, indent=2)}

ANALYSIS REQUIREMENTS:
1. Validate momentum strength for trade execution
2. Select optimal strike price (delta 0.4-0.7 range)
3. Analyze premium value and capital efficiency
4. Consider liquidity (avoid illiquid strikes)
5. Rate technical momentum 0-100

STRIKE SELECTION CRITERIA:
- For BULLISH: CE with delta 0.4-0.6 (ATM or slightly OTM)
- For BEARISH: PE with delta 0.4-0.6 (ATM or slightly OTM)
- Prefer higher open interest for liquidity
- Balance premium cost vs delta sensitivity

RESPOND IN EXACT JSON FORMAT:
{{
    "pass_tier2": true | false,
    "momentum_strength": <0-100>,
    "technical_score": <0-100>,
    "recommended_option": "CE" | "PE",
    "strike_price": <price>,
    "premium_estimate": <price>,
    "delta": <0.0-1.0>,
    "gamma": <value>,
    "theta": <value>,
    "liquidity_grade": "A+" | "A" | "B" | "C",
    "priority_score": <0-100>,
    "reasoning": "<detailed 3-line analysis>"
}}
"""
        return await self.generate_content(GEMINI_MODELS["tier2"], prompt)
    
    async def confirm_tier3(self, candidate: MomentumCandidate, 
                            capital_available: float) -> Dict[str, Any]:
        """
        TIER 3 Final Confirmation using gemini-3-pro
        High-conviction trade validation with position sizing
        """
        prompt = f"""
You are a senior options strategist making final trade decisions. This is the FINAL CONFIRMATION before capital deployment.

CANDIDATE DETAILS:
- Symbol: {candidate.scan_result.symbol}
- Sector: {candidate.scan_result.sector}
- Signal: {candidate.scan_result.signal.value}
- Lot Size: {candidate.scan_result.lot_size}
- Option Type: {candidate.recommended_option}
- Strike: {candidate.strike_price}
- Premium: {candidate.premium_estimate}
- Delta: {candidate.delta}
- Momentum Strength: {candidate.momentum_strength}/100
- Technical Score: {candidate.technical_score}/100
- Priority Score: {candidate.priority_score}/100

TIER 1 REASONING: {candidate.scan_result.tier1_reasoning}
TIER 2 REASONING: {candidate.tier2_reasoning}

AVAILABLE CAPITAL: ₹{capital_available:,.2f}

CAPITAL ALLOCATION STRATEGY:
1. Calculate maximum lots affordable = Available Capital / (Premium × Lot Size)
2. For HIGH confidence (85%+): Use 40% of available capital
3. For MEDIUM confidence (70-85%): Use 25% of available capital  
4. For LOW confidence (60-70%): Use 15% of available capital
5. MAXIMIZE QUANTITY when confidence is high - more lots = more profit potential

STOPLOSS STRATEGY:
- Use WIDE stoploss (20-25% of premium) as we're trading high-confirmation setups
- NO trailing stoploss - let momentum run
- Target 1: 50% profit (exit 50% position)
- Target 2: 100% profit (exit remaining)

FINAL DECISION:
1. Validate all screening criteria
2. Assign confidence level (HIGH/MEDIUM/LOW)
3. Calculate exact position size and capital allocation
4. Set stoploss and targets
5. Provide execution recommendation

RESPOND IN EXACT JSON FORMAT:
{{
    "approved": true | false,
    "confidence": "HIGH" | "MEDIUM" | "LOW",
    "confidence_score": <60-100>,
    "allocated_capital": <amount in rupees>,
    "lots_to_trade": <number of lots>,
    "entry_price": <premium price>,
    "stoploss_price": <20-25% below entry>,
    "target1_price": <50% above entry>,
    "target2_price": <100% above entry>,
    "risk_reward_ratio": <calculated ratio>,
    "execution_priority": <1-10, 1 being highest>,
    "recommendation": "<EXECUTE | WAIT | SKIP>",
    "reasoning": "<comprehensive 4-line final reasoning>",
    "exit_strategy": "<brief exit plan>"
}}
"""
        return await self.generate_content(GEMINI_MODELS["tier3"], prompt)
    
    async def consult_exit(self, trade_info: Dict, current_pnl: float,
                           market_conditions: Dict) -> Dict[str, Any]:
        """
        Exit Consultation using gemini-3-pro
        Real-time exit decision support
        """
        prompt = f"""
You are an expert options trader monitoring an ACTIVE POSITION and need to make an EXIT DECISION.

ACTIVE TRADE:
{json.dumps(trade_info, indent=2)}

CURRENT P&L: {current_pnl:+.2f}% ({"PROFIT" if current_pnl > 0 else "LOSS"})

CURRENT MARKET CONDITIONS:
{json.dumps(market_conditions, indent=2)}

EXIT DECISION FRAMEWORK:
1. If P&L > +50%: Consider partial exit (50% position)
2. If P&L > +100%: Strongly consider full exit
3. If P&L < -20%: Stoploss triggered - EXIT
4. Analyze if momentum is still intact
5. Check time decay impact (theta)
6. Consider market-wide conditions

IMPORTANT:
- We use WIDE stoploss (no trailing) for momentum trades
- Let winners run, cut losers quick
- Time decay accelerates near expiry

RESPOND IN EXACT JSON FORMAT:
{{
    "action": "HOLD" | "PARTIAL_EXIT" | "FULL_EXIT" | "STOPLOSS_HIT",
    "exit_percentage": <0-100>,
    "urgency": "IMMEDIATE" | "NORMAL" | "CAN_WAIT",
    "reasoning": "<3-line explanation>",
    "next_review_minutes": <minutes until next check>
}}
"""
        return await self.generate_content(GEMINI_MODELS["exit"], prompt)


# ============================================================================
# ELITE OPTIONS SCANNER - Main Scanner Class
# ============================================================================

class EliteOptionsScanner:
    """
    Elite 3-Tier AI-Powered F&O Options Scanner
    
    Implements intelligent screening with:
    - Tier 1: Rapid screening (gemini-2.5-flash-lite)
    - Tier 2: Deep analysis (gemini-2.5-flash)
    - Tier 3: Final confirmation (gemini-3-pro)
    - Exit monitoring (gemini-3-pro)
    """
    
    def __init__(self, total_capital: float = 100000.0, dhan_client=None):
        self.total_capital = total_capital
        self.available_capital = total_capital
        self.dhan_client = dhan_client
        self.gemini = GeminiDirectClient()
        
        # Active state
        self.active_signals: List[TradeSignal] = []
        self.scan_results: List[ScanResult] = []
        self.candidates: List[MomentumCandidate] = []
        
        # Configuration
        self.max_positions = 5
        self.max_capital_per_trade = 0.4  # 40% max per trade
        self.min_momentum_score = 65
        self.min_technical_score = 60
        
        logger.info(f"Elite Scanner initialized with ₹{total_capital:,.2f} capital")
    
    async def initialize(self):
        """Initialize scanner with Dhan client if not provided"""
        if not self.dhan_client:
            try:
                from ..core.dhan_connector import DhanAPIClient
                self.dhan_client = DhanAPIClient()
                logger.info("Dhan client initialized")
            except Exception as e:
                logger.error(f"Failed to initialize Dhan client: {e}")
    
    async def close(self):
        """Cleanup resources"""
        await self.gemini.close()
    
    # ==========================================================================
    # TIER 1: HIGH-SPEED SCREENING
    # ==========================================================================
    
    async def tier1_rapid_screening(self, stocks: List[str] = None) -> List[ScanResult]:
        """
        Tier 1: Rapid market scan using gemini-2.5-flash-lite
        Filters 80+ stocks down to momentum candidates
        """
        stocks = stocks or list(FO_STOCKS.keys())
        self.scan_results = []
        
        logger.info(f"[TIER 1] Starting rapid screening of {len(stocks)} stocks using {GEMINI_MODELS['tier1']}")
        
        # Batch process for efficiency
        batch_size = 10
        for i in range(0, len(stocks), batch_size):
            batch = stocks[i:i + batch_size]
            tasks = [self._screen_stock_tier1(stock) for stock in batch]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for result in results:
                if isinstance(result, ScanResult) and result.signal != SignalType.NEUTRAL:
                    if result.momentum_score >= self.min_momentum_score:
                        self.scan_results.append(result)
        
        # Sort by momentum score
        self.scan_results.sort(key=lambda x: x.momentum_score, reverse=True)
        
        logger.info(f"[TIER 1] Passed {len(self.scan_results)} stocks to Tier 2")
        return self.scan_results
    
    async def _screen_stock_tier1(self, symbol: str) -> Optional[ScanResult]:
        """Screen individual stock in Tier 1"""
        try:
            stock_info = FO_STOCKS.get(symbol, {})
            
            # Get market data (simulated if Dhan not available)
            market_data = await self._get_market_data(symbol)
            
            # Call Gemini for Tier 1 analysis
            result = await self.gemini.screen_tier1(symbol, market_data)
            
            if result["success"]:
                try:
                    # Parse JSON response
                    response_text = result["response"]
                    # Extract JSON from response
                    json_start = response_text.find("{")
                    json_end = response_text.rfind("}") + 1
                    if json_start != -1 and json_end > json_start:
                        analysis = json.loads(response_text[json_start:json_end])
                        
                        if analysis.get("pass_tier1", False):
                            signal_str = analysis.get("signal", "NEUTRAL")
                            signal = SignalType[signal_str] if signal_str in SignalType.__members__ else SignalType.NEUTRAL
                            
                            return ScanResult(
                                symbol=symbol,
                                sector=stock_info.get("sector", "Unknown"),
                                lot_size=stock_info.get("lot_size", 1),
                                signal=signal,
                                momentum_score=float(analysis.get("momentum_score", 0)),
                                volume_surge=float(analysis.get("volume_surge_pct", 0)),
                                price_change=float(analysis.get("price_change_pct", 0)),
                                tier1_reasoning=analysis.get("reasoning", "")
                            )
                except json.JSONDecodeError:
                    logger.warning(f"Failed to parse Tier 1 response for {symbol}")
        except Exception as e:
            logger.error(f"Tier 1 screening failed for {symbol}: {e}")
        
        return None
    
    async def _get_market_data(self, symbol: str) -> Dict:
        """Get market data for symbol"""
        # Try Dhan client first
        if self.dhan_client:
            try:
                quote = await self.dhan_client.get_quote(symbol)
                if quote:
                    return {
                        "symbol": symbol,
                        "ltp": quote.get("ltp", 0),
                        "open": quote.get("open", 0),
                        "high": quote.get("high", 0),
                        "low": quote.get("low", 0),
                        "volume": quote.get("volume", 0),
                        "prev_close": quote.get("prev_close", 0),
                        "change_pct": quote.get("change_pct", 0)
                    }
            except Exception as e:
                logger.warning(f"Failed to get market data from Dhan for {symbol}: {e}")
        
        # Fallback to simulated data
        import random
        base_price = random.uniform(100, 5000)
        return {
            "symbol": symbol,
            "ltp": base_price,
            "open": base_price * 0.99,
            "high": base_price * 1.02,
            "low": base_price * 0.98,
            "volume": random.randint(100000, 5000000),
            "prev_close": base_price * 0.995,
            "change_pct": random.uniform(-2, 2)
        }
    
    # ==========================================================================
    # TIER 2: DEEP MOMENTUM ANALYSIS
    # ==========================================================================
    
    async def tier2_deep_analysis(self, scan_results: List[ScanResult] = None) -> List[MomentumCandidate]:
        """
        Tier 2: Deep momentum analysis using gemini-2.5-flash
        Analyzes option chain and selects optimal strikes
        """
        scan_results = scan_results or self.scan_results
        self.candidates = []
        
        logger.info(f"[TIER 2] Starting deep analysis of {len(scan_results)} candidates using {GEMINI_MODELS['tier2']}")
        
        for scan_result in scan_results:
            candidate = await self._analyze_tier2(scan_result)
            if candidate and candidate.technical_score >= self.min_technical_score:
                # Calculate priority score
                candidate.priority_score = self._calculate_priority(candidate)
                self.candidates.append(candidate)
        
        # Sort by priority score
        self.candidates.sort(key=lambda x: x.priority_score, reverse=True)
        
        logger.info(f"[TIER 2] Passed {len(self.candidates)} candidates to Tier 3")
        return self.candidates
    
    async def _analyze_tier2(self, scan_result: ScanResult) -> Optional[MomentumCandidate]:
        """Deep analysis of individual stock"""
        try:
            # Get option chain data
            option_chain = await self._get_option_chain(scan_result.symbol)
            
            # Call Gemini for Tier 2 analysis
            result = await self.gemini.analyze_tier2(scan_result, option_chain)
            
            if result["success"]:
                try:
                    response_text = result["response"]
                    json_start = response_text.find("{")
                    json_end = response_text.rfind("}") + 1
                    if json_start != -1 and json_end > json_start:
                        analysis = json.loads(response_text[json_start:json_end])
                        
                        if analysis.get("pass_tier2", False):
                            premium = float(analysis.get("premium_estimate", 0))
                            lot_size = scan_result.lot_size
                            position_size = premium * lot_size
                            lots_affordable = int(self.available_capital / position_size) if position_size > 0 else 0
                            
                            return MomentumCandidate(
                                scan_result=scan_result,
                                momentum_strength=float(analysis.get("momentum_strength", 0)),
                                technical_score=float(analysis.get("technical_score", 0)),
                                recommended_option=analysis.get("recommended_option", "CE"),
                                strike_price=float(analysis.get("strike_price", 0)),
                                premium_estimate=premium,
                                delta=float(analysis.get("delta", 0)),
                                lots_affordable=lots_affordable,
                                position_size=position_size,
                                tier2_reasoning=analysis.get("reasoning", "")
                            )
                except json.JSONDecodeError:
                    logger.warning(f"Failed to parse Tier 2 response for {scan_result.symbol}")
        except Exception as e:
            logger.error(f"Tier 2 analysis failed for {scan_result.symbol}: {e}")
        
        return None
    
    async def _get_option_chain(self, symbol: str) -> Dict:
        """Get option chain for symbol"""
        if self.dhan_client:
            try:
                chain = await self.dhan_client.get_option_chain(symbol)
                if chain:
                    return chain
            except Exception as e:
                logger.warning(f"Failed to get option chain from Dhan for {symbol}: {e}")
        
        # Simulated option chain
        import random
        base_price = random.uniform(1000, 3000)
        strikes = []
        for i in range(-5, 6):
            strike = round((base_price + i * 50) / 50) * 50
            strikes.append({
                "strike": strike,
                "ce_premium": max(5, (base_price - strike) + random.uniform(10, 50)),
                "pe_premium": max(5, (strike - base_price) + random.uniform(10, 50)),
                "ce_delta": 0.5 - i * 0.08,
                "pe_delta": -(0.5 + i * 0.08),
                "ce_oi": random.randint(10000, 500000),
                "pe_oi": random.randint(10000, 500000)
            })
        
        return {"symbol": symbol, "underlying": base_price, "strikes": strikes}
    
    def _calculate_priority(self, candidate: MomentumCandidate) -> float:
        """Calculate priority score for capital allocation"""
        # Weighted scoring
        score = (
            candidate.momentum_strength * 0.3 +
            candidate.technical_score * 0.3 +
            (candidate.delta * 100) * 0.2 +  # Prefer delta 0.5
            (100 - min(candidate.premium_estimate, 100)) * 0.1 +  # Lower premium preferred
            (min(candidate.lots_affordable, 10) * 10) * 0.1  # More affordable = better
        )
        
        # Sector bonus (momentum sectors)
        momentum_sectors = {"Banking", "IT", "Auto", "NBFC"}
        if candidate.scan_result.sector in momentum_sectors:
            score *= 1.1
        
        return min(score, 100)
    
    # ==========================================================================
    # TIER 3: FINAL CONFIRMATION & CAPITAL ALLOCATION
    # ==========================================================================
    
    async def tier3_confirmation(self, candidates: List[MomentumCandidate] = None) -> List[TradeSignal]:
        """
        Tier 3: Final confirmation using gemini-3-pro
        Validates trades and allocates capital intelligently
        """
        candidates = candidates or self.candidates
        self.active_signals = []
        
        remaining_capital = self.available_capital
        
        logger.info(f"[TIER 3] Final confirmation of {len(candidates)} candidates using {GEMINI_MODELS['tier3']}")
        
        for candidate in candidates:
            if len(self.active_signals) >= self.max_positions:
                break
            
            if remaining_capital < candidate.position_size:
                continue
            
            signal = await self._confirm_tier3(candidate, remaining_capital)
            
            if signal:
                self.active_signals.append(signal)
                remaining_capital -= signal.allocated_capital
                logger.info(f"[TIER 3] APPROVED: {signal.candidate.scan_result.symbol} | "
                           f"Confidence: {signal.confidence.value} | "
                           f"Lots: {signal.quantity} | "
                           f"Capital: ₹{signal.allocated_capital:,.2f}")
        
        logger.info(f"[TIER 3] Generated {len(self.active_signals)} trade signals")
        return self.active_signals
    
    async def _confirm_tier3(self, candidate: MomentumCandidate, 
                             capital_available: float) -> Optional[TradeSignal]:
        """Get Tier 3 confirmation for candidate"""
        try:
            result = await self.gemini.confirm_tier3(candidate, capital_available)
            
            if result["success"]:
                try:
                    response_text = result["response"]
                    json_start = response_text.find("{")
                    json_end = response_text.rfind("}") + 1
                    if json_start != -1 and json_end > json_start:
                        analysis = json.loads(response_text[json_start:json_end])
                        
                        if analysis.get("approved", False):
                            confidence_str = analysis.get("confidence", "LOW")
                            confidence = ConfidenceLevel[confidence_str] if confidence_str in ConfidenceLevel.__members__ else ConfidenceLevel.LOW
                            
                            return TradeSignal(
                                candidate=candidate,
                                confidence=confidence,
                                entry_price=float(analysis.get("entry_price", candidate.premium_estimate)),
                                stoploss_price=float(analysis.get("stoploss_price", candidate.premium_estimate * 0.75)),
                                target1_price=float(analysis.get("target1_price", candidate.premium_estimate * 1.5)),
                                target2_price=float(analysis.get("target2_price", candidate.premium_estimate * 2.0)),
                                risk_reward_ratio=float(analysis.get("risk_reward_ratio", 2.0)),
                                allocated_capital=float(analysis.get("allocated_capital", 0)),
                                quantity=int(analysis.get("lots_to_trade", 1)),
                                tier3_reasoning=analysis.get("reasoning", ""),
                                gemini_recommendation=analysis.get("recommendation", "EXECUTE"),
                                execution_priority=int(analysis.get("execution_priority", 5))
                            )
                except json.JSONDecodeError:
                    logger.warning(f"Failed to parse Tier 3 response for {candidate.scan_result.symbol}")
        except Exception as e:
            logger.error(f"Tier 3 confirmation failed for {candidate.scan_result.symbol}: {e}")
        
        return None
    
    # ==========================================================================
    # MAIN SCANNING WORKFLOW
    # ==========================================================================
    
    async def full_scan(self, stocks: List[str] = None) -> List[TradeSignal]:
        """
        Execute full 3-tier scanning workflow
        
        Returns list of ready-to-execute trade signals
        """
        logger.info("=" * 60)
        logger.info("ELITE OPTIONS SCANNER - FULL SCAN INITIATED")
        logger.info(f"Available Capital: ₹{self.available_capital:,.2f}")
        logger.info(f"Max Positions: {self.max_positions}")
        logger.info("=" * 60)
        
        try:
            # Tier 1: Rapid screening
            logger.info("\n[PHASE 1] Tier 1 - Rapid Momentum Screening")
            scan_results = await self.tier1_rapid_screening(stocks)
            
            if not scan_results:
                logger.info("No stocks passed Tier 1 screening")
                return []
            
            # Tier 2: Deep analysis
            logger.info("\n[PHASE 2] Tier 2 - Deep Momentum Analysis")
            candidates = await self.tier2_deep_analysis(scan_results)
            
            if not candidates:
                logger.info("No stocks passed Tier 2 analysis")
                return []
            
            # Tier 3: Final confirmation
            logger.info("\n[PHASE 3] Tier 3 - Final Confirmation & Capital Allocation")
            signals = await self.tier3_confirmation(candidates)
            
            # Summary
            logger.info("\n" + "=" * 60)
            logger.info("SCAN COMPLETE - SUMMARY")
            logger.info("=" * 60)
            logger.info(f"Tier 1 Passed: {len(scan_results)}")
            logger.info(f"Tier 2 Passed: {len(candidates)}")
            logger.info(f"Tier 3 Approved: {len(signals)}")
            
            for i, signal in enumerate(signals, 1):
                logger.info(f"\nSignal #{i}:")
                logger.info(f"  Symbol: {signal.candidate.scan_result.symbol}")
                logger.info(f"  Option: {signal.candidate.recommended_option}")
                logger.info(f"  Strike: {signal.candidate.strike_price}")
                logger.info(f"  Entry: ₹{signal.entry_price}")
                logger.info(f"  Stoploss: ₹{signal.stoploss_price} (Wide)")
                logger.info(f"  Target 1: ₹{signal.target1_price} (50% profit)")
                logger.info(f"  Target 2: ₹{signal.target2_price} (100% profit)")
                logger.info(f"  Lots: {signal.quantity}")
                logger.info(f"  Capital: ₹{signal.allocated_capital:,.2f}")
                logger.info(f"  Confidence: {signal.confidence.value}")
            
            return signals
            
        except Exception as e:
            logger.error(f"Full scan failed: {e}")
            return []
    
    # ==========================================================================
    # EXIT MONITORING
    # ==========================================================================
    
    async def consult_exit(self, trade_info: Dict, current_pnl: float,
                           market_conditions: Dict = None) -> Dict[str, Any]:
        """
        Consult Gemini 3 Pro for exit decisions on active trades
        """
        market_conditions = market_conditions or {}
        
        result = await self.gemini.consult_exit(trade_info, current_pnl, market_conditions)
        
        if result["success"]:
            try:
                response_text = result["response"]
                json_start = response_text.find("{")
                json_end = response_text.rfind("}") + 1
                if json_start != -1 and json_end > json_start:
                    return json.loads(response_text[json_start:json_end])
            except json.JSONDecodeError:
                pass
        
        # Default response
        return {
            "action": "HOLD",
            "exit_percentage": 0,
            "urgency": "NORMAL",
            "reasoning": "Unable to analyze - holding position",
            "next_review_minutes": 5
        }
    
    # ==========================================================================
    # UTILITY METHODS
    # ==========================================================================
    
    def get_scan_summary(self) -> Dict[str, Any]:
        """Get summary of last scan"""
        return {
            "total_capital": self.total_capital,
            "available_capital": self.available_capital,
            "tier1_results": len(self.scan_results),
            "tier2_candidates": len(self.candidates),
            "active_signals": len(self.active_signals),
            "signals": [
                {
                    "symbol": s.candidate.scan_result.symbol,
                    "option": s.candidate.recommended_option,
                    "strike": s.candidate.strike_price,
                    "entry": s.entry_price,
                    "stoploss": s.stoploss_price,
                    "target1": s.target1_price,
                    "target2": s.target2_price,
                    "lots": s.quantity,
                    "capital": s.allocated_capital,
                    "confidence": s.confidence.value
                }
                for s in self.active_signals
            ]
        }
    
    def update_capital(self, new_capital: float):
        """Update available capital"""
        self.available_capital = new_capital
        logger.info(f"Capital updated to ₹{new_capital:,.2f}")


# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

async def main():
    """Test the Elite Options Scanner"""
    scanner = EliteOptionsScanner(total_capital=200000.0)
    
    try:
        # Run full scan
        signals = await scanner.full_scan()
        
        # Print results
        print("\n" + "=" * 60)
        print("TRADE SIGNALS FOR EXECUTION")
        print("=" * 60)
        
        for signal in signals:
            print(f"\n{signal.candidate.scan_result.symbol} {signal.candidate.recommended_option}")
            print(f"  Strike: {signal.candidate.strike_price}")
            print(f"  Entry: ₹{signal.entry_price}")
            print(f"  SL: ₹{signal.stoploss_price}")
            print(f"  T1: ₹{signal.target1_price}")
            print(f"  T2: ₹{signal.target2_price}")
            print(f"  Lots: {signal.quantity}")
            print(f"  Capital: ₹{signal.allocated_capital:,.2f}")
            
    finally:
        await scanner.close()


if __name__ == "__main__":
    asyncio.run(main())
