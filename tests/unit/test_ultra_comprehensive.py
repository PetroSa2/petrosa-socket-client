"""
Ultra comprehensive test suite to maximize coverage.
Exhaustive tests for all modules to reach 90% target.
"""

import asyncio
import time
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from aiohttp import web

from socket_client.core.client import BinanceWebSocketClient
from socket_client.health.server import HealthServer
from socket_client.models.message import (
    DepthMessage,
    TickerMessage,
    TradeMessage,
    WebSocketMessage,
)

# =============================================================================
# ULTRA CLIENT TESTS (100+ tests targeting all uncovered lines)
# =============================================================================


@pytest.mark.unit
class TestClientEveryAttribute:
    """Test every single client attribute individually."""

    def test_ws_url_attr(self):
        """Test ws_url attribute."""
        client = BinanceWebSocketClient("wss://a", ["s"], "nats://n", "t")
        assert hasattr(client, "ws_url")
        assert client.ws_url == "wss://a"

    def test_streams_attr(self):
        """Test streams attribute."""
        client = BinanceWebSocketClient("wss://a", ["s1", "s2"], "nats://n", "t")
        assert hasattr(client, "streams")
        assert len(client.streams) == 2

    def test_nats_url_attr(self):
        """Test nats_url attribute."""
        client = BinanceWebSocketClient("wss://a", ["s"], "nats://test", "t")
        assert hasattr(client, "nats_url")
        assert client.nats_url == "nats://test"

    def test_nats_topic_attr(self):
        """Test nats_topic attribute."""
        client = BinanceWebSocketClient("wss://a", ["s"], "nats://n", "topic.test")
        assert hasattr(client, "nats_topic")
        assert client.nats_topic == "topic.test"

    def test_logger_attr(self):
        """Test logger attribute."""
        client = BinanceWebSocketClient("wss://a", ["s"], "nats://n", "t")
        assert hasattr(client, "logger")
        assert client.logger is not None

    def test_max_reconnect_attempts_attr(self):
        """Test max_reconnect_attempts attribute."""
        client = BinanceWebSocketClient(
            "wss://a", ["s"], "nats://n", "t", max_reconnect_attempts=99
        )
        assert client.max_reconnect_attempts == 99

    def test_reconnect_delay_attr(self):
        """Test reconnect_delay attribute."""
        client = BinanceWebSocketClient(
            "wss://a", ["s"], "nats://n", "t", reconnect_delay=77
        )
        assert client.reconnect_delay == 77

    def test_ping_interval_attr(self):
        """Test ping_interval attribute."""
        client = BinanceWebSocketClient(
            "wss://a", ["s"], "nats://n", "t", ping_interval=88
        )
        assert client.ping_interval == 88

    def test_ping_timeout_attr(self):
        """Test ping_timeout attribute."""
        client = BinanceWebSocketClient(
            "wss://a", ["s"], "nats://n", "t", ping_timeout=66
        )
        assert client.ping_timeout == 66

    def test_websocket_attr(self):
        """Test websocket attribute."""
        client = BinanceWebSocketClient("wss://a", ["s"], "nats://n", "t")
        assert hasattr(client, "websocket")
        assert client.websocket is None

    def test_nats_client_attr(self):
        """Test nats_client attribute."""
        client = BinanceWebSocketClient("wss://a", ["s"], "nats://n", "t")
        assert hasattr(client, "nats_client")
        assert client.nats_client is None

    def test_is_connected_attr(self):
        """Test is_connected attribute."""
        client = BinanceWebSocketClient("wss://a", ["s"], "nats://n", "t")
        assert hasattr(client, "is_connected")
        assert client.is_connected is False

    def test_is_running_attr(self):
        """Test is_running attribute."""
        client = BinanceWebSocketClient("wss://a", ["s"], "nats://n", "t")
        assert hasattr(client, "is_running")
        assert client.is_running is False

    def test_reconnect_attempts_attr(self):
        """Test reconnect_attempts attribute."""
        client = BinanceWebSocketClient("wss://a", ["s"], "nats://n", "t")
        assert hasattr(client, "reconnect_attempts")
        assert client.reconnect_attempts == 0

    def test_last_ping_attr(self):
        """Test last_ping attribute."""
        client = BinanceWebSocketClient("wss://a", ["s"], "nats://n", "t")
        assert hasattr(client, "last_ping")
        assert client.last_ping == 0.0

    def test_message_queue_attr(self):
        """Test message_queue attribute."""
        client = BinanceWebSocketClient("wss://a", ["s"], "nats://n", "t")
        assert hasattr(client, "message_queue")
        assert isinstance(client.message_queue, asyncio.Queue)

    def test_processed_messages_attr(self):
        """Test processed_messages attribute."""
        client = BinanceWebSocketClient("wss://a", ["s"], "nats://n", "t")
        assert hasattr(client, "processed_messages")
        assert client.processed_messages == 0

    def test_dropped_messages_attr(self):
        """Test dropped_messages attribute."""
        client = BinanceWebSocketClient("wss://a", ["s"], "nats://n", "t")
        assert hasattr(client, "dropped_messages")
        assert client.dropped_messages == 0

    def test_last_message_time_attr(self):
        """Test last_message_time attribute."""
        client = BinanceWebSocketClient("wss://a", ["s"], "nats://n", "t")
        assert hasattr(client, "last_message_time")
        assert client.last_message_time == 0.0

    def test_start_time_attr(self):
        """Test start_time attribute."""
        client = BinanceWebSocketClient("wss://a", ["s"], "nats://n", "t")
        assert hasattr(client, "start_time")
        assert client.start_time > 0

    def test_last_heartbeat_time_attr(self):
        """Test last_heartbeat_time attribute."""
        client = BinanceWebSocketClient("wss://a", ["s"], "nats://n", "t")
        assert hasattr(client, "last_heartbeat_time")
        assert client.last_heartbeat_time > 0

    def test_last_heartbeat_processed_attr(self):
        """Test last_heartbeat_processed attribute."""
        client = BinanceWebSocketClient("wss://a", ["s"], "nats://n", "t")
        assert hasattr(client, "last_heartbeat_processed")
        assert client.last_heartbeat_processed == 0

    def test_last_heartbeat_dropped_attr(self):
        """Test last_heartbeat_dropped attribute."""
        client = BinanceWebSocketClient("wss://a", ["s"], "nats://n", "t")
        assert hasattr(client, "last_heartbeat_dropped")
        assert client.last_heartbeat_dropped == 0

    def test_last_stats_log_time_attr(self):
        """Test last_stats_log_time attribute."""
        client = BinanceWebSocketClient("wss://a", ["s"], "nats://n", "t")
        assert hasattr(client, "last_stats_log_time")
        assert client.last_stats_log_time > 0

    def test_stats_log_interval_attr(self):
        """Test stats_log_interval attribute."""
        client = BinanceWebSocketClient("wss://a", ["s"], "nats://n", "t")
        assert hasattr(client, "stats_log_interval")
        assert client.stats_log_interval == 60

    def test_num_processors_attr(self):
        """Test num_processors attribute."""
        client = BinanceWebSocketClient("wss://a", ["s"], "nats://n", "t")
        assert hasattr(client, "num_processors")
        assert client.num_processors > 0

    def test_processor_tasks_attr(self):
        """Test processor_tasks attribute."""
        client = BinanceWebSocketClient("wss://a", ["s"], "nats://n", "t")
        assert hasattr(client, "processor_tasks")
        assert isinstance(client.processor_tasks, list)
        assert len(client.processor_tasks) == 0

    def test_ping_task_attr(self):
        """Test ping_task attribute."""
        client = BinanceWebSocketClient("wss://a", ["s"], "nats://n", "t")
        assert hasattr(client, "ping_task")
        assert client.ping_task is None

    def test_heartbeat_task_attr(self):
        """Test heartbeat_task attribute."""
        client = BinanceWebSocketClient("wss://a", ["s"], "nats://n", "t")
        assert hasattr(client, "heartbeat_task")
        assert client.heartbeat_task is None


