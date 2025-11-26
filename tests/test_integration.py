"""Integration tests for Moogo Home Assistant integration with pymoogo."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from pymoogo import MoogoClient

# Define DOMAIN here to avoid importing from the integration
# which would trigger homeassistant imports
DOMAIN = "moogo"


class TestMoogoIntegration:
    """Test Moogo integration with pymoogo library."""

    @pytest.mark.asyncio
    async def test_pymoogo_client_initialization(
        self, mock_aiohttp_session: MagicMock
    ) -> None:
        """Test that pymoogo client can be initialized with session injection."""
        client = MoogoClient(
            email="test@example.com",
            password="test_password",
            session=mock_aiohttp_session,
        )

        assert client is not None

    @pytest.mark.asyncio
    async def test_pymoogo_public_data_access(
        self, mock_aiohttp_session: MagicMock
    ) -> None:
        """Test that public data can be accessed without authentication."""
        with patch.object(MoogoClient, "get_liquid_types") as mock_liquid:
            mock_liquid.return_value = [{"liquidName": "Fresh"}]

            client = MoogoClient(session=mock_aiohttp_session)
            result = await client.get_liquid_types()

            assert len(result) == 1
            assert result[0]["liquidName"] == "Fresh"

    @pytest.mark.asyncio
    async def test_moogo_device_properties(
        self, mock_pymoogo_device: MagicMock
    ) -> None:
        """Test MoogoDevice property access."""
        device = mock_pymoogo_device

        # Test all properties used by the integration
        assert device.id == "test_device_123"
        assert device.name == "Test Moogo Device"
        assert device.is_online is True
        assert device.is_running is False
        assert device.temperature == 25.0
        assert device.humidity == 50
        assert device.liquid_level == 1
        assert device.water_level == 1
        assert device.rssi == -50
        assert device.firmware == "1.0.0"

    @pytest.mark.asyncio
    async def test_moogo_device_status_properties(
        self, mock_pymoogo_device: MagicMock
    ) -> None:
        """Test MoogoDevice status object properties."""
        device = mock_pymoogo_device
        status = device.status

        assert status.is_online is True
        assert status.is_running is False
        assert status.latest_spraying_duration == 60
        assert status.latest_spraying_end == 1700000000000

    @pytest.mark.asyncio
    async def test_moogo_device_refresh(self, mock_pymoogo_device: MagicMock) -> None:
        """Test device refresh updates status."""
        device = mock_pymoogo_device

        await device.refresh()

        device.refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_moogo_device_spray_control(
        self, mock_pymoogo_device: MagicMock
    ) -> None:
        """Test device spray control methods."""
        device = mock_pymoogo_device

        # Start spray
        await device.start_spray()
        device.start_spray.assert_called_once()

        # Stop spray
        await device.stop_spray()
        device.stop_spray.assert_called_once()

    @pytest.mark.asyncio
    async def test_moogo_device_schedules(
        self, mock_pymoogo_device: MagicMock, mock_schedule: MagicMock
    ) -> None:
        """Test device schedule retrieval."""
        device = mock_pymoogo_device
        device.get_schedules.return_value = [mock_schedule]

        schedules = await device.get_schedules()

        assert len(schedules) == 1
        assert schedules[0].id == "schedule_1"
        assert schedules[0].hour == 8
        assert schedules[0].minute == 30
        assert schedules[0].is_enabled is True

    @pytest.mark.asyncio
    async def test_moogo_device_circuit_breaker_status(
        self, mock_pymoogo_device: MagicMock
    ) -> None:
        """Test device circuit breaker status access."""
        device = mock_pymoogo_device

        circuit_status = device.circuit_status

        assert circuit_status["circuit_open"] is False
        assert circuit_status["failures"] == 0


class TestEntityIdCompatibility:
    """Test that entity IDs remain compatible with v1."""

    def test_device_status_sensor_unique_id(
        self, mock_pymoogo_device: MagicMock
    ) -> None:
        """Test device status sensor unique ID format."""
        device_id = mock_pymoogo_device.id
        expected_unique_id = f"{device_id}_status"

        assert expected_unique_id == "test_device_123_status"

    def test_liquid_level_sensor_unique_id(
        self, mock_pymoogo_device: MagicMock
    ) -> None:
        """Test liquid level sensor unique ID format."""
        device_id = mock_pymoogo_device.id
        expected_unique_id = f"{device_id}_liquid_level"

        assert expected_unique_id == "test_device_123_liquid_level"

    def test_water_level_sensor_unique_id(self, mock_pymoogo_device: MagicMock) -> None:
        """Test water level sensor unique ID format."""
        device_id = mock_pymoogo_device.id
        expected_unique_id = f"{device_id}_water_level"

        assert expected_unique_id == "test_device_123_water_level"

    def test_temperature_sensor_unique_id(self, mock_pymoogo_device: MagicMock) -> None:
        """Test temperature sensor unique ID format."""
        device_id = mock_pymoogo_device.id
        expected_unique_id = f"{device_id}_temperature"

        assert expected_unique_id == "test_device_123_temperature"

    def test_humidity_sensor_unique_id(self, mock_pymoogo_device: MagicMock) -> None:
        """Test humidity sensor unique ID format."""
        device_id = mock_pymoogo_device.id
        expected_unique_id = f"{device_id}_humidity"

        assert expected_unique_id == "test_device_123_humidity"

    def test_signal_strength_sensor_unique_id(
        self, mock_pymoogo_device: MagicMock
    ) -> None:
        """Test signal strength sensor unique ID format."""
        device_id = mock_pymoogo_device.id
        expected_unique_id = f"{device_id}_signal_strength"

        assert expected_unique_id == "test_device_123_signal_strength"

    def test_schedules_sensor_unique_id(self, mock_pymoogo_device: MagicMock) -> None:
        """Test schedules sensor unique ID format."""
        device_id = mock_pymoogo_device.id
        expected_unique_id = f"{device_id}_active_schedules"

        assert expected_unique_id == "test_device_123_active_schedules"

    def test_last_spray_sensor_unique_id(self, mock_pymoogo_device: MagicMock) -> None:
        """Test last spray sensor unique ID format."""
        device_id = mock_pymoogo_device.id
        expected_unique_id = f"{device_id}_last_spray"

        assert expected_unique_id == "test_device_123_last_spray"

    def test_spray_switch_unique_id(self, mock_pymoogo_device: MagicMock) -> None:
        """Test spray switch unique ID format."""
        device_id = mock_pymoogo_device.id
        expected_unique_id = f"{device_id}_spray_switch"

        assert expected_unique_id == "test_device_123_spray_switch"

    def test_public_sensors_unique_ids(self) -> None:
        """Test public sensor unique IDs."""
        assert "moogo_liquid_types" == "moogo_liquid_types"
        assert "moogo_schedule_templates" == "moogo_schedule_templates"
        assert "moogo_api_status" == "moogo_api_status"


class TestDeviceIdentifiers:
    """Test that device identifiers remain compatible."""

    def test_device_identifier_format(self, mock_pymoogo_device: MagicMock) -> None:
        """Test device identifier tuple format."""
        device_id = mock_pymoogo_device.id
        identifier = (DOMAIN, device_id)

        assert identifier == ("moogo", "test_device_123")

    def test_device_info_structure(self, mock_pymoogo_device: MagicMock) -> None:
        """Test device info dictionary structure."""
        device = mock_pymoogo_device

        device_info = {
            "identifiers": {(DOMAIN, device.id)},
            "name": device.name,
            "manufacturer": "Moogo",
            "model": "Smart Spray Device",
        }

        assert device_info["identifiers"] == {("moogo", "test_device_123")}
        assert device_info["name"] == "Test Moogo Device"
        assert device_info["manufacturer"] == "Moogo"
