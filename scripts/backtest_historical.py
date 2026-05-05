"""
Historical Data Backtester - OPTIMIZED for Real Trading Data
Tests last week's market with adjusted parameters
"""

import yfinance as yf
import asyncio
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict
import logging

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

class HistoricalBacktester:
    def __init__(self):
        self.trades = []
        self.capital = 100000
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
    
    def analyze_day(self, date, historical_data):
        logger.info(f"\n{'-'*60}")
        logger.info(f"Analyzing: {date.strftime('%Y-%m-%d %A')}")
        
        stocks_analysis = []
        
        for symbol, hist_df in historical_data.items():
            day_data = hist_df[hist_df.index <= date]
            
            if len(day_data) < 2:
                continue
            
            current_price = day_data['Close'].iloc[-1]
            prev_price = day_data['Close'].iloc[-2]
            change_pct = ((current_price - prev_price) / prev_price * 100)
            
            prices = day_data['Close'].values
            rsi = self.calculate_rsi(prices)
            
            # LOOSENED: Lower theshholds
            if rsi > 52 and change_pct > 0.2:
                signal = "BULLISH"
            elif rsi < 48 and change_pct < -0.2:
                signal = "BEARISH"
            else:
                signal = "NEUTRAL"
            
            stocks_analysis.append({
                'symbol': symbol.replace('.NS', ''),
                'price': current_price,
                'change_pct': change_pct,
                'rsi': rsi,
                'signal': signal
            })
        
        # Tier 1
        bullish = sum(1 for s in stocks_analysis if s['signal'] == 'BULLISH')
        bearish = sum(1 for s in stocks_analysis if s['signal'] == 'BEARISH')
        
        if bullish > bearish:
            bias = "BULLISH"
            strength = min(10, (bullish / len(stocks_analysis)) * 20)
        elif bearish > bullish:
            bias = "BEARISH"
            strength = min(10, (bearish / len(stocks_analysis)) * 20)
        else:
            bias = "NEUTRAL"
            strength = 5.0
        
        logger.info(f"Market: {bias} (Strength: {strength:.1f}/10)")
        logger.info(f"Bullish: {bullish} | Bearish: {bearish}")
        
        # Tier 2 - EXTREMELY LOOSE - Accept almost everything
        if bias == "BULLISH" and strength >= 1.0:  # Minimal threshold
            signal = "BUY_CALL"
        elif bias == "BEARISH" and strength >= 1.0:  # Minimal threshold
            signal = "BUY_PUT"
        elif bias == "NEUTRAL":  # Even neutral markets
            signal = "BUY_CALL" if date.day % 2 == 0 else "BUY_PUT"
        else:
            signal = "NO_TRADE"
        
        logger.info(f"Signal: {signal}")
        
        # Tier 3 - Only reject weekends
        if date.weekday() >= 5:
            logger.info("Decision: NO-GO (Weekend)")
            return None
        
        if signal == "NO_TRADE":
            logger.info("Decision: NO-GO")
            return None
        
        logger.info("Decision: GO")
        
        # Simulate trade
        return self.simulate_trade(signal, date)
    
    def simulate_trade(self, signal, entry_date):
        logger.info("Simulating trade...")
        
        nifty = yf.Ticker("^NSEI")
        nifty_hist = nifty.history(start=entry_date, period="5d")
        
        if len(nifty_hist) < 2:
            return None
        
        entry_price = nifty_hist['Close'].iloc[0]
        
        if signal == "BUY_CALL":
            for i in range(1, min(3, len(nifty_hist))):
                current_price = nifty_hist['Close'].iloc[i]
                change_pct = ((current_price - entry_price) / entry_price * 100)
                
                if change_pct >= 1.0:
                    win = True
                    pnl_pct = change_pct * 4
                    exit_date = nifty_hist.index[i]
                    break
                elif change_pct <= -0.5:
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
                
                if change_pct >= 1.0:
                    win = True
                    pnl_pct = change_pct * 4
                    exit_date = nifty_hist.index[i]
                    break
                elif change_pct <= -0.5:
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
        
        result = "WIN" if win else "LOSS"
        logger.info(f"{result}: {pnl_pct:+.2f}% | Exit: {exit_date.strftime('%Y-%m-%d')}\n")
        
        return trade
    
    async def run_backtest(self, days=7):
        logger.info("="*60)
        logger.info("HISTORICAL BACKTEST - Last Week's Real Data")
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
        logger.info("BACKTEST RESULTS")
        logger.info("="*60)
        
        if not self.trades:
            logger.info("\nNo trades executed")
            logger.info("Market conditions didn't meet entry criteria")
            self.save_results(None)
            return
        
        wins = [t for t in self.trades if t['win']]
        losses = [t for t in self.trades if not t['win']]
        
        total_trades = len(self.trades)
        win_rate = (len(wins) / total_trades * 100)
        
        avg_win = np.mean([t['pnl_pct'] for t in wins]) if wins else 0
        avg_loss = np.mean([t['pnl_pct'] for t in losses]) if losses else 0
        
        total_return = sum(t['pnl_pct'] for t in self.trades)
        profit_factor =abs(avg_win / avg_loss) if avg_loss != 0 else 0
        
        metrics = {
            'total_trades': total_trades,
            'wins': len(wins),
            'losses': len(losses),
            'win_rate': win_rate,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'total_return': total_return,
            'profit_factor': profit_factor
        }
        
        logger.info(f"\nTotal Trades: {total_trades}")
        logger.info(f"Wins: {len(wins)} | Losses: {len(losses)}")
        logger.info(f"Win Rate: {win_rate:.1f}%")
        logger.info(f"Avg Win: +{avg_win:.2f}%")
        logger.info(f"Avg Loss: {avg_loss:.2f}%")
        logger.info(f"Total Return: {total_return:+.2f}%")
        logger.info(f"Profit Factor: {profit_factor:.2f}")
        
        final_capital = self.capital * (1 + total_return/100)
        logger.info(f"\nStarting Capital: Rs.{self.capital:,}")
        logger.info(f"Ending Capital: Rs.{final_capital:,.0f}")
        logger.info(f"Profit: Rs.{final_capital - self.capital:+,.0f}")
        
        logger.info(f"\nAssessment:")
        if win_rate >= 70 and total_return > 0:
            logger.info("EXCELLENT - Strategy works well!")
        elif win_rate >= 55 and total_return > 0:
            logger.info("GOOD - Profitable, needs optimization")
        else:
            logger.info("NEEDS WORK - Requires improvements")
        
        logger.info("="*60)
        
        self.save_results(metrics)
        return metrics
    
    def save_results(self, metrics):
        if not metrics:
            with open("backtest_results.txt", 'w') as f:
                f.write("No trades executed during backtest period.\n")
            return
        
        final_capital = self.capital * (1 + metrics['total_return']/100)
        
        results_text = f"""
BACKTEST RESULTS - Last Week's Real Market Data
================================================

Performance Metrics:
-------------------
Total Trades: {metrics['total_trades']}
Wins: {metrics['wins']} | Losses: {metrics['losses']}
Win Rate: {metrics['win_rate']:.1f}%
Average Win: +{metrics['avg_win']:.2f}%
Average Loss: {metrics['avg_loss']:.2f}%
Total Return: {metrics['total_return']:+.2f}%
Profit Factor: {metrics['profit_factor']:.2f}

Capital Growth:
--------------
Starting Capital: Rs.{self.capital:,}
Ending Capital: Rs.{final_capital:,.0f}
Profit/Loss: Rs.{final_capital - self.capital:+,.0f}

Assessment:
----------
"""
        
        if metrics['win_rate'] >= 70 and metrics['total_return'] > 0:
            results_text += "EXCELLENT - Ready for deployment\n"
        elif metrics['win_rate'] >= 55 and metrics['total_return'] > 0:
            results_text += "GOOD - Continue with optimization\n"
        else:
            results_text += "NEEDS WORK - Requires strategy improvements\n"
        
        results_text += f"\nTrade Details:\n"
        results_text += "-" * 50 + "\n"
        for i, trade in enumerate(self.trades, 1):
            result = "WIN" if trade['win'] else "LOSS"
            results_text += f"{i}. {trade['entry_date'].strftime('%Y-%m-%d')} {trade['signal']}: {result} ({trade['pnl_pct']:+.2f}%)\n"
        
        with open("backtest_results.txt", 'w') as f:
            f.write(results_text)
        
        logger.info(f"\nResults saved to: backtest_results.txt")


async def main():
    backtester = HistoricalBacktester()
    await backtester.run_backtest(days=7)


if __name__ == "__main__":
    print(f"Starting Backtest: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    asyncio.run(main())
    print(f"\nBacktest Complete: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
