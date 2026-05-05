"""
╔══════════════════════════════════════════════════════════════════════════════════════╗
║                    PROBE-SCALE TRADE EXECUTOR v1.0                                   ║
║         10% Probe → Gemini Confirmation → 90% Scale → AI-Monitored Exit             ║
╠══════════════════════════════════════════════════════════════════════════════════════╣
║                                                                                      ║
║  EXECUTION FLOW:                                                                     ║
║  ═══════════════════════════════════════════════════════════════════════════════    ║
║                                                                                      ║
║  ┌─────────────┐    ┌─────────────────────┐    ┌─────────────────┐                  ║
║  │   SIGNAL    │ →  │   PROBE ENTRY (10%) │ →  │  MONITOR PROBE  │                  ║
║  │   RECEIVED  │    │   Wide SL (50%)     │    │  Every 30 sec   │                  ║
║  └─────────────┘    └─────────────────────┘    └─────────────────┘                  ║
║                                                        │                             ║
║         ┌──────────────────────────────────────────────┴───────────────┐            ║
║         │                                                              │            ║
║         ▼                                                              ▼            ║
║  ┌─────────────────────┐                                    ┌─────────────────┐    ║
║  │  PROBE PROFITABLE   │                                    │  PROBE LOSING   │    ║
║  │  (>10% profit)      │                                    │  (>25% loss)    │    ║
║  └─────────────────────┘                                    └─────────────────┘    ║
║         │                                                              │            ║
║         ▼                                                              ▼            ║
║  ┌─────────────────────┐                                    ┌─────────────────┐    ║
║  │  GEMINI CONFIRMS?   │                                    │  MINIMIZE LOSS  │    ║
║  │  (Confidence >85%)  │                                    │  Exit Probe     │    ║
║  └─────────────────────┘                                    └─────────────────┘    ║
║         │                                                                           ║
║         ▼                                                                           ║
║  ┌─────────────────────┐    ┌─────────────────┐    ┌─────────────────┐            ║
║  │  SCALE UP (90%)     │ →  │  FULL POSITION  │ →  │  GEMINI MONITOR │            ║
║  │  Tighter SL (30%)   │    │  Trailing (50pt)│    │  Every 30 sec   │            ║
║  └─────────────────────┘    └─────────────────┘    └─────────────────┘            ║
║                                                              │                      ║
║                                            ┌─────────────────┼─────────────────┐   ║
║                                            ▼                 ▼                 ▼   ║
║                                     ┌───────────┐    ┌───────────┐    ┌───────────┐║
║                                     │   HOLD    │    │  PARTIAL  │    │   FULL    │║
║                                     │  (Strong) │    │   EXIT    │    │   EXIT    │║
║                                     └───────────┘    └───────────┘    └───────────┘║
║                                                                                      ║
╚══════════════════════════════════════════════════════════════════════════════════════╝
"""

import asyncio
import aiohttp
import json
import logging
import sqlite3
import uuid
from datetime import datetime, timedelta
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
import os

# Import the Gemini Intelligence Engine
from .gemini_trade_intelligence import (
    GeminiTradeIntelligence,
    GeminiConfig,
    ProbeScaleConfig,
    ProbePosition,
    TradePhase,
    GeminiDecision,
    MomentumStatus,
    GeminiAnalysisResult
)

logger = logging.getLogger(__name__ + '.probe_scale_executor')


# ============================================================================
# CONFIGURATION
# ============================================================================

