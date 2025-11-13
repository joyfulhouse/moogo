"""Sensor platform for Moogo integration."""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    PERCENTAGE,
    UnitOfTemperature,
    SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

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
    """Set up Moogo sensor entities."""
    coordinator: MoogoCoordinator = config_entry.runtime_data
    
    entities = []
    
    # Public data sensors (always available)
    entities.extend([
        MoogoLiquidTypesSensor(coordinator),
        MoogoScheduleTemplatesSensor(coordinator),
        MoogoAPIStatusSensor(coordinator),
    ])
    
    # Device sensors (only if authenticated)
    if coordinator.api.is_authenticated and coordinator.data.get("devices"):
        device_count = len(coordinator.data["devices"])
        _LOGGER.info(f"Setting up sensors for {device_count} authenticated devices")
        
        for device in coordinator.data["devices"]:
            device_id = device.get("deviceId")
            device_name = device.get("deviceName", f"Moogo Device {device_id}")
            
            if device_id:
                entities.extend([
                    MoogoDeviceStatusSensor(coordinator, device_id, device_name),
                    MoogoDeviceLiquidLevelSensor(coordinator, device_id, device_name),
                    MoogoDeviceWaterLevelSensor(coordinator, device_id, device_name),
                    MoogoDeviceTemperatureSensor(coordinator, device_id, device_name),
                    MoogoDeviceHumiditySensor(coordinator, device_id, device_name),
                    MoogoDeviceSignalStrengthSensor(coordinator, device_id, device_name),
                    MoogoDeviceSchedulesSensor(coordinator, device_id, device_name),  # New Phase 2 sensor
                    MoogoDeviceLastSpraySensor(coordinator, device_id, device_name),  # New Phase 2 sensor
                ])
                _LOGGER.debug(f"Added 8 sensors for device: {device_name} ({device_id})")
    else:
        auth_status = "authenticated" if coordinator.api.is_authenticated else "not authenticated"
        device_count = len(coordinator.data.get("devices", []))
        _LOGGER.info(f"No device sensors added - Auth: {auth_status}, Devices: {device_count}")
    
    async_add_entities(entities, update_before_add=True)


