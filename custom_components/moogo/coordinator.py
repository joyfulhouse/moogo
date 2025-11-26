"""Data update coordinator for Moogo integration."""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import TYPE_CHECKING, Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from pymoogo import MoogoAPIError, MoogoClient, MoogoDevice

from .const import DEFAULT_UPDATE_INTERVAL, PUBLIC_DATA_UPDATE_INTERVAL

if TYPE_CHECKING:
    pass

_LOGGER = logging.getLogger(__name__)


class MoogoCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Moogo data update coordinator using pymoogo library."""

    def __init__(
        self, hass: HomeAssistant, client: MoogoClient, entry: ConfigEntry
    ) -> None:
        """Initialize the coordinator."""
        self.client: MoogoClient = client
        self.entry: ConfigEntry = entry
        self._last_device_count: int = 0
        self._device_availability: dict[str, bool] = {}
        self._devices: dict[str, MoogoDevice] = {}

        # Dynamic update interval based on authentication status
        update_interval = self._get_update_interval()

        super().__init__(
            hass,
            _LOGGER,
            name="Moogo",
            update_interval=timedelta(seconds=update_interval),
        )

    def _get_update_interval(self) -> int:
        """Get appropriate update interval based on authentication status."""
        if self.client.is_authenticated:
            return DEFAULT_UPDATE_INTERVAL
        return PUBLIC_DATA_UPDATE_INTERVAL

    def get_device(self, device_id: str) -> MoogoDevice | None:
        """Get a MoogoDevice instance by ID."""
        return self._devices.get(device_id)

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from Moogo API using pymoogo library."""
        try:
            data: dict[str, Any] = {}

            # Always fetch public data (pymoogo handles caching internally)
            data["liquid_types"] = await self.client.get_liquid_types()
            data["recommended_schedules"] = (
                await self.client.get_recommended_schedules()
            )

            # Fetch authenticated data if available
            if self.client.is_authenticated:
                _LOGGER.debug("Fetching authenticated device data")

                # Get devices using pymoogo's MoogoDevice objects
                devices = await self.client.get_devices()
                data["devices"] = []

                # Update polling interval if authentication status changed
                new_interval = self._get_update_interval()
                if new_interval != self.update_interval.total_seconds():  # type: ignore[has-type]
                    self.update_interval = timedelta(seconds=new_interval)
                    _LOGGER.info(
                        "Updated polling interval to %d seconds for authenticated data",
                        new_interval,
                    )

                if devices:
                    device_count: int = len(devices)

                    # Log if device count changed
                    if device_count != self._last_device_count:
                        _LOGGER.info(
                            "Device count changed: %d -> %d",
                            self._last_device_count,
                            device_count,
                        )
                        self._last_device_count = device_count

                    for device in devices:
                        # Store MoogoDevice reference for control operations and property access
                        self._devices[device.id] = device

                        # Store device info in legacy format for entity compatibility
                        data["devices"].append(
                            {
                                "deviceId": device.id,
                                "deviceName": device.name,
                                "model": device.model,
                            }
                        )

                        # Refresh device status using MoogoDevice method
                        try:
                            await device.refresh()

                            # Track device availability changes using device properties
                            is_available = device.is_online
                            previous_availability = self._device_availability.get(
                                device.id
                            )

                            if (
                                previous_availability is not None
                                and previous_availability != is_available
                            ):
                                if is_available:
                                    _LOGGER.info(
                                        "Device %s (%s) is now ONLINE",
                                        device.name,
                                        device.id,
                                    )
                                else:
                                    _LOGGER.warning(
                                        "Device %s (%s) is now OFFLINE",
                                        device.name,
                                        device.id,
                                    )

                            self._device_availability[device.id] = is_available

                            _LOGGER.debug(
                                "Updated status for %s (%s)",
                                device.name,
                                device.id,
                            )

                        except MoogoAPIError as err:
                            _LOGGER.warning(
                                "Failed to refresh status for %s: %s",
                                device.name,
                                err,
                            )

                    _LOGGER.debug(
                        "Successfully updated data for %d devices",
                        len(self._devices),
                    )
                else:
                    _LOGGER.info("No devices found for authenticated user")
            else:
                # No authentication, ensure we're using public data interval
                new_interval = self._get_update_interval()
                if new_interval != self.update_interval.total_seconds():
                    self.update_interval = timedelta(seconds=new_interval)
                    _LOGGER.info(
                        "Updated polling interval to %d seconds for public data only",
                        new_interval,
                    )

                data["devices"] = []

            # Add metadata
            data["auth_status"] = (
                "authenticated" if self.client.is_authenticated else "public_only"
            )
            data["update_time"] = self.last_update_success

            return data

        except MoogoAPIError as err:
            _LOGGER.error("Error updating Moogo data: %s", err)
            raise UpdateFailed(f"Error communicating with Moogo API: {err}") from err
        except Exception as err:
            _LOGGER.error("Unexpected error updating Moogo data: %s", err)
            raise UpdateFailed(f"Unexpected error: {err}") from err
