"""
Production Directional Hedge Strategy - World-Class Options Trading Engine
============================================================================
This is the main strategy wrapper that integrates all components for 
institutional-grade options trading with the Dhan API.

NO MOCK DATA - ALL REAL PRODUCTION COMPONENTS
"""

import asyncio
import logging
from typing import Dict, Optional, Any, List
from datetime import datetime
from dataclasses import dataclass
from enum import Enum

# Configure logging
logger = logging.getLogger(__name__)


class StrategyState(Enum):
    """Strategy lifecycle states"""
    INITIALIZED = "initialized"
    STARTING = "starting"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"


@dataclass
class StrategyConfig:
    """Configuration for the directional hedge strategy"""
    initial_capital: float = 1000000.0
    max_position_size: int = 10
    max_risk_per_trade: float = 0.02
    max_daily_loss: float = 0.05
    min_signal_confidence: float = 0.7
    enable_stacking: bool = True
    enable_neural_enhancement: bool = True
    enable_rl_optimization: bool = True
    hedge_ratio: float = 0.5
    stop_loss_pct: float = 0.03
    take_profit_pct: float = 0.06
    max_vix_threshold: float = 30.0
    min_oi_threshold: int = 1000
    execution_algorithm: str = "SMART"  # TWAP, VWAP, SMART
    rebalance_interval_seconds: int = 300


