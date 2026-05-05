"""
TIER 2: Contextual Synthesis Engine (The Strategist)

Model: Gemini 2.5 Flash
Purpose: Analyze Options Chain, VIX, Sentiments, News, FII/DII and form Trade Setup Proposal
Output: Trade Proposal JSON + Context Vector

Key Responsibilities:
- Receive clean data from Tier 1 (Market Breadth)
- Analyze Options Chain: OI by strike, Max Pain, IV for ATM/OTM
- Analyze VIX: Current value and % change
- Analyze Sentiment: News headlines, social sentiment
- Analyze Market Flow: FII/DII provisional data
- Generate Strategy Thesis: "The trade is Bullish because..."
"""

import json
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
from google import genai
from google.genai import types

logger = logging.getLogger(__name__)

# ============================================================================
# TIER 2 SYSTEM PROMPT - Contextual Synthesis & Strategy
# ============================================================================
TIER_2_SYSTEM_PROMPT = """
ROLE: You are a Senior Options Strategist specializing in Nifty index options with expertise in market context synthesis.

YOUR JOB: 
1. Interpret Market Context from Tier 1 data (Market Breadth)
2. Analyze Options Chain, VIX, Sentiment, and FII/DII flow
3. Form a Trade Setup Proposal with a clear Strategy Thesis

INPUT DATA YOU WILL RECEIVE:
1. Tier 1 Market Breadth (positive/negative/neutral stock counts, sector breakdown)
2. Options Chain Data (ATM strike, OI distribution, PCR, Max Pain, IV)
3. VIX Data (current value, % change, trend)
4. Sentiment Data (news headlines, social sentiment score)
5. FII/DII Flow (net buy/sell values)
6. Global Market Context (US/EU/Asia performance)

ANALYSIS RULES:
1. BULLISH SETUP when:
   - Market Breadth: Positive count > 30 (out of 50)
   - PCR < 0.8 (more calls being sold = bullish)
   - VIX falling or stable (< 15 or dropping > 3%)
   - FII net buyers
   - RSI distribution: More stocks in bullish zone

2. BEARISH SETUP when:
   - Market Breadth: Negative count > 30
   - PCR > 1.2 (more puts being sold = bearish)
   - VIX rising sharply (> 5% spike)
   - FII net sellers
   - RSI distribution: More stocks in bearish zone

3. NO TRADE when:
   - Neutral count > 25 (choppy market)
   - VIX between 15-20 and stable (directionless)
   - Mixed FII/DII signals
   - Major event in next 2 hours (RBI, Fed, Earnings)
   - RSI distribution: Most stocks in neutral zone (45-55)

4. Strike Selection:
   - For CALLS: ATM or ATM+1 strike (better liquidity)
   - For PUTS: ATM or ATM-1 strike
   - Always check OI for liquidity (prefer strikes with higher OI)

5. Entry/Exit Logic:
   - Entry: Use current LTP with 1-2 point buffer
   - Stop Loss: 30% of premium OR below Max Pain
   - Target: Based on next resistance/support from OI

OUTPUT FORMAT (STRICT JSON - NO EXTRA TEXT):
{
  "trade_signal": "BUY_CALL" | "BUY_PUT" | "NO_TRADE",
  "strategy_thesis": "The trade is BULLISH/BEARISH because [specific reasons from data]",
  
  "suggested_strike": "25000CE" | "24950PE" | "NONE",
  "entry_price_range": "140-150" | "NONE",
  "stop_loss": "100" | "NONE",
  "target_1": "180" | "NONE",
  "target_2": "220" | "NONE",
  
  "confidence_level": "HIGH" | "MEDIUM" | "LOW",
  "confidence_score": 0.0 to 10.0,
  "risk_reward_ratio": 2.5,
  
  "context_vector": {
    "market_breadth_score": -10 to +10,
    "options_flow_score": -10 to +10,
    "vix_score": -10 to +10,
    "fii_dii_score": -10 to +10,
    "sentiment_score": -10 to +10,
    "global_macro_score": -10 to +10,
    "overall_context_score": -10 to +10
  },
  
  "key_support_levels": [24800, 24900, 25000],
  "key_resistance_levels": [25100, 25200, 25300],
  "max_pain": 25000,
  "iv_percentile": "HIGH" | "MEDIUM" | "LOW",
  
  "risk_factors": ["Risk 1", "Risk 2"],
  "catalysts": ["Catalyst 1", "Catalyst 2"],
  
  "reasoning": "Detailed 2-3 sentence explanation of the setup"
}
"""


