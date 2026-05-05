"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                    INTELLIGENT CAPITAL MANAGER v3.0                          ║
║         Dynamic Fund Management & Quantity Calculation System                ║
╚══════════════════════════════════════════════════════════════════════════════╝

Features:
- Dynamic capital allocation with real-time updates
- Intelligent quantity calculation based on available funds
- Risk-based position sizing (max 2-5% per trade based on confidence)
- Auto-fallback to available funds when allocation is insufficient
- Integration with Dhan API for live fund data
- Dynamic instrument selection (NIFTY/BANKNIFTY/FINNIFTY/SENSEX/BANKEX)
- Capital distribution based on selected instruments
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

# ==================== INTELLIGENT INSTRUMENT PROFILES ====================
# This section defines the cost characteristics of each instrument for
# intelligent capital allocation based on actual market requirements.

# Allocation priority (lower = allocate first, BANKNIFTY last due to high premium)
# BANKNIFTY has the highest premiums, so it gets whatever capital remains
INSTRUMENT_ALLOCATION_PRIORITY = {
    "NIFTY": 1,         # First priority - moderate premium
    "MIDCPNIFTY": 2,    # Second priority - lower premium, good liquidity
    "SENSEX": 3,        # Third priority - needs many lots for qty
    "FINNIFTY": 4,      # Fourth priority - similar to NIFTY
    "BANKEX": 5,        # Fifth priority
    "BANKNIFTY": 6,     # LAST priority - highest premiums, allocate remaining
}

# Approximate index values (updated periodically) - used for premium estimation
INDEX_APPROXIMATE_VALUES = {
    "NIFTY": 24500,      # NIFTY 50 around 24,500
    "BANKNIFTY": 52000,  # BANK NIFTY around 52,000
    "FINNIFTY": 24000,   # FINNIFTY around 24,000
    "SENSEX": 81000,     # SENSEX around 81,000 (much higher!)
    "BANKEX": 57000,     # BANKEX around 57,000
    "MIDCPNIFTY": 13000, # MIDCAP NIFTY SELECT around 13,000
}

# Freeze quantities (max shares per single order) - from exchange rules
# Orders above this need to use Dhan's Order Slicing API
FREEZE_QUANTITIES = {
    "NIFTY": 1800,       # 24 lots max per order (1800/75)
    "BANKNIFTY": 1050,   # 30 lots max per order (1050/35)
    "FINNIFTY": 1300,    # 20 lots max per order (1300/65)
    "SENSEX": 1000,      # 50 lots max per order (1000/20)
    "BANKEX": 900,       # 30 lots max per order (900/30)
    "MIDCPNIFTY": 2800,  # 20 lots max per order (2800/140)
}

# Default ATM premium per share (in ₹) - FALLBACK if live data unavailable
# These will be overridden by live options chain data
DEFAULT_ATM_PREMIUM_PER_SHARE = {
    "NIFTY": 150,        # ₹150 per share typical ATM
    "BANKNIFTY": 350,    # ₹350 per share typical ATM (HIGHEST!)
    "FINNIFTY": 140,     # ₹140 per share typical ATM
    "SENSEX": 250,       # ₹250 per share typical ATM
    "BANKEX": 180,       # ₹180 per share typical ATM
    "MIDCPNIFTY": 80,    # ₹80 per share typical ATM (lower premium)
}

# Live premium cache - updated from options chain before trading
_live_atm_premiums: Dict[str, float] = {}
_premium_cache_timestamp: Optional[datetime] = None
_PREMIUM_CACHE_EXPIRY_MINUTES = 5  # Refresh every 5 minutes

def get_atm_premium(instrument: str) -> float:
    """Get ATM premium for instrument (live or default)"""
    inst = instrument.upper()
    # Use live premium if available and fresh
    if inst in _live_atm_premiums:
        return _live_atm_premiums[inst]
    # Fallback to default
    return DEFAULT_ATM_PREMIUM_PER_SHARE.get(inst, 200)

def update_live_premiums(premiums: Dict[str, float]):
    """Update live ATM premiums from options chain"""
    global _live_atm_premiums, _premium_cache_timestamp
    _live_atm_premiums.update(premiums)
    _premium_cache_timestamp = datetime.now()
    logger.info(f"📊 Updated live ATM premiums: {premiums}")

def is_premium_cache_fresh() -> bool:
    """Check if premium cache is still valid"""
    if _premium_cache_timestamp is None:
        return False
    age = (datetime.now() - _premium_cache_timestamp).total_seconds() / 60
    return age < _PREMIUM_CACHE_EXPIRY_MINUTES

def get_premium_cache_status() -> dict:
    """Get current premium cache status"""
    return {
        "live_premiums": dict(_live_atm_premiums),
        "default_premiums": dict(DEFAULT_ATM_PREMIUM_PER_SHARE),
        "cache_timestamp": _premium_cache_timestamp.isoformat() if _premium_cache_timestamp else None,
        "cache_fresh": is_premium_cache_fresh(),
        "cache_expiry_minutes": _PREMIUM_CACHE_EXPIRY_MINUTES,
    }

