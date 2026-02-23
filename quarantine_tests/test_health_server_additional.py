"""
Additional tests for health_server.py to boost coverage.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from socket_client.health.server import HealthServer


@pytest.mark.unit
class TestHealthServerInitialization:
    """Test health server initialization."""

    def test_init_with_defaults(self):
        """Test initialization with default parameters."""
        server = HealthServer(port=8080)
        
        assert server.port == 8080
        assert server.app is not None
        assert server.server is None

    def test_init_with_logger(self):
        """Test initialization with custom logger."""
        mock_logger = MagicMock()
        server = HealthServer(port=8081, logger=mock_logger)
        
        assert server.logger is mock_logger
        assert server.port == 8081


@pytest.mark.unit  
class TestHealthServerEndpoints:
    """Test health server endpoints."""

    @pytest.mark.asyncio
    async def test_health_endpoint_structure(self):
        """Test health endpoint response structure."""
        server = HealthServer(port=8082)
        
        # The _health_check method should return a dict
        response = await server._health_check(None)
        
        assert isinstance(response, dict)
        assert "status" in response
        assert "timestamp" in response

    @pytest.mark.asyncio
    async def test_metrics_endpoint_structure(self):
        """Test metrics endpoint response structure."""
        server = HealthServer(port=8083)
        
        # The _metrics method should return a dict
        response = await server._metrics(None)
        
        assert isinstance(response, dict)
        assert "uptime_seconds" in response


@pytest.mark.unit
class TestHealthServerLifecycle:
    """Test server lifecycle."""

    @pytest.mark.asyncio
    async def test_start_creates_server(self):
        """Test that start creates server instance."""
        server = HealthServer(port=8084)
        
        with patch("aiohttp.web.AppRunner") as mock_runner:
            mock_runner_instance = AsyncMock()
            mock_runner.return_value = mock_runner_instance
            
            # Mock the site
            with patch("aiohttp.web.TCPSite") as mock_site:
                mock_site_instance = AsyncMock()
                mock_site.return_value = mock_site_instance
                
                await server.start()
                
                # Verify runner was created and started
                mock_runner.assert_called_once()
                mock_runner_instance.setup.assert_called_once()

    @pytest.mark.asyncio
    async def test_stop_when_not_started(self):
        """Test stopping server when it hasn't been started."""
        server = HealthServer(port=8085)
        
        # Should handle gracefully
        await server.stop()
        
        assert server.server is None

    @pytest.mark.asyncio
    async def test_stop_cleans_up_runner(self):
        """Test that stop cleans up the runner."""
        server = HealthServer(port=8086)
        server.runner = AsyncMock()
        server.server = MagicMock()
        
        await server.stop()
        
        # Verify cleanup was called
        server.runner.cleanup.assert_called_once()


@pytest.mark.unit
class TestHealthServerConfiguration:
    """Test server configuration."""

    def test_different_ports(self):
        """Test servers can be created on different ports."""
        server1 = HealthServer(port=9001)
        server2 = HealthServer(port=9002)
        
        assert server1.port != server2.port
        assert server1.port == 9001
        assert server2.port == 9002

    def test_app_configuration(self):
        """Test aiohttp app is configured."""
        server = HealthServer(port=9003)
        
        assert server.app is not None
        # Check routes are configured
        assert len(server.app.router.routes()) > 0

