"""Constants for the Moogo integration."""

from __future__ import annotations

from typing import Final

DOMAIN: Final = "moogo"

# Configuration keys
CONF_EMAIL: Final = "email"
CONF_PASSWORD: Final = "password"

# Update intervals (seconds)
DEFAULT_UPDATE_INTERVAL: Final = 30  # For authenticated users
PUBLIC_DATA_UPDATE_INTERVAL: Final = 3600  # 1 hour for public data only

# Device attributes (for compatibility)
ATTR_DEVICE_ID: Final = "device_id"
ATTR_DEVICE_NAME: Final = "device_name"

# Level status values from API
LEVEL_OK: Final = 1
LEVEL_EMPTY: Final = 0

# Level status display strings
LEVEL_STATUS_OK: Final = "OK"
LEVEL_STATUS_EMPTY: Final = "Empty"
LEVEL_STATUS_UNKNOWN: Final = "Unknown"

# Device status display strings
STATUS_ONLINE: Final = "Online"
STATUS_OFFLINE: Final = "Offline"
STATUS_UNKNOWN: Final = "Unknown"

# API status display strings
API_STATUS_CONNECTED: Final = "Connected"
API_STATUS_DISCONNECTED: Final = "Disconnected"

# Authentication status
AUTH_STATUS_AUTHENTICATED: Final = "authenticated"
AUTH_STATUS_PUBLIC_ONLY: Final = "public_only"

# Timestamp threshold for milliseconds detection
# Timestamps greater than this are in milliseconds (roughly year 2001)
TIMESTAMP_MS_THRESHOLD: Final = 1_000_000_000_000

# Schedule status values
SCHEDULE_ENABLED: Final = 1
SCHEDULE_DISABLED: Final = 0

# Default device info
DEFAULT_MANUFACTURER: Final = "Moogo"
DEFAULT_MODEL: Final = "Smart Spray Device"

# Entity icons
ICON_LIQUID_TYPES: Final = "mdi:bottle-wine"
ICON_SCHEDULE_TEMPLATES: Final = "mdi:calendar-clock"
ICON_API_STATUS: Final = "mdi:api"
ICON_DEVICE_STATUS: Final = "mdi:power-settings"
ICON_LIQUID_LEVEL: Final = "mdi:cup-water"
ICON_WATER_LEVEL: Final = "mdi:water-percent"
ICON_SCHEDULES: Final = "mdi:calendar-check"
ICON_LAST_SPRAY: Final = "mdi:spray-bottle"
ICON_SPRAY_SWITCH: Final = "mdi:spray"

# Logging messages
LOG_DEVICE_ONLINE: Final = "Device %s (%s) is now ONLINE"
LOG_DEVICE_OFFLINE: Final = "Device %s (%s) is now OFFLINE"