@dataclass
class ExecutorConfig:
    """
    ╔══════════════════════════════════════════════════════════════════════════╗
    ║  ELITE PROBE-SCALE EXECUTOR - 300%+ MONTHLY RETURNS                      ║
    ║  Aggressive Pyramid Scaling with Smart Risk Management                   ║
    ╚══════════════════════════════════════════════════════════════════════════╝
    """
    # Capital - AGGRESSIVE deployment
    total_capital: float = 100000.0
    max_capital_per_trade: float = 80000.0     # RAISED: 80% max (was 50%)
    
    # ═══════════════════════════════════════════════════════════════════════
    # AGGRESSIVE PROBE SETTINGS FOR 300%+ RETURNS
    # ═══════════════════════════════════════════════════════════════════════
    probe_capital_percent: float = 15.0        # RAISED: 15% probe (was 10%)
    probe_stoploss_percent: float = 25.0       # TIGHTER: 25% stop (was 35%)
    
    # Aggressive scale settings
    scale_capital_percent: float = 85.0        # Remaining 85% on scale
    scaled_stoploss_percent: float = 15.0      # TIGHTER: 15% (was 20%)
    
    # NEW: Multi-level scaling for 300%+ returns
    enable_pyramid_scaling: bool = True        # Enable pyramid scaling
    scale_level_1_percent: float = 40.0        # First scale: 40%
    scale_level_2_percent: float = 30.0        # Second scale: 30%
    scale_level_3_percent: float = 15.0        # Third scale: 15%
    
    # ═══════════════════════════════════════════════════════════════════════
    # FASTER CONFIRMATION FOR MOMENTUM CAPTURE
    # ═══════════════════════════════════════════════════════════════════════
    min_profit_to_consider_scale: float = 5.0     # LOWERED: 5% (was 8%) - scale faster
    min_gemini_confidence_to_scale: float = 85.0  # LOWERED: 85% (was 90%) - more scales
    max_probe_loss_to_abort: float = 15.0         # TIGHTER: 15% (was 20%) - cut faster
    
    # Multi-level scale triggers
    scale_level_1_profit: float = 5.0          # Scale 1 at 5% profit
    scale_level_2_profit: float = 12.0         # Scale 2 at 12% profit
    scale_level_3_profit: float = 20.0         # Scale 3 at 20% profit
    
    # ═══════════════════════════════════════════════════════════════════════
    # AGGRESSIVE TRAILING FOR PROFIT MAXIMIZATION
    # ═══════════════════════════════════════════════════════════════════════
    trailing_activation_profit: float = 15.0     # LOWERED: 15% (was 25%) - trail sooner
    trailing_distance_percent: float = 10.0      # TIGHTER: 10% (was 15%) - lock profits
    
    # NEW: Multi-tier trailing
    enable_tiered_trailing: bool = True
    tier_1_profit: float = 15.0                # Tier 1: 15% profit → 10% trail
    tier_1_trail: float = 10.0
    tier_2_profit: float = 30.0                # Tier 2: 30% profit → 8% trail
    tier_2_trail: float = 8.0
    tier_3_profit: float = 50.0                # Tier 3: 50% profit → 5% trail
    tier_3_trail: float = 5.0
    
    # ═══════════════════════════════════════════════════════════════════════
    # FASTER EXECUTION FOR MOMENTUM
    # ═══════════════════════════════════════════════════════════════════════
    probe_timeout_seconds: int = 90              # REDUCED: 90 sec (was 120)
    gemini_check_interval: int = 20              # FASTER: 20 sec (was 30)
    max_holding_minutes: int = 45                # REDUCED: 45 min (was 60)
    
    # Trading mode
    paper_trading: bool = True
    
    # Service URLs
    dhan_backend_url: str = "http://localhost:8000"
    gemini_service_url: str = "http://localhost:4080"


# ============================================================================
# TRADE TRACKING
# ============================================================================

@dataclass
class ProbeScaleTrade:
    """Complete trade record for probe-scale execution"""
    trade_id: str
    signal_id: str
    
    # Instrument
    symbol: str
    option_type: str          # CE or PE
    strike: float
    expiry: str
    lot_size: int
    
    # Capital allocation
    allocated_capital: float
    probe_capital: float      # 10%
    scale_capital: float      # 90% (potential)
    
    # Probe entry
    probe_entry_price: float
    probe_entry_time: datetime
    probe_quantity: int
    probe_stoploss: float     # 50% wide
    
    # Scale entry (filled when scaled)
    scaled: bool = False
    scale_entry_price: float = 0.0
    scale_entry_time: Optional[datetime] = None
    scale_quantity: int = 0
    scale_stoploss: float = 0.0
    
    # Current state
    phase: TradePhase = TradePhase.PROBE
    current_price: float = 0.0
    highest_price: float = 0.0
    lowest_price: float = 0.0
    
    # P&L
    unrealized_pnl: float = 0.0
    pnl_percent: float = 0.0
    
    # Trailing
    trailing_activated: bool = False
    trailing_stop_price: float = 0.0
    
    # Gemini tracking
    gemini_checks: int = 0
    last_gemini_check: Optional[datetime] = None
    last_gemini_decision: str = ""
    momentum_status: str = "STRONG"
    
    # Exit
    exited: bool = False
    exit_price: float = 0.0
    exit_time: Optional[datetime] = None
    exit_reason: str = ""
    realized_pnl: float = 0.0
    
    def total_quantity(self) -> int:
        return self.probe_quantity + self.scale_quantity
    
    def total_capital_used(self) -> float:
        return self.probe_capital + (self.scale_capital if self.scaled else 0)
    
    def avg_entry_price(self) -> float:
        if not self.scaled:
            return self.probe_entry_price
        total_cost = (self.probe_entry_price * self.probe_quantity) + \
                     (self.scale_entry_price * self.scale_quantity)
        return total_cost / self.total_quantity()
    
    def update_price(self, price: float):
        self.current_price = price
        self.highest_price = max(self.highest_price, price)
        if self.lowest_price == 0:
            self.lowest_price = price
        else:
            self.lowest_price = min(self.lowest_price, price)
        
        avg_entry = self.avg_entry_price()
        self.unrealized_pnl = (price - avg_entry) * self.total_quantity() * self.lot_size
        self.pnl_percent = ((price - avg_entry) / avg_entry) * 100 if avg_entry > 0 else 0
    
    def to_dict(self) -> Dict:
        return {
            "trade_id": self.trade_id,
            "symbol": self.symbol,
            "option_type": self.option_type,
            "strike": self.strike,
            "phase": self.phase.value,
            "probe_entry": self.probe_entry_price,
            "scale_entry": self.scale_entry_price if self.scaled else None,
            "current_price": self.current_price,
            "total_quantity": self.total_quantity(),
            "pnl_percent": self.pnl_percent,
            "unrealized_pnl": self.unrealized_pnl,
            "trailing_activated": self.trailing_activated,
            "momentum_status": self.momentum_status,
            "gemini_checks": self.gemini_checks
        }


