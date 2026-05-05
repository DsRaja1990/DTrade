"""
╔══════════════════════════════════════════════════════════════════════════════╗
║             INSTITUTIONAL GRADE CAPITAL MANAGER v4.0                         ║
║        World-Class Fund Management & Intelligent Position Sizing             ║
║                    For AI Scalping Service                                   ║
╚══════════════════════════════════════════════════════════════════════════════╝

Features:
- Dynamic capital allocation with real-time updates
- Intelligent quantity calculation based on VIX-adjusted sizing
- Priority-based instrument allocation (BANKNIFTY last - highest premiums)
- Order slicing for freeze-quantity exceeding trades
- Multi-timeframe risk management
- Integration with Dhan API for live fund data
- Kelly Criterion position sizing with confidence adjustment
"""

import json
import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple, List, Set
from dataclasses import dataclass, field, asdict
from pathlib import Path
from enum import Enum

logger = logging.getLogger(__name__)

# ============================================================================
#                         INDEX INSTRUMENT CONFIGURATION
# ============================================================================

# All available index instruments
ALL_INDEX_INSTRUMENTS = ["NIFTY", "BANKNIFTY", "FINNIFTY", "SENSEX", "BANKEX", "MIDCPNIFTY"]

# Lot sizes for index options (as of Dec 2024 - verified from NSE)
INDEX_LOT_SIZES = {
    "NIFTY": 75,        # NIFTY 50 - 1 lot = 75 qty
    "BANKNIFTY": 35,    # BANK NIFTY - 1 lot = 35 qty (highest premium!)
    "FINNIFTY": 65,     # FIN NIFTY - 1 lot = 65 qty
    "SENSEX": 20,       # SENSEX (BSE) - 1 lot = 20 qty (50 lots = 1000 qty)
    "BANKEX": 30,       # BANKEX (BSE) - 1 lot = 30 qty
    "MIDCPNIFTY": 140,  # MIDCAP NIFTY SELECT - 1 lot = 140 qty
}

# Allocation priority (lower = allocate first, BANKNIFTY last due to high premium)
INSTRUMENT_ALLOCATION_PRIORITY = {
    "NIFTY": 1,         # First priority - moderate premium
    "MIDCPNIFTY": 2,    # Second priority - lower premium, good liquidity
    "SENSEX": 3,        # Third priority - needs many lots for qty
    "FINNIFTY": 4,      # Fourth priority - similar to NIFTY
    "BANKEX": 5,        # Fifth priority
    "BANKNIFTY": 6,     # LAST priority - highest premiums, allocate remaining
}

# Freeze quantities (max shares per single order) - from exchange rules
FREEZE_QUANTITIES = {
    "NIFTY": 1800,       # 24 lots max per order (1800/75)
    "BANKNIFTY": 1050,   # 30 lots max per order (1050/35)
    "FINNIFTY": 1300,    # 20 lots max per order (1300/65)
    "SENSEX": 1000,      # 50 lots max per order (1000/20)
    "BANKEX": 900,       # 30 lots max per order (900/30)
    "MIDCPNIFTY": 2800,  # 20 lots max per order (2800/140)
}

# Approximate index values - used for premium estimation
INDEX_APPROXIMATE_VALUES = {
    "NIFTY": 24500,
    "BANKNIFTY": 52000,
    "FINNIFTY": 24000,
    "SENSEX": 81000,
    "BANKEX": 57000,
    "MIDCPNIFTY": 13000,
}

# Default ATM premium per share (₹) - fallback if live data unavailable
DEFAULT_ATM_PREMIUM_PER_SHARE = {
    "NIFTY": 150,
    "BANKNIFTY": 350,
    "FINNIFTY": 140,
    "SENSEX": 250,
    "BANKEX": 180,
    "MIDCPNIFTY": 80,
}

# ============================================================================
#                         RISK MANAGEMENT CONFIGURATION
# ============================================================================

