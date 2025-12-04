"""
Simple unit tests targeting specific uncovered methods in client.py.
Focus on easy-to-test methods without complex async mocking.
"""

import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from socket_client.core.client import BinanceWebSocketClient


@pytest.mark.unit
class TestGetMetrics:
    """Test get_metrics method comprehensively."""

    def test_get_metrics_returns_dict(self):
        """Test get_metrics returns a dictionary."""
        client = BinanceWebSocketClient(
            ws_url="wss://test.com",
            streams=["btcusdt@trade"],
            nats_url="nats://localhost:4222",
            nats_topic="test.topic",
        )

        metrics = client.get_metrics()
        assert isinstance(metrics, dict)

    def test_get_metrics_includes_all_fields(self):
        """Test get_metrics includes all expected fields."""
        client = BinanceWebSocketClient(
            ws_url="wss://test.com",
            streams=["btcusdt@trade", "ethusdt@ticker"],
            nats_url="nats://localhost:4222",
            nats_topic="test.topic",
        )

        metrics = client.get_metrics()

        required_fields = [
            "stream_count",
            "streams",
            "connection_status",
            "uptime",
            "processed_messages",
            "dropped_messages",
            "reconnect_attempts",
        ]

        for field in required_fields:
            assert field in metrics, f"Missing field: {field}"

    def test_get_metrics_stream_count(self):
        """Test get_metrics returns correct stream count."""
        streams = ["btcusdt@trade", "ethusdt@ticker", "bnbusdt@depth"]
        client = BinanceWebSocketClient(
            ws_url="wss://test.com",
            streams=streams,
            nats_url="nats://localhost:4222",
            nats_topic="test.topic",
        )

        metrics = client.get_metrics()

        assert metrics["stream_count"] == 3
        assert len(metrics["streams"]) == 3

    def test_get_metrics_uptime_calculation(self):
        """Test get_metrics calculates uptime correctly."""
        client = BinanceWebSocketClient(
            ws_url="wss://test.com",
            streams=["test@stream"],
            nats_url="nats://localhost:4222",
            nats_topic="test.topic",
        )

        # Wait a bit
        time.sleep(0.1)

        metrics = client.get_metrics()

        assert metrics["uptime"] > 0
        assert metrics["uptime"] < 10  # Should be less than 10 seconds

    def test_get_metrics_connection_status_disconnected(self):
        """Test get_metrics shows disconnected status."""
        client = BinanceWebSocketClient(
            ws_url="wss://test.com",
            streams=["test@stream"],
            nats_url="nats://localhost:4222",
            nats_topic="test.topic",
        )

        client.is_connected = False

        metrics = client.get_metrics()

        assert metrics["connection_status"] == "disconnected"

    def test_get_metrics_connection_status_connected(self):
        """Test get_metrics shows connected status."""
        client = BinanceWebSocketClient(
            ws_url="wss://test.com",
            streams=["test@stream"],
            nats_url="nats://localhost:4222",
            nats_topic="test.topic",
        )

        client.is_connected = True

        metrics = client.get_metrics()

        assert metrics["connection_status"] == "connected"

    def test_get_metrics_message_counts(self):
        """Test get_metrics includes message counts."""
        client = BinanceWebSocketClient(
            ws_url="wss://test.com",
            streams=["test@stream"],
            nats_url="nats://localhost:4222",
            nats_topic="test.topic",
        )

        client.processed_messages = 150
        client.dropped_messages = 3

        metrics = client.get_metrics()

        assert metrics["processed_messages"] == 150
        assert metrics["dropped_messages"] == 3

    def test_get_metrics_reconnect_attempts(self):
        """Test get_metrics includes reconnect attempts."""
        client = BinanceWebSocketClient(
            ws_url="wss://test.com",
            streams=["test@stream"],
            nats_url="nats://localhost:4222",
            nats_topic="test.topic",
        )

        client.reconnect_attempts = 5

        metrics = client.get_metrics()

        assert metrics["reconnect_attempts"] == 5


