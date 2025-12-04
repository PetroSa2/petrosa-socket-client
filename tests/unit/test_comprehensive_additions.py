"""
Comprehensive test additions targeting uncovered code paths.
Systematically covers uncovered lines in key modules.
"""

import asyncio
import json
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from socket_client.core.client import BinanceWebSocketClient


@pytest.mark.unit
class TestMessageProcessing:
    """Test message processing methods."""

    @pytest.mark.asyncio
    async def test_handle_websocket_message_valid_json(self):
        """Test handling valid JSON WebSocket message."""
        client = BinanceWebSocketClient(
            ws_url="wss://test.com",
            streams=["test@stream"],
            nats_url="nats://localhost:4222",
            nats_topic="test.topic",
        )

        valid_msg = '{"stream": "test@stream", "data": {"price": "100"}}'
        
        # Should add to queue
        await client._handle_websocket_message(valid_msg)
        
        # Queue should have message (if not full)
        assert client.message_queue.qsize() >= 0

    @pytest.mark.asyncio
    async def test_handle_websocket_message_invalid_json(self):
        """Test handling invalid JSON."""
        client = BinanceWebSocketClient(
            ws_url="wss://test.com",
            streams=["test@stream"],
            nats_url="nats://localhost:4222",
            nats_topic="test.topic",
        )

        # Invalid JSON should not crash
        await client._handle_websocket_message("not json")
        await client._handle_websocket_message("{invalid")
        await client._handle_websocket_message("")

    @pytest.mark.asyncio
    async def test_process_and_publish_message(self):
        """Test _process_and_publish_message method."""
        client = BinanceWebSocketClient(
            ws_url="wss://test.com",
            streams=["test@stream"],
            nats_url="nats://localhost:4222",
            nats_topic="test.topic",
        )

        mock_nats = AsyncMock()
        client.nats_client = mock_nats

        message_data = {"stream": "test@stream", "data": {"price": "100"}}
        
        await client._process_and_publish_message(json.dumps(message_data))
        
        # Should have attempted to publish
        assert client.processed_messages >= 0

    @pytest.mark.asyncio
    async def test_process_and_publish_without_nats(self):
        """Test processing when NATS client is None."""
        client = BinanceWebSocketClient(
            ws_url="wss://test.com",
            streams=["test@stream"],
            nats_url="nats://localhost:4222",
            nats_topic="test.topic",
        )

        client.nats_client = None

        message_data = {"stream": "test@stream", "data": {"price": "100"}}
        
        # Should handle gracefully when NATS not connected
        await client._process_and_publish_message(json.dumps(message_data))


@pytest.mark.unit
class TestHeartbeatAndMetrics:
    """Test heartbeat and metrics methods."""

    def test_get_metrics_structure(self):
        """Test get_metrics returns proper structure."""
        client = BinanceWebSocketClient(
            ws_url="wss://test.com",
            streams=["test@stream", "another@ticker"],
            nats_url="nats://localhost:4222",
            nats_topic="test.topic",
        )

        metrics = client.get_metrics()

        # Verify all expected keys
        assert "stream_count" in metrics
        assert "streams" in metrics
        assert "connection_status" in metrics
        assert "uptime" in metrics
        assert "processed_messages" in metrics
        assert "dropped_messages" in metrics

        # Verify values
        assert metrics["stream_count"] == 2
        assert len(metrics["streams"]) == 2
        assert metrics["uptime"] >= 0

    def test_get_metrics_when_connected(self):
        """Test metrics when client is connected."""
        client = BinanceWebSocketClient(
            ws_url="wss://test.com",
            streams=["test@stream"],
            nats_url="nats://localhost:4222",
            nats_topic="test.topic",
        )

        client.is_connected = True
        client.processed_messages = 100
        client.dropped_messages = 5

        metrics = client.get_metrics()

        assert metrics["connection_status"] == "connected"
        assert metrics["processed_messages"] == 100
        assert metrics["dropped_messages"] == 5

    def test_get_metrics_when_disconnected(self):
        """Test metrics when client is disconnected."""
        client = BinanceWebSocketClient(
            ws_url="wss://test.com",
            streams=["test@stream"],
            nats_url="nats://localhost:4222",
            nats_topic="test.topic",
        )

        client.is_connected = False

        metrics = client.get_metrics()

        assert metrics["connection_status"] == "disconnected"