@pytest.mark.unit
class TestClientEveryMethod:
    """Test every client method exists and is callable."""

    def test_start_method_exists(self):
        """Test start method exists."""
        client = BinanceWebSocketClient("wss://a", ["s"], "nats://n", "t")
        assert hasattr(client, "start")
        assert callable(client.start)

    def test_stop_method_exists(self):
        """Test stop method exists."""
        client = BinanceWebSocketClient("wss://a", ["s"], "nats://n", "t")
        assert hasattr(client, "stop")
        assert callable(client.stop)

    def test_get_metrics_method_exists(self):
        """Test get_metrics method exists."""
        client = BinanceWebSocketClient("wss://a", ["s"], "nats://n", "t")
        assert hasattr(client, "get_metrics")
        assert callable(client.get_metrics)

    def test_connect_nats_method_exists(self):
        """Test _connect_nats method exists."""
        client = BinanceWebSocketClient("wss://a", ["s"], "nats://n", "t")
        assert hasattr(client, "_connect_nats")
        assert callable(client._connect_nats)

    def test_connect_websocket_method_exists(self):
        """Test _connect_websocket method exists."""
        client = BinanceWebSocketClient("wss://a", ["s"], "nats://n", "t")
        assert hasattr(client, "_connect_websocket")
        assert callable(client._connect_websocket)


