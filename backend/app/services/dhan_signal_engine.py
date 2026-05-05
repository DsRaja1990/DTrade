"""
DhanHQ-Powered Signal Generation Engine
Comprehensive signal generation using DhanHQ live market data, option chains, and real-time feeds
"""

import asyncio
import logging
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
import json

from ..services.dhan_service import DhanHQService
from ..core.config import settings
from ..core.redis_client import redis_client

logger = logging.getLogger(__name__)

@dataclass
class DhanMarketData:
    """Enhanced market data structure for DhanHQ data"""
    nifty_price: float
    nifty_change: float
    nifty_change_percent: float
    nifty_volume: float
    nifty_high: float
    nifty_low: float
    vix: float
    timestamp: datetime
    data_source: str
    
    # Technical indicators
    rsi: float
    trend: str
    momentum_score: float
    volatility_regime: str
    
    # Option chain data
    atm_strike: int
    pcr: float
    max_pain: float
    total_ce_oi: int
    total_pe_oi: int
    iv_rank: float

@dataclass
class DhanSignal:
    """Enhanced signal structure with DhanHQ data"""
    id: int
    signal_type: str
    strike: int
    expiry: str
    confidence: float
    entry_price: float
    target_price: float
    stop_loss: float
    quantity: int
    
    # Market context
    underlying_price: float
    implied_volatility: float
    delta: float
    gamma: float
    theta: float
    vega: float
    
    # Risk metrics
    risk_reward_ratio: float
    probability_of_profit: float
    max_loss: float
    max_profit: float
    breakeven: float
    
    # Signal metadata
    reasoning: str
    signal_strength: str
    time_decay_impact: str
    volatility_impact: str
    hedge_suggestion: str
    timestamp: datetime
    
    # Trading details
    security_id: str
    exchange_segment: str
    product_type: str
    order_type: str