class MoogoBaseSensor(CoordinatorEntity, SensorEntity):
    """Base class for Moogo sensors."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: MoogoCoordinator) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.coordinator = coordinator
        self._was_available: bool | None = None

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        is_available = self.coordinator.last_update_success

        # Log availability changes
        if self._was_available is not None and self._was_available != is_available:
            if is_available:
                _LOGGER.debug(f"{self.name} is now available")
            else:
                _LOGGER.warning(f"{self.name} is now unavailable (coordinator update failed)")

        self._was_available = is_available
        return is_available


# Public Data Sensors
class MoogoLiquidTypesSensor(MoogoBaseSensor):
    """Sensor for available liquid concentrate types."""

    def __init__(self, coordinator: MoogoCoordinator) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_name = "Moogo Liquid Types"
        self._attr_unique_id = "moogo_liquid_types"
        self._attr_icon = "mdi:bottle-wine"

    @property
    def native_value(self) -> str | None:
        """Return the state of the sensor."""
        liquid_types = self.coordinator.data.get("liquid_types", [])
        if liquid_types:
            return str(len(liquid_types))
        return "0"

    @property
    def extra_state_attributes(self) -> Dict[str, Any] | None:
        """Return additional state attributes."""
        liquid_types = self.coordinator.data.get("liquid_types", [])
        if liquid_types:
            return {
                "liquid_types": [item.get("liquidName", "Unknown") for item in liquid_types],
                "details": liquid_types
            }
        return {"liquid_types": [], "details": []}


class MoogoScheduleTemplatesSensor(MoogoBaseSensor):
    """Sensor for recommended schedule templates."""

    def __init__(self, coordinator: MoogoCoordinator) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_name = "Moogo Schedule Templates"
        self._attr_unique_id = "moogo_schedule_templates"
        self._attr_icon = "mdi:calendar-clock"

    @property
    def native_value(self) -> str | None:
        """Return the state of the sensor."""
        schedules = self.coordinator.data.get("recommended_schedules", [])
        if schedules:
            return str(len(schedules))
        return "0"

    @property
    def extra_state_attributes(self) -> Dict[str, Any] | None:
        """Return additional state attributes."""
        schedules = self.coordinator.data.get("recommended_schedules", [])
        if schedules:
            return {
                "schedule_names": [item.get("title", "Unknown") for item in schedules],
                "details": schedules
            }
        return {"schedule_names": [], "details": []}


class MoogoAPIStatusSensor(MoogoBaseSensor):
    """Sensor for API connectivity status."""

    def __init__(self, coordinator: MoogoCoordinator) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_name = "Moogo API Status"
        self._attr_unique_id = "moogo_api_status"
        self._attr_icon = "mdi:api"

    @property
    def native_value(self) -> str:
        """Return the state of the sensor."""
        if self.coordinator.last_update_success:
            return "Connected"
        return "Disconnected"

    @property
    def extra_state_attributes(self) -> Dict[str, Any] | None:
        """Return additional state attributes."""
        return {
            "authenticated": self.coordinator.api.is_authenticated,
            "base_url": self.coordinator.api.base_url,
            "last_update": self.coordinator.last_update_success,
        }


# Device-specific sensors (require authentication)
class MoogoDeviceSensor(CoordinatorEntity, SensorEntity):
    """Base class for device-specific sensors."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: MoogoCoordinator, device_id: str, device_name: str) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.device_id = device_id
        self.device_name = device_name
        self.coordinator = coordinator
        self._was_available: bool | None = None

    @property
    def device_info(self) -> Dict[str, Any]:
        """Return device information."""
        device_info = {
            "identifiers": {(DOMAIN, self.device_id)},
            "name": self.device_name,
            "manufacturer": "Moogo",
            "model": "Smart Spray Device",
        }

        # Add firmware version if available from device status
        device_status = self.coordinator.data.get("device_statuses", {}).get(self.device_id)
        if device_status and "firmware" in device_status:
            device_info["sw_version"] = device_status["firmware"]

        return device_info

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        device_status = self.coordinator.data.get("device_statuses", {}).get(self.device_id)
        is_available = device_status is not None and self.coordinator.last_update_success

        # Log availability changes with reasons
        if self._was_available is not None and self._was_available != is_available:
            if is_available:
                _LOGGER.info(f"{self.device_name} sensor {self.name} is now available")
            else:
                # Determine reason for unavailability
                if not self.coordinator.last_update_success:
                    reason = "coordinator update failed"
                elif device_status is None:
                    reason = "device status unavailable"
                else:
                    reason = "unknown"
                _LOGGER.warning(f"{self.device_name} sensor {self.name} is now unavailable ({reason})")

        self._was_available = is_available
        return is_available


class MoogoDeviceStatusSensor(MoogoDeviceSensor):
    """Device online/offline status sensor."""

    def __init__(self, coordinator: MoogoCoordinator, device_id: str, device_name: str) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, device_id, device_name)
        self._attr_name = f"{device_name} Status"
        self._attr_unique_id = f"{device_id}_status"
        self._attr_icon = "mdi:power-settings"

    @property
    def native_value(self) -> str | None:
        """Return the state of the sensor."""
        device_status = self.coordinator.data.get("device_statuses", {}).get(self.device_id)
        if device_status:
            online_status = device_status.get("onlineStatus", 0)
            return "Online" if online_status == 1 else "Offline"
        return "Unknown"



