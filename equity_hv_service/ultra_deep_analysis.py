"""
🔬 ULTRA DEEP MARKET ANALYSIS - CRACKING INDIAN MARKET PATTERNS
================================================================
Goal: Find patterns that deliver 90%+ Win Rate and 300%+ Monthly Returns

This analysis will:
1. Test every RSI level (20-45) for optimal entry
2. Find the exact confirmation combinations that work
3. Analyze intraday vs swing patterns
4. Find high-frequency setups with maximum edge
5. Calculate realistic position sizing for 300% returns
"""

import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta
from collections import defaultdict
import warnings
warnings.filterwarnings('ignore')

print("=" * 80)
print("🔬 ULTRA DEEP MARKET ANALYSIS - CRACKING INDIAN MARKET")
print("=" * 80)
print(f"Analysis Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
print("Goal: 90%+ Win Rate | 300%+ Monthly Returns")
print("=" * 80)

# Extended stock universe - top liquid Indian stocks
STOCKS = [
    "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "ICICIBANK.NS",
    "HINDUNILVR.NS", "SBIN.NS", "BHARTIARTL.NS", "KOTAKBANK.NS", "ITC.NS",
    "LT.NS", "AXISBANK.NS", "ASIANPAINT.NS", "MARUTI.NS", "TITAN.NS",
    "SUNPHARMA.NS", "BAJFINANCE.NS", "WIPRO.NS", "ULTRACEMCO.NS", "ONGC.NS",
    "NTPC.NS", "POWERGRID.NS", "HCLTECH.NS", "ADANIENT.NS",
    "TATAMOTORS.NS", "INDUSINDBK.NS", "JSWSTEEL.NS", "TATASTEEL.NS", "TECHM.NS",
    "DRREDDY.NS", "BAJAJFINSV.NS", "CIPLA.NS", "GRASIM.NS", "NESTLEIND.NS",
    "BRITANNIA.NS", "BPCL.NS", "DIVISLAB.NS", "HINDALCO.NS", "COALINDIA.NS",
    "ADANIPORTS.NS", "EICHERMOT.NS", "HEROMOTOCO.NS", "APOLLOHOSP.NS", "TATACONSUM.NS"
]

def calculate_advanced_indicators(df):
    """Calculate comprehensive indicators for pattern detection"""
    if len(df) < 50:
        return df
    
    # RSI with multiple periods
    for period in [7, 14, 21]:
        delta = df['Close'].diff()
        gain = delta.where(delta > 0, 0)
        loss = (-delta).where(delta < 0, 0)
        avg_gain = gain.rolling(period).mean()
        avg_loss = loss.rolling(period).mean()
        rs = avg_gain / (avg_loss + 1e-10)
        df[f'RSI_{period}'] = 100 - (100 / (1 + rs))
    
    df['RSI'] = df['RSI_14']
    df['RSI_prev'] = df['RSI'].shift(1)
    df['RSI_prev2'] = df['RSI'].shift(2)
    df['RSI_prev3'] = df['RSI'].shift(3)
    
    # RSI patterns
    df['RSI_turning_up'] = (df['RSI'] > df['RSI_prev']) & (df['RSI_prev'] <= df['RSI_prev2'])
    df['RSI_double_bottom'] = (df['RSI'] > df['RSI_prev']) & (df['RSI_prev'] < df['RSI_prev2']) & (df['RSI_prev2'] < df['RSI_prev3'])
    df['RSI_oversold_bounce'] = (df['RSI'] > 30) & (df['RSI_prev'] < 30)
    df['RSI_extreme_oversold'] = df['RSI'] < 25
    
    # MACD with sensitivity analysis
    for fast, slow in [(8, 17), (12, 26)]:
        exp_fast = df['Close'].ewm(span=fast, adjust=False).mean()
        exp_slow = df['Close'].ewm(span=slow, adjust=False).mean()
        df[f'MACD_{fast}_{slow}'] = exp_fast - exp_slow
        df[f'MACD_signal_{fast}_{slow}'] = df[f'MACD_{fast}_{slow}'].ewm(span=9, adjust=False).mean()
        df[f'MACD_hist_{fast}_{slow}'] = df[f'MACD_{fast}_{slow}'] - df[f'MACD_signal_{fast}_{slow}']
    
    df['MACD'] = df['MACD_12_26']
    df['MACD_signal'] = df['MACD_signal_12_26']
    df['MACD_hist'] = df['MACD_hist_12_26']
    df['MACD_hist_prev'] = df['MACD_hist'].shift(1)
    df['MACD_hist_prev2'] = df['MACD_hist'].shift(2)
    
    # MACD patterns
    df['MACD_hist_turning'] = (df['MACD_hist'] > df['MACD_hist_prev']) & (df['MACD_hist_prev'] <= df['MACD_hist_prev2'])
    df['MACD_bullish_cross'] = (df['MACD'] > df['MACD_signal']) & (df['MACD'].shift(1) <= df['MACD_signal'].shift(1))
    df['MACD_above_signal'] = df['MACD'] > df['MACD_signal']
    df['MACD_positive'] = df['MACD'] > 0
    df['MACD_hist_positive'] = df['MACD_hist'] > 0
    df['MACD_hist_accelerating'] = df['MACD_hist'] > df['MACD_hist_prev']
    
    # Bollinger Bands
    df['BB_mid'] = df['Close'].rolling(20).mean()
    df['BB_std'] = df['Close'].rolling(20).std()
    df['BB_upper'] = df['BB_mid'] + 2 * df['BB_std']
    df['BB_lower'] = df['BB_mid'] - 2 * df['BB_std']
    df['BB_pos'] = (df['Close'] - df['BB_lower']) / (df['BB_upper'] - df['BB_lower'] + 1e-10)
    df['BB_squeeze'] = df['BB_std'] / df['BB_mid'] < 0.02  # Low volatility
    df['BB_touch_lower'] = df['Low'] <= df['BB_lower']
    df['BB_bounce_lower'] = df['BB_touch_lower'].shift(1) & (df['Close'] > df['Open'])
    
    # Volume analysis
    df['Vol_MA'] = df['Volume'].rolling(20).mean()
    df['Vol_ratio'] = df['Volume'] / (df['Vol_MA'] + 1)
    df['Vol_spike'] = df['Vol_ratio'] > 1.5
    df['Vol_dry_up'] = df['Vol_ratio'] < 0.5
    df['Vol_increasing'] = df['Volume'] > df['Volume'].shift(1)
    
    # Price action
    df['body'] = df['Close'] - df['Open']
    df['body_pct'] = abs(df['body']) / df['Open'] * 100
    df['upper_wick'] = df['High'] - df[['Open', 'Close']].max(axis=1)
    df['lower_wick'] = df[['Open', 'Close']].min(axis=1) - df['Low']
    df['is_green'] = df['Close'] > df['Open']
    df['is_strong_green'] = df['is_green'] & (df['body_pct'] > 0.5)
    df['is_doji'] = df['body_pct'] < 0.1
    df['is_hammer'] = (df['lower_wick'] > 2 * abs(df['body'])) & (df['upper_wick'] < abs(df['body']))
    df['is_bullish_engulfing'] = df['is_green'] & (~df['is_green'].shift(1)) & (df['Close'] > df['Open'].shift(1)) & (df['Open'] < df['Close'].shift(1))
    
    # Moving averages
    for period in [5, 10, 20, 50, 200]:
        df[f'SMA_{period}'] = df['Close'].rolling(period).mean()
        df[f'EMA_{period}'] = df['Close'].ewm(span=period, adjust=False).mean()
    
    df['price_above_ema5'] = df['Close'] > df['EMA_5']
    df['price_above_ema10'] = df['Close'] > df['EMA_10']
    df['price_above_sma20'] = df['Close'] > df['SMA_20']
    df['price_above_sma50'] = df['Close'] > df['SMA_50']
    df['ema5_above_ema10'] = df['EMA_5'] > df['EMA_10']
    df['ema_golden_cross'] = (df['EMA_5'] > df['EMA_10']) & (df['EMA_5'].shift(1) <= df['EMA_10'].shift(1))
    
    # Trend
    df['trend_up'] = df['SMA_20'] > df['SMA_50']
    df['strong_trend_up'] = df['trend_up'] & (df['SMA_50'] > df['SMA_50'].shift(5))
    
    # Support/Resistance
    df['recent_low_3'] = df['Low'].rolling(3).min()
    df['recent_low_5'] = df['Low'].rolling(5).min()
    df['recent_high_3'] = df['High'].rolling(3).max()
    df['above_recent_support'] = df['Close'] > df['recent_low_5']
    df['near_support'] = (df['Close'] - df['recent_low_5']) / df['Close'] < 0.02
    
    # Momentum
    df['momentum_1d'] = df['Close'].pct_change()
    df['momentum_3d'] = df['Close'].pct_change(3)
    df['momentum_5d'] = df['Close'].pct_change(5)
    df['momentum_positive'] = df['momentum_1d'] > 0
    df['momentum_accelerating'] = df['momentum_1d'] > df['momentum_1d'].shift(1)
    
    # ATR for volatility
    df['TR'] = pd.concat([
        df['High'] - df['Low'],
        abs(df['High'] - df['Close'].shift(1)),
        abs(df['Low'] - df['Close'].shift(1))
    ], axis=1).max(axis=1)
    df['ATR'] = df['TR'].rolling(14).mean()
    df['ATR_pct'] = df['ATR'] / df['Close'] * 100
    
    # Consecutive patterns
    df['consecutive_green'] = df['is_green'].rolling(3).sum()
    df['consecutive_higher_lows'] = (df['Low'] > df['Low'].shift(1)).rolling(3).sum()
    
    return df

def analyze_pattern_performance(df, holding_days=[1, 2, 3, 5]):
    """Analyze returns after specific patterns"""
    results = []
    
    for hd in holding_days:
        df[f'future_return_{hd}d'] = df['Close'].shift(-hd) / df['Close'] - 1
        df[f'future_max_{hd}d'] = df['High'].rolling(hd).max().shift(-hd) / df['Close'] - 1
        df[f'future_min_{hd}d'] = df['Low'].rolling(hd).min().shift(-hd) / df['Close'] - 1
    
    return df

def find_ultra_high_winrate_patterns(all_data):
    """Find patterns with 90%+ win rate"""
    print("\n🔍 SEARCHING FOR 90%+ WIN RATE PATTERNS...")
    print("-" * 80)
    
    # Collect all signals
    all_signals = []
    
    for symbol, df in all_data.items():
        if len(df) < 60:
            continue
            
        df = df.dropna()
        
        for i in range(50, len(df) - 5):
            row = df.iloc[i]
            
            # Skip if no future data
            if pd.isna(row.get('future_return_1d')):
                continue
            
            rsi = row['RSI']
            rsi_int = int(round(rsi))
            
            # Count confirmations with detailed tracking
            confs = []
            
            # RSI patterns
            if rsi < 35:
                confs.append('RSI_OVERSOLD')
            if row['RSI_turning_up']:
                confs.append('RSI_TURN')
            if row['RSI_double_bottom']:
                confs.append('RSI_DOUBLE_BOTTOM')
            if row['RSI_oversold_bounce']:
                confs.append('RSI_BOUNCE')
            if row['RSI_7'] < row['RSI_14']:  # Short-term more oversold
                confs.append('RSI_SHORT_OVERSOLD')
                
            # MACD patterns
            if row['MACD_hist_turning']:
                confs.append('MACD_HIST_TURN')
            if row['MACD_bullish_cross']:
                confs.append('MACD_CROSS')
            if row['MACD_above_signal']:
                confs.append('MACD_ABOVE')
            if row['MACD_hist_accelerating']:
                confs.append('MACD_ACCEL')
            if row['MACD_hist_8_17'] > row['MACD_hist_8_17']:  # Fast MACD turning
                confs.append('FAST_MACD_TURN')
                
            # Bollinger patterns
            if row['BB_pos'] < 0.3:
                confs.append('BB_LOW')
            if row['BB_bounce_lower']:
                confs.append('BB_BOUNCE')
            if row['BB_squeeze']:
                confs.append('BB_SQUEEZE')
                
            # Volume patterns
            if row['Vol_spike']:
                confs.append('VOL_SPIKE')
            if row['Vol_increasing']:
                confs.append('VOL_UP')
                
            # Candle patterns
            if row['is_green']:
                confs.append('GREEN')
            if row['is_strong_green']:
                confs.append('STRONG_GREEN')
            if row['is_hammer']:
                confs.append('HAMMER')
            if row['is_bullish_engulfing']:
                confs.append('ENGULFING')
                
            # Trend patterns
            if row['trend_up']:
                confs.append('TREND_UP')
            if row['ema5_above_ema10']:
                confs.append('EMA_ALIGNED')
            if row['ema_golden_cross']:
                confs.append('EMA_CROSS')
            if row['price_above_ema5']:
                confs.append('ABOVE_EMA5')
            if row['price_above_sma20']:
                confs.append('ABOVE_SMA20')
                
            # Support patterns
            if row['above_recent_support']:
                confs.append('ABOVE_SUPPORT')
            if row['near_support']:
                confs.append('NEAR_SUPPORT')
            if row['consecutive_higher_lows'] >= 2:
                confs.append('HIGHER_LOWS')
                
            # Momentum
            if row['momentum_positive']:
                confs.append('MOM_POS')
            if row['momentum_accelerating']:
                confs.append('MOM_ACCEL')
            
            signal_data = {
                'symbol': symbol,
                'date': df.index[i],
                'rsi': rsi,
                'rsi_int': rsi_int,
                'confirmations': confs,
                'conf_count': len(confs),
                'return_1d': row['future_return_1d'] * 100,
                'return_2d': row['future_return_2d'] * 100,
                'return_3d': row['future_return_3d'] * 100,
                'return_5d': row['future_return_5d'] * 100,
                'max_1d': row['future_max_1d'] * 100,
                'max_3d': row['future_max_3d'] * 100,
                'min_1d': row['future_min_1d'] * 100,
                'entry_price': row['Close'],
                'atr_pct': row['ATR_pct']
            }
            
            all_signals.append(signal_data)
    
    df_signals = pd.DataFrame(all_signals)
    print(f"Total signals collected: {len(df_signals)}")
    
    return df_signals

def analyze_confirmation_combinations(df_signals):
    """Find the exact confirmation combinations with highest win rates"""
    print("\n📊 ANALYZING CONFIRMATION COMBINATIONS...")
    print("-" * 80)
    
    # Key confirmations to analyze
    key_confs = [
        'RSI_OVERSOLD', 'RSI_TURN', 'RSI_DOUBLE_BOTTOM', 'RSI_BOUNCE',
        'MACD_HIST_TURN', 'MACD_CROSS', 'MACD_ABOVE', 'MACD_ACCEL',
        'BB_LOW', 'BB_BOUNCE', 'BB_SQUEEZE',
        'VOL_SPIKE', 'VOL_UP',
        'GREEN', 'STRONG_GREEN', 'HAMMER', 'ENGULFING',
        'TREND_UP', 'EMA_ALIGNED', 'EMA_CROSS',
        'ABOVE_SUPPORT', 'NEAR_SUPPORT', 'HIGHER_LOWS',
        'MOM_POS', 'MOM_ACCEL'
    ]
    
    # Analyze each confirmation individually
    print("\n🎯 INDIVIDUAL CONFIRMATION WIN RATES:")
    conf_stats = []
    
    for conf in key_confs:
        mask = df_signals['confirmations'].apply(lambda x: conf in x)
        subset = df_signals[mask]
        if len(subset) < 20:
            continue
            
        wins_1d = (subset['return_1d'] > 0).sum()
        wins_2d = (subset['return_2d'] > 0).sum()
        wr_1d = wins_1d / len(subset) * 100
        wr_2d = wins_2d / len(subset) * 100
        avg_return = subset['return_1d'].mean()
        max_gain = subset['max_1d'].mean()
        
        conf_stats.append({
            'confirmation': conf,
            'count': len(subset),
            'wr_1d': wr_1d,
            'wr_2d': wr_2d,
            'avg_return': avg_return,
            'avg_max_gain': max_gain
        })
    
    conf_df = pd.DataFrame(conf_stats).sort_values('wr_1d', ascending=False)
    print(conf_df.head(15).to_string(index=False))
    
    return conf_df

def find_golden_patterns(df_signals):
    """Find the exact patterns that give 90%+ win rate"""
    print("\n🏆 SEARCHING FOR GOLDEN PATTERNS (90%+ WR)...")
    print("-" * 80)
    
    golden_patterns = []
    
    # Strategy 1: RSI + MACD Double Turn with Volume
    mask = df_signals['confirmations'].apply(
        lambda x: 'RSI_TURN' in x and 'MACD_HIST_TURN' in x and 'GREEN' in x
    )
    subset = df_signals[mask]
    if len(subset) >= 10:
        wr = (subset['return_1d'] > 0).sum() / len(subset) * 100
        golden_patterns.append({
            'pattern': 'RSI_TURN + MACD_HIST_TURN + GREEN',
            'trades': len(subset),
            'wr_1d': wr,
            'avg_return': subset['return_1d'].mean(),
            'avg_max': subset['max_1d'].mean()
        })
    
    # Strategy 2: Double Bottom RSI with Volume Spike
    mask = df_signals['confirmations'].apply(
        lambda x: 'RSI_DOUBLE_BOTTOM' in x and 'VOL_SPIKE' in x
    )
    subset = df_signals[mask]
    if len(subset) >= 5:
        wr = (subset['return_1d'] > 0).sum() / len(subset) * 100
        golden_patterns.append({
            'pattern': 'RSI_DOUBLE_BOTTOM + VOL_SPIKE',
            'trades': len(subset),
            'wr_1d': wr,
            'avg_return': subset['return_1d'].mean(),
            'avg_max': subset['max_1d'].mean()
        })
    
    # Strategy 3: BB Bounce with MACD Cross
    mask = df_signals['confirmations'].apply(
        lambda x: 'BB_BOUNCE' in x and 'MACD_CROSS' in x
    )
    subset = df_signals[mask]
    if len(subset) >= 5:
        wr = (subset['return_1d'] > 0).sum() / len(subset) * 100
        golden_patterns.append({
            'pattern': 'BB_BOUNCE + MACD_CROSS',
            'trades': len(subset),
            'wr_1d': wr,
            'avg_return': subset['return_1d'].mean(),
            'avg_max': subset['max_1d'].mean()
        })
    
    # Strategy 4: Hammer at Support with Volume
    mask = df_signals['confirmations'].apply(
        lambda x: 'HAMMER' in x and 'NEAR_SUPPORT' in x and 'VOL_UP' in x
    )
    subset = df_signals[mask]
    if len(subset) >= 5:
        wr = (subset['return_1d'] > 0).sum() / len(subset) * 100
        golden_patterns.append({
            'pattern': 'HAMMER + NEAR_SUPPORT + VOL_UP',
            'trades': len(subset),
            'wr_1d': wr,
            'avg_return': subset['return_1d'].mean(),
            'avg_max': subset['max_1d'].mean()
        })
    
    # Strategy 5: EMA Cross in Uptrend
    mask = df_signals['confirmations'].apply(
        lambda x: 'EMA_CROSS' in x and 'TREND_UP' in x and 'MOM_POS' in x
    )
    subset = df_signals[mask]
    if len(subset) >= 5:
        wr = (subset['return_1d'] > 0).sum() / len(subset) * 100
        golden_patterns.append({
            'pattern': 'EMA_CROSS + TREND_UP + MOM_POS',
            'trades': len(subset),
            'wr_1d': wr,
            'avg_return': subset['return_1d'].mean(),
            'avg_max': subset['max_1d'].mean()
        })
    
    # Strategy 6: Engulfing with MACD turn
    mask = df_signals['confirmations'].apply(
        lambda x: 'ENGULFING' in x and 'MACD_HIST_TURN' in x
    )
    subset = df_signals[mask]
    if len(subset) >= 5:
        wr = (subset['return_1d'] > 0).sum() / len(subset) * 100
        golden_patterns.append({
            'pattern': 'ENGULFING + MACD_HIST_TURN',
            'trades': len(subset),
            'wr_1d': wr,
            'avg_return': subset['return_1d'].mean(),
            'avg_max': subset['max_1d'].mean()
        })
    
    # Strategy 7: RSI Oversold Bounce with Higher Lows
    mask = df_signals['confirmations'].apply(
        lambda x: 'RSI_BOUNCE' in x and 'HIGHER_LOWS' in x and 'GREEN' in x
    )
    subset = df_signals[mask]
    if len(subset) >= 5:
        wr = (subset['return_1d'] > 0).sum() / len(subset) * 100
        golden_patterns.append({
            'pattern': 'RSI_BOUNCE + HIGHER_LOWS + GREEN',
            'trades': len(subset),
            'wr_1d': wr,
            'avg_return': subset['return_1d'].mean(),
            'avg_max': subset['max_1d'].mean()
        })
    
    # Strategy 8: BB Squeeze Breakout
    mask = df_signals['confirmations'].apply(
        lambda x: 'BB_SQUEEZE' in x and 'STRONG_GREEN' in x and 'VOL_SPIKE' in x
    )
    subset = df_signals[mask]
    if len(subset) >= 5:
        wr = (subset['return_1d'] > 0).sum() / len(subset) * 100
        golden_patterns.append({
            'pattern': 'BB_SQUEEZE + STRONG_GREEN + VOL_SPIKE',
            'trades': len(subset),
            'wr_1d': wr,
            'avg_return': subset['return_1d'].mean(),
            'avg_max': subset['max_1d'].mean()
        })
    
    # Analyze by RSI level + high confirmations
    print("\n📊 WIN RATE BY RSI LEVEL (6+ confirmations):")
    for rsi in range(20, 45):
        mask = (df_signals['rsi_int'] == rsi) & (df_signals['conf_count'] >= 6)
        subset = df_signals[mask]
        if len(subset) >= 5:
            wr = (subset['return_1d'] > 0).sum() / len(subset) * 100
            avg_ret = subset['return_1d'].mean()
            if wr >= 60:
                print(f"   RSI {rsi}: {len(subset):3d} trades, WR={wr:.1f}%, Avg={avg_ret:.2f}%")
    
    # Analyze by confirmation count
    print("\n📊 WIN RATE BY CONFIRMATION COUNT:")
    for conf_count in range(5, 15):
        mask = df_signals['conf_count'] >= conf_count
        subset = df_signals[mask]
        if len(subset) >= 10:
            wr = (subset['return_1d'] > 0).sum() / len(subset) * 100
            avg_ret = subset['return_1d'].mean()
            print(f"   {conf_count}+ confs: {len(subset):4d} trades, WR={wr:.1f}%, Avg={avg_ret:.2f}%")
    
    # Print golden patterns
    print("\n🏆 GOLDEN PATTERNS DISCOVERED:")
    gp_df = pd.DataFrame(golden_patterns).sort_values('wr_1d', ascending=False)
    if len(gp_df) > 0:
        print(gp_df.to_string(index=False))
    
    # Find ultra patterns (combining multiple conditions)
    print("\n💎 ULTRA PATTERNS (Multiple Golden Conditions):")
    
    # Ultra Pattern 1: Triple confirmation with trend
    mask = df_signals['confirmations'].apply(
        lambda x: ('RSI_TURN' in x or 'RSI_BOUNCE' in x) and 
                  'MACD_HIST_TURN' in x and 
                  'GREEN' in x and 
                  ('VOL_SPIKE' in x or 'VOL_UP' in x) and
                  ('TREND_UP' in x or 'EMA_ALIGNED' in x)
    )
    subset = df_signals[mask]
    if len(subset) >= 3:
        wr = (subset['return_1d'] > 0).sum() / len(subset) * 100
        wr_2d = (subset['return_2d'] > 0).sum() / len(subset) * 100
        avg_ret = subset['return_1d'].mean()
        max_gain = subset['max_1d'].mean()
        print(f"   ULTRA-1 (RSI+MACD+VOL+TREND): {len(subset)} trades, WR={wr:.1f}%, 2D-WR={wr_2d:.1f}%, Avg={avg_ret:.2f}%, MaxGain={max_gain:.2f}%")
    
    # Ultra Pattern 2: Extreme oversold reversal
    mask = df_signals['confirmations'].apply(
        lambda x: 'RSI_OVERSOLD' in x and 
                  'RSI_TURN' in x and 
                  'MACD_HIST_TURN' in x and 
                  'BB_LOW' in x and
                  'GREEN' in x
    ) & (df_signals['rsi'] < 30)
    subset = df_signals[mask]
    if len(subset) >= 3:
        wr = (subset['return_1d'] > 0).sum() / len(subset) * 100
        wr_2d = (subset['return_2d'] > 0).sum() / len(subset) * 100
        avg_ret = subset['return_1d'].mean()
        max_gain = subset['max_3d'].mean()
        print(f"   ULTRA-2 (EXTREME OVERSOLD): {len(subset)} trades, WR={wr:.1f}%, 2D-WR={wr_2d:.1f}%, Avg={avg_ret:.2f}%, MaxGain3D={max_gain:.2f}%")
    
    return gp_df

def calculate_returns_potential(df_signals):
    """Calculate potential monthly returns with different strategies"""
    print("\n💰 CALCULATING 300%+ MONTHLY RETURNS STRATEGY...")
    print("-" * 80)
    
    # For 300% monthly returns, we need:
    # Option 1: 15 trades x 20% each = 300%
    # Option 2: 30 trades x 10% each = 300%
    # Option 3: 60 trades x 5% each = 300%
    
    # With options leverage (typical 5-10x), we need:
    # 2-4% stock move = 10-40% option profit
    
    print("\n📈 RETURN SCENARIOS (22 trading days/month):")
    
    # Scenario 1: Conservative (5 trades/week, 90% WR, 3% avg win, 1% avg loss)
    trades_week = 5
    trades_month = trades_week * 4
    win_rate = 0.90
    avg_win = 3.0  # 3% per winning trade
    avg_loss = 1.0  # 1% per losing trade
    
    wins = trades_month * win_rate
    losses = trades_month * (1 - win_rate)
    monthly_return = (wins * avg_win) - (losses * avg_loss)
    
    print(f"\n   Scenario 1 - Conservative Options:")
    print(f"   • Trades/month: {trades_month}")
    print(f"   • Win rate: {win_rate*100:.0f}%")
    print(f"   • Avg win: {avg_win}% | Avg loss: {avg_loss}%")
    print(f"   • Monthly Return: {monthly_return:.1f}%")
    print(f"   • With 3x leverage: {monthly_return * 3:.1f}%")
    
    # Scenario 2: Aggressive (10 trades/week, 85% WR, 5% avg win, 2% avg loss)
    trades_week = 10
    trades_month = trades_week * 4
    win_rate = 0.85
    avg_win = 5.0
    avg_loss = 2.0
    
    wins = trades_month * win_rate
    losses = trades_month * (1 - win_rate)
    monthly_return = (wins * avg_win) - (losses * avg_loss)
    
    print(f"\n   Scenario 2 - Aggressive Options:")
    print(f"   • Trades/month: {trades_month}")
    print(f"   • Win rate: {win_rate*100:.0f}%")
    print(f"   • Avg win: {avg_win}% | Avg loss: {avg_loss}%")
    print(f"   • Monthly Return: {monthly_return:.1f}%")
    print(f"   • With 3x leverage: {monthly_return * 3:.1f}%")
    
    # Scenario 3: Ultra (15 trades/week, 80% WR, 8% avg win, 3% avg loss)
    trades_week = 15
    trades_month = trades_week * 4
    win_rate = 0.80
    avg_win = 8.0
    avg_loss = 3.0
    
    wins = trades_month * win_rate
    losses = trades_month * (1 - win_rate)
    monthly_return = (wins * avg_win) - (losses * avg_loss)
    
    print(f"\n   Scenario 3 - Ultra (ATM Options):")
    print(f"   • Trades/month: {trades_month}")
    print(f"   • Win rate: {win_rate*100:.0f}%")
    print(f"   • Avg win: {avg_win}% | Avg loss: {avg_loss}%")
    print(f"   • Monthly Return: {monthly_return:.1f}%")
    print(f"   • With 2x position sizing: {monthly_return * 2:.1f}%")

def main():
    """Main analysis function"""
    
    # Load data - 6 months for comprehensive analysis
    print("\n📥 Loading 6 months of market data...")
    all_data = {}
    
    for i, stock in enumerate(STOCKS):
        try:
            df = yf.download(stock, period="6mo", progress=False, auto_adjust=True)
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = [col[0] for col in df.columns]
            if len(df) > 50:
                df = calculate_advanced_indicators(df)
                df = analyze_pattern_performance(df)
                all_data[stock] = df
            print(f"   [{i+1}/{len(STOCKS)}] {stock}: {len(df)} days", end='\r')
        except Exception as e:
            pass
    
    print(f"\n   Loaded {len(all_data)} stocks successfully")
    
    # Find high win rate patterns
    df_signals = find_ultra_high_winrate_patterns(all_data)
    
    if len(df_signals) == 0:
        print("No signals found!")
        return
    
    # Analyze confirmation combinations
    conf_df = analyze_confirmation_combinations(df_signals)
    
    # Find golden patterns
    golden_df = find_golden_patterns(df_signals)
    
    # Calculate return potential
    calculate_returns_potential(df_signals)
    
    print("\n" + "=" * 80)
    print("🏆 ANALYSIS COMPLETE")
    print("=" * 80)

if __name__ == "__main__":
    main()
