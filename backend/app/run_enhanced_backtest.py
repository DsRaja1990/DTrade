"""
Enhanced Backtest Runner

This script provides a flexible way to run backtests with different
configurations and scenarios.
"""

import asyncio
import argparse
import logging
import sys
import os
from datetime import datetime
from pathlib import Path
from typing import List, Optional

# Add backend app to Python path
current_dir = Path(__file__).parent
backend_dir = current_dir.parent
sys.path.append(str(backend_dir))

from backtest.time_based_backtest import TimeBasedBacktestEngine
from backtest.performance_analyzer import PerformanceAnalyzer
from backtest.backtest_config import (
    BacktestConfig, BacktestScenario, 
    BULL_MARKET_CONFIG, BEAR_MARKET_CONFIG, 
    VOLATILE_MARKET_CONFIG, DEFAULT_CONFIG
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('enhanced_backtest.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

class EnhancedBacktestRunner:
    """Enhanced backtest runner with configuration support"""
    
    def __init__(self, config: BacktestConfig = None):
        self.config = config or DEFAULT_CONFIG
        self.results = {}
        
    async def run_scenario(self, scenario: BacktestScenario, 
                          market_config: str = "default") -> dict:
        """Run a single backtest scenario"""
        
        logger.info(f"Starting scenario: {scenario.name}")
        logger.info(f"Description: {scenario.description}")
        logger.info(f"Period: {scenario.start_date} to {scenario.end_date}")
        logger.info(f"Capital: Rs{scenario.initial_capital:,}")
        logger.info(f"Instruments: {', '.join(scenario.instruments)}")
        
        # Initialize backtest engine
        engine = TimeBasedBacktestEngine(
            initial_capital=scenario.initial_capital,
            start_date=scenario.start_date,
            end_date=scenario.end_date
        )
        
        # Run backtest
        start_time = datetime.now()
        metrics = await engine.run_backtest(
            instruments=scenario.instruments,
            use_synthetic_data=self.config.market_data.use_synthetic_data
        )
        end_time = datetime.now()
        
        # Analyze performance
        analyzer = PerformanceAnalyzer()
        performance_metrics = analyzer.analyze_performance(
            trades=engine.trades,
            daily_pnl=engine.daily_pnl,
            initial_capital=scenario.initial_capital
        )
        
        # Generate reports  
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        scenario_name_clean = scenario.name.replace(" ", "_").replace("-", "_")
        
        # Generate performance report
        report_file = analyzer.generate_performance_report(
            metrics=performance_metrics,
            trades=engine.trades,
            initial_capital=scenario.initial_capital
        )
        
        # Create performance charts  
        charts_dir = analyzer.create_performance_charts(
            trades=engine.trades,
            daily_pnl=engine.daily_pnl,
            scenario_name=scenario_name_clean,
            timestamp=timestamp
        )
        
        # Export detailed results
        detailed_file = analyzer.export_detailed_results(
            trades=engine.trades,
            daily_pnl=engine.daily_pnl,
            scenario_name=scenario_name_clean,
            timestamp=timestamp
        )
        
        report_files = {
            "report": f"performance_report_{scenario_name_clean}_{timestamp}.txt",
            "charts": charts_dir,
            "detailed": detailed_file
        }
        
        # Save the report to file
        with open(f"performance_report_{scenario_name_clean}_{timestamp}.txt", "w", encoding="utf-8") as f:
            f.write(report_file)
        
        # Calculate execution time
        execution_time = (end_time - start_time).total_seconds()
        
        result = {
            "scenario": scenario,
            "metrics": metrics,
            "performance": performance_metrics,
            "execution_time": execution_time,
            "report_files": report_files,
            "timestamp": timestamp
        }
        
        logger.info(f"Scenario completed in {execution_time:.1f} seconds")
        logger.info(f"Total Return: {metrics.total_return_percentage:.2f}%")
        logger.info(f"Sharpe Ratio: {metrics.sharpe_ratio:.2f}")
        logger.info(f"Max Drawdown: {metrics.max_drawdown:.2f}%")
        
        return result
        
    async def run_all_scenarios(self, 
                               scenario_names: Optional[List[str]] = None,
                               market_config: str = "default") -> dict:
        """Run all or specified scenarios"""
        
        scenarios_to_run = []
        if scenario_names:
            for name in scenario_names:
                scenario = self.config.get_scenario_by_name(name)
                if scenario:
                    scenarios_to_run.append(scenario)
                else:
                    logger.warning(f"Scenario '{name}' not found")
        else:
            scenarios_to_run = self.config.scenarios
            
        logger.info(f"Running {len(scenarios_to_run)} scenarios")
        
        results = {}
        for scenario in scenarios_to_run:
            try:
                result = await self.run_scenario(scenario, market_config)
                results[scenario.name] = result
                logger.info(f"✅ Completed: {scenario.name}")
            except Exception as e:
                logger.error(f"❌ Failed: {scenario.name} - {str(e)}")
                results[scenario.name] = {"error": str(e)}
                
        return results
        
    def generate_comparison_report(self, results: dict) -> str:
        """Generate a comparison report across scenarios"""
        
        report_lines = []
        report_lines.append("="*80)
        report_lines.append("ENHANCED BACKTEST COMPARISON REPORT")
        report_lines.append("="*80)
        report_lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report_lines.append(f"Total Scenarios: {len(results)}")
        report_lines.append("")
        
        # Sort scenarios by Sharpe ratio
        valid_results = {k: v for k, v in results.items() if "error" not in v}
        if valid_results:
            sorted_results = sorted(
                valid_results.items(), 
                key=lambda x: x[1]["metrics"].sharpe_ratio, 
                reverse=True
            )
            
            report_lines.append("📊 SCENARIO RANKINGS (by Sharpe Ratio)")
            report_lines.append("-" * 60)
            
            for i, (name, result) in enumerate(sorted_results, 1):
                metrics = result["metrics"]
                report_lines.append(f"{i}. {name}")
                report_lines.append(f"   Return: {metrics.total_return_percentage:.2f}%")
                report_lines.append(f"   Sharpe: {metrics.sharpe_ratio:.2f}")
                report_lines.append(f"   Max DD: {metrics.max_drawdown:.2f}%")
                report_lines.append(f"   Trades: {metrics.total_trades}")
                report_lines.append("")
                
            # Best performing scenario
            best_name, best_result = sorted_results[0]
            report_lines.append("🏆 BEST PERFORMING SCENARIO")
            report_lines.append("-" * 40)
            report_lines.append(f"Scenario: {best_name}")
            report_lines.append(f"Sharpe Ratio: {best_result['metrics'].sharpe_ratio:.2f}")
            report_lines.append(f"Total Return: {best_result['metrics'].total_return_percentage:.2f}%")
            report_lines.append("")
            
            # Risk analysis
            report_lines.append("📈 RISK ANALYSIS")
            report_lines.append("-" * 40)
            
            avg_sharpe = sum(r["metrics"].sharpe_ratio for r in valid_results.values()) / len(valid_results)
            avg_return = sum(r["metrics"].total_return_percentage for r in valid_results.values()) / len(valid_results)
            max_drawdown = max(r["metrics"].max_drawdown for r in valid_results.values())
            
            report_lines.append(f"Average Sharpe Ratio: {avg_sharpe:.2f}")
            report_lines.append(f"Average Return: {avg_return:.2f}%")
            report_lines.append(f"Maximum Drawdown: {max_drawdown:.2f}%")
            report_lines.append("")
            
        # Failed scenarios
        failed_results = {k: v for k, v in results.items() if "error" in v}
        if failed_results:
            report_lines.append("❌ FAILED SCENARIOS")
            report_lines.append("-" * 40)
            for name, result in failed_results.items():
                report_lines.append(f"• {name}: {result['error']}")
            report_lines.append("")
            
        # Recommendations
        report_lines.append("💡 RECOMMENDATIONS")
        report_lines.append("-" * 40)
        
        if valid_results:
            if avg_sharpe > 2.0:
                report_lines.append("• Strategy shows excellent risk-adjusted returns")
            elif avg_sharpe > 1.0:
                report_lines.append("• Strategy shows good risk-adjusted returns")
            else:
                report_lines.append("• Consider optimizing strategy parameters")
                
            if max_drawdown < 0.05:
                report_lines.append("• Risk management is very effective")
            elif max_drawdown < 0.10:
                report_lines.append("• Risk management is adequate")
            else:
                report_lines.append("• Consider strengthening risk management")
                
            if avg_return > 0.15:
                report_lines.append("• Returns are strong for deployment consideration")
            elif avg_return > 0.08:
                report_lines.append("• Returns are moderate")
            else:
                report_lines.append("• Returns may need improvement")
                
        report_lines.append("")
        report_lines.append("="*80)
        
        report_content = "\n".join(report_lines)
        
        # Save report
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"enhanced_backtest_comparison_{timestamp}.txt"
        with open(filename, "w", encoding="utf-8") as f:
            f.write(report_content)
            
        logger.info(f"Comparison report saved: {filename}")
        return filename

def main():
    """Main function with command line interface"""
    
    parser = argparse.ArgumentParser(description="Enhanced Backtest Runner")
    parser.add_argument("--scenarios", nargs="*", help="Specific scenarios to run")
    parser.add_argument("--market-config", default="default", 
                       choices=["default", "bull", "bear", "volatile"],
                       help="Market configuration to use")
    parser.add_argument("--list-scenarios", action="store_true",
                       help="List available scenarios")
    
    args = parser.parse_args()
    
    # Select configuration
    config_map = {
        "default": DEFAULT_CONFIG,
        "bull": BULL_MARKET_CONFIG,
        "bear": BEAR_MARKET_CONFIG,
        "volatile": VOLATILE_MARKET_CONFIG
    }
    
    config = config_map[args.market_config]
    
    if args.list_scenarios:
        print("Available scenarios:")
        for scenario in config.scenarios:
            print(f"• {scenario.name}: {scenario.description}")
        return
        
    # Run backtests
    runner = EnhancedBacktestRunner(config)
    
    async def run_backtests():
        logger.info("🚀 Starting Enhanced Backtest Runner")
        logger.info(f"Market Configuration: {args.market_config}")
        
        results = await runner.run_all_scenarios(
            scenario_names=args.scenarios,
            market_config=args.market_config
        )
        
        # Generate comparison report
        if results:
            report_file = runner.generate_comparison_report(results)
            logger.info(f"📊 Comparison report generated: {report_file}")
        
        logger.info("🎉 Enhanced backtest completed successfully!")
        
    asyncio.run(run_backtests())

if __name__ == "__main__":
    main()
