#!/usr/bin/env python3
"""
Production Services Launcher
=============================

This script launches both trading services as continuous background jobs:
1. gemini_trade_service (Port 4080) - Screening & AI Analysis
2. equity_hv_service (Port 5080) - Trade Execution & Auto-Trading

Usage:
    python run_production_services.py [--mode paper|live]

Author: DTrade Systems
Version: 1.0.0
"""

import asyncio
import subprocess
import sys
import os
import signal
import time
import argparse
import logging
from datetime import datetime
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/production_services.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class ServiceManager:
    """Manages multiple trading services as background processes"""
    
    def __init__(self):
        self.processes = {}
        self.is_running = False
        
        # Service configurations
        self.services = {
            "gemini_trade_service": {
                "name": "Gemini Trade Service (Screening)",
                "path": Path(__file__).parent / "gemini_trade_service",
                "command": ["python", "main.py"],
                "port": 4080,
                "health_endpoint": "/health"
            },
            "equity_hv_service": {
                "name": "Equity HV Service (Execution)",
                "path": Path(__file__).parent / "equity_hv_service",
                "command": ["python", "-m", "uvicorn", "equity_hv_service:app", "--host", "0.0.0.0", "--port", "5080"],
                "port": 5080,
                "health_endpoint": "/health"
            }
        }
    
    def start_service(self, service_key: str) -> bool:
        """Start a single service"""
        if service_key not in self.services:
            logger.error(f"Unknown service: {service_key}")
            return False
        
        service = self.services[service_key]
        
        try:
            logger.info(f"Starting {service['name']}...")
            
            # Set working directory
            cwd = str(service["path"]) if service_key == "gemini_trade_service" else str(Path(__file__).parent / "equity_hv_service")
            
            # Build command
            if service_key == "equity_hv_service":
                cmd = [
                    sys.executable, "-m", "uvicorn",
                    "equity_hv_service:app",
                    "--host", "0.0.0.0",
                    "--port", str(service["port"])
                ]
            else:
                cmd = [sys.executable, "main.py"]
            
            # Start process
            process = subprocess.Popen(
                cmd,
                cwd=cwd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == 'nt' else 0
            )
            
            self.processes[service_key] = process
            
            # Wait a bit for startup
            time.sleep(3)
            
            if process.poll() is None:
                logger.info(f"✅ {service['name']} started on port {service['port']}")
                return True
            else:
                stdout, stderr = process.communicate()
                logger.error(f"❌ {service['name']} failed to start")
                logger.error(f"Stderr: {stderr.decode()}")
                return False
                
        except Exception as e:
            logger.error(f"Error starting {service['name']}: {e}")
            return False
    
    def stop_service(self, service_key: str):
        """Stop a single service"""
        if service_key in self.processes:
            process = self.processes[service_key]
            if process.poll() is None:
                logger.info(f"Stopping {self.services[service_key]['name']}...")
                
                if os.name == 'nt':
                    process.terminate()
                else:
                    os.killpg(os.getpgid(process.pid), signal.SIGTERM)
                
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill()
                
                logger.info(f"✅ {self.services[service_key]['name']} stopped")
            
            del self.processes[service_key]
    
    def start_all(self) -> bool:
        """Start all services"""
        self.is_running = True
        
        # Start Gemini service first (screening)
        if not self.start_service("gemini_trade_service"):
            logger.warning("Gemini Trade Service failed to start, continuing...")
        
        time.sleep(2)
        
        # Start Equity HV service (execution)
        if not self.start_service("equity_hv_service"):
            logger.error("Equity HV Service failed to start")
            return False
        
        return True
    
    def stop_all(self):
        """Stop all services"""
        logger.info("Stopping all services...")
        self.is_running = False
        
        for service_key in list(self.processes.keys()):
            self.stop_service(service_key)
        
        logger.info("All services stopped")
    
    def check_health(self) -> dict:
        """Check health of all services"""
        import requests
        
        health = {}
        
        for service_key, service in self.services.items():
            try:
                url = f"http://localhost:{service['port']}{service['health_endpoint']}"
                response = requests.get(url, timeout=5)
                health[service_key] = {
                    "status": "healthy" if response.status_code == 200 else "unhealthy",
                    "port": service["port"],
                    "response_code": response.status_code
                }
            except Exception as e:
                health[service_key] = {
                    "status": "unreachable",
                    "port": service["port"],
                    "error": str(e)
                }
        
        return health
    
    def monitor(self):
        """Monitor running services"""
        while self.is_running:
            # Check if processes are still running
            for service_key, process in list(self.processes.items()):
                if process.poll() is not None:
                    logger.warning(f"{self.services[service_key]['name']} has stopped unexpectedly")
                    # Attempt restart
                    logger.info(f"Attempting to restart {self.services[service_key]['name']}...")
                    self.start_service(service_key)
            
            time.sleep(30)  # Check every 30 seconds


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Production Services Launcher")
    parser.add_argument("--mode", choices=["paper", "live"], default="paper",
                       help="Trading mode (default: paper)")
    parser.add_argument("--auto-trade", action="store_true",
                       help="Start auto-trader after services are running")
    args = parser.parse_args()
    
    # Create logs directory
    Path("logs").mkdir(exist_ok=True)
    
    # Create service manager
    manager = ServiceManager()
    
    # Handle shutdown signals
    def shutdown_handler(signum, frame):
        logger.info("Shutdown signal received")
        manager.stop_all()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, shutdown_handler)
    signal.signal(signal.SIGTERM, shutdown_handler)
    
    logger.info("=" * 60)
    logger.info("Production Services Launcher")
    logger.info(f"Mode: {args.mode}")
    logger.info(f"Auto-trade: {args.auto_trade}")
    logger.info("=" * 60)
    
    try:
        # Start all services
        if manager.start_all():
            logger.info("\n" + "=" * 60)
            logger.info("All services started successfully!")
            logger.info("=" * 60)
            
            # Check health
            time.sleep(5)
            health = manager.check_health()
            
            logger.info("\nService Health:")
            for service, status in health.items():
                logger.info(f"  {service}: {status['status']} (port {status['port']})")
            
            # Start auto-trader if requested
            if args.auto_trade:
                logger.info("\nStarting auto-trader...")
                import requests
                
                try:
                    response = requests.post(
                        "http://localhost:5080/api/auto-trader/start",
                        json={
                            "mode": args.mode,
                            "capital": 500000,
                            "max_positions": 5,
                            "screening_interval_seconds": 300
                        },
                        timeout=30
                    )
                    
                    if response.status_code == 200:
                        logger.info("✅ Auto-trader started successfully!")
                    else:
                        logger.warning(f"Auto-trader start returned: {response.status_code}")
                        
                except Exception as e:
                    logger.error(f"Failed to start auto-trader: {e}")
            
            logger.info("\n" + "=" * 60)
            logger.info("Services are running. Press Ctrl+C to stop.")
            logger.info("=" * 60)
            
            # Monitor services
            manager.monitor()
        else:
            logger.error("Failed to start all services")
            manager.stop_all()
            sys.exit(1)
            
    except KeyboardInterrupt:
        logger.info("\nKeyboard interrupt received")
    finally:
        manager.stop_all()


if __name__ == "__main__":
    main()
