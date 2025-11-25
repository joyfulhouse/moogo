"""Sensor platform for Moogo integration."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    PERCENTAGE,
    SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from pymoogo import MoogoDevice

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

    entities: list[SensorEntity] = []

    # Public data sensors (always available)
    entities.extend(
        [
            MoogoLiquidTypesSensor(coordinator),
            MoogoScheduleTemplatesSensor(coordinator),
            MoogoAPIStatusSensor(coordinator),
        ]
    )

    # Device sensors (only if authenticated)
    if coordinator.client.is_authenticated and coordinator.data.get("devices"):
        device_count = len(coordinator.data["devices"])
        _LOGGER.info("Setting up sensors for %d authenticated devices", device_count)

        for device_data in coordinator.data["devices"]:
            device_id = device_data.get("deviceId")
            device_name = device_data.get("deviceName", f"Moogo Device {device_id}")

            if device_id:
                entities.extend(
                    [
                        MoogoDeviceStatusSensor(coordinator, device_id, device_name),
                        MoogoDeviceLiquidLevelSensor(
                            coordinator, device_id, device_name
                        ),
                        MoogoDeviceWaterLevelSensor(
                            coordinator, device_id, device_name
                        ),
                        MoogoDeviceTemperatureSensor(
                            coordinator, device_id, device_name
                        ),
                        MoogoDeviceHumiditySensor(coordinator, device_id, device_name),
                        MoogoDeviceSignalStrengthSensor(
                            coordinator, device_id, device_name
                        ),
                        MoogoDeviceSchedulesSensor(coordinator, device_id, device_name),
                        MoogoDeviceLastSpraySensor(coordinator, device_id, device_name),
                    ]
                )
                _LOGGER.debug(
                    "Added 8 sensors for device: %s (%s)", device_name, device_id
                )
    else:
        auth_status = (
            "authenticated"
            if coordinator.client.is_authenticated
            else "not authenticated"
        )
        device_count = len(coordinator.data.get("devices", []))
        _LOGGER.info(
            "No device sensors added - Auth: %s, Devices: %d",
            auth_status,
            device_count,
        )

    async_add_entities(entities, update_before_add=True)


class MoogoBaseSensor(CoordinatorEntity[MoogoCoordinator], SensorEntity):
    """Base class for Moogo sensors."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: MoogoCoordinator) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._was_available: bool | None = None

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        is_available = bool(self.coordinator.last_update_success)

        # Log availability changes
        if self._was_available is not None and self._was_available != is_available:
            if is_available:
                _LOGGER.debug("%s is now available", self.name)
            else:
                _LOGGER.warning(
                    "%s is now unavailable (coordinator update failed)", self.name
                )

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
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return additional state attributes."""
        liquid_types = self.coordinator.data.get("liquid_types", [])
        if liquid_types:
            return {
                "liquid_types": [
                    item.get("liquidName", "Unknown") for item in liquid_types
                ],
                "details": liquid_types,
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
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return additional state attributes."""
        schedules = self.coordinator.data.get("recommended_schedules", [])
        if schedules:
            return {
                "schedule_names": [item.get("title", "Unknown") for item in schedules],
                "details": schedules,
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
        self._attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def native_value(self) -> str:
        """Return the state of the sensor."""
        if self.coordinator.last_update_success:
            return "Connected"
        return "Disconnected"

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return additional state attributes."""
        return {
            "authenticated": self.coordinator.client.is_authenticated,
            "last_update": self.coordinator.last_update_success,
        }


# Device-specific sensors (require authentication)
class MoogoDeviceSensor(CoordinatorEntity[MoogoCoordinator], SensorEntity):
    """Base class for device-specific sensors using pymoogo MoogoDevice."""

    _attr_has_entity_name = True

    def __init__(
        self, coordinator: MoogoCoordinator, device_id: str, device_name: str
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.device_id = device_id
        self.device_name = device_name
        self._was_available: bool | None = None

    @property
    def device(self) -> MoogoDevice | None:
        """Get the MoogoDevice instance."""
        return self.coordinator.get_device(self.device_id)

    @property
    def device_info(self) -> dict[str, Any]:
        """Return device information."""
        device_info: dict[str, Any] = {
            "identifiers": {(DOMAIN, self.device_id)},
            "name": self.device_name,
            "manufacturer": "Moogo",
            "model": "Smart Spray Device",
        }

        # Add firmware version from device properties
        device = self.device
        if device and device.firmware:
            device_info["sw_version"] = device.firmware

        return device_info

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        device = self.device
        is_available = device is not None and self.coordinator.last_update_success

        # Log availability changes with reasons
        if self._was_available is not None and self._was_available != is_available:
            if is_available:
                _LOGGER.info(
                    "%s sensor %s is now available", self.device_name, self.name
                )
            else:
                if not self.coordinator.last_update_success:
                    reason = "coordinator update failed"
                elif device is None:
                    reason = "device not found"
                else:
                    reason = "unknown"
                _LOGGER.warning(
                    "%s sensor %s is now unavailable (%s)",
                    self.device_name,
                    self.name,
                    reason,
                )

        self._was_available = is_available
        return is_available


class MoogoDeviceStatusSensor(MoogoDeviceSensor):
    """Device online/offline status sensor."""

    def __init__(
        self, coordinator: MoogoCoordinator, device_id: str, device_name: str
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, device_id, device_name)
        self._attr_name = "Status"
        self._attr_unique_id = f"{device_id}_status"
        self._attr_icon = "mdi:power-settings"

    @property
    def native_value(self) -> str | None:
        """Return the state of the sensor."""
        device = self.device
        if device:
            return "Online" if device.is_online else "Offline"
        return "Unknown"


class MoogoDeviceLiquidLevelSensor(MoogoDeviceSensor):
    """Device liquid level sensor."""

    def __init__(
        self, coordinator: MoogoCoordinator, device_id: str, device_name: str
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, device_id, device_name)
        self._attr_name = "Liquid Level"
        self._attr_unique_id = f"{device_id}_liquid_level"
        self._attr_icon = "mdi:cup-water"

    @property
    def native_value(self) -> str | None:
        """Return the state of the sensor."""
        device = self.device
        if device:
            liquid_level = device.liquid_level
            if liquid_level == 1:
                return "OK"
            elif liquid_level == 0:
                return "Empty"
            else:
                return "Unknown"
        return None


class MoogoDeviceWaterLevelSensor(MoogoDeviceSensor):
    """Device water level sensor."""

    def __init__(
        self, coordinator: MoogoCoordinator, device_id: str, device_name: str
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, device_id, device_name)
        self._attr_name = "Water Level"
        self._attr_unique_id = f"{device_id}_water_level"
        self._attr_icon = "mdi:water-percent"

    @property
    def native_value(self) -> str | None:
        """Return the state of the sensor."""
        device = self.device
        if device:
            water_level = device.water_level
            if water_level == 1:
                return "OK"
            elif water_level == 0:
                return "Empty"
            else:
                return "Unknown"
        return None


class MoogoDeviceTemperatureSensor(MoogoDeviceSensor):
    """Device temperature sensor."""

    def __init__(
        self, coordinator: MoogoCoordinator, device_id: str, device_name: str
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, device_id, device_name)
        self._attr_name = "Temperature"
        self._attr_unique_id = f"{device_id}_temperature"
        self._attr_device_class = SensorDeviceClass.TEMPERATURE
        self._attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
        self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self) -> float | None:
        """Return the state of the sensor."""
        device = self.device
        if device:
            temp = device.temperature
            return float(temp) if temp is not None else None
        return None


class MoogoDeviceHumiditySensor(MoogoDeviceSensor):
    """Device humidity sensor."""

    def __init__(
        self, coordinator: MoogoCoordinator, device_id: str, device_name: str
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, device_id, device_name)
        self._attr_name = "Humidity"
        self._attr_unique_id = f"{device_id}_humidity"
        self._attr_device_class = SensorDeviceClass.HUMIDITY
        self._attr_native_unit_of_measurement = PERCENTAGE
        self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self) -> int | None:
        """Return the state of the sensor."""
        device = self.device
        if device:
            humidity = device.humidity
            return int(humidity) if humidity is not None else None
        return None


class MoogoDeviceSignalStrengthSensor(MoogoDeviceSensor):
    """Device signal strength sensor."""

    def __init__(
        self, coordinator: MoogoCoordinator, device_id: str, device_name: str
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, device_id, device_name)
        self._attr_name = "Signal Strength"
        self._attr_unique_id = f"{device_id}_signal_strength"
        self._attr_device_class = SensorDeviceClass.SIGNAL_STRENGTH
        self._attr_native_unit_of_measurement = SIGNAL_STRENGTH_DECIBELS_MILLIWATT
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def native_value(self) -> int | None:
        """Return the state of the sensor."""
        device = self.device
        if device:
            rssi = device.rssi
            return int(rssi) if rssi is not None else None
        return None


class MoogoDeviceSchedulesSensor(MoogoDeviceSensor):
    """Device active schedules sensor."""

    def __init__(
        self, coordinator: MoogoCoordinator, device_id: str, device_name: str
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, device_id, device_name)
        self._attr_name = "Active Schedules"
        self._attr_unique_id = f"{device_id}_active_schedules"
        self._attr_icon = "mdi:calendar-check"
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._schedules_cache: list[dict[str, Any]] = []

    async def async_update(self) -> None:
        """Update schedule data from device."""
        device = self.device
        if device:
            try:
                schedules = await device.get_schedules()
                self._schedules_cache = [
                    {
                        "id": s.id,
                        "hour": s.hour,
                        "minute": s.minute,
                        "duration": s.duration,
                        "repeatSet": s.repeat_set,
                        "status": 1 if s.is_enabled else 0,
                    }
                    for s in schedules
                ]
            except Exception as err:
                _LOGGER.debug("Failed to get schedules for %s: %s", self.device_id, err)

    @property
    def native_value(self) -> int | None:
        """Return the number of active schedules."""
        return sum(1 for s in self._schedules_cache if s.get("status") == 1)

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return additional state attributes."""
        schedule_info = []
        for schedule in self._schedules_cache:
            schedule_info.append(
                {
                    "id": schedule.get("id"),
                    "time": f"{schedule.get('hour', 0):02d}:{schedule.get('minute', 0):02d}",
                    "duration": schedule.get("duration", 0),
                    "repeat": schedule.get("repeatSet", ""),
                    "status": "enabled" if schedule.get("status") == 1 else "disabled",
                }
            )

        enabled = sum(1 for s in self._schedules_cache if s.get("status") == 1)
        disabled = sum(1 for s in self._schedules_cache if s.get("status") == 0)

        return {
            "schedules": schedule_info,
            "total_schedules": len(self._schedules_cache),
            "enabled_schedules": enabled,
            "disabled_schedules": disabled,
        }


class MoogoDeviceLastSpraySensor(MoogoDeviceSensor):
    """Device last spray information sensor."""

    def __init__(
        self, coordinator: MoogoCoordinator, device_id: str, device_name: str
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, device_id, device_name)
        self._attr_name = "Last Spray"
        self._attr_unique_id = f"{device_id}_last_spray"
        self._attr_icon = "mdi:spray-bottle"
        self._attr_device_class = SensorDeviceClass.TIMESTAMP
        self._attr_entity_registry_enabled_default = False

    @property
    def native_value(self) -> datetime | None:
        """Return the last spray timestamp."""
        device = self.device
        if device and device.status:
            last_spray_end = device.status.latest_spraying_end
            if last_spray_end and last_spray_end > 0:
                _LOGGER.debug(
                    "Raw timestamp value for %s: %s", self.device_id, last_spray_end
                )

                try:
                    # First try as milliseconds (typical for modern APIs)
                    if last_spray_end > 1000000000000:  # Roughly year 2001 in ms
                        result = datetime.fromtimestamp(last_spray_end / 1000, tz=UTC)
                        _LOGGER.debug(
                            "Converted milliseconds %s to %s", last_spray_end, result
                        )
                        return result
                    # If less than that, it's probably in seconds
                    else:
                        result = datetime.fromtimestamp(last_spray_end, tz=UTC)
                        _LOGGER.debug(
                            "Converted seconds %s to %s", last_spray_end, result
                        )
                        return result
                except (ValueError, OSError) as e:
                    _LOGGER.warning(
                        "Invalid timestamp format: %s, error: %s", last_spray_end, e
                    )
                    return None
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return additional state attributes."""
        device = self.device
        if device and device.status:
            return {
                "last_spray_duration": device.status.latest_spraying_duration or 0,
                "run_status": 1 if device.is_running else 0,
                "spray_status": "running" if device.is_running else "stopped",
            }
        return {"last_spray_duration": 0, "run_status": 0, "spray_status": "unknown"}