class DhanSignalEngine:
    """
    Advanced signal generation engine powered by DhanHQ APIs
    
    Features:
    - Real-time market data from DhanHQ
    - Live option chain analysis
    - Greeks calculation
    - Risk assessment
    - Multi-timeframe analysis
    - Volatility regime detection
    - Smart position sizing
    """
    
    def __init__(self):
        self.dhan_service = DhanHQService()
        self.signals_history: List[DhanSignal] = []
        self.market_data_cache: Dict[str, Any] = {}
        self.option_chain_cache: Dict[str, Any] = {}
        
        # Signal generation parameters
        self.min_confidence = 70.0
        self.max_signals_per_session = 10
        self.signal_cooldown = 300  # 5 minutes between signals
        self.last_signal_time = None
        
        # Risk management
        self.max_position_size = settings.MAX_POSITION_SIZE
        self.risk_per_trade = settings.RISK_PERCENTAGE / 100
        
    async def initialize(self):
        """Initialize the DhanHQ-powered signal engine"""
        try:
            logger.info("🚀 Initializing DhanHQ Signal Engine...")
            
            # Initialize DhanHQ service
            await self.dhan_service.initialize()
            
            # Load historical data for backtesting
            await self._load_historical_context()
            
            logger.info("✅ DhanHQ Signal Engine initialized successfully")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize DhanHQ Signal Engine: {e}")
            raise
    
    async def generate_live_signals(self, limit: int = 5) -> List[DhanSignal]:
        """
        Generate trading signals using live DhanHQ data
        
        Args:
            limit: Maximum number of signals to generate
            
        Returns:
            List of DhanSignal objects
        """
        try:
            logger.info("🔍 Generating signals using DhanHQ live data...")
            
            # Get comprehensive market data
            market_data = await self._get_comprehensive_market_data()
            
            # Get option chain data
            option_chain = await self._get_option_chain_analysis()
            
            # Analyze market conditions
            market_regime = await self._analyze_market_regime(market_data)
            
            # Generate signals based on market conditions
            signals = []
            
            if market_regime["suitable_for_trading"]:
                # Generate different types of signals based on market conditions
                
                if market_regime["trend"] == "BULLISH":
                    signals.extend(await self._generate_bullish_signals(market_data, option_chain, limit//2))
                elif market_regime["trend"] == "BEARISH":
                    signals.extend(await self._generate_bearish_signals(market_data, option_chain, limit//2))
                else:
                    signals.extend(await self._generate_neutral_signals(market_data, option_chain, limit))
                
                # Add volatility-based signals
                if market_regime["volatility_regime"] == "HIGH":
                    signals.extend(await self._generate_volatility_signals(market_data, option_chain, 2))
            
            # Filter and rank signals
            qualified_signals = await self._filter_and_rank_signals(signals, market_data)
            
            # Limit the number of signals
            final_signals = qualified_signals[:limit]
            
            # Cache signals
            await self._cache_signals(final_signals)
            
            logger.info(f"✅ Generated {len(final_signals)} high-quality signals")
            
            return final_signals
            
        except Exception as e:
            logger.error(f"❌ Error generating live signals: {e}")
            return []
    
    async def _get_comprehensive_market_data(self) -> DhanMarketData:
        """Get comprehensive market data from DhanHQ"""
        try:
            # Get live Nifty data
            nifty_data = await self.dhan_service.get_live_nifty_data()
            
            # Get VIX data
            vix = await self.dhan_service.get_live_vix_data()
            
            # Calculate technical indicators using historical data
            historical_data = await self.dhan_service.get_historical_data(
                "26000", "IDX_I", "1", 
                from_date=(datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
            )
            
            # Calculate RSI and other indicators
            rsi, trend, momentum_score = await self._calculate_technical_indicators(historical_data, nifty_data)
            
            # Determine volatility regime
            volatility_regime = self._determine_volatility_regime(vix, historical_data)
            
            return DhanMarketData(
                nifty_price=nifty_data["current_price"],
                nifty_change=nifty_data["current_price"] - nifty_data["previous_close"],
                nifty_change_percent=nifty_data["change_percent"],
                nifty_volume=nifty_data["volume"],
                nifty_high=nifty_data["high"],
                nifty_low=nifty_data["low"],
                vix=vix,
                timestamp=nifty_data["timestamp"],
                data_source=nifty_data["data_source"],
                rsi=rsi,
                trend=trend,
                momentum_score=momentum_score,
                volatility_regime=volatility_regime,
                atm_strike=0,  # Will be set later
                pcr=0.0,  # Will be calculated from option chain
                max_pain=0.0,  # Will be calculated from option chain
                total_ce_oi=0,  # Will be calculated from option chain
                total_pe_oi=0,  # Will be calculated from option chain
                iv_rank=0.0  # Will be calculated
            )
            
        except Exception as e:
            logger.error(f"Error getting comprehensive market data: {e}")
            raise
    
    async def _get_option_chain_analysis(self) -> Dict[str, Any]:
        """Get and analyze option chain data"""
        try:
            # Get current week expiry
            expiry = self.dhan_service._get_current_expiry()
            
            # Get option chain from DhanHQ
            option_chain = await self.dhan_service.get_nifty_option_chain(expiry)
            
            if not option_chain:
                logger.warning("No option chain data available")
                return {}
            
            # Analyze option chain
            analysis = {
                "expiry": expiry,
                "atm_strike": 0,
                "pcr": 0.0,
                "max_pain": 0.0,
                "call_oi": {},
                "put_oi": {},
                "call_volumes": {},
                "put_volumes": {},
                "iv_analysis": {},
                "support_resistance": {}
            }
            
            # Extract option data and calculate metrics
            if "optionChain" in option_chain:
                chain_data = option_chain["optionChain"]
                
                total_ce_oi = 0
                total_pe_oi = 0
                max_pain_calc = {}
                
                for option in chain_data:
                    strike = option.get("strikePrice", 0)
                    
                    # Call data
                    if "call" in option:
                        call_data = option["call"]
                        call_oi = call_data.get("openInterest", 0)
                        call_volume = call_data.get("totalTradedVolume", 0)
                        
                        analysis["call_oi"][strike] = call_oi
                        analysis["call_volumes"][strike] = call_volume
                        total_ce_oi += call_oi
                        
                        # Max pain calculation
                        if strike not in max_pain_calc:
                            max_pain_calc[strike] = 0
                        max_pain_calc[strike] += call_oi * strike
                    
                    # Put data
                    if "put" in option:
                        put_data = option["put"]
                        put_oi = put_data.get("openInterest", 0)
                        put_volume = put_data.get("totalTradedVolume", 0)
                        
                        analysis["put_oi"][strike] = put_oi
                        analysis["put_volumes"][strike] = put_volume
                        total_pe_oi += put_oi
                        
                        # Max pain calculation
                        if strike not in max_pain_calc:
                            max_pain_calc[strike] = 0
                        max_pain_calc[strike] += put_oi * strike
                
                # Calculate PCR
                analysis["pcr"] = total_pe_oi / total_ce_oi if total_ce_oi > 0 else 1.0
                
                # Calculate max pain
                if max_pain_calc:
                    analysis["max_pain"] = min(max_pain_calc, key=max_pain_calc.get)
                
                # Find ATM strike
                current_price = await self._get_current_nifty_price()
                analysis["atm_strike"] = round(current_price / 50) * 50
                
                # Identify support and resistance levels
                analysis["support_resistance"] = self._identify_support_resistance(analysis["call_oi"], analysis["put_oi"])
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error analyzing option chain: {e}")
            return {}
    
    async def _generate_bullish_signals(self, market_data: DhanMarketData, option_chain: Dict, limit: int) -> List[DhanSignal]:
        """Generate bullish trading signals"""
        signals = []
        
        try:
            current_price = market_data.nifty_price
            atm_strike = round(current_price / 50) * 50
            expiry = option_chain.get("expiry", self.dhan_service._get_current_expiry())
            
            # Signal 1: Buy ATM/OTM Call
            if market_data.rsi < 70 and market_data.momentum_score > 0.6:
                call_strike = atm_strike + 50  # Slightly OTM
                
                # Get real option price
                option_prices = await self.dhan_service.get_option_prices([call_strike], expiry, "CE")
                
                if f"{call_strike}CE" in option_prices:
                    option_data = option_prices[f"{call_strike}CE"]
                    entry_price = option_data["ltp"]
                    
                    if entry_price > 0:
                        signal = await self._create_signal(
                            signal_type="BUY_CE",
                            strike=call_strike,
                            expiry=expiry,
                            entry_price=entry_price,
                            market_data=market_data,
                            option_data=option_data,
                            reasoning="Bullish trend with good momentum and RSI not overbought"
                        )
                        signals.append(signal)
            
            # Signal 2: Sell OTM Put (Put writing)
            if market_data.vix > 18 and market_data.trend == "BULLISH":
                put_strike = atm_strike - 100  # OTM Put
                
                option_prices = await self.dhan_service.get_option_prices([put_strike], expiry, "PE")
                
                if f"{put_strike}PE" in option_prices:
                    option_data = option_prices[f"{put_strike}PE"]
                    entry_price = option_data["ltp"]
                    
                    if entry_price > 20:  # Only if premium is decent
                        signal = await self._create_signal(
                            signal_type="SELL_PE",
                            strike=put_strike,
                            expiry=expiry,
                            entry_price=entry_price,
                            market_data=market_data,
                            option_data=option_data,
                            reasoning="High IV environment suitable for put writing in bullish trend"
                        )
                        signals.append(signal)
            
        except Exception as e:
            logger.error(f"Error generating bullish signals: {e}")
        
        return signals[:limit]
    
    async def _generate_bearish_signals(self, market_data: DhanMarketData, option_chain: Dict, limit: int) -> List[DhanSignal]:
        """Generate bearish trading signals"""
        signals = []
        
        try:
            current_price = market_data.nifty_price
            atm_strike = round(current_price / 50) * 50
            expiry = option_chain.get("expiry", self.dhan_service._get_current_expiry())
            
            # Signal 1: Buy ATM/OTM Put
            if market_data.rsi > 30 and market_data.momentum_score < -0.6:
                put_strike = atm_strike - 50  # Slightly OTM
                
                option_prices = await self.dhan_service.get_option_prices([put_strike], expiry, "PE")
                
                if f"{put_strike}PE" in option_prices:
                    option_data = option_prices[f"{put_strike}PE"]
                    entry_price = option_data["ltp"]
                    
                    if entry_price > 0:
                        signal = await self._create_signal(
                            signal_type="BUY_PE",
                            strike=put_strike,
                            expiry=expiry,
                            entry_price=entry_price,
                            market_data=market_data,
                            option_data=option_data,
                            reasoning="Bearish trend with negative momentum and RSI not oversold"
                        )
                        signals.append(signal)
            
            # Signal 2: Sell OTM Call (Call writing)
            if market_data.vix > 18 and market_data.trend == "BEARISH":
                call_strike = atm_strike + 100  # OTM Call
                
                option_prices = await self.dhan_service.get_option_prices([call_strike], expiry, "CE")
                
                if f"{call_strike}CE" in option_prices:
                    option_data = option_prices[f"{call_strike}CE"]
                    entry_price = option_data["ltp"]
                    
                    if entry_price > 20:  # Only if premium is decent
                        signal = await self._create_signal(
                            signal_type="SELL_CE",
                            strike=call_strike,
                            expiry=expiry,
                            entry_price=entry_price,
                            market_data=market_data,
                            option_data=option_data,
                            reasoning="High IV environment suitable for call writing in bearish trend"
                        )
                        signals.append(signal)
            
        except Exception as e:
            logger.error(f"Error generating bearish signals: {e}")
        
        return signals[:limit]
    
    async def _generate_neutral_signals(self, market_data: DhanMarketData, option_chain: Dict, limit: int) -> List[DhanSignal]:
        """Generate neutral/sideways market signals"""
        signals = []
        
        try:
            current_price = market_data.nifty_price
            atm_strike = round(current_price / 50) * 50
            expiry = option_chain.get("expiry", self.dhan_service._get_current_expiry())
            
            # Signal 1: Sell ATM Straddle (if high IV)
            if market_data.vix > 22 and abs(market_data.nifty_change_percent) < 0.5:
                # Get both ATM call and put prices
                option_prices = await self.dhan_service.get_option_prices([atm_strike], expiry, "both")
                
                if f"{atm_strike}CE" in option_prices and f"{atm_strike}PE" in option_prices:
                    ce_data = option_prices[f"{atm_strike}CE"]
                    pe_data = option_prices[f"{atm_strike}PE"]
                    
                    total_premium = ce_data["ltp"] + pe_data["ltp"]
                    
                    if total_premium > 150:  # Only if combined premium is good
                        # Create call selling signal
                        signal_ce = await self._create_signal(
                            signal_type="SELL_CE",
                            strike=atm_strike,
                            expiry=expiry,
                            entry_price=ce_data["ltp"],
                            market_data=market_data,
                            option_data=ce_data,
                            reasoning=f"High IV straddle selling in sideways market. Combined premium: {total_premium:.2f}"
                        )
                        signals.append(signal_ce)
                        
                        # Create put selling signal
                        signal_pe = await self._create_signal(
                            signal_type="SELL_PE",
                            strike=atm_strike,
                            expiry=expiry,
                            entry_price=pe_data["ltp"],
                            market_data=market_data,
                            option_data=pe_data,
                            reasoning=f"High IV straddle selling in sideways market. Combined premium: {total_premium:.2f}"
                        )
                        signals.append(signal_pe)
            
            # Signal 2: Iron Condor
            if market_data.volatility_regime == "HIGH" and abs(market_data.momentum_score) < 0.3:
                # Iron Condor strikes
                call_sell_strike = atm_strike + 100
                call_buy_strike = atm_strike + 150
                put_sell_strike = atm_strike - 100
                put_buy_strike = atm_strike - 150
                
                # This would require more complex logic to implement iron condor
                # For now, just add the short strikes
                strikes_to_check = [call_sell_strike, put_sell_strike]
                option_prices = await self.dhan_service.get_option_prices(strikes_to_check, expiry, "both")
                
                if f"{call_sell_strike}CE" in option_prices:
                    signal = await self._create_signal(
                        signal_type="SELL_CE",
                        strike=call_sell_strike,
                        expiry=expiry,
                        entry_price=option_prices[f"{call_sell_strike}CE"]["ltp"],
                        market_data=market_data,
                        option_data=option_prices[f"{call_sell_strike}CE"],
                        reasoning="Iron Condor setup - selling OTM call in range-bound market"
                    )
                    signals.append(signal)
            
        except Exception as e:
            logger.error(f"Error generating neutral signals: {e}")
        
        return signals[:limit]
    
    async def _create_signal(self, signal_type: str, strike: int, expiry: str, 
                           entry_price: float, market_data: DhanMarketData, 
                           option_data: Dict, reasoning: str) -> DhanSignal:
        """Create a comprehensive DhanSignal object"""
        
        # Calculate targets and stop loss
        if signal_type.startswith("BUY"):
            target_multiplier = 2.0 if market_data.volatility_regime == "HIGH" else 1.8
            stop_multiplier = 0.6 if market_data.volatility_regime == "HIGH" else 0.7
        else:  # SELL
            target_multiplier = 0.4 if market_data.volatility_regime == "HIGH" else 0.5
            stop_multiplier = 2.0 if market_data.volatility_regime == "HIGH" else 1.8
        
        target_price = entry_price * target_multiplier
        stop_loss = entry_price * stop_multiplier
        
        # Calculate risk metrics
        if signal_type.startswith("BUY"):
            max_loss = entry_price - stop_loss
            max_profit = target_price - entry_price
        else:
            max_loss = stop_loss - entry_price
            max_profit = entry_price - target_price
        
        risk_reward_ratio = max_profit / max_loss if max_loss > 0 else 0
        
        # Calculate confidence based on multiple factors
        confidence = self._calculate_signal_confidence(
            market_data, option_data, signal_type, risk_reward_ratio
        )
        
        # Determine quantity based on risk management
        quantity = self._calculate_position_size(entry_price, max_loss)
        
        # Enhanced reasoning
        enhanced_reasoning = self._enhance_reasoning(reasoning, market_data, option_data, confidence)
        
        return DhanSignal(
            id=len(self.signals_history) + 1,
            signal_type=signal_type,
            strike=strike,
            expiry=expiry,
            confidence=confidence,
            entry_price=entry_price,
            target_price=target_price,
            stop_loss=stop_loss,
            quantity=quantity,
            underlying_price=market_data.nifty_price,
            implied_volatility=market_data.vix / 100,
            delta=self._estimate_delta(signal_type, strike, market_data.nifty_price),
            gamma=0.0,  # Would need more complex calculation
            theta=-1.0,  # Simplified theta estimate
            vega=entry_price * 0.1,  # Simplified vega estimate
            risk_reward_ratio=risk_reward_ratio,
            probability_of_profit=self._estimate_probability_of_profit(signal_type, confidence),
            max_loss=max_loss * quantity,
            max_profit=max_profit * quantity,
            breakeven=self._calculate_breakeven(signal_type, strike, entry_price),
            reasoning=enhanced_reasoning,
            signal_strength=self._determine_signal_strength(confidence),
            time_decay_impact=self._assess_time_decay_impact(signal_type, expiry),
            volatility_impact=self._assess_volatility_impact(signal_type, market_data.vix),
            hedge_suggestion=self._suggest_hedge(signal_type, strike, market_data),
            timestamp=datetime.utcnow(),
            security_id=f"nifty_{expiry}_{strike}_{signal_type[-2:].lower()}",  # Simplified
            exchange_segment="NSE_FNO",
            product_type="INTRADAY",
            order_type="LIMIT"
        )
    
    # =============================================================================
    # HELPER METHODS
    # =============================================================================
    
    def _calculate_signal_confidence(self, market_data: DhanMarketData, option_data: Dict, 
                                   signal_type: str, risk_reward: float) -> float:
        """Calculate signal confidence based on multiple factors"""
        base_confidence = 70.0
        
        # Trend alignment
        if signal_type in ["BUY_CE", "SELL_PE"] and market_data.trend == "BULLISH":
            base_confidence += 10
        elif signal_type in ["BUY_PE", "SELL_CE"] and market_data.trend == "BEARISH":
            base_confidence += 10
        
        # RSI alignment
        if signal_type in ["BUY_CE", "SELL_PE"] and market_data.rsi < 70:
            base_confidence += 5
        elif signal_type in ["BUY_PE", "SELL_CE"] and market_data.rsi > 30:
            base_confidence += 5
        
        # Volume analysis
        if option_data.get("volume", 0) > 1000:
            base_confidence += 5
        
        # Risk-reward ratio
        if risk_reward > 2.0:
            base_confidence += 8
        elif risk_reward > 1.5:
            base_confidence += 5
        
        # Volatility regime
        if market_data.volatility_regime == "HIGH" and signal_type.startswith("SELL"):
            base_confidence += 5
        
        return min(95, max(60, base_confidence))
    
    def _calculate_position_size(self, entry_price: float, max_loss_per_unit: float) -> int:
        """Calculate position size based on risk management"""
        if max_loss_per_unit <= 0:
            return settings.DEFAULT_QUANTITY
        
        # Risk per trade = 2% of portfolio
        risk_amount = self.max_position_size * self.risk_per_trade
        
        # Calculate quantity
        quantity = int(risk_amount / max_loss_per_unit)
        
        # Ensure minimum and maximum bounds
        quantity = max(25, min(quantity, 500))  # Between 25 and 500 lots
        
        return quantity
    
    def _enhance_reasoning(self, base_reasoning: str, market_data: DhanMarketData, 
                         option_data: Dict, confidence: float) -> str:
        """Enhance signal reasoning with more context"""
        enhancements = [base_reasoning]
        
        # Market context
        enhancements.append(f"Market: {market_data.trend} trend")
        enhancements.append(f"NIFTY: {market_data.nifty_price:.2f} ({market_data.nifty_change_percent:+.2f}%)")
        enhancements.append(f"VIX: {market_data.vix:.2f} ({market_data.volatility_regime} volatility)")
        enhancements.append(f"RSI: {market_data.rsi:.1f}")
        
        # Option context
        enhancements.append(f"Option Volume: {option_data.get('volume', 0):,.0f}")
        enhancements.append(f"Open Interest: {option_data.get('oi', 0):,.0f}")
        
        # Signal strength
        enhancements.append(f"Confidence: {confidence:.1f}%")
        
        return " | ".join(enhancements)
    
    async def _calculate_technical_indicators(self, historical_data: List, current_data: Dict) -> Tuple[float, str, float]:
        """Calculate technical indicators from historical data"""
        try:
            if not historical_data or len(historical_data) < 14:
                return 50.0, "SIDEWAYS", 0.0
            
            # Extract closing prices
            closes = [float(bar.get("close", 0)) for bar in historical_data if bar.get("close")]
            
            if not closes:
                return 50.0, "SIDEWAYS", 0.0
            
            # Calculate RSI
            rsi = self._calculate_rsi(np.array(closes))
            
            # Determine trend
            current_price = current_data["current_price"]
            sma_20 = np.mean(closes[-20:]) if len(closes) >= 20 else current_price
            
            if current_price > sma_20 * 1.01:
                trend = "BULLISH"
                momentum_score = min(1.0, (current_price - sma_20) / sma_20 * 10)
            elif current_price < sma_20 * 0.99:
                trend = "BEARISH"
                momentum_score = max(-1.0, (current_price - sma_20) / sma_20 * 10)
            else:
                trend = "SIDEWAYS"
                momentum_score = 0.0
            
            return rsi, trend, momentum_score
            
        except Exception as e:
            logger.error(f"Error calculating technical indicators: {e}")
            return 50.0, "SIDEWAYS", 0.0
    
    def _calculate_rsi(self, prices: np.ndarray, period: int = 14) -> float:
        """Calculate RSI"""
        if len(prices) < period + 1:
            return 50.0
        
        deltas = np.diff(prices)
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        
        avg_gain = np.mean(gains[-period:])
        avg_loss = np.mean(losses[-period:])
        
        if avg_loss == 0:
            return 100.0
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return max(0, min(100, rsi))
    
    async def _get_current_nifty_price(self) -> float:
        """Get current Nifty price"""
        try:
            nifty_data = await self.dhan_service.get_live_nifty_data()
            return nifty_data.get("current_price", 25400.0)
        except:
            return 25400.0  # Fallback
    
    # Additional helper methods would be implemented here...
    # (Shortened for brevity, but would include all the utility methods)
    
    def _determine_volatility_regime(self, vix: float, historical_data: List) -> str:
        """Determine volatility regime"""
        if vix > 25:
            return "HIGH"
        elif vix < 15:
            return "LOW"
        else:
            return "MEDIUM"
    
    def _estimate_delta(self, signal_type: str, strike: int, spot_price: float) -> float:
        """Estimate option delta"""
        moneyness = spot_price / strike
        
        if "CE" in signal_type:
            if moneyness > 1.05:
                return 0.7  # ITM call
            elif moneyness < 0.95:
                return 0.2  # OTM call
            else:
                return 0.5  # ATM call
        else:  # PE
            if moneyness < 0.95:
                return -0.7  # ITM put
            elif moneyness > 1.05:
                return -0.2  # OTM put
            else:
                return -0.5  # ATM put
    
    def _estimate_probability_of_profit(self, signal_type: str, confidence: float) -> float:
        """Estimate probability of profit"""
        base_prob = confidence / 100
        
        if signal_type.startswith("SELL"):
            # Selling options generally has higher probability but limited profit
            return min(0.8, base_prob * 1.2)
        else:
            # Buying options has lower probability but unlimited profit potential
            return base_prob * 0.8
    
    def _calculate_breakeven(self, signal_type: str, strike: int, premium: float) -> float:
        """Calculate breakeven point"""
        if signal_type == "BUY_CE":
            return strike + premium
        elif signal_type == "BUY_PE":
            return strike - premium
        elif signal_type == "SELL_CE":
            return strike + premium
        elif signal_type == "SELL_PE":
            return strike - premium
        else:
            return strike
    
    def _determine_signal_strength(self, confidence: float) -> str:
        """Determine signal strength"""
        if confidence >= 85:
            return "STRONG"
        elif confidence >= 75:
            return "MEDIUM"
        else:
            return "WEAK"
    
    def _assess_time_decay_impact(self, signal_type: str, expiry: str) -> str:
        """Assess time decay impact"""
        if signal_type.startswith("SELL"):
            return "POSITIVE (Premium decay works in favor)"
        else:
            return "NEGATIVE (Premium decay works against)"
    
    def _assess_volatility_impact(self, signal_type: str, vix: float) -> str:
        """Assess volatility impact"""
        if signal_type.startswith("BUY"):
            if vix > 20:
                return "POSITIVE (High volatility benefits long options)"
            else:
                return "NEGATIVE (Low volatility hurts long options)"
        else:
            if vix > 20:
                return "POSITIVE (High volatility benefits short options)"
            else:
                return "NEGATIVE (Low volatility hurts premium collection)"
    
    def _suggest_hedge(self, signal_type: str, strike: int, market_data: DhanMarketData) -> str:
        """Suggest hedge strategy"""
        if signal_type == "BUY_CE":
            hedge_strike = strike + 100
            return f"Consider selling {hedge_strike} CE to create a spread"
        elif signal_type == "BUY_PE":
            hedge_strike = strike - 100
            return f"Consider selling {hedge_strike} PE to create a spread"
        elif signal_type.startswith("SELL"):
            return "Consider buying protective option to limit risk"
        else:
            return "Monitor position closely"
    
    async def _filter_and_rank_signals(self, signals: List[DhanSignal], market_data: DhanMarketData) -> List[DhanSignal]:
        """Filter and rank signals by quality"""
        # Filter by minimum confidence
        qualified_signals = [s for s in signals if s.confidence >= self.min_confidence]
        
        # Sort by a composite score
        qualified_signals.sort(key=lambda s: (
            s.confidence * 0.4 +
            s.risk_reward_ratio * 10 +
            s.probability_of_profit * 30
        ), reverse=True)
        
        return qualified_signals
    
    async def _cache_signals(self, signals: List[DhanSignal]):
        """Cache signals for later retrieval"""
        try:
            if redis_client:
                signals_data = [asdict(signal) for signal in signals]
                await redis_client.setex(
                    "dhan_latest_signals", 
                    300,  # 5 minutes
                    json.dumps(signals_data, default=str)
                )
        except Exception as e:
            logger.warning(f"Failed to cache signals: {e}")
    
    async def _load_historical_context(self):
        """Load historical context for better signal generation"""
        try:
            # Load last 30 days of Nifty data for context
            historical_data = await self.dhan_service.get_historical_data(
                "26000", "IDX_I", "1",
                from_date=(datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
            )
            
            if historical_data:
                self.market_data_cache["historical_context"] = historical_data
                logger.info(f"Loaded {len(historical_data)} days of historical context")
            
        except Exception as e:
            logger.warning(f"Failed to load historical context: {e}")
    
    async def _analyze_market_regime(self, market_data: DhanMarketData) -> Dict[str, Any]:
        """Analyze current market regime for trading suitability"""
        
        regime = {
            "suitable_for_trading": True,
            "trend": market_data.trend,
            "volatility_regime": market_data.volatility_regime,
            "risk_level": "MEDIUM",
            "preferred_strategies": []
        }
        
        # Check if market is suitable for trading
        if abs(market_data.nifty_change_percent) > 3:
            regime["risk_level"] = "HIGH"
            regime["preferred_strategies"] = ["BUYING_OPTIONS"]
        elif market_data.vix > 25:
            regime["risk_level"] = "HIGH"
            regime["preferred_strategies"] = ["SELLING_OPTIONS", "SPREADS"]
        elif market_data.vix < 12:
            regime["risk_level"] = "LOW"
            regime["suitable_for_trading"] = False  # Very low volatility
        else:
            regime["preferred_strategies"] = ["MIXED"]
        
        return regime
    
    def _identify_support_resistance(self, call_oi: Dict, put_oi: Dict) -> Dict[str, List]:
        """Identify support and resistance levels from option OI"""
        support_levels = []
        resistance_levels = []
        
        # Find strikes with high put OI (support)
        sorted_put_oi = sorted(put_oi.items(), key=lambda x: x[1], reverse=True)
        support_levels = [strike for strike, oi in sorted_put_oi[:3] if oi > 50000]
        
        # Find strikes with high call OI (resistance)
        sorted_call_oi = sorted(call_oi.items(), key=lambda x: x[1], reverse=True)
        resistance_levels = [strike for strike, oi in sorted_call_oi[:3] if oi > 50000]
        
        return {
            "support": support_levels,
            "resistance": resistance_levels
        }
    
    async def _generate_volatility_signals(self, market_data: DhanMarketData, option_chain: Dict, limit: int) -> List[DhanSignal]:
        """Generate volatility-based signals"""
        signals = []
        
        try:
            if market_data.vix > 25:
                # High volatility - sell options
                current_price = market_data.nifty_price
                atm_strike = round(current_price / 50) * 50
                expiry = option_chain.get("expiry", self.dhan_service._get_current_expiry())
                
                # Sell OTM strangles
                call_strike = atm_strike + 150
                put_strike = atm_strike - 150
                
                option_prices = await self.dhan_service.get_option_prices([call_strike, put_strike], expiry, "both")
                
                if f"{call_strike}CE" in option_prices:
                    signal = await self._create_signal(
                        signal_type="SELL_CE",
                        strike=call_strike,
                        expiry=expiry,
                        entry_price=option_prices[f"{call_strike}CE"]["ltp"],
                        market_data=market_data,
                        option_data=option_prices[f"{call_strike}CE"],
                        reasoning="High volatility environment - selling OTM call"
                    )
                    signals.append(signal)
                
                if f"{put_strike}PE" in option_prices:
                    signal = await self._create_signal(
                        signal_type="SELL_PE",
                        strike=put_strike,
                        expiry=expiry,
                        entry_price=option_prices[f"{put_strike}PE"]["ltp"],
                        market_data=market_data,
                        option_data=option_prices[f"{put_strike}PE"],
                        reasoning="High volatility environment - selling OTM put"
                    )
                    signals.append(signal)
                    
        except Exception as e:
            logger.error(f"Error generating volatility signals: {e}")
        
        return signals[:limit]
