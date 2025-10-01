"""
Appium Hub Package - Parallel Appium Server Gateway
"""

from .main import AppiumHub, main
from .session_pool import SessionPool
from .server_manager import AppiumServerManager
from .gateway import AppiumGateway
from .config import HubConfig, DEFAULT_CONFIG

__version__ = "1.0.0"
__all__ = [
    "AppiumHub",
    "SessionPool",
    "AppiumServerManager",
    "AppiumGateway",
    "HubConfig",
    "DEFAULT_CONFIG",
    "main",
]
