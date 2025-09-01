"""
Content Intelligence Platform - Request Logging Middleware

Provides structured logging for all HTTP requests with performance metrics.
"""

import time
import json
import structlog
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

logger = structlog.get_logger()

class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for logging HTTP requests with structured data"""
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and log details"""
        start_time = time.time()
        
        # Extract request details
        request_id = self._generate_request_id()
        method = request.method
        url = str(request.url)
        client_ip = self._get_client_ip(request)
        user_agent = request.headers.get("user-agent", "")
        
        # Log request start
        logger.info(
            "Request started",
            request_id=request_id,
            method=method,
            url=url,
            client_ip=client_ip,
            user_agent=user_agent,
            headers=self._sanitize_headers(request.headers)
        )
        
        # Process request
        try:
            response = await call_next(request)
            
            # Calculate processing time
            process_time = time.time() - start_time
            
            # Log successful response
            logger.info(
                "Request completed",
                request_id=request_id,
                method=method,
                url=url,
                status_code=response.status_code,
                process_time_ms=round(process_time * 1000, 2),
                response_size=self._get_response_size(response)
            )
            
            # Add response headers for tracking
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Process-Time"] = str(round(process_time * 1000, 2))
            
            return response
            
        except Exception as e:
            # Calculate processing time
            process_time = time.time() - start_time
            
            # Log error
            logger.error(
                "Request failed",
                request_id=request_id,
                method=method,
                url=url,
                error_type=type(e).__name__,
                error_message=str(e),
                process_time_ms=round(process_time * 1000, 2)
            )
            
            # Re-raise the exception
            raise
    
    def _generate_request_id(self) -> str:
        """Generate unique request ID"""
        import uuid
        return str(uuid.uuid4())
    
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
        
        # Fall back to client host
        return request.client.host if request.client else "unknown"
    
    def _sanitize_headers(self, headers) -> dict:
        """Sanitize headers for logging (remove sensitive data)"""
        sensitive_headers = {
            "authorization", "cookie", "x-api-key", "x-auth-token",
            "x-forwarded-for", "x-real-ip"
        }
        
        sanitized = {}
        for key, value in headers.items():
            if key.lower() in sensitive_headers:
                sanitized[key] = "[REDACTED]"
            else:
                sanitized[key] = value
        
        return sanitized
    
    def _get_response_size(self, response: Response) -> int:
        """Get response size in bytes"""
        try:
            # Try to get content length from headers
            content_length = response.headers.get("content-length")
            if content_length:
                return int(content_length)
            
            # For streaming responses, we can't determine size easily
            return -1
        except (ValueError, TypeError):
            return -1 