@dataclass
class RiskConfig:
    """Risk management configuration"""
    max_position_risk_percent: float = 5.0     # Max 5% of capital risk per position (after stop loss)
    max_daily_loss_percent: float = 3.0        # Max 3% daily loss
    max_concurrent_positions: int = 6          # Max open positions
    stop_loss_percent: float = 0.5             # 0.5% stop loss on position value
    take_profit_percent: float = 1.0           # 1.0% take profit (2:1 R:R)
    max_exposure_percent: float = 60.0         # Max 60% of capital deployed at once
    max_capital_per_position_percent: float = 25.0  # Max 25% of capital per single position
    vix_threshold_high: float = 25.0           # Reduce size above this VIX
    vix_threshold_extreme: float = 35.0        # Minimal size above this VIX

# ============================================================================
#                         POSITION SIZING ENGINE
# ============================================================================

class PositionSizingMode(Enum):
    """Position sizing methodology"""
    FIXED = "fixed"                 # Fixed lot count
    KELLY = "kelly"                 # Kelly Criterion based
    CONFIDENCE_SCALED = "confidence" # Scale with signal confidence
    VIX_ADJUSTED = "vix_adjusted"   # Adjust based on VIX
    INSTITUTIONAL = "institutional"  # Full institutional sizing


@dataclass
class PositionSize:
    """Position sizing result"""
    instrument: str
    lot_size: int
    quantity: int
    lots: int
    capital_required: float
    risk_amount: float
    risk_percent: float
    confidence_adjusted: bool
    vix_adjusted: bool
    slicing_required: bool
    num_slices: int = 1
    
    def get_order_slices(self) -> List[int]:
        """Get order quantities for each slice"""
        if not self.slicing_required:
            return [self.quantity]
        
        freeze_qty = FREEZE_QUANTITIES.get(self.instrument, 1800)
        lot_size = INDEX_LOT_SIZES.get(self.instrument, 75)
        
        slices = []
        remaining = self.quantity
        
        while remaining > 0:
            slice_qty = min(remaining, freeze_qty)
            # Round down to complete lots
            slice_lots = slice_qty // lot_size
            slice_qty = slice_lots * lot_size
            
            if slice_qty > 0:
                slices.append(slice_qty)
            remaining -= slice_qty
            
            if remaining > 0 and remaining < lot_size:
                # Remaining is less than 1 lot, skip
                break
        
        return slices if slices else [self.quantity]


