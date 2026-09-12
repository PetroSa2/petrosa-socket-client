"""
Comprehensive unit tests for the Circuit Breaker pattern implementation.

Tests cover all circuit breaker states, failure thresholds, recovery mechanisms,
async operations, and performance characteristics.
"""

import asyncio
import os
import time

import pytest

from socket_client.utils.circuit_breaker import (
    AsyncCircuitBreaker,
    CircuitBreakerOpenError,
    CircuitState,
    nats_circuit_breaker,
    websocket_circuit_breaker,
)


@pytest.mark.unit
class TestCircuitState:
    """Test cases for CircuitState enum."""

    def test_circuit_state_values(self) -> None:
        """Test circuit state enum values."""
        assert CircuitState.CLOSED.value == "closed"
        assert CircuitState.OPEN.value == "open"
        assert CircuitState.HALF_OPEN.value == "half_open"

    def test_circuit_state_comparison(self) -> None:
        """Test circuit state comparison."""
        assert CircuitState.CLOSED == CircuitState.CLOSED
        assert CircuitState.CLOSED != CircuitState.OPEN
        assert CircuitState.OPEN != CircuitState.HALF_OPEN


@pytest.mark.unit
class TestAsyncCircuitBreaker:
    """Test cases for AsyncCircuitBreaker."""

    def test_initialization_default_parameters(self) -> None:
        """Test circuit breaker initialization with default parameters."""
        cb = AsyncCircuitBreaker()

        assert cb.failure_threshold == 5
        assert cb.recovery_timeout == 60
        assert cb.expected_exception is Exception
        assert cb.name == "default"
        assert cb.state == CircuitState.CLOSED
        assert cb.failure_count == 0
        assert cb.last_failure_time == 0

    def test_initialization_custom_parameters(self) -> None:
        """Test circuit breaker initialization with custom parameters."""
        cb = AsyncCircuitBreaker(
            failure_threshold=3,
            recovery_timeout=30,
            expected_exception=ValueError,
            name="test-breaker",
        )

        assert cb.failure_threshold == 3
        assert cb.recovery_timeout == 30
        assert cb.expected_exception is ValueError
        assert cb.name == "test-breaker"

    @pytest.mark.asyncio
    async def test_successful_function_call(self) -> None:
        """Test successful function execution through circuit breaker."""
        cb = AsyncCircuitBreaker(name="test")

        async def successful_function():
            return "success"

        result = await cb.call(successful_function)

        assert result == "success"
        assert cb.state == CircuitState.CLOSED
        assert cb.failure_count == 0

    @pytest.mark.asyncio
    async def test_sync_function_call(self) -> None:
        """Test synchronous function execution through circuit breaker."""
        cb = AsyncCircuitBreaker(name="test")

        def sync_function():
            return "sync_success"

        result = await cb.call(sync_function)

        assert result == "sync_success"
        assert cb.state == CircuitState.CLOSED

    @pytest.mark.asyncio
    async def test_function_call_with_arguments(self) -> None:
        """Test function execution with arguments and keyword arguments."""
        cb = AsyncCircuitBreaker(name="test")

        async def function_with_args(arg1, arg2, kwarg1=None):
            return f"{arg1}-{arg2}-{kwarg1}"

        result = await cb.call(function_with_args, "a", "b", kwarg1="c")

        assert result == "a-b-c"

    @pytest.mark.asyncio
    async def test_failure_count_increment(self) -> None:
        """Test that failure count increments on exceptions."""
        cb = AsyncCircuitBreaker(failure_threshold=3, name="test")

        async def failing_function():
            raise ValueError("Test error")

        # First failure
        with pytest.raises(ValueError):
            await cb.call(failing_function)

        assert cb.failure_count == 1
        assert cb.state == CircuitState.CLOSED

        # Second failure
        with pytest.raises(ValueError):
            await cb.call(failing_function)

        assert cb.failure_count == 2
        assert cb.state == CircuitState.CLOSED

    @pytest.mark.asyncio
    async def test_circuit_opens_after_threshold(self) -> None:
        """Test that circuit opens after failure threshold is reached."""
        cb = AsyncCircuitBreaker(failure_threshold=3, name="test")

        async def failing_function():
            raise Exception("Test error")

        # Trigger failures to reach threshold
        for i in range(3):
            with pytest.raises(Exception):
                await cb.call(failing_function)

            if i < 2:
                assert cb.state == CircuitState.CLOSED
            else:
                assert cb.state == CircuitState.OPEN

        assert cb.failure_count == 3

    @pytest.mark.asyncio
    async def test_circuit_breaker_open_blocks_calls(self) -> None:
        """Test that open circuit breaker blocks function calls."""
        cb = AsyncCircuitBreaker(failure_threshold=2, name="test")

        async def failing_function():
            raise Exception("Test error")

        # Open the circuit
        for _ in range(2):
            with pytest.raises(Exception):
                await cb.call(failing_function)

        assert cb.state == CircuitState.OPEN

        # Should now block calls
        with pytest.raises(
            CircuitBreakerOpenError, match="Circuit breaker 'test' is open"
        ):
            await cb.call(failing_function)

    @pytest.mark.asyncio
    async def test_circuit_transitions_to_half_open_after_timeout(self) -> None:
        """Test transition from OPEN to HALF_OPEN after recovery timeout."""
        cb = AsyncCircuitBreaker(failure_threshold=2, recovery_timeout=1, name="test")

        async def failing_function():
            raise Exception("Test error")

        # Open the circuit
        for _ in range(2):
            with pytest.raises(Exception):
                await cb.call(failing_function)

        assert cb.state == CircuitState.OPEN

        # Wait for recovery timeout
        await asyncio.sleep(1.1)

        # Next call should transition to HALF_OPEN (but still fail)
        with pytest.raises(Exception):
            await cb.call(failing_function)

        # The state should have been HALF_OPEN during the call
        # but now it's OPEN again due to the failure

    @pytest.mark.asyncio
    async def test_circuit_closes_after_successful_half_open_call(self) -> None:
        """Test circuit closes after successful call in HALF_OPEN state."""
        cb = AsyncCircuitBreaker(failure_threshold=2, recovery_timeout=1, name="test")

        async def failing_function():
            raise Exception("Test error")

        async def successful_function():
            return "success"

        # Open the circuit
        for _ in range(2):
            with pytest.raises(Exception):
                await cb.call(failing_function)

        assert cb.state == CircuitState.OPEN

        # Wait for recovery timeout
        await asyncio.sleep(1.1)

        # Successful call should close the circuit
        result = await cb.call(successful_function)

        assert result == "success"
        assert cb.state == CircuitState.CLOSED
        assert cb.failure_count == 0

    @pytest.mark.asyncio
    async def test_different_exception_types_not_counted(self) -> None:
        """Test that non-expected exceptions are not counted as failures."""
        cb = AsyncCircuitBreaker(
            failure_threshold=2, expected_exception=ValueError, name="test"
        )

        async def type_error_function():
            raise TypeError("Type error")

        async def value_error_function():
            raise ValueError("Value error")

        # TypeError should not be counted
        with pytest.raises(TypeError):
            await cb.call(type_error_function)

        assert cb.failure_count == 0
        assert cb.state == CircuitState.CLOSED

        # ValueError should be counted
        with pytest.raises(ValueError):
            await cb.call(value_error_function)

        assert cb.failure_count == 1
        assert cb.state == CircuitState.CLOSED

    @pytest.mark.asyncio
    async def test_successful_call_resets_failure_count(self) -> None:
        """Test that successful calls reset failure count in CLOSED state."""
        cb = AsyncCircuitBreaker(failure_threshold=3, name="test")

        async def failing_function():
            raise Exception("Test error")

        async def successful_function():
            return "success"

        # Accumulate some failures
        for _ in range(2):
            with pytest.raises(Exception):
                await cb.call(failing_function)

        assert cb.failure_count == 2
        assert cb.state == CircuitState.CLOSED

        # Successful call should reset failure count
        result = await cb.call(successful_function)

        assert result == "success"
        assert cb.failure_count == 0
        assert cb.state == CircuitState.CLOSED

    def test_get_state(self) -> None:
        """Test get_state method."""
        cb = AsyncCircuitBreaker(name="test")

        assert cb.get_state() == CircuitState.CLOSED

        # Manually set state for testing
        cb.state = CircuitState.OPEN
        assert cb.get_state() == CircuitState.OPEN

    def test_get_metrics(self) -> None:
        """Test get_metrics method."""
        cb = AsyncCircuitBreaker(
            failure_threshold=5, recovery_timeout=60, name="test-metrics"
        )

        metrics = cb.get_metrics()

        assert metrics["name"] == "test-metrics"
        assert metrics["state"] == "closed"
        assert metrics["failure_count"] == 0
        assert metrics["failure_threshold"] == 5
        assert metrics["recovery_timeout"] == 60
        assert metrics["half_open_max_calls"] == 3
        assert metrics["half_open_calls"] == 0
        assert metrics["last_failure_time"] == 0
        assert "time_since_last_failure" in metrics

    @pytest.mark.asyncio
    async def test_half_open_max_calls_limits_trial_calls(self) -> None:
        """Per #133: half_open_max_calls must actually be enforced.

        Once the circuit is HALF_OPEN, at most `half_open_max_calls` trial
        calls are admitted concurrently; further concurrent calls are
        rejected with CircuitBreakerOpenError instead of being let through.
        """
        cb = AsyncCircuitBreaker(
            failure_threshold=1,
            recovery_timeout=0.1,
            name="test-half-open-limit",
            half_open_max_calls=2,
        )

        async def failing_function():
            raise Exception("Test error")

        with pytest.raises(Exception):
            await cb.call(failing_function)
        assert cb.state == CircuitState.OPEN

        await asyncio.sleep(0.15)

        async def slow_success():
            await asyncio.sleep(0.2)
            return "ok"

        # 5 concurrent calls arrive right as the circuit goes HALF_OPEN.
        # Only half_open_max_calls=2 should be admitted as trials; the rest
        # must be rejected immediately with CircuitBreakerOpenError.
        results = await asyncio.gather(
            *[cb.call(slow_success) for _ in range(5)], return_exceptions=True
        )

        admitted = [r for r in results if r == "ok"]
        rejected = [r for r in results if isinstance(r, CircuitBreakerOpenError)]

        assert len(admitted) == 2
        assert len(rejected) == 3
        assert all("trial-call limit" in str(r) for r in rejected)

    @pytest.mark.asyncio
    async def test_half_open_calls_reset_on_close(self) -> None:
        """half_open_calls resets to 0 when the circuit closes again."""
        cb = AsyncCircuitBreaker(
            failure_threshold=1,
            recovery_timeout=0.1,
            name="test-half-open-reset",
            half_open_max_calls=3,
        )

        async def failing_function():
            raise Exception("Test error")

        async def successful_function():
            return "ok"

        with pytest.raises(Exception):
            await cb.call(failing_function)
        assert cb.state == CircuitState.OPEN

        await asyncio.sleep(0.15)

        result = await cb.call(successful_function)
        assert result == "ok"
        assert cb.state == CircuitState.CLOSED
        assert cb.half_open_calls == 0

    @pytest.mark.asyncio
    async def test_concurrent_calls(self) -> None:
        """Test circuit breaker behavior with concurrent calls."""
        cb = AsyncCircuitBreaker(failure_threshold=3, name="test")

        async def slow_function():
            await asyncio.sleep(0.1)
            return "success"

        # Execute multiple concurrent calls
        tasks = [cb.call(slow_function) for _ in range(5)]
        results = await asyncio.gather(*tasks)

        assert all(result == "success" for result in results)
        assert cb.state == CircuitState.CLOSED
        assert cb.failure_count == 0

    @pytest.mark.asyncio
    async def test_concurrent_failures(self) -> None:
        """Test circuit breaker with concurrent failures."""
        cb = AsyncCircuitBreaker(failure_threshold=3, name="test")

        async def failing_function():
            await asyncio.sleep(0.05)  # Small delay
            raise Exception("Concurrent failure")

        # Execute concurrent failing calls
        tasks = [cb.call(failing_function) for _ in range(5)]

        with pytest.raises(Exception):
            await asyncio.gather(*tasks, return_exceptions=False)

        # Circuit should be open after threshold failures
        assert cb.state == CircuitState.OPEN
        assert cb.failure_count >= cb.failure_threshold

    @pytest.mark.asyncio
    async def test_recovery_timeout_precision(self) -> None:
        """Test recovery timeout precision."""
        cb = AsyncCircuitBreaker(failure_threshold=1, recovery_timeout=0.5, name="test")

        async def failing_function():
            raise Exception("Test error")

        # Open the circuit
        with pytest.raises(Exception):
            await cb.call(failing_function)

        assert cb.state == CircuitState.OPEN

        # Should still be blocked before timeout
        await asyncio.sleep(0.3)
        with pytest.raises(CircuitBreakerOpenError):
            await cb.call(failing_function)

        # Should transition to half-open after timeout
        await asyncio.sleep(0.3)  # Total: 0.6 seconds

        # This should transition to half-open and fail again
        with pytest.raises(Exception):
            await cb.call(failing_function)

    @pytest.mark.asyncio
    async def test_thread_safety_with_asyncio_lock(self) -> None:
        """Test that the circuit breaker uses asyncio.Lock for thread safety."""
        cb = AsyncCircuitBreaker(name="test")

        # Verify that _lock is an asyncio.Lock
        assert isinstance(cb._lock, asyncio.Lock)

        async def test_function():
            return "success"

        # Should work normally
        result = await cb.call(test_function)
        assert result == "success"

    @pytest.mark.asyncio
    async def test_exception_propagation(self) -> None:
        """Test that original exceptions are properly propagated."""
        cb = AsyncCircuitBreaker(name="test")

        class CustomException(Exception):
            def __init__(self, message, code):
                super().__init__(message)
                self.code = code

        async def custom_exception_function():
            raise CustomException("Custom error", 500)

        with pytest.raises(CustomException) as exc_info:
            await cb.call(custom_exception_function)

        assert str(exc_info.value) == "Custom error"
        assert exc_info.value.code == 500

    @pytest.mark.asyncio
    async def test_function_return_value_preservation(self) -> None:
        """Test that function return values are preserved."""
        cb = AsyncCircuitBreaker(name="test")

        async def complex_return_function():
            return {"data": [1, 2, 3], "status": "success", "nested": {"key": "value"}}

        result = await cb.call(complex_return_function)

        assert result["data"] == [1, 2, 3]
        assert result["status"] == "success"
        assert result["nested"]["key"] == "value"

    @pytest.mark.asyncio
    async def test_last_failure_time_tracking(self) -> None:
        """Test that last failure time is properly tracked."""
        cb = AsyncCircuitBreaker(name="test")

        async def failing_function():
            raise Exception("Test error")

        start_time = time.time()

        with pytest.raises(Exception):
            await cb.call(failing_function)

        end_time = time.time()

        assert start_time <= cb.last_failure_time <= end_time

        metrics = cb.get_metrics()
        assert metrics["time_since_last_failure"] >= 0


