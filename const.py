"""Constants for the Moogo integration."""

from typing import Final

DOMAIN: Final = "moogo"

# Configuration keys
CONF_EMAIL: Final = "email"
CONF_PASSWORD: Final = "password"
CONF_API_BASE_URL: Final = "api_base_url"

# Default API endpoints
DEFAULT_API_BASE_URL: Final = "https://api.moogo.com/"
TEST_API_BASE_URL: Final = "https://api-test.moogo.com/"

# Update intervals
DEFAULT_UPDATE_INTERVAL: Final = 30  # seconds
PUBLIC_DATA_UPDATE_INTERVAL: Final = 3600  # 1 hour for public data

# Device attributes
ATTR_DEVICE_ID: Final = "device_id"
ATTR_DEVICE_NAME: Final = "device_name"
ATTR_ONLINE_STATUS: Final = "online_status"
ATTR_RUN_STATUS: Final = "run_status"
ATTR_TEMPERATURE: Final = "temperature"
ATTR_HUMIDITY: Final = "humidity"
ATTR_RSSI: Final = "rssi"
ATTR_WATER_LEVEL: Final = "water_level"
ATTR_LIQUID_LEVEL: Final = "liquid_level"
ATTR_MIX_RATIO: Final = "mix_ratio"
ATTR_FIRMWARE_VERSION: Final = "firmware_version"

# API endpoints
API_LOGIN: Final = "v1/user/login"
API_DEVICES: Final = "v1/devices"
API_LIQUID_TYPES: Final = "v1/liquid"
API_SCHEDULES: Final = "v1/devices/schedules"
API_DEVICE_STATUS: Final = "v1/devices/{device_id}"
API_START_SPRAY: Final = "v1/devices/{device_id}/start"
API_STOP_SPRAY: Final = "v1/devices/{device_id}/stop"

# Authentication constants
TOKEN_EXPIRY_BUFFER: Final = 300  # Refresh token 5 minutes before expiry
MAX_RETRY_ATTEMPTS: Final = 3