class InstitutionalCapitalManager:
    """
    Institutional-grade capital management system.
    
    Features:
    - Dynamic capital allocation across instruments
    - VIX-based position sizing adjustments
    - Kelly Criterion integration
    - Confidence-scaled entries
    - Order slicing for large positions
    - Real-time P&L tracking
    - Priority-based instrument allocation
    """
    
    def __init__(self, config_path: str = None):
        self.config_path = config_path
        self.risk_config = RiskConfig()
        
        # Capital tracking
        self.initial_capital: float = 500000.0  # Default ₹5L
        self.current_capital: float = self.initial_capital
        self.allocated_capital: Dict[str, float] = {}
        self.reserved_capital: float = 0.0
        
        # Enabled instruments
        self.enabled_instruments: Set[str] = {"NIFTY", "BANKNIFTY", "SENSEX"}
        
        # Premium cache (live)
        self._live_premiums: Dict[str, float] = {}
        self._premium_cache_time: Optional[datetime] = None
        
        # Performance tracking
        self.daily_pnl: float = 0.0
        self.realized_pnl: float = 0.0
        self.unrealized_pnl: float = 0.0
        self.win_count: int = 0
        self.loss_count: int = 0
        
        # VIX tracking
        self.current_vix: float = 15.0
        
        # Load config if provided
        if config_path:
            self._load_config(config_path)
        
        logger.info(f"💰 Institutional Capital Manager initialized with ₹{self.initial_capital:,.2f}")
    
    def _load_config(self, config_path: str) -> bool:
        """Load configuration from JSON file"""
        try:
            path = Path(config_path)
            if path.exists():
                with open(path, 'r') as f:
                    config = json.load(f)
                
                self.initial_capital = config.get('initial_capital', self.initial_capital)
                self.current_capital = config.get('current_capital', self.initial_capital)
                self.enabled_instruments = set(config.get('enabled_instruments', list(self.enabled_instruments)))
                
                if 'risk_config' in config:
                    rc = config['risk_config']
                    self.risk_config = RiskConfig(
                        max_position_risk_percent=rc.get('max_position_risk_percent', 2.0),
                        max_daily_loss_percent=rc.get('max_daily_loss_percent', 3.0),
                        max_concurrent_positions=rc.get('max_concurrent_positions', 6),
                        stop_loss_percent=rc.get('stop_loss_percent', 0.5),
                        take_profit_percent=rc.get('take_profit_percent', 1.0),
                        max_exposure_percent=rc.get('max_exposure_percent', 60.0),
                    )
                
                logger.info(f"✓ Loaded capital config: ₹{self.current_capital:,.2f}")
                return True
        except Exception as e:
            logger.error(f"Failed to load capital config: {e}")
        return False
    
    def save_config(self, config_path: str = None) -> bool:
        """Save current configuration to JSON file"""
        try:
            path = Path(config_path or self.config_path or "capital_config.json")
            config = {
                'initial_capital': self.initial_capital,
                'current_capital': self.current_capital,
                'enabled_instruments': list(self.enabled_instruments),
                'risk_config': asdict(self.risk_config),
                'last_updated': datetime.now().isoformat(),
            }
            
            with open(path, 'w') as f:
                json.dump(config, f, indent=2)
            
            logger.info(f"✓ Saved capital config to {path}")
            return True
        except Exception as e:
            logger.error(f"Failed to save capital config: {e}")
        return False
    
    # ========================================================================
    #                         PREMIUM MANAGEMENT
    # ========================================================================
    
    def get_atm_premium(self, instrument: str) -> float:
        """Get ATM premium for instrument (live or default)"""
        inst = instrument.upper()
        if inst in self._live_premiums:
            return self._live_premiums[inst]
        return DEFAULT_ATM_PREMIUM_PER_SHARE.get(inst, 200)
    
    def update_live_premiums(self, premiums: Dict[str, float]):
        """Update live ATM premiums from options chain"""
        self._live_premiums.update(premiums)
        self._premium_cache_time = datetime.now()
        logger.info(f"📊 Updated live premiums: {premiums}")
    
    def update_vix(self, vix_value: float):
        """Update current VIX for position sizing"""
        self.current_vix = vix_value
    
    # ========================================================================
    #                         POSITION SIZING
    # ========================================================================
    
    def calculate_position_size(
        self,
        instrument: str,
        signal_confidence: float = 0.8,
        atm_premium: float = None,
        mode: PositionSizingMode = PositionSizingMode.INSTITUTIONAL,
        win_rate: float = 0.6,
        avg_win_loss_ratio: float = 2.0
    ) -> PositionSize:
        """
        Calculate optimal position size for an instrument.
        
        Args:
            instrument: Index symbol (NIFTY, BANKNIFTY, etc.)
            signal_confidence: Signal confidence (0.0 to 1.0)
            atm_premium: Current ATM option premium (optional)
            mode: Position sizing methodology
            win_rate: Historical win rate for Kelly calculation
            avg_win_loss_ratio: Average win / average loss ratio
        
        Returns:
            PositionSize object with all sizing details
        """
        inst = instrument.upper()
        lot_size = INDEX_LOT_SIZES.get(inst, 75)
        freeze_qty = FREEZE_QUANTITIES.get(inst, 1800)
        
        # Get premium
        premium = atm_premium or self.get_atm_premium(inst)
        
        # Calculate base position size based on mode
        if mode == PositionSizingMode.FIXED:
            lots = self._calculate_fixed_lots(inst)
        elif mode == PositionSizingMode.KELLY:
            lots = self._calculate_kelly_lots(inst, premium, win_rate, avg_win_loss_ratio)
        elif mode == PositionSizingMode.CONFIDENCE_SCALED:
            lots = self._calculate_confidence_lots(inst, premium, signal_confidence)
        elif mode == PositionSizingMode.VIX_ADJUSTED:
            lots = self._calculate_vix_adjusted_lots(inst, premium)
        else:  # INSTITUTIONAL
            lots = self._calculate_institutional_lots(inst, premium, signal_confidence, win_rate, avg_win_loss_ratio)
        
        # Ensure minimum 1 lot
        lots = max(1, lots)
        
        # Calculate quantity
        quantity = lots * lot_size
        
        # Check if slicing required
        slicing_required = quantity > freeze_qty
        num_slices = (quantity // freeze_qty) + (1 if quantity % freeze_qty > 0 else 0)
        
        # Calculate capital required
        capital_required = quantity * premium
        
        # Calculate risk
        risk_amount = capital_required * (self.risk_config.stop_loss_percent / 100)
        risk_percent = (risk_amount / self.current_capital) * 100
        
        return PositionSize(
            instrument=inst,
            lot_size=lot_size,
            quantity=quantity,
            lots=lots,
            capital_required=capital_required,
            risk_amount=risk_amount,
            risk_percent=risk_percent,
            confidence_adjusted=(mode in [PositionSizingMode.CONFIDENCE_SCALED, PositionSizingMode.INSTITUTIONAL]),
            vix_adjusted=(mode in [PositionSizingMode.VIX_ADJUSTED, PositionSizingMode.INSTITUTIONAL]),
            slicing_required=slicing_required,
            num_slices=num_slices
        )
    
    def _calculate_fixed_lots(self, instrument: str) -> int:
        """Calculate fixed lot count based on capital tier"""
        capital = self.current_capital
        
        # Capital tier-based lot allocation
        if capital >= 2000000:  # ≥20L
            base_lots = {"NIFTY": 20, "BANKNIFTY": 15, "SENSEX": 50, "FINNIFTY": 15, "BANKEX": 20, "MIDCPNIFTY": 10}
        elif capital >= 1000000:  # 10-20L
            base_lots = {"NIFTY": 15, "BANKNIFTY": 10, "SENSEX": 40, "FINNIFTY": 10, "BANKEX": 15, "MIDCPNIFTY": 7}
        elif capital >= 500000:  # 5-10L
            base_lots = {"NIFTY": 10, "BANKNIFTY": 7, "SENSEX": 30, "FINNIFTY": 7, "BANKEX": 10, "MIDCPNIFTY": 5}
        elif capital >= 200000:  # 2-5L
            base_lots = {"NIFTY": 5, "BANKNIFTY": 3, "SENSEX": 15, "FINNIFTY": 3, "BANKEX": 5, "MIDCPNIFTY": 2}
        else:  # <2L
            base_lots = {"NIFTY": 2, "BANKNIFTY": 1, "SENSEX": 5, "FINNIFTY": 1, "BANKEX": 2, "MIDCPNIFTY": 1}
        
        return base_lots.get(instrument.upper(), 5)
    
    def _calculate_kelly_lots(
        self,
        instrument: str,
        premium: float,
        win_rate: float,
        avg_win_loss_ratio: float
    ) -> int:
        """Calculate lots using Kelly Criterion"""
        lot_size = INDEX_LOT_SIZES.get(instrument.upper(), 75)
        
        # Kelly Formula: f* = (p * b - q) / b
        # p = win probability, q = 1-p, b = win/loss ratio
        p = win_rate
        q = 1 - p
        b = avg_win_loss_ratio
        
        kelly_fraction = (p * b - q) / b
        
        # Apply half-Kelly for safety
        kelly_fraction = max(0, kelly_fraction) * 0.5
        
        # Calculate position capital
        position_capital = self.current_capital * kelly_fraction
        
        # Calculate lots
        cost_per_lot = lot_size * premium
        if cost_per_lot > 0:
            lots = int(position_capital / cost_per_lot)
        else:
            lots = 1
        
        return max(1, lots)
    
    def _calculate_confidence_lots(
        self,
        instrument: str,
        premium: float,
        signal_confidence: float
    ) -> int:
        """Calculate lots scaled by signal confidence"""
        base_lots = self._calculate_fixed_lots(instrument)
        
        # Scale by confidence: 50% at 0.5 confidence, 100% at 0.9+, 120% at 0.95+
        if signal_confidence >= 0.95:
            confidence_factor = 1.2
        elif signal_confidence >= 0.9:
            confidence_factor = 1.0
        elif signal_confidence >= 0.8:
            confidence_factor = 0.8
        elif signal_confidence >= 0.7:
            confidence_factor = 0.6
        else:
            confidence_factor = 0.5
        
        return max(1, int(base_lots * confidence_factor))
    
    def _calculate_vix_adjusted_lots(self, instrument: str, premium: float) -> int:
        """Calculate lots adjusted for current VIX"""
        base_lots = self._calculate_fixed_lots(instrument)
        
        # VIX adjustment factor
        if self.current_vix >= self.risk_config.vix_threshold_extreme:
            vix_factor = 0.3  # Very small positions in extreme volatility
        elif self.current_vix >= self.risk_config.vix_threshold_high:
            vix_factor = 0.6  # Reduced positions in high volatility
        elif self.current_vix >= 18:
            vix_factor = 0.8  # Slightly reduced
        elif self.current_vix <= 12:
            vix_factor = 1.2  # Can be slightly larger in low vol
        else:
            vix_factor = 1.0  # Normal
        
        return max(1, int(base_lots * vix_factor))
    
    def _calculate_institutional_lots(
        self,
        instrument: str,
        premium: float,
        signal_confidence: float,
        win_rate: float,
        avg_win_loss_ratio: float
    ) -> int:
        """
        Institutional-grade position sizing combining multiple factors:
        - Takes MAXIMUM of Fixed (aggressive) and Kelly (conservative)
        - Applies confidence adjustment
        - Applies VIX adjustment
        - Enforces risk limits
        
        This balances aggressive capital deployment with risk management.
        """
        # Get both calculations
        fixed_lots = self._calculate_fixed_lots(instrument)
        kelly_lots = self._calculate_kelly_lots(instrument, premium, win_rate, avg_win_loss_ratio)
        
        # Use maximum of fixed and kelly for base (aggressive approach)
        # This ensures we deploy capital effectively while respecting Kelly when it suggests more
        base_lots = max(fixed_lots, kelly_lots)
        
        # Apply confidence scaling (0.6 to 1.2 range based on confidence)
        if signal_confidence >= 0.95:
            confidence_factor = 1.2
        elif signal_confidence >= 0.90:
            confidence_factor = 1.0
        elif signal_confidence >= 0.85:
            confidence_factor = 0.9
        elif signal_confidence >= 0.80:
            confidence_factor = 0.8
        elif signal_confidence >= 0.70:
            confidence_factor = 0.7
        else:
            confidence_factor = 0.6
        
        # Apply VIX adjustment
        if self.current_vix >= self.risk_config.vix_threshold_extreme:
            vix_factor = 0.3
        elif self.current_vix >= self.risk_config.vix_threshold_high:
            vix_factor = 0.6
        elif self.current_vix >= 20:
            vix_factor = 0.85
        elif self.current_vix <= 12:
            vix_factor = 1.15
        else:
            vix_factor = 1.0
        
        # Combined lots
        institutional_lots = int(base_lots * confidence_factor * vix_factor)
        
        # Enforce max capital per position limit (e.g., 25% of capital per position)
        lot_size = INDEX_LOT_SIZES.get(instrument.upper(), 75)
        max_capital_per_position = self.current_capital * (self.risk_config.max_capital_per_position_percent / 100)
        cost_per_lot = lot_size * premium
        
        if cost_per_lot > 0:
            max_lots_by_capital = int(max_capital_per_position / cost_per_lot)
            institutional_lots = min(institutional_lots, max_lots_by_capital)
        
        # Also enforce max exposure limit
        max_exposure_capital = self.current_capital * (self.risk_config.max_exposure_percent / 100)
        if cost_per_lot > 0:
            max_lots_by_exposure = int(max_exposure_capital / cost_per_lot)
            institutional_lots = min(institutional_lots, max_lots_by_exposure)
        
        return max(1, institutional_lots)
    
    # ========================================================================
    #                         CAPITAL ALLOCATION
    # ========================================================================
    
    def allocate_capital_by_priority(
        self,
        instruments: List[str] = None
    ) -> Dict[str, Dict]:
        """
        Allocate capital across instruments by priority.
        
        BANKNIFTY (highest premiums) gets whatever capital remains after
        allocating to higher priority instruments.
        
        Returns:
            Dict with allocation details per instrument
        """
        if instruments is None:
            instruments = list(self.enabled_instruments)
        
        # Sort by priority
        sorted_instruments = sorted(
            instruments,
            key=lambda x: INSTRUMENT_ALLOCATION_PRIORITY.get(x.upper(), 99)
        )
        
        # Calculate total available capital for trading
        available_capital = self.current_capital * (self.risk_config.max_exposure_percent / 100)
        available_capital -= self.reserved_capital
        
        allocation = {}
        remaining_capital = available_capital
        num_instruments = len(sorted_instruments)
        
        for i, inst in enumerate(sorted_instruments):
            inst_upper = inst.upper()
            
            # Last instrument (BANKNIFTY) gets all remaining capital
            if i == num_instruments - 1:
                inst_capital = remaining_capital
            else:
                # Others get equal share of remaining
                inst_capital = remaining_capital / (num_instruments - i) * 0.8  # 80% of equal share
            
            # Calculate lots for this allocation
            premium = self.get_atm_premium(inst_upper)
            lot_size = INDEX_LOT_SIZES.get(inst_upper, 75)
            cost_per_lot = lot_size * premium
            
            if cost_per_lot > 0:
                lots = int(inst_capital / cost_per_lot)
            else:
                lots = 0
            
            actual_capital_used = lots * cost_per_lot
            remaining_capital -= actual_capital_used
            
            allocation[inst_upper] = {
                "capital_allocated": actual_capital_used,
                "lots": lots,
                "quantity": lots * lot_size,
                "premium_used": premium,
                "priority": INSTRUMENT_ALLOCATION_PRIORITY.get(inst_upper, 99),
            }
            
            self.allocated_capital[inst_upper] = actual_capital_used
        
        return allocation
    
    # ========================================================================
    #                         P&L TRACKING
    # ========================================================================
    
    def record_trade_result(self, pnl: float, is_win: bool):
        """Record a trade result for P&L tracking"""
        self.daily_pnl += pnl
        self.realized_pnl += pnl
        self.current_capital += pnl
        
        if is_win:
            self.win_count += 1
        else:
            self.loss_count += 1
    
    def get_current_win_rate(self) -> float:
        """Get current session win rate"""
        total = self.win_count + self.loss_count
        if total == 0:
            return 0.6  # Default assumption
        return self.win_count / total
    
    def check_daily_loss_limit(self) -> Tuple[bool, float]:
        """Check if daily loss limit is reached"""
        max_loss = self.initial_capital * (self.risk_config.max_daily_loss_percent / 100)
        is_exceeded = self.daily_pnl <= -max_loss
        return is_exceeded, max_loss
    
    def reset_daily_stats(self):
        """Reset daily statistics (call at market open)"""
        self.daily_pnl = 0.0
        self.unrealized_pnl = 0.0
        self.win_count = 0
        self.loss_count = 0
        logger.info("📊 Daily stats reset")
    
    # ========================================================================
    #                         STATUS & REPORTING
    # ========================================================================
    
    def get_status(self) -> Dict:
        """Get current capital manager status"""
        daily_loss_exceeded, max_daily_loss = self.check_daily_loss_limit()
        
        return {
            "initial_capital": self.initial_capital,
            "current_capital": self.current_capital,
            "daily_pnl": self.daily_pnl,
            "realized_pnl": self.realized_pnl,
            "unrealized_pnl": self.unrealized_pnl,
            "win_count": self.win_count,
            "loss_count": self.loss_count,
            "win_rate": self.get_current_win_rate(),
            "enabled_instruments": list(self.enabled_instruments),
            "allocated_capital": dict(self.allocated_capital),
            "current_vix": self.current_vix,
            "daily_loss_exceeded": daily_loss_exceeded,
            "max_daily_loss": max_daily_loss,
            "risk_config": asdict(self.risk_config),
        }


# ============================================================================
#                         GLOBAL INSTANCE
# ============================================================================

# Create global capital manager instance
capital_manager = InstitutionalCapitalManager()


def get_capital_manager() -> InstitutionalCapitalManager:
    """Get the global capital manager instance"""
    return capital_manager
