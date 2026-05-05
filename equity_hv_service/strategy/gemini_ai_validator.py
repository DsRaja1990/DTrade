"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                    GEMINI AI TRADE VALIDATOR v1.0                            ║
║            Integrates 3-Tier Gemini AI for Trade Confirmation                ║
║━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━║
║  Purpose: Validate World-Class Engine signals with AI confirmation           ║
║  Target: Increase Win Rate from 85% to 95%+                                  ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import json
import logging
import asyncio
import aiohttp
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

# Gemini Trade Service endpoint
GEMINI_SERVICE_URL = "http://localhost:8080"


class AIConfidence(Enum):
    """AI Confidence levels"""
    CONFIRMED = "confirmed"      # 90%+ confidence - IMMEDIATE ENTRY
    VALIDATED = "validated"      # 80-90% confidence - ENTRY OK
    CAUTIOUS = "cautious"        # 70-80% confidence - REDUCED SIZE
    REJECTED = "rejected"        # <70% confidence - NO TRADE


@dataclass
class AIValidationResult:
    """Result from Gemini AI validation"""
    confidence: AIConfidence
    confidence_score: float  # 0-100
    ai_thesis: str
    risk_factors: List[str]
    catalysts: List[str]
    
    # Price targets from Tier 3
    max_target: float
    reversal_point: float
    hold_duration_minutes: int
    
    # Context scores
    market_breadth_score: float  # -10 to +10
    options_flow_score: float
    vix_score: float
    fii_dii_score: float
    sentiment_score: float
    
    # Final decision
    final_decision: str  # GO or NO-GO
    veto_reason: Optional[str] = None
    
    # Timestamps
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()
    
    @property
    def is_trade_approved(self) -> bool:
        """Check if trade is approved by AI"""
        return (self.final_decision == "GO" and 
                self.confidence in [AIConfidence.CONFIRMED, AIConfidence.VALIDATED])
    
    @property
    def position_size_multiplier(self) -> float:
        """Get position size multiplier based on confidence"""
        if self.confidence == AIConfidence.CONFIRMED:
            return 1.0  # Full size
        elif self.confidence == AIConfidence.VALIDATED:
            return 0.75  # 75% size
        elif self.confidence == AIConfidence.CAUTIOUS:
            return 0.5  # 50% size
        else:
            return 0.0  # No trade