async def fetch_live_atm_premiums(instruments: List[str] = None) -> Dict[str, float]:
    """
    Fetch live ATM premiums from Dhan options chain.
    
    This function fetches the current day's ATM option premiums for
    each instrument to enable dynamic capital allocation.
    
    Returns:
        Dict mapping instrument name to ATM premium per share
    """
    from dhan_data_client import get_option_chain
    
    if instruments is None:
        instruments = ALL_INDEX_INSTRUMENTS
    
    live_premiums = {}
    
    # Segment mapping for Dhan API
    SEGMENT_MAP = {
        "NIFTY": "NSE_FNO",
        "BANKNIFTY": "NSE_FNO",
        "FINNIFTY": "NSE_FNO",
        "SENSEX": "BSE_FNO",
        "BANKEX": "BSE_FNO",
    }
    
    # Symbol mapping for Dhan API
    SYMBOL_MAP = {
        "NIFTY": "NIFTY",
        "BANKNIFTY": "BANKNIFTY",
        "FINNIFTY": "FINNIFTY",
        "SENSEX": "SENSEX",
        "BANKEX": "BANKEX",
    }
    
    for inst in instruments:
        inst_upper = inst.upper()
        try:
            segment = SEGMENT_MAP.get(inst_upper, "NSE_FNO")
            symbol = SYMBOL_MAP.get(inst_upper, inst_upper)
            
            # Get option chain data
            chain_data = get_option_chain(symbol, segment)
            
            if chain_data and isinstance(chain_data, dict):
                # Find ATM strike (closest to spot price)
                spot_price = chain_data.get("spotPrice", INDEX_APPROXIMATE_VALUES.get(inst_upper, 24500))
                options = chain_data.get("data", [])
                
                if options:
                    # Find ATM strike
                    atm_option = min(options, key=lambda x: abs(x.get("strikePrice", 0) - spot_price))
                    
                    # Get ATM CE premium (or average of CE + PE)
                    ce_premium = atm_option.get("CE", {}).get("ltp", 0) or 0
                    pe_premium = atm_option.get("PE", {}).get("ltp", 0) or 0
                    
                    # Use CE premium as primary, or average if both available
                    if ce_premium > 0 and pe_premium > 0:
                        atm_premium = (ce_premium + pe_premium) / 2
                    elif ce_premium > 0:
                        atm_premium = ce_premium
                    elif pe_premium > 0:
                        atm_premium = pe_premium
                    else:
                        atm_premium = DEFAULT_ATM_PREMIUM_PER_SHARE.get(inst_upper, 200)
                    
                    live_premiums[inst_upper] = round(atm_premium, 2)
                    logger.info(f"📊 {inst_upper} Live ATM Premium: ₹{atm_premium:.2f}/share (spot: {spot_price})")
                else:
                    logger.warning(f"⚠️ No options data for {inst_upper}, using default")
                    live_premiums[inst_upper] = DEFAULT_ATM_PREMIUM_PER_SHARE.get(inst_upper, 200)
            else:
                logger.warning(f"⚠️ Invalid chain data for {inst_upper}, using default")
                live_premiums[inst_upper] = DEFAULT_ATM_PREMIUM_PER_SHARE.get(inst_upper, 200)
                
        except Exception as e:
            logger.error(f"❌ Failed to fetch {inst_upper} option chain: {e}")
            live_premiums[inst_upper] = DEFAULT_ATM_PREMIUM_PER_SHARE.get(inst_upper, 200)
    
    # Update cache
    if live_premiums:
        update_live_premiums(live_premiums)
    
    return live_premiums

def refresh_premiums_sync(instruments: List[str] = None) -> Dict[str, float]:
    """Synchronous wrapper for fetch_live_atm_premiums"""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # Already in async context
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                future = pool.submit(asyncio.run, fetch_live_atm_premiums(instruments))
                return future.result(timeout=30)
        else:
            return asyncio.run(fetch_live_atm_premiums(instruments))
    except Exception as e:
        logger.error(f"Failed to refresh premiums: {e}")
        return dict(DEFAULT_ATM_PREMIUM_PER_SHARE)

# Cost per lot (lot_size × typical_premium) - for capital planning
# NIFTY: 75 × 150 = ₹11,250 per lot
# BANKNIFTY: 30 × 350 = ₹10,500 per lot (but more volatile)
# FINNIFTY: 65 × 140 = ₹9,100 per lot
# SENSEX: 10 × 250 = ₹2,500 per lot (need many lots!)
# BANKEX: 15 × 200 = ₹3,000 per lot

def get_instrument_cost_profile(instrument: str) -> dict:
    """Get cost profile for an instrument using live or default premiums"""
    inst = instrument.upper()
    lot_size = INDEX_LOT_SIZES.get(inst, 75)
    premium = get_atm_premium(inst)  # Uses live or default
    freeze_qty = FREEZE_QUANTITIES.get(inst, 1800)
    index_value = INDEX_APPROXIMATE_VALUES.get(inst, 24500)
    priority = INSTRUMENT_ALLOCATION_PRIORITY.get(inst, 99)
    
    cost_per_lot = lot_size * premium
    max_lots_per_order = freeze_qty // lot_size
    
    # Notional value per lot (for comparing actual exposure)
    notional_per_lot = lot_size * index_value
    
    return {
        "instrument": inst,
        "lot_size": lot_size,
        "atm_premium_per_share": premium,
        "is_live_premium": inst in _live_atm_premiums,
        "cost_per_lot": cost_per_lot,
        "freeze_quantity": freeze_qty,
        "max_lots_per_order": max_lots_per_order,
        "index_value": index_value,
        "notional_per_lot": notional_per_lot,
        "allocation_priority": priority,
    }


