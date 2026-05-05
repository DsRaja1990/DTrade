"""
Strategy Orchestrator - Central Decision Loop Controller
Acts as the main decision engine that triggers when strategy is enabled.
Reads live feed → evaluates signal → routes to directional_hedge_strategy or RL policy.
Handles state transitions (e.g., from CE → hedge PE → stack CE again).
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any, Callable
from dataclasses import dataclass
from enum import Enum
import threading
import time
from concurrent.futures import ThreadPoolExecutor

from .directional_hedge_strategy import DirectionalHedgeStrategy, TradeAction, Position
from ai_engine.reinforcement_learning.rl_hedge_agent import RLHedgeAgent
from data_ingestion.dhan_api_connector import DhanAPIConnector
from signals.signal_evaluation_matrix import EnhancedOptionsSignalEvaluator
from evaluation.performance_tracker import PerformanceTracker
from .position_tracker import PositionTracker
from utils.health_monitor import HealthMonitor

logger = logging.getLogger(__name__)

class StrategyState(Enum):
    """Strategy execution states"""
    STOPPED = "STOPPED"
    STARTING = "STARTING"
    RUNNING = "RUNNING"
    PAUSING = "PAUSING"
    PAUSED = "PAUSED"
    STOPPING = "STOPPING"
    ERROR = "ERROR"

class DecisionMode(Enum):
    """Decision making modes"""
    RULE_BASED = "RULE_BASED"
    RL_AGENT = "RL_AGENT"
    HYBRID = "HYBRID"

@dataclass
class StrategyConfig:
    """Strategy orchestrator configuration"""
    loop_interval: float = 1.0  # seconds
    max_concurrent_decisions: int = 5
    decision_timeout: float = 10.0  # seconds
    enable_rl_agent: bool = True
    decision_mode: DecisionMode = DecisionMode.HYBRID
    health_check_interval: float = 30.0  # seconds
    auto_restart_on_error: bool = True
    max_restart_attempts: int = 3

class StrategyOrchestrator:
    """
    Central orchestrator that manages the entire trading strategy lifecycle.
    Integrates with local intelligent-options-hedger components and manages decision flow.
    """
    
    def __init__(self, 
                 config: StrategyConfig,
                 dhan_connector: DhanAPIConnector,
                 config_manager: Any):
        """Initialize the strategy orchestrator"""
        self.config = config
        self.dhan_connector = dhan_connector
        self.config_manager = config_manager
        
        # State management
        self.state = StrategyState.STOPPED
        self.state_lock = threading.Lock()
        self.is_running = False
        self.restart_count = 0
        
        # Core components - integrating with local modules
        self.directional_strategy = DirectionalHedgeStrategy(
            config_manager=config_manager,
            notification_manager=None  # Will be set later
        )
        
        # RL Agent integration
        self.rl_agent = RLHedgeAgent() if config.enable_rl_agent else None
        
        # Signal evaluation from local modules
        self.signal_evaluator = EnhancedOptionsSignalEvaluator()
        
        # Position tracking
        self.position_tracker = PositionTracker()
        
        # Performance tracking from local modules
        self.performance_tracker = PerformanceTracker()
        
        # Health monitoring
        self.health_monitor = HealthMonitor(self)
        
        # Threading
        self.executor = ThreadPoolExecutor(max_workers=config.max_concurrent_decisions)
        self.main_loop_task = None
        self.health_check_task = None
        
        # Callbacks
        self.state_change_callbacks: List[Callable] = []
        self.decision_callbacks: List[Callable] = []
        
        logger.info("Strategy Orchestrator initialized")
    
    def add_state_change_callback(self, callback: Callable):
        """Add callback for state changes"""
        self.state_change_callbacks.append(callback)
    
    def add_decision_callback(self, callback: Callable):
        """Add callback for decision events"""
        self.decision_callbacks.append(callback)
    
    def _change_state(self, new_state: StrategyState):
        """Change state and notify callbacks"""
        with self.state_lock:
            old_state = self.state
            self.state = new_state
            
        logger.info(f"Strategy state changed: {old_state} -> {new_state}")
        
        # Notify callbacks
        for callback in self.state_change_callbacks:
            try:
                callback(old_state, new_state)
            except Exception as e:
                logger.error(f"Error in state change callback: {e}")
    
    async def start_strategy(self):
        """Start the strategy orchestrator"""
        if self.state != StrategyState.STOPPED:
            logger.warning(f"Cannot start strategy in state: {self.state}")
            return False
        
        try:
            self._change_state(StrategyState.STARTING)
            
            # Initialize components
            await self._initialize_components()
            
            # Start main loop
            self.is_running = True
            self.main_loop_task = asyncio.create_task(self._main_decision_loop())
            self.health_check_task = asyncio.create_task(self._health_check_loop())
            
            self._change_state(StrategyState.RUNNING)
            logger.info("Strategy orchestrator started successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start strategy: {e}")
            self._change_state(StrategyState.ERROR)
            return False
    
    async def stop_strategy(self):
        """Stop the strategy orchestrator"""
        if self.state in [StrategyState.STOPPED, StrategyState.STOPPING]:
            return True
        
        try:
            self._change_state(StrategyState.STOPPING)
            self.is_running = False
            
            # Cancel tasks
            if self.main_loop_task:
                self.main_loop_task.cancel()
            if self.health_check_task:
                self.health_check_task.cancel()
            
            # Close all positions if needed
            await self._emergency_close_all()
            
            # Cleanup components
            await self._cleanup_components()
            
            self._change_state(StrategyState.STOPPED)
            logger.info("Strategy orchestrator stopped successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error stopping strategy: {e}")
            self._change_state(StrategyState.ERROR)
            return False
    
    async def pause_strategy(self):
        """Pause the strategy (keep positions, stop new trades)"""
        if self.state != StrategyState.RUNNING:
            return False
        
        self._change_state(StrategyState.PAUSING)
        # Implementation would pause decision making
        self._change_state(StrategyState.PAUSED)
        return True
    
    async def resume_strategy(self):
        """Resume the strategy from paused state"""
        if self.state != StrategyState.PAUSED:
            return False
        
        self._change_state(StrategyState.RUNNING)
        return True
    
    async def _initialize_components(self):
        """Initialize all strategy components"""
        # Initialize signal evaluator with local module integration
        await self.signal_evaluator.initialize()
        
        # Initialize directional strategy
        await self.directional_strategy.initialize()
        
        # Initialize RL agent if enabled
        if self.rl_agent:
            await self.rl_agent.initialize()
        
        # Initialize position tracker
        await self.position_tracker.initialize()
        
        # Initialize performance tracker
        await self.performance_tracker.initialize()
        
        # Initialize health monitor
        await self.health_monitor.initialize()
        
        logger.info("All components initialized")
    
    async def _cleanup_components(self):
        """Cleanup all components"""
        components = [
            self.signal_evaluator,
            self.directional_strategy,
            self.position_tracker,
            self.performance_tracker,
            self.health_monitor
        ]
        
        for component in components:
            try:
                if hasattr(component, 'cleanup'):
                    await component.cleanup()
            except Exception as e:
                logger.error(f"Error cleaning up component {component}: {e}")
    
    async def _main_decision_loop(self):
        """Main decision loop - core orchestration logic"""
        logger.info("Starting main decision loop")
        
        while self.is_running:
            try:
                if self.state != StrategyState.RUNNING:
                    await asyncio.sleep(self.config.loop_interval)
                    continue
                
                # Get live market data
                market_data = await self._get_live_market_data()
                
                # Evaluate signals using local modules
                signals = await self._evaluate_signals(market_data)
                
                # Make trading decision
                decision = await self._make_trading_decision(signals, market_data)
                
                # Execute decision
                if decision and decision != TradeAction.HOLD:
                    await self._execute_decision(decision, market_data)
                
                # Update performance tracking
                await self._update_performance()
                
                # Notify decision callbacks
                for callback in self.decision_callbacks:
                    try:
                        callback(decision, signals, market_data)
                    except Exception as e:
                        logger.error(f"Error in decision callback: {e}")
                
                await asyncio.sleep(self.config.loop_interval)
                
            except Exception as e:
                logger.error(f"Error in main decision loop: {e}")
                if self.config.auto_restart_on_error:
                    await self._handle_error()
                else:
                    self._change_state(StrategyState.ERROR)
                    break
    
    async def _get_live_market_data(self) -> Dict[str, Any]:
        """Get live market data for decision making"""
        try:
            # This integrates with existing DhanAPI connector
            return await self.dhan_connector.get_live_market_data()
        except Exception as e:
            logger.error(f"Error getting live market data: {e}")
            return {}
    
    async def _evaluate_signals(self, market_data: Dict[str, Any]) -> List[Any]:
        """Evaluate trading signals using local components"""
        try:
            # Use existing signal evaluation matrix
            signals = await self.signal_evaluator.evaluate_signals(market_data)
            return signals
        except Exception as e:
            logger.error(f"Error evaluating signals: {e}")
            return []
    
    async def _make_trading_decision(self, signals: List[Any], market_data: Dict[str, Any]) -> TradeAction:
        """Make trading decision based on signals and current positions"""
        try:
            current_positions = await self.position_tracker.get_current_positions()
            
            if self.config.decision_mode == DecisionMode.RULE_BASED:
                return await self._rule_based_decision(signals, current_positions, market_data)
            elif self.config.decision_mode == DecisionMode.RL_AGENT and self.rl_agent:
                return await self._rl_based_decision(signals, current_positions, market_data)
            elif self.config.decision_mode == DecisionMode.HYBRID:
                return await self._hybrid_decision(signals, current_positions, market_data)
            else:
                return TradeAction.HOLD
                
        except Exception as e:
            logger.error(f"Error making trading decision: {e}")
            return TradeAction.HOLD
    
    async def _rule_based_decision(self, signals: List[Any], positions: List[Position], market_data: Dict[str, Any]) -> TradeAction:
        """Rule-based decision using existing directional strategy"""
        return await self.directional_strategy.make_decision(signals, positions, market_data)
    
    async def _rl_based_decision(self, signals: List[Any], positions: List[Position], market_data: Dict[str, Any]) -> TradeAction:
        """RL agent based decision"""
        if not self.rl_agent:
            return TradeAction.HOLD
        
        # Convert signals and positions to RL agent format
        state = await self._prepare_rl_state(signals, positions, market_data)
        action = await self.rl_agent.get_action(state)
        
        # Convert RL action to TradeAction
        return self._convert_rl_action(action)
    
    async def _hybrid_decision(self, signals: List[Any], positions: List[Position], market_data: Dict[str, Any]) -> TradeAction:
        """Hybrid decision combining rule-based and RL approaches"""
        # Get both decisions
        rule_decision = await self._rule_based_decision(signals, positions, market_data)
        rl_decision = await self._rl_based_decision(signals, positions, market_data)
        
        # Combine decisions with confidence scoring
        final_decision = await self._combine_decisions(rule_decision, rl_decision, signals)
        return final_decision
    
    async def _execute_decision(self, decision: TradeAction, market_data: Dict[str, Any]):
        """Execute the trading decision"""
        try:
            result = await self.directional_strategy.execute_action(decision, market_data)
            
            # Update position tracker
            if result:
                await self.position_tracker.update_positions(result)
            
        except Exception as e:
            logger.error(f"Error executing decision {decision}: {e}")
    
    async def _update_performance(self):
        """Update performance metrics"""
        try:
            positions = await self.position_tracker.get_current_positions()
            await self.performance_tracker.update_performance(positions)
        except Exception as e:
            logger.error(f"Error updating performance: {e}")
    
    async def _health_check_loop(self):
        """Health monitoring loop"""
        while self.is_running:
            try:
                await self.health_monitor.check_health()
                await asyncio.sleep(self.config.health_check_interval)
            except Exception as e:
                logger.error(f"Error in health check: {e}")
                await asyncio.sleep(self.config.health_check_interval)
    
    async def _handle_error(self):
        """Handle errors with auto-restart logic"""
        if self.restart_count >= self.config.max_restart_attempts:
            logger.error("Max restart attempts reached, stopping strategy")
            self._change_state(StrategyState.ERROR)
            return
        
        self.restart_count += 1
        logger.info(f"Attempting restart {self.restart_count}/{self.config.max_restart_attempts}")
        
        try:
            await self.stop_strategy()
            await asyncio.sleep(5)  # Wait before restart
            await self.start_strategy()
            self.restart_count = 0  # Reset on successful restart
        except Exception as e:
            logger.error(f"Restart attempt failed: {e}")
    
    async def _emergency_close_all(self):
        """Emergency close all positions"""
        try:
            await self.directional_strategy.close_all_positions()
        except Exception as e:
            logger.error(f"Error in emergency close: {e}")
    
    # Helper methods for RL integration
    async def _prepare_rl_state(self, signals: List[Any], positions: List[Position], market_data: Dict[str, Any]) -> np.ndarray:
        """Prepare state for RL agent"""
        # Implementation to convert signals, positions, and market data to RL state
        pass
    
    def _convert_rl_action(self, rl_action: Any) -> TradeAction:
        """Convert RL agent action to TradeAction"""
        # Implementation to map RL actions to TradeAction enum
        pass
    
    async def _combine_decisions(self, rule_decision: TradeAction, rl_decision: TradeAction, signals: List[Any]) -> TradeAction:
        """Combine rule-based and RL decisions"""
        # Implementation to intelligently combine decisions
        pass
    
    # Status and control methods
    def get_status(self) -> Dict[str, Any]:
        """Get current orchestrator status"""
        return {
            "state": self.state.value,
            "is_running": self.is_running,
            "restart_count": self.restart_count,
            "decision_mode": self.config.decision_mode.value,
            "rl_enabled": self.rl_agent is not None,
            "timestamp": datetime.now().isoformat()
        }
    
    async def get_current_positions(self) -> List[Position]:
        """Get current positions"""
        return await self.position_tracker.get_current_positions()
    
    async def get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics"""
        return await self.performance_tracker.get_metrics()
