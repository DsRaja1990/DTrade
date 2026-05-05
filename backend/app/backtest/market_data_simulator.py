"""
Market Data Simulator for Backtesting

This module provides realistic market data simulation for the
time-based execution strategy backtest.
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import logging

logger = logging.getLogger(__name__)

class MarketDataSimulator:
    """
    Advanced market data simulator with realistic price patterns,
    volatility clustering, and intraday seasonality.
    """

    def __init__(self):
        self.volatility_regimes = {
            "low": 0.12,    # 12% annual volatility
            "medium": 0.18, # 18% annual volatility
            "high": 0.25    # 25% annual volatility
        }
        
        self.market_hours = {
            "pre_open": (9, 0),
            "open": (9, 15),
            "close": (15, 30),
            "post_close": (16, 0)
        }

    def generate_realistic_price_series(self, 
                                      instrument: str,
                                      start_date: datetime,
                                      end_date: datetime,
                                      frequency: str = "15min") -> pd.DataFrame:
        """
        Generate realistic intraday price series with market microstructure effects
        
        Args:
            instrument: NIFTY, BANKNIFTY, or SENSEX
            start_date: Start date for simulation
            end_date: End date for simulation
            frequency: Data frequency (15min, 5min, 1min)
            
        Returns:
            DataFrame with OHLCV data
        """
        
        # Base parameters by instrument
        instrument_params = self._get_instrument_params(instrument)
        
        # Generate trading calendar
        trading_days = pd.bdate_range(start=start_date, end=end_date)
        
        all_data = []
        
        for day in trading_days:
            daily_data = self._generate_intraday_data(
                day, instrument_params, frequency
            )
            all_data.append(daily_data)
        
        # Combine all days
        market_data = pd.concat(all_data, ignore_index=True)
        market_data.set_index('timestamp', inplace=True)
        
        logger.info(f"Generated {len(market_data)} data points for {instrument}")
        return market_data

    def _get_instrument_params(self, instrument: str) -> Dict:
        """Get instrument-specific simulation parameters"""
        
        base_prices = {
            "NIFTY": 22000,
            "BANKNIFTY": 48000,
            "SENSEX": 72000
        }
        
        daily_volatilities = {
            "NIFTY": 0.018,    # 1.8% daily
            "BANKNIFTY": 0.025, # 2.5% daily
            "SENSEX": 0.016     # 1.6% daily
        }
        
        correlations = {
            "NIFTY": {"BANKNIFTY": 0.85, "SENSEX": 0.90},
            "BANKNIFTY": {"NIFTY": 0.85, "SENSEX": 0.80},
            "SENSEX": {"NIFTY": 0.90, "BANKNIFTY": 0.80}
        }
        
        return {
            "base_price": base_prices[instrument],
            "daily_vol": daily_volatilities[instrument],
            "correlations": correlations[instrument],
            "drift": 0.0005,  # Small positive drift
            "jump_intensity": 0.02,  # 2% chance of jump per day
            "jump_size": 0.01  # 1% average jump size
        }

    def _generate_intraday_data(self, 
                               trading_day: datetime,
                               params: Dict,
                               frequency: str) -> pd.DataFrame:
        """Generate intraday data for a single trading day"""
        
        # Create timestamp range for the day
        if frequency == "15min":
            freq = "15T"
        elif frequency == "5min":
            freq = "5T"
        elif frequency == "1min":
            freq = "1T"
        else:
            freq = "15T"
        
        # Trading session: 9:15 AM to 3:30 PM
        start_time = trading_day.replace(hour=9, minute=15)
        end_time = trading_day.replace(hour=15, minute=30)
        
        timestamps = pd.date_range(start=start_time, end=end_time, freq=freq)
        
        # Generate base price path
        n_points = len(timestamps)
        
        # Intraday volatility pattern
        vol_pattern = self._get_intraday_volatility_pattern(timestamps, params["daily_vol"])
        
        # Generate returns with volatility clustering
        returns = self._generate_realistic_returns(n_points, vol_pattern, params)
        
        # Apply price constraints and market microstructure
        prices = self._generate_price_path(params["base_price"], returns, timestamps)
        
        # Generate volume pattern
        volumes = self._generate_volume_pattern(timestamps, prices)
        
        # Create OHLC from price path
        ohlc_data = self._create_ohlc_bars(timestamps, prices, volumes, frequency)
        
        return ohlc_data

    def _get_intraday_volatility_pattern(self, 
                                       timestamps: pd.DatetimeIndex,
                                       daily_vol: float) -> np.ndarray:
        """Generate realistic intraday volatility pattern"""
        
        vol_multipliers = []
        
        for ts in timestamps:
            hour = ts.hour
            minute = ts.minute
            time_decimal = hour + minute / 60.0
            
            # U-shaped volatility pattern (high at open/close, low at lunch)
            if 9.25 <= time_decimal <= 10.0:  # Opening hour
                multiplier = 2.5
            elif 10.0 <= time_decimal <= 11.0:  # Post-opening
                multiplier = 1.8
            elif 11.0 <= time_decimal <= 13.0:  # Mid-day (lunch)
                multiplier = 0.6
            elif 13.0 <= time_decimal <= 14.0:  # Post-lunch
                multiplier = 1.2
            elif 14.0 <= time_decimal <= 15.0:  # Pre-close
                multiplier = 1.6
            elif 15.0 <= time_decimal <= 15.5:  # Closing
                multiplier = 2.2
            else:
                multiplier = 1.0
            
            vol_multipliers.append(multiplier)
        
        # Convert daily vol to intraday
        intraday_vol = daily_vol / np.sqrt(len(timestamps))
        
        return np.array(vol_multipliers) * intraday_vol

    def _generate_realistic_returns(self, 
                                   n_points: int,
                                   vol_pattern: np.ndarray,
                                   params: Dict) -> np.ndarray:
        """Generate realistic returns with clustering and jumps"""
        
        # Base random returns
        base_returns = np.random.normal(0, 1, n_points)
        
        # Apply GARCH-like volatility clustering
        returns = []
        volatility = vol_pattern[0]
        
        for i in range(n_points):
            # Update volatility (simple GARCH(1,1))
            if i > 0:
                alpha, beta, omega = 0.1, 0.85, vol_pattern[i] * 0.05
                volatility = omega + alpha * (returns[-1]**2) + beta * volatility
            else:
                volatility = vol_pattern[i]
            
            # Generate return with current volatility
            return_val = base_returns[i] * volatility + params["drift"] / n_points
            
            # Add occasional jumps
            if np.random.random() < params["jump_intensity"] / n_points:
                jump_direction = np.random.choice([-1, 1])
                jump_size = np.random.exponential(params["jump_size"])
                return_val += jump_direction * jump_size
            
            returns.append(return_val)
        
        return np.array(returns)

    def _generate_price_path(self, 
                           base_price: float,
                           returns: np.ndarray,
                           timestamps: pd.DatetimeIndex) -> np.ndarray:
        """Generate price path with market constraints"""
        
        # Apply returns to generate price path
        log_prices = np.log(base_price) + np.cumsum(returns)
        prices = np.exp(log_prices)
        
        # Apply circuit breaker constraints (±10% for indices)
        lower_limit = base_price * 0.90
        upper_limit = base_price * 1.10
        
        prices = np.clip(prices, lower_limit, upper_limit)
        
        # Add mean reversion tendency
        for i in range(1, len(prices)):
            deviation = (prices[i] - base_price) / base_price
            if abs(deviation) > 0.03:  # If more than 3% away
                reversion_force = -0.1 * deviation
                prices[i] = prices[i] * (1 + reversion_force)
        
        return prices

    def _generate_volume_pattern(self, 
                               timestamps: pd.DatetimeIndex,
                               prices: np.ndarray) -> np.ndarray:
        """Generate realistic volume pattern"""
        
        volumes = []
        
        for i, ts in enumerate(timestamps):
            hour = ts.hour
            minute = ts.minute
            time_decimal = hour + minute / 60.0
            
            # Base volume (higher at open/close)
            if 9.25 <= time_decimal <= 10.0:  # Opening
                base_vol = 100000
            elif 15.0 <= time_decimal <= 15.5:  # Closing
                base_vol = 80000
            elif 11.0 <= time_decimal <= 13.0:  # Lunch
                base_vol = 20000
            else:
                base_vol = 50000
            
            # Volume increases with price movement
            if i > 0:
                price_change = abs(prices[i] - prices[i-1]) / prices[i-1]
                volume_multiplier = 1 + (price_change * 10)
            else:
                volume_multiplier = 1
            
            # Add randomness
            random_factor = np.random.lognormal(0, 0.3)
            
            volume = int(base_vol * volume_multiplier * random_factor)
            volumes.append(volume)
        
        return np.array(volumes)

    def _create_ohlc_bars(self, 
                         timestamps: pd.DatetimeIndex,
                         prices: np.ndarray,
                         volumes: np.ndarray,
                         frequency: str) -> pd.DataFrame:
        """Create OHLC bars from tick data"""
        
        # For simplicity, create OHLC from single price series
        # In reality, we'd use tick-by-tick data
        
        data = []
        
        for i, (ts, price, volume) in enumerate(zip(timestamps, prices, volumes)):
            # Generate realistic OHLC around the price
            if i == 0:
                open_price = price
            else:
                open_price = prices[i-1]  # Previous close
            
            # Generate high/low with realistic spread
            spread_pct = np.random.uniform(0.0005, 0.002)  # 0.05% to 0.2%
            
            high = price * (1 + spread_pct)
            low = price * (1 - spread_pct)
            close = price
            
            # Ensure OHLC consistency
            high = max(high, open_price, close)
            low = min(low, open_price, close)
            
            data.append({
                'timestamp': ts,
                'open': open_price,
                'high': high,
                'low': low,
                'close': close,
                'volume': volume,
                'price': price  # Keep mid-price for simplicity
            })
        
        return pd.DataFrame(data)

    def add_options_data(self, 
                        market_data: pd.DataFrame,
                        instrument: str) -> Dict:
        """Add realistic options pricing data"""
        
        options_data = {}
        
        for timestamp, row in market_data.iterrows():
            spot_price = row['price']
            
            # Generate strikes around spot
            if instrument in ["NIFTY", "BANKNIFTY"]:
                strike_gap = 50
            else:  # SENSEX
                strike_gap = 100
            
            atm_strike = round(spot_price / strike_gap) * strike_gap
            
            # Create strikes from ATM-500 to ATM+500
            strikes = []
            for i in range(-10, 11):
                strikes.append(atm_strike + (i * strike_gap))
            
            strike_data = {}
            
            for strike in strikes:
                # Simplified IV smile
                moneyness = spot_price / strike
                
                if 0.98 <= moneyness <= 1.02:  # ATM
                    iv = 0.18 + np.random.normal(0, 0.01)
                elif moneyness < 0.98:  # OTM puts
                    skew_effect = (0.98 - moneyness) * 0.5
                    iv = 0.20 + skew_effect + np.random.normal(0, 0.015)
                else:  # OTM calls
                    iv = 0.16 + np.random.normal(0, 0.01)
                
                iv = max(0.10, min(0.50, iv))  # Reasonable bounds
                
                # Time to expiry (assume weekly options)
                days_to_expiry = max(1, 5 - timestamp.weekday())
                time_value_factor = np.sqrt(days_to_expiry / 365)
                
                # Simplified option pricing
                intrinsic_call = max(0, spot_price - strike)
                intrinsic_put = max(0, strike - spot_price)
                
                time_value = iv * spot_price * time_value_factor * 0.4
                
                call_price = intrinsic_call + time_value
                put_price = intrinsic_put + time_value
                
                strike_data[strike] = {
                    'call_price': call_price,
                    'put_price': put_price,
                    'call_iv': iv,
                    'put_iv': iv * 1.05,  # Put skew
                    'volume': max(10, int(np.random.lognormal(6, 1)))
                }
            
            options_data[timestamp] = strike_data
        
        return options_data

    def simulate_market_impact(self, 
                             order_size: int,
                             instrument: str,
                             execution_style: str) -> Dict:
        """Simulate market impact for different execution styles"""
        
        # Base impact parameters
        base_impact = {
            "NIFTY": 0.0002,
            "BANKNIFTY": 0.0003,
            "SENSEX": 0.0002
        }
        
        # Execution style multipliers
        style_multipliers = {
            "ICEBERG": 0.6,
            "VWAP": 0.4,
            "TWAP": 0.5,
            "MARKET": 1.5,
            "DARK_POOL": 0.3
        }
        
        # Size impact (square root law)
        size_impact = np.sqrt(order_size / 100) * 0.1
        
        total_impact = base_impact[instrument] * style_multipliers.get(execution_style, 1.0) * (1 + size_impact)
        
        return {
            "market_impact_bps": total_impact * 10000,
            "temporary_impact": total_impact * 0.6,
            "permanent_impact": total_impact * 0.4,
            "execution_shortfall": total_impact * order_size
        }
