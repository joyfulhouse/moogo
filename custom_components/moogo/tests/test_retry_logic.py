"""Tests for retry logic with exponential backoff and jitter."""

import asyncio
import sys
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

import pytest

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from moogo_api.client import (
    MoogoAuthError,
    MoogoDeviceError,
    MoogoRateLimitError,
    retry_with_backoff,
)


class TestRetryWithBackoff:
    """Test retry_with_backoff decorator."""

    @pytest.mark.asyncio
    async def test_successful_first_attempt(self):
        """Test that successful calls don't retry."""
        call_count = 0

        @retry_with_backoff(max_attempts=3)
        async def successful_func():
            nonlocal call_count
            call_count += 1
            return "success"

        result = await successful_func()
        assert result == "success"
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_retry_on_transient_failure(self):
        """Test retry behavior on transient failures."""
        call_count = 0

        @retry_with_backoff(max_attempts=3, initial_delay=0.1)
        async def failing_then_success():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise MoogoDeviceError("Transient error")
            return "success"

        start_time = datetime.now()
        result = await failing_then_success()
        elapsed = (datetime.now() - start_time).total_seconds()

        assert result == "success"
        assert call_count == 3
        # Should have waited at least 0.1 + 0.2 = 0.3 seconds
        assert elapsed >= 0.3

    @pytest.mark.asyncio
    async def test_max_retries_exceeded(self):
        """Test that max retries is respected."""
        call_count = 0

        @retry_with_backoff(max_attempts=3, initial_delay=0.05)
        async def always_fails():
            nonlocal call_count
            call_count += 1
            raise MoogoDeviceError("Persistent error")

        with pytest.raises(MoogoDeviceError, match="Persistent error"):
            await always_fails()

        assert call_count == 3

    @pytest.mark.asyncio
    async def test_rate_limit_no_retry(self):
        """Test that rate limit errors are not retried."""
        call_count = 0

        @retry_with_backoff(
            max_attempts=3, retry_on=(MoogoRateLimitError, MoogoDeviceError)
        )
        async def rate_limited():
            nonlocal call_count
            call_count += 1
            raise MoogoRateLimitError("Rate limited")

        with pytest.raises(MoogoRateLimitError, match="Rate limited"):
            await rate_limited()

        # Should not retry on rate limit
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_device_offline_extended_retries(self):
        """Test that device offline errors get extended retry attempts."""
        call_count = 0

        @retry_with_backoff(
            max_attempts=3,
            initial_delay=0.05,
            device_offline_max_attempts=5,
            retry_on=(MoogoDeviceError,),
        )
        async def device_offline():
            nonlocal call_count
            call_count += 1
            raise MoogoDeviceError("Device offline: network error")

        with pytest.raises(MoogoDeviceError):
            await device_offline()

        # Should use extended attempts for offline errors
        assert call_count == 5

    @pytest.mark.asyncio
    async def test_jitter_is_applied(self):
        """Test that jitter is added to delays."""

        @retry_with_backoff(max_attempts=3, initial_delay=0.1, backoff_factor=2.0)
        async def track_delays():
            raise MoogoDeviceError("Error")

        with patch("asyncio.sleep") as mock_sleep:
            mock_sleep.return_value = asyncio.coroutine(lambda: None)()
            try:
                await track_delays()
            except MoogoDeviceError:
                pass

            # Get all sleep calls
            sleep_calls = [call[0][0] for call in mock_sleep.call_args_list]

            # First delay should be 0.1 + jitter (0-1), so between 0.1 and 1.1
            assert 0.1 <= sleep_calls[0] <= 1.1

            # Second delay should be 0.2 + jitter (0-1), so between 0.2 and 1.2
            assert 0.2 <= sleep_calls[1] <= 1.2

    @pytest.mark.asyncio
    async def test_max_delay_cap(self):
        """Test that max_delay parameter caps the retry delay."""

        @retry_with_backoff(
            max_attempts=5,
            initial_delay=10.0,
            backoff_factor=2.0,
            max_delay=5.0,  # Cap at 5 seconds
        )
        async def capped_delays():
            raise MoogoDeviceError("Error")

        with patch("asyncio.sleep") as mock_sleep:
            mock_sleep.return_value = asyncio.coroutine(lambda: None)()
            try:
                await capped_delays()
            except MoogoDeviceError:
                pass

            # All delays should be capped at max_delay (5.0)
            sleep_calls = [call[0][0] for call in mock_sleep.call_args_list]
            for delay in sleep_calls:
                assert delay <= 5.0

    @pytest.mark.asyncio
    async def test_unexpected_error_no_retry(self):
        """Test that unexpected errors are not retried."""
        call_count = 0

        @retry_with_backoff(max_attempts=3, retry_on=(MoogoDeviceError,))
        async def unexpected_error():
            nonlocal call_count
            call_count += 1
            raise ValueError("Unexpected error")

        with pytest.raises(ValueError, match="Unexpected error"):
            await unexpected_error()

        # Should not retry on unexpected errors
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_auth_error_retry(self):
        """Test that auth errors are retried when specified."""
        call_count = 0

        @retry_with_backoff(
            max_attempts=3, initial_delay=0.05, retry_on=(MoogoAuthError,)
        )
        async def auth_fails():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise MoogoAuthError("Auth failed")
            return "success"

        result = await auth_fails()
        assert result == "success"
        assert call_count == 2
