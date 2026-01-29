"""
Shared test configuration and fixtures
"""
import pytest
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

# Set test environment before importing app
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["JWT_SECRET"] = "test-secret-key-for-testing-only"
os.environ["SKIP_SCHEDULER"] = "true"  # Skip scheduler during tests

from main import app
from db.base import Base

# Import all models to register them with Base
from db.models.user import User
from db.models.monitor import Monitor
from db.models.api_key import ApiKey
from db.models.settings import Settings

# Create test database engine
TEST_DATABASE_URL = "sqlite:///:memory:"
test_engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


def override_get_db():
    """Override database dependency for tests"""
    db = TestSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(scope="function")
def test_db():
    """Create a fresh database for each test"""
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture
def client(test_db):
    """Create a test client with overridden database"""
    from api.dependencies import get_db
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