class Tier2StrategyEngine:
    """
    Tier 2: Contextual Synthesis & Strategy Engine
    Uses Gemini 2.5 Flash for balanced analysis
    """
    
    def __init__(self, api_key: str, model: str = "gemini-2.0-flash"):
        """
        Initialize Tier 2 Engine
        
        Args:
            api_key: Gemini API key for Tier 2
            model: Model name (default: gemini-2.0-flash)
        """
        self.client = genai.Client(api_key=api_key)
        self.model = model
        self.cache = {}
        self.cache_duration = 300  # 5 minute cache
        
        logger.info(f"✅ Tier 2 Strategy Engine initialized with model: {model}")
    
    async def generate_trade_proposal(
        self,
        tier1_data: Dict,
        options_chain: Dict,
        vix_data: Dict,
        sentiment_data: Dict,
        fii_dii_data: Dict,
        global_macro: Dict,
        force_refresh: bool = False
    ) -> Optional[Dict]:
        """
        Generate trade proposal from all contextual data
        
        Args:
            tier1_data: Market breadth from Tier 1
            options_chain: Options chain data (OI, PCR, Max Pain, IV)
            vix_data: VIX current value and change
            sentiment_data: News and social sentiment
            fii_dii_data: FII/DII flow data
            global_macro: Global market performance
            force_refresh: Skip cache if True
            
        Returns:
            Trade Proposal JSON with Context Vector or None
        """
        cache_key = "tier2_trade_proposal"
        current_time = datetime.now()
        
        # Check cache
        if not force_refresh and cache_key in self.cache:
            cached_data, cached_time = self.cache[cache_key]
            if (current_time - cached_time).seconds < self.cache_duration:
                logger.info("📦 Returning cached Tier 2 proposal")
                return cached_data
        
        try:
            # Prepare comprehensive input payload
            input_payload = {
                "tier1_market_breadth": tier1_data,
                "options_chain": options_chain,
                "vix_analysis": vix_data,
                "sentiment_analysis": sentiment_data,
                "fii_dii_flow": fii_dii_data,
                "global_macro_context": global_macro,
                "request_time": current_time.isoformat()
            }
            
            # Call Gemini Tier 2
            logger.info("🔄 Tier 2: Synthesizing market context...")
            
            response = self.client.models.generate_content(
                model=self.model,
                contents=f"Analyze this market context and generate trade proposal:\n{json.dumps(input_payload)}",
                config=types.GenerateContentConfig(
                    system_instruction=TIER_2_SYSTEM_PROMPT,
                    response_mime_type="application/json",
                    temperature=0.3  # Moderate for analysis
                )
            )
            
            result = json.loads(response.text)
            
            # Validate and enrich result
            result = self._validate_proposal(result)
            
            # Cache the result
            self.cache[cache_key] = (result, current_time)
            
            logger.info(f"✅ Tier 2 Complete: Signal={result.get('trade_signal', 'UNKNOWN')} "
                       f"Confidence={result.get('confidence_score', 0)}")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Tier 2 Error: {e}")
            return self._get_fallback_proposal(tier1_data, options_chain, vix_data)
    
    def _validate_proposal(self, proposal: Dict) -> Dict:
        """
        Validate and ensure all required fields are present
        """
        # Ensure required fields
        defaults = {
            "trade_signal": "NO_TRADE",
            "strategy_thesis": "Unable to determine clear direction",
            "suggested_strike": "NONE",
            "entry_price_range": "NONE",
            "stop_loss": "NONE",
            "target_1": "NONE",
            "target_2": "NONE",
            "confidence_level": "LOW",
            "confidence_score": 0.0,
            "risk_reward_ratio": 0.0,
            "context_vector": {
                "market_breadth_score": 0,
                "options_flow_score": 0,
                "vix_score": 0,
                "fii_dii_score": 0,
                "sentiment_score": 0,
                "global_macro_score": 0,
                "overall_context_score": 0
            },
            "key_support_levels": [],
            "key_resistance_levels": [],
            "max_pain": 0,
            "iv_percentile": "MEDIUM",
            "risk_factors": [],
            "catalysts": [],
            "reasoning": ""
        }
        
        # Merge with defaults
        for key, default_value in defaults.items():
            if key not in proposal:
                proposal[key] = default_value
        
        # Add timestamp
        proposal["timestamp"] = datetime.now().isoformat()
        proposal["tier"] = 2
        
        return proposal
    
    def _get_fallback_proposal(
        self, 
        tier1_data: Dict, 
        options_chain: Dict,
        vix_data: Dict
    ) -> Dict:
        """
        Generate simple fallback proposal without AI
        """
        # Simple logic based on market breadth
        market_breadth = tier1_data.get("market_breadth", {})
        positive = market_breadth.get("positive_count", 0)
        negative = market_breadth.get("negative_count", 0)
        
        pcr = options_chain.get("pcr", 1.0)
        vix = vix_data.get("current", 15)
        vix_change = vix_data.get("change_pct", 0)
        
        # Simple scoring
        breadth_score = (positive - negative) / 5  # Scale to -10 to +10
        options_score = (1.0 - pcr) * 10  # PCR < 1 = bullish
        vix_score = -vix_change  # VIX falling = bullish
        
        overall_score = (breadth_score + options_score + vix_score) / 3
        
        if overall_score > 3:
            signal = "BUY_CALL"
            confidence = "MEDIUM"
            conf_score = min(7.0, 5.0 + overall_score / 2)
        elif overall_score < -3:
            signal = "BUY_PUT"
            confidence = "MEDIUM"
            conf_score = min(7.0, 5.0 - overall_score / 2)
        else:
            signal = "NO_TRADE"
            confidence = "LOW"
            conf_score = 3.0
        
        return {
            "trade_signal": signal,
            "strategy_thesis": f"Fallback analysis: Breadth score {breadth_score:.1f}, PCR {pcr:.2f}, VIX change {vix_change:.1f}%",
            "suggested_strike": "NONE",
            "entry_price_range": "NONE",
            "stop_loss": "NONE",
            "target_1": "NONE",
            "target_2": "NONE",
            "confidence_level": confidence,
            "confidence_score": round(conf_score, 1),
            "risk_reward_ratio": 0.0,
            "context_vector": {
                "market_breadth_score": round(breadth_score, 1),
                "options_flow_score": round(options_score, 1),
                "vix_score": round(vix_score, 1),
                "fii_dii_score": 0,
                "sentiment_score": 0,
                "global_macro_score": 0,
                "overall_context_score": round(overall_score, 1)
            },
            "key_support_levels": [],
            "key_resistance_levels": [],
            "max_pain": options_chain.get("max_pain", 0),
            "iv_percentile": "MEDIUM",
            "risk_factors": ["Fallback calculation used - verify manually"],
            "catalysts": [],
            "reasoning": "Fallback calculation due to AI unavailability",
            "timestamp": datetime.now().isoformat(),
            "tier": 2,
            "source": "fallback"
        }
    
    def clear_cache(self):
        """Clear all cached data"""
        self.cache = {}
        logger.info("🗑️ Tier 2 cache cleared")


