"""
Auto-Adaptive Strategy Selector - Dynamic Strategy Selection Based on Market Conditions
Uses machine learning and market regime analysis to automatically select optimal strategies
"""

import asyncio
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import logging
from enum import Enum
import joblib
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, precision_score, recall_score
import threading

logger = logging.getLogger(__name__)

class MarketRegime(Enum):
    TRENDING_UP = "trending_up"
    TRENDING_DOWN = "trending_down"
    SIDEWAYS = "sideways"
    HIGH_VOLATILITY = "high_volatility"
    LOW_VOLATILITY = "low_volatility"
    BREAKOUT = "breakout"
    BREAKDOWN = "breakdown"
    CONSOLIDATION = "consolidation"

class StrategyType(Enum):
    MOMENTUM = "momentum"
    MEAN_REVERSION = "mean_reversion"
    VOLATILITY_BREAKOUT = "volatility_breakout"
    DELTA_HEDGED = "delta_hedged"
    GAMMA_SCALPING = "gamma_scalping"
    VEGA_NEUTRAL = "vega_neutral"
    IRON_CONDOR = "iron_condor"
    STRADDLE = "straddle"
    STRANGLE = "strangle"
    BUTTERFLY = "butterfly"
    CALENDAR_SPREAD = "calendar_spread"

@dataclass
class MarketCondition:
    """Current market condition assessment"""
    regime: MarketRegime
    volatility: float
    trend_strength: float
    volume_profile: float
    option_flow_sentiment: float
    vix_level: float
    time_to_expiry: float
    timestamp: datetime
    confidence: float

@dataclass
class StrategyPerformance:
    """Strategy performance metrics"""
    strategy_type: StrategyType
    total_trades: int
    win_rate: float
    avg_return: float
    max_drawdown: float
    sharpe_ratio: float
    calmar_ratio: float
    recent_performance: float
    market_regime_performance: Dict[MarketRegime, float]
    last_updated: datetime

@dataclass
class StrategyRecommendation:
    """Strategy recommendation with reasoning"""
    strategy_type: StrategyType
    confidence: float
    expected_return: float
    risk_level: float
    market_fit_score: float
    reasoning: str
    parameters: Dict[str, Any]

