#!/usr/bin/env python3
"""
DTrade Universal Service Launcher
Centralized startup script for all DTrade services including frontend, backend, and microservices
"""

import os
import sys
import time
import json
import signal
import logging
import argparse
import subprocess
import threading
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any
import requests
import asyncio

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/dtrade_launcher.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('DTradeLauncher')

class DTradeServiceLauncher:
    """Universal launcher for all DTrade services"""
    
    def __init__(self):
        self.root_dir = Path(__file__).parent.parent
        self.processes = {}
        self.services_config = self._load_services_config()
        self.running = False
        
        # Ensure logs directory exists
        os.makedirs(self.root_dir / "logs", exist_ok=True)
        
    def _load_services_config(self) -> Dict[str, Any]:
        """Load service configuration"""
        return {
            "frontend": {
                "name": "React Frontend",
                "directory": "frontend",
                "command": ["npm", "run", "dev"],
                "port": 5173,
                "health_endpoint": "http://localhost:5173",
                "startup_delay": 2,
                "enabled": True,
                "category": "ui"
            },
            "backend": {
                "name": "DTrade Backend",
                "directory": "backend",
                "command": ["python", "minimal_backend.py"],
                "port": 8000,
                "health_endpoint": "http://localhost:8000/health",
                "startup_delay": 3,
                "enabled": True,
                "category": "core"
            },
            "index_scalping": {
                "name": "Index Scalping Service",
                "directory": "index_scalping_service",
                "command": ["python", "index_scalping_service.py"],
                "port": 8003,
                "health_endpoint": "http://localhost:8003/status",
                "startup_delay": 5,
                "enabled": True,
                "category": "strategy"
            },
            "qsbp_service": {
                "name": "QSBP Service",
                "directory": "qsbp_service",
                "command": ["python", "qsbp_service.py"],
                "port": 8001,
                "health_endpoint": "http://localhost:8001/health",
                "startup_delay": 4,
                "enabled": True,
                "category": "strategy"
            },
            "signal_engine": {
                "name": "Revolutionary Signal Engine",
                "directory": "signal_engine",
                "command": ["python", "revolutionary_signal_engine.py"],
                "port": 8002,
                "health_endpoint": "http://localhost:8002/health",
                "startup_delay": 4,
                "enabled": True,
                "category": "engine"
            },
            "ratio_service": {
                "name": "Ratio Service",
                "directory": "ratio_service",
                "command": ["python", "ratio_service.py"],
                "port": 8004,
                "health_endpoint": "http://localhost:8004/health",
                "startup_delay": 3,
                "enabled": True,
                "category": "strategy"
            }
        }
    
    def _check_port_availability(self, port: int) -> bool:
        """Check if a port is available"""
        import socket
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(1)
                result = sock.connect_ex(('localhost', port))
                return result != 0
        except Exception:
            return True
    
    def _check_service_health(self, service_name: str, config: Dict[str, Any]) -> bool:
        """Check if a service is healthy"""
        try:
            response = requests.get(config["health_endpoint"], timeout=5)
            return response.status_code == 200
        except Exception:
            return False
    
    def _start_service(self, service_name: str, config: Dict[str, Any]) -> Optional[subprocess.Popen]:
        """Start a single service"""
        try:
            # Check if port is already in use
            if not self._check_port_availability(config["port"]):
                logger.warning(f"Port {config['port']} already in use for {service_name}")
                # Check if it's our service running
                if self._check_service_health(service_name, config):
                    logger.info(f"{config['name']} is already running and healthy")
                    return None
                else:
                    logger.error(f"Port {config['port']} occupied by unknown service")
                    return None
            
            # Change to service directory
            service_dir = self.root_dir / config["directory"]
            if not service_dir.exists():
                logger.error(f"Service directory not found: {service_dir}")
                return None
            
            logger.info(f"🚀 Starting {config['name']}...")
            
            # Create log file for the service
            log_file = self.root_dir / "logs" / f"{service_name}.log"
            
            # Start the service
            with open(log_file, 'w') as log:
                process = subprocess.Popen(
                    config["command"],
                    cwd=service_dir,
                    stdout=log,
                    stderr=subprocess.STDOUT,
                    creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == "win32" else 0
                )
            
            # Wait for startup
            time.sleep(config["startup_delay"])
            
            # Check if process is still running
            if process.poll() is None:
                logger.info(f"✅ {config['name']} started successfully (PID: {process.pid})")
                return process
            else:
                logger.error(f"❌ {config['name']} failed to start")
                return None
                
        except Exception as e:
            logger.error(f"Failed to start {service_name}: {e}")
            return None
    
    def _wait_for_service_health(self, service_name: str, config: Dict[str, Any], timeout: int = 30) -> bool:
        """Wait for service to become healthy"""
        logger.info(f"⏳ Waiting for {config['name']} to become healthy...")
        
        start_time = time.time()
        while time.time() - start_time < timeout:
            if self._check_service_health(service_name, config):
                logger.info(f"✅ {config['name']} is healthy")
                return True
            time.sleep(2)
        
        logger.warning(f"⚠️ {config['name']} did not become healthy within {timeout}s")
        return False
    
    def start_all_services(self, categories: Optional[List[str]] = None, exclude: Optional[List[str]] = None):
        """Start all enabled services"""
        logger.info("🚀 Starting DTrade Universal Service Launcher")
        logger.info("=" * 70)
        
        self.running = True
        
        # Filter services based on categories and exclusions
        services_to_start = {}
        for service_name, config in self.services_config.items():
            if not config.get("enabled", True):
                continue
            
            if categories and config.get("category") not in categories:
                continue
            
            if exclude and service_name in exclude:
                continue
            
            services_to_start[service_name] = config
        
        logger.info(f"📋 Services to start: {list(services_to_start.keys())}")
        
        # Start services in dependency order (core -> engines -> strategies -> ui)
        start_order = ["core", "engine", "strategy", "ui"]
        
        for category in start_order:
            category_services = {k: v for k, v in services_to_start.items() 
                               if v.get("category") == category}
            
            if not category_services:
                continue
            
            logger.info(f"\n📂 Starting {category.upper()} services...")
            
            for service_name, config in category_services.items():
                process = self._start_service(service_name, config)
                if process:
                    self.processes[service_name] = {
                        "process": process,
                        "config": config,
                        "started_at": datetime.now()
                    }
        
        # Wait for all services to become healthy
        logger.info("\n🔍 Checking service health...")
        for service_name, service_info in self.processes.items():
            self._wait_for_service_health(service_name, service_info["config"])
        
        # Display service status
        self._display_service_status()
        
        logger.info("\n🎉 DTrade services startup complete!")
        logger.info("💡 Press Ctrl+C to stop all services")
    
    def stop_all_services(self):
        """Stop all running services"""
        logger.info("\n🛑 Stopping all DTrade services...")
        
        self.running = False
        
        for service_name, service_info in self.processes.items():
            try:
                process = service_info["process"]
                config = service_info["config"]
                
                logger.info(f"⏹️ Stopping {config['name']}...")
                
                if sys.platform == "win32":
                    # Windows: terminate process tree
                    subprocess.run(["taskkill", "/F", "/T", "/PID", str(process.pid)], 
                                 capture_output=True)
                else:
                    # Unix: send SIGTERM
                    process.terminate()
                    try:
                        process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        process.kill()
                
                logger.info(f"✅ {config['name']} stopped")
                
            except Exception as e:
                logger.error(f"Error stopping {service_name}: {e}")
        
        self.processes.clear()
        logger.info("🏁 All services stopped")
    
    def restart_service(self, service_name: str):
        """Restart a specific service"""
        if service_name not in self.services_config:
            logger.error(f"Unknown service: {service_name}")
            return
        
        config = self.services_config[service_name]
        
        # Stop if running
        if service_name in self.processes:
            logger.info(f"🔄 Restarting {config['name']}...")
            process = self.processes[service_name]["process"]
            try:
                if sys.platform == "win32":
                    subprocess.run(["taskkill", "/F", "/T", "/PID", str(process.pid)], 
                                 capture_output=True)
                else:
                    process.terminate()
                    process.wait(timeout=5)
            except Exception as e:
                logger.warning(f"Error stopping {service_name}: {e}")
            
            del self.processes[service_name]
            time.sleep(2)
        
        # Start the service
        process = self._start_service(service_name, config)
        if process:
            self.processes[service_name] = {
                "process": process,
                "config": config,
                "started_at": datetime.now()
            }
            self._wait_for_service_health(service_name, config)
    
    def _display_service_status(self):
        """Display current status of all services"""
        logger.info("\n📊 Service Status:")
        logger.info("-" * 70)
        
        for service_name, config in self.services_config.items():
            if not config.get("enabled", True):
                continue
            
            status = "❌ Not Running"
            health = "Unknown"
            
            if service_name in self.processes:
                process = self.processes[service_name]["process"]
                if process.poll() is None:
                    status = "✅ Running"
                    if self._check_service_health(service_name, config):
                        health = "Healthy"
                    else:
                        health = "Unhealthy"
                else:
                    status = "💀 Crashed"
            
            logger.info(f"{config['name']:30} | {status:15} | Port: {config['port']:4} | {health}")
    
    def monitor_services(self):
        """Monitor running services and restart if needed"""
        logger.info("👁️ Starting service monitor...")
        
        while self.running:
            try:
                time.sleep(10)  # Check every 10 seconds
                
                crashed_services = []
                for service_name, service_info in self.processes.items():
                    process = service_info["process"]
                    if process.poll() is not None:  # Process has terminated
                        crashed_services.append(service_name)
                
                for service_name in crashed_services:
                    logger.warning(f"💀 {service_name} has crashed, restarting...")
                    self.restart_service(service_name)
                
            except KeyboardInterrupt:
                break
            except Exception as e:
                logger.error(f"Monitor error: {e}")
    
    def run_interactive_mode(self):
        """Run in interactive mode with command prompt"""
        logger.info("\n🎮 Interactive Mode - Available Commands:")
        logger.info("  status    - Show service status")
        logger.info("  restart <service> - Restart specific service")
        logger.info("  stop      - Stop all services")
        logger.info("  quit/exit - Exit launcher")
        
        while self.running:
            try:
                command = input("\nDTrade> ").strip().lower()
                
                if command == "status":
                    self._display_service_status()
                elif command.startswith("restart "):
                    service_name = command.split(" ", 1)[1]
                    self.restart_service(service_name)
                elif command == "stop":
                    self.stop_all_services()
                    break
                elif command in ["quit", "exit"]:
                    self.stop_all_services()
                    break
                elif command == "help":
                    logger.info("Available commands: status, restart <service>, stop, quit/exit")
                else:
                    logger.info("Unknown command. Type 'help' for available commands.")
                    
            except KeyboardInterrupt:
                logger.info("\nShutting down...")
                self.stop_all_services()
                break
            except EOFError:
                logger.info("\nShutting down...")
                self.stop_all_services()
                break

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="DTrade Universal Service Launcher")
    parser.add_argument("--categories", nargs="+", 
                       choices=["core", "engine", "strategy", "ui"],
                       help="Start only specific categories of services")
    parser.add_argument("--exclude", nargs="+",
                       help="Exclude specific services")
    parser.add_argument("--no-monitor", action="store_true",
                       help="Disable service monitoring")
    parser.add_argument("--interactive", action="store_true",
                       help="Run in interactive mode")
    
    args = parser.parse_args()
    
    launcher = DTradeServiceLauncher()
    
    def signal_handler(signum, frame):
        logger.info("\n🛑 Received shutdown signal")
        launcher.stop_all_services()
        sys.exit(0)
    
    # Set up signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    if hasattr(signal, 'SIGTERM'):
        signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # Start services
        launcher.start_all_services(
            categories=args.categories,
            exclude=args.exclude
        )
        
        if args.interactive:
            launcher.run_interactive_mode()
        elif not args.no_monitor:
            # Start monitoring in background
            monitor_thread = threading.Thread(target=launcher.monitor_services)
            monitor_thread.daemon = True
            monitor_thread.start()
            
            # Keep main thread alive
            while launcher.running:
                time.sleep(1)
        else:
            # Just wait for interrupt
            while launcher.running:
                time.sleep(1)
                
    except Exception as e:
        logger.error(f"Launcher error: {e}")
    finally:
        launcher.stop_all_services()

if __name__ == "__main__":
    main()
