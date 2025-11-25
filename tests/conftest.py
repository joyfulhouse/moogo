"""Pytest configuration and fixtures for Moogo integration tests.

These tests validate pymoogo library integration without requiring
the homeassistant package. Tests do not import any integration code
that depends on homeassistant.
"""

from __future__ import annotations

from collections.abc import Generator
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.fixture
def mock_aiohttp_session() -> MagicMock:
    """Mock aiohttp session for testing."""
    session = MagicMock()
    session.request = AsyncMock()
    return session


@pytest.fixture
def mock_pymoogo_client() -> Generator[MagicMock]:
    """Create a mock pymoogo MoogoClient."""
    with patch("pymoogo.MoogoClient") as MockClient:
        client = MockClient.return_value
        client.is_authenticated = True
        client.authenticate = AsyncMock()
        client.get_liquid_types = AsyncMock(return_value=[])
        client.get_recommended_schedules = AsyncMock(return_value=[])
        client.get_devices = AsyncMock(return_value=[])
        client.close = AsyncMock()
        yield client


@pytest.fixture
def mock_pymoogo_device() -> MagicMock:
    """Create a mock pymoogo MoogoDevice."""
    device = MagicMock()
    device.id = "test_device_123"
    device.name = "Test Moogo Device"
    device.model = "Smart Spray Device"
    device.is_online = True
    device.is_running = False
    device.temperature = 25.0
    device.humidity = 50
    device.liquid_level = 1
    device.water_level = 1
    device.rssi = -50
    device.firmware = "1.0.0"
    device.mix_ratio = 10

    # Mock status object
    status = MagicMock()
    status.is_online = True
    status.is_running = False
    status.temperature = 25.0
    status.humidity = 50
    status.liquid_level = 1
    status.water_level = 1
    status.rssi = -50
    status.firmware = "1.0.0"
    status.mix_ratio = 10
    status.latest_spraying_duration = 60
    status.latest_spraying_end = 1700000000000  # Timestamp in milliseconds
    device.status = status

    # Mock methods
    device.refresh = AsyncMock()
    device.start_spray = AsyncMock()
    device.stop_spray = AsyncMock()
    device.get_schedules = AsyncMock(return_value=[])
    device.circuit_status = {"circuit_open": False, "failures": 0}

    return device


@pytest.fixture
def mock_schedule() -> MagicMock:
    """Create a mock pymoogo Schedule."""
    schedule = MagicMock()
    schedule.id = "schedule_1"
    schedule.hour = 8
    schedule.minute = 30
    schedule.duration = 60
    schedule.repeat_set = "0,1,2,3,4,5,6"
    schedule.is_enabled = True
    return schedule


@pytest.fixture
def sample_liquid_types() -> list[dict[str, Any]]:
    """Sample liquid types data."""
    return [
        {"id": "1", "liquidName": "Fresh Scent", "description": "A fresh scent"},
        {"id": "2", "liquidName": "Lavender", "description": "Calming lavender"},
    ]


@pytest.fixture
def sample_recommended_schedules() -> list[dict[str, Any]]:
    """Sample recommended schedules data."""
    return [
        {"id": "1", "title": "Morning Refresh", "hour": 8, "minute": 0},
        {"id": "2", "title": "Evening Calm", "hour": 20, "minute": 0},
    ]


@pytest.fixture
def sample_device_data() -> list[dict[str, Any]]:
    """Sample device data in coordinator format."""
    return [
        {
            "deviceId": "device_123",
            "deviceName": "Living Room Moogo",
            "model": "Smart Spray Device",
        },
        {
            "deviceId": "device_456",
            "deviceName": "Bedroom Moogo",
            "model": "Smart Spray Device",
        },
    ]
