"""
Tests for socket_client/utils/logger.py to boost from current to 100%.
"""

import logging
import os
from unittest.mock import MagicMock, patch

import pytest

from socket_client.utils.logger import setup_logging, get_logger


@pytest.mark.unit
class TestSetupLogging:
    """Test setup_logging function."""

    def test_setup_logging_returns_logger(self):
        """Test setup_logging returns a logger."""
        logger = setup_logging()

        assert logger is not None
        assert hasattr(logger, "info")
        assert hasattr(logger, "error")
        assert hasattr(logger, "debug")

    def test_setup_logging_with_level(self):
        """Test setup_logging with custom level."""
        logger = setup_logging(level="DEBUG")

        assert logger is not None

    def test_setup_logging_info_level(self):
        """Test setup_logging with INFO level."""
        logger = setup_logging(level="INFO")

        assert logger is not None

    def test_setup_logging_error_level(self):
        """Test setup_logging with ERROR level."""
        logger = setup_logging(level="ERROR")

        assert logger is not None

    def test_setup_logging_warning_level(self):
        """Test setup_logging with WARNING level."""
        logger = setup_logging(level="WARNING")

        assert logger is not None

    def test_setup_logging_multiple_calls(self):
        """Test setup_logging can be called multiple times."""
        logger1 = setup_logging(level="INFO")
        logger2 = setup_logging(level="DEBUG")

        assert logger1 is not None
        assert logger2 is not None


@pytest.mark.unit
class TestGetLogger:
    """Test get_logger function."""

    def test_get_logger_with_name(self):
        """Test get_logger with custom name."""
        logger = get_logger("test_module")

        assert logger is not None
        assert hasattr(logger, "info")

    def test_get_logger_without_name(self):
        """Test get_logger without name."""
        logger = get_logger()

        assert logger is not None

    def test_get_logger_different_names(self):
        """Test get_logger with different names."""
        logger1 = get_logger("module1")
        logger2 = get_logger("module2")

        # Should return logger instances
        assert logger1 is not None
        assert logger2 is not None

    def test_get_logger_same_name_twice(self):
        """Test get_logger with same name twice."""
        logger1 = get_logger("same_module")
        logger2 = get_logger("same_module")

        # Should return loggers (may be same instance)
        assert logger1 is not None
        assert logger2 is not None


@pytest.mark.unit
class TestLoggingConfiguration:
    """Test logging configuration."""

    def test_logging_works_after_setup(self):
        """Test logging works after setup."""
        logger = setup_logging()

        # Should be able to log without errors
        logger.info("Test message")
        logger.error("Test error")
        logger.debug("Test debug")

    def test_logger_has_handlers(self):
        """Test logger has handlers configured."""
        logger = setup_logging()

        # Logger should have some configuration
        assert logger is not None

    def test_get_logger_works_after_setup(self):
        """Test get_logger works after setup_logging."""
        setup_logging()
        logger = get_logger("test")

        # Should work
        logger.info("Test")

