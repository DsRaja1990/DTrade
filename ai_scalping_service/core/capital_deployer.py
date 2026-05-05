"""
================================================================================
    INTELLIGENT CAPITAL DEPLOYER v1.0
    Focus Capital on the BEST Single Opportunity
    
    Core Principle: "Don't spread thin - CONCENTRATE on the best trade"
    
    This module implements the intelligent capital allocation strategy that:
    1. Scans all instruments for momentum opportunities
    2. Identifies the SINGLE BEST opportunity
    3. Deploys capital to ONLY that opportunity
    4. Watches for when to shift capital to a better opportunity
    5. Manages capital reallocation during momentum shifts
================================================================================

Unlike traditional portfolio allocation that spreads across instruments,
this system FOCUSES capital where momentum is strongest.

Key Philosophy:
- You can't catch all waves - catch the BEST one
- Capital sitting idle is okay - deploying badly is not
- Quick reallocation when momentum shifts to another instrument
- Preserve capital when no good opportunities exist

Target: 400%+ Monthly Returns through focused execution

Author: AI Scalping Service v6.0
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum
import json

# Import dependencies
from core.momentum_detector import (
    MomentumSignal,
    MomentumPhase,
    MomentumQuality,
    MultiInstrumentMomentumCoordinator,
    get_momentum_coordinator
)
from core.position_scaling import (
    PositionScalingManager,
    ScalingDecision,
    ScaleAction,
    PositionStage,
    get_scaling_manager
)

logger = logging.getLogger(__name__)


# ============================================================================
#                     CAPITAL DEPLOYMENT STATES
# ============================================================================

class DeploymentMode(Enum):
    """Capital deployment mode"""
    IDLE = "IDLE"                       # No deployment, watching
    FOCUSED = "FOCUSED"                 # Deployed to single instrument
    TRANSITIONING = "TRANSITIONING"     # Shifting capital between instruments
    DEFENSIVE = "DEFENSIVE"             # Reduced exposure, protecting capital


class OpportunityRating(Enum):
    """Quality rating for trading opportunities"""
    EXCEPTIONAL = "EXCEPTIONAL"  # 90+: Deploy aggressively
    STRONG = "STRONG"           # 75-90: Deploy normally
    MODERATE = "MODERATE"       # 60-75: Deploy cautiously
    WEAK = "WEAK"               # 40-60: Avoid or reduce
    NONE = "NONE"               # <40: No deployment


# Lot sizes for reference
INDEX_LOT_SIZES = {
    "NIFTY": 75,
    "BANKNIFTY": 35,
    "SENSEX": 20,
    "BANKEX": 30,
    "FINNIFTY": 65,
    "MIDCPNIFTY": 140,
}


# ============================================================================
#                     OPPORTUNITY ASSESSMENT
# ============================================================================

@dataclass
class TradingOpportunity:
    """Assessed trading opportunity for an instrument"""
    instrument: str
    timestamp: datetime
    
    # Core metrics
    opportunity_score: float  # 0-100 composite score
    rating: OpportunityRating
    
    # Momentum metrics
    momentum_score: float
    momentum_phase: MomentumPhase
    momentum_quality: MomentumQuality
    position_scale_factor: float
    
    # Risk metrics
    exhaustion_risk: float
    reversal_risk: float
    
    # Time factors
    expected_duration_minutes: int
    time_until_expiry_minutes: int = 999
    
    # Entry details
    entry_urgency: str
    recommended_quantity_percent: float  # % of capital to deploy
    
    # Reasoning
    reasoning: str
    confidence: float
    
    def to_dict(self) -> Dict:
        return {
            'instrument': self.instrument,
            'timestamp': self.timestamp.isoformat(),
            'opportunity_score': self.opportunity_score,
            'rating': self.rating.value,
            'momentum_score': self.momentum_score,
            'momentum_phase': self.momentum_phase.value,
            'momentum_quality': self.momentum_quality.value,
            'position_scale_factor': self.position_scale_factor,
            'exhaustion_risk': self.exhaustion_risk,
            'reversal_risk': self.reversal_risk,
            'expected_duration_minutes': self.expected_duration_minutes,
            'entry_urgency': self.entry_urgency,
            'recommended_quantity_percent': self.recommended_quantity_percent,
            'reasoning': self.reasoning,
            'confidence': self.confidence
        }


@dataclass
class DeploymentDecision:
    """Capital deployment decision"""
    mode: DeploymentMode
    target_instrument: Optional[str]
    
    # Capital allocation
    deploy_percent: float  # % of total capital to deploy
    deploy_amount: float   # Actual amount
    
    # Current state
    current_instrument: Optional[str]
    current_exposure: float
    
    # Actions to take
    actions: List[Dict]  # List of {instrument, action, quantity, reason}
    
    # Reasoning
    reasoning: str
    confidence: float
    urgency: str
    
    def to_dict(self) -> Dict:
        return {
            'mode': self.mode.value,
            'target_instrument': self.target_instrument,
            'deploy_percent': self.deploy_percent,
            'deploy_amount': self.deploy_amount,
            'current_instrument': self.current_instrument,
            'current_exposure': self.current_exposure,
            'actions': self.actions,
            'reasoning': self.reasoning,
            'confidence': self.confidence,
            'urgency': self.urgency
        }


# ============================================================================
#                     INTELLIGENT CAPITAL DEPLOYER
# ============================================================================

class IntelligentCapitalDeployer:
    """
    Intelligent Capital Deployment System
    
    Key Features:
    1. Single-Instrument Focus: Deploys to ONE best opportunity
    2. Dynamic Reallocation: Shifts capital when momentum shifts
    3. Opportunity Scoring: Ranks instruments by opportunity quality
    4. Risk-Adjusted Sizing: Adjusts deployment based on risk
    5. Quick Exit: Rapidly exits when conditions deteriorate
    
    Workflow:
    1. Scan all instruments for momentum
    2. Score each opportunity
    3. Select BEST opportunity (if any meet threshold)
    4. Deploy capital with scaling (probe -> confirm -> full)
    5. Monitor for exit signals or better opportunities
    6. Reallocate when needed
    """
    
    # Configuration
    MIN_OPPORTUNITY_SCORE = 50.0  # Minimum score to consider trading
    EXCEPTIONAL_THRESHOLD = 90.0
    STRONG_THRESHOLD = 75.0
    MODERATE_THRESHOLD = 60.0
    WEAK_THRESHOLD = 40.0
    
    # Reallocation triggers
    REALLOCATION_SCORE_DIFF = 20.0  # Switch if new opportunity is 20+ points better
    MINIMUM_EXPOSURE_TO_REALLOCATE = 0.1  # Min 10% exposure to trigger reallocation
    
    # Capital limits
    MAX_SINGLE_INSTRUMENT_PERCENT = 60.0  # Max 60% to single instrument
    DEFAULT_DEPLOYMENT_PERCENT = 50.0     # Default deployment target
    DEFENSIVE_EXPOSURE_PERCENT = 20.0     # Reduced exposure in defensive mode
    
    def __init__(
        self,
        total_capital: float = 500000.0,
        instruments: List[str] = None
    ):
        """
        Initialize the Intelligent Capital Deployer.
        
        Args:
            total_capital: Total trading capital
            instruments: List of instruments to monitor
        """
        self.total_capital = total_capital
        self.instruments = instruments or ["NIFTY", "BANKNIFTY", "SENSEX", "BANKEX"]
        
        # Initialize components
        self.momentum_coordinator = get_momentum_coordinator(self.instruments)
        self.scaling_manager = get_scaling_manager(total_capital)
        
        # State tracking
        self._mode: DeploymentMode = DeploymentMode.IDLE
        self._focused_instrument: Optional[str] = None
        self._current_exposure: float = 0.0
        
        # Opportunity cache
        self._opportunities: Dict[str, TradingOpportunity] = {}
        self._best_opportunity: Optional[TradingOpportunity] = None
        
        # Decision history
        self._decision_history: List[DeploymentDecision] = []
        
        # Statistics
        self._total_deployments: int = 0
        self._successful_deployments: int = 0
        self._reallocations: int = 0
        
        logger.info(f"[CapitalDeployer] Initialized with {total_capital} capital")
        logger.info(f"[CapitalDeployer] Monitoring: {self.instruments}")
    
    # ========================================================================
    #                     OPPORTUNITY ASSESSMENT
    # ========================================================================
    
    def assess_opportunity(
        self,
        instrument: str,
        momentum_signal: MomentumSignal
    ) -> TradingOpportunity:
        """
        Assess a trading opportunity for an instrument.
        
        Scoring Components:
        - Momentum Score (40%): Raw momentum strength
        - Quality Score (25%): Institutional vs retail momentum
        - Risk Score (20%): Exhaustion and reversal risk (inverted)
        - Duration Score (15%): Expected momentum duration
        """
        # Base momentum contribution
        momentum_contribution = momentum_signal.momentum_score * 0.40
        
        # Quality contribution
        quality_scores = {
            MomentumQuality.INSTITUTIONAL: 100,
            MomentumQuality.STRONG: 80,
            MomentumQuality.MODERATE: 60,
            MomentumQuality.WEAK: 30,
            MomentumQuality.CHOPPY: 0
        }
        quality_score = quality_scores.get(momentum_signal.momentum_quality, 50)
        quality_contribution = quality_score * 0.25
        
        # Risk contribution (lower risk = higher score)
        avg_risk = (momentum_signal.exhaustion_risk + momentum_signal.reversal_risk) / 2
        risk_score = 100 - avg_risk
        risk_contribution = risk_score * 0.20
        
        # Duration contribution (longer = better for scalping)
        duration = momentum_signal.expected_duration_minutes
        if duration >= 15:
            duration_score = 100
        elif duration >= 10:
            duration_score = 80
        elif duration >= 5:
            duration_score = 60
        else:
            duration_score = 40
        duration_contribution = duration_score * 0.15
        
        # Composite score
        opportunity_score = (
            momentum_contribution +
            quality_contribution +
            risk_contribution +
            duration_contribution
        )
        
        # Apply phase multiplier
        phase_multipliers = {
            MomentumPhase.ACCELERATING: 1.15,  # Boost for accelerating
            MomentumPhase.BUILDING: 1.05,
            MomentumPhase.PEAK: 0.95,         # Slight penalty for peak
            MomentumPhase.FADING: 0.70,
            MomentumPhase.DORMANT: 0.30,
            MomentumPhase.EXHAUSTION: 0.10,
            MomentumPhase.REVERSAL: 0.05
        }
        multiplier = phase_multipliers.get(momentum_signal.momentum_phase, 0.5)
        opportunity_score *= multiplier
        
        # Cap at 100
        opportunity_score = min(opportunity_score, 100)
        
        # Determine rating
        if opportunity_score >= self.EXCEPTIONAL_THRESHOLD:
            rating = OpportunityRating.EXCEPTIONAL
        elif opportunity_score >= self.STRONG_THRESHOLD:
            rating = OpportunityRating.STRONG
        elif opportunity_score >= self.MODERATE_THRESHOLD:
            rating = OpportunityRating.MODERATE
        elif opportunity_score >= self.WEAK_THRESHOLD:
            rating = OpportunityRating.WEAK
        else:
            rating = OpportunityRating.NONE
        
        # Calculate recommended deployment
        if rating == OpportunityRating.EXCEPTIONAL:
            recommended_percent = self.MAX_SINGLE_INSTRUMENT_PERCENT
        elif rating == OpportunityRating.STRONG:
            recommended_percent = self.DEFAULT_DEPLOYMENT_PERCENT
        elif rating == OpportunityRating.MODERATE:
            recommended_percent = 30.0
        else:
            recommended_percent = 0.0
        
        # Adjust by scale factor
        recommended_percent *= min(momentum_signal.position_scale_factor, 2.0) / 2.0
        
        # Generate reasoning
        reasoning = self._generate_opportunity_reasoning(
            instrument, opportunity_score, rating, momentum_signal
        )
        
        opportunity = TradingOpportunity(
            instrument=instrument,
            timestamp=datetime.now(),
            opportunity_score=round(opportunity_score, 1),
            rating=rating,
            momentum_score=momentum_signal.momentum_score,
            momentum_phase=momentum_signal.momentum_phase,
            momentum_quality=momentum_signal.momentum_quality,
            position_scale_factor=momentum_signal.position_scale_factor,
            exhaustion_risk=momentum_signal.exhaustion_risk,
            reversal_risk=momentum_signal.reversal_risk,
            expected_duration_minutes=momentum_signal.expected_duration_minutes,
            entry_urgency=momentum_signal.entry_urgency,
            recommended_quantity_percent=round(recommended_percent, 1),
            reasoning=reasoning,
            confidence=momentum_signal.signal_confidence
        )
        
        # Cache it
        self._opportunities[instrument] = opportunity
        
        return opportunity
    
    def _generate_opportunity_reasoning(
        self,
        instrument: str,
        score: float,
        rating: OpportunityRating,
        momentum: MomentumSignal
    ) -> str:
        """Generate human-readable reasoning for opportunity assessment"""
        reasons = []
        
        reasons.append(f"{instrument}: Score {score:.0f}/100 ({rating.value})")
        reasons.append(f"Momentum {momentum.momentum_phase.value} at {momentum.momentum_score:.0f}")
        reasons.append(f"Quality: {momentum.momentum_quality.value}")
        
        if momentum.exhaustion_risk > 50:
            reasons.append(f"WARNING: High exhaustion risk ({momentum.exhaustion_risk:.0f}%)")
        
        if momentum.reversal_risk > 50:
            reasons.append(f"WARNING: High reversal risk ({momentum.reversal_risk:.0f}%)")
        
        if momentum.momentum_quality == MomentumQuality.INSTITUTIONAL:
            reasons.append("INSTITUTIONAL momentum detected - prime opportunity")
        
        return " | ".join(reasons)
    
    # ========================================================================
    #                     BEST OPPORTUNITY SELECTION
    # ========================================================================
    
    def find_best_opportunity(self) -> Optional[TradingOpportunity]:
        """
        Find the single best trading opportunity across all instruments.
        
        Returns:
            Best opportunity or None if no good opportunities
        """
        if not self._opportunities:
            return None
        
        # Filter to tradeable opportunities
        tradeable = [
            opp for opp in self._opportunities.values()
            if opp.opportunity_score >= self.MIN_OPPORTUNITY_SCORE and
               opp.rating not in [OpportunityRating.WEAK, OpportunityRating.NONE] and
               opp.entry_urgency != "NO_ENTRY"
        ]
        
        if not tradeable:
            return None
        
        # Sort by opportunity score
        tradeable.sort(key=lambda x: x.opportunity_score, reverse=True)
        
        self._best_opportunity = tradeable[0]
        
        return self._best_opportunity
    
    def should_reallocate(
        self,
        current_opp: TradingOpportunity,
        new_opp: TradingOpportunity
    ) -> Tuple[bool, str]:
        """
        Determine if capital should be reallocated from current to new opportunity.
        
        Reallocation triggers:
        1. New opportunity score is significantly higher
        2. Current opportunity is degrading rapidly
        3. Current position is in profit (lock in gains)
        """
        # Must be different instruments
        if current_opp.instrument == new_opp.instrument:
            return False, "Same instrument"
        
        # Score difference check
        score_diff = new_opp.opportunity_score - current_opp.opportunity_score
        
        if score_diff >= self.REALLOCATION_SCORE_DIFF:
            return True, f"New opportunity {score_diff:.0f} points better"
        
        # Current degrading check
        if current_opp.momentum_phase in [MomentumPhase.FADING, MomentumPhase.EXHAUSTION]:
            if new_opp.momentum_phase in [MomentumPhase.BUILDING, MomentumPhase.ACCELERATING]:
                return True, "Current fading, new building"
        
        # Institutional momentum in new
        if (new_opp.momentum_quality == MomentumQuality.INSTITUTIONAL and
            current_opp.momentum_quality != MomentumQuality.INSTITUTIONAL):
            return True, "New has INSTITUTIONAL momentum"
        
        return False, "No reallocation needed"
    
    # ========================================================================
    #                     DEPLOYMENT DECISIONS
    # ========================================================================
    
    def get_deployment_decision(self) -> DeploymentDecision:
        """
        Get the next capital deployment decision.
        
        This is the MAIN METHOD that orchestrates:
        1. Scan all opportunities
        2. Find best opportunity
        3. Compare with current deployment
        4. Decide: Deploy, Hold, Reallocate, or Exit
        """
        # Find best opportunity
        best_opp = self.find_best_opportunity()
        
        # Get current position info
        current_positions = self.scaling_manager.get_all_positions()
        current_instrument = None
        current_exposure = 0.0
        
        for inst, pos_data in current_positions.items():
            if pos_data.get('current_quantity', 0) > 0:
                current_instrument = inst
                price = pos_data.get('current_price', 0)
                qty = pos_data.get('current_quantity', 0)
                current_exposure = price * qty
        
        self._current_exposure = current_exposure
        
        # Case 1: No good opportunities
        if best_opp is None:
            if current_instrument:
                # Have position but no good opportunities - consider defensive
                return self._defensive_decision(current_instrument, current_exposure)
            else:
                # No position, no opportunities - stay idle
                return self._idle_decision()
        
        # Case 2: Have position, check for reallocation or hold
        if current_instrument:
            current_opp = self._opportunities.get(current_instrument)
            
            if current_opp and best_opp.instrument != current_instrument:
                # Check if should reallocate
                should_switch, reason = self.should_reallocate(current_opp, best_opp)
                
                if should_switch:
                    return self._reallocation_decision(
                        current_instrument, current_exposure,
                        best_opp, reason
                    )
            
            # Continue with current instrument
            return self._continue_decision(current_instrument, current_opp or best_opp)
        
        # Case 3: No position, have opportunity - deploy
        return self._deploy_decision(best_opp)
    
    def _idle_decision(self) -> DeploymentDecision:
        """Return decision to stay idle"""
        decision = DeploymentDecision(
            mode=DeploymentMode.IDLE,
            target_instrument=None,
            deploy_percent=0,
            deploy_amount=0,
            current_instrument=None,
            current_exposure=0,
            actions=[],
            reasoning="No good opportunities - staying idle (capital preserved)",
            confidence=0.9,
            urgency="NORMAL"
        )
        
        self._mode = DeploymentMode.IDLE
        self._focused_instrument = None
        
        return decision
    
    def _defensive_decision(
        self,
        current_instrument: str,
        current_exposure: float
    ) -> DeploymentDecision:
        """Return decision to go defensive (reduce exposure)"""
        actions = [{
            'instrument': current_instrument,
            'action': 'REDUCE',
            'quantity_percent': 50,  # Reduce to 50%
            'reason': 'No good opportunities - reducing exposure'
        }]
        
        decision = DeploymentDecision(
            mode=DeploymentMode.DEFENSIVE,
            target_instrument=current_instrument,
            deploy_percent=self.DEFENSIVE_EXPOSURE_PERCENT,
            deploy_amount=self.total_capital * (self.DEFENSIVE_EXPOSURE_PERCENT / 100),
            current_instrument=current_instrument,
            current_exposure=current_exposure,
            actions=actions,
            reasoning="Reducing exposure - no strong opportunities detected",
            confidence=0.8,
            urgency="NORMAL"
        )
        
        self._mode = DeploymentMode.DEFENSIVE
        
        return decision
    
    def _deploy_decision(self, opportunity: TradingOpportunity) -> DeploymentDecision:
        """Return decision to deploy capital to an opportunity"""
        deploy_percent = opportunity.recommended_quantity_percent
        deploy_amount = self.total_capital * (deploy_percent / 100)
        
        # Determine entry type based on rating
        if opportunity.rating == OpportunityRating.EXCEPTIONAL:
            entry_type = "AGGRESSIVE_PROBE"  # Start at 50% instead of 25%
            urgency = "IMMEDIATE"
        elif opportunity.rating == OpportunityRating.STRONG:
            entry_type = "NORMAL_PROBE"  # Standard 25% probe
            urgency = "IMMEDIATE"
        else:
            entry_type = "CAUTIOUS_PROBE"  # 20% probe
            urgency = "NORMAL"
        
        actions = [{
            'instrument': opportunity.instrument,
            'action': 'DEPLOY',
            'entry_type': entry_type,
            'target_deploy_percent': deploy_percent,
            'reason': f'Best opportunity: {opportunity.rating.value} ({opportunity.opportunity_score:.0f}/100)'
        }]
        
        decision = DeploymentDecision(
            mode=DeploymentMode.FOCUSED,
            target_instrument=opportunity.instrument,
            deploy_percent=deploy_percent,
            deploy_amount=deploy_amount,
            current_instrument=None,
            current_exposure=0,
            actions=actions,
            reasoning=opportunity.reasoning,
            confidence=opportunity.confidence,
            urgency=urgency
        )
        
        self._mode = DeploymentMode.FOCUSED
        self._focused_instrument = opportunity.instrument
        self._total_deployments += 1
        self._decision_history.append(decision)
        
        logger.info(f"[CapitalDeployer] DEPLOY to {opportunity.instrument}: {deploy_percent:.0f}% ({deploy_amount:.0f})")
        
        return decision
    
    def _continue_decision(
        self,
        current_instrument: str,
        opportunity: TradingOpportunity
    ) -> DeploymentDecision:
        """Return decision to continue with current instrument"""
        # Get scaling decision from position manager
        position = self.scaling_manager.get_position(current_instrument)
        
        actions = []
        
        if position:
            if opportunity.momentum_phase == MomentumPhase.ACCELERATING:
                actions.append({
                    'instrument': current_instrument,
                    'action': 'SCALE_UP',
                    'reason': 'Momentum accelerating - scale up if in profit'
                })
            elif opportunity.momentum_phase == MomentumPhase.FADING:
                actions.append({
                    'instrument': current_instrument,
                    'action': 'REDUCE',
                    'quantity_percent': 30,
                    'reason': 'Momentum fading - reduce position'
                })
            else:
                actions.append({
                    'instrument': current_instrument,
                    'action': 'HOLD',
                    'reason': f'Continue position - momentum {opportunity.momentum_phase.value}'
                })
        
        decision = DeploymentDecision(
            mode=DeploymentMode.FOCUSED,
            target_instrument=current_instrument,
            deploy_percent=opportunity.recommended_quantity_percent,
            deploy_amount=self.total_capital * (opportunity.recommended_quantity_percent / 100),
            current_instrument=current_instrument,
            current_exposure=self._current_exposure,
            actions=actions,
            reasoning=f"Continue focus on {current_instrument}: {opportunity.rating.value}",
            confidence=opportunity.confidence,
            urgency="NORMAL"
        )
        
        return decision
    
    def _reallocation_decision(
        self,
        current_instrument: str,
        current_exposure: float,
        new_opportunity: TradingOpportunity,
        reason: str
    ) -> DeploymentDecision:
        """Return decision to reallocate capital to new instrument"""
        actions = [
            {
                'instrument': current_instrument,
                'action': 'EXIT',
                'reason': f'Reallocating to {new_opportunity.instrument}'
            },
            {
                'instrument': new_opportunity.instrument,
                'action': 'DEPLOY',
                'entry_type': 'REALLOCATION_PROBE',
                'target_deploy_percent': new_opportunity.recommended_quantity_percent,
                'reason': reason
            }
        ]
        
        decision = DeploymentDecision(
            mode=DeploymentMode.TRANSITIONING,
            target_instrument=new_opportunity.instrument,
            deploy_percent=new_opportunity.recommended_quantity_percent,
            deploy_amount=self.total_capital * (new_opportunity.recommended_quantity_percent / 100),
            current_instrument=current_instrument,
            current_exposure=current_exposure,
            actions=actions,
            reasoning=f"REALLOCATION: {current_instrument} -> {new_opportunity.instrument}. {reason}",
            confidence=new_opportunity.confidence,
            urgency="IMMEDIATE"
        )
        
        self._mode = DeploymentMode.TRANSITIONING
        self._focused_instrument = new_opportunity.instrument
        self._reallocations += 1
        self._decision_history.append(decision)
        
        logger.info(
            f"[CapitalDeployer] REALLOCATE: {current_instrument} -> {new_opportunity.instrument}"
        )
        
        return decision
    
    # ========================================================================
    #                     UPDATE & MONITORING
    # ========================================================================
    
    def update_instrument(
        self,
        instrument: str,
        price: float,
        volume: int,
        timestamp: datetime = None,
        **kwargs
    ) -> Optional[TradingOpportunity]:
        """
        Update an instrument with new market data and return assessed opportunity.
        """
        # Update momentum detector
        momentum_signal = self.momentum_coordinator.update(
            instrument=instrument,
            price=price,
            volume=volume,
            timestamp=timestamp,
            **kwargs
        )
        
        if momentum_signal is None:
            return None
        
        # Assess opportunity
        opportunity = self.assess_opportunity(instrument, momentum_signal)
        
        return opportunity
    
    def process_tick(
        self,
        instrument: str,
        price: float,
        volume: int,
        **kwargs
    ) -> DeploymentDecision:
        """
        Process a tick and get deployment decision.
        
        Convenience method that:
        1. Updates momentum
        2. Assesses opportunity
        3. Returns deployment decision
        """
        # Update instrument
        self.update_instrument(instrument, price, volume, **kwargs)
        
        # Get deployment decision
        return self.get_deployment_decision()
    
    # ========================================================================
    #                     PUBLIC API
    # ========================================================================
    
    def get_all_opportunities(self) -> Dict[str, Dict]:
        """Get all current opportunities"""
        return {
            inst: opp.to_dict()
            for inst, opp in self._opportunities.items()
        }
    
    def get_best_opportunity_summary(self) -> Optional[Dict]:
        """Get summary of best opportunity"""
        opp = self.find_best_opportunity()
        if opp:
            return opp.to_dict()
        return None
    
    def get_deployment_status(self) -> Dict:
        """Get current deployment status"""
        return {
            'mode': self._mode.value,
            'focused_instrument': self._focused_instrument,
            'current_exposure': self._current_exposure,
            'total_capital': self.total_capital,
            'exposure_percent': (self._current_exposure / self.total_capital * 100) if self.total_capital > 0 else 0,
            'total_deployments': self._total_deployments,
            'reallocations': self._reallocations,
            'best_opportunity': self._best_opportunity.to_dict() if self._best_opportunity else None
        }
    
    def get_statistics(self) -> Dict:
        """Get deployer statistics"""
        return {
            'total_capital': self.total_capital,
            'mode': self._mode.value,
            'focused_instrument': self._focused_instrument,
            'current_exposure': self._current_exposure,
            'total_deployments': self._total_deployments,
            'successful_deployments': self._successful_deployments,
            'reallocations': self._reallocations,
            'opportunities_tracked': len(self._opportunities),
            'decision_history_count': len(self._decision_history)
        }
    
    def update_capital(self, new_capital: float):
        """Update total capital"""
        self.total_capital = new_capital
        self.scaling_manager.update_total_capital(new_capital)
        logger.info(f"[CapitalDeployer] Capital updated to {new_capital}")
    
    def reset(self):
        """Reset the deployer"""
        self._mode = DeploymentMode.IDLE
        self._focused_instrument = None
        self._current_exposure = 0.0
        self._opportunities.clear()
        self._best_opportunity = None
        self._decision_history.clear()
        self._total_deployments = 0
        self._successful_deployments = 0
        self._reallocations = 0
        self.scaling_manager.reset()
        logger.info("[CapitalDeployer] Reset complete")


# ============================================================================
#                     SINGLETON INSTANCE
# ============================================================================

_capital_deployer: Optional[IntelligentCapitalDeployer] = None


def get_capital_deployer(
    total_capital: float = None,
    instruments: List[str] = None
) -> IntelligentCapitalDeployer:
    """Get or create the global capital deployer"""
    global _capital_deployer
    
    if _capital_deployer is None:
        capital = total_capital or 500000.0
        _capital_deployer = IntelligentCapitalDeployer(capital, instruments)
    elif total_capital:
        _capital_deployer.update_capital(total_capital)
    
    return _capital_deployer
