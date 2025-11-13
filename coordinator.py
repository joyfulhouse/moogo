"""Data update coordinator for Moogo integration."""
from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .moogo_api import MoogoClient
from .const import DEFAULT_UPDATE_INTERVAL, PUBLIC_DATA_UPDATE_INTERVAL

_LOGGER = logging.getLogger(__name__)


class MoogoCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Moogo data update coordinator."""

    def __init__(self, hass: HomeAssistant, api: MoogoClient, entry: ConfigEntry) -> None:
        """Initialize the coordinator."""
        self.api: MoogoClient = api
        self.entry: ConfigEntry = entry
        self._last_device_count: int = 0
        self._device_availability: dict[str, bool] = {}  # Track device availability states

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
        if self.api.is_authenticated:
            return DEFAULT_UPDATE_INTERVAL
        else:
            return PUBLIC_DATA_UPDATE_INTERVAL

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from Moogo API."""
        try:
            data: dict[str, Any] = {}
            
            # Always fetch public data
            data["liquid_types"] = await self.api.get_liquid_types()
            data["recommended_schedules"] = await self.api.get_recommended_schedules()
            
            # Fetch authenticated data if available
            if self.api.is_authenticated:
                _LOGGER.debug("Fetching authenticated device data")
                devices = await self.api.get_devices()
                data["devices"] = devices or []
                
                # Update polling interval if authentication status changed
                new_interval = self._get_update_interval()
                if new_interval != self.update_interval.total_seconds():
                    self.update_interval = timedelta(seconds=new_interval)
                    _LOGGER.info(f"Updated polling interval to {new_interval} seconds for authenticated data")
                
                # Get detailed information for each device
                if devices:
                    device_statuses: dict[str, Any] = {}
                    device_schedules: dict[str, Any] = {}
                    device_count: int = len(devices)
                    
                    # Log if device count changed
                    if device_count != self._last_device_count:
                        _LOGGER.info(f"Device count changed: {self._last_device_count} -> {device_count}")
                        self._last_device_count = device_count
                    
                    for device in devices:
                        device_id = device.get("deviceId")
                        device_name = device.get("deviceName", f"Device {device_id}")

                        if device_id:
                            # Get device status
                            status = await self.api.get_device_status(device_id)
                            if status:
                                device_statuses[device_id] = status
                                _LOGGER.debug(f"Updated status for {device_name} ({device_id})")

                                # Track device availability changes
                                is_available = status.get("onlineStatus") == 1
                                previous_availability = self._device_availability.get(device_id)

                                # Log availability changes
                                if previous_availability is not None and previous_availability != is_available:
                                    if is_available:
                                        _LOGGER.info(f"Device {device_name} ({device_id}) is now ONLINE")
                                    else:
                                        _LOGGER.warning(f"Device {device_name} ({device_id}) is now OFFLINE")

                                # Update tracked availability
                                self._device_availability[device_id] = is_available

                            # Get device schedules
                            schedules = await self.api.get_device_schedules(device_id)
                            if schedules:
                                device_schedules[device_id] = schedules
                                # Handle the fact that MoogoClient returns dict with items
                                schedule_count = len(schedules.get("items", [])) if isinstance(schedules, dict) else len(schedules)
                                _LOGGER.debug(f"Updated schedules for {device_name} ({device_id}): {schedule_count} schedules")
                    
                    data["device_statuses"] = device_statuses
                    data["device_schedules"] = device_schedules
                    
                    _LOGGER.debug(f"Successfully updated data for {len(device_statuses)} devices")
                else:
                    data["device_statuses"] = {}
                    data["device_schedules"] = {}
                    _LOGGER.info("No devices found for authenticated user")
            else:
                # No authentication, ensure we're using public data interval
                new_interval = self._get_update_interval()
                if new_interval != self.update_interval.total_seconds():
                    self.update_interval = timedelta(seconds=new_interval)
                    _LOGGER.info(f"Updated polling interval to {new_interval} seconds for public data only")
                    
                data["devices"] = []
                data["device_statuses"] = {}
                data["device_schedules"] = {}
            
            # Add metadata
            data["auth_status"] = "authenticated" if self.api.is_authenticated else "public_only"
            data["update_time"] = self.last_update_success
            
            return data
            
        except Exception as err:
            _LOGGER.error(f"Error updating Moogo data: {err}")
            raise UpdateFailed(f"Error communicating with Moogo API: {err}")