"""
Moogo API Client - Complete implementation for device control and monitoring

This client provides full access to the Moogo API based on discovered endpoints
and testing results. Supports authentication, device discovery, spray control,
and real-time monitoring.

API Discovery Results:
- Authentication: email/password with token-based auth (header: "token: <token>")
- Spray Control: POST /v1/devices/{device_id}/start and /stop with empty payload
- Device Status: GET /v1/devices/{device_id} for detailed device information
- Public Data: GET /v1/liquid and /v1/devices/schedules (no auth required)
"""

import logging
import asyncio
from typing import Any, Final
from datetime import datetime, timedelta

import aiohttp
from aiohttp import ClientSession, ClientTimeout


_LOGGER = logging.getLogger(__name__)


class MoogoAPIError(Exception):
    """Base exception for Moogo API errors."""
    pass


class MoogoAuthError(MoogoAPIError):
    """Authentication related errors."""
    pass


class MoogoDeviceError(MoogoAPIError):
    """Device operation errors."""
    pass


class MoogoRateLimitError(MoogoAPIError):
    """Rate limiting errors."""
    pass


class MoogoClient:
    """
    Comprehensive Moogo API Client
    
    Features:
    - Email/password authentication with automatic token management
    - Device discovery and status monitoring
    - Manual spray control (start/stop)
    - Public data access (liquid types, schedules)
    - Error handling and rate limiting
    - Async/await support for HomeAssistant integration
    """
    
    # API Configuration
    DEFAULT_BASE_URL: Final = "https://api.moogo.com"
    DEFAULT_TIMEOUT: Final = 30

    # API Endpoints (discovered from Android app analysis)
    ENDPOINTS: Final[dict[str, str]] = {
        # Authentication
        "login": "v1/user/login",
        
        # Device Management
        "devices": "v1/devices",
        "device_detail": "v1/devices/{device_id}",
        "device_register": "v1/devices/{device_id}/register",
        "device_update": "v1/devices/{device_id}/update",
        "device_delete": "v1/devices/{device_id}",
        "device_configs": "v1/devices/{device_id}/configs",
        "device_ota_check": "v1/devices/{device_id}/otaCheck",
        "device_ota_update": "v1/devices/{device_id}/otaUpdate",
        "device_logs": "v1/devices/{device_id}/logs",
        
        # Device Control
        "device_start": "v1/devices/{device_id}/start",
        "device_stop": "v1/devices/{device_id}/stop",
        
        # Schedule Management
        "schedules": "v1/devices/schedules",  # Public recommended schedules
        "device_schedules": "v1/devices/{device_id}/schedules",
        "device_schedule_detail": "v1/devices/{device_id}/schedules/{schedule_id}",
        "device_schedule_enable": "v1/devices/{device_id}/schedules/{schedule_id}/enable",
        "device_schedule_disable": "v1/devices/{device_id}/schedules/{schedule_id}/disable",
        "device_schedule_skip": "v1/devices/{device_id}/schedules/{schedule_id}/skip",
        "device_schedules_enable_all": "v1/devices/{device_id}/schedules/switch/open",
        "device_schedules_disable_all": "v1/devices/{device_id}/schedules/switch/close",
        
        # Public Data
        "liquid_types": "v1/liquid",
    }
    
    # Response Codes
    SUCCESS_CODE: Final = 0
    AUTH_INVALID_CODE: Final = 10104
    RATE_LIMITED_CODE: Final = 10000
    DEVICE_OFFLINE_CODE: Final = 10201
    SERVER_ERROR_CODE: Final = 500
    UNAUTHORIZED_CODE: Final = 401
    
    def __init__(
        self,
        email: str | None = None,
        password: str | None = None,
        base_url: str = DEFAULT_BASE_URL,
        session: ClientSession | None = None,
        timeout: int = DEFAULT_TIMEOUT,
    ) -> None:
        """
        Initialize Moogo API client.

        Args:
            email: User email for authentication
            password: User password for authentication
            base_url: API base URL (default: https://api.moogo.com)
            session: Optional aiohttp session (will create if None)
            timeout: Request timeout in seconds
        """
        self.base_url: str = base_url.rstrip('/')
        self.email: str | None = email
        self.password: str | None = password
        self.timeout: ClientTimeout = ClientTimeout(total=timeout)

        # Session management
        self._session: ClientSession | None = session
        self._session_owner: bool = session is None

        # Authentication state
        self._token: str | None = None
        self._user_id: str | None = None
        self._token_expires: datetime | None = None
        self._authenticated: bool = False

        # Cache for device list
        self._devices_cache: list[dict[str, Any]] | None = None
        self._devices_cache_time: datetime | None = None
        self._devices_cache_ttl: timedelta = timedelta(minutes=5)
    
    async def __aenter__(self) -> "MoogoClient":
        """Async context manager entry."""
        if self._session is None:
            self._session = aiohttp.ClientSession(timeout=self.timeout)
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit."""
        del exc_type, exc_val, exc_tb  # Unused parameters
        await self.close()

    async def close(self) -> None:
        """Close the client and cleanup resources."""
        if self._session_owner and self._session:
            await self._session.close()
            self._session = None
    
    @property
    def session(self) -> ClientSession:
        """Get or create aiohttp session."""
        if self._session is None:
            self._session = aiohttp.ClientSession(timeout=self.timeout)
        return self._session
    
    @property
    def is_authenticated(self) -> bool:
        """Check if client is authenticated."""
        return (
            self._authenticated and 
            self._token is not None and
            (self._token_expires is None or datetime.now() < self._token_expires)
        )
    
    def _get_headers(self, authenticated: bool = True) -> dict[str, str]:
        """Get request headers."""
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "Moogo API Client/1.0"
        }

        if authenticated and self._token:
            headers["token"] = self._token

        return headers
    
    async def _request(
        self,
        method: str,
        endpoint: str,
        authenticated: bool = True,
        retry_auth: bool = True,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """
        Make API request with error handling and automatic reauthentication.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint
            authenticated: Whether request requires authentication
            retry_auth: Whether to retry with reauthentication on 401 errors
            **kwargs: Additional arguments for aiohttp request
            
        Returns:
            Parsed JSON response
            
        Raises:
            MoogoAPIError: For API errors
            MoogoAuthError: For authentication errors
            MoogoRateLimitError: For rate limiting
            MoogoDeviceError: For device operation errors
        """
        url = f"{self.base_url}/{endpoint}"
        headers = self._get_headers(authenticated)
        
        if 'headers' in kwargs:
            headers.update(kwargs.pop('headers'))
        
        try:
            async with self.session.request(
                method, url, headers=headers, **kwargs
            ) as response:
                
                if response.status != 200:
                    if response.status == 401 and authenticated and retry_auth and self.email and self.password:
                        # Token expired, try to reauthenticate
                        _LOGGER.warning(f"Received 401 for {endpoint}, attempting reauthentication...")
                        
                        # Clear current token
                        self._token = None
                        
                        # Try to reauthenticate
                        if await self.authenticate(self.email, self.password):
                            _LOGGER.info("Reauthentication successful, retrying original request...")
                            # Retry the original request with new token (but don't retry again)
                            return await self._request(method, endpoint, authenticated, retry_auth=False, **kwargs)
                        else:
                            _LOGGER.error("Reauthentication failed")
                            raise MoogoAuthError(f"Reauthentication failed after 401: {response.status}")
                    elif response.status == 401:
                        raise MoogoAuthError(f"Unauthorized: {response.status}")
                    else:
                        raise MoogoAPIError(f"HTTP {response.status}: {response.reason}")
                
                data = await response.json()
                
                # Handle API error codes
                code = data.get("code")
                message = data.get("message", "Unknown error")
                
                if code == self.SUCCESS_CODE:
                    return data
                elif code == self.AUTH_INVALID_CODE:
                    raise MoogoAuthError(f"Invalid credentials: {message}")
                elif code == self.RATE_LIMITED_CODE:
                    raise MoogoRateLimitError(f"Rate limited: {message}")
                elif code == self.DEVICE_OFFLINE_CODE:
                    raise MoogoDeviceError(f"Device offline: {message}")
                elif code == self.SERVER_ERROR_CODE:
                    raise MoogoAPIError(f"Server error: {message}")
                elif code == self.UNAUTHORIZED_CODE and authenticated and retry_auth and self.email and self.password:
                    # API returned unauthorized code, try to reauthenticate
                    _LOGGER.warning(f"Received unauthorized code {code} for {endpoint}, attempting reauthentication...")
                    
                    # Clear current token
                    self._token = None
                    
                    # Try to reauthenticate
                    if await self.authenticate(self.email, self.password):
                        _LOGGER.info("Reauthentication successful, retrying original request...")
                        # Retry the original request with new token (but don't retry again)
                        return await self._request(method, endpoint, authenticated, retry_auth=False, **kwargs)
                    else:
                        _LOGGER.error("Reauthentication failed")
                        raise MoogoAuthError(f"Reauthentication failed after unauthorized code: {message}")
                elif code == self.UNAUTHORIZED_CODE:
                    raise MoogoAuthError(f"Unauthorized: {message}")
                else:
                    raise MoogoAPIError(f"API error {code}: {message}")
                    
        except aiohttp.ClientError as e:
            raise MoogoAPIError(f"Request failed: {e}")
    
    async def authenticate(self, email: str | None = None, password: str | None = None) -> bool:
        """
        Authenticate with Moogo API.
        
        Args:
            email: User email (uses instance email if not provided)
            password: User password (uses instance password if not provided)
            
        Returns:
            True if authentication successful
            
        Raises:
            MoogoAuthError: If authentication fails
            MoogoRateLimitError: If rate limited
        """
        auth_email = email or self.email
        auth_password = password or self.password
        
        if not auth_email or not auth_password:
            raise MoogoAuthError("Email and password required for authentication")
        
        payload = {
            "email": auth_email,
            "password": auth_password,
            "keep": True  # Request persistent session
        }
        
        try:
            response = await self._request(
                "POST", 
                self.ENDPOINTS["login"], 
                authenticated=False,
                json=payload
            )
            
            user_data = response.get("data", {})
            self._token = user_data.get("token")
            self._user_id = user_data.get("userId")
            
            # Calculate token expiration (TTL in seconds)
            ttl = user_data.get("ttl", 31536000)  # Default 1 year
            self._token_expires = datetime.now() + timedelta(seconds=ttl)
            
            self._authenticated = True
            
            _LOGGER.info(f"Successfully authenticated user: {user_data.get('email')}")
            return True
            
        except (MoogoAuthError, MoogoRateLimitError):
            raise
        except Exception as e:
            raise MoogoAuthError(f"Authentication failed: {e}")
    
    async def get_devices(self, force_refresh: bool = False) -> list[dict[str, Any]]:
        """
        Get list of user's devices.
        
        Args:
            force_refresh: Force refresh of cached device list
            
        Returns:
            List of device dictionaries
        """
        if not self.is_authenticated:
            raise MoogoAuthError("Authentication required")
        
        # Check cache
        now = datetime.now()
        if (
            not force_refresh and 
            self._devices_cache and 
            self._devices_cache_time and
            now - self._devices_cache_time < self._devices_cache_ttl
        ):
            return self._devices_cache
        
        response = await self._request("GET", self.ENDPOINTS["devices"])
        devices = response.get("data", {}).get("items", [])
        
        # Update cache
        self._devices_cache = devices
        self._devices_cache_time = now
        
        return devices
    
    async def get_device_status(self, device_id: str) -> dict[str, Any]:
        """
        Get detailed device status.
        
        Args:
            device_id: Device ID
            
        Returns:
            Device status dictionary
        """
        if not self.is_authenticated:
            raise MoogoAuthError("Authentication required")
        
        endpoint = self.ENDPOINTS["device_detail"].format(device_id=device_id)
        response = await self._request("GET", endpoint)
        return response.get("data", {})
    
    async def start_spray(self, device_id: str, mode: str | None = None) -> bool:
        """
        Start device spray/misting.
        
        Args:
            device_id: Device ID
            mode: Optional spray mode ("manual", "schedule", etc.)
            
        Returns:
            True if successful
            
        Raises:
            MoogoDeviceError: If device is offline or operation fails
            
        Note:
            Duration control is handled through schedules, not direct start commands.
            For custom durations, create a temporary schedule or use existing ones.
        """
        if not self.is_authenticated:
            raise MoogoAuthError("Authentication required")
        
        endpoint = self.ENDPOINTS["device_start"].format(device_id=device_id)
        
        # API Discovery Results:
        # - Empty payload {} works for default spray
        # - {"mode": "manual"} works for manual mode
        # - {"mode": "schedule"} works for schedule mode
        # - Duration is NOT supported in start endpoint
        payload = {}
        if mode:
            payload["mode"] = mode
        
        try:
            response = await self._request("POST", endpoint, json=payload)
            success = response.get("data", {}).get("code") == 0
            
            if success:
                _LOGGER.info(f"Started spray for device {device_id} with mode: {mode or 'default'}")
            
            return success
            
        except MoogoDeviceError:
            raise
        except Exception as e:
            raise MoogoDeviceError(f"Failed to start spray: {e}")
    
    async def stop_spray(self, device_id: str, mode: str | None = None) -> bool:
        """
        Stop device spray/misting.
        
        Args:
            device_id: Device ID
            mode: Optional stop mode (discovered: empty payload works best)
            
        Returns:
            True if successful
            
        Raises:
            MoogoDeviceError: If device is offline or operation fails
        """
        if not self.is_authenticated:
            raise MoogoAuthError("Authentication required")
        
        endpoint = self.ENDPOINTS["device_stop"].format(device_id=device_id)
        
        # Based on testing: empty payload works, mode parameter causes errors
        payload = {}
        if mode:
            payload["mode"] = mode
        
        try:
            response = await self._request("POST", endpoint, json=payload)
            success = response.get("data", {}).get("code") == 0
            
            if success:
                _LOGGER.info(f"Stopped spray for device {device_id}")
            
            return success
            
        except MoogoDeviceError:
            raise
        except Exception as e:
            raise MoogoDeviceError(f"Failed to stop spray: {e}")
    
    # Public API endpoints (no authentication required)
    
    async def get_liquid_types(self) -> list[dict[str, Any]]:
        """
        Get available liquid concentrate types (public endpoint).
        
        Returns:
            List of liquid type dictionaries
        """
        response = await self._request(
            "GET", 
            self.ENDPOINTS["liquid_types"], 
            authenticated=False
        )
        return response.get("data", [])
    
    async def get_recommended_schedules(self) -> list[dict[str, Any]]:
        """
        Get recommended spray schedules (public endpoint).
        
        Returns:
            List of schedule dictionaries
        """
        response = await self._request(
            "GET", 
            self.ENDPOINTS["schedules"], 
            authenticated=False
        )
        return response.get("data", {}).get("items", [])
    
    async def get_device_schedules(self, device_id: str) -> dict[str, Any]:
        """
        Get device-specific schedules with duration information.
        
        Args:
            device_id: Device ID
            
        Returns:
            Dictionary with schedule data including items with duration fields
        """
        if not self.is_authenticated:
            raise MoogoAuthError("Authentication required")
        
        endpoint = self.ENDPOINTS["device_schedules"].format(device_id=device_id)
        response = await self._request("GET", endpoint)
        return response.get("data", {})
    
    async def create_schedule(
        self, 
        device_id: str, 
        hour: int, 
        minute: int, 
        duration: int,
        repeat_set: str = "0,1,2,3,4,5,6"  # Daily by default
    ) -> bool:
        """
        Create a new spray schedule with custom duration.
        
        Args:
            device_id: Device ID
            hour: Hour (0-23)
            minute: Minute (0-59)
            duration: Spray duration in seconds
            repeat_set: Days to repeat (0=Sunday, 6=Saturday)
            
        Returns:
            True if successful
        """
        if not self.is_authenticated:
            raise MoogoAuthError("Authentication required")
        
        endpoint = self.ENDPOINTS["device_schedules"].format(device_id=device_id)
        payload = {
            "hour": hour,
            "minute": minute,
            "duration": duration,
            "repeatSet": repeat_set,
            "status": 1  # Enable by default
        }
        
        try:
            response = await self._request("POST", endpoint, json=payload)
            success = response.get("code") == self.SUCCESS_CODE
            
            if success:
                _LOGGER.info(f"Created schedule for device {device_id}: {hour:02d}:{minute:02d} for {duration}s")
            
            return success
            
        except Exception as e:
            raise MoogoDeviceError(f"Failed to create schedule: {e}")
    
    async def update_schedule(
        self,
        device_id: str,
        schedule_id: str,
        hour: int | None = None,
        minute: int | None = None,
        duration: int | None = None,
        repeat_set: str | None = None,
        status: int | None = None,
    ) -> bool:
        """
        Update an existing schedule.
        
        Args:
            device_id: Device ID
            schedule_id: Schedule ID to update
            hour: Hour (0-23)
            minute: Minute (0-59)
            duration: Spray duration in seconds
            repeat_set: Days to repeat
            status: 1=enabled, 0=disabled
            
        Returns:
            True if successful
        """
        if not self.is_authenticated:
            raise MoogoAuthError("Authentication required")
        
        endpoint = self.ENDPOINTS["device_schedule_detail"].format(
            device_id=device_id, 
            schedule_id=schedule_id
        )
        
        payload = {}
        if hour is not None:
            payload["hour"] = hour
        if minute is not None:
            payload["minute"] = minute
        if duration is not None:
            payload["duration"] = duration
        if repeat_set is not None:
            payload["repeatSet"] = repeat_set
        if status is not None:
            payload["status"] = status
        
        try:
            response = await self._request("PUT", endpoint, json=payload)
            success = response.get("code") == self.SUCCESS_CODE
            
            if success:
                _LOGGER.info(f"Updated schedule {schedule_id} for device {device_id}")
            
            return success
            
        except Exception as e:
            raise MoogoDeviceError(f"Failed to update schedule: {e}")
    
    async def delete_schedule(self, device_id: str, schedule_id: str) -> bool:
        """
        Delete a spray schedule.
        
        Args:
            device_id: Device ID
            schedule_id: Schedule ID to delete
            
        Returns:
            True if successful
        """
        if not self.is_authenticated:
            raise MoogoAuthError("Authentication required")
        
        endpoint = self.ENDPOINTS["device_schedule_detail"].format(
            device_id=device_id, 
            schedule_id=schedule_id
        )
        
        try:
            response = await self._request("DELETE", endpoint)
            success = response.get("code") == self.SUCCESS_CODE
            
            if success:
                _LOGGER.info(f"Deleted schedule {schedule_id} for device {device_id}")
            
            return success
            
        except Exception as e:
            raise MoogoDeviceError(f"Failed to delete schedule: {e}")
    
    async def start_spray_with_duration(
        self, 
        device_id: str, 
        duration: int,
        cleanup: bool = True
    ) -> bool:
        """
        Start spray with custom duration by creating a temporary schedule.
        
        This method creates a temporary schedule for immediate execution,
        optionally cleaning it up after use.
        
        Args:
            device_id: Device ID
            duration: Spray duration in seconds
            cleanup: Whether to delete the temporary schedule after use
            
        Returns:
            True if successful
        """
        if not self.is_authenticated:
            raise MoogoAuthError("Authentication required")
        
        from datetime import datetime, timedelta
        
        # Create schedule for immediate execution (next minute)
        now = datetime.now()
        next_minute = now + timedelta(minutes=1)
        
        try:
            # Create temporary schedule
            success = await self.create_schedule(
                device_id=device_id,
                hour=next_minute.hour,
                minute=next_minute.minute,
                duration=duration,
                repeat_set=""  # No repeat, one-time only
            )
            
            if not success:
                raise MoogoDeviceError("Failed to create temporary schedule")
            
            # Get the created schedule ID for cleanup
            if cleanup:
                schedules_data = await self.get_device_schedules(device_id)
                schedules = schedules_data.get("items", [])
                
                # Find the schedule we just created
                temp_schedule = None
                for schedule in schedules:
                    if (schedule.get("hour") == next_minute.hour and 
                        schedule.get("minute") == next_minute.minute and
                        schedule.get("duration") == duration):
                        temp_schedule = schedule
                        break
                
                if temp_schedule:
                    schedule_id = temp_schedule.get("id")
                    
                    # Wait for spray to complete, then cleanup
                    await asyncio.sleep(duration + 5)  # Extra buffer
                    await self.delete_schedule(device_id, schedule_id)
            
            _LOGGER.info(f"Started spray with custom duration {duration}s for device {device_id}")
            return True
            
        except Exception as e:
            raise MoogoDeviceError(f"Failed to start spray with duration: {e}")
    
    async def test_connection(self) -> bool:
        """
        Test API connectivity.
        
        Returns:
            True if API is accessible
        """
        try:
            # Test public endpoint first
            await self.get_liquid_types()
            
            # If authenticated, test device endpoint
            if self.is_authenticated:
                await self.get_devices()
            
            return True
            
        except Exception as e:
            _LOGGER.error(f"Connection test failed: {e}")
            return False


# Convenience functions for quick testing

async def quick_test(email: str, password: str) -> dict[str, Any]:
    """
    Quick test of API functionality.
    
    Args:
        email: User email
        password: User password
        
    Returns:
        Dictionary with test results
    """
    results = {
        "authenticated": False,
        "devices_found": 0,
        "device_details": [],
        "liquid_types": [],
        "schedules": [],
        "spray_test": False
    }
    
    async with MoogoClient(email, password) as client:
        try:
            # Test authentication
            await client.authenticate()
            results["authenticated"] = True
            
            # Test device discovery
            devices = await client.get_devices()
            results["devices_found"] = len(devices)
            
            # Test device details
            for device in devices[:3]:  # Limit to first 3 devices
                device_id = device.get("deviceId")
                if device_id:
                    details = await client.get_device_status(device_id)
                    results["device_details"].append(details)
            
            # Test public endpoints
            results["liquid_types"] = await client.get_liquid_types()
            results["schedules"] = await client.get_recommended_schedules()
            
            # Test spray control (on first device only)
            if devices:
                device_id = devices[0].get("deviceId")
                if device_id:
                    try:
                        await client.start_spray(device_id)
                        await asyncio.sleep(2)  # Brief spray
                        await client.stop_spray(device_id)
                        results["spray_test"] = True
                    except MoogoDeviceError:
                        # Device might be offline, not a client error
                        pass
            
        except Exception as e:
            results["error"] = str(e)
    
    return results


if __name__ == "__main__":
    # Example usage
    import sys
    if len(sys.argv) >= 3:
        email, password = sys.argv[1], sys.argv[2]
        
        async def main():
            results = await quick_test(email, password)
            print(f"Test Results: {results}")
        
        asyncio.run(main())
    else:
        print("Usage: python client.py <email> <password>")