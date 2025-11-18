"""Middleware for tracking API metrics with Prometheus."""
import time
from collections.abc import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.metrics import REQUEST_COUNT, REQUEST_LATENCY


class PrometheusMiddleware(BaseHTTPMiddleware):
    """Middleware to collect Prometheus metrics for all API requests."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Track request metrics."""
        # Start timing
        start_time = time.time()
        
        # Process request
        response = await call_next(request)
        
        # Calculate duration
        duration = time.time() - start_time
        
        # Extract route path (use URL path if route not available)
        path = request.url.path
        if hasattr(request, "scope") and "route" in request.scope:
            route = request.scope.get("route")
            if hasattr(route, "path"):
                path = route.path
        
        method = request.method
        status = response.status_code
        
        # Record metrics
        REQUEST_COUNT.labels(path=path, method=method, status=status).inc()
        REQUEST_LATENCY.labels(path=path, method=method).observe(duration)
        
        return response
