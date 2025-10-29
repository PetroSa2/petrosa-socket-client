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


