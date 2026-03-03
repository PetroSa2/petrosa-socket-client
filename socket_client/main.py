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

# Load environment variables FIRST so they are available for OTEL setup
load_dotenv()

# 1. Setup OpenTelemetry FIRST (before any other imports that might use it)
try:
    from petrosa_otel import attach_logging_handler, setup_telemetry
    # Inverted logic: call setup_telemetry() manually ONLY if auto-init is disabled
    # via OTEL_NO_AUTO_INIT=1. This avoids conflicts with opentelemetry-instrument auto-init.
    if os.getenv("OTEL_NO_AUTO_INIT"):
        service_name = os.getenv("OTEL_SERVICE_NAME", "socket-client")
        setup_telemetry(
            service_name=service_name,
            service_type="async",
            auto_attach_logging=True,
        )
        # Also ensure logging handler is attached for this process
        attach_logging_handler()
except (ImportError, Exception) as e:
    if not isinstance(e, ImportError):
        print(f"⚠️  OpenTelemetry setup failed: {e}")
    setup_telemetry = None
    attach_logging_handler = None

import requests
import typer

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

__version__ = "1.0.0"

import constants  # noqa: E402
from socket_client.core.client import BinanceWebSocketClient  # noqa: E402
from socket_client.health.server import HealthServer  # noqa: E402
from socket_client.utils.logger import setup_logging  # noqa: E402

app = typer.Typer(help="Petrosa Socket Client - Binance WebSocket client")


class SocketClientService:
    """Main service class for the Socket Client."""

    def __init__(self) -> None:
        """Initialize the service."""
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
        """Stop the service gracefully."""
        self.logger.info("Stopping Petrosa Socket Client service")

        # Stop WebSocket client
        if self.websocket_client:
            await self.websocket_client.stop()
            self.logger.info("WebSocket client stopped")

        # Stop health server
        if self.health_server:
            await self.health_server.stop()
            self.logger.info("Health server stopped")

        self.logger.info("Service stopped gracefully")


def signal_handler(signum: int, frame: Any) -> None:
    """Handle shutdown signals."""
    print(f"\nReceived signal {signum}, shutting down gracefully...")
    if hasattr(signal_handler, "service"):
        asyncio.create_task(signal_handler.service.shutdown_event.set())


@app.command()
def run(
    ws_url: Optional[str] = typer.Option(
        None, "--ws-url", help="Binance WebSocket URL"
    ),
    streams: Optional[str] = typer.Option(
        None, "--streams", help="Comma-separated list of streams"
    ),
    nats_url: Optional[str] = typer.Option(None, "--nats-url", help="NATS server URL"),
    nats_topic: Optional[str] = typer.Option(
        None, "--nats-topic", help="NATS topic for publishing"
    ),
    log_level: str = typer.Option(
        constants.LOG_LEVEL, "--log-level", help="Logging level"
    ),
) -> None:
    """Run the Socket Client service."""
    # Override constants with command line arguments
    if ws_url:
        os.environ["BINANCE_WS_URL"] = ws_url
    if streams:
        os.environ["BINANCE_STREAMS"] = streams
    if nats_url:
        os.environ["NATS_URL"] = nats_url
    if nats_topic:
        os.environ["NATS_TOPIC"] = nats_topic
    if log_level:
        os.environ["LOG_LEVEL"] = log_level

    # Set up signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Create and run service
    service = SocketClientService()
    if attach_logging_handler:
        try:
            attach_logging_handler()
        except Exception as e:
            print(f"⚠️  Failed to attach OTLP logging handler: {e}")
    else:
        print("⚠️  petrosa_otel not found, skipping OTLP logging handler.")
    signal_handler.service = service  # type: ignore[attr-defined]

    try:
        asyncio.run(service.start())
    except KeyboardInterrupt:
        print("\nShutdown requested by user")
    except Exception as e:
        print(f"Service failed: {e}")
        sys.exit(1)


@app.command()
def health() -> None:
    """Check service health."""
    import requests

    try:
        response = requests.get(
            f"http://localhost:{constants.HEALTH_CHECK_PORT}/healthz", timeout=5
        )
        if response.status_code == 200:
            print("✅ Service is healthy")
            print(f"Response: {response.json()}")
        else:
            print(f"❌ Service is unhealthy: {response.status_code}")
            sys.exit(1)
    except requests.exceptions.RequestException as e:
        print(f"❌ Health check failed: {e}")
        sys.exit(1)


@app.command()
def version() -> None:
    """Show version information."""
    print(f"Petrosa Socket Client version: {__version__}")


if __name__ == "__main__":
    app()
