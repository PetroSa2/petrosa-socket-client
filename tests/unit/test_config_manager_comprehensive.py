"""
Comprehensive tests for socket_client/services/config_manager.py

Tests cover:
- Configuration loading and saving
- MongoDB integration
- Error handling
- Edge cases
"""

import os
from unittest.mock import MagicMock, Mock, patch

import pytest

from socket_client.services.config_manager import ConfigManager


class TestConfigManager:
    """Comprehensive tests for ConfigManager."""

    @pytest.fixture
    def mock_mongo_client(self):
        """Create a mock MongoDB client."""
        mock_client = MagicMock()
        mock_db = MagicMock()
        mock_collection = MagicMock()

        mock_client.__getitem__.return_value = mock_db
        mock_db.__getitem__.return_value = mock_collection

        return mock_client, mock_collection

    @pytest.fixture
    def config_manager(self, mock_mongo_client):
        """Create ConfigManager instance with mocked MongoDB."""
        mock_client, mock_collection = mock_mongo_client

        with patch("socket_client.services.config_manager.MongoClient", return_value=mock_client):
            with patch.dict(
                os.environ,
                {
                    "MONGO_URI": "mongodb://test:27017",
                    "MONGO_DB": "test_db",
                    "MONGO_COLLECTION": "test_collection",
                },
            ):
                manager = ConfigManager()
                manager.collection = mock_collection
                return manager

    def test_initialization_with_env_vars(self, mock_mongo_client):
        """Test ConfigManager initialization with environment variables."""
        mock_client, _ = mock_mongo_client

        with patch("socket_client.services.config_manager.MongoClient", return_value=mock_client):
            with patch.dict(
                os.environ,
                {
                    "MONGO_URI": "mongodb://custom:27017",
                    "MONGO_DB": "custom_db",
                    "MONGO_COLLECTION": "custom_collection",
                },
            ):
                manager = ConfigManager()

                assert manager.mongo_uri == "mongodb://custom:27017"
                assert manager.db_name == "custom_db"
                assert manager.collection_name == "custom_collection"

    def test_initialization_with_defaults(self, mock_mongo_client):
        """Test ConfigManager initialization with default values."""
        mock_client, _ = mock_mongo_client

        with patch("socket_client.services.config_manager.MongoClient", return_value=mock_client):
            with patch.dict(os.environ, {}, clear=True):
                manager = ConfigManager()

                assert manager.mongo_uri == "mongodb://localhost:27017"
                assert manager.db_name == "socket_client"
                assert manager.collection_name == "config"

    def test_load_config_success(self, config_manager):
        """Test successful configuration loading."""
        mock_config = {
            "_id": "test_id",
            "streams": ["btcusdt@trade", "ethusdt@trade"],
            "settings": {"reconnect": True},
        }
        config_manager.collection.find_one.return_value = mock_config

        result = config_manager.load_config()

        assert result == mock_config
        config_manager.collection.find_one.assert_called_once()

    def test_load_config_not_found(self, config_manager):
        """Test configuration loading when config doesn't exist."""
        config_manager.collection.find_one.return_value = None

        result = config_manager.load_config()

        assert result is None
        config_manager.collection.find_one.assert_called_once()

    def test_load_config_with_filter(self, config_manager):
        """Test configuration loading with custom filter."""
        custom_filter = {"version": "v2"}
        mock_config = {"_id": "test_id", "version": "v2"}
        config_manager.collection.find_one.return_value = mock_config

        result = config_manager.load_config(custom_filter)

        assert result == mock_config
        config_manager.collection.find_one.assert_called_once_with(custom_filter)

    def test_load_config_exception_handling(self, config_manager):
        """Test configuration loading handles MongoDB exceptions."""
        config_manager.collection.find_one.side_effect = Exception("MongoDB error")

        with pytest.raises(Exception, match="MongoDB error"):
            config_manager.load_config()

    def test_save_config_success(self, config_manager):
        """Test successful configuration saving."""
        config_data = {
            "streams": ["btcusdt@trade"],
            "settings": {"reconnect": True},
        }
        mock_result = MagicMock()
        mock_result.upserted_id = "new_id"
        mock_result.modified_count = 1
        config_manager.collection.update_one.return_value = mock_result

        result = config_manager.save_config(config_data)

        assert result is True
        config_manager.collection.update_one.assert_called_once()

        # Verify upsert=True was used
        call_args = config_manager.collection.update_one.call_args
        assert call_args[1]["upsert"] is True

    def test_save_config_with_filter(self, config_manager):
        """Test configuration saving with custom filter."""
        config_data = {"streams": ["btcusdt@trade"]}
        custom_filter = {"version": "v2"}
        mock_result = MagicMock()
        mock_result.modified_count = 1
        config_manager.collection.update_one.return_value = mock_result

        result = config_manager.save_config(config_data, custom_filter)

        assert result is True
        config_manager.collection.update_one.assert_called_once_with(
            custom_filter, {"$set": config_data}, upsert=True
        )

    def test_save_config_no_changes(self, config_manager):
        """Test configuration saving when no changes are made."""
        config_data = {"streams": ["btcusdt@trade"]}
        mock_result = MagicMock()
        mock_result.modified_count = 0
        mock_result.upserted_id = None
        config_manager.collection.update_one.return_value = mock_result

        result = config_manager.save_config(config_data)

        # Should still return True (upsert succeeded even if no changes)
        assert result is True

    def test_save_config_exception_handling(self, config_manager):
        """Test configuration saving handles MongoDB exceptions."""
        config_data = {"streams": ["btcusdt@trade"]}
        config_manager.collection.update_one.side_effect = Exception("Write error")

        with pytest.raises(Exception, match="Write error"):
            config_manager.save_config(config_data)

    def test_get_streams_from_config(self, config_manager):
        """Test extracting streams from loaded configuration."""
        mock_config = {
            "streams": ["btcusdt@trade", "ethusdt@ticker"],
        }
        config_manager.collection.find_one.return_value = mock_config

        config = config_manager.load_config()
        streams = config.get("streams", [])

        assert streams == ["btcusdt@trade", "ethusdt@ticker"]

    def test_connection_error_handling(self, mock_mongo_client):
        """Test ConfigManager handles connection errors."""
        mock_client, _ = mock_mongo_client

        with patch(
            "socket_client.services.config_manager.MongoClient",
            side_effect=Exception("Connection failed"),
        ):
            with pytest.raises(Exception, match="Connection failed"):
                ConfigManager()

    def test_empty_config_save(self, config_manager):
        """Test saving empty configuration."""
        empty_config = {}
        mock_result = MagicMock()
        mock_result.modified_count = 1
        config_manager.collection.update_one.return_value = mock_result

        result = config_manager.save_config(empty_config)

        assert result is True

    def test_complex_nested_config(self, config_manager):
        """Test saving and loading complex nested configuration."""
        complex_config = {
            "streams": ["btcusdt@trade"],
            "settings": {
                "reconnect": True,
                "retry": {
                    "max_attempts": 5,
                    "backoff": "exponential",
                },
            },
            "thresholds": {
                "price": [100, 200, 300],
                "volume": [1000, 5000],
            },
        }

        mock_result = MagicMock()
        mock_result.modified_count = 1
        config_manager.collection.update_one.return_value = mock_result
        config_manager.collection.find_one.return_value = complex_config

        # Save
        save_result = config_manager.save_config(complex_config)
        assert save_result is True

        # Load
        loaded_config = config_manager.load_config()
        assert loaded_config == complex_config

    def test_config_with_special_characters(self, config_manager):
        """Test configuration with special characters."""
        special_config = {
            "name": "Test-Config_v1.0",
            "description": "Config with $pecial @haracters!",
            "symbols": ["BTC/USDT", "ETH-USDT"],
        }

        mock_result = MagicMock()
        mock_result.modified_count = 1
        config_manager.collection.update_one.return_value = mock_result
        config_manager.collection.find_one.return_value = special_config

        save_result = config_manager.save_config(special_config)
        assert save_result is True

        loaded_config = config_manager.load_config()
        assert loaded_config == special_config

    def test_concurrent_operations(self, config_manager):
        """Test handling of rapid successive operations."""
        config_data = {"streams": ["btcusdt@trade"]}
        mock_result = MagicMock()
        mock_result.modified_count = 1
        config_manager.collection.update_one.return_value = mock_result

        # Perform multiple save operations
        for i in range(10):
            result = config_manager.save_config({**config_data, "version": i})
            assert result is True

        assert config_manager.collection.update_one.call_count == 10

    def test_unicode_in_config(self, config_manager):
        """Test configuration with Unicode characters."""
        unicode_config = {
            "name": "Config with émojis 🚀💰",
            "symbols": ["比特币", "以太坊"],
            "messages": {
                "welcome": "Bienvenido",
                "goodbye": "さようなら",
            },
        }

        mock_result = MagicMock()
        mock_result.modified_count = 1
        config_manager.collection.update_one.return_value = mock_result
        config_manager.collection.find_one.return_value = unicode_config

        save_result = config_manager.save_config(unicode_config)
        assert save_result is True

        loaded_config = config_manager.load_config()
        assert loaded_config == unicode_config

    def test_large_config_data(self, config_manager):
        """Test handling of large configuration data."""
        large_config = {
            "streams": [f"symbol{i}@trade" for i in range(1000)],
            "metadata": {f"key_{i}": f"value_{i}" for i in range(1000)},
        }

        mock_result = MagicMock()
        mock_result.modified_count = 1
        config_manager.collection.update_one.return_value = mock_result

        result = config_manager.save_config(large_config)
        assert result is True

    def test_boolean_and_numeric_values(self, config_manager):
        """Test configuration with various data types."""
        mixed_types_config = {
            "enabled": True,
            "disabled": False,
            "count": 42,
            "price": 99.99,
            "ratio": 0.5,
            "null_value": None,
        }

        mock_result = MagicMock()
        mock_result.modified_count = 1
        config_manager.collection.update_one.return_value = mock_result
        config_manager.collection.find_one.return_value = mixed_types_config

        save_result = config_manager.save_config(mixed_types_config)
        assert save_result is True

        loaded_config = config_manager.load_config()
        assert loaded_config == mixed_types_config

