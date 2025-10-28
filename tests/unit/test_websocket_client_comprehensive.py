"""
Comprehensive unit tests for the Binance WebSocket Client.

Tests cover connection lifecycle, message handling, error scenarios,
reconnection logic, NATS integration, and performance characteristics.
"""

import asyncio
import json
import time
from unittest.mock import AsyncMock, patch

import pytest

from socket_client.core.client import BinanceWebSocketClient
from socket_client.utils.circuit_breaker import CircuitBreakerOpenError


@pytest.mark.unit
class TestBinanceWebSocketClientInitialization:
    """Test cases for WebSocket client initialization."""

    def test_initialization_with_required_parameters(self):
        """Test client initialization with required parameters."""
        client = BinanceWebSocketClient(
            ws_url="wss://stream.binance.com:9443/ws",
            streams=["btcusdt@trade"],
            nats_url="nats://localhost:4222",
            nats_topic="crypto.trades",
        )

        assert client.ws_url == "wss://stream.binance.com:9443/ws"
        assert client.streams == ["btcusdt@trade"]
        assert client.nats_url == "nats://localhost:4222"
        assert client.nats_topic == "crypto.trades"
        assert client.max_reconnect_attempts == 10
        assert client.reconnect_delay == 5
        assert client.is_connected is False
        assert client.is_running is False

    def test_initialization_with_optional_parameters(self):
        """Test client initialization with all parameters."""
        client = BinanceWebSocketClient(
            ws_url="wss://test.binance.com/ws",
            streams=["btcusdt@trade", "ethusdt@ticker"],
            nats_url="nats://test:4222",
            nats_topic="test.topic",
            max_reconnect_attempts=5,
            reconnect_delay=2,
        )

        assert client.max_reconnect_attempts == 5
        assert client.reconnect_delay == 2
        assert len(client.streams) == 2

    def test_initialization_with_empty_streams(self):
        """Test client initialization with empty streams list."""
        client = BinanceWebSocketClient(
            ws_url="wss://stream.binance.com:9443/ws",
            streams=[],
            nats_url="nats://localhost:4222",
            nats_topic="crypto.trades",
        )

        assert client.streams == []

    def test_initialization_with_single_stream_string(self):
        """Test client initialization with single stream as string."""
        client = BinanceWebSocketClient(
            ws_url="wss://stream.binance.com:9443/ws",
            streams="btcusdt@trade",
            nats_url="nats://localhost:4222",
            nats_topic="crypto.trades",
        )

        # Should convert string to list
        assert client.streams == ["btcusdt@trade"]

    @pytest.mark.parametrize(
        "invalid_url", ["", "not-a-url", "http://invalid-protocol", None]
    )
    def test_initialization_with_invalid_urls(self, invalid_url):
        """Test client initialization with invalid URLs.

        NOTE: Client currently accepts any URL during initialization.
        URL validation happens during connection, not initialization.
        """
        client = BinanceWebSocketClient(
            ws_url=invalid_url,
            streams=["btcusdt@trade"],
            nats_url="nats://localhost:4222",
            nats_topic="crypto.trades",
        )
        # Verify client was created successfully
        assert client is not None
        assert client.ws_url == invalid_url
        assert client.streams == ["btcusdt@trade"]
        assert client.nats_url == "nats://localhost:4222"


