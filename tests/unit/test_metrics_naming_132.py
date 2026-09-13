"""
Tests for the metrics fixes in #132 — 4 Grafana alert rules referenced
socket-client metrics that were never emitted.

Covers:
- Naming convention: all instruments in `socket_client.core.client` and the
  new circuit-breaker gauge use the `petrosa_socket_client_` prefix so they
  match the names already provisioned in
  `observability/alert-rules/socket-client-alerts.yaml` (petrosa_k8s repo) —
  no companion alert-rule PR is required.
- The `petrosa_socket_client_ws_reconnects_total` counter (renamed from
  `socket_client_reconnect_attempts_total`) still increments on reconnect
  attempts.
- The new `petrosa_socket_client_nats_publish_errors_total` counter
  increments when `nats_client.publish()` raises.
- The new `petrosa_socket_client_circuit_breaker_state` observable gauge
  reports a bounded (2 breakers * 3 states = 6 series) set of 0/1
  observations reflecting the *current* state of each breaker.

A subprocess (rather than in-process instrumentation) is used to install a
real `MeterProvider` + `InMemoryMetricReader` before the target modules are
imported, mirroring the pattern in `test_circuit_breaker_config_wiring.py`
(`set_meter_provider` is a global, one-shot call per process).
"""

import json
import os
import subprocess
import sys

import pytest


def _run_snippet(snippet: str) -> dict:
    # tests/conftest.py sets OTEL_SDK_DISABLED=true for the *test* process so
    # real telemetry never fires during the suite; that env var is inherited
    # by subprocess.run() by default and would silently no-op every SDK
    # instrument in the child too (InMemoryMetricReader.get_metrics_data()
    # then returns None). Explicitly re-enable the SDK in the child's env.
    child_env = {**os.environ, "OTEL_SDK_DISABLED": "false"}
    result = subprocess.run(
        [sys.executable, "-c", snippet],
        capture_output=True,
        text=True,
        timeout=30,
        env=child_env,
    )
    assert result.returncode == 0, result.stderr
    last_line = result.stdout.strip().splitlines()[-1]
    return json.loads(last_line)


@pytest.mark.unit
class TestMetricNamingConvention:
    """All client.py instruments use the petrosa_socket_client_ prefix."""

    def test_client_instrument_names_use_petrosa_prefix(self) -> None:
        snippet = (
            "import json\n"
            "from opentelemetry.sdk.metrics import MeterProvider\n"
            "from opentelemetry.sdk.metrics.export import InMemoryMetricReader\n"
            "reader = InMemoryMetricReader()\n"
            "from opentelemetry import metrics\n"
            "metrics.set_meter_provider(MeterProvider(metric_readers=[reader]))\n"
            "import socket_client.core.client as client_mod\n"
            "client_mod._messages_forwarded.add(1)\n"
            "client_mod._messages_dropped.add(1)\n"
            "client_mod._reconnect_attempts.add(1)\n"
            "client_mod._connection_errors.add(1)\n"
            "client_mod._nats_publish_errors.add(1)\n"
            "client_mod._processing_time.record(0.1)\n"
            "client_mod._queue_wait_time.record(0.1)\n"
            "data = reader.get_metrics_data()\n"
            "names = sorted(\n"
            "    m.name\n"
            "    for rm in data.resource_metrics\n"
            "    for sm in rm.scope_metrics\n"
            "    for m in sm.metrics\n"
            ")\n"
            "print(json.dumps(names))\n"
        )
        names = _run_snippet(snippet)

        expected = {
            "petrosa_socket_client_messages_forwarded_total",
            "petrosa_socket_client_messages_dropped_total",
            "petrosa_socket_client_ws_reconnects_total",
            "petrosa_socket_client_connection_errors_total",
            "petrosa_socket_client_nats_publish_errors_total",
            "petrosa_socket_client_message_processing_seconds",
            "petrosa_socket_client_queue_wait_seconds",
        }
        assert expected.issubset(set(names))
        # None of the old, un-prefixed names should survive the rename.
        assert not any(n.startswith("socket_client_") for n in names)


@pytest.mark.unit
class TestNatsPublishErrorCounter:
    """AC: a NATS publish-error counter is emitted on publish() failure."""

    @pytest.mark.asyncio
    async def test_nats_publish_failure_increments_counter(self) -> None:
        from unittest.mock import AsyncMock

        from socket_client.core import client as client_mod
        from socket_client.core.client import BinanceWebSocketClient

        client = BinanceWebSocketClient(
            ws_url="wss://test.com",
            streams=["btcusdt@trade"],
            nats_url="nats://localhost:4222",
            nats_topic="test.topic",
        )
        client.nats_client = AsyncMock()
        client.nats_client.is_closed = False
        client.nats_client.publish = AsyncMock(side_effect=Exception("boom"))

        add_calls = []
        orig_add = client_mod._nats_publish_errors.add

        def _spy_add(*args, **kwargs):
            add_calls.append((args, kwargs))
            return orig_add(*args, **kwargs)

        client_mod._nats_publish_errors.add = _spy_add  # type: ignore[method-assign]
        try:
            # Real Binance top-level trade-event shape (see tests/conftest.py
            # sample_trade_message / #136) — required for
            # _determine_stream_name() to resolve a non-None stream.
            await client._do_process_single_message(
                {"e": "trade", "E": 123456789, "s": "BTCUSDT", "t": 12345}
            )
        finally:
            client_mod._nats_publish_errors.add = orig_add  # type: ignore[method-assign]

        assert len(add_calls) == 1
        args, _kwargs = add_calls[0]
        assert args[0] == 1
        assert args[1]["service"] == "socket-client"


@pytest.mark.unit
class TestCircuitBreakerStateGauge:
    """AC: circuit-breaker state gauge, bounded labels, current state only."""

    def test_gauge_reports_bounded_current_state_series(self) -> None:
        snippet = (
            "import json\n"
            "from opentelemetry.sdk.metrics import MeterProvider\n"
            "from opentelemetry.sdk.metrics.export import InMemoryMetricReader\n"
            "reader = InMemoryMetricReader()\n"
            "from opentelemetry import metrics\n"
            "metrics.set_meter_provider(MeterProvider(metric_readers=[reader]))\n"
            "from socket_client.utils.circuit_breaker import (\n"
            "    CircuitState, websocket_circuit_breaker, nats_circuit_breaker,\n"
            ")\n"
            "websocket_circuit_breaker.state = CircuitState.OPEN\n"
            "nats_circuit_breaker.state = CircuitState.CLOSED\n"
            "data = reader.get_metrics_data()\n"
            "points = []\n"
            "for rm in data.resource_metrics:\n"
            "    for sm in rm.scope_metrics:\n"
            "        for m in sm.metrics:\n"
            "            if m.name != 'petrosa_socket_client_circuit_breaker_state':\n"
            "                continue\n"
            "            for pt in m.data.data_points:\n"
            "                points.append((dict(pt.attributes), pt.value))\n"
            "print(json.dumps(points))\n"
        )
        points = _run_snippet(snippet)

        # Bounded: exactly 2 breakers * 3 states = 6 series, every call.
        assert len(points) == 6

        by_key = {(attrs["name"], attrs["state"]): value for attrs, value in points}
        assert by_key[("websocket", "open")] == 1.0
        assert by_key[("websocket", "closed")] == 0.0
        assert by_key[("websocket", "half_open")] == 0.0
        assert by_key[("nats", "closed")] == 1.0
        assert by_key[("nats", "open")] == 0.0
        assert by_key[("nats", "half_open")] == 0.0

        for attrs, _value in points:
            assert attrs["service"] == "socket-client"
            assert attrs["name"] in ("websocket", "nats")
            assert attrs["state"] in ("open", "closed", "half_open")
