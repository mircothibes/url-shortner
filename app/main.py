"""URL Shortener API - Main application file

Production-grade URL shortening service with advanced analytics and click tracking.
"""
from datetime import datetime, timezone
from typing import Optional, List
from uuid import UUID
import secrets

from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.responses import RedirectResponse, JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import func, text
from pydantic import BaseModel

from app.database import SessionLocal
from app.models import User, URL, Click, AuditLog


# ============================================================================
# FastAPI Application Setup
# ============================================================================

app = FastAPI(
    title="URL Shortener API",
    description="Production-grade URL shortening service with advanced analytics and click tracking",
    version="1.0.0",
    contact={
        "name": "Marcos (mircothibes)",
        "url": "https://github.com/mircothibes",
        "email": "mircothibes@gmail.com"
    }
)


# ============================================================================
# Pydantic Models
# ============================================================================

class URLCreateRequest(BaseModel):
    """Request model for creating a shortened URL"""
    original_url: str
    custom_slug: Optional[str] = None
    expires_at: Optional[datetime] = None
    password: Optional[str] = None
    tags: Optional[List[str]] = None
    description: Optional[str] = None


class URLResponse(BaseModel):
    """Response model for URL data"""
    id: int
    short_code: str
    original_url: str
    created_at: datetime
    total_clicks: int
    is_active: bool
    expires_at: Optional[datetime] = None
    description: Optional[str] = None

    class Config:
        from_attributes = True


class AnalyticsResponse(BaseModel):
    """Response model for URL analytics"""
    total_clicks: int
    unique_visitors: int
    top_country: Optional[str] = None
    top_device: Optional[str] = None
    device_breakdown: dict
    country_breakdown: dict


# ============================================================================
# Database Dependencies
# ============================================================================

def get_db():
    """
    Dependency function to get database session.
    
    """
    db = SessionLocal()
    try:        
        yield db
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=f"Database unavailable: {str(e)}"
        )
    finally:
        db.close()


async def get_current_user(
    request: Request,
    db: Session = Depends(get_db)
) -> UUID:
    """
    Verify API key and return authenticated user ID.
    
    Args:
        request: FastAPI request object
        db: Database session
        
    Returns:
        UUID: User ID if authentication successful
        
    Raises:
        HTTPException: If API key is missing, invalid, or user is inactive
    """
    auth_header = request.headers.get("Authorization", "")
    
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing API key")
    
    api_key = auth_header.replace("Bearer ", "")
    user = db.query(User).filter(User.api_key == api_key).first()
    
    if not user:
        raise HTTPException(status_code=401, detail="Invalid API key")
    
    if not user.is_active:
        raise HTTPException(status_code=403, detail="User is inactive")
    
    return user.id


# ============================================================================
# Health Check & Root Endpoints
# ============================================================================

@app.get("/")
async def root():
    """Root endpoint - confirms API is running"""
    return {"message": "API is running"}


@app.get(
    "/health",
    tags=["Health"],
    summary="Health Check",
    description="Verify API status"
)
async def health_check():
    """
    Health check endpoint to verify API status.
    
    Returns:
        dict: API status information
    """
    return JSONResponse(
        status_code=200,
        content={
            "status": "ok",
            "service": "URL Shortener API",
            "version": "1.0.0"
        }
    )


# ============================================================================
# URL Management Endpoints
# ============================================================================