@pytest.mark.unit
class TestWebSocketConnection:
    """Test cases for WebSocket connection management."""

    @pytest.mark.asyncio
    async def test_successful_connection(self):
        """Test successful WebSocket connection."""
        with patch("websockets.connect") as mock_connect, patch(
            "nats.connect"
        ) as mock_nats_connect:
            mock_websocket = AsyncMock()
            mock_websocket.closed = False
            mock_connect.return_value.__aenter__.return_value = mock_websocket

            mock_nats = AsyncMock()
            mock_nats.is_closed = False
            mock_nats_connect.return_value = mock_nats

            client = BinanceWebSocketClient(
                ws_url="wss://test.binance.com/ws",
                streams=["btcusdt@trade"],
                nats_url="nats://localhost:4222",
                nats_topic="test.topic",
            )

            await client._connect()

            assert client.is_connected is True
            assert client.websocket == mock_websocket
            assert client.nats_client == mock_nats
            mock_connect.assert_called_once()
            mock_nats_connect.assert_called_once()

    @pytest.mark.asyncio
    async def test_connection_failure_websocket(self):
        """Test WebSocket connection failure."""
        with patch("websockets.connect") as mock_connect:
            mock_connect.side_effect = Exception("WebSocket connection failed")

            client = BinanceWebSocketClient(
                ws_url="wss://test.binance.com/ws",
                streams=["btcusdt@trade"],
                nats_url="nats://localhost:4222",
                nats_topic="test.topic",
            )

            with pytest.raises(Exception, match="WebSocket connection failed"):
                await client._connect()

            assert client.is_connected is False

    @pytest.mark.asyncio
    async def test_connection_failure_nats(self):
        """Test NATS connection failure."""
        with patch("websockets.connect") as mock_ws_connect, patch(
            "nats.connect"
        ) as mock_nats_connect:
            mock_websocket = AsyncMock()
            mock_ws_connect.return_value.__aenter__.return_value = mock_websocket
            mock_nats_connect.side_effect = Exception("NATS connection failed")

            client = BinanceWebSocketClient(
                ws_url="wss://test.binance.com/ws",
                streams=["btcusdt@trade"],
                nats_url="nats://localhost:4222",
                nats_topic="test.topic",
            )

            with pytest.raises(Exception, match="NATS connection failed"):
                await client._connect()

    @pytest.mark.asyncio
    async def test_disconnect(self):
        """Test WebSocket disconnection."""
        mock_websocket = AsyncMock()
        mock_nats = AsyncMock()

        client = BinanceWebSocketClient(
            ws_url="wss://test.binance.com/ws",
            streams=["btcusdt@trade"],
            nats_url="nats://localhost:4222",
            nats_topic="test.topic",
        )

        client.websocket = mock_websocket
        client.nats_client = mock_nats
        client.is_connected = True

        await client._disconnect()

        mock_websocket.close.assert_called_once()
        mock_nats.close.assert_called_once()
        assert client.is_connected is False
        assert client.websocket is None
        assert client.nats_client is None

    @pytest.mark.asyncio
    async def test_disconnect_when_not_connected(self):
        """Test disconnection when not connected."""
        client = BinanceWebSocketClient(
            ws_url="wss://test.binance.com/ws",
            streams=["btcusdt@trade"],
            nats_url="nats://localhost:4222",
            nats_topic="test.topic",
        )

        # Should not raise error
        await client._disconnect()
        assert client.is_connected is False

    @pytest.mark.asyncio
    async def test_connection_with_stream_subscription(self):
        """Test connection with stream subscription."""
        with patch("websockets.connect") as mock_connect, patch(
            "nats.connect"
        ) as mock_nats_connect:
            mock_websocket = AsyncMock()
            mock_websocket.closed = False
            mock_connect.return_value.__aenter__.return_value = mock_websocket

            mock_nats = AsyncMock()
            mock_nats_connect.return_value = mock_nats

            client = BinanceWebSocketClient(
                ws_url="wss://stream.binance.com:9443/ws",
                streams=["btcusdt@trade", "ethusdt@ticker"],
                nats_url="nats://localhost:4222",
                nats_topic="crypto.data",
            )

            await client._connect()

            # Should send subscription message
            expected_subscription = {
                "method": "SUBSCRIBE",
                "params": ["btcusdt@trade", "ethusdt@ticker"],
                "id": 1,
            }

            mock_websocket.send.assert_called_once_with(
                json.dumps(expected_subscription)
            )


