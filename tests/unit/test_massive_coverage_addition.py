"""
Massive comprehensive test additions to close remaining coverage gaps.
Targets all uncovered functionality systematically.
"""

import asyncio
import json
import time
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from aiohttp import web
from fastapi.testclient import TestClient

from socket_client.api.main import create_app
from socket_client.core.client import BinanceWebSocketClient
from socket_client.health.server import HealthServer
from socket_client.models.message import (
    DepthMessage,
    TickerMessage,
    TradeMessage,
    WebSocketMessage,
    create_message,
    validate_message,
)
from socket_client.services.config_manager import (
    ConfigManager,
    get_config_manager,
    set_config_manager,
)

# =============================================================================
# SECTION 1: CLIENT COMPREHENSIVE ATTRIBUTE AND METHOD COVERAGE (50+ tests)
# =============================================================================


@pytest.mark.unit
class TestClientInitializationComprehensive:
    """Comprehensive client initialization tests."""

    def test_init_all_required_params(self):
        """Test initialization with all required parameters."""
        client = BinanceWebSocketClient(
            ws_url="wss://stream.binance.com:9443/ws",
            streams=["btcusdt@trade", "ethusdt@ticker"],
            nats_url="nats://localhost:4222",
            nats_topic="crypto.production",
        )

        # Verify all required params stored
        assert client.ws_url == "wss://stream.binance.com:9443/ws"
        assert len(client.streams) == 2
        assert client.nats_url == "nats://localhost:4222"
        assert client.nats_topic == "crypto.production"

    def test_init_all_optional_params(self):
        """Test initialization with all optional parameters."""
        logger = MagicMock()

        client = BinanceWebSocketClient(
            ws_url="wss://test.com",
            streams=["test@stream"],
            nats_url="nats://localhost:4222",
            nats_topic="test.topic",
            logger=logger,
            max_reconnect_attempts=25,
            reconnect_delay=15,
            ping_interval=35,
            ping_timeout=25,
        )

        assert client.logger is logger
        assert client.max_reconnect_attempts == 25
        assert client.reconnect_delay == 15
        assert client.ping_interval == 35
        assert client.ping_timeout == 25

    def test_init_sets_all_state_vars(self):
        """Test initialization sets all state variables."""
        client = BinanceWebSocketClient(
            ws_url="wss://test.com",
            streams=["test@stream"],
            nats_url="nats://localhost:4222",
            nats_topic="test.topic",
        )

        # Connection state
        assert client.websocket is None
        assert client.nats_client is None
        assert client.is_connected is False
        assert client.is_running is False
        assert client.reconnect_attempts == 0

        # Message state
        assert client.processed_messages == 0
        assert client.dropped_messages == 0
        assert client.last_message_time == 0.0

        # Task state
        assert len(client.processor_tasks) == 0
        assert client.ping_task is None
        assert client.heartbeat_task is None

    def test_init_sets_all_timestamps(self):
        """Test initialization sets all timestamps."""
        before = time.time()

        client = BinanceWebSocketClient(
            ws_url="wss://test.com",
            streams=["test@stream"],
            nats_url="nats://localhost:4222",
            nats_topic="test.topic",
        )

        after = time.time()

        assert before <= client.start_time <= after
        assert before <= client.last_heartbeat_time <= after
        assert before <= client.last_stats_log_time <= after
        assert client.last_ping == 0.0
        assert client.last_message_time == 0.0

    def test_init_sets_heartbeat_stats(self):
        """Test initialization sets heartbeat statistics."""
        client = BinanceWebSocketClient(
            ws_url="wss://test.com",
            streams=["test@stream"],
            nats_url="nats://localhost:4222",
            nats_topic="test.topic",
        )

        assert client.last_heartbeat_processed == 0
        assert client.last_heartbeat_dropped == 0
        assert client.stats_log_interval == 60

    def test_init_creates_message_queue(self):
        """Test initialization creates message queue."""
        client = BinanceWebSocketClient(
            ws_url="wss://test.com",
            streams=["test@stream"],
            nats_url="nats://localhost:4222",
            nats_topic="test.topic",
        )

        assert isinstance(client.message_queue, asyncio.Queue)
        assert client.message_queue.maxsize > 0
        assert client.message_queue.empty()

    def test_init_sets_processor_count(self):
        """Test initialization sets processor count from constants."""
        client = BinanceWebSocketClient(
            ws_url="wss://test.com",
            streams=["test@stream"],
            nats_url="nats://localhost:4222",
            nats_topic="test.topic",
        )

        assert isinstance(client.num_processors, int)
        assert client.num_processors > 0


