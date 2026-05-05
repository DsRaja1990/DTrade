"""
╔══════════════════════════════════════════════════════════════════════════════════════╗
║            UNIFIED PROBE-SCALE TRADING SERVICE v1.0                                  ║
║    Complete Integration: Scanner → Probe Entry → Scale → Monitor → Exit             ║
╠══════════════════════════════════════════════════════════════════════════════════════╣
║                                                                                      ║
║  This service orchestrates the complete trading lifecycle:                           ║
║                                                                                      ║
║  1. SCAN: Elite Options Scanner identifies high-conviction opportunities            ║
║  2. PROBE: Enter with 10% capital, 50% wide stoploss                                ║
║  3. CONFIRM: Gemini 3 Pro confirms momentum continuation                            ║
║  4. SCALE: Add remaining 90% capital on confirmation                                ║
║  5. MONITOR: Continuous Gemini 3 Pro exit consultation (every 30 sec)               ║
║  6. EXIT: Intelligent exit based on AI decision or trailing stop                    ║
║                                                                                      ║
╚══════════════════════════════════════════════════════════════════════════════════════╝
"""

import asyncio
import aiohttp
import json
import logging
import os
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from enum import Enum

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s'
)
logger = logging.getLogger(__name__)


# ============================================================================
# CONFIGURATION
# ============================================================================

@dataclass
class UnifiedTradingConfig:
    """Complete trading system configuration"""
    
    # Capital Management
    total_capital: float = 100000.0
    max_capital_per_trade: float = 50000.0
    max_concurrent_trades: int = 3
    reserve_capital_percent: float = 10.0  # Keep 10% as reserve
    
    # Probe-Scale Settings
    probe_capital_percent: float = 10.0      # 10% probe
    scale_capital_percent: float = 90.0      # 90% scale
    probe_stoploss_percent: float = 50.0     # 50% wide stoploss
    scaled_stoploss_percent: float = 30.0    # 30% after scaling
    
    # Confirmation Thresholds
    min_profit_to_scale: float = 10.0        # Need 10% profit on probe
    min_gemini_confidence: float = 85.0      # Need 85% confidence
    max_probe_loss: float = 25.0             # Abort if 25% loss on probe
    
    # Trailing Stop
    trailing_activation: float = 30.0        # Activate at 30% profit
    trailing_distance: float = 20.0          # Trail 20% from peak
    
    # Timing
    gemini_check_interval: int = 30          # Check every 30 seconds
    max_holding_minutes: int = 60            # Max 60 min hold
    probe_timeout_seconds: int = 120         # 2 min probe timeout
    
    # Scanning
    scan_interval_seconds: int = 60          # Scan every 60 seconds
    min_scan_confidence: float = 80.0        # Minimum signal confidence
    preferred_instruments: List[str] = field(default_factory=lambda: [
        "NIFTY", "BANKNIFTY", "RELIANCE", "TCS", "INFY", "HDFCBANK", "ICICIBANK"
    ])
    
    # Service URLs
    gemini_service_url: str = "http://localhost:4080"
    dhan_backend_url: str = "http://localhost:8000"
    
    # Mode
    paper_trading: bool = True


# ============================================================================
# UNIFIED TRADING SERVICE
# ============================================================================

