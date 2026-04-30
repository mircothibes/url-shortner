"""CORS configuration for URL Shortener API

Handles Cross-Origin Resource Sharing with different rules
for development and production environments.
"""

import os
from typing import List


# ============================================================================
# Environment Detection
# ============================================================================

ENVIRONMENT = os.getenv("ENVIRONMENT", "development").lower()
IS_PRODUCTION = ENVIRONMENT == "production"


# ============================================================================
# CORS Origins Configuration
# ============================================================================

# Development origins (allow multiple dev servers)
DEV_ORIGINS = [
    "http://localhost:3000",      # React dev server (default)
    "http://localhost:5173",      # Vite dev server
    "http://127.0.0.1:3000",      # Alternative localhost format
    "http://127.0.0.1:5173",      # Alternative localhost format
]

# Production origins (to be set via environment variables)
# Example: CORS_ALLOWED_ORIGINS="https://mydomain.com,https://app.mydomain.com"
PROD_ORIGINS = [
    origin.strip()
    for origin in os.getenv("CORS_ALLOWED_ORIGINS", "").split(",")
    if origin.strip()
]

# Select origins based on environment
ALLOWED_ORIGINS = DEV_ORIGINS if not IS_PRODUCTION else PROD_ORIGINS


# ============================================================================
# CORS Methods & Headers Configuration
# ============================================================================

# HTTP methods allowed from frontend
ALLOWED_METHODS = [
    "GET",
    "POST",
    "PUT",
    "DELETE",
    "OPTIONS",
    "PATCH",
]

# Request headers that frontend can send
ALLOWED_HEADERS = [
    "Content-Type",
    "Authorization",
    "Accept",
    "Origin",
    "X-Requested-With",
]

# Response headers exposed to frontend JavaScript
EXPOSE_HEADERS = [
    "Content-Type",
    "X-RateLimit-Limit",
    "X-RateLimit-Remaining",
    "X-RateLimit-Reset",
]


# ============================================================================
# CORS Configuration Dictionary
# ============================================================================

def get_cors_config() -> dict:
    """
    Get CORS configuration dictionary for FastAPI middleware.
    
    Returns:
        dict: Configuration ready to pass to CORSMiddleware
    """
    return {
        "allow_origins": ALLOWED_ORIGINS,
        "allow_credentials": True,  # Allow cookies + auth headers
        "allow_methods": ALLOWED_METHODS,
        "allow_headers": ALLOWED_HEADERS,
        "expose_headers": EXPOSE_HEADERS,
        "max_age": 600,  # 10 minutes - preflight cache duration
    }


# ============================================================================
# Validation & Debugging
# ============================================================================

def validate_cors_config() -> None:
    """
    Validate CORS configuration and log warnings if needed.
    Useful for debugging CORS issues in development.
    """
    if not ALLOWED_ORIGINS:
        if IS_PRODUCTION:
            raise ValueError(
                "PRODUCTION mode but no CORS_ALLOWED_ORIGINS set! "
                "Set environment variable: CORS_ALLOWED_ORIGINS=https://yourdomain.com"
            )
        else:
            print("⚠️  DEVELOPMENT: Using default localhost origins")
    
    print(f"✅ CORS Enabled for: {', '.join(ALLOWED_ORIGINS)}")
    print(f"   Environment: {ENVIRONMENT.upper()}")
    print(f"   Methods: {', '.join(ALLOWED_METHODS)}")