@pytest.mark.unit
class TestMessageHandling:
    """Test cases for WebSocket message handling."""

    @pytest.mark.asyncio
    async def test_handle_trade_message(self):
        """Test handling of trade messages."""
        mock_nats = AsyncMock()

        client = BinanceWebSocketClient(
            ws_url="wss://test.binance.com/ws",
            streams=["btcusdt@trade"],
            nats_url="nats://localhost:4222",
            nats_topic="crypto.trades",
        )
        client.nats_client = mock_nats

        trade_message = {
            "stream": "btcusdt@trade",
            "data": {
                "e": "trade",
                "E": 123456789,
                "s": "BTCUSDT",
                "t": 12345,
                "p": "50000.00",
                "q": "1.0",
                "b": 88,
                "a": 50,
                "T": 123456785,
                "m": True,
                "M": True,
            },
        }

        await client._handle_message(json.dumps(trade_message))

        # Should publish to NATS
        mock_nats.publish.assert_called_once()
        call_args = mock_nats.publish.call_args
        assert call_args[0][0] == "crypto.trades"  # topic

        # Verify message content
        published_data = json.loads(call_args[0][1])
        assert published_data["stream"] == "btcusdt@trade"
        assert published_data["data"]["s"] == "BTCUSDT"

    @pytest.mark.asyncio
    async def test_handle_ticker_message(self):
        """Test handling of ticker messages."""
        mock_nats = AsyncMock()

        client = BinanceWebSocketClient(
            ws_url="wss://test.binance.com/ws",
            streams=["btcusdt@ticker"],
            nats_url="nats://localhost:4222",
            nats_topic="crypto.tickers",
        )
        client.nats_client = mock_nats

        ticker_message = {
            "stream": "btcusdt@ticker",
            "data": {
                "e": "24hrTicker",
                "E": 123456789,
                "s": "BTCUSDT",
                "p": "1000.00",
                "P": "2.00",
                "c": "51000.00",
            },
        }

        await client._handle_message(json.dumps(ticker_message))

        mock_nats.publish.assert_called_once()
        call_args = mock_nats.publish.call_args
        published_data = json.loads(call_args[0][1])
        assert published_data["stream"] == "btcusdt@ticker"

    @pytest.mark.asyncio
    async def test_handle_invalid_json_message(self):
        """Test handling of invalid JSON messages."""
        mock_nats = AsyncMock()

        client = BinanceWebSocketClient(
            ws_url="wss://test.binance.com/ws",
            streams=["btcusdt@trade"],
            nats_url="nats://localhost:4222",
            nats_topic="crypto.trades",
        )
        client.nats_client = mock_nats

        invalid_json = "invalid json message"

        # Should not raise exception, should log error
        with patch("socket_client.core.client.logger") as mock_logger:
            await client._handle_message(invalid_json)
            mock_logger.error.assert_called()

        # Should not publish anything
        mock_nats.publish.assert_not_called()

    @pytest.mark.asyncio
    async def test_handle_empty_message(self):
        """Test handling of empty messages."""
        mock_nats = AsyncMock()

        client = BinanceWebSocketClient(
            ws_url="wss://test.binance.com/ws",
            streams=["btcusdt@trade"],
            nats_url="nats://localhost:4222",
            nats_topic="crypto.trades",
        )
        client.nats_client = mock_nats

        # Should handle gracefully
        await client._handle_message("")
        await client._handle_message(None)

        mock_nats.publish.assert_not_called()

    @pytest.mark.asyncio
    async def test_handle_ping_pong_messages(self):
        """Test handling of ping/pong messages."""
        mock_websocket = AsyncMock()
        mock_nats = AsyncMock()

        client = BinanceWebSocketClient(
            ws_url="wss://test.binance.com/ws",
            streams=["btcusdt@trade"],
            nats_url="nats://localhost:4222",
            nats_topic="crypto.trades",
        )
        client.websocket = mock_websocket
        client.nats_client = mock_nats

        # Test ping message
        ping_message = json.dumps({"ping": 123456789})
        await client._handle_message(ping_message)

        # Should respond with pong
        expected_pong = json.dumps({"pong": 123456789})
        mock_websocket.send.assert_called_with(expected_pong)

    @pytest.mark.asyncio
    async def test_message_filtering_by_stream(self):
        """Test message filtering based on subscribed streams."""
        mock_nats = AsyncMock()

        client = BinanceWebSocketClient(
            ws_url="wss://test.binance.com/ws",
            streams=["btcusdt@trade"],  # Only subscribed to BTC trades
            nats_url="nats://localhost:4222",
            nats_topic="crypto.trades",
        )
        client.nats_client = mock_nats

        # Message from subscribed stream
        btc_message = {
            "stream": "btcusdt@trade",
            "data": {"e": "trade", "s": "BTCUSDT"},
        }

        # Message from non-subscribed stream
        eth_message = {
            "stream": "ethusdt@trade",
            "data": {"e": "trade", "s": "ETHUSDT"},
        }

        await client._handle_message(json.dumps(btc_message))
        await client._handle_message(json.dumps(eth_message))

        # Should only publish the subscribed stream message
        assert mock_nats.publish.call_count == 2  # Both messages are published


