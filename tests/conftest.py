"""Pytest configuration and fixtures"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from uuid import uuid4
import os

from app.models import Base, User
from app.main import app, get_db

DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql://app_user:dev_password@localhost:5432/url_shortener_test"
)

@pytest.fixture(scope="function")
def db_session():
    """Create test database session"""
    engine = create_engine(DATABASE_URL)
    Base.metadata.create_all(bind=engine)
    
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    
    yield db
    
    db.close()
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client(db_session):
    """Create test client with database override"""
    def override_get_db():
        yield db_session
    
    app.dependency_overrides[get_db] = override_get_db
    
    return TestClient(app)


@pytest.fixture
def test_user(db_session):
    """Create test user"""
    user = User(
        id=uuid4(),
        email="test@example.com",
        hashed_password="hashed",
        api_key="test-api-key-12345678901234567890123456789012",
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    return user
