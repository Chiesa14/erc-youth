from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import Optional
import json
import time
from app.db.session import SessionLocal
from app.services.logging_service import LoggingService
import logging

logger = logging.getLogger(__name__)


class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for automatic request logging and activity tracking"""
    
    def __init__(self, app, exclude_paths: Optional[list] = None):
        super().__init__(app)
        self.exclude_paths = exclude_paths or [
            "/docs",
            "/redoc", 
            "/openapi.json",
            "/static",
            "/favicon.ico",
            "/health",
            "/metrics"
        ]
    
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        
        # Skip logging for excluded paths
        if any(request.url.path.startswith(path) for path in self.exclude_paths):
            response = await call_next(request)
            return response
        
        # Get request details
        method = request.method
        path = request.url.path
        query_params = str(request.query_params)
        client_ip = self._get_client_ip(request)
        user_agent = request.headers.get("user-agent", "")
        
        # Try to get user from token if available (simplified approach)
        user = None
        try:
            auth_header = request.headers.get("authorization")
            if auth_header and auth_header.startswith("Bearer "):
                # For now, we'll log the request without user context
                # The actual user logging will happen in the controllers via decorators
                pass
        except Exception as e:
            logger.debug(f"Could not extract user from token: {e}")
        
        # Process the request
        try:
            response = await call_next(request)
            status_code = response.status_code
            success = 200 <= status_code < 400
        except Exception as e:
            status_code = 500
            success = False
            logger.error(f"Request failed: {e}")
            raise
        
        # Calculate response time
        response_time = time.time() - start_time
        
        # Log the request if it's a significant operation
        if self._should_log_request(method, path, status_code):
            await self._log_request(
                method=method,
                path=path,
                status_code=status_code,
                response_time=response_time,
                user=user,
                client_ip=client_ip,
                user_agent=user_agent,
                query_params=query_params,
                success=success
            )
        
        return response
    
    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP address from request"""
        # Check for forwarded headers first
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        # Check for real IP header
        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip
        
        # Fallback to client host
        return request.client.host if request.client else "unknown"
    
    def _should_log_request(self, method: str, path: str, status_code: int) -> bool:
        """Determine if a request should be logged"""
        # Log all non-GET requests
        if method != "GET":
            return True
        
        # Log GET requests to important endpoints
        important_paths = [
            "/api/users",
            "/api/families", 
            "/api/announcements",
            "/api/documents",
            "/api/prayer-chains",
            "/api/feedback"
        ]
        
        if any(path.startswith(api_path) for api_path in important_paths):
            return True
        
        # Log failed requests
        if status_code >= 400:
            return True
        
        return False
    
    async def _log_request(
        self,
        method: str,
        path: str,
        status_code: int,
        response_time: float,
        user,
        client_ip: str,
        user_agent: str,
        query_params: str,
        success: bool
    ):
        """Log the request details"""
        try:
            # For now, we'll just log to console since we don't have user context
            # The actual database logging will happen in controllers via decorators
            logger.info(
                f"Request: {method} {path} - Status: {status_code} - "
                f"Time: {response_time:.3f}s - IP: {client_ip} - "
                f"Success: {success}"
            )
            
        except Exception as e:
            logger.error(f"Failed to log request: {e}")
    
    def _determine_action(self, method: str, path: str) -> str:
        """Determine the action type based on HTTP method and path"""
        if method == "GET":
            return "VIEW"
        elif method == "POST":
            if "login" in path.lower():
                return "LOGIN"
            elif "register" in path.lower():
                return "REGISTER"
            else:
                return "CREATE"
        elif method == "PUT" or method == "PATCH":
            return "UPDATE"
        elif method == "DELETE":
            return "DELETE"
        else:
            return "OTHER"
    
    def _generate_description(self, method: str, path: str, status_code: int, success: bool) -> str:
        """Generate human-readable description for the request"""
        if method == "GET":
            if "users" in path:
                return "Viewed user information"
            elif "families" in path:
                return "Viewed family information"
            elif "announcements" in path:
                return "Viewed announcements"
            elif "documents" in path:
                return "Viewed documents"
            elif "prayer-chains" in path:
                return "Viewed prayer chains"
            elif "feedback" in path:
                return "Viewed feedback"
            else:
                return "Viewed information"
        
        elif method == "POST":
            if "login" in path.lower():
                return "Logged into the system"
            elif "register" in path.lower():
                return "Registered new account"
            elif "users" in path:
                return "Created new user"
            elif "families" in path:
                return "Created new family"
            elif "announcements" in path:
                return "Created new announcement"
            elif "documents" in path:
                return "Uploaded new document"
            elif "prayer-chains" in path:
                return "Created new prayer chain"
            elif "feedback" in path:
                return "Submitted feedback"
            else:
                return "Created new record"
        
        elif method in ["PUT", "PATCH"]:
            if "users" in path:
                return "Updated user profile"
            elif "families" in path:
                return "Updated family information"
            elif "announcements" in path:
                return "Updated announcement"
            elif "documents" in path:
                return "Updated document"
            elif "prayer-chains" in path:
                return "Updated prayer chain"
            else:
                return "Updated record"
        
        elif method == "DELETE":
            if "users" in path:
                return "Deleted user account"
            elif "families" in path:
                return "Deleted family"
            elif "announcements" in path:
                return "Deleted announcement"
            elif "documents" in path:
                return "Deleted document"
            elif "prayer-chains" in path:
                return "Deleted prayer chain"
            else:
                return "Deleted record"
        
        return "Performed action"
    
    def _extract_table_name(self, path: str) -> str:
        """Extract table name from API path"""
        path_parts = path.strip("/").split("/")
        if len(path_parts) >= 2 and path_parts[0] == "api":
            # Convert plural to singular and handle special cases
            table_mapping = {
                "users": "users",
                "families": "families",
                "announcements": "announcements",
                "documents": "family_documents",
                "prayer-chains": "prayer_chains",
                "feedback": "feedback",
                "family-members": "family_members",
                "shared-documents": "shared_documents",
                "recommendations": "recommendations"
            }
            return table_mapping.get(path_parts[1], path_parts[1])
        return "unknown"