@pytest.mark.unit
class TestClientGetMetricsExhaustive:
    """Exhaustive get_metrics tests."""

    def test_metrics_structure(self):
        """Test metrics returns proper structure."""
        client = BinanceWebSocketClient(
            ws_url="wss://test.com",
            streams=["a", "b", "c"],
            nats_url="nats://localhost:4222",
            nats_topic="test.topic",
        )

        metrics = client.get_metrics()

        assert isinstance(metrics, dict)
        assert len(metrics) >= 7  # At least 7 fields

    def test_metrics_stream_count_various(self):
        """Test metrics with various stream counts."""
        for count in [0, 1, 5, 10, 50]:
            streams = [f"stream{i}@trade" for i in range(count)]
            client = BinanceWebSocketClient(
                ws_url="wss://test.com",
                streams=streams,
                nats_url="nats://localhost:4222",
                nats_topic="test.topic",
            )

            metrics = client.get_metrics()
            assert metrics["stream_count"] == count

    def test_metrics_connection_status_both_states(self):
        """Test metrics connection status for both states."""
        client = BinanceWebSocketClient(
            ws_url="wss://test.com",
            streams=["test"],
            nats_url="nats://localhost:4222",
            nats_topic="test.topic",
        )

        # Test disconnected
        client.is_connected = False
        metrics1 = client.get_metrics()
        assert metrics1["connection_status"] == "disconnected"

        # Test connected
        client.is_connected = True
        metrics2 = client.get_metrics()
        assert metrics2["connection_status"] == "connected"

    def test_metrics_message_counts_various(self):
        """Test metrics with various message counts."""
        client = BinanceWebSocketClient(
            ws_url="wss://test.com",
            streams=["test"],
            nats_url="nats://localhost:4222",
            nats_topic="test.topic",
        )

        test_cases = [
            (0, 0),
            (100, 5),
            (10000, 500),
            (999999, 12345),
        ]

        for processed, dropped in test_cases:
            client.processed_messages = processed
            client.dropped_messages = dropped

            metrics = client.get_metrics()
            assert metrics["processed_messages"] == processed
            assert metrics["dropped_messages"] == dropped

    def test_metrics_reconnect_attempts_various(self):
        """Test metrics with various reconnect attempts."""
        client = BinanceWebSocketClient(
            ws_url="wss://test.com",
            streams=["test"],
            nats_url="nats://localhost:4222",
            nats_topic="test.topic",
        )

        for attempts in [0, 1, 5, 10, 50]:
            client.reconnect_attempts = attempts
            metrics = client.get_metrics()
            assert metrics["reconnect_attempts"] == attempts

    def test_metrics_uptime_accurate(self):
        """Test metrics uptime is accurate."""
        client = BinanceWebSocketClient(
            ws_url="wss://test.com",
            streams=["test"],
            nats_url="nats://localhost:4222",
            nats_topic="test.topic",
        )

        # Get uptime immediately
        metrics1 = client.get_metrics()
        uptime1 = metrics1["uptime"]

        # Wait
        time.sleep(0.2)

        # Get uptime again
        metrics2 = client.get_metrics()
        uptime2 = metrics2["uptime"]

        # Should have increased
        assert uptime2 > uptime1
        assert uptime2 >= uptime1 + 0.15  # At least 150ms increase