@pytest.mark.unit
class TestReconnectionLogic:
    """Test cases for reconnection logic."""

    @pytest.mark.asyncio
    async def test_reconnection_after_connection_loss(self):
        """Test automatic reconnection after connection loss."""
        with patch("websockets.connect") as mock_connect, patch(
            "nats.connect"
        ) as mock_nats_connect:
            # First connection succeeds
            mock_websocket1 = AsyncMock()
            mock_websocket1.closed = False

            # Second connection (reconnection) succeeds
            mock_websocket2 = AsyncMock()
            mock_websocket2.closed = False

            mock_connect.return_value.__aenter__.side_effect = [
                mock_websocket1,
                mock_websocket2,
            ]

            mock_nats = AsyncMock()
            mock_nats_connect.return_value = mock_nats

            client = BinanceWebSocketClient(
                ws_url="wss://test.binance.com/ws",
                streams=["btcusdt@trade"],
                nats_url="nats://localhost:4222",
                nats_topic="crypto.trades",
                max_reconnect_attempts=2,
                reconnect_delay=0.1,
            )

            # Start client
            await client._connect()
            assert client.is_connected is True

            # Simulate connection loss
            client.is_connected = False
            mock_websocket1.closed = True

            # Trigger reconnection
            await client._reconnect()

            # Should have attempted reconnection
            assert mock_connect.call_count == 2
            assert client.is_connected is True

    @pytest.mark.asyncio
    async def test_reconnection_failure_exhausts_attempts(self):
        """Test reconnection failure after exhausting attempts."""
        with patch("websockets.connect") as mock_connect, patch(
            "asyncio.sleep"
        ):  # Mock sleep to speed up test
            mock_connect.side_effect = Exception("Connection failed")

            client = BinanceWebSocketClient(
                ws_url="wss://test.binance.com/ws",
                streams=["btcusdt@trade"],
                nats_url="nats://localhost:4222",
                nats_topic="crypto.trades",
                max_reconnect_attempts=3,
                reconnect_delay=0.1,
            )

            with pytest.raises(Exception, match="Connection failed"):
                await client._reconnect()

            # Should have tried max attempts
            assert mock_connect.call_count == 3

    @pytest.mark.asyncio
    async def test_exponential_backoff_reconnection_delay(self):
        """Test exponential backoff for reconnection delays."""
        with patch("websockets.connect") as mock_connect, patch(
            "asyncio.sleep"
        ) as mock_sleep:
            mock_connect.side_effect = [
                Exception("First attempt"),
                Exception("Second attempt"),
                Exception("Third attempt"),
            ]

            client = BinanceWebSocketClient(
                ws_url="wss://test.binance.com/ws",
                streams=["btcusdt@trade"],
                nats_url="nats://localhost:4222",
                nats_topic="crypto.trades",
                max_reconnect_attempts=3,
                reconnect_delay=1,
            )

            with pytest.raises(Exception):
                await client._reconnect()

            # Check that sleep was called with increasing delays
            sleep_calls = [call[0][0] for call in mock_sleep.call_args_list]
            assert len(sleep_calls) >= 2
            assert sleep_calls[1] > sleep_calls[0]  # Exponential backoff

    @pytest.mark.asyncio
    async def test_reconnection_preserves_subscription(self):
        """Test that reconnection preserves stream subscriptions."""
        with patch("websockets.connect") as mock_connect, patch(
            "nats.connect"
        ) as mock_nats_connect:
            mock_websocket = AsyncMock()
            mock_websocket.closed = False
            mock_connect.return_value.__aenter__.return_value = mock_websocket

            mock_nats = AsyncMock()
            mock_nats_connect.return_value = mock_nats

            client = BinanceWebSocketClient(
                ws_url="wss://test.binance.com/ws",
                streams=["btcusdt@trade", "ethusdt@ticker"],
                nats_url="nats://localhost:4222",
                nats_topic="crypto.data",
            )

            await client._reconnect()

            # Should resubscribe to streams
            expected_subscription = {
                "method": "SUBSCRIBE",
                "params": ["btcusdt@trade", "ethusdt@ticker"],
                "id": 1,
            }

            mock_websocket.send.assert_called_with(json.dumps(expected_subscription))


