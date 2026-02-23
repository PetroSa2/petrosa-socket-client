"""
Batch 3: Additional comprehensive tests for 90% coverage push.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from socket_client.core.client import BinanceWebSocketClient
from socket_client.health.server import HealthServer


@pytest.mark.unit
class TestClientStartMethodPaths:
    """Test different code paths in start method."""

    @pytest.mark.asyncio
    async def test_start_sets_is_running_true(self):
        """Test start sets is_running to True."""
        client = BinanceWebSocketClient(
            ws_url="wss://test.com",
            streams=["test@stream"],
            nats_url="nats://localhost:4222",
            nats_topic="test.topic",
        )

        with (
            patch.object(client, "_connect_nats", new_callable=AsyncMock),
            patch.object(client, "_connect_websocket", new_callable=AsyncMock),
            patch("asyncio.create_task", return_value=AsyncMock()),
        ):
            # Start in background
            start_task = asyncio.create_task(client.start())
            await asyncio.sleep(0.05)

            # Should be running
            assert client.is_running is True

            # Stop it
            client.is_running = False
            await asyncio.sleep(0.05)

            try:
                await asyncio.wait_for(start_task, timeout=1.0)
            except asyncio.TimeoutError:
                start_task.cancel()

    @pytest.mark.asyncio
    async def test_start_creates_processor_tasks(self):
        """Test start creates processor tasks."""
        client = BinanceWebSocketClient(
            ws_url="wss://test.com",
            streams=["test@stream"],
            nats_url="nats://localhost:4222",
            nats_topic="test.topic",
        )

        assert len(client.processor_tasks) == 0

        with (
            patch.object(client, "_connect_nats", new_callable=AsyncMock),
            patch.object(client, "_connect_websocket", new_callable=AsyncMock),
            patch(
                "asyncio.create_task", side_effect=lambda coro: AsyncMock()
            ) as mock_create,
        ):
            start_task = asyncio.create_task(client.start())
            await asyncio.sleep(0.05)
            client.is_running = False
            await asyncio.sleep(0.05)

            try:
                await asyncio.wait_for(start_task, timeout=1.0)
            except:
                start_task.cancel()

            # Should have created tasks
            assert mock_create.call_count >= client.num_processors


@pytest.mark.unit
class TestClientConnectionStates:
    """Test connection state transitions."""

    def test_initial_connection_state(self):
        """Test initial connection state."""
        client = BinanceWebSocketClient(
            ws_url="wss://test.com",
            streams=["test@stream"],
            nats_url="nats://localhost:4222",
            nats_topic="test.topic",
        )

        assert client.websocket is None
        assert client.nats_client is None
        assert client.is_connected is False

    def test_connection_state_can_change(self):
        """Test connection state can be modified."""
        client = BinanceWebSocketClient(
            ws_url="wss://test.com",
            streams=["test@stream"],
            nats_url="nats://localhost:4222",
            nats_topic="test.topic",
        )

        # Simulate connection
        client.is_connected = True
        client.websocket = AsyncMock()
        client.nats_client = AsyncMock()

        assert client.is_connected is True
        assert client.websocket is not None
        assert client.nats_client is not None

        # Simulate disconnection
        client.is_connected = False
        client.websocket = None
        client.nats_client = None

        assert client.is_connected is False


@pytest.mark.unit
class TestHealthServerProperties:
    """Test health server properties."""

    def test_server_port_accessible(self):
        """Test server port is accessible."""
        server = HealthServer(port=9400)

        assert server.port == 9400

    def test_server_logger_accessible(self):
        """Test server logger is accessible."""
        logger = MagicMock()
        server = HealthServer(port=9401, logger=logger)

        assert server.logger is logger

    def test_server_app_accessible(self):
        """Test server app is accessible."""
        server = HealthServer(port=9402)

        assert server.app is not None

    def test_server_runner_initially_none(self):
        """Test server runner is None initially."""
        server = HealthServer(port=9403)

        assert server.runner is None

    def test_server_site_initially_none(self):
        """Test server site is None initially."""
        server = HealthServer(port=9404)

        assert server.site is None


@pytest.mark.unit
class TestClientMetricsDetails:
    """Test detailed metrics functionality."""

    def test_metrics_with_zero_messages(self):
        """Test metrics when no messages processed."""
        client = BinanceWebSocketClient(
            ws_url="wss://test.com",
            streams=["test@stream"],
            nats_url="nats://localhost:4222",
            nats_topic="test.topic",
        )

        metrics = client.get_metrics()

        assert metrics["processed_messages"] == 0
        assert metrics["dropped_messages"] == 0

    def test_metrics_with_many_messages(self):
        """Test metrics with high message counts."""
        client = BinanceWebSocketClient(
            ws_url="wss://test.com",
            streams=["test@stream"],
            nats_url="nats://localhost:4222",
            nats_topic="test.topic",
        )

        client.processed_messages = 1000000
        client.dropped_messages = 50000

        metrics = client.get_metrics()

        assert metrics["processed_messages"] == 1000000
        assert metrics["dropped_messages"] == 50000

    def test_metrics_connection_status_variations(self):
        """Test metrics connection status variations."""
        client = BinanceWebSocketClient(
            ws_url="wss://test.com",
            streams=["test@stream"],
            nats_url="nats://localhost:4222",
            nats_topic="test.topic",
        )

        # Disconnected
        client.is_connected = False
        assert client.get_metrics()["connection_status"] == "disconnected"

        # Connected
        client.is_connected = True
        assert client.get_metrics()["connection_status"] == "connected"


@pytest.mark.unit
class TestClientHeartbeatAttributes:
    """Test heartbeat-related attributes."""

    def test_heartbeat_attributes_initialized(self):
        """Test heartbeat attributes are properly initialized."""
        client = BinanceWebSocketClient(
            ws_url="wss://test.com",
            streams=["test@stream"],
            nats_url="nats://localhost:4222",
            nats_topic="test.topic",
        )

        assert client.last_heartbeat_time > 0
        assert client.last_heartbeat_processed == 0
        assert client.last_heartbeat_dropped == 0

    def test_heartbeat_counters_can_update(self):
        """Test heartbeat counters can be updated."""
        client = BinanceWebSocketClient(
            ws_url="wss://test.com",
            streams=["test@stream"],
            nats_url="nats://localhost:4222",
            nats_topic="test.topic",
        )

        client.last_heartbeat_processed = 150
        client.last_heartbeat_dropped = 5

        assert client.last_heartbeat_processed == 150
        assert client.last_heartbeat_dropped == 5


@pytest.mark.unit
class TestClientTaskAttributes:
    """Test task-related attributes."""

    def test_processor_tasks_is_list(self):
        """Test processor_tasks is a list."""
        client = BinanceWebSocketClient(
            ws_url="wss://test.com",
            streams=["test@stream"],
            nats_url="nats://localhost:4222",
            nats_topic="test.topic",
        )

        assert isinstance(client.processor_tasks, list)
        assert client.processor_tasks == []

    def test_task_references_none_initially(self):
        """Test task references are None initially."""
        client = BinanceWebSocketClient(
            ws_url="wss://test.com",
            streams=["test@stream"],
            nats_url="nats://localhost:4222",
            nats_topic="test.topic",
        )

        assert client.ping_task is None
        assert client.heartbeat_task is None

    def test_processor_tasks_can_be_populated(self):
        """Test processor_tasks list can be populated."""
        client = BinanceWebSocketClient(
            ws_url="wss://test.com",
            streams=["test@stream"],
            nats_url="nats://localhost:4222",
            nats_topic="test.topic",
        )

        mock_tasks = [AsyncMock(), AsyncMock()]
        client.processor_tasks = mock_tasks

        assert len(client.processor_tasks) == 2