@pytest.mark.unit
class TestGlobalCircuitBreakers:
    """Test cases for global circuit breaker instances."""

    def test_websocket_circuit_breaker_configuration(self) -> None:
        """Test websocket circuit breaker configuration (defaults)."""
        assert websocket_circuit_breaker.name == "websocket"
        assert websocket_circuit_breaker.failure_threshold == 5
        assert websocket_circuit_breaker.recovery_timeout == 60
        assert websocket_circuit_breaker.half_open_max_calls == 3
        assert websocket_circuit_breaker.expected_exception is Exception

    def test_nats_circuit_breaker_configuration(self) -> None:
        """Test NATS circuit breaker configuration (defaults)."""
        assert nats_circuit_breaker.name == "nats"
        assert nats_circuit_breaker.failure_threshold == 3
        assert nats_circuit_breaker.recovery_timeout == 30
        assert nats_circuit_breaker.half_open_max_calls == 3
        assert nats_circuit_breaker.expected_exception is Exception

    def test_global_instances_are_different(self) -> None:
        """Test that global instances are separate."""
        assert websocket_circuit_breaker is not nats_circuit_breaker
        assert websocket_circuit_breaker.name != nats_circuit_breaker.name

    def test_global_instances_wired_to_constants_env_vars(self) -> None:
        """Per #133 AC2/AC3: changing the env vars must change the global

        circuit breakers' actual thresholds — not just the value read into
        `constants`, but the object `socket_client.core.client` calls
        `.call()` on. Runs in a fresh subprocess (rather than
        `importlib.reload` in-process) to avoid polluting this test
        session's module/class identities (reload rebinds `CircuitState`/
        `AsyncCircuitBreaker` in place, which breaks `is`/`==` checks in
        other tests that imported the pre-reload classes).
        """
        import json
        import subprocess
        import sys

        env_overrides = {
            "CIRCUIT_BREAKER_FAILURE_THRESHOLD": "17",
            "CIRCUIT_BREAKER_RECOVERY_TIMEOUT": "99",
            "CIRCUIT_BREAKER_HALF_OPEN_MAX_CALLS": "7",
            "NATS_CIRCUIT_BREAKER_FAILURE_THRESHOLD": "11",
            "NATS_CIRCUIT_BREAKER_RECOVERY_TIMEOUT": "44",
            "NATS_CIRCUIT_BREAKER_HALF_OPEN_MAX_CALLS": "9",
        }
        child_env = {**os.environ, **env_overrides}
        snippet = (
            "import json\n"
            "from socket_client.utils.circuit_breaker import (\n"
            "    websocket_circuit_breaker, nats_circuit_breaker,\n"
            ")\n"
            "print(json.dumps({\n"
            "    'ws_failure_threshold': websocket_circuit_breaker.failure_threshold,\n"
            "    'ws_recovery_timeout': websocket_circuit_breaker.recovery_timeout,\n"
            "    'ws_half_open_max_calls': websocket_circuit_breaker.half_open_max_calls,\n"
            "    'nats_failure_threshold': nats_circuit_breaker.failure_threshold,\n"
            "    'nats_recovery_timeout': nats_circuit_breaker.recovery_timeout,\n"
            "    'nats_half_open_max_calls': nats_circuit_breaker.half_open_max_calls,\n"
            "}))\n"
        )
        result = subprocess.run(
            [sys.executable, "-c", snippet],
            env=child_env,
            capture_output=True,
            text=True,
            timeout=30,
            check=True,
        )
        # structlog emits init-log lines to stdout before our json.dumps
        # print; the JSON payload is always the last line.
        last_line = result.stdout.strip().splitlines()[-1]
        values = json.loads(last_line)

        assert values["ws_failure_threshold"] == 17
        assert values["ws_recovery_timeout"] == 99
        assert values["ws_half_open_max_calls"] == 7
        assert values["nats_failure_threshold"] == 11
        assert values["nats_recovery_timeout"] == 44
        assert values["nats_half_open_max_calls"] == 9


