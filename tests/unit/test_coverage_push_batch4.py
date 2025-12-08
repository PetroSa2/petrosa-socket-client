"""
Batch 4: Comprehensive test additions targeting remaining gaps.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from socket_client.core.client import BinanceWebSocketClient


@pytest.mark.unit
class TestClientURLHandling:
    """Test URL handling and construction."""

    def test_ws_url_with_query_params(self):
        """Test WebSocket URL with query parameters."""
        client = BinanceWebSocketClient(
            ws_url="wss://stream.binance.com/ws?streams=btcusdt@trade",
            streams=["btcusdt@trade"],
            nats_url="nats://localhost:4222",
            nats_topic="test.topic",
        )

        assert "?" in client.ws_url
        assert "streams=" in client.ws_url

    def test_ws_url_with_port(self):
        """Test WebSocket URL with explicit port."""
        client = BinanceWebSocketClient(
            ws_url="wss://stream.binance.com:9443/ws",
            streams=["test@stream"],
            nats_url="nats://localhost:4222",
            nats_topic="test.topic",
        )

        assert ":9443" in client.ws_url

    def test_nats_url_with_credentials(self):
        """Test NATS URL with credentials."""
        client = BinanceWebSocketClient(
            ws_url="wss://test.com",
            streams=["test@stream"],
            nats_url="nats://username:password@nats.server:4222",
            nats_topic="test.topic",
        )

        assert "username:password" in client.nats_url
        assert "@nats.server" in client.nats_url


@pytest.mark.unit
class TestClientStreamHandling:
    """Test stream handling variations."""

    def test_single_stream_access(self):
        """Test accessing single stream."""
        client = BinanceWebSocketClient(
            ws_url="wss://test.com",
            streams=["btcusdt@trade"],
            nats_url="nats://localhost:4222",
            nats_topic="test.topic",
        )

        assert client.streams[0] == "btcusdt@trade"

    def test_multiple_streams_access(self):
        """Test accessing multiple streams."""
        streams = ["btcusdt@trade", "ethusdt@ticker", "bnbusdt@depth"]
        client = BinanceWebSocketClient(
            ws_url="wss://test.com",
            streams=streams,
            nats_url="nats://localhost:4222",
            nats_topic="test.topic",
        )

        for i, stream in enumerate(streams):
            assert client.streams[i] == stream

    def test_stream_list_iteration(self):
        """Test iterating over streams list."""
        streams = ["a@trade", "b@ticker", "c@depth"]
        client = BinanceWebSocketClient(
            ws_url="wss://test.com",
            streams=streams,
            nats_url="nats://localhost:4222",
            nats_topic="test.topic",
        )

        collected = []
        for stream in client.streams:
            collected.append(stream)

        assert collected == streams


@pytest.mark.unit
class TestClientReconnectionConfig:
    """Test reconnection configuration."""

    def test_default_reconnection_settings(self):
        """Test default reconnection settings."""
        client = BinanceWebSocketClient(
            ws_url="wss://test.com",
            streams=["test@stream"],
            nats_url="nats://localhost:4222",
            nats_topic="test.topic",
        )

        # Should have defaults from constants
        assert client.max_reconnect_attempts > 0
        assert client.reconnect_delay > 0

    def test_custom_reconnection_settings(self):
        """Test custom reconnection settings."""
        client = BinanceWebSocketClient(
            ws_url="wss://test.com",
            streams=["test@stream"],
            nats_url="nats://localhost:4222",
            nats_topic="test.topic",
            max_reconnect_attempts=100,
            reconnect_delay=30,
        )

        assert client.max_reconnect_attempts == 100
        assert client.reconnect_delay == 30

    def test_reconnect_counter_starts_zero(self):
        """Test reconnect counter starts at zero."""
        client = BinanceWebSocketClient(
            ws_url="wss://test.com",
            streams=["test@stream"],
            nats_url="nats://localhost:4222",
            nats_topic="test.topic",
        )

        assert client.reconnect_attempts == 0


@pytest.mark.unit
class TestClientPingConfig:
    """Test ping configuration."""

    def test_default_ping_settings(self):
        """Test default ping settings."""
        client = BinanceWebSocketClient(
            ws_url="wss://test.com",
            streams=["test@stream"],
            nats_url="nats://localhost:4222",
            nats_topic="test.topic",
        )

        assert client.ping_interval > 0
        assert client.ping_timeout > 0

    def test_custom_ping_settings(self):
        """Test custom ping settings."""
        client = BinanceWebSocketClient(
            ws_url="wss://test.com",
            streams=["test@stream"],
            nats_url="nats://localhost:4222",
            nats_topic="test.topic",
            ping_interval=60,
            ping_timeout=40,
        )

        assert client.ping_interval == 60
        assert client.ping_timeout == 40

    def test_last_ping_starts_zero(self):
        """Test last_ping starts at zero."""
        client = BinanceWebSocketClient(
            ws_url="wss://test.com",
            streams=["test@stream"],
            nats_url="nats://localhost:4222",
            nats_topic="test.topic",
        )

        assert client.last_ping == 0.0


@pytest.mark.unit
class TestClientMessageStats:
    """Test message statistics."""

    def test_stats_log_interval_default(self):
        """Test stats_log_interval default value."""
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

    def test_num_processors_from_constants(self):
        """Test num_processors is set from constants."""
        client = BinanceWebSocketClient(
            ws_url="wss://test.com",
            streams=["test@stream"],
            nats_url="nats://localhost:4222",
            nats_topic="test.topic",
        )

        assert isinstance(client.num_processors, int)
        assert client.num_processors > 0
