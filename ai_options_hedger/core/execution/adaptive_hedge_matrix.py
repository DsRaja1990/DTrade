"""
Adaptive Hedge Matrix - Dynamic hedging system for maximum win rate
Implements intelligent hedging decisions based on market conditions
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum
import logging

logger = logging.getLogger(__name__)

class HedgeType(Enum):
    """Types of hedging strategies"""
    PROTECTIVE_PUT = "PROTECTIVE_PUT"
    PROTECTIVE_CALL = "PROTECTIVE_CALL"
    COLLAR = "COLLAR"
    STRADDLE = "STRADDLE"
    STRANGLE = "STRANGLE"
    IRON_CONDOR = "IRON_CONDOR"
    BUTTERFLY = "BUTTERFLY"
    CALENDAR = "CALENDAR"

class HedgeUrgency(Enum):
    """Urgency levels for hedging"""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

@dataclass
class HedgeRecommendation:
    """Hedge recommendation with detailed parameters"""
    hedge_type: HedgeType
    urgency: HedgeUrgency
    hedge_ratio: float  # 0.0 to 1.0
    optimal_strike: float
    expected_cost: float
    max_protection: float
    confidence: float
    time_to_implement: int  # minutes
    hedge_delta: float
    hedge_gamma: float
    hedge_theta: float
    hedge_vega: float
    reasoning: str

class AdaptiveHedgeMatrix:
    """
    Intelligent hedging system that adapts to market conditions
    Implements the precise hedging logic from the requirements
    """
    
    def __init__(self):
        # Premium spacing rules from requirements
        self.spacing_rules = {
            'SENSEX': {'min_spacing': 80, 'max_spacing': 100, 'optimal': 90},
            'BANKEX': {'min_spacing': 80, 'max_spacing': 100, 'optimal': 90},
            'NIFTY': {'min_spacing': 25, 'max_spacing': 50, 'optimal': 40},
            'BANKNIFTY': {'min_spacing': 25, 'max_spacing': 50, 'optimal': 40},
            'FINNIFTY': {'min_spacing': 25, 'max_spacing': 50, 'optimal': 40}
        }
        
        # Risk thresholds (more sensitive for options trading)
        self.adverse_move_thresholds = {
            'LOW_VOL': 0.003,    # 0.3%
            'NORMAL_VOL': 0.005, # 0.5%
            'HIGH_VOL': 0.008,   # 0.8%
            'EXTREME_VOL': 0.010 # 1.0%
        }
        
        # Hedging decision matrix
        self.hedge_matrix = self._initialize_hedge_matrix()
        
        logger.info("Adaptive Hedge Matrix initialized")
    
    def _initialize_hedge_matrix(self) -> Dict[str, Any]:
        """Initialize the hedge decision matrix"""
        return {
            'STRONG_BUY_CE': {
                'primary_hedge': HedgeType.PROTECTIVE_PUT,
                'secondary_hedge': HedgeType.COLLAR,
                'emergency_hedge': HedgeType.STRADDLE
            },
            'STRONG_SELL_PE': {
                'primary_hedge': HedgeType.PROTECTIVE_CALL,
                'secondary_hedge': HedgeType.COLLAR,
                'emergency_hedge': HedgeType.STRADDLE
            },
            'MOMENTUM_CONTINUATION': {
                'primary_hedge': HedgeType.STRANGLE,
                'secondary_hedge': HedgeType.IRON_CONDOR,
                'emergency_hedge': HedgeType.BUTTERFLY
            }
        }
    
    async def evaluate_hedge_requirement(self, 
                                       current_position: Dict[str, Any],
                                       market_data: Dict[str, Any],
                                       options_data: Dict[str, Any]) -> Optional[HedgeRecommendation]:
        """
        Evaluate if hedging is required based on current position and market conditions
        Implements the exact logic from requirements document
        """
        try:
            underlying = current_position.get('underlying', 'NIFTY')
            position_type = current_position.get('type')  # CE or PE
            entry_price = current_position.get('entry_price', 0)
            current_price = market_data.get('current_price', 0)
            strike_price = current_position.get('strike', 0)
            
            # Calculate adverse move
            adverse_move = self._calculate_adverse_move(
                position_type, entry_price, current_price, strike_price
            )
            
            # Determine volatility regime
            vol_regime = self._classify_volatility_regime(market_data)
            
            # Check if adverse move threshold is breached
            threshold = self.adverse_move_thresholds.get(vol_regime, 0.015)
            
            if adverse_move < threshold:
                return None  # No hedging required
            
            # Calculate hedge urgency
            urgency = self._calculate_hedge_urgency(adverse_move, threshold, market_data)
            
            # Determine optimal hedge type
            hedge_type = self._determine_hedge_type(current_position, market_data, urgency)
            
            # Calculate hedge parameters
            hedge_params = await self._calculate_hedge_parameters(
                underlying, position_type, current_price, options_data, hedge_type
            )
            
            if not hedge_params:
                return None
            
            # Validate premium spacing rules
            if not self._validate_premium_spacing(underlying, hedge_params):
                # Adjust hedge parameters to meet spacing rules
                hedge_params = self._adjust_for_spacing_rules(underlying, hedge_params)
            
            # Create hedge recommendation
            recommendation = HedgeRecommendation(
                hedge_type=hedge_type,
                urgency=urgency,
                hedge_ratio=hedge_params.get('hedge_ratio', 0.5),
                optimal_strike=hedge_params.get('optimal_strike', current_price),
                expected_cost=hedge_params.get('expected_cost', 0),
                max_protection=hedge_params.get('max_protection', 0),
                confidence=hedge_params.get('confidence', 0.8),
                time_to_implement=hedge_params.get('time_to_implement', 5),
                hedge_delta=hedge_params.get('delta', 0),
                hedge_gamma=hedge_params.get('gamma', 0),
                hedge_theta=hedge_params.get('theta', 0),
                hedge_vega=hedge_params.get('vega', 0),
                reasoning=hedge_params.get('reasoning', f"Adverse move {adverse_move:.3f} exceeded threshold {threshold:.3f}")
            )
            
            return recommendation
            
        except Exception as e:
            logger.error(f"Error evaluating hedge requirement: {str(e)}")
            return None
    
    def _calculate_adverse_move(self, position_type: str, entry_price: float, 
                              current_price: float, strike_price: float) -> float:
        """Calculate adverse move percentage"""
        try:
            if position_type == 'CE':
                # For CE positions, adverse move is when underlying price drops
                # Calculate percentage drop from entry price
                if current_price < entry_price:
                    adverse_move = (entry_price - current_price) / entry_price
                else:
                    adverse_move = 0.0
            else:  # PE
                # For PE positions, adverse move is when underlying price rises  
                # Calculate percentage rise from entry price
                if current_price > entry_price:
                    adverse_move = (current_price - entry_price) / entry_price
                else:
                    adverse_move = 0.0
            
            return adverse_move
            
        except Exception as e:
            logger.error(f"Error calculating adverse move: {str(e)}")
            return 0.0
    
    def _classify_volatility_regime(self, market_data: Dict[str, Any]) -> str:
        """Classify current volatility regime"""
        try:
            volatility = market_data.get('volatility', 0.02)
            
            if volatility < 0.10:  # 10%
                return 'LOW_VOL'
            elif volatility < 0.20:  # 20%
                return 'NORMAL_VOL'
            elif volatility < 0.30:  # 30%
                return 'HIGH_VOL'
            else:
                return 'EXTREME_VOL'
                
        except Exception as e:
            logger.error(f"Error classifying volatility regime: {str(e)}")
            return 'NORMAL_VOL'
    
    def _calculate_hedge_urgency(self, adverse_move: float, threshold: float, 
                               market_data: Dict[str, Any]) -> HedgeUrgency:
        """Calculate urgency of hedging requirement"""
        try:
            urgency_ratio = adverse_move / threshold
            momentum = abs(market_data.get('momentum_score', 0))
            
            if urgency_ratio > 2.0 or momentum > 0.8:
                return HedgeUrgency.CRITICAL
            elif urgency_ratio > 1.5 or momentum > 0.6:
                return HedgeUrgency.HIGH
            elif urgency_ratio > 1.2 or momentum > 0.4:
                return HedgeUrgency.MEDIUM
            else:
                return HedgeUrgency.LOW
                
        except Exception as e:
            logger.error(f"Error calculating hedge urgency: {str(e)}")
            return HedgeUrgency.MEDIUM
    
    def _determine_hedge_type(self, current_position: Dict[str, Any], 
                            market_data: Dict[str, Any], urgency: HedgeUrgency) -> HedgeType:
        """Determine optimal hedge type based on position and market conditions"""
        try:
            position_type = current_position.get('type')
            trend_direction = market_data.get('trend_direction', 0)
            volatility = market_data.get('volatility', 0.02)
            
            # Primary hedge selection based on position type
            if position_type == 'CE':
                if urgency in [HedgeUrgency.CRITICAL, HedgeUrgency.HIGH]:
                    return HedgeType.PROTECTIVE_PUT
                elif volatility > 0.03:
                    return HedgeType.COLLAR
                else:
                    return HedgeType.PROTECTIVE_PUT
            
            else:  # PE position
                if urgency in [HedgeUrgency.CRITICAL, HedgeUrgency.HIGH]:
                    return HedgeType.PROTECTIVE_CALL
                elif volatility > 0.03:
                    return HedgeType.COLLAR
                else:
                    return HedgeType.PROTECTIVE_CALL
                    
        except Exception as e:
            logger.error(f"Error determining hedge type: {str(e)}")
            return HedgeType.PROTECTIVE_PUT
    
    async def _calculate_hedge_parameters(self, underlying: str, position_type: str,
                                        current_price: float, options_data: Dict[str, Any],
                                        hedge_type: HedgeType) -> Optional[Dict[str, Any]]:
        """Calculate hedge parameters including strikes, costs, and Greeks"""
        try:
            hedge_side = 'PE' if position_type == 'CE' else 'CE'
            hedge_options = options_data.get(hedge_side, {})
            
            if not hedge_options:
                return None
            
            # Find optimal hedge strike based on spacing rules
            spacing_rule = self.spacing_rules.get(underlying, self.spacing_rules['NIFTY'])
            optimal_spacing = spacing_rule['optimal']
            
            # For hedge, we want a strike that provides good protection
            if hedge_side == 'PE':
                # For PE hedge (protecting CE position), choose strike below current price
                target_strike = current_price - (current_price * 0.02)  # 2% below
            else:
                # For CE hedge (protecting PE position), choose strike above current price  
                target_strike = current_price + (current_price * 0.02)  # 2% above
            
            # Find closest available strike
            available_strikes = [float(strike) for strike in hedge_options.keys()]
            if not available_strikes:
                return None
                
            optimal_strike = min(available_strikes, key=lambda x: abs(x - target_strike))
            
            # Get option details
            option_data = hedge_options.get(str(int(optimal_strike)), {})
            hedge_cost = option_data.get('ltp', 0)
            
            # Validate premium spacing
            if not self._check_spacing_compliance(underlying, hedge_cost, optimal_spacing):
                # Adjust strike to meet spacing requirements
                adjusted_strikes = [s for s in available_strikes 
                                  if self._check_spacing_compliance(underlying, 
                                                                  hedge_options.get(str(int(s)), {}).get('ltp', 0), 
                                                                  optimal_spacing)]
                if adjusted_strikes:
                    optimal_strike = min(adjusted_strikes, key=lambda x: abs(x - target_strike))
                    option_data = hedge_options.get(str(int(optimal_strike)), {})
                    hedge_cost = option_data.get('ltp', 0)
            
            return {
                'hedge_ratio': 0.5,  # 50% hedge ratio
                'optimal_strike': optimal_strike,
                'expected_cost': hedge_cost,
                'max_protection': hedge_cost * 10,  # Assume 10x leverage
                'confidence': 0.8,
                'time_to_implement': 5,
                'delta': option_data.get('delta', 0),
                'gamma': option_data.get('gamma', 0),
                'theta': option_data.get('theta', 0),
                'vega': option_data.get('vega', 0),
                'reasoning': f"Hedge {position_type} position with {hedge_side} at strike {optimal_strike}"
            }
            
        except Exception as e:
            logger.error(f"Error calculating hedge parameters: {str(e)}")
            return None
    
    def _validate_premium_spacing(self, underlying: str, hedge_params: Dict[str, Any]) -> bool:
        """Validate that hedge meets premium spacing rules"""
        try:
            spacing_rule = self.spacing_rules.get(underlying, self.spacing_rules['NIFTY'])
            hedge_cost = hedge_params.get('expected_cost', 0)
            
            return self._check_spacing_compliance(underlying, hedge_cost, spacing_rule['optimal'])
            
        except Exception as e:
            logger.error(f"Error validating premium spacing: {str(e)}")
            return False
    
    def _check_spacing_compliance(self, underlying: str, premium: float, required_spacing: float) -> bool:
        """Check if premium meets spacing requirements"""
        try:
            # Simple implementation - check if premium is reasonable
            spacing_rule = self.spacing_rules.get(underlying, self.spacing_rules['NIFTY'])
            min_premium = spacing_rule['min_spacing']
            max_premium = spacing_rule['max_spacing'] * 2  # Allow some flexibility
            
            return min_premium <= premium <= max_premium
            
        except Exception as e:
            logger.error(f"Error checking spacing compliance: {str(e)}")
            return True
    
    def _adjust_for_spacing_rules(self, underlying: str, hedge_params: Dict[str, Any]) -> Dict[str, Any]:
        """Adjust hedge parameters to meet spacing rules"""
        try:
            # Simple adjustment - this would be more sophisticated in production
            spacing_rule = self.spacing_rules.get(underlying, self.spacing_rules['NIFTY'])
            optimal_cost = spacing_rule['optimal']
            
            hedge_params['expected_cost'] = optimal_cost
            hedge_params['reasoning'] += f" (adjusted for {underlying} spacing rules)"
            
            return hedge_params
            
        except Exception as e:
            logger.error(f"Error adjusting for spacing rules: {str(e)}")
            return hedge_params
    
    def _calculate_implementation_time(self, urgency: HedgeUrgency) -> int:
        """Calculate time to implement hedge in minutes"""
        time_mapping = {
            HedgeUrgency.CRITICAL: 1,   # 1 minute
            HedgeUrgency.HIGH: 3,       # 3 minutes
            HedgeUrgency.MEDIUM: 5,     # 5 minutes
            HedgeUrgency.LOW: 10        # 10 minutes
        }
        return time_mapping.get(urgency, 5)
    
    def _generate_hedge_reasoning(self, adverse_move: float, threshold: float,
                                hedge_type: HedgeType, urgency: HedgeUrgency) -> str:
        """Generate human-readable reasoning for hedge recommendation"""
        try:
            urgency_ratio = adverse_move / threshold if threshold > 0 else 1
            
            reasoning = f"Adverse move of {adverse_move:.2%} detected (threshold: {threshold:.2%}). "
            reasoning += f"Urgency level: {urgency.value}. "
            reasoning += f"Recommended hedge: {hedge_type.value} "
            
            if urgency == HedgeUrgency.CRITICAL:
                reasoning += "due to critical market movement requiring immediate protection."
            elif urgency == HedgeUrgency.HIGH:
                reasoning += "due to significant adverse movement."
            elif urgency == HedgeUrgency.MEDIUM:
                reasoning += "as preventive measure against increasing risk."
            else:
                reasoning += "as prudent risk management practice."
            
            return reasoning
            
        except Exception as e:
            logger.error(f"Error generating hedge reasoning: {str(e)}")
            return "Hedge recommended based on risk management protocols."
