"""
Content Intelligence Platform - Middleware Package

This package contains custom middleware for logging, monitoring, and request processing.
"""

from . import RequestLoggingMiddleware

__all__ = [
    'RequestLoggingMiddleware'
] 