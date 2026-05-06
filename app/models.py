"""
SQLAlchemy ORM Models for URL Shortener
Production-grade models with validations and constraints
"""

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB, INET, UUID
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


# ============================================================================
# USER MODEL
# ============================================================================

class User(Base):
    """User account model with API key management"""

    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    api_key = Column(String(64), unique=True, nullable=False, index=True)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    urls = relationship("URL", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User(id={self.id}, email={self.email})>"


# ============================================================================
# URL MODEL
# ============================================================================

class URL(Base):
    """Main URL shortening model"""

    __tablename__ = "urls"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    short_code = Column(String(10), unique=True, nullable=False, index=True)
    original_url = Column(Text, nullable=False)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    expires_at = Column(DateTime(timezone=True), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)
    tags = Column(JSONB, default=list, nullable=False)
    custom_metadata = Column(JSONB, default=dict, nullable=False)
    total_clicks = Column(BigInteger, default=0, nullable=False)

    # Indexes
    __table_args__ = (
        Index("idx_urls_user_id_created", "user_id", created_at.desc()),
        Index("idx_urls_active_expires", "is_active", "expires_at"),
    )

    # Relationships
    user = relationship("User", back_populates="urls")
    clicks = relationship("Click", back_populates="url", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<URL(id={self.id}, short_code={self.short_code}, clicks={self.total_clicks})>"

    def to_dict(self):
        """Convert to dictionary for caching"""
        return {
            "id": self.id,
            "short_code": self.short_code,
            "original_url": self.original_url,
            "created_at": self.created_at.isoformat(),
            "total_clicks": self.total_clicks,
            "is_active": self.is_active,
        }


# ============================================================================
# CLICK MODEL
# ============================================================================

class Click(Base):
    """Click event - tracks every URL access"""

    __tablename__ = "clicks"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    url_id = Column(
        BigInteger,
        ForeignKey("urls.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    clicked_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )
    country = Column(String(2), nullable=True, index=True)
    region = Column(String(100), nullable=True)
    city = Column(String(100), nullable=True)
    latitude = Column(String(20), nullable=True)
    longitude = Column(String(20), nullable=True)
    device_type = Column(String(20), nullable=True, index=True)
    os_name = Column(String(50), nullable=True)
    browser_name = Column(String(50), nullable=True)
    referrer = Column(Text, nullable=True)
    user_agent = Column(Text, nullable=True)
    ip_address = Column(INET, nullable=True)

    # Relationships
    url = relationship("URL", back_populates="clicks")

    def __repr__(self):
        return f"<Click(url_id={self.url_id}, country={self.country})>"


# ============================================================================
# CLICK AGGREGATE MODEL
# ============================================================================

class ClickAggregate(Base):
    """Hourly aggregated analytics for fast queries"""

    __tablename__ = "click_aggregates"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    url_id = Column(
        BigInteger,
        ForeignKey("urls.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    date_hour = Column(DateTime(timezone=True), nullable=False, index=True)
    total_clicks = Column(BigInteger, default=0, nullable=False)
    unique_ips = Column(BigInteger, default=0, nullable=False)
    device_breakdown = Column(JSONB, default=dict, nullable=True)
    country_breakdown = Column(JSONB, default=dict, nullable=True)
    os_breakdown = Column(JSONB, default=dict, nullable=True)
    browser_breakdown = Column(JSONB, default=dict, nullable=True)
    top_referrers = Column(JSONB, default=list, nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    __table_args__ = (
        Index("idx_aggregates_url_date", "url_id", date_hour.desc()),
    )

    def __repr__(self):
        return f"<ClickAggregate(url_id={self.url_id}, clicks={self.total_clicks})>"


# ============================================================================
# AUDIT LOG MODEL
# ============================================================================

class AuditLog(Base):
    """Audit trail for compliance and debugging"""

    __tablename__ = "audit_logs"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    action = Column(String(50), nullable=False, index=True)
    resource_type = Column(String(50), nullable=True)
    resource_id = Column(String(255), nullable=True)
    ip_address = Column(INET, nullable=True)
    user_agent = Column(Text, nullable=True)
    details = Column(JSONB, default=dict, nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )

    __table_args__ = (
        Index("idx_audit_logs_user_action", "user_id", "action", created_at.desc()),
    )

    def __repr__(self):
        return f"<AuditLog(action={self.action}, resource={self.resource_type})>"

# ============================================================================
# WEBHOOK MODEL
# ============================================================================

class Webhook(Base):
    """User webhook configuration for event notifications"""

    __tablename__ = "webhooks"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    url = Column(Text, nullable=False)
    events = Column(JSONB, default=list, nullable=False)  # ["url.clicked", "url.created", etc]
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    secret = Column(String(64), nullable=False)  # For HMAC signature verification
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    last_triggered_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    user = relationship("User", backref="webhooks")
    logs = relationship("WebhookLog", back_populates="webhook", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Webhook(id={self.id}, user_id={self.user_id}, url={self.url})>"


# ============================================================================
# WEBHOOK LOG MODEL
# ============================================================================

class WebhookLog(Base):
    """Log of webhook delivery attempts"""

    __tablename__ = "webhook_logs"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    webhook_id = Column(
        BigInteger,
        ForeignKey("webhooks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    event_type = Column(String(50), nullable=False)  # "url.clicked", "url.created", etc
    event_data = Column(JSONB, nullable=False)  # The actual event payload
    http_status = Column(BigInteger, nullable=True)  # Response status code
    response_body = Column(Text, nullable=True)  # Response from webhook endpoint
    error_message = Column(Text, nullable=True)  # Error details if failed
    attempt_number = Column(BigInteger, default=1, nullable=False)
    success = Column(Boolean, default=False, nullable=False, index=True)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )
    next_retry_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    webhook = relationship("Webhook", back_populates="logs")

    def __repr__(self):
        return f"<WebhookLog(webhook_id={self.webhook_id}, event_type={self.event_type}, success={self.success})>"





