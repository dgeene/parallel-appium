"""
HTTP Gateway Server - FastAPI server that proxies requests to Appium servers
"""

import json
import httpx
import logging
from typing import Dict, Any, Optional
from fastapi import FastAPI, Request, Response, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from .session_pool import SessionPool


class CreateSessionRequest(BaseModel):
    """Request model for creating a new session"""

    capabilities: Dict[str, Any]
    device_udid: Optional[str] = None
    device_name: Optional[str] = None


class AppiumGateway:
    """FastAPI application that acts as a gateway to Appium servers"""

    def __init__(self, session_pool: SessionPool):
        self.session_pool = session_pool
        self.app = FastAPI(title="Appium Gateway Hub", version="1.0.0")
        self.logger = logging.getLogger(__name__)
        self._setup_routes()

    def _setup_routes(self):
        """Setup FastAPI routes"""

        @self.app.get("/")
        async def root():
            """Root endpoint with basic information"""
            return {
                "name": "Appium Gateway Hub",
                "version": "1.0.0",
                "status": "running",
                "sessions": self.session_pool.get_session_count(),
            }

        @self.app.get("/health")
        async def health_check():
            """Health check endpoint"""
            health = self.session_pool.health_check()
            return JSONResponse(content=health)

        @self.app.get("/sessions")
        async def list_sessions():
            """List all active sessions"""
            sessions = self.session_pool.list_sessions()
            return JSONResponse(content={"sessions": sessions})

        @self.app.post("/session")
        async def create_session(request: CreateSessionRequest):
            """Create a new Appium session"""
            try:
                session_id = self.session_pool.create_session(
                    device_udid=request.device_udid, device_name=request.device_name
                )

                if not session_id:
                    raise HTTPException(
                        status_code=503, detail="Unable to create session"
                    )

                # Get session URL
                session_url = self.session_pool.get_session_url(session_id)

                # Forward the session creation request to the actual Appium server
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        f"{session_url}/session",
                        json={"capabilities": request.capabilities},
                        timeout=60.0,
                    )

                if response.status_code != 200:
                    # Clean up the session if Appium server creation failed
                    self.session_pool.delete_session(session_id)
                    raise HTTPException(
                        status_code=response.status_code,
                        detail=f"Failed to create Appium session: {response.text}",
                    )

                # Parse the response to get the actual session ID from Appium
                appium_response = response.json()

                return {
                    "hub_session_id": session_id,
                    "appium_session": appium_response,
                    "service_url": session_url,
                }

            except httpx.RequestError as e:
                self.logger.error(f"Request error creating session: {str(e)}")
                if "session_id" in locals():
                    self.session_pool.delete_session(session_id)
                raise HTTPException(status_code=503, detail="Service unavailable")
            except Exception as e:
                self.logger.error(f"Error creating session: {str(e)}")
                if "session_id" in locals():
                    self.session_pool.delete_session(session_id)
                raise HTTPException(status_code=500, detail="Internal server error")

        @self.app.delete("/session/{session_id}")
        async def delete_session(session_id: str):
            """Delete an Appium session"""
            session = self.session_pool.get_session(session_id)
            if not session:
                raise HTTPException(status_code=404, detail="Session not found")

            # Try to delete session from Appium server first
            try:
                session_url = session.server_manager.get_service_url()
                async with httpx.AsyncClient() as client:
                    # This will fail if there's no active Appium session, but that's OK
                    await client.delete(f"{session_url}/session", timeout=30.0)
            except Exception as e:
                self.logger.warning(f"Could not delete Appium session: {str(e)}")

            # Delete the session from our pool
            if self.session_pool.delete_session(session_id):
                return {"message": "Session deleted successfully"}
            else:
                raise HTTPException(status_code=500, detail="Failed to delete session")

        @self.app.api_route(
            "/session/{session_id}/{path:path}",
            methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
        )
        async def proxy_to_appium(session_id: str, path: str, request: Request):
            """Proxy requests to the appropriate Appium server"""
            session = self.session_pool.get_session(session_id)
            if not session:
                raise HTTPException(status_code=404, detail="Session not found")

            session_url = session.server_manager.get_service_url()
            target_url = f"{session_url}/session/{path}"

            try:
                # Get request body
                body = await request.body()

                # Prepare headers (exclude hop-by-hop headers)
                headers = dict(request.headers)
                excluded_headers = ["host", "content-length", "connection", "upgrade"]
                headers = {
                    k: v
                    for k, v in headers.items()
                    if k.lower() not in excluded_headers
                }

                async with httpx.AsyncClient() as client:
                    response = await client.request(
                        method=request.method,
                        url=target_url,
                        headers=headers,
                        content=body,
                        timeout=60.0,
                    )

                # Return the response from Appium server
                return Response(
                    content=response.content,
                    status_code=response.status_code,
                    headers=dict(response.headers),
                )

            except httpx.RequestError as e:
                self.logger.error(f"Request error proxying to Appium: {str(e)}")
                raise HTTPException(status_code=503, detail="Service unavailable")
            except Exception as e:
                self.logger.error(f"Error proxying request: {str(e)}")
                raise HTTPException(status_code=500, detail="Internal server error")

        @self.app.get("/session/{session_id}/info")
        async def get_session_info(session_id: str):
            """Get information about a specific session"""
            session = self.session_pool.get_session(session_id)
            if not session:
                raise HTTPException(status_code=404, detail="Session not found")

            return {
                "session_id": session_id,
                "port": session.server_manager.port,
                "service_url": session.server_manager.get_service_url(),
                "created_at": session.created_at,
                "last_used": session.last_used,
                "device_udid": session.device_udid,
                "device_name": session.device_name,
                "is_alive": session.server_manager.is_alive(),
                "log_file": session.server_manager.log_file,
            }

    def get_app(self) -> FastAPI:
        """Get the FastAPI application instance"""
        return self.app
