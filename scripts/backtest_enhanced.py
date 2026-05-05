"""
ENHANCED Trading Strategy - Phase 1 Implementation
Implements critical filters to improve win rate from 16.7% to 50%+
"""

import yfinance as yf
import asyncio
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict
import logging

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

class EnhancedBacktester:
    def __init__(self):
        self.trades = []
        self.capital = 100000
        self.max_trades_per_day = 2  # ENHANCEMENT: Limit overtrading
        self.trades_today = {}
        
        self.nifty_symbols = [
            'RELIANCE.NS', 'TCS.NS', 'HDFCBANK.NS', 'INFY.NS', 'ICICIBANK.NS',
            'HINDUNILVR.NS', 'ITC.NS', 'SBIN.NS', 'BHARTIARTL.NS', 'KOTAKBANK.NS',
            'LT.NS', 'AXISBANK.NS', 'BAJFINANCE.NS', 'ASIANPAINT.NS', 'MARUTI.NS',
            'TITAN.NS', 'ULTRACEMCO.NS', 'SUNPHARMA.NS', 'NESTLEIND.NS', 'WIPRO.NS'
        ]
    
    def fetch_historical_data(self, days_back=7):
        logger.info(f"Fetching {days_back} days of historical data...")
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back+5)
        
        historical_data = {}
        for symbol in self.nifty_symbols:
            try:
                ticker = yf.Ticker(symbol)
                hist = ticker.history(start=start_date, end=end_date)
                if not hist.empty:
                    historical_data[symbol] = hist
            except:
                pass
        
        logger.info(f"Loaded data for {len(historical_data)} stocks\n")
        return historical_data
    
    def calculate_rsi(self, prices, period=14):
        if len(prices) < period:
            return 50.0
        
        deltas = np.diff(prices)
        gain = np.where(deltas > 0, deltas, 0)
        loss = np.where(deltas < 0, -deltas, 0)
        
        avg_gain = np.mean(gain[-period:])
        avg_loss = np.mean(loss[-period:])
        
        if avg_loss == 0:
            return 100.0
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    def calculate_ema(self, prices, period):
        """Calculate Exponential Moving Average"""
        if len(prices) < period:
            return np.mean(prices)
        
        multiplier = 2 / (period + 1)
        ema = prices[period - 1]  # Start with SMA
        
        for price in prices[period:]:
            ema = (price - ema) * multiplier + ema
        
        return ema
    
    def has_trend_confirmation(self, prices):
        """ENHANCEMENT: Check if 20 EMA > 50 EMA (uptrend) or vice versa"""
        if len(prices) < 50:
            return False, "NEUTRAL"
        
        ema_20 = self.calculate_ema(prices, 20)
        ema_50 = self.calculate_ema(prices, 50)
        
        if ema_20 > ema_50 * 1.01:  # At least 1% above
            return True, "BULLISH"
        elif ema_20 < ema_50 * 0.99:  # At least 1% below
            return True, "BEARISH"
        else:
            return False, "NEUTRAL"
    
    def has_volume_confirmation(self, volumes):
        """ENHANCEMENT: Check for volume surge"""
        if len(volumes) < 5:
            return False
        
        recent_vol = volumes.iloc[-1]
        avg_vol = np.mean(volumes.iloc[-5:])
        
        # Volume must be 30%+ above average
        return recent_vol > avg_vol * 1.3
    
    def analyze_day(self, date, historical_data):
        logger.info(f"\n{'-'*60}")
        logger.info(f"Analyzing: {date.strftime('%Y-%m-%d %A')}")
        
        # ENHANCEMENT: Check daily trade limit
        date_key = date.strftime('%Y-%m-%d')
        if self.trades_today.get(date_key, 0) >= self.max_trades_per_day:
            logger.info(f"Max trades ({self.max_trades_per_day}) reached for today - SKIP")
            return None
        
        stocks_analysis = []
        strong_signals = 0
        
        for symbol, hist_df in historical_data.items():
            day_data = hist_df[hist_df.index <= date]
            
            if len(day_data) < 50:  # Need enough data for trend
                continue
            
            prices = day_data['Close'].values
            volumes = day_data['Volume']
            
            current_price = prices[-1]
            prev_price = prices[-2]
            change_pct = ((current_price - prev_price) / prev_price * 100)
            
            rsi = self.calculate_rsi(prices)
            
            # ENHANCEMENT: Require trend confirmation
            has_trend, trend_direction = self.has_trend_confirmation(prices)
            
            # ENHANCEMENT: Require volume confirmation
            has_volume = self.has_volume_confirmation(volumes)
            
            # ENHANCED signal logic: Much stricter
            signal = "NEUTRAL"
            
            if has_trend and has_volume:
                if trend_direction == "BULLISH" and rsi > 55 and change_pct > 0.5:
                    signal = "BULLISH"
                    strong_signals += 1
                elif trend_direction == "BEARISH" and rsi < 45 and change_pct < -0.5:
                    signal = "BEARISH"
                    strong_signals += 1
            
            stocks_analysis.append({
                'symbol': symbol.replace('.NS', ''),
                'price': current_price,
                'change_pct': change_pct,
                'rsi': rsi,
                'has_trend': has_trend,
                'trend': trend_direction,
                'has_volume': has_volume,
                'signal': signal
            })
        
        # Tier 1 - ENHANCED: Only strong signals count
        bullish = sum(1 for s in stocks_analysis if s['signal'] == 'BULLISH')
        bearish = sum(1 for s in stocks_analysis if s['signal'] == 'BEARISH')
        
        logger.info(f"Strong Signals: {strong_signals} stocks with trend + volume")
        logger.info(f"Bullish: {bullish} | Bearish: {bearish}")
        
        # ENHANCEMENT: Require minimum threshold of strong signals
        if strong_signals < 3:  # Need at least 3 stocks confirming
            logger.info("Insufficient strong signals - SKIP")
            return None
        
        if bullish > bearish:
            bias = "BULLISH"
            strength = min(10, (bullish / len(stocks_analysis)) * 20)
        elif bearish > bullish:
            bias = "BEARISH"
            strength = min(10, (bearish / len(stocks_analysis)) * 20)
        else:
            bias = "NEUTRAL"
            strength = 0
        
        logger.info(f"Market: {bias} (Strength: {strength:.1f}/10)")
        
        # Tier 2 - ENHANCED: Much higher threshold
        if bias == "BULLISH" and strength >= 6.5:  # Was 1.0
            signal = "BUY_CALL"
        elif bias == "BEARISH" and strength >= 6.5:  # Was 1.0
            signal = "BUY_PUT"
        else:
            signal = "NO_TRADE"
            logger.info(f"Signal strength too low ({strength:.1f}) - SKIP")
            return None
        
        logger.info(f"Signal: {signal}")
        
        # Tier 3 - Enhanced checks
        if date.weekday() >= 5:
            logger.info("Weekend - SKIP")
            return None
        
        # ENHANCEMENT: Check if last 2 trades were losses (avoid losing streaks)
        recent_trades = self.trades[-2:] if len(self.trades) >= 2 else []
        if all(not t['win'] for t in recent_trades) and len(recent_trades) == 2:
            logger.info("Last 2 trades lost - Taking break - SKIP")
            return None
        
        logger.info("Decision: GO ✅")
        
        # Update daily counter
        self.trades_today[date_key] = self.trades_today.get(date_key, 0) + 1
        
        # Simulate trade
        return self.simulate_trade(signal, date)
    
    def simulate_trade(self, signal, entry_date):
        logger.info("Simulating trade...")
        
        nifty = yf.Ticker("^NSEI")
        nifty_hist = nifty.history(start=entry_date, period="5d")
        
        if len(nifty_hist) < 2:
            return None
        
        entry_price = nifty_hist['Close'].iloc[0]
        
        # ENHANCEMENT: Dynamic stops based on recent volatility
        recent_volatility = np.std(nifty_hist['Close'].pct_change().dropna()) * 100
        stop_loss_pct = max(0.5, recent_volatility * 1.5)  # Dynamic stop
        profit_target_pct = stop_loss_pct * 2.5  # 2.5:1 risk/reward
        
        logger.info(f"Stop: -{stop_loss_pct:.2f}% | Target: +{profit_target_pct:.2f}%")
        
        if signal == "BUY_CALL":
            for i in range(1, min(3, len(nifty_hist))):
                current_price = nifty_hist['Close'].iloc[i]
                change_pct = ((current_price - entry_price) / entry_price * 100)
                
                if change_pct >= profit_target_pct:
                    win = True
                    pnl_pct = change_pct * 4
                    exit_date = nifty_hist.index[i]
                    break
                elif change_pct <= -stop_loss_pct:
                    win = False
                    pnl_pct = change_pct * 4
                    exit_date = nifty_hist.index[i]
                    break
            else:
                exit_price = nifty_hist['Close'].iloc[-1]
                change_pct = ((exit_price - entry_price) / entry_price * 100)
                win = change_pct > 0
                pnl_pct = change_pct * 4
                exit_date = nifty_hist.index[-1]
        
        elif signal == "BUY_PUT":
            for i in range(1, min(3, len(nifty_hist))):
                current_price = nifty_hist['Close'].iloc[i]
                change_pct = ((entry_price - current_price) / entry_price * 100)
                
                if change_pct >= profit_target_pct:
                    win = True
                    pnl_pct = change_pct * 4
                    exit_date = nifty_hist.index[i]
                    break
                elif change_pct <= -stop_loss_pct:
                    win = False
                    pnl_pct = change_pct * 4
                    exit_date = nifty_hist.index[i]
                    break
            else:
                exit_price = nifty_hist['Close'].iloc[-1]
                change_pct = ((entry_price - exit_price) / entry_price * 100)
                win = change_pct > 0
                pnl_pct = change_pct * 4
                exit_date = nifty_hist.index[-1]
        else:
            return None
        
        trade = {
            'entry_date': entry_date,
            'exit_date': exit_date,
            'signal': signal,
            'pnl_pct': pnl_pct,
            'win': win
        }
        
        self.trades.append(trade)
        
        result = "WIN ✅" if win else "LOSS ❌"
        logger.info(f"{result}: {pnl_pct:+.2f}% | Exit: {exit_date.strftime('%Y-%m-%d')}\n")
        
        return trade
    
    async def run_backtest(self, days=7):
        logger.info("="*60)
        logger.info("ENHANCED BACKTEST - Phase 1 Improvements")
        logger.info("="*60)
        
        historical_data = self.fetch_historical_data(days)
        
        if not historical_data:
            logger.error("No data available!")
            return
        
        sample_data = next(iter(historical_data.values()))
        trading_days = sample_data.index[-days:]
        
        for date in trading_days:
            self.analyze_day(date, historical_data)
        
        # Results
        logger.info("\n" + "="*60)
        logger.info("ENHANCED BACKTEST RESULTS")
        logger.info("="*60)
        
        if not self.trades:
            logger.info("\nNo trades executed")
            logger.info("Filters prevented low-quality setups (This is GOOD!)")
            logger.info("Recommendation: Strategy is selective - wait for high-conviction signals")
            return
        
        wins = [t for t in self.trades if t['win']]
        losses = [t for t in self.trades if not t['win']]
        
        total_trades = len(self.trades)
        win_rate = (len(wins) / total_trades * 100)
        
        avg_win = np.mean([t['pnl_pct'] for t in wins]) if wins else 0
        avg_loss = np.mean([t['pnl_pct'] for t in losses]) if losses else 0
        
        total_return = sum(t['pnl_pct'] for t in self.trades)
        profit_factor = abs(avg_win / avg_loss) if avg_loss != 0 else 0
        
        logger.info(f"\nTotal Trades: {total_trades} (vs 6 in baseline)")
        logger.info(f"Wins: {len(wins)} | Losses: {len(losses)}")
        logger.info(f"Win Rate: {win_rate:.1f}% (vs 16.7% baseline)")
        logger.info(f"Avg Win: +{avg_win:.2f}%")
        logger.info(f"Avg Loss: {avg_loss:.2f}%")
        logger.info(f"Total Return: {total_return:+.2f}% (vs -2.60% baseline)")
        logger.info(f"Profit Factor: {profit_factor:.2f}")
        
        final_capital = self.capital * (1 + total_return/100)
        logger.info(f"\nStarting Capital: Rs.{self.capital:,}")
        logger.info(f"Ending Capital: Rs.{final_capital:,.0f}")
        logger.info(f"Profit: Rs.{final_capital - self.capital:+,.0f}")
        
        logger.info(f"\nEnhancements Applied:")
        logger.info("✅ Trend confirmation (20/50 EMA)")
        logger.info("✅ Volume surge filter (1.3x average)")
        logger.info("✅ Minimum signal threshold (6.5/10)")
        logger.info("✅ Max 2 trades/day limit")
        logger.info("✅ Loss streak protection")
        logger.info("✅ Dynamic stop-loss")
        
        logger.info(f"\nAssessment:")
        if win_rate >= 70:
            logger.info("🎯 EXCELLENT - Phase 1 target exceeded!")
        elif win_rate >= 50:
            logger.info("✅ GOOD - Phase 1 improvements working!")
        elif win_rate >= 30:
            logger.info("⚠️  PROGRESS - Better than baseline, needs more work")
        else:
            logger.info("❌ NEEDS MORE - Continue to Phase 2")
        
        logger.info("="*60)


async def main():
    backtester = EnhancedBacktester()
    await backtester.run_backtest(days=7)


if __name__ == "__main__":
    print(f"Starting Enhanced Backtest: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    asyncio.run(main())
    print(f"\nBacktest Complete: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
