"""
Main controller for the Indian markets trading system
"""
import os
import time
import logging
import schedule
import threading
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Custom modules
from modules.api_connector import DhanConnector
from modules.market_data import MarketDataEngine
from modules.strategy_engine import StrategyEngine
from modules.risk_manager import RiskManager
from modules.position_manager import PositionManager
from modules.capital_allocator import CapitalAllocator
from modules.analytics import PerformanceAnalytics
from modules.notification import NotificationSystem

# Load environment variables
load_dotenv()
API_KEY = os.getenv('DHAN_API_KEY')
CLIENT_ID = os.getenv('DHAN_CLIENT_ID')
ACCESS_TOKEN = os.getenv('DHAN_ACCESS_TOKEN')

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("trading_system.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class TradingSystem:
    def __init__(self, initial_capital=1000000):  # 10 Lakhs
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        self.is_market_open = False
        self.trading_active = False
        
        # Initialize components
        self.api = DhanConnector(API_KEY, CLIENT_ID, ACCESS_TOKEN)
        self.market_data = MarketDataEngine(self.api)
        self.risk_manager = RiskManager(self.api, max_capital_at_risk=0.05)  # 5% max risk
        self.position_manager = PositionManager(self.api)
        self.capital_allocator = CapitalAllocator(self.initial_capital)
        self.analytics = PerformanceAnalytics()
        self.notifier = NotificationSystem()
        
        # Initialize strategy engine with component dependencies
        self.strategy_engine = StrategyEngine(
            self.api,
            self.market_data,
            self.risk_manager,
            self.position_manager,
            self.capital_allocator
        )
        
        logger.info(f"Trading system initialized with {initial_capital} capital")
    
    def start(self):
        """Start the trading system"""
        try:
            logger.info("Starting trading system...")
            
            # Connect to API
            self.api.connect()
            
            # Check if market is open
            self.update_market_status()
            if not self.is_market_open:
                logger.warning("Market is closed, starting in monitoring mode only")
            
            # Subscribe to real-time data
            self.subscribe_to_market_data()
            
            # Initialize risk manager with current capital
            self.risk_manager.initialize(self.current_capital)
            
            # Start all system components
            self.risk_manager.start_monitoring()
            self.position_manager.start_management()
            self.strategy_engine.start()
            
            self.trading_active = True
            
            # Set up scheduled tasks
            self._setup_scheduled_tasks()
            
            # Main trading loop
            self._trading_loop()
            
        except Exception as e:
            logger.error(f"Error starting trading system: {e}", exc_info=True)
            self.stop()
    
    def stop(self):
        """Stop the trading system"""
        logger.info("Stopping trading system...")
        self.trading_active = False
        
        # Stop components in reverse order
        self.strategy_engine.stop()
        self.position_manager.stop_management()
        self.risk_manager.stop_monitoring()
        
        # Close all positions if needed
        if self.risk_manager.should_close_positions():
            self.position_manager.close_all_positions()
        
        # Unsubscribe from market data
        self.market_data.unsubscribe_all()
        
        # Disconnect API
        self.api.disconnect()
        
        # Generate end of day report
        self._generate_eod_report()
        
        logger.info("Trading system stopped")
    
    def _setup_scheduled_tasks(self):
        """Set up scheduled tasks for the trading day"""
        # Market status check every 5 minutes
        schedule.every(5).minutes.do(self.update_market_status)
        
        # Risk check every minute
        schedule.every(1).minutes.do(self.risk_manager.check_risk_parameters)
        
        # Performance update every hour
        schedule.every(1).hours.do(self.analytics.update_performance_metrics)
        
        # End of day processing
        schedule.every().day.at("15:30").do(self._end_of_day_process)
        
        # Run scheduled tasks in a separate thread
        self.scheduler_thread = threading.Thread(target=self._run_scheduler)
        self.scheduler_thread.daemon = True
        self.scheduler_thread.start()
    
    def _run_scheduler(self):
        """Run the scheduler in a separate thread"""
        while self.trading_active:
            schedule.run_pending()
            time.sleep(1)
    
    def _trading_loop(self):
        """Main trading loop"""
        logger.info("Entering main trading loop")
        
        while self.trading_active:
            try:
                if self.is_market_open:
                    # Update current capital based on positions
                    self.current_capital = self.position_manager.get_account_value()
                    self.capital_allocator.update_available_capital(self.current_capital)
                    
                    # Execute strategies
                    self.strategy_engine.execute_strategies()
                    
                    # Log current status
                    if datetime.now().second == 0:  # Once per minute
                        self._log_system_status()
                
                time.sleep(1)  # 1 second intervals
                
            except Exception as e:
                logger.error(f"Error in trading loop: {e}", exc_info=True)
                # Continue running despite errors
    
    def update_market_status(self):
        """Check if market is open"""
        try:
            self.is_market_open = self.api.check_market_status()
            logger.info(f"Market status updated: {'Open' if self.is_market_open else 'Closed'}")
            return self.is_market_open
        except Exception as e:
            logger.error(f"Error checking market status: {e}")
            return False
    
    def subscribe_to_market_data(self):
        """Subscribe to required market data streams"""
        try:
            # Subscribe to indices
            self.market_data.subscribe_index("NIFTY 50")
            self.market_data.subscribe_index("NIFTY BANK")
            self.market_data.subscribe_index("INDIA VIX")
            self.market_data.subscribe_index("SENSEX")
            
            # Subscribe to major option chains
            self.market_data.subscribe_option_chain("NIFTY 50", depth=5)  # Top 5 strikes around ATM
            self.market_data.subscribe_option_chain("NIFTY BANK", depth=5)
            
            # Subscribe to selected stocks
            top_stocks = self.market_data.get_top_liquid_stocks(10)
            for stock in top_stocks:
                self.market_data.subscribe_equity(stock)
            
            logger.info("Subscribed to all required market data streams")
        except Exception as e:
            logger.error(f"Error subscribing to market data: {e}")
    
    def _end_of_day_process(self):
        """End of day processing"""
        logger.info("Running end of day process")
        
        # Close all positions if needed
        if self.risk_manager.should_close_eod_positions():
            self.position_manager.close_all_positions()
        
        # Generate EOD report
        self._generate_eod_report()
        
        # Reset daily metrics
        self.analytics.reset_daily_metrics()
    
    def _generate_eod_report(self):
        """Generate end of day report"""
        try:
            # Get current positions
            positions = self.position_manager.get_all_positions()
            
            # Get position history
            history = self.position_manager.get_position_history()
            
            # Get risk metrics
            risk_metrics = self.risk_manager.get_risk_metrics()
            
            # Get allocation report
            allocation_report = self.capital_allocator.get_allocation_report()
            
            # Get performance metrics
            performance = self.analytics.get_performance_metrics()
            
            # Create report
            report = {
                'date': datetime.now().strftime('%Y-%m-%d'),
                'account_value': self.current_capital,
                'daily_change': risk_metrics.get('daily_pnl', 0),
                'daily_change_pct': risk_metrics.get('daily_pnl_percentage', 0) * 100,
                'open_positions': len(positions),
                'closed_positions': len([p for p in history if p.get('exit_time') and p['exit_time'].date() == datetime.now().date()]),
                'capital_allocation': allocation_report,
                'risk_metrics': risk_metrics,
                'performance': performance
            }
            
            # Log summary
            logger.info(f"EOD Report: Account value: {report['account_value']:.2f}, Daily P&L: {report['daily_change']:.2f} ({report['daily_change_pct']:.2f}%)")
            
            # Save report to file
            report_file = f"reports/eod_report_{datetime.now().strftime('%Y%m%d')}.json"
            os.makedirs(os.path.dirname(report_file), exist_ok=True)
            
            with open(report_file, 'w') as f:
                import json
                json.dump(report, f, indent=4, default=str)
            
            # Send notification
            self.notifier.send_eod_report(report)
            
            logger.info(f"EOD report generated and saved to {report_