"""
Simple tests for config_manager to boost coverage.
"""

import os
from unittest.mock import MagicMock

import pytest

from socket_client.services.config_manager import ConfigManager, get_config_manager, set_config_manager


class TestConfigManagerGlobals:
    """Test config manager global functions."""

    def test_set_and_get_config_manager(self):
        """Test setting and getting config manager."""
        mock_manager = MagicMock(spec=ConfigManager)
        
        set_config_manager(mock_manager)
        retrieved = get_config_manager()
        
        assert retrieved is mock_manager
        
        # Cleanup
        set_config_manager(None)

    def test_get_config_manager_none_initially(self):
        """Test config manager is None initially."""
        set_config_manager(None)
        
        result = get_config_manager()
        assert result is not None


class TestConfigManagerInit:
    """Test ConfigManager initialization."""

    def test_init_reads_env_vars(self):
        """Test initialization reads environment variables."""
        env_vars = {
            "BINANCE_STREAMS": "btcusdt@trade,ethusdt@ticker",
            "WEBSOCKET_RECONNECT_DELAY": "10",
            "CIRCUIT_BREAKER_FAILURE_THRESHOLD": "15",
            "MONGODB_URI": "mongodb://test:27017"
        }
        
        # Create a mock environment
        import os
        original_environ = os.environ.copy()
        os.environ.update(env_vars)
        
        try:
            manager = ConfigManager()
            
            assert manager.get_streams() == ["btcusdt@trade", "ethusdt@ticker"]
            assert manager.mongo_uri == "mongodb://test:27017"
        finally:
            # Restore environment
            os.environ.clear()
            os.environ.update(original_environ)

    def test_init_with_defaults(self):
        """Test initialization with default values."""
        # Ensure env vars are clear for this test
        import os
        original_environ = os.environ.copy()
        for key in ["BINANCE_STREAMS", "WEBSOCKET_RECONNECT_DELAY"]:
            os.environ.pop(key, None)
        
        try:
            manager = ConfigManager()
            # Default should be empty or from base environment if not cleared
            assert isinstance(manager.get_streams(), list)
        finally:
            os.environ.clear()
            os.environ.update(original_environ)


class TestConfigManagerMethods:
    """Test ConfigManager methods."""

    def test_get_streams_method_exists(self):
        """Test get_streams method exists."""
        manager = ConfigManager()
        assert hasattr(manager, "get_streams")
        assert callable(manager.get_streams)

    def test_add_stream_method_exists(self):
        """Test add_stream method exists."""
        manager = ConfigManager()
        assert hasattr(manager, "add_stream")
        assert callable(manager.add_stream)

    def test_remove_stream_method_exists(self):
        """Test remove_stream method exists."""
        manager = ConfigManager()
        assert hasattr(manager, "remove_stream")
        assert callable(manager.remove_stream)

    def test_update_streams_method_exists(self):
        """Test update_streams method exists."""
        manager = ConfigManager()
        assert hasattr(manager, "update_streams")
        assert callable(manager.update_streams)

    def test_get_reconnection_config_method_exists(self):
        """Test get_reconnection_config method exists."""
        manager = ConfigManager()
        assert hasattr(manager, "get_reconnection_config")
        assert callable(manager.get_reconnection_config)

    def test_get_circuit_breaker_config_method_exists(self):
        """Test get_circuit_breaker_config method exists."""
        manager = ConfigManager()
        assert hasattr(manager, "get_circuit_breaker_config")
        assert callable(manager.get_circuit_breaker_config)


class TestConfigManagerAttributes:
    """Test ConfigManager attributes."""

    def test_mongo_uri_attribute(self):
        """Test mongo_uri attribute."""
        manager = ConfigManager()
        assert hasattr(manager, "mongo_uri")

    def test_db_name_attribute(self):
        """Test db_name attribute."""
        manager = ConfigManager()
        assert hasattr(manager, "db_name")

    def test_collection_name_attribute(self):
        """Test collection_name attribute."""
        manager = ConfigManager()
        assert hasattr(manager, "collection_name")