# ============================================================================
# PROBE-SCALE EXECUTOR
# ============================================================================

class ProbeScaleExecutor:
    """
    Executes trades using probe-scale methodology:
    1. Enter with 10% capital (probe)
    2. If profitable + Gemini confirms → scale to 100%
    3. If losing → exit with minimal loss
    4. Continuous Gemini monitoring for exits
    """
    
    def __init__(self, config: ExecutorConfig = None):
        self.config = config or ExecutorConfig()
        self.gemini = GeminiTradeIntelligence(
            gemini_config=GeminiConfig(
                local_service_url=self.config.gemini_service_url
            ),
            probe_config=ProbeScaleConfig(
                probe_capital_percent=self.config.probe_capital_percent,
                scale_capital_percent=self.config.scale_capital_percent,
                probe_stoploss_percent=self.config.probe_stoploss_percent,
                scaled_stoploss_percent=self.config.scaled_stoploss_percent,
                min_profit_to_confirm_percent=self.config.min_profit_to_consider_scale,
                min_gemini_confidence_to_scale=self.config.min_gemini_confidence_to_scale,
                max_loss_to_abort_percent=self.config.max_probe_loss_to_abort
            )
        )
        
        self.session: Optional[aiohttp.ClientSession] = None
        self.active_trades: Dict[str, ProbeScaleTrade] = {}
        
        # Capital tracking
        self.available_capital = self.config.total_capital
        self.deployed_capital = 0.0
        
        # Monitoring task
        self._monitoring_task: Optional[asyncio.Task] = None
        self._running = False
        
        # Database
        self.db_path = os.path.join(
            os.path.dirname(__file__), 
            "database", 
            "probe_scale_trades.db"
        )
        self._init_database()
        
        logger.info("ProbeScaleExecutor initialized")
        logger.info(f"  Total Capital: ₹{self.config.total_capital:,.2f}")
        logger.info(f"  Probe Size: {self.config.probe_capital_percent}%")
        logger.info(f"  Probe SL: {self.config.probe_stoploss_percent}% (wide)")
    
    def _init_database(self):
        """Initialize SQLite database"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS probe_scale_trades (
                    trade_id TEXT PRIMARY KEY,
                    signal_id TEXT,
                    symbol TEXT,
                    option_type TEXT,
                    strike REAL,
                    expiry TEXT,
                    lot_size INTEGER,
                    allocated_capital REAL,
                    probe_capital REAL,
                    scale_capital REAL,
                    probe_entry_price REAL,
                    probe_entry_time TEXT,
                    probe_quantity INTEGER,
                    probe_stoploss REAL,
                    scaled INTEGER,
                    scale_entry_price REAL,
                    scale_entry_time TEXT,
                    scale_quantity INTEGER,
                    scale_stoploss REAL,
                    phase TEXT,
                    current_price REAL,
                    highest_price REAL,
                    lowest_price REAL,
                    trailing_activated INTEGER,
                    trailing_stop_price REAL,
                    gemini_checks INTEGER,
                    last_gemini_decision TEXT,
                    momentum_status TEXT,
                    exited INTEGER,
                    exit_price REAL,
                    exit_time TEXT,
                    exit_reason TEXT,
                    realized_pnl REAL,
                    created_at TEXT,
                    updated_at TEXT
                )
            """)
            conn.commit()
    
    async def _ensure_session(self):
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=30)
            )
    
    async def close(self):
        """Cleanup"""
        self._running = False
        if self._monitoring_task:
            self._monitoring_task.cancel()
        if self.session and not self.session.closed:
            await self.session.close()
        await self.gemini.close()
    
    # =========================================================================
    # PROBE ENTRY (10% Capital)
    # =========================================================================
    
    async def enter_probe(
        self,
        signal_id: str,
        symbol: str,
        option_type: str,
        strike: float,
        expiry: str,
        entry_price: float,
        lot_size: int,
        allocated_capital: float
    ) -> Optional[ProbeScaleTrade]:
        """
        Enter a probe position with 10% of allocated capital.
        Wide 50% stoploss to allow the trade to breathe.
        """
        
        # Calculate probe size
        probe_capital = allocated_capital * (self.config.probe_capital_percent / 100)
        position_value = entry_price * lot_size
        probe_quantity = max(1, int(probe_capital / position_value))
        actual_probe_capital = probe_quantity * position_value * lot_size
        
        # Wide stoploss (50%)
        probe_stoploss = entry_price * (1 - self.config.probe_stoploss_percent / 100)
        
        trade = ProbeScaleTrade(
            trade_id=f"PS_{uuid.uuid4().hex[:8].upper()}",
            signal_id=signal_id,
            symbol=symbol,
            option_type=option_type,
            strike=strike,
            expiry=expiry,
            lot_size=lot_size,
            allocated_capital=allocated_capital,
            probe_capital=actual_probe_capital,
            scale_capital=allocated_capital - actual_probe_capital,
            probe_entry_price=entry_price,
            probe_entry_time=datetime.now(),
            probe_quantity=probe_quantity,
            probe_stoploss=probe_stoploss,
            current_price=entry_price,
            highest_price=entry_price,
            lowest_price=entry_price,
            phase=TradePhase.PROBE
        )
        
        # Execute probe order
        if self.config.paper_trading:
            logger.info(f"📊 [PAPER] PROBE ENTRY: {symbol} {option_type}")
        else:
            # Real order via Dhan
            success = await self._place_order(
                symbol=symbol,
                option_type=option_type,
                strike=strike,
                expiry=expiry,
                quantity=probe_quantity * lot_size,
                price=entry_price,
                order_type="BUY"
            )
            if not success:
                logger.error(f"Failed to place probe order for {symbol}")
                return None
        
        # Track trade
        self.active_trades[trade.trade_id] = trade
        self.deployed_capital += actual_probe_capital
        self.available_capital -= actual_probe_capital
        
        # Save to database
        self._save_trade(trade)
        
        logger.info(f"✅ PROBE ENTERED: {symbol} {option_type} @ ₹{entry_price:.2f}")
        logger.info(f"   Quantity: {probe_quantity} lots ({probe_quantity * lot_size} shares)")
        logger.info(f"   Capital: ₹{actual_probe_capital:,.2f} (10% of allocation)")
        logger.info(f"   Stoploss: ₹{probe_stoploss:.2f} (50% wide)")
        logger.info(f"   Remaining for scale: ₹{trade.scale_capital:,.2f}")
        
        # Start monitoring if not already running
        if not self._running:
            await self.start_monitoring()
        
        return trade
    
    # =========================================================================
    # SCALE UP (90% Capital on Confirmation)
    # =========================================================================
    
    async def scale_up_trade(self, trade: ProbeScaleTrade) -> bool:
        """
        Scale up trade after Gemini confirmation.
        Adds remaining 90% capital to the position.
        """
        if trade.scaled:
            logger.warning(f"Trade {trade.trade_id} already scaled")
            return False
        
        # Create probe position for Gemini analysis
        probe_position = self._trade_to_probe_position(trade)
        
        # Get scale decision from Gemini
        analysis = await self.gemini.analyze_scale_decision(
            probe_position,
            trade.scale_capital
        )
        
        if analysis.decision != GeminiDecision.SCALE_UP:
            logger.info(f"Gemini doesn't recommend scaling: {analysis.reasoning}")
            trade.last_gemini_decision = analysis.decision.value
            return False
        
        if analysis.confidence < self.config.min_gemini_confidence_to_scale:
            logger.info(f"Gemini confidence too low: {analysis.confidence}%")
            return False
        
        # Calculate scale quantity
        scale_percent = analysis.additional_insights.get("scale_percent", 75)
        actual_scale_capital = trade.scale_capital * (scale_percent / 100)
        position_value = trade.current_price * trade.lot_size
        scale_quantity = max(1, int(actual_scale_capital / position_value))
        
        # New stoploss after scaling (tighter)
        avg_entry = (trade.probe_entry_price * trade.probe_quantity + 
                     trade.current_price * scale_quantity) / (trade.probe_quantity + scale_quantity)
        scale_stoploss = avg_entry * (1 - self.config.scaled_stoploss_percent / 100)
        
        # Execute scale order
        if self.config.paper_trading:
            logger.info(f"📈 [PAPER] SCALE UP: {trade.symbol}")
        else:
            success = await self._place_order(
                symbol=trade.symbol,
                option_type=trade.option_type,
                strike=trade.strike,
                expiry=trade.expiry,
                quantity=scale_quantity * trade.lot_size,
                price=trade.current_price,
                order_type="BUY"
            )
            if not success:
                logger.error(f"Failed to place scale order for {trade.symbol}")
                return False
        
        # Update trade
        trade.scaled = True
        trade.scale_entry_price = trade.current_price
        trade.scale_entry_time = datetime.now()
        trade.scale_quantity = scale_quantity
        trade.scale_stoploss = scale_stoploss
        trade.phase = TradePhase.FULL_POSITION
        trade.last_gemini_decision = "SCALE_UP"
        
        # Update capital tracking
        actual_used = scale_quantity * trade.current_price * trade.lot_size
        self.deployed_capital += actual_used
        self.available_capital -= actual_used
        
        # Save to database
        self._save_trade(trade)
        
        logger.info(f"✅ SCALED UP: {trade.symbol} {trade.option_type}")
        logger.info(f"   Added: {scale_quantity} lots @ ₹{trade.current_price:.2f}")
        logger.info(f"   Total Position: {trade.total_quantity()} lots")
        logger.info(f"   Avg Entry: ₹{trade.avg_entry_price():.2f}")
        logger.info(f"   New Stoploss: ₹{scale_stoploss:.2f} (30%)")
        logger.info(f"   Gemini Confidence: {analysis.confidence}%")
        
        return True
    
    # =========================================================================
    # EXIT MANAGEMENT
    # =========================================================================
    
    async def exit_trade(
        self, 
        trade: ProbeScaleTrade, 
        reason: str,
        exit_percent: float = 100
    ) -> bool:
        """Exit trade (fully or partially)"""
        
        exit_quantity = int(trade.total_quantity() * (exit_percent / 100))
        
        if self.config.paper_trading:
            logger.info(f"🔴 [PAPER] EXIT: {trade.symbol} ({exit_percent}%)")
        else:
            success = await self._place_order(
                symbol=trade.symbol,
                option_type=trade.option_type,
                strike=trade.strike,
                expiry=trade.expiry,
                quantity=exit_quantity * trade.lot_size,
                price=trade.current_price,
                order_type="SELL"
            )
            if not success:
                logger.error(f"Failed to place exit order for {trade.symbol}")
                return False
        
        # Calculate P&L
        avg_entry = trade.avg_entry_price()
        pnl = (trade.current_price - avg_entry) * exit_quantity * trade.lot_size
        
        if exit_percent >= 100:
            # Full exit
            trade.exited = True
            trade.exit_price = trade.current_price
            trade.exit_time = datetime.now()
            trade.exit_reason = reason
            trade.realized_pnl = pnl
            trade.phase = TradePhase.EXITED
            
            # Update capital
            self.deployed_capital -= trade.total_capital_used()
            self.available_capital += trade.total_capital_used() + pnl
            
            # Remove from active
            if trade.trade_id in self.active_trades:
                del self.active_trades[trade.trade_id]
        else:
            # Partial exit - reduce quantities proportionally
            exit_probe = int(trade.probe_quantity * (exit_percent / 100))
            exit_scale = int(trade.scale_quantity * (exit_percent / 100))
            
            trade.probe_quantity -= exit_probe
            trade.scale_quantity -= exit_scale
            trade.realized_pnl += pnl
        
        # Save to database
        self._save_trade(trade)
        
        logger.info(f"✅ EXITED: {trade.symbol} {trade.option_type}")
        logger.info(f"   Reason: {reason}")
        logger.info(f"   Exit Price: ₹{trade.current_price:.2f}")
        logger.info(f"   P&L: ₹{pnl:+,.2f} ({trade.pnl_percent:+.2f}%)")
        
        return True
    
    async def abort_probe(self, trade: ProbeScaleTrade, reason: str) -> bool:
        """
        Abort probe when it fails.
        Uses Gemini for loss minimization strategy.
        """
        probe_position = self._trade_to_probe_position(trade)
        
        # Consult Gemini for loss minimization
        analysis = await self.gemini.analyze_loss_minimization(probe_position)
        
        logger.info(f"⚠️ ABORTING PROBE: {trade.symbol}")
        logger.info(f"   Loss: {trade.pnl_percent:.2f}%")
        logger.info(f"   Gemini Strategy: {analysis.recommended_action}")
        
        trade.phase = TradePhase.ABORTED
        trade.last_gemini_decision = "ABORT"
        
        return await self.exit_trade(trade, f"PROBE_ABORT: {reason}")
    
    # =========================================================================
    # CONTINUOUS MONITORING
    # =========================================================================
    
    async def start_monitoring(self):
        """Start the continuous monitoring loop"""
        if self._running:
            return
        
        self._running = True
        self._monitoring_task = asyncio.create_task(self._monitoring_loop())
        logger.info("🔄 Monitoring started (Gemini check every 30 seconds)")
    
    async def stop_monitoring(self):
        """Stop monitoring"""
        self._running = False
        if self._monitoring_task:
            self._monitoring_task.cancel()
    
    async def _monitoring_loop(self):
        """Main monitoring loop - checks all active trades every 30 seconds"""
        while self._running:
            try:
                for trade_id, trade in list(self.active_trades.items()):
                    if trade.exited:
                        continue
                    
                    await self._monitor_trade(trade)
                
                # Wait for next check
                await asyncio.sleep(self.config.gemini_check_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Monitoring error: {e}")
                await asyncio.sleep(5)
    
    async def _monitor_trade(self, trade: ProbeScaleTrade):
        """Monitor a single trade and take appropriate action"""
        
        # Update price (in real implementation, get from market data)
        # For now, price should be updated externally
        
        trade.gemini_checks += 1
        trade.last_gemini_check = datetime.now()
        
        # Check stoploss first (no AI needed)
        current_sl = trade.scale_stoploss if trade.scaled else trade.probe_stoploss
        if trade.current_price <= current_sl:
            await self.exit_trade(trade, "STOPLOSS_HIT")
            return
        
        # Check trailing stop
        if trade.trailing_activated and trade.current_price <= trade.trailing_stop_price:
            await self.exit_trade(trade, "TRAILING_STOP_HIT")
            return
        
        # Phase-specific handling
        if trade.phase == TradePhase.PROBE:
            await self._handle_probe_phase(trade)
        elif trade.phase == TradePhase.FULL_POSITION:
            await self._handle_full_position_phase(trade)
    
    async def _handle_probe_phase(self, trade: ProbeScaleTrade):
        """Handle probe phase monitoring"""
        
        # Check if probe is profitable enough to consider scaling
        if trade.pnl_percent >= self.config.min_profit_to_consider_scale:
            logger.info(f"📊 Probe profitable ({trade.pnl_percent:.1f}%), checking for scale")
            
            # Get Gemini confirmation
            probe_position = self._trade_to_probe_position(trade)
            analysis = await self.gemini.analyze_probe_confirmation(probe_position)
            
            trade.last_gemini_decision = analysis.decision.value
            trade.momentum_status = analysis.momentum_status.value
            
            if analysis.decision == GeminiDecision.SCALE_UP and \
               analysis.confidence >= self.config.min_gemini_confidence_to_scale:
                # Scale up!
                await self.scale_up_trade(trade)
            else:
                logger.info(f"   Gemini: {analysis.decision.value} (conf: {analysis.confidence}%)")
        
        # Check if probe is losing too much
        elif trade.pnl_percent <= -self.config.max_probe_loss_to_abort:
            logger.warning(f"⚠️ Probe losing {trade.pnl_percent:.1f}%, checking abort")
            await self.abort_probe(trade, f"Loss exceeded {self.config.max_probe_loss_to_abort}%")
        
        # Check probe timeout
        probe_duration = (datetime.now() - trade.probe_entry_time).total_seconds()
        if probe_duration > self.config.probe_timeout_seconds:
            if trade.pnl_percent < self.config.min_profit_to_consider_scale:
                logger.info(f"⏰ Probe timeout without confirmation")
                await self.abort_probe(trade, "PROBE_TIMEOUT")
    
    async def _handle_full_position_phase(self, trade: ProbeScaleTrade):
        """Handle full position monitoring with Gemini exit analysis"""
        
        # Update trailing stop if activated
        if trade.pnl_percent >= self.config.trailing_activation_profit:
            if not trade.trailing_activated:
                trade.trailing_activated = True
                logger.info(f"📈 Trailing stop ACTIVATED for {trade.symbol}")
            
            new_trail = trade.current_price * (1 - self.config.trailing_distance_percent / 100)
            if new_trail > trade.trailing_stop_price:
                trade.trailing_stop_price = new_trail
                logger.debug(f"   Trailing updated to ₹{new_trail:.2f}")
        
        # Get Gemini exit analysis
        probe_position = self._trade_to_probe_position(trade)
        analysis = await self.gemini.analyze_exit(probe_position)
        
        trade.last_gemini_decision = analysis.decision.value
        trade.momentum_status = analysis.momentum_status.value
        
        # Act on Gemini decision
        if analysis.decision == GeminiDecision.FULL_EXIT:
            logger.info(f"🤖 Gemini recommends FULL EXIT: {analysis.reasoning}")
            await self.exit_trade(trade, f"GEMINI_EXIT: {analysis.reasoning}")
            
        elif analysis.decision == GeminiDecision.PARTIAL_EXIT:
            logger.info(f"🤖 Gemini recommends {analysis.exit_percent}% exit")
            await self.exit_trade(trade, "GEMINI_PARTIAL", analysis.exit_percent)
            
        elif analysis.momentum_status in [MomentumStatus.EXHAUSTED, MomentumStatus.REVERSING]:
            logger.warning(f"⚠️ Momentum {analysis.momentum_status.value} - exiting")
            await self.exit_trade(trade, f"MOMENTUM_{analysis.momentum_status.value}")
        
        # Save state
        self._save_trade(trade)
    
    # =========================================================================
    # HELPER METHODS
    # =========================================================================
    
    def _trade_to_probe_position(self, trade: ProbeScaleTrade) -> ProbePosition:
        """Convert trade to ProbePosition for Gemini analysis"""
        return ProbePosition(
            trade_id=trade.trade_id,
            symbol=trade.symbol,
            option_type=trade.option_type,
            strike=trade.strike,
            expiry=trade.expiry,
            entry_price=trade.probe_entry_price,
            entry_time=trade.probe_entry_time,
            probe_quantity=trade.probe_quantity,
            probe_capital=trade.probe_capital,
            current_price=trade.current_price,
            highest_price=trade.highest_price,
            lowest_price=trade.lowest_price,
            stoploss_price=trade.probe_stoploss,
            trailing_stop_price=trade.trailing_stop_price,
            trailing_activated=trade.trailing_activated,
            unrealized_pnl=trade.unrealized_pnl,
            pnl_percent=trade.pnl_percent,
            phase=trade.phase,
            scaled_quantity=trade.scale_quantity,
            scaled_capital=trade.scale_capital if trade.scaled else 0,
            scale_entry_price=trade.scale_entry_price,
            gemini_checks_count=trade.gemini_checks,
            momentum_status=MomentumStatus[trade.momentum_status] if trade.momentum_status else MomentumStatus.STRONG
        )
    
    async def _place_order(
        self,
        symbol: str,
        option_type: str,
        strike: float,
        expiry: str,
        quantity: int,
        price: float,
        order_type: str
    ) -> bool:
        """Place order via Dhan backend"""
        await self._ensure_session()
        
        try:
            async with self.session.post(
                f"{self.config.dhan_backend_url}/api/orders/place",
                json={
                    "symbol": symbol,
                    "option_type": option_type,
                    "strike": strike,
                    "expiry": expiry,
                    "quantity": quantity,
                    "price": price,
                    "order_type": order_type,
                    "product_type": "INTRADAY"
                }
            ) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    return result.get("success", False)
        except Exception as e:
            logger.error(f"Order placement error: {e}")
        
        return False
    
    def _save_trade(self, trade: ProbeScaleTrade):
        """Save trade to database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO probe_scale_trades VALUES (
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
                )
            """, (
                trade.trade_id, trade.signal_id, trade.symbol, trade.option_type,
                trade.strike, trade.expiry, trade.lot_size, trade.allocated_capital,
                trade.probe_capital, trade.scale_capital, trade.probe_entry_price,
                trade.probe_entry_time.isoformat(), trade.probe_quantity,
                trade.probe_stoploss, int(trade.scaled), trade.scale_entry_price,
                trade.scale_entry_time.isoformat() if trade.scale_entry_time else None,
                trade.scale_quantity, trade.scale_stoploss, trade.phase.value,
                trade.current_price, trade.highest_price, trade.lowest_price,
                int(trade.trailing_activated), trade.trailing_stop_price,
                trade.gemini_checks, trade.last_gemini_decision, trade.momentum_status,
                int(trade.exited), trade.exit_price,
                trade.exit_time.isoformat() if trade.exit_time else None,
                trade.exit_reason, trade.realized_pnl,
                datetime.now().isoformat(), datetime.now().isoformat()
            ))
            conn.commit()
    
    def update_price(self, trade_id: str, new_price: float):
        """Update current price for a trade"""
        if trade_id in self.active_trades:
            self.active_trades[trade_id].update_price(new_price)
    
    def get_active_trades(self) -> List[Dict]:
        """Get all active trades"""
        return [trade.to_dict() for trade in self.active_trades.values()]
    
    def get_summary(self) -> Dict:
        """Get executor summary"""
        return {
            "total_capital": self.config.total_capital,
            "available_capital": self.available_capital,
            "deployed_capital": self.deployed_capital,
            "active_trades": len(self.active_trades),
            "trades": self.get_active_trades(),
            "monitoring_active": self._running
        }


