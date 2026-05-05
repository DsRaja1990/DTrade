"""
Premium Spacing Rules and Validation for Options Hedging
Implements the specific spacing rules for SENSEX/NIFTY as per requirements
"""

import logging
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
from enum import Enum
import numpy as np

logger = logging.getLogger(__name__)

class IndexType(Enum):
    """Supported index types"""
    SENSEX = "SENSEX"
    BANKEX = "BANKEX"
    NIFTY = "NIFTY"
    BANKNIFTY = "BANKNIFTY"
    FINNIFTY = "FINNIFTY"

@dataclass
class SpacingRule:
    """Premium spacing rule for an index"""
    index: IndexType
    min_spacing: float
    max_spacing: float
    optimal_spacing: float
    description: str

class PremiumSpacingValidator:
    """
    Validates premium spacing rules for options hedging as per specification:
    - Sensex: ₹80-₹100 spacing
    - Nifty: ≤₹50 spacing
    """
    
    def __init__(self):
        # Define spacing rules as per requirements
        self.spacing_rules = {
            IndexType.SENSEX: SpacingRule(
                index=IndexType.SENSEX,
                min_spacing=80.0,
                max_spacing=100.0,
                optimal_spacing=90.0,
                description="Sensex: Always hedge with leg that's ₹80-₹100 lower in premium"
            ),
            IndexType.BANKEX: SpacingRule(
                index=IndexType.BANKEX,
                min_spacing=80.0,
                max_spacing=100.0,
                optimal_spacing=90.0,
                description="Bankex: Same rules as Sensex"
            ),
            IndexType.NIFTY: SpacingRule(
                index=IndexType.NIFTY,
                min_spacing=25.0,
                max_spacing=50.0,
                optimal_spacing=40.0,
                description="Nifty: Hedge with leg ≤₹50 lower in premium"
            ),
            IndexType.BANKNIFTY: SpacingRule(
                index=IndexType.BANKNIFTY,
                min_spacing=25.0,
                max_spacing=50.0,
                optimal_spacing=40.0,
                description="Bank Nifty: Same rules as Nifty"
            ),
            IndexType.FINNIFTY: SpacingRule(
                index=IndexType.FINNIFTY,
                min_spacing=25.0,
                max_spacing=50.0,
                optimal_spacing=40.0,
                description="Fin Nifty: Same rules as Nifty"
            )
        }
        
        logger.info("Premium Spacing Validator initialized with institutional rules")

    def validate_hedging_spacing(self, 
                                index: str, 
                                ce_premium: float, 
                                pe_premium: float) -> Dict[str, Any]:
        """
        Validate if the premium spacing is suitable for hedging
        
        Args:
            index: Index name (SENSEX, NIFTY, etc.)
            ce_premium: Call option premium
            pe_premium: Put option premium
            
        Returns:
            Validation result with details
        """
        try:
            # Convert string to IndexType
            index_type = self._get_index_type(index)
            if not index_type:
                return {
                    'is_valid': False,
                    'reason': f'Unsupported index: {index}',
                    'spacing': 0,
                    'rule': None
                }
            
            # Calculate actual spacing
            spacing = abs(ce_premium - pe_premium)
            rule = self.spacing_rules[index_type]
            
            # Check if spacing is within valid range
            is_valid = rule.min_spacing <= spacing <= rule.max_spacing
            
            # Additional validation for direction
            hedge_recommendation = self._get_hedge_recommendation(
                index_type, ce_premium, pe_premium, spacing
            )
            
            return {
                'is_valid': is_valid,
                'spacing': spacing,
                'rule': rule,
                'optimal_spacing': rule.optimal_spacing,
                'spacing_deviation': abs(spacing - rule.optimal_spacing),
                'hedge_recommendation': hedge_recommendation,
                'quality_score': self._calculate_quality_score(rule, spacing),
                'reason': self._get_validation_reason(rule, spacing, is_valid)
            }
            
        except Exception as e:
            logger.error(f"Error validating spacing: {str(e)}")
            return {
                'is_valid': False,
                'reason': f'Validation error: {str(e)}',
                'spacing': 0,
                'rule': None
            }

    def get_optimal_hedge_leg(self, 
                            index: str, 
                            ce_premium: float, 
                            pe_premium: float,
                            current_position_type: str) -> Dict[str, Any]:
        """
        Determine which leg to use for hedging based on spacing rules
        
        Args:
            index: Index name
            ce_premium: Call option premium
            pe_premium: Put option premium
            current_position_type: Current position type (CE or PE)
            
        Returns:
            Optimal hedge leg recommendation
        """
        try:
            index_type = self._get_index_type(index)
            if not index_type:
                return {'hedge_leg': None, 'reason': f'Unsupported index: {index}'}
            
            rule = self.spacing_rules[index_type]
            spacing = abs(ce_premium - pe_premium)
            
            # Determine hedge leg based on current position and spacing rules
            if current_position_type == 'CE':
                # Currently long CE, need PE hedge
                hedge_leg = 'PE'
                hedge_premium = pe_premium
                primary_premium = ce_premium
            else:
                # Currently long PE, need CE hedge
                hedge_leg = 'CE'
                hedge_premium = ce_premium
                primary_premium = pe_premium
            
            # Check if hedge premium is appropriately lower
            premium_difference = primary_premium - hedge_premium
            is_hedge_cheaper = premium_difference > 0
            
            # Validate according to rules
            validation = self.validate_hedging_spacing(index, ce_premium, pe_premium)
            
            # Calculate hedge quality
            hedge_quality = self._calculate_hedge_quality(
                rule, spacing, premium_difference, is_hedge_cheaper
            )
            
            return {
                'hedge_leg': hedge_leg,
                'hedge_premium': hedge_premium,
                'primary_premium': primary_premium,
                'premium_difference': premium_difference,
                'is_hedge_cheaper': is_hedge_cheaper,
                'spacing_valid': validation['is_valid'],
                'hedge_quality': hedge_quality,
                'recommendation': self._get_hedge_action_recommendation(hedge_quality),
                'rule_description': rule.description
            }
            
        except Exception as e:
            logger.error(f"Error determining hedge leg: {str(e)}")
            return {'hedge_leg': None, 'reason': f'Error: {str(e)}'}

    def validate_stacking_conditions(self, 
                                   index: str,
                                   existing_positions: List[Dict[str, Any]],
                                   new_premium: float,
                                   direction: str) -> Dict[str, Any]:
        """
        Validate if conditions are suitable for stacking additional legs
        
        Args:
            index: Index name
            existing_positions: List of existing positions
            new_premium: Premium of new leg to be added
            direction: Direction for stacking (CE or PE)
            
        Returns:
            Stacking validation result
        """
        try:
            index_type = self._get_index_type(index)
            if not index_type:
                return {'is_valid': False, 'reason': f'Unsupported index: {index}'}
            
            # Count existing legs by direction
            ce_legs = len([p for p in existing_positions if p.get('option_type') == 'CE'])
            pe_legs = len([p for p in existing_positions if p.get('option_type') == 'PE'])
            
            # Maximum legs per direction (as per requirements)
            max_legs = 3
            
            if direction == 'CE' and ce_legs >= max_legs:
                return {'is_valid': False, 'reason': f'Maximum CE legs ({max_legs}) reached'}
            
            if direction == 'PE' and pe_legs >= max_legs:
                return {'is_valid': False, 'reason': f'Maximum PE legs ({max_legs}) reached'}
            
            # Check premium progression for stacking
            same_direction_positions = [
                p for p in existing_positions 
                if p.get('option_type') == direction
            ]
            
            stacking_quality = self._assess_stacking_quality(
                same_direction_positions, new_premium, direction
            )
            
            return {
                'is_valid': True,
                'current_ce_legs': ce_legs,
                'current_pe_legs': pe_legs,
                'max_legs': max_legs,
                'stacking_direction': direction,
                'stacking_quality': stacking_quality,
                'recommendation': 'PROCEED' if stacking_quality > 0.6 else 'CAUTION',
                'reason': f'Stacking {direction} leg - Quality: {stacking_quality:.2f}'
            }
            
        except Exception as e:
            logger.error(f"Error validating stacking: {str(e)}")
            return {'is_valid': False, 'reason': f'Error: {str(e)}'}

    def calculate_risk_adjusted_spacing(self, 
                                      index: str,
                                      ce_premium: float,
                                      pe_premium: float,
                                      volatility: float,
                                      time_to_expiry: int) -> Dict[str, Any]:
        """
        Calculate risk-adjusted optimal spacing considering volatility and time decay
        """
        try:
            index_type = self._get_index_type(index)
            if not index_type:
                return {'optimal_spacing': 0, 'reason': f'Unsupported index: {index}'}
            
            rule = self.spacing_rules[index_type]
            base_spacing = rule.optimal_spacing
            
            # Adjust for volatility (higher vol = wider spacing tolerance)
            vol_adjustment = 1 + (volatility - 0.2) * 0.5  # Baseline 20% vol
            vol_adjustment = max(0.5, min(vol_adjustment, 2.0))  # Cap adjustments
            
            # Adjust for time decay (less time = tighter spacing)
            time_factor = min(time_to_expiry / 30, 1.0)  # Normalize to 30 days
            time_adjustment = 0.7 + (time_factor * 0.3)  # 70%-100% range
            
            # Calculate adjusted spacing
            adjusted_spacing = base_spacing * vol_adjustment * time_adjustment
            
            # Ensure within rule bounds
            adjusted_spacing = max(rule.min_spacing, min(adjusted_spacing, rule.max_spacing))
            
            return {
                'base_spacing': base_spacing,
                'volatility_adjustment': vol_adjustment,
                'time_adjustment': time_adjustment,
                'adjusted_spacing': adjusted_spacing,
                'current_spacing': abs(ce_premium - pe_premium),
                'spacing_quality': self._calculate_quality_score(rule, adjusted_spacing),
                'recommendation': self._get_spacing_recommendation(rule, adjusted_spacing)
            }
            
        except Exception as e:
            logger.error(f"Error calculating risk-adjusted spacing: {str(e)}")
            return {'optimal_spacing': 0, 'reason': f'Error: {str(e)}'}

    # === PRIVATE HELPER METHODS ===
    
    def _get_index_type(self, index: str) -> Optional[IndexType]:
        """Convert string index name to IndexType enum"""
        try:
            return IndexType(index.upper())
        except ValueError:
            # Try partial matching
            index_upper = index.upper()
            for idx_type in IndexType:
                if idx_type.value in index_upper or index_upper in idx_type.value:
                    return idx_type
            return None

    def _get_hedge_recommendation(self, 
                                index_type: IndexType, 
                                ce_premium: float, 
                                pe_premium: float,
                                spacing: float) -> Dict[str, Any]:
        """Get specific hedge recommendation based on premiums"""
        rule = self.spacing_rules[index_type]
        
        # Determine which option is cheaper (hedge candidate)
        if ce_premium < pe_premium:
            cheaper_option = 'CE'
            premium_diff = pe_premium - ce_premium
        else:
            cheaper_option = 'PE'
            premium_diff = ce_premium - pe_premium
        
        # Check if difference meets rule requirements
        meets_requirement = rule.min_spacing <= premium_diff <= rule.max_spacing
        
        return {
            'cheaper_option': cheaper_option,
            'premium_difference': premium_diff,
            'meets_requirement': meets_requirement,
            'recommended_hedge': cheaper_option if meets_requirement else None,
            'rule_min': rule.min_spacing,
            'rule_max': rule.max_spacing
        }

    def _calculate_quality_score(self, rule: SpacingRule, actual_spacing: float) -> float:
        """Calculate quality score for spacing (0-1 scale)"""
        try:
            # Distance from optimal spacing
            optimal_distance = abs(actual_spacing - rule.optimal_spacing)
            max_distance = max(
                rule.optimal_spacing - rule.min_spacing,
                rule.max_spacing - rule.optimal_spacing
            )
            
            if max_distance == 0:
                return 1.0
            
            # Quality decreases with distance from optimal
            quality = 1.0 - (optimal_distance / max_distance)
            return max(0.0, min(1.0, quality))
            
        except Exception:
            return 0.0

    def _get_validation_reason(self, rule: SpacingRule, spacing: float, is_valid: bool) -> str:
        """Get human-readable validation reason"""
        if is_valid:
            return f"Spacing ₹{spacing:.0f} is within {rule.index.value} rule (₹{rule.min_spacing}-₹{rule.max_spacing})"
        else:
            if spacing < rule.min_spacing:
                return f"Spacing ₹{spacing:.0f} is below minimum ₹{rule.min_spacing} for {rule.index.value}"
            else:
                return f"Spacing ₹{spacing:.0f} exceeds maximum ₹{rule.max_spacing} for {rule.index.value}"

    def _calculate_hedge_quality(self, 
                               rule: SpacingRule, 
                               spacing: float, 
                               premium_diff: float, 
                               is_hedge_cheaper: bool) -> float:
        """Calculate overall hedge quality score"""
        try:
            # Base score from spacing quality
            spacing_score = self._calculate_quality_score(rule, spacing)
            
            # Penalty if hedge is not cheaper
            cheapness_score = 1.0 if is_hedge_cheaper else 0.3
            
            # Premium difference score (closer to optimal is better)
            if premium_diff > 0:
                diff_score = min(premium_diff / rule.optimal_spacing, 1.0)
            else:
                diff_score = 0.0
            
            # Weighted combination
            hedge_quality = (spacing_score * 0.5 + cheapness_score * 0.3 + diff_score * 0.2)
            
            return max(0.0, min(1.0, hedge_quality))
            
        except Exception:
            return 0.0

    def _get_hedge_action_recommendation(self, hedge_quality: float) -> str:
        """Get action recommendation based on hedge quality"""
        if hedge_quality >= 0.8:
            return "STRONG_HEDGE"
        elif hedge_quality >= 0.6:
            return "HEDGE"
        elif hedge_quality >= 0.4:
            return "WEAK_HEDGE"
        else:
            return "NO_HEDGE"

    def _assess_stacking_quality(self, 
                               existing_positions: List[Dict[str, Any]], 
                               new_premium: float, 
                               direction: str) -> float:
        """Assess quality of stacking additional leg"""
        try:
            if not existing_positions:
                return 0.8  # First leg is generally good
            
            # Check premium progression
            existing_premiums = [p.get('entry_price', 0) for p in existing_positions]
            avg_existing_premium = np.mean(existing_premiums)
            
            # Prefer adding cheaper legs
            if new_premium < avg_existing_premium:
                premium_score = 0.8
            elif new_premium <= avg_existing_premium * 1.1:  # Within 10%
                premium_score = 0.6
            else:
                premium_score = 0.3
            
            # Consider number of existing legs
            leg_count = len(existing_positions)
            if leg_count == 0:
                count_score = 1.0
            elif leg_count == 1:
                count_score = 0.8
            elif leg_count == 2:
                count_score = 0.5
            else:
                count_score = 0.2
            
            # Combined stacking quality
            stacking_quality = (premium_score * 0.6 + count_score * 0.4)
            
            return max(0.0, min(1.0, stacking_quality))
            
        except Exception:
            return 0.0

    def _get_spacing_recommendation(self, rule: SpacingRule, spacing: float) -> str:
        """Get spacing-based recommendation"""
        quality = self._calculate_quality_score(rule, spacing)
        
        if quality >= 0.9:
            return "EXCELLENT"
        elif quality >= 0.7:
            return "GOOD"
        elif quality >= 0.5:
            return "ACCEPTABLE"
        elif quality >= 0.3:
            return "POOR"
        else:
            return "AVOID"

    # === PUBLIC UTILITY METHODS ===
    
    def get_all_spacing_rules(self) -> Dict[str, SpacingRule]:
        """Get all defined spacing rules"""
        return {idx.value: rule for idx, rule in self.spacing_rules.items()}

    def get_rule_for_index(self, index: str) -> Optional[SpacingRule]:
        """Get spacing rule for specific index"""
        index_type = self._get_index_type(index)
        return self.spacing_rules.get(index_type) if index_type else None

    def validate_batch_spacing(self, 
                             spacing_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Validate spacing for multiple option pairs"""
        results = []
        
        for data in spacing_data:
            result = self.validate_hedging_spacing(
                data.get('index', ''),
                data.get('ce_premium', 0),
                data.get('pe_premium', 0)
            )
            result['input_data'] = data
            results.append(result)
        
        return results

    def get_market_making_spreads(self, index: str) -> Dict[str, float]:
        """Get recommended bid-ask spreads for market making"""
        index_type = self._get_index_type(index)
        if not index_type:
            return {}
        
        rule = self.spacing_rules[index_type]
        
        # Market making spreads based on liquidity characteristics
        if index_type in [IndexType.SENSEX, IndexType.BANKEX]:
            # Lower liquidity, wider spreads
            return {
                'bid_spread': rule.optimal_spacing * 0.02,  # 2% of spacing
                'ask_spread': rule.optimal_spacing * 0.02,
                'min_spread': 2.0,
                'max_spread': 10.0
            }
        else:
            # Higher liquidity, tighter spreads
            return {
                'bid_spread': rule.optimal_spacing * 0.01,  # 1% of spacing
                'ask_spread': rule.optimal_spacing * 0.01,
                'min_spread': 1.0,
                'max_spread': 5.0
            }

    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get validator performance metrics"""
        return {
            'supported_indices': list(self.spacing_rules.keys()),
            'total_rules': len(self.spacing_rules),
            'rule_coverage': {
                'sensex_group': ['SENSEX', 'BANKEX'],
                'nifty_group': ['NIFTY', 'BANKNIFTY', 'FINNIFTY']
            },
            'spacing_ranges': {
                idx.value: {
                    'min': rule.min_spacing,
                    'max': rule.max_spacing,
                    'optimal': rule.optimal_spacing
                }
                for idx, rule in self.spacing_rules.items()
            }
        }


# === TESTING AND VALIDATION ===

def test_spacing_validator():
    """Test the premium spacing validator"""
    validator = PremiumSpacingValidator()
    
    # Test cases
    test_cases = [
        # Sensex cases
        {'index': 'SENSEX', 'ce_premium': 150, 'pe_premium': 60},  # 90 spacing - optimal
        {'index': 'SENSEX', 'ce_premium': 140, 'pe_premium': 70},  # 70 spacing - below min
        {'index': 'SENSEX', 'ce_premium': 180, 'pe_premium': 70},  # 110 spacing - above max
        
        # Nifty cases
        {'index': 'NIFTY', 'ce_premium': 80, 'pe_premium': 40},    # 40 spacing - optimal
        {'index': 'NIFTY', 'ce_premium': 70, 'pe_premium': 65},    # 5 spacing - too low
        {'index': 'NIFTY', 'ce_premium': 100, 'pe_premium': 40},   # 60 spacing - above max
    ]
    
    print("Testing Premium Spacing Validator:")
    print("=" * 50)
    
    for i, case in enumerate(test_cases, 1):
        result = validator.validate_hedging_spacing(
            case['index'], case['ce_premium'], case['pe_premium']
        )
        
        print(f"Test {i}: {case['index']}")
        print(f"  CE: ₹{case['ce_premium']}, PE: ₹{case['pe_premium']}")
        print(f"  Spacing: ₹{result['spacing']:.0f}")
        print(f"  Valid: {result['is_valid']}")
        print(f"  Quality: {result.get('quality_score', 0):.2f}")
        print(f"  Reason: {result['reason']}")
        print()

if __name__ == "__main__":
    test_spacing_validator()
