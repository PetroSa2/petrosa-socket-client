"""
Extended defensive checks and edge case tests.
Builds on existing test_client_defensive_checks.py.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from socket_client.core.client import BinanceWebSocketClient


@pytest.mark.unit
class TestClientDefensiveInitialization:
    """Test defensive initialization checks."""

    def test_empty_streams_list(self):
        """Test client with empty streams list."""
        client = BinanceWebSocketClient(
            ws_url="wss://test.com",
            streams=[],
            nats_url="nats://localhost:4222",
            nats_topic="test.topic",
        )

        assert client.streams == []
        assert len(client.streams) == 0

    def test_single_stream(self):
        """Test client with single stream."""
        client = BinanceWebSocketClient(
            ws_url="wss://test.com",
            streams=["btcusdt@trade"],
            nats_url="nats://localhost:4222",
            nats_topic="test.topic",
        )

        assert len(client.streams) == 1

    def test_many_streams(self):
        """Test client with many streams."""
        streams = [f"symbol{i}@trade" for i in range(50)]
        client = BinanceWebSocketClient(
            ws_url="wss://test.com",
            streams=streams,
            nats_url="nats://localhost:4222",
            nats_topic="test.topic",
        )

        assert len(client.streams) == 50

    def test_special_characters_in_urls(self):
        """Test URLs with special characters."""
        client = BinanceWebSocketClient(
            ws_url="wss://test.com:9443/stream?param=value",
            streams=["test@stream"],
            nats_url="nats://user:pass@host:4222",
            nats_topic="topic.with.dots",
        )

        assert "?" in client.ws_url
        assert "@" in client.nats_url
        assert "." in client.nats_topic


@pytest.mark.unit
class TestClientCounterOperations:
    """Test counter increment/reset operations."""

    def test_processed_messages_increment(self):
        """Test processed_messages can increment."""
        client = BinanceWebSocketClient(
            ws_url="wss://test.com",
            streams=["test@stream"],
            nats_url="nats://localhost:4222",
            nats_topic="test.topic",
        )

        assert client.processed_messages == 0

        client.processed_messages += 1
        assert client.processed_messages == 1

        client.processed_messages += 99
        assert client.processed_messages == 100

    def test_dropped_messages_increment(self):
        """Test dropped_messages can increment."""
        client = BinanceWebSocketClient(
            ws_url="wss://test.com",
            streams=["test@stream"],
            nats_url="nats://localhost:4222",
            nats_topic="test.topic",
        )

        assert client.dropped_messages == 0

        client.dropped_messages += 5
        assert client.dropped_messages == 5

    def test_reconnect_attempts_increment(self):
        """Test reconnect_attempts can increment."""
        client = BinanceWebSocketClient(
            ws_url="wss://test.com",
            streams=["test@stream"],
            nats_url="nats://localhost:4222",
            nats_topic="test.topic",
        )

        assert client.reconnect_attempts == 0

        client.reconnect_attempts += 1
        assert client.reconnect_attempts == 1

        client.reconnect_attempts += 2
        assert client.reconnect_attempts == 3


@pytest.mark.unit
class TestClientFlagOperations:
    """Test boolean flag operations."""

    def test_is_connected_can_be_set(self):
        """Test is_connected flag can be toggled."""
        client = BinanceWebSocketClient(
            ws_url="wss://test.com",
            streams=["test@stream"],
            nats_url="nats://localhost:4222",
            nats_topic="test.topic",
        )

        assert client.is_connected is False

        client.is_connected = True
        assert client.is_connected is True

        client.is_connected = False
        assert client.is_connected is False

    def test_is_running_can_be_set(self):
        """Test is_running flag can be toggled."""
        client = BinanceWebSocketClient(
            ws_url="wss://test.com",
            streams=["test@stream"],
            nats_url="nats://localhost:4222",
            nats_topic="test.topic",
        )

        assert client.is_running is False

        client.is_running = True
        assert client.is_running is True

        client.is_running = False
        assert client.is_running is False


@pytest.mark.unit
class TestClientTimestampOperations:
    """Test timestamp attribute operations."""

    def test_last_ping_can_be_updated(self):
        """Test last_ping timestamp can be updated."""
        import time

        client = BinanceWebSocketClient(
            ws_url="wss://test.com",
            streams=["test@stream"],
            nats_url="nats://localhost:4222",
            nats_topic="test.topic",
        )

        assert client.last_ping == 0.0

        now = time.time()
        client.last_ping = now

        assert client.last_ping == now
        assert client.last_ping > 0

    def test_last_message_time_can_be_updated(self):
        """Test last_message_time can be updated."""
        import time

        client = BinanceWebSocketClient(
            ws_url="wss://test.com",
            streams=["test@stream"],
            nats_url="nats://localhost:4222",
            nats_topic="test.topic",
        )

        assert client.last_message_time == 0.0

        now = time.time()
        client.last_message_time = now

        assert client.last_message_time == now

    def test_start_time_is_current_time(self):
        """Test start_time is set to current time."""
        import time

        before = time.time()

        client = BinanceWebSocketClient(
            ws_url="wss://test.com",
            streams=["test@stream"],
            nats_url="nats://localhost:4222",
            nats_topic="test.topic",
        )

        after = time.time()

        assert before <= client.start_time <= after


@pytest.mark.unit
class TestClientNoneChecks:
    """Test None value handling."""

    def test_logger_none_uses_default(self):
        """Test None logger uses default."""
        client = BinanceWebSocketClient(
            ws_url="wss://test.com",
            streams=["test@stream"],
            nats_url="nats://localhost:4222",
            nats_topic="test.topic",
            logger=None,
        )

        # Should create default logger
        assert client.logger is not None

    def test_max_reconnect_none_uses_default(self):
        """Test None max_reconnect_attempts uses default from constants."""
        client = BinanceWebSocketClient(
            ws_url="wss://test.com",
            streams=["test@stream"],
            nats_url="nats://localhost:4222",
            nats_topic="test.topic",
            max_reconnect_attempts=None,
        )

        # Should use constant value
        assert client.max_reconnect_attempts > 0

    def test_reconnect_delay_none_uses_default(self):
        """Test None reconnect_delay uses default."""
        client = BinanceWebSocketClient(
            ws_url="wss://test.com",
            streams=["test@stream"],
            nats_url="nats://localhost:4222",
            nats_topic="test.topic",
            reconnect_delay=None,
        )

        assert client.reconnect_delay > 0

    def test_ping_interval_none_uses_default(self):
        """Test None ping_interval uses default."""
        client = BinanceWebSocketClient(
            ws_url="wss://test.com",
            streams=["test@stream"],
            nats_url="nats://localhost:4222",
            nats_topic="test.topic",
            ping_interval=None,
        )

        assert client.ping_interval > 0

    def test_ping_timeout_none_uses_default(self):
        """Test None ping_timeout uses default."""
        client = BinanceWebSocketClient(
            ws_url="wss://test.com",
            streams=["test@stream"],
            nats_url="nats://localhost:4222",
            nats_topic="test.topic",
            ping_timeout=None,
        )

        assert client.ping_timeout > 0
