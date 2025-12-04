# Socket Client 90% Test Coverage Plan

**Current Coverage**: 52.76%  
**Target Coverage**: 90%  
**Gap**: 37.24 percentage points

---

## Summary

This document provides a detailed plan to achieve 90% test coverage for the Socket Client service, broken down into manageable phases with specific test requirements for each module.

---

## Coverage Breakdown by Module

### High Priority (Core Functionality)

#### 1. `socket_client/main.py` - **0% → 90%** (100 lines)
**Status**: ⚠️ **CRITICAL** - No coverage  
**Impact**: High - Entry point and service lifecycle  
**Estimated Tests**: 25-30 tests  
**Estimated Time**: 2-3 hours

**Test Categories**:
- [ ] `SocketClientService` initialization (3 tests)
- [ ] Service startup/shutdown (5 tests)
- [ ] Signal handling (SIGTERM, SIGINT) (3 tests)
- [ ] CLI commands (`run`, `health`, `version`) (8 tests)
- [ ] OpenTelemetry integration (4 tests)
- [ ] Environment variable handling (4 tests)
- [ ] Error handling (startup failures, connection errors) (5 tests)

**Key Test Scenarios**:
```python
- test_service_initialization()
- test_service_start_success()
- test_service_stop_graceful()
- test_signal_handler_triggers_shutdown()
- test_cli_run_with_custom_parameters()
- test_cli_health_check()
- test_otel_setup_and_logging()
- test_startup_failure_cleanup()
```

#### 2. `socket_client/core/client.py` - **34.40% → 85%** (164 lines uncovered)
**Status**: ⚠️ **HIGH PRIORITY** - Core WebSocket client  
**Impact**: Critical - Main business logic  
**Estimated Tests**: 30-35 tests  
**Estimated Time**: 3-4 hours

**Uncovered Lines**:
- 124-156: Connection management edge cases
- 160-190: Message processing error paths
- 194-230: Reconnection logic
- 234-248: Circuit breaker integration
- 255-284: NATS publishing edge cases
- 296-321: Shutdown sequences
- 329-375: Error handling
- 401-539: Recovery mechanisms

**Test Categories**:
- [ ] Connection lifecycle (connect, disconnect, reconnect) (8 tests)
- [ ] Message processing (valid, invalid, malformed) (6 tests)
- [ ] Error handling (network failures, timeouts) (6 tests)
- [ ] Circuit breaker integration (3 tests)
- [ ] NATS publishing (success, failure, retry) (5 tests)
- [ ] Shutdown scenarios (graceful, forced, with pending messages) (4 tests)
- [ ] Reconnection storms prevention (3 tests)

**Key Test Scenarios**:
```python
- test_connection_during_shutdown()
- test_rapid_reconnects_with_backoff()
- test_message_processing_invalid_json()
- test_circuit_breaker_opens_after_failures()
- test_nats_publish_with_retries()
- test_graceful_shutdown_with_pending_messages()
- test_reconnection_storm_prevention()
```

### Medium Priority

#### 3. `socket_client/services/config_manager.py` - **46.15% → 80%** (21 lines)
**Status**: Medium  
**Impact**: Medium - Configuration management  
**Estimated Tests**: 12-15 tests  
**Estimated Time**: 1-1.5 hours

**Uncovered Lines**:
- 23-29: MongoDB connection error handling
- 33, 37-38: Config loading edge cases
- 43, 58-61: Config saving edge cases
- 66, 81-84: Filter handling
- 92: Connection cleanup

**Test Categories**:
- [ ] MongoDB connection (success, failure, timeout) (4 tests)
- [ ] Config loading (exists, missing, corrupt) (4 tests)
- [ ] Config saving (new, update, upsert) (4 tests)
- [ ] Filter operations (3 tests)

#### 4. `socket_client/health/server.py` - **46.60% → 80%** (55 lines)
**Status**: Medium  
**Impact**: Medium - Health monitoring  
**Estimated Tests**: 10-12 tests  
**Estimated Time**: 1 hour

**Uncovered Lines**:
- 70-81: Health check endpoint edge cases
- 85-91: Status response variations
- 95-117: Metrics endpoint
- 124-175: Server lifecycle
- 179-196: Error handling

**Test Categories**:
- [ ] Health check endpoint (healthy, unhealthy, degraded) (4 tests)
- [ ] Metrics endpoint (3 tests)
- [ ] Server startup/shutdown (3 tests)
- [ ] Concurrent requests (2 tests)

#### 5. `socket_client/utils/circuit_breaker.py` - **52.46% → 85%** (29 lines)
**Status**: Good progress - needs edge cases  
**Impact**: Medium - Reliability  
**Estimated Tests**: 8-10 tests  
**Estimated Time**: 45 minutes

**Uncovered Lines**:
- 81-104: Half-open state transitions
- 108-114: Concurrent access edge cases
- 118-131: Timeout precision
- 139, 143: Metrics during transitions

**Test Categories**:
- [ ] Half-open to closed transitions (3 tests)
- [ ] Concurrent failures and race conditions (3 tests)
- [ ] Timeout precision and edge cases (2 tests)
- [ ] Metrics accuracy (2 tests)

### Lower Priority

#### 6. `socket_client/api/routes/config.py` - **77.54% → 90%** (31 lines)
**Status**: Good - needs error path coverage  
**Impact**: Low - API endpoints  
**Estimated Tests**: 6-8 tests  
**Estimated Time**: 30 minutes

**Uncovered Lines**: Error handling in routes

