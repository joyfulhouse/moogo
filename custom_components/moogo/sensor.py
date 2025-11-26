"""Sensor platform for Moogo integration."""

from __future__ import annotations

import logging
from datetime import datetime
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

from .const import (
    API_STATUS_CONNECTED,
    API_STATUS_DISCONNECTED,
    ICON_API_STATUS,
    ICON_DEVICE_STATUS,
    ICON_LAST_SPRAY,
    ICON_LIQUID_LEVEL,
    ICON_LIQUID_TYPES,
    ICON_SCHEDULE_TEMPLATES,
    ICON_SCHEDULES,
    ICON_WATER_LEVEL,
    SCHEDULE_DISABLED,
    SCHEDULE_ENABLED,
    STATUS_OFFLINE,
    STATUS_ONLINE,
    STATUS_UNKNOWN,
)
from .coordinator import MoogoCoordinator
from .entity import MoogoCoordinatorEntity, MoogoDeviceEntity
from .models import ScheduleCache, ScheduleInfo
from .utils import (
    convert_api_timestamp,
    format_schedule_time,
    get_level_status,
    safe_float,
    safe_int,
)

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
                    _create_device_sensors(coordinator, device_id, device_name)
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


def _create_device_sensors(
    coordinator: MoogoCoordinator, device_id: str, device_name: str
) -> list[SensorEntity]:
    """Create all sensors for a device.

    Args:
        coordinator: The Moogo data coordinator.
        device_id: Unique device identifier.
        device_name: Human-readable device name.

    Returns:
        List of sensor entities for the device.
    """
    return [
        MoogoDeviceStatusSensor(coordinator, device_id, device_name),
        MoogoDeviceLiquidLevelSensor(coordinator, device_id, device_name),
        MoogoDeviceWaterLevelSensor(coordinator, device_id, device_name),
        MoogoDeviceTemperatureSensor(coordinator, device_id, device_name),
        MoogoDeviceHumiditySensor(coordinator, device_id, device_name),
        MoogoDeviceSignalStrengthSensor(coordinator, device_id, device_name),
        MoogoDeviceSchedulesSensor(coordinator, device_id, device_name),
        MoogoDeviceLastSpraySensor(coordinator, device_id, device_name),
    ]


# =============================================================================
# Public Data Sensors
# =============================================================================


class MoogoLiquidTypesSensor(MoogoCoordinatorEntity, SensorEntity):
    """Sensor for available liquid concentrate types."""

    def __init__(self, coordinator: MoogoCoordinator) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_name = "Moogo Liquid Types"
        self._attr_unique_id = "moogo_liquid_types"
        self._attr_icon = ICON_LIQUID_TYPES

    @property
    def native_value(self) -> str:
        """Return the state of the sensor."""
        liquid_types = self.coordinator.data.get("liquid_types", [])
        return str(len(liquid_types)) if liquid_types else "0"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional state attributes."""
        liquid_types = self.coordinator.data.get("liquid_types", [])
        return {
            "liquid_types": [
                item.get("liquidName", "Unknown") for item in liquid_types
            ],
            "details": liquid_types,
        }


class MoogoScheduleTemplatesSensor(MoogoCoordinatorEntity, SensorEntity):
    """Sensor for recommended schedule templates."""

    def __init__(self, coordinator: MoogoCoordinator) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_name = "Moogo Schedule Templates"
        self._attr_unique_id = "moogo_schedule_templates"
        self._attr_icon = ICON_SCHEDULE_TEMPLATES

    @property
    def native_value(self) -> str:
        """Return the state of the sensor."""
        schedules = self.coordinator.data.get("recommended_schedules", [])
        return str(len(schedules)) if schedules else "0"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional state attributes."""
        schedules = self.coordinator.data.get("recommended_schedules", [])
        return {
            "schedule_names": [item.get("title", "Unknown") for item in schedules],
            "details": schedules,
        }


