"""Rate limiting configuration and utilities for URL Shortener API

Implements per-endpoint and per-IP rate limiting using slowapi.
Different endpoints have different rate limit tiers based on resource consumption.
"""

from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import Request
from fastapi.responses import JSONResponse


# ============================================================================
# Limiter Setup
# ============================================================================

limiter = Limiter(key_func=get_remote_address)


# ============================================================================
# Rate Limit Tiers
# ============================================================================

# Tier 1: Heavy operations (URL creation)
# 100 requests per 15 minutes = ~6-7 per minute
TIER_1_LIMIT = "100/15 minutes"

# Tier 2: Medium operations (listing, analytics)
# 300 requests per 15 minutes = ~20 per minute
TIER_2_LIMIT = "300/15 minutes"

# Tier 3: Light operations (health check, public redirects)
# 1000 requests per 15 minutes = ~66 per minute
TIER_3_LIMIT = "1000/15 minutes"

# Tier 4: Authentication endpoints
# 20 requests per 5 minutes to prevent brute force
TIER_4_LIMIT = "20/5 minutes"


# ============================================================================
# Rate Limit Error Handler
# ============================================================================

async def rate_limit_error_handler(request: Request, exc: RateLimitExceeded):
    """
    Custom error handler for rate limit exceeded.
    
    Args:
        request: FastAPI request object
        exc: RateLimitExceeded exception
        
    Returns:
        JSONResponse: Rate limit error details
    """
    return JSONResponse(
        status_code=429,
        content={
            "error": "Rate limit exceeded",
            "detail": str(exc.detail),
            "status_code": 429
        }
    )