**Test Categories**:
- [ ] Error responses (4xx, 5xx) (4 tests)
- [ ] Validation edge cases (2 tests)
- [ ] Concurrent API requests (2 tests)

#### 7. `socket_client/api/main.py` - **88.46% → 95%** (3 lines)
**Status**: Excellent  
**Estimated Tests**: 2 tests  
**Estimated Time**: 15 minutes

#### 8. `socket_client/models/message.py` - **89.06% → 95%** (7 lines)
**Status**: Excellent  
**Estimated Tests**: 2-3 tests  
**Estimated Time**: 15 minutes

---

## Implementation Phases

### Phase 1: Critical Path (Days 1-2)
**Target**: 52.76% → 70% (+17 points)  
**Focus**: main.py + core functionality in client.py

1. **main.py** - Complete test suite (0% → 90%)
   - Service lifecycle tests
   - CLI command tests
   - Signal handling tests

2. **client.py** - Connection and message processing (34% → 60%)
   - Connection management
   - Basic message processing
   - Error handling

**Deliverable**: Core service functionality fully tested

### Phase 2: Reliability (Day 3)
**Target**: 70% → 80% (+10 points)  
**Focus**: Complete client.py + circuit breaker

1. **client.py** - Advanced scenarios (60% → 85%)
   - Reconnection logic
   - Circuit breaker integration
   - NATS publishing

2. **circuit_breaker.py** - Edge cases (52% → 85%)
   - Concurrent access
   - State transitions
   - Race conditions

**Deliverable**: High reliability scenarios covered

### Phase 3: Infrastructure (Day 4)
**Target**: 80% → 90% (+10 points)  
**Focus**: config_manager, health_server, API routes

1. **config_manager.py** - Complete coverage (46% → 80%)
2. **health/server.py** - Complete coverage (46% → 80%)
3. **api/routes/config.py** - Error paths (77% → 90%)
4. **api/main.py** - Final gaps (88% → 95%)
5. **models/message.py** - Final gaps (89% → 95%)

**Deliverable**: 90% coverage achieved

---

## Test Writing Guidelines

### Structure
```python
class TestFeatureName:
    """Test suite for feature X."""
    
    @pytest.fixture
    def setup_fixture(self):
        """Reusable test setup."""
        pass
    
    def test_happy_path(self):
        """Test normal successful operation."""
        pass
    
    def test_error_handling(self):
        """Test error conditions."""
        pass
    
    @pytest.mark.asyncio
    async def test_async_operation(self):
        """Test async functionality."""
        pass
```

### Coverage Tips
1. **Focus on untested lines**: Use `coverage.json` to identify gaps
2. **Test error paths**: Often untested but critical
3. **Mock external dependencies**: NATS, MongoDB, WebSocket connections
4. **Test edge cases**: Empty inputs, None values, timeouts
5. **Test concurrent scenarios**: Race conditions, simultaneous operations

### Quality Standards
- Each test should test ONE specific behavior
- Use descriptive test names: `test_<what>_<condition>_<expected>`
- Include docstrings explaining test purpose
- Mock external dependencies (don't hit real services)
- Tests must be deterministic (no flaky tests)
- Aim for <100ms per test (use async where needed)

---

## Mocking Patterns

### WebSocket Connection
```python
@pytest.fixture
def mock_websocket():
    with patch('websockets.connect') as mock:
        mock.return_value = AsyncMock()
        yield mock
```

### NATS Connection
```python
@pytest.fixture
def mock_nats():
    with patch('nats.connect') as mock:
        mock.return_value = AsyncMock()
        yield mock
```

### MongoDB
```python
@pytest.fixture
def mock_mongo():
    with patch('pymongo.MongoClient') as mock:
        mock.return_value = MagicMock()
        yield mock
```

---

## Progress Tracking

### Current Status (as of implementation)
- ✅ Circuit breaker: 52.46% (comprehensive tests exist)
- ✅ Message models: 89.06% (excellent coverage)
- ✅ API models: 100% (complete)
- ✅ Logger: 100% (complete)
- ⚠️ main.py: 0% (**needs all tests**)
- ⚠️ client.py: 34.40% (**needs 50+ points**)
- ⚠️ config_manager.py: 46.15% (**needs 35 points**)
- ⚠️ health_server.py: 46.60% (**needs 35 points**)

### Milestone Targets
- [ ] **65% Coverage** - Phase 1 Day 1 complete
- [ ] **70% Coverage** - Phase 1 complete
- [ ] **80% Coverage** - Phase 2 complete
- [ ] **90% Coverage** - Phase 3 complete ✨

---

## Estimated Total Effort

**Total Time**: 8-10 hours of focused test writing

**Breakdown**:
- main.py: 2-3 hours
- client.py: 3-4 hours
- config_manager.py: 1-1.5 hours
- health_server.py: 1 hour
- circuit_breaker.py: 45 minutes
- API routes: 30 minutes
- Other modules: 30 minutes

**Recommendation**: Break into 4 separate tickets:
1. **[TESTING] Socket Client - Achieve 65% Coverage** (main.py focus)
2. **[TESTING] Socket Client - Achieve 75% Coverage** (client.py basic)
3. **[TESTING] Socket Client - Achieve 85% Coverage** (client.py advanced + circuit breaker)
4. **[TESTING] Socket Client - Achieve 90% Coverage** (config, health, API cleanup)

---

## References

- Current test suite: `tests/unit/`
- Coverage report: `htmlcov/index.html`
- Coverage JSON: `coverage.json`
- Makefile: `make test` to run with coverage

---

**Last Updated**: December 2025  
**Status**: Planning Document - Ready for Implementation

