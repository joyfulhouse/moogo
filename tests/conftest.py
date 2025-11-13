"""Common fixtures for Moogo tests."""

from __future__ import annotations

from collections.abc import Generator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from custom_components.moogo.const import CONF_EMAIL, CONF_PASSWORD, DOMAIN


@pytest.fixture
def mock_setup_entry() -> Generator[AsyncMock, None, None]:
    """Override async_setup_entry."""
    with patch(
        "custom_components.moogo.async_setup_entry", return_value=True
    ) as mock_setup_entry:
        yield mock_setup_entry


@pytest.fixture
def mock_moogo_client():
    """Mock MoogoClient."""
    with patch("custom_components.moogo.config_flow.MoogoClient") as mock_client_class:
        mock_client = MagicMock()
        mock_client.is_authenticated = True
        mock_client.test_connection = AsyncMock(return_value=True)
        mock_client.authenticate = AsyncMock(return_value=True)
        mock_client.get_liquid_types = AsyncMock(
            return_value=[{"liquidName": "Type 1"}, {"liquidName": "Type 2"}]
        )
        mock_client.get_recommended_schedules = AsyncMock(
            return_value=[{"title": "Schedule 1"}, {"title": "Schedule 2"}]
        )
        mock_client.get_devices = AsyncMock(
            return_value=[{"deviceId": "test_device_1", "deviceName": "Test Device 1"}]
        )
        mock_client.get_device_status = AsyncMock(
            return_value={"onlineStatus": 1, "runStatus": 0}
        )
        mock_client_class.return_value = mock_client
        yield mock_client


@pytest.fixture
def mock_config_entry():
    """Create a mock config entry."""
    from homeassistant.config_entries import ConfigEntry

    return ConfigEntry(
        version=1,
        minor_version=0,
        domain=DOMAIN,
        title="Moogo (test@example.com)",
        data={CONF_EMAIL: "test@example.com", CONF_PASSWORD: "test_password"},
        source="user",
        entry_id="test_entry_id",
        unique_id="test@example.com",
    )


@pytest.fixture
def mock_config_entry_public():
    """Create a mock config entry for public data only."""
    from homeassistant.config_entries import ConfigEntry

    return ConfigEntry(
        version=1,
        minor_version=0,
        domain=DOMAIN,
        title="Moogo (Public Data Only)",
        data={},
        source="user",
        entry_id="test_entry_id_public",
        unique_id="public_data",
    )
