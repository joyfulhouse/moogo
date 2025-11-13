"""The Moogo integration."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr

from .const import CONF_EMAIL, CONF_PASSWORD, DOMAIN
from .coordinator import MoogoCoordinator
from .moogo_api import MoogoClient

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
        session=session,
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

    # Clean up stale devices (Gold tier: stale device removal)
    await _async_remove_stale_devices(hass, entry, coordinator)

    # Set up platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def _async_remove_stale_devices(
    hass: HomeAssistant,
    entry: ConfigEntry,
    coordinator: MoogoCoordinator,
) -> None:
    """Remove devices that are no longer present in the API."""
    device_registry = dr.async_get(hass)

    # Get all devices for this integration entry
    devices_in_registry = dr.async_entries_for_config_entry(
        device_registry, entry.entry_id
    )

    # Get current device IDs from coordinator data
    current_device_ids = set()
    if coordinator.api.is_authenticated and coordinator.data.get("devices"):
        current_device_ids = {
            device.get("deviceId")
            for device in coordinator.data["devices"]
            if device.get("deviceId")
        }

    # Check each registered device
    for device_entry in devices_in_registry:
        # Extract device ID from identifiers
        device_id = None
        for identifier in device_entry.identifiers:
            if identifier[0] == DOMAIN:
                device_id = identifier[1]
                break

        # If device is no longer in API response, remove it
        if device_id and device_id not in current_device_ids:
            _LOGGER.info(
                "Removing stale device '%s' (ID: %s) - no longer found in API",
                device_entry.name,
                device_id,
            )
            device_registry.async_remove_device(device_entry.id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    # Unload platforms
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
