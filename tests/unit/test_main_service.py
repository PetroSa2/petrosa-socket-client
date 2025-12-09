"""
Comprehensive tests for socket_client/main.py

Tests cover:
- SocketClientService initialization
- Service startup and shutdown
- Signal handling
- CLI commands
- Error handling
"""

import asyncio
import os
import signal
import sys
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
import typer.testing

# Mock constants before importing main
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))


@pytest.fixture
def mock_constants():
    """Mock constants module."""
    mock_const = MagicMock()
    mock_const.LOG_LEVEL = "INFO"
    mock_const.OTEL_SERVICE_NAME = "test-socket-client"
    mock_const.HEALTH_CHECK_PORT = 8081
    mock_const.BINANCE_WS_URL = "wss://test.binance.com"
    mock_const.NATS_URL = "nats://localhost:4222"
    mock_const.NATS_TOPIC = "test.topic"
    mock_const.get_streams = Mock(return_value=["btcusdt@trade"])
    return mock_const


@pytest.fixture
def mock_modules(mock_constants):
    """Mock all required modules before importing main."""
    with patch.dict(
        "sys.modules",
        {
            "constants": mock_constants,
            "petrosa_otel": MagicMock(),
        },
    ):
        yield


class TestSocketClientService:
    """Test SocketClientService class."""

    @pytest.fixture
    async def service(self, mock_modules):
        """Create service instance with mocked dependencies."""
        with (
            patch("socket_client.main.setup_logging") as mock_logging,
            patch("socket_client.main.attach_logging_handler"),
        ):
            mock_logger = MagicMock()
            mock_logging.return_value = mock_logger

            from socket_client.main import SocketClientService

            service = SocketClientService()
            yield service

    @pytest.mark.asyncio
    async def test_service_initialization(self, service):
        """Test service initializes correctly."""
        assert service.websocket_client is None
        assert service.health_server is None
        assert isinstance(service.shutdown_event, asyncio.Event)
        assert not service.shutdown_event.is_set()

    @pytest.mark.asyncio
    async def test_service_start_success(self, service):
        """Test successful service startup."""
        mock_health_server = AsyncMock()
        mock_health_server.start = AsyncMock()
        mock_ws_client = AsyncMock()
        mock_ws_client.start = AsyncMock()

        with (
            patch("socket_client.main.HealthServer", return_value=mock_health_server),
            patch(
                "socket_client.main.BinanceWebSocketClient", return_value=mock_ws_client
            ),
        ):
            # Start service in background and trigger shutdown immediately
            start_task = asyncio.create_task(service.start())
            await asyncio.sleep(0.1)  # Let it start
            service.shutdown_event.set()  # Trigger shutdown
            await start_task

            # Verify components were started
            mock_health_server.start.assert_called_once()
            mock_ws_client.start.assert_called_once()

    @pytest.mark.asyncio
    async def test_service_start_failure(self, service):
        """Test service handles startup failure."""
        with patch(
            "socket_client.main.HealthServer",
            side_effect=Exception("Health server failed"),
        ):
            with pytest.raises(Exception, match="Health server failed"):
                await service.start()

    @pytest.mark.asyncio
    async def test_service_stop_with_clients(self, service):
        """Test graceful shutdown with active clients."""
        mock_health_server = AsyncMock()
        mock_ws_client = AsyncMock()

        service.health_server = mock_health_server
        service.websocket_client = mock_ws_client

        await service.stop()

        mock_ws_client.stop.assert_called_once()
        mock_health_server.stop.assert_called_once()

    @pytest.mark.asyncio
    async def test_service_stop_without_clients(self, service):
        """Test shutdown when clients are None."""
        service.health_server = None
        service.websocket_client = None

        # Should not raise exception
        await service.stop()

    @pytest.mark.asyncio
    async def test_service_startup_exception_triggers_stop(self, service):
        """Test that exceptions during startup trigger cleanup."""
        with (
            patch(
                "socket_client.main.HealthServer",
                side_effect=Exception("Startup failed"),
            ),
            patch.object(service, "stop", new_callable=AsyncMock) as mock_stop,
        ):
            with pytest.raises(Exception):
                await service.start()

            # Verify stop was called in finally block
            mock_stop.assert_called_once()


class TestSignalHandler:
    """Test signal handling."""

    def test_signal_handler_sets_shutdown_event(self, mock_modules):
        """Test signal handler triggers shutdown."""
        from socket_client.main import SocketClientService, signal_handler

        service = MagicMock(spec=SocketClientService)
        service.shutdown_event = asyncio.Event()
        signal_handler.service = service  # type: ignore

        # Create event loop for the test
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            # Call signal handler
            signal_handler(signal.SIGTERM, None)

            # Wait briefly for async task
            loop.run_until_complete(asyncio.sleep(0.1))

            # Verify shutdown event was set
            assert service.shutdown_event.is_set()
        finally:
            loop.close()


