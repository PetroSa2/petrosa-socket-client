"""
Configuration manager for Socket Client service.

Manages runtime configuration for streams, reconnection, and circuit breaker settings.
"""

import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)

# Global config manager instance
_config_manager: Optional["ConfigManager"] = None


class ConfigManager:
    """Manages configuration for Socket Client service.

    Per #133: this is a **read-only snapshot** of the env-var-backed
    configuration loaded at process start. There is no persistence layer
    (no MongoDB, no shared store) and no IPC path to the separately-deployed
    ``BinanceWebSocketClient`` process (see ``socket_client/main.py`` vs
    ``socket_client/api/main.py``), so mutating this in-memory object cannot
    change running WebSocket-client behavior. The former ``set_streams`` /
    ``set_reconnection_config`` / ``set_circuit_breaker_config`` mutators
    were removed because they silently no-opped past a log line — callers
    believed they were changing runtime behavior and were not. Configuration
    is changed by editing the env vars / k8s ConfigMap and restarting the
    pod.
    """

    def __init__(self):
        """Initialize configuration manager."""
        # Load from environment variables (defaults)
        self._streams = (
            os.getenv("BINANCE_STREAMS", "").split(",")
            if os.getenv("BINANCE_STREAMS")
            else []
        )
        self._reconnect_delay = int(os.getenv("WEBSOCKET_RECONNECT_DELAY", "5"))
        self._max_reconnect_attempts = int(
            os.getenv("WEBSOCKET_MAX_RECONNECT_ATTEMPTS", "10")
        )
        self._backoff_multiplier = float(
            os.getenv("WEBSOCKET_BACKOFF_MULTIPLIER", "2.0")
        )
        self._failure_threshold = int(
            os.getenv("CIRCUIT_BREAKER_FAILURE_THRESHOLD", "5")
        )
        self._recovery_timeout = int(
            os.getenv("CIRCUIT_BREAKER_RECOVERY_TIMEOUT", "60")
        )
        self._half_open_max_calls = int(
            os.getenv("CIRCUIT_BREAKER_HALF_OPEN_MAX_CALLS", "3")
        )

        # MongoDB configuration (for backward compatibility with tests)
        self.mongo_uri = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
        self.db_name = os.getenv("MONGODB_DATABASE", "petrosa")
        self.collection_name = os.getenv("MONGODB_COLLECTION", "socket_config")

    def get_streams(self) -> list[str]:
        """Get current stream subscriptions."""
        return self._streams.copy()

    def get_reconnection_config(self) -> dict:
        """Get reconnection configuration."""
        return {
            "reconnect_delay": self._reconnect_delay,
            "max_reconnect_attempts": self._max_reconnect_attempts,
            "backoff_multiplier": self._backoff_multiplier,
        }

    def get_circuit_breaker_config(self) -> dict:
        """Get circuit breaker configuration."""
        return {
            "failure_threshold": self._failure_threshold,
            "recovery_timeout": self._recovery_timeout,
            "half_open_max_calls": self._half_open_max_calls,
        }


def get_config_manager() -> ConfigManager:
    """Get the global config manager instance."""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    return _config_manager


def set_config_manager(manager: ConfigManager) -> None:
    """Set the global config manager instance (for testing)."""
    global _config_manager
    _config_manager = manager
