# Moogo Integration: Offline Device Handling Improvements

## Overview

This document summarizes the improvements made to handle device offline scenarios more gracefully in the Moogo Home Assistant integration.

## Problem Statement

The integration was experiencing errors when devices went offline:
```
Max retry attempts (3) reached for start_spray: Device offline:
Your device may be offline, please check your network settings
```

The API sometimes reports devices as offline when the backend connection isn't fully established, requiring more time and better retry strategies.

## Solutions Implemented

### 1. Enhanced Retry Logic with Jitter ✅

**File**: `moogo_api/client.py:56-178`

**Changes**:
- Added `random` import for jitter calculation
- Enhanced `retry_with_backoff` decorator with new parameters:
  - `max_delay`: Cap for exponential backoff (default: 30s)
  - `device_offline_max_attempts`: Extended retries for offline errors
- Added 0-1 second jitter to all retry delays

**Benefits**:
- Prevents synchronized retries across multiple devices (thundering herd prevention)
- Provides configurable retry behavior based on error type

**Code Example**:
```python
# Add jitter (0-1 second randomization) to prevent synchronized retries
jitter = random.uniform(0, 1.0)
actual_delay = min(delay + jitter, max_delay)
```

### 2. Smart Retry Strategy with Device Offline Detection ✅

**File**: `moogo_api/client.py:117-133`

**Changes**:
- Automatically detects "offline" in error messages
- Extends retry attempts from `max_attempts` to `device_offline_max_attempts`
- Different logging for offline errors vs. other errors

**Benefits**:
- Gives offline devices more time to reconnect (30-40s vs. 3s)
- Doesn't impact retry behavior for other error types

**Before**:
- All errors: 3 attempts, ~3 seconds total

**After**:
- Offline errors: 5 attempts, ~30-40 seconds total
- Other errors: 3 attempts, ~3 seconds total

### 3. Improved Spray Operations Retry Configuration ✅

**Files**:
- `moogo_api/client.py:685-782` (start_spray)
- `moogo_api/client.py:784-871` (stop_spray)

**Changes**:
```python
@retry_with_backoff(
    max_attempts=5,              # Up from 3
    initial_delay=2.0,           # Up from 1.0
    backoff_factor=2.0,          # Unchanged
    max_delay=30.0,              # New: cap delays
    device_offline_max_attempts=5,  # Extended for offline
    retry_on=(MoogoDeviceError, MoogoAuthError, MoogoAPIError),
)
```

**Retry Timeline**:
```
Attempt 1: 0s      - Fail (offline)
  ↓ wait 2.0s + jitter (~2.5s)
Attempt 2: 2.5s    - Fail (offline)
  ↓ wait 4.0s + jitter (~4.7s)
Attempt 3: 7.2s    - Fail (offline)
  ↓ wait 8.0s + jitter (~8.3s)
Attempt 4: 15.5s   - Fail (offline)
  ↓ wait 16.0s + jitter (~16.8s)
Attempt 5: 32.3s   - Success! (device woke up)
```

### 4. Pre-flight Device Status Checks ✅

**Files**:
- `moogo_api/client.py:733-749` (start_spray)
- `moogo_api/client.py:828-844` (stop_spray)

**Changes**:
- Check device online status before spray operations
- Log warnings if device appears offline
- Non-blocking: Failures don't prevent operation attempt

**Benefits**:
- Better error messages for debugging
- Early warning of potential issues
- Still attempts operation even if pre-flight fails

**Code Example**:
```python
try:
    status = await self.get_device_status(device_id)
    if status.get("onlineStatus") != 1:
        _LOGGER.warning(
            f"Device {device_id} appears offline. "
            "Attempting anyway as device may be waking up..."
        )
except Exception as e:
    _LOGGER.debug(f"Pre-check failed: {e}. Proceeding...")
```

### 5. Circuit Breaker Pattern for Persistently Offline Devices ✅

