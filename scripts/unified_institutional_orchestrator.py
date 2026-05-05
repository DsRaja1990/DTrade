"""
================================================================================
    UNIFIED INSTITUTIONAL ALGORITHM ORCHESTRATOR
    Combines all three institutional engines for maximum alpha
    
    Engines Integrated:
    1. Scalping Engine (SMC, Volume Profile, Gamma Exposure)
    2. Greeks Hedging Engine (Delta, Gamma, Vanna-Volga)
    3. Alpha Engine (Statistical Arbitrage, Multi-Factor, Order Flow)
    
    Usage:
    - Import and instantiate UnifiedInstitutionalOrchestrator
    - Feed market data continuously
    - Call generate_unified_signal() for combined analysis
    - Use hedge_portfolio() for risk management
================================================================================
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


# ============================================================================
# DATA CLASSES
# ============================================================================

class UnifiedDirection(Enum):
    LONG = "LONG"
    SHORT = "SHORT"
    NEUTRAL = "NEUTRAL"


class SignalConfidence(Enum):
    LEGENDARY = "LEGENDARY"  # 90%+ confluence
    ULTRA = "ULTRA"          # 80-89% confluence
    STRONG = "STRONG"        # 70-79% confluence
    MODERATE = "MODERATE"    # 60-69% confluence
    WEAK = "WEAK"           # Below 60%


@dataclass
class UnifiedSignal:
    """Combined signal from all institutional engines"""
    timestamp: datetime
    instrument: str
    direction: UnifiedDirection
    
    # Confluence scores
    unified_score: float  # 0-100
    scalping_score: float
    greeks_score: float
    alpha_score: float
    
    # Confidence level
    confidence: SignalConfidence
    
    # Trade parameters
    entry_price: float
    stop_loss: float
    targets: List[float] = field(default_factory=list)
    recommended_position_pct: float = 0.0
    
    # Risk metrics (from Greeks engine)
    delta_exposure: float = 0.0
    gamma_exposure: float = 0.0
    vega_exposure: float = 0.0
    
    # Market context (from Alpha engine)
    market_regime: str = "UNKNOWN"
    
    # Analysis breakdown
    smc_analysis: Dict = field(default_factory=dict)
    volume_profile: Dict = field(default_factory=dict)
    gamma_analysis: Dict = field(default_factory=dict)
    factor_scores: Dict = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        return {
            'timestamp': self.timestamp.isoformat(),
            'instrument': self.instrument,
            'direction': self.direction.value,
            'unified_score': round(self.unified_score, 2),
            'scalping_score': round(self.scalping_score, 2),
            'greeks_score': round(self.greeks_score, 2),
            'alpha_score': round(self.alpha_score, 2),
            'confidence': self.confidence.value,
            'entry_price': self.entry_price,
            'stop_loss': self.stop_loss,
            'targets': self.targets,
            'recommended_position_pct': round(self.recommended_position_pct, 2),
            'delta_exposure': round(self.delta_exposure, 2),
            'gamma_exposure': round(self.gamma_exposure, 4),
            'vega_exposure': round(self.vega_exposure, 2),
            'market_regime': self.market_regime,
            'smc_analysis': self.smc_analysis,
            'volume_profile': self.volume_profile,
            'gamma_analysis': self.gamma_analysis,
            'factor_scores': self.factor_scores
        }


# ============================================================================
# UNIFIED ORCHESTRATOR
# ============================================================================

class UnifiedInstitutionalOrchestrator:
    """
    Orchestrates all three institutional algorithm engines.
    Provides unified signal generation and risk management.
    
    Algorithm Execution Order:
    1. Regime Detection (Alpha Engine) - Determines market state
    2. SMC + Volume Profile (Scalping Engine) - Identifies setups
    3. Greeks Calculation (Greeks Engine) - Risk assessment
    4. Factor Signals (Alpha Engine) - Alpha generation
    5. Signal Confluence - Combines all signals
    6. Position Sizing - Greeks-adjusted sizing
    """
    
    def __init__(self, config: Dict = None):
        self.config = config or {}
        
        # Engine instances (lazy loaded)
        self._scalping_engine = None
        self._greeks_engine = None
        self._alpha_engine = None
        
        # Weights for signal combination
        self._weights = {
            'scalping': self.config.get('scalping_weight', 0.40),
            'greeks': self.config.get('greeks_weight', 0.25),
            'alpha': self.config.get('alpha_weight', 0.35)
        }
        
        # Risk limits
        self._max_delta = self.config.get('max_delta', 2000)
        self._max_gamma = self.config.get('max_gamma', 100)
        self._min_confluence = self.config.get('min_confluence', 65)
        
        self._initialized = False
        logger.info("UnifiedInstitutionalOrchestrator created (not yet initialized)")
    
    async def initialize(self) -> bool:
        """Initialize all three engines"""
        try:
            logger.info("=" * 70)
            logger.info("INITIALIZING UNIFIED INSTITUTIONAL ORCHESTRATOR")
            logger.info("=" * 70)
            
            # 1. Initialize Scalping Engine
            try:
                from ai_scalping_service.core.institutional_scalping_engine import (
                    create_institutional_engine
                )
                self._scalping_engine = create_institutional_engine({
                    'min_confluence_score': 60,
                    'max_signals_per_hour': 10
                })
                logger.info("  ✅ Scalping Engine (SMC, Volume Profile, Gamma)")
            except ImportError as e:
                logger.warning(f"  ⚠️ Scalping Engine not available: {e}")
            
            # 2. Initialize Greeks Engine
            try:
                from ai_options_hedger.core.engines.institutional_greeks_engine import (
                    create_hedging_engine
                )
                self._greeks_engine = create_hedging_engine({
                    'max_delta': self._max_delta,
                    'max_gamma': self._max_gamma,
                    'max_vega': 500
                })
                logger.info("  ✅ Greeks Engine (Delta, Gamma, Vanna-Volga)")
            except ImportError as e:
                logger.warning(f"  ⚠️ Greeks Engine not available: {e}")
            
            # 3. Initialize Alpha Engine
            try:
                from equity_hv_service.strategy.institutional_alpha_engine import (
                    create_alpha_engine
                )
                self._alpha_engine = create_alpha_engine({
                    'elite_stocks': self.config.get('elite_stocks', []),
                    'max_position_pct': 20.0
                })
                logger.info("  ✅ Alpha Engine (Stat Arb, Multi-Factor, Order Flow)")
            except ImportError as e:
                logger.warning(f"  ⚠️ Alpha Engine not available: {e}")
            
            self._initialized = True
            
            engines_count = sum([
                1 if self._scalping_engine else 0,
                1 if self._greeks_engine else 0,
                1 if self._alpha_engine else 0
            ])
            
            logger.info("=" * 70)
            logger.info(f"ORCHESTRATOR READY: {engines_count}/3 engines initialized")
            logger.info("=" * 70)
            
            return engines_count > 0
            
        except Exception as e:
            logger.error(f"Failed to initialize orchestrator: {e}")
            return False
    
    def update_market_data(
        self,
        instrument: str,
        price: float,
        volume: int,
        high: float = None,
        low: float = None,
        buy_volume: int = 0,
        sell_volume: int = 0
    ):
        """Feed market data to scalping engine"""
        if self._scalping_engine:
            try:
                self._scalping_engine.update_data(
                    instrument=instrument,
                    price=price,
                    volume=volume,
                    high=high or price,
                    low=low or price,
                    buy_volume=buy_volume,
                    sell_volume=sell_volume
                )
            except Exception as e:
                logger.debug(f"Scalping engine update error: {e}")
    
    def add_option_position(
        self,
        symbol: str,
        strike: float,
        expiry,
        option_type: str,
        quantity: int,
        entry_price: float,
        spot_price: float,
        implied_vol: float = 0.15
    ):
        """Track option position in Greeks engine"""
        if self._greeks_engine:
            try:
                return self._greeks_engine.add_position(
                    symbol=symbol,
                    strike=strike,
                    expiry=expiry,
                    option_type=option_type,
                    quantity=quantity,
                    entry_price=entry_price,
                    spot_price=spot_price,
                    implied_vol=implied_vol
                )
            except Exception as e:
                logger.debug(f"Greeks engine position add error: {e}")
        return None
    
    async def generate_unified_signal(
        self,
        instrument: str,
        current_price: float,
        option_chain: Dict = None,
        price_data: Dict = None
    ) -> Optional[UnifiedSignal]:
        """
        Generate unified signal from all three engines.
        
        Execution Order:
        1. Detect regime (Alpha Engine)
        2. Analyze SMC & Volume Profile (Scalping Engine)
        3. Calculate Greeks & risk (Greeks Engine)
        4. Generate alpha signals (Alpha Engine)
        5. Combine all signals with weighted average
        """
        
        if not self._initialized:
            await self.initialize()
        
        try:
            # STEP 1: Get market regime
            regime = "UNKNOWN"
            regime_mult = 1.0
            if self._alpha_engine:
                try:
                    regime = self._alpha_engine.regime_detector.current_regime.value
                    params = self._alpha_engine.regime_detector.get_regime_adjusted_params()
                    regime_mult = params.get('position_size_multiplier', 1.0)
                except:
                    pass
            
            # STEP 2: Get scalping signal
            scalping_score = 0.0
            scalping_signal = None
            smc_analysis = {}
            volume_profile = {}
            gamma_analysis = {}
            entry_price = current_price
            stop_loss = current_price * 0.98
            targets = [current_price * 1.02, current_price * 1.03, current_price * 1.05]
            direction = UnifiedDirection.NEUTRAL
            
            if self._scalping_engine:
                try:
                    scalping_signal = self._scalping_engine.analyze(
                        instrument=instrument,
                        current_price=current_price,
                        option_chain=option_chain
                    )
                    if scalping_signal:
                        scalping_score = scalping_signal.confluence_score
                        direction = UnifiedDirection.LONG if scalping_signal.direction.value == "LONG" else UnifiedDirection.SHORT
                        entry_price = scalping_signal.entry_price
                        stop_loss = scalping_signal.stop_loss
                        targets = [scalping_signal.target_1, scalping_signal.target_2, scalping_signal.target_3]
                        smc_analysis = scalping_signal.smc_analysis
                        volume_profile = scalping_signal.volume_profile
                        gamma_analysis = scalping_signal.gamma_analysis
                except Exception as e:
                    logger.debug(f"Scalping analysis error: {e}")
            
            # STEP 3: Get Greeks assessment
            greeks_score = 50.0  # Default neutral score
            delta_exposure = 0.0
            gamma_exposure = 0.0
            vega_exposure = 0.0
            greeks_mult = 1.0
            
            if self._greeks_engine:
                try:
                    summary = self._greeks_engine.get_portfolio_summary()
                    greeks = summary.get('greeks', {})
                    delta_exposure = greeks.get('delta', 0)
                    gamma_exposure = greeks.get('gamma', 0)
                    vega_exposure = greeks.get('vega', 0)
                    
                    risk_status = summary.get('risk_status', {})
                    if risk_status.get('within_limits', True):
                        greeks_score = 80.0
                    else:
                        greeks_score = 30.0
                        breaches = len(risk_status.get('breaches', []))
                        greeks_mult = max(0.3, 1.0 - (breaches * 0.2))
                except Exception as e:
                    logger.debug(f"Greeks analysis error: {e}")
            
            # STEP 4: Get alpha signals
            alpha_score = 0.0
            factor_scores = {}
            
            if self._alpha_engine and price_data:
                try:
                    alpha_signals = await self._alpha_engine.generate_alpha_signals(
                        price_data=price_data
                    )
                    
                    for sig in alpha_signals:
                        if sig.symbol == instrument:
                            alpha_score = sig.confidence * 100
                            factor_scores = {
                                'type': sig.alpha_type.value if hasattr(sig.alpha_type, 'value') else str(sig.alpha_type),
                                'expected_return': sig.expected_return,
                                'sharpe': sig.sharpe_ratio
                            }
                            
                            # Adjust direction if alpha disagrees
                            if (sig.direction == "LONG" and direction == UnifiedDirection.SHORT) or \
                               (sig.direction == "SHORT" and direction == UnifiedDirection.LONG):
                                alpha_score *= 0.5  # Reduce score for conflicting signals
                            break
                except Exception as e:
                    logger.debug(f"Alpha analysis error: {e}")
            
            # STEP 5: Calculate unified score
            unified_score = (
                scalping_score * self._weights['scalping'] +
                greeks_score * self._weights['greeks'] +
                alpha_score * self._weights['alpha']
            )
            
            # Apply regime and Greeks multipliers
            adjusted_score = unified_score * regime_mult * greeks_mult
            
            # STEP 6: Determine confidence level
            if adjusted_score >= 90:
                confidence = SignalConfidence.LEGENDARY
            elif adjusted_score >= 80:
                confidence = SignalConfidence.ULTRA
            elif adjusted_score >= 70:
                confidence = SignalConfidence.STRONG
            elif adjusted_score >= 60:
                confidence = SignalConfidence.MODERATE
            else:
                confidence = SignalConfidence.WEAK
            
            # Don't return weak signals
            if adjusted_score < self._min_confluence:
                return None
            
            # Calculate position size
            base_size = min(20.0, adjusted_score / 5)  # Max 20%
            position_pct = base_size * regime_mult * greeks_mult
            
            return UnifiedSignal(
                timestamp=datetime.now(),
                instrument=instrument,
                direction=direction,
                unified_score=adjusted_score,
                scalping_score=scalping_score,
                greeks_score=greeks_score,
                alpha_score=alpha_score,
                confidence=confidence,
                entry_price=entry_price,
                stop_loss=stop_loss,
                targets=targets,
                recommended_position_pct=position_pct,
                delta_exposure=delta_exposure,
                gamma_exposure=gamma_exposure,
                vega_exposure=vega_exposure,
                market_regime=regime,
                smc_analysis=smc_analysis,
                volume_profile=volume_profile,
                gamma_analysis=gamma_analysis,
                factor_scores=factor_scores
            )
            
        except Exception as e:
            logger.error(f"Error generating unified signal: {e}")
            return None
    
    def get_hedge_recommendations(self, spot_price: float) -> List[Dict]:
        """Get hedge recommendations from Greeks engine"""
        if not self._greeks_engine:
            return []
        
        try:
            recommendations = self._greeks_engine.generate_hedge_recommendations(
                spot_price=spot_price,
                realized_vol=0.15,
                implied_vol=0.15
            )
            
            return [
                {
                    'strategy': rec.strategy.value,
                    'action': rec.action.value,
                    'symbol': rec.symbol,
                    'quantity': rec.quantity,
                    'urgency': rec.urgency,
                    'confidence': rec.confidence,
                    'rationale': rec.rationale
                } for rec in recommendations
            ]
        except Exception as e:
            logger.error(f"Error getting hedge recommendations: {e}")
            return []
    
    def get_status(self) -> Dict:
        """Get status of all engines"""
        status = {
            'initialized': self._initialized,
            'engines': {
                'scalping': self._scalping_engine is not None,
                'greeks': self._greeks_engine is not None,
                'alpha': self._alpha_engine is not None
            },
            'weights': self._weights,
            'min_confluence': self._min_confluence,
            'timestamp': datetime.now().isoformat()
        }
        
        if self._scalping_engine:
            try:
                status['scalping_status'] = self._scalping_engine.get_status()
            except:
                pass
        
        if self._greeks_engine:
            try:
                status['greeks_status'] = self._greeks_engine.get_portfolio_summary()
            except:
                pass
        
        if self._alpha_engine:
            try:
                status['alpha_status'] = self._alpha_engine.get_summary()
            except:
                pass
        
        return status


# ============================================================================
# FACTORY FUNCTION
# ============================================================================

def create_unified_orchestrator(config: Dict = None) -> UnifiedInstitutionalOrchestrator:
    """Create and return a UnifiedInstitutionalOrchestrator instance"""
    return UnifiedInstitutionalOrchestrator(config or {})


# ============================================================================
# ALGORITHM EXECUTION FLOW DOCUMENTATION
# ============================================================================
"""
INSTITUTIONAL ALGORITHM EXECUTION FLOW
======================================