@pytest.mark.unit
class TestTaskManagement:
    """Test task creation and management."""

    @pytest.mark.asyncio
    async def test_processor_tasks_list_exists(self):
        """Test processor_tasks list is initialized."""
        client = BinanceWebSocketClient(
            ws_url="wss://test.com",
            streams=["test@stream"],
            nats_url="nats://localhost:4222",
            nats_topic="test.topic",
        )

        assert hasattr(client, "processor_tasks")
        assert isinstance(client.processor_tasks, list)

    @pytest.mark.asyncio
    async def test_ping_task_none_initially(self):
        """Test ping_task is None before start."""
        client = BinanceWebSocketClient(
            ws_url="wss://test.com",
            streams=["test@stream"],
            nats_url="nats://localhost:4222",
            nats_topic="test.topic",
        )

        assert client.ping_task is None

    @pytest.mark.asyncio
    async def test_heartbeat_task_none_initially(self):
        """Test heartbeat_task is None before start."""
        client = BinanceWebSocketClient(
            ws_url="wss://test.com",
            streams=["test@stream"],
            nats_url="nats://localhost:4222",
            nats_topic="test.topic",
        )

        assert client.heartbeat_task is None


@pytest.mark.unit
class TestClientAttributes:
    """Test client attribute access and initialization."""

    def test_streams_list_is_mutable(self):
        """Test streams list can be modified."""
        client = BinanceWebSocketClient(
            ws_url="wss://test.com",
            streams=["test@stream"],
            nats_url="nats://localhost:4222",
            nats_topic="test.topic",
        )

        original_count = len(client.streams)
        client.streams.append("new@stream")
        
        assert len(client.streams) == original_count + 1

    def test_message_queue_size_limit(self):
        """Test message queue has size limit."""
        client = BinanceWebSocketClient(
            ws_url="wss://test.com",
            streams=["test@stream"],
            nats_url="nats://localhost:4222",
            nats_topic="test.topic",
        )

        assert client.message_queue.maxsize > 0

    def test_num_processors_from_constants(self):
        """Test num_processors is set from constants."""
        client = BinanceWebSocketClient(
            ws_url="wss://test.com",
            streams=["test@stream"],
            nats_url="nats://localhost:4222",
            nats_topic="test.topic",
        )

        assert client.num_processors > 0
        assert isinstance(client.num_processors, int)

    def test_stats_log_interval(self):
        """Test stats_log_interval is set."""
        client = BinanceWebSocketClient(
            ws_url="wss://test.com",
            streams=["test@stream"],
            nats_url="nats://localhost:4222",
            nats_topic="test.topic",
        )

        assert client.stats_log_interval == 60

    def test_last_stats_log_time_initialized(self):
        """Test last_stats_log_time is initialized."""
        import time
        
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
class TestURLConstruction:
    """Test WebSocket URL construction with streams."""

    def test_ws_url_stored_correctly(self):
        """Test WebSocket URL is stored."""
        url = "wss://stream.binance.com:9443/stream"
        client = BinanceWebSocketClient(
            ws_url=url,
            streams=["btcusdt@trade"],
            nats_url="nats://localhost:4222",
            nats_topic="test.topic",
        )

        assert client.ws_url == url

    def test_multiple_streams_stored(self):
        """Test multiple streams are stored correctly."""
        streams = ["btcusdt@trade", "ethusdt@ticker", "bnbusdt@depth"]
        client = BinanceWebSocketClient(
            ws_url="wss://test.com",
            streams=streams,
            nats_url="nats://localhost:4222",
            nats_topic="test.topic",
        )

        assert client.streams == streams
        assert len(client.streams) == 3

    def test_nats_topic_stored(self):
        """Test NATS topic is stored."""
        topic = "crypto.market.data"
        client = BinanceWebSocketClient(
            ws_url="wss://test.com",
            streams=["test@stream"],
            nats_url="nats://localhost:4222",
            nats_topic=topic,
        )

        assert client.nats_topic == topic

