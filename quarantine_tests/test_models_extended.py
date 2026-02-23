"""
Extended tests for message models.
Targets remaining uncovered lines in models/message.py.
"""

import json
from datetime import datetime
from unittest.mock import patch

import pytest

from socket_client.models.message import (
    DepthMessage,
    TickerMessage,
    TradeMessage,
    WebSocketMessage,
    create_message,
    validate_message,
)


@pytest.mark.unit
class TestTradeMessage:
    """Test TradeMessage model."""

    def test_trade_message_creation(self):
        """Test creating TradeMessage."""
        msg = TradeMessage(
            stream="btcusdt@trade",
            data={"price": "50000", "quantity": "1.5"},
        )

        assert isinstance(msg, WebSocketMessage)
        assert msg.stream == "btcusdt@trade"
        assert msg.data["price"] == "50000"

    def test_trade_message_to_nats(self):
        """Test TradeMessage to_nats_message."""
        msg = TradeMessage(
            stream="btcusdt@trade",
            data={"price": "50000"},
        )

        nats_msg = msg.to_nats_message()

        assert "stream" in nats_msg
        assert "data" in nats_msg
        assert nats_msg["stream"] == "btcusdt@trade"

    def test_trade_message_to_json(self):
        """Test TradeMessage to_json."""
        msg = TradeMessage(
            stream="btcusdt@trade",
            data={"price": "50000"},
        )

        json_str = msg.to_json()

        assert isinstance(json_str, str)
        assert "btcusdt@trade" in json_str


@pytest.mark.unit
class TestTickerMessage:
    """Test TickerMessage model."""

    def test_ticker_message_creation(self):
        """Test creating TickerMessage."""
        msg = TickerMessage(
            stream="ethusdt@ticker",
            data={"last_price": "3000"},
        )

        assert isinstance(msg, WebSocketMessage)
        assert msg.stream == "ethusdt@ticker"

    def test_ticker_message_to_nats(self):
        """Test TickerMessage to_nats_message."""
        msg = TickerMessage(
            stream="ethusdt@ticker",
            data={"last_price": "3000"},
        )

        nats_msg = msg.to_nats_message()

        assert nats_msg["stream"] == "ethusdt@ticker"


@pytest.mark.unit
class TestDepthMessage:
    """Test DepthMessage model."""

    def test_depth_message_creation(self):
        """Test creating DepthMessage."""
        msg = DepthMessage(
            stream="bnbusdt@depth",
            data={"bids": [], "asks": []},
        )

        assert isinstance(msg, WebSocketMessage)
        assert msg.stream == "bnbusdt@depth"

    def test_depth_message_to_nats(self):
        """Test DepthMessage to_nats_message."""
        msg = DepthMessage(
            stream="bnbusdt@depth",
            data={"bids": [], "asks": []},
        )

        nats_msg = msg.to_nats_message()

        assert nats_msg["stream"] == "bnbusdt@depth"


@pytest.mark.unit
class TestCreateMessageFunction:
    """Test create_message function variations."""

    def test_create_message_trade_type(self):
        """Test create_message with 'trade' type."""
        msg = create_message("trade", {"symbol": "BTCUSDT"})

        assert isinstance(msg, TradeMessage)

    def test_create_message_ticker_type(self):
        """Test create_message with 'ticker' type."""
        msg = create_message("ticker", {"symbol": "ETHUSDT"})

        assert isinstance(msg, TickerMessage)

    def test_create_message_depth_type(self):
        """Test create_message with 'depth' type."""
        msg = create_message("depth", {"symbol": "BNBUSDT"})

        assert isinstance(msg, DepthMessage)

    def test_create_message_unknown_type(self):
        """Test create_message with unknown type."""
        msg = create_message("kline", {"symbol": "ADAUSDT"})

        assert isinstance(msg, WebSocketMessage)

    def test_create_message_none_type(self):
        """Test create_message with None type."""
        msg = create_message(None, {"symbol": "SOLUSDT"})

        assert isinstance(msg, WebSocketMessage)

    def test_create_message_empty_data(self):
        """Test create_message with empty data."""
        msg = create_message("trade", {})

        assert isinstance(msg, TradeMessage)
        assert msg.data == {}


@pytest.mark.unit
class TestValidateMessageFunction:
    """Test validate_message function edge cases."""

    def test_validate_valid_complete_message(self):
        """Test validating complete valid message."""
        msg = {
            "stream": "btcusdt@trade",
            "data": {"price": "50000", "quantity": "1.0"},
        }

        assert validate_message(msg) is True

    def test_validate_minimal_valid_message(self):
        """Test validating minimal valid message."""
        msg = {
            "stream": "test@stream",
            "data": {},
        }

        assert validate_message(msg) is True

    def test_validate_stream_only(self):
        """Test validating message with stream only."""
        msg = {"stream": "btcusdt@trade"}

        assert validate_message(msg) is False

    def test_validate_data_only(self):
        """Test validating message with data only."""
        msg = {"data": {"price": "50000"}}

        assert validate_message(msg) is False

    def test_validate_list_instead_of_dict(self):
        """Test validating list instead of dict."""
        assert validate_message([]) is False
        assert validate_message(["item"]) is False

    def test_validate_string_instead_of_dict(self):
        """Test validating string instead of dict."""
        assert validate_message("invalid") is False

    def test_validate_number_instead_of_dict(self):
        """Test validating number instead of dict."""
        assert validate_message(123) is False
        assert validate_message(45.67) is False

    def test_validate_boolean_instead_of_dict(self):
        """Test validating boolean instead of dict."""
        assert validate_message(True) is False
        assert validate_message(False) is False


@pytest.mark.unit
class TestMessageJSONSerialization:
    """Test JSON serialization."""

    def test_to_json_returns_string(self):
        """Test to_json returns string."""
        msg = WebSocketMessage(
            stream="test@stream",
            data={"test": "data"},
        )

        result = msg.to_json()

        assert isinstance(result, str)

    def test_to_json_valid_json(self):
        """Test to_json produces valid JSON."""
        msg = WebSocketMessage(
            stream="test@stream",
            data={"test": "data"},
        )

        json_str = msg.to_json()

        # Should be parseable
        parsed = json.loads(json_str)
        assert isinstance(parsed, dict)

    def test_to_json_includes_stream(self):
        """Test to_json includes stream."""
        msg = WebSocketMessage(
            stream="btcusdt@trade",
            data={"price": "50000"},
        )

        json_str = msg.to_json()

        assert "btcusdt@trade" in json_str

    def test_to_json_complex_data(self):
        """Test to_json with complex nested data."""
        msg = WebSocketMessage(
            stream="test@stream",
            data={
                "level1": {
                    "level2": {
                        "level3": "value",
                        "array": [1, 2, 3],
                    }
                }
            },
        )

        json_str = msg.to_json()
        parsed = json.loads(json_str)

        assert parsed["data"]["level1"]["level2"]["level3"] == "value"
