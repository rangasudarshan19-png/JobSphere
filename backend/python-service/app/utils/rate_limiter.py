"""
Rate limiting configuration using slowapi
"""
from slowapi import Limiter
from slowapi.util import get_remote_address
from fastapi import Request


def get_user_identifier(request: Request) -> str:
    """
    Get identifier for rate limiting
    Prefer user ID if authenticated, otherwise use IP
    """
    # Try to get user from request state (set by auth dependency)
    if hasattr(request.state, "user") and request.state.user:
        return f"user_{request.state.user.id}"
    
    # Fall back to IP address
    return get_remote_address(request)


# Create limiter instance
limiter = Limiter(
    key_func=get_user_identifier,
    default_limits=["200/minute", "2000/hour"]  # Global limits
)


# Custom limits for specific endpoints
AUTH_LIMITS = "5/minute"  # Login/register attempts
AI_LIMITS = "10/minute"  # AI features
SCRAPER_LIMITS = "20/minute"  # Job scraping