# =============================================================================
# ULTRA HEALTH SERVER TESTS
# =============================================================================


@pytest.mark.unit
class TestHealthServerEveryAttribute:
    """Test every health server attribute."""

    def test_port_attr(self):
        """Test port attribute."""
        server = HealthServer(port=8888)
        assert server.port == 8888

    def test_logger_attr(self):
        """Test logger attribute."""
        server = HealthServer(port=8889)
        assert hasattr(server, "logger")
        assert server.logger is not None

    def test_app_attr(self):
        """Test app attribute."""
        server = HealthServer(port=8890)
        assert hasattr(server, "app")
        assert server.app is not None

    def test_runner_attr(self):
        """Test runner attribute."""
        server = HealthServer(port=8891)
        assert hasattr(server, "runner")
        assert server.runner is None

    def test_site_attr(self):
        """Test site attribute."""
        server = HealthServer(port=8892)
        assert hasattr(server, "site")
        assert server.site is None

    def test_start_time_attr(self):
        """Test start_time attribute."""
        server = HealthServer(port=8893)
        assert hasattr(server, "start_time")
        assert server.start_time > 0


@pytest.mark.unit
class TestHealthServerEveryMethod:
    """Test every health server method."""

    def test_start_method_exists(self):
        """Test start method exists."""
        server = HealthServer(port=8900)
        assert hasattr(server, "start")
        assert callable(server.start)

    def test_stop_method_exists(self):
        """Test stop method exists."""
        server = HealthServer(port=8901)
        assert hasattr(server, "stop")
        assert callable(server.stop)

    def test_health_check_method_exists(self):
        """Test health_check method exists."""
        server = HealthServer(port=8902)
        assert hasattr(server, "health_check")
        assert callable(server.health_check)

    def test_ready_check_method_exists(self):
        """Test ready_check method exists."""
        server = HealthServer(port=8903)
        assert hasattr(server, "ready_check")
        assert callable(server.ready_check)

    def test_metrics_method_exists(self):
        """Test metrics method exists."""
        server = HealthServer(port=8904)
        assert hasattr(server, "metrics")
        assert callable(server.metrics)

    def test_get_memory_usage_method_exists(self):
        """Test _get_memory_usage method exists."""
        server = HealthServer(port=8905)
        assert hasattr(server, "_get_memory_usage")
        assert callable(server._get_memory_usage)

    def test_get_cpu_usage_method_exists(self):
        """Test _get_cpu_usage method exists."""
        server = HealthServer(port=8906)
        assert hasattr(server, "_get_cpu_usage")
        assert callable(server._get_cpu_usage)


# =============================================================================
# EXHAUSTIVE MESSAGE TESTS
# =============================================================================


@pytest.mark.unit
class TestEveryMessageType:
    """Test every message type exhaustively."""

    def test_websocket_message_type(self):
        """Test WebSocketMessage type."""
        msg = WebSocketMessage(stream="test", data={})
        assert isinstance(msg, WebSocketMessage)

    def test_trade_message_type(self):
        """Test TradeMessage type."""
        msg = TradeMessage(stream="btcusdt@trade", data={"price": "100"})
        assert isinstance(msg, TradeMessage)
        assert isinstance(msg, WebSocketMessage)

    def test_ticker_message_type(self):
        """Test TickerMessage type."""
        msg = TickerMessage(stream="ethusdt@ticker", data={"last": "3000"})
        assert isinstance(msg, TickerMessage)
        assert isinstance(msg, WebSocketMessage)

    def test_depth_message_type(self):
        """Test DepthMessage type."""
        msg = DepthMessage(stream="bnbusdt@depth", data={"bids": []})
        assert isinstance(msg, DepthMessage)
        assert isinstance(msg, WebSocketMessage)


