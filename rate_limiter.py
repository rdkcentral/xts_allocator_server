"""
Rate limiting middleware for API protection.

Implements simple in-memory rate limiting using a sliding window approach.
For production, consider Redis-backed rate limiting for distributed deployments.
"""

from datetime import datetime, timedelta, timezone
from collections import defaultdict, deque
from functools import wraps
from sanic.response import json
from logging_config import get_logger

logger = get_logger()


class RateLimiter:
    """
    In-memory rate limiter using sliding window algorithm.
    
    Tracks requests per identifier (IP or user) within a time window.
    """
    
    def __init__(self):
        # Storage: identifier -> deque of request timestamps
        self.requests = defaultdict(deque)
        self.cleanup_counter = 0
    
    def is_allowed(self, identifier, max_requests, window_seconds):
        """
        Check if request is allowed under rate limit.
        
        Args:
            identifier (str): Unique identifier (IP address, user email, API key)
            max_requests (int): Maximum requests allowed in window
            window_seconds (int): Time window in seconds
            
        Returns:
            tuple: (allowed: bool, remaining: int, reset_time: datetime)
        """
        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(seconds=window_seconds)
        
        # Get request history for this identifier
        request_times = self.requests[identifier]
        
        # Remove old requests outside the window
        while request_times and request_times[0] < cutoff:
            request_times.popleft()
        
        # Check if under limit
        current_count = len(request_times)
        allowed = current_count < max_requests
        
        if allowed:
            # Record this request
            request_times.append(now)
            remaining = max_requests - current_count - 1
        else:
            remaining = 0
        
        # Calculate reset time (when oldest request expires)
        if request_times:
            reset_time = request_times[0] + timedelta(seconds=window_seconds)
        else:
            reset_time = now + timedelta(seconds=window_seconds)
        
        # Periodic cleanup of empty identifiers (every 100 checks)
        self.cleanup_counter += 1
        if self.cleanup_counter >= 100:
            self._cleanup_empty_identifiers()
            self.cleanup_counter = 0
        
        return allowed, remaining, reset_time
    
    def _cleanup_empty_identifiers(self):
        """Remove identifiers with no recent requests (memory cleanup)."""
        empty_identifiers = [
            identifier for identifier, times in self.requests.items()
            if len(times) == 0
        ]
        for identifier in empty_identifiers:
            del self.requests[identifier]
    
    def reset(self, identifier=None):
        """Reset rate limit for identifier or all identifiers."""
        if identifier:
            if identifier in self.requests:
                del self.requests[identifier]
        else:
            self.requests.clear()


# Global rate limiter instance
_rate_limiter = RateLimiter()


def rate_limit(max_requests=100, window_seconds=60, identifier_fn=None):
    """
    Decorator to apply rate limiting to route handlers.
    
    Args:
        max_requests (int): Maximum requests allowed in window (default: 100)
        window_seconds (int): Time window in seconds (default: 60)
        identifier_fn (callable): Function to extract identifier from request
                                 (default: uses IP address)
    
    Example:
        @rate_limit(max_requests=10, window_seconds=60)
        async def my_route(request):
            return json({"message": "success"})
    """
    def decorator(handler):
        @wraps(handler)
        async def wrapper(request, *args, **kwargs):
            # Get identifier (IP by default, or custom function)
            if identifier_fn:
                identifier = identifier_fn(request)
            else:
                # Use IP address from request
                identifier = request.ip
                # If behind proxy, use X-Forwarded-For
                if "X-Forwarded-For" in request.headers:
                    identifier = request.headers["X-Forwarded-For"].split(",")[0].strip()
            
            # Check rate limit
            allowed, remaining, reset_time = _rate_limiter.is_allowed(
                identifier, max_requests, window_seconds
            )
            
            if not allowed:
                logger.warning(
                    f"Rate limit exceeded for {identifier}: "
                    f"{max_requests} requests per {window_seconds}s"
                )
                return json({
                    "error": "Rate limit exceeded",
                    "message": f"Maximum {max_requests} requests per {window_seconds} seconds",
                    "retry_after": int((reset_time - datetime.now(timezone.utc)).total_seconds())
                }, status=429, headers={
                    "X-RateLimit-Limit": str(max_requests),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": reset_time.isoformat(),
                    "Retry-After": str(int((reset_time - datetime.now(timezone.utc)).total_seconds()))
                })
            
            # Add rate limit headers to response
            response = await handler(request, *args, **kwargs)
            
            # Add headers if response supports it
            if hasattr(response, 'headers'):
                response.headers["X-RateLimit-Limit"] = str(max_requests)
                response.headers["X-RateLimit-Remaining"] = str(remaining)
                response.headers["X-RateLimit-Reset"] = reset_time.isoformat()
            
            return response
        
        return wrapper
    return decorator


def get_rate_limiter():
    """Get the global rate limiter instance (for testing/admin purposes)."""
    return _rate_limiter


def user_email_identifier(request):
    """Extract user email from request JSON for rate limiting."""
    try:
        data = request.json
        if data and "user" in data and "email" in data["user"]:
            return data["user"]["email"]
    except Exception:
        # Malformed body / non-JSON / missing keys — fall through to IP-based identification.
        pass
    return request.ip
