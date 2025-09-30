"""
Session Pool - Manages multiple Appium server instances and session allocation
"""
import uuid
import time
import logging
import threading
from typing import Dict, Optional, List, Set
from dataclasses import dataclass
from .server_manager import AppiumServerManager


@dataclass
class SessionInfo:
    """Information about an active session"""
    session_id: str
    server_manager: AppiumServerManager
    created_at: float
    last_used: float
    device_udid: Optional[str] = None
    device_name: Optional[str] = None


class SessionPool:
    """Manages a pool of Appium server instances for parallel testing"""
    
    def __init__(self, 
                 port_range_start: int = 4723,
                 port_range_end: int = 4773,
                 max_sessions: int = 10,
                 session_timeout: int = 1800,  # 30 minutes
                 log_dir: str = "logs"):
        
        self.port_range_start = port_range_start
        self.port_range_end = port_range_end
        self.max_sessions = max_sessions
        self.session_timeout = session_timeout
        self.log_dir = log_dir
        
        # Thread-safe data structures
        self._lock = threading.RLock()
        self._sessions: Dict[str, SessionInfo] = {}
        self._used_ports: Set[int] = set()
        self._available_ports = list(range(port_range_start, port_range_end + 1))
        
        # Setup logging
        self.logger = logging.getLogger(__name__)
        
        # Start cleanup thread
        self._cleanup_thread = threading.Thread(target=self._cleanup_expired_sessions, daemon=True)
        self._cleanup_thread.start()
    
    def _get_next_available_port(self) -> Optional[int]:
        """Get the next available port from the range"""
        for port in self._available_ports:
            if port not in self._used_ports:
                return port
        return None
    
    def create_session(self, device_udid: Optional[str] = None, device_name: Optional[str] = None) -> Optional[str]:
        """Create a new session and start an Appium server"""
        with self._lock:
            if len(self._sessions) >= self.max_sessions:
                self.logger.warning(f"Maximum sessions ({self.max_sessions}) reached")
                return None
            
            # Get next available port
            port = self._get_next_available_port()
            if port is None:
                self.logger.error("No available ports in the specified range")
                return None
            
            # Generate session ID
            session_id = str(uuid.uuid4())
            
            try:
                # Create and start server manager
                server_manager = AppiumServerManager(
                    port=port,
                    session_id=session_id,
                    log_dir=self.log_dir
                )
                
                if not server_manager.start():
                    self.logger.error(f"Failed to start server for session {session_id}")
                    return None
                
                # Mark port as used
                self._used_ports.add(port)
                
                # Create session info
                session_info = SessionInfo(
                    session_id=session_id,
                    server_manager=server_manager,
                    created_at=time.time(),
                    last_used=time.time(),
                    device_udid=device_udid,
                    device_name=device_name
                )
                
                self._sessions[session_id] = session_info
                
                self.logger.info(f"Created session {session_id} on port {port}")
                return session_id
                
            except Exception as e:
                self.logger.error(f"Error creating session: {str(e)}")
                if port in self._used_ports:
                    self._used_ports.remove(port)
                return None
    
    def get_session(self, session_id: str) -> Optional[SessionInfo]:
        """Get session information"""
        with self._lock:
            session = self._sessions.get(session_id)
            if session:
                session.last_used = time.time()
            return session
    
    def get_session_url(self, session_id: str) -> Optional[str]:
        """Get the Appium server URL for a session"""
        session = self.get_session(session_id)
        if session:
            return session.server_manager.get_service_url()
        return None
    
    def delete_session(self, session_id: str) -> bool:
        """Delete a session and stop its Appium server"""
        with self._lock:
            session = self._sessions.get(session_id)
            if not session:
                self.logger.warning(f"Session {session_id} not found")
                return False
            
            try:
                # Stop the server
                session.server_manager.stop()
                
                # Free the port
                port = session.server_manager.port
                if port in self._used_ports:
                    self._used_ports.remove(port)
                
                # Remove session
                del self._sessions[session_id]
                
                self.logger.info(f"Deleted session {session_id}")
                return True
                
            except Exception as e:
                self.logger.error(f"Error deleting session {session_id}: {str(e)}")
                return False
    
    def list_sessions(self) -> List[Dict]:
        """List all active sessions"""
        with self._lock:
            sessions = []
            for session_id, session_info in self._sessions.items():
                sessions.append({
                    "session_id": session_id,
                    "port": session_info.server_manager.port,
                    "service_url": session_info.server_manager.get_service_url(),
                    "created_at": session_info.created_at,
                    "last_used": session_info.last_used,
                    "device_udid": session_info.device_udid,
                    "device_name": session_info.device_name,
                    "is_alive": session_info.server_manager.is_alive(),
                    "log_file": session_info.server_manager.log_file
                })
            return sessions
    
    def get_session_count(self) -> int:
        """Get the number of active sessions"""
        with self._lock:
            return len(self._sessions)
    
    def shutdown_all(self) -> None:
        """Shutdown all sessions"""
        with self._lock:
            self.logger.info("Shutting down all sessions...")
            session_ids = list(self._sessions.keys())
            for session_id in session_ids:
                self.delete_session(session_id)
            self.logger.info("All sessions shut down")
    
    def _cleanup_expired_sessions(self) -> None:
        """Background thread to cleanup expired sessions"""
        while True:
            try:
                time.sleep(60)  # Check every minute
                current_time = time.time()
                
                with self._lock:
                    expired_sessions = []
                    for session_id, session_info in self._sessions.items():
                        if current_time - session_info.last_used > self.session_timeout:
                            expired_sessions.append(session_id)
                    
                    for session_id in expired_sessions:
                        self.logger.info(f"Cleaning up expired session {session_id}")
                        self.delete_session(session_id)
                        
            except Exception as e:
                self.logger.error(f"Error in cleanup thread: {str(e)}")
    
    def health_check(self) -> Dict:
        """Perform health check on all sessions"""
        with self._lock:
            healthy_sessions = 0
            unhealthy_sessions = []
            
            for session_id, session_info in self._sessions.items():
                if session_info.server_manager.is_alive():
                    healthy_sessions += 1
                else:
                    unhealthy_sessions.append(session_id)
            
            return {
                "total_sessions": len(self._sessions),
                "healthy_sessions": healthy_sessions,
                "unhealthy_sessions": unhealthy_sessions,
                "available_ports": len(self._available_ports) - len(self._used_ports),
                "used_ports": list(self._used_ports)
            }
    
    def __enter__(self):
        """Context manager entry"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.shutdown_all()