@pytest.mark.unit
class TestCircuitBreakerOpenError:
    """Test cases for CircuitBreakerOpenError."""

    def test_circuit_breaker_open_error_inheritance(self) -> None:
        """Test CircuitBreakerOpenError inheritance."""
        error = CircuitBreakerOpenError("Test message")

        assert isinstance(error, Exception)
        assert str(error) == "Test message"

    def test_circuit_breaker_open_error_with_custom_message(self) -> None:
        """Test CircuitBreakerOpenError with custom message."""
        message = "Circuit 'test-circuit' is open due to failures"
        error = CircuitBreakerOpenError(message)

        assert str(error) == message


@pytest.mark.unit
class TestCircuitBreakerEdgeCases:
    """Test edge cases and error conditions."""

    @pytest.mark.asyncio
    async def test_zero_failure_threshold(self) -> None:
        """Test circuit breaker with zero failure threshold."""
        cb = AsyncCircuitBreaker(failure_threshold=0, name="test")

        async def any_function():
            return "success"

        # Should work normally with zero threshold
        result = await cb.call(any_function)
        assert result == "success"

    @pytest.mark.asyncio
    async def test_negative_recovery_timeout(self) -> None:
        """Test circuit breaker with negative recovery timeout."""
        cb = AsyncCircuitBreaker(failure_threshold=1, recovery_timeout=-1, name="test")

        async def failing_function():
            raise Exception("Test error")

        # Open the circuit
        with pytest.raises(Exception):
            await cb.call(failing_function)

        assert cb.state == CircuitState.OPEN

        # Should immediately transition to half-open due to negative timeout
        with pytest.raises(Exception):
            await cb.call(failing_function)

    @pytest.mark.asyncio
    async def test_very_large_failure_threshold(self) -> None:
        """Test circuit breaker with very large failure threshold."""
        cb = AsyncCircuitBreaker(failure_threshold=1000000, name="test")

        async def failing_function():
            raise Exception("Test error")

        # Should accumulate failures without opening
        for _ in range(100):
            with pytest.raises(Exception):
                await cb.call(failing_function)

        assert cb.state == CircuitState.CLOSED
        assert cb.failure_count == 100

    @pytest.mark.asyncio
    async def test_function_that_returns_none(self) -> None:
        """Test function that returns None."""
        cb = AsyncCircuitBreaker(name="test")

        async def none_returning_function():
            return None

        result = await cb.call(none_returning_function)
        assert result is None

    @pytest.mark.asyncio
    async def test_function_that_raises_keyboard_interrupt(self) -> None:
        """Test function that raises KeyboardInterrupt."""
        cb = AsyncCircuitBreaker(name="test")

        async def keyboard_interrupt_function():
            raise KeyboardInterrupt("User interrupted")

        # `call()` only catches `self.expected_exception` (default: Exception).
        # KeyboardInterrupt (like SystemExit and asyncio.CancelledError) is a
        # BaseException, not an Exception, so it is intentionally NOT caught
        # here -- it propagates immediately, unrecorded, and does not trip the
        # circuit. Catching BaseException instead would risk silently
        # swallowing asyncio.CancelledError during real cancellation, which
        # would be far worse than under-counting a Ctrl+C. See #136.
        with pytest.raises(KeyboardInterrupt):
            await cb.call(keyboard_interrupt_function)

        assert cb.failure_count == 0