class GeminiAIValidator:
    """
    Validates trading signals using 3-Tier Gemini AI
    
    Tier 1: Market Breadth Analysis (50 Nifty stocks)
    Tier 2: Options/VIX/Sentiment/FII-DII Context
    Tier 3: Price Prediction & Final Decision
    """
    
    def __init__(self, service_url: str = GEMINI_SERVICE_URL):
        self.service_url = service_url
        self.session = None
        self.is_available = False
        self.cache = {}
        self.cache_duration = 60  # seconds
        self._initialized = False
        
        logger.info(f"🤖 Gemini AI Validator initialized - Service: {service_url}")
    
    async def initialize(self):
        """Initialize async session and check service availability"""
        if self._initialized:
            return
            
        try:
            self.session = aiohttp.ClientSession()
            
            # Check if Gemini service is running
            async with self.session.get(f"{self.service_url}/health", timeout=5) as response:
                if response.status == 200:
                    self.is_available = True
                    logger.info("✅ Gemini AI Service is available")
                else:
                    self.is_available = False
                    logger.warning("⚠️ Gemini AI Service not responding")
        except Exception as e:
            self.is_available = False
            logger.warning(f"⚠️ Gemini AI Service not available: {e}")
            # Close session if service unavailable
            if self.session:
                await self.session.close()
                self.session = None
        
        self._initialized = True
    
    async def close(self):
        """Close async session"""
        if self.session and not self.session.closed:
            await self.session.close()
            self.session = None
        self._initialized = False
    
    def __del__(self):
        """Cleanup on deletion"""
        if self.session and not self.session.closed:
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    loop.create_task(self.close())
                else:
                    loop.run_until_complete(self.close())
            except Exception:
                pass  # Ignore cleanup errors
    
    async def validate_signal(
        self,
        symbol: str,
        current_price: float,
        signal_confidence: str,
        patterns_matched: List[str],
        rsi: float,
        target_price: float,
        stop_loss: float,
        force_refresh: bool = False
    ) -> AIValidationResult:
        """
        Validate a trading signal using Gemini AI 3-tier system
        
        Args:
            symbol: Stock symbol
            current_price: Current stock price
            signal_confidence: Signal confidence level from World-Class Engine
            patterns_matched: List of patterns that matched
            rsi: Current RSI value
            target_price: Proposed target price
            stop_loss: Proposed stop loss
            force_refresh: Skip cache
            
        Returns:
            AIValidationResult with AI confirmation
        """
        
        # Check cache first
        cache_key = f"{symbol}_{current_price:.2f}"
        if not force_refresh and cache_key in self.cache:
            cached_result, cached_time = self.cache[cache_key]
            if (datetime.now() - cached_time).seconds < self.cache_duration:
                logger.info(f"📦 Using cached AI validation for {symbol}")
                return cached_result
        
        # If service is not available, return a default validation
        if not self.is_available:
            return self._get_fallback_validation(
                symbol, current_price, signal_confidence, patterns_matched, rsi
            )
        
        try:
            # Call Gemini Trade Service for full 3-tier analysis
            validation_request = {
                "symbol": symbol,
                "current_price": current_price,
                "signal_confidence": signal_confidence,
                "patterns_matched": patterns_matched,
                "rsi": rsi,
                "proposed_target": target_price,
                "proposed_stop_loss": stop_loss,
                "request_type": "EQUITY_VALIDATION"
            }
            
            async with self.session.post(
                f"{self.service_url}/api/validate-trade",
                json=validation_request,
                timeout=10
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    result = self._parse_ai_response(data, symbol)
                    
                    # Cache the result
                    self.cache[cache_key] = (result, datetime.now())
                    
                    return result
                else:
                    logger.warning(f"AI validation failed for {symbol}: {response.status}")
                    return self._get_fallback_validation(
                        symbol, current_price, signal_confidence, patterns_matched, rsi
                    )
                    
        except asyncio.TimeoutError:
            logger.warning(f"AI validation timeout for {symbol}")
            return self._get_fallback_validation(
                symbol, current_price, signal_confidence, patterns_matched, rsi
            )
        except Exception as e:
            logger.error(f"AI validation error for {symbol}: {e}")
            return self._get_fallback_validation(
                symbol, current_price, signal_confidence, patterns_matched, rsi
            )
    
    def _parse_ai_response(self, data: Dict, symbol: str) -> AIValidationResult:
        """Parse AI service response into AIValidationResult"""
        
        # Extract confidence
        confidence_score = data.get("confidence_score", 75)
        if confidence_score >= 90:
            confidence = AIConfidence.CONFIRMED
        elif confidence_score >= 80:
            confidence = AIConfidence.VALIDATED
        elif confidence_score >= 70:
            confidence = AIConfidence.CAUTIOUS
        else:
            confidence = AIConfidence.REJECTED
        
        # Extract context vector
        context = data.get("context_vector", {})
        
        # Extract price forecast
        forecast = data.get("price_action_forecast", {})
        
        return AIValidationResult(
            confidence=confidence,
            confidence_score=confidence_score,
            ai_thesis=data.get("strategy_thesis", data.get("forecast_thesis", "No thesis")),
            risk_factors=data.get("risk_factors", []),
            catalysts=data.get("catalysts", []),
            max_target=forecast.get("max_level_target", 0),
            reversal_point=forecast.get("reversal_point", 0),
            hold_duration_minutes=data.get("hold_duration_minutes", 
                data.get("strategic_recommendation", {}).get("hold_duration_minutes", 15)),
            market_breadth_score=context.get("market_breadth_score", 0),
            options_flow_score=context.get("options_flow_score", 0),
            vix_score=context.get("vix_score", 0),
            fii_dii_score=context.get("fii_dii_score", 0),
            sentiment_score=context.get("sentiment_score", 0),
            final_decision=data.get("final_decision", "GO"),
            veto_reason=data.get("veto_reason")
        )
    
    def _get_fallback_validation(
        self,
        symbol: str,
        current_price: float,
        signal_confidence: str,
        patterns_matched: List[str],
        rsi: float
    ) -> AIValidationResult:
        """
        Fallback validation when AI service is not available
        Uses rule-based logic to provide a conservative validation
        """
        
        # Calculate confidence based on signal and patterns
        base_confidence = 70.0
        
        # Boost for legendary/ultra signals
        if signal_confidence == "legendary":
            base_confidence += 15
        elif signal_confidence == "ultra":
            base_confidence += 10
        elif signal_confidence == "premium":
            base_confidence += 5
        
        # Boost for multiple patterns
        pattern_boost = min(len(patterns_matched) * 2, 10)
        base_confidence += pattern_boost
        
        # RSI zone boost
        if 18 <= rsi <= 26:  # Legendary zone
            base_confidence += 5
        elif 27 <= rsi <= 30:  # Premium zone
            base_confidence += 2
        
        # Cap at 90 for fallback (can't confirm without AI)
        confidence_score = min(base_confidence, 90)
        
        # Determine confidence level
        if confidence_score >= 85:
            confidence = AIConfidence.VALIDATED
        elif confidence_score >= 75:
            confidence = AIConfidence.CAUTIOUS
        else:
            confidence = AIConfidence.REJECTED
        
        return AIValidationResult(
            confidence=confidence,
            confidence_score=confidence_score,
            ai_thesis=f"Fallback validation: {len(patterns_matched)} patterns matched, RSI={rsi:.1f}",
            risk_factors=["AI service unavailable - using conservative validation"],
            catalysts=patterns_matched[:3],
            max_target=current_price * 1.02,  # 2% target
            reversal_point=current_price * 1.015,
            hold_duration_minutes=15,
            market_breadth_score=0,
            options_flow_score=0,
            vix_score=0,
            fii_dii_score=0,
            sentiment_score=0,
            final_decision="GO" if confidence_score >= 75 else "NO-GO",
            veto_reason=None if confidence_score >= 75 else "Low confidence score"
        )
    
    async def get_market_context(self) -> Dict:
        """Get current market context from Gemini service"""
        if not self.is_available:
            return {}
        
        try:
            async with self.session.get(
                f"{self.service_url}/api/market-context",
                timeout=5
            ) as response:
                if response.status == 200:
                    return await response.json()
        except Exception as e:
            logger.warning(f"Failed to get market context: {e}")
        
        return {}
    
    async def get_vix_status(self) -> Dict:
        """Get current VIX status for risk assessment"""
        if not self.is_available:
            return {"vix": 15, "vix_change_pct": 0, "status": "unknown"}
        
        try:
            async with self.session.get(
                f"{self.service_url}/api/vix-status",
                timeout=5
            ) as response:
                if response.status == 200:
                    return await response.json()
        except Exception as e:
            logger.warning(f"Failed to get VIX status: {e}")
        
        return {"vix": 15, "vix_change_pct": 0, "status": "unknown"}


# Synchronous wrapper for easy integration
class SyncGeminiValidator:
    """Synchronous wrapper for GeminiAIValidator"""
    
    def __init__(self, service_url: str = GEMINI_SERVICE_URL):
        self.async_validator = GeminiAIValidator(service_url)
        self._loop = None
    
    def _get_loop(self):
        """Get or create event loop"""
        try:
            return asyncio.get_running_loop()
        except RuntimeError:
            if self._loop is None or self._loop.is_closed():
                self._loop = asyncio.new_event_loop()
            return self._loop
    
    def initialize(self):
        """Initialize the validator"""
        loop = self._get_loop()
        if loop.is_running():
            asyncio.ensure_future(self.async_validator.initialize())
        else:
            loop.run_until_complete(self.async_validator.initialize())
    
    def validate_signal(
        self,
        symbol: str,
        current_price: float,
        signal_confidence: str,
        patterns_matched: List[str],
        rsi: float,
        target_price: float,
        stop_loss: float
    ) -> AIValidationResult:
        """Validate signal synchronously"""
        loop = self._get_loop()
        
        coro = self.async_validator.validate_signal(
            symbol, current_price, signal_confidence,
            patterns_matched, rsi, target_price, stop_loss
        )
        
        if loop.is_running():
            # Create a new loop for sync call
            new_loop = asyncio.new_event_loop()
            try:
                return new_loop.run_until_complete(coro)
            finally:
                new_loop.close()
        else:
            return loop.run_until_complete(coro)
    
    def close(self):
        """Close the validator"""
        loop = self._get_loop()
        if not loop.is_running():
            loop.run_until_complete(self.async_validator.close())
            if self._loop and not self._loop.is_closed():
                self._loop.close()


# Quick test function
def test_validator():
    """Test the Gemini AI Validator"""
    validator = SyncGeminiValidator()
    validator.initialize()
    
    result = validator.validate_signal(
        symbol="RELIANCE",
        current_price=2500.0,
        signal_confidence="legendary",
        patterns_matched=["OVERSOLD_REVERSAL", "BB_SQUEEZE_BREAKOUT", "MACD_REVERSAL"],
        rsi=22.5,
        target_price=2550.0,
        stop_loss=2487.5
    )
    
    print(f"\n🤖 AI Validation Result for RELIANCE:")
    print(f"   Confidence: {result.confidence.value} ({result.confidence_score:.1f}%)")
    print(f"   Decision: {result.final_decision}")
    print(f"   Thesis: {result.ai_thesis[:100]}...")
    print(f"   Position Multiplier: {result.position_size_multiplier:.2f}")
    
    validator.close()
    return result


if __name__ == "__main__":
    test_validator()
