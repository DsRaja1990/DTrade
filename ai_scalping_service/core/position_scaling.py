"""
================================================================================
    POSITION SCALING MANAGER v1.0
    Dynamic Position Sizing with Momentum-Based Scaling
    
    World-Class Scalping Position Management:
    - Start small, scale up on confirmation (like pro scalpers)
    - Deploy full capital when momentum is CONFIRMED
    - Reduce position when momentum fades
    - Exit before momentum dies
    
    Target: 400%+ Monthly Returns with Smart Capital Deployment
================================================================================

This module implements the core logic that separates amateur scalpers from pros:
"Test the waters, then dive in when conditions are right"

Scaling Philosophy:
1. PROBE: Enter with 20-25% of intended position (test position)
2. CONFIRM: If momentum builds + in profit, scale to 50%
3. ACCELERATE: If institutional momentum + strong profit, scale to 100%+
4. PROTECT: Reduce position as momentum fades
5. EXIT: Full exit on reversal or exhaustion

Author: AI Scalping Service v6.0
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum
import json

# Import momentum detector
from core.momentum_detector import (
    MomentumSignal,
    MomentumPhase,
    MomentumQuality,
    MomentumDetector,
    get_momentum_coordinator
)

logger = logging.getLogger(__name__)


# ============================================================================
#                     SCALING CONFIGURATION
# ============================================================================

class ScaleAction(Enum):
    """Position scaling actions"""
    HOLD = "HOLD"           # Keep current position
    SCALE_IN = "SCALE_IN"   # Add to position
    SCALE_OUT = "SCALE_OUT" # Reduce position
    FULL_EXIT = "FULL_EXIT" # Exit all


class PositionStage(Enum):
    """Current position stage in the scaling process"""
    NO_POSITION = "NO_POSITION"     # Not in any trade
    PROBE = "PROBE"                 # Initial test position (20-25%)
    CONFIRMED = "CONFIRMED"         # Confirmed position (50%)
    FULL = "FULL"                   # Full position (100%)
    AGGRESSIVE = "AGGRESSIVE"       # Aggressive position (150%+)
    REDUCING = "REDUCING"           # Actively reducing position
    EXITING = "EXITING"             # Exiting position


# Lot sizes for each index
INDEX_LOT_SIZES = {
    "NIFTY": 75,
    "BANKNIFTY": 35,
    "SENSEX": 20,
    "BANKEX": 30,
    "FINNIFTY": 65,
    "MIDCPNIFTY": 140,
}


@dataclass
class ScalingConfig:
    """Configuration for position scaling"""
    # Initial probe size (% of target position)
    probe_size_percent: float = 25.0
    
    # Confirmed size (% of target position)
    confirmed_size_percent: float = 50.0
    
    # Full size (% of target)
    full_size_percent: float = 100.0
    
    # Aggressive size (% of target)
    aggressive_size_percent: float = 150.0
    
    # Maximum position (% of capital)
    max_position_percent: float = 60.0
    
    # Minimum profit to scale up (%)
    min_profit_to_confirm: float = 0.3  # 0.3% profit to confirm
    min_profit_to_full: float = 0.8     # 0.8% profit for full
    min_profit_to_aggressive: float = 1.5  # 1.5% profit for aggressive
    
    # Momentum thresholds for scaling
    momentum_score_for_probe: float = 40.0
    momentum_score_for_confirm: float = 55.0
    momentum_score_for_full: float = 70.0
    momentum_score_for_aggressive: float = 85.0
    
    # Reduction triggers
    reduce_at_momentum_score: float = 45.0  # Start reducing below this
    exit_at_momentum_score: float = 30.0    # Full exit below this
    
    # Time-based constraints
    max_time_in_probe_minutes: int = 5  # Exit if no confirmation in 5 mins
    max_time_in_trade_minutes: int = 30  # Maximum time in any trade
    
    # Scale-out levels (% of position to reduce at each level)
    scale_out_levels: List[float] = field(default_factory=lambda: [30, 30, 40])


# ============================================================================
#                     POSITION STATE TRACKING
# ============================================================================

@dataclass
class ScaledPosition:
    """Tracks a scaled position through its lifecycle"""
    position_id: str
    instrument: str
    option_type: str  # CE or PE
    strike: int
    
    # Entry details
    entry_price: float = 0.0
    entry_time: datetime = None
    
    # Scaling state
    stage: PositionStage = PositionStage.NO_POSITION
    current_quantity: int = 0
    target_quantity: int = 0
    max_quantity_reached: int = 0
    
    # Scaling history
    scale_history: List[Dict] = field(default_factory=list)
    
    # P&L tracking
    avg_entry_price: float = 0.0
    current_price: float = 0.0
    unrealized_pnl: float = 0.0
    realized_pnl: float = 0.0
    pnl_percent: float = 0.0
    
    # Momentum context
    entry_momentum_score: float = 0.0
    current_momentum_score: float = 0.0
    peak_momentum_score: float = 0.0
    
    # Risk tracking
    stop_loss: float = 0.0
    trailing_stop: float = 0.0
    highest_price: float = 0.0
    lowest_price: float = 999999.0
    
    def to_dict(self) -> Dict:
        return {
            'position_id': self.position_id,
            'instrument': self.instrument,
            'option_type': self.option_type,
            'strike': self.strike,
            'stage': self.stage.value,
            'current_quantity': self.current_quantity,
            'target_quantity': self.target_quantity,
            'avg_entry_price': self.avg_entry_price,
            'current_price': self.current_price,
            'unrealized_pnl': self.unrealized_pnl,
            'realized_pnl': self.realized_pnl,
            'pnl_percent': self.pnl_percent,
            'entry_momentum_score': self.entry_momentum_score,
            'current_momentum_score': self.current_momentum_score,
            'entry_time': self.entry_time.isoformat() if self.entry_time else None,
            'scale_history': self.scale_history
        }


@dataclass 
class ScalingDecision:
    """Decision output from the Position Scaling Manager"""
    action: ScaleAction
    quantity_change: int  # Positive = add, Negative = reduce
    target_quantity: int  # Target quantity after action
    
    # Context
    current_stage: PositionStage
    new_stage: PositionStage
    
    # Reasoning
    momentum_score: float
    pnl_percent: float
    reasoning: str
    confidence: float
    
    # Urgency
    urgency: str  # IMMEDIATE, NORMAL, DELAYED
    
    # Price levels
    recommended_entry_price: float = 0.0
    recommended_stop_loss: float = 0.0
    
    def to_dict(self) -> Dict:
        return {
            'action': self.action.value,
            'quantity_change': self.quantity_change,
            'target_quantity': self.target_quantity,
            'current_stage': self.current_stage.value,
            'new_stage': self.new_stage.value,
            'momentum_score': self.momentum_score,
            'pnl_percent': self.pnl_percent,
            'reasoning': self.reasoning,
            'confidence': self.confidence,
            'urgency': self.urgency
        }


# ============================================================================
#                     POSITION SCALING MANAGER
# ============================================================================

class PositionScalingManager:
    """
    World-Class Position Scaling Manager
    
    Implements pro scalper position management:
    1. PROBE: Test the market with small position
    2. CONFIRM: Scale up when momentum + profit confirm
    3. AGGRESSIVE: Full capital deployment on institutional momentum
    4. PROTECT: Reduce position as momentum fades
    5. EXIT: Get out before reversal
    
    Key Principle: "Never deploy full capital upfront - earn the right to scale"
    """
    
    def __init__(
        self,
        total_capital: float = 500000.0,
        config: ScalingConfig = None
    ):
        """
        Initialize the Position Scaling Manager.
        
        Args:
            total_capital: Total trading capital
            config: Scaling configuration
        """
        self.total_capital = total_capital
        self.config = config or ScalingConfig()
        
        # Active positions by instrument
        self._positions: Dict[str, ScaledPosition] = {}
        
        # Locked capital (for current positions)
        self._locked_capital: float = 0.0
        
        # Available capital for new positions
        self._available_capital: float = total_capital
        
        # Statistics
        self._total_scales: int = 0
        self._successful_scales: int = 0
        self._total_trades: int = 0
        
        logger.info(f"[PositionScaling] Initialized with capital: {total_capital}")
    
    # ========================================================================
    #                     CORE SCALING LOGIC
    # ========================================================================
    
    def get_scaling_decision(
        self,
        instrument: str,
        current_price: float,
        momentum_signal: MomentumSignal,
        option_type: str = "CE",
        strike: int = 0,
        signal_type: str = None  # BUY_CALL, BUY_PUT
    ) -> ScalingDecision:
        """
        Get the next scaling decision for an instrument.
        
        This is the CORE METHOD that determines:
        - Whether to enter (and with what size)
        - Whether to scale up (and by how much)
        - Whether to reduce (and by how much)
        - Whether to exit
        
        Args:
            instrument: NIFTY, BANKNIFTY, etc.
            current_price: Current option premium price
            momentum_signal: Current momentum signal from detector
            option_type: CE or PE
            strike: Strike price
            signal_type: Trading signal (BUY_CALL, BUY_PUT)
        
        Returns:
            ScalingDecision with action and quantities
        """
        # Get or create position
        position = self._positions.get(instrument)
        
        if position is None or position.stage == PositionStage.NO_POSITION:
            # No position - check if we should enter
            return self._decide_entry(
                instrument, current_price, momentum_signal, 
                option_type, strike, signal_type
            )
        else:
            # Have position - check for scaling or exit
            return self._decide_scaling(position, current_price, momentum_signal)
    
    def _decide_entry(
        self,
        instrument: str,
        current_price: float,
        momentum: MomentumSignal,
        option_type: str,
        strike: int,
        signal_type: str
    ) -> ScalingDecision:
        """
        Decide whether to enter a new position.
        
        Entry Rules (Pro Scalper Logic):
        1. Momentum must be BUILDING or ACCELERATING
        2. Momentum quality must not be CHOPPY or WEAK
        3. Entry urgency must not be NO_ENTRY
        4. Must have available capital
        5. Start with PROBE size (25% of target)
        """
        # Check momentum conditions
        if momentum.entry_urgency == "NO_ENTRY":
            return self._no_action_decision(momentum, "Entry not recommended")
        
        if momentum.momentum_phase in [
            MomentumPhase.DORMANT, 
            MomentumPhase.EXHAUSTION,
            MomentumPhase.REVERSAL
        ]:
            return self._no_action_decision(momentum, f"Phase {momentum.momentum_phase.value} not suitable for entry")
        
        if momentum.momentum_quality in [MomentumQuality.CHOPPY, MomentumQuality.WEAK]:
            return self._no_action_decision(momentum, f"Quality {momentum.momentum_quality.value} too poor")
        
        if momentum.momentum_score < self.config.momentum_score_for_probe:
            return self._no_action_decision(momentum, f"Momentum {momentum.momentum_score:.0f} below threshold")
        
        # Calculate target position size
        target_qty = self._calculate_target_quantity(
            instrument, current_price, momentum
        )
        
        if target_qty < INDEX_LOT_SIZES.get(instrument, 1):
            return self._no_action_decision(momentum, "Insufficient capital for 1 lot")
        
        # Calculate PROBE size (25% of target)
        probe_qty = self._round_to_lots(
            target_qty * (self.config.probe_size_percent / 100),
            instrument
        )
        
        # Minimum 1 lot
        lot_size = INDEX_LOT_SIZES.get(instrument, 1)
        probe_qty = max(probe_qty, lot_size)
        
        # Determine entry stage based on momentum
        if momentum.momentum_phase == MomentumPhase.ACCELERATING and \
           momentum.momentum_quality == MomentumQuality.INSTITUTIONAL:
            # Exceptional momentum - enter with 50% directly
            probe_qty = self._round_to_lots(
                target_qty * (self.config.confirmed_size_percent / 100),
                instrument
            )
            new_stage = PositionStage.CONFIRMED
            reasoning = "INSTITUTIONAL momentum - entering at CONFIRMED size"
            urgency = "IMMEDIATE"
        else:
            new_stage = PositionStage.PROBE
            reasoning = f"PROBE entry at {self.config.probe_size_percent}% ({probe_qty} qty)"
            urgency = "NORMAL" if momentum.entry_urgency == "NORMAL" else "IMMEDIATE"
        
        # Create new position
        position_id = f"{instrument}_{datetime.now().strftime('%H%M%S')}"
        new_position = ScaledPosition(
            position_id=position_id,
            instrument=instrument,
            option_type=option_type,
            strike=strike,
            entry_price=current_price,
            entry_time=datetime.now(),
            stage=new_stage,
            current_quantity=probe_qty,
            target_quantity=target_qty,
            max_quantity_reached=probe_qty,
            avg_entry_price=current_price,
            current_price=current_price,
            entry_momentum_score=momentum.momentum_score,
            current_momentum_score=momentum.momentum_score,
            peak_momentum_score=momentum.momentum_score,
            stop_loss=current_price * 0.97,  # 3% stop initially
            trailing_stop=0,
            highest_price=current_price
        )
        
        # Record scale history
        new_position.scale_history.append({
            'action': 'ENTRY',
            'stage': new_stage.value,
            'quantity': probe_qty,
            'price': current_price,
            'momentum_score': momentum.momentum_score,
            'timestamp': datetime.now().isoformat()
        })
        
        self._positions[instrument] = new_position
        self._update_capital_allocation()
        
        return ScalingDecision(
            action=ScaleAction.SCALE_IN,
            quantity_change=probe_qty,
            target_quantity=probe_qty,
            current_stage=PositionStage.NO_POSITION,
            new_stage=new_stage,
            momentum_score=momentum.momentum_score,
            pnl_percent=0.0,
            reasoning=reasoning,
            confidence=momentum.signal_confidence,
            urgency=urgency,
            recommended_entry_price=current_price,
            recommended_stop_loss=new_position.stop_loss
        )
    
    def _decide_scaling(
        self,
        position: ScaledPosition,
        current_price: float,
        momentum: MomentumSignal
    ) -> ScalingDecision:
        """
        Decide whether to scale an existing position.
        
        Scaling Rules (Pro Scalper Logic):
        1. Scale UP when: momentum building + in profit + quality good
        2. Scale DOWN when: momentum fading or profit target hit
        3. EXIT when: momentum reversal or exhaustion or max loss
        """
        # Update position with current price
        position.current_price = current_price
        position.current_momentum_score = momentum.momentum_score
        position.peak_momentum_score = max(position.peak_momentum_score, momentum.momentum_score)
        
        # Update high/low tracking
        position.highest_price = max(position.highest_price, current_price)
        position.lowest_price = min(position.lowest_price, current_price)
        
        # Calculate P&L
        position.unrealized_pnl = (current_price - position.avg_entry_price) * position.current_quantity
        if position.avg_entry_price > 0:
            position.pnl_percent = ((current_price - position.avg_entry_price) / position.avg_entry_price) * 100
        
        # Check for EXIT conditions first (most important)
        exit_decision = self._check_exit_conditions(position, momentum)
        if exit_decision:
            return exit_decision
        
        # Check for SCALE DOWN conditions
        scale_down_decision = self._check_scale_down_conditions(position, momentum)
        if scale_down_decision:
            return scale_down_decision
        
        # Check for SCALE UP conditions
        scale_up_decision = self._check_scale_up_conditions(position, momentum)
        if scale_up_decision:
            return scale_up_decision
        
        # No action needed - hold
        return ScalingDecision(
            action=ScaleAction.HOLD,
            quantity_change=0,
            target_quantity=position.current_quantity,
            current_stage=position.stage,
            new_stage=position.stage,
            momentum_score=momentum.momentum_score,
            pnl_percent=position.pnl_percent,
            reasoning=f"HOLD - momentum {momentum.momentum_score:.0f}, P&L {position.pnl_percent:.1f}%",
            confidence=momentum.signal_confidence,
            urgency="NORMAL"
        )
    
    def _check_exit_conditions(
        self,
        position: ScaledPosition,
        momentum: MomentumSignal
    ) -> Optional[ScalingDecision]:
        """
        Check if position should be fully exited.
        
        Exit Triggers:
        1. Stop loss hit
        2. Momentum exhaustion
        3. Momentum reversal
        4. Maximum time exceeded
        5. Trailing stop hit
        """
        reasoning = None
        urgency = "NORMAL"
        
        # 1. Stop loss hit
        if position.current_price <= position.stop_loss:
            reasoning = f"STOP LOSS hit at {position.current_price:.2f} (stop: {position.stop_loss:.2f})"
            urgency = "IMMEDIATE"
        
        # 2. Trailing stop hit (if activated)
        elif position.trailing_stop > 0 and position.current_price <= position.trailing_stop:
            reasoning = f"TRAILING STOP hit at {position.current_price:.2f}"
            urgency = "IMMEDIATE"
        
        # 3. Momentum exhaustion
        elif momentum.momentum_phase == MomentumPhase.EXHAUSTION:
            reasoning = "MOMENTUM EXHAUSTION detected - exit before reversal"
            urgency = "IMMEDIATE"
        
        # 4. Momentum reversal
        elif momentum.momentum_phase == MomentumPhase.REVERSAL:
            reasoning = "MOMENTUM REVERSAL detected - exit immediately"
            urgency = "IMMEDIATE"
        
        # 5. Momentum score too low
        elif momentum.momentum_score < self.config.exit_at_momentum_score:
            reasoning = f"Momentum {momentum.momentum_score:.0f} below exit threshold {self.config.exit_at_momentum_score}"
            urgency = "IMMEDIATE"
        
        # 6. Maximum time exceeded
        elif position.entry_time:
            time_in_trade = (datetime.now() - position.entry_time).total_seconds() / 60
            if time_in_trade > self.config.max_time_in_trade_minutes:
                reasoning = f"Maximum time ({self.config.max_time_in_trade_minutes} mins) exceeded"
                urgency = "NORMAL"
        
        # 7. Probe timeout - no confirmation within time limit
        if position.stage == PositionStage.PROBE and position.entry_time:
            time_in_probe = (datetime.now() - position.entry_time).total_seconds() / 60
            if time_in_probe > self.config.max_time_in_probe_minutes:
                if position.pnl_percent < self.config.min_profit_to_confirm:
                    reasoning = f"PROBE timeout - no confirmation after {self.config.max_time_in_probe_minutes} mins"
                    urgency = "NORMAL"
        
        if reasoning:
            exit_qty = position.current_quantity
            realized_pnl = position.unrealized_pnl
            
            # Record in history
            position.scale_history.append({
                'action': 'EXIT',
                'stage': PositionStage.EXITING.value,
                'quantity': -exit_qty,
                'price': position.current_price,
                'momentum_score': momentum.momentum_score,
                'pnl': realized_pnl,
                'reason': reasoning,
                'timestamp': datetime.now().isoformat()
            })
            
            # Update position
            position.realized_pnl += realized_pnl
            position.current_quantity = 0
            position.stage = PositionStage.NO_POSITION
            
            self._update_capital_allocation()
            self._total_trades += 1
            
            return ScalingDecision(
                action=ScaleAction.FULL_EXIT,
                quantity_change=-exit_qty,
                target_quantity=0,
                current_stage=position.stage,
                new_stage=PositionStage.NO_POSITION,
                momentum_score=momentum.momentum_score,
                pnl_percent=position.pnl_percent,
                reasoning=reasoning,
                confidence=0.95,
                urgency=urgency
            )
        
        return None
    
    def _check_scale_down_conditions(
        self,
        position: ScaledPosition,
        momentum: MomentumSignal
    ) -> Optional[ScalingDecision]:
        """
        Check if position should be reduced.
        
        Scale Down Triggers:
        1. Momentum fading
        2. High exhaustion risk
        3. Profit target levels hit (partial booking)
        """
        # Already reducing
        if position.stage == PositionStage.REDUCING:
            # Continue reduction if momentum still fading
            if momentum.momentum_phase == MomentumPhase.FADING:
                return self._execute_scale_down(position, momentum, 0.3, "Continued reduction - momentum still fading")
            return None
        
        # Check for scale down conditions
        should_reduce = False
        reduction_percent = 0.3  # Default 30% reduction
        reasoning = ""
        
        # 1. Momentum fading significantly
        if momentum.momentum_phase == MomentumPhase.FADING:
            should_reduce = True
            reasoning = f"Momentum FADING (score: {momentum.momentum_score:.0f})"
        
        # 2. Momentum dropped from peak significantly
        elif position.peak_momentum_score - momentum.momentum_score > 25:
            should_reduce = True
            reasoning = f"Momentum dropped from peak {position.peak_momentum_score:.0f} to {momentum.momentum_score:.0f}"
        
        # 3. Momentum below reduction threshold
        elif momentum.momentum_score < self.config.reduce_at_momentum_score:
            should_reduce = True
            reasoning = f"Momentum {momentum.momentum_score:.0f} below threshold {self.config.reduce_at_momentum_score}"
        
        # 4. High exhaustion risk
        elif momentum.exhaustion_risk > 60:
            should_reduce = True
            reduction_percent = 0.5  # More aggressive reduction
            reasoning = f"High exhaustion risk: {momentum.exhaustion_risk:.0f}%"
        
        # 5. Exit urgency is SOON
        elif momentum.exit_urgency == "SOON":
            should_reduce = True
            reasoning = "Exit urgency: SOON"
        
        # 6. Profit target hit - book partial profits
        if position.pnl_percent >= 2.0 and not should_reduce:
            should_reduce = True
            reduction_percent = 0.3  # Book 30% profits
            reasoning = f"Profit target 2% hit - booking partial profits"
        elif position.pnl_percent >= 3.0:
            should_reduce = True
            reduction_percent = 0.3
            reasoning = f"Profit target 3% hit - booking more profits"
        
        if should_reduce and position.current_quantity > INDEX_LOT_SIZES.get(position.instrument, 1):
            return self._execute_scale_down(position, momentum, reduction_percent, reasoning)
        
        return None
    
    def _execute_scale_down(
        self,
        position: ScaledPosition,
        momentum: MomentumSignal,
        reduction_percent: float,
        reasoning: str
    ) -> ScalingDecision:
        """Execute a scale down operation"""
        lot_size = INDEX_LOT_SIZES.get(position.instrument, 1)
        
        # Calculate reduction quantity
        reduce_qty = self._round_to_lots(
            position.current_quantity * reduction_percent,
            position.instrument
        )
        
        # Keep at least 1 lot
        max_reduce = position.current_quantity - lot_size
        reduce_qty = min(reduce_qty, max_reduce)
        
        if reduce_qty <= 0:
            return None
        
        # Update position
        old_stage = position.stage
        position.current_quantity -= reduce_qty
        position.stage = PositionStage.REDUCING
        
        # Calculate realized P&L for reduced portion
        pnl_per_unit = position.current_price - position.avg_entry_price
        realized = pnl_per_unit * reduce_qty
        position.realized_pnl += realized
        
        # Record in history
        position.scale_history.append({
            'action': 'SCALE_DOWN',
            'stage': PositionStage.REDUCING.value,
            'quantity': -reduce_qty,
            'price': position.current_price,
            'momentum_score': momentum.momentum_score,
            'pnl': realized,
            'reason': reasoning,
            'timestamp': datetime.now().isoformat()
        })
        
        self._update_capital_allocation()
        
        return ScalingDecision(
            action=ScaleAction.SCALE_OUT,
            quantity_change=-reduce_qty,
            target_quantity=position.current_quantity,
            current_stage=old_stage,
            new_stage=position.stage,
            momentum_score=momentum.momentum_score,
            pnl_percent=position.pnl_percent,
            reasoning=reasoning,
            confidence=0.85,
            urgency="NORMAL"
        )
    
    def _check_scale_up_conditions(
        self,
        position: ScaledPosition,
        momentum: MomentumSignal
    ) -> Optional[ScalingDecision]:
        """
        Check if position should be scaled up.
        
        Scale Up Conditions (ALL must be true):
        1. Currently in profit
        2. Momentum is building or accelerating
        3. Momentum quality is good
        4. Haven't reached max position
        5. Stage allows scaling
        """
        # Can't scale up if reducing
        if position.stage in [PositionStage.REDUCING, PositionStage.EXITING]:
            return None
        
        # Can't scale up if at or above target
        if position.current_quantity >= position.target_quantity * 1.5:
            return None
        
        # Must be in profit to scale up
        if position.pnl_percent <= 0:
            return None
        
        # Momentum must be favorable
        if momentum.momentum_phase not in [
            MomentumPhase.BUILDING,
            MomentumPhase.ACCELERATING,
            MomentumPhase.PEAK
        ]:
            return None
        
        # Quality must be acceptable
        if momentum.momentum_quality in [MomentumQuality.CHOPPY, MomentumQuality.WEAK]:
            return None
        
        # Determine scale-up target based on current stage
        new_stage = position.stage
        scale_percent = 0
        reasoning = ""
        
        if position.stage == PositionStage.PROBE:
            # Check if ready to confirm
            if (position.pnl_percent >= self.config.min_profit_to_confirm and
                momentum.momentum_score >= self.config.momentum_score_for_confirm):
                new_stage = PositionStage.CONFIRMED
                scale_percent = self.config.confirmed_size_percent - self.config.probe_size_percent
                reasoning = f"PROBE confirmed - scaling to {self.config.confirmed_size_percent}%"
        
        elif position.stage == PositionStage.CONFIRMED:
            # Check if ready for full
            if (position.pnl_percent >= self.config.min_profit_to_full and
                momentum.momentum_score >= self.config.momentum_score_for_full):
                new_stage = PositionStage.FULL
                scale_percent = self.config.full_size_percent - self.config.confirmed_size_percent
                reasoning = f"Momentum strong - scaling to FULL ({self.config.full_size_percent}%)"
        
        elif position.stage == PositionStage.FULL:
            # Check if ready for aggressive
            if (position.pnl_percent >= self.config.min_profit_to_aggressive and
                momentum.momentum_score >= self.config.momentum_score_for_aggressive and
                momentum.momentum_quality == MomentumQuality.INSTITUTIONAL):
                new_stage = PositionStage.AGGRESSIVE
                scale_percent = self.config.aggressive_size_percent - self.config.full_size_percent
                reasoning = f"INSTITUTIONAL momentum - going AGGRESSIVE ({self.config.aggressive_size_percent}%)"
        
        if scale_percent > 0:
            return self._execute_scale_up(position, momentum, new_stage, scale_percent, reasoning)
        
        return None
    
    def _execute_scale_up(
        self,
        position: ScaledPosition,
        momentum: MomentumSignal,
        new_stage: PositionStage,
        scale_percent: float,
        reasoning: str
    ) -> ScalingDecision:
        """Execute a scale up operation"""
        # Calculate scale quantity
        scale_qty = self._round_to_lots(
            position.target_quantity * (scale_percent / 100),
            position.instrument
        )
        
        lot_size = INDEX_LOT_SIZES.get(position.instrument, 1)
        scale_qty = max(scale_qty, lot_size)
        
        # Check capital availability
        required_capital = scale_qty * position.current_price
        if required_capital > self._available_capital:
            scale_qty = self._round_to_lots(
                self._available_capital / position.current_price,
                position.instrument
            )
            if scale_qty < lot_size:
                return None  # Not enough capital
        
        # Update position
        old_stage = position.stage
        old_qty = position.current_quantity
        
        # Calculate new average entry price
        total_cost = (position.avg_entry_price * old_qty) + (position.current_price * scale_qty)
        position.avg_entry_price = total_cost / (old_qty + scale_qty)
        position.current_quantity += scale_qty
        position.max_quantity_reached = max(position.max_quantity_reached, position.current_quantity)
        position.stage = new_stage
        
        # Update trailing stop after scale up
        self._update_trailing_stop(position)
        
        # Record in history
        position.scale_history.append({
            'action': 'SCALE_UP',
            'stage': new_stage.value,
            'quantity': scale_qty,
            'price': position.current_price,
            'new_avg_price': position.avg_entry_price,
            'momentum_score': momentum.momentum_score,
            'reason': reasoning,
            'timestamp': datetime.now().isoformat()
        })
        
        self._update_capital_allocation()
        self._total_scales += 1
        self._successful_scales += 1
        
        urgency = "IMMEDIATE" if momentum.entry_urgency == "IMMEDIATE" else "NORMAL"
        
        return ScalingDecision(
            action=ScaleAction.SCALE_IN,
            quantity_change=scale_qty,
            target_quantity=position.current_quantity,
            current_stage=old_stage,
            new_stage=new_stage,
            momentum_score=momentum.momentum_score,
            pnl_percent=position.pnl_percent,
            reasoning=reasoning,
            confidence=momentum.signal_confidence,
            urgency=urgency,
            recommended_stop_loss=position.stop_loss
        )
    
    # ========================================================================
    #                     HELPER METHODS
    # ========================================================================
    
    def _calculate_target_quantity(
        self,
        instrument: str,
        premium_price: float,
        momentum: MomentumSignal
    ) -> int:
        """
        Calculate target position quantity based on capital and momentum.
        
        Uses momentum scale factor to adjust position size.
        """
        lot_size = INDEX_LOT_SIZES.get(instrument, 75)
        
        # Maximum capital for this position
        max_position_capital = self.total_capital * (self.config.max_position_percent / 100)
        
        # Adjust by momentum scale factor
        adjusted_capital = max_position_capital * min(momentum.position_scale_factor, 2.0)
        
        # Calculate lots
        capital_per_lot = premium_price * lot_size
        if capital_per_lot <= 0:
            return 0
        
        target_lots = int(adjusted_capital / capital_per_lot)
        target_qty = target_lots * lot_size
        
        return target_qty
    
    def _round_to_lots(self, quantity: float, instrument: str) -> int:
        """Round quantity to complete lots"""
        lot_size = INDEX_LOT_SIZES.get(instrument, 1)
        lots = int(quantity / lot_size)
        return lots * lot_size
    
    def _update_trailing_stop(self, position: ScaledPosition):
        """Update trailing stop based on profit"""
        if position.pnl_percent >= 1.0:
            # Activate trailing stop at break-even + small buffer
            position.trailing_stop = position.avg_entry_price * 1.005
        elif position.pnl_percent >= 2.0:
            # Trail at 50% of profit
            profit = position.current_price - position.avg_entry_price
            position.trailing_stop = position.avg_entry_price + (profit * 0.5)
        elif position.pnl_percent >= 3.0:
            # Trail at 70% of profit
            profit = position.current_price - position.avg_entry_price
            position.trailing_stop = position.avg_entry_price + (profit * 0.7)
    
    def _update_capital_allocation(self):
        """Update locked and available capital"""
        self._locked_capital = 0
        
        for position in self._positions.values():
            if position.stage != PositionStage.NO_POSITION:
                self._locked_capital += position.current_quantity * position.current_price
        
        self._available_capital = self.total_capital - self._locked_capital
    
    def _no_action_decision(
        self,
        momentum: MomentumSignal,
        reasoning: str
    ) -> ScalingDecision:
        """Return a no-action decision"""
        return ScalingDecision(
            action=ScaleAction.HOLD,
            quantity_change=0,
            target_quantity=0,
            current_stage=PositionStage.NO_POSITION,
            new_stage=PositionStage.NO_POSITION,
            momentum_score=momentum.momentum_score if momentum else 0,
            pnl_percent=0,
            reasoning=reasoning,
            confidence=0.5,
            urgency="NORMAL"
        )
    
    # ========================================================================
    #                     PUBLIC API
    # ========================================================================
    
    def get_position(self, instrument: str) -> Optional[ScaledPosition]:
        """Get current position for an instrument"""
        return self._positions.get(instrument)
    
    def get_all_positions(self) -> Dict[str, Dict]:
        """Get all active positions"""
        return {
            inst: pos.to_dict()
            for inst, pos in self._positions.items()
            if pos.stage != PositionStage.NO_POSITION
        }
    
    def get_capital_status(self) -> Dict:
        """Get capital allocation status"""
        return {
            'total_capital': self.total_capital,
            'locked_capital': self._locked_capital,
            'available_capital': self._available_capital,
            'utilization_percent': (self._locked_capital / self.total_capital * 100) if self.total_capital > 0 else 0
        }
    
    def get_statistics(self) -> Dict:
        """Get scaling statistics"""
        active_positions = sum(
            1 for p in self._positions.values() 
            if p.stage != PositionStage.NO_POSITION
        )
        
        total_unrealized = sum(
            p.unrealized_pnl for p in self._positions.values()
            if p.stage != PositionStage.NO_POSITION
        )
        
        total_realized = sum(
            p.realized_pnl for p in self._positions.values()
        )
        
        return {
            'total_capital': self.total_capital,
            'available_capital': self._available_capital,
            'active_positions': active_positions,
            'total_trades': self._total_trades,
            'total_scales': self._total_scales,
            'successful_scales': self._successful_scales,
            'unrealized_pnl': total_unrealized,
            'realized_pnl': total_realized,
            'total_pnl': total_unrealized + total_realized
        }
    
    def update_total_capital(self, new_capital: float):
        """Update total capital"""
        self.total_capital = new_capital
        self._update_capital_allocation()
        logger.info(f"[PositionScaling] Capital updated to {new_capital}")
    
    def close_position(self, instrument: str, exit_price: float = None) -> Optional[Dict]:
        """Manually close a position"""
        position = self._positions.get(instrument)
        if not position or position.stage == PositionStage.NO_POSITION:
            return None
        
        if exit_price:
            position.current_price = exit_price
        
        # Calculate final P&L
        pnl = (position.current_price - position.avg_entry_price) * position.current_quantity
        position.realized_pnl += pnl
        
        result = {
            'instrument': instrument,
            'quantity': position.current_quantity,
            'entry_price': position.avg_entry_price,
            'exit_price': position.current_price,
            'pnl': pnl,
            'pnl_percent': position.pnl_percent,
            'scale_history': position.scale_history
        }
        
        # Reset position
        position.current_quantity = 0
        position.stage = PositionStage.NO_POSITION
        
        self._update_capital_allocation()
        self._total_trades += 1
        
        logger.info(f"[PositionScaling] Closed {instrument} position with P&L: {pnl:.2f}")
        
        return result
    
    def reset(self):
        """Reset all positions and stats"""
        self._positions.clear()
        self._locked_capital = 0
        self._available_capital = self.total_capital
        self._total_scales = 0
        self._successful_scales = 0
        self._total_trades = 0
        logger.info("[PositionScaling] Reset complete")


# ============================================================================
#                     SINGLETON INSTANCE
# ============================================================================

_scaling_manager: Optional[PositionScalingManager] = None


def get_scaling_manager(
    total_capital: float = None,
    config: ScalingConfig = None
) -> PositionScalingManager:
    """Get or create the global position scaling manager"""
    global _scaling_manager
    
    if _scaling_manager is None:
        capital = total_capital or 500000.0
        _scaling_manager = PositionScalingManager(capital, config)
    elif total_capital:
        _scaling_manager.update_total_capital(total_capital)
    
    return _scaling_manager
