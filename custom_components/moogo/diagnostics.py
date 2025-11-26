"""Diagnostics support for Moogo integration."""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import CONF_EMAIL, CONF_PASSWORD
from .coordinator import MoogoCoordinator

# Keys to redact from diagnostics data
TO_REDACT = {
    CONF_EMAIL,
    CONF_PASSWORD,
    "token",
    "deviceId",
    "userId",
    "email",
    "password",
}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinator: MoogoCoordinator = entry.runtime_data

    # Gather diagnostic data
    diagnostics_data: dict[str, Any] = {
        "config_entry": {
            "title": entry.title,
            "unique_id": entry.unique_id,
            "version": entry.version,
            "domain": entry.domain,
        },
        "coordinator_data": {
            "last_update_success": coordinator.last_update_success,
            "last_update_time": (
                coordinator.last_update_success_time.isoformat()
                if hasattr(coordinator, "last_update_success_time")
                and coordinator.last_update_success_time
                else None
            ),
            "update_interval": (
                coordinator.update_interval.total_seconds()
                if coordinator.update_interval
                else None
            ),
            "auth_status": coordinator.data.get("auth_status", "unknown"),
        },
        "api_info": {
            "is_authenticated": coordinator.client.is_authenticated,
        },
        "integration_data": {
            "devices_count": len(coordinator.data.get("devices", [])),
            "liquid_types_count": len(coordinator.data.get("liquid_types", [])),
            "schedules_count": len(coordinator.data.get("recommended_schedules", [])),
        },
    }

    # Add device information if authenticated
    if coordinator.client.is_authenticated and coordinator.data.get("devices"):
        devices_info = []
        for device_data in coordinator.data.get("devices", []):
            device_id = device_data.get("deviceId")
            device = coordinator.get_device(device_id) if device_id else None

            device_info: dict[str, Any] = {
                "device_name": device_data.get("deviceName", "Unknown"),
                "model": device_data.get("model", "Unknown"),
            }

            if device:
                device_info.update(
                    {
                        "is_online": device.is_online,
                        "is_running": device.is_running,
                        "firmware": device.firmware,
                        "temperature": device.temperature,
                        "humidity": device.humidity,
                        "liquid_level": device.liquid_level,
                        "water_level": device.water_level,
                        "rssi": device.rssi,
                    }
                )

                # Add circuit breaker status
                circuit_status = device.circuit_status
                if circuit_status:
                    device_info["circuit_breaker"] = {
                        "is_open": circuit_status.get("circuit_open", False),
                        "failures": circuit_status.get("failures", 0),
                    }

            devices_info.append(device_info)

        diagnostics_data["devices"] = devices_info

    # Redact sensitive information
    result = async_redact_data(diagnostics_data, TO_REDACT)
    return dict(result) if result else {}
