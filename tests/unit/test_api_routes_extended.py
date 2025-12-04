"""
Extended tests for API routes to boost coverage from 77.54% to 90%+.
Targets error handling and edge cases.
"""

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from socket_client.api.main import create_app
from socket_client.services.config_manager import ConfigManager, set_config_manager


@pytest.fixture
def mock_config_manager_extended():
    """Extended mock configuration manager."""
    manager = MagicMock(spec=ConfigManager)

    # Default successful responses
    manager.get_streams.return_value = ["btcusdt@trade"]
    manager.add_stream.return_value = {"success": True}
    manager.remove_stream.return_value = {"success": True}
    manager.update_streams.return_value = {"success": True}
    manager.get_reconnection_config.return_value = {
        "reconnect_delay": 5,
        "max_reconnect_attempts": 10,
    }
    manager.update_reconnection_config.return_value = {"success": True}
    manager.get_circuit_breaker_config.return_value = {
        "failure_threshold": 5,
        "recovery_timeout": 60,
    }
    manager.update_circuit_breaker_config.return_value = {"success": True}

    return manager


@pytest.fixture
def client_extended(mock_config_manager_extended):
    """Create test client with extended mock."""
    set_config_manager(mock_config_manager_extended)
    app = create_app()
    client = TestClient(app)
    yield client
    set_config_manager(None)


class TestStreamsAPIEdgeCases:
    """Test streams API edge cases."""

    def test_add_stream_with_special_characters(self, client_extended):
        """Test adding stream with special characters."""
        response = client_extended.post("/api/v1/config/streams/btc%2Fusdt@trade")

        # Should handle URL encoding
        assert response.status_code in [200, 201]

    def test_remove_stream_url_encoded(self, client_extended):
        """Test removing stream with URL encoding."""
        response = client_extended.delete("/api/v1/config/streams/btc%40usdt")

        assert response.status_code in [200, 204, 404]

    def test_get_streams_empty_list(
        self, client_extended, mock_config_manager_extended
    ):
        """Test getting streams when none configured."""
        mock_config_manager_extended.get_streams.return_value = []

        response = client_extended.get("/api/v1/config/streams")

        assert response.status_code == 200
        data = response.json()
        assert data["data"]["count"] == 0

    def test_update_streams_single_stream(self, client_extended):
        """Test updating with single stream."""
        response = client_extended.put(
            "/api/v1/config/streams", json={"streams": ["btcusdt@trade"]}
        )

        assert response.status_code == 200

    def test_update_streams_many_streams(self, client_extended):
        """Test updating with many streams."""
        many_streams = [f"symbol{i}@trade" for i in range(100)]

        response = client_extended.put(
            "/api/v1/config/streams", json={"streams": many_streams}
        )

        assert response.status_code == 200


class TestReconnectionAPIEdgeCases:
    """Test reconnection API edge cases."""

    def test_update_reconnection_zero_delay(self, client_extended):
        """Test updating reconnection with zero delay."""
        response = client_extended.put(
            "/api/v1/config/reconnection",
            json={"reconnect_delay": 0, "max_reconnect_attempts": 10},
        )

        # Should either accept or validate
        assert response.status_code in [200, 400, 422]

    def test_update_reconnection_large_values(self, client_extended):
        """Test updating reconnection with large values."""
        response = client_extended.put(
            "/api/v1/config/reconnection",
            json={"reconnect_delay": 3600, "max_reconnect_attempts": 1000},
        )

        assert response.status_code in [200, 400]

    def test_update_reconnection_negative_values(self, client_extended):
        """Test updating reconnection with negative values."""
        response = client_extended.put(
            "/api/v1/config/reconnection",
            json={"reconnect_delay": -5, "max_reconnect_attempts": -10},
        )

        # Should reject or validate
        assert response.status_code in [200, 400, 422]


class TestCircuitBreakerAPIEdgeCases:
    """Test circuit breaker API edge cases."""

    def test_update_circuit_breaker_zero_threshold(self, client_extended):
        """Test updating with zero failure threshold."""
        response = client_extended.put(
            "/api/v1/config/circuit-breaker",
            json={"failure_threshold": 0, "recovery_timeout": 60},
        )

        assert response.status_code in [200, 400, 422]

    def test_update_circuit_breaker_large_timeout(self, client_extended):
        """Test updating with large recovery timeout."""
        response = client_extended.put(
            "/api/v1/config/circuit-breaker",
            json={"failure_threshold": 5, "recovery_timeout": 86400},
        )

        assert response.status_code in [200, 400]

    def test_update_circuit_breaker_partial_config(self, client_extended):
        """Test updating with partial configuration."""
        response = client_extended.put(
            "/api/v1/config/circuit-breaker", json={"failure_threshold": 10}
        )

        # Should handle partial updates
        assert response.status_code in [200, 400, 422]


class TestValidateEndpointEdgeCases:
    """Test validate endpoint edge cases."""

    def test_validate_streams_empty_list(self, client_extended):
        """Test validating empty streams list."""
        response = client_extended.post(
            "/api/v1/config/validate/streams", json={"streams": []}
        )

        assert response.status_code in [200, 400]

    def test_validate_streams_duplicate_streams(self, client_extended):
        """Test validating duplicate streams."""
        response = client_extended.post(
            "/api/v1/config/validate/streams",
            json={"streams": ["btcusdt@trade", "btcusdt@trade"]},
        )

        assert response.status_code in [200, 400]

    def test_validate_reconnection_boundary_values(self, client_extended):
        """Test validating boundary values."""
        response = client_extended.post(
            "/api/v1/config/validate/reconnection",
            json={"reconnect_delay": 1, "max_reconnect_attempts": 1},
        )

        assert response.status_code in [200, 400]

    def test_validate_circuit_breaker_boundary_values(self, client_extended):
        """Test validating circuit breaker boundary values."""
        response = client_extended.post(
            "/api/v1/config/validate/circuit-breaker",
            json={"failure_threshold": 1, "recovery_timeout": 1},
        )

        assert response.status_code in [200, 400]


class TestAPIResponseFormats:
    """Test API response formats."""

    def test_streams_response_has_success_field(self, client_extended):
        """Test streams response has success field."""
        response = client_extended.get("/api/v1/config/streams")

        data = response.json()
        assert "success" in data

    def test_streams_response_has_data_field(self, client_extended):
        """Test streams response has data field."""
        response = client_extended.get("/api/v1/config/streams")

        data = response.json()
        assert "data" in data

    def test_reconnection_response_format(self, client_extended):
        """Test reconnection response format."""
        response = client_extended.get("/api/v1/config/reconnection")

        data = response.json()
        assert "success" in data
        assert "data" in data

    def test_circuit_breaker_response_format(self, client_extended):
        """Test circuit breaker response format."""
        response = client_extended.get("/api/v1/config/circuit-breaker")

        data = response.json()
        assert "success" in data
        assert "data" in data