def calculate_intelligent_allocation(
    available_capital: float,
    instruments: List[str],
    allocation_mode: str = "priority"
) -> Dict[str, dict]:
    """
    Calculate intelligent capital allocation based on actual instrument costs.
    
    Two allocation modes:
    
    1. "priority" (DEFAULT) - Allocate by priority order, BANKNIFTY gets remaining
       Priority: NIFTY(1) → SENSEX(2) → FINNIFTY(3) → BANKEX(4) → BANKNIFTY(5-last)
       - Allocates equal capital to each priority instrument
       - BANKNIFTY (highest premiums) gets whatever capital remains
    
    2. "weighted" - Allocate proportionally by premium per share
       - Higher premium instruments get more capital
       - Useful when you want equal SHARES across instruments
    
    Example (Priority mode) with ₹5L capital for NIFTY + SENSEX + BANKNIFTY:
    - First: NIFTY gets ₹2L, SENSEX gets ₹2L
    - Last: BANKNIFTY gets remaining ₹1L (lower priority due to high premium)
    
    Example (Weighted mode) with NIFTY + SENSEX:
    - NIFTY premium: ₹150/share → weight 0.25
    - SENSEX premium: ₹450/share → weight 0.75
    - Result: NIFTY 25%, SENSEX 75%
    """
    if not instruments:
        return {}
    
    # Get cost profiles for all instruments
    profiles = {inst.upper(): get_instrument_cost_profile(inst) for inst in instruments}
    
    allocation = {}
    
    if allocation_mode == "priority":
        # Sort by priority (lower number = allocate first)
        # BANKNIFTY (priority 6) will be allocated LAST
        sorted_instruments = sorted(
            [inst.upper() for inst in instruments],
            key=lambda x: INSTRUMENT_ALLOCATION_PRIORITY.get(x, 99)
        )
        
        remaining_capital = available_capital
        non_banknifty = [i for i in sorted_instruments if i != "BANKNIFTY"]
        has_banknifty = "BANKNIFTY" in sorted_instruments
        
        if non_banknifty:
            # Allocate equally among non-BANKNIFTY instruments
            # BANKNIFTY will get whatever remains
            num_priority_instruments = len(non_banknifty)
            per_instrument_capital = remaining_capital / (num_priority_instruments + (1 if has_banknifty else 0))
            
            # If we have BANKNIFTY, give it less - it gets remaining after others
            if has_banknifty and num_priority_instruments > 0:
                # Priority instruments share 80%, BANKNIFTY gets 20%
                priority_share = 0.80
                per_instrument_capital = (remaining_capital * priority_share) / num_priority_instruments
            
            for inst in non_banknifty:
                profile = profiles[inst]
                allocated = per_instrument_capital
                remaining_capital -= allocated
                
                lots_affordable = int(allocated / profile["cost_per_lot"]) if profile["cost_per_lot"] > 0 else 0
                shares_affordable = lots_affordable * profile["lot_size"]
                
                allocation[inst] = {
                    "instrument": inst,
                    "allocated_capital": round(allocated, 2),
                    "allocation_pct": round((allocated / available_capital) * 100, 2),
                    "cost_per_lot": profile["cost_per_lot"],
                    "cost_per_share": profile["atm_premium_per_share"],
                    "is_live_premium": profile["is_live_premium"],
                    "lot_size": profile["lot_size"],
                    "lots_affordable": lots_affordable,
                    "shares_affordable": shares_affordable,
                    "max_lots_per_order": profile["max_lots_per_order"],
                    "need_slicing": lots_affordable > profile["max_lots_per_order"],
                    "freeze_quantity": profile["freeze_quantity"],
                    "notional_per_lot": profile["notional_per_lot"],
                    "allocation_priority": profile["allocation_priority"],
                    "allocation_reason": "priority-based allocation",
                }
        
        # BANKNIFTY gets remaining capital (last priority)
        if has_banknifty:
            profile = profiles["BANKNIFTY"]
            allocated = remaining_capital  # Whatever is left
            
            lots_affordable = int(allocated / profile["cost_per_lot"]) if profile["cost_per_lot"] > 0 else 0
            shares_affordable = lots_affordable * profile["lot_size"]
            
            allocation["BANKNIFTY"] = {
                "instrument": "BANKNIFTY",
                "allocated_capital": round(allocated, 2),
                "allocation_pct": round((allocated / available_capital) * 100, 2) if available_capital > 0 else 0,
                "cost_per_lot": profile["cost_per_lot"],
                "cost_per_share": profile["atm_premium_per_share"],
                "is_live_premium": profile["is_live_premium"],
                "lot_size": profile["lot_size"],
                "lots_affordable": lots_affordable,
                "shares_affordable": shares_affordable,
                "max_lots_per_order": profile["max_lots_per_order"],
                "need_slicing": lots_affordable > profile["max_lots_per_order"],
                "freeze_quantity": profile["freeze_quantity"],
                "notional_per_lot": profile["notional_per_lot"],
                "allocation_priority": profile["allocation_priority"],
                "allocation_reason": "LAST priority - gets remaining capital (high premiums)",
            }
    
    else:  # "weighted" mode
        # Calculate weights based on premium per share
        # Higher premium = needs more capital allocation
        total_premium_weight = sum(p["atm_premium_per_share"] for p in profiles.values())
        
        for inst in [i.upper() for i in instruments]:
            profile = profiles[inst]
            premium_per_share = profile["atm_premium_per_share"]
            
            # Weight by premium per share (higher premium = higher allocation)
            weight = premium_per_share / total_premium_weight if total_premium_weight > 0 else 1/len(instruments)
            
            allocated = available_capital * weight
            lots_affordable = int(allocated / profile["cost_per_lot"]) if profile["cost_per_lot"] > 0 else 0
            shares_affordable = lots_affordable * profile["lot_size"]
            
            allocation[inst] = {
                "instrument": inst,
                "allocated_capital": round(allocated, 2),
                "allocation_pct": round(weight * 100, 2),
                "cost_per_lot": profile["cost_per_lot"],
                "cost_per_share": profile["atm_premium_per_share"],
                "is_live_premium": profile["is_live_premium"],
                "lot_size": profile["lot_size"],
                "lots_affordable": lots_affordable,
                "shares_affordable": shares_affordable,
                "max_lots_per_order": profile["max_lots_per_order"],
                "need_slicing": lots_affordable > profile["max_lots_per_order"],
                "freeze_quantity": profile["freeze_quantity"],
                "notional_per_lot": profile["notional_per_lot"],
                "allocation_priority": profile["allocation_priority"],
                "allocation_reason": "weighted by premium per share",
            }
    
    return allocation


# Instrument correlations (for intelligent capital distribution)
INSTRUMENT_CORRELATIONS = {
    # NIFTY and SENSEX are highly correlated (both broad market indices)
    ("NIFTY", "SENSEX"): 0.95,
    # BANKNIFTY and BANKEX are highly correlated (both banking indices)
    ("BANKNIFTY", "BANKEX"): 0.92,
    # Cross correlations
    ("NIFTY", "BANKNIFTY"): 0.75,
    ("NIFTY", "FINNIFTY"): 0.70,
    ("NIFTY", "BANKEX"): 0.72,
    ("SENSEX", "BANKNIFTY"): 0.73,
    ("SENSEX", "FINNIFTY"): 0.68,
    ("SENSEX", "BANKEX"): 0.70,
    ("BANKNIFTY", "FINNIFTY"): 0.65,
    ("FINNIFTY", "BANKEX"): 0.60,
    ("FINNIFTY", "SENSEX"): 0.68,
}

# Margin requirements (approximate % of premium for buy)
MARGIN_MULTIPLIER = {
    "BUY_CE": 1.0,      # 100% premium for buying calls
    "BUY_PE": 1.0,      # 100% premium for buying puts
    "SELL_CE": 15.0,    # ~15x margin for selling (not used - we only buy)
    "SELL_PE": 15.0,    # ~15x margin for selling (not used - we only buy)
}


class RiskLevel(Enum):
    """Risk levels for position sizing"""
    CONSERVATIVE = 0.02     # 2% max risk per trade
    MODERATE = 0.03         # 3% max risk per trade
    AGGRESSIVE = 0.04       # 4% max risk per trade
    ULTRA = 0.05            # 5% max risk per trade (highest confidence only)


@dataclass
class FundStatus:
    """Current fund status from Dhan"""
    available_balance: float = 0.0
    utilized_amount: float = 0.0
    collateral_amount: float = 0.0
    total_balance: float = 0.0
    withdrawable_balance: float = 0.0
    blocked_amount: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)
    
    @property
    def tradeable_balance(self) -> float:
        """Balance available for new trades"""
        return max(0, self.available_balance - self.blocked_amount)


