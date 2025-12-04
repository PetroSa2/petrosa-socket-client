"""
Batch 2: More comprehensive tests to push toward 90% coverage.
Targets client.py, health_server, and other gaps.
"""

import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from socket_client.core.client import BinanceWebSocketClient
from socket_client.health.server import HealthServer


@pytest.mark.unit
class TestClientStopScenarios:
    """Test client stop scenarios comprehensively."""

    @pytest.mark.asyncio
    async def test_stop_with_no_connections(self):
        """Test stop when nothing is connected."""
        client = BinanceWebSocketClient(
            ws_url="wss://test.com",
            streams=["test@stream"],
            nats_url="nats://localhost:4222",
            nats_topic="test.topic",
        )

        # Nothing started, should handle gracefully
        await client.stop()
        
        assert client.is_running is False

    @pytest.mark.asyncio
    async def test_stop_with_websocket_only(self):
        """Test stop with only websocket connected."""
        client = BinanceWebSocketClient(
            ws_url="wss://test.com",
            streams=["test@stream"],
            nats_url="nats://localhost:4222",
            nats_topic="test.topic",
        )

        client.websocket = AsyncMock()
        
        await client.stop()
        
        client.websocket.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_stop_with_nats_only(self):
        """Test stop with only NATS connected."""
        client = BinanceWebSocketClient(
            ws_url="wss://test.com",
            streams=["test@stream"],
            nats_url="nats://localhost:4222",
            nats_topic="test.topic",
        )

        client.nats_client = AsyncMock()
        
        await client.stop()
        
        client.nats_client.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_stop_with_all_tasks(self):
        """Test stop with all tasks running."""
        client = BinanceWebSocketClient(
            ws_url="wss://test.com",
            streams=["test@stream"],
            nats_url="nats://localhost:4222",
            nats_topic="test.topic",
        )

        # Create all tasks
        client.ping_task = AsyncMock()
        client.heartbeat_task = AsyncMock()
        client.processor_tasks = [AsyncMock(), AsyncMock()]
        client.websocket = AsyncMock()
        client.nats_client = AsyncMock()

        await client.stop()

        # Verify all cancelled/closed
        client.ping_task.cancel.assert_called_once()
        client.heartbeat_task.cancel.assert_called_once()
        for task in client.processor_tasks:
            task.cancel.assert_called_once()


@pytest.mark.unit
class TestClientGetMetricsComprehensive:
    """Comprehensive get_metrics tests."""

    def test_metrics_all_fields_present(self):
        """Test all metric fields are present."""
        client = BinanceWebSocketClient(
            ws_url="wss://test.com",
            streams=["btc@trade", "eth@trade"],
            nats_url="nats://localhost:4222",
            nats_topic="test.topic",
        )

        metrics = client.get_metrics()

        # All required fields
        assert "stream_count" in metrics
        assert "streams" in metrics
        assert "connection_status" in metrics
        assert "uptime" in metrics
        assert "processed_messages" in metrics
        assert "dropped_messages" in metrics
        assert "reconnect_attempts" in metrics

    def test_metrics_values_accurate(self):
        """Test metric values are accurate."""
        client = BinanceWebSocketClient(
            ws_url="wss://test.com",
            streams=["a@trade", "b@trade", "c@trade"],
            nats_url="nats://localhost:4222",
            nats_topic="test.topic",
        )

        client.processed_messages = 999
        client.dropped_messages = 11
        client.reconnect_attempts = 3
        client.is_connected = True

        metrics = client.get_metrics()

        assert metrics["stream_count"] == 3
        assert len(metrics["streams"]) == 3
        assert metrics["processed_messages"] == 999
        assert metrics["dropped_messages"] == 11
        assert metrics["reconnect_attempts"] == 3
        assert metrics["connection_status"] == "connected"

    def test_metrics_uptime_increases(self):
        """Test uptime metric increases over time."""
        client = BinanceWebSocketClient(
            ws_url="wss://test.com",
            streams=["test@stream"],
            nats_url="nats://localhost:4222",
            nats_topic="test.topic",
        )

        metrics1 = client.get_metrics()
        uptime1 = metrics1["uptime"]

        time.sleep(0.1)

        metrics2 = client.get_metrics()
        uptime2 = metrics2["uptime"]

        assert uptime2 > uptime1


