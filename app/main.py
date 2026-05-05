"""URL Shortener API - Main application file

Production-grade URL shortening service with advanced analytics and click tracking.
"""
from datetime import datetime, timezone
from typing import Optional, List
from uuid import UUID

import secrets
import io
import os

from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.responses import RedirectResponse, JSONResponse, StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import func, text
from pydantic import BaseModel, ConfigDict

from app.cors import get_cors_config, validate_cors_config
from app.rate_limit import limiter, rate_limit_error_handler
from slowapi.errors import RateLimitExceeded

from app.database import SessionLocal
from app.models import User, URL, Click, AuditLog

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from app.qrcode import generate_qrcode_png

from app.batch import BatchURLRequest, BatchURLResponse, BatchErrorResponse, validate_batch_request


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
# CORS Configuration
# ============================================================================

validate_cors_config()

app.add_middleware(
    CORSMiddleware,
    **get_cors_config()
)

# ============================================================================
# Rate Limiting Configuration
# ============================================================================

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_error_handler)

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

    model_config = ConfigDict(from_attributes=True)


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
    except HTTPException:
        raise    
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
@limiter.limit("100/15 minutes")
async def create_short_url(
    request: Request,
    url_request: URLCreateRequest,
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
        request: FastAPI request object
        url_request: URL creation request data
        db: Database session
        user_id: Authenticated user ID
        
    Returns:
        URLResponse: Created URL data
        
    Raises:
        HTTPException: If URL format is invalid or custom slug already exists
    """
    original_url = url_request.original_url
    
    if not original_url.startswith(("http://", "https://")):
        raise HTTPException(
            status_code=422,
            detail="Invalid URL format. Must start with http:// or https://"
        )
    
    if url_request.custom_slug:
        existing = db.query(URL).filter(URL.short_code == url_request.custom_slug).first()
        if existing:
            raise HTTPException(status_code=409, detail="Custom slug already exists")
        short_code = url_request.custom_slug
    else:
        while True:
            short_code = secrets.token_urlsafe(6)[:8]
            existing = db.query(URL).filter(URL.short_code == short_code).first()
            if not existing:
                break
    
    url = URL(
        short_code=short_code,
        original_url=original_url,
        user_id=user_id,
        expires_at=url_request.expires_at,
        description=url_request.description,
        tags=url_request.tags or []
    )
    
    if url_request.password:
        pwd_hasher = PasswordHasher()
        url.password_hash = pwd_hasher.hash(url_request.password) 
    
    db.add(url)
    db.commit()
    db.refresh(url)
    
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
@limiter.limit("300/15 minutes")
async def list_user_urls(
    request: Request,
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
@limiter.limit("300/15 minutes")
async def get_url_details(
    request: Request,
    url_id: int,
    db: Session = Depends(get_db),
    user_id: UUID = Depends(get_current_user)
):
    """
    Get detailed information about a specific shortened URL.
    
    Args:
        request: FastAPI request object
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


@app.get(
    "/api/v1/urls/{url_id}/qrcode",
    tags=["URLs"],
    summary="Get URL QR Code",
    description="Generates and returns a QR code PNG image for the shortened URL"
)
@limiter.limit("300/15 minutes")
async def get_qrcode(
    request: Request,
    url_id: int,
    db: Session = Depends(get_db),
    user_id: UUID = Depends(get_current_user)
):
    """
    Generate and return QR code for a shortened URL.
    
    The QR code encodes the full shortened URL and can be scanned
    with any QR code reader to access the link.
    
    Args:
        request: FastAPI request object
        url_id: URL record ID
        db: Database session
        user_id: Authenticated user ID
        
    Returns:
        PNG image binary (image/png content type)
        
    Raises:
        HTTPException: If URL not found or doesn't belong to user
    """
    url = db.query(URL).filter(
        URL.id == url_id,
        URL.user_id == user_id
    ).first()
    
    if not url:
        raise HTTPException(status_code=404, detail="URL not found")
    
    if os.getenv("ENVIRONMENT") == "production":
        base_url = os.getenv("APP_URL", "https://your-domain.com")
    else:
        base_url = "http://localhost:8000"
    
    full_short_url = f"{base_url}/{url.short_code}"
    
    try:
        qr_png = generate_qrcode_png(full_short_url)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate QR code: {str(e)}"
        )
    
    return StreamingResponse(
        io.BytesIO(qr_png),
        media_type="image/png",
        headers={"Content-Disposition": f"inline; filename=qrcode_{url.short_code}.png"}
    )


