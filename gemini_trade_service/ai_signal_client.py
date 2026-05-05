"""
AI Signal Client
Shared library for all trading strategies to call Gemini Trade Service
"""
import requests
import logging
from typing import Dict, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class GeminiSignalClient:
    """
    Client to interact with Gemini Trade Service
    Used by all strategies to get AI-generated trade signals
    """
    
    def __init__(self, service_url: str = "http://localhost:4080"):
        """
        Initialize the Gemini Signal Client
        
        Args:
            service_url: URL of the Gemini Trade Service (default: http://localhost:4080)
        """
        self.service_url = service_url.rstrip('/')
        self.timeout = 30  # 30 seconds timeout
        self.last_signal = None
        self.last_signal_time = None
    
    async def get_trade_signal(self, index: str = "NIFTY") -> Dict:
        """
        Get AI-generated trade signal from Gemini Service
        
        Args:
            index: Index name (NIFTY or SENSEX)
        
        Returns:
            Dictionary with trade signal details:
            {
                "signal": "BUY_CALL" | "BUY_PUT" | "NO_TRADE",
                "strike": "25000CE" | "24950PE" | "NONE",
                "entry_range": "140-150",
                "stop_loss": "120",
                "target": "180",
                "confidence": 0-10,
                "reasoning": "explanation",
                "risk_adjustment": "optional adjustment",
                "macro_score": 0-10,
                "timestamp": "ISO timestamp"
            }
        """
        try:
            # Call Gemini Trade Service API
            url = f"{self.service_url}/api/signal"
            params = {"index": index}
            
            logger.info(f"Calling Gemini Trade Service: {url}")
            response = requests.get(url, params=params, timeout=self.timeout)
            
            if response.status_code == 200:
                signal_data = response.json()
                
                # Cache the signal
                self.last_signal = signal_data
                self.last_signal_time = datetime.now()
                
                logger.info(f"AI Signal: {signal_data.get('signal', 'UNKNOWN')} "
                          f"- Confidence: {signal_data.get('confidence', 0)}")
                
                return signal_data
            else:
                logger.error(f"Gemini Service returned status {response.status_code}: {response.text}")
                return self._get_fallback_signal()
        
        except requests.Timeout:
            logger.error("Gemini Service request timed out")
            return self._get_fallback_signal()
        
        except Exception as e:
            logger.error(f"Error calling Gemini Trade Service: {e}")
            return self._get_fallback_signal()
    
    def _get_fallback_signal(self) -> Dict:
        """
        Fallback signal when service is unavailable
        """
        return {
            "signal": "NO_TRADE",
            "confidence": 0,
            "reasoning": "Gemini Trade Service unavailable",
            "strike": "NONE",
            "entry_range": "NONE",
            "stop_loss": "NONE",
            "target": "NONE",
            "timestamp": datetime.now().isoformat()
        }
    
    def get_last_signal(self) -> Optional[Dict]:
        """
        Get the last cached signal
        
        Returns:
            Last signal data or None
        """
        return self.last_signal
    
    def is_signal_fresh(self, max_age_seconds: int = 300) -> bool:
        """
        Check if the last signal is still fresh
        
        Args:
            max_age_seconds: Maximum age in seconds (default: 300 = 5 minutes)
        
        Returns:
            True if signal is fresh, False otherwise
        """
        if not self.last_signal_time:
            return False
        
        age = (datetime.now() - self.last_signal_time).total_seconds()
        return age <= max_age_seconds
    
    def should_take_trade(self, 
                         ai_signal: str, 
                         strategy_signal: str, 
                         ai_confidence: float,
                         min_confidence: float = 6.0) -> bool:
        """
        Decision helper: Should the strategy take the trade?
        
        Args:
            ai_signal: AI signal (BUY_CALL, BUY_PUT, NO_TRADE)
            strategy_signal: Strategy's own signal
            ai_confidence: AI confidence score (0-10)
            min_confidence: Minimum confidence threshold
        
        Returns:
            True if trade should be taken, False otherwise
        """
        # If AI says NO_TRADE, be cautious
        if ai_signal == "NO_TRADE":
            logger.warning("AI recommends NO_TRADE - exercise caution")
            return False
        
        # If AI confidence is too low, skip
        if ai_confidence < min_confidence:
            logger.warning(f"AI confidence too low ({ai_confidence}) - skipping trade")
            return False
        
        # If AI and strategy align, strong signal
        if ai_signal == strategy_signal:
            logger.info(f"AI and strategy ALIGNED on {ai_signal} - Strong signal!")
            return True
        
        # If AI and strategy conflict, defer to AI if confidence is high
        if ai_confidence >= 8.0:
            logger.warning(f"AI ({ai_signal}) conflicts with strategy ({strategy_signal}) "
                         f"but AI confidence is high ({ai_confidence}) - Following AI")
            return True
        
        # Otherwise, skip
        logger.warning(f"AI ({ai_signal}) conflicts with strategy ({strategy_signal}) - Skipping")
        return False
    
    def get_weighted_confidence(self,
                               strategy_confidence: float,
                               ai_confidence: float,
                               strategy_weight: float = 0.5) -> float:
        """
        Calculate weighted confidence combining strategy and AI
        
        Args:
            strategy_confidence: Strategy's confidence (0-1 or 0-10)
            ai_confidence: AI confidence (0-10)
            strategy_weight: Weight for strategy (0-1, default 0.5 = 50/50)
        
        Returns:
            Weighted confidence score
        """
        # Normalize strategy confidence to 0-10 scale if needed
        if strategy_confidence <= 1.0:
            strategy_confidence *= 10
        
        # Calculate weighted average
        weighted = (strategy_confidence * strategy_weight) + (ai_confidence * (1 - strategy_weight))
        
        return round(weighted, 2)
    
    def health_check(self) -> bool:
        """
        Check if Gemini Trade Service is healthy
        
        Returns:
            True if service is healthy, False otherwise
        """
        try:
            url = f"{self.service_url}/health"
            response = requests.get(url, timeout=5)
            return response.status_code == 200
        except:
            return False

# Example usage:
# client = GeminiSignalClient()
# signal = await client.get_trade_signal("NIFTY")
# if client.should_take_trade(signal['signal'], "BUY_CALL", signal['confidence']):
#     # Execute trade