┌─────────────────────────────────────────────────────────────────────┐
│                    ALGORITHM EXECUTION FLOW                          │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  PHASE 1: DATA COLLECTION (Every tick)                              │
│  ───────────────────────────────────────                            │
│  • Update price/volume history via update_market_data()             │
│  • Feed to all three engines                                        │
│                                                                      │
│  PHASE 2: ANALYSIS (Every 1-5 seconds)                              │
│  ─────────────────────────────────────                              │
│  ORDER:                                                              │
│   1. Regime Detection (alpha_engine.regime_detector)                │
│      → Determines if TRENDING/MEAN_REVERTING/VOLATILE               │
│      → Adjusts parameters for other algorithms                      │
│                                                                      │
│   2. Smart Money Concept Analysis (scalping_engine)                 │
│      → Detects Order Blocks, FVGs, Liquidity Sweeps                 │
│      → Identifies institutional footprints                          │
│                                                                      │
│   3. Volume Profile Analysis (scalping_engine)                      │
│      → Calculates POC, VAH, VAL                                     │
│      → Identifies HV/LV nodes                                       │
│                                                                      │
│   4. Greeks Calculation (greeks_engine)                             │
│      → Updates portfolio Greeks                                     │
│      → Checks risk limits                                           │
│                                                                      │
│   5. Factor Alpha Generation (alpha_engine)                         │
│      → Momentum, Value, Quality scores                              │
│      → Statistical arbitrage pairs                                  │
│                                                                      │
│  PHASE 3: SIGNAL CONFLUENCE (Before entry)                          │
│  ────────────────────────────────────────                           │
│   1. Collect signals from all engines                               │
│   2. Calculate weighted confluence score                            │
│   3. Apply regime-based adjustments                                 │
│   4. Apply Greeks-based position sizing                             │
│                                                                      │
│  PHASE 4: EXECUTION DECISION                                        │
│  ─────────────────────────────                                      │
│   IF confluence_score >= threshold AND risk_limits_ok:              │
│      → Generate entry signal                                        │
│      → Apply Gemini AI validation (existing)                        │
│      → Execute trade                                                │
│                                                                      │
│  PHASE 5: POSITION MANAGEMENT (Every 5-30 seconds)                  │
│  ─────────────────────────────────────────────────                  │
│   1. Update Greeks for all positions                                │
│   2. Check hedge recommendations (greeks_engine)                    │
│   3. Apply gamma scalping if applicable                             │
│   4. Monitor exit signals                                           │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘

SIGNAL WEIGHTS (Default):
- Scalping Engine: 40% (SMC + Volume Profile + Gamma)
- Greeks Engine: 25% (Risk assessment)
- Alpha Engine: 35% (Statistical + Factor signals)

REGIME ADJUSTMENTS:
- TRENDING_UP/DOWN: 1.2x position size
- MEAN_REVERTING: 0.9x position size
- HIGH_VOLATILITY: 0.7x position size
- CRISIS: 0.5x position size
"""
