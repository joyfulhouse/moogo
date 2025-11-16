"""Tests for retry logic with exponential backoff."""

import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from custom_components.moogo.moogo_api import (
    MoogoAPIError,
    MoogoAuthError,
    MoogoClient,
    MoogoDeviceError,
    MoogoRateLimitError,
    retry_with_backoff,
)


@pytest.mark.asyncio
async def test_retry_decorator_success_first_attempt() -> None:
    """Test that decorator allows successful first attempt."""
    mock_func = AsyncMock(return_value={"status": "success"})
    decorated = retry_with_backoff()(mock_func)

    result = await decorated()

    assert result == {"status": "success"}
    assert mock_func.call_count == 1


@pytest.mark.asyncio
async def test_retry_decorator_success_after_retries() -> None:
    """Test that decorator retries and succeeds on second attempt."""
    mock_func = AsyncMock(
        side_effect=[
            MoogoDeviceError("Device offline"),
            {"status": "success"},
        ]
    )
    decorated = retry_with_backoff(max_attempts=3, initial_delay=0.1)(mock_func)

    result = await decorated()

    assert result == {"status": "success"}
    assert mock_func.call_count == 2


@pytest.mark.asyncio
async def test_retry_decorator_all_attempts_fail() -> None:
    """Test that decorator raises exception after max attempts."""
    mock_func = AsyncMock(side_effect=MoogoDeviceError("Device offline"))
    decorated = retry_with_backoff(max_attempts=3, initial_delay=0.1)(mock_func)

    with pytest.raises(MoogoDeviceError, match="Device offline"):
        await decorated()

    assert mock_func.call_count == 3


@pytest.mark.asyncio
async def test_retry_decorator_exponential_backoff() -> None:
    """Test that decorator implements exponential backoff correctly."""
    mock_func = AsyncMock(side_effect=MoogoDeviceError("Device offline"))
    decorated = retry_with_backoff(
        max_attempts=3, initial_delay=0.1, backoff_factor=2.0
    )(mock_func)

    start_time = asyncio.get_event_loop().time()

    with pytest.raises(MoogoDeviceError):
        await decorated()

    elapsed_time = asyncio.get_event_loop().time() - start_time

    # Should wait: 0.1s + 0.2s = 0.3s total (plus some margin for execution)
    assert elapsed_time >= 0.3
    assert elapsed_time < 0.5  # Allow some margin for test execution


@pytest.mark.asyncio
async def test_retry_decorator_no_retry_on_rate_limit() -> None:
    """Test that decorator does not retry on rate limit errors."""
    mock_func = AsyncMock(side_effect=MoogoRateLimitError("Rate limited"))
    decorated = retry_with_backoff(
        max_attempts=3,
        initial_delay=0.1,
        retry_on=(MoogoDeviceError, MoogoAuthError, MoogoRateLimitError),
    )(mock_func)

    with pytest.raises(MoogoRateLimitError, match="Rate limited"):
        await decorated()

    # Should not retry on rate limit errors
    assert mock_func.call_count == 1


@pytest.mark.asyncio
async def test_retry_decorator_no_retry_on_unexpected_exception() -> None:
    """Test that decorator does not retry on unexpected exceptions."""
    mock_func = AsyncMock(side_effect=ValueError("Unexpected error"))
    decorated = retry_with_backoff(max_attempts=3, initial_delay=0.1)(mock_func)

    with pytest.raises(ValueError, match="Unexpected error"):
        await decorated()

    # Should not retry on unexpected exceptions
    assert mock_func.call_count == 1


@pytest.mark.asyncio
async def test_get_device_status_retry_on_auth_error() -> None:
    """Test that get_device_status retries on authentication errors."""
    client = MoogoClient(email="test@example.com", password="password")
    client._authenticated = True
    client._token = "test_token"

    with patch.object(
        client,
        "_request",
        side_effect=[
            MoogoAuthError("Token expired"),
            {"data": {"deviceId": "123", "onlineStatus": 1}},
        ],
    ):
        result = await client.get_device_status("123")

    assert result["deviceId"] == "123"