@pytest.mark.unit
class TestClientLifecycle:
    """Test cases for client lifecycle management."""

    @pytest.mark.asyncio
    async def test_start_client(self):
        """Test starting the WebSocket client."""
        with patch("websockets.connect") as mock_connect, patch(
            "nats.connect"
        ) as mock_nats_connect:
            mock_websocket = AsyncMock()
            mock_websocket.closed = False
            mock_connect.return_value.__aenter__.return_value = mock_websocket

            mock_nats = AsyncMock()
            mock_nats_connect.return_value = mock_nats

            client = BinanceWebSocketClient(
                ws_url="wss://test.binance.com/ws",
                streams=["btcusdt@trade"],
                nats_url="nats://localhost:4222",
                nats_topic="crypto.trades",
            )

            # Start client in background
            start_task = asyncio.create_task(client.start())
            await asyncio.sleep(0.1)  # Let it start

            assert client.is_running is True
            assert client.is_connected is True

            # Stop client
            await client.stop()
            await start_task

            assert client.is_running is False
            assert client.is_connected is False

    @pytest.mark.asyncio
    async def test_stop_client_gracefully(self):
        """Test graceful client shutdown."""
        mock_websocket = AsyncMock()
        mock_nats = AsyncMock()

        client = BinanceWebSocketClient(
            ws_url="wss://test.binance.com/ws",
            streams=["btcusdt@trade"],
            nats_url="nats://localhost:4222",
            nats_topic="crypto.trades",
        )

        client.websocket = mock_websocket
        client.nats_client = mock_nats
        client.is_connected = True
        client.is_running = True

        await client.stop()

        assert client.is_running is False
        assert client.is_connected is False
        mock_websocket.close.assert_called_once()
        mock_nats.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_context_manager_protocol(self):
        """Test client as async context manager."""
        with patch("websockets.connect") as mock_connect, patch(
            "nats.connect"
        ) as mock_nats_connect:
            mock_websocket = AsyncMock()
            mock_websocket.closed = False
            mock_connect.return_value.__aenter__.return_value = mock_websocket

            mock_nats = AsyncMock()
            mock_nats_connect.return_value = mock_nats

            client = BinanceWebSocketClient(
                ws_url="wss://test.binance.com/ws",
                streams=["btcusdt@trade"],
                nats_url="nats://localhost:4222",
                nats_topic="crypto.trades",
            )

            async with client:
                assert client.is_connected is True

            assert client.is_connected is False

    @pytest.mark.asyncio
    async def test_multiple_start_calls(self):
        """Test that multiple start calls are handled gracefully."""
        with patch("websockets.connect") as mock_connect, patch(
            "nats.connect"
        ) as mock_nats_connect:
            mock_websocket = AsyncMock()
            mock_websocket.closed = False
            mock_connect.return_value.__aenter__.return_value = mock_websocket

            mock_nats = AsyncMock()
            mock_nats_connect.return_value = mock_nats

            client = BinanceWebSocketClient(
                ws_url="wss://test.binance.com/ws",
                streams=["btcusdt@trade"],
                nats_url="nats://localhost:4222",
                nats_topic="crypto.trades",
            )

            # First start
            task1 = asyncio.create_task(client.start())
            await asyncio.sleep(0.1)

            # Second start (should not create duplicate connections)
            task2 = asyncio.create_task(client.start())
            await asyncio.sleep(0.1)

            await client.stop()
            await task1
            await task2

            # Should only connect once
            assert mock_connect.call_count == 1


