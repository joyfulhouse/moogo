"""Diagnostics support for Moogo integration."""
from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import CONF_EMAIL, CONF_PASSWORD

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
    coordinator = entry.runtime_data

    # Gather diagnostic data
    diagnostics_data = {
        "config_entry": {
            "title": entry.title,
            "unique_id": entry.unique_id,
            "version": entry.version,
            "domain": entry.domain,
        },
        "coordinator_data": {
            "last_update_success": coordinator.last_update_success,
            "last_update_time": coordinator.last_update_success_time.isoformat()
            if coordinator.last_update_success_time
            else None,
            "update_interval": coordinator.update_interval.total_seconds(),
            "auth_status": coordinator.data.get("auth_status", "unknown"),
        },
        "api_info": {
            "is_authenticated": coordinator.api.is_authenticated,
            "base_url": coordinator.api.base_url,
        },
        "integration_data": {
            "devices_count": len(coordinator.data.get("devices", [])),
            "liquid_types_count": len(coordinator.data.get("liquid_types", [])),
            "schedules_count": len(coordinator.data.get("recommended_schedules", [])),
        },
    }

    # Add device information if authenticated
    if coordinator.api.is_authenticated and coordinator.data.get("devices"):
        devices_info = []
        for device in coordinator.data.get("devices", []):
            device_status = coordinator.data.get("device_statuses", {}).get(
                device.get("deviceId")
            )
            device_info = {
                "device_name": device.get("deviceName", "Unknown"),
                "online_status": device_status.get("onlineStatus") if device_status else None,
                "firmware": device_status.get("firmware") if device_status else None,
                "model": device.get("model", "Unknown"),
            }
            devices_info.append(device_info)

        diagnostics_data["devices"] = devices_info

    # Redact sensitive information
    return async_redact_data(diagnostics_data, TO_REDACT)
