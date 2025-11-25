"""
Tests for the configuration API routes.

Tests the FastAPI configuration endpoints for streams, reconnection, and circuit breaker.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

from socket_client.api.main import create_app
from socket_client.services.config_manager import ConfigManager, get_config_manager, set_config_manager


@pytest.fixture
def mock_config_manager():
    """Mock configuration manager."""
    manager = MagicMock(spec=ConfigManager)
    manager.get_streams.return_value = ["btcusdt@trade", "ethusdt@ticker"]
    manager.get_reconnection_config.return_value = {
        "reconnect_delay": 5,
        "max_reconnect_attempts": 10,
        "backoff_multiplier": 2.0,
    }
    manager.get_circuit_breaker_config.return_value = {
        "failure_threshold": 5,
        "recovery_timeout": 60,
        "half_open_max_calls": 3,
    }
    return manager


@pytest.fixture
def client(mock_config_manager):
    """Create test client with mocked config manager."""
    # Set the mock config manager
    set_config_manager(mock_config_manager)
    
    app = create_app()
    return TestClient(app)


class TestStreamsEndpoints:
    """Tests for streams configuration endpoints."""

    def test_get_streams(self, client, mock_config_manager):
        """Test GET /api/v1/config/streams."""
        response = client.get("/api/v1/config/streams")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "data" in data
        assert data["data"]["count"] == 2
        assert "btcusdt@trade" in data["data"]["streams"]

    def test_update_streams_success(self, client, mock_config_manager):
        """Test POST /api/v1/config/streams with valid streams."""
        request_data = {
            "streams": ["btcusdt@trade", "ethusdt@ticker"],
            "changed_by": "test_user",
            "reason": "Testing",
            "validate_only": False,
        }
        response = client.post("/api/v1/config/streams", json=request_data)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["count"] == 2
        mock_config_manager.set_streams.assert_called_once()

    def test_update_streams_validate_only(self, client, mock_config_manager):
        """Test POST /api/v1/config/streams with validate_only=true."""
        request_data = {
            "streams": ["btcusdt@trade", "ethusdt@ticker"],
            "changed_by": "test_user",
            "reason": "Testing",
            "validate_only": True,
        }
        response = client.post("/api/v1/config/streams", json=request_data)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["metadata"]["validation"] == "passed"
        assert data["data"] is None
        # Should not call set_streams when validate_only=True
        mock_config_manager.set_streams.assert_not_called()

    def test_update_streams_invalid_format(self, client, mock_config_manager):
        """Test POST /api/v1/config/streams with invalid stream format."""
        request_data = {
            "streams": ["INVALID_STREAM"],
            "changed_by": "test_user",
            "validate_only": False,
        }
        response = client.post("/api/v1/config/streams", json=request_data)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
        assert "VALIDATION_ERROR" in data["error"]["code"]

    def test_update_streams_invalid_format_validate_only(self, client, mock_config_manager):
        """Test POST /api/v1/config/streams with invalid format and validate_only=true."""
        request_data = {
            "streams": ["INVALID_STREAM"],
            "changed_by": "test_user",
            "validate_only": True,
        }
        response = client.post("/api/v1/config/streams", json=request_data)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["metadata"]["validation"] == "failed"
        assert data["data"] is None


class TestReconnectionEndpoints:
    """Tests for reconnection configuration endpoints."""

    def test_get_reconnection(self, client, mock_config_manager):
        """Test GET /api/v1/config/reconnection."""
        response = client.get("/api/v1/config/reconnection")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["reconnect_delay"] == 5
        assert data["data"]["max_reconnect_attempts"] == 10

    def test_update_reconnection_success(self, client, mock_config_manager):
        """Test POST /api/v1/config/reconnection with valid parameters."""
        request_data = {
            "reconnect_delay": 10,
            "max_reconnect_attempts": 20,
            "backoff_multiplier": 2.5,
            "changed_by": "test_user",
            "reason": "Testing",
            "validate_only": False,
        }
        response = client.post("/api/v1/config/reconnection", json=request_data)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["reconnect_delay"] == 10
        mock_config_manager.set_reconnection_config.assert_called_once()

    def test_update_reconnection_validate_only(self, client, mock_config_manager):
        """Test POST /api/v1/config/reconnection with validate_only=true."""
        request_data = {
            "reconnect_delay": 10,
            "max_reconnect_attempts": 20,
            "backoff_multiplier": 2.5,
            "changed_by": "test_user",
            "validate_only": True,
        }
        response = client.post("/api/v1/config/reconnection", json=request_data)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["metadata"]["validation"] == "passed"
        assert data["data"] is None
        mock_config_manager.set_reconnection_config.assert_not_called()


class TestCircuitBreakerEndpoints:
    """Tests for circuit breaker configuration endpoints."""

    def test_get_circuit_breaker(self, client, mock_config_manager):
        """Test GET /api/v1/config/circuit-breaker."""
        response = client.get("/api/v1/config/circuit-breaker")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["failure_threshold"] == 5
        assert data["data"]["recovery_timeout"] == 60

    def test_update_circuit_breaker_success(self, client, mock_config_manager):
        """Test POST /api/v1/config/circuit-breaker with valid parameters."""
        request_data = {
            "failure_threshold": 10,
            "recovery_timeout": 120,
            "half_open_max_calls": 5,
            "changed_by": "test_user",
            "reason": "Testing",
            "validate_only": False,
        }
        response = client.post("/api/v1/config/circuit-breaker", json=request_data)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["failure_threshold"] == 10
        mock_config_manager.set_circuit_breaker_config.assert_called_once()

    def test_update_circuit_breaker_validate_only(self, client, mock_config_manager):
        """Test POST /api/v1/config/circuit-breaker with validate_only=true."""
        request_data = {
            "failure_threshold": 10,
            "recovery_timeout": 120,
            "half_open_max_calls": 5,
            "changed_by": "test_user",
            "validate_only": True,
        }
        response = client.post("/api/v1/config/circuit-breaker", json=request_data)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["metadata"]["validation"] == "passed"
        assert data["data"] is None
        mock_config_manager.set_circuit_breaker_config.assert_not_called()


class TestValidateEndpoint:
    """Tests for /api/v1/config/validate endpoint."""

    def test_validate_streams_success(self, client):
        """Test validate endpoint with valid streams."""
        request_data = {
            "config_type": "streams",
            "parameters": {
                "streams": ["btcusdt@trade", "ethusdt@ticker"],
            },
        }
        response = client.post("/api/v1/config/validate", json=request_data)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["validation_passed"] is True
        assert len(data["data"]["errors"]) == 0

    def test_validate_streams_invalid(self, client):
        """Test validate endpoint with invalid streams."""
        request_data = {
            "config_type": "streams",
            "parameters": {
                "streams": ["INVALID_STREAM"],
            },
        }
        response = client.post("/api/v1/config/validate", json=request_data)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["validation_passed"] is False
        assert len(data["data"]["errors"]) > 0

    def test_validate_reconnection_success(self, client):
        """Test validate endpoint with valid reconnection config."""
        request_data = {
            "config_type": "reconnection",
            "parameters": {
                "reconnect_delay": 10,
                "max_reconnect_attempts": 20,
                "backoff_multiplier": 2.0,
            },
        }
        response = client.post("/api/v1/config/validate", json=request_data)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["validation_passed"] is True

    def test_validate_reconnection_invalid(self, client):
        """Test validate endpoint with invalid reconnection config."""
        request_data = {
            "config_type": "reconnection",
            "parameters": {
                "reconnect_delay": 500,  # Out of range (> 300)
                "max_reconnect_attempts": 20,
            },
        }
        response = client.post("/api/v1/config/validate", json=request_data)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["validation_passed"] is False
        assert len(data["data"]["errors"]) > 0

    def test_validate_circuit_breaker_success(self, client):
        """Test validate endpoint with valid circuit breaker config."""
        request_data = {
            "config_type": "circuit_breaker",
            "parameters": {
                "failure_threshold": 10,
                "recovery_timeout": 120,
            },
        }
        response = client.post("/api/v1/config/validate", json=request_data)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["validation_passed"] is True

    def test_validate_circuit_breaker_invalid(self, client):
        """Test validate endpoint with invalid circuit breaker config."""
        request_data = {
            "config_type": "circuit_breaker",
            "parameters": {
                "failure_threshold": 100,  # Out of range (> 50)
                "recovery_timeout": 120,
            },
        }
        response = client.post("/api/v1/config/validate", json=request_data)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["validation_passed"] is False
        assert len(data["data"]["errors"]) > 0

    def test_validate_invalid_config_type(self, client):
        """Test validate endpoint with invalid config type."""
        request_data = {
            "config_type": "invalid_type",
            "parameters": {},
        }
        response = client.post("/api/v1/config/validate", json=request_data)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["validation_passed"] is False
        assert len(data["data"]["errors"]) > 0


class TestRootEndpoints:
    """Tests for root and health endpoints."""

    def test_root_endpoint(self, client):
        """Test GET / endpoint."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "Socket Client Configuration API"
        assert "/api/v1/config/streams" in data["endpoints"]

    def test_healthz_endpoint(self, client):
        """Test GET /healthz endpoint."""
        response = client.get("/healthz")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"

    def test_ready_endpoint(self, client):
        """Test GET /ready endpoint."""
        response = client.get("/ready")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ready"