# ============================================================================
# API ROUTER
# ============================================================================

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

executor_router = APIRouter()

# Global executor instance
_executor: Optional[ProbeScaleExecutor] = None


def get_executor() -> ProbeScaleExecutor:
    global _executor
    if _executor is None:
        _executor = ProbeScaleExecutor()
    return _executor


class ProbeEntryRequest(BaseModel):
    signal_id: str
    symbol: str
    option_type: str
    strike: float
    expiry: str
    entry_price: float
    lot_size: int
    allocated_capital: float


class UpdatePriceRequest(BaseModel):
    trade_id: str
    new_price: float


class ExitRequest(BaseModel):
    trade_id: str
    exit_percent: float = 100


@executor_router.post("/probe-entry")
async def create_probe_entry(request: ProbeEntryRequest):
    """Enter a new probe position (10% capital)"""
    executor = get_executor()
    
    trade = await executor.enter_probe(
        signal_id=request.signal_id,
        symbol=request.symbol,
        option_type=request.option_type,
        strike=request.strike,
        expiry=request.expiry,
        entry_price=request.entry_price,
        lot_size=request.lot_size,
        allocated_capital=request.allocated_capital
    )
    
    if trade:
        return {"success": True, "trade": trade.to_dict()}
    else:
        raise HTTPException(status_code=500, detail="Failed to enter probe")


