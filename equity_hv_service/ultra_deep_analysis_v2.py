"""
🔬 ULTRA DEEP MARKET ANALYSIS v2 - CRACKING INDIAN MARKET PATTERNS
===================================================================
Goal: Find patterns that deliver 90%+ Win Rate and 300%+ Monthly Returns
"""

import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta
from collections import defaultdict
import warnings
warnings.filterwarnings('ignore')

print("=" * 80)
print("🔬 ULTRA DEEP MARKET ANALYSIS v2 - CRACKING INDIAN MARKET")
print("=" * 80)
print(f"Analysis Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
print("Goal: 90%+ Win Rate | 300%+ Monthly Returns")
print("=" * 80)

# Extended stock universe
STOCKS = [
    "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "ICICIBANK.NS",
    "HINDUNILVR.NS", "SBIN.NS", "BHARTIARTL.NS", "KOTAKBANK.NS", "ITC.NS",
    "LT.NS", "AXISBANK.NS", "ASIANPAINT.NS", "MARUTI.NS", "TITAN.NS",
    "SUNPHARMA.NS", "BAJFINANCE.NS", "WIPRO.NS", "ULTRACEMCO.NS", "ONGC.NS",
    "NTPC.NS", "POWERGRID.NS", "HCLTECH.NS", "TATAMOTORS.NS", "JSWSTEEL.NS",
    "TATASTEEL.NS", "TECHM.NS", "DRREDDY.NS", "BAJAJFINSV.NS", "CIPLA.NS"
]

def load_stock_data(symbol, period="6mo"):
    """Load and clean stock data"""
    try:
        df = yf.download(symbol, period=period, progress=False)
        
        # Handle MultiIndex columns
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = [col[0] for col in df.columns]
        
        # Ensure we have required columns
        required = ['Open', 'High', 'Low', 'Close', 'Volume']
        for col in required:
            if col not in df.columns:
                return None
        
        return df
    except Exception as e:
        return None

def calculate_indicators(df):
    """Calculate all technical indicators"""
    if len(df) < 50:
        return df
    
    # RSI
    delta = df['Close'].diff()
    gain = delta.where(delta > 0, 0)
    loss = (-delta).where(delta < 0, 0)
    avg_gain = gain.rolling(14).mean()
    avg_loss = loss.rolling(14).mean()
    rs = avg_gain / (avg_loss + 1e-10)
    df['RSI'] = 100 - (100 / (1 + rs))
    df['RSI_prev'] = df['RSI'].shift(1)
    df['RSI_prev2'] = df['RSI'].shift(2)
    df['RSI_prev3'] = df['RSI'].shift(3)
    
    # RSI patterns
    df['RSI_turning_up'] = (df['RSI'] > df['RSI_prev']) & (df['RSI_prev'] <= df['RSI_prev2'])
    df['RSI_double_bottom'] = (df['RSI'] > df['RSI_prev']) & (df['RSI_prev'] < df['RSI_prev2']) & (df['RSI_prev2'] < df['RSI_prev3'])
    df['RSI_oversold_bounce'] = (df['RSI'] > 30) & (df['RSI_prev'] < 30)
    
    # MACD
    exp12 = df['Close'].ewm(span=12, adjust=False).mean()
    exp26 = df['Close'].ewm(span=26, adjust=False).mean()
    df['MACD'] = exp12 - exp26
    df['MACD_signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
    df['MACD_hist'] = df['MACD'] - df['MACD_signal']
    df['MACD_hist_prev'] = df['MACD_hist'].shift(1)
    df['MACD_hist_prev2'] = df['MACD_hist'].shift(2)
    
    df['MACD_hist_turning'] = (df['MACD_hist'] > df['MACD_hist_prev']) & (df['MACD_hist_prev'] <= df['MACD_hist_prev2'])
    df['MACD_bullish_cross'] = (df['MACD'] > df['MACD_signal']) & (df['MACD'].shift(1) <= df['MACD_signal'].shift(1))
    df['MACD_above_signal'] = df['MACD'] > df['MACD_signal']
    df['MACD_hist_accelerating'] = df['MACD_hist'] > df['MACD_hist_prev']
    
    # Bollinger Bands
    df['BB_mid'] = df['Close'].rolling(20).mean()
    df['BB_std'] = df['Close'].rolling(20).std()
    df['BB_upper'] = df['BB_mid'] + 2 * df['BB_std']
    df['BB_lower'] = df['BB_mid'] - 2 * df['BB_std']
    df['BB_pos'] = (df['Close'] - df['BB_lower']) / (df['BB_upper'] - df['BB_lower'] + 1e-10)
    df['BB_squeeze'] = df['BB_std'] / df['BB_mid'] < 0.02
    df['BB_touch_lower'] = df['Low'] <= df['BB_lower']
    
    # Volume
    df['Vol_MA'] = df['Volume'].rolling(20).mean()
    df['Vol_ratio'] = df['Volume'] / (df['Vol_MA'] + 1)
    df['Vol_spike'] = df['Vol_ratio'] > 1.5
    df['Vol_increasing'] = df['Volume'] > df['Volume'].shift(1)
    
    # Price action
    df['body'] = df['Close'] - df['Open']
    df['body_pct'] = abs(df['body']) / df['Open'] * 100
    df['is_green'] = df['Close'] > df['Open']
    df['is_strong_green'] = df['is_green'] & (df['body_pct'] > 0.5)
    
    # Hammer pattern
    df['lower_wick'] = df[['Open', 'Close']].min(axis=1) - df['Low']
    df['is_hammer'] = (df['lower_wick'] > 2 * abs(df['body'])) & (abs(df['body']) > 0)
    
    # Moving averages
    df['EMA_5'] = df['Close'].ewm(span=5, adjust=False).mean()
    df['EMA_10'] = df['Close'].ewm(span=10, adjust=False).mean()
    df['SMA_20'] = df['Close'].rolling(20).mean()
    df['SMA_50'] = df['Close'].rolling(50).mean()
    
    df['price_above_ema5'] = df['Close'] > df['EMA_5']
    df['ema5_above_ema10'] = df['EMA_5'] > df['EMA_10']
    df['trend_up'] = df['SMA_20'] > df['SMA_50']
    df['ema_cross'] = (df['EMA_5'] > df['EMA_10']) & (df['EMA_5'].shift(1) <= df['EMA_10'].shift(1))
    
    # Support
    df['recent_low_5'] = df['Low'].rolling(5).min()
    df['above_support'] = df['Close'] > df['recent_low_5']
    df['near_support'] = (df['Close'] - df['recent_low_5']) / df['Close'] < 0.02
    df['higher_lows'] = df['Low'] > df['Low'].shift(1)
    
    # Momentum
    df['momentum'] = df['Close'].pct_change()
    df['momentum_positive'] = df['momentum'] > 0
    
    # Future returns for backtesting
    df['return_1d'] = df['Close'].shift(-1) / df['Close'] - 1
    df['return_2d'] = df['Close'].shift(-2) / df['Close'] - 1
    df['return_3d'] = df['Close'].shift(-3) / df['Close'] - 1
    df['return_5d'] = df['Close'].shift(-5) / df['Close'] - 1
    
    # Max gain in next N days
    df['max_1d'] = df['High'].shift(-1) / df['Close'] - 1
    df['max_2d'] = df['High'].rolling(2).max().shift(-2) / df['Close'] - 1
    df['max_3d'] = df['High'].rolling(3).max().shift(-3) / df['Close'] - 1
    
    return df

def get_confirmations(row):
    """Count all confirmations for a row"""
    confs = []
    
    # RSI patterns
    if row['RSI'] < 35:
        confs.append('RSI_OVERSOLD')
    if row['RSI'] < 30:
        confs.append('RSI_EXTREME')
    if row['RSI_turning_up']:
        confs.append('RSI_TURN')
    if row['RSI_double_bottom']:
        confs.append('RSI_DOUBLE')
    if row['RSI_oversold_bounce']:
        confs.append('RSI_BOUNCE')
    
    # MACD patterns
    if row['MACD_hist_turning']:
        confs.append('MACD_HIST_TURN')
    if row['MACD_bullish_cross']:
        confs.append('MACD_CROSS')
    if row['MACD_above_signal']:
        confs.append('MACD_ABOVE')
    if row['MACD_hist_accelerating']:
        confs.append('MACD_ACCEL')
    
    # BB patterns
    if row['BB_pos'] < 0.3:
        confs.append('BB_LOW')
    if row['BB_pos'] < 0.1:
        confs.append('BB_EXTREME')
    if row['BB_squeeze']:
        confs.append('BB_SQUEEZE')
    
    # Volume
    if row['Vol_spike']:
        confs.append('VOL_SPIKE')
    if row['Vol_increasing']:
        confs.append('VOL_UP')
    
    # Candle
    if row['is_green']:
        confs.append('GREEN')
    if row['is_strong_green']:
        confs.append('STRONG_GREEN')
    if row['is_hammer']:
        confs.append('HAMMER')
    
    # Trend
    if row['trend_up']:
        confs.append('TREND_UP')
    if row['ema5_above_ema10']:
        confs.append('EMA_ALIGNED')
    if row['ema_cross']:
        confs.append('EMA_CROSS')
    if row['price_above_ema5']:
        confs.append('ABOVE_EMA')
    
    # Support/Momentum
    if row['above_support']:
        confs.append('ABOVE_SUPPORT')
    if row['near_support']:
        confs.append('NEAR_SUPPORT')
    if row['higher_lows']:
        confs.append('HIGHER_LOW')
    if row['momentum_positive']:
        confs.append('MOM_POS')
    
    return confs

def main():
    print("\n📥 Loading 6 months of market data...")
    
    all_signals = []
    loaded = 0
    
    for i, symbol in enumerate(STOCKS):
        df = load_stock_data(symbol, "6mo")
        if df is None or len(df) < 50:
            continue
        
        df = calculate_indicators(df)
        loaded += 1
        
        # Collect all potential signals
        for idx in range(50, len(df) - 5):
            row = df.iloc[idx]
            
            if pd.isna(row.get('return_1d')):
                continue
            
            rsi = row['RSI']
            if pd.isna(rsi) or rsi > 50:  # Only oversold conditions
                continue
            
            confs = get_confirmations(row)
            
            if len(confs) >= 3:  # At least 3 confirmations
                all_signals.append({
                    'symbol': symbol,
                    'date': df.index[idx],
                    'rsi': rsi,
                    'rsi_int': int(round(rsi)),
                    'confs': confs,
                    'conf_count': len(confs),
                    'return_1d': row['return_1d'] * 100,
                    'return_2d': row['return_2d'] * 100,
                    'return_3d': row['return_3d'] * 100,
                    'max_1d': row['max_1d'] * 100,
                    'max_3d': row['max_3d'] * 100,
                    'close': row['Close']
                })
        
        print(f"   [{i+1}/{len(STOCKS)}] {symbol}: {len(df)} days", end='\r')
    
    print(f"\n   Loaded {loaded} stocks, {len(all_signals)} signals")
    
    if len(all_signals) == 0:
        print("No signals found!")
        return
    
    df_signals = pd.DataFrame(all_signals)
    
    # ========================================
    # ANALYSIS BY RSI LEVEL
    # ========================================
    print("\n" + "=" * 80)
    print("📊 WIN RATE BY RSI LEVEL")
    print("=" * 80)
    
    for rsi in range(20, 46):
        mask = df_signals['rsi_int'] == rsi
        subset = df_signals[mask]
        if len(subset) >= 5:
            wr_1d = (subset['return_1d'] > 0).sum() / len(subset) * 100
            wr_2d = (subset['return_2d'] > 0).sum() / len(subset) * 100
            avg_ret = subset['return_1d'].mean()
            avg_max = subset['max_1d'].mean()
            flag = "🏆" if wr_1d >= 70 else ("⭐" if wr_1d >= 60 else "")
            print(f"   RSI {rsi:2d}: {len(subset):4d} trades | WR-1D={wr_1d:5.1f}% | WR-2D={wr_2d:5.1f}% | AvgRet={avg_ret:+.2f}% | MaxGain={avg_max:.2f}% {flag}")
    
    # ========================================
    # ANALYSIS BY CONFIRMATION COUNT
    # ========================================
    print("\n" + "=" * 80)
    print("📊 WIN RATE BY CONFIRMATION COUNT")
    print("=" * 80)
    
    for conf_count in range(3, 15):
        mask = df_signals['conf_count'] >= conf_count
        subset = df_signals[mask]
        if len(subset) >= 10:
            wr_1d = (subset['return_1d'] > 0).sum() / len(subset) * 100
            wr_2d = (subset['return_2d'] > 0).sum() / len(subset) * 100
            avg_ret = subset['return_1d'].mean()
            avg_max = subset['max_3d'].mean()
            flag = "🏆" if wr_1d >= 70 else ("⭐" if wr_1d >= 60 else "")
            print(f"   {conf_count:2d}+ confirmations: {len(subset):4d} trades | WR-1D={wr_1d:5.1f}% | WR-2D={wr_2d:5.1f}% | AvgRet={avg_ret:+.2f}% {flag}")
    
    # ========================================
    # INDIVIDUAL CONFIRMATION ANALYSIS
    # ========================================
    print("\n" + "=" * 80)
    print("📊 TOP PERFORMING INDIVIDUAL CONFIRMATIONS")
    print("=" * 80)
    
    all_confs = set()
    for c in df_signals['confs']:
        all_confs.update(c)
    
    conf_stats = []
    for conf in all_confs:
        mask = df_signals['confs'].apply(lambda x: conf in x)
        subset = df_signals[mask]
        if len(subset) >= 20:
            wr_1d = (subset['return_1d'] > 0).sum() / len(subset) * 100
            avg_ret = subset['return_1d'].mean()
            conf_stats.append({
                'conf': conf,
                'count': len(subset),
                'wr_1d': wr_1d,
                'avg_ret': avg_ret
            })
    
    conf_df = pd.DataFrame(conf_stats).sort_values('wr_1d', ascending=False)
    print(conf_df.head(15).to_string(index=False))
    
    # ========================================
    # GOLDEN PATTERNS
    # ========================================
    print("\n" + "=" * 80)
    print("🏆 GOLDEN PATTERNS (HIGH WIN RATE)")
    print("=" * 80)
    
    patterns = [
        ('RSI_TURN + MACD_HIST_TURN + GREEN', lambda x: 'RSI_TURN' in x and 'MACD_HIST_TURN' in x and 'GREEN' in x),
        ('RSI_TURN + MACD_HIST_TURN + VOL_SPIKE', lambda x: 'RSI_TURN' in x and 'MACD_HIST_TURN' in x and 'VOL_SPIKE' in x),
        ('RSI_EXTREME + GREEN + VOL_UP', lambda x: 'RSI_EXTREME' in x and 'GREEN' in x and 'VOL_UP' in x),
        ('RSI_BOUNCE + TREND_UP + GREEN', lambda x: 'RSI_BOUNCE' in x and 'TREND_UP' in x and 'GREEN' in x),
        ('MACD_CROSS + TREND_UP + GREEN', lambda x: 'MACD_CROSS' in x and 'TREND_UP' in x and 'GREEN' in x),
        ('BB_LOW + MACD_HIST_TURN + GREEN', lambda x: 'BB_LOW' in x and 'MACD_HIST_TURN' in x and 'GREEN' in x),
        ('HAMMER + VOL_SPIKE + RSI_OVERSOLD', lambda x: 'HAMMER' in x and 'VOL_SPIKE' in x and 'RSI_OVERSOLD' in x),
        ('EMA_CROSS + TREND_UP + VOL_UP', lambda x: 'EMA_CROSS' in x and 'TREND_UP' in x and 'VOL_UP' in x),
        ('RSI_DOUBLE + MACD_ACCEL + GREEN', lambda x: 'RSI_DOUBLE' in x and 'MACD_ACCEL' in x and 'GREEN' in x),
        ('BB_EXTREME + RSI_TURN + GREEN', lambda x: 'BB_EXTREME' in x and 'RSI_TURN' in x and 'GREEN' in x),
    ]
    
    for name, filter_fn in patterns:
        mask = df_signals['confs'].apply(filter_fn)
        subset = df_signals[mask]
        if len(subset) >= 3:
            wr_1d = (subset['return_1d'] > 0).sum() / len(subset) * 100
            wr_2d = (subset['return_2d'] > 0).sum() / len(subset) * 100
            avg_ret = subset['return_1d'].mean()
            avg_max = subset['max_1d'].mean()
            flag = "🏆🏆🏆" if wr_1d >= 90 else ("🏆🏆" if wr_1d >= 80 else ("🏆" if wr_1d >= 70 else ""))
            print(f"   {name}")
            print(f"      Trades: {len(subset):3d} | WR-1D: {wr_1d:.1f}% | WR-2D: {wr_2d:.1f}% | Avg: {avg_ret:+.2f}% | MaxGain: {avg_max:.2f}% {flag}")
    
    # ========================================
    # ULTRA PATTERNS - COMBINING BEST
    # ========================================
    print("\n" + "=" * 80)
    print("💎 ULTRA PATTERNS (MAXIMUM EDGE)")
    print("=" * 80)
    
    # Ultra 1: Low RSI + Multiple turns + Volume
    mask = (df_signals['rsi'] < 32) & df_signals['confs'].apply(
        lambda x: 'RSI_TURN' in x and 'MACD_HIST_TURN' in x and 'GREEN' in x and ('VOL_SPIKE' in x or 'VOL_UP' in x)
    )
    subset = df_signals[mask]
    if len(subset) >= 3:
        wr = (subset['return_1d'] > 0).sum() / len(subset) * 100
        wr2 = (subset['return_2d'] > 0).sum() / len(subset) * 100
        print(f"   ULTRA-1: RSI<32 + RSI_TURN + MACD_TURN + GREEN + VOLUME")
        print(f"            {len(subset)} trades | WR-1D: {wr:.1f}% | WR-2D: {wr2:.1f}% | Avg: {subset['return_1d'].mean():.2f}%")
    
    # Ultra 2: RSI extreme with trend support
    mask = (df_signals['rsi'] < 28) & df_signals['confs'].apply(
        lambda x: 'GREEN' in x and 'TREND_UP' in x
    )
    subset = df_signals[mask]
    if len(subset) >= 3:
        wr = (subset['return_1d'] > 0).sum() / len(subset) * 100
        wr2 = (subset['return_2d'] > 0).sum() / len(subset) * 100
        print(f"   ULTRA-2: RSI<28 + GREEN + TREND_UP")
        print(f"            {len(subset)} trades | WR-1D: {wr:.1f}% | WR-2D: {wr2:.1f}% | Avg: {subset['return_1d'].mean():.2f}%")
    
    # Ultra 3: High confirmation count with trend
    mask = (df_signals['conf_count'] >= 10) & df_signals['confs'].apply(
        lambda x: 'TREND_UP' in x
    )
    subset = df_signals[mask]
    if len(subset) >= 3:
        wr = (subset['return_1d'] > 0).sum() / len(subset) * 100
        wr2 = (subset['return_2d'] > 0).sum() / len(subset) * 100
        print(f"   ULTRA-3: 10+ Confirmations + TREND_UP")
        print(f"            {len(subset)} trades | WR-1D: {wr:.1f}% | WR-2D: {wr2:.1f}% | Avg: {subset['return_1d'].mean():.2f}%")
    
    # ========================================
    # 300% RETURNS CALCULATION
    # ========================================
    print("\n" + "=" * 80)
    print("💰 300%+ MONTHLY RETURNS STRATEGY")
    print("=" * 80)
    
    # Find the best performing pattern
    best_wr = 0
    best_pattern = None
    best_subset = None
    
    for name, filter_fn in patterns:
        mask = df_signals['confs'].apply(filter_fn)
        subset = df_signals[mask]
        if len(subset) >= 5:
            wr = (subset['return_1d'] > 0).sum() / len(subset) * 100
            if wr > best_wr:
                best_wr = wr
                best_pattern = name
                best_subset = subset
    
    if best_subset is not None:
        avg_win = best_subset[best_subset['return_1d'] > 0]['return_1d'].mean()
        avg_loss = abs(best_subset[best_subset['return_1d'] <= 0]['return_1d'].mean()) if len(best_subset[best_subset['return_1d'] <= 0]) > 0 else 1
        
        print(f"\n   Best Pattern: {best_pattern}")
        print(f"   Win Rate: {best_wr:.1f}%")
        print(f"   Avg Win: {avg_win:.2f}%")
        print(f"   Avg Loss: {avg_loss:.2f}%")
        
        # Calculate with options leverage
        print("\n   📈 WITH OPTIONS (3-5x leverage):")
        for leverage in [3, 4, 5]:
            option_win = avg_win * leverage
            option_loss = avg_loss * leverage
            
            # Monthly trades estimate
            trades_per_month = 20  # ~1 per day
            
            wins = trades_per_month * (best_wr / 100)
            losses = trades_per_month * (1 - best_wr / 100)
            
            monthly_return = (wins * option_win) - (losses * option_loss)
            
            print(f"      {leverage}x Leverage: {monthly_return:.1f}% monthly ({monthly_return * 12:.0f}% annual)")
    
    print("\n" + "=" * 80)
    print("✅ ANALYSIS COMPLETE")
    print("=" * 80)

if __name__ == "__main__":
    main()