@pytest.mark.unit
class TestClientProperties:
    """Test client property access."""

    def test_ws_url_property(self):
        """Test ws_url is accessible."""
        url = "wss://stream.binance.com:9443/stream"
        client = BinanceWebSocketClient(
            ws_url=url,
            streams=["test@stream"],
            nats_url="nats://localhost:4222",
            nats_topic="test.topic",
        )

        assert client.ws_url == url

    def test_streams_property(self):
        """Test streams property is accessible."""
        streams = ["btcusdt@trade", "ethusdt@ticker"]
        client = BinanceWebSocketClient(
            ws_url="wss://test.com",
            streams=streams,
            nats_url="nats://localhost:4222",
            nats_topic="test.topic",
        )

        assert client.streams == streams

    def test_nats_url_property(self):
        """Test nats_url property."""
        url = "nats://production:4222"
        client = BinanceWebSocketClient(
            ws_url="wss://test.com",
            streams=["test@stream"],
            nats_url=url,
            nats_topic="test.topic",
        )

        assert client.nats_url == url

    def test_nats_topic_property(self):
        """Test nats_topic property."""
        topic = "crypto.market.data.v2"
        client = BinanceWebSocketClient(
            ws_url="wss://test.com",
            streams=["test@stream"],
            nats_url="nats://localhost:4222",
            nats_topic=topic,
        )

        assert client.nats_topic == topic

    def test_logger_property(self):
        """Test logger property."""
        custom_logger = MagicMock()
        client = BinanceWebSocketClient(
            ws_url="wss://test.com",
            streams=["test@stream"],
            nats_url="nats://localhost:4222",
            nats_topic="test.topic",
            logger=custom_logger,
        )

        assert client.logger is custom_logger

    def test_max_reconnect_attempts_property(self):
        """Test max_reconnect_attempts property."""
        client = BinanceWebSocketClient(
            ws_url="wss://test.com",
            streams=["test@stream"],
            nats_url="nats://localhost:4222",
            nats_topic="test.topic",
            max_reconnect_attempts=20,
        )

        assert client.max_reconnect_attempts == 20

    def test_reconnect_delay_property(self):
        """Test reconnect_delay property."""
        client = BinanceWebSocketClient(
            ws_url="wss://test.com",
            streams=["test@stream"],
            nats_url="nats://localhost:4222",
            nats_topic="test.topic",
            reconnect_delay=15,
        )

        assert client.reconnect_delay == 15

    def test_ping_interval_property(self):
        """Test ping_interval property."""
        client = BinanceWebSocketClient(
            ws_url="wss://test.com",
            streams=["test@stream"],
            nats_url="nats://localhost:4222",
            nats_topic="test.topic",
            ping_interval=30,
        )

        assert client.ping_interval == 30

    def test_ping_timeout_property(self):
        """Test ping_timeout property."""
        client = BinanceWebSocketClient(
            ws_url="wss://test.com",
            streams=["test@stream"],
            nats_url="nats://localhost:4222",
            nats_topic="test.topic",
            ping_timeout=20,
        )

        assert client.ping_timeout == 20


@pytest.mark.unit
class TestClientStateAttributes:
    """Test client state attribute access."""

    def test_websocket_none_initially(self):
        """Test websocket is None on init."""
        client = BinanceWebSocketClient(
            ws_url="wss://test.com",
            streams=["test@stream"],
            nats_url="nats://localhost:4222",
            nats_topic="test.topic",
        )

        assert client.websocket is None

    def test_nats_client_none_initially(self):
        """Test nats_client is None on init."""
        client = BinanceWebSocketClient(
            ws_url="wss://test.com",
            streams=["test@stream"],
            nats_url="nats://localhost:4222",
            nats_topic="test.topic",
        )

        assert client.nats_client is None

    def test_is_connected_false_initially(self):
        """Test is_connected is False on init."""
        client = BinanceWebSocketClient(
            ws_url="wss://test.com",
            streams=["test@stream"],
            nats_url="nats://localhost:4222",
            nats_topic="test.topic",
        )

        assert client.is_connected is False

    def test_is_running_false_initially(self):
        """Test is_running is False on init."""
        client = BinanceWebSocketClient(
            ws_url="wss://test.com",
            streams=["test@stream"],
            nats_url="nats://localhost:4222",
            nats_topic="test.topic",
        )

        assert client.is_running is False

    def test_reconnect_attempts_zero_initially(self):
        """Test reconnect_attempts is 0 on init."""
        client = BinanceWebSocketClient(
            ws_url="wss://test.com",
            streams=["test@stream"],
            nats_url="nats://localhost:4222",
            nats_topic="test.topic",
        )

        assert client.reconnect_attempts == 0

    def test_processed_messages_zero_initially(self):
        """Test processed_messages is 0 on init."""
        client = BinanceWebSocketClient(
            ws_url="wss://test.com",
            streams=["test@stream"],
            nats_url="nats://localhost:4222",
            nats_topic="test.topic",
        )

        assert client.processed_messages == 0

    def test_dropped_messages_zero_initially(self):
        """Test dropped_messages is 0 on init."""
        client = BinanceWebSocketClient(
            ws_url="wss://test.com",
            streams=["test@stream"],
            nats_url="nats://localhost:4222",
            nats_topic="test.topic",
        )

        assert client.dropped_messages == 0

    def test_last_ping_zero_initially(self):
        """Test last_ping is 0.0 on init."""
        client = BinanceWebSocketClient(
            ws_url="wss://test.com",
            streams=["test@stream"],
            nats_url="nats://localhost:4222",
            nats_topic="test.topic",
        )

        assert client.last_ping == 0.0

    def test_last_message_time_zero_initially(self):
        """Test last_message_time is 0.0 on init."""
        client = BinanceWebSocketClient(
            ws_url="wss://test.com",
            streams=["test@stream"],
            nats_url="nats://localhost:4222",
            nats_topic="test.topic",
        )

        assert client.last_message_time == 0.0


