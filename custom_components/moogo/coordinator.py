"""Data update coordinator for Moogo integration."""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from pymoogo import MoogoAPIError, MoogoClient, MoogoDevice

from .const import (
    AUTH_STATUS_AUTHENTICATED,
    AUTH_STATUS_PUBLIC_ONLY,
    DEFAULT_UPDATE_INTERVAL,
    LOG_DEVICE_OFFLINE,
    LOG_DEVICE_ONLINE,
    PUBLIC_DATA_UPDATE_INTERVAL,
)
from .models import CoordinatorData, DeviceData

_LOGGER = logging.getLogger(__name__)


class MoogoCoordinator(DataUpdateCoordinator[CoordinatorData]):
    """Moogo data update coordinator using pymoogo library."""

    def __init__(
        self, hass: HomeAssistant, client: MoogoClient, entry: ConfigEntry
    ) -> None:
        """Initialize the coordinator.

        Args:
            hass: Home Assistant instance.
            client: Initialized pymoogo MoogoClient.
            entry: Config entry for this integration instance.
        """
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

    async def _async_update_data(self) -> CoordinatorData:
        """Fetch data from Moogo API using pymoogo library."""
        try:
            data: dict[str, Any] = {}

            # Fetch public data (always available)
            await self._fetch_public_data(data)

            # Fetch authenticated data if available
            if self.client.is_authenticated:
                await self._fetch_authenticated_data(data)
            else:
                self._handle_unauthenticated_mode(data)

            # Add metadata
            data["auth_status"] = (
                AUTH_STATUS_AUTHENTICATED
                if self.client.is_authenticated
                else AUTH_STATUS_PUBLIC_ONLY
            )
            data["update_time"] = self.last_update_success

            # Cast to CoordinatorData - data dict matches the TypedDict structure
            return data  # type: ignore[return-value]

        except MoogoAPIError as err:
            _LOGGER.error("Error updating Moogo data: %s", err)
            raise UpdateFailed(f"Error communicating with Moogo API: {err}") from err
        except Exception as err:
            _LOGGER.error("Unexpected error updating Moogo data: %s", err)
            raise UpdateFailed(f"Unexpected error: {err}") from err

    async def _fetch_public_data(self, data: dict[str, Any]) -> None:
        """Fetch public data (liquid types and schedules).

        Args:
            data: Dictionary to populate with fetched data.
        """
        data["liquid_types"] = await self.client.get_liquid_types()
        data["recommended_schedules"] = await self.client.get_recommended_schedules()

    async def _fetch_authenticated_data(self, data: dict[str, Any]) -> None:
        """Fetch authenticated user data (devices).

        Args:
            data: Dictionary to populate with fetched data.
        """
        _LOGGER.debug("Fetching authenticated device data")

        # Update polling interval if needed
        self._update_polling_interval()

        # Get devices using pymoogo's MoogoDevice objects
        devices = await self.client.get_devices()
        data["devices"] = []

        if devices:
            self._log_device_count_change(len(devices))
            await self._process_devices(devices, data)
            _LOGGER.debug(
                "Successfully updated data for %d devices", len(self._devices)
            )
        else:
            _LOGGER.info("No devices found for authenticated user")

    def _handle_unauthenticated_mode(self, data: dict[str, Any]) -> None:
        """Handle data fetch for unauthenticated mode.

        Args:
            data: Dictionary to populate.
        """
        # Update polling interval for public data only mode
        new_interval = self._get_update_interval()
        current_interval: timedelta | None = self.update_interval
        if current_interval and new_interval != current_interval.total_seconds():
            self.update_interval = timedelta(seconds=new_interval)
            _LOGGER.info(
                "Updated polling interval to %d seconds for public data only",
                new_interval,
            )
        data["devices"] = []

    def _update_polling_interval(self) -> None:
        """Update polling interval if authentication status changed."""
        new_interval = self._get_update_interval()
        current_interval: timedelta | None = self.update_interval
        if current_interval and new_interval != current_interval.total_seconds():
            self.update_interval = timedelta(seconds=new_interval)
            _LOGGER.info(
                "Updated polling interval to %d seconds for authenticated data",
                new_interval,
            )

    def _log_device_count_change(self, device_count: int) -> None:
        """Log if device count changed.

        Args:
            device_count: Current number of devices.
        """
        if device_count != self._last_device_count:
            _LOGGER.info(
                "Device count changed: %d -> %d",
                self._last_device_count,
                device_count,
            )
            self._last_device_count = device_count

    async def _process_devices(
        self, devices: list[MoogoDevice], data: dict[str, Any]
    ) -> None:
        """Process and refresh all devices.

        Args:
            devices: List of MoogoDevice objects.
            data: Dictionary to populate with device data.
        """
        for device in devices:
            # Store MoogoDevice reference for control operations
            self._devices[device.id] = device

            # Store device info in legacy format for entity compatibility
            device_data: DeviceData = {
                "deviceId": device.id,
                "deviceName": device.name,
                "model": device.model,
            }
            data["devices"].append(device_data)

            # Refresh device status
            await self._refresh_device_status(device)

    async def _refresh_device_status(self, device: MoogoDevice) -> None:
        """Refresh single device status and track availability.

        Args:
            device: MoogoDevice to refresh.
        """
        try:
            await device.refresh()
            self._track_device_availability(device)
            _LOGGER.debug("Updated status for %s (%s)", device.name, device.id)
        except MoogoAPIError as err:
            _LOGGER.warning("Failed to refresh status for %s: %s", device.name, err)

    def _track_device_availability(self, device: MoogoDevice) -> None:
        """Track and log device availability changes.

        Args:
            device: MoogoDevice to track.
        """
        is_available = device.is_online
        previous_availability = self._device_availability.get(device.id)

        if previous_availability is not None and previous_availability != is_available:
            if is_available:
                _LOGGER.info(LOG_DEVICE_ONLINE, device.name, device.id)
            else:
                _LOGGER.warning(LOG_DEVICE_OFFLINE, device.name, device.id)

        self._device_availability[device.id] = is_available
