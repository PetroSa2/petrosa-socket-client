"""Tests for the logger utilities module."""

from socket_client.utils.logger import get_logger, setup_logging


def test_setup_logging_json_format() -> None:
    """Test setup_logging with JSON format."""
    logger = setup_logging(level="INFO", format_type="json")
    assert logger is not None
    logger.info("test message", test_key="test_value")


def test_setup_logging_text_format() -> None:
    """Test setup_logging with text format."""
    logger = setup_logging(level="DEBUG", format_type="text")
    assert logger is not None
    logger.debug("debug message")


def test_get_logger_without_name() -> None:
    """Test get_logger without name parameter."""
    logger = get_logger()
    assert logger is not None
    logger.info("test")


def test_get_logger_with_name() -> None:
    """Test get_logger with name parameter."""
    logger = get_logger("test_logger")
    assert logger is not None
    logger.info("test with name")