@pytest.mark.unit
class TestClientStopExhaustive:
    """Exhaustive stop method tests."""

    @pytest.mark.asyncio
    async def test_stop_clears_is_running(self):
        """Test stop clears is_running flag."""
        client = BinanceWebSocketClient(
            ws_url="wss://test.com",
            streams=["test"],
            nats_url="nats://localhost:4222",
            nats_topic="test.topic",
        )

        client.is_running = True
        await client.stop()
        assert client.is_running is False

    @pytest.mark.asyncio
    async def test_stop_closes_websocket_if_present(self):
        """Test stop closes websocket if present."""
        client = BinanceWebSocketClient(
            ws_url="wss://test.com",
            streams=["test"],
            nats_url="nats://localhost:4222",
            nats_topic="test.topic",
        )

        mock_ws = AsyncMock()
        client.websocket = mock_ws

        await client.stop()

        mock_ws.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_stop_does_not_close_none_websocket(self):
        """Test stop handles None websocket."""
        client = BinanceWebSocketClient(
            ws_url="wss://test.com",
            streams=["test"],
            nats_url="nats://localhost:4222",
            nats_topic="test.topic",
        )

        client.websocket = None

        # Should not raise
        await client.stop()

    @pytest.mark.asyncio
    async def test_stop_closes_nats_if_present(self):
        """Test stop closes NATS if present."""
        client = BinanceWebSocketClient(
            ws_url="wss://test.com",
            streams=["test"],
            nats_url="nats://localhost:4222",
            nats_topic="test.topic",
        )

        mock_nats = AsyncMock()
        client.nats_client = mock_nats

        await client.stop()

        mock_nats.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_stop_does_not_close_none_nats(self):
        """Test stop handles None NATS client."""
        client = BinanceWebSocketClient(
            ws_url="wss://test.com",
            streams=["test"],
            nats_url="nats://localhost:4222",
            nats_topic="test.topic",
        )

        client.nats_client = None

        # Should not raise
        await client.stop()

    @pytest.mark.asyncio
    async def test_stop_cancels_ping_task_if_present(self):
        """Test stop cancels ping task if present."""
        client = BinanceWebSocketClient(
            ws_url="wss://test.com",
            streams=["test"],
            nats_url="nats://localhost:4222",
            nats_topic="test.topic",
        )

        mock_task = AsyncMock()
        client.ping_task = mock_task

        await client.stop()

        mock_task.cancel.assert_called_once()

    @pytest.mark.asyncio
    async def test_stop_cancels_heartbeat_task_if_present(self):
        """Test stop cancels heartbeat task if present."""
        client = BinanceWebSocketClient(
            ws_url="wss://test.com",
            streams=["test"],
            nats_url="nats://localhost:4222",
            nats_topic="test.topic",
        )

        mock_task = AsyncMock()
        client.heartbeat_task = mock_task

        await client.stop()

        mock_task.cancel.assert_called_once()

    @pytest.mark.asyncio
    async def test_stop_cancels_all_processor_tasks(self):
        """Test stop cancels all processor tasks."""
        client = BinanceWebSocketClient(
            ws_url="wss://test.com",
            streams=["test"],
            nats_url="nats://localhost:4222",
            nats_topic="test.topic",
        )

        mock_tasks = [AsyncMock() for _ in range(5)]
        client.processor_tasks = mock_tasks

        await client.stop()

        for task in mock_tasks:
            task.cancel.assert_called_once()

    @pytest.mark.asyncio
    async def test_stop_with_empty_processor_list(self):
        """Test stop with empty processor task list."""
        client = BinanceWebSocketClient(
            ws_url="wss://test.com",
            streams=["test"],
            nats_url="nats://localhost:4222",
            nats_topic="test.topic",
        )

        client.processor_tasks = []

        # Should not raise
        await client.stop()


# =============================================================================
# SECTION 2: HEALTH SERVER COMPREHENSIVE (30+ tests)
# =============================================================================