@app.delete(
    "/api/v1/urls/{url_id}",
    status_code=204,
    tags=["URLs"],
    summary="Delete URL",
    description="Soft deletes a shortened URL by marking it as inactive"
)
@limiter.limit("300/15 minutes")
async def delete_url(
    request: Request,
    url_id: int,
    db: Session = Depends(get_db),
    user_id: UUID = Depends(get_current_user)
):
    """
    Delete a shortened URL (soft delete).
    
    The URL is marked as inactive rather than permanently deleted,
    preserving analytics history.
    
    Args:
        request: FastAPI request object
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
    
    audit = AuditLog(
        user_id=user_id,
        action="DELETE_URL",
        resource_type="URL",
        resource_id=str(url_id),
        details={"short_code": url.short_code}
    )
    db.add(audit)
    db.commit()


@app.post(
    "/api/v1/urls/batch",
    status_code=201,
    response_model=BatchURLResponse,
    tags=["URLs"],
    summary="Create Multiple Shortened URLs",
    description="Creates multiple shortened URLs in a single atomic transaction"
)
@limiter.limit("50/15 minutes")
async def create_batch_urls(
    request: Request,
    batch_request: BatchURLRequest,
    db: Session = Depends(get_db),
    user_id: UUID = Depends(get_current_user)
):
    """
    Create multiple shortened URLs in a single transaction.
    
    Features:
    - Atomic: all URLs created or none
    - Fail-fast: validates all before creating any
    - Up to 50 URLs per batch
    - Same customization as single URL creation
    
    Args:
        request: FastAPI request object
        batch_request: Batch request with URLs to create
        db: Database session
        user_id: Authenticated user ID
        
    Returns:
        BatchURLResponse: List of created URLs
        
    Raises:
        HTTPException: If validation fails or database error
    """
    validation_result = validate_batch_request(batch_request)
    if not validation_result["valid"]:
        raise HTTPException(
            status_code=422,
            detail=validation_result["error"]
        )
    
    created_urls = []
    
    try:
        existing_codes = db.query(URL.short_code).all()
        existing_codes = [code[0] for code in existing_codes]
        
        short_codes_needed = []
        for url_item in batch_request.urls:
            if url_item.custom_slug:
                short_codes_needed.append(url_item.custom_slug)
            else:
                short_codes_needed.append(None)
        
        auto_gen_count = sum(1 for code in short_codes_needed if code is None)
        
        from app.batch import generate_short_codes
        auto_codes = generate_short_codes(auto_gen_count, existing_codes) if auto_gen_count > 0 else []
        
        auto_code_index = 0
        
        for idx, url_item in enumerate(batch_request.urls):
            if short_codes_needed[idx]:
                short_code = short_codes_needed[idx]
                existing = db.query(URL).filter(URL.short_code == short_code).first()
                if existing:
                    raise HTTPException(
                        status_code=409,
                        detail=f"Custom slug '{short_code}' already exists"
                    )
            else:
                short_code = auto_codes[auto_code_index]
                auto_code_index += 1
            
            url = URL(
                short_code=short_code,
                original_url=url_item.original_url,
                user_id=user_id,
                expires_at=url_item.expires_at,
                description=url_item.description,
                tags=url_item.tags or []
            )
            
            if url_item.password:
                pwd_hasher = PasswordHasher()
                url.password_hash = pwd_hasher.hash(url_item.password)
            
            db.add(url)
            created_urls.append(url)
        
        db.commit()
        
        for url in created_urls:
            db.refresh(url)
        
        audit = AuditLog(
            user_id=user_id,
            action="CREATE_BATCH_URLS",
            resource_type="URL",
            resource_id=str(len(created_urls)),
            ip_address=request.client.host if hasattr(request, 'client') else None,
            details={"count": len(created_urls), "short_codes": [u.short_code for u in created_urls]}
        )
        db.add(audit)
        db.commit()
        
        return {
            "created": len(created_urls),
            "urls": [
                {
                    "id": url.id,
                    "short_code": url.short_code,
                    "original_url": url.original_url,
                    "created_at": url.created_at.isoformat() if url.created_at else "",
                    "is_active": url.is_active,
                    "expires_at": url.expires_at.isoformat() if url.expires_at else None,
                    "description": url.description or None,
                    "tags": url.tags or None
                }
                for url in created_urls
            ]
        }
        
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create batch: {str(e)}"
        )


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
@limiter.limit("300/15 minutes")
async def get_analytics(
    request: Request,
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
        request: FastAPI request object
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
    
    clicks = db.query(Click).filter(Click.url_id == url_id).all()
    
    device_breakdown = {}
    country_breakdown = {}
    
    for click in clicks:
        if click.device_type:
            device_breakdown[click.device_type] = device_breakdown.get(click.device_type, 0) + 1
        if click.country:
            country_breakdown[click.country] = country_breakdown.get(click.country, 0) + 1
    
    top_country = max(country_breakdown, key=country_breakdown.get) if country_breakdown else None
    top_device = max(device_breakdown, key=device_breakdown.get) if device_breakdown else None
    
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

@app.get("/{short_code}", tags=["Redirects"])
@limiter.limit("1000/15 minutes")
async def redirect_to_original(
    short_code: str,
    request: Request,
    db: Session = Depends(get_db)
):
    """Redirect to original URL"""
    url = db.query(URL).filter(URL.short_code == short_code).first()
    
    if not url:
        raise HTTPException(status_code=404, detail="URL not found")
    
    if not url.is_active:
        raise HTTPException(status_code=410, detail="URL is no longer available")
    
    if url.expires_at and url.expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=410, detail="URL has expired")
    
    if url.password_hash:
        password = request.query_params.get("password")
        if not password:
            raise HTTPException(status_code=401, detail="Password required")
        
        pwd_hasher = PasswordHasher()
        try:
            pwd_hasher.verify(url.password_hash, password)
        except VerifyMismatchError:
            raise HTTPException(status_code=401, detail="Invalid password") 
    
    ip_addr = "127.0.0.1"
    if request.client and request.client.host not in ["testclient"]:
        ip_addr = str(request.client.host)
    
    click = Click(
        url_id=url.id,
        clicked_at=datetime.now(timezone.utc),
        ip_address=ip_addr,
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
