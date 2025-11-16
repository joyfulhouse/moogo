"""
Moogo API Package

A comprehensive Python client for the Moogo smart spray system API.
Provides authentication, device control, monitoring, and schedule management.
"""

from .client import (
    MoogoAPIError,
    MoogoAuthError,
    MoogoClient,
    MoogoDeviceError,
    MoogoRateLimitError,
    quick_test,
    retry_with_backoff,
)

__version__ = "1.0.1"
__all__ = [
    "MoogoClient",
    "MoogoAPIError",
    "MoogoAuthError",
    "MoogoDeviceError",
    "MoogoRateLimitError",
    "quick_test",
    "retry_with_backoff",
]
