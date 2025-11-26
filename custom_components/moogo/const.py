"""Constants for the Moogo integration."""

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
