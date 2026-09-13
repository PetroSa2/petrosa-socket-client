"""
Circuit breaker pattern implementation for the Socket Client.

This module provides a circuit breaker pattern to handle connection failures
and prevent cascading failures in the WebSocket client.
"""

import asyncio
import time
from collections.abc import Callable, Iterable
from enum import Enum
from typing import Any, TypeVar, cast

from opentelemetry import metrics
from opentelemetry.metrics import CallbackOptions, Observation
from structlog import get_logger

import constants

logger = get_logger(__name__)

T = TypeVar("T")


class CircuitState(Enum):
    """Circuit breaker states."""

    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class AsyncCircuitBreaker:
    """Async circuit breaker implementation."""

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        expected_exception: type = Exception,
        name: str = "default",
        half_open_max_calls: int = 3,
    ) -> None:
        """
        Initialize the circuit breaker.

        Args:
            failure_threshold: Number of failures before opening circuit
            recovery_timeout: Time in seconds before attempting recovery
            expected_exception: Exception type to count as failures
            name: Circuit breaker name for logging
            half_open_max_calls: Max number of trial calls admitted while the
                circuit is HALF_OPEN. Additional calls are rejected with
                CircuitBreakerOpenError until the trial batch resolves the
                circuit back to CLOSED (success) or OPEN (failure).
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        self.name = name
        self.half_open_max_calls = half_open_max_calls

        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time: float = 0.0
        self.half_open_calls = 0
        self._lock = asyncio.Lock()

        logger.info(
            "Circuit breaker initialized",
            name=name,
            failure_threshold=failure_threshold,
            recovery_timeout=recovery_timeout,
            half_open_max_calls=half_open_max_calls,
        )

    async def call(self, func: Callable[..., T], *args: Any, **kwargs: Any) -> T:
        """
        Execute a function with circuit breaker protection.

        Args:
            func: Function to execute
            *args: Function arguments
            **kwargs: Function keyword arguments

        Returns:
            Function result

        Raises:
            CircuitBreakerOpenError: When circuit is open
            Exception: Original function exception
        """
        async with self._lock:
            if self.state == CircuitState.OPEN:
                if time.time() - self.last_failure_time >= self.recovery_timeout:
                    self.state = CircuitState.HALF_OPEN
                    self.half_open_calls = 0
                    logger.info(
                        "Circuit breaker transitioning to half-open", name=self.name
                    )
                else:
                    raise CircuitBreakerOpenError(
                        f"Circuit breaker '{self.name}' is open"
                    )

            if self.state == CircuitState.HALF_OPEN:
                if self.half_open_calls >= self.half_open_max_calls:
                    raise CircuitBreakerOpenError(
                        f"Circuit breaker '{self.name}' is half-open and at its "
                        f"trial-call limit ({self.half_open_max_calls})"
                    )
                self.half_open_calls += 1

        try:
            if asyncio.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                result = func(*args, **kwargs)

            await self._on_success()
            return cast(T, result)

        except self.expected_exception:  # type: ignore[misc]
            await self._on_failure()
            raise

    async def _on_success(self) -> None:
        """Handle successful execution."""
        async with self._lock:
            if self.state == CircuitState.HALF_OPEN:
                self.state = CircuitState.CLOSED
                self.half_open_calls = 0
                logger.info(
                    "Circuit breaker closed after successful execution", name=self.name
                )
            self.failure_count = 0

    async def _on_failure(self) -> None:
        """Handle failed execution."""
        async with self._lock:
            self.failure_count += 1
            self.last_failure_time = time.time()

            logger.warning(
                "Circuit breaker failure recorded",
                name=self.name,
                failure_count=self.failure_count,
                threshold=self.failure_threshold,
            )

            if self.state == CircuitState.HALF_OPEN:
                self.state = CircuitState.OPEN
                self.half_open_calls = 0
                logger.error(
                    "Circuit breaker reopened after half-open trial failure",
                    name=self.name,
                )
            elif self.failure_count >= self.failure_threshold:
                self.state = CircuitState.OPEN
                logger.error(
                    "Circuit breaker opened due to failure threshold",
                    name=self.name,
                    failure_count=self.failure_count,
                )

    def get_state(self) -> CircuitState:
        """Get current circuit breaker state."""
        return self.state

    def get_metrics(self) -> dict:
        """Get circuit breaker metrics."""
        return {
            "name": self.name,
            "state": self.state.value,
            "failure_count": self.failure_count,
            "failure_threshold": self.failure_threshold,
            "recovery_timeout": self.recovery_timeout,
            "half_open_max_calls": self.half_open_max_calls,
            "half_open_calls": self.half_open_calls,
            "last_failure_time": self.last_failure_time,
            "time_since_last_failure": time.time() - self.last_failure_time,
        }


class CircuitBreakerOpenError(Exception):
    """Exception raised when circuit breaker is open."""

    pass


# Global circuit breaker instances.
#
# Per #133: these MUST read from `constants` (env-var backed) rather than
# hardcoding literals — operators tune failure_threshold/recovery_timeout via
# the k8s ConfigMap (CIRCUIT_BREAKER_FAILURE_THRESHOLD/_RECOVERY_TIMEOUT/
# _HALF_OPEN_MAX_CALLS) and expect it to take effect.
websocket_circuit_breaker = AsyncCircuitBreaker(
    failure_threshold=constants.CIRCUIT_BREAKER_FAILURE_THRESHOLD,
    recovery_timeout=constants.CIRCUIT_BREAKER_RECOVERY_TIMEOUT,
    expected_exception=Exception,
    name="websocket",
    half_open_max_calls=constants.CIRCUIT_BREAKER_HALF_OPEN_MAX_CALLS,
)

nats_circuit_breaker = AsyncCircuitBreaker(
    failure_threshold=constants.NATS_CIRCUIT_BREAKER_FAILURE_THRESHOLD,
    recovery_timeout=constants.NATS_CIRCUIT_BREAKER_RECOVERY_TIMEOUT,
    expected_exception=Exception,
    name="nats",
    half_open_max_calls=constants.NATS_CIRCUIT_BREAKER_HALF_OPEN_MAX_CALLS,
)

# OpenTelemetry gauge for circuit-breaker state (per #132).
#
# Emits one series per (breaker name, state) pair on every collection —
# value 1.0 for the breaker's current state, 0.0 for the other two — rather
# than only emitting the current state. This keeps the series set constantly
# present (bounded: 2 breakers * 3 states = 6 series) so the Grafana alert
# `max(petrosa_socket_client_circuit_breaker_state{state="open"}) > 0`
# evaluates against real 0/1 data instead of a label combination that only
# exists while OPEN.
_meter = metrics.get_meter(__name__)


def _observe_circuit_breaker_state(
    options: CallbackOptions,
) -> Iterable[Observation]:
    for breaker in (websocket_circuit_breaker, nats_circuit_breaker):
        current_state = breaker.get_state()
        for state in CircuitState:
            yield Observation(
                1.0 if state is current_state else 0.0,
                {
                    "service": "socket-client",
                    "name": breaker.name,
                    "state": state.value,
                },
            )


_circuit_breaker_state_gauge = _meter.create_observable_gauge(
    "petrosa_socket_client_circuit_breaker_state",
    callbacks=[_observe_circuit_breaker_state],
    description="Circuit breaker state (1=current state, 0=other states); labels: name, state",
)
