"""
Advanced Logger for Intelligent Options Hedging Engine
Provides structured logging with multiple handlers, log rotation, and performance tracking
"""

import logging
import logging.handlers
import json
import time
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List
from enum import Enum
import threading
from dataclasses import dataclass, asdict
import gzip
import shutil

class LogLevel(Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"
    TRADE = "TRADE"
    SIGNAL = "SIGNAL"
    RISK = "RISK"

@dataclass
class LogEntry:
    timestamp: float
    level: str
    module: str
    message: str
    extra_data: Dict[str, Any]
    trade_id: Optional[str] = None
    symbol: Optional[str] = None
    strategy: Optional[str] = None

class StructuredFormatter(logging.Formatter):
    """Custom formatter for structured JSON logging"""
    
    def format(self, record):
        log_entry = {
            'timestamp': record.created,
            'datetime': datetime.fromtimestamp(record.created).isoformat(),
            'level': record.levelname,
            'module': record.name,
            'message': record.getMessage(),
            'thread': record.thread,
            'process': record.process
        }
        
        # Add extra fields if present
        if hasattr(record, 'trade_id'):
            log_entry['trade_id'] = record.trade_id
        if hasattr(record, 'symbol'):
            log_entry['symbol'] = record.symbol
        if hasattr(record, 'strategy'):
            log_entry['strategy'] = record.strategy
        if hasattr(record, 'extra_data'):
            log_entry['extra_data'] = record.extra_data
        if hasattr(record, 'performance_data'):
            log_entry['performance_data'] = record.performance_data
            
        return json.dumps(log_entry)

class PerformanceLogger:
    """Separate logger for performance metrics"""
    
    def __init__(self, log_dir: Path):
        self.log_dir = log_dir
        self.performance_data = []
        self.lock = threading.Lock()
        
    def log_performance(self, metric_name: str, value: float, 
                       context: Dict[str, Any] = None):
        """Log performance metrics"""
        entry = {
            'timestamp': time.time(),
            'metric': metric_name,
            'value': value,
            'context': context or {}
        }
        
        with self.lock:
            self.performance_data.append(entry)
            
    def flush_performance_data(self):
        """Flush performance data to file"""
        if not self.performance_data:
            return
            
        with self.lock:
            data_to_write = self.performance_data.copy()
            self.performance_data.clear()
            
        perf_file = self.log_dir / f"performance_{datetime.now().strftime('%Y%m%d')}.jsonl"
        with open(perf_file, 'a') as f:
            for entry in data_to_write:
                f.write(json.dumps(entry) + '\n')

class TradeLogger:
    """Specialized logger for trade events"""
    
    def __init__(self, log_dir: Path):
        self.logger = logging.getLogger('trades')
        self.logger.setLevel(logging.INFO)
        
        # Trade-specific handler
        trade_handler = logging.handlers.TimedRotatingFileHandler(
            log_dir / 'trades.log',
            when='midnight',
            interval=1,
            backupCount=30
        )
        trade_handler.setFormatter(StructuredFormatter())
        self.logger.addHandler(trade_handler)
        
    def log_trade(self, trade_type: str, symbol: str, quantity: int,
                  price: float, trade_id: str, strategy: str,
                  extra_data: Dict[str, Any] = None):
        """Log trade execution"""
        self.logger.info(
            f"TRADE {trade_type}: {symbol} {quantity}@{price}",
            extra={
                'trade_id': trade_id,
                'symbol': symbol,
                'strategy': strategy,
                'extra_data': {
                    'trade_type': trade_type,
                    'quantity': quantity,
                    'price': price,
                    **(extra_data or {})
                }
            }
        )

class AsyncLogHandler(logging.Handler):
    """Async log handler for non-blocking logging"""
    
    def __init__(self, target_handler):
        super().__init__()
        self.target_handler = target_handler
        self.queue = asyncio.Queue()
        self.running = False
        
    async def start(self):
        """Start async logging task"""
        self.running = True
        asyncio.create_task(self._process_logs())
        
    async def stop(self):
        """Stop async logging"""
        self.running = False
        
    def emit(self, record):
        """Emit log record to queue"""
        if self.running:
            try:
                asyncio.create_task(self.queue.put(record))
            except RuntimeError:
                # No event loop running, fall back to sync
                self.target_handler.emit(record)
    
    async def _process_logs(self):
        """Process logs from queue"""
        while self.running:
            try:
                record = await asyncio.wait_for(self.queue.get(), timeout=1.0)
                self.target_handler.emit(record)
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                print(f"Error in async logging: {e}")

class IntelligentLogger:
    """Advanced logger with multiple specialized handlers"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.log_dir = Path(config.get('log_dir', 'logs'))
        self.log_dir.mkdir(exist_ok=True)
        
        # Initialize components
        self.performance_logger = PerformanceLogger(self.log_dir)
        self.trade_logger = TradeLogger(self.log_dir)
        
        # Setup main logger
        self.logger = logging.getLogger('hedging_engine')
        self.logger.setLevel(getattr(logging, config.get('log_level', 'INFO')))
        
        # Clear existing handlers
        self.logger.handlers.clear()
        
        # Setup handlers
        self._setup_handlers()
        
        # Start background tasks
        self._start_background_tasks()
        
    def _setup_handlers(self):
        """Setup various log handlers"""
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        console_handler.setFormatter(console_formatter)
        self.logger.addHandler(console_handler)
        
        # Main file handler with rotation
        main_handler = logging.handlers.TimedRotatingFileHandler(
            self.log_dir / 'hedging_engine.log',
            when='midnight',
            interval=1,
            backupCount=30,
            encoding='utf-8'
        )
        main_handler.setLevel(logging.DEBUG)
        main_handler.setFormatter(StructuredFormatter())
        
        # Compress old log files
        def compress_rotated_log(source, dest):
            with open(source, 'rb') as f_in:
                with gzip.open(dest + '.gz', 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)
            Path(source).unlink()
                    
        main_handler.rotator = compress_rotated_log
        self.logger.addHandler(main_handler)
        
        # Error file handler
        error_handler = logging.handlers.TimedRotatingFileHandler(
            self.log_dir / 'errors.log',
            when='midnight',
            interval=1,
            backupCount=7
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(StructuredFormatter())
        self.logger.addHandler(error_handler)
        
        # Signal-specific handler
        signal_handler = logging.handlers.TimedRotatingFileHandler(
            self.log_dir / 'signals.log',
            when='midnight',
            interval=1,
            backupCount=15
        )
        signal_handler.setLevel(logging.INFO)
        signal_handler.setFormatter(StructuredFormatter())
        signal_handler.addFilter(lambda record: hasattr(record, 'signal_type'))
        self.logger.addHandler(signal_handler)
        
    def _start_background_tasks(self):
        """Start background logging tasks"""
        def flush_performance():
            while True:
                time.sleep(60)  # Flush every minute
                self.performance_logger.flush_performance_data()
                
        perf_thread = threading.Thread(target=flush_performance, daemon=True)
        perf_thread.start()
        
    def info(self, message: str, **kwargs):
        """Log info message"""
        self.logger.info(message, extra=kwargs)
        
    def debug(self, message: str, **kwargs):
        """Log debug message"""
        self.logger.debug(message, extra=kwargs)
        
    def warning(self, message: str, **kwargs):
        """Log warning message"""
        self.logger.warning(message, extra=kwargs)
        
    def error(self, message: str, **kwargs):
        """Log error message"""
        self.logger.error(message, extra=kwargs)
        
    def critical(self, message: str, **kwargs):
        """Log critical message"""
        self.logger.critical(message, extra=kwargs)
        
    def log_signal(self, signal_type: str, symbol: str, confidence: float,
                   signal_data: Dict[str, Any], strategy: str = None):
        """Log signal generation"""
        self.logger.info(
            f"SIGNAL {signal_type}: {symbol} (confidence: {confidence:.3f})",
            extra={
                'signal_type': signal_type,
                'symbol': symbol,
                'strategy': strategy,
                'extra_data': {
                    'confidence': confidence,
                    'signal_data': signal_data
                }
            }
        )
        
    def log_trade(self, trade_type: str, symbol: str, quantity: int,
                  price: float, trade_id: str, strategy: str,
                  extra_data: Dict[str, Any] = None):
        """Log trade execution"""
        self.trade_logger.log_trade(
            trade_type, symbol, quantity, price, trade_id, strategy, extra_data
        )
        
    def log_performance(self, metric_name: str, value: float,
                       context: Dict[str, Any] = None):
        """Log performance metric"""
        self.performance_logger.log_performance(metric_name, value, context)
        
    def log_risk_event(self, risk_type: str, severity: str, message: str,
                      symbol: str = None, strategy: str = None,
                      risk_data: Dict[str, Any] = None):
        """Log risk-related events"""
        level = logging.ERROR if severity in ['HIGH', 'CRITICAL'] else logging.WARNING
        
        self.logger.log(
            level,
            f"RISK {risk_type} [{severity}]: {message}",
            extra={
                'risk_type': risk_type,
                'severity': severity,
                'symbol': symbol,
                'strategy': strategy,
                'extra_data': risk_data or {}
            }
        )
        
    def log_market_event(self, event_type: str, symbol: str, 
                        event_data: Dict[str, Any]):
        """Log market events"""
        self.logger.info(
            f"MARKET {event_type}: {symbol}",
            extra={
                'event_type': event_type,
                'symbol': symbol,
                'extra_data': event_data
            }
        )
        
    def get_log_stats(self) -> Dict[str, Any]:
        """Get logging statistics"""
        stats = {
            'log_files': [],
            'total_size': 0,
            'error_count': 0,
            'warning_count': 0
        }
        
        for log_file in self.log_dir.glob('*.log'):
            file_stats = log_file.stat()
            stats['log_files'].append({
                'name': log_file.name,
                'size': file_stats.st_size,
                'modified': file_stats.st_mtime
            })
            stats['total_size'] += file_stats.st_size
            
        return stats

# Global logger instance
_logger_instance = None

def setup_logger(config: Dict[str, Any]) -> IntelligentLogger:
    """Setup global logger instance"""
    global _logger_instance
    _logger_instance = IntelligentLogger(config)
    return _logger_instance

def get_logger() -> IntelligentLogger:
    """Get global logger instance"""
    if _logger_instance is None:
        raise RuntimeError("Logger not initialized. Call setup_logger() first.")
    return _logger_instance

# Convenience function for simple setup
def setup_logging(log_dir: str = "logs", log_level: str = "INFO") -> IntelligentLogger:
    """
    Simple setup function for logging initialization.
    
    Args:
        log_dir: Directory for log files
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    
    Returns:
        Configured IntelligentLogger instance
    """
    config = {
        'log_dir': log_dir,
        'log_level': log_level.upper(),
    }
    return setup_logger(config)

# Convenience functions
def log_info(message: str, **kwargs):
    get_logger().info(message, **kwargs)

def log_error(message: str, **kwargs):
    get_logger().error(message, **kwargs)

def log_warning(message: str, **kwargs):
    get_logger().warning(message, **kwargs)

def log_debug(message: str, **kwargs):
    get_logger().debug(message, **kwargs)

def log_signal(signal_type: str, symbol: str, confidence: float,
               signal_data: Dict[str, Any], strategy: str = None):
    get_logger().log_signal(signal_type, symbol, confidence, signal_data, strategy)

def log_trade(trade_type: str, symbol: str, quantity: int,
              price: float, trade_id: str, strategy: str,
              extra_data: Dict[str, Any] = None):
    get_logger().log_trade(trade_type, symbol, quantity, price, trade_id, strategy, extra_data)