@pytest.mark.unit
class TestHealthServerResponseStructures:
    """Test health server response structures."""

    @pytest.mark.asyncio
    async def test_health_check_response_structure(self):
        """Test health check returns proper structure."""
        server = HealthServer(port=9100)
        
        # Create mock request
        mock_request = Mock(spec=web.Request)
        
        response = await server.health_check(mock_request)
        
        assert isinstance(response, web.Response)

    @pytest.mark.asyncio
    async def test_ready_check_response_structure(self):
        """Test ready check returns proper structure."""
        server = HealthServer(port=9101)
        
        mock_request = Mock(spec=web.Request)
        
        response = await server.ready_check(mock_request)
        
        assert isinstance(response, web.Response)

    @pytest.mark.asyncio
    async def test_metrics_response_structure(self):
        """Test metrics returns proper structure."""
        server = HealthServer(port=9102)
        
        mock_request = Mock(spec=web.Request)
        
        response = await server.metrics(mock_request)
        
        assert isinstance(response, web.Response)


@pytest.mark.unit
class TestClientQueueOperations:
    """Test client message queue operations."""

    @pytest.mark.asyncio
    async def test_queue_put_multiple_messages(self):
        """Test putting multiple messages in queue."""
        client = BinanceWebSocketClient(
            ws_url="wss://test.com",
            streams=["test@stream"],
            nats_url="nats://localhost:4222",
            nats_topic="test.topic",
        )

        messages = [{"msg": i} for i in range(10)]
        
        for msg in messages:
            await client.message_queue.put(msg)

        assert client.message_queue.qsize() == 10

    @pytest.mark.asyncio
    async def test_queue_get_fifo_order(self):
        """Test queue maintains FIFO order."""
        client = BinanceWebSocketClient(
            ws_url="wss://test.com",
            streams=["test@stream"],
            nats_url="nats://localhost:4222",
            nats_topic="test.topic",
        )

        # Put messages in order
        for i in range(5):
            await client.message_queue.put({"order": i})

        # Get messages - should be FIFO
        for i in range(5):
            msg = await client.message_queue.get()
            assert msg["order"] == i


@pytest.mark.unit
class TestClientConfigurationVariations:
    """Test various client configuration combinations."""

    def test_minimal_config(self):
        """Test client with minimal required config."""
        client = BinanceWebSocketClient(
            ws_url="wss://test.com",
            streams=["s"],
            nats_url="nats://h:4222",
            nats_topic="t",
        )

        assert client.ws_url == "wss://test.com"
        assert client.streams == ["s"]
        assert client.nats_url == "nats://h:4222"
        assert client.nats_topic == "t"

    def test_maximal_config(self):
        """Test client with all optional parameters."""
        logger = MagicMock()
        
        client = BinanceWebSocketClient(
            ws_url="wss://maximal.test.com:9443/stream?params=1",
            streams=["a@trade", "b@ticker", "c@depth", "d@kline"],
            nats_url="nats://user:pass@nats.example.com:4222",
            nats_topic="crypto.market.production.v2",
            logger=logger,
            max_reconnect_attempts=50,
            reconnect_delay=20,
            ping_interval=45,
            ping_timeout=30,
        )

        assert "9443" in client.ws_url
        assert len(client.streams) == 4
        assert "user:pass" in client.nats_url
        assert client.logger is logger
        assert client.max_reconnect_attempts == 50
        assert client.reconnect_delay == 20

    def test_zero_reconnect_attempts(self):
        """Test client with zero reconnect attempts."""
        client = BinanceWebSocketClient(
            ws_url="wss://test.com",
            streams=["test@stream"],
            nats_url="nats://localhost:4222",
            nats_topic="test.topic",
            max_reconnect_attempts=0,
        )

        assert client.max_reconnect_attempts == 0

    def test_large_reconnect_delay(self):
        """Test client with large reconnect delay."""
        client = BinanceWebSocketClient(
            ws_url="wss://test.com",
            streams=["test@stream"],
            nats_url="nats://localhost:4222",
            nats_topic="test.topic",
            reconnect_delay=3600,
        )

        assert client.reconnect_delay == 3600


@pytest.mark.unit
class TestHealthServerMultipleInstances:
    """Test multiple health server instances."""

    def test_multiple_servers_different_ports(self):
        """Test creating multiple servers on different ports."""
        servers = [
            HealthServer(port=9200),
            HealthServer(port=9201),
            HealthServer(port=9202),
        ]

        for i, server in enumerate(servers):
            assert server.port == 9200 + i

    def test_multiple_servers_different_loggers(self):
        """Test creating servers with different loggers."""
        logger1 = MagicMock()
        logger2 = MagicMock()

        server1 = HealthServer(port=9300, logger=logger1)
        server2 = HealthServer(port=9301, logger=logger2)

        assert server1.logger is logger1
        assert server2.logger is logger2
        assert server1.logger is not server2.logger

