"""
Market Data Engine for processing real-time and historical data
"""
import pandas as pd
import numpy as np
import logging
from datetime import datetime, timedelta
from collections import defaultdict, deque
import threading
import time

logger = logging.getLogger(__name__)

class MarketDataEngine:
    def __init__(self, api_connector):
        self.api = api_connector
        self.subscribed_instruments = {}
        self.data_buffer = defaultdict(lambda: deque(maxlen=1000))  # Store last 1000 ticks
        self.indicators = {}
        self.option_chains = {}
        self.lock = threading.RLock()
        
        # Internal buffers for technical indicators
        self._init_indicator_buffers()
        
        # Register callback for market data
        self.api.register_callback("tick", self._process_tick_data)
        
    def _init_indicator_buffers(self):
        """Initialize buffers for technical indicators"""
        self.indicator_periods = {
            'rsi': 14,
            'macd': {'fast': 12, 'slow': 26, 'signal': 9},
            'bollinger': 20,
            'atr': 14,
            'adx': 14,
            'vwap': 1,  # Daily
            'ema': [9, 21, 50, 200],
            'entropy': 20,
            'obv': 1,
        }
        
        # Dataframes to store OHLCV data for different timeframes
        self.timeframes = {
            '1m': {},
            '5m': {},
            '15m': {},
            '1h': {},
            'D': {}
        }
    
    def subscribe_index(self, index_name):
        """Subscribe to index data"""
        exchange = "NSE_IDX"  # NSE Indices
        instrument = self.api.get_instrument_by_symbol(index_name, exchange)
        
        if instrument:
            instrument_id = instrument["instrumentId"]
            self.api.subscribe_ticker(instrument_id)
            with self.lock:
                self.subscribed_instruments[instrument_id] = {
                    "symbol": index_name,
                    "type": "index",
                    "exchange": exchange,
                    "last_price": None,
                    "timestamp": None
                }
            logger.info(f"Subscribed to index: {index_name}")
            return True
        else:
            logger.error(f"Failed to find instrument for index: {index_name}")
            return False
    
    def subscribe_equity(self, symbol):
        """Subscribe to equity data"""
        exchange = "NSE"
        instrument = self.api.get_instrument_by_symbol(symbol, exchange)
        
        if instrument:
            instrument_id = instrument["instrumentId"]
            self.api.subscribe_ticker(instrument_id)
            with self.lock:
                self.subscribed_instruments[instrument_id] = {
                    "symbol": symbol,
                    "type": "equity",
                    "exchange": exchange,
                    "last_price": None,
                    "timestamp": None
                }
            logger.info(f"Subscribed to equity: {symbol}")
            return True
        else:
            logger.error(f"Failed to find instrument for equity: {symbol}")
            return False
    
    def subscribe_option_chain(self, underlying, depth=5):
        """Subscribe to option chain with specified depth around ATM"""
        # Get current index value
        if underlying == "NIFTY 50":
            symbol = "NIFTY"
        elif underlying == "NIFTY BANK":
            symbol = "BANKNIFTY"
        else:
            symbol = underlying
            
        index_instrument = self.api.get_instrument_by_symbol(symbol, "NSE_IDX")
        if not index_instrument:
            logger.error(f"Failed to find instrument for index: {symbol}")
            return False
            
        # Get current index value (or use last known value if already subscribed)
        instrument_id = index_instrument["instrumentId"]
        current_value = None
        
        if instrument_id in self.subscribed_instruments:
            current_value = self.subscribed_instruments[instrument_id].get("last_price")
        
        if not current_value:
            # Fetch current value through API
            try:
                quote = self.api.get_quote(instrument_id)
                if quote and "last_price" in quote:
                    current_value = quote["last_price"]
            except Exception as e:
                logger.error(f"Error fetching quote for {symbol}: {e}")
                return False
        
        if not current_value:
            logger.error(f"Failed to determine current value for {symbol}")
            return False
        
        # Get nearest expiry
        now = datetime.now()
        expiry_date = self._get_nearest_expiry(symbol)
        
        # Round to nearest strike price interval
        if symbol == "NIFTY":
            strike_interval = 50
        elif symbol == "BANKNIFTY":
            strike_interval = 100
        else:
            strike_interval = 50  # Default
            
        atm_strike = round(current_value / strike_interval) * strike_interval
        
        # Subscribe to strikes around ATM
        strikes_to_subscribe = []
        for i in range(-depth, depth + 1):
            strikes_to_subscribe.append(atm_strike + (i * strike_interval))
        
        # Subscribe to both calls and puts
        exchange = "NFO"  # NSE Futures & Options
        for strike in strikes_to_subscribe:
            # Subscribe to call
            call_symbol = f"{symbol}{expiry_date.strftime('%d%b%y').upper()}{strike}CE"
            call_instrument = self.api.get_instrument_by_symbol(call_symbol, exchange)
            if call_instrument:
                instrument_id = call_instrument["instrumentId"]
                self.api.subscribe_ticker(instrument_id)
                with self.lock:
                    self.subscribed_instruments[instrument_id] = {
                        "symbol": call_symbol,
                        "type": "option",
                        "option_type": "CE",
                        "strike": strike,
                        "underlying": symbol,
                        "expiry": expiry_date,
                        "exchange": exchange,
                        "last_price": None,
                        "timestamp": None
                    }
                
            # Subscribe to put
            put_symbol = f"{symbol}{expiry_date.strftime('%d%b%y').upper()}{strike}PE"
            put_instrument = self.api.get_instrument_by_symbol(put_symbol, exchange)
            if put_instrument:
                instrument_id = put_instrument["instrumentId"]
                self.api.subscribe_ticker(instrument_id)
                with self.lock:
                    self.subscribed_instruments[instrument_id] = {
                        "symbol": put_symbol,
                        "type": "option",
                        "option_type": "PE",
                        "strike": strike,
                        "underlying": symbol,
                        "expiry": expiry_date,
                        "exchange": exchange,
                        "last_price": None,
                        "timestamp": None
                    }
        
        logger.info(f"Subscribed to {symbol} option chain with {len(strikes_to_subscribe)} strikes")
        return True
    
    def _get_nearest_expiry(self, symbol):
        """Get the nearest expiry date for the given symbol"""
        now = datetime.now()
        current_weekday = now.weekday()  # 0 is Monday, 6 is Sunday
        
        # For weekly options (NIFTY, BANKNIFTY)
        if symbol in ["NIFTY", "BANKNIFTY"]:
            # Determine the next expiry Thursday
            days_to_thursday = (3 - current_weekday) % 7
            # If it's Thursday after market hours, move to next Thursday
            if current_weekday == 3 and now.hour >= 15:
                days_to_thursday = 7
            
            return now.date() + timedelta(days=days_to_thursday)
        else:
            # For monthly expiry (typically last Thursday of month)
            # This is a simplified approach
            current_month = now.month
            current_year = now.year
            
            # Find last Thursday of current month
            last_day = 31  # Start from the 31st
            while True:
                try:
                    candidate = datetime(current_year, current_month, last_day)
                    break
                except ValueError:
                    last_day -= 1
            
            # Find the last Thursday
            while candidate.weekday() != 3:  # 3 is Thursday
                candidate -= timedelta(days=1)
            
            # If we're past this month's expiry, go to next month
            if now.date() > candidate.date():
                if current_month == 12:
                    current_month = 1
                    current_year += 1
                else:
                    current_month += 1
                
                # Find last Thursday of next month
                last_day = 31
                while True:
                    try:
                        candidate = datetime(current_year, current_month, last_day)
                        break
                    except ValueError:
                        last_day -= 1
                
                while candidate.weekday() != 3:  # 3 is Thursday
                    candidate -= timedelta(days=1)
            
            return candidate.date()
    
    def _process_tick_data(self, tick_data):
        """Process incoming tick data"""
        if "instrument_id" not in tick_data:
            return
            
        instrument_id = tick_data["instrument_id"]
        
        # Update our data buffers
        with self.lock:
            # Store the tick
            self.data_buffer[instrument_id].append(tick_data)
            
            # Update instrument info
            if instrument_id in self.subscribed_instruments:
                instrument = self.subscribed_instruments[instrument_id]
                instrument["last_price"] = tick_data.get("last_price")
                instrument["timestamp"] = tick_data.get("timestamp")
                
                # Update OHLCV for technical indicators
                self._update_ohlcv(instrument_id, tick_data)
                
                # Update option chain if this is an option
                if instrument["type"] == "option":
                    underlying = instrument["underlying"]
                    if underlying not in self.option_chains:
                        self.option_chains[underlying] = {}
                    
                    expiry = instrument["expiry"]
                    if expiry not in self.option_chains[underlying]:
                        self.option_chains[underlying][expiry] = {}
                    
                    strike = instrument["strike"]
                    if strike not in self.option_chains[underlying][expiry]:
                        self.option_chains[underlying][expiry][strike] = {}
                    
                    option_type = instrument["option_type"]  # CE or PE
                    self.option_chains[underlying][expiry][strike][option_type] = {
                        "instrument_id": instrument_id,
                        "last_price": instrument["last_price"],
                        "timestamp": instrument["timestamp"],
                        # Add other details here (open, high, low, volume, etc.)
                    }
    
    def _update_ohlcv(self, instrument_id, tick_data):
        """Update OHLCV data for the instrument"""
        timestamp = tick_data.get("timestamp")
        if not timestamp:
            return
            
        timestamp = pd.to_datetime(timestamp)
        price = tick_data.get("last_price")
        volume = tick_data.get("volume", 0)
        
        # Update different timeframes
        self._update_timeframe('1m', instrument_id, timestamp, price, volume)
        self._update_timeframe('5m', instrument_id, timestamp, price, volume)
        self._update_timeframe('15m', instrument_id, timestamp, price, volume)
        self._update_timeframe('1h', instrument_id, timestamp, price, volume)
        self._update_timeframe('D', instrument_id, timestamp, price, volume)
        
        # Calculate technical indicators after updating OHLCV
        self._calculate_technical_indicators(instrument_id)
    
    def _update_timeframe(self, timeframe, instrument_id, timestamp, price, volume):
        """Update a specific timeframe's OHLCV data"""
        # Determine the bar timestamp based on timeframe
        if timeframe == '1m':
            bar_timestamp = timestamp.floor('1min')
        elif timeframe == '5m':
            bar_timestamp = timestamp.floor('5min')
        elif timeframe == '15m':
            bar_timestamp = timestamp.floor('15min')
        elif timeframe == '1h':
            bar_timestamp = timestamp.floor('1h')
        else:  # Daily
            bar_timestamp = timestamp.floor('1d')
        
        # Initialize if needed
        if instrument_id not in self.timeframes[timeframe]:
            self.timeframes[timeframe][instrument_id] = {
                'timestamps': [],
                'open': [],
                'high': [],
                'low': [],
                'close': [],
                'volume': []
            }
        
        data = self.timeframes[timeframe][instrument_id]
        
        # Check if we're still in the current bar or need a new one
        if not data['timestamps'] or data['timestamps'][-1] != bar_timestamp:
            # Start a new bar
            data['timestamps'].append(bar_timestamp)
            data['open'].append(price)
            data['high'].append(price)
            data['low'].append(price)
            data['close'].append(price)
            data['volume'].append(volume)
        else:
            # Update the current bar
            data['high'][-1] = max(data['high'][-1], price)
            data['low'][-1] = min(data['low'][-1], price)
            data['close'][-1] = price
            data['volume'][-1] += volume
    
    def _calculate_technical_indicators(self, instrument_id):
        """Calculate technical indicators for the instrument"""
        # Make sure we have enough data
        if instrument_id not in self.timeframes['1m']:
            return
            
        # Initialize indicators dictionary for this instrument if needed
        if instrument_id not in self.indicators:
            self.indicators[instrument_id] = {}
        
        # Calculate indicators for each timeframe
        for timeframe in self.timeframes:
            if instrument_id in self.timeframes[timeframe] and len(self.timeframes[timeframe][instrument_id]['close']) > 0:
                # Create dataframe from OHLCV data
                df = pd.DataFrame({
                    'open': self.timeframes[timeframe][instrument_id]['open'],
                    'high': self.timeframes[timeframe][instrument_id]['high'],
                    'low': self.timeframes[timeframe][instrument_id]['low'],
                    'close': self.timeframes[timeframe][instrument_id]['close'],
                    'volume': self.timeframes[timeframe][instrument_id]['volume']
                }, index=self.timeframes[timeframe][instrument_id]['timestamps'])
                
                # Calculate indicators only if we have enough data
                if len(df) > self.indicator_periods['rsi']:
                    self.indicators[instrument_id][f'rsi_{timeframe}'] = self._calculate_rsi(df)
                
                if len(df) > self.indicator_periods['bollinger']:
                    upper, middle, lower = self._calculate_bollinger_bands(df)
                    self.indicators[instrument_id][f'bb_upper_{timeframe}'] = upper
                    self.indicators[instrument_id][f'bb_middle_{timeframe}'] = middle
                    self.indicators[instrument_id][f'bb_lower_{timeframe}'] = lower
                
                if len(df) > max(self.indicator_periods['macd']['slow'], self.indicator_periods['macd']['fast']):
                    macd, signal, hist = self._calculate_macd(df)
                    self.indicators[instrument_id][f'macd_{timeframe}'] = macd
                    self.indicators[instrument_id][f'macd_signal_{timeframe}'] = signal
                    self.indicators[instrument_id][f'macd_hist_{timeframe}'] = hist
                
                if len(df) > self.indicator_periods['atr']:
                    self.indicators[instrument_id][f'atr_{timeframe}'] = self._calculate_atr(df)
                
                if len(df) > self.indicator_periods['entropy']:
                    self.indicators[instrument_id][f'entropy_{timeframe}'] = self._calculate_entropy(df)
                
                # Volume based indicators
                self.indicators[instrument_id][f'obv_{timeframe}'] = self._calculate_obv(df)
                
                # Moving averages
                for period in self.indicator_periods['ema']:
                    if len(df) > period:
                        self.indicators[instrument_id][f'ema{period}_{timeframe}'] = self._calculate_ema(df, period)
    
    def _calculate_rsi(self, df, period=14):
        """Calculate Relative Strength Index"""
        close_diff = df['close'].diff()
        gain = close_diff.where(close_diff > 0, 0).fillna(0)
        loss = -close_diff.where(close_diff < 0, 0).fillna(0)
        
        avg_gain = gain.rolling(window=period).mean()
        avg_loss = loss.rolling(window=period).mean()
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        return rsi.iloc[-1] if not pd.isna(rsi.iloc[-1]) else 50
    
    def _calculate_bollinger_bands(self, df, period=20, std_dev=2):
        """Calculate Bollinger Bands"""
        middle = df['close'].rolling(window=period).mean()
        std = df['close'].rolling(window=period).std()
        upper = middle + (std * std_dev)
        lower = middle - (std * std_dev)
        
        return (
            upper.iloc[-1] if not pd.isna(upper.iloc[-1]) else df['close'].iloc[-1],
            middle.iloc[-1] if not pd.isna(middle.iloc[-1]) else df['close'].iloc[-1],
            lower.iloc[-1] if not pd.isna(lower.iloc[-1]) else df['close'].iloc[-1]
        )
    
    def _calculate_macd(self, df, fast=12, slow=26, signal=9):
        """Calculate MACD (Moving Average Convergence Divergence)"""
        ema_fast = df['close'].ewm(span=fast, adjust=False).mean()
        ema_slow = df['close'].ewm(span=slow, adjust=False).mean()
        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=signal, adjust=False).mean()
        histogram = macd_line - signal_line
        
        return (
            macd_line.iloc[-1] if not pd.isna(macd_line.iloc[-1]) else 0,
            signal_line.iloc[-1] if not pd.isna(signal_line.iloc[-1]) else 0,
            histogram.iloc[-1] if not pd.isna(histogram.iloc[-1]) else 0
        )
    
    def _calculate_atr(self, df, period=14):
        """Calculate Average True Range"""
        high_low = df['high'] - df['low']
        high_close = (df['high'] - df['close'].shift()).abs()
        low_close = (df['low'] - df['close'].shift()).abs()
        
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        atr = tr.rolling(period).mean()
        
        return atr.iloc[-1] if not pd.isna(atr.iloc[-1]) else 0
    
    def _calculate_entropy(self, df, period=20):
        """Calculate price entropy (measure of uncertainty/volatility)"""
        if len(df) < period:
            return 0
            
        # Get normalized returns
        returns = df['close'].pct_change().dropna()
        if len(returns) < period:
            return 0
            
        # Use rolling window to calculate entropy
        entropy_window = returns.iloc[-period:]
        
        # Create histogram
        hist, _ = np.histogram(entropy_window, bins=10, density=True)
        
        # Calculate entropy
        entropy = -np.sum(hist * np.log2(hist + 1e-10))  # Add small value to avoid log(0)
        
        return entropy
    
    def _calculate_ema(self, df, period):
        """Calculate Exponential Moving Average"""
        ema = df['close'].ewm(span=period, adjust=False).mean()
        return ema.iloc[-1] if not pd.isna(ema.iloc[-1]) else df['close'].iloc[-1]
    
    def _calculate_obv(self, df):
        """Calculate On-Balance Volume"""
        close_diff = df['close'].diff()
        obv = pd.Series(index=df.index)
        obv.iloc[0] = 0
        
        for i in range(1, len(df)):
            if close_diff.iloc[i] > 0:
                obv.iloc[i] = obv.iloc[i-1] + df['volume'].iloc[i]
            elif close_diff.iloc[i] < 0:
                obv.iloc[i] = obv.iloc[i-1] - df['volume'].iloc[i]
            else:
                obv.iloc[i] = obv.iloc[i-1]
                
        return obv.iloc[-1]
    
    def get_option_chain_snapshot(self, underlying):
        """Get current snapshot of option chain for analysis"""
        with self.lock:
            if underlying not in self.option_chains:
                return None
                
            # Get nearest expiry
            expiries = sorted(self.option_chains[underlying].keys())
            if not expiries:
                return None
                
            nearest_expiry = expiries[0]
            chain = self.option_chains[underlying][nearest_expiry]
            
            # Transform into useful format
            strikes = sorted(chain.keys())
            result = []
            
            for strike in strikes:
                strike_data = chain[strike]
                call_data = strike_data.get('CE', {})
                put_data = strike_data.get('PE', {})
                
                result.append({
                    'strike': strike,
                    'call_price': call_data.get('last_price'),
                    'put_price': put_data.get('last_price'),
                    'call_id': call_data.get('instrument_id'),
                    'put_id': put_data.get('instrument_id')
                })
                
            return {
                'underlying': underlying,
                'expiry': nearest_expiry,
                'data': result
            }
    
    def get_technical_indicators(self, instrument_id, timeframe='5m'):
        """Get current technical indicators for an instrument"""
        with self.lock:
            if instrument_id not in self.indicators:
                return None
                
            # Filter indicators for the requested timeframe
            result = {}
            for key, value in self.indicators[instrument_id].items():
                if key.endswith(f'_{timeframe}'):
                    # Remove the timeframe suffix for cleaner output
                    clean_key = key.replace(f'_{timeframe}', '')
                    result[clean_key] = value
                    
            return result
    
    def get_top_liquid_stocks(self, count=10):
        """Get the top liquid stocks based on volume"""
        # This would normally query market data or a predefined list
        # For this implementation, return a static list of liquid Indian stocks
        return [
            "RELIANCE", "HDFCBANK", "INFY", "TCS", "ICICIBANK",
            "HINDUNILVR", "SBIN", "BHARTIARTL", "KOTAKBANK", "LT"
        ][:count]
    
    def unsubscribe_all(self):
        """Unsubscribe from all market data"""
        with self.lock:
            for instrument_id in self.subscribed_instruments:
                self.api.unsubscribe_ticker(instrument_id)
            self.subscribed_instruments.clear()
            logger.info("Unsubscribed from all market data")