class AutoAdaptiveSelector:
    """Auto-adaptive strategy selector using ML and market analysis"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.strategy_performance: Dict[StrategyType, StrategyPerformance] = {}
        self.market_history: List[MarketCondition] = []
        self.strategy_history: List[Tuple[datetime, StrategyType, float]] = []
        
        # ML Models
        self.regime_classifier = RandomForestClassifier(n_estimators=100, random_state=42)
        self.strategy_selector = GradientBoostingClassifier(n_estimators=100, random_state=42)
        self.scaler = StandardScaler()
        
        # Model training status
        self.models_trained = False
        self.last_training = None
        self.training_lock = threading.Lock()
        
        # Strategy weights and preferences
        self.strategy_weights = {
            StrategyType.MOMENTUM: 1.0,
            StrategyType.MEAN_REVERSION: 1.0,
            StrategyType.VOLATILITY_BREAKOUT: 1.0,
            StrategyType.DELTA_HEDGED: 1.2,  # Prefer hedged strategies
            StrategyType.GAMMA_SCALPING: 1.1,
            StrategyType.VEGA_NEUTRAL: 1.0,
            StrategyType.IRON_CONDOR: 0.9,
            StrategyType.STRADDLE: 1.0,
            StrategyType.STRANGLE: 1.0,
            StrategyType.BUTTERFLY: 0.8,
            StrategyType.CALENDAR_SPREAD: 0.9
        }
        
        # Initialize with default performance data
        self._initialize_default_performance()
        
        logger.info("Auto-Adaptive Strategy Selector initialized")
    
    def _initialize_default_performance(self):
        """Initialize with default strategy performance data"""
        for strategy in StrategyType:
            self.strategy_performance[strategy] = StrategyPerformance(
                strategy_type=strategy,
                total_trades=0,
                win_rate=0.5,
                avg_return=0.0,
                max_drawdown=0.0,
                sharpe_ratio=0.0,
                calmar_ratio=0.0,
                recent_performance=0.0,
                market_regime_performance={regime: 0.0 for regime in MarketRegime},
                last_updated=datetime.now()
            )
    
    async def analyze_market_condition(self, market_data: Dict[str, Any]) -> MarketCondition:
        """Analyze current market condition"""
        try:
            # Extract market features
            price_data = market_data.get('price_data', {})
            volume_data = market_data.get('volume_data', {})
            options_data = market_data.get('options_data', {})
            
            # Calculate market metrics
            volatility = self._calculate_volatility(price_data)
            trend_strength = self._calculate_trend_strength(price_data)
            volume_profile = self._calculate_volume_profile(volume_data)
            option_flow_sentiment = self._calculate_option_flow_sentiment(options_data)
            vix_level = market_data.get('vix', 20.0)
            time_to_expiry = market_data.get('time_to_expiry', 30.0)
            
            # Determine market regime
            regime = await self._classify_market_regime(
                volatility, trend_strength, volume_profile, vix_level
            )
            
            # Calculate confidence based on signal clarity
            confidence = self._calculate_regime_confidence(
                volatility, trend_strength, volume_profile
            )
            
            market_condition = MarketCondition(
                regime=regime,
                volatility=volatility,
                trend_strength=trend_strength,
                volume_profile=volume_profile,
                option_flow_sentiment=option_flow_sentiment,
                vix_level=vix_level,
                time_to_expiry=time_to_expiry,
                timestamp=datetime.now(),
                confidence=confidence
            )
            
            # Store in history
            self.market_history.append(market_condition)
            if len(self.market_history) > 1000:
                self.market_history = self.market_history[-1000:]
            
            return market_condition
            
        except Exception as e:
            logger.error(f"Error analyzing market condition: {e}")
            # Return default condition
            return MarketCondition(
                regime=MarketRegime.SIDEWAYS,
                volatility=20.0,
                trend_strength=0.5,
                volume_profile=1.0,
                option_flow_sentiment=0.0,
                vix_level=20.0,
                time_to_expiry=30.0,
                timestamp=datetime.now(),
                confidence=0.5
            )
    
    async def select_optimal_strategy(self, market_condition: MarketCondition) -> List[StrategyRecommendation]:
        """Select optimal strategy based on market condition"""
        try:
            recommendations = []
            
            # Get strategy scores for current market condition
            strategy_scores = await self._calculate_strategy_scores(market_condition)
            
            # Sort strategies by score
            sorted_strategies = sorted(
                strategy_scores.items(),
                key=lambda x: x[1],
                reverse=True
            )
            
            # Generate recommendations for top strategies
            for strategy_type, score in sorted_strategies[:5]:
                recommendation = await self._generate_strategy_recommendation(
                    strategy_type, market_condition, score
                )
                recommendations.append(recommendation)
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Error selecting optimal strategy: {e}")
            return []
    
    async def _calculate_strategy_scores(self, market_condition: MarketCondition) -> Dict[StrategyType, float]:
        """Calculate strategy scores based on market condition"""
        scores = {}
        
        for strategy_type in StrategyType:
            # Base score from historical performance
            performance = self.strategy_performance[strategy_type]
            base_score = self._calculate_base_score(performance, market_condition.regime)
            
            # Market condition adjustment
            market_adjustment = self._calculate_market_adjustment(strategy_type, market_condition)
            
            # Volatility adjustment
            volatility_adjustment = self._calculate_volatility_adjustment(strategy_type, market_condition.volatility)
            
            # Time decay adjustment
            time_adjustment = self._calculate_time_adjustment(strategy_type, market_condition.time_to_expiry)
            
            # Apply strategy weight
            weight = self.strategy_weights.get(strategy_type, 1.0)
            
            # Final score
            final_score = base_score * market_adjustment * volatility_adjustment * time_adjustment * weight
            scores[strategy_type] = final_score
        
        return scores
    
    def _calculate_base_score(self, performance: StrategyPerformance, regime: MarketRegime) -> float:
        """Calculate base score from performance metrics"""
        # Weight different metrics
        win_rate_weight = 0.3
        avg_return_weight = 0.4
        sharpe_weight = 0.2
        regime_performance_weight = 0.1
        
        # Normalize metrics
        win_rate_score = performance.win_rate
        return_score = max(0, min(1, (performance.avg_return + 0.1) / 0.2))  # Normalize around 0-20%
        sharpe_score = max(0, min(1, (performance.sharpe_ratio + 1) / 3))  # Normalize around -1 to 2
        regime_score = performance.market_regime_performance.get(regime, 0.0)
        
        base_score = (
            win_rate_weight * win_rate_score +
            avg_return_weight * return_score +
            sharpe_weight * sharpe_score +
            regime_performance_weight * regime_score
        )
        
        return base_score
    
    def _calculate_market_adjustment(self, strategy_type: StrategyType, market_condition: MarketCondition) -> float:
        """Calculate market condition adjustment factor"""
        regime = market_condition.regime
        
        # Strategy-regime compatibility matrix
        compatibility = {
            StrategyType.MOMENTUM: {
                MarketRegime.TRENDING_UP: 1.5,
                MarketRegime.TRENDING_DOWN: 1.5,
                MarketRegime.BREAKOUT: 1.8,
                MarketRegime.BREAKDOWN: 1.8,
                MarketRegime.SIDEWAYS: 0.3,
                MarketRegime.CONSOLIDATION: 0.2,
                MarketRegime.HIGH_VOLATILITY: 1.2,
                MarketRegime.LOW_VOLATILITY: 0.7
            },
            StrategyType.MEAN_REVERSION: {
                MarketRegime.TRENDING_UP: 0.4,
                MarketRegime.TRENDING_DOWN: 0.4,
                MarketRegime.BREAKOUT: 0.2,
                MarketRegime.BREAKDOWN: 0.2,
                MarketRegime.SIDEWAYS: 1.6,
                MarketRegime.CONSOLIDATION: 1.8,
                MarketRegime.HIGH_VOLATILITY: 1.3,
                MarketRegime.LOW_VOLATILITY: 1.1
            },
            StrategyType.VOLATILITY_BREAKOUT: {
                MarketRegime.TRENDING_UP: 1.2,
                MarketRegime.TRENDING_DOWN: 1.2,
                MarketRegime.BREAKOUT: 1.9,
                MarketRegime.BREAKDOWN: 1.9,
                MarketRegime.SIDEWAYS: 0.5,
                MarketRegime.CONSOLIDATION: 1.4,
                MarketRegime.HIGH_VOLATILITY: 1.6,
                MarketRegime.LOW_VOLATILITY: 0.4
            },
            StrategyType.DELTA_HEDGED: {
                MarketRegime.TRENDING_UP: 1.1,
                MarketRegime.TRENDING_DOWN: 1.1,
                MarketRegime.BREAKOUT: 1.0,
                MarketRegime.BREAKDOWN: 1.0,
                MarketRegime.SIDEWAYS: 1.3,
                MarketRegime.CONSOLIDATION: 1.2,
                MarketRegime.HIGH_VOLATILITY: 1.4,
                MarketRegime.LOW_VOLATILITY: 1.0
            },
            StrategyType.GAMMA_SCALPING: {
                MarketRegime.TRENDING_UP: 0.8,
                MarketRegime.TRENDING_DOWN: 0.8,
                MarketRegime.BREAKOUT: 0.6,
                MarketRegime.BREAKDOWN: 0.6,
                MarketRegime.SIDEWAYS: 1.5,
                MarketRegime.CONSOLIDATION: 1.4,
                MarketRegime.HIGH_VOLATILITY: 1.7,
                MarketRegime.LOW_VOLATILITY: 0.5
            },
            StrategyType.IRON_CONDOR: {
                MarketRegime.TRENDING_UP: 0.3,
                MarketRegime.TRENDING_DOWN: 0.3,
                MarketRegime.BREAKOUT: 0.2,
                MarketRegime.BREAKDOWN: 0.2,
                MarketRegime.SIDEWAYS: 1.8,
                MarketRegime.CONSOLIDATION: 1.6,
                MarketRegime.HIGH_VOLATILITY: 0.4,
                MarketRegime.LOW_VOLATILITY: 1.5
            },
            StrategyType.STRADDLE: {
                MarketRegime.TRENDING_UP: 1.3,
                MarketRegime.TRENDING_DOWN: 1.3,
                MarketRegime.BREAKOUT: 1.7,
                MarketRegime.BREAKDOWN: 1.7,
                MarketRegime.SIDEWAYS: 0.4,
                MarketRegime.CONSOLIDATION: 0.6,
                MarketRegime.HIGH_VOLATILITY: 1.5,
                MarketRegime.LOW_VOLATILITY: 0.3
            }
        }
        
        # Default compatibility for strategies not in matrix
        default_compatibility = {regime: 1.0 for regime in MarketRegime}
        
        strategy_compatibility = compatibility.get(strategy_type, default_compatibility)
        return strategy_compatibility.get(regime, 1.0)
    
    def _calculate_volatility_adjustment(self, strategy_type: StrategyType, volatility: float) -> float:
        """Calculate volatility-based adjustment"""
        # Volatility preferences for each strategy
        volatility_preferences = {
            StrategyType.MOMENTUM: (15, 35),  # Optimal volatility range
            StrategyType.MEAN_REVERSION: (10, 25),
            StrategyType.VOLATILITY_BREAKOUT: (20, 50),
            StrategyType.DELTA_HEDGED: (5, 40),
            StrategyType.GAMMA_SCALPING: (15, 45),
            StrategyType.VEGA_NEUTRAL: (10, 30),
            StrategyType.IRON_CONDOR: (5, 20),
            StrategyType.STRADDLE: (20, 60),
            StrategyType.STRANGLE: (15, 50),
            StrategyType.BUTTERFLY: (5, 25),
            StrategyType.CALENDAR_SPREAD: (10, 30)
        }
        
        min_vol, max_vol = volatility_preferences.get(strategy_type, (10, 30))
        
        if min_vol <= volatility <= max_vol:
            return 1.2  # Boost for optimal range
        elif volatility < min_vol:
            return 0.5 + 0.5 * (volatility / min_vol)
        else:  # volatility > max_vol
            return 1.2 - 0.7 * ((volatility - max_vol) / max_vol)
    
    def _calculate_time_adjustment(self, strategy_type: StrategyType, time_to_expiry: float) -> float:
        """Calculate time to expiry adjustment"""
        # Time preferences (days to expiry)
        time_preferences = {
            StrategyType.MOMENTUM: (5, 30),
            StrategyType.MEAN_REVERSION: (7, 45),
            StrategyType.VOLATILITY_BREAKOUT: (3, 21),
            StrategyType.DELTA_HEDGED: (14, 60),
            StrategyType.GAMMA_SCALPING: (1, 14),
            StrategyType.VEGA_NEUTRAL: (21, 90),
            StrategyType.IRON_CONDOR: (14, 45),
            StrategyType.STRADDLE: (7, 30),
            StrategyType.STRANGLE: (14, 45),
            StrategyType.BUTTERFLY: (21, 60),
            StrategyType.CALENDAR_SPREAD: (30, 120)
        }
        
        min_time, max_time = time_preferences.get(strategy_type, (14, 45))
        
        if min_time <= time_to_expiry <= max_time:
            return 1.1
        elif time_to_expiry < min_time:
            return 0.6 + 0.4 * (time_to_expiry / min_time)
        else:
            return 1.1 - 0.5 * ((time_to_expiry - max_time) / max_time)
    
    async def _generate_strategy_recommendation(
        self, 
        strategy_type: StrategyType, 
        market_condition: MarketCondition, 
        score: float
    ) -> StrategyRecommendation:
        """Generate detailed strategy recommendation"""
        
        performance = self.strategy_performance[strategy_type]
        
        # Calculate expected return based on historical performance and market fit
        expected_return = performance.avg_return * score
        
        # Calculate risk level
        risk_level = max(0.1, min(1.0, performance.max_drawdown + (1 - score) * 0.3))
        
        # Market fit score
        market_fit_score = score
        
        # Generate reasoning
        reasoning = self._generate_reasoning(strategy_type, market_condition, score)
        
        # Generate strategy parameters
        parameters = self._generate_strategy_parameters(strategy_type, market_condition)
        
        return StrategyRecommendation(
            strategy_type=strategy_type,
            confidence=min(1.0, score * market_condition.confidence),
            expected_return=expected_return,
            risk_level=risk_level,
            market_fit_score=market_fit_score,
            reasoning=reasoning,
            parameters=parameters
        )
    
    def _generate_reasoning(self, strategy_type: StrategyType, market_condition: MarketCondition, score: float) -> str:
        """Generate human-readable reasoning for strategy selection"""
        regime = market_condition.regime.value.replace('_', ' ').title()
        vol_level = "high" if market_condition.volatility > 25 else "moderate" if market_condition.volatility > 15 else "low"
        
        base_reasoning = f"Market regime: {regime}, Volatility: {vol_level} ({market_condition.volatility:.1f}%)"
        
        strategy_reasons = {
            StrategyType.MOMENTUM: f"Strong directional movement expected. {base_reasoning}",
            StrategyType.MEAN_REVERSION: f"Market showing oversold/overbought conditions. {base_reasoning}",
            StrategyType.VOLATILITY_BREAKOUT: f"Volatility expansion anticipated. {base_reasoning}",
            StrategyType.DELTA_HEDGED: f"Market neutral approach suitable for current conditions. {base_reasoning}",
            StrategyType.GAMMA_SCALPING: f"High gamma exposure profitable in current volatility environment. {base_reasoning}",
            StrategyType.IRON_CONDOR: f"Range-bound market ideal for premium collection. {base_reasoning}",
            StrategyType.STRADDLE: f"Significant move expected in either direction. {base_reasoning}"
        }
        
        return strategy_reasons.get(strategy_type, f"Strategy suitable for current market conditions. {base_reasoning}")
    
    def _generate_strategy_parameters(self, strategy_type: StrategyType, market_condition: MarketCondition) -> Dict[str, Any]:
        """Generate optimal parameters for the strategy"""
        base_params = {
            "volatility": market_condition.volatility,
            "time_to_expiry": market_condition.time_to_expiry,
            "market_regime": market_condition.regime.value
        }
        
        strategy_specific = {
            StrategyType.MOMENTUM: {
                "stop_loss": 0.15 if market_condition.volatility > 25 else 0.10,
                "take_profit": 0.25 if market_condition.volatility > 25 else 0.20,
                "momentum_threshold": 0.7
            },
            StrategyType.MEAN_REVERSION: {
                "oversold_threshold": 0.2,
                "overbought_threshold": 0.8,
                "mean_reversion_period": 14
            },
            StrategyType.DELTA_HEDGED: {
                "hedge_ratio": 0.5,
                "rebalance_threshold": 0.1,
                "max_delta_exposure": 0.2
            },
            StrategyType.GAMMA_SCALPING: {
                "gamma_target": 0.05,
                "scalping_frequency": "intraday",
                "profit_target": 0.1
            },
            StrategyType.IRON_CONDOR: {
                "wing_width": 100,
                "profit_target": 0.5,
                "max_loss": 0.2
            }
        }
        
        base_params.update(strategy_specific.get(strategy_type, {}))
        return base_params
    
    # Market analysis helper methods
    def _calculate_volatility(self, price_data: Dict[str, Any]) -> float:
        """Calculate current volatility"""
        try:
            closes = price_data.get('close', [])
            if len(closes) < 20:
                return 20.0  # Default
            
            returns = np.diff(np.log(closes))
            volatility = np.std(returns) * np.sqrt(252) * 100
            return min(100, max(5, volatility))
        except:
            return 20.0
    
    def _calculate_trend_strength(self, price_data: Dict[str, Any]) -> float:
        """Calculate trend strength (0-1)"""
        try:
            closes = price_data.get('close', [])
            if len(closes) < 20:
                return 0.5
            
            # Simple trend strength based on moving averages
            ma_short = np.mean(closes[-10:])
            ma_long = np.mean(closes[-20:])
            
            trend_strength = abs(ma_short - ma_long) / ma_long
            return min(1.0, trend_strength * 10)
        except:
            return 0.5
    
    def _calculate_volume_profile(self, volume_data: Dict[str, Any]) -> float:
        """Calculate volume profile relative to average"""
        try:
            volumes = volume_data.get('volume', [])
            if len(volumes) < 20:
                return 1.0
            
            current_volume = volumes[-1]
            avg_volume = np.mean(volumes[-20:])
            
            return current_volume / avg_volume if avg_volume > 0 else 1.0
        except:
            return 1.0
    
    def _calculate_option_flow_sentiment(self, options_data: Dict[str, Any]) -> float:
        """Calculate option flow sentiment (-1 to 1)"""
        try:
            put_call_ratio = options_data.get('put_call_ratio', 1.0)
            # Convert to sentiment (-1 bearish, 1 bullish)
            sentiment = (1 - put_call_ratio) if put_call_ratio <= 2 else -0.5
            return max(-1, min(1, sentiment))
        except:
            return 0.0
    
    async def _classify_market_regime(self, volatility: float, trend_strength: float, volume_profile: float, vix: float) -> MarketRegime:
        """Classify current market regime"""
        try:
            # Rule-based classification (can be enhanced with ML)
            if volatility > 30 or vix > 30:
                return MarketRegime.HIGH_VOLATILITY
            elif volatility < 12 and vix < 15:
                return MarketRegime.LOW_VOLATILITY
            elif trend_strength > 0.7:
                if volume_profile > 1.5:
                    return MarketRegime.BREAKOUT if trend_strength > 0.8 else MarketRegime.TRENDING_UP
                else:
                    return MarketRegime.TRENDING_UP
            elif trend_strength < 0.3:
                return MarketRegime.CONSOLIDATION if volume_profile < 0.8 else MarketRegime.SIDEWAYS
            else:
                return MarketRegime.SIDEWAYS
        except:
            return MarketRegime.SIDEWAYS
    
    def _calculate_regime_confidence(self, volatility: float, trend_strength: float, volume_profile: float) -> float:
        """Calculate confidence in regime classification"""
        # Higher confidence when signals are clear
        vol_clarity = 1.0 - abs(volatility - 20) / 20  # More confident away from neutral 20%
        trend_clarity = abs(trend_strength - 0.5) * 2  # More confident away from neutral 0.5
        volume_clarity = 1.0 - abs(volume_profile - 1.0)  # More confident away from average volume
        
        confidence = (vol_clarity + trend_clarity + volume_clarity) / 3
        return max(0.3, min(1.0, confidence))
    
    async def update_strategy_performance(self, strategy_type: StrategyType, trade_result: Dict[str, Any]) -> None:
        """Update strategy performance based on trade results"""
        try:
            performance = self.strategy_performance[strategy_type]
            
            # Update trade count
            performance.total_trades += 1
            
            # Update win rate
            is_win = trade_result.get('profit_loss', 0) > 0
            old_wins = performance.win_rate * (performance.total_trades - 1)
            new_wins = old_wins + (1 if is_win else 0)
            performance.win_rate = new_wins / performance.total_trades
            
            # Update average return
            return_pct = trade_result.get('return_pct', 0)
            old_avg = performance.avg_return * (performance.total_trades - 1)
            performance.avg_return = (old_avg + return_pct) / performance.total_trades
            
            # Update recent performance (last 20 trades)
            if not hasattr(performance, 'recent_returns'):
                performance.recent_returns = []
            performance.recent_returns.append(return_pct)
            if len(performance.recent_returns) > 20:
                performance.recent_returns = performance.recent_returns[-20:]
            performance.recent_performance = np.mean(performance.recent_returns)
            
            performance.last_updated = datetime.now()
            
            logger.info(f"Updated performance for {strategy_type.value}: Win rate: {performance.win_rate:.2f}, Avg return: {performance.avg_return:.2f}%")
            
        except Exception as e:
            logger.error(f"Error updating strategy performance: {e}")
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get performance summary for all strategies"""
        summary = {}
        
        for strategy_type, performance in self.strategy_performance.items():
            summary[strategy_type.value] = {
                "total_trades": performance.total_trades,
                "win_rate": performance.win_rate,
                "avg_return": performance.avg_return,
                "recent_performance": performance.recent_performance,
                "sharpe_ratio": performance.sharpe_ratio,
                "last_updated": performance.last_updated.isoformat()
            }
        
        return summary

# Factory function
def create_auto_adaptive_selector(config: Dict[str, Any]) -> AutoAdaptiveSelector:
    """Factory function to create auto-adaptive selector"""
    return AutoAdaptiveSelector(config)