class MoogoDeviceLiquidLevelSensor(MoogoDeviceSensor):
    """Device liquid level sensor."""

    def __init__(self, coordinator: MoogoCoordinator, device_id: str, device_name: str) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, device_id, device_name)
        self._attr_name = f"{device_name} Liquid Level"
        self._attr_unique_id = f"{device_id}_liquid_level"
        self._attr_icon = "mdi:cup-water"
        # Remove unit and state class for text sensor

    @property
    def native_value(self) -> str | None:
        """Return the state of the sensor."""
        device_status = self.coordinator.data.get("device_statuses", {}).get(self.device_id)
        if device_status:
            liquid_level = device_status.get("liquid_level")
            if liquid_level == 1:
                return "OK"
            elif liquid_level == 0:
                return "Empty"
            else:
                return "Unknown"
        return None


class MoogoDeviceWaterLevelSensor(MoogoDeviceSensor):
    """Device water level sensor."""

    def __init__(self, coordinator: MoogoCoordinator, device_id: str, device_name: str) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, device_id, device_name)
        self._attr_name = f"{device_name} Water Level"
        self._attr_unique_id = f"{device_id}_water_level"
        self._attr_icon = "mdi:water-percent"
        # Remove unit and state class for text sensor

    @property
    def native_value(self) -> str | None:
        """Return the state of the sensor."""
        device_status = self.coordinator.data.get("device_statuses", {}).get(self.device_id)
        if device_status:
            water_level = device_status.get("water_level")
            if water_level == 1:
                return "OK"
            elif water_level == 0:
                return "Empty"
            else:
                return "Unknown"
        return None


class MoogoDeviceTemperatureSensor(MoogoDeviceSensor):
    """Device temperature sensor."""

    def __init__(self, coordinator: MoogoCoordinator, device_id: str, device_name: str) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, device_id, device_name)
        self._attr_name = f"{device_name} Temperature"
        self._attr_unique_id = f"{device_id}_temperature"
        self._attr_device_class = SensorDeviceClass.TEMPERATURE
        self._attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
        self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self) -> float | None:
        """Return the state of the sensor."""
        device_status = self.coordinator.data.get("device_statuses", {}).get(self.device_id)
        if device_status:
            return device_status.get("temperature")
        return None


class MoogoDeviceHumiditySensor(MoogoDeviceSensor):
    """Device humidity sensor."""

    def __init__(self, coordinator: MoogoCoordinator, device_id: str, device_name: str) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, device_id, device_name)
        self._attr_name = f"{device_name} Humidity"
        self._attr_unique_id = f"{device_id}_humidity"
        self._attr_device_class = SensorDeviceClass.HUMIDITY
        self._attr_native_unit_of_measurement = PERCENTAGE
        self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self) -> int | None:
        """Return the state of the sensor."""
        device_status = self.coordinator.data.get("device_statuses", {}).get(self.device_id)
        if device_status:
            return device_status.get("humidity")
        return None


class MoogoDeviceSignalStrengthSensor(MoogoDeviceSensor):
    """Device signal strength sensor."""

    def __init__(self, coordinator: MoogoCoordinator, device_id: str, device_name: str) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, device_id, device_name)
        self._attr_name = f"{device_name} Signal Strength"
        self._attr_unique_id = f"{device_id}_signal_strength"
        self._attr_device_class = SensorDeviceClass.SIGNAL_STRENGTH
        self._attr_native_unit_of_measurement = SIGNAL_STRENGTH_DECIBELS_MILLIWATT
        self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self) -> int | None:
        """Return the state of the sensor."""
        device_status = self.coordinator.data.get("device_statuses", {}).get(self.device_id)
        if device_status:
            return device_status.get("rssi")
        return None