@pytest.mark.unit
class TestCircuitBreakerPerformance:
    """Performance tests for circuit breaker."""

    @pytest.mark.asyncio
    async def test_performance_overhead(self) -> None:
        """Test performance overhead of circuit breaker.

        A ratio against a near-zero-cost baseline (an `await` on a function
        that just returns a literal) is not a portable CI signal: on a fast
        or lightly-loaded runner `direct_time` can be microseconds, so any
        fixed per-call cost (two lock acquisitions, a logger call) inflates
        the ratio by 10-20x with no actual regression -- this is what made
        the original `< 3.0` ratio assertion flake/fail across environments
        (#136). Assert an absolute per-call overhead bound instead, which
        stays meaningful regardless of how fast the bare-async-call baseline
        happens to be on a given runner.
        """
        cb = AsyncCircuitBreaker(name="test")
        iterations = 1000

        async def fast_function():
            return "fast"

        # Measure time with circuit breaker
        start_time = time.time()
        for _ in range(iterations):
            await cb.call(fast_function)
        cb_time = time.time() - start_time

        # Measure time without circuit breaker
        start_time = time.time()
        for _ in range(iterations):
            await fast_function()
        direct_time = time.time() - start_time

        # Circuit breaker overhead should be minimal in absolute terms.
        per_call_overhead_ms = ((cb_time - direct_time) / iterations) * 1000
        assert per_call_overhead_ms < 1.0  # Less than 1ms overhead per call

    @pytest.mark.asyncio
    async def test_memory_usage_stability(self) -> None:
        """Test that circuit breaker doesn't leak memory."""
        cb = AsyncCircuitBreaker(name="test")

        async def test_function():
            return "test"

        # Run many operations
        for _ in range(10000):
            await cb.call(test_function)

        # Metrics should remain stable
        metrics = cb.get_metrics()
        assert metrics["failure_count"] == 0
        assert metrics["state"] == "closed"
