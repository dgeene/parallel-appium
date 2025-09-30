"""
Appium Server Manager - Manages individual Appium server instances
"""
import os
import time
import logging
import threading
import subprocess
import signal
import requests
from typing import Optional, Dict, Any


class AppiumServerManager:
    """Manages a single Appium server instance with unique port and log file"""
    
    def __init__(self, port: int, session_id: str, log_dir: str = "logs"):
        self.port = port
        self.session_id = session_id
        self.log_dir = log_dir
        self.process: Optional[subprocess.Popen] = None
        self._lock = threading.Lock()
        self.is_running = False
        
        # Ensure log directory exists
        os.makedirs(self.log_dir, exist_ok=True)
        
        # Setup logging for this server instance
        self.log_file = os.path.join(self.log_dir, f"appium_server_{session_id}_{port}.log")
        self.logger = self._setup_logger()
        
    def _setup_logger(self) -> logging.Logger:
        """Setup a logger for this specific server instance"""
        logger = logging.getLogger(f"appium_server_{self.session_id}")
        logger.setLevel(logging.INFO)
        
        # Remove any existing handlers to avoid duplicates
        logger.handlers.clear()
        
        # File handler for server-specific logs
        file_handler = logging.FileHandler(self.log_file)
        file_handler.setLevel(logging.INFO)
        
        # Formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(formatter)
        
        logger.addHandler(file_handler)
        return logger
    
    def start(self, timeout: int = 30) -> bool:
        """Start the Appium server"""
        with self._lock:
            if self.is_running:
                self.logger.warning(f"Server for session {self.session_id} is already running")
                return True
            
            try:
                self.logger.info(f"Starting Appium server for session {self.session_id} on port {self.port}")
                
                # Build the Appium command
                cmd = [
                    "appium",
                    "--address", "127.0.0.1",
                    "--port", str(self.port),
                    "--session-override",          # Allow session override
                    "--log-timestamp",             # Add timestamps to logs
                    "--log-no-colors",             # Disable colors in logs for file output
                    "--relaxed-security",          # Allow relaxed security for testing
                    "--log", self.log_file,        # Log file path
                ]
                
                # Open log file for writing
                with open(self.log_file, 'w') as log_file:
                    # Start the Appium server process
                    self.process = subprocess.Popen(
                        cmd,
                        stdout=log_file,
                        stderr=subprocess.STDOUT,
                        preexec_fn=os.setsid  # Create new process group for proper cleanup
                    )
                
                # Wait for service to be ready
                if self._wait_for_server_ready(timeout):
                    self.is_running = True
                    self.logger.info(f"Appium server started successfully on port {self.port}")
                    return True
                else:
                    self.logger.error(f"Failed to start Appium server on port {self.port} within {timeout}s")
                    self._cleanup_process()
                    return False
                    
            except Exception as e:
                self.logger.error(f"Error starting Appium server: {str(e)}")
                self._cleanup_process()
                return False

    def _wait_for_server_ready(self, timeout: int) -> bool:
        """Wait for the Appium server to be ready"""
        start_time = time.time()
        status_url = f"http://127.0.0.1:{self.port}/status"

        while (time.time() - start_time) < timeout:
            try:
                # Check if process is still running
                if self.process and self.process.poll() is not None:
                    self.logger.error("Appium process terminated unexpectedly")
                    return False
                
                # Try to connect to the server
                response = requests.get(status_url, timeout=2)
                if response.status_code == 200:
                    return True
            except requests.RequestException:
                pass  # Server not ready yet

            time.sleep(1)

        return False

    def _cleanup_process(self):
        """Clean up the process if it exists"""
        if self.process:
            try:
                # Terminate the process group
                os.killpg(os.getpgid(self.process.pid), signal.SIGTERM)
                self.process.wait(timeout=5)
            except (ProcessLookupError, subprocess.TimeoutExpired):
                try:
                    # Force kill if needed
                    os.killpg(os.getpgid(self.process.pid), signal.SIGKILL)
                except ProcessLookupError:
                    pass
            finally:
                self.process = None

    def stop(self) -> bool:
        """Stop the Appium server"""
        with self._lock:
            if not self.is_running:
                self.logger.warning(f"Server for session {self.session_id} is not running")
                return True
            
            try:
                self.logger.info(f"Stopping Appium server for session {self.session_id}")

                self._cleanup_process()
                self.is_running = False
                self.logger.info(f"Appium server stopped successfully")
                return True

            except Exception as e:
                self.logger.error(f"Error stopping Appium server: {str(e)}")
                return False
    
    def is_alive(self) -> bool:
        """Check if the Appium server is running"""
        if not self.process:
            return False

        # Check if process is still running
        if self.process.poll() is not None:
            self.is_running = False
            return False

        # Try to ping the server
        try:
            response = requests.get(f"http://127.0.0.1:{self.port}/status", timeout=2)
            return response.status_code == 200
        except requests.RequestException:
            return False
    
    def get_service_url(self) -> str:
        """Get the service URL for this Appium server"""
        return f"http://127.0.0.1:{self.port}"
    
    def get_info(self) -> Dict[str, Any]:
        """Get information about this server instance"""
        return {
            "session_id": self.session_id,
            "port": self.port,
            "is_running": self.is_running,
            "service_url": self.get_service_url(),
            "log_file": self.log_file,
            "is_alive": self.is_alive()
        }
    
    def __enter__(self):
        """Context manager entry"""
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.stop()