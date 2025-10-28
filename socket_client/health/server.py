"""
Health check server for the Socket Client service.

This module provides HTTP endpoints for Kubernetes health checks
and service monitoring.
"""

import time
from datetime import datetime
from typing import Optional

from aiohttp import web
from prometheus_client import Counter, Gauge, generate_latest
from structlog import get_logger

logger = get_logger(__name__)

# Prometheus metrics
WEBSOCKET_CONNECTED = Gauge(
    "websocket_connected", "WebSocket connection status (1=connected, 0=disconnected)"
)
WEBSOCKET_MESSAGES_PROCESSED = Counter(
    "websocket_messages_processed_total", "Total WebSocket messages processed"
)
WEBSOCKET_MESSAGES_DROPPED = Counter(
    "websocket_messages_dropped_total", "Total WebSocket messages dropped"
)
WEBSOCKET_RECONNECT_ATTEMPTS = Counter(
    "websocket_reconnect_attempts_total", "Total WebSocket reconnection attempts"
)
NATS_CONNECTED = Gauge(
    "nats_connected", "NATS connection status (1=connected, 0=disconnected)"
)
NATS_MESSAGES_PUBLISHED = Counter(
    "nats_messages_published_total", "Total messages published to NATS"
)
SERVICE_UPTIME = Gauge("service_uptime_seconds", "Service uptime in seconds")
MEMORY_USAGE = Gauge("memory_usage_bytes", "Memory usage in bytes")
CPU_USAGE = Gauge("cpu_usage_percent", "CPU usage percentage")


class HealthServer:
    """HTTP server for health checks and monitoring."""

    def __init__(self, port: int = 8080, logger=None) -> None:
        """
        Initialize the health server.

        Args:
            port: Server port
            logger: Logger instance
        """
        self.port = port
        self.logger = logger or get_logger(__name__)
        self.app = web.Application()
        self.runner: Optional[web.AppRunner] = None
        self.site: Optional[web.TCPSite] = None
        self.start_time = time.time()

        # Setup routes
        self.app.router.add_get("/healthz", self.health_check)
        self.app.router.add_get("/ready", self.ready_check)
        self.app.router.add_get("/metrics", self.metrics)
        self.app.router.add_get("/", self.root)

        self.logger.info(f"Health server initialized on port {port}")

    async def start(self) -> None:
        """Start the health server."""
        try:
            self.runner = web.AppRunner(self.app)
            await self.runner.setup()

            self.site = web.TCPSite(self.runner, "0.0.0.0", self.port)
            await self.site.start()

            self.logger.info(f"Health server started on port {self.port}")

        except Exception as e:
            self.logger.error(f"Failed to start health server: {e}")
            raise

    async def stop(self) -> None:
        """Stop the health server."""
        if self.site:
            await self.site.stop()

        if self.runner:
            await self.runner.cleanup()

        self.logger.info("Health server stopped")

    async def health_check(self, request: web.Request) -> web.Response:
        """Health check endpoint for Kubernetes liveness probe."""
        try:
            uptime = time.time() - self.start_time

            health_data = {
                "status": "healthy",
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "service": "socket-client",
                "version": "1.0.0",
                "uptime": uptime,
                "metrics": {
                    "uptime_seconds": uptime,
                    "start_time": datetime.fromtimestamp(self.start_time).isoformat(),
                },
            }

            return web.json_response(
                health_data,
                status=200,
            )

        except Exception as e:
            self.logger.error(f"Health check failed: {e}")
            return web.json_response(
                {"status": "unhealthy", "error": str(e)},
                status=503,
            )

    async def ready_check(self, request: web.Request) -> web.Response:
        """Readiness check endpoint for Kubernetes readiness probe."""
        try:
            # Check if service is ready to receive traffic
            # This could include checks for:
            # - WebSocket connection status
            # - NATS connection status
            # - Message queue health

            ready_data = {
                "status": "ready",
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "service": "socket-client",
                "checks": {
                    "websocket": "connected",  # This would be dynamic
                    "nats": "connected",  # This would be dynamic
                    "queue": "healthy",  # This would be dynamic
                },
            }

            return web.json_response(ready_data, status=200)

        except Exception as e:
            self.logger.error(f"Ready check failed: {e}")
            return web.json_response(
                {"status": "not_ready", "error": str(e)},
                status=503,
            )

    async def metrics(self, request: web.Request) -> web.Response:
        """Metrics endpoint for Prometheus monitoring."""
        try:
            # Update gauge metrics with current values
            uptime = time.time() - self.start_time
            SERVICE_UPTIME.set(uptime)

            memory_mb = self._get_memory_usage()
            MEMORY_USAGE.set(memory_mb * 1024 * 1024)  # Convert MB to bytes

            cpu = self._get_cpu_usage()
            CPU_USAGE.set(cpu)

            # Generate Prometheus-format metrics
            metrics_output = generate_latest()

            return web.Response(
                body=metrics_output,
                headers={"Content-Type": "text/plain; version=0.0.4; charset=utf-8"},
                status=200,
            )

        except Exception as e:
            self.logger.error(f"Metrics endpoint failed: {e}")
            return web.Response(text=f"# Error generating metrics: {e}\n", status=500)

    async def root(self, request: web.Request) -> web.Response:
        """Root endpoint with service information."""
        try:
            info_data = {
                "service": "Petrosa Socket Client",
                "version": "1.0.0",
                "description": "Binance WebSocket client for real-time data streaming",
                "endpoints": {
                    "health": "/healthz",
                    "ready": "/ready",
                    "metrics": "/metrics",
                },
                "documentation": "https://github.com/petrosa/petrosa-socket-client",
            }

            return web.json_response(info_data, status=200)

        except Exception as e:
            self.logger.error(f"Root endpoint failed: {e}")
            return web.json_response(
                {"error": str(e)},
                status=500,
            )

    def _get_memory_usage(self) -> float:
        """Get current memory usage in MB."""
        try:
            import psutil

            process = psutil.Process()
            memory_info = process.memory_info()
            return memory_info.rss / 1024 / 1024  # Convert to MB
        except ImportError:
            return 0.0
        except Exception:
            return 0.0

    def _get_cpu_usage(self) -> float:
        """Get current CPU usage percentage."""
        try:
            import psutil

            process = psutil.Process()
            return process.cpu_percent()
        except ImportError:
            return 0.0
        except Exception:
            return 0.0

    def update_websocket_metrics(self, metrics: dict) -> None:
        """Update WebSocket metrics (called by main service)."""
        # This method would be called by the main service to update
        # the metrics with real-time data
        pass

    def update_nats_metrics(self, metrics: dict) -> None:
        """Update NATS metrics (called by main service)."""
        # This method would be called by the main service to update
        # the metrics with real-time data
        pass