@pytest.mark.unit
class TestClientTaskLists:
    """Test client task list attributes."""

    def test_processor_tasks_list_empty_initially(self):
        """Test processor_tasks is empty list on init."""
        client = BinanceWebSocketClient(
            ws_url="wss://test.com",
            streams=["test@stream"],
            nats_url="nats://localhost:4222",
            nats_topic="test.topic",
        )

        assert isinstance(client.processor_tasks, list)
        assert len(client.processor_tasks) == 0

    def test_ping_task_none_initially(self):
        """Test ping_task is None on init."""
        client = BinanceWebSocketClient(
            ws_url="wss://test.com",
            streams=["test@stream"],
            nats_url="nats://localhost:4222",
            nats_topic="test.topic",
        )

        assert client.ping_task is None

    def test_heartbeat_task_none_initially(self):
        """Test heartbeat_task is None on init."""
        client = BinanceWebSocketClient(
            ws_url="wss://test.com",
            streams=["test@stream"],
            nats_url="nats://localhost:4222",
            nats_topic="test.topic",
        )

        assert client.heartbeat_task is None


@pytest.mark.unit
class TestClientMessageQueue:
    """Test message queue functionality."""

    @pytest.mark.asyncio
    async def test_message_queue_created(self):
        """Test message queue is created."""
        client = BinanceWebSocketClient(
            ws_url="wss://test.com",
            streams=["test@stream"],
            nats_url="nats://localhost:4222",
            nats_topic="test.topic",
        )

        assert isinstance(client.message_queue, asyncio.Queue)

    @pytest.mark.asyncio
    async def test_message_queue_empty_initially(self):
        """Test message queue is empty on init."""
        client = BinanceWebSocketClient(
            ws_url="wss://test.com",
            streams=["test@stream"],
            nats_url="nats://localhost:4222",
            nats_topic="test.topic",
        )

        assert client.message_queue.empty()

    @pytest.mark.asyncio
    async def test_message_queue_has_maxsize(self):
        """Test message queue has maxsize set."""
        client = BinanceWebSocketClient(
            ws_url="wss://test.com",
            streams=["test@stream"],
            nats_url="nats://localhost:4222",
            nats_topic="test.topic",
        )

        assert client.message_queue.maxsize > 0

    @pytest.mark.asyncio
    async def test_message_queue_put_get(self):
        """Test message queue put and get."""
        client = BinanceWebSocketClient(
            ws_url="wss://test.com",
            streams=["test@stream"],
            nats_url="nats://localhost:4222",
            nats_topic="test.topic",
        )

        test_msg = {"test": "message"}
        await client.message_queue.put(test_msg)

        assert not client.message_queue.empty()

        msg = await client.message_queue.get()
        assert msg == test_msg
        assert client.message_queue.empty()


@pytest.mark.unit
class TestClientTimestamps:
    """Test timestamp attributes."""

    def test_start_time_set_on_init(self):
        """Test start_time is set on initialization."""
        before = time.time()

        client = BinanceWebSocketClient(
            ws_url="wss://test.com",
            streams=["test@stream"],
            nats_url="nats://localhost:4222",
            nats_topic="test.topic",
        )

        after = time.time()

        assert before <= client.start_time <= after

    def test_last_heartbeat_time_set_on_init(self):
        """Test last_heartbeat_time is set on initialization."""
        before = time.time()

        client = BinanceWebSocketClient(
            ws_url="wss://test.com",
            streams=["test@stream"],
            nats_url="nats://localhost:4222",
            nats_topic="test.topic",
        )

        after = time.time()

        assert before <= client.last_heartbeat_time <= after

    def test_last_stats_log_time_set_on_init(self):
        """Test last_stats_log_time is set on initialization."""
        before = time.time()

        client = BinanceWebSocketClient(
            ws_url="wss://test.com",
            streams=["test@stream"],
            nats_url="nats://localhost:4222",
            nats_topic="test.topic",
        )

        after = time.time()

        assert before <= client.last_stats_log_time <= after


