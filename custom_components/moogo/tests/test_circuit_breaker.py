"""Tests for circuit breaker pattern."""

import sys
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from moogo_api.client import MoogoClient, MoogoDeviceError


class TestCircuitBreaker:
    """Test circuit breaker functionality."""

    def test_initial_circuit_state(self):
        """Test that circuit starts closed."""
        client = MoogoClient()
        assert not client._is_circuit_open("device_123")

    def test_record_device_failure(self):
        """Test recording device failures."""
        client = MoogoClient()
        error = MoogoDeviceError("Test error")

        # Record first failure
        client._record_device_failure("device_123", error)

        circuit = client._device_circuit_breakers["device_123"]
        assert circuit["failures"] == 1
        assert circuit["last_failure"] is not None
        assert circuit["last_success"] is None

    def test_circuit_opens_after_threshold(self):
        """Test that circuit opens after threshold failures."""
        client = MoogoClient()
        client._circuit_breaker_threshold = 3
        error = MoogoDeviceError("Test error")

        # Record failures up to threshold
        for _ in range(3):
            client._record_device_failure("device_123", error)

        # Circuit should now be open
        assert client._is_circuit_open("device_123")

    def test_circuit_stays_closed_below_threshold(self):
        """Test that circuit stays closed below threshold."""
        client = MoogoClient()
        client._circuit_breaker_threshold = 5
        error = MoogoDeviceError("Test error")

        # Record failures below threshold
        for _ in range(4):
            client._record_device_failure("device_123", error)

        # Circuit should still be closed
        assert not client._is_circuit_open("device_123")

    def test_record_device_success_resets_failures(self):
        """Test that success resets failure count."""
        client = MoogoClient()
        error = MoogoDeviceError("Test error")

        # Record some failures
        client._record_device_failure("device_123", error)
        client._record_device_failure("device_123", error)

        assert client._device_circuit_breakers["device_123"]["failures"] == 2

        # Record success
        client._record_device_success("device_123")

        circuit = client._device_circuit_breakers["device_123"]
        assert circuit["failures"] == 0
        assert circuit["last_success"] is not None

    def test_circuit_resets_after_timeout(self):
        """Test that circuit auto-resets after timeout period."""
        client = MoogoClient()
        client._circuit_breaker_threshold = 3
        client._circuit_breaker_timeout = timedelta(seconds=5)
        error = MoogoDeviceError("Test error")

        # Open the circuit
        for _ in range(3):
            client._record_device_failure("device_123", error)

        assert client._is_circuit_open("device_123")

        # Simulate timeout by setting last_failure to past
        client._device_circuit_breakers["device_123"]["last_failure"] = (
            datetime.now() - timedelta(seconds=10)
        )

        # Circuit should now be closed
        assert not client._is_circuit_open("device_123")

        # Failure count should be reset
        assert client._device_circuit_breakers["device_123"]["failures"] == 0

    def test_get_device_circuit_status(self):
        """Test getting circuit status for diagnostics."""
        client = MoogoClient()
        error = MoogoDeviceError("Test error")

        # Initially no circuit data
        status = client.get_device_circuit_status("device_123")
        assert status["circuit_open"] is False
        assert status["failures"] == 0
        assert status["last_failure"] is None

        # Record some failures
        client._record_device_failure("device_123", error)
        client._record_device_failure("device_123", error)

        status = client.get_device_circuit_status("device_123")
        assert status["failures"] == 2
        assert status["last_failure"] is not None

    def test_circuit_breaker_per_device(self):
        """Test that circuit breaker is tracked per device."""
        client = MoogoClient()
        client._circuit_breaker_threshold = 2
        error = MoogoDeviceError("Test error")

        # Open circuit for device_1
        client._record_device_failure("device_1", error)
        client._record_device_failure("device_1", error)

        assert client._is_circuit_open("device_1")
        assert not client._is_circuit_open("device_2")

        # Record failure for device_2
        client._record_device_failure("device_2", error)

        assert client._is_circuit_open("device_1")
        assert not client._is_circuit_open("device_2")  # Below threshold

    @pytest.mark.asyncio
    async def test_start_spray_fails_fast_when_circuit_open(self):
        """Test that start_spray fails fast when circuit is open."""
        client = MoogoClient(email="test@example.com", password="password")
        client._authenticated = True
        client._token = "test_token"
        client._circuit_breaker_threshold = 2
        error = MoogoDeviceError("Device offline")

        # Open the circuit
        client._record_device_failure("device_123", error)
        client._record_device_failure("device_123", error)

        # start_spray should fail fast without making API call
        with pytest.raises(MoogoDeviceError, match="circuit breaker is open"):
            await client.start_spray("device_123")

    @pytest.mark.asyncio
    async def test_stop_spray_fails_fast_when_circuit_open(self):
        """Test that stop_spray fails fast when circuit is open."""
        client = MoogoClient(email="test@example.com", password="password")
        client._authenticated = True
        client._token = "test_token"
        client._circuit_breaker_threshold = 2
        error = MoogoDeviceError("Device offline")

        # Open the circuit
        client._record_device_failure("device_123", error)
        client._record_device_failure("device_123", error)

        # stop_spray should fail fast without making API call
        with pytest.raises(MoogoDeviceError, match="circuit breaker is open"):
            await client.stop_spray("device_123")

    @pytest.mark.asyncio
    async def test_successful_spray_resets_circuit(self):
        """Test that successful spray operation resets circuit breaker."""
        client = MoogoClient(email="test@example.com", password="password")
        client._authenticated = True
        client._token = "test_token"
        error = MoogoDeviceError("Device offline")

        # Record a failure
        client._record_device_failure("device_123", error)
        assert client._device_circuit_breakers["device_123"]["failures"] == 1

        # Mock successful spray
        with patch.object(client, "_request", new=AsyncMock()) as mock_request:
            mock_request.return_value = {"code": 0, "data": {"code": 0}}

            # Mock get_device_status (pre-flight check)
            with patch.object(
                client, "get_device_status", new=AsyncMock()
            ) as mock_status:
                mock_status.return_value = {"onlineStatus": 1}

                await client.start_spray("device_123")

        # Failure count should be reset
        assert client._device_circuit_breakers["device_123"]["failures"] == 0

    @pytest.mark.asyncio
    async def test_failed_spray_increments_failures(self):
        """Test that failed spray operation increments failure count."""
        client = MoogoClient(email="test@example.com", password="password")
        client._authenticated = True
        client._token = "test_token"

        # Mock failed spray with device offline
        with patch.object(client, "_request", new=AsyncMock()) as mock_request:
            mock_request.side_effect = MoogoDeviceError("Device offline")

            # Mock get_device_status (pre-flight check)
            with patch.object(
                client, "get_device_status", new=AsyncMock()
            ) as mock_status:
                mock_status.return_value = {"onlineStatus": 0}

                try:
                    await client.start_spray("device_123")
                except MoogoDeviceError:
                    pass

        # Failure should be recorded (note: retry decorator will cause 5 failures)
        assert "device_123" in client._device_circuit_breakers
        assert client._device_circuit_breakers["device_123"]["failures"] > 0
