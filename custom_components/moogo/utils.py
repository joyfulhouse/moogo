"""Utility functions for the Moogo integration."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from .const import TIMESTAMP_MS_THRESHOLD

_LOGGER = logging.getLogger(__name__)


def convert_api_timestamp(timestamp: int | float | None) -> datetime | None:
    """Convert API timestamp (milliseconds or seconds) to datetime.

    The Moogo API may return timestamps in either milliseconds or seconds.
    This function detects the format and converts accordingly.

    Args:
        timestamp: Unix timestamp in milliseconds or seconds, or None.

    Returns:
        datetime object in UTC timezone, or None if conversion fails.
    """
    if timestamp is None or timestamp <= 0:
        return None

    try:
        # Timestamps greater than threshold are in milliseconds
        if timestamp > TIMESTAMP_MS_THRESHOLD:
            result = datetime.fromtimestamp(timestamp / 1000, tz=UTC)
            _LOGGER.debug("Converted milliseconds %s to %s", timestamp, result)
            return result

        # Otherwise assume seconds
        result = datetime.fromtimestamp(timestamp, tz=UTC)
        _LOGGER.debug("Converted seconds %s to %s", timestamp, result)
        return result

    except (ValueError, OSError, OverflowError) as err:
        _LOGGER.warning("Invalid timestamp format: %s, error: %s", timestamp, err)
        return None


def get_level_status(level: int | None) -> str:
    """Convert numeric level to status string.

    Args:
        level: Numeric level value (1 = OK, 0 = Empty).

    Returns:
        Status string ('OK', 'Empty', or 'Unknown').
    """
    from .const import (
        LEVEL_EMPTY,
        LEVEL_OK,
        LEVEL_STATUS_EMPTY,
        LEVEL_STATUS_OK,
        LEVEL_STATUS_UNKNOWN,
    )

    if level == LEVEL_OK:
        return LEVEL_STATUS_OK
    if level == LEVEL_EMPTY:
        return LEVEL_STATUS_EMPTY
    return LEVEL_STATUS_UNKNOWN


def build_device_info(
    device_id: str,
    device_name: str,
    firmware: str | None = None,
) -> dict[str, Any]:
    """Build standard device info dictionary.

    Args:
        device_id: Unique device identifier.
        device_name: Human-readable device name.
        firmware: Optional firmware version.

    Returns:
        Device info dictionary for HomeAssistant device registry.
    """
    from .const import DEFAULT_MANUFACTURER, DEFAULT_MODEL, DOMAIN

    device_info: dict[str, Any] = {
        "identifiers": {(DOMAIN, device_id)},
        "name": device_name,
        "manufacturer": DEFAULT_MANUFACTURER,
        "model": DEFAULT_MODEL,
    }

    if firmware:
        device_info["sw_version"] = firmware

    return device_info


def format_schedule_time(hour: int, minute: int) -> str:
    """Format schedule time as HH:MM string.

    Args:
        hour: Hour (0-23).
        minute: Minute (0-59).

    Returns:
        Formatted time string.
    """
    return f"{hour:02d}:{minute:02d}"


def safe_float(value: Any) -> float | None:
    """Safely convert value to float.

    Args:
        value: Value to convert.

    Returns:
        Float value or None if conversion fails or value is None.
    """
    if value is None:
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None


def safe_int(value: Any) -> int | None:
    """Safely convert value to int.

    Args:
        value: Value to convert.

    Returns:
        Integer value or None if conversion fails or value is None.
    """
    if value is None:
        return None
    try:
        return int(value)
    except (ValueError, TypeError):
        return None