@dataclass
class CapitalAllocation:
    """Capital allocation configuration with instrument selection"""
    total_capital: float = 100000.0          # Total allocated capital
    max_exposure_pct: float = 0.90           # Max 90% of capital can be used
    max_single_trade_pct: float = 1.0        # Max 100% per single trade (no limit)
    min_cash_reserve_pct: float = 0.05       # Keep 5% as cash reserve
    max_daily_loss_pct: float = 0.10         # Stop trading if 10% daily loss
    max_positions: int = 10                   # Max concurrent positions
    risk_level: RiskLevel = RiskLevel.MODERATE
    
    # Instrument selection - which instruments are enabled for trading
    enabled_instruments: List[str] = field(default_factory=lambda: ["NIFTY", "BANKNIFTY"])
    
    # Tracking
    current_exposure: float = 0.0
    daily_pnl: float = 0.0
    open_positions: int = 0
    last_updated: datetime = field(default_factory=datetime.now)
    
    @property
    def available_for_trading(self) -> float:
        """Capital available for new trades"""
        max_exposure = self.total_capital * self.max_exposure_pct
        reserved = self.total_capital * self.min_cash_reserve_pct
        available = max_exposure - self.current_exposure - reserved
        return max(0, available)
    
    @property
    def max_trade_amount(self) -> float:
        """Maximum amount for a single trade - based on available capital"""
        # No artificial limit - use available capital
        return self.available_for_trading * self.max_single_trade_pct
    
    @property
    def capital_per_instrument(self) -> float:
        """Capital allocated per enabled instrument"""
        if not self.enabled_instruments:
            return 0
        return self.available_for_trading / len(self.enabled_instruments)
    
    @property
    def can_trade(self) -> bool:
        """Check if trading is allowed based on risk limits"""
        # Check daily loss limit
        if self.daily_pnl < -(self.total_capital * self.max_daily_loss_pct):
            return False
        # Check max positions
        if self.open_positions >= self.max_positions:
            return False
        # Check available capital
        if self.available_for_trading < 1000:  # Min ₹1000
            return False
        # Check if any instruments are enabled
        if not self.enabled_instruments:
            return False
        return True
    
    def is_instrument_enabled(self, instrument: str) -> bool:
        """Check if a specific instrument is enabled for trading"""
        return instrument.upper() in [i.upper() for i in self.enabled_instruments]
    
    def get_intelligent_allocation(self, mode: str = "priority") -> Dict[str, dict]:
        """
        Get intelligent capital allocation for enabled instruments.
        
        Two allocation modes:
        
        1. "priority" (DEFAULT): 
           - Allocates equally among non-BANKNIFTY instruments first
           - BANKNIFTY gets remaining capital (LAST due to high premiums)
           - Order: NIFTY → SENSEX → FINNIFTY → BANKEX → BANKNIFTY
        
        2. "weighted":
           - Allocates MORE capital to instruments that cost more per share
           - Results in equal SHARES across instruments
        
        Example with ₹500,000 available and NIFTY + SENSEX + BANKNIFTY:
        Priority mode:
        - NIFTY: ₹166,667 (equal share)
        - SENSEX: ₹166,667 (equal share)
        - BANKNIFTY: ₹166,666 (remaining - last priority)
        """
        return calculate_intelligent_allocation(
            self.available_for_trading,
            self.enabled_instruments,
            allocation_mode=mode
        )
    
    def get_capital_for_instrument(self, instrument: str, mode: str = "priority") -> float:
        """Get intelligently allocated capital for a specific instrument"""
        allocation = self.get_intelligent_allocation(mode=mode)
        inst_alloc = allocation.get(instrument.upper(), {})
        return inst_alloc.get("allocated_capital", 0.0)


@dataclass
class QuantityResult:
    """Result of quantity calculation"""
    quantity: int                    # Number of lots
    total_lots: int                  # Total lots
    lot_size: int                    # Lot size for the instrument
    total_qty: int                   # quantity * lot_size
    premium_per_lot: float           # Premium per lot
    total_investment: float          # Total premium required
    max_loss: float                  # Max possible loss (full premium)
    position_size_pct: float         # % of capital used
    can_afford: bool                 # Whether we can afford this trade
    reason: str                      # Explanation
    # Order slicing information (for quantities exceeding freeze limits)
    need_slicing: bool = False       # Whether order needs to be sliced
    max_lots_per_order: int = 0      # Max lots per single order
    num_orders: int = 1              # Number of orders needed
    freeze_quantity: int = 0         # Freeze quantity limit


