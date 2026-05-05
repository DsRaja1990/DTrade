"""
Premium Risk Management Module
Advanced risk controls for high win-rate options scalping
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from datetime import datetime, time

@dataclass
class PositionSizing:
    """Position sizing recommendations"""
    base_quantity: int
    max_quantity: int
    risk_amount: float
    risk_percent: float
    confidence_adjusted: bool
    

class AdvancedRiskManager:
    """Advanced risk management system for premium scalping strategy"""
    
    def __init__(self):
        self.max_daily_drawdown = -0.02  # 2% max daily loss
        self.max_trade_risk = -0.005     # 0.5% max risk per trade
        self.max_open_risk = -0.015      # 1.5% max open risk across all trades
        
        # Regime-specific risk parameters
        self.regime_risk_factors = {
            "TRENDING": 1.0,    # Standard risk in trending markets
            "RANGING": 0.8,     # 20% risk reduction in ranging markets
            "BREAKOUT": 1.1,    # 10% risk increase in breakouts
            "REVERSAL": 0.7,    # 30% risk reduction in reversals
            "UNCERTAIN": 0.6    # 40% risk reduction in uncertain regimes
        }
        
        # Volatility-based adjustments
        self.vix_adjustments = {
            "low": 1.2,         # Increase size in low volatility
            "normal": 1.0,      # Standard size in normal volatility
            "high": 0.7,        # Reduce size in high volatility
            "extreme": 0.4      # Significantly reduce in extreme volatility
        }
        
        # Performance-based adjustments
        self.win_streak_bonuses = [0, 0.1, 0.2, 0.3, 0.4]  # Bonus based on win streak
        self.loss_streak_reductions = [0, 0.4, 0.6, 0.7]   # Reduction based on loss streak
        
        # Time-based risk adjustments
        self.time_risk_factors = {
            "opening_hour": 0.7,  # First trading hour
            "mid_session": 1.0,   # Mid-day session
            "closing_hour": 0.8   # Last trading hour
        }
        
        # Portfolio correlation limits
        self.max_sector_exposure = 0.4  # Maximum 40% risk in one sector
        self.max_correlation = 0.7     # Maximum correlation between positions
        
        # Risk distribution
        self.desired_win_rate = 0.93   # Target win rate
        self.reward_risk_ratio = 1.2   # Target reward:risk ratio
        
    def classify_vix_regime(self, vix_value: float) -> str:
        """Classify VIX regime based on Indian VIX levels"""
        if vix_value < 13:
            return "low"
        elif vix_value < 18:
            return "normal"
        elif vix_value < 25:
            return "high"
        else:
            return "extreme"
    
    def get_time_factor(self) -> float:
        """Calculate time-based risk adjustment factor"""
        current_time = datetime.now().time()
        
        # Opening hour (9:15 - 10:15)
        if time(9, 15) <= current_time <= time(10, 15):
            return self.time_risk_factors["opening_hour"]
        
        # Closing hour (14:30 - 15:30)
        elif time(14, 30) <= current_time <= time(15, 30):
            return self.time_risk_factors["closing_hour"]
        
        # Mid session
        else:
            return self.time_risk_factors["mid_session"]
    
    def calculate_position_size(self, 
                              capital: float,
                              entry_price: float,
                              stop_price: float,
                              win_streak: int,
                              loss_streak: int,
                              vix: float,
                              market_regime: str) -> PositionSizing:
        """Calculate optimal position size based on comprehensive factors"""
        
        # 1. Calculate base risk amount (% of capital)
        base_risk_pct = abs(self.max_trade_risk) 
        base_risk_amount = capital * base_risk_pct
        
        # 2. Calculate risk per unit
        risk_per_unit = abs(entry_price - stop_price)
        if risk_per_unit == 0:  # Avoid division by zero
            risk_per_unit = entry_price * 0.005  # Default to 0.5% risk
            
        # 3. Calculate base quantity
        base_quantity = int(base_risk_amount / risk_per_unit)
        
        # 4. Apply market regime adjustment
        regime_factor = self.regime_risk_factors.get(market_regime, 0.6)
        
        # 5. Apply volatility adjustment
        vix_regime = self.classify_vix_regime(vix)
        vix_factor = self.vix_adjustments.get(vix_regime, 1.0)
        
        # 6. Apply win/loss streak adjustments
        streak_factor = 1.0
        
        if win_streak > 0:
            streak_idx = min(win_streak, len(self.win_streak_bonuses) - 1)
            streak_factor += self.win_streak_bonuses[streak_idx]
        
        if loss_streak > 0:
            streak_idx = min(loss_streak, len(self.loss_streak_reductions) - 1)
            streak_factor -= self.loss_streak_reductions[streak_idx]
            
        # 7. Apply time-based factor
        time_factor = self.get_time_factor()
        
        # 8. Calculate final quantity
        adjusted_quantity = base_quantity * regime_factor * vix_factor * streak_factor * time_factor
        max_quantity = int(adjusted_quantity * 1.5)  # Maximum allowed
        final_quantity = int(max(1, adjusted_quantity))  # Ensure at least 1 contract
        
        # Return position sizing recommendation
        return PositionSizing(
            base_quantity=final_quantity,
            max_quantity=max_quantity,
            risk_amount=final_quantity * risk_per_unit,
            risk_percent=(final_quantity * risk_per_unit) / capital,
            confidence_adjusted=True
        )
    
    def validate_trade(self,
                      current_drawdown: float,
                      open_risk: float,
                      vix_value: float,
                      vix_change: float,
                      market_breadth: float) -> Tuple[bool, str]:
        """Validate if a trade should be taken given current conditions"""
        
        # 1. Check daily drawdown limit
        if current_drawdown <= self.max_daily_drawdown:
            return False, "Daily drawdown limit reached"
        
        # 2. Check open risk exposure
        if open_risk <= self.max_open_risk:
            return False, "Maximum open risk exposure reached"
        
        # 3. Check VIX conditions
        if vix_value > 30:
            return False, "VIX too high (>30)"
            
        if vix_change > 10:  # VIX up more than 10% recently
            return False, "VIX rising too rapidly"
        
        # 4. Check market breadth
        if market_breadth < -0.4:  # Negative breadth (more decliners than advancers)
            return False, "Market breadth too negative"
            
        # All checks passed
        return True, "Trade validated"
    
    def calculate_exit_adjustments(self,
                                  initial_target: float,
                                  initial_stop: float,
                                  entry_price: float,
                                  market_regime: str,
                                  vix: float,
                                  time_in_trade: float) -> Tuple[float, float]:
        """Calculate dynamic exit adjustments"""
        
        # Base exit values
        target = initial_target
        stop = initial_stop
        
        # 1. Regime-specific adjustments
        if market_regime == "TRENDING":
            # In trends, widen targets slightly
            target_adjustment = 1.1
            stop_adjustment = 0.95  # Tighter stops in trends
        elif market_regime == "RANGING":
            # In ranges, tighten targets
            target_adjustment = 0.9
            stop_adjustment = 0.9
        elif market_regime == "BREAKOUT":
            # In breakouts, widen targets significantly
            target_adjustment = 1.25
            stop_adjustment = 0.9
        elif market_regime == "REVERSAL":
            # In reversals, tighter targets
            target_adjustment = 0.85
            stop_adjustment = 0.85
        else:
            # Default/uncertain
            target_adjustment = 1.0
            stop_adjustment = 1.0
        
        # 2. VIX-based adjustments
        vix_regime = self.classify_vix_regime(vix)
        if vix_regime == "high" or vix_regime == "extreme":
            # In high volatility, tighten both targets and stops
            target_adjustment *= 0.9
            stop_adjustment *= 0.85
            
        # 3. Time-based decay
        # As trade duration increases, gradually move targets closer
        time_factor = min(1.0, time_in_trade / 60.0)  # Normalize to 1-minute scale
        
        # Apply time decay to target (bring it closer to entry as time passes)
        if time_in_trade > 30:  # After 30 seconds, start tightening
            # For target: linear decay towards entry + 25% of initial target distance
            target_decay_factor = 1.0 - (time_factor * 0.75)
            target_distance = abs(initial_target - entry_price)
            
            if initial_target > entry_price:  # Long position
                target = entry_price + (target_distance * target_decay_factor)
            else:  # Short position
                target = entry_price - (target_distance * target_decay_factor)
        
        # 4. Apply all adjustments
        # Calculate distances from entry to exit points
        target_distance = abs(target - entry_price)
        stop_distance = abs(stop - entry_price)
        
        # Apply regime and volatility adjustments to the distances
        adjusted_target_distance = target_distance * target_adjustment
        adjusted_stop_distance = stop_distance * stop_adjustment
        
        # Calculate final exit points
        if target > entry_price:  # Long position
            final_target = entry_price + adjusted_target_distance
            final_stop = entry_price - adjusted_stop_distance
        else:  # Short position
            final_target = entry_price - adjusted_target_distance
            final_stop = entry_price + adjusted_stop_distance
        
        return final_target, final_stop
    
    def calculate_scaling_conditions(self,
                                   current_price: float,
                                   entry_price: float,
                                   is_long: bool,
                                   market_regime: str,
                                   vix: float,
                                   current_profit_pct: float) -> Tuple[bool, float]:
        """Determine if position scaling is appropriate and by what factor"""
        
        # Base scaling threshold - minimum profit % needed to consider scaling
        base_threshold = 0.004  # 0.4%
        
        # 1. Adjust threshold based on regime
        if market_regime == "TRENDING":
            regime_factor = 0.8  # Lower threshold in trending market
        elif market_regime == "BREAKOUT":
            regime_factor = 0.7  # Even lower threshold in breakout
        elif market_regime == "RANGING":
            regime_factor = 1.5  # Higher threshold in ranging market
        else:
            regime_factor = 1.2  # Slightly higher in other regimes
            
        # 2. Adjust for volatility
        vix_regime = self.classify_vix_regime(vix)
        if vix_regime == "high":
            vix_factor = 1.2  # Higher threshold in high volatility
        elif vix_regime == "extreme":
            vix_factor = 1.5  # Much higher threshold in extreme volatility
        else:
            vix_factor = 1.0  # No adjustment for normal/low volatility
        
        # 3. Calculate final threshold
        scaling_threshold = base_threshold * regime_factor * vix_factor
        
        # 4. Determine if scaling condition is met
        should_scale = current_profit_pct >= scaling_threshold
        
        # 5. Calculate scaling factor (how much to add)
        # Base scaling is 30% of original position
        scaling_factor = 0.3
        
        # Adjust for strength of move - scale more for stronger moves
        if current_profit_pct > scaling_threshold * 2:
            scaling_factor = 0.5  # Stronger move = larger scaling
        
        # Limit scaling in higher volatility
        if vix_regime in ["high", "extreme"]:
            scaling_factor *= 0.7
        
        return should_scale, scaling_factor
    
    def calculate_trailing_stop(self,
                              entry_price: float,
                              current_price: float,
                              highest_price: float,
                              lowest_price: float,
                              is_long: bool,
                              atr: float,
                              market_regime: str) -> float:
        """Calculate optimal trailing stop value"""
        
        # Base trailing factor as percentage of ATR
        if market_regime == "TRENDING":
            base_trailing_factor = 2.0
        elif market_regime == "RANGING":
            base_trailing_factor = 1.5
        elif market_regime == "BREAKOUT":
            base_trailing_factor = 2.5
        else:
            base_trailing_factor = 2.0
        
        # Calculate trailing distance
        trailing_distance = atr * base_trailing_factor
        
        # Calculate trailing stop
        if is_long:
            # For long positions, trail below highest price
            trail_price = highest_price - trailing_distance
            # But never below entry price once in profit
            if highest_price > entry_price * 1.003:  # 0.3% profit buffer
                trail_price = max(trail_price, entry_price)
        else:
            # For short positions, trail above lowest price
            trail_price = lowest_price + trailing_distance
            # But never above entry price once in profit
            if lowest_price < entry_price * 0.997:  # 0.3% profit buffer
                trail_price = min(trail_price, entry_price)
        
        return trail_price
    
    def calculate_volatility_based_exits(self,
                                       entry_price: float,
                                       vix: float,
                                       option_days_to_expiry: float) -> Tuple[float, float, float]:
        """Calculate volatility-based targets and stops for options"""
        
        # Adjust for Indian VIX specifics
        norm_vix = vix / 15.0  # Normalize against typical Indian VIX of ~15
        
        # 1. Base values (optimized for Indian indices)
        base_target_pct = 0.007  # 0.7%
        base_stop_pct = 0.003    # 0.3%
        max_stop_pct = 0.01      # 1% maximum stop distance
        
        # 2. Adjust for VIX (higher VIX = wider targets and stops)
        target_pct = base_target_pct * np.sqrt(norm_vix)
        stop_pct = base_stop_pct * np.sqrt(norm_vix)
        stop_pct = min(stop_pct, max_stop_pct)  # Cap stop loss
        
        # 3. Adjust for days to expiry (closer to expiry = tighter ranges)
        # For options nearing expiry, theta decay becomes significant
        if option_days_to_expiry < 3:
            theta_factor = 0.7  # Reduce target for near-expiry options
            target_pct *= theta_factor
        
        # 4. Calculate actual price levels
        target = entry_price * (1 + target_pct)
        stop_loss = entry_price * (1 - stop_pct)
        emergency_stop = entry_price * (1 - stop_pct * 1.5)  # 50% wider emergency stop
        
        return target, stop_loss, emergency_stop
    
    def get_nifty_specific_adjustments(self, 
                                     time_of_day: datetime, 
                                     days_to_monthly_expiry: int) -> Dict[str, float]:
        """Get specific adjustments for Nifty options based on time and expiry"""
        
        adjustments = {}
        current_time = time_of_day.time()
        
        # Time-specific patterns for Nifty
        if time(9, 15) <= current_time <= time(9, 45):
            # First 30 minutes - higher volatility
            adjustments['target_factor'] = 1.2
            adjustments['stop_factor'] = 0.8
            adjustments['holding_time'] = 45  # Seconds
            
        elif time(15, 0) <= current_time <= time(15, 30):
            # Last 30 minutes - extreme care
            adjustments['target_factor'] = 0.8
            adjustments['stop_factor'] = 0.7
            adjustments['holding_time'] = 35  # Seconds
            
        elif time(12, 0) <= current_time <= time(13, 30):
            # Lunch hours - typically lower volatility
            adjustments['target_factor'] = 0.9
            adjustments['stop_factor'] = 0.9
            adjustments['holding_time'] = 60  # Seconds
            
        else:
            # Regular trading hours
            adjustments['target_factor'] = 1.0
            adjustments['stop_factor'] = 1.0
            adjustments['holding_time'] = 52  # Seconds
        
        # Expiry-specific adjustments
        if days_to_monthly_expiry == 0:  # Expiry day
            adjustments['target_factor'] *= 0.8  # Tighter targets
            adjustments['stop_factor'] *= 0.75  # Tighter stops
            adjustments['holding_time'] *= 0.8  # Shorter holds
            
        elif days_to_monthly_expiry <= 2:  # Near expiry
            adjustments['target_factor'] *= 0.9
            adjustments['stop_factor'] *= 0.85
            
        return adjustments
    
    def analyze_trade_opportunity(self,
                                signal_quality: float,
                                vix: float,
                                current_drawdown: float,
                                win_rate: float,
                                trades_today: int) -> Tuple[bool, float]:
        """Analyze if a trade opportunity should be taken and with what confidence"""
        
        # Start with signal quality as base confidence
        confidence = signal_quality
        
        # 1. Check if trading should be paused
        if current_drawdown <= self.max_daily_drawdown:
            return False, 0
            
        if trades_today >= 30:  # Hard cap on daily trades
            return False, 0
        
        # 2. VIX adjustments
        vix_regime = self.classify_vix_regime(vix)
        if vix_regime == "extreme":
            confidence *= 0.8
            if confidence < 0.9:  # Higher bar during extreme volatility
                return False, confidence
        
        # 3. Win rate momentum adjustment
        # If win rate is below target, be more selective
        if win_rate < self.desired_win_rate:
            confidence_threshold = 0.92
            confidence *= 0.95  # Slightly reduce confidence
        else:
            confidence_threshold = 0.88
            
        # 4. Drawdown-based adjustment
        # More cautious when in drawdown
        if current_drawdown < -0.005:  # -0.5%
            confidence *= 0.95
            confidence_threshold = 0.93
        
        # 5. Decision
        take_trade = confidence >= confidence_threshold
        
        return take_trade, confidence

# Create a global instance of the advanced risk manager
advanced_risk = AdvancedRiskManager()