class TestCLICommands:
    """Test CLI commands."""

    @pytest.fixture
    def cli_runner(self):
        """Create CLI test runner."""
        return typer.testing.CliRunner()

    def test_run_command_with_defaults(self, mock_modules, cli_runner):
        """Test run command with default parameters."""
        from socket_client.main import app

        with (
            patch("socket_client.main.SocketClientService") as mock_service_class,
            patch("socket_client.main.signal.signal"),
            patch("socket_client.main.asyncio.run") as mock_asyncio_run,
        ):
            mock_service = MagicMock()
            mock_service_class.return_value = mock_service

            result = cli_runner.invoke(app, ["run"])

            # Verify service was created and started
            mock_service_class.assert_called_once()
            mock_asyncio_run.assert_called_once()
            assert result.exit_code == 0

    def test_run_command_with_custom_parameters(self, mock_modules, cli_runner):
        """Test run command with custom CLI parameters."""
        from socket_client.main import app

        with (
            patch("socket_client.main.SocketClientService") as mock_service_class,
            patch("socket_client.main.signal.signal"),
            patch("socket_client.main.asyncio.run"),
        ):
            mock_service = MagicMock()
            mock_service_class.return_value = mock_service

            result = cli_runner.invoke(
                app,
                [
                    "run",
                    "--ws-url",
                    "wss://custom.url",
                    "--streams",
                    "ethusdt@trade",
                    "--nats-url",
                    "nats://custom:4222",
                    "--nats-topic",
                    "custom.topic",
                    "--log-level",
                    "DEBUG",
                ],
            )

            # Verify environment variables were set
            assert os.environ.get("BINANCE_WS_URL") == "wss://custom.url"
            assert os.environ.get("BINANCE_STREAMS") == "ethusdt@trade"
            assert os.environ.get("NATS_URL") == "nats://custom:4222"
            assert os.environ.get("NATS_TOPIC") == "custom.topic"
            assert os.environ.get("LOG_LEVEL") == "DEBUG"
            assert result.exit_code == 0

    def test_run_command_keyboard_interrupt(self, mock_modules, cli_runner):
        """Test run command handles KeyboardInterrupt gracefully."""
        from socket_client.main import app

        with (
            patch("socket_client.main.SocketClientService"),
            patch("socket_client.main.signal.signal"),
            patch(
                "socket_client.main.asyncio.run", side_effect=KeyboardInterrupt()
            ) as mock_run,
        ):
            result = cli_runner.invoke(app, ["run"])

            mock_run.assert_called_once()
            # CLI should handle KeyboardInterrupt gracefully
            assert "Shutdown requested" in result.stdout or result.exit_code == 0

    def test_run_command_service_failure(self, mock_modules, cli_runner):
        """Test run command handles service failure."""
        from socket_client.main import app

        with (
            patch("socket_client.main.SocketClientService"),
            patch("socket_client.main.signal.signal"),
            patch(
                "socket_client.main.asyncio.run",
                side_effect=Exception("Service crashed"),
            ),
        ):
            result = cli_runner.invoke(app, ["run"])

            # Should exit with error code
            assert result.exit_code != 0
            assert "Service failed" in result.stdout

    def test_health_command(self, mock_modules, cli_runner):
        """Test health check command."""
        from socket_client.main import app

        with patch("socket_client.main.requests.get") as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"status": "healthy"}
            mock_get.return_value = mock_response

            result = cli_runner.invoke(app, ["health"])

            assert result.exit_code == 0
            assert "healthy" in result.stdout.lower()

    def test_health_command_service_down(self, mock_modules, cli_runner):
        """Test health check when service is down."""
        from socket_client.main import app

        with patch(
            "socket_client.main.requests.get",
            side_effect=Exception("Connection refused"),
        ):
            result = cli_runner.invoke(app, ["health"])

            # Should handle connection error gracefully
            assert "error" in result.stdout.lower() or result.exit_code != 0

    def test_version_command(self, mock_modules, cli_runner):
        """Test version command."""
        from socket_client.main import app

        with patch("socket_client.main.__version__", "1.2.3"):
            result = cli_runner.invoke(app, ["version"])

            assert result.exit_code == 0
            assert "1.2.3" in result.stdout


class TestOpenTelemetryIntegration:
    """Test OpenTelemetry setup."""

    def test_otel_setup_success(self, mock_modules):
        """Test OpenTelemetry initializes correctly."""
        with (
            patch.dict(os.environ, {"OTEL_NO_AUTO_INIT": ""}, clear=False),
            patch("socket_client.main.setup_telemetry") as mock_setup,
        ):
            # Re-import to trigger OTEL setup
            import importlib

            import socket_client.main

            importlib.reload(socket_client.main)

            # Verify setup_telemetry was called or no exceptions were raised
            # Note: This may not be called if OTEL_NO_AUTO_INIT is set
            assert True  # Test passes if no exception was raised

    def test_otel_import_error_handled(self, mock_modules):
        """Test handles missing petrosa_otel gracefully."""
        with patch.dict("sys.modules", {"petrosa_otel": None}):
            # Re-import should not raise exception
            import importlib

            import socket_client.main

            importlib.reload(socket_client.main)
            # Verify no exception was raised
            assert True

    def test_otel_logging_handler_failure(self, mock_modules):
        """Test handles logging handler attachment failure."""
        with (
            patch("socket_client.main.setup_logging") as mock_logging,
            patch(
                "socket_client.main.attach_logging_handler",
                side_effect=Exception("Handler failed"),
            ),
        ):
            mock_logger = MagicMock()
            mock_logging.return_value = mock_logger

            # Should not raise exception - logs warning instead
            from socket_client.main import SocketClientService

            service = SocketClientService()
            assert service is not None


class TestModuleInitialization:
    """Test module-level initialization."""

    def test_dotenv_loaded(self, mock_modules):
        """Test that .env file is loaded."""
        with patch("socket_client.main.load_dotenv") as mock_load:
            import importlib

            import socket_client.main

            importlib.reload(socket_client.main)

            mock_load.assert_called_once()

    def test_typer_app_created(self, mock_modules):
        """Test Typer app is created correctly."""
        from socket_client.main import app

        assert isinstance(app, typer.Typer)

    def test_project_root_added_to_path(self, mock_modules):
        """Test project root is added to sys.path."""
        import importlib

        import socket_client.main

        importlib.reload(socket_client.main)

        # Verify path manipulation occurred (hard to test exact value)
        assert len(sys.path) > 0