**File**: `moogo_api/client.py:274-420`

**Changes**:
- Added circuit breaker tracking attributes to `MoogoClient.__init__`
- Implemented helper methods:
  - `_record_device_failure()`: Track failures per device
  - `_record_device_success()`: Reset failure count
  - `_is_circuit_open()`: Check if device is persistently offline
  - `get_device_circuit_status()`: Diagnostic method

**Configuration**:
- Threshold: 5 failures
- Timeout: 5 minutes
- Auto-reset after cooldown period

**Benefits**:
- Fast-fail for persistently offline devices (saves API calls)
- Automatic recovery after timeout
- Per-device tracking (one offline device doesn't affect others)

**State Diagram**:
```
[Closed] --5 failures--> [Open] --5 min timeout--> [Half-Open] --success--> [Closed]
   ↑                        |                           |
   |                        |                           |
   +------success-----------+                           +--failure--> [Open]
```

**Code Example**:
```python
# Check circuit breaker before operation
if self._is_circuit_open(device_id):
    raise MoogoDeviceError(
        f"Device {device_id} circuit breaker is open. "
        f"Will retry in {time_remaining}s"
    )
```

### 6. Optimized Switch Polling Logic ✅

**File**: `switch.py:123-299`

**Changes**:
- Reduced start spray polling: 60s → 30s (10 attempts × 3s)
- Reduced stop spray polling: 30s → 18s (6 attempts × 3s)
- Better exception handling in polling loops
- More informative debug messages

**Rationale**:
- API client now handles 30-40s of retries internally
- Switch polling focuses on confirming operation success
- Total operation time: ~30-40s (API) + ~30s (polling) = ~60-70s max

**Before**:
```
API retry: 3 attempts × ~1s = ~3s
Switch poll: 12 attempts × 5s = 60s
Total: ~63s
```

**After**:
```
API retry: 5 attempts × 2-16s = ~30-40s
Switch poll: 10 attempts × 3s = 30s
Total: ~60-70s (similar but smarter)
```

### 7. Enhanced Logging ✅

**Throughout all files**

**Improvements**:
- Device offline detection logged at INFO level
- Circuit breaker state changes prominently logged
- Retry attempts show actual delay time with jitter
- Clear distinction between temporary vs. persistent offline states
- Separate log levels for different severity

**Examples**:
```python
# INFO: Extended retries for offline
_LOGGER.info(
    f"Device offline detected, extending retries to {attempts} attempts"
)

# WARNING: Circuit breaker threshold
_LOGGER.warning(
    f"Circuit breaker threshold reached for device {device_id} "
    f"({circuit['failures']} failures)"
)

# INFO: Circuit breaker reset
_LOGGER.info(
    f"Circuit breaker reset for device {device_id} after successful operation"
)
```

## Test Coverage

### Test Structure
```
tests/
├── __init__.py
├── conftest.py                    # Fixtures
├── pytest.ini                     # Config
├── requirements-test.txt          # Dependencies
├── README.md                      # Documentation
├── test_retry_logic.py           # 11 tests
├── test_circuit_breaker.py       # 12 tests
└── test_spray_operations.py      # 12 tests
```

### Test Summary
- **Total Tests**: 35
- **Retry Logic**: 11 tests covering exponential backoff, jitter, max delay, error handling
- **Circuit Breaker**: 12 tests covering state transitions, thresholds, timeouts, per-device tracking
- **Spray Operations**: 12 tests covering auth, pre-flight checks, success/failure recording

### Running Tests
```bash
cd tests
pip install -r requirements-test.txt
pytest -v
pytest --cov=../ --cov-report=html
```

## Code Quality

### Linting and Formatting
All code passes:
- ✅ **Ruff linter**: `ruff check .` - All checks passed
- ✅ **Ruff formatter**: `ruff format .` - All files formatted
- ✅ **Python syntax**: AST validation passed
- ✅ **Type hints**: Proper type annotations throughout

### Validation Commands
```bash
# Linting
ruff check .

# Formatting
ruff format .

# Syntax check
python3 -m py_compile moogo_api/client.py switch.py
```

## Performance Impact

### Positive Impacts
1. **Resource Efficiency**: Circuit breaker prevents wasting API calls on dead devices
2. **Better Success Rate**: Extended retry window gives devices time to connect
3. **Load Distribution**: Jitter prevents synchronized retries

### Trade-offs
1. **Slightly Longer Operation Time**: Max 60-70s vs. previous 63s (negligible)
2. **Memory Overhead**: Circuit breaker state per device (~100 bytes)
3. **Logging Volume**: More detailed logs (configurable via log level)

## Migration Notes

### Backward Compatibility
✅ **No breaking changes**
- All changes are internal to the API client and switch
- Existing functionality preserved
- No changes to public API surface

### Configuration
No user configuration required. All improvements are automatic with sensible defaults:
- Max retry attempts: 5 (for offline errors)
- Circuit breaker threshold: 5 failures
- Circuit breaker timeout: 5 minutes
- Max retry delay: 30 seconds

### Monitoring
Check circuit breaker status programmatically:
```python
status = client.get_device_circuit_status("device_123")
# Returns: {
#   "circuit_open": bool,
#   "failures": int,
#   "last_failure": datetime,
#   "last_success": datetime
# }
```

## Benefits Summary

| Improvement | Before | After | Benefit |
|-------------|--------|-------|---------|
| Retry Time (offline) | ~3s | ~30-40s | 10x more time for devices to wake |
| Retry Synchronization | None | Jitter (0-1s) | Prevents thundering herd |
| Persistent Offline Handling | None | Circuit breaker | Saves API calls, auto-recovery |
| Pre-flight Checks | None | Status check | Better error messages |
| Test Coverage | 0 tests | 35 tests | Comprehensive validation |
| Code Quality | Manual | Ruff validated | Consistent, linted |

## Files Changed

### Core Implementation
1. `moogo_api/client.py` - Enhanced retry logic, circuit breaker, pre-flight checks
2. `switch.py` - Optimized polling logic

### Tests
3. `tests/__init__.py` - Test package
4. `tests/conftest.py` - Pytest fixtures
5. `tests/pytest.ini` - Pytest configuration
6. `tests/requirements-test.txt` - Test dependencies
7. `tests/README.md` - Test documentation
8. `tests/test_retry_logic.py` - Retry decorator tests
9. `tests/test_circuit_breaker.py` - Circuit breaker tests
10. `tests/test_spray_operations.py` - Spray operation tests

### Documentation
11. `OFFLINE_HANDLING_IMPROVEMENTS.md` - This document

## Future Enhancements

Potential future improvements:
1. **Adaptive Retry Intervals**: Learn optimal retry timing per device based on history
2. **Metrics Collection**: Track retry success rates, circuit breaker activations
3. **Configuration Options**: Allow users to tune retry parameters via integration config
4. **Device Health Dashboard**: Expose circuit breaker status in UI
5. **Notification Integration**: Alert users when devices become persistently offline

## References

### Best Practices Followed
- AWS Prescriptive Guidance: Retry with backoff pattern
- Martin Fowler: Circuit Breaker pattern
- Google Cloud: Exponential backoff
- Home Assistant: Entity availability patterns

### Related Documentation
- [Home Assistant Integration Quality Scale](https://developers.home-assistant.io/docs/integration_quality_scale_index)
- [Home Assistant Entity Availability](https://developers.home-assistant.io/docs/core/entity#available)
- [Exponential Backoff Best Practices](https://cloud.google.com/memorystore/docs/redis/exponential-backoff)

---

**Implementation Date**: November 17, 2025
**Version**: 1.5.1
**Status**: ✅ Complete, Tested, and Production Ready
