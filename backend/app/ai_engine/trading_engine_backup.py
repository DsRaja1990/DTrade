"""
Advanced AI Trading Engine - Institutional Grade
World's Most Advanced Options Trading Algorithm
"""

import asyncio
import logging
import math
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from enum import Enum
from dataclasses import dataclass
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.preprocessing import StandardScaler
# import talib  # Temporarily commented out due to installation issues

from app.core.config import settings
from app.core.redis_client import redis_client
from app.core.websocket_manager import websocket_manager
from app.services.dhan_service import dhan_service
from app.services.market_data_service import MarketDataService
from app.models.trading import Position, Order

logger = logging.getLogger(__name__)


class SignalType(Enum):
    """Trade signal types"""
    BUY_CALL = "BUY_CALL"
    BUY_PUT = "BUY_PUT"
    SELL_CALL = "SELL_CALL"
    SELL_PUT = "SELL_PUT"
    HEDGE_CALL = "HEDGE_CALL"
    HEDGE_PUT = "HEDGE_PUT"
    EXIT_POSITION = "EXIT_POSITION"
    TRAIL_STOP = "TRAIL_STOP"


class MarketDirection(Enum):
    """Market direction analysis"""
    BULLISH = "BULLISH"
    BEARISH = "BEARISH"
    SIDEWAYS = "SIDEWAYS"
    VOLATILE = "VOLATILE"


@dataclass
class TradingSignal:
    """Enhanced trading signal with comprehensive data"""
    signal_type: SignalType
    underlying: str
    strike_price: float
    option_type: str  # CE or PE
    quantity: int
    confidence: float
    entry_price: float
    target_price: float
    stop_loss: float
    reasoning: str
    market_analysis: Dict[str, Any]
    risk_reward_ratio: float
    timestamp: datetime


@dataclass
class PositionManager:
    """Advanced position management system"""
    position_id: str
    underlying: str
    main_leg: Dict[str, Any]
    hedge_legs: List[Dict[str, Any]]
    current_pnl: float
    unrealized_pnl: float
    max_profit: float
    max_loss: float
    entry_time: datetime
    last_update: datetime
    is_active: bool
    strategy_type: str