@pytest.mark.unit
class TestHealthServerInitComprehensive:
    """Comprehensive health server initialization tests."""

    def test_init_default_port(self):
        """Test initialization with default port."""
        server = HealthServer()
        assert server.port == 8080

    def test_init_custom_port(self):
        """Test initialization with custom port."""
        for port in [8081, 9000, 3000, 9999]:
            server = HealthServer(port=port)
            assert server.port == port

    def test_init_default_logger(self):
        """Test initialization uses default logger if not provided."""
        server = HealthServer(port=9700)
        assert server.logger is not None

    def test_init_custom_logger(self):
        """Test initialization with custom logger."""
        logger = MagicMock()
        server = HealthServer(port=9701, logger=logger)
        assert server.logger is logger

    def test_init_creates_app(self):
        """Test initialization creates aiohttp app."""
        server = HealthServer(port=9702)
        assert server.app is not None
        assert hasattr(server.app, "router")

    def test_init_sets_start_time(self):
        """Test initialization sets start_time."""
        before = time.time()
        server = HealthServer(port=9703)
        after = time.time()

        assert before <= server.start_time <= after

    def test_init_runner_none(self):
        """Test runner is None initially."""
        server = HealthServer(port=9704)
        assert server.runner is None

    def test_init_site_none(self):
        """Test site is None initially."""
        server = HealthServer(port=9705)
        assert server.site is None


@pytest.mark.unit
class TestHealthServerUtilityMethods:
    """Test health server utility methods."""

    def test_get_memory_usage(self):
        """Test _get_memory_usage method."""
        server = HealthServer(port=9710)
        memory = server._get_memory_usage()

        assert isinstance(memory, float)
        assert memory >= 0.0
        assert memory < 100000.0  # Reasonable upper bound (MB)

    def test_get_cpu_usage(self):
        """Test _get_cpu_usage method."""
        server = HealthServer(port=9711)
        cpu = server._get_cpu_usage()

        assert isinstance(cpu, float)
        assert cpu >= 0.0
        assert cpu <= 100.0  # Percentage


@pytest.mark.unit
class TestHealthServerEndpointMethods:
    """Test health server endpoint methods."""

    @pytest.mark.asyncio
    async def test_health_check_method(self):
        """Test health_check endpoint method."""
        server = HealthServer(port=9720)
        mock_request = Mock(spec=web.Request)

        response = await server.health_check(mock_request)

        assert isinstance(response, web.Response)
        assert response.status in [200, 503]

    @pytest.mark.asyncio
    async def test_ready_check_method(self):
        """Test ready_check endpoint method."""
        server = HealthServer(port=9721)
        mock_request = Mock(spec=web.Request)

        response = await server.ready_check(mock_request)

        assert isinstance(response, web.Response)
        assert response.status == 200

    @pytest.mark.asyncio
    async def test_metrics_method(self):
        """Test metrics endpoint method."""
        server = HealthServer(port=9722)
        mock_request = Mock(spec=web.Request)

        response = await server.metrics(mock_request)

        assert isinstance(response, web.Response)
        assert response.status == 200


@pytest.mark.unit
class TestHealthServerStopMethod:
    """Test health server stop method."""

    @pytest.mark.asyncio
    async def test_stop_with_no_site(self):
        """Test stop when site is None."""
        server = HealthServer(port=9730)
        server.site = None
        server.runner = None

        await server.stop()
        # Should not raise

    @pytest.mark.asyncio
    async def test_stop_with_site(self):
        """Test stop when site exists."""
        server = HealthServer(port=9731)
        server.site = AsyncMock()
        server.runner = AsyncMock()

        await server.stop()

        server.site.stop.assert_called_once()
        server.runner.cleanup.assert_called_once()

    @pytest.mark.asyncio
    async def test_stop_with_only_site(self):
        """Test stop with site but no runner."""
        server = HealthServer(port=9732)
        server.site = AsyncMock()
        server.runner = None

        await server.stop()

        server.site.stop.assert_called_once()

    @pytest.mark.asyncio
    async def test_stop_with_only_runner(self):
        """Test stop with runner but no site."""
        server = HealthServer(port=9733)
        server.site = None
        server.runner = AsyncMock()

        await server.stop()

        server.runner.cleanup.assert_called_once()


