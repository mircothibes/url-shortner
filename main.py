# app/main.py
from fastapi import FastAPI, HTTPException, Depends
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, Union

app = FastAPI(title="URL Shortener API")


# Request Models
class URLCreateRequest(BaseModel):
    original_url: str
    custom_slug: str | None = None
    expires_at: Optinal[datetime] = None
    password: str | None = None

class URLResponse(BaseModel):
    id: int
    short_code: str
    original_url: str
    created_at: datetime
    clicks_total: int
    
    class Config:
        from_attributes = True

# Routes
@app.post("/api/v1/urls")
async def create_short_url(
    request: URLCreateRequest,
    db: Session = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user)
):
    # Validate URL
    # Generate unique short_code if not custom
    # Check rate limit via Redis
    # Save to PostgreSQL
    # Return shortened URL
    pass

@app.get("/{short_code}")
async def redirect_to_original(
    short_code: str,
    db: Session = Depends(get_db),
    request: Request
):
    # Check Redis cache first
    # If miss: query PostgreSQL
    # Track click (async to Celery)
    # Redirect to original URL
    pass

@app.get("/api/v1/urls/{url_id}/analytics")
async def get_analytics(
    url_id: int,
    db: Session = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user)
):
    # Return aggregated metrics
    # Geographic breakdown
    # Device breakdown
    # Time-series data
    pass