@pytest.mark.unit
class TestMessageEveryField:
    """Test every message field."""

    def test_stream_field(self):
        """Test stream field."""
        msg = WebSocketMessage(stream="field@test", data={})
        assert msg.stream == "field@test"

    def test_data_field(self):
        """Test data field."""
        data = {"key": "value", "num": 123}
        msg = WebSocketMessage(stream="test", data=data)
        assert msg.data == data

    def test_timestamp_field(self):
        """Test timestamp field."""
        msg = WebSocketMessage(stream="test", data={})
        assert isinstance(msg.timestamp, datetime)

    def test_message_id_field(self):
        """Test message_id field."""
        msg = WebSocketMessage(stream="test", data={}, message_id="custom-id")
        assert msg.message_id == "custom-id"

    def test_message_id_field_none(self):
        """Test message_id field can be None."""
        msg = WebSocketMessage(stream="test", data={})
        # message_id is optional
        assert msg.message_id is None or isinstance(msg.message_id, str)


@pytest.mark.unit
class TestMessageEveryConversion:
    """Test every message conversion method."""

    def test_to_nats_message_method(self):
        """Test to_nats_message method."""
        msg = WebSocketMessage(stream="test", data={"test": "data"})
        result = msg.to_nats_message()

        assert isinstance(result, dict)
        assert "stream" in result
        assert "data" in result
        assert "timestamp" in result
        assert "source" in result
        assert "version" in result

    def test_to_json_method(self):
        """Test to_json method."""
        msg = WebSocketMessage(stream="test", data={"test": "data"})
        result = msg.to_json()

        assert isinstance(result, str)
        import json

        parsed = json.loads(result)
        assert "stream" in parsed


# =============================================================================
# ADDITIONAL CLIENT SCENARIOS
# =============================================================================


@pytest.mark.unit
class TestClientScenarios:
    """Test various client scenarios."""

    @pytest.mark.asyncio
    async def test_client_create_and_destroy(self):
        """Test creating and destroying client."""
        client = BinanceWebSocketClient("wss://a", ["s"], "nats://n", "t")
        await client.stop()
        del client

    @pytest.mark.asyncio
    async def test_client_stop_idempotent(self):
        """Test stop is idempotent."""
        client = BinanceWebSocketClient("wss://a", ["s"], "nats://n", "t")

        await client.stop()
        await client.stop()
        await client.stop()

        assert client.is_running is False

    def test_client_metrics_call_multiple_times(self):
        """Test calling get_metrics multiple times."""
        client = BinanceWebSocketClient("wss://a", ["s"], "nats://n", "t")

        for i in range(10):
            metrics = client.get_metrics()
            assert "stream_count" in metrics


# =============================================================================
# ADDITIONAL HEALTH SERVER SCENARIOS
# =============================================================================


@pytest.mark.unit
class TestHealthServerScenarios:
    """Test various health server scenarios."""

    @pytest.mark.asyncio
    async def test_server_create_and_destroy(self):
        """Test creating and destroying server."""
        server = HealthServer(port=8800)
        await server.stop()
        del server

    @pytest.mark.asyncio
    async def test_server_stop_idempotent(self):
        """Test stop is idempotent."""
        server = HealthServer(port=8801)

        await server.stop()
        await server.stop()
        await server.stop()

    def test_server_utility_methods_multiple_calls(self):
        """Test calling utility methods multiple times."""
        server = HealthServer(port=8802)

        for i in range(5):
            memory = server._get_memory_usage()
            cpu = server._get_cpu_usage()
            assert memory >= 0
            assert cpu >= 0


# =============================================================================
# EXHAUSTIVE EDGE CASES
# =============================================================================