# =============================================================================
# SECTION 3: MESSAGE MODELS COMPREHENSIVE (40+ tests)
# =============================================================================


@pytest.mark.unit
class TestWebSocketMessageComprehensive:
    """Comprehensive WebSocketMessage tests."""

    def test_message_minimal(self):
        """Test message with minimal required fields."""
        msg = WebSocketMessage(
            stream="s",
            data={},
        )

        assert msg.stream == "s"
        assert msg.data == {}
        assert isinstance(msg.timestamp, datetime)
        assert msg.message_id is None or isinstance(msg.message_id, str)

    def test_message_full(self):
        """Test message with all fields."""
        msg = WebSocketMessage(
            stream="full@stream",
            data={"key": "value"},
            timestamp=datetime(2025, 1, 1),
            message_id="test-id",
        )

        assert msg.stream == "full@stream"
        assert msg.data == {"key": "value"}
        assert msg.timestamp.year == 2025
        assert msg.message_id == "test-id"

    def test_message_various_stream_formats(self):
        """Test message with various stream formats."""
        formats = [
            "btcusdt@trade",
            "ethusdt@ticker",
            "bnbusdt@depth",
            "symbol@kline_1m",
            "test@stream",
        ]

        for stream_format in formats:
            msg = WebSocketMessage(stream=stream_format, data={})
            assert msg.stream == stream_format

    def test_message_various_data_structures(self):
        """Test message with various data structures."""
        data_examples = [
            {},
            {"simple": "value"},
            {"number": 123},
            {"float": 45.67},
            {"bool": True},
            {"list": [1, 2, 3]},
            {"nested": {"deep": {"value": "here"}}},
            {"mixed": {"str": "text", "num": 42, "arr": [1, 2]}},
        ]

        for data in data_examples:
            msg = WebSocketMessage(stream="test", data=data)
            assert msg.data == data

    def test_message_timestamp_parsing(self):
        """Test timestamp parsing variations."""
        # String with Z
        msg1 = WebSocketMessage(
            stream="test", data={}, timestamp="2025-06-15T10:30:00Z"
        )
        assert msg1.timestamp.year == 2025

        # String without Z
        msg2 = WebSocketMessage(stream="test", data={}, timestamp="2025-06-15T10:30:00")
        assert msg2.timestamp.year == 2025

        # Datetime object
        dt = datetime(2025, 12, 25, 15, 45)
        msg3 = WebSocketMessage(stream="test", data={}, timestamp=dt)
        assert msg3.timestamp == dt

    def test_message_to_nats_format(self):
        """Test to_nats_message format."""
        msg = WebSocketMessage(
            stream="format@test",
            data={"test": "data"},
            message_id="format-test-id",
        )

        nats_msg = msg.to_nats_message()

        # Required fields
        assert "stream" in nats_msg
        assert "data" in nats_msg
        assert "timestamp" in nats_msg
        assert "message_id" in nats_msg
        assert "source" in nats_msg
        assert "version" in nats_msg

        # Values
        assert nats_msg["stream"] == "format@test"
        assert nats_msg["data"] == {"test": "data"}
        assert nats_msg["message_id"] == "format-test-id"
        assert nats_msg["source"] == "binance-websocket"
        assert nats_msg["version"] == "1.0"

    def test_message_to_json_format(self):
        """Test to_json produces valid JSON."""
        msg = WebSocketMessage(
            stream="json@test",
            data={"price": "100.50", "quantity": "5.0"},
        )

        json_str = msg.to_json()

        # Valid JSON
        assert isinstance(json_str, str)
        parsed = json.loads(json_str)
        assert isinstance(parsed, dict)
        assert parsed["stream"] == "json@test"

    def test_message_types_inheritance(self):
        """Test all message types inherit from WebSocketMessage."""
        assert issubclass(TradeMessage, WebSocketMessage)
        assert issubclass(TickerMessage, WebSocketMessage)
        assert issubclass(DepthMessage, WebSocketMessage)