@executor_router.post("/update-price")
async def update_trade_price(request: UpdatePriceRequest):
    """Update current price for a trade"""
    executor = get_executor()
    executor.update_price(request.trade_id, request.new_price)
    return {"success": True}


@executor_router.post("/exit")
async def exit_trade(request: ExitRequest):
    """Manually exit a trade"""
    executor = get_executor()
    
    if request.trade_id not in executor.active_trades:
        raise HTTPException(status_code=404, detail="Trade not found")
    
    trade = executor.active_trades[request.trade_id]
    success = await executor.exit_trade(trade, "MANUAL_EXIT", request.exit_percent)
    
    return {"success": success}


@executor_router.get("/trades")
async def get_trades():
    """Get all active trades"""
    executor = get_executor()
    return {"trades": executor.get_active_trades()}


@executor_router.get("/summary")
async def get_summary():
    """Get executor summary"""
    executor = get_executor()
    return executor.get_summary()


@executor_router.post("/start-monitoring")
async def start_monitoring():
    """Start the monitoring loop"""
    executor = get_executor()
    await executor.start_monitoring()
    return {"success": True, "message": "Monitoring started"}


@executor_router.post("/stop-monitoring")
async def stop_monitoring():
    """Stop the monitoring loop"""
    executor = get_executor()
    await executor.stop_monitoring()
    return {"success": True, "message": "Monitoring stopped"}
