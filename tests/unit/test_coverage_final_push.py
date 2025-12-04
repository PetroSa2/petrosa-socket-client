"""
Final comprehensive test push toward 90% coverage.
Extensive tests across all modules.
"""

import asyncio
import json
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from aiohttp import web

from socket_client.core.client import BinanceWebSocketClient
from socket_client.health.server import HealthServer
from socket_client.models.message import WebSocketMessage, validate_message

# =============================================================================
# CLIENT COMPREHENSIVE TESTS
# =============================================================================


@pytest.mark.unit
class TestClientAllAttributes:
    """Test all client attributes are accessible."""

    def test_all_url_attributes(self):
        """Test all URL-related attributes."""
        client = BinanceWebSocketClient(
            ws_url="wss://example.com",
            streams=["test"],
            nats_url="nats://nats.com",
            nats_topic="topic",
        )

        assert hasattr(client, "ws_url")
        assert hasattr(client, "nats_url")
        assert hasattr(client, "nats_topic")
        assert client.ws_url == "wss://example.com"
        assert client.nats_url == "nats://nats.com"
        assert client.nats_topic == "topic"

    def test_all_connection_attributes(self):
        """Test all connection-related attributes."""
        client = BinanceWebSocketClient(
            ws_url="wss://test.com",
            streams=["test"],
            nats_url="nats://localhost:4222",
            nats_topic="topic",
        )

        assert hasattr(client, "websocket")
        assert hasattr(client, "nats_client")
        assert hasattr(client, "is_connected")
        assert hasattr(client, "is_running")

    def test_all_reconnection_attributes(self):
        """Test all reconnection-related attributes."""
        client = BinanceWebSocketClient(
            ws_url="wss://test.com",
            streams=["test"],
            nats_url="nats://localhost:4222",
            nats_topic="topic",
        )

        assert hasattr(client, "max_reconnect_attempts")
        assert hasattr(client, "reconnect_delay")
        assert hasattr(client, "reconnect_attempts")

    def test_all_ping_attributes(self):
        """Test all ping-related attributes."""
        client = BinanceWebSocketClient(
            ws_url="wss://test.com",
            streams=["test"],
            nats_url="nats://localhost:4222",
            nats_topic="topic",
        )

        assert hasattr(client, "ping_interval")
        assert hasattr(client, "ping_timeout")
        assert hasattr(client, "last_ping")

    def test_all_message_attributes(self):
        """Test all message-related attributes."""
        client = BinanceWebSocketClient(
            ws_url="wss://test.com",
            streams=["test"],
            nats_url="nats://localhost:4222",
            nats_topic="topic",
        )

        assert hasattr(client, "message_queue")
        assert hasattr(client, "processed_messages")
        assert hasattr(client, "dropped_messages")
        assert hasattr(client, "last_message_time")

    def test_all_task_attributes(self):
        """Test all task-related attributes."""
        client = BinanceWebSocketClient(
            ws_url="wss://test.com",
            streams=["test"],
            nats_url="nats://localhost:4222",
            nats_topic="topic",
        )

        assert hasattr(client, "processor_tasks")
        assert hasattr(client, "ping_task")
        assert hasattr(client, "heartbeat_task")
        assert hasattr(client, "num_processors")

    def test_all_stats_attributes(self):
        """Test all statistics attributes."""
        client = BinanceWebSocketClient(
            ws_url="wss://test.com",
            streams=["test"],
            nats_url="nats://localhost:4222",
            nats_topic="topic",
        )

        assert hasattr(client, "start_time")
        assert hasattr(client, "last_heartbeat_time")
        assert hasattr(client, "last_heartbeat_processed")
        assert hasattr(client, "last_heartbeat_dropped")
        assert hasattr(client, "stats_log_interval")
        assert hasattr(client, "last_stats_log_time")


# =============================================================================
# HEALTH SERVER COMPREHENSIVE TESTS
# =============================================================================


@pytest.mark.unit
class TestHealthServerAllAttributes:
    """Test all health server attributes."""

    def test_all_core_attributes(self):
        """Test all core attributes."""
        logger = MagicMock()
        server = HealthServer(port=9500, logger=logger)

        assert hasattr(server, "port")
        assert hasattr(server, "logger")
        assert hasattr(server, "app")
        assert hasattr(server, "runner")
        assert hasattr(server, "site")
        assert hasattr(server, "start_time")

    def test_attribute_values(self):
        """Test attribute initial values."""
        logger = MagicMock()
        server = HealthServer(port=9501, logger=logger)

        assert server.port == 9501
        assert server.logger is logger
        assert server.app is not None
        assert server.runner is None
        assert server.site is None
        assert server.start_time > 0