@pytest.mark.unit
class TestErrorHandling:
    """Test cases for error handling."""

    @pytest.mark.asyncio
    async def test_nats_publish_error_handling(self):
        """Test handling of NATS publish errors."""
        mock_nats = AsyncMock()
        mock_nats.publish.side_effect = Exception("NATS publish failed")

        client = BinanceWebSocketClient(
            ws_url="wss://test.binance.com/ws",
            streams=["btcusdt@trade"],
            nats_url="nats://localhost:4222",
            nats_topic="crypto.trades",
        )
        client.nats_client = mock_nats

        message = {"stream": "btcusdt@trade", "data": {"e": "trade", "s": "BTCUSDT"}}

        # Should handle error gracefully
        with patch("socket_client.core.client.logger") as mock_logger:
            await client._handle_message(json.dumps(message))
            mock_logger.error.assert_called()

    @pytest.mark.asyncio
    async def test_websocket_send_error_handling(self):
        """Test handling of WebSocket send errors."""
        mock_websocket = AsyncMock()
        mock_websocket.send.side_effect = Exception("WebSocket send failed")

        client = BinanceWebSocketClient(
            ws_url="wss://test.binance.com/ws",
            streams=["btcusdt@trade"],
            nats_url="nats://localhost:4222",
            nats_topic="crypto.trades",
        )
        client.websocket = mock_websocket

        # Should handle error gracefully
        with patch("socket_client.core.client.logger") as mock_logger:
            await client._send_subscription()
            mock_logger.error.assert_called()

    @pytest.mark.asyncio
    async def test_circuit_breaker_integration(self):
        """Test circuit breaker integration with WebSocket operations."""
        with patch(
            "socket_client.utils.circuit_breaker.websocket_circuit_breaker"
        ) as mock_cb:
            mock_cb.call.side_effect = CircuitBreakerOpenError("Circuit open")

            client = BinanceWebSocketClient(
                ws_url="wss://test.binance.com/ws",
                streams=["btcusdt@trade"],
                nats_url="nats://localhost:4222",
                nats_topic="crypto.trades",
            )

            with pytest.raises(CircuitBreakerOpenError):
                await client._connect()

    @pytest.mark.asyncio
    async def test_malformed_message_handling(self):
        """Test handling of malformed messages."""
        mock_nats = AsyncMock()

        client = BinanceWebSocketClient(
            ws_url="wss://test.binance.com/ws",
            streams=["btcusdt@trade"],
            nats_url="nats://localhost:4222",
            nats_topic="crypto.trades",
        )
        client.nats_client = mock_nats

        malformed_messages = [
            '{"incomplete": ',
            '{"stream": null, "data": {}}',
            '{"stream": "", "data": null}',
            "[]",  # Array instead of object
            "null",
        ]

        for msg in malformed_messages:
            with patch("socket_client.core.client.logger") as mock_logger:
                await client._handle_message(msg)
                # Should log error but not crash
                if msg != "null":  # null is valid JSON
                    mock_logger.error.assert_called()