class MoogoAPIStatusSensor(MoogoCoordinatorEntity, SensorEntity):
    """Sensor for API connectivity status."""

    def __init__(self, coordinator: MoogoCoordinator) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_name = "Moogo API Status"
        self._attr_unique_id = "moogo_api_status"
        self._attr_icon = ICON_API_STATUS
        self._attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def native_value(self) -> str:
        """Return the state of the sensor."""
        if self.coordinator.last_update_success:
            return API_STATUS_CONNECTED
        return API_STATUS_DISCONNECTED

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional state attributes."""
        return {
            "authenticated": self.coordinator.client.is_authenticated,
            "last_update": self.coordinator.last_update_success,
        }


# =============================================================================
# Device-Specific Sensors
# =============================================================================


class MoogoDeviceStatusSensor(MoogoDeviceEntity, SensorEntity):
    """Device online/offline status sensor."""

    def __init__(
        self, coordinator: MoogoCoordinator, device_id: str, device_name: str
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, device_id, device_name)
        self._attr_name = "Status"
        self._attr_unique_id = f"{device_id}_status"
        self._attr_icon = ICON_DEVICE_STATUS

    @property
    def native_value(self) -> str:
        """Return the state of the sensor."""
        device = self.device
        if device:
            return STATUS_ONLINE if device.is_online else STATUS_OFFLINE
        return STATUS_UNKNOWN


class MoogoDeviceLiquidLevelSensor(MoogoDeviceEntity, SensorEntity):
    """Device liquid level sensor."""

    def __init__(
        self, coordinator: MoogoCoordinator, device_id: str, device_name: str
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, device_id, device_name)
        self._attr_name = "Liquid Level"
        self._attr_unique_id = f"{device_id}_liquid_level"
        self._attr_icon = ICON_LIQUID_LEVEL

    @property
    def native_value(self) -> str | None:
        """Return the state of the sensor."""
        device = self.device
        if device:
            return get_level_status(device.liquid_level)
        return None


class MoogoDeviceWaterLevelSensor(MoogoDeviceEntity, SensorEntity):
    """Device water level sensor."""

    def __init__(
        self, coordinator: MoogoCoordinator, device_id: str, device_name: str
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, device_id, device_name)
        self._attr_name = "Water Level"
        self._attr_unique_id = f"{device_id}_water_level"
        self._attr_icon = ICON_WATER_LEVEL

    @property
    def native_value(self) -> str | None:
        """Return the state of the sensor."""
        device = self.device
        if device:
            return get_level_status(device.water_level)
        return None


class MoogoDeviceTemperatureSensor(MoogoDeviceEntity, SensorEntity):
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
        return safe_float(device.temperature) if device else None


class MoogoDeviceHumiditySensor(MoogoDeviceEntity, SensorEntity):
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
        return safe_int(device.humidity) if device else None


class MoogoDeviceSignalStrengthSensor(MoogoDeviceEntity, SensorEntity):
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
        return safe_int(device.rssi) if device else None


class MoogoDeviceSchedulesSensor(MoogoDeviceEntity, SensorEntity):
    """Device active schedules sensor."""

    def __init__(
        self, coordinator: MoogoCoordinator, device_id: str, device_name: str
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, device_id, device_name)
        self._attr_name = "Active Schedules"
        self._attr_unique_id = f"{device_id}_active_schedules"
        self._attr_icon = ICON_SCHEDULES
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._schedules_cache: list[ScheduleCache] = []
        # Cache computed counts to avoid duplicate calculation
        self._enabled_count: int = 0
        self._disabled_count: int = 0

    async def async_update(self) -> None:
        """Update schedule data from device."""
        device = self.device
        if not device:
            return

        try:
            schedules = await device.get_schedules()
            self._schedules_cache = [
                ScheduleCache(
                    id=s.id,
                    hour=s.hour,
                    minute=s.minute,
                    duration=s.duration,
                    repeatSet=s.repeat_set,
                    status=SCHEDULE_ENABLED if s.is_enabled else SCHEDULE_DISABLED,
                )
                for s in schedules
            ]
            # Update cached counts
            self._enabled_count = sum(
                1 for s in self._schedules_cache if s["status"] == SCHEDULE_ENABLED
            )
            self._disabled_count = sum(
                1 for s in self._schedules_cache if s["status"] == SCHEDULE_DISABLED
            )
        except Exception as err:
            _LOGGER.debug("Failed to get schedules for %s: %s", self.device_id, err)

    @property
    def native_value(self) -> int:
        """Return the number of active schedules."""
        return self._enabled_count

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional state attributes."""
        schedule_info: list[ScheduleInfo] = [
            ScheduleInfo(
                id=schedule.get("id"),
                time=format_schedule_time(
                    schedule.get("hour", 0), schedule.get("minute", 0)
                ),
                duration=schedule.get("duration", 0),
                repeat=schedule.get("repeatSet", ""),
                status="enabled"
                if schedule.get("status") == SCHEDULE_ENABLED
                else "disabled",
            )
            for schedule in self._schedules_cache
        ]

        return {
            "schedules": schedule_info,
            "total_schedules": len(self._schedules_cache),
            "enabled_schedules": self._enabled_count,
            "disabled_schedules": self._disabled_count,
        }


class MoogoDeviceLastSpraySensor(MoogoDeviceEntity, SensorEntity):
    """Device last spray information sensor."""

    def __init__(
        self, coordinator: MoogoCoordinator, device_id: str, device_name: str
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, device_id, device_name)
        self._attr_name = "Last Spray"
        self._attr_unique_id = f"{device_id}_last_spray"
        self._attr_icon = ICON_LAST_SPRAY
        self._attr_device_class = SensorDeviceClass.TIMESTAMP
        self._attr_entity_registry_enabled_default = False

    @property
    def native_value(self) -> datetime | None:
        """Return the last spray timestamp."""
        device = self.device
        if device and device.status:
            return convert_api_timestamp(device.status.latest_spraying_end)
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional state attributes."""
        device = self.device
        if device and device.status:
            return {
                "last_spray_duration": device.status.latest_spraying_duration or 0,
                "run_status": 1 if device.is_running else 0,
                "spray_status": "running" if device.is_running else "stopped",
            }
        return {"last_spray_duration": 0, "run_status": 0, "spray_status": "unknown"}
