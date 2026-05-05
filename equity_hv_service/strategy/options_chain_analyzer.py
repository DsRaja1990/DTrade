"""
╔══════════════════════════════════════════════════════════════════════════════════════╗
║                     OPTIONS CHAIN ANALYZER v1.0                                      ║
║        Intelligent Strike Selection + Greeks Analysis + Liquidity Scoring            ║
║══════════════════════════════════════════════════════════════════════════════════════║
║                                                                                      ║
║  PURPOSE:                                                                            ║
║  ─────────                                                                           ║
║  Analyze option chains to select the OPTIMAL strike price based on:                  ║
║  • Delta (probability of profit)                                                     ║
║  • Gamma (momentum sensitivity)                                                      ║
║  • Theta decay (time cost)                                                           ║
║  • IV percentile (volatility edge)                                                   ║
║  • Liquidity (bid-ask spread, volume)                                                ║
║  • Capital efficiency (premium vs lot size)                                          ║
║                                                                                      ║
║  STRATEGY FOR MOMENTUM TRADING:                                                      ║
║  ─────────────────────────────────                                                    ║
║  • Prefer slightly ITM/ATM for high delta (captures momentum quickly)                ║
║  • High gamma preferred for explosive moves                                          ║
║  • Accept theta decay for 1-2 day holds with momentum                                ║
║  • Avoid strikes with poor liquidity (wide spreads)                                  ║
║  • Balance premium cost with capital availability                                     ║
║                                                                                      ║
╚══════════════════════════════════════════════════════════════════════════════════════╝
"""

import asyncio
import aiohttp
import logging
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum
import math

logger = logging.getLogger(__name__ + '.options_chain_analyzer')


class StrikeType(Enum):
    """Strike position relative to spot"""
    DEEP_ITM = "deep_itm"      # >5% ITM
    ITM = "itm"                 # 2-5% ITM
    SLIGHT_ITM = "slight_itm"  # 0-2% ITM
    ATM = "atm"                 # At the money
    SLIGHT_OTM = "slight_otm"  # 0-2% OTM
    OTM = "otm"                 # 2-5% OTM
    DEEP_OTM = "deep_otm"      # >5% OTM


class LiquidityGrade(Enum):
    """Liquidity grading for options"""
    A_PLUS = "A+"     # <0.5% spread, 10000+ OI
    A = "A"           # <1% spread, 5000+ OI
    B = "B"           # <2% spread, 1000+ OI
    C = "C"           # <3% spread, 100+ OI
    D = "D"           # >3% spread or <100 OI
    ILLIQUID = "ILLIQUID"  # Avoid


@dataclass
class OptionStrike:
    """Single option strike with Greeks and scores"""
    symbol: str
    expiry: str
    strike: float
    option_type: str  # CE or PE
    spot_price: float
    
    # Prices
    ltp: float = 0.0
    bid: float = 0.0
    ask: float = 0.0
    
    # Volume & OI
    volume: int = 0
    open_interest: int = 0
    change_in_oi: int = 0
    
    # Greeks
    delta: float = 0.0
    gamma: float = 0.0
    theta: float = 0.0
    vega: float = 0.0
    iv: float = 0.0
    
    # Calculated scores
    moneyness_pct: float = 0.0
    strike_type: StrikeType = StrikeType.ATM
    liquidity_grade: LiquidityGrade = LiquidityGrade.C
    
    # Scoring
    momentum_score: float = 0.0    # How well suited for momentum trades
    capital_score: float = 0.0     # Capital efficiency
    liquidity_score: float = 0.0   # Liquidity quality
    overall_score: float = 0.0     # Combined score
    
    # Lot info
    lot_size: int = 0
    premium_per_lot: float = 0.0
    
    @property
    def spread(self) -> float:
        """Bid-ask spread"""
        if self.ask > 0 and self.bid > 0:
            return self.ask - self.bid
        return float('inf')
    
    @property
    def spread_pct(self) -> float:
        """Percentage spread"""
        mid = (self.ask + self.bid) / 2
        if mid > 0:
            return (self.spread / mid) * 100
        return 100
    
    @property
    def volume_oi_ratio(self) -> float:
        """Volume to OI ratio - indicates activity"""
        if self.open_interest > 0:
            return self.volume / self.open_interest
        return 0
    
    def __post_init__(self):
        if self.lot_size > 0 and self.ltp > 0:
            self.premium_per_lot = self.ltp * self.lot_size


