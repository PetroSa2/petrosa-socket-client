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

# Add project root to path
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


@pytest.fixture
def service(mock_modules):
    """Create service instance with mocked dependencies."""
    with (
        patch("socket_client.main.setup_logging"),
        patch("socket_client.main.attach_logging_handler"),
    ):
        from socket_client.main import SocketClientService

        service = SocketClientService()
        return service


class TestSocketClientService:
    """Test SocketClientService class."""

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
        """Test service startup failure."""
        mock_health_server = AsyncMock()
        mock_health_server.start.side_effect = Exception("Health server failed")

        with patch("socket_client.main.HealthServer", return_value=mock_health_server):
            with pytest.raises(Exception, match="Health server failed"):
                await service.start()

    @pytest.mark.asyncio
    async def test_service_stop_with_clients(self, service):
        """Test service stop with active clients."""
        mock_health_server = AsyncMock()
        mock_ws_client = AsyncMock()

        service.health_server = mock_health_server
        service.websocket_client = mock_ws_client

        await service.stop()

        mock_health_server.stop.assert_called_once()
        mock_ws_client.stop.assert_called_once()

    @pytest.mark.asyncio
    async def test_service_stop_without_clients(self, service):
        """Test service stop without active clients."""
        service.health_server = None
        service.websocket_client = None

        # Should not raise exception
        await service.stop()

    @pytest.mark.asyncio
    async def test_service_startup_exception_triggers_stop(self, service):
        """Test that exception during startup triggers cleanup."""
        mock_health_server = AsyncMock()
        # Startup fails
        mock_health_server.start.side_effect = Exception("Fatal error")

        with (
            patch("socket_client.main.HealthServer", return_value=mock_health_server),
            patch.object(service, "stop", new_callable=AsyncMock) as mock_stop,
        ):
            with pytest.raises(Exception, match="Fatal error"):
                await service.start()

            # Verify stop was called
            mock_stop.assert_called_once()


class TestSignalHandler:
    """Test signal handler functionality."""

    @pytest.mark.asyncio
    async def test_signal_handler_sets_shutdown_event(self, service):
        """Test signal handler sets shutdown event."""
        from socket_client.main import SocketClientService, signal_handler

        service = MagicMock(spec=SocketClientService)
        service.shutdown_event = asyncio.Event()
        signal_handler.service = service  # type: ignore

        with patch("asyncio.create_task") as mock_create_task:
            # Call signal handler
            signal_handler(signal.SIGTERM, None)

            # Verify task was created
            mock_create_task.assert_called_once()


