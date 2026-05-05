"""
╔═══════════════════════════════════════════════════════════════════════════════════════════════════╗
║                    AI INTEGRATION MODULE - INDEX OPTIONS TRADING                                    ║
║                         Ultra AI Components for 99%+ Win Rate                                       ║
╚═══════════════════════════════════════════════════════════════════════════════════════════════════╝

This module provides:
1. EnhancedGeminiClient - Basic Gemini Trade Service integration
2. UltraAIOptionsValidator - Full 3-Tier AI validation pipeline
3. NeuralEnsembleValidator - Multi-model consensus validation
4. UltraAIStrategyIntegrator - Combined validation for maximum accuracy
"""

# Basic Gemini Client
from .enhanced_gemini_client import EnhancedGeminiClient

# Ultra AI Validator (Full 3-Tier Pipeline)
from .ultra_ai_options_validator import (
    UltraAIOptionsValidator,
    UltraAIEnsembleValidator,
    AIValidationResult,
    AIConfidenceLevel,
    TradeDecision,
    TradeOutcome
)

# Neural Ensemble Validator (Multi-Model Consensus)
from .neural_ensemble_validator import (
    NeuralEnsembleValidator,
    EnsembleResult,
    ConsensusLevel,
    ModelPrediction
)

# Ultra AI Strategy Integrator (Combined Validation)
from .ultra_ai_strategy_integrator import (
    UltraAIStrategyIntegrator,
    UltraValidationResult,
    FinalTradeDecision
)

__all__ = [
    # Basic Client
    'EnhancedGeminiClient',
    
    # Ultra AI Validator
    'UltraAIOptionsValidator',
    'UltraAIEnsembleValidator',
    'AIValidationResult',
    'AIConfidenceLevel',
    'TradeDecision',
    'TradeOutcome',
    
    # Neural Ensemble
    'NeuralEnsembleValidator',
    'EnsembleResult',
    'ConsensusLevel',
    'ModelPrediction',
    
    # Strategy Integrator
    'UltraAIStrategyIntegrator',
    'UltraValidationResult',
    'FinalTradeDecision'
]

__version__ = '2.0.0'
__author__ = 'AI Options Hedger System'
