"""Socket-client health evaluator (P2.7, petrosa_k8s#697 AC1 / socket-client#123).

Emits ``evaluator.socket-client.verdict`` via the shared P2.1 framework
(:mod:`petrosa_otel.evaluators`) so the operator dashboard's evaluator strip
counts socket-client among the reporting subsystems (FR17 / FR23 / FR32).

The verdict combines three health signals sampled from the running
``BinanceWebSocketClient`` on each emit tick:

1. **NATS publish latency** — rolling mean of the per-message dequeue→publish
   duration (the ``socket_client_message_processing_seconds`` instrument's
   source). A sustained high value means NATS publishing is backpressured.
2. **WebSocket reconnection rate** — the increase in ``reconnect_attempts``
   over one emit interval. A burst of reconnects means the upstream Binance
   socket is flapping.
3. **Message-throughput rolling mean vs baseline** — per-tick forwarded-message
   rate compared against a rolling baseline. A collapse to a small fraction of
   baseline while still connected means messages have stopped flowing.

Verdict vocabulary is the framework's locked three-state contract
(``healthy`` / ``unhealthy`` / ``unknown``); the framework intentionally has no
separate ``degraded`` state, so any breached signal maps to ``unhealthy`` and
the reason string names which signal tripped (NFR-O5 verbatim render).

Hysteresis / cadence (AC4 / AC7, FR18 per-evaluator ``decision_window``):
the evaluator emits every ``EMIT_INTERVAL_S`` (15s) and, via
``ConsecutiveSamplesHysteresis(n=HYSTERESIS_SAMPLES)`` (n=3), only flips its
published verdict after 3 consecutive matching samples — roughly a 45s
decision window. This matches socket-client's high-cadence signals: a single
slow tick or transient reconnect should not flap the verdict, but a sustained
condition surfaces within ~45s.
"""

from __future__ import annotations

import asyncio
import logging
from collections import deque
from collections.abc import Callable
from datetime import datetime
from typing import TYPE_CHECKING, Any

try:
    from datetime import UTC
except ImportError:  # pragma: no cover - py310 compatibility
    from datetime import timezone

    UTC = timezone.utc  # noqa: UP017

from petrosa_otel.evaluators import (
    ConsecutiveSamplesHysteresis,
    Evaluator,
    NatsVerdictPublisher,
)

if TYPE_CHECKING:
    from petrosa_otel.evaluators.base import HysteresisPolicy
    from petrosa_otel.evaluators.publisher import VerdictPublisher

    from socket_client.core.client import BinanceWebSocketClient

logger = logging.getLogger(__name__)

SUBSYSTEM = "socket-client"

# Cadence + smoothing (documented per AC4 / AC7).
EMIT_INTERVAL_S = 15.0
HYSTERESIS_SAMPLES = 3

# Signal thresholds.
# Publish latency: the healthy dequeue→publish path is sub-millisecond; 500ms
# sustained indicates NATS backpressure or a stalled publish path.
DEFAULT_LATENCY_THRESHOLD_S = 0.5
# Reconnect rate: 3+ reconnect attempts inside one emit interval is sustained
# flapping rather than a single transient drop.
DEFAULT_RECONNECT_RATE_THRESHOLD = 3
# Throughput collapse: once a baseline is established, dropping below 10% of the
# rolling-mean rate while still connected means messages have effectively
# stopped flowing.
DEFAULT_THROUGHPUT_COLLAPSE_RATIO = 0.1
# Rolling baseline window for the throughput mean (8 samples ≈ 2 min at 15s).
DEFAULT_BASELINE_WINDOW = 8
# Minimum baseline samples before the throughput-collapse check may trip.
DEFAULT_MIN_BASELINE_SAMPLES = 4


