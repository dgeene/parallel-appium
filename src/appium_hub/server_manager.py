"""
Appium Server Manager - Manages individual Appium server instances
"""
import os
import time
import logging
import threading
from typing import Optional, Dict, Any
from appium.webdriver.appium_service import AppiumService
from appium.webdriver.appium_service_builder import AppiumServiceBuilder


class AppiumServerManager:
    """Manages a single Appium server instance with unique port and log file"""
    
    def __init__(self, port: int, session_id: str, log_dir: str = "logs"):
        self.port = port
        self.session_id = session_id
        self.log_dir = log_dir
        self.service: Optional[AppiumService] = None
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
                
                # Build the Appium service
                builder = AppiumServiceBuilder()
                builder.with_ip_address("127.0.0.1")
                builder.with_port(self.port)
                builder.with_log_file(self.log_file)
                
                # Additional Appium server arguments
                builder.with_arguments([
                    "--session-override",  # Allow session override
                    "--log-timestamp",     # Add timestamps to logs
                    "--log-no-colors",     # Disable colors in logs for file output
                    "--relaxed-security",  # Allow relaxed security for testing
                ])
                
                self.service = AppiumService.create_service(builder)
                self.service.start()
                
                # Wait for service to be ready
                start_time = time.time()
                while not self.service.is_running and (time.time() - start_time) < timeout:
                    time.sleep(1)
                
                if self.service.is_running:
                    self.is_running = True
                    self.logger.info(f"Appium server started successfully on port {self.port}")
                    return True
                else:
                    self.logger.error(f"Failed to start Appium server on port {self.port} within {timeout}s")
                    return False
                    
            except Exception as e:
                self.logger.error(f"Error starting Appium server: {str(e)}")
                return False
    
    def stop(self) -> bool:
        """Stop the Appium server"""
        with self._lock:
            if not self.is_running:
                self.logger.warning(f"Server for session {self.session_id} is not running")
                return True
            
            try:
                self.logger.info(f"Stopping Appium server for session {self.session_id}")
                
                if self.service:
                    self.service.stop()
                    self.is_running = False
                    self.logger.info(f"Appium server stopped successfully")
                    return True
                else:
                    self.logger.warning("No service instance found to stop")
                    return False
                    
            except Exception as e:
                self.logger.error(f"Error stopping Appium server: {str(e)}")
                return False
    
    def is_alive(self) -> bool:
        """Check if the Appium server is running"""
        if not self.service:
            return False
        return self.service.is_running
    
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