class CapitalManager:
    """
    Intelligent Capital Manager for Options Trading v3.0
    
    Manages:
    - Dynamic capital allocation
    - Real-time fund status from Dhan
    - Intelligent quantity calculation
    - Risk-based position sizing
    - Dynamic instrument selection
    - Capital distribution across instruments
    - Order slicing for large orders
    """
    
    def __init__(self, dhan_connector=None, config_path: str = "capital_config.json"):
        self.dhan_connector = dhan_connector
        self.config_path = Path(config_path)
        
        # Initialize allocation
        self.allocation = self._load_config()
        self.fund_status: Optional[FundStatus] = None
        self._last_fund_fetch: datetime = datetime.min
        self._fund_cache_seconds = 30  # Cache fund status for 30 seconds
        
        logger.info(f"💰 Capital Manager v3.0 initialized")
        logger.info(f"   Capital: ₹{self.allocation.total_capital:,.2f}")
        logger.info(f"   Enabled Instruments: {self.allocation.enabled_instruments}")
    
    def _load_config(self) -> CapitalAllocation:
        """Load capital configuration from file"""
        try:
            if self.config_path.exists():
                with open(self.config_path, 'r') as f:
                    data = json.load(f)
                    # Get enabled instruments with default
                    enabled = data.get('enabled_instruments', ["NIFTY", "BANKNIFTY"])
                    # Validate instruments
                    enabled = [i.upper() for i in enabled if i.upper() in ALL_INDEX_INSTRUMENTS]
                    if not enabled:
                        enabled = ["NIFTY", "BANKNIFTY"]
                    
                    alloc = CapitalAllocation(
                        total_capital=data.get('total_capital', 100000),
                        max_exposure_pct=data.get('max_exposure_pct', 0.90),
                        max_single_trade_pct=data.get('max_single_trade_pct', 1.0),
                        min_cash_reserve_pct=data.get('min_cash_reserve_pct', 0.05),
                        max_daily_loss_pct=data.get('max_daily_loss_pct', 0.10),
                        max_positions=data.get('max_positions', 10),
                        risk_level=RiskLevel(data.get('risk_level', 0.03)),
                        enabled_instruments=enabled
                    )
                    logger.info(f"Loaded capital config: ₹{alloc.total_capital:,.2f}")
                    return alloc
        except Exception as e:
            logger.warning(f"Could not load config: {e}, using defaults")
        
        return CapitalAllocation()
    
    def save_config(self):
        """Save current configuration to file"""
        try:
            data = {
                'total_capital': self.allocation.total_capital,
                'max_exposure_pct': self.allocation.max_exposure_pct,
                'max_single_trade_pct': self.allocation.max_single_trade_pct,
                'min_cash_reserve_pct': self.allocation.min_cash_reserve_pct,
                'max_daily_loss_pct': self.allocation.max_daily_loss_pct,
                'max_positions': self.allocation.max_positions,
                'risk_level': self.allocation.risk_level.value,
                'enabled_instruments': self.allocation.enabled_instruments,
                'last_updated': datetime.now().isoformat()
            }
            with open(self.config_path, 'w') as f:
                json.dump(data, f, indent=2)
            logger.info(f"Saved capital config: ₹{self.allocation.total_capital:,.2f}")
        except Exception as e:
            logger.error(f"Failed to save config: {e}")
    
    def set_enabled_instruments(self, instruments: List[str]) -> Dict:
        """
        Set which instruments are enabled for trading.
        
        Args:
            instruments: List of instrument names (NIFTY, BANKNIFTY, FINNIFTY, SENSEX, BANKEX)
            
        Returns:
            Dict with updated instrument configuration
        """
        # Validate and normalize instruments
        valid_instruments = []
        invalid = []
        for inst in instruments:
            inst_upper = inst.upper()
            if inst_upper in ALL_INDEX_INSTRUMENTS:
                if inst_upper not in valid_instruments:
                    valid_instruments.append(inst_upper)
            else:
                invalid.append(inst)
        
        if not valid_instruments:
            return {
                "success": False,
                "error": f"No valid instruments provided. Valid options: {ALL_INDEX_INSTRUMENTS}",
                "invalid_instruments": invalid
            }
        
        old_instruments = self.allocation.enabled_instruments.copy()
        self.allocation.enabled_instruments = valid_instruments
        self.allocation.last_updated = datetime.now()
        self.save_config()
        
        # Calculate capital per instrument
        capital_per_inst = self.allocation.capital_per_instrument
        
        logger.info(f"🎯 Instruments updated: {old_instruments} → {valid_instruments}")
        logger.info(f"   Capital per instrument: ₹{capital_per_inst:,.2f}")
        
        return {
            "success": True,
            "old_instruments": old_instruments,
            "new_instruments": valid_instruments,
            "invalid_instruments": invalid if invalid else None,
            "capital_per_instrument": capital_per_inst,
            "total_available": self.allocation.available_for_trading,
            "instrument_count": len(valid_instruments)
        }
    
    def get_enabled_instruments(self) -> List[str]:
        """Get list of currently enabled instruments"""
        return self.allocation.enabled_instruments.copy()
    
    def is_instrument_tradeable(self, instrument: str) -> Tuple[bool, str]:
        """
        Check if an instrument can be traded.
        
        Returns:
            Tuple of (can_trade, reason)
        """
        instrument = instrument.upper()
        
        if instrument not in ALL_INDEX_INSTRUMENTS:
            return False, f"Unknown instrument: {instrument}"
        
        if not self.allocation.is_instrument_enabled(instrument):
            return False, f"Instrument {instrument} is not enabled. Enabled: {self.allocation.enabled_instruments}"
        
        if not self.allocation.can_trade:
            return False, "Trading disabled (risk limits reached)"
        
        return True, "OK"
    
    def update_capital(self, new_capital: float) -> Dict:
        """
        Dynamically update the allocated capital.
        
        Args:
            new_capital: New capital amount in INR
            
        Returns:
            Dict with updated status
        """
        old_capital = self.allocation.total_capital
        self.allocation.total_capital = max(10000, new_capital)  # Min ₹10,000
        self.allocation.last_updated = datetime.now()
        self.save_config()
        
        logger.info(f"💰 Capital updated: ₹{old_capital:,.2f} → ₹{new_capital:,.2f}")
        
        return {
            "success": True,
            "old_capital": old_capital,
            "new_capital": self.allocation.total_capital,
            "available_for_trading": self.allocation.available_for_trading,
            "max_trade_amount": self.allocation.max_trade_amount,
            "updated_at": datetime.now().isoformat()
        }
    
    async def fetch_fund_status(self, force: bool = False) -> FundStatus:
        """
        Fetch current fund status from Dhan API.
        
        Args:
            force: Force refresh even if cache is valid
            
        Returns:
            FundStatus with current balances
        """
        # Check cache
        if not force and self.fund_status:
            age = (datetime.now() - self._last_fund_fetch).seconds
            if age < self._fund_cache_seconds:
                return self.fund_status
        
        try:
            if self.dhan_connector:
                # Use Dhan API to get fund limits
                result = await asyncio.to_thread(
                    self.dhan_connector.dhan.get_fund_limits
                )
                
                if result and result.get('status') == 'success':
                    data = result.get('data', {})
                    self.fund_status = FundStatus(
                        available_balance=float(data.get('availabelBalance', 0)),
                        utilized_amount=float(data.get('utilizedAmount', 0)),
                        collateral_amount=float(data.get('collateralAmount', 0)),
                        total_balance=float(data.get('sodLimit', 0)),
                        withdrawable_balance=float(data.get('withdrawableBalance', 0)),
                        blocked_amount=float(data.get('blockedPayoutAmount', 0)),
                        timestamp=datetime.now()
                    )
                    self._last_fund_fetch = datetime.now()
                    logger.info(f"📊 Fund status: Available ₹{self.fund_status.available_balance:,.2f}")
                    return self.fund_status
        except Exception as e:
            logger.error(f"Error fetching fund status: {e}")
        
        # Return cached or empty status
        return self.fund_status or FundStatus()
    
    async def calculate_quantity(
        self,
        underlying: str,
        premium: float,
        confidence: float,
        option_type: str = "CE"
    ) -> QuantityResult:
        """
        Calculate optimal quantity based on capital, funds, and confidence.
        
        Logic:
        1. Check allocated capital first
        2. If insufficient, fallback to available funds in account
        3. Apply risk-based position sizing based on confidence
        4. Ensure we don't exceed max position limits
        
        Args:
            underlying: Index name (NIFTY, BANKNIFTY, etc.)
            premium: Option premium per share
            confidence: AI confidence score (0-100)
            option_type: CE or PE
            
        Returns:
            QuantityResult with calculated quantity and details
        """
        underlying = underlying.upper()
        lot_size = INDEX_LOT_SIZES.get(underlying, 75)
        premium_per_lot = premium * lot_size
        
        # Get fresh fund status
        fund_status = await self.fetch_fund_status()
        
        # Calculate position size based on confidence
        position_size_pct = self._get_position_size_for_confidence(confidence)
        
        # Calculate maximum investment amount
        # Step 1: Try allocated capital first
        max_from_allocation = min(
            self.allocation.available_for_trading,
            self.allocation.max_trade_amount,
            self.allocation.total_capital * position_size_pct
        )
        
        # Step 2: If allocation insufficient, check available funds
        max_from_funds = fund_status.tradeable_balance if fund_status else 0
        
        # Use the higher of allocation or available funds (with priority to allocation)
        if max_from_allocation >= premium_per_lot:
            max_investment = max_from_allocation
            source = "allocation"
        elif max_from_funds >= premium_per_lot:
            # Fallback to available funds
            max_investment = min(max_from_funds, self.allocation.total_capital * 0.1)  # Max 10% of capital from funds fallback
            source = "available_funds"
            logger.warning(f"Using available funds fallback: ₹{max_investment:,.2f}")
        else:
            # Insufficient funds
            return QuantityResult(
                quantity=0,
                total_lots=0,
                lot_size=lot_size,
                total_qty=0,
                premium_per_lot=premium_per_lot,
                total_investment=0,
                max_loss=0,
                position_size_pct=0,
                can_afford=False,
                reason=f"Insufficient funds. Need ₹{premium_per_lot:,.2f}, have ₹{max(max_from_allocation, max_from_funds):,.2f}",
                need_slicing=False,
                max_lots_per_order=0,
                num_orders=0,
                freeze_quantity=0
            )
        
        # Get intelligent allocation for this instrument
        intelligent_alloc = self.allocation.get_intelligent_allocation()
        inst_alloc = intelligent_alloc.get(underlying, {})
        
        # Use intelligent allocation capital if available
        if inst_alloc.get("allocated_capital", 0) > 0:
            max_investment = min(max_investment, inst_alloc["allocated_capital"])
            source = "intelligent_allocation"
        
        # Calculate number of lots we can afford
        max_lots = int(max_investment / premium_per_lot)
        
        # Get freeze limits for order slicing
        freeze_qty = FREEZE_QUANTITIES.get(underlying, 1800)
        max_lots_per_order = freeze_qty // lot_size
        
        # Apply limits - use intelligent allocation limits, not hard 10 lot limit
        affordable_lots = inst_alloc.get("lots_affordable", max_lots)
        max_lots = min(max_lots, affordable_lots) if affordable_lots > 0 else max_lots
        max_lots = max(max_lots, 1)   # Minimum 1 lot
        
        # Check if order needs slicing
        need_slicing = max_lots > max_lots_per_order
        num_orders = (max_lots + max_lots_per_order - 1) // max_lots_per_order if need_slicing else 1
        
        # Final calculations
        total_qty = max_lots * lot_size
        total_investment = max_lots * premium_per_lot
        position_pct = total_investment / self.allocation.total_capital * 100
        
        slicing_info = ""
        if need_slicing:
            slicing_info = f" [NEEDS {num_orders} ORDERS - max {max_lots_per_order} lots/order]"
        
        return QuantityResult(
            quantity=max_lots,
            total_lots=max_lots,
            lot_size=lot_size,
            total_qty=total_qty,
            premium_per_lot=premium_per_lot,
            total_investment=total_investment,
            max_loss=total_investment,  # For buy options, max loss = premium paid
            position_size_pct=position_pct,
            can_afford=True,
            reason=f"Calculated {max_lots} lots ({total_qty} qty) using {source}. Investment: ₹{total_investment:,.2f} ({position_pct:.1f}% of capital){slicing_info}",
            # Order slicing info
            need_slicing=need_slicing,
            max_lots_per_order=max_lots_per_order,
            num_orders=num_orders,
            freeze_quantity=freeze_qty
        )
    
    def _get_position_size_for_confidence(self, confidence: float) -> float:
        """
        Get position size percentage based on confidence level.
        
        Higher confidence = larger position (within risk limits)
        """
        if confidence >= 90:
            return 0.05  # 5% for 90%+ confidence
        elif confidence >= 85:
            return 0.04  # 4% for 85-90%
        elif confidence >= 80:
            return 0.03  # 3% for 80-85%
        elif confidence >= 75:
            return 0.025  # 2.5% for 75-80%
        elif confidence >= 70:
            return 0.02  # 2% for 70-75%
        else:
            return 0.015  # 1.5% for <70%
    
    def update_exposure(self, amount: float, is_new_position: bool = True):
        """Update current exposure after trade"""
        if is_new_position:
            self.allocation.current_exposure += amount
            self.allocation.open_positions += 1
        else:
            self.allocation.current_exposure = max(0, self.allocation.current_exposure - amount)
            self.allocation.open_positions = max(0, self.allocation.open_positions - 1)
        
        self.allocation.last_updated = datetime.now()
    
    def update_pnl(self, pnl: float):
        """Update daily P&L"""
        self.allocation.daily_pnl += pnl
        self.allocation.last_updated = datetime.now()
        
        if pnl > 0:
            logger.info(f"💚 P&L Update: +₹{pnl:,.2f} (Daily: ₹{self.allocation.daily_pnl:,.2f})")
        else:
            logger.info(f"🔴 P&L Update: ₹{pnl:,.2f} (Daily: ₹{self.allocation.daily_pnl:,.2f})")
    
    def reset_daily_stats(self):
        """Reset daily statistics (call at start of each trading day)"""
        self.allocation.daily_pnl = 0
        self.allocation.last_updated = datetime.now()
        logger.info("📅 Daily stats reset")
    
    def get_status(self) -> Dict:
        """Get current capital status including intelligent allocation"""
        # Get intelligent allocation for enabled instruments
        intelligent_alloc = self.allocation.get_intelligent_allocation()
        
        return {
            "total_capital": self.allocation.total_capital,
            "current_exposure": self.allocation.current_exposure,
            "available_for_trading": self.allocation.available_for_trading,
            "max_trade_amount": self.allocation.max_trade_amount,
            "daily_pnl": self.allocation.daily_pnl,
            "open_positions": self.allocation.open_positions,
            "max_positions": self.allocation.max_positions,
            "can_trade": self.allocation.can_trade,
            "risk_level": self.allocation.risk_level.name,
            # Instrument configuration
            "enabled_instruments": self.allocation.enabled_instruments,
            "all_instruments": ALL_INDEX_INSTRUMENTS,
            "instrument_count": len(self.allocation.enabled_instruments),
            # Simple equal allocation (legacy)
            "capital_per_instrument": self.allocation.capital_per_instrument,
            # Intelligent allocation (NEW)
            "intelligent_allocation": intelligent_alloc,
            # Fund status
            "fund_status": {
                "available_balance": self.fund_status.available_balance if self.fund_status else 0,
                "utilized_amount": self.fund_status.utilized_amount if self.fund_status else 0,
                "last_updated": self.fund_status.timestamp.isoformat() if self.fund_status else None
            } if self.fund_status else None,
            "last_updated": self.allocation.last_updated.isoformat()
        }