class SocketClientHealthEvaluator(Evaluator):
    """Subsystem evaluator for socket-client WebSocket→NATS forwarding health."""

    def __init__(
        self,
        *,
        metrics_source: Callable[[], dict[str, Any]],
        publisher: VerdictPublisher | None = None,
        hysteresis: HysteresisPolicy | None = None,
        latency_threshold_s: float = DEFAULT_LATENCY_THRESHOLD_S,
        reconnect_rate_threshold: int = DEFAULT_RECONNECT_RATE_THRESHOLD,
        throughput_collapse_ratio: float = DEFAULT_THROUGHPUT_COLLAPSE_RATIO,
        baseline_window: int = DEFAULT_BASELINE_WINDOW,
        min_baseline_samples: int = DEFAULT_MIN_BASELINE_SAMPLES,
        emit_interval_s: float = EMIT_INTERVAL_S,
        time_source: Callable[[], datetime] | None = None,
    ) -> None:
        super().__init__(
            subsystem=SUBSYSTEM,
            publisher=publisher,
            hysteresis=hysteresis or ConsecutiveSamplesHysteresis(n=HYSTERESIS_SAMPLES),
        )
        self._metrics_source = metrics_source
        self._latency_threshold_s = latency_threshold_s
        self._reconnect_rate_threshold = reconnect_rate_threshold
        self._throughput_collapse_ratio = throughput_collapse_ratio
        self._min_baseline_samples = max(1, min_baseline_samples)
        self._emit_interval_s = emit_interval_s
        self._time = time_source or (lambda: datetime.now(UTC))

        self._throughput_baseline: deque[float] = deque(maxlen=max(1, baseline_window))
        self._prev_processed: int | None = None
        self._prev_reconnects: int = 0
        self._prev_sample_at: datetime | None = None

        self._emit_task: asyncio.Task[Any] | None = None

    # ----- lifecycle -----

    async def start(self) -> None:
        """Start the periodic emit loop (idempotent)."""
        if self._emit_task is not None:
            return
        self._emit_task = asyncio.create_task(self._emit_loop())
        logger.info(
            "socket_client_health_evaluator_started",
            extra={
                "subsystem": SUBSYSTEM,
                "emit_interval_s": self._emit_interval_s,
            },
        )

    async def stop(self) -> None:
        """Stop the emit loop."""
        if self._emit_task is None:
            return
        self._emit_task.cancel()
        try:
            await self._emit_task
        except asyncio.CancelledError:
            pass
        except Exception as exc:  # noqa: BLE001
            logger.warning(f"socket_client_health_evaluator stop error: {exc}")
        self._emit_task = None

    async def _emit_loop(self) -> None:
        while True:
            try:
                await self.tick()
            except Exception as exc:  # noqa: BLE001 — never crash the loop
                logger.warning(
                    "socket_client_health_evaluator_tick_failed",
                    extra={"error": str(exc)},
                )
            await asyncio.sleep(self._emit_interval_s)

    # ----- framework hook -----

    async def evaluate(self) -> tuple[str, str]:
        """Compute the raw ``(verdict, reason)`` sample for the current state."""
        snapshot = self._metrics_source()
        now = self._time()

        processed = int(snapshot.get("processed_messages", 0) or 0)
        reconnects = int(snapshot.get("reconnect_attempts", 0) or 0)
        latency_s = float(snapshot.get("recent_publish_latency_s", 0.0) or 0.0)
        ws_connected = snapshot.get("websocket_state") == "connected"
        nats_connected = snapshot.get("nats_state") == "connected"

        prev_processed = self._prev_processed
        prev_reconnects = self._prev_reconnects
        prev_at = self._prev_sample_at

        # Advance bookkeeping for the next tick before any early return.
        self._prev_processed = processed
        self._prev_reconnects = reconnects
        self._prev_sample_at = now

        # First sample: nothing to diff against yet.
        if prev_processed is None or prev_at is None:
            return "unknown", "establishing baseline (first sample)"

        # Counter reset (pod restart) — diffing would be meaningless.
        if processed < prev_processed or reconnects < prev_reconnects:
            self._throughput_baseline.clear()
            return "unknown", "counter reset detected; rebaselining"

        # 1) Connectivity is the dominant signal.
        if not nats_connected:
            return "unhealthy", "NATS disconnected; messages cannot be forwarded"
        if not ws_connected:
            return "unhealthy", "Binance WebSocket disconnected"

        # 2) Reconnection rate.
        reconnect_delta = reconnects - prev_reconnects
        if reconnect_delta >= self._reconnect_rate_threshold:
            return (
                "unhealthy",
                f"WebSocket flapping: {reconnect_delta} reconnects in last "
                f"{int(self._emit_interval_s)}s",
            )

        # 3) NATS publish latency.
        if latency_s > self._latency_threshold_s:
            return (
                "unhealthy",
                f"NATS publish latency {latency_s * 1000:.0f}ms > "
                f"{self._latency_threshold_s * 1000:.0f}ms threshold",
            )

        # 4) Throughput rolling mean vs baseline.
        interval_s = (now - prev_at).total_seconds()
        rate = (processed - prev_processed) / interval_s if interval_s > 0 else 0.0
        if (
            len(self._throughput_baseline) >= self._min_baseline_samples
            and self._throughput_baseline
        ):
            baseline_mean = sum(self._throughput_baseline) / len(
                self._throughput_baseline
            )
            if (
                baseline_mean > 0
                and rate < self._throughput_collapse_ratio * baseline_mean
            ):
                # Record before returning so recovery re-establishes baseline.
                self._throughput_baseline.append(rate)
                return (
                    "unhealthy",
                    f"throughput collapsed: {rate:.1f} msg/s vs baseline "
                    f"{baseline_mean:.1f} msg/s",
                )
        self._throughput_baseline.append(rate)

        return (
            "healthy",
            f"{rate:.1f} msg/s, latency {latency_s * 1000:.0f}ms, "
            f"reconnects {reconnect_delta}",
        )


def build_socket_client_health_evaluator(
    client: BinanceWebSocketClient,
) -> SocketClientHealthEvaluator | None:
    """Construct an evaluator wired to ``client``'s NATS connection.

    Returns ``None`` when the client has no live NATS connection yet — the
    publisher would have nowhere to write. Call after ``client.start()``.
    """
    nats_client = getattr(client, "nats_client", None)
    if nats_client is None:
        logger.warning(
            "socket_client_health_evaluator not started: no NATS client available"
        )
        return None
    publisher = NatsVerdictPublisher(nats_client=nats_client)
    return SocketClientHealthEvaluator(
        metrics_source=client.get_metrics,
        publisher=publisher,
    )