@pytest.mark.unit
class TestHealthServerMethods:
    """Test health server methods."""

    @pytest.mark.asyncio
    async def test_start_method_exists(self):
        """Test start method exists."""
        server = HealthServer(port=9502)

        assert hasattr(server, "start")
        assert callable(server.start)

    @pytest.mark.asyncio
    async def test_stop_method_exists(self):
        """Test stop method exists."""
        server = HealthServer(port=9503)

        assert hasattr(server, "stop")
        assert callable(server.stop)

    @pytest.mark.asyncio
    async def test_health_check_method_callable(self):
        """Test health_check method is callable."""
        server = HealthServer(port=9504)

        assert hasattr(server, "health_check")
        assert callable(server.health_check)

    @pytest.mark.asyncio
    async def test_ready_check_method_callable(self):
        """Test ready_check method is callable."""
        server = HealthServer(port=9505)

        assert hasattr(server, "ready_check")
        assert callable(server.ready_check)

    @pytest.mark.asyncio
    async def test_metrics_method_callable(self):
        """Test metrics method is callable."""
        server = HealthServer(port=9506)

        assert hasattr(server, "metrics")
        assert callable(server.metrics)


# =============================================================================
# MESSAGE MODEL COMPREHENSIVE TESTS
# =============================================================================


@pytest.mark.unit
class TestMessageModelComprehensive:
    """Comprehensive message model tests."""

    def test_message_with_all_fields_set(self):
        """Test message with all fields explicitly set."""
        msg = WebSocketMessage(
            stream="comprehensive@test",
            data={"key1": "value1", "key2": 123, "key3": [1, 2, 3]},
            timestamp=datetime(2025, 6, 15, 10, 30, 45),
            message_id="comprehensive-test-id",
        )

        assert msg.stream == "comprehensive@test"
        assert msg.data["key1"] == "value1"
        assert msg.data["key2"] == 123
        assert msg.timestamp.year == 2025
        assert msg.message_id == "comprehensive-test-id"

    def test_message_to_nats_comprehensive(self):
        """Test comprehensive to_nats_message conversion."""
        msg = WebSocketMessage(
            stream="nats@test",
            data={"price": "100.50"},
            message_id="nats-test-123",
        )

        nats_msg = msg.to_nats_message()

        # All fields present
        assert "stream" in nats_msg
        assert "data" in nats_msg
        assert "timestamp" in nats_msg
        assert "message_id" in nats_msg
        assert "source" in nats_msg
        assert "version" in nats_msg

        # Values correct
        assert nats_msg["stream"] == "nats@test"
        assert nats_msg["message_id"] == "nats-test-123"
        assert nats_msg["source"] == "binance-websocket"
        assert nats_msg["version"] == "1.0"

    def test_message_to_json_comprehensive(self):
        """Test comprehensive to_json conversion."""
        msg = WebSocketMessage(
            stream="json@test",
            data={"nested": {"deep": {"value": "here"}}},
        )

        json_str = msg.to_json()

        # Valid JSON
        parsed = json.loads(json_str)
        assert isinstance(parsed, dict)
        assert parsed["stream"] == "json@test"
        assert parsed["data"]["nested"]["deep"]["value"] == "here"


@pytest.mark.unit
class TestValidateMessageComprehensive:
    """Comprehensive validate_message tests."""

    def test_validate_all_valid_formats(self):
        """Test validating various valid message formats."""
        valid_messages = [
            {"stream": "a", "data": {}},
            {"stream": "b", "data": {"key": "value"}},
            {"stream": "c@trade", "data": {"price": "100"}},
            {"stream": "d@ticker", "data": {"nested": {"data": "value"}}},
        ]

        for msg in valid_messages:
            assert validate_message(msg) is True

    def test_validate_all_invalid_formats(self):
        """Test validating various invalid formats."""
        invalid_messages = [
            {},
            {"stream": "only_stream"},
            {"data": "only_data"},
            None,
            "string",
            123,
            [],
            [{"stream": "a", "data": {}}],
        ]

        for msg in invalid_messages:
            assert validate_message(msg) is False


# =============================================================================
# INTEGRATION-STYLE UNIT TESTS
# =============================================================================


@pytest.mark.unit
class TestClientCompleteLifecycle:
    """Test complete client lifecycle scenarios."""

    @pytest.mark.asyncio
    async def test_client_creation_and_immediate_stop(self):
        """Test creating client and immediately stopping."""
        client = BinanceWebSocketClient(
            ws_url="wss://test.com",
            streams=["test"],
            nats_url="nats://localhost:4222",
            nats_topic="topic",
        )

        await client.stop()

        assert client.is_running is False

    @pytest.mark.asyncio
    async def test_client_multiple_stops(self):
        """Test multiple stop calls."""
        client = BinanceWebSocketClient(
            ws_url="wss://test.com",
            streams=["test"],
            nats_url="nats://localhost:4222",
            nats_topic="topic",
        )

        await client.stop()
        await client.stop()
        await client.stop()

        # Should handle gracefully
        assert client.is_running is False


@pytest.mark.unit
class TestHealthServerCompleteLifecycle:
    """Test complete health server lifecycle."""

    def test_server_creation_and_attributes(self):
        """Test server creation sets all attributes."""
        import time

        before = time.time()

        server = HealthServer(port=9600)

        after = time.time()

        # All attributes set
        assert server.port == 9600
        assert server.app is not None
        assert server.runner is None
        assert server.site is None
        assert before <= server.start_time <= after
        assert server.logger is not None

    @pytest.mark.asyncio
    async def test_server_stop_without_start(self):
        """Test stopping server that was never started."""
        server = HealthServer(port=9601)

        # Should handle gracefully
        await server.stop()

        assert server.runner is None
        assert server.site is None