@pytest.mark.unit
class TestClientHeartbeatStats:
    """Test heartbeat statistics attributes."""

    def test_last_heartbeat_processed_zero(self):
        """Test last_heartbeat_processed is 0 initially."""
        client = BinanceWebSocketClient(
            ws_url="wss://test.com",
            streams=["test@stream"],
            nats_url="nats://localhost:4222",
            nats_topic="test.topic",
        )

        assert client.last_heartbeat_processed == 0

    def test_last_heartbeat_dropped_zero(self):
        """Test last_heartbeat_dropped is 0 initially."""
        client = BinanceWebSocketClient(
            ws_url="wss://test.com",
            streams=["test@stream"],
            nats_url="nats://localhost:4222",
            nats_topic="test.topic",
        )

        assert client.last_heartbeat_dropped == 0

    def test_stats_log_interval_set(self):
        """Test stats_log_interval is set correctly."""
        client = BinanceWebSocketClient(
            ws_url="wss://test.com",
            streams=["test@stream"],
            nats_url="nats://localhost:4222",
            nats_topic="test.topic",
        )

        assert client.stats_log_interval == 60


@pytest.mark.unit
class TestClientProcessorConfig:
    """Test processor configuration."""

    def test_num_processors_set(self):
        """Test num_processors is set from constants."""
        client = BinanceWebSocketClient(
            ws_url="wss://test.com",
            streams=["test@stream"],
            nats_url="nats://localhost:4222",
            nats_topic="test.topic",
        )

        assert isinstance(client.num_processors, int)
        assert client.num_processors > 0


@pytest.mark.unit
class TestClientStopMethod:
    """Test stop method variations."""

    @pytest.mark.asyncio
    async def test_stop_sets_is_running_false(self):
        """Test stop sets is_running to False."""
        client = BinanceWebSocketClient(
            ws_url="wss://test.com",
            streams=["test@stream"],
            nats_url="nats://localhost:4222",
            nats_topic="test.topic",
        )

        client.is_running = True

        await client.stop()

        assert client.is_running is False

    @pytest.mark.asyncio
    async def test_stop_when_already_stopped(self):
        """Test stop when client is already stopped."""
        client = BinanceWebSocketClient(
            ws_url="wss://test.com",
            streams=["test@stream"],
            nats_url="nats://localhost:4222",
            nats_topic="test.topic",
        )

        client.is_running = False

        # Should not raise exception
        await client.stop()

        assert client.is_running is False

    @pytest.mark.asyncio
    async def test_stop_with_mock_websocket(self):
        """Test stop closes websocket."""
        client = BinanceWebSocketClient(
            ws_url="wss://test.com",
            streams=["test@stream"],
            nats_url="nats://localhost:4222",
            nats_topic="test.topic",
        )

        mock_ws = AsyncMock()
        client.websocket = mock_ws

        await client.stop()

        mock_ws.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_stop_with_mock_nats(self):
        """Test stop closes NATS connection."""
        client = BinanceWebSocketClient(
            ws_url="wss://test.com",
            streams=["test@stream"],
            nats_url="nats://localhost:4222",
            nats_topic="test.topic",
        )

        mock_nats = AsyncMock()
        client.nats_client = mock_nats

        await client.stop()

        mock_nats.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_stop_with_mock_tasks(self):
        """Test stop cancels tasks."""
        client = BinanceWebSocketClient(
            ws_url="wss://test.com",
            streams=["test@stream"],
            nats_url="nats://localhost:4222",
            nats_topic="test.topic",
        )

        # Add mock tasks
        mock_ping = AsyncMock()
        mock_heartbeat = AsyncMock()
        mock_processor = AsyncMock()

        client.ping_task = mock_ping
        client.heartbeat_task = mock_heartbeat
        client.processor_tasks = [mock_processor]

        await client.stop()

        mock_ping.cancel.assert_called_once()
        mock_heartbeat.cancel.assert_called_once()
        mock_processor.cancel.assert_called_once()