class TestCLICommands:
    """Test CLI commands."""

    @pytest.fixture
    def cli_runner(self):
        """Create CLI test runner."""
        return typer.testing.CliRunner()

    def test_run_command_with_defaults(self, mock_modules, cli_runner):
        """Test run command with default parameters."""
        mock_service_instance = MagicMock()
        mock_service_instance.start = AsyncMock()

        with patch(
            "socket_client.main.SocketClientService", return_value=mock_service_instance
        ):
            from socket_client.main import app

            # Run with short timeout to prevent hanging
            result = cli_runner.invoke(app, ["run"], input="\n")

            assert result.exit_code == 0
            mock_service_instance.start.assert_called_once()

    def test_run_command_with_custom_parameters(self, mock_modules, cli_runner):
        """Test run command with custom parameters."""
        mock_service_instance = MagicMock()
        mock_service_instance.start = AsyncMock()

        with (
            patch(
                "socket_client.main.SocketClientService",
                return_value=mock_service_instance,
            ),
            patch("os.environ", {}),
        ):
            from socket_client.main import app

            result = cli_runner.invoke(
                app,
                [
                    "run",
                    "--ws-url",
                    "wss://custom.ws",
                    "--nats-url",
                    "nats://custom:4222",
                    "--streams",
                    "ethusdt@trade",
                ],
                input="\n",
            )

            assert result.exit_code == 0
            assert os.environ["BINANCE_WS_URL"] == "wss://custom.ws"
            assert os.environ["NATS_URL"] == "nats://custom:4222"
            assert os.environ["BINANCE_STREAMS"] == "ethusdt@trade"

    def test_run_command_keyboard_interrupt(self, mock_modules, cli_runner):
        """Test run command handles KeyboardInterrupt."""
        mock_service_instance = MagicMock()
        mock_service_instance.start.side_effect = KeyboardInterrupt()

        with patch(
            "socket_client.main.SocketClientService", return_value=mock_service_instance
        ):
            from socket_client.main import app

            result = cli_runner.invoke(app, ["run"])

            assert result.exit_code == 0
            assert "Shutdown requested by user" in result.stdout

    def test_run_command_service_failure(self, mock_modules, cli_runner):
        """Test run command handles service failure."""
        mock_service_instance = MagicMock()
        mock_service_instance.start.side_effect = Exception("Service failed")

        with patch(
            "socket_client.main.SocketClientService", return_value=mock_service_instance
        ):
            from socket_client.main import app

            result = cli_runner.invoke(app, ["run"])

            assert result.exit_code == 1
            assert "Service failed: Service failed" in result.stdout

    def test_health_command(self, mock_modules, cli_runner):
        """Test health command."""
        with patch("requests.get") as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"status": "healthy"}
            mock_get.return_value = mock_response

            from socket_client.main import app

            result = cli_runner.invoke(app, ["health"])

            assert result.exit_code == 0
            assert "Service is healthy" in result.stdout

    def test_health_command_service_down(self, mock_modules, cli_runner):
        """Test health command when service is down."""
        with patch("requests.get", side_effect=Exception("Connection refused")):
            from socket_client.main import app

            result = cli_runner.invoke(app, ["health"])

            assert result.exit_code == 1
            # Check for the actual error message in output
            assert "Health check failed" in result.stdout or "Service is down" in result.stdout or "Connection refused" in result.stdout

    def test_version_command(self, mock_modules, cli_runner):
        """Test version command."""
        from socket_client.main import app

        result = cli_runner.invoke(app, ["version"])

        assert result.exit_code == 0
        assert "Petrosa Socket Client version" in result.stdout


class TestOpenTelemetryIntegration:
    """Test OpenTelemetry integration."""

    def test_otel_setup_success(self, mock_modules):
        """Test successful telemetry setup."""
        with (
            patch("socket_client.main.setup_telemetry") as mock_setup,
            patch.dict(os.environ, {"OTEL_NO_AUTO_INIT": ""}),
        ):
            # Clear it from environ directly too to be sure
            if "OTEL_NO_AUTO_INIT" in os.environ:
                del os.environ["OTEL_NO_AUTO_INIT"]
                
            # Reload module to trigger initialization code
            if "socket_client.main" in sys.modules:
                del sys.modules["socket_client.main"]
            import socket_client.main  # noqa: F401

            mock_setup.assert_called_once()

    def test_otel_import_error_handled(self, mock_constants):
        """Test that import error for petrosa_otel is handled."""
        with (
            patch.dict("sys.modules", {"petrosa_otel": None}),
            patch("socket_client.main.setup_logging"),
        ):
            # Should not raise exception
            if "socket_client.main" in sys.modules:
                del sys.modules["socket_client.main"]
            import socket_client.main  # noqa: F401

    def test_otel_logging_handler_failure(self, service):
        """Test that logging handler attachment failure is handled."""
        with (
            patch(
                "socket_client.main.attach_logging_handler",
                side_effect=Exception("Attach failed"),
            ),
            patch("socket_client.main.setup_logging"),
        ):
            # Initialization should continue
            from socket_client.main import SocketClientService

            SocketClientService()


class TestModuleInitialization:
    """Test module-level initialization."""

    def test_dotenv_loaded(self, mock_modules):
        """Test that load_dotenv is called."""
        with patch("socket_client.main.load_dotenv") as mock_load:
            # Reload module to trigger initialization code
            if "socket_client.main" in sys.modules:
                del sys.modules["socket_client.main"]
            import socket_client.main  # noqa: F401

            mock_load.assert_called_once()

    def test_typer_app_created(self, mock_modules):
        """Test that typer app instance is created."""
        from socket_client.main import app

        assert isinstance(app, typer.Typer)

    def test_project_root_added_to_path(self, mock_modules):
        """Test that project root is in sys.path."""
        import socket_client.main  # noqa: F401

        # The actual path depends on environment, but it should be there
        assert any("socket-client" in path for path in sys.path)
