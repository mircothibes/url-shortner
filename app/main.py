"""
URL Shortener API - Main application file
Production-ready FastAPI application
"""

from datetime import datetime, timezone
from typing import Optional, List
from uuid import UUID
import uuid
import secrets

from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel

from app.database import SessionLocal, engine
from app.models import Base, User, URL, Click, AuditLog

# Create all tables on startup
Base.metadata.create_all(bind=engine)

# ============================================================================
# APPLICATION
# ============================================================================

app = FastAPI(
    title="URL Shortener API",
    description="Production-grade URL shortening service with analytics",
    version="1.0.0",
)

# ============================================================================
# REQUEST MODELS (Pydantic)
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
    """Response model for URL"""
    id: int
    short_code: str
    original_url: str
    created_at: datetime
    clicks_total: int
    is_active: bool
    expires_at: Optional[datetime] = None
    description: Optional[str] = None

    class Config:
        from_attributes = True


class AnalyticsResponse(BaseModel):
    """Response model for analytics"""
    total_clicks: int
    unique_visitors: int
    top_country: Optional[str] = None
    top_device: Optional[str] = None
    device_breakdown: dict
    country_breakdown: dict


# ============================================================================
# DEPENDENCIES
# ============================================================================

def get_db():
    """Dependency to get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


async def get_current_user(
    request: Request,
    db: Session = Depends(get_db)
) -> UUID:
    """Extract API key from Authorization header and return user_id"""
    auth_header = request.headers.get("Authorization", "")

    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing API key")

    api_key = auth_header.replace("Bearer ", "")

    # Query user from database by API key
    user = db.query(User).filter(User.api_key == api_key).first()

    if not user:
        raise HTTPException(status_code=401, detail="Invalid API key")

    if not user.is_active:
        raise HTTPException(status_code=403, detail="User is inactive")

    return user.id

# ============================================================================
# ROUTES - HEALTH CHECK
# ============================================================================

@app.get("/health")
async def health_check(db: Session = Depends(get_db)):
    """Health check endpoint"""
    try:
        db.execute("SELECT 1")
        return {
            "status": "ok",
            "service": "URL Shortener API",
            "database": "connected",
            "version": "1.0.0"
        }
    except Exception as e:
        return {
            "status": "error",
            "database": str(e),
        }

# ============================================================================
# ROUTES - CREATE SHORT URL
# ============================================================================

@app.post("/api/v1/urls", status_code=201, response_model=URLResponse)
async def create_short_url(
    request: URLCreateRequest,
    db: Session = Depends(get_db),
    user_id: UUID = Depends(get_current_user),
):
    """Create a new shortened URL"""

    # Validate URL format
    original_url = request.original_url
    if not original_url.startswith(("http://", "https://")):
        raise HTTPException(status_code=422, detail="Invalid URL format. Must start with http:// or https://")

    # Determine short code
    if request.custom_slug:
        # Check if custom slug already exists
        existing = db.query(URL).filter(URL.short_code == request.custom_slug).first()
        if existing:
            raise HTTPException(status_code=409, detail="Custom slug already exists")
        short_code = request.custom_slug
    else:
        # Generate random short code (8 characters)
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
        tags=request.tags or [],
    )

    # Hash password if provided
    if request.password:
        from passlib.context import CryptContext
        pwd_context = CryptContext(schemes=["bcrypt"])
        url.password_hash = pwd_context.hash(request.password)

    # Save to database
    db.add(url)
    db.commit()
    db.refresh(url)

    # Log audit
    audit = AuditLog(
        user_id=user_id,
        action="CREATE_URL",
        resource_type="URL",
        resource_id=str(url.id),
        ip_address=request.client.host if hasattr(request, 'client') else None,
        details={"short_code": short_code},
    )
    db.add(audit)
    db.commit()

    return url

# ============================================================================
# ROUTES - REDIRECT
# ============================================================================

@app.get("/{short_code}")
async def redirect_to_original(
    short_code: str,
    request: Request,
    db: Session = Depends(get_db),
):
    """Redirect to original URL and track the click"""

    # Query database
    url = db.query(URL).filter(URL.short_code == short_code).first()

    if not url:
        raise HTTPException(status_code=404, detail="URL not found")

    if not url.is_active:
        raise HTTPException(status_code=410, detail="URL is no longer available")

    # Check expiration
    if url.expires_at and url.expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=410, detail="URL has expired")

    # Check password if protected
    if url.password_hash:
        password = request.query_params.get("password")
        if not password:
            raise HTTPException(status_code=401, detail="Password required")

        from passlib.context import CryptContext
        pwd_context = CryptContext(schemes=["bcrypt"])
        if not pwd_context.verify(password, url.password_hash):
            raise HTTPException(status_code=401, detail="Invalid password")

    # Track click
    click = Click(
        url_id=url.id,
        ip_address=str(request.client.host) if request.client else None,
        user_agent=request.headers.get("user-agent"),
        referrer=request.headers.get("referer"),
    )
    db.add(click)

    # Increment denormalized counter
    url.total_clicks += 1

    db.commit()

    return RedirectResponse(url=url.original_url, status_code=307)

# ============================================================================
# ROUTES - ANALYTICS
# ============================================================================

@app.get("/api/v1/urls/{url_id}/analytics", response_model=AnalyticsResponse)
async def get_analytics(
    url_id: int,
    db: Session = Depends(get_db),
    user_id: UUID = Depends(get_current_user),
):
    """Get analytics for a specific URL"""

    # Verify user owns this URL
    url = db.query(URL).filter(URL.id == url_id, URL.user_id == user_id).first()

    if not url:
        raise HTTPException(status_code=404, detail="URL not found")

    # Get clicks for this URL
    clicks = db.query(Click).filter(Click.url_id == url_id).all()

    # Calculate breakdowns
    device_breakdown = {}
    country_breakdown = {}

    for click in clicks:
        if click.device_type:
            device_breakdown[click.device_type] = device_breakdown.get(click.device_type, 0) + 1
        if click.country:
            country_breakdown[click.country] = country_breakdown.get(click.country, 0) + 1

    # Get top country and device
    top_country = max(country_breakdown, key=country_breakdown.get) if country_breakdown else None
    top_device = max(device_breakdown, key=device_breakdown.get) if device_breakdown else None

    # Count unique IPs
    unique_ips = db.query(func.count(func.distinct(Click.ip_address))).filter(
        Click.url_id == url_id
    ).scalar() or 0

    return {
        "total_clicks": url.total_clicks,
        "unique_visitors": unique_ips,
        "top_country": top_country,
        "top_device": top_device,
        "device_breakdown": device_breakdown,
        "country_breakdown": country_breakdown,
    }

# ============================================================================
# ROUTES - LIST URLs
# ============================================================================

@app.get("/api/v1/urls", response_model=List[URLResponse])
async def list_user_urls(
    db: Session = Depends(get_db),
    user_id: UUID = Depends(get_current_user),
):
    """List all URLs created by current user"""

    urls = db.query(URL).filter(
        URL.user_id == user_id,
        URL.is_active == True
    ).order_by(URL.created_at.desc()).all()

    return urls

# ============================================================================
# ROUTES - GET URL DETAILS
# ============================================================================

@app.get("/api/v1/urls/{url_id}", response_model=URLResponse)
async def get_url_details(
    url_id: int,
    db: Session = Depends(get_db),
    user_id: UUID = Depends(get_current_user),
):
    """Get details of a specific URL"""

    url = db.query(URL).filter(URL.id == url_id, URL.user_id == user_id).first()

    if not url:
        raise HTTPException(status_code=404, detail="URL not found")

    return url

# ============================================================================
# ROUTES - DELETE URL
# ============================================================================

@app.delete("/api/v1/urls/{url_id}", status_code=204)
async def delete_url(
    url_id: int,
    db: Session = Depends(get_db),
    user_id: UUID = Depends(get_current_user),
):
    """Delete (deactivate) a URL"""

    url = db.query(URL).filter(URL.id == url_id, URL.user_id == user_id).first()

    if not url:
        raise HTTPException(status_code=404, detail="URL not found")

    # Soft delete: mark as inactive
    url.is_active = False
    db.commit()

    # Log audit
    audit = AuditLog(
        user_id=user_id,
        action="DELETE_URL",
        resource_type="URL",
        resource_id=str(url_id),
        details={"short_code": url.short_code},
    )
    db.add(audit)
    db.commit()

# ============================================================================
# ERROR HANDLERS
# ============================================================================

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Custom HTTP exception handler"""
    return {
        "error": exc.detail,
        "status_code": exc.status_code,
    }

# ============================================================================
# STARTUP
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)














