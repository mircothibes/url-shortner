"""Batch URL creation logic for URL Shortener API

Handles creating multiple shortened URLs in a single transaction.
Implements validation before creation (fail-fast approach).
"""

import secrets
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, validator 


# ============================================================================
# Batch Request/Response Models
# ============================================================================

class BatchURLItem(BaseModel):
    """Single URL item in batch request"""
    original_url: str
    custom_slug: str = None
    password: str = None
    tags: List[str] = None
    description: str = None
    expires_at: str = None
    
    @validator('original_url')
    def validate_url_format(cls, v):
        """Validate URL format"""
        if not v:
            raise ValueError("original_url is required")
        if not v.startswith(("http://", "https://")):
            raise ValueError("URL must start with http:// or https://")
        if len(v) > 2048:
            raise ValueError("URL too long (max 2048 characters)")
        return v
    
    @validator('custom_slug')
    def validate_custom_slug(cls, v):
        """Validate custom slug if provided"""
        if v is not None:
            if len(v) < 3:
                raise ValueError("Custom slug must be at least 3 characters")
            if len(v) > 10:
                raise ValueError("Custom slug must be at most 10 characters")
            if not v.isalnum():
                raise ValueError("Custom slug must contain only alphanumeric characters")
        return v
    
    @validator('password')
    def validate_password(cls, v):
        """Validate password if provided"""
        if v is not None:
            if len(v) < 4:
                raise ValueError("Password must be at least 4 characters")
            if len(v) > 255:
                raise ValueError("Password too long (max 255 characters)")
        return v
    
    @validator('tags')
    def validate_tags(cls, v):
        """Validate tags if provided"""
        if v is not None:
            if len(v) > 10:
                raise ValueError("Maximum 10 tags allowed")
            for tag in v:
                if not isinstance(tag, str):
                    raise ValueError("Tags must be strings")
                if len(tag) > 50:
                    raise ValueError("Tag too long (max 50 characters)")
        return v
    
    @validator('description')
    def validate_description(cls, v):
        """Validate description if provided"""
        if v is not None:
            if len(v) > 500:
                raise ValueError("Description too long (max 500 characters)")
        return v


class BatchURLRequest(BaseModel):
    """Batch URL creation request"""
    urls: List[BatchURLItem]
    
    @validator('urls')
    def validate_urls_list(cls, v):
        """Validate URLs list"""
        if not v:
            raise ValueError("At least one URL is required")
        if len(v) > 50:
            raise ValueError("Maximum 50 URLs per batch (got {})".format(len(v)))
        return v


class BatchURLItemResponse(BaseModel):
    """Single URL item in batch response"""
    id: int
    short_code: str
    original_url: str
    created_at: str
    is_active: bool
    expires_at: Optional[str] = None 
    description: Optional[str] = None 
    tags: Optional[List[str]] = None    

    class Config:
        from_attributes = True
   

class BatchURLResponse(BaseModel):
    """Batch URL creation response"""
    created: int
    urls: List[BatchURLItemResponse]


class BatchErrorResponse(BaseModel):
    """Batch creation error response"""
    error: str
    detail: str
    created: int = 0


# ============================================================================
# Batch Validation Functions
# ============================================================================

def validate_batch_request(batch_request: BatchURLRequest) -> Dict[str, Any]:
    """
    Validate entire batch before creation.
    Implements fail-fast: if anything fails, return error immediately.
    
    Args:
        batch_request: Batch request with URLs to validate
        
    Returns:
        dict: Validation result with 'valid' (bool) and 'error' (str if invalid)
    """
    try:
        # Pydantic validation already happened
        # Additional business logic validations here
        
        for index, url_item in enumerate(batch_request.urls):
            # Check for duplicate URLs in same batch
            for other_index, other_item in enumerate(batch_request.urls):
                if index < other_index:
                    if url_item.original_url == other_item.original_url:
                        return {
                            "valid": False,
                            "error": f"Duplicate URL at index {index} and {other_index}"
                        }
        
        return {"valid": True}
        
    except Exception as e:
        return {
            "valid": False,
            "error": str(e)
        }


def generate_short_codes(count: int, existing_codes: List[str]) -> List[str]:
    """
    Generate multiple unique short codes.
    
    Args:
        count: Number of short codes to generate
        existing_codes: List of existing codes to avoid duplicates
        
    Returns:
        list: List of unique short codes
    """
    codes = []
    attempts = 0
    max_attempts = count * 10  # Prevent infinite loop
    
    while len(codes) < count and attempts < max_attempts:
        code = secrets.token_urlsafe(6)[:8]
        if code not in codes and code not in existing_codes:
            codes.append(code)
        attempts += 1
    
    if len(codes) < count:
        raise Exception(f"Could not generate {count} unique short codes")
    
    return codes


# ============================================================================
# Batch Constants
# ============================================================================

"""
BATCH URL CREATION LIMITS:

Max URLs per batch: 50
- Reasonable for user experience
- Prevents resource exhaustion
- Allows for 50 URLs in ~500ms

Transaction guarantee:
- All or nothing (atomic)
- If validation fails, 0 URLs created
- If database fails, all rolled back

Rate limiting:
- Batch creation uses same rate limits as single creation
- Counted per endpoint (not per URL in batch)
- 100 requests/15min per IP
"""
