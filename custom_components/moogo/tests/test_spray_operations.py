"""Tests for spray operations with pre-flight checks."""

import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from moogo_api.client import MoogoAuthError, MoogoClient, MoogoDeviceError


class TestSprayOperations:
    """Test spray operations with improved error handling."""

    @pytest.mark.asyncio
    async def test_start_spray_requires_authentication(self):
        """Test that start_spray requires authentication."""
        client = MoogoClient()

        with pytest.raises(MoogoAuthError, match="Authentication required"):
            await client.start_spray("device_123")

    @pytest.mark.asyncio
    async def test_stop_spray_requires_authentication(self):
        """Test that stop_spray requires authentication."""
        client = MoogoClient()

        with pytest.raises(MoogoAuthError, match="Authentication required"):
            await client.stop_spray("device_123")

    @pytest.mark.asyncio
    async def test_start_spray_with_preflight_online(self):
        """Test start_spray with pre-flight check showing device online."""
        client = MoogoClient(email="test@example.com", password="password")
        client._authenticated = True
        client._token = "test_token"

        with patch.object(client, "_request", new=AsyncMock()) as mock_request:
            # Mock responses
            mock_request.side_effect = [
                # Pre-flight status check
                {"code": 0, "data": {"onlineStatus": 1}},
                # Actual start spray call
                {"code": 0, "data": {"code": 0}},
            ]

            result = await client.start_spray("device_123")

            assert result is True
            assert mock_request.call_count == 2

    @pytest.mark.asyncio
    async def test_start_spray_with_preflight_offline_warning(self):
        """Test start_spray with pre-flight check showing device offline."""
        client = MoogoClient(email="test@example.com", password="password")
        client._authenticated = True
        client._token = "test_token"

        with patch.object(client, "_request", new=AsyncMock()) as mock_request:
            # Mock responses
            mock_request.side_effect = [
                # Pre-flight status check shows offline
                {"code": 0, "data": {"onlineStatus": 0}},
                # But spray command succeeds anyway (device waking up)
                {"code": 0, "data": {"code": 0}},
            ]

            # Should log warning but still attempt
            result = await client.start_spray("device_123")

            assert result is True

    @pytest.mark.asyncio
    async def test_start_spray_preflight_failure_continues(self):
        """Test that pre-flight check failure doesn't prevent spray attempt."""
        client = MoogoClient(email="test@example.com", password="password")
        client._authenticated = True
        client._token = "test_token"

        with patch.object(client, "get_device_status", new=AsyncMock()) as mock_status:
            # Pre-flight check fails
            mock_status.side_effect = Exception("Network error")

            with patch.object(client, "_request", new=AsyncMock()) as mock_request:
                # But spray command succeeds
                mock_request.return_value = {"code": 0, "data": {"code": 0}}

                result = await client.start_spray("device_123")

                # Should still succeed despite pre-flight failure
                assert result is True

    @pytest.mark.asyncio
    async def test_stop_spray_with_preflight(self):
        """Test stop_spray with pre-flight check."""
        client = MoogoClient(email="test@example.com", password="password")
        client._authenticated = True
        client._token = "test_token"

        with patch.object(client, "_request", new=AsyncMock()) as mock_request:
            # Mock responses
            mock_request.side_effect = [
                # Pre-flight status check
                {"code": 0, "data": {"onlineStatus": 1}},
                # Actual stop spray call
                {"code": 0, "data": {"code": 0}},
            ]

            result = await client.stop_spray("device_123")

            assert result is True

    @pytest.mark.asyncio
    async def test_start_spray_records_success(self):
        """Test that successful spray records success for circuit breaker."""
        client = MoogoClient(email="test@example.com", password="password")
        client._authenticated = True
        client._token = "test_token"

        # Pre-populate with a failure
        error = MoogoDeviceError("Previous error")
        client._record_device_failure("device_123", error)

        with patch.object(client, "_request", new=AsyncMock()) as mock_request:
            mock_request.side_effect = [
                # Pre-flight status check
                {"code": 0, "data": {"onlineStatus": 1}},
                # Successful spray
                {"code": 0, "data": {"code": 0}},
            ]

            await client.start_spray("device_123")

            # Failures should be reset
            assert client._device_circuit_breakers["device_123"]["failures"] == 0
            assert (
                client._device_circuit_breakers["device_123"]["last_success"]
                is not None
            )

    @pytest.mark.asyncio
    async def test_start_spray_records_failure(self):
        """Test that failed spray records failure for circuit breaker."""
        client = MoogoClient(email="test@example.com", password="password")
        client._authenticated = True
        client._token = "test_token"

        with patch.object(client, "_request", new=AsyncMock()) as mock_request:
            # Mock device offline error
            mock_request.side_effect = MoogoDeviceError("Device offline")

            with patch.object(
                client, "get_device_status", new=AsyncMock()
            ) as mock_status:
                mock_status.return_value = {"onlineStatus": 0}

                try:
                    await client.start_spray("device_123")
                except MoogoDeviceError:
                    pass

        # Failures should be recorded (note: retry will cause multiple)
        assert "device_123" in client._device_circuit_breakers
        assert client._device_circuit_breakers["device_123"]["failures"] > 0

    @pytest.mark.asyncio
    async def test_start_spray_with_mode_parameter(self):
        """Test start_spray with mode parameter."""
        client = MoogoClient(email="test@example.com", password="password")
        client._authenticated = True
        client._token = "test_token"

        with patch.object(client, "_request", new=AsyncMock()) as mock_request:
            mock_request.side_effect = [
                # Pre-flight
                {"code": 0, "data": {"onlineStatus": 1}},
                # Spray with mode
                {"code": 0, "data": {"code": 0}},
            ]

            await client.start_spray("device_123", mode="manual")

            # Check that mode was passed in payload
            spray_call = mock_request.call_args_list[1]
            assert spray_call[1]["json"]["mode"] == "manual"

    @pytest.mark.asyncio
    async def test_stop_spray_with_mode_parameter(self):
        """Test stop_spray with mode parameter."""
        client = MoogoClient(email="test@example.com", password="password")
        client._authenticated = True
        client._token = "test_token"

        with patch.object(client, "_request", new=AsyncMock()) as mock_request:
            mock_request.side_effect = [
                # Pre-flight
                {"code": 0, "data": {"onlineStatus": 1}},
                # Stop with mode
                {"code": 0, "data": {"code": 0}},
            ]

            await client.stop_spray("device_123", mode="manual_stop")

            # Check that mode was passed in payload
            spray_call = mock_request.call_args_list[1]
            assert spray_call[1]["json"]["mode"] == "manual_stop"

    @pytest.mark.asyncio
    async def test_retry_configuration_for_spray_operations(self):
        """Test that spray operations use correct retry configuration."""
        client = MoogoClient(email="test@example.com", password="password")
        client._authenticated = True
        client._token = "test_token"

        call_count = 0

        async def failing_request(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                # First 2 calls are pre-flight checks
                return {"code": 0, "data": {"onlineStatus": 0}}
            raise MoogoDeviceError("Device offline: network error")

        with patch.object(client, "_request", new=AsyncMock()) as mock_request:
            mock_request.side_effect = failing_request

            try:
                await client.start_spray("device_123")
            except MoogoDeviceError:
                pass

            # Should have retried 5 times (extended for device offline)
            # Plus pre-flight checks on each attempt
            # Total: 5 spray attempts + 5 pre-flight checks = 10 calls
            assert call_count >= 5  # At minimum, spray was attempted 5 times
