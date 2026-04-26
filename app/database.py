"""Database configuration for URL Shortener API"""
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://app_user:dev_password@localhost:5432/url_shortener"
)

engine = create_engine(
    DATABASE_URL,
    poolclass=StaticPool,
    isolation_level="AUTOCOMMIT"
)

SessionLocal = sessionmaker(bind=engine)
