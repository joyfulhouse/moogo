"""The Moogo integration."""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .moogo_api import MoogoClient
from .const import CONF_EMAIL, CONF_PASSWORD, DOMAIN
from .coordinator import MoogoCoordinator

_LOGGER = logging.getLogger(__name__)

# Platforms: sensor for monitoring, switch for control
PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.SWITCH]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Moogo from a config entry."""
    # Initialize API client
    from homeassistant.helpers.aiohttp_client import async_get_clientsession
    session = async_get_clientsession(hass)

    api = MoogoClient(
        email=entry.data.get(CONF_EMAIL),
        password=entry.data.get(CONF_PASSWORD),
        session=session
    )

    # Test connection before setup (Bronze tier: test-before-setup)
    if not await api.test_connection():
        _LOGGER.error("Failed to connect to Moogo API during setup")
        return False

    # Authenticate if credentials provided
    if entry.data.get(CONF_EMAIL) and entry.data.get(CONF_PASSWORD):
        if not await api.authenticate():
            _LOGGER.error("Authentication failed during setup")
            return False

    # Initialize coordinator
    coordinator = MoogoCoordinator(hass, api, entry)

    # Fetch initial data
    await coordinator.async_config_entry_first_refresh()

    # Store coordinator using runtime_data (Bronze tier: runtime-data)
    entry.runtime_data = coordinator

    # Set up platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    # Unload platforms
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)