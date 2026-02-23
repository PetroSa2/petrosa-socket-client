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
    """Manages configuration for Socket Client service."""

    def __init__(self):
        """Initialize configuration manager."""
        # Load from environment variables (defaults)
        self._streams = os.getenv("BINANCE_STREAMS", "").split(",") if os.getenv("BINANCE_STREAMS") else []
        self._reconnect_delay = int(os.getenv("WEBSOCKET_RECONNECT_DELAY", "5"))
        self._max_reconnect_attempts = int(os.getenv("WEBSOCKET_MAX_RECONNECT_ATTEMPTS", "10"))
        self._backoff_multiplier = float(os.getenv("WEBSOCKET_BACKOFF_MULTIPLIER", "2.0"))
        self._failure_threshold = int(os.getenv("CIRCUIT_BREAKER_FAILURE_THRESHOLD", "5"))
        self._recovery_timeout = int(os.getenv("CIRCUIT_BREAKER_RECOVERY_TIMEOUT", "60"))
        self._half_open_max_calls = int(os.getenv("CIRCUIT_BREAKER_HALF_OPEN_MAX_CALLS", "3"))

        # MongoDB configuration (for backward compatibility with tests)
        self.mongo_uri = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
        self.db_name = os.getenv("MONGODB_DATABASE", "petrosa")
        self.collection_name = os.getenv("MONGODB_COLLECTION", "socket_config")

    def get_streams(self) -> list[str]:
        """Get current stream subscriptions."""
        return self._streams.copy()

    def set_streams(self, streams: list[str], changed_by: str, reason: Optional[str] = None) -> None:
        """Set stream subscriptions."""
        self._streams = streams
        logger.info(f"Streams updated by {changed_by}: {streams} (reason: {reason})")
        # TODO: Persist to MongoDB and update WebSocket client

    def add_stream(self, stream: str, changed_by: str, reason: Optional[str] = None) -> None:
        """Add a single stream subscription."""
        if stream not in self._streams:
            self._streams.append(stream)
            logger.info(f"Stream added by {changed_by}: {stream} (reason: {reason})")

    def remove_stream(self, stream: str, changed_by: str, reason: Optional[str] = None) -> None:
        """Remove a single stream subscription."""
        if stream in self._streams:
            self._streams.remove(stream)
            logger.info(f"Stream removed by {changed_by}: {stream} (reason: {reason})")

    def update_streams(self, streams: list[str], changed_by: str, reason: Optional[str] = None) -> None:
        """Update multiple stream subscriptions (alias for set_streams)."""
        self.set_streams(streams, changed_by, reason)

    def get_reconnection_config(self) -> dict:
        """Get reconnection configuration."""
        return {
            "reconnect_delay": self._reconnect_delay,
            "max_reconnect_attempts": self._max_reconnect_attempts,
            "backoff_multiplier": self._backoff_multiplier,
        }

    def set_reconnection_config(
        self,
        reconnect_delay: int,
        max_reconnect_attempts: int,
        backoff_multiplier: float,
        changed_by: str,
        reason: Optional[str] = None,
    ) -> None:
        """Set reconnection configuration."""
        self._reconnect_delay = reconnect_delay
        self._max_reconnect_attempts = max_reconnect_attempts
        self._backoff_multiplier = backoff_multiplier
        logger.info(f"Reconnection config updated by {changed_by} (reason: {reason})")
        # TODO: Persist to MongoDB and update WebSocket client

    def get_circuit_breaker_config(self) -> dict:
        """Get circuit breaker configuration."""
        return {
            "failure_threshold": self._failure_threshold,
            "recovery_timeout": self._recovery_timeout,
            "half_open_max_calls": self._half_open_max_calls,
        }

    def set_circuit_breaker_config(
        self,
        failure_threshold: int,
        recovery_timeout: int,
        half_open_max_calls: int,
        changed_by: str,
        reason: Optional[str] = None,
    ) -> None:
        """Set circuit breaker configuration."""
        self._failure_threshold = failure_threshold
        self._recovery_timeout = recovery_timeout
        self._half_open_max_calls = half_open_max_calls
        logger.info(f"Circuit breaker config updated by {changed_by} (reason: {reason})")
        # TODO: Persist to MongoDB and update circuit breaker


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

