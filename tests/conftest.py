"""Pytest configuration and fixtures for URL Shortener API"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient
from uuid import uuid4
import os

from app.models import Base, User
from app.main import app, get_db

# Use test database from environment or default
TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL", "postgresql://app_user:dev_password@localhost:5432/url_shortener_test")

@pytest.fixture(scope="function")
def test_db():
    """Create a test database session"""
    engine = create_engine(TEST_DATABASE_URL)
    
    # Create all tables
    Base.metadata.create_all(bind=engine)
    
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = TestingSessionLocal()
    
    def override_get_db():
        try:
            yield db
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db
    
    yield db
    
    # Cleanup
    db.close()
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client(test_db):
    """Create a test client"""
    from fastapi.testclient import TestClient as FC_TestClient
    return TestClient(app=app)


@pytest.fixture
def test_user(test_db):
    """Create a test user"""
    user = User(
        id=uuid4(),
        email="test@example.com",
        hashed_password="hashed_password",
        api_key="test-api-key-12345678901234567890123456789012",
        is_active=True,
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    
    return user
