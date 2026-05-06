"""Webhook management and event handling for URL Shortener API

Handles webhook registration, event triggering, and delivery with retry logic.
"""

import hmac
import hashlib
import secrets
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone, timedelta
from pydantic import BaseModel, HttpUrl, validator
import httpx


# ============================================================================
# Webhook Models (Pydantic)
# ============================================================================

class WebhookCreateRequest(BaseModel):
    """Request model for creating a webhook"""
    url: HttpUrl
    events: List[str]
    
    @validator('events')
    def validate_events(cls, v):
        """Validate that only allowed events are requested"""
        allowed_events = {
            "url.created",
            "url.clicked",
            "url.expired",
            "url.deleted"
        }
        
        if not v:
            raise ValueError("At least one event is required")
        
        for event in v:
            if event not in allowed_events:
                raise ValueError(f"Invalid event: {event}. Allowed: {allowed_events}")
        
        return list(set(v))  # Remove duplicates


class WebhookResponse(BaseModel):
    """Response model for webhook"""
    id: int
    url: str
    events: List[str]
    is_active: bool
    created_at: str
    last_triggered_at: Optional[str] = None


class WebhookLogResponse(BaseModel):
    """Response model for webhook log"""
    id: int
    event_type: str
    success: bool
    http_status: Optional[int] = None
    attempt_number: int
    created_at: str
    error_message: Optional[str] = None


# ============================================================================
# Event Payloads
# ============================================================================

class URLClickedEvent(BaseModel):
    """Payload for url.clicked event"""
    event_type: str = "url.clicked"
    timestamp: str
    url_id: int
    short_code: str
    original_url: str
    total_clicks: int
    ip_address: Optional[str] = None
    country: Optional[str] = None
    device_type: Optional[str] = None


class URLCreatedEvent(BaseModel):
    """Payload for url.created event"""
    event_type: str = "url.created"
    timestamp: str
    url_id: int
    short_code: str
    original_url: str
    user_id: str


class URLExpiredEvent(BaseModel):
    """Payload for url.expired event"""
    event_type: str = "url.expired"
    timestamp: str
    url_id: int
    short_code: str
    original_url: str
    expired_at: str


class URLDeletedEvent(BaseModel):
    """Payload for url.deleted event"""
    event_type: str = "url.deleted"
    timestamp: str
    url_id: int
    short_code: str
    original_url: str


# ============================================================================
# Webhook Utilities
# ============================================================================

def generate_webhook_secret() -> str:
    """
    Generate a secure secret for webhook HMAC signing.
    
    Returns:
        str: Random 64-character secret
    """
    return secrets.token_urlsafe(48)


def create_webhook_signature(payload: str, secret: str) -> str:
    """
    Create HMAC-SHA256 signature for webhook payload.
    
    Args:
        payload: JSON payload as string
        secret: Webhook secret
        
    Returns:
        str: Hex-encoded HMAC signature
    """
    return hmac.new(
        secret.encode(),
        payload.encode(),
        hashlib.sha256
    ).hexdigest()


def verify_webhook_signature(payload: str, signature: str, secret: str) -> bool:
    """
    Verify webhook signature (for receiving webhooks).
    
    Args:
        payload: JSON payload as string
        signature: Signature to verify
        secret: Webhook secret
        
    Returns:
        bool: True if signature is valid
    """
    expected_signature = create_webhook_signature(payload, secret)
    return hmac.compare_digest(signature, expected_signature)


# ============================================================================
# Webhook Delivery
# ============================================================================

async def deliver_webhook(
    webhook_url: str,
    event_type: str,
    event_payload: Dict[str, Any],
    secret: str,
    timeout: int = 10
) -> tuple[bool, int, str]:
    """
    Attempt to deliver webhook to external endpoint.
    
    Args:
        webhook_url: URL to send webhook to
        event_type: Type of event (e.g., "url.clicked")
        event_payload: Event data as dictionary
        secret: Webhook secret for signing
        timeout: Request timeout in seconds
        
    Returns:
        tuple: (success: bool, status_code: int, response_body: str)
    """
    import json
    
    payload = json.dumps(event_payload)
    signature = create_webhook_signature(payload, secret)
    
    headers = {
        "Content-Type": "application/json",
        "X-Webhook-Signature": signature,
        "X-Webhook-Event": event_type,
        "User-Agent": "URLShortener/1.0"
    }
    
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                webhook_url,
                content=payload,
                headers=headers
            )
            
            return (
                response.status_code == 200,
                response.status_code,
                response.text[:1000]  # Limit response body
            )
    except Exception as e:
        return (False, 0, str(e)[:1000])


# ============================================================================
# Retry Logic
# ============================================================================

def calculate_next_retry(attempt_number: int, base_delay: int = 60) -> datetime:
    """
    Calculate next retry time using exponential backoff.
    
    Formula: delay = base_delay * (2 ^ (attempt - 1))
    
    Examples:
    - Attempt 1: 60 seconds
    - Attempt 2: 120 seconds
    - Attempt 3: 240 seconds
    - Attempt 4: 480 seconds (8 minutes)
    - Attempt 5: 960 seconds (16 minutes)
    
    Max retries: 5 (after which webhook is considered failed)
    
    Args:
        attempt_number: Current attempt number (1-based)
        base_delay: Base delay in seconds
        
    Returns:
        datetime: When to retry next
    """
    if attempt_number >= 5:
        return None  # No more retries
    
    delay_seconds = base_delay * (2 ** (attempt_number - 1))
    return datetime.now(timezone.utc) + timedelta(seconds=delay_seconds)


# ============================================================================
# Constants
# ============================================================================

"""
WEBHOOK CONFIGURATION:

Supported events:
- url.created: When a URL is created
- url.clicked: When a URL is accessed
- url.expired: When a URL expires
- url.deleted: When a URL is deleted

Delivery guarantees:
- Best effort (not guaranteed)
- Retry with exponential backoff
- Max 5 retry attempts
- Response must return 200 OK

Signing:
- HMAC-SHA256 signature in X-Webhook-Signature header
- Sign the entire request body
- Recipients should verify signature

Timeouts:
- 10 second timeout per request
- If no response within 10 seconds, counts as failed

Rate limits:
- Webhook delivery not rate limited
- But webhook creation/management is (100/15min)
"""