@pytest.mark.asyncio
async def test_get_device_status_fails_after_max_retries() -> None:
    """Test that get_device_status fails after max retry attempts."""
    client = MoogoClient(email="test@example.com", password="password")
    client._authenticated = True
    client._token = "test_token"

    with patch.object(
        client, "_request", side_effect=MoogoDeviceError("Device offline")
    ):
        with pytest.raises(MoogoDeviceError, match="Device offline"):
            await client.get_device_status("123")


@pytest.mark.asyncio
async def test_start_spray_retry_on_device_error() -> None:
    """Test that start_spray retries on device errors."""
    client = MoogoClient(email="test@example.com", password="password")
    client._authenticated = True
    client._token = "test_token"

    with patch.object(
        client,
        "_request",
        side_effect=[
            MoogoDeviceError("Device offline"),
            {"data": {"code": 0}},
        ],
    ):
        result = await client.start_spray("123")

    assert result is True


@pytest.mark.asyncio
async def test_start_spray_fails_after_max_retries() -> None:
    """Test that start_spray fails after max retry attempts."""
    client = MoogoClient(email="test@example.com", password="password")
    client._authenticated = True
    client._token = "test_token"

    with patch.object(
        client, "_request", side_effect=MoogoDeviceError("Device offline")
    ):
        with pytest.raises(MoogoDeviceError, match="Device offline"):
            await client.start_spray("123")


@pytest.mark.asyncio
async def test_stop_spray_retry_on_device_error() -> None:
    """Test that stop_spray retries on device errors."""
    client = MoogoClient(email="test@example.com", password="password")
    client._authenticated = True
    client._token = "test_token"

    with patch.object(
        client,
        "_request",
        side_effect=[
            MoogoDeviceError("Device offline"),
            {"data": {"code": 0}},
        ],
    ):
        result = await client.stop_spray("123")

    assert result is True


@pytest.mark.asyncio
async def test_stop_spray_fails_after_max_retries() -> None:
    """Test that stop_spray fails after max retry attempts."""
    client = MoogoClient(email="test@example.com", password="password")
    client._authenticated = True
    client._token = "test_token"

    with patch.object(
        client, "_request", side_effect=MoogoDeviceError("Device offline")
    ):
        with pytest.raises(MoogoDeviceError, match="Device offline"):
            await client.stop_spray("123")


@pytest.mark.asyncio
async def test_retry_decorator_custom_retry_exceptions() -> None:
    """Test that decorator only retries on specified exception types."""
    mock_func = AsyncMock(side_effect=MoogoAPIError("API error"))
    decorated = retry_with_backoff(
        max_attempts=3, initial_delay=0.1, retry_on=(MoogoDeviceError,)
    )(mock_func)

    # Should not retry on MoogoAPIError when only configured for MoogoDeviceError
    with pytest.raises(MoogoAPIError, match="API error"):
        await decorated()

    assert mock_func.call_count == 1


@pytest.mark.asyncio
async def test_retry_decorator_preserves_function_metadata() -> None:
    """Test that decorator preserves function name and docstring."""

    @retry_with_backoff()
    async def test_function() -> str:
        """Test function docstring."""
        return "test"

    assert test_function.__name__ == "test_function"
    assert test_function.__doc__ == "Test function docstring."


@pytest.mark.asyncio
async def test_retry_with_different_backoff_factors() -> None:
    """Test retry with different backoff factors."""
    mock_func = AsyncMock(side_effect=MoogoDeviceError("Device offline"))

    # Test with backoff factor of 3.0
    decorated = retry_with_backoff(
        max_attempts=3, initial_delay=0.1, backoff_factor=3.0
    )(mock_func)

    start_time = asyncio.get_event_loop().time()

    with pytest.raises(MoogoDeviceError):
        await decorated()

    elapsed_time = asyncio.get_event_loop().time() - start_time

    # Should wait: 0.1s + 0.3s = 0.4s total (backoff_factor=3.0)
    assert elapsed_time >= 0.4
    assert elapsed_time < 0.6


@pytest.mark.asyncio
async def test_retry_decorator_with_args_and_kwargs() -> None:
    """Test that decorator properly passes args and kwargs to function."""
    mock_func = AsyncMock(return_value="success")
    decorated = retry_with_backoff()(mock_func)

    result = await decorated("arg1", "arg2", kwarg1="value1", kwarg2="value2")

    assert result == "success"
    mock_func.assert_called_once_with("arg1", "arg2", kwarg1="value1", kwarg2="value2")
