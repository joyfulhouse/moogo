"""Test the Moogo integration init."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

from custom_components.moogo import async_setup_entry, async_unload_entry
from custom_components.moogo.const import DOMAIN
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from homeassistant.core import HomeAssistant


async def test_setup_entry_success(hass: HomeAssistant, mock_moogo_client) -> None:
    """Test successful setup of config entry."""
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

    with (
        patch("custom_components.moogo.MoogoClient", return_value=mock_moogo_client),
        patch(
            "custom_components.moogo.coordinator.MoogoCoordinator"
        ) as mock_coordinator_class,
    ):
        mock_coordinator = MagicMock()
        mock_coordinator.async_config_entry_first_refresh = AsyncMock()
        mock_coordinator.data = {
            "devices": [],
            "liquid_types": [],
            "recommended_schedules": [],
        }
        mock_coordinator_class.return_value = mock_coordinator

        result = await async_setup_entry(hass, config_entry)
        assert result is True
        assert config_entry.runtime_data == mock_coordinator


async def test_setup_entry_auth_failure(hass: HomeAssistant) -> None:
    """Test setup failure due to authentication error."""
    config_entry = ConfigEntry(
        version=1,
        minor_version=0,
        domain=DOMAIN,
        title="Moogo (test@example.com)",
        data={
            CONF_EMAIL: "test@example.com",
            CONF_PASSWORD: "wrong_password",
        },
        source="user",
        entry_id="test_entry_id",
        unique_id="test@example.com",
    )

    with patch("custom_components.moogo.MoogoClient") as mock_client_class:
        mock_client = MagicMock()
        mock_client.test_connection = AsyncMock(return_value=True)
        mock_client.authenticate = AsyncMock(return_value=False)
        mock_client_class.return_value = mock_client

        result = await async_setup_entry(hass, config_entry)
        assert result is False


async def test_setup_entry_connection_failure(hass: HomeAssistant) -> None:
    """Test setup failure due to connection error."""
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

    with patch("custom_components.moogo.MoogoClient") as mock_client_class:
        mock_client = MagicMock()
        mock_client.test_connection = AsyncMock(return_value=False)
        mock_client_class.return_value = mock_client

        result = await async_setup_entry(hass, config_entry)
        assert result is False


async def test_setup_entry_public_data_only(
    hass: HomeAssistant, mock_moogo_client
) -> None:
    """Test setup with public data only (no credentials)."""
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

    mock_moogo_client.is_authenticated = False

    with (
        patch("custom_components.moogo.MoogoClient", return_value=mock_moogo_client),
        patch(
            "custom_components.moogo.coordinator.MoogoCoordinator"
        ) as mock_coordinator_class,
    ):
        mock_coordinator = MagicMock()
        mock_coordinator.async_config_entry_first_refresh = AsyncMock()
        mock_coordinator.data = {
            "liquid_types": [],
            "recommended_schedules": [],
        }
        mock_coordinator_class.return_value = mock_coordinator

        result = await async_setup_entry(hass, config_entry)
        assert result is True
        assert config_entry.runtime_data == mock_coordinator


async def test_unload_entry(hass: HomeAssistant, mock_moogo_client) -> None:
    """Test unloading a config entry."""
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

    with patch(
        "homeassistant.config_entries.ConfigEntries.async_unload_platforms",
        return_value=True,
    ) as mock_unload:
        result = await async_unload_entry(hass, config_entry)
        assert result is True
        mock_unload.assert_called_once()
