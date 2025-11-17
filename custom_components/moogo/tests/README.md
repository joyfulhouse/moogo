# Moogo Integration Tests

This directory contains tests for the Moogo Home Assistant integration, with focus on the improved offline device handling features.

## Test Coverage

### 1. Retry Logic Tests (`test_retry_logic.py`)
- ✅ Successful first attempt (no retries)
- ✅ Retry on transient failures with exponential backoff
- ✅ Max retries exceeded behavior
- ✅ Rate limit errors are not retried
- ✅ Device offline errors get extended retry attempts
- ✅ Jitter is applied to prevent synchronized retries
- ✅ Max delay cap prevents excessive waits
- ✅ Unexpected errors are not retried
- ✅ Auth errors are retried when specified

### 2. Circuit Breaker Tests (`test_circuit_breaker.py`)
- ✅ Initial circuit state (closed)
- ✅ Recording device failures
- ✅ Circuit opens after threshold failures
- ✅ Circuit stays closed below threshold
- ✅ Success resets failure count
- ✅ Circuit auto-resets after timeout
- ✅ Circuit status diagnostics
- ✅ Per-device circuit tracking
- ✅ Fast-fail when circuit is open
- ✅ Successful operations reset circuit
- ✅ Failed operations increment failures

### 3. Spray Operations Tests (`test_spray_operations.py`)
- ✅ Authentication required for spray operations
- ✅ Pre-flight checks for online devices
- ✅ Pre-flight checks for offline devices (with warning)
- ✅ Pre-flight failure doesn't prevent attempt
- ✅ Successful spray records success
- ✅ Failed spray records failure
- ✅ Mode parameter support
- ✅ Correct retry configuration (5 attempts for offline)

## Running Tests

### Install Test Dependencies

```bash
cd custom_components/moogo/tests
pip install -r requirements-test.txt
```

### Run All Tests

```bash
# From the tests directory
pytest

# With coverage
pytest --cov=../ --cov-report=html --cov-report=term

# Verbose output
pytest -v

# Specific test file
pytest test_retry_logic.py

# Specific test
pytest test_circuit_breaker.py::TestCircuitBreaker::test_circuit_opens_after_threshold
```

### Run Tests from Integration Root

```bash
cd custom_components/moogo
python -m pytest tests/
```

## Test Architecture

### Fixtures (`conftest.py`)
- `mock_aiohttp_session`: Mocked aiohttp session
- `authenticated_client`: Pre-authenticated MoogoClient
- `unauthenticated_client`: Unauthenticated MoogoClient

### Key Testing Patterns

1. **Async Testing**: Uses `pytest-asyncio` for async function testing
2. **Mocking**: Uses `unittest.mock` for patching external dependencies
3. **Time-based Testing**: Simulates delays and timeouts for retry logic
4. **State Verification**: Validates internal state changes (circuit breaker, failure counts)

## Expected Test Results

All tests should pass:
- **Retry Logic**: 11 tests
- **Circuit Breaker**: 12 tests
- **Spray Operations**: 12 tests

**Total**: 35 tests covering all new offline device handling features

## CI/CD Integration

These tests can be integrated into GitHub Actions or other CI/CD pipelines:

```yaml
- name: Install test dependencies
  run: pip install -r custom_components/moogo/tests/requirements-test.txt

- name: Run tests
  run: pytest custom_components/moogo/tests/ --cov --cov-report=xml

- name: Upload coverage
  uses: codecov/codecov-action@v3
```

## Test Maintenance

When adding new features:
1. Add corresponding test cases
2. Maintain >80% code coverage
3. Test both success and failure paths
4. Test edge cases (circuit breaker thresholds, timeout boundaries)
5. Verify async behavior with proper mocking