@dataclass
class StrikeRecommendation:
    """Recommended strike with rationale"""
    symbol: str
    direction: str  # CE or PE
    expiry: str
    
    # Recommended strike
    primary_strike: OptionStrike
    
    # Alternatives (for user choice)
    aggressive_strike: Optional[OptionStrike] = None   # Higher gamma, lower capital
    conservative_strike: Optional[OptionStrike] = None # Higher delta, higher capital
    
    # Capital analysis
    min_capital_required: float = 0.0  # 1 lot
    optimal_lots: int = 0
    capital_for_optimal: float = 0.0
    
    # Rationale
    selection_reason: str = ""
    risk_notes: List[str] = field(default_factory=list)
    
    @property
    def capital_efficiency(self) -> float:
        """Returns expected return per rupee invested"""
        if self.primary_strike.premium_per_lot > 0:
            # Estimate based on delta and typical momentum move
            expected_move = self.primary_strike.delta * 0.02 * self.primary_strike.spot_price
            return expected_move / self.primary_strike.premium_per_lot
        return 0


@dataclass
class FullChainAnalysis:
    """Complete option chain analysis result"""
    symbol: str
    spot_price: float
    expiry: str
    analysis_time: datetime
    
    # All strikes
    ce_strikes: List[OptionStrike] = field(default_factory=list)
    pe_strikes: List[OptionStrike] = field(default_factory=list)
    
    # ATM info
    atm_strike: float = 0.0
    atm_ce_premium: float = 0.0
    atm_pe_premium: float = 0.0
    
    # Chain metrics
    pcr: float = 0.0  # Put-Call ratio
    max_pain: float = 0.0
    iv_skew: float = 0.0  # Call IV - Put IV at ATM
    
    # Recommendations for each direction
    ce_recommendation: Optional[StrikeRecommendation] = None
    pe_recommendation: Optional[StrikeRecommendation] = None


