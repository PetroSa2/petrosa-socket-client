"""
Tests for circuit breaker configuration wiring (per #133).

`tests/unit/test_circuit_breaker.py` is excluded from the default pytest run
(see `pytest.ini` `--ignore=tests/unit/test_circuit_breaker.py`), so the
acceptance-criteria-critical tests for #133 live here instead, where they
are guaranteed to actually run in CI:

- AC2: changing `CIRCUIT_BREAKER_FAILURE_THRESHOLD` / `_RECOVERY_TIMEOUT`
  (and the NATS equivalents) in the environment must measurably change the
  module-level `websocket_circuit_breaker` / `nats_circuit_breaker`
  instances that `socket_client/core/client.py` actually calls `.call()`
  on — not just the value parsed into `constants`.
- AC3: `half_open_max_calls` must have a real, enforced implementation.
"""

import asyncio
import json
import os
import subprocess
import sys

import pytest

from socket_client.utils.circuit_breaker import (
    AsyncCircuitBreaker,
    CircuitBreakerOpenError,
    CircuitState,
    nats_circuit_breaker,
    websocket_circuit_breaker,
)


@pytest.mark.unit
class TestGlobalCircuitBreakerDefaults:
    """Defaults must match constants.py's own env-var defaults."""

    def test_websocket_circuit_breaker_defaults(self) -> None:
        assert websocket_circuit_breaker.name == "websocket"
        assert websocket_circuit_breaker.failure_threshold == 5
        assert websocket_circuit_breaker.recovery_timeout == 60
        assert websocket_circuit_breaker.half_open_max_calls == 3

    def test_nats_circuit_breaker_defaults(self) -> None:
        assert nats_circuit_breaker.name == "nats"
        assert nats_circuit_breaker.failure_threshold == 3
        assert nats_circuit_breaker.recovery_timeout == 30
        assert nats_circuit_breaker.half_open_max_calls == 3


@pytest.mark.unit
class TestGlobalCircuitBreakersWiredToConstants:
    """AC2: env vars must actually change the running circuit breakers."""

    def test_global_instances_wired_to_constants_env_vars(self) -> None:
        """Spawn a fresh subprocess with overridden env vars and assert the

        module-level circuit breaker instances pick them up at import time.
        A subprocess (rather than in-process `importlib.reload`) is used
        deliberately: reloading `circuit_breaker` in-process rebinds
        `CircuitState`/`AsyncCircuitBreaker` in the module's `__dict__`,
        which silently breaks `==`/`isinstance` checks in any test that
        already imported the pre-reload classes.
        """
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
class TestHalfOpenMaxCallsEnforced:
    """AC3: half_open_max_calls must be a real, enforced limit."""

    @pytest.mark.asyncio
    async def test_half_open_max_calls_limits_trial_calls(self) -> None:
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
    async def test_half_open_calls_reset_on_reopen(self) -> None:
        cb = AsyncCircuitBreaker(
            failure_threshold=1,
            recovery_timeout=0.1,
            name="test-half-open-reopen-reset",
            half_open_max_calls=3,
        )

        async def failing_function():
            raise Exception("Test error")

        with pytest.raises(Exception):
            await cb.call(failing_function)
        assert cb.state == CircuitState.OPEN

        await asyncio.sleep(0.15)

        # HALF_OPEN trial fails -> reopens, half_open_calls resets to 0.
        with pytest.raises(Exception):
            await cb.call(failing_function)
        assert cb.state == CircuitState.OPEN
        assert cb.half_open_calls == 0

    def test_get_metrics_includes_half_open_fields(self) -> None:
        cb = AsyncCircuitBreaker(name="test-metrics", half_open_max_calls=4)
        metrics = cb.get_metrics()
        assert metrics["half_open_max_calls"] == 4
        assert metrics["half_open_calls"] == 0
