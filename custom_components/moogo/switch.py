"""Switch platform for Moogo integration."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from pymoogo import MoogoDevice, MoogoDeviceError

from .const import DOMAIN
from .coordinator import MoogoCoordinator

_LOGGER = logging.getLogger(__name__)

# Limit parallel updates to prevent overwhelming the API
PARALLEL_UPDATES = 1


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Moogo switch entities."""
    coordinator: MoogoCoordinator = config_entry.runtime_data

    entities: list[SwitchEntity] = []

    # Only add switch entities if authenticated and devices found
    if coordinator.client.is_authenticated and coordinator.data.get("devices"):
        for device_data in coordinator.data["devices"]:
            device_id = device_data.get("deviceId")
            device_name = device_data.get("deviceName", f"Moogo Device {device_id}")

            if device_id:
                entities.append(MoogoSpraySwitch(coordinator, device_id, device_name))

    if entities:
        async_add_entities(entities, update_before_add=True)


class MoogoSpraySwitch(CoordinatorEntity[MoogoCoordinator], SwitchEntity):
    """Switch entity for controlling spray functionality using pymoogo."""

    _attr_has_entity_name = True

    def __init__(
        self, coordinator: MoogoCoordinator, device_id: str, device_name: str
    ) -> None:
        """Initialize the switch."""
        super().__init__(coordinator)
        self.device_id = device_id
        self.device_name = device_name
        self._was_available: bool | None = None

        self._attr_name = "Spray"
        self._attr_unique_id = f"{device_id}_spray_switch"
        self._attr_icon = "mdi:spray"

    @property
    def device(self) -> MoogoDevice | None:
        """Get the MoogoDevice instance."""
        return self.coordinator.get_device(self.device_id)

    @property
    def device_info(self) -> dict[str, Any]:
        """Return device information."""
        return {
            "identifiers": {(DOMAIN, self.device_id)},
            "name": self.device_name,
            "manufacturer": "Moogo",
            "model": "Smart Spray Device",
        }

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        device = self.device
        is_available = False

        # Check if device is online and API is authenticated
        if device and self.coordinator.client.is_authenticated:
            is_available = device.is_online and self.coordinator.last_update_success

        # Log availability changes with detailed reasons
        if self._was_available is not None and self._was_available != is_available:
            if is_available:
                _LOGGER.info("%s spray switch is now available", self.device_name)
            else:
                if not self.coordinator.client.is_authenticated:
                    reason = "API not authenticated"
                elif not self.coordinator.last_update_success:
                    reason = "coordinator update failed"
                elif device is None:
                    reason = "device not found"
                elif not device.is_online:
                    reason = "device offline"
                else:
                    reason = "unknown"
                _LOGGER.warning(
                    "%s spray switch is now unavailable (%s)",
                    self.device_name,
                    reason,
                )

        self._was_available = is_available
        return is_available

    @property
    def is_on(self) -> bool | None:
        """Return true if the spray is currently running."""
        device = self.device
        if device:
            return bool(device.is_running)
        return None

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn on the spray using pymoogo device control.

        pymoogo handles:
        - Exponential backoff retry (5 attempts, 2s initial delay)
        - Circuit breaker for persistently offline devices
        - Automatic reauthentication on token expiry
        """
        device = self.device
        if not device:
            _LOGGER.error("Device %s not found", self.device_id)
            return

        try:
            _LOGGER.info("Starting spray for device %s", self.device_name)

            # pymoogo's start_spray handles all retry logic internally
            await device.start_spray()

            _LOGGER.info("Spray started for %s", self.device_name)

            # Refresh device status to update UI
            await device.refresh()

            # Request coordinator refresh to update all entities
            await self.coordinator.async_request_refresh()

        except MoogoDeviceError as err:
            _LOGGER.error(
                "Failed to start spray for %s: %s",
                self.device_name,
                err,
            )
        except Exception as err:
            _LOGGER.error(
                "Unexpected error starting spray for %s: %s",
                self.device_name,
                err,
            )

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off the spray using pymoogo device control.

        pymoogo handles:
        - Exponential backoff retry (5 attempts, 2s initial delay)
        - Circuit breaker for persistently offline devices
        - Automatic reauthentication on token expiry
        """
        device = self.device
        if not device:
            _LOGGER.error("Device %s not found", self.device_id)
            return

        try:
            _LOGGER.info("Stopping spray for device %s", self.device_name)

            # pymoogo's stop_spray handles all retry logic internally
            await device.stop_spray()

            _LOGGER.info("Spray stopped for %s", self.device_name)

            # Refresh device status to update UI
            await device.refresh()

            # Request coordinator refresh to update all entities
            await self.coordinator.async_request_refresh()

        except MoogoDeviceError as err:
            _LOGGER.error(
                "Failed to stop spray for %s: %s",
                self.device_name,
                err,
            )
        except Exception as err:
            _LOGGER.error(
                "Unexpected error stopping spray for %s: %s",
                self.device_name,
                err,
            )

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return additional state attributes."""
        device = self.device
        if device:
            attrs: dict[str, Any] = {
                "device_id": self.device_id,
                "is_running": device.is_running,
                "is_online": device.is_online,
            }

            # Add status details if available
            if device.status:
                attrs["latest_spraying_duration"] = (
                    device.status.latest_spraying_duration or 0
                )
                attrs["liquid_level"] = device.liquid_level
                attrs["water_level"] = device.water_level

            # Add circuit breaker status for diagnostics
            circuit_status = device.circuit_status
            if circuit_status:
                attrs["circuit_breaker_open"] = circuit_status.get(
                    "circuit_open", False
                )
                attrs["circuit_breaker_failures"] = circuit_status.get("failures", 0)

            return attrs
        return {}
