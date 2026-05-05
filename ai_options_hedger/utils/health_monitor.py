"""
Health Monitor - Heartbeat & Fail-Safe Monitor
Ensures live feed is active, orders are not stuck, and RL agent didn't hang.
Provides comprehensive system health monitoring and alerts.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
import time
import psutil
import threading
from concurrent.futures import ThreadPoolExecutor
import json

logger = logging.getLogger(__name__)

class HealthStatus(Enum):
    """Health status levels"""
    HEALTHY = "HEALTHY"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"
    UNKNOWN = "UNKNOWN"

class ComponentType(Enum):
    """Types of components to monitor"""
    DATA_FEED = "DATA_FEED"
    ORDER_EXECUTION = "ORDER_EXECUTION"
    RL_AGENT = "RL_AGENT"
    STRATEGY_ENGINE = "STRATEGY_ENGINE"
    DATABASE = "DATABASE"
    NETWORK = "NETWORK"
    SYSTEM_RESOURCES = "SYSTEM_RESOURCES"

@dataclass
class HealthCheck:
    """Individual health check definition"""
    name: str
    component_type: ComponentType
    check_function: Callable
    interval: float  # seconds
    timeout: float = 10.0
    critical: bool = False
    enabled: bool = True
    last_check: Optional[datetime] = None
    last_status: HealthStatus = HealthStatus.UNKNOWN
    last_result: Optional[Dict[str, Any]] = None
    consecutive_failures: int = 0
    max_failures: int = 3

@dataclass
class HealthAlert:
    """Health alert information"""
    component: str
    status: HealthStatus
    message: str
    timestamp: datetime
    details: Dict[str, Any] = field(default_factory=dict)
    resolved: bool = False
    resolution_time: Optional[datetime] = None

class HealthMonitor:
    """
    Comprehensive health monitoring system that watches all critical components.
    Provides heartbeat monitoring, fail-safe mechanisms, and alerting.
    """
    
    def __init__(self, orchestrator=None, config: Dict[str, Any] = None):
        """Initialize health monitor"""
        self.orchestrator = orchestrator
        self.config = config or {}
        
        # Health checks registry
        self.health_checks: Dict[str, HealthCheck] = {}
        
        # Monitoring state
        self.is_monitoring = False
        self.monitor_task = None
        self.alert_history: List[HealthAlert] = []
        
        # Thresholds and limits
        self.data_feed_timeout = self.config.get('data_feed_timeout', 30.0)
        self.order_timeout = self.config.get('order_timeout', 60.0)
        self.rl_response_timeout = self.config.get('rl_response_timeout', 10.0)
        self.max_memory_usage = self.config.get('max_memory_usage', 80.0)  # percentage
        self.max_cpu_usage = self.config.get('max_cpu_usage', 85.0)  # percentage
        
        # Component references (set by orchestrator)
        self.data_feed = None
        self.order_engine = None
        self.rl_agent = None
        self.strategy_engine = None
        self.database = None
        
        # Alerting
        self.alert_callbacks: List[Callable] = []
        
        # Threading
        self.executor = ThreadPoolExecutor(max_workers=5)
        self.lock = threading.Lock()
        
        # Initialize default health checks
        self._register_default_health_checks()
        
        logger.info("Health Monitor initialized")
    
    def set_components(self, **components):
        """Set component references for monitoring"""
        self.data_feed = components.get('data_feed')
        self.order_engine = components.get('order_engine')
        self.rl_agent = components.get('rl_agent')
        self.strategy_engine = components.get('strategy_engine')
        self.database = components.get('database')
        logger.info("Component references set for health monitoring")
    
    def add_alert_callback(self, callback: Callable):
        """Add callback for health alerts"""
        self.alert_callbacks.append(callback)
    
    async def initialize(self):
        """Initialize health monitoring"""
        try:
            logger.info("Initializing Health Monitor")
            self.is_monitoring = True
            self.monitor_task = asyncio.create_task(self._monitoring_loop())
            logger.info("Health Monitor initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Health Monitor: {e}")
            raise
    
    async def cleanup(self):
        """Cleanup health monitoring"""
        self.is_monitoring = False
        if self.monitor_task:
            self.monitor_task.cancel()
        self.executor.shutdown(wait=True)
    
    def _register_default_health_checks(self):
        """Register default health checks"""
        
        # Data feed health check
        self.register_health_check(HealthCheck(
            name="data_feed_heartbeat",
            component_type=ComponentType.DATA_FEED,
            check_function=self._check_data_feed_health,
            interval=10.0,
            timeout=5.0,
            critical=True,
            max_failures=3
        ))
        
        # Order execution health check
        self.register_health_check(HealthCheck(
            name="order_execution_health",
            component_type=ComponentType.ORDER_EXECUTION,
            check_function=self._check_order_execution_health,
            interval=30.0,
            timeout=10.0,
            critical=True,
            max_failures=2
        ))
        
        # RL agent health check
        self.register_health_check(HealthCheck(
            name="rl_agent_health",
            component_type=ComponentType.RL_AGENT,
            check_function=self._check_rl_agent_health,
            interval=15.0,
            timeout=5.0,
            critical=False,
            max_failures=5
        ))
        
        # Strategy engine health check
        self.register_health_check(HealthCheck(
            name="strategy_engine_health",
            component_type=ComponentType.STRATEGY_ENGINE,
            check_function=self._check_strategy_engine_health,
            interval=20.0,
            timeout=5.0,
            critical=True,
            max_failures=3
        ))
        
        # Database health check
        self.register_health_check(HealthCheck(
            name="database_health",
            component_type=ComponentType.DATABASE,
            check_function=self._check_database_health,
            interval=60.0,
            timeout=10.0,
            critical=True,
            max_failures=2
        ))
        
        # System resources health check
        self.register_health_check(HealthCheck(
            name="system_resources",
            component_type=ComponentType.SYSTEM_RESOURCES,
            check_function=self._check_system_resources,
            interval=30.0,
            timeout=5.0,
            critical=False,
            max_failures=5
        ))
        
        # Network connectivity check
        self.register_health_check(HealthCheck(
            name="network_connectivity",
            component_type=ComponentType.NETWORK,
            check_function=self._check_network_connectivity,
            interval=45.0,
            timeout=10.0,
            critical=True,
            max_failures=3
        ))
    
    def register_health_check(self, health_check: HealthCheck):
        """Register a new health check"""
        with self.lock:
            self.health_checks[health_check.name] = health_check
        logger.info(f"Registered health check: {health_check.name}")
    
    def unregister_health_check(self, name: str):
        """Unregister a health check"""
        with self.lock:
            if name in self.health_checks:
                del self.health_checks[name]
                logger.info(f"Unregistered health check: {name}")
    
    async def _monitoring_loop(self):
        """Main monitoring loop"""
        logger.info("Starting health monitoring loop")
        
        while self.is_monitoring:
            try:
                current_time = datetime.now()
                
                # Check each health check
                for name, health_check in list(self.health_checks.items()):
                    if not health_check.enabled:
                        continue
                    
                    # Check if it's time to run this check
                    if (health_check.last_check is None or 
                        (current_time - health_check.last_check).total_seconds() >= health_check.interval):
                        
                        await self._run_health_check(health_check)
                
                # Sleep for a short interval
                await asyncio.sleep(1.0)
                
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(5.0)  # Wait before retrying
    
    async def _run_health_check(self, health_check: HealthCheck):
        """Run a single health check"""
        try:
            # Run check with timeout
            result = await asyncio.wait_for(
                health_check.check_function(),
                timeout=health_check.timeout
            )
            
            # Update health check status
            health_check.last_check = datetime.now()
            health_check.last_result = result
            
            # Determine status
            if result.get('success', False):
                health_check.last_status = HealthStatus.HEALTHY
                health_check.consecutive_failures = 0
            else:
                health_check.consecutive_failures += 1
                
                if health_check.consecutive_failures >= health_check.max_failures:
                    health_check.last_status = HealthStatus.CRITICAL
                else:
                    health_check.last_status = HealthStatus.WARNING
                
                # Create alert
                await self._create_alert(health_check, result)
            
        except asyncio.TimeoutError:
            health_check.last_check = datetime.now()
            health_check.consecutive_failures += 1
            health_check.last_status = HealthStatus.CRITICAL
            health_check.last_result = {'success': False, 'error': 'Timeout'}
            
            await self._create_alert(health_check, {'error': 'Health check timed out'})
            
        except Exception as e:
            health_check.last_check = datetime.now()
            health_check.consecutive_failures += 1
            health_check.last_status = HealthStatus.CRITICAL
            health_check.last_result = {'success': False, 'error': str(e)}
            
            await self._create_alert(health_check, {'error': f'Health check failed: {e}'})
    
    async def _create_alert(self, health_check: HealthCheck, result: Dict[str, Any]):
        """Create and handle health alert"""
        alert = HealthAlert(
            component=health_check.name,
            status=health_check.last_status,
            message=result.get('error', 'Health check failed'),
            timestamp=datetime.now(),
            details=result
        )
        
        self.alert_history.append(alert)
        
        # Notify callbacks
        for callback in self.alert_callbacks:
            try:
                await callback(alert)
            except Exception as e:
                logger.error(f"Error in alert callback: {e}")
        
        # Log alert
        if health_check.last_status == HealthStatus.CRITICAL:
            logger.critical(f"CRITICAL: {health_check.name} - {alert.message}")
        else:
            logger.warning(f"WARNING: {health_check.name} - {alert.message}")
        
        # Take corrective action if critical
        if health_check.critical and health_check.last_status == HealthStatus.CRITICAL:
            await self._handle_critical_failure(health_check, alert)
    
    async def _handle_critical_failure(self, health_check: HealthCheck, alert: HealthAlert):
        """Handle critical component failures"""
        logger.critical(f"Handling critical failure in {health_check.name}")
        
        try:
            if health_check.component_type == ComponentType.DATA_FEED:
                await self._handle_data_feed_failure()
            elif health_check.component_type == ComponentType.ORDER_EXECUTION:
                await self._handle_order_execution_failure()
            elif health_check.component_type == ComponentType.STRATEGY_ENGINE:
                await self._handle_strategy_engine_failure()
            elif health_check.component_type == ComponentType.DATABASE:
                await self._handle_database_failure()
            
        except Exception as e:
            logger.error(f"Error handling critical failure: {e}")
    
    # Individual health check functions
    async def _check_data_feed_health(self) -> Dict[str, Any]:
        """Check data feed health"""
        try:
            if not self.data_feed:
                return {'success': False, 'error': 'Data feed component not available'}
            
            # Check if we're receiving recent data
            last_update = getattr(self.data_feed, 'last_update_time', None)
            if last_update:
                time_diff = (datetime.now() - last_update).total_seconds()
                if time_diff > self.data_feed_timeout:
                    return {
                        'success': False, 
                        'error': f'No data received for {time_diff:.1f} seconds',
                        'last_update': last_update.isoformat()
                    }
            
            # Check data feed connection status
            if hasattr(self.data_feed, 'is_connected'):
                if not self.data_feed.is_connected():
                    return {'success': False, 'error': 'Data feed not connected'}
            
            return {
                'success': True,
                'last_update': last_update.isoformat() if last_update else None,
                'connection_status': 'connected'
            }
            
        except Exception as e:
            return {'success': False, 'error': f'Data feed check failed: {e}'}
    
    async def _check_order_execution_health(self) -> Dict[str, Any]:
        """Check order execution engine health"""
        try:
            if not self.order_engine:
                return {'success': False, 'error': 'Order engine component not available'}
            
            # Check for stuck orders
            if hasattr(self.order_engine, 'get_pending_orders'):
                pending_orders = self.order_engine.get_pending_orders()
                stuck_orders = []
                
                for order in pending_orders:
                    order_age = (datetime.now() - order.timestamp).total_seconds()
                    if order_age > self.order_timeout:
                        stuck_orders.append(order.order_id)
                
                if stuck_orders:
                    return {
                        'success': False,
                        'error': f'Found {len(stuck_orders)} stuck orders',
                        'stuck_orders': stuck_orders
                    }
            
            # Check order engine connection
            if hasattr(self.order_engine, 'is_connected'):
                if not self.order_engine.is_connected():
                    return {'success': False, 'error': 'Order engine not connected'}
            
            return {
                'success': True,
                'pending_orders': len(pending_orders) if 'pending_orders' in locals() else 0,
                'connection_status': 'connected'
            }
            
        except Exception as e:
            return {'success': False, 'error': f'Order execution check failed: {e}'}
    
    async def _check_rl_agent_health(self) -> Dict[str, Any]:
        """Check RL agent health"""
        try:
            if not self.rl_agent:
                return {'success': False, 'error': 'RL agent component not available'}
            
            # Test RL agent responsiveness
            start_time = time.time()
            
            # Create dummy state for testing
            dummy_state = [0.0] * 38  # Based on MarketState.to_array() size
            
            # Test if RL agent responds
            if hasattr(self.rl_agent, 'get_action'):
                response = await asyncio.wait_for(
                    self.rl_agent.get_action(dummy_state),
                    timeout=self.rl_response_timeout
                )
                
                response_time = time.time() - start_time
                
                return {
                    'success': True,
                    'response_time': response_time,
                    'agent_status': 'responsive'
                }
            else:
                return {'success': False, 'error': 'RL agent missing get_action method'}
            
        except asyncio.TimeoutError:
            return {'success': False, 'error': 'RL agent not responding'}
        except Exception as e:
            return {'success': False, 'error': f'RL agent check failed: {e}'}
    
    async def _check_strategy_engine_health(self) -> Dict[str, Any]:
        """Check strategy engine health"""
        try:
            if not self.strategy_engine:
                return {'success': False, 'error': 'Strategy engine component not available'}
            
            # Check strategy engine state
            if hasattr(self.strategy_engine, 'get_status'):
                status = self.strategy_engine.get_status()
                
                if status.get('state') == 'ERROR':
                    return {
                        'success': False,
                        'error': 'Strategy engine in error state',
                        'status': status
                    }
                
                return {
                    'success': True,
                    'status': status,
                    'state': status.get('state', 'unknown')
                }
            
            return {'success': True, 'status': 'unknown'}
            
        except Exception as e:
            return {'success': False, 'error': f'Strategy engine check failed: {e}'}
    
    async def _check_database_health(self) -> Dict[str, Any]:
        """Check database health"""
        try:
            if not self.database:
                return {'success': False, 'error': 'Database component not available'}
            
            # Test database connectivity
            if hasattr(self.database, 'test_connection'):
                connection_ok = await self.database.test_connection()
                if not connection_ok:
                    return {'success': False, 'error': 'Database connection failed'}
            
            # Check database space (if available)
            db_stats = {}
            if hasattr(self.database, 'get_stats'):
                db_stats = await self.database.get_stats()
            
            return {
                'success': True,
                'connection_status': 'connected',
                'stats': db_stats
            }
            
        except Exception as e:
            return {'success': False, 'error': f'Database check failed: {e}'}
    
    async def _check_system_resources(self) -> Dict[str, Any]:
        """Check system resource usage"""
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # Memory usage
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            
            # Disk usage
            disk = psutil.disk_usage('/')
            disk_percent = (disk.used / disk.total) * 100
            
            # Check thresholds
            issues = []
            if cpu_percent > self.max_cpu_usage:
                issues.append(f'High CPU usage: {cpu_percent:.1f}%')
            
            if memory_percent > self.max_memory_usage:
                issues.append(f'High memory usage: {memory_percent:.1f}%')
            
            if disk_percent > 90:  # Hard limit for disk
                issues.append(f'High disk usage: {disk_percent:.1f}%')
            
            return {
                'success': len(issues) == 0,
                'error': '; '.join(issues) if issues else None,
                'cpu_percent': cpu_percent,
                'memory_percent': memory_percent,
                'disk_percent': disk_percent,
                'available_memory_gb': memory.available / (1024**3)
            }
            
        except Exception as e:
            return {'success': False, 'error': f'System resources check failed: {e}'}
    
    async def _check_network_connectivity(self) -> Dict[str, Any]:
        """Check network connectivity"""
        try:
            import socket
            
            # Test DNS resolution
            socket.gethostbyname('www.google.com')
            
            # Test network interfaces
            network_stats = psutil.net_if_stats()
            active_interfaces = [name for name, stats in network_stats.items() if stats.isup]
            
            return {
                'success': True,
                'dns_resolution': 'working',
                'active_interfaces': len(active_interfaces),
                'interfaces': active_interfaces
            }
            
        except Exception as e:
            return {'success': False, 'error': f'Network connectivity check failed: {e}'}
    
    # Failure handlers
    async def _handle_data_feed_failure(self):
        """Handle data feed failure"""
        logger.info("Attempting to recover data feed")
        try:
            if hasattr(self.data_feed, 'reconnect'):
                await self.data_feed.reconnect()
        except Exception as e:
            logger.error(f"Failed to recover data feed: {e}")
    
    async def _handle_order_execution_failure(self):
        """Handle order execution failure"""
        logger.info("Handling order execution failure")
        try:
            # Cancel stuck orders
            if hasattr(self.order_engine, 'cancel_all_pending'):
                await self.order_engine.cancel_all_pending()
            
            # Reconnect if possible
            if hasattr(self.order_engine, 'reconnect'):
                await self.order_engine.reconnect()
        except Exception as e:
            logger.error(f"Failed to handle order execution failure: {e}")
    
    async def _handle_strategy_engine_failure(self):
        """Handle strategy engine failure"""
        logger.info("Handling strategy engine failure")
        try:
            # Emergency stop
            if self.orchestrator and hasattr(self.orchestrator, 'stop_strategy'):
                await self.orchestrator.stop_strategy()
        except Exception as e:
            logger.error(f"Failed to handle strategy engine failure: {e}")
    
    async def _handle_database_failure(self):
        """Handle database failure"""
        logger.info("Handling database failure")
        try:
            # Try to reconnect
            if hasattr(self.database, 'reconnect'):
                await self.database.reconnect()
        except Exception as e:
            logger.error(f"Failed to handle database failure: {e}")
    
    # Status and reporting methods
    async def check_health(self) -> Dict[str, Any]:
        """Manual health check - returns overall system health"""
        overall_status = HealthStatus.HEALTHY
        component_statuses = {}
        critical_issues = []
        warnings = []
        
        for name, health_check in self.health_checks.items():
            if not health_check.enabled:
                continue
            
            component_statuses[name] = {
                'status': health_check.last_status.value,
                'last_check': health_check.last_check.isoformat() if health_check.last_check else None,
                'consecutive_failures': health_check.consecutive_failures,
                'result': health_check.last_result
            }
            
            if health_check.last_status == HealthStatus.CRITICAL:
                overall_status = HealthStatus.CRITICAL
                if health_check.critical:
                    critical_issues.append(name)
            elif health_check.last_status == HealthStatus.WARNING and overall_status == HealthStatus.HEALTHY:
                overall_status = HealthStatus.WARNING
                warnings.append(name)
        
        return {
            'overall_status': overall_status.value,
            'components': component_statuses,
            'critical_issues': critical_issues,
            'warnings': warnings,
            'timestamp': datetime.now().isoformat()
        }
    
    def get_recent_alerts(self, hours: int = 24) -> List[HealthAlert]:
        """Get recent alerts"""
        cutoff = datetime.now() - timedelta(hours=hours)
        return [alert for alert in self.alert_history if alert.timestamp > cutoff]
    
    def get_component_status(self, component_name: str) -> Optional[Dict[str, Any]]:
        """Get status for specific component"""
        if component_name in self.health_checks:
            hc = self.health_checks[component_name]
            return {
                'name': component_name,
                'status': hc.last_status.value,
                'last_check': hc.last_check.isoformat() if hc.last_check else None,
                'consecutive_failures': hc.consecutive_failures,
                'enabled': hc.enabled,
                'critical': hc.critical,
                'last_result': hc.last_result
            }
        return None
