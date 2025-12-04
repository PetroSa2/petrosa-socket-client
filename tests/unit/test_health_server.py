"""Tests for the health server module."""

import pytest

from socket_client.health.server import HealthServer
from socket_client.utils.logger import get_logger


def test_health_server_init_default() -> None:
    """Test HealthServer initialization with defaults."""
    server = HealthServer()
    assert server.port == 8080
    assert server.logger is not None


def test_health_server_init_with_port() -> None:
    """Test HealthServer initialization with custom port."""
    server = HealthServer(port=9090)
    assert server.port == 9090


def test_health_server_init_with_logger() -> None:
    """Test HealthServer initialization with custom logger."""
    custom_logger = get_logger("test_health")
    server = HealthServer(logger=custom_logger)
    assert server.logger is custom_logger


def test_health_server_get_memory_usage() -> None:
    """Test _get_memory_usage method."""
    server = HealthServer()
    memory_usage = server._get_memory_usage()
    assert isinstance(memory_usage, float)
    assert memory_usage >= 0.0


def test_health_server_get_cpu_usage() -> None:
    """Test _get_cpu_usage method."""
    server = HealthServer()
    cpu_usage = server._get_cpu_usage()
    assert isinstance(cpu_usage, float)
    assert cpu_usage >= 0.0


def test_health_server_init_with_all_params() -> None:
    """Test HealthServer with all parameters specified."""
    custom_logger = get_logger("custom")
    server = HealthServer(port=8888, logger=custom_logger)
    assert server.port == 8888
    assert server.logger is custom_logger
    assert hasattr(server, "start_time")


def test_health_server_has_app() -> None:
    """Test HealthServer creates aiohttp app."""
    server = HealthServer()
    assert server.app is not None
    assert hasattr(server.app, "router")


def test_health_server_start_time_set() -> None:
    """Test HealthServer sets start_time on init."""
    import time

    before = time.time()
    server = HealthServer()
    after = time.time()

    assert before <= server.start_time <= after


def test_health_server_runner_none_initially() -> None:
    """Test runner is None before start."""
    server = HealthServer()
    assert server.runner is None


def test_health_server_site_none_initially() -> None:
    """Test site is None before start."""
    server = HealthServer()
    assert server.site is None


@pytest.mark.asyncio
async def test_health_server_stop_with_runner() -> None:
    """Test stop with active runner."""
    from unittest.mock import AsyncMock, MagicMock

    server = HealthServer()
    server.runner = AsyncMock()
    server.site = AsyncMock()

    await server.stop()

    server.site.stop.assert_called_once()
    server.runner.cleanup.assert_called_once()


@pytest.mark.asyncio
async def test_health_server_stop_without_runner() -> None:
    """Test stop without runner."""
    server = HealthServer()
    server.runner = None
    server.site = None

    # Should not raise exception
    await server.stop()


def test_health_server_routes_configured() -> None:
    """Test routes are configured."""
    server = HealthServer()
    routes = list(server.app.router.routes())

    assert len(routes) > 0

    # Check for expected endpoints
    paths = [
        route.resource.canonical
        for route in routes
        if hasattr(route.resource, "canonical")
    ]
    assert "/health" in paths or any("/health" in str(r) for r in routes)
    assert "/ready" in paths or any("/ready" in str(r) for r in routes)
    assert "/metrics" in paths or any("/metrics" in str(r) for r in routes)


def test_health_server_different_ports() -> None:
    """Test multiple servers with different ports."""
    server1 = HealthServer(port=9001)
    server2 = HealthServer(port=9002)
    server3 = HealthServer(port=9003)

    assert server1.port == 9001
    assert server2.port == 9002
    assert server3.port == 9003
    assert server1.port != server2.port