# Singleton instance
_capital_manager: Optional[CapitalManager] = None


def get_capital_manager(dhan_connector=None) -> CapitalManager:
    """Get singleton capital manager instance"""
    global _capital_manager
    if _capital_manager is None:
        _capital_manager = CapitalManager(dhan_connector)
    elif dhan_connector and _capital_manager.dhan_connector is None:
        _capital_manager.dhan_connector = dhan_connector
    return _capital_manager


# Quick test
if __name__ == "__main__":
    async def test():
        manager = CapitalManager()
        
        print("=" * 60)
        print("  💰 CAPITAL MANAGER TEST")
        print("=" * 60)
        
        # Test capital update
        result = manager.update_capital(200000)
        print(f"\n1. Capital Update: {result}")
        
        # Test quantity calculation
        qty_result = await manager.calculate_quantity(
            underlying="NIFTY",
            premium=150,
            confidence=85,
            option_type="PE"
        )
        print(f"\n2. Quantity Calculation:")
        print(f"   {qty_result.reason}")
        print(f"   Lots: {qty_result.quantity}, Total Qty: {qty_result.total_qty}")
        print(f"   Max Loss: ₹{qty_result.max_loss:,.2f}")
        
        # Test status
        status = manager.get_status()
        print(f"\n3. Current Status:")
        print(f"   Capital: ₹{status['total_capital']:,.2f}")
        print(f"   Available: ₹{status['available_for_trading']:,.2f}")
        print(f"   Can Trade: {status['can_trade']}")
    
    asyncio.run(test())
