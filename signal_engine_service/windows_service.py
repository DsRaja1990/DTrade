"""
AI Signal Engine Windows Service Wrapper
=========================================
Runs the World-Class Signal Engine as a Windows service.
Service Name: AISignalEngineService
Port: 4090
"""

import win32serviceutil
import win32service
import win32event
import servicemanager
import socket
import sys
import os
import subprocess
import logging
from pathlib import Path

# Setup paths
SERVICE_DIR = Path(__file__).parent
PROJECT_ROOT = SERVICE_DIR.parent
LOG_DIR = SERVICE_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_DIR / "service_wrapper.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("AISignalEngineService")


class AISignalEngineService(win32serviceutil.ServiceFramework):
    """Windows Service for AI Signal Engine"""
    
    _svc_name_ = "AISignalEngineService"
    _svc_display_name_ = "AI Signal Engine Service"
    _svc_description_ = "World-Class AI-Powered Trading Signal Generator for NIFTY, BANKNIFTY, SENSEX. Port 4090"
    
    def __init__(self, args):
        win32serviceutil.ServiceFramework.__init__(self, args)
        self.hWaitStop = win32event.CreateEvent(None, 0, 0, None)
        self.process = None
        socket.setdefaulttimeout(60)
    
    def SvcStop(self):
        """Stop the service"""
        logger.info("Stopping AI Signal Engine Service...")
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        win32event.SetEvent(self.hWaitStop)
        
        if self.process:
            try:
                self.process.terminate()
                self.process.wait(timeout=10)
            except Exception as e:
                logger.error(f"Error stopping process: {e}")
                try:
                    self.process.kill()
                except:
                    pass
        
        logger.info("AI Signal Engine Service stopped")
    
    def SvcDoRun(self):
        """Run the service"""
        servicemanager.LogMsg(
            servicemanager.EVENTLOG_INFORMATION_TYPE,
            servicemanager.PYS_SERVICE_STARTED,
            (self._svc_name_, '')
        )
        logger.info("Starting AI Signal Engine Service...")
        self.main()
    
    def main(self):
        """Main service loop"""
        try:
            # Find Python executable
            venv_python = PROJECT_ROOT / ".venv" / "Scripts" / "python.exe"
            if venv_python.exists():
                python_exe = str(venv_python)
            else:
                python_exe = sys.executable
            
            # Path to the main script
            script_path = SERVICE_DIR / "world_class_signal_engine.py"
            
            logger.info(f"Python: {python_exe}")
            logger.info(f"Script: {script_path}")
            
            # Start the process
            self.process = subprocess.Popen(
                [python_exe, str(script_path)],
                cwd=str(SERVICE_DIR),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            
            logger.info(f"Process started with PID: {self.process.pid}")
            
            # Wait for stop signal
            while True:
                rc = win32event.WaitForSingleObject(self.hWaitStop, 5000)
                if rc == win32event.WAIT_OBJECT_0:
                    break
                
                # Check if process is still running
                if self.process.poll() is not None:
                    logger.warning("Process exited unexpectedly, restarting...")
                    self.process = subprocess.Popen(
                        [python_exe, str(script_path)],
                        cwd=str(SERVICE_DIR),
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        creationflags=subprocess.CREATE_NO_WINDOW
                    )
        
        except Exception as e:
            logger.error(f"Service error: {e}")
            servicemanager.LogErrorMsg(f"AI Signal Engine Service error: {e}")


if __name__ == '__main__':
    if len(sys.argv) == 1:
        servicemanager.Initialize()
        servicemanager.PrepareToHostSingle(AISignalEngineService)
        servicemanager.StartServiceCtrlDispatcher()
    else:
        win32serviceutil.HandleCommandLine(AISignalEngineService)