@app.post(
    "/api/v1/urls",
    status_code=201,
    response_model=URLResponse,
    tags=["URLs"],
    summary="Create Shortened URL",
    description="Creates a new shortened URL with unique short code and optional customization"
)
async def create_short_url(
    request: URLCreateRequest,
    db: Session = Depends(get_db),
    user_id: UUID = Depends(get_current_user)
):
    """
    Create a new shortened URL.
    
    Features:
    - Auto-generated or custom short code
    - Optional expiration date
    - Optional password protection
    - Tags and description for organization
    
    Args:
        request: URL creation request data
        db: Database session
        user_id: Authenticated user ID
        
    Returns:
        URLResponse: Created URL data
        
    Raises:
        HTTPException: If URL format is invalid or custom slug already exists
    """
    original_url = request.original_url
    
    # Validate URL format
    if not original_url.startswith(("http://", "https://")):
        raise HTTPException(
            status_code=422,
            detail="Invalid URL format. Must start with http:// or https://"
        )
    
    # Handle custom slug or generate random short code
    if request.custom_slug:
        existing = db.query(URL).filter(URL.short_code == request.custom_slug).first()
        if existing:
            raise HTTPException(status_code=409, detail="Custom slug already exists")
        short_code = request.custom_slug
    else:
        while True:
            short_code = secrets.token_urlsafe(6)[:8]
            existing = db.query(URL).filter(URL.short_code == short_code).first()
            if not existing:
                break
    
    # Create URL record
    url = URL(
        short_code=short_code,
        original_url=original_url,
        user_id=user_id,
        expires_at=request.expires_at,
        description=request.description,
        tags=request.tags or []
    )
    
    # Hash password if provided
    if request.password:
        from passlib.context import CryptContext
        pwd_context = CryptContext(schemes=["bcrypt"])
        url.password_hash = pwd_context.hash(request.password)
    
    db.add(url)
    db.commit()
    db.refresh(url)
    
    # Log audit event
    audit = AuditLog(
        user_id=user_id,
        action="CREATE_URL",
        resource_type="URL",
        resource_id=str(url.id),
        ip_address=request.client.host if hasattr(request, 'client') else None,
        details={"short_code": short_code}
    )
    db.add(audit)
    db.commit()
    
    return url


@app.get(
    "/api/v1/urls",
    response_model=List[URLResponse],
    tags=["URLs"],
    summary="List User's URLs",
    description="Returns all active shortened URLs created by the authenticated user"
)
async def list_user_urls(
    db: Session = Depends(get_db),
    user_id: UUID = Depends(get_current_user)
):
    """
    List all shortened URLs for the authenticated user.
    
    Returns:
        List[URLResponse]: User's active URLs, ordered by creation date (newest first)
    """
    urls = db.query(URL).filter(
        URL.user_id == user_id,
        URL.is_active == True
    ).order_by(URL.created_at.desc()).all()
    return urls


@app.get(
    "/api/v1/urls/{url_id}",
    response_model=URLResponse,
    tags=["URLs"],
    summary="Get URL Details",
    description="Retrieves detailed information about a specific shortened URL"
)
async def get_url_details(
    url_id: int,
    db: Session = Depends(get_db),
    user_id: UUID = Depends(get_current_user)
):
    """
    Get detailed information about a specific shortened URL.
    
    Args:
        url_id: URL record ID
        db: Database session
        user_id: Authenticated user ID
        
    Returns:
        URLResponse: URL details
        
    Raises:
        HTTPException: If URL not found or doesn't belong to user
    """
    url = db.query(URL).filter(
        URL.id == url_id,
        URL.user_id == user_id
    ).first()
    
    if not url:
        raise HTTPException(status_code=404, detail="URL not found")
    
    return url


@app.delete(
    "/api/v1/urls/{url_id}",
    status_code=204,
    tags=["URLs"],
    summary="Delete URL",
    description="Soft deletes a shortened URL by marking it as inactive"
)
async def delete_url(
    url_id: int,
    db: Session = Depends(get_db),
    user_id: UUID = Depends(get_current_user)
):
    """
    Delete a shortened URL (soft delete).
    
    The URL is marked as inactive rather than permanently deleted,
    preserving analytics history.
    
    Args:
        url_id: URL record ID
        db: Database session
        user_id: Authenticated user ID
        
    Raises:
        HTTPException: If URL not found or doesn't belong to user
    """
    url = db.query(URL).filter(
        URL.id == url_id,
        URL.user_id == user_id
    ).first()
    
    if not url:
        raise HTTPException(status_code=404, detail="URL not found")
    
    url.is_active = False
    db.commit()
    
    # Log audit event
    audit = AuditLog(
        user_id=user_id,
        action="DELETE_URL",
        resource_type="URL",
        resource_id=str(url_id),
        details={"short_code": url.short_code}
    )
    db.add(audit)
    db.commit()


# ============================================================================
# Analytics Endpoints
# ============================================================================