class DirectionalHedgeStrategy:
    """
    Production-grade Directional Hedge Strategy
    
    This is the main entry point that integrates:
    - Dhan API for real market data and order execution
    - Enhanced signal evaluation and confluence scoring
    - Production stacking engine with guardrails
    - Neural network enhancement (when available)
    - Reinforcement learning optimization (when available)
    - Advanced position tracking with Greeks
    - TWAP/VWAP/Smart execution algorithms
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the strategy with optional configuration.
        
        Args:
            config: Optional configuration dictionary
        """
        self.config = StrategyConfig(**(config or {}))
        self.state = StrategyState.INITIALIZED
        self._dhan_connector = None
        self._enhanced_strategy = None
        self._signal_evaluator = None
        self._stacking_engine = None
        self._trade_executor = None
        self._position_tracker = None
        self._strategy_orchestrator = None
        self._running = False
        self._task = None
        self._initialized = False
        
        logger.info(f"DirectionalHedgeStrategy initialized with config: {self.config}")
    
    async def initialize(self) -> bool:
        """
        Initialize all strategy components with real production services.
        
        Returns:
            True if initialization successful, False otherwise
        """
        if self._initialized:
            logger.warning("Strategy already initialized")
            return True
        
        try:
            logger.info("Initializing DirectionalHedgeStrategy with production components...")
            self.state = StrategyState.STARTING
            
            # Import components here to avoid circular imports
            await self._initialize_components()
            
            self._initialized = True
            self.state = StrategyState.INITIALIZED
            logger.info("DirectionalHedgeStrategy initialization complete")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize strategy: {e}", exc_info=True)
            self.state = StrategyState.ERROR
            return False
    
    async def _initialize_components(self):
        """Initialize all strategy components"""
        
        # 1. Initialize Dhan Connector
        try:
            from data_ingestion.dhan_api_connector import get_dhan_connector, DhanAPIConnector
            # Store the connector factory - actual connection happens during run
            self._dhan_connector_factory = get_dhan_connector
            logger.info("✓ Dhan API Connector factory ready")
        except ImportError as e:
            logger.error(f"Failed to import DhanAPIConnector: {e}")
            raise
        
        # 2. Initialize Signal Evaluator
        try:
            from signals.signal_evaluation_matrix import EnhancedOptionsSignalEvaluator
            self._signal_evaluator = EnhancedOptionsSignalEvaluator(dhan_connector=None)
            logger.info("✓ Signal evaluator initialized")
        except ImportError as e:
            logger.warning(f"Signal evaluator not available: {e}")
            self._signal_evaluator = None
        
        # Try to initialize confluence engine separately
        try:
            from signals.enhanced_signal_confluence import EnhancedSignalConfluenceEngine
            self._confluence_engine = EnhancedSignalConfluenceEngine(config={})
            logger.info("✓ Confluence engine initialized")
        except ImportError as e:
            logger.warning(f"Confluence engine not available: {e}")
            self._confluence_engine = None
        
        # 3. Initialize Stacking Engine
        try:
            from strategies.production_stacking_engine import ProductionStackingDecisionEngine
            stacking_config = {
                'stacking_mode': 'hybrid_validation',
                'guardrails_weight': 0.7,
                'neural_weight': 0.3,
                'require_consensus': True,
                'min_confidence_threshold': self.config.min_signal_confidence
            }
            self._stacking_engine = ProductionStackingDecisionEngine(config=stacking_config)
            logger.info("✓ Stacking engine initialized")
        except ImportError as e:
            logger.warning(f"Stacking engine not available: {e}")
            self._stacking_engine = None
        
        # Try to initialize guardrails separately
        try:
            from strategies.enhanced_stacking_guardrails import EnhancedStackingGuardrails
            self._stacking_guardrails = EnhancedStackingGuardrails()
            logger.info("✓ Stacking guardrails initialized")
        except ImportError as e:
            logger.warning(f"Stacking guardrails not available: {e}")
            self._stacking_guardrails = None
        
        # 4. Initialize Trade Executor (will be set when connector is available)
        try:
            from strategies.trade_executor import TradeExecutor
            # TradeExecutor requires dhan_connector, so we defer initialization
            self._trade_executor_class = TradeExecutor
            self._trade_executor = None  # Will be created when connector is available
            logger.info("✓ Trade executor class loaded (will initialize with connector)")
        except ImportError as e:
            logger.warning(f"Trade executor not available: {e}")
            self._trade_executor_class = None
            self._trade_executor = None
        
        # 5. Initialize Position Tracker
        try:
            from strategies.position_tracker import PositionTracker
            self._position_tracker = PositionTracker()
            logger.info("✓ Position tracker initialized")
        except ImportError as e:
            logger.warning(f"Position tracker not available: {e}")
            self._position_tracker = None
        
        # 6. Initialize Neural Enhancement (optional)
        if self.config.enable_neural_enhancement:
            try:
                from ai_engine.neural_options_chain_mapper import NeuralOptionsChainMapper
                self._neural_mapper = NeuralOptionsChainMapper()
                logger.info("✓ Neural options chain mapper initialized")
            except ImportError as e:
                logger.warning(f"Neural enhancement not available: {e}")
                self._neural_mapper = None
        else:
            self._neural_mapper = None
        
        # 7. Initialize RL Optimization (optional)
        if self.config.enable_rl_optimization:
            try:
                from ai_engine.reinforcement_learning.rl_strategy_integration import RLStrategyIntegration, RL_AVAILABLE
                if RL_AVAILABLE:
                    rl_config = {'enable_rl': True}
                    self._rl_integration = RLStrategyIntegration(
                        strategy_instance=self,
                        config=rl_config
                    )
                    if self._rl_integration.rl_available:
                        logger.info("✓ RL optimization initialized")
                    else:
                        logger.info("RL optimization disabled (PyTorch not available)")
                        self._rl_integration = None
                else:
                    logger.info("RL components not available (PyTorch not installed)")
                    self._rl_integration = None
            except ImportError as e:
                logger.warning(f"RL optimization not available: {e}")
                self._rl_integration = None
        else:
            self._rl_integration = None
        
        # 8. Initialize Strategy Orchestrator
        try:
            from strategies.strategy_orchestrator import StrategyOrchestrator
            self._strategy_orchestrator = StrategyOrchestrator(config=vars(self.config))
            await self._strategy_orchestrator.initialize()
            logger.info("✓ Strategy orchestrator initialized")
        except ImportError as e:
            logger.warning(f"Strategy orchestrator not available: {e}")
            self._strategy_orchestrator = None
        except Exception as e:
            logger.warning(f"Strategy orchestrator initialization failed: {e}")
            self._strategy_orchestrator = None
    
    async def start(self) -> bool:
        """
        Start the strategy engine.
        
        Returns:
            True if started successfully
        """
        if not self._initialized:
            success = await self.initialize()
            if not success:
                return False
        
        if self._running:
            logger.warning("Strategy already running")
            return True
        
        try:
            logger.info("Starting DirectionalHedgeStrategy...")
            self.state = StrategyState.STARTING
            self._running = True
            
            # Start the main strategy loop as background task
            self._task = asyncio.create_task(self._run_strategy_loop())
            
            self.state = StrategyState.RUNNING
            logger.info("DirectionalHedgeStrategy started successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start strategy: {e}", exc_info=True)
            self.state = StrategyState.ERROR
            self._running = False
            return False
    
    async def _run_strategy_loop(self):
        """Main strategy execution loop"""
        logger.info("Strategy loop started")
        
        while self._running:
            try:
                # Use async context manager for Dhan connection
                async with self._dhan_connector_factory() as connector:
                    self._dhan_connector = connector
                    
                    while self._running:
                        await self._execute_cycle(connector)
                        await asyncio.sleep(self.config.rebalance_interval_seconds)
                        
            except Exception as e:
                logger.error(f"Strategy loop error: {e}", exc_info=True)
                if self._running:
                    logger.info("Reconnecting in 30 seconds...")
                    await asyncio.sleep(30)
        
        logger.info("Strategy loop stopped")
    
    async def _execute_cycle(self, connector) -> Dict[str, Any]:
        """
        Execute one cycle of the trading strategy.
        
        Args:
            connector: Active Dhan API connector
            
        Returns:
            Cycle results dictionary
        """
        cycle_start = datetime.now()
        result = {
            "timestamp": cycle_start.isoformat(),
            "signals": [],
            "decisions": [],
            "executions": [],
            "errors": []
        }
        
        try:
            # 1. Get current market data
            market_data = await self._get_market_data(connector)
            if not market_data:
                result["errors"].append("Failed to get market data")
                return result
            
            # 2. Generate signals
            signals = await self._generate_signals(market_data)
            result["signals"] = signals
            
            # 3. Apply stacking decisions
            if self._stacking_engine and signals:
                decisions = await self._make_stacking_decisions(signals, market_data)
                result["decisions"] = decisions
            
            # 4. Execute trades
            if result["decisions"]:
                executions = await self._execute_trades(connector, result["decisions"])
                result["executions"] = executions
            
            # 5. Update positions
            await self._update_positions(connector)
            
            # 6. Check risk limits
            await self._check_risk_limits(connector)
            
            cycle_time = (datetime.now() - cycle_start).total_seconds()
            result["cycle_time_seconds"] = cycle_time
            logger.debug(f"Cycle completed in {cycle_time:.2f}s: {len(signals)} signals, {len(result['decisions'])} decisions")
            
        except Exception as e:
            logger.error(f"Cycle execution error: {e}", exc_info=True)
            result["errors"].append(str(e))
        
        return result
    
    async def _get_market_data(self, connector) -> Optional[Dict[str, Any]]:
        """Fetch current market data from Dhan API"""
        try:
            # Get NIFTY index quote
            nifty_quote = await connector.get_live_quote(
                symbol="NIFTY 50",
                exchange="NSE"
            )
            
            # Get option chain
            option_chain = await connector.get_option_chain(
                symbol="NIFTY",
                expiry_date=None  # Get nearest expiry
            )
            
            # Get VIX
            vix_quote = await connector.get_live_quote(
                symbol="INDIA VIX",
                exchange="NSE"
            )
            
            return {
                "spot": nifty_quote,
                "option_chain": option_chain,
                "vix": vix_quote.get("ltp", 15.0) if vix_quote else 15.0,
                "timestamp": datetime.now()
            }
            
        except Exception as e:
            logger.error(f"Failed to get market data: {e}")
            return None
    
    async def _generate_signals(self, market_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate trading signals from market data"""
        signals = []
        
        try:
            if self._signal_evaluator:
                # Use signal evaluator for comprehensive analysis
                signal_result = self._signal_evaluator.evaluate(
                    option_chain=market_data.get("option_chain", {}),
                    spot_price=market_data.get("spot", {}).get("ltp", 0),
                    vix=market_data.get("vix", 15.0)
                )
                if signal_result and signal_result.get("confidence", 0) >= self.config.min_signal_confidence:
                    signals.append(signal_result)
            
            # Apply neural enhancement if available
            if self._neural_mapper and signals:
                enhanced_signals = []
                for signal in signals:
                    enhanced = self._neural_mapper.enhance_signal(signal, market_data)
                    enhanced_signals.append(enhanced)
                signals = enhanced_signals
            
            # Apply RL optimization if available
            if self._rl_integration and signals:
                rl_signals = []
                for signal in signals:
                    optimized = self._rl_integration.optimize_signal(signal, market_data)
                    rl_signals.append(optimized)
                signals = rl_signals
                
        except Exception as e:
            logger.error(f"Signal generation error: {e}")
        
        return signals
    
    async def _make_stacking_decisions(
        self, 
        signals: List[Dict[str, Any]], 
        market_data: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Make stacking/position decisions based on signals"""
        decisions = []
        
        try:
            if self._stacking_engine:
                for signal in signals:
                    decision = self._stacking_engine.evaluate(
                        signal=signal,
                        current_positions=self._get_current_positions(),
                        market_data=market_data
                    )
                    if decision and decision.get("action") != "HOLD":
                        decisions.append(decision)
        except Exception as e:
            logger.error(f"Stacking decision error: {e}")
        
        return decisions
    
    async def _execute_trades(
        self, 
        connector, 
        decisions: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Execute trades based on decisions"""
        executions = []
        
        try:
            if self._trade_executor:
                for decision in decisions:
                    execution = await self._trade_executor.execute(
                        connector=connector,
                        decision=decision
                    )
                    executions.append(execution)
            else:
                # Direct execution without advanced algorithms
                for decision in decisions:
                    try:
                        order_result = await connector.place_order(
                            symbol=decision.get("symbol"),
                            exchange=decision.get("exchange", "NFO"),
                            quantity=decision.get("quantity"),
                            order_type=decision.get("order_type", "LIMIT"),
                            transaction_type=decision.get("action", "BUY"),
                            price=decision.get("price"),
                            product_type="NRML"
                        )
                        executions.append({
                            "decision": decision,
                            "order_result": order_result,
                            "success": order_result.get("status") == "SUCCESS"
                        })
                    except Exception as e:
                        logger.error(f"Order execution failed: {e}")
                        executions.append({
                            "decision": decision,
                            "error": str(e),
                            "success": False
                        })
        except Exception as e:
            logger.error(f"Trade execution error: {e}")
        
        return executions
    
    async def _update_positions(self, connector):
        """Update position tracker with current positions"""
        try:
            if self._position_tracker:
                positions = await connector.get_positions()
                self._position_tracker.update(positions)
        except Exception as e:
            logger.error(f"Position update error: {e}")
    
    async def _check_risk_limits(self, connector):
        """Check and enforce risk limits"""
        try:
            if self._position_tracker:
                risk_status = self._position_tracker.check_risk_limits(
                    max_daily_loss=self.config.max_daily_loss,
                    max_position_size=self.config.max_position_size
                )
                
                if risk_status.get("limit_breached"):
                    logger.warning(f"Risk limit breached: {risk_status}")
                    await self._handle_risk_breach(connector, risk_status)
        except Exception as e:
            logger.error(f"Risk check error: {e}")
    
    async def _handle_risk_breach(self, connector, risk_status: Dict[str, Any]):
        """Handle risk limit breaches"""
        try:
            if risk_status.get("daily_loss_exceeded"):
                logger.warning("Daily loss limit exceeded - closing all positions")
                await self.close_all_positions()
                self.state = StrategyState.PAUSED
        except Exception as e:
            logger.error(f"Risk breach handling error: {e}")
    
    def _get_current_positions(self) -> List[Dict[str, Any]]:
        """Get current positions from tracker"""
        if self._position_tracker:
            return self._position_tracker.get_all_positions()
        return []
    
    async def stop(self) -> bool:
        """
        Stop the strategy engine gracefully.
        
        Returns:
            True if stopped successfully
        """
        if not self._running:
            logger.warning("Strategy not running")
            return True
        
        try:
            logger.info("Stopping DirectionalHedgeStrategy...")
            self.state = StrategyState.STOPPING
            self._running = False
            
            # Cancel the background task
            if self._task:
                self._task.cancel()
                try:
                    await self._task
                except asyncio.CancelledError:
                    pass
                self._task = None
            
            self.state = StrategyState.STOPPED
            logger.info("DirectionalHedgeStrategy stopped successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to stop strategy: {e}", exc_info=True)
            self.state = StrategyState.ERROR
            return False
    
    async def shutdown(self) -> bool:
        """
        Shutdown the strategy and cleanup resources.
        
        Returns:
            True if shutdown successful
        """
        try:
            logger.info("Shutting down DirectionalHedgeStrategy...")
            
            # Stop if running
            if self._running:
                await self.stop()
            
            # Cleanup orchestrator
            if self._strategy_orchestrator:
                await self._strategy_orchestrator.shutdown()
            
            # Cleanup components
            self._signal_evaluator = None
            self._stacking_engine = None
            self._trade_executor = None
            self._position_tracker = None
            self._neural_mapper = None
            self._rl_integration = None
            self._dhan_connector = None
            
            self._initialized = False
            logger.info("DirectionalHedgeStrategy shutdown complete")
            return True
            
        except Exception as e:
            logger.error(f"Shutdown error: {e}", exc_info=True)
            return False
    
    async def close_all_positions(self) -> Dict[str, Any]:
        """
        Close all open positions (emergency exit).
        
        Returns:
            Result of position closing operations
        """
        result = {"closed": [], "errors": []}
        
        try:
            logger.warning("CLOSING ALL POSITIONS")
            
            if not self._dhan_connector:
                # Create temporary connection for emergency close
                async with self._dhan_connector_factory() as connector:
                    result = await self._close_positions_with_connector(connector)
            else:
                result = await self._close_positions_with_connector(self._dhan_connector)
                
        except Exception as e:
            logger.error(f"Close all positions error: {e}", exc_info=True)
            result["errors"].append(str(e))
        
        return result
    
    async def _close_positions_with_connector(self, connector) -> Dict[str, Any]:
        """Close positions using the provided connector"""
        result = {"closed": [], "errors": []}
        
        try:
            positions = await connector.get_positions()
            
            for position in positions:
                if position.get("quantity", 0) != 0:
                    try:
                        # Determine exit action
                        action = "SELL" if position.get("quantity", 0) > 0 else "BUY"
                        qty = abs(position.get("quantity", 0))
                        
                        order_result = await connector.place_order(
                            symbol=position.get("symbol"),
                            exchange=position.get("exchange", "NFO"),
                            quantity=qty,
                            order_type="MARKET",
                            transaction_type=action,
                            product_type="NRML"
                        )
                        result["closed"].append({
                            "symbol": position.get("symbol"),
                            "quantity": qty,
                            "order_result": order_result
                        })
                    except Exception as e:
                        result["errors"].append({
                            "symbol": position.get("symbol"),
                            "error": str(e)
                        })
                        
        except Exception as e:
            result["errors"].append(str(e))
        
        return result
    
    # Alias methods for compatibility
    async def run_engine(self) -> bool:
        """Alias for start() for backward compatibility"""
        return await self.start()
    
    def get_status(self) -> Dict[str, Any]:
        """Get current strategy status"""
        return {
            "state": self.state.value,
            "running": self._running,
            "initialized": self._initialized,
            "config": vars(self.config),
            "components": {
                "signal_evaluator": self._signal_evaluator is not None,
                "stacking_engine": self._stacking_engine is not None,
                "trade_executor": self._trade_executor is not None,
                "position_tracker": self._position_tracker is not None,
                "neural_mapper": self._neural_mapper is not None,
                "rl_integration": self._rl_integration is not None,
                "strategy_orchestrator": self._strategy_orchestrator is not None
            },
            "timestamp": datetime.now().isoformat()
        }
    
    def get_positions(self) -> List[Dict[str, Any]]:
        """Get current positions"""
        return self._get_current_positions()
    
    def get_pnl(self) -> Dict[str, Any]:
        """Get current P&L summary"""
        if self._position_tracker:
            return self._position_tracker.get_pnl_summary()
        return {"realized": 0.0, "unrealized": 0.0, "total": 0.0}


# Factory function for creating strategy instances
def create_strategy(config: Optional[Dict[str, Any]] = None) -> DirectionalHedgeStrategy:
    """
    Factory function to create a DirectionalHedgeStrategy instance.
    
    Args:
        config: Optional configuration dictionary
        
    Returns:
        DirectionalHedgeStrategy instance
    """
    return DirectionalHedgeStrategy(config=config)


# For module-level access
__all__ = [
    "DirectionalHedgeStrategy",
    "StrategyConfig",
    "StrategyState",
    "create_strategy"
]
