"""
Database configuration and session management
"""

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Get database URL from environment or use default
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://app_user:dev_password@localhost:5432/url_shortener"
)

# Create engine
engine = create_engine(
    DATABASE_URL,
    echo=False,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
)

# Session factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


def get_db():
    """
    Get database session
    Use as dependency: Depends(get_db)
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def test_connection():
    """Test database connection"""
    try:
        with engine.connect() as connection:
            connection.execute("SELECT 1")
            print("✅ Database connected successfully")
            return True
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False


if __name__ == "__main__":
    test_connection()
