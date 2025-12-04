"""
Tests to boost models/message.py from 90.62% to 100%.
Target the 6 remaining uncovered lines.
"""

import pytest
from datetime import datetime

from socket_client.models.message import (
    WebSocketMessage,
    TradeMessage,
    TickerMessage,
    DepthMessage,
    create_message,
    validate_message,
)


@pytest.mark.unit
class TestMessageTimestampEdgeCases:
    """Test timestamp edge cases (lines 18, 42-47)."""

    def test_timestamp_as_datetime_object(self):
        """Test timestamp passed as datetime object."""
        dt = datetime(2025, 1, 1, 12, 0, 0)
        
        msg = WebSocketMessage(
            stream="test@stream",
            data={"test": "data"},
            timestamp=dt,
        )

        assert msg.timestamp == dt

    def test_timestamp_default_factory(self):
        """Test timestamp uses default factory when not provided."""
        before = datetime.utcnow()
        
        msg = WebSocketMessage(
            stream="test@stream",
            data={"test": "data"},
        )

        after = datetime.utcnow()

        # Timestamp should be between before and after
        assert before <= msg.timestamp <= after

    def test_timestamp_iso_string_with_z(self):
        """Test parsing ISO timestamp with Z suffix."""
        msg = WebSocketMessage(
            stream="test@stream",
            data={"test": "data"},
            timestamp="2025-01-15T10:30:00Z",
        )

        assert msg.timestamp.year == 2025
        assert msg.timestamp.month == 1
        assert msg.timestamp.day == 15

    def test_timestamp_iso_string_without_z(self):
        """Test parsing ISO timestamp without Z suffix."""
        msg = WebSocketMessage(
            stream="test@stream",
            data={"test": "data"},
            timestamp="2025-02-20T14:45:30",
        )

        assert msg.timestamp.year == 2025
        assert msg.timestamp.month == 2
        assert msg.timestamp.day == 20

    def test_timestamp_with_microseconds(self):
        """Test timestamp with microseconds."""
        msg = WebSocketMessage(
            stream="test@stream",
            data={"test": "data"},
            timestamp="2025-03-10T08:15:30.123456Z",
        )

        assert msg.timestamp.year == 2025
        assert msg.timestamp.microsecond == 123456

    def test_timestamp_midnight(self):
        """Test timestamp at midnight."""
        msg = WebSocketMessage(
            stream="test@stream",
            data={"test": "data"},
            timestamp="2025-01-01T00:00:00Z",
        )

        assert msg.timestamp.hour == 0
        assert msg.timestamp.minute == 0
        assert msg.timestamp.second == 0


@pytest.mark.unit
class TestMessageNATSFormat:
    """Test to_nats_message format."""

    def test_nats_message_includes_all_fields(self):
        """Test NATS message includes all required fields."""
        msg = WebSocketMessage(
            stream="btcusdt@trade",
            data={"price": "50000"},
            message_id="msg-123",
        )

        nats_msg = msg.to_nats_message()

        assert "stream" in nats_msg
        assert "data" in nats_msg
        assert "timestamp" in nats_msg
        assert "message_id" in nats_msg
        assert "source" in nats_msg
        assert "version" in nats_msg

    def test_nats_message_source_field(self):
        """Test NATS message source is correct."""
        msg = WebSocketMessage(
            stream="test@stream",
            data={"test": "data"},
        )

        nats_msg = msg.to_nats_message()

        assert nats_msg["source"] == "binance-websocket"

    def test_nats_message_version_field(self):
        """Test NATS message version is correct."""
        msg = WebSocketMessage(
            stream="test@stream",
            data={"test": "data"},
        )

        nats_msg = msg.to_nats_message()

        assert nats_msg["version"] == "1.0"

    def test_nats_message_timestamp_format(self):
        """Test NATS message timestamp has Z suffix."""
        msg = WebSocketMessage(
            stream="test@stream",
            data={"test": "data"},
        )

        nats_msg = msg.to_nats_message()

        assert nats_msg["timestamp"].endswith("Z")
        assert "T" in nats_msg["timestamp"]


@pytest.mark.unit
class TestCreateMessageFunction:
    """Test create_message function."""

    def test_create_trade_message(self):
        """Test creating trade message."""
        msg = create_message("trade", {"symbol": "BTCUSDT", "price": "50000"})

        assert isinstance(msg, TradeMessage)
        assert msg.data["symbol"] == "BTCUSDT"

    def test_create_ticker_message(self):
        """Test creating ticker message."""
        msg = create_message("ticker", {"symbol": "ETHUSDT"})

        assert isinstance(msg, TickerMessage)

    def test_create_depth_message(self):
        """Test creating depth message."""
        msg = create_message("depth", {"symbol": "BNBUSDT"})

        assert isinstance(msg, DepthMessage)

    def test_create_generic_message(self):
        """Test creating generic message."""
        msg = create_message("unknown", {"test": "data"})

        assert isinstance(msg, WebSocketMessage)


@pytest.mark.unit
class TestValidateMessageFunction:
    """Test validate_message function."""

    def test_validate_valid_message(self):
        """Test validating valid message."""
        valid_msg = {
            "stream": "btcusdt@trade",
            "data": {"price": "50000"},
        }

        result = validate_message(valid_msg)

        assert result is True

    def test_validate_message_missing_stream(self):
        """Test validating message missing stream."""
        invalid_msg = {
            "data": {"price": "50000"},
        }

        result = validate_message(invalid_msg)

        assert result is False

    def test_validate_message_missing_data(self):
        """Test validating message missing data."""
        invalid_msg = {
            "stream": "btcusdt@trade",
        }

        result = validate_message(invalid_msg)

        assert result is False

    def test_validate_message_invalid_type(self):
        """Test validating non-dict message."""
        result = validate_message("not a dict")

        assert result is False

    def test_validate_none_message(self):
        """Test validating None message."""
        result = validate_message(None)

        assert result is False

    def test_validate_empty_dict(self):
        """Test validating empty dict."""
        result = validate_message({})

        assert result is False

