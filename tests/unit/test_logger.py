"""Tests for the logger utilities module."""

import pytest
from socket_client.utils.logger import get_logger, setup_logging, LoggerMixin


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


def test_logger_mixin() -> None:
    """Test LoggerMixin functionality."""

    class TestClass(LoggerMixin):
        """Test class using LoggerMixin."""

        def __init__(self) -> None:
            """Initialize test class."""
            super().__init__()

    obj = TestClass()
    assert hasattr(obj, "logger")
    assert obj.logger is not None


def test_logger_mixin_log_methods() -> None:
    """Test LoggerMixin log methods."""

    class TestClass(LoggerMixin):
        """Test class using LoggerMixin."""

        def __init__(self) -> None:
            """Initialize test class."""
            super().__init__()

    obj = TestClass()

    # Test all log methods
    obj.log_info("info message", key="value")
    obj.log_error("error message", error_code=500)
    obj.log_warning("warning message", warning_type="test")
    obj.log_debug("debug message", debug_data={"test": "data"})


def test_logger_mixin_with_kwargs() -> None:
    """Test LoggerMixin with various kwargs."""

    class TestClass(LoggerMixin):
        """Test class using LoggerMixin."""

        def __init__(self, custom_arg: str = "default") -> None:
            """Initialize with custom argument."""
            super().__init__()
            self.custom_arg = custom_arg

    obj = TestClass(custom_arg="custom")
    assert obj.custom_arg == "custom"
    assert obj.logger is not None
    obj.log_info("test")

