import asyncio
import os
from typing import AsyncGenerator, Generator

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from src.api.server import app
from src.core.database import Base, get_session
from src.core.config import settings

# Test database URL
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

# Create test engine
test_engine = create_async_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
)

# Create test session factory
TestSessionLocal = sessionmaker(
    test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Create a test database session."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async with TestSessionLocal() as session:
        yield session
    
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture(scope="function")
def test_client(db_session: AsyncSession) -> TestClient:
    """Create a test client with database override."""
    
    async def override_get_session() -> AsyncSession:
        yield db_session
    
    app.dependency_overrides[get_session] = override_get_session
    
    with TestClient(app) as client:
        yield client
    
    app.dependency_overrides.clear()


@pytest.fixture
def api_headers() -> dict:
    """Get API headers with authentication."""
    return {"X-API-Key": settings.api_key}


@pytest.fixture
def sample_model_data() -> dict:
    """Sample model best practices data."""
    return {
        "model_id": "test-model",
        "model_name": "Test Model",
        "category": "text",
        "version": "1.0.0",
        "prompt_structure": "Test prompt structure",
        "prompt_examples": [
            {
                "prompt": "Test prompt",
                "explanation": "Test explanation",
                "tags": ["test"],
            }
        ],
        "parameters": [
            {
                "name": "temperature",
                "type": "float",
                "default": 0.7,
                "recommended": 0.3,
                "range": {"min": 0.0, "max": 1.0},
                "description": "Controls randomness",
                "impact": "Lower is more deterministic",
            }
        ],
        "pitfalls": [
            {
                "title": "Test Pitfall",
                "description": "Test description",
                "solution": "Test solution",
                "severity": "medium",
            }
        ],
        "tags": ["test", "sample"],
        "related_models": ["other-model"],
    }


@pytest.fixture
def sample_scraped_post() -> dict:
    """Sample scraped post data."""
    return {
        "source_type": "reddit",
        "post_id": "test123",
        "url": "https://reddit.com/r/test/test123",
        "title": "Test Post",
        "content": "This is a test post about prompting",
        "author": "testuser",
        "created_at": "2024-01-01T00:00:00Z",
        "score": 100,
        "relevance_score": 0.8,
        "extracted_practices": {
            "tips": ["Test tip"],
            "prompt_patterns": ["Test pattern"],
        },
        "metadata": {
            "subreddit": "test",
            "num_comments": 10,
        },
    }


@pytest.fixture
def mock_reddit_env(monkeypatch):
    """Mock Reddit environment variables."""
    monkeypatch.setenv("REDDIT_CLIENT_ID", "test_client_id")
    monkeypatch.setenv("REDDIT_CLIENT_SECRET", "test_client_secret")
    monkeypatch.setenv("REDDIT_USER_AGENT", "test_user_agent")