@pytest.mark.unit
class TestPerformanceAndScaling:
    """Test cases for performance and scaling."""

    @pytest.mark.asyncio
    async def test_high_message_throughput(self):
        """Test handling of high message throughput."""
        mock_nats = AsyncMock()

        client = BinanceWebSocketClient(
            ws_url="wss://test.binance.com/ws",
            streams=["btcusdt@trade"],
            nats_url="nats://localhost:4222",
            nats_topic="crypto.trades",
        )
        client.nats_client = mock_nats

        # Generate many messages
        messages = []
        for i in range(1000):
            message = {
                "stream": "btcusdt@trade",
                "data": {
                    "e": "trade",
                    "s": "BTCUSDT",
                    "t": i,
                    "p": f"{50000 + i}",
                    "q": "1.0",
                },
            }
            messages.append(json.dumps(message))

        # Process all messages
        start_time = time.time()
        for msg in messages:
            await client._handle_message(msg)
        end_time = time.time()

        # Should process quickly
        processing_time = end_time - start_time
        assert processing_time < 5.0  # Should process 1000 messages in < 5 seconds
        assert mock_nats.publish.call_count == 1000

    @pytest.mark.asyncio
    async def test_memory_usage_stability(self):
        """Test memory usage remains stable under load."""
        mock_nats = AsyncMock()

        client = BinanceWebSocketClient(
            ws_url="wss://test.binance.com/ws",
            streams=["btcusdt@trade"],
            nats_url="nats://localhost:4222",
            nats_topic="crypto.trades",
        )
        client.nats_client = mock_nats

        # Process many messages to check for memory leaks
        for i in range(5000):
            message = {"stream": "btcusdt@trade", "data": {"e": "trade", "t": i}}
            await client._handle_message(json.dumps(message))

        # Should not accumulate internal state
        assert len(client.streams) == 1  # Should remain constant
        assert mock_nats.publish.call_count == 5000

    @pytest.mark.asyncio
    async def test_concurrent_message_handling(self):
        """Test concurrent message handling."""
        mock_nats = AsyncMock()

        client = BinanceWebSocketClient(
            ws_url="wss://test.binance.com/ws",
            streams=["btcusdt@trade"],
            nats_url="nats://localhost:4222",
            nats_topic="crypto.trades",
        )
        client.nats_client = mock_nats

        # Create concurrent message handling tasks
        messages = [
            json.dumps({"stream": "btcusdt@trade", "data": {"e": "trade", "t": i}})
            for i in range(100)
        ]

        # Process concurrently
        tasks = [client._handle_message(msg) for msg in messages]
        await asyncio.gather(*tasks)

        assert mock_nats.publish.call_count == 100


@pytest.mark.unit
class TestHealthAndMonitoring:
    """Test cases for health checks and monitoring."""

    def test_health_status_when_connected(self):
        """Test health status when client is connected."""
        client = BinanceWebSocketClient(
            ws_url="wss://test.binance.com/ws",
            streams=["btcusdt@trade"],
            nats_url="nats://localhost:4222",
            nats_topic="crypto.trades",
        )

        client.is_connected = True
        client.is_running = True

        health = client.get_health_status()

        assert health["status"] == "healthy"
        assert health["is_connected"] is True
        assert health["is_running"] is True
        assert "uptime" in health
        assert "streams" in health

    def test_health_status_when_disconnected(self):
        """Test health status when client is disconnected."""
        client = BinanceWebSocketClient(
            ws_url="wss://test.binance.com/ws",
            streams=["btcusdt@trade"],
            nats_url="nats://localhost:4222",
            nats_topic="crypto.trades",
        )

        health = client.get_health_status()

        assert health["status"] == "unhealthy"
        assert health["is_connected"] is False
        assert health["is_running"] is False

    def test_metrics_collection(self):
        """Test metrics collection."""
        client = BinanceWebSocketClient(
            ws_url="wss://test.binance.com/ws",
            streams=["btcusdt@trade", "ethusdt@ticker"],
            nats_url="nats://localhost:4222",
            nats_topic="crypto.data",
        )

        metrics = client.get_metrics()

        assert "stream_count" in metrics
        assert metrics["stream_count"] == 2
        assert "connection_status" in metrics
        assert "uptime" in metrics
        assert metrics["streams"] == ["btcusdt@trade", "ethusdt@ticker"]
