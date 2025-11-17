"""Pytest configuration and fixtures for Moogo tests."""

import sys
from pathlib import Path

import pytest

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture
def mock_aiohttp_session():
    """Mock aiohttp session for testing."""
    from unittest.mock import AsyncMock, MagicMock

    session = MagicMock()
    session.request = AsyncMock()
    return session


@pytest.fixture
def authenticated_client(mock_aiohttp_session):
    """Create an authenticated MoogoClient for testing."""
    from moogo_api.client import MoogoClient

    client = MoogoClient(
        email="test@example.com",
        password="test_password",
        session=mock_aiohttp_session,
    )
    client._authenticated = True
    client._token = "test_token"
    return client


@pytest.fixture
def unauthenticated_client(mock_aiohttp_session):
    """Create an unauthenticated MoogoClient for testing."""
    from moogo_api.client import MoogoClient

    return MoogoClient(session=mock_aiohttp_session)
