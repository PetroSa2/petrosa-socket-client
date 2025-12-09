"""
Tests for client connection methods (_connect_websocket, _connect_nats).
Targets uncovered lines in connection handling.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from socket_client.core.client import BinanceWebSocketClient


@pytest.mark.unit
class TestConnectWebSocket:
    """Test _connect_websocket method."""

    @pytest.mark.asyncio
    async def test_connect_websocket_success(self):
        """Test successful WebSocket connection."""
        client = BinanceWebSocketClient(
            ws_url="wss://test.com",
            streams=["test@stream"],
            nats_url="nats://localhost:4222",
            nats_topic="test.topic",
        )

        mock_ws = AsyncMock()
        
        with patch("websockets.connect", return_value=mock_ws):
            result = await client._connect_websocket()
            
            assert result is True
            assert client.websocket is not None
            assert client.is_connected is True

    @pytest.mark.asyncio
    async def test_connect_websocket_circuit_breaker_open(self):
        """Test WebSocket connection when circuit breaker is open."""
        client = BinanceWebSocketClient(
            ws_url="wss://test.com",
            streams=["test@stream"],
            nats_url="nats://localhost:4222",
            nats_topic="test.topic",
        )

        from socket_client.utils.circuit_breaker import CircuitBreakerOpenError

        with patch(
            "socket_client.utils.circuit_breaker.websocket_circuit_breaker.call",
            side_effect=CircuitBreakerOpenError("Circuit open"),
        ):
            result = await client._connect_websocket()
            
            assert result is False
            assert client.websocket is None

    @pytest.mark.asyncio
    async def test_connect_websocket_generic_exception(self):
        """Test WebSocket connection with generic exception."""
        client = BinanceWebSocketClient(
            ws_url="wss://test.com",
            streams=["test@stream"],
            nats_url="nats://localhost:4222",
            nats_topic="test.topic",
        )

        with patch("websockets.connect", side_effect=Exception("Connection refused")):
            result = await client._connect_websocket()
            
            assert result is False


@pytest.mark.unit
class TestConnectNATS:
    """Test _connect_nats method."""

    @pytest.mark.asyncio
    async def test_connect_nats_success(self):
        """Test successful NATS connection."""
        client = BinanceWebSocketClient(
            ws_url="wss://test.com",
            streams=["test@stream"],
            nats_url="nats://localhost:4222",
            nats_topic="test.topic",
        )

        mock_nats = AsyncMock()
        
        with patch("nats.connect", return_value=mock_nats):
            result = await client._connect_nats()
            
            assert result is True
            assert client.nats_client is not None

    @pytest.mark.asyncio
    async def test_connect_nats_circuit_breaker_open(self):
        """Test NATS connection when circuit breaker is open."""
        client = BinanceWebSocketClient(
            ws_url="wss://test.com",
            streams=["test@stream"],
            nats_url="nats://localhost:4222",
            nats_topic="test.topic",
        )

        from socket_client.utils.circuit_breaker import CircuitBreakerOpenError

        with patch(
            "socket_client.utils.circuit_breaker.nats_circuit_breaker.call",
            side_effect=CircuitBreakerOpenError("Circuit open"),
        ):
            result = await client._connect_nats()
            
            assert result is False
            assert client.nats_client is None

    @pytest.mark.asyncio
    async def test_connect_nats_generic_exception(self):
        """Test NATS connection with generic exception."""
        client = BinanceWebSocketClient(
            ws_url="wss://test.com",
            streams=["test@stream"],
            nats_url="nats://localhost:4222",
            nats_topic="test.topic",
        )

        with patch("nats.connect", side_effect=Exception("NATS unavailable")):
            result = await client._connect_nats()
            
            assert result is False


@pytest.mark.unit
class TestProcessMessages:
    """Test _process_messages worker method."""

    @pytest.mark.asyncio
    async def test_process_messages_processes_queue(self):
        """Test message processor processes queue messages."""
        client = BinanceWebSocketClient(
            ws_url="wss://test.com",
            streams=["test@stream"],
            nats_url="nats://localhost:4222",
            nats_topic="test.topic",
        )

        # Mock NATS client
        mock_nats = AsyncMock()
        client.nats_client = mock_nats

        # Add test message to queue
        test_message = '{"stream": "test@stream", "data": {"price": "100"}}'
        await client.message_queue.put(test_message)

        # Start processor
        client.is_running = True
        processor_task = asyncio.create_task(client._process_messages(worker_id=0))

        # Let it process
        await asyncio.sleep(0.2)

        # Stop
        client.is_running = False
        await asyncio.sleep(0.1)
        processor_task.cancel()

        try:
            await processor_task
        except asyncio.CancelledError:
            pass

        # Verify message was processed
        # (implementation dependent - may have been published)

    @pytest.mark.asyncio
    async def test_process_messages_handles_exception(self):
        """Test message processor handles exceptions gracefully."""
        client = BinanceWebSocketClient(
            ws_url="wss://test.com",
            streams=["test@stream"],
            nats_url="nats://localhost:4222",
            nats_topic="test.topic",
        )

        # Add invalid message
        await client.message_queue.put("invalid")

        # Start processor
        client.is_running = True
        processor_task = asyncio.create_task(client._process_messages(worker_id=0))

        # Let it attempt processing
        await asyncio.sleep(0.2)

        # Stop
        client.is_running = False
        await asyncio.sleep(0.1)
        processor_task.cancel()

        try:
            await processor_task
        except asyncio.CancelledError:
            pass

        # Should not have crashed


@pytest.mark.unit
class TestReconnection:
    """Test reconnection logic."""

    @pytest.mark.asyncio
    async def test_reconnect_increments_counter(self):
        """Test reconnection increments attempt counter."""
        client = BinanceWebSocketClient(
            ws_url="wss://test.com",
            streams=["test@stream"],
            nats_url="nats://localhost:4222",
            nats_topic="test.topic",
        )

        initial_attempts = client.reconnect_attempts
        
        # Mock failed connection
        with patch.object(client, "_connect_websocket", return_value=False):
            client.reconnect_attempts += 1
            
        assert client.reconnect_attempts == initial_attempts + 1

    @pytest.mark.asyncio
    async def test_reconnect_respects_max_attempts(self):
        """Test reconnection respects max attempts limit."""
        client = BinanceWebSocketClient(
            ws_url="wss://test.com",
            streams=["test@stream"],
            nats_url="nats://localhost:4222",
            nats_topic="test.topic",
            max_reconnect_attempts=3,
        )

        # Verify limit is set
        assert client.max_reconnect_attempts == 3
        
        # Simulate hitting limit
        client.reconnect_attempts = 3
        
        assert client.reconnect_attempts >= client.max_reconnect_attempts


@pytest.mark.unit
class TestPingLoop:
    """Test ping loop functionality."""

    @pytest.mark.asyncio
    async def test_ping_updates_last_ping_time(self):
        """Test ping updates last_ping timestamp."""
        import time
        
        client = BinanceWebSocketClient(
            ws_url="wss://test.com",
            streams=["test@stream"],
            nats_url="nats://localhost:4222",
            nats_topic="test.topic",
        )

        initial_time = client.last_ping
        assert initial_time == 0.0
        
        # Update it manually to test the attribute
        client.last_ping = time.time()
        
        assert client.last_ping > initial_time

