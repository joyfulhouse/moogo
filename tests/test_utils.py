"""Tests for Moogo utility functions."""

from __future__ import annotations

from datetime import UTC, datetime

from custom_components.moogo.utils import (
    build_device_info,
    convert_api_timestamp,
    format_schedule_time,
    get_level_status,
    safe_float,
    safe_int,
)


class TestConvertApiTimestamp:
    """Tests for convert_api_timestamp utility function."""

    def test_milliseconds_timestamp(self) -> None:
        """Test conversion of millisecond timestamp."""
        # Timestamp in milliseconds (Nov 14, 2023 22:13:20 UTC)
        timestamp_ms = 1700000000000
        result = convert_api_timestamp(timestamp_ms)

        assert result is not None
        assert isinstance(result, datetime)
        assert result.tzinfo == UTC
        assert result.year == 2023
        assert result.month == 11

    def test_seconds_timestamp(self) -> None:
        """Test conversion of seconds timestamp."""
        # Timestamp in seconds (Jan 1, 2024 00:00:00 UTC)
        timestamp_s = 1704067200
        result = convert_api_timestamp(timestamp_s)

        assert result is not None
        assert isinstance(result, datetime)
        assert result.year == 2024
        assert result.month == 1

    def test_none_timestamp(self) -> None:
        """Test handling of None timestamp."""
        result = convert_api_timestamp(None)
        assert result is None

    def test_zero_timestamp(self) -> None:
        """Test handling of zero timestamp."""
        result = convert_api_timestamp(0)
        assert result is None

    def test_negative_timestamp(self) -> None:
        """Test handling of negative timestamp."""
        result = convert_api_timestamp(-1)
        assert result is None


class TestGetLevelStatus:
    """Tests for get_level_status utility function."""

    def test_level_ok(self) -> None:
        """Test OK level status."""
        result = get_level_status(1)
        assert result == "OK"

    def test_level_empty(self) -> None:
        """Test Empty level status."""
        result = get_level_status(0)
        assert result == "Empty"

    def test_level_unknown(self) -> None:
        """Test Unknown level status."""
        result = get_level_status(None)
        assert result == "Unknown"

        result = get_level_status(2)
        assert result == "Unknown"

        result = get_level_status(-1)
        assert result == "Unknown"


class TestFormatScheduleTime:
    """Tests for format_schedule_time utility function."""

    def test_format_time_basic(self) -> None:
        """Test basic time formatting."""
        assert format_schedule_time(8, 30) == "08:30"
        assert format_schedule_time(14, 0) == "14:00"
        assert format_schedule_time(0, 0) == "00:00"
        assert format_schedule_time(23, 59) == "23:59"

    def test_format_time_padding(self) -> None:
        """Test that single digits are zero-padded."""
        assert format_schedule_time(1, 5) == "01:05"
        assert format_schedule_time(9, 9) == "09:09"


class TestSafeFloat:
    """Tests for safe_float utility function."""

    def test_valid_float(self) -> None:
        """Test conversion of valid float values."""
        assert safe_float(25.5) == 25.5
        assert safe_float(0.0) == 0.0
        assert safe_float(-10.5) == -10.5

    def test_int_to_float(self) -> None:
        """Test conversion of integer to float."""
        assert safe_float(25) == 25.0
        assert safe_float(0) == 0.0

    def test_string_to_float(self) -> None:
        """Test conversion of string to float."""
        assert safe_float("25.5") == 25.5
        assert safe_float("0") == 0.0

    def test_none_returns_none(self) -> None:
        """Test that None input returns None."""
        assert safe_float(None) is None

    def test_invalid_string_returns_none(self) -> None:
        """Test that invalid string returns None."""
        assert safe_float("not a number") is None
        assert safe_float("") is None


class TestSafeInt:
    """Tests for safe_int utility function."""

    def test_valid_int(self) -> None:
        """Test conversion of valid int values."""
        assert safe_int(25) == 25
        assert safe_int(0) == 0
        assert safe_int(-10) == -10

    def test_float_to_int(self) -> None:
        """Test conversion of float to int."""
        assert safe_int(25.9) == 25
        assert safe_int(25.1) == 25

    def test_string_to_int(self) -> None:
        """Test conversion of string to int."""
        assert safe_int("25") == 25
        assert safe_int("0") == 0

    def test_none_returns_none(self) -> None:
        """Test that None input returns None."""
        assert safe_int(None) is None

    def test_invalid_string_returns_none(self) -> None:
        """Test that invalid string returns None."""
        assert safe_int("not a number") is None
        assert safe_int("") is None


class TestBuildDeviceInfo:
    """Tests for build_device_info utility function."""

    def test_basic_device_info(self) -> None:
        """Test basic device info without firmware."""
        result = build_device_info("device_123", "Living Room Moogo")

        assert result["identifiers"] == {("moogo", "device_123")}
        assert result["name"] == "Living Room Moogo"
        assert result["manufacturer"] == "Moogo"
        assert result["model"] == "Smart Spray Device"
        assert "sw_version" not in result

    def test_device_info_with_firmware(self) -> None:
        """Test device info with firmware version."""
        result = build_device_info("device_456", "Bedroom Moogo", "1.2.3")

        assert result["identifiers"] == {("moogo", "device_456")}
        assert result["name"] == "Bedroom Moogo"
        assert result["sw_version"] == "1.2.3"
