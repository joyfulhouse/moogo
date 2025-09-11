"""Constants for the Moogo integration."""

DOMAIN = "moogo"

# Configuration keys
CONF_EMAIL = "email"
CONF_PASSWORD = "password"
CONF_API_BASE_URL = "api_base_url"

# Default API endpoints
DEFAULT_API_BASE_URL = "https://api.moogo.com/"
TEST_API_BASE_URL = "https://api-test.moogo.com/"

# Update intervals
DEFAULT_UPDATE_INTERVAL = 30  # seconds
PUBLIC_DATA_UPDATE_INTERVAL = 3600  # 1 hour for public data

# Device attributes
ATTR_DEVICE_ID = "device_id"
ATTR_DEVICE_NAME = "device_name"
ATTR_ONLINE_STATUS = "online_status"
ATTR_RUN_STATUS = "run_status"
ATTR_TEMPERATURE = "temperature"
ATTR_HUMIDITY = "humidity"
ATTR_RSSI = "rssi"
ATTR_WATER_LEVEL = "water_level"
ATTR_LIQUID_LEVEL = "liquid_level"
ATTR_MIX_RATIO = "mix_ratio"
ATTR_FIRMWARE_VERSION = "firmware_version"

# API endpoints
API_LOGIN = "v1/user/login"
API_DEVICES = "v1/devices"
API_LIQUID_TYPES = "v1/liquid"
API_SCHEDULES = "v1/devices/schedules"
API_DEVICE_STATUS = "v1/devices/{device_id}"
API_START_SPRAY = "v1/devices/{device_id}/start"
API_STOP_SPRAY = "v1/devices/{device_id}/stop"

# Authentication constants
TOKEN_EXPIRY_BUFFER = 300  # Refresh token 5 minutes before expiry
MAX_RETRY_ATTEMPTS = 3