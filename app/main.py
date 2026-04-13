"""URL Shortener API - Main application file"""
from datetime import datetime, timezone
from typing import Optional, List
from uuid import UUID
import secrets
from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.responses import RedirectResponse, JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel
from app.database import SessionLocal, engine
from app.models import Base, User, URL, Click, AuditLog

Base.metadata.create_all(bind=engine)

app = FastAPI(title="URL Shortener API", description="Production-grade URL shortening service with analytics", version="1.0.0")

class URLCreateRequest(BaseModel):
    original_url: str
    custom_slug: Optional[str] = None
    expires_at: Optional[datetime] = None
    password: Optional[str] = None
    tags: Optional[List[str]] = None
    description: Optional[str] = None

class URLResponse(BaseModel):
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
    total_clicks: int
    unique_visitors: int
    top_country: Optional[str] = None
    top_device: Optional[str] = None
    device_breakdown: dict
    country_breakdown: dict

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

async def get_current_user(request: Request, db: Session = Depends(get_db)) -> UUID:
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

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "ok",
        "service": "URL Shortener API",
        "database": "connected",
        "version": "1.0.0"
    }

@app.post("/api/v1/urls", status_code=201, response_model=URLResponse)
async def create_short_url(request: URLCreateRequest, db: Session = Depends(get_db), user_id: UUID = Depends(get_current_user)):
    original_url = request.original_url
    if not original_url.startswith(("http://", "https://")):
        raise HTTPException(status_code=422, detail="Invalid URL format. Must start with http:// or https://")
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
    url = URL(short_code=short_code, original_url=original_url, user_id=user_id, expires_at=request.expires_at, description=request.description, tags=request.tags or [])
    if request.password:
        from passlib.context import CryptContext
        pwd_context = CryptContext(schemes=["bcrypt"])
        url.password_hash = pwd_context.hash(request.password)
    db.add(url)
    db.commit()
    db.refresh(url)
    audit = AuditLog(user_id=user_id, action="CREATE_URL", resource_type="URL", resource_id=str(url.id), ip_address=request.client.host if hasattr(request, 'client') else None, details={"short_code": short_code})
    db.add(audit)
    db.commit()
    return url

@app.get("/api/v1/urls", response_model=List[URLResponse])
async def list_user_urls(db: Session = Depends(get_db), user_id: UUID = Depends(get_current_user)):
    urls = db.query(URL).filter(URL.user_id == user_id, URL.is_active == True).order_by(URL.created_at.desc()).all()
    return urls

@app.get("/api/v1/urls/{url_id}", response_model=URLResponse)
async def get_url_details(url_id: int, db: Session = Depends(get_db), user_id: UUID = Depends(get_current_user)):
    url = db.query(URL).filter(URL.id == url_id, URL.user_id == user_id).first()
    if not url:
        raise HTTPException(status_code=404, detail="URL not found")
    return url

@app.get("/api/v1/urls/{url_id}/analytics", response_model=AnalyticsResponse)
async def get_analytics(url_id: int, db: Session = Depends(get_db), user_id: UUID = Depends(get_current_user)):
    url = db.query(URL).filter(URL.id == url_id, URL.user_id == user_id).first()
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
    unique_ips = db.query(func.count(func.distinct(Click.ip_address))).filter(Click.url_id == url_id).scalar() or 0
    return {"total_clicks": url.total_clicks, "unique_visitors": unique_ips, "top_country": top_country, "top_device": top_device, "device_breakdown": device_breakdown, "country_breakdown": country_breakdown}

@app.delete("/api/v1/urls/{url_id}", status_code=204)
async def delete_url(url_id: int, db: Session = Depends(get_db), user_id: UUID = Depends(get_current_user)):
    url = db.query(URL).filter(URL.id == url_id, URL.user_id == user_id).first()
    if not url:
        raise HTTPException(status_code=404, detail="URL not found")
    url.is_active = False
    db.commit()
    audit = AuditLog(user_id=user_id, action="DELETE_URL", resource_type="URL", resource_id=str(url_id), details={"short_code": url.short_code})
    db.add(audit)
    db.commit()

@app.get("/{short_code}")
async def redirect_to_original(short_code: str, request: Request, db: Session = Depends(get_db)):
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
        from passlib.context import CryptContext
        pwd_context = CryptContext(schemes=["bcrypt"])
        if not pwd_context.verify(password, url.password_hash):
            raise HTTPException(status_code=401, detail="Invalid password")
    click = Click(url_id=url.id, ip_address=str(request.client.host) if request.client else None, user_agent=request.headers.get("user-agent"), referrer=request.headers.get("referer"))
    db.add(click)
    url.total_clicks += 1
    db.commit()
    return RedirectResponse(url=url.original_url, status_code=307)

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail, "status_code": exc.status_code}
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
