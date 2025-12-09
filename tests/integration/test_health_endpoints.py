"""
Integration tests for health server endpoints.
Tests actual HTTP endpoint behavior.
"""

import asyncio
import time
from unittest.mock import MagicMock

import pytest
from aiohttp import web
from aiohttp.test_utils import AioHTTPTestCase, unittest_run_loop

from socket_client.health.server import HealthServer


class TestHealthCheckEndpoint(AioHTTPTestCase):
    """Test health check endpoint."""

    async def get_application(self):
        """Create test application."""
        server = HealthServer(port=8888)
        return server.app

    @unittest_run_loop
    async def test_health_check_returns_200(self):
        """Test health check returns 200 OK."""
        resp = await self.client.request("GET", "/health")
        assert resp.status == 200

        data = await resp.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert "service" in data
        assert data["service"] == "socket-client"

    @unittest_run_loop
    async def test_health_check_includes_uptime(self):
        """Test health check includes uptime metrics."""
        resp = await self.client.request("GET", "/health")
        data = await resp.json()

        assert "uptime" in data
        assert "metrics" in data
        assert "uptime_seconds" in data["metrics"]
        assert "start_time" in data["metrics"]
        assert data["metrics"]["uptime_seconds"] >= 0

    @unittest_run_loop
    async def test_health_check_includes_version(self):
        """Test health check includes version."""
        resp = await self.client.request("GET", "/health")
        data = await resp.json()

        assert "version" in data
        assert data["version"] == "1.0.0"


class TestReadyEndpoint(AioHTTPTestCase):
    """Test ready endpoint."""

    async def get_application(self):
        """Create test application."""
        server = HealthServer(port=8889)
        return server.app

    @unittest_run_loop
    async def test_ready_check_returns_200(self):
        """Test ready check returns 200 OK."""
        resp = await self.client.request("GET", "/ready")
        assert resp.status == 200

        data = await resp.json()
        assert data["status"] == "ready"

    @unittest_run_loop
    async def test_ready_check_includes_timestamp(self):
        """Test ready check includes timestamp."""
        resp = await self.client.request("GET", "/ready")
        data = await resp.json()

        assert "timestamp" in data
        # Timestamp should be ISO format
        assert "T" in data["timestamp"]
        assert "Z" in data["timestamp"]


class TestMetricsEndpoint(AioHTTPTestCase):
    """Test metrics endpoint."""

    async def get_application(self):
        """Create test application."""
        server = HealthServer(port=8890)
        return server.app

    @unittest_run_loop
    async def test_metrics_returns_200(self):
        """Test metrics endpoint returns 200 OK."""
        resp = await self.client.request("GET", "/metrics")
        assert resp.status == 200

        data = await resp.json()
        assert isinstance(data, dict)

    @unittest_run_loop
    async def test_metrics_includes_uptime(self):
        """Test metrics includes uptime."""
        resp = await self.client.request("GET", "/metrics")
        data = await resp.json()

        assert "uptime_seconds" in data
        assert data["uptime_seconds"] >= 0

    @unittest_run_loop
    async def test_metrics_includes_start_time(self):
        """Test metrics includes start time."""
        resp = await self.client.request("GET", "/metrics")
        data = await resp.json()

        assert "start_time" in data
        # Should be ISO format
        assert isinstance(data["start_time"], str)


class TestHealthServerStartStop(AioHTTPTestCase):
    """Test server start/stop lifecycle."""

    async def get_application(self):
        """Create test application."""
        server = HealthServer(port=8891)
        return server.app

    @unittest_run_loop
    async def test_server_starts_successfully(self):
        """Test server starts without errors."""
        # Server is already started by AioHTTPTestCase
        resp = await self.client.request("GET", "/health")
        assert resp.status == 200

    @unittest_run_loop
    async def test_multiple_health_requests(self):
        """Test handling multiple health check requests."""
        responses = []
        
        for _ in range(10):
            resp = await self.client.request("GET", "/health")
            responses.append(resp.status)
        
        # All should succeed
        assert all(status == 200 for status in responses)

    @unittest_run_loop
    async def test_concurrent_health_requests(self):
        """Test concurrent health check requests."""
        tasks = [
            self.client.request("GET", "/health")
            for _ in range(5)
        ]
        
        responses = await asyncio.gather(*tasks)
        
        # All should succeed
        for resp in responses:
            assert resp.status == 200