class MoogoDeviceSchedulesSensor(MoogoDeviceSensor):
    """Device active schedules sensor."""

    def __init__(self, coordinator: MoogoCoordinator, device_id: str, device_name: str) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, device_id, device_name)
        self._attr_name = f"{device_name} Active Schedules"
        self._attr_unique_id = f"{device_id}_active_schedules"
        self._attr_icon = "mdi:calendar-check"
        self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self) -> int | None:
        """Return the number of active schedules."""
        schedules_data = self.coordinator.data.get("device_schedules", {}).get(self.device_id, [])
        if schedules_data is not None:
            # Handle dict response with items key or direct list
            schedules = schedules_data.get("items", []) if isinstance(schedules_data, dict) else schedules_data
            # Count enabled schedules
            active_count = sum(1 for schedule in schedules if isinstance(schedule, dict) and schedule.get("status") == 1)
            return active_count
        return 0

    @property
    def extra_state_attributes(self) -> Dict[str, Any] | None:
        """Return additional state attributes."""
        schedules_data = self.coordinator.data.get("device_schedules", {}).get(self.device_id, [])
        if schedules_data:
            # Handle dict response with items key or direct list
            schedules = schedules_data.get("items", []) if isinstance(schedules_data, dict) else schedules_data
            schedule_info = []
            for schedule in schedules:
                if isinstance(schedule, dict):
                    schedule_info.append({
                        "id": schedule.get("id"),
                        "time": f"{schedule.get('hour', 0):02d}:{schedule.get('minute', 0):02d}",
                        "duration": schedule.get("duration", 0),
                        "repeat": schedule.get("repeatSet", ""),
                        "status": "enabled" if schedule.get("status") == 1 else "disabled"
                    })
            
            return {
                "schedules": schedule_info,
                "total_schedules": len(schedules),
                "enabled_schedules": sum(1 for s in schedules if isinstance(s, dict) and s.get("status") == 1),
                "disabled_schedules": sum(1 for s in schedules if isinstance(s, dict) and s.get("status") == 0)
            }
        return {"schedules": [], "total_schedules": 0, "enabled_schedules": 0, "disabled_schedules": 0}


class MoogoDeviceLastSpraySensor(MoogoDeviceSensor):
    """Device last spray information sensor."""

    def __init__(self, coordinator: MoogoCoordinator, device_id: str, device_name: str) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, device_id, device_name)
        self._attr_name = f"{device_name} Last Spray"
        self._attr_unique_id = f"{device_id}_last_spray"
        self._attr_icon = "mdi:spray-bottle"
        self._attr_device_class = SensorDeviceClass.TIMESTAMP

    @property
    def native_value(self) -> datetime | None:
        """Return the last spray timestamp."""
        device_status = self.coordinator.data.get("device_statuses", {}).get(self.device_id)
        if device_status:
            last_spray_end = device_status.get("latestSprayingEnd")
            if last_spray_end and last_spray_end > 0:
                # Debug log the raw timestamp value
                logging.getLogger(__name__).debug(f"Raw timestamp value for {self.device_id}: {last_spray_end}")
                
                # Try different timestamp formats to handle API variations
                try:
                    # First try as milliseconds (typical for modern APIs)
                    if last_spray_end > 1000000000000:  # Roughly year 2001 in milliseconds
                        result = datetime.fromtimestamp(last_spray_end / 1000, tz=timezone.utc)
                        logging.getLogger(__name__).debug(f"Converted milliseconds {last_spray_end} to {result}")
                        return result
                    # If less than that, it's probably in seconds
                    else:
                        result = datetime.fromtimestamp(last_spray_end, tz=timezone.utc)
                        logging.getLogger(__name__).debug(f"Converted seconds {last_spray_end} to {result}")
                        return result
                except (ValueError, OSError) as e:
                    # If timestamp conversion fails, log the raw value for debugging
                    logging.getLogger(__name__).warning(f"Invalid timestamp format: {last_spray_end}, error: {e}")
                    return None
        return None

    @property
    def extra_state_attributes(self) -> Dict[str, Any] | None:
        """Return additional state attributes."""
        device_status = self.coordinator.data.get("device_statuses", {}).get(self.device_id)
        if device_status:
            return {
                "last_spray_duration": device_status.get("latestSprayingDuration", 0),
                "run_status": device_status.get("runStatus", 0),
                "spray_status": "running" if device_status.get("runStatus") == 1 else "stopped"
            }
        return {"last_spray_duration": 0, "run_status": 0, "spray_status": "unknown"}