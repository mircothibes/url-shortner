"""
Create a test user in the database
"""

from uuid import uuid4
from sqlalchemy.orm import sessionmaker
from app.database import engine
from app.models import Base, User

# Create tables
Base.metadata.create_all(bind=engine)

# Create session
SessionLocal = sessionmaker(bind=engine)
db = SessionLocal()

# Check if user already exists
existing_user = db.query(User).filter(User.email == "test@example.com").first()

if existing_user:
    print(f"✅ User already exists!")
    print(f"Email: {existing_user.email}")
    print(f"API Key: {existing_user.api_key}")
    print(f"User ID: {existing_user.id}")
else:
    # Create test user
    test_user = User(
        id=uuid4(),
        email="test@example.com",
        hashed_password="hashed_dummy_password",
        api_key="test-api-key-12345678901234567890123456789012",
        is_active=True,
    )

    db.add(test_user)
    db.commit()
    db.refresh(test_user)

    print(f"✅ User created successfully!")
    print(f"Email: {test_user.email}")
    print(f"API Key: {test_user.api_key}")
    print(f"User ID: {test_user.id}")

db.close()