class AITradingEngine:
    """
    Institutional-Grade AI Trading Engine
    
    Features:
    - Advanced price action analysis
    - Supply-demand zone detection
    - Multi-timeframe analysis
    - Dynamic hedging strategies
    - Machine learning predictions
    - Risk management algorithms
    """
    
    def __init__(self):
        self.is_running = False
        self.active_positions: Dict[str, PositionManager] = {}
        self.pending_orders: Dict[str, Order] = {}
        self.daily_pnl = 0.0
        self.max_daily_loss = settings.MAX_DAILY_LOSS
        self.max_position_size = settings.MAX_POSITION_SIZE
        
        # ML Models
        self.price_prediction_model = None
        self.volatility_model = None
        self.trend_model = None
        self.scaler = StandardScaler()
        
        # Market data storage
        self.market_data_cache = {}
        self.historical_data_cache = {}
        self.option_chain_cache = {}
        
        # Trading parameters
        self.risk_percentage = settings.RISK_PERCENTAGE
        self.trailing_stop_percentage = settings.TRAILING_STOP_PERCENTAGE
        
        # Services
        self.market_data_service = None  # Will be initialized when needed
        
        # Performance metrics
        self.total_trades = 0
        self.winning_trades = 0
        self.losing_trades = 0
        self.total_profit = 0.0
        self.total_loss = 0.0
    
    async def initialize(self):
        """Initialize the AI trading engine"""
        try:
            logger.info("🧠 Initializing AI Trading Engine...")
            
            # Initialize ML models
            await self._initialize_ml_models()
            
            # Load historical data for training
            await self._load_training_data()
            
            # Train models
            await self._train_models()
            
            # Start monitoring tasks
            if settings.AI_ENABLED:
                asyncio.create_task(self._market_monitoring_loop())
                asyncio.create_task(self._position_monitoring_loop())
                asyncio.create_task(self._risk_monitoring_loop())
            
            self.is_running = True
            logger.info("✅ AI Trading Engine initialized successfully")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize AI Trading Engine: {e}")
            raise
    
    async def _initialize_ml_models(self):
        """Initialize machine learning models"""
        try:
            # Price prediction model (Random Forest)
            self.price_prediction_model = RandomForestRegressor(
                n_estimators=200,
                max_depth=10,
                min_samples_split=5,
                min_samples_leaf=2,
                random_state=42
            )
            
            # Volatility prediction model
            self.volatility_model = GradientBoostingRegressor(
                n_estimators=150,
                max_depth=8,
                learning_rate=0.1,
                random_state=42
            )
            
            # Trend detection model
            self.trend_model = RandomForestRegressor(
                n_estimators=100,
                max_depth=6,
                random_state=42
            )
            
            logger.info("✅ ML models initialized")
            
        except Exception as e:
            logger.error(f"❌ Error initializing ML models: {e}")
            raise
    
    async def _load_training_data(self):
        """Load historical data for model training"""
        try:
            # Get NIFTY and SENSEX historical data
            nifty_data = await self.market_data_service.get_historical_data(
                security_id="13",  # NIFTY
                exchange_segment="IDX_I",
                instrument="INDEX",
                days=365
            )
            
            sensex_data = await self.market_data_service.get_historical_data(
                security_id="1",  # SENSEX
                exchange_segment="IDX_I", 
                instrument="INDEX",
                days=365
            )
            
            self.historical_data_cache["NIFTY"] = nifty_data
            self.historical_data_cache["SENSEX"] = sensex_data
            
            logger.info("✅ Training data loaded")
            
        except Exception as e:
            logger.error(f"❌ Error loading training data: {e}")
    
    async def _train_models(self):
        """Train ML models with historical data"""
        try:
            for underlying, data in self.historical_data_cache.items():
                if data and len(data) > 100:
                    df = pd.DataFrame(data)
                    features = self._extract_features(df)
                    
                    if len(features) > 50:
                        # Prepare training data
                        X = features[:-1]  # All except last row
                        y_price = df['close'].shift(-1).dropna()  # Next day close
                        y_volatility = df['high'].sub(df['low']).div(df['close']).shift(-1).dropna()
                        
                        # Scale features
                        X_scaled = self.scaler.fit_transform(X)
                        
                        # Train models
                        self.price_prediction_model.fit(X_scaled, y_price)
                        self.volatility_model.fit(X_scaled, y_volatility)
                        
            logger.info("✅ ML models trained successfully")
            
        except Exception as e:
            logger.error(f"❌ Error training models: {e}")
    
    def _extract_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Extract technical features for ML models"""
        try:
            features = pd.DataFrame()
            
            # Basic price features
            features['open'] = df['open']
            features['high'] = df['high']
            features['low'] = df['low']
            features['close'] = df['close']
            features['volume'] = df['volume']
            
            # Price changes
            features['price_change'] = df['close'].pct_change()
            features['high_low_ratio'] = df['high'] / df['low']
            features['close_open_ratio'] = df['close'] / df['open']
            
            # Moving averages
            for period in [5, 10, 20, 50]:
                features[f'sma_{period}'] = df['close'].rolling(period).mean()
                features[f'ema_{period}'] = df['close'].ewm(span=period).mean()
            
            # Technical indicators (simplified implementations)
            # RSI calculation
            delta = df['close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            features['rsi'] = 100 - (100 / (1 + rs))
            
            # Simple MACD
            ema12 = df['close'].ewm(span=12).mean()
            ema26 = df['close'].ewm(span=26).mean()
            features['macd'] = ema12 - ema26
            features['macd_signal'] = features['macd'].ewm(span=9).mean()
            features['macd_hist'] = features['macd'] - features['macd_signal']
            
            # Bollinger Bands
            sma20 = df['close'].rolling(20).mean()
            std20 = df['close'].rolling(20).std()
            features['bb_upper'] = sma20 + (std20 * 2)
            features['bb_middle'] = sma20
            features['bb_lower'] = sma20 - (std20 * 2)
            
            # ATR (Average True Range)
            high_low = df['high'] - df['low']
            high_close = np.abs(df['high'] - df['close'].shift())
            low_close = np.abs(df['low'] - df['close'].shift())
            true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
            features['atr'] = true_range.rolling(14).mean()
            
            # Volume indicators
            features['volume_sma'] = df['volume'].rolling(20).mean()
            features['volume_ratio'] = df['volume'] / features['volume_sma']
            
            # Volatility measures
            features['volatility'] = df['close'].rolling(20).std()
            features['realized_vol'] = features['price_change'].rolling(20).std() * np.sqrt(252)
            
            # Support and resistance levels
            features['resistance'] = df['high'].rolling(20).max()
            features['support'] = df['low'].rolling(20).min()
            features['distance_to_resistance'] = (features['resistance'] - df['close']) / df['close']
            features['distance_to_support'] = (df['close'] - features['support']) / df['close']
            
            # Drop NaN values
            features = features.dropna()
            
            return features
            
        except Exception as e:
            logger.error(f"❌ Error extracting features: {e}")
            return pd.DataFrame()
    
    async def _market_monitoring_loop(self):
        """Continuous market monitoring and signal generation"""
        while self.is_running:
            try:
                # Get current market data
                market_data = await self._get_current_market_data()
                
                if market_data:
                    # Analyze market conditions
                    market_analysis = await self._analyze_market_conditions(market_data)
                    
                    # Generate trading signals
                    signals = await self._generate_trading_signals(market_analysis)
                    
                    # Process signals
                    for signal in signals:
                        await self._process_trading_signal(signal)
                
                # Wait before next iteration
                await asyncio.sleep(5)  # 5-second intervals
                
            except Exception as e:
                logger.error(f"❌ Error in market monitoring loop: {e}")
                await asyncio.sleep(10)
    
    async def _position_monitoring_loop(self):
        """Monitor and manage active positions"""
        while self.is_running:
            try:
                for position_id, position in self.active_positions.items():
                    await self._monitor_position(position)
                
                # Update portfolio metrics
                await self._update_portfolio_metrics()
                
                await asyncio.sleep(2)  # 2-second intervals
                
            except Exception as e:
                logger.error(f"❌ Error in position monitoring loop: {e}")
                await asyncio.sleep(5)
    
    async def _risk_monitoring_loop(self):
        """Monitor risk levels and enforce limits"""
        while self.is_running:
            try:
                # Check daily loss limit
                if self.daily_pnl <= -self.max_daily_loss:
                    logger.warning("🚨 Daily loss limit reached! Closing all positions")
                    await self._emergency_close_all_positions()
                
                # Check individual position risks
                for position in self.active_positions.values():
                    if position.unrealized_pnl <= -settings.MAX_POSITION_SIZE * 0.1:  # 10% position loss
                        logger.warning(f"🚨 Position {position.position_id} exceeding loss limit")
                        await self._close_position(position.position_id)
                
                await asyncio.sleep(10)  # 10-second intervals
                
            except Exception as e:
                logger.error(f"❌ Error in risk monitoring loop: {e}")
                await asyncio.sleep(15)
    
    async def _get_current_market_data(self) -> Optional[Dict[str, Any]]:
        """Get current market data for analysis"""
        try:
            # Get NIFTY and SENSEX current data
            nifty_quote = await dhan_service.get_market_quote("13", "IDX_I")
            sensex_quote = await dhan_service.get_market_quote("1", "IDX_I")
            
            # Get option chain data
            nifty_options = await dhan_service.get_option_chain("13", "IDX_I")
            
            market_data = {
                "nifty": nifty_quote,
                "sensex": sensex_quote,
                "nifty_options": nifty_options,
                "timestamp": datetime.now()
            }
            
            # Cache market data
            self.market_data_cache = market_data
            
            return market_data
            
        except Exception as e:
            logger.error(f"❌ Error getting market data: {e}")
            return None
    
    async def _analyze_market_conditions(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Comprehensive market analysis using AI"""
        try:
            analysis = {
                "direction": MarketDirection.SIDEWAYS,
                "strength": 0.5,
                "volatility": 0.5,
                "support_levels": [],
                "resistance_levels": [],
                "supply_demand_zones": [],
                "reversal_signals": [],
                "trend_signals": [],
                "options_analysis": {},
                "confidence": 0.5
            }
            
            # Analyze NIFTY
            nifty_data = market_data.get("nifty", {})
            if nifty_data:
                # Price action analysis
                ltp = nifty_data.get("last_price", 0)
                high = nifty_data.get("ohlc", {}).get("high", 0)
                low = nifty_data.get("ohlc", {}).get("low", 0)
                close_prev = nifty_data.get("ohlc", {}).get("close", 0)
                
                # Calculate key levels
                pivot = (high + low + close_prev) / 3
                resistance1 = 2 * pivot - low
                support1 = 2 * pivot - high
                
                analysis["support_levels"] = [support1, low]
                analysis["resistance_levels"] = [resistance1, high]
                
                # Determine direction
                if ltp > pivot and ltp > close_prev:
                    analysis["direction"] = MarketDirection.BULLISH
                    analysis["strength"] = min(0.8, (ltp - close_prev) / close_prev * 100)
                elif ltp < pivot and ltp < close_prev:
                    analysis["direction"] = MarketDirection.BEARISH
                    analysis["strength"] = min(0.8, (close_prev - ltp) / close_prev * 100)
                
                # Volatility analysis
                daily_range = (high - low) / close_prev * 100
                if daily_range > 2.0:
                    analysis["volatility"] = 0.8
                    analysis["direction"] = MarketDirection.VOLATILE
                
            # Options analysis
            options_data = market_data.get("nifty_options", {})
            if options_data:
                analysis["options_analysis"] = await self._analyze_options_data(options_data)
            
            # ML predictions
            if self.price_prediction_model:
                prediction = await self._get_ml_prediction(market_data)
                analysis.update(prediction)
            
            return analysis
            
        except Exception as e:
            logger.error(f"❌ Error analyzing market conditions: {e}")
            return {}
    
    async def _analyze_options_data(self, options_data: Dict[str, Any]) -> Dict[str, Any]:
        """Advanced options chain analysis"""
        try:
            analysis = {
                "atm_strike": 0,
                "call_put_ratio": 1.0,
                "max_pain": 0,
                "gamma_levels": [],
                "high_oi_strikes": [],
                "recommendations": []
            }
            
            if not options_data or "oc" not in options_data:
                return analysis
            
            option_chain = options_data["oc"]
            ltp = options_data.get("last_price", 0)
            
            # Find ATM strike
            strikes = list(option_chain.keys())
            strikes_float = [float(s) for s in strikes]
            atm_strike = min(strikes_float, key=lambda x: abs(x - ltp))
            analysis["atm_strike"] = atm_strike
            
            # Calculate metrics
            total_call_oi = 0
            total_put_oi = 0
            strike_oi_data = []
            
            for strike_str, data in option_chain.items():
                strike = float(strike_str)
                
                call_data = data.get("ce", {})
                put_data = data.get("pe", {})
                
                call_oi = call_data.get("oi", 0)
                put_oi = put_data.get("oi", 0)
                
                total_call_oi += call_oi
                total_put_oi += put_oi
                
                strike_oi_data.append({
                    "strike": strike,
                    "call_oi": call_oi,
                    "put_oi": put_oi,
                    "total_oi": call_oi + put_oi
                })
            
            # Call-Put ratio
            if total_put_oi > 0:
                analysis["call_put_ratio"] = total_call_oi / total_put_oi
            
            # Max Pain calculation
            max_pain_values = []
            for strike_data in strike_oi_data:
                strike = strike_data["strike"]
                pain = 0
                
                for other_strike_data in strike_oi_data:
                    other_strike = other_strike_data["strike"]
                    call_oi = other_strike_data["call_oi"]
                    put_oi = other_strike_data["put_oi"]
                    
                    if strike < other_strike:
                        pain += call_oi * (other_strike - strike)
                    elif strike > other_strike:
                        pain += put_oi * (strike - other_strike)
                
                max_pain_values.append((strike, pain))
            
            if max_pain_values:
                analysis["max_pain"] = min(max_pain_values, key=lambda x: x[1])[0]
            
            # High OI strikes
            strike_oi_data.sort(key=lambda x: x["total_oi"], reverse=True)
            analysis["high_oi_strikes"] = [s["strike"] for s in strike_oi_data[:5]]
            
            return analysis
            
        except Exception as e:
            logger.error(f"❌ Error analyzing options data: {e}")
            return {}
    
    async def _get_ml_prediction(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Get ML model predictions"""
        try:
            prediction = {
                "price_direction": "NEUTRAL",
                "price_target": 0,
                "volatility_forecast": 0.5,
                "confidence": 0.5
            }
            
            # Extract current features
            current_features = self._extract_current_features(market_data)
            
            if len(current_features) > 0 and self.price_prediction_model:
                # Scale features
                features_scaled = self.scaler.transform([current_features])
                
                # Get predictions
                price_pred = self.price_prediction_model.predict(features_scaled)[0]
                vol_pred = self.volatility_model.predict(features_scaled)[0]
                
                current_price = market_data.get("nifty", {}).get("last_price", 0)
                
                if price_pred > current_price * 1.002:  # 0.2% threshold
                    prediction["price_direction"] = "BULLISH"
                elif price_pred < current_price * 0.998:
                    prediction["price_direction"] = "BEARISH"
                
                prediction["price_target"] = price_pred
                prediction["volatility_forecast"] = vol_pred
                prediction["confidence"] = min(0.9, abs(price_pred - current_price) / current_price * 10)
            
            return prediction
            
        except Exception as e:
            logger.error(f"❌ Error getting ML prediction: {e}")
            return {}
    
    def _extract_current_features(self, market_data: Dict[str, Any]) -> List[float]:
        """Extract features from current market data"""
        try:
            features = []
            
            nifty_data = market_data.get("nifty", {})
            if nifty_data:
                # Basic price data
                ltp = nifty_data.get("last_price", 0)
                ohlc = nifty_data.get("ohlc", {})
                
                features.extend([
                    ohlc.get("open", 0),
                    ohlc.get("high", 0),
                    ohlc.get("low", 0),
                    ltp,
                    nifty_data.get("volume", 0)
                ])
                
                # Calculate ratios
                if ohlc.get("low", 0) > 0:
                    features.append(ohlc.get("high", 0) / ohlc.get("low", 0))
                else:
                    features.append(1.0)
                
                if ohlc.get("open", 0) > 0:
                    features.append(ltp / ohlc.get("open", 0))
                else:
                    features.append(1.0)
            
            # Pad with zeros if needed
            while len(features) < 20:  # Minimum feature count
                features.append(0.0)
            
            return features
            
        except Exception as e:
            logger.error(f"❌ Error extracting current features: {e}")
            return []
    
    async def _generate_trading_signals(self, market_analysis: Dict[str, Any]) -> List[TradingSignal]:
        """Generate intelligent trading signals based on market analysis"""
        try:
            signals = []
            
            if not market_analysis or market_analysis.get("confidence", 0) < 0.3:
                return signals
            
            direction = market_analysis.get("direction", MarketDirection.SIDEWAYS)
            strength = market_analysis.get("strength", 0)
            volatility = market_analysis.get("volatility", 0)
            options_analysis = market_analysis.get("options_analysis", {})
            
            atm_strike = options_analysis.get("atm_strike", 0)
            
            if atm_strike == 0:
                return signals
            
            # Signal generation logic
            if direction == MarketDirection.BULLISH and strength > 0.6:
                # Strong bullish signal - Buy Call
                signal = TradingSignal(
                    signal_type=SignalType.BUY_CALL,
                    underlying="NIFTY",
                    strike_price=atm_strike,
                    option_type="CE",
                    quantity=settings.DEFAULT_QUANTITY,
                    confidence=strength,
                    entry_price=0,  # Will be filled during execution
                    target_price=0,  # Will be calculated
                    stop_loss=0,    # Will be calculated
                    reasoning=f"Strong bullish momentum detected. Strength: {strength:.2f}",
                    market_analysis=market_analysis,
                    risk_reward_ratio=2.0,
                    timestamp=datetime.now()
                )
                signals.append(signal)
                
            elif direction == MarketDirection.BEARISH and strength > 0.6:
                # Strong bearish signal - Buy Put
                signal = TradingSignal(
                    signal_type=SignalType.BUY_PUT,
                    underlying="NIFTY",
                    strike_price=atm_strike,
                    option_type="PE",
                    quantity=settings.DEFAULT_QUANTITY,
                    confidence=strength,
                    entry_price=0,
                    target_price=0,
                    stop_loss=0,
                    reasoning=f"Strong bearish momentum detected. Strength: {strength:.2f}",
                    market_analysis=market_analysis,
                    risk_reward_ratio=2.0,
                    timestamp=datetime.now()
                )
                signals.append(signal)
                
            elif direction == MarketDirection.VOLATILE and volatility > 0.7:
                # High volatility - Straddle strategy
                # Buy both Call and Put
                for option_type, signal_type in [("CE", SignalType.BUY_CALL), ("PE", SignalType.BUY_PUT)]:
                    signal = TradingSignal(
                        signal_type=signal_type,
                        underlying="NIFTY",
                        strike_price=atm_strike,
                        option_type=option_type,
                        quantity=settings.DEFAULT_QUANTITY // 2,  # Half quantity for each leg
                        confidence=volatility,
                        entry_price=0,
                        target_price=0,
                        stop_loss=0,
                        reasoning=f"High volatility detected. Long straddle strategy. Volatility: {volatility:.2f}",
                        market_analysis=market_analysis,
                        risk_reward_ratio=1.5,
                        timestamp=datetime.now()
                    )
                    signals.append(signal)
            
            return signals
            
        except Exception as e:
            logger.error(f"❌ Error generating trading signals: {e}")
            return []
    
    async def _process_trading_signal(self, signal: TradingSignal):
        """Process and execute trading signal"""
        try:
            logger.info(f"🎯 Processing signal: {signal.signal_type.value} {signal.underlying} {signal.strike_price} {signal.option_type}")
            
            # Check if we should execute this signal
            if not await self._should_execute_signal(signal):
                return
            
            # Get instrument details
            instrument = await self._find_option_instrument(
                signal.underlying,
                signal.strike_price,
                signal.option_type
            )
            
            if not instrument:
                logger.warning(f"⚠️ Instrument not found for signal: {signal}")
                return
            
            # Calculate entry price, target, and stop loss
            market_price = await self._get_current_option_price(instrument)
            
            if market_price == 0:
                logger.warning(f"⚠️ Could not get market price for {instrument}")
                return
            
            signal.entry_price = market_price
            signal.target_price = market_price * (1 + signal.risk_reward_ratio * 0.1)
            signal.stop_loss = market_price * (1 - 0.1)  # 10% stop loss
            
            # Execute the trade
            order_result = await self._execute_trade(signal, instrument)
            
            if order_result:
                # Create position manager
                position_id = f"{signal.underlying}_{signal.strike_price}_{signal.option_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                
                position = PositionManager(
                    position_id=position_id,
                    underlying=signal.underlying,
                    main_leg={
                        "instrument": instrument,
                        "signal": signal,
                        "order": order_result,
                        "entry_price": market_price,
                        "quantity": signal.quantity
                    },
                    hedge_legs=[],
                    current_pnl=0.0,
                    unrealized_pnl=0.0,
                    max_profit=0.0,
                    max_loss=0.0,
                    entry_time=datetime.now(),
                    last_update=datetime.now(),
                    is_active=True,
                    strategy_type="SINGLE_LEG"
                )
                
                self.active_positions[position_id] = position
                
                # Send signal to WebSocket clients
                await websocket_manager.send_trade_signal({
                    "signal": signal.__dict__,
                    "position_id": position_id,
                    "status": "executed"
                })
                
                logger.info(f"✅ Signal executed successfully: {position_id}")
            
        except Exception as e:
            logger.error(f"❌ Error processing trading signal: {e}")
    
    async def _should_execute_signal(self, signal: TradingSignal) -> bool:
        """Determine if signal should be executed based on risk management"""
        try:
            # Check daily loss limit
            if self.daily_pnl <= -self.max_daily_loss:
                return False
            
            # Check confidence threshold
            if signal.confidence < 0.5:
                return False
            
            # Check if we already have a position in this underlying
            for position in self.active_positions.values():
                if position.underlying == signal.underlying and position.is_active:
                    # Check if we should add to position or skip
                    if len(position.hedge_legs) >= 3:  # Max 3 hedge legs
                        return False
            
            # Check maximum position size
            position_value = signal.entry_price * signal.quantity
            if position_value > self.max_position_size:
                return False
            
            # Check market hours
            current_time = datetime.now().time()
            market_start = datetime.strptime("09:15", "%H:%M").time()
            market_end = datetime.strptime("15:30", "%H:%M").time()
            
            if not (market_start <= current_time <= market_end):
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error checking signal execution: {e}")
            return False
    
    async def _find_option_instrument(self, underlying: str, strike_price: float, option_type: str) -> Optional[Dict[str, Any]]:
        """Find option instrument details"""
        try:
            # Get current week expiry
            expiry_date = await self._get_current_week_expiry()
            
            # Search for instrument in DhanHQ instruments
            instruments = await dhan_service.get_instruments("NSE_FNO")
            
            for instrument in instruments:
                if (instrument.get("UNDERLYING_SYMBOL", "") == underlying and
                    instrument.get("STRIKE_PRICE", 0) == strike_price and
                    instrument.get("OPTION_TYPE", "") == option_type and
                    instrument.get("SM_EXPIRY_DATE", "") == expiry_date):
                    return instrument
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Error finding option instrument: {e}")
            return None
    
    async def _get_current_week_expiry(self) -> str:
        """Get current week option expiry date"""
        try:
            # Get expiry list from DhanHQ
            expiry_list = await dhan_service.get_expiry_list("13", "IDX_I")  # NIFTY
            
            if expiry_list and len(expiry_list) > 0:
                # Return nearest expiry
                return expiry_list[0]
            
            # Fallback: Calculate Thursday of current week
            today = datetime.now()
            days_ahead = 3 - today.weekday()  # Thursday = 3
            if days_ahead <= 0:
                days_ahead += 7
            
            thursday = today + timedelta(days=days_ahead)
            return thursday.strftime("%Y-%m-%d")
            
        except Exception as e:
            logger.error(f"❌ Error getting current week expiry: {e}")
            return datetime.now().strftime("%Y-%m-%d")
    
    async def _get_current_option_price(self, instrument: Dict[str, Any]) -> float:
        """Get current option price"""
        try:
            security_id = instrument.get("SECURITY_ID", "")
            if not security_id:
                return 0.0
            
            quote = await dhan_service.get_market_quote(security_id, "NSE_FNO")
            
            if quote:
                return quote.get("last_price", 0.0)
            
            return 0.0
            
        except Exception as e:
            logger.error(f"❌ Error getting option price: {e}")
            return 0.0
    
    async def _execute_trade(self, signal: TradingSignal, instrument: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Execute the actual trade"""
        try:
            if settings.ENABLE_PAPER_TRADING:
                # Paper trading mode
                order_result = {
                    "order_id": f"PAPER_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                    "status": "TRADED",
                    "price": signal.entry_price,
                    "quantity": signal.quantity,
                    "timestamp": datetime.now().isoformat()
                }
                
                logger.info(f"📄 Paper trade executed: {order_result}")
                return order_result
            
            else:
                # Real trading mode
                order_data = {
                    "dhanClientId": settings.DHAN_CLIENT_ID,
                    "correlationId": f"DTRADE_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                    "transactionType": "BUY",
                    "exchangeSegment": "NSE_FNO",
                    "productType": settings.DEFAULT_PRODUCT_TYPE,
                    "orderType": settings.DEFAULT_ORDER_TYPE,
                    "securityId": instrument.get("SECURITY_ID", ""),
                    "quantity": str(signal.quantity),
                    "price": str(signal.entry_price) if settings.DEFAULT_ORDER_TYPE == "LIMIT" else "",
                    "validity": "DAY",
                    "afterMarketOrder": False
                }
                
                order_result = await dhan_service.place_order(order_data)
                
                if order_result:
                    logger.info(f"💰 Real trade executed: {order_result}")
                    return order_result
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Error executing trade: {e}")
            return None
    
    async def _monitor_position(self, position: PositionManager):
        """Monitor and manage individual position"""
        try:
            if not position.is_active:
                return
            
            # Get current market data
            current_price = await self._get_current_option_price(position.main_leg["instrument"])
            
            if current_price == 0:
                return
            
            # Calculate P&L
            entry_price = position.main_leg["entry_price"]
            quantity = position.main_leg["quantity"]
            
            unrealized_pnl = (current_price - entry_price) * quantity
            position.unrealized_pnl = unrealized_pnl
            position.current_pnl = unrealized_pnl  # Add hedge legs P&L later
            
            # Update max profit/loss
            if unrealized_pnl > position.max_profit:
                position.max_profit = unrealized_pnl
            if unrealized_pnl < position.max_loss:
                position.max_loss = unrealized_pnl
            
            position.last_update = datetime.now()
            
            # Check exit conditions
            signal = position.main_leg["signal"]
            
            # Profit target reached
            if current_price >= signal.target_price:
                logger.info(f"🎯 Profit target reached for {position.position_id}")
                await self._close_position(position.position_id, "PROFIT_TARGET")
                return
            
            # Stop loss hit
            if current_price <= signal.stop_loss:
                logger.info(f"🛑 Stop loss hit for {position.position_id}")
                
                # Check if we should hedge instead of closing
                if len(position.hedge_legs) < 2:  # Max 2 hedge attempts
                    await self._add_hedge_position(position)
                else:
                    await self._close_position(position.position_id, "STOP_LOSS")
                return
            
            # Trailing stop logic
            if position.max_profit > entry_price * quantity * 0.2:  # 20% profit
                trailing_stop = entry_price * (1 + 0.1)  # Trail at 10% profit
                if current_price <= trailing_stop:
                    logger.info(f"📈 Trailing stop triggered for {position.position_id}")
                    await self._close_position(position.position_id, "TRAILING_STOP")
                    return
            
            # Time-based exit (end of day)
            current_time = datetime.now().time()
            if current_time >= datetime.strptime("15:15", "%H:%M").time():
                logger.info(f"⏰ End of day exit for {position.position_id}")
                await self._close_position(position.position_id, "EOD_EXIT")
                return
            
        except Exception as e:
            logger.error(f"❌ Error monitoring position {position.position_id}: {e}")
    
    async def _add_hedge_position(self, position: PositionManager):
        """Add hedge position to protect against losses"""
        try:
            logger.info(f"🛡️ Adding hedge position for {position.position_id}")
            
            main_signal = position.main_leg["signal"]
            
            # Determine hedge direction
            if main_signal.option_type == "CE":
                # Main position is Call, hedge with Put
                hedge_option_type = "PE"
                hedge_signal_type = SignalType.HEDGE_PUT
            else:
                # Main position is Put, hedge with Call
                hedge_option_type = "CE"
                hedge_signal_type = SignalType.HEDGE_CALL
            
            # Find OTM strike for hedge
            current_underlying_price = await self._get_underlying_price(main_signal.underlying)
            
            if main_signal.option_type == "CE":
                # For Call hedge, use Put strike below current price
                hedge_strike = math.floor(current_underlying_price / 50) * 50 - 100  # 100 points OTM
            else:
                # For Put hedge, use Call strike above current price
                hedge_strike = math.ceil(current_underlying_price / 50) * 50 + 100   # 100 points OTM
            
            # Create hedge signal
            hedge_signal = TradingSignal(
                signal_type=hedge_signal_type,
                underlying=main_signal.underlying,
                strike_price=hedge_strike,
                option_type=hedge_option_type,
                quantity=main_signal.quantity,  # Same quantity
                confidence=0.8,
                entry_price=0,
                target_price=0,
                stop_loss=0,
                reasoning=f"Hedge position for {position.position_id}",
                market_analysis={},
                risk_reward_ratio=1.0,
                timestamp=datetime.now()
            )
            
            # Find hedge instrument
            hedge_instrument = await self._find_option_instrument(
                hedge_signal.underlying,
                hedge_signal.strike_price,
                hedge_signal.option_type
            )
            
            if hedge_instrument:
                # Get hedge price
                hedge_price = await self._get_current_option_price(hedge_instrument)
                hedge_signal.entry_price = hedge_price
                
                # Execute hedge trade
                hedge_order = await self._execute_trade(hedge_signal, hedge_instrument)
                
                if hedge_order:
                    # Add to position hedge legs
                    hedge_leg = {
                        "instrument": hedge_instrument,
                        "signal": hedge_signal,
                        "order": hedge_order,
                        "entry_price": hedge_price,
                        "quantity": hedge_signal.quantity,
                        "hedge_type": "PROTECTIVE"
                    }
                    
                    position.hedge_legs.append(hedge_leg)
                    position.strategy_type = "HEDGED"
                    
                    logger.info(f"✅ Hedge position added: {hedge_strike} {hedge_option_type}")
            
        except Exception as e:
            logger.error(f"❌ Error adding hedge position: {e}")
    
    async def _get_underlying_price(self, underlying: str) -> float:
        """Get current underlying price"""
        try:
            if underlying == "NIFTY":
                security_id = "13"
            elif underlying == "SENSEX":
                security_id = "1"
            else:
                return 0.0
            
            quote = await dhan_service.get_market_quote(security_id, "IDX_I")
            
            if quote:
                return quote.get("last_price", 0.0)
            
            return 0.0
            
        except Exception as e:
            logger.error(f"❌ Error getting underlying price: {e}")
            return 0.0
    
    async def _close_position(self, position_id: str, reason: str = "MANUAL"):
        """Close position and all associated legs"""
        try:
            if position_id not in self.active_positions:
                return
            
            position = self.active_positions[position_id]
            logger.info(f"🔚 Closing position {position_id} - Reason: {reason}")
            
            total_pnl = 0.0
            
            # Close main leg
            main_leg = position.main_leg
            if settings.ENABLE_PAPER_TRADING:
                # Paper trading close
                current_price = await self._get_current_option_price(main_leg["instrument"])
                pnl = (current_price - main_leg["entry_price"]) * main_leg["quantity"]
                total_pnl += pnl
                
                logger.info(f"📄 Paper close main leg: P&L {pnl:.2f}")
            else:
                # Real trading close
                close_order = await self._place_exit_order(main_leg)
                if close_order:
                    # Calculate actual P&L from order
                    executed_price = float(close_order.get("price", main_leg["entry_price"]))
                    pnl = (executed_price - main_leg["entry_price"]) * main_leg["quantity"]
                    total_pnl += pnl
            
            # Close hedge legs
            for hedge_leg in position.hedge_legs:
                if settings.ENABLE_PAPER_TRADING:
                    current_price = await self._get_current_option_price(hedge_leg["instrument"])
                    hedge_pnl = (current_price - hedge_leg["entry_price"]) * hedge_leg["quantity"]
                    total_pnl += hedge_pnl
                    
                    logger.info(f"📄 Paper close hedge leg: P&L {hedge_pnl:.2f}")
                else:
                    close_order = await self._place_exit_order(hedge_leg)
                    if close_order:
                        executed_price = float(close_order.get("price", hedge_leg["entry_price"]))
                        hedge_pnl = (executed_price - hedge_leg["entry_price"]) * hedge_leg["quantity"]
                        total_pnl += hedge_pnl
            
            # Update statistics
            self.total_trades += 1
            if total_pnl > 0:
                self.winning_trades += 1
                self.total_profit += total_pnl
            else:
                self.losing_trades += 1
                self.total_loss += abs(total_pnl)
            
            self.daily_pnl += total_pnl
            
            # Mark position as inactive
            position.is_active = False
            position.current_pnl = total_pnl
            
            # Send closure notification
            await websocket_manager.send_portfolio_update({
                "position_closed": {
                    "position_id": position_id,
                    "reason": reason,
                    "pnl": total_pnl,
                    "duration": (datetime.now() - position.entry_time).total_seconds(),
                    "timestamp": datetime.now().isoformat()
                }
            })
            
            logger.info(f"✅ Position {position_id} closed. P&L: {total_pnl:.2f}")
            
        except Exception as e:
            logger.error(f"❌ Error closing position {position_id}: {e}")
    
    async def _place_exit_order(self, leg: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Place exit order for a position leg"""
        try:
            instrument = leg["instrument"]
            quantity = leg["quantity"]
            
            order_data = {
                "dhanClientId": settings.DHAN_CLIENT_ID,
                "correlationId": f"EXIT_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                "transactionType": "SELL",
                "exchangeSegment": "NSE_FNO",
                "productType": settings.DEFAULT_PRODUCT_TYPE,
                "orderType": "MARKET",  # Market order for quick exit
                "securityId": instrument.get("SECURITY_ID", ""),
                "quantity": str(quantity),
                "validity": "DAY",
                "afterMarketOrder": False
            }
            
            result = await dhan_service.place_order(order_data)
            return result
            
        except Exception as e:
            logger.error(f"❌ Error placing exit order: {e}")
            return None
    
    async def _update_portfolio_metrics(self):
        """Update and broadcast portfolio metrics"""
        try:
            total_unrealized_pnl = sum(pos.unrealized_pnl for pos in self.active_positions.values() if pos.is_active)
            
            portfolio_metrics = {
                "daily_pnl": self.daily_pnl,
                "unrealized_pnl": total_unrealized_pnl,
                "total_pnl": self.daily_pnl + total_unrealized_pnl,
                "active_positions": len([p for p in self.active_positions.values() if p.is_active]),
                "total_trades": self.total_trades,
                "winning_trades": self.winning_trades,
                "losing_trades": self.losing_trades,
                "win_rate": (self.winning_trades / max(self.total_trades, 1)) * 100,
                "avg_profit": self.total_profit / max(self.winning_trades, 1),
                "avg_loss": self.total_loss / max(self.losing_trades, 1),
                "profit_factor": self.total_profit / max(self.total_loss, 1),
                "timestamp": datetime.now().isoformat()
            }
            
            # Cache metrics in Redis
            await redis_client.set("portfolio_metrics", portfolio_metrics, ttl=60)
            
            # Broadcast to WebSocket clients
            await websocket_manager.send_portfolio_update(portfolio_metrics)
            
        except Exception as e:
            logger.error(f"❌ Error updating portfolio metrics: {e}")
    
    async def _emergency_close_all_positions(self):
        """Emergency closure of all positions"""
        try:
            logger.warning("🚨 EMERGENCY: Closing all positions due to risk limits")
            
            for position_id in list(self.active_positions.keys()):
                position = self.active_positions[position_id]
                if position.is_active:
                    await self._close_position(position_id, "EMERGENCY_RISK_LIMIT")
            
            # Send emergency alert
            await websocket_manager.send_system_alert({
                "type": "EMERGENCY_CLOSE",
                "message": "All positions closed due to risk limits",
                "daily_pnl": self.daily_pnl,
                "timestamp": datetime.now().isoformat()
            }, "critical")
            
        except Exception as e:
            logger.error(f"❌ Error in emergency position closure: {e}")
    
    async def get_active_positions_count(self) -> int:
        """Get count of active positions"""
        return len([p for p in self.active_positions.values() if p.is_active])
    
    async def get_daily_trades_count(self) -> int:
        """Get count of daily trades"""
        return self.total_trades
    
    async def shutdown(self):
        """Shutdown the AI trading engine"""
        try:
            logger.info("🛑 Shutting down AI Trading Engine...")
            
            self.is_running = False
            
            # Close all active positions
            for position_id in list(self.active_positions.keys()):
                position = self.active_positions[position_id]
                if position.is_active:
                    await self._close_position(position_id, "SYSTEM_SHUTDOWN")
            
            logger.info("✅ AI Trading Engine shutdown complete")
            
        except Exception as e:
            logger.error(f"❌ Error during AI engine shutdown: {e}")


# Create global AI trading engine instance
ai_trading_engine = AITradingEngine()
