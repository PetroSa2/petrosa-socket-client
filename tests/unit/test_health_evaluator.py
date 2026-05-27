"""Unit tests for SocketClientHealthEvaluator (socket-client#123, P2.7 AC1)."""

import json
from datetime import UTC, datetime, timedelta

import pytest
from petrosa_otel.evaluators import ConsecutiveSamplesHysteresis
from petrosa_otel.evaluators.publisher import (
    EVALUATOR_SUBJECT_TEMPLATE,
    NatsVerdictPublisher,
)

from socket_client.evaluators import (
    SocketClientHealthEvaluator,
    build_socket_client_health_evaluator,
)


class FakeClock:
    """Monotonic clock that advances a fixed step on every read."""

    def __init__(self, start: datetime, step: timedelta) -> None:
        self._t = start
        self._step = step

    def __call__(self) -> datetime:
        now = self._t
        self._t = self._t + self._step
        return now


class MetricsSource:
    """Mutable snapshot the test rewrites between ticks."""

    def __init__(self) -> None:
        self.snap = {
            "processed_messages": 0,
            "reconnect_attempts": 0,
            "recent_publish_latency_s": 0.0,
            "websocket_state": "connected",
            "nats_state": "connected",
        }

    def __call__(self) -> dict:
        return dict(self.snap)


class FakeNats:
    """Records (subject, payload) tuples for publish-subject assertions."""

    def __init__(self) -> None:
        self.messages: list[tuple[str, bytes]] = []

    async def publish(self, subject: str, payload: bytes) -> None:
        self.messages.append((subject, payload))


def _make(
    source: MetricsSource,
    clock: FakeClock,
    *,
    publisher=None,
    n: int = 1,
) -> SocketClientHealthEvaluator:
    return SocketClientHealthEvaluator(
        metrics_source=source,
        publisher=publisher,
        hysteresis=ConsecutiveSamplesHysteresis(n=n),
        time_source=clock,
    )


@pytest.fixture
def clock() -> FakeClock:
    return FakeClock(datetime(2026, 5, 27, 12, 0, 0, tzinfo=UTC), timedelta(seconds=15))


@pytest.mark.asyncio
async def test_first_sample_is_unknown(clock):
    src = MetricsSource()
    ev = _make(src, clock)
    verdict, reason = await ev.evaluate()
    assert verdict == "unknown"
    assert "baseline" in reason.lower()


@pytest.mark.asyncio
async def test_healthy_when_connected_and_flowing(clock):
    src = MetricsSource()
    ev = _make(src, clock)
    await ev.evaluate()  # prime baseline
    src.snap["processed_messages"] = 1500  # ~100 msg/s over 15s
    verdict, reason = await ev.evaluate()
    assert verdict == "healthy"
    assert "msg/s" in reason


@pytest.mark.asyncio
async def test_unhealthy_when_nats_disconnected(clock):
    src = MetricsSource()
    ev = _make(src, clock)
    await ev.evaluate()
    src.snap["nats_state"] = "disconnected"
    verdict, reason = await ev.evaluate()
    assert verdict == "unhealthy"
    assert "NATS" in reason


@pytest.mark.asyncio
async def test_unhealthy_when_websocket_disconnected(clock):
    src = MetricsSource()
    ev = _make(src, clock)
    await ev.evaluate()
    src.snap["websocket_state"] = "disconnected"
    verdict, reason = await ev.evaluate()
    assert verdict == "unhealthy"
    assert "WebSocket" in reason


@pytest.mark.asyncio
async def test_unhealthy_on_reconnect_burst(clock):
    src = MetricsSource()
    ev = _make(src, clock)
    await ev.evaluate()
    src.snap["reconnect_attempts"] = 4  # >= threshold (3) in one interval
    verdict, reason = await ev.evaluate()
    assert verdict == "unhealthy"
    assert "flapping" in reason


@pytest.mark.asyncio
async def test_unhealthy_on_high_latency(clock):
    src = MetricsSource()
    ev = _make(src, clock)
    await ev.evaluate()
    src.snap["recent_publish_latency_s"] = 1.2  # > 0.5s threshold
    verdict, reason = await ev.evaluate()
    assert verdict == "unhealthy"
    assert "latency" in reason


@pytest.mark.asyncio
async def test_unhealthy_on_throughput_collapse(clock):
    src = MetricsSource()
    ev = _make(src, clock)
    await ev.evaluate()  # prime
    # Four healthy high-throughput samples establish the baseline.
    processed = 0
    for _ in range(4):
        processed += 1500
        src.snap["processed_messages"] = processed
        verdict, _ = await ev.evaluate()
        assert verdict == "healthy"
    # Throughput collapses to ~0 while still connected.
    src.snap["processed_messages"] = processed  # no new messages
    verdict, reason = await ev.evaluate()
    assert verdict == "unhealthy"
    assert "throughput collapsed" in reason


@pytest.mark.asyncio
async def test_counter_reset_returns_unknown(clock):
    src = MetricsSource()
    ev = _make(src, clock)
    src.snap["processed_messages"] = 5000
    await ev.evaluate()
    src.snap["processed_messages"] = 10  # pod restart resets the counter
    verdict, reason = await ev.evaluate()
    assert verdict == "unknown"
    assert "reset" in reason.lower()


@pytest.mark.asyncio
async def test_publishes_on_socket_client_subject(clock):
    src = MetricsSource()
    nats = FakeNats()
    publisher = NatsVerdictPublisher(nats_client=nats)
    ev = _make(src, clock, publisher=publisher, n=1)

    await ev.tick()  # unknown (baseline)
    src.snap["processed_messages"] = 1500
    await ev.tick()  # healthy

    assert nats.messages, "evaluator did not publish"
    subject, payload = nats.messages[-1]
    assert subject == "evaluator.socket-client.verdict"
    assert subject == EVALUATOR_SUBJECT_TEMPLATE.format(subsystem="socket-client")
    body = json.loads(payload.decode())
    assert body["subsystem"] == "socket-client"
    assert body["verdict"] == "healthy"


@pytest.mark.asyncio
async def test_hysteresis_suppresses_single_flap(clock):
    src = MetricsSource()
    ev = _make(src, clock, n=3)

    # Commit healthy: needs 3 consecutive healthy samples.
    await ev.tick()  # unknown baseline
    processed = 0
    for _ in range(3):
        processed += 1500
        src.snap["processed_messages"] = processed
        v = await ev.tick()
    assert v.verdict == "healthy"

    # One disconnected sample must NOT flip the committed verdict (n=3).
    src.snap["nats_state"] = "disconnected"
    v = await ev.tick()
    assert v.verdict == "healthy"


def test_build_returns_none_without_nats():
    class _Client:
        nats_client = None

        def get_metrics(self) -> dict:
            return {}

    assert build_socket_client_health_evaluator(_Client()) is None