@app.get(
    "/api/v1/urls/{url_id}/analytics",
    response_model=AnalyticsResponse,
    tags=["Analytics"],
    summary="Get URL Analytics",
    description="Retrieves comprehensive analytics and statistics for a specific shortened URL"
)
async def get_analytics(
    url_id: int,
    db: Session = Depends(get_db),
    user_id: UUID = Depends(get_current_user)
):
    """
    Get detailed analytics for a shortened URL.
    
    Includes:
    - Total click count
    - Unique visitor count (by IP)
    - Top country and device
    - Device type breakdown
    - Geographic distribution
    
    Args:
        url_id: URL record ID
        db: Database session
        user_id: Authenticated user ID
        
    Returns:
        AnalyticsResponse: Analytics data
        
    Raises:
        HTTPException: If URL not found or doesn't belong to user
    """
    url = db.query(URL).filter(
        URL.id == url_id,
        URL.user_id == user_id
    ).first()
    
    if not url:
        raise HTTPException(status_code=404, detail="URL not found")
    
    # Fetch all clicks for this URL
    clicks = db.query(Click).filter(Click.url_id == url_id).all()
    
    # Build device and country breakdowns
    device_breakdown = {}
    country_breakdown = {}
    
    for click in clicks:
        if click.device_type:
            device_breakdown[click.device_type] = device_breakdown.get(click.device_type, 0) + 1
        if click.country:
            country_breakdown[click.country] = country_breakdown.get(click.country, 0) + 1
    
    # Get top values
    top_country = max(country_breakdown, key=country_breakdown.get) if country_breakdown else None
    top_device = max(device_breakdown, key=device_breakdown.get) if device_breakdown else None
    
    # Count unique visitors by IP
    unique_ips = db.query(func.count(func.distinct(Click.ip_address))).filter(
        Click.url_id == url_id
    ).scalar() or 0
    
    return {
        "total_clicks": url.total_clicks,
        "unique_visitors": unique_ips,
        "top_country": top_country,
        "top_device": top_device,
        "device_breakdown": device_breakdown,
        "country_breakdown": country_breakdown
    }


# ============================================================================
# Redirect Endpoint (Catch-all)
# ============================================================================

@app.get(
    "/{short_code}",
    tags=["Redirects"],
    summary="Redirect to Original URL",
    description="Redirects to the original URL and records click analytics data"
)
async def redirect_to_original(
    short_code: str,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Redirect to the original URL for a given short code.
    
    This endpoint automatically:
    - Records the click in analytics
    - Captures IP address
    - Logs user agent and referrer
    - Increments click counter
    
    Args:
        short_code: Short code of the URL
        request: FastAPI request object
        db: Database session
        
    Returns:
        RedirectResponse: Redirect to original URL
        
    Raises:
        HTTPException: If URL not found, expired, or password required
    """
    url = db.query(URL).filter(URL.short_code == short_code).first()
    
    if not url:
        raise HTTPException(status_code=404, detail="URL not found")
    
    if not url.is_active:
        raise HTTPException(status_code=410, detail="URL is no longer available")
    
    # Check expiration
    if url.expires_at and url.expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=410, detail="URL has expired")
    
    # Check password if required
    if url.password_hash:
        password = request.query_params.get("password")
        if not password:
            raise HTTPException(status_code=401, detail="Password required")
        
        from passlib.context import CryptContext
        pwd_context = CryptContext(schemes=["bcrypt"])
        if not pwd_context.verify(password, url.password_hash):
            raise HTTPException(status_code=401, detail="Invalid password")
    
    # Record click
    click = Click(
        url_id=url.id,
        ip_address=str(request.client.host) if request.client else None,
        user_agent=request.headers.get("user-agent"),
        referrer=request.headers.get("referer")
    )
    db.add(click)
    url.total_clicks += 1
    db.commit()
    
    return RedirectResponse(url=url.original_url, status_code=307)


# ============================================================================
# Exception Handlers
# ============================================================================

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Custom exception handler for HTTP exceptions"""
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail, "status_code": exc.status_code}
    )


# ============================================================================
# Local Development
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