class UnifiedTradingService:
    """
    Complete trading service that:
    1. Scans for opportunities
    2. Enters probes
    3. Scales on confirmation
    4. Monitors with Gemini
    5. Exits intelligently
    """
    
    def __init__(self, config: UnifiedTradingConfig = None):
        self.config = config or UnifiedTradingConfig()
        self.session: Optional[aiohttp.ClientSession] = None
        
        # State
        self.active_trades: Dict[str, Dict] = {}
        self.trade_history: List[Dict] = []
        
        # Capital tracking
        self.available_capital = self.config.total_capital * (1 - self.config.reserve_capital_percent / 100)
        self.deployed_capital = 0.0
        self.daily_pnl = 0.0
        
        # Running state
        self._running = False
        self._scan_task: Optional[asyncio.Task] = None
        self._monitor_task: Optional[asyncio.Task] = None
        
        logger.info("=" * 70)
        logger.info("UNIFIED PROBE-SCALE TRADING SERVICE INITIALIZED")
        logger.info("=" * 70)
        logger.info(f"Total Capital: ₹{self.config.total_capital:,.2f}")
        logger.info(f"Available for Trading: ₹{self.available_capital:,.2f}")
        logger.info(f"Probe Size: {self.config.probe_capital_percent}% | Scale: {self.config.scale_capital_percent}%")
        logger.info(f"Probe SL: {self.config.probe_stoploss_percent}% (wide)")
        logger.info(f"Paper Trading: {self.config.paper_trading}")
        logger.info("=" * 70)
    
    async def _ensure_session(self):
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=60)
            )
    
    async def close(self):
        """Cleanup resources"""
        self._running = False
        if self._scan_task:
            self._scan_task.cancel()
        if self._monitor_task:
            self._monitor_task.cancel()
        if self.session and not self.session.closed:
            await self.session.close()
    
    # =========================================================================
    # MAIN LOOP
    # =========================================================================
    
    async def start(self):
        """Start the unified trading service"""
        if self._running:
            logger.warning("Service already running")
            return
        
        self._running = True
        logger.info("🚀 Starting Unified Trading Service...")
        
        # Start scanning loop
        self._scan_task = asyncio.create_task(self._scanning_loop())
        
        # Start monitoring loop
        self._monitor_task = asyncio.create_task(self._monitoring_loop())
        
        logger.info("✅ Service started successfully")
    
    async def stop(self):
        """Stop the trading service"""
        logger.info("Stopping Unified Trading Service...")
        self._running = False
        
        if self._scan_task:
            self._scan_task.cancel()
        if self._monitor_task:
            self._monitor_task.cancel()
        
        logger.info("Service stopped")
    
    async def _scanning_loop(self):
        """Continuously scan for trading opportunities"""
        while self._running:
            try:
                # Check if we can take more trades
                if len(self.active_trades) >= self.config.max_concurrent_trades:
                    logger.debug("Max concurrent trades reached, skipping scan")
                    await asyncio.sleep(self.config.scan_interval_seconds)
                    continue
                
                if self.available_capital < self.config.max_capital_per_trade * 0.1:
                    logger.debug("Insufficient capital for new trades")
                    await asyncio.sleep(self.config.scan_interval_seconds)
                    continue
                
                # Scan for opportunities
                opportunities = await self._scan_for_opportunities()
                
                for opp in opportunities:
                    if len(self.active_trades) >= self.config.max_concurrent_trades:
                        break
                    
                    if opp.get('confidence', 0) >= self.config.min_scan_confidence:
                        await self._enter_probe(opp)
                
                await asyncio.sleep(self.config.scan_interval_seconds)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Scanning error: {e}")
                await asyncio.sleep(10)
    
    async def _monitoring_loop(self):
        """Monitor all active trades"""
        while self._running:
            try:
                for trade_id, trade in list(self.active_trades.items()):
                    await self._monitor_trade(trade)
                
                await asyncio.sleep(self.config.gemini_check_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Monitoring error: {e}")
                await asyncio.sleep(5)
    
    # =========================================================================
    # SCANNING
    # =========================================================================
    
    async def _scan_for_opportunities(self) -> List[Dict]:
        """Scan for trading opportunities using Gemini service"""
        await self._ensure_session()
        opportunities = []
        
        try:
            # Get momentum stocks from Gemini service
            async with self.session.get(
                f"{self.config.gemini_service_url}/api/screener/fo-signals"
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    signals = data.get('signals', [])
                    
                    for signal in signals[:5]:  # Top 5
                        if signal.get('confidence', 0) >= self.config.min_scan_confidence:
                            opportunities.append({
                                'symbol': signal.get('symbol'),
                                'option_type': 'CE' if signal.get('direction') == 'bullish' else 'PE',
                                'strike': signal.get('atm_strike', 0),
                                'entry_price': signal.get('entry_price', 0),
                                'confidence': signal.get('confidence', 0),
                                'lot_size': signal.get('lot_size', 50),
                                'expiry': signal.get('expiry', ''),
                                'reason': signal.get('reason', '')
                            })
            
            if opportunities:
                logger.info(f"📊 Found {len(opportunities)} opportunities")
                for opp in opportunities:
                    logger.info(f"   {opp['symbol']} {opp['option_type']} - Conf: {opp['confidence']}%")
                    
        except Exception as e:
            logger.error(f"Scan error: {e}")
        
        return opportunities
    
    # =========================================================================
    # PROBE ENTRY
    # =========================================================================
    
    async def _enter_probe(self, opportunity: Dict) -> Optional[str]:
        """Enter a probe position with 10% capital"""
        
        symbol = opportunity['symbol']
        option_type = opportunity['option_type']
        entry_price = opportunity.get('entry_price', 0)
        
        if entry_price <= 0:
            logger.warning(f"Invalid entry price for {symbol}")
            return None
        
        # Calculate allocation
        allocated_capital = min(
            self.config.max_capital_per_trade,
            self.available_capital * 0.5  # Max 50% of available
        )
        
        probe_capital = allocated_capital * (self.config.probe_capital_percent / 100)
        lot_size = opportunity.get('lot_size', 50)
        position_value = entry_price * lot_size
        probe_quantity = max(1, int(probe_capital / position_value))
        actual_probe_capital = probe_quantity * position_value
        
        # Wide stoploss (50%)
        stoploss = entry_price * (1 - self.config.probe_stoploss_percent / 100)
        
        # Create trade record
        import uuid
        trade_id = f"PS_{uuid.uuid4().hex[:8].upper()}"
        
        trade = {
            'trade_id': trade_id,
            'symbol': symbol,
            'option_type': option_type,
            'strike': opportunity.get('strike', 0),
            'expiry': opportunity.get('expiry', ''),
            'lot_size': lot_size,
            
            # Capital
            'allocated_capital': allocated_capital,
            'probe_capital': actual_probe_capital,
            'scale_capital': allocated_capital - actual_probe_capital,
            
            # Probe entry
            'probe_entry_price': entry_price,
            'probe_entry_time': datetime.now().isoformat(),
            'probe_quantity': probe_quantity,
            'probe_stoploss': stoploss,
            
            # State
            'phase': 'PROBE',
            'scaled': False,
            'current_price': entry_price,
            'highest_price': entry_price,
            'pnl_percent': 0.0,
            
            # Trailing
            'trailing_activated': False,
            'trailing_stop': 0,
            
            # Gemini
            'gemini_checks': 0,
            'last_gemini_decision': '',
            'momentum_status': 'STRONG',
            
            # Reason
            'entry_reason': opportunity.get('reason', 'AI Signal')
        }
        
        # Execute (paper or real)
        if self.config.paper_trading:
            logger.info(f"📊 [PAPER] PROBE ENTRY: {symbol} {option_type}")
        else:
            success = await self._place_order(trade, 'BUY', probe_quantity)
            if not success:
                return None
        
        # Track
        self.active_trades[trade_id] = trade
        self.available_capital -= actual_probe_capital
        self.deployed_capital += actual_probe_capital
        
        logger.info("=" * 50)
        logger.info(f"✅ PROBE ENTERED: {symbol} {option_type}")
        logger.info(f"   Trade ID: {trade_id}")
        logger.info(f"   Entry: ₹{entry_price:.2f}")
        logger.info(f"   Quantity: {probe_quantity} lots ({probe_quantity * lot_size} shares)")
        logger.info(f"   Capital: ₹{actual_probe_capital:,.2f} (10%)")
        logger.info(f"   Stoploss: ₹{stoploss:.2f} (50% wide)")
        logger.info(f"   Remaining for scale: ₹{trade['scale_capital']:,.2f}")
        logger.info("=" * 50)
        
        return trade_id
    
    # =========================================================================
    # MONITORING
    # =========================================================================
    
    async def _monitor_trade(self, trade: Dict):
        """Monitor a single trade and take action"""
        
        trade_id = trade['trade_id']
        trade['gemini_checks'] += 1
        
        # Update price (simulated for paper, real for live)
        current_price = await self._get_current_price(trade)
        trade['current_price'] = current_price
        trade['highest_price'] = max(trade['highest_price'], current_price)
        
        # Calculate P&L
        if trade['scaled']:
            avg_entry = (trade['probe_entry_price'] * trade['probe_quantity'] + 
                        trade.get('scale_entry_price', 0) * trade.get('scale_quantity', 0)) / \
                       (trade['probe_quantity'] + trade.get('scale_quantity', 0))
        else:
            avg_entry = trade['probe_entry_price']
        
        trade['pnl_percent'] = ((current_price - avg_entry) / avg_entry) * 100
        
        # Check hard stoploss first (no AI needed)
        current_sl = trade.get('scale_stoploss') if trade['scaled'] else trade['probe_stoploss']
        if current_price <= current_sl:
            await self._exit_trade(trade, 'STOPLOSS_HIT')
            return
        
        # Check trailing stop
        if trade['trailing_activated'] and current_price <= trade['trailing_stop']:
            await self._exit_trade(trade, 'TRAILING_STOP_HIT')
            return
        
        # Phase-specific handling
        if trade['phase'] == 'PROBE':
            await self._handle_probe_phase(trade)
        elif trade['phase'] == 'FULL_POSITION':
            await self._handle_full_position(trade)
    
    async def _handle_probe_phase(self, trade: Dict):
        """Handle probe phase - check for scaling or abort"""
        
        # Check if profitable enough to scale
        if trade['pnl_percent'] >= self.config.min_profit_to_scale:
            logger.info(f"📈 Probe profitable ({trade['pnl_percent']:.1f}%), checking scale")
            
            # Consult Gemini for confirmation
            analysis = await self._consult_gemini_probe_confirmation(trade)
            trade['last_gemini_decision'] = analysis.get('decision', 'UNKNOWN')
            trade['momentum_status'] = analysis.get('momentum_status', 'MODERATE')
            
            if analysis.get('decision') == 'SCALE_UP' and \
               analysis.get('confidence', 0) >= self.config.min_gemini_confidence:
                await self._scale_up(trade)
            else:
                logger.info(f"   Gemini: {analysis.get('decision')} (conf: {analysis.get('confidence')}%)")
        
        # Check if losing too much
        elif trade['pnl_percent'] <= -self.config.max_probe_loss:
            logger.warning(f"⚠️ Probe losing {trade['pnl_percent']:.1f}%")
            await self._abort_probe(trade)
        
        # Check timeout
        entry_time = datetime.fromisoformat(trade['probe_entry_time'])
        elapsed = (datetime.now() - entry_time).total_seconds()
        
        if elapsed > self.config.probe_timeout_seconds:
            if trade['pnl_percent'] < self.config.min_profit_to_scale:
                logger.info("⏰ Probe timeout without confirmation")
                await self._abort_probe(trade)
    
    async def _handle_full_position(self, trade: Dict):
        """Handle full position - check exit conditions"""
        
        # Update trailing stop
        if trade['pnl_percent'] >= self.config.trailing_activation:
            if not trade['trailing_activated']:
                trade['trailing_activated'] = True
                logger.info(f"📈 Trailing stop ACTIVATED for {trade['symbol']}")
            
            new_trail = trade['current_price'] * (1 - self.config.trailing_distance / 100)
            if new_trail > trade['trailing_stop']:
                trade['trailing_stop'] = new_trail
        
        # Consult Gemini for exit analysis
        analysis = await self._consult_gemini_exit(trade)
        trade['last_gemini_decision'] = analysis.get('decision', 'UNKNOWN')
        trade['momentum_status'] = analysis.get('momentum_status', 'MODERATE')
        
        # Act on decision
        if analysis.get('decision') == 'FULL_EXIT':
            logger.info(f"🤖 Gemini: FULL EXIT - {analysis.get('reasoning', '')[:50]}")
            await self._exit_trade(trade, f"GEMINI_EXIT: {analysis.get('reasoning', '')[:30]}")
        
        elif analysis.get('decision') == 'PARTIAL_EXIT':
            exit_pct = analysis.get('exit_percent', 50)
            logger.info(f"🤖 Gemini: {exit_pct}% EXIT")
            await self._partial_exit(trade, exit_pct)
        
        elif analysis.get('momentum_status') in ['EXHAUSTED', 'REVERSING']:
            logger.warning(f"⚠️ Momentum {analysis.get('momentum_status')} - exiting")
            await self._exit_trade(trade, f"MOMENTUM_{analysis.get('momentum_status')}")
    
    # =========================================================================
    # SCALING
    # =========================================================================
    
    async def _scale_up(self, trade: Dict):
        """Scale up position after probe confirmation"""
        
        if trade['scaled']:
            return
        
        # Get scale decision from Gemini
        analysis = await self._consult_gemini_scale(trade)
        
        if analysis.get('decision') != 'SCALE_UP':
            logger.info(f"Gemini doesn't recommend scaling: {analysis.get('reasoning', '')[:50]}")
            return
        
        # Calculate scale quantity
        scale_percent = analysis.get('scale_percent', 75)
        scale_capital = trade['scale_capital'] * (scale_percent / 100)
        lot_size = trade['lot_size']
        current_price = trade['current_price']
        position_value = current_price * lot_size
        scale_quantity = max(1, int(scale_capital / position_value))
        
        # New stoploss (tighter)
        total_qty = trade['probe_quantity'] + scale_quantity
        avg_entry = (trade['probe_entry_price'] * trade['probe_quantity'] + 
                    current_price * scale_quantity) / total_qty
        scale_stoploss = avg_entry * (1 - self.config.scaled_stoploss_percent / 100)
        
        # Execute scale
        if self.config.paper_trading:
            logger.info(f"📈 [PAPER] SCALE UP: {trade['symbol']}")
        else:
            success = await self._place_order(trade, 'BUY', scale_quantity)
            if not success:
                return
        
        # Update trade
        trade['scaled'] = True
        trade['scale_entry_price'] = current_price
        trade['scale_entry_time'] = datetime.now().isoformat()
        trade['scale_quantity'] = scale_quantity
        trade['scale_stoploss'] = scale_stoploss
        trade['phase'] = 'FULL_POSITION'
        
        # Update capital
        actual_scale = scale_quantity * current_price * lot_size
        self.available_capital -= actual_scale
        self.deployed_capital += actual_scale
        
        logger.info("=" * 50)
        logger.info(f"✅ SCALED UP: {trade['symbol']} {trade['option_type']}")
        logger.info(f"   Added: {scale_quantity} lots @ ₹{current_price:.2f}")
        logger.info(f"   Total: {total_qty} lots")
        logger.info(f"   Avg Entry: ₹{avg_entry:.2f}")
        logger.info(f"   New SL: ₹{scale_stoploss:.2f} (30%)")
        logger.info(f"   Gemini Conf: {analysis.get('confidence', 0)}%")
        logger.info("=" * 50)
    
    # =========================================================================
    # EXIT
    # =========================================================================
    
    async def _exit_trade(self, trade: Dict, reason: str):
        """Exit trade completely"""
        
        total_qty = trade['probe_quantity'] + trade.get('scale_quantity', 0)
        
        if self.config.paper_trading:
            logger.info(f"🔴 [PAPER] EXIT: {trade['symbol']} ({total_qty} lots)")
        else:
            await self._place_order(trade, 'SELL', total_qty)
        
        # Calculate P&L
        avg_entry = trade['probe_entry_price']
        if trade['scaled']:
            avg_entry = (trade['probe_entry_price'] * trade['probe_quantity'] + 
                        trade['scale_entry_price'] * trade['scale_quantity']) / total_qty
        
        pnl = (trade['current_price'] - avg_entry) * total_qty * trade['lot_size']
        
        # Update state
        trade['phase'] = 'EXITED'
        trade['exit_price'] = trade['current_price']
        trade['exit_time'] = datetime.now().isoformat()
        trade['exit_reason'] = reason
        trade['realized_pnl'] = pnl
        
        # Update capital
        capital_used = trade['probe_capital']
        if trade['scaled']:
            capital_used += trade['scale_quantity'] * trade['scale_entry_price'] * trade['lot_size']
        
        self.deployed_capital -= capital_used
        self.available_capital += capital_used + pnl
        self.daily_pnl += pnl
        
        # Move to history
        self.trade_history.append(trade)
        if trade['trade_id'] in self.active_trades:
            del self.active_trades[trade['trade_id']]
        
        logger.info("=" * 50)
        logger.info(f"✅ EXITED: {trade['symbol']} {trade['option_type']}")
        logger.info(f"   Reason: {reason}")
        logger.info(f"   Exit Price: ₹{trade['current_price']:.2f}")
        logger.info(f"   P&L: ₹{pnl:+,.2f} ({trade['pnl_percent']:+.2f}%)")
        logger.info(f"   Daily P&L: ₹{self.daily_pnl:+,.2f}")
        logger.info("=" * 50)
    
    async def _partial_exit(self, trade: Dict, exit_percent: float):
        """Partial exit"""
        total_qty = trade['probe_quantity'] + trade.get('scale_quantity', 0)
        exit_qty = int(total_qty * (exit_percent / 100))
        
        if exit_qty <= 0:
            return
        
        if self.config.paper_trading:
            logger.info(f"🔴 [PAPER] PARTIAL EXIT: {trade['symbol']} ({exit_qty} lots)")
        else:
            await self._place_order(trade, 'SELL', exit_qty)
        
        # Reduce quantities proportionally
        probe_exit = int(trade['probe_quantity'] * (exit_percent / 100))
        scale_exit = exit_qty - probe_exit
        
        trade['probe_quantity'] -= probe_exit
        if trade.get('scale_quantity'):
            trade['scale_quantity'] -= scale_exit
        
        logger.info(f"   Remaining: {trade['probe_quantity'] + trade.get('scale_quantity', 0)} lots")
    
    async def _abort_probe(self, trade: Dict):
        """Abort failing probe with minimal loss"""
        
        # Consult Gemini for loss minimization
        analysis = await self._consult_gemini_loss_minimization(trade)
        
        logger.info(f"⚠️ ABORTING PROBE: {trade['symbol']}")
        logger.info(f"   Loss: {trade['pnl_percent']:.2f}%")
        logger.info(f"   Gemini: {analysis.get('recommended_action', 'EXIT')}")
        
        trade['phase'] = 'ABORTED'
        await self._exit_trade(trade, f"PROBE_ABORT: Loss {trade['pnl_percent']:.1f}%")
    
    # =========================================================================
    # GEMINI CONSULTATIONS
    # =========================================================================
    
    async def _consult_gemini_probe_confirmation(self, trade: Dict) -> Dict:
        """Consult Gemini for probe confirmation"""
        await self._ensure_session()
        
        try:
            async with self.session.post(
                f"{self.config.gemini_service_url}/api/gemini/probe-confirmation",
                json={
                    'trade_id': trade['trade_id'],
                    'symbol': trade['symbol'],
                    'option_type': trade['option_type'],
                    'strike': trade['strike'],
                    'entry_price': trade['probe_entry_price'],
                    'current_price': trade['current_price'],
                    'highest_price': trade['highest_price'],
                    'pnl_percent': trade['pnl_percent'],
                    'probe_quantity': trade['probe_quantity'],
                    'probe_capital': trade['probe_capital'],
                    'entry_time': trade['probe_entry_time'],
                    'time_in_trade_minutes': (datetime.now() - datetime.fromisoformat(trade['probe_entry_time'])).total_seconds() / 60
                }
            ) as resp:
                if resp.status == 200:
                    return await resp.json()
        except Exception as e:
            logger.error(f"Gemini probe confirmation error: {e}")
        
        return {'decision': 'HOLD', 'confidence': 50}
    
    async def _consult_gemini_scale(self, trade: Dict) -> Dict:
        """Consult Gemini for scale decision"""
        await self._ensure_session()
        
        try:
            async with self.session.post(
                f"{self.config.gemini_service_url}/api/gemini/scale-decision",
                json={
                    'trade_id': trade['trade_id'],
                    'symbol': trade['symbol'],
                    'option_type': trade['option_type'],
                    'strike': trade['strike'],
                    'current_price': trade['current_price'],
                    'pnl_percent': trade['pnl_percent'],
                    'remaining_capital': trade['scale_capital'],
                    'momentum_status': trade['momentum_status']
                }
            ) as resp:
                if resp.status == 200:
                    return await resp.json()
        except Exception as e:
            logger.error(f"Gemini scale decision error: {e}")
        
        return {'decision': 'HOLD', 'confidence': 50, 'scale_percent': 0}
    
    async def _consult_gemini_exit(self, trade: Dict) -> Dict:
        """Consult Gemini for exit analysis"""
        await self._ensure_session()
        
        try:
            total_qty = trade['probe_quantity'] + trade.get('scale_quantity', 0)
            total_capital = trade['probe_capital']
            if trade['scaled']:
                total_capital += trade['scale_quantity'] * trade['scale_entry_price'] * trade['lot_size']
            
            async with self.session.post(
                f"{self.config.gemini_service_url}/api/gemini/exit-analysis",
                json={
                    'trade_id': trade['trade_id'],
                    'symbol': trade['symbol'],
                    'option_type': trade['option_type'],
                    'strike': trade['strike'],
                    'entry_price': trade['probe_entry_price'],
                    'current_price': trade['current_price'],
                    'highest_price': trade['highest_price'],
                    'pnl_percent': trade['pnl_percent'],
                    'total_quantity': total_qty,
                    'total_capital': total_capital,
                    'stoploss_price': trade.get('scale_stoploss', trade['probe_stoploss']),
                    'trailing_stop_price': trade['trailing_stop'],
                    'trailing_activated': trade['trailing_activated'],
                    'time_in_trade_minutes': (datetime.now() - datetime.fromisoformat(trade['probe_entry_time'])).total_seconds() / 60
                }
            ) as resp:
                if resp.status == 200:
                    return await resp.json()
        except Exception as e:
            logger.error(f"Gemini exit analysis error: {e}")
        
        return {'decision': 'HOLD', 'confidence': 50, 'momentum_status': 'MODERATE'}
    
    async def _consult_gemini_loss_minimization(self, trade: Dict) -> Dict:
        """Consult Gemini for loss minimization"""
        await self._ensure_session()
        
        try:
            async with self.session.post(
                f"{self.config.gemini_service_url}/api/gemini/loss-minimization",
                json={
                    'trade_id': trade['trade_id'],
                    'symbol': trade['symbol'],
                    'option_type': trade['option_type'],
                    'entry_price': trade['probe_entry_price'],
                    'current_price': trade['current_price'],
                    'pnl_percent': trade['pnl_percent'],
                    'probe_quantity': trade['probe_quantity'],
                    'scaled_quantity': trade.get('scale_quantity', 0),
                    'total_capital': trade['probe_capital'] + (trade.get('scale_quantity', 0) * trade.get('scale_entry_price', 0) * trade['lot_size']),
                    'stoploss_price': trade['probe_stoploss']
                }
            ) as resp:
                if resp.status == 200:
                    return await resp.json()
        except Exception as e:
            logger.error(f"Gemini loss minimization error: {e}")
        
        return {'decision': 'FULL_EXIT', 'recommended_action': 'Exit immediately'}
    
    # =========================================================================
    # HELPERS
    # =========================================================================
    
    async def _get_current_price(self, trade: Dict) -> float:
        """Get current price for the trade instrument"""
        # In paper mode, simulate price movement
        if self.config.paper_trading:
            import random
            # Small random movement
            change = random.uniform(-0.02, 0.02)
            return trade['current_price'] * (1 + change)
        
        # Real mode - get from Dhan
        await self._ensure_session()
        try:
            async with self.session.get(
                f"{self.config.dhan_backend_url}/api/quote/{trade['symbol']}"
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data.get('ltp', trade['current_price'])
        except:
            pass
        
        return trade['current_price']
    
    async def _place_order(self, trade: Dict, side: str, quantity: int) -> bool:
        """Place order via Dhan backend"""
        await self._ensure_session()
        
        try:
            async with self.session.post(
                f"{self.config.dhan_backend_url}/api/orders/place",
                json={
                    'symbol': trade['symbol'],
                    'option_type': trade['option_type'],
                    'strike': trade['strike'],
                    'expiry': trade['expiry'],
                    'quantity': quantity * trade['lot_size'],
                    'side': side,
                    'product_type': 'INTRADAY'
                }
            ) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    return result.get('success', False)
        except Exception as e:
            logger.error(f"Order placement error: {e}")
        
        return False
    
    def get_status(self) -> Dict:
        """Get current service status"""
        return {
            'running': self._running,
            'total_capital': self.config.total_capital,
            'available_capital': self.available_capital,
            'deployed_capital': self.deployed_capital,
            'daily_pnl': self.daily_pnl,
            'active_trades': len(self.active_trades),
            'trades': list(self.active_trades.values()),
            'paper_trading': self.config.paper_trading
        }


# ============================================================================
# MAIN
# ============================================================================

async def main():
    """Main entry point"""
    config = UnifiedTradingConfig(
        total_capital=100000.0,
        paper_trading=True  # Start in paper mode
    )
    
    service = UnifiedTradingService(config)
    
    try:
        await service.start()
        
        # Keep running
        while True:
            status = service.get_status()
            logger.info(f"📊 Status: {status['active_trades']} trades | P&L: ₹{status['daily_pnl']:+,.2f}")
            await asyncio.sleep(60)
            
    except KeyboardInterrupt:
        logger.info("Shutting down...")
    finally:
        await service.close()


if __name__ == "__main__":
    asyncio.run(main())
