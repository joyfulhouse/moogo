"""
Moogo API Package

A comprehensive Python client for the Moogo smart spray system API.
Provides authentication, device control, monitoring, and schedule management.
"""

from .client import (
    MoogoClient,
    MoogoAPIError, 
    MoogoAuthError,
    MoogoDeviceError,
    MoogoRateLimitError,
    quick_test
)

__version__ = "1.0.0"
__all__ = [
    "MoogoClient",
    "MoogoAPIError",
    "MoogoAuthError", 
    "MoogoDeviceError",
    "MoogoRateLimitError",
    "quick_test"
]