"""Test the Moogo coordinator."""

from __future__ import annotations

from datetime import timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest
from custom_components.moogo.const import DOMAIN
from custom_components.moogo.coordinator import MoogoCoordinator
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import UpdateFailed


async def test_coordinator_update_authenticated(
    hass: HomeAssistant, mock_moogo_client
) -> None:
    """Test coordinator data update with authentication."""
    config_entry = ConfigEntry(
        version=1,
        minor_version=0,
        domain=DOMAIN,
        title="Moogo (test@example.com)",
        data={
            CONF_EMAIL: "test@example.com",
            CONF_PASSWORD: "test_password",
        },
        source="user",
        entry_id="test_entry_id",
        unique_id="test@example.com",
    )

    coordinator = MoogoCoordinator(hass, mock_moogo_client, config_entry)
    await coordinator.async_config_entry_first_refresh()

    assert coordinator.data is not None
    assert "liquid_types" in coordinator.data
    assert "recommended_schedules" in coordinator.data
    assert "devices" in coordinator.data
    assert coordinator.data["auth_status"] == "authenticated"


async def test_coordinator_update_public_only(
    hass: HomeAssistant, mock_moogo_client
) -> None:
    """Test coordinator data update with public data only."""
    mock_moogo_client.is_authenticated = False

    config_entry = ConfigEntry(
        version=1,
        minor_version=0,
        domain=DOMAIN,
        title="Moogo (Public Data Only)",
        data={},
        source="user",
        entry_id="test_entry_id_public",
        unique_id="public_data",
    )

    coordinator = MoogoCoordinator(hass, mock_moogo_client, config_entry)
    await coordinator.async_config_entry_first_refresh()

    assert coordinator.data is not None
    assert "liquid_types" in coordinator.data
    assert "recommended_schedules" in coordinator.data
    assert coordinator.data["auth_status"] == "public_only"
    assert coordinator.data["devices"] == []


async def test_coordinator_update_failure(hass: HomeAssistant) -> None:
    """Test coordinator handling of update failure."""
    mock_client = MagicMock()
    mock_client.is_authenticated = True
    mock_client.get_liquid_types = AsyncMock(side_effect=Exception("API Error"))
    mock_client.get_recommended_schedules = AsyncMock(return_value=[])
    mock_client.get_devices = AsyncMock(return_value=[])

    config_entry = ConfigEntry(
        version=1,
        minor_version=0,
        domain=DOMAIN,
        title="Moogo (test@example.com)",
        data={
            CONF_EMAIL: "test@example.com",
            CONF_PASSWORD: "test_password",
        },
        source="user",
        entry_id="test_entry_id",
        unique_id="test@example.com",
    )

    coordinator = MoogoCoordinator(hass, mock_client, config_entry)

    with pytest.raises(UpdateFailed):
        await coordinator.async_config_entry_first_refresh()


async def test_coordinator_dynamic_interval(
    hass: HomeAssistant, mock_moogo_client
) -> None:
    """Test coordinator adjusts update interval based on auth status."""
    config_entry = ConfigEntry(
        version=1,
        minor_version=0,
        domain=DOMAIN,
        title="Moogo (test@example.com)",
        data={
            CONF_EMAIL: "test@example.com",
            CONF_PASSWORD: "test_password",
        },
        source="user",
        entry_id="test_entry_id",
        unique_id="test@example.com",
    )

    # Test authenticated interval (30 seconds)
    mock_moogo_client.is_authenticated = True
    coordinator = MoogoCoordinator(hass, mock_moogo_client, config_entry)
    assert coordinator.update_interval == timedelta(seconds=30)

    # Test public data interval (3600 seconds)
    mock_moogo_client.is_authenticated = False
    coordinator = MoogoCoordinator(hass, mock_moogo_client, config_entry)
    assert coordinator.update_interval == timedelta(seconds=3600)