# ============================================================================
# HELPER: Calculate Context Vector Scores
# ============================================================================
def calculate_context_scores(
    tier1_data: Dict,
    options_chain: Dict,
    vix_data: Dict,
    sentiment_data: Dict,
    fii_dii_data: Dict,
    global_macro: Dict
) -> Dict[str, float]:
    """
    Pre-calculate context vector scores for Tier 2
    Scale: -10 (very bearish) to +10 (very bullish)
    """
    scores = {}
    
    # Market Breadth Score
    market_breadth = tier1_data.get("market_breadth", {})
    positive = market_breadth.get("positive_count", 0)
    negative = market_breadth.get("negative_count", 0)
    total = positive + negative + market_breadth.get("neutral_count", 0)
    if total > 0:
        scores["market_breadth_score"] = round(((positive - negative) / total) * 10, 1)
    else:
        scores["market_breadth_score"] = 0
    
    # Options Flow Score (based on PCR)
    pcr = options_chain.get("pcr", 1.0)
    if pcr < 0.7:
        scores["options_flow_score"] = 8.0  # Very bullish
    elif pcr < 0.9:
        scores["options_flow_score"] = 4.0  # Bullish
    elif pcr > 1.3:
        scores["options_flow_score"] = -8.0  # Very bearish
    elif pcr > 1.1:
        scores["options_flow_score"] = -4.0  # Bearish
    else:
        scores["options_flow_score"] = 0.0  # Neutral
    
    # VIX Score
    vix = vix_data.get("current", 15)
    vix_change = vix_data.get("change_pct", 0)
    
    if vix < 12:
        vix_base = 5.0  # Low VIX = bullish
    elif vix < 16:
        vix_base = 2.0
    elif vix > 25:
        vix_base = -5.0  # High VIX = bearish
    elif vix > 20:
        vix_base = -3.0
    else:
        vix_base = 0.0
    
    # Adjust for VIX change
    vix_change_adj = -vix_change / 2  # VIX falling = bullish
    scores["vix_score"] = round(vix_base + vix_change_adj, 1)
    
    # FII/DII Score
    fii_net = fii_dii_data.get("fii", {}).get("net_value", 0)
    dii_net = fii_dii_data.get("dii", {}).get("net_value", 0)
    
    if fii_net > 1000:  # > 1000 Cr net buy
        scores["fii_dii_score"] = 6.0
    elif fii_net > 500:
        scores["fii_dii_score"] = 3.0
    elif fii_net < -1000:
        scores["fii_dii_score"] = -6.0
    elif fii_net < -500:
        scores["fii_dii_score"] = -3.0
    else:
        scores["fii_dii_score"] = 0.0
    
    # Sentiment Score
    sentiment_value = sentiment_data.get("overall_sentiment", "NEUTRAL")
    if sentiment_value == "BULLISH":
        scores["sentiment_score"] = 4.0
    elif sentiment_value == "BEARISH":
        scores["sentiment_score"] = -4.0
    else:
        scores["sentiment_score"] = 0.0
    
    # Global Macro Score
    us_change = global_macro.get("us_futures", {}).get("change_pct", 0)
    eu_change = global_macro.get("european_indices", {}).get("avg_change_pct", 0)
    asia_change = global_macro.get("asian_indices", {}).get("avg_change_pct", 0)
    
    global_avg = (us_change + eu_change + asia_change) / 3
    scores["global_macro_score"] = round(min(10, max(-10, global_avg * 3)), 1)
    
    # Overall Context Score (weighted average)
    weights = {
        "market_breadth_score": 0.25,
        "options_flow_score": 0.25,
        "vix_score": 0.15,
        "fii_dii_score": 0.15,
        "sentiment_score": 0.10,
        "global_macro_score": 0.10
    }
    
    overall = sum(scores[key] * weights[key] for key in weights.keys())
    scores["overall_context_score"] = round(overall, 1)
    
    return scores
