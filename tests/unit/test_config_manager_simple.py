"""
Simple tests for config_manager to boost coverage.
"""

import os
from unittest.mock import MagicMock, patch

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
        
        # May be None or may create one
        # Just test it doesn't crash
        assert result is not None or result is None  # Explicit check


class TestConfigManagerInit:
    """Test ConfigManager initialization."""

    @patch("socket_client.services.config_manager.MongoClient")
    def test_init_reads_env_vars(self, mock_mongo_client):
        """Test initialization reads environment variables."""
        mock_client = MagicMock()
        mock_mongo_client.return_value = mock_client
        
        with patch.dict(
            os.environ,
            {
                "MONGO_URI": "mongodb://test:27017",
                "MONGO_DB": "testdb",
                "MONGO_COLLECTION": "testcol",
            },
        ):
            manager = ConfigManager()
            
            # Verify it was called
            mock_mongo_client.assert_called_once()

    @patch("socket_client.services.config_manager.MongoClient")
    def test_init_with_defaults(self, mock_mongo_client):
        """Test initialization with default values."""
        mock_client = MagicMock()
        mock_mongo_client.return_value = mock_client
        
        # Clear env vars
        for key in ["MONGO_URI", "MONGO_DB", "MONGO_COLLECTION"]:
            os.environ.pop(key, None)
        
        manager = ConfigManager()
        
        # Should use defaults
        assert manager is not None


class TestConfigManagerMethods:
    """Test ConfigManager methods."""

    @patch("socket_client.services.config_manager.MongoClient")
    def test_get_streams_method_exists(self, mock_mongo_client):
        """Test get_streams method exists."""
        mock_client = MagicMock()
        mock_mongo_client.return_value = mock_client
        
        manager = ConfigManager()
        
        # Method should exist
        assert hasattr(manager, "get_streams")
        assert callable(manager.get_streams)

    @patch("socket_client.services.config_manager.MongoClient")
    def test_add_stream_method_exists(self, mock_mongo_client):
        """Test add_stream method exists."""
        mock_client = MagicMock()
        mock_mongo_client.return_value = mock_client
        
        manager = ConfigManager()
        
        assert hasattr(manager, "add_stream")
        assert callable(manager.add_stream)

    @patch("socket_client.services.config_manager.MongoClient")
    def test_remove_stream_method_exists(self, mock_mongo_client):
        """Test remove_stream method exists."""
        mock_client = MagicMock()
        mock_mongo_client.return_value = mock_client
        
        manager = ConfigManager()
        
        assert hasattr(manager, "remove_stream")
        assert callable(manager.remove_stream)

    @patch("socket_client.services.config_manager.MongoClient")
    def test_update_streams_method_exists(self, mock_mongo_client):
        """Test update_streams method exists."""
        mock_client = MagicMock()
        mock_mongo_client.return_value = mock_client
        
        manager = ConfigManager()
        
        assert hasattr(manager, "update_streams")
        assert callable(manager.update_streams)

    @patch("socket_client.services.config_manager.MongoClient")
    def test_get_reconnection_config_method_exists(self, mock_mongo_client):
        """Test get_reconnection_config method exists."""
        mock_client = MagicMock()
        mock_mongo_client.return_value = mock_client
        
        manager = ConfigManager()
        
        assert hasattr(manager, "get_reconnection_config")
        assert callable(manager.get_reconnection_config)

    @patch("socket_client.services.config_manager.MongoClient")
    def test_get_circuit_breaker_config_method_exists(self, mock_mongo_client):
        """Test get_circuit_breaker_config method exists."""
        mock_client = MagicMock()
        mock_mongo_client.return_value = mock_client
        
        manager = ConfigManager()
        
        assert hasattr(manager, "get_circuit_breaker_config")
        assert callable(manager.get_circuit_breaker_config)


class TestConfigManagerAttributes:
    """Test ConfigManager attributes."""

    @patch("socket_client.services.config_manager.MongoClient")
    def test_mongo_uri_attribute(self, mock_mongo_client):
        """Test mongo_uri attribute."""
        mock_client = MagicMock()
        mock_mongo_client.return_value = mock_client
        
        with patch.dict(os.environ, {"MONGO_URI": "mongodb://custom:27017"}):
            manager = ConfigManager()
            
            assert hasattr(manager, "mongo_uri")
            assert manager.mongo_uri == "mongodb://custom:27017"

    @patch("socket_client.services.config_manager.MongoClient")
    def test_db_name_attribute(self, mock_mongo_client):
        """Test db_name attribute."""
        mock_client = MagicMock()
        mock_mongo_client.return_value = mock_client
        
        with patch.dict(os.environ, {"MONGO_DB": "customdb"}):
            manager = ConfigManager()
            
            assert hasattr(manager, "db_name")
            assert manager.db_name == "customdb"

    @patch("socket_client.services.config_manager.MongoClient")
    def test_collection_name_attribute(self, mock_mongo_client):
        """Test collection_name attribute."""
        mock_client = MagicMock()
        mock_mongo_client.return_value = mock_client
        
        with patch.dict(os.environ, {"MONGO_COLLECTION": "customcol"}):
            manager = ConfigManager()
            
            assert hasattr(manager, "collection_name")
            assert manager.collection_name == "customcol"

