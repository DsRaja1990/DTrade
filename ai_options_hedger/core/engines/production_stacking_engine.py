"""
Production Architecture Implementation for Enhanced Stacking
Implements the recommended hybrid validation approach for optimal stacking decisions
"""

import logging
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

class StackingArchitectureMode(Enum):
    """Different modes for stacking decision architecture"""
    GUARDRAILS_ONLY = "guardrails_only"
    NEURAL_ONLY = "neural_only" 
    HYBRID_VALIDATION = "hybrid_validation"
    ENSEMBLE_SCORING = "ensemble_scoring"

@dataclass
class StackingDecisionResult:
    """Result from the production stacking decision system"""
    should_stack: bool
    primary_confidence: float
    secondary_confidence: Optional[float]
    consensus_score: float
    decision_method: str
    reasoning: str
    risk_score: float
    recommended_size: float

class ProductionStackingDecisionEngine:
    """
    Production-ready stacking decision engine that combines enhanced guardrails
    with optional neural engine validation for optimal decision making
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.mode = StackingArchitectureMode(config.get('stacking_mode', 'hybrid_validation'))
        
        # Component weights for ensemble scoring
        self.guardrails_weight = config.get('guardrails_weight', 0.7)
        self.neural_weight = config.get('neural_weight', 0.3)
        
        # Consensus requirements for hybrid validation
        self.require_consensus = config.get('require_consensus', True)
        self.min_confidence_threshold = config.get('min_confidence_threshold', 0.65)
        
        logger.info(f"Initialized production stacking engine in {self.mode.value} mode")
    
    async def make_stacking_decision(
        self,
        guardrails_engine,
        neural_engine,
        market_conditions,
        direction: str,
        index: str,
        current_position_size: float,
        existing_stack_level: int
    ) -> StackingDecisionResult:
        """
        Make production stacking decision using configured architecture mode
        """
        
        if self.mode == StackingArchitectureMode.GUARDRAILS_ONLY:
            return await self._guardrails_only_decision(
                guardrails_engine, market_conditions, direction, 
                index, current_position_size, existing_stack_level
            )
        
        elif self.mode == StackingArchitectureMode.NEURAL_ONLY:
            return await self._neural_only_decision(
                neural_engine, market_conditions, direction,
                index, current_position_size, existing_stack_level
            )
        
        elif self.mode == StackingArchitectureMode.HYBRID_VALIDATION:
            return await self._hybrid_validation_decision(
                guardrails_engine, neural_engine, market_conditions,
                direction, index, current_position_size, existing_stack_level
            )
        
        elif self.mode == StackingArchitectureMode.ENSEMBLE_SCORING:
            return await self._ensemble_scoring_decision(
                guardrails_engine, neural_engine, market_conditions,
                direction, index, current_position_size, existing_stack_level
            )
        
        else:
            logger.error(f"Unknown stacking mode: {self.mode}")
            return self._create_rejection_result("Unknown stacking mode")
    
    async def _guardrails_only_decision(
        self, guardrails_engine, market_conditions, direction: str,
        index: str, current_position_size: float, existing_stack_level: int
    ) -> StackingDecisionResult:
        """Enhanced Stacking Guardrails only decision"""
        
        guardrail_result = await guardrails_engine.evaluate_stacking_opportunity(
            market_conditions=market_conditions,
            direction=direction,
            index=index,
            current_position_size=current_position_size,
            existing_stack_level=existing_stack_level
        )
        
        return StackingDecisionResult(
            should_stack=guardrail_result.can_stack,
            primary_confidence=guardrail_result.confidence,
            secondary_confidence=None,
            consensus_score=guardrail_result.confidence,
            decision_method="guardrails_only",
            reasoning=guardrail_result.reasoning,
            risk_score=guardrail_result.risk_score,
            recommended_size=guardrail_result.recommended_size
        )
    
    async def _neural_only_decision(
        self, neural_engine, market_conditions, direction: str,
        index: str, current_position_size: float, existing_stack_level: int
    ) -> StackingDecisionResult:
        """Neural engine only decision"""
        
        # Convert market conditions to neural engine format
        neural_signal = await neural_engine.evaluate_stacking_opportunity(
            underlying=index,
            current_price=market_conditions.spot_price,
            volatility=(market_conditions.ce_iv + market_conditions.pe_iv) / 2,  # Average IV
            time_to_expiry=0.1,  # Weekly expiry assumption
            existing_positions=existing_stack_level
        )
        
        return StackingDecisionResult(
            should_stack=neural_signal.should_stack,
            primary_confidence=neural_signal.confidence,
            secondary_confidence=None,
            consensus_score=neural_signal.confidence,
            decision_method="neural_only",
            reasoning=neural_signal.reasoning,
            risk_score=neural_signal.risk_score,
            recommended_size=current_position_size * 0.5  # Conservative sizing
        )
    
    async def _hybrid_validation_decision(
        self, guardrails_engine, neural_engine, market_conditions,
        direction: str, index: str, current_position_size: float, existing_stack_level: int
    ) -> StackingDecisionResult:
        """Hybrid validation requiring both engines to agree"""
        
        # Get guardrails decision (primary)
        guardrail_result = await guardrails_engine.evaluate_stacking_opportunity(
            market_conditions=market_conditions,
            direction=direction,
            index=index,
            current_position_size=current_position_size,
            existing_stack_level=existing_stack_level
        )
        
        # Get neural validation (secondary)
        neural_signal = await neural_engine.evaluate_stacking_opportunity(
            underlying=index,
            current_price=market_conditions.spot_price,
            volatility=(market_conditions.ce_iv + market_conditions.pe_iv) / 2,  # Average IV
            time_to_expiry=0.1,
            existing_positions=existing_stack_level
        )
        
        # Require consensus for approval
        both_approve = guardrail_result.can_stack and neural_signal.should_stack
        min_confidence_met = (guardrail_result.confidence >= self.min_confidence_threshold and
                             neural_signal.confidence >= self.min_confidence_threshold)
        
        final_decision = both_approve and min_confidence_met if self.require_consensus else guardrail_result.can_stack
        
        # Calculate consensus score
        consensus_score = (guardrail_result.confidence + neural_signal.confidence) / 2
        
        reasoning = self._build_hybrid_reasoning(guardrail_result, neural_signal, final_decision)
        
        return StackingDecisionResult(
            should_stack=final_decision,
            primary_confidence=guardrail_result.confidence,
            secondary_confidence=neural_signal.confidence,
            consensus_score=consensus_score,
            decision_method="hybrid_validation",
            reasoning=reasoning,
            risk_score=(guardrail_result.risk_score + neural_signal.risk_score) / 2,
            recommended_size=guardrail_result.recommended_size
        )
    
    async def _ensemble_scoring_decision(
        self, guardrails_engine, neural_engine, market_conditions,
        direction: str, index: str, current_position_size: float, existing_stack_level: int
    ) -> StackingDecisionResult:
        """Ensemble scoring with weighted combination"""
        
        # Get both decisions
        guardrail_result = await guardrails_engine.evaluate_stacking_opportunity(
            market_conditions=market_conditions,
            direction=direction,
            index=index,
            current_position_size=current_position_size,
            existing_stack_level=existing_stack_level
        )
        
        neural_signal = await neural_engine.evaluate_stacking_opportunity(
            underlying=index,
            current_price=market_conditions.spot_price,
            volatility=(market_conditions.ce_iv + market_conditions.pe_iv) / 2,  # Average IV
            time_to_expiry=0.1,
            existing_positions=existing_stack_level
        )
        
        # Calculate weighted ensemble score
        guardrail_score = guardrail_result.confidence if guardrail_result.can_stack else 0
        neural_score = neural_signal.confidence if neural_signal.should_stack else 0
        
        ensemble_score = (guardrail_score * self.guardrails_weight + 
                         neural_score * self.neural_weight)
        
        final_decision = ensemble_score >= self.min_confidence_threshold
        
        reasoning = f"Ensemble: Guardrails={guardrail_score:.2f}*{self.guardrails_weight}, Neural={neural_score:.2f}*{self.neural_weight} = {ensemble_score:.2f}"
        
        return StackingDecisionResult(
            should_stack=final_decision,
            primary_confidence=guardrail_result.confidence,
            secondary_confidence=neural_signal.confidence,
            consensus_score=ensemble_score,
            decision_method="ensemble_scoring",
            reasoning=reasoning,
            risk_score=(guardrail_result.risk_score + neural_signal.risk_score) / 2,
            recommended_size=guardrail_result.recommended_size
        )
    
    def _build_hybrid_reasoning(self, guardrail_result, neural_signal, final_decision: bool) -> str:
        """Build reasoning text for hybrid validation"""
        
        guardrail_status = "APPROVE" if guardrail_result.can_stack else "REJECT"
        neural_status = "APPROVE" if neural_signal.should_stack else "REJECT"
        
        reasoning = f"Hybrid Decision: Guardrails={guardrail_status}({guardrail_result.confidence:.2f}), "
        reasoning += f"Neural={neural_status}({neural_signal.confidence:.2f}) "
        reasoning += f"→ {'APPROVED' if final_decision else 'REJECTED'}"
        
        if not final_decision:
            reasons = []
            if not guardrail_result.can_stack:
                reasons.append("guardrails rejected")
            if not neural_signal.should_stack:
                reasons.append("neural rejected") 
            if guardrail_result.confidence < self.min_confidence_threshold:
                reasons.append("low guardrails confidence")
            if neural_signal.confidence < self.min_confidence_threshold:
                reasons.append("low neural confidence")
            
            reasoning += f" ({', '.join(reasons)})"
        
        return reasoning
    
    def _create_rejection_result(self, reason: str) -> StackingDecisionResult:
        """Create a rejection result with given reason"""
        return StackingDecisionResult(
            should_stack=False,
            primary_confidence=0.0,
            secondary_confidence=None,
            consensus_score=0.0,
            decision_method="error",
            reasoning=reason,
            risk_score=1.0,
            recommended_size=0.0
        )