class OptionsChainAnalyzer:
    """
    Advanced Options Chain Analyzer
    
    Fetches option chains and provides intelligent strike selection
    based on Greeks, liquidity, and capital efficiency for momentum trading.
    """
    
    def __init__(self, dhan_connector=None, backend_url: str = "http://localhost:8000"):
        self.dhan_connector = dhan_connector
        self.backend_url = backend_url
        self.session = None
        
        # F&O lot sizes cache
        self.lot_sizes = {
            "HDFCBANK": 550, "ICICIBANK": 700, "RELIANCE": 250,
            "TATAMOTORS": 1350, "BAJFINANCE": 125, "INFY": 400,
            "TCS": 175, "SBIN": 1500, "AXISBANK": 1200,
            "MARUTI": 100, "SUNPHARMA": 350, "LT": 300,
            "ADANIENT": 400, "TRENT": 125, "TITAN": 250,
            "WIPRO": 1500, "TECHM": 600, "HCLTECH": 350,
            "M&M": 350, "BHARTIARTL": 475, "ITC": 1600,
            "NTPC": 2100, "POWERGRID": 2700, "COALINDIA": 2100,
            "ONGC": 3850, "TATASTEEL": 5500, "HINDALCO": 1400,
            "JSWSTEEL": 1350, "VEDL": 2300, "DLF": 825,
            "ADANIPORTS": 625, "GRASIM": 475, "ULTRACEMCO": 100,
            "DRREDDY": 125, "CIPLA": 650, "DIVISLAB": 175,
            "KOTAKBANK": 400, "INDUSINDBK": 500, "ASIANPAINT": 300,
            "HINDUNILVR": 300, "NESTLEIND": 25, "BRITANNIA": 150,
            "EICHERMOT": 175, "HEROMOTOCO": 150, "BAJAJ-AUTO": 125,
            "PNB": 8000, "RBLBANK": 4500, "AUBANK": 1000,
        }
        
        # Configuration
        self.preferred_expiry = "weekly"  # weekly or monthly
        self.max_spread_pct = 2.0  # Max acceptable spread
        self.min_oi = 500  # Minimum OI required
        
        logger.info("📊 Options Chain Analyzer initialized")
    
    async def initialize(self) -> bool:
        """Initialize the analyzer"""
        try:
            self.session = aiohttp.ClientSession()
            logger.info("✅ Options Chain Analyzer ready")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize: {e}")
            return False
    
    async def close(self):
        """Close the session"""
        if self.session and not self.session.closed:
            await self.session.close()
    
    def get_lot_size(self, symbol: str) -> int:
        """Get lot size for symbol"""
        return self.lot_sizes.get(symbol, 1)
    
    def get_next_expiry(self, expiry_type: str = "weekly") -> str:
        """Get next expiry date"""
        today = datetime.now()
        
        if expiry_type == "weekly":
            # Thursday is expiry day
            days_ahead = (3 - today.weekday()) % 7
            if days_ahead == 0 and today.hour >= 15:
                days_ahead = 7
            elif days_ahead == 0:
                pass  # Today is expiry
            expiry_date = today + timedelta(days=days_ahead)
        else:
            # Monthly - last Thursday
            import calendar
            year = today.year
            month = today.month if today.day < 25 else (today.month % 12) + 1
            if month == 1 and today.month == 12:
                year += 1
            
            last_day = calendar.monthrange(year, month)[1]
            last_thursday = last_day
            while datetime(year, month, last_thursday).weekday() != 3:
                last_thursday -= 1
            expiry_date = datetime(year, month, last_thursday)
        
        return expiry_date.strftime("%Y-%m-%d")
    
    async def get_option_chain(self, symbol: str, expiry: str = None) -> List[Dict]:
        """
        Fetch option chain from backend/Dhan
        """
        if expiry is None:
            expiry = self.get_next_expiry(self.preferred_expiry)
        
        try:
            # Try backend first
            async with self.session.get(
                f"{self.backend_url}/api/options/chain/{symbol}",
                params={"expiry": expiry}
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data.get("chain", [])
            
            # Fallback to Dhan connector
            if self.dhan_connector:
                return await self.dhan_connector.get_option_chain(symbol, expiry)
            
            # Generate simulated chain for testing
            return self._generate_simulated_chain(symbol, expiry)
            
        except Exception as e:
            logger.error(f"Error fetching option chain for {symbol}: {e}")
            return self._generate_simulated_chain(symbol, expiry)
    
    def _generate_simulated_chain(self, symbol: str, expiry: str) -> List[Dict]:
        """Generate simulated option chain for testing"""
        import random
        
        # Simulate spot price
        base_prices = {
            "HDFCBANK": 1650, "ICICIBANK": 1250, "RELIANCE": 2900,
            "TATAMOTORS": 950, "BAJFINANCE": 7500, "INFY": 1850,
            "TCS": 4200, "SBIN": 820, "AXISBANK": 1150,
            "TRENT": 6800, "TITAN": 3500, "ADANIENT": 2800,
        }
        spot = base_prices.get(symbol, random.uniform(500, 3000))
        
        # ATM strike
        strike_gap = 50 if spot > 1000 else 25
        atm = round(spot / strike_gap) * strike_gap
        
        chain = []
        for i in range(-10, 11):
            strike = atm + (i * strike_gap)
            
            # CE pricing
            ce_itm = max(0, spot - strike)
            ce_extrinsic = random.uniform(10, 50) * math.exp(-abs(i) * 0.2)
            ce_price = ce_itm + ce_extrinsic
            
            chain.append({
                "strike": strike,
                "option_type": "CE",
                "ltp": round(ce_price, 2),
                "bid": round(ce_price * 0.98, 2),
                "ask": round(ce_price * 1.02, 2),
                "volume": random.randint(100, 50000),
                "open_interest": random.randint(1000, 500000),
                "iv": random.uniform(15, 45),
                "delta": min(0.99, max(0.01, 0.5 + (spot - strike) / spot)),
                "gamma": random.uniform(0.001, 0.02),
                "theta": random.uniform(-3, -0.1),
                "vega": random.uniform(0.5, 3),
            })
            
            # PE pricing
            pe_itm = max(0, strike - spot)
            pe_extrinsic = random.uniform(10, 50) * math.exp(-abs(i) * 0.2)
            pe_price = pe_itm + pe_extrinsic
            
            chain.append({
                "strike": strike,
                "option_type": "PE",
                "ltp": round(pe_price, 2),
                "bid": round(pe_price * 0.98, 2),
                "ask": round(pe_price * 1.02, 2),
                "volume": random.randint(100, 50000),
                "open_interest": random.randint(1000, 500000),
                "iv": random.uniform(15, 45),
                "delta": -min(0.99, max(0.01, 0.5 + (strike - spot) / spot)),
                "gamma": random.uniform(0.001, 0.02),
                "theta": random.uniform(-3, -0.1),
                "vega": random.uniform(0.5, 3),
            })
        
        return chain
    
    def _classify_strike(self, strike: float, spot: float, option_type: str) -> Tuple[float, StrikeType]:
        """Classify strike as ITM/ATM/OTM"""
        if option_type == "CE":
            moneyness = ((spot - strike) / spot) * 100
        else:
            moneyness = ((strike - spot) / spot) * 100
        
        if moneyness > 5:
            return moneyness, StrikeType.DEEP_ITM
        elif moneyness > 2:
            return moneyness, StrikeType.ITM
        elif moneyness > 0.5:
            return moneyness, StrikeType.SLIGHT_ITM
        elif moneyness > -0.5:
            return moneyness, StrikeType.ATM
        elif moneyness > -2:
            return moneyness, StrikeType.SLIGHT_OTM
        elif moneyness > -5:
            return moneyness, StrikeType.OTM
        else:
            return moneyness, StrikeType.DEEP_OTM
    
    def _grade_liquidity(self, strike: OptionStrike) -> LiquidityGrade:
        """Grade liquidity of a strike"""
        spread_pct = strike.spread_pct
        oi = strike.open_interest
        
        if spread_pct < 0.5 and oi >= 10000:
            return LiquidityGrade.A_PLUS
        elif spread_pct < 1.0 and oi >= 5000:
            return LiquidityGrade.A
        elif spread_pct < 2.0 and oi >= 1000:
            return LiquidityGrade.B
        elif spread_pct < 3.0 and oi >= 100:
            return LiquidityGrade.C
        elif oi < 100:
            return LiquidityGrade.ILLIQUID
        else:
            return LiquidityGrade.D
    
    def _calculate_momentum_score(self, strike: OptionStrike) -> float:
        """
        Calculate momentum trading suitability score (0-100)
        
        For momentum trading we prefer:
        - High delta (0.4-0.7 range) - captures price movement
        - High gamma - amplifies gains on explosive moves
        - Acceptable theta - not too expensive for short holds
        - Good liquidity - easy entry/exit
        """
        score = 0.0
        
        # Delta scoring (max 40 points)
        # Prefer 0.4-0.7 delta for momentum
        delta = abs(strike.delta)
        if 0.4 <= delta <= 0.7:
            score += 40  # Perfect range
        elif 0.3 <= delta < 0.4:
            score += 30
        elif 0.7 < delta <= 0.8:
            score += 30
        elif delta < 0.3:
            score += 15  # Too low, won't capture momentum
        else:
            score += 25  # Too high, expensive
        
        # Gamma scoring (max 25 points)
        # Higher gamma = more explosive potential
        if strike.gamma >= 0.01:
            score += 25
        elif strike.gamma >= 0.005:
            score += 20
        elif strike.gamma >= 0.002:
            score += 15
        else:
            score += 10
        
        # Theta scoring (max 15 points)
        # Less negative theta is better
        theta = abs(strike.theta)
        if theta <= 0.5:
            score += 15
        elif theta <= 1.0:
            score += 12
        elif theta <= 2.0:
            score += 8
        else:
            score += 5  # High decay cost
        
        # Liquidity scoring (max 20 points)
        if strike.liquidity_grade == LiquidityGrade.A_PLUS:
            score += 20
        elif strike.liquidity_grade == LiquidityGrade.A:
            score += 18
        elif strike.liquidity_grade == LiquidityGrade.B:
            score += 15
        elif strike.liquidity_grade == LiquidityGrade.C:
            score += 10
        elif strike.liquidity_grade == LiquidityGrade.D:
            score += 5
        else:
            score += 0  # Illiquid, avoid
        
        return score
    
    def _calculate_capital_score(
        self, 
        strike: OptionStrike, 
        available_capital: float
    ) -> float:
        """
        Calculate capital efficiency score (0-100)
        
        Considers:
        - How many lots can be bought
        - Premium cost relative to expected gain
        - Capital utilization
        """
        if strike.premium_per_lot <= 0:
            return 0
        
        # Lots affordable
        lots_affordable = available_capital / strike.premium_per_lot
        
        if lots_affordable < 1:
            return 0  # Can't even buy 1 lot
        
        score = 0.0
        
        # Lots scoring (max 40 points)
        # More lots = more profit potential
        if lots_affordable >= 10:
            score += 40
        elif lots_affordable >= 5:
            score += 35
        elif lots_affordable >= 3:
            score += 30
        elif lots_affordable >= 2:
            score += 25
        else:
            score += 15  # Only 1 lot
        
        # Capital efficiency (max 30 points)
        # Lower premium with good delta is efficient
        efficiency = abs(strike.delta) / (strike.premium_per_lot / 10000)
        if efficiency >= 1.0:
            score += 30
        elif efficiency >= 0.5:
            score += 25
        elif efficiency >= 0.3:
            score += 20
        else:
            score += 15
        
        # Premium affordability (max 30 points)
        # Premium should be reasonable relative to capital
        premium_ratio = strike.premium_per_lot / available_capital
        if premium_ratio <= 0.05:  # <5% per lot
            score += 30
        elif premium_ratio <= 0.10:
            score += 25
        elif premium_ratio <= 0.20:
            score += 20
        elif premium_ratio <= 0.50:
            score += 15
        else:
            score += 10  # Expensive
        
        return score
    
    async def analyze_chain(
        self, 
        symbol: str, 
        spot_price: float = None,
        available_capital: float = 100000,
        expiry: str = None
    ) -> FullChainAnalysis:
        """
        Complete option chain analysis
        
        Returns:
            FullChainAnalysis with recommendations for both CE and PE
        """
        if expiry is None:
            expiry = self.get_next_expiry(self.preferred_expiry)
        
        lot_size = self.get_lot_size(symbol)
        
        # Fetch chain
        chain_data = await self.get_option_chain(symbol, expiry)
        
        if not chain_data:
            logger.warning(f"No option chain data for {symbol}")
            return None
        
        # Infer spot from ATM options if not provided
        if spot_price is None:
            atm_strikes = []
            for opt in chain_data:
                if opt.get("option_type") == "CE":
                    atm_strikes.append(opt["strike"])
            if atm_strikes:
                spot_price = sum(atm_strikes) / len(atm_strikes)
            else:
                spot_price = chain_data[0].get("strike", 0)
        
        # Process chain
        ce_strikes: List[OptionStrike] = []
        pe_strikes: List[OptionStrike] = []
        
        for opt in chain_data:
            strike_price = opt.get("strike", 0)
            opt_type = opt.get("option_type", "")
            
            moneyness, strike_type = self._classify_strike(
                strike_price, spot_price, opt_type
            )
            
            option = OptionStrike(
                symbol=symbol,
                expiry=expiry,
                strike=strike_price,
                option_type=opt_type,
                spot_price=spot_price,
                ltp=opt.get("ltp", 0),
                bid=opt.get("bid", 0),
                ask=opt.get("ask", 0),
                volume=opt.get("volume", 0),
                open_interest=opt.get("open_interest", 0),
                change_in_oi=opt.get("change_oi", 0),
                delta=opt.get("delta", 0),
                gamma=opt.get("gamma", 0),
                theta=opt.get("theta", 0),
                vega=opt.get("vega", 0),
                iv=opt.get("iv", 0),
                moneyness_pct=moneyness,
                strike_type=strike_type,
                lot_size=lot_size,
                premium_per_lot=opt.get("ltp", 0) * lot_size
            )
            
            # Calculate scores
            option.liquidity_grade = self._grade_liquidity(option)
            option.liquidity_score = self._calculate_momentum_score(option) * 0.2
            option.momentum_score = self._calculate_momentum_score(option)
            option.capital_score = self._calculate_capital_score(option, available_capital)
            
            # Overall score (weighted)
            option.overall_score = (
                option.momentum_score * 0.5 +
                option.capital_score * 0.3 +
                option.liquidity_score * 0.2
            )
            
            if opt_type == "CE":
                ce_strikes.append(option)
            else:
                pe_strikes.append(option)
        
        # Sort by strike
        ce_strikes.sort(key=lambda x: x.strike)
        pe_strikes.sort(key=lambda x: x.strike)
        
        # Find ATM
        strike_gap = 50 if spot_price > 1000 else 25
        atm_strike = round(spot_price / strike_gap) * strike_gap
        
        # Get ATM premiums
        atm_ce = next((s for s in ce_strikes if s.strike == atm_strike), None)
        atm_pe = next((s for s in pe_strikes if s.strike == atm_strike), None)
        
        # Calculate PCR
        total_ce_oi = sum(s.open_interest for s in ce_strikes)
        total_pe_oi = sum(s.open_interest for s in pe_strikes)
        pcr = total_pe_oi / max(1, total_ce_oi)
        
        # Create analysis
        analysis = FullChainAnalysis(
            symbol=symbol,
            spot_price=spot_price,
            expiry=expiry,
            analysis_time=datetime.now(),
            ce_strikes=ce_strikes,
            pe_strikes=pe_strikes,
            atm_strike=atm_strike,
            atm_ce_premium=atm_ce.ltp if atm_ce else 0,
            atm_pe_premium=atm_pe.ltp if atm_pe else 0,
            pcr=pcr,
            iv_skew=(atm_ce.iv if atm_ce else 0) - (atm_pe.iv if atm_pe else 0)
        )
        
        # Get recommendations
        analysis.ce_recommendation = self._get_strike_recommendation(
            ce_strikes, "CE", available_capital
        )
        analysis.pe_recommendation = self._get_strike_recommendation(
            pe_strikes, "PE", available_capital
        )
        
        return analysis
    
    def _get_strike_recommendation(
        self, 
        strikes: List[OptionStrike], 
        direction: str,
        available_capital: float
    ) -> Optional[StrikeRecommendation]:
        """
        Get the best strike recommendation for momentum trading
        """
        if not strikes:
            return None
        
        # Filter out illiquid and unaffordable strikes
        valid_strikes = [
            s for s in strikes 
            if s.liquidity_grade != LiquidityGrade.ILLIQUID
            and s.premium_per_lot > 0
            and s.premium_per_lot <= available_capital
        ]
        
        if not valid_strikes:
            return None
        
        # Sort by overall score
        sorted_strikes = sorted(valid_strikes, key=lambda x: x.overall_score, reverse=True)
        
        # Primary recommendation - highest score
        primary = sorted_strikes[0]
        
        # Find aggressive alternative (higher gamma, lower premium)
        aggressive = None
        for s in sorted_strikes:
            if s.gamma > primary.gamma and s.premium_per_lot < primary.premium_per_lot:
                aggressive = s
                break
        
        # Find conservative alternative (higher delta, safer)
        conservative = None
        for s in sorted_strikes:
            if abs(s.delta) > abs(primary.delta):
                conservative = s
                break
        
        # Calculate optimal lots
        lots_affordable = int(available_capital / primary.premium_per_lot)
        optimal_lots = min(lots_affordable, 5)  # Cap at 5 for risk management
        
        # Build selection reason
        reasons = []
        reasons.append(f"Strike {primary.strike} selected for {direction}")
        reasons.append(f"Delta: {primary.delta:.2f}, Gamma: {primary.gamma:.4f}")
        reasons.append(f"Premium/Lot: ₹{primary.premium_per_lot:,.0f}")
        reasons.append(f"Liquidity Grade: {primary.liquidity_grade.value}")
        reasons.append(f"Momentum Score: {primary.momentum_score:.1f}/100")
        
        # Risk notes
        risk_notes = []
        if primary.strike_type in [StrikeType.DEEP_OTM, StrikeType.DEEP_ITM]:
            risk_notes.append("Strike is far from ATM - higher risk")
        if primary.liquidity_grade in [LiquidityGrade.C, LiquidityGrade.D]:
            risk_notes.append("Moderate liquidity - may face slippage")
        if abs(primary.theta) > 2:
            risk_notes.append("High theta decay - time sensitive")
        
        return StrikeRecommendation(
            symbol=primary.symbol,
            direction=direction,
            expiry=primary.expiry,
            primary_strike=primary,
            aggressive_strike=aggressive,
            conservative_strike=conservative,
            min_capital_required=primary.premium_per_lot,
            optimal_lots=optimal_lots,
            capital_for_optimal=optimal_lots * primary.premium_per_lot,
            selection_reason=" | ".join(reasons),
            risk_notes=risk_notes
        )
    
    async def get_best_strike_for_signal(
        self,
        symbol: str,
        direction: str,  # "CE" or "PE"
        spot_price: float,
        available_capital: float,
        momentum_strength: float = 0.7,  # 0-1
        prefer_aggressive: bool = False
    ) -> Optional[OptionStrike]:
        """
        Quick method to get the best strike for a given signal
        
        Args:
            symbol: Stock symbol
            direction: CE for bullish, PE for bearish
            spot_price: Current spot price
            available_capital: Capital available for this trade
            momentum_strength: Expected momentum strength (0-1)
            prefer_aggressive: If True, prefer higher gamma strikes
        
        Returns:
            Best OptionStrike or None
        """
        analysis = await self.analyze_chain(
            symbol=symbol,
            spot_price=spot_price,
            available_capital=available_capital
        )
        
        if not analysis:
            return None
        
        if direction == "CE":
            rec = analysis.ce_recommendation
        else:
            rec = analysis.pe_recommendation
        
        if not rec:
            return None
        
        # Choose based on preference
        if prefer_aggressive and rec.aggressive_strike:
            return rec.aggressive_strike
        elif not prefer_aggressive and rec.conservative_strike and momentum_strength < 0.5:
            return rec.conservative_strike
        else:
            return rec.primary_strike
    
    def format_recommendation(self, rec: StrikeRecommendation) -> str:
        """Format recommendation for display"""
        if not rec:
            return "No recommendation available"
        
        s = rec.primary_strike
        output = []
        output.append(f"\n{'='*60}")
        output.append(f"  🎯 STRIKE RECOMMENDATION: {rec.symbol} {rec.direction}")
        output.append(f"{'='*60}")
        output.append(f"  📊 Primary Strike: {s.strike:.0f}")
        output.append(f"  💰 Premium: ₹{s.ltp:.2f} (₹{s.premium_per_lot:,.0f}/lot)")
        output.append(f"  📈 Greeks: Δ={s.delta:.2f} Γ={s.gamma:.4f} θ={s.theta:.2f}")
        output.append(f"  📊 IV: {s.iv:.1f}% | OI: {s.open_interest:,}")
        output.append(f"  💧 Liquidity: {s.liquidity_grade.value} | Spread: {s.spread_pct:.2f}%")
        output.append(f"  🎯 Scores: Momentum={s.momentum_score:.0f} Capital={s.capital_score:.0f}")
        output.append(f"\n  📋 Capital Analysis:")
        output.append(f"     Min Required: ₹{rec.min_capital_required:,.0f}")
        output.append(f"     Optimal Lots: {rec.optimal_lots}")
        output.append(f"     Capital Needed: ₹{rec.capital_for_optimal:,.0f}")
        
        if rec.aggressive_strike:
            a = rec.aggressive_strike
            output.append(f"\n  ⚡ Aggressive Alt: {a.strike:.0f} @ ₹{a.ltp:.2f} (Δ={a.delta:.2f})")
        
        if rec.conservative_strike:
            c = rec.conservative_strike
            output.append(f"  🛡️ Conservative Alt: {c.strike:.0f} @ ₹{c.ltp:.2f} (Δ={c.delta:.2f})")
        
        if rec.risk_notes:
            output.append(f"\n  ⚠️ Risk Notes:")
            for note in rec.risk_notes:
                output.append(f"     • {note}")
        
        output.append(f"{'='*60}\n")
        
        return "\n".join(output)


# ============================================================================
# MAIN TEST
# ============================================================================

async def main():
    """Test the options chain analyzer"""
    analyzer = OptionsChainAnalyzer()
    await analyzer.initialize()
    
    # Test symbols
    test_symbols = ["TATAMOTORS", "RELIANCE", "HDFCBANK", "TRENT"]
    
    for symbol in test_symbols:
        print(f"\n{'='*70}")
        print(f"  Analyzing {symbol} Option Chain")
        print(f"{'='*70}")
        
        analysis = await analyzer.analyze_chain(
            symbol=symbol,
            available_capital=100000
        )
        
        if analysis:
            print(f"\n  Spot: ₹{analysis.spot_price:,.2f}")
            print(f"  ATM Strike: {analysis.atm_strike}")
            print(f"  ATM CE Premium: ₹{analysis.atm_ce_premium:.2f}")
            print(f"  ATM PE Premium: ₹{analysis.atm_pe_premium:.2f}")
            print(f"  PCR: {analysis.pcr:.2f}")
            
            print(analyzer.format_recommendation(analysis.ce_recommendation))
            print(analyzer.format_recommendation(analysis.pe_recommendation))
    
    await analyzer.close()


if __name__ == "__main__":
    asyncio.run(main())