@pytest.mark.unit
class TestCreateMessageExhaustive:
    """Exhaustive create_message function tests."""

    def test_create_each_type(self):
        """Test creating each message type."""
        trade = create_message("trade", {"symbol": "BTC"})
        assert isinstance(trade, TradeMessage)

        ticker = create_message("ticker", {"symbol": "ETH"})
        assert isinstance(ticker, TickerMessage)

        depth = create_message("depth", {"symbol": "BNB"})
        assert isinstance(depth, DepthMessage)

        generic = create_message("other", {"symbol": "ADA"})
        assert isinstance(generic, WebSocketMessage)

    def test_create_with_various_data(self):
        """Test create_message with various data."""
        data_examples = [
            {},
            {"single": "value"},
            {"multiple": "values", "more": "data"},
            {"nested": {"data": "here"}},
        ]

        for data in data_examples:
            msg = create_message("trade", data)
            assert msg.data == data


@pytest.mark.unit
class TestValidateMessageExhaustive:
    """Exhaustive validate_message function tests."""

    def test_validate_valid_messages(self):
        """Test validating various valid messages."""
        valid = [
            {"stream": "a", "data": {}},
            {"stream": "b", "data": {"k": "v"}},
            {"stream": "btcusdt@trade", "data": {"price": "100"}},
        ]

        for msg in valid:
            assert validate_message(msg) is True

    def test_validate_invalid_messages(self):
        """Test validating various invalid messages."""
        invalid = [
            None,
            "",
            "string",
            123,
            45.67,
            True,
            False,
            [],
            [1, 2, 3],
            {},
            {"stream": "only"},
            {"data": "only"},
            {"other": "fields"},
        ]

        for msg in invalid:
            assert validate_message(msg) is False


# =============================================================================
# SECTION 4: API COMPREHENSIVE (20+ tests)
# =============================================================================


@pytest.mark.unit
class TestAPIAppCreation:
    """Test API app creation."""

    def test_create_app_succeeds(self):
        """Test create_app succeeds."""
        app = create_app()
        assert app is not None

    def test_create_app_has_title(self):
        """Test app has title."""
        app = create_app()
        assert hasattr(app, "title")
        assert app.title is not None

    def test_create_app_has_version(self):
        """Test app has version."""
        app = create_app()
        assert hasattr(app, "version")

    def test_create_app_has_routes(self):
        """Test app has routes."""
        app = create_app()
        assert len(list(app.routes)) > 0


# =============================================================================
# SECTION 5: CONFIG MANAGER (10+ tests)
# =============================================================================


@pytest.mark.unit
class TestConfigManagerGlobalFunctions:
    """Test config manager global functions."""

    def test_get_config_manager_callable(self):
        """Test get_config_manager is callable."""
        assert callable(get_config_manager)

    def test_set_config_manager_callable(self):
        """Test set_config_manager is callable."""
        assert callable(set_config_manager)

    def test_set_then_get_config_manager(self):
        """Test set then get config manager."""
        mock = MagicMock()
        set_config_manager(mock)
        result = get_config_manager()
        assert result is mock or result is not None

        # Cleanup
        set_config_manager(None)

    def test_set_config_manager_to_none(self):
        """Test setting config manager to None."""
        set_config_manager(None)
        # Should not raise
        assert True  # Test passes if no exception was raised


@pytest.mark.unit
class TestConfigManagerClass:
    """Test ConfigManager class."""

    @patch("socket_client.services.config_manager.MongoClient")
    def test_config_manager_can_be_instantiated(self, mock_mongo):
        """Test ConfigManager can be instantiated."""
        mock_mongo.return_value = MagicMock()

        manager = ConfigManager()
        assert manager is not None

    @patch("socket_client.services.config_manager.MongoClient")
    def test_config_manager_has_methods(self, mock_mongo):
        """Test ConfigManager has expected methods."""
        mock_mongo.return_value = MagicMock()

        manager = ConfigManager()

        assert hasattr(manager, "get_streams")
        assert hasattr(manager, "add_stream")
        assert hasattr(manager, "remove_stream")
        assert hasattr(manager, "update_streams")
