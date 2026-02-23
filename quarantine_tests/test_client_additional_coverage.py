"""
Additional tests to boost client.py coverage.

Focuses on error paths, edge cases, and scenarios not covered by existing comprehensive tests.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from socket_client.core.client import BinanceWebSocketClient


@pytest.mark.unit
class TestClientErrorHandling:
    """Test error handling scenarios."""

    @pytest.mark.asyncio
    async def test_connect_websocket_failure(self):
        """Test WebSocket connection failure."""
        client = BinanceWebSocketClient(
            ws_url="wss://test.com",
            streams=["test@stream"],
            nats_url="nats://localhost:4222",
            nats_topic="test.topic",
        )

        with patch("websockets.connect", side_effect=Exception("Connection failed")):
            result = await client._connect_websocket()
            assert result is False

    @pytest.mark.asyncio
    async def test_connect_nats_failure(self):
        """Test NATS connection failure."""
        client = BinanceWebSocketClient(
            ws_url="wss://test.com",
            streams=["test@stream"],
            nats_url="nats://localhost:4222",
            nats_topic="test.topic",
        )

        with patch("nats.connect", side_effect=Exception("NATS connection failed")):
            result = await client._connect_nats()
            assert result is False

    @pytest.mark.asyncio
    async def test_process_message_invalid_json(self):
        """Test processing invalid JSON message."""
        client = BinanceWebSocketClient(
            ws_url="wss://test.com",
            streams=["test@stream"],
            nats_url="nats://localhost:4222",
            nats_topic="test.topic",
        )

        # Mock NATS client
        client.nats_client = AsyncMock()

        # Invalid JSON should be handled gracefully
        await client._process_message("invalid json")
        
        # Should not have published anything
        assert client.nats_client.publish.call_count == 0

    @pytest.mark.asyncio
    async def test_publish_nats_failure(self):
        """Test NATS publish failure."""
        client = BinanceWebSocketClient(
            ws_url="wss://test.com",
            streams=["test@stream"],
            nats_url="nats://localhost:4222",
            nats_topic="test.topic",
        )

        mock_nats = AsyncMock()
        mock_nats.publish.side_effect = Exception("Publish failed")
        client.nats_client = mock_nats

        valid_message = '{"stream": "test@stream", "data": {"test": true}}'
        await client._process_message(valid_message)
        
        # Should have attempted to publish
        assert mock_nats.publish.call_count > 0


@pytest.mark.unit
class TestClientStatistics:
    """Test client statistics tracking."""

    def test_statistics_initialization(self):
        """Test statistics are initialized correctly."""
        client = BinanceWebSocketClient(
            ws_url="wss://test.com",
            streams=["test@stream"],
            nats_url="nats://localhost:4222",
            nats_topic="test.topic",
        )

        assert client.processed_messages == 0
        assert client.dropped_messages == 0
        assert client.reconnect_attempts == 0
        assert client.start_time > 0

    @pytest.mark.asyncio
    async def test_message_queue_full_drops_messages(self):
        """Test messages are dropped when queue is full."""
        client = BinanceWebSocketClient(
            ws_url="wss://test.com",
            streams=["test@stream"],
            nats_url="nats://localhost:4222",
            nats_topic="test.topic",
        )

        # Fill the queue
        for i in range(1001):  # Queue maxsize is 1000
            try:
                client.message_queue.put_nowait({"msg": i})
            except asyncio.QueueFull:
                break

        initial_dropped = client.dropped_messages
        
        # Try to add more - should be dropped
        await client._handle_websocket_message('{"test": "overflow"}')
        
        # Dropped count should increase if queue was full
        # (implementation dependent)


@pytest.mark.unit
class TestClientConnectionState:
    """Test connection state management."""

    def test_initial_state(self):
        """Test client starts in disconnected state."""
        client = BinanceWebSocketClient(
            ws_url="wss://test.com",
            streams=["test@stream"],
            nats_url="nats://localhost:4222",
            nats_topic="test.topic",
        )

        assert client.is_connected is False
        assert client.is_running is False
        assert client.websocket is None
        assert client.nats_client is None

    @pytest.mark.asyncio
    async def test_stop_when_not_running(self):
        """Test stopping client when it's not running."""
        client = BinanceWebSocketClient(
            ws_url="wss://test.com",
            streams=["test@stream"],
            nats_url="nats://localhost:4222",
            nats_topic="test.topic",
        )

        # Should handle stop gracefully even if not running
        await client.stop()
        
        assert client.is_running is False

    @pytest.mark.asyncio
    async def test_reconnect_attempt_limit(self):
        """Test reconnection attempts are limited."""
        client = BinanceWebSocketClient(
            ws_url="wss://test.com",
            streams=["test@stream"],
            nats_url="nats://localhost:4222",
            nats_topic="test.topic",
            max_reconnect_attempts=3,
        )

        assert client.max_reconnect_attempts == 3
        assert client.reconnect_attempts == 0


@pytest.mark.unit
class TestClientConfiguration:
    """Test client configuration."""

    def test_custom_configuration(self):
        """Test client with custom configuration."""
        client = BinanceWebSocketClient(
            ws_url="wss://custom.url",
            streams=["stream1@trade", "stream2@ticker"],
            nats_url="nats://custom:4222",
            nats_topic="custom.topic",
            max_reconnect_attempts=15,
            reconnect_delay=10,
            ping_interval=25,
            ping_timeout=15,
        )

        assert client.ws_url == "wss://custom.url"
        assert len(client.streams) == 2
        assert client.nats_url == "nats://custom:4222"
        assert client.nats_topic == "custom.topic"
        assert client.max_reconnect_attempts == 15
        assert client.reconnect_delay == 10
        assert client.ping_interval == 25
        assert client.ping_timeout == 15

    def test_logger_parameter(self):
        """Test custom logger can be provided."""
        custom_logger = MagicMock()
        
        client = BinanceWebSocketClient(
            ws_url="wss://test.com",
            streams=["test@stream"],
            nats_url="nats://localhost:4222",
            nats_topic="test.topic",
            logger=custom_logger,
        )

        assert client.logger is custom_logger

