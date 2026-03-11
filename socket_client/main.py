#!/usr/bin/env python3
"""
Main entry point for the Petrosa Socket Client.

This module handles the startup, configuration, and graceful shutdown
of the WebSocket client service.
"""

import asyncio
import os
import signal
import sys
from typing import Any, Optional

from dotenv import load_dotenv

# Load environment variables FIRST
load_dotenv()

import requests
import typer

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

__version__ = "1.1.0"

# Initialize OpenTelemetry as early as possible
try:
    from petrosa_otel import setup_telemetry

    if not os.getenv("OTEL_NO_AUTO_INIT"):
        service_name = os.getenv("OTEL_SERVICE_NAME", "socket-client")
        setup_telemetry(
            service_name=service_name,
            service_type="async",
            auto_attach_logging=True,
        )
except ImportError:
    pass

import constants  # noqa: E402
from socket_client.core.client import BinanceWebSocketClient  # noqa: E402
from socket_client.health.server import HealthServer  # noqa: E402
from socket_client.utils.logger import setup_logging  # noqa: E402

app = typer.Typer(help="Petrosa Socket Client - Binance WebSocket client")


class SocketClientService:
    """Main service class for the Socket Client."""

    def __init__(self) -> None:
        """Initialize the service."""
        # Standard library logging is configured here
        self.logger = setup_logging(level=constants.LOG_LEVEL)

        self.websocket_client: Optional[BinanceWebSocketClient] = None
        self.health_server: Optional[HealthServer] = None
        self.shutdown_event = asyncio.Event()

    async def start(self) -> None:
        """Start the service."""
        self.logger.info("Starting Petrosa Socket Client service")

        try:
            # Start health server
            self.health_server = HealthServer(
                port=constants.HEALTH_CHECK_PORT, logger=self.logger
            )
            await self.health_server.start()
            self.logger.info(
                f"Health server started on port {constants.HEALTH_CHECK_PORT}"
            )

            # Start WebSocket client
            self.websocket_client = BinanceWebSocketClient(
                ws_url=constants.BINANCE_WS_URL,
                streams=constants.get_streams(),
                nats_url=constants.NATS_URL,
                nats_topic=constants.NATS_TOPIC,
                logger=self.logger,
            )
            await self.websocket_client.start()
            self.logger.info("WebSocket client started successfully")

            # Wait for shutdown signal
            await self.shutdown_event.wait()

        except Exception as e:
            self.logger.error(f"Error starting service: {e}")
            raise
        finally:
            await self.stop()

    async def stop(self) -> None:
        """Stop the service."""
        self.logger.info("Stopping Petrosa Socket Client service")

        if self.websocket_client:
            await self.websocket_client.stop()

        if self.health_server:
            await self.health_server.stop()

        self.logger.info("Service stopped gracefully")


def signal_handler(signum, frame):
    """Handle termination signals."""
    print(f"\nReceived signal {signum}, shutting down...")
    if hasattr(signal_handler, "service"):
        signal_handler.service.shutdown_event.set()


@app.command()
def run(
    ws_url: Optional[str] = typer.Option(None, "--ws-url", help="Binance WebSocket URL"),
    nats_url: Optional[str] = typer.Option(None, "--nats-url", help="NATS server URL"),
    nats_topic: Optional[str] = typer.Option(None, "--nats-topic", help="NATS topic"),
):
    """Run the Socket Client service."""
    # Override configuration with CLI options if provided
    if ws_url:
        constants.BINANCE_WS_URL = ws_url
    if nats_url:
        constants.NATS_URL = nats_url
    if nats_topic:
        constants.NATS_TOPIC = nats_topic

    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Create service (this initializes logging)
    service = SocketClientService()

    # Start the service
    try:
        asyncio.run(service.start())
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f"Service failed: {e}")
        sys.exit(1)


@app.command()
def health():
    """Check service health."""
    try:
        response = requests.get(
            f"http://localhost:{constants.HEALTH_CHECK_PORT}/healthz", timeout=5
        )
        if response.status_code == 200:
            print("✅ Service is healthy")
            sys.exit(0)
        else:
            print(f"❌ Service is unhealthy (status: {response.status_code})")
            sys.exit(1)
    except Exception as e:
        print(f"❌ Health check failed: {e}")
        sys.exit(1)


@app.command()
def version():
    """Show version information."""
    print(f"Petrosa Socket Client v{__version__}")


if __name__ == "__main__":
    app()
