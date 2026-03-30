from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel

#from app.database import SessionLocal

# ============================================================================
app = FastAPI(title="URL Shortener API")

# ============================================================================
# DEPENDENCIES
# ============================================================================

def get_db():
    """Dependency para obter sessão do banco"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


async def get_current_user(request: Request, db: Session = Depends(get_db)) -> UUID:
    """Extrai API key do header e retorna user_id"""
    auth_header = request.headers.get("Authorization", "")
    
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing API key")
    
    api_key = auth_header.replace("Bearer ", "")
    
    try:
        return UUID(api_key)
    except:
        raise HTTPException(status_code=401, detail="Invalid API key")

# ============================================================================
# REQUEST MODELS
# ============================================================================

class URLCreateRequest(BaseModel):
    original_url: str
    custom_slug: Optional[str] = None
    expires_at: Optional[datetime] = None
    password: Optional[str] = None


class URLResponse(BaseModel):
    id: int
    short_code: str
    original_url: str
    created_at: datetime
    clicks_total: int
    
    class Config:
        from_attributes = True

# ============================================================================
# ROUTES
# ============================================================================

@app.post("/api/v1/urls")
async def create_short_url(
    request: URLCreateRequest,
    db: Session = Depends(get_db),
    user_id: UUID = Depends(get_current_user)
):
    """Cria uma URL encurtada"""
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
    """Redireciona para URL original"""
    # Check Redis cache first
    # If miss: query PostgreSQL
    # Track click (async to Celery)
    # Redirect to original URL
    pass


@app.get("/api/v1/urls/{url_id}/analytics")
async def get_analytics(
    url_id: int,
    db: Session = Depends(get_db),
    user_id: UUID = Depends(get_current_user)
):
    """Retorna analytics da URL"""
    # Return aggregated metrics
    # Geographic breakdown
    # Device breakdown
    # Time-series data
    pass
