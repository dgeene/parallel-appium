"""
Main Application - Appium Gateway Hub
"""
import logging
import signal
import sys
import asyncio
import uvicorn
from typing import Optional
from .session_pool import SessionPool
from .gateway import AppiumGateway


class AppiumHub:
    """Main Appium Hub application"""
    
    def __init__(self, 
                 host: str = "0.0.0.0",
                 port: int = 4444,
                 appium_port_start: int = 4723,
                 appium_port_end: int = 4773,
                 max_sessions: int = 10,
                 session_timeout: int = 1800,
                 log_dir: str = "logs",
                 log_level: str = "INFO"):
        
        self.host = host
        self.port = port
        self.log_level = log_level
        
        # Setup logging
        self._setup_logging()
        self.logger = logging.getLogger(__name__)
        
        # Initialize session pool
        self.session_pool = SessionPool(
            port_range_start=appium_port_start,
            port_range_end=appium_port_end,
            max_sessions=max_sessions,
            session_timeout=session_timeout,
            log_dir=log_dir
        )
        
        # Initialize gateway
        self.gateway = AppiumGateway(self.session_pool)
        self.app = self.gateway.get_app()
        
        # Setup signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        self.logger.info(f"Appium Hub initialized on {host}:{port}")
        self.logger.info(f"Appium port range: {appium_port_start}-{appium_port_end}")
        self.logger.info(f"Max sessions: {max_sessions}")
    
    def _setup_logging(self):
        """Setup logging configuration"""
        logging.basicConfig(
            level=getattr(logging, self.log_level.upper()),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(sys.stdout),
                logging.FileHandler('appium_hub.log')
            ]
        )
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        self.logger.info(f"Received signal {signum}, shutting down...")
        self.shutdown()
        sys.exit(0)
    
    def shutdown(self):
        """Shutdown the hub gracefully"""
        self.logger.info("Shutting down Appium Hub...")
        self.session_pool.shutdown_all()
        self.logger.info("Appium Hub shutdown complete")
    
    def run(self):
        """Run the Appium Hub server"""
        self.logger.info(f"Starting Appium Hub on {self.host}:{self.port}")
        
        try:
            uvicorn.run(
                self.app,
                host=self.host,
                port=self.port,
                log_level=self.log_level.lower(),
                access_log=True
            )
        except Exception as e:
            self.logger.error(f"Error running server: {str(e)}")
            self.shutdown()
            raise
    
    async def run_async(self):
        """Run the Appium Hub server asynchronously"""
        self.logger.info(f"Starting Appium Hub on {self.host}:{self.port}")
        
        config = uvicorn.Config(
            self.app,
            host=self.host,
            port=self.port,
            log_level=self.log_level.lower(),
            access_log=True
        )
        server = uvicorn.Server(config)
        
        try:
            await server.serve()
        except Exception as e:
            self.logger.error(f"Error running server: {str(e)}")
            self.shutdown()
            raise


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Appium Gateway Hub")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    parser.add_argument("--port", type=int, default=4444, help="Port to bind to")
    parser.add_argument("--appium-port-start", type=int, default=4723, 
                       help="Start of Appium port range")
    parser.add_argument("--appium-port-end", type=int, default=4773,
                       help="End of Appium port range")
    parser.add_argument("--max-sessions", type=int, default=10,
                       help="Maximum number of concurrent sessions")
    parser.add_argument("--session-timeout", type=int, default=1800,
                       help="Session timeout in seconds")
    parser.add_argument("--log-dir", default="logs", help="Log directory")
    parser.add_argument("--log-level", default="INFO", 
                       choices=["DEBUG", "INFO", "WARNING", "ERROR"],
                       help="Log level")
    
    args = parser.parse_args()
    
    hub = AppiumHub(
        host=args.host,
        port=args.port,
        appium_port_start=args.appium_port_start,
        appium_port_end=args.appium_port_end,
        max_sessions=args.max_sessions,
        session_timeout=args.session_timeout,
        log_dir=args.log_dir,
        log_level=args.log_level
    )
    
    try:
        hub.run()
    except KeyboardInterrupt:
        hub.shutdown()
    except Exception as e:
        print(f"Fatal error: {str(e)}")
        hub.shutdown()
        sys.exit(1)


if __name__ == "__main__":
    main()