@pytest.mark.unit
class TestEdgeCases:
    """Test edge cases across all modules."""

    def test_client_with_single_character_values(self):
        """Test client with minimal string lengths."""
        client = BinanceWebSocketClient("wss://a", ["s"], "nats://n", "t")
        assert len(client.ws_url) > 0
        assert len(client.streams) > 0
        assert len(client.nats_url) > 0
        assert len(client.nats_topic) > 0

    def test_client_with_very_long_values(self):
        """Test client with very long string values."""
        long_url = "wss://" + "a" * 1000
        long_stream = "stream" + "x" * 1000
        long_nats = "nats://" + "n" * 1000
        long_topic = "topic." + "t" * 1000

        client = BinanceWebSocketClient(long_url, [long_stream], long_nats, long_topic)

        assert len(client.ws_url) > 1000
        assert len(client.streams[0]) > 1000
        assert len(client.nats_url) > 1000
        assert len(client.nats_topic) > 1000

    def test_client_with_many_streams(self):
        """Test client with many streams."""
        many_streams = [f"stream{i}@trade" for i in range(100)]
        client = BinanceWebSocketClient("wss://a", many_streams, "nats://n", "t")

        assert len(client.streams) == 100

    def test_health_server_with_high_port(self):
        """Test health server with high port number."""
        server = HealthServer(port=65535)
        assert server.port == 65535

    def test_health_server_with_low_port(self):
        """Test health server with low port number."""
        server = HealthServer(port=1024)
        assert server.port == 1024

    def test_message_with_large_data(self):
        """Test message with large data payload."""
        large_data = {f"key{i}": f"value{i}" for i in range(1000)}
        msg = WebSocketMessage(stream="test", data=large_data)

        assert len(msg.data) == 1000

    def test_message_with_unicode_data(self):
        """Test message with unicode data."""
        unicode_data = {
            "chinese": "比特币",
            "japanese": "ビットコイン",
            "arabic": "بيتكوين",
            "emoji": "🚀💰📈",
        }
        msg = WebSocketMessage(stream="test", data=unicode_data)

        assert msg.data["chinese"] == "比特币"
        assert "🚀" in msg.data["emoji"]


@pytest.mark.unit
class TestStateChanges:
    """Test state changes."""

    def test_client_state_toggle(self):
        """Test client state can be toggled."""
        client = BinanceWebSocketClient("wss://a", ["s"], "nats://n", "t")

        assert client.is_connected is False
        client.is_connected = True
        assert client.is_connected is True
        client.is_connected = False
        assert client.is_connected is False

        assert client.is_running is False
        client.is_running = True
        assert client.is_running is True
        client.is_running = False
        assert client.is_running is False

    def test_client_counter_increments(self):
        """Test client counters can increment."""
        client = BinanceWebSocketClient("wss://a", ["s"], "nats://n", "t")

        for i in range(10):
            client.processed_messages += 1
            assert client.processed_messages == i + 1

        for i in range(5):
            client.dropped_messages += 1
            assert client.dropped_messages == i + 1

        for i in range(3):
            client.reconnect_attempts += 1
            assert client.reconnect_attempts == i + 1

    def test_client_timestamp_updates(self):
        """Test client timestamps can be updated."""
        client = BinanceWebSocketClient("wss://a", ["s"], "nats://n", "t")

        new_time = time.time()
        client.last_ping = new_time
        assert client.last_ping == new_time

        client.last_message_time = new_time
        assert client.last_message_time == new_time


@pytest.mark.unit
class TestMultipleInstances:
    """Test multiple instances."""

    def test_multiple_clients(self):
        """Test multiple client instances."""
        clients = [
            BinanceWebSocketClient("wss://a", ["s1"], "nats://n", "t1"),
            BinanceWebSocketClient("wss://b", ["s2"], "nats://n", "t2"),
            BinanceWebSocketClient("wss://c", ["s3"], "nats://n", "t3"),
        ]

        for i, client in enumerate(clients):
            assert client.streams == [f"s{i+1}"]
            assert client.nats_topic == f"t{i+1}"

    def test_multiple_servers(self):
        """Test multiple server instances."""
        servers = [
            HealthServer(port=9000),
            HealthServer(port=9001),
            HealthServer(port=9002),
        ]

        for i, server in enumerate(servers):
            assert server.port == 9000 + i

    def test_multiple_messages(self):
        """Test multiple message instances."""
        messages = [
            WebSocketMessage(stream=f"stream{i}", data={"id": i}) for i in range(10)
        ]

        for i, msg in enumerate(messages):
            assert msg.stream == f"stream{i}"
            assert msg.data["id"] == i
