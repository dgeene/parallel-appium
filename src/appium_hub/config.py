"""
Configuration module for Appium Hub
"""
import os
from typing import Dict, Any
from pydantic import BaseModel


class HubConfig(BaseModel):
    """Configuration for the Appium Hub"""
    
    # Server settings
    host: str = "0.0.0.0"
    port: int = 4444
    
    # Appium server settings
    appium_port_start: int = 4723
    appium_port_end: int = 4773
    max_sessions: int = 10
    session_timeout: int = 1800  # 30 minutes
    
    # Logging settings
    log_dir: str = "logs"
    log_level: str = "INFO"
    
    # Health check settings
    health_check_interval: int = 60  # seconds
    
    @classmethod
    def from_env(cls) -> "HubConfig":
        """Create configuration from environment variables"""
        return cls(
            host=os.getenv("HUB_HOST", "0.0.0.0"),
            port=int(os.getenv("HUB_PORT", "4444")),
            appium_port_start=int(os.getenv("APPIUM_PORT_START", "4723")),
            appium_port_end=int(os.getenv("APPIUM_PORT_END", "4773")),
            max_sessions=int(os.getenv("MAX_SESSIONS", "10")),
            session_timeout=int(os.getenv("SESSION_TIMEOUT", "1800")),
            log_dir=os.getenv("LOG_DIR", "logs"),
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            health_check_interval=int(os.getenv("HEALTH_CHECK_INTERVAL", "60"))
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return self.model_dump()


# Default configuration
DEFAULT_CONFIG = HubConfig()