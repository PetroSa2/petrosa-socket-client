import json
import os
import subprocess
import sys
from unittest.mock import AsyncMock, MagicMock

import pytest

from socket_client.core.client import BinanceWebSocketClient


def _metric_snapshot() -> list[dict[str, object]]:
    script = """
import json
from opentelemetry import metrics
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import InMemoryMetricReader
reader = InMemoryMetricReader()
metrics.set_meter_provider(MeterProvider(metric_readers=[reader]))
import socket_client.core.client as module
module._socket_messages.add(1, {"direction": "outbound", "outcome": "success"})
module._socket_connections.callback if hasattr(module._socket_connections, "callback") else None
data = reader.get_metrics_data()
result = []
for resource in data.resource_metrics:
    for scope in resource.scope_metrics:
        for metric in scope.metrics:
            if metric.name in {"petrosa_socket_connections", "petrosa_socket_messages_total"}:
                result.append({"name": metric.name, "labels": [dict(p.attributes) for p in metric.data.data_points]})
print(json.dumps(result))
"""
    environment = {**os.environ, "OTEL_SDK_DISABLED": "false"}
    result = subprocess.run(
        [sys.executable, "-c", script], capture_output=True, text=True, env=environment
    )
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout.strip().splitlines()[-1])


@pytest.mark.unit
def test_socket_metrics_have_required_names_and_labels() -> None:
    metrics = _metric_snapshot()
    by_name = {metric["name"]: metric["labels"] for metric in metrics}
    assert set(by_name) == {
        "petrosa_socket_connections",
        "petrosa_socket_messages_total",
    }
    assert {"direction", "outcome"}.issubset(
        by_name["petrosa_socket_messages_total"][0]
    )
    assert {"state"}.issubset(by_name["petrosa_socket_connections"][0])


@pytest.mark.unit
def test_summary_is_bounded_and_uses_five_minute_window() -> None:
    logger = MagicMock()
    client = BinanceWebSocketClient(
        ws_url="wss://example.invalid",
        streams=["btcusdt@trade"],
        nats_url="nats://example.invalid",
        nats_topic="test",
        logger=logger,
    )
    client._summary_messages["outbound_success"] = 2
    client._summary_outcomes["success"] = 2
    client._recent_publish_latencies.extend([0.01, 0.02, 0.03])

    client._emit_summary()

    logger.info.assert_called_once()
    args, fields = logger.info.call_args
    assert args == ("SUMMARY",)
    assert fields["window_seconds"] == 300
    assert fields["service"] == "petrosa-socket-client"
    assert set(fields) == {
        "window_seconds",
        "service",
        "started_at",
        "counters",
        "outcomes",
        "connection_state",
        "latency_ms",
    }
    assert set(fields["latency_ms"]) == {"p50", "p95"}


@pytest.mark.unit
@pytest.mark.asyncio
async def test_expected_skip_is_debug_and_publish_success_updates_metric() -> None:
    logger = MagicMock()
    client = BinanceWebSocketClient(
        ws_url="wss://example.invalid",
        streams=["btcusdt@trade"],
        nats_url="nats://example.invalid",
        nats_topic="test",
        logger=logger,
    )
    await client._do_process_single_message({"invalid": "shape"})
    logger.debug.assert_called()

    client.nats_client = MagicMock(is_closed=False)
    client.nats_client.publish = AsyncMock()
    await client._do_process_single_message({"e": "trade", "s": "BTCUSDT"})
    client.nats_client.publish.assert_awaited_once()
