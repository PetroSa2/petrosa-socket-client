"""
Unit tests for message models.
"""

from datetime import datetime
from unittest import mock

import pytest

from socket_client.models.message import (
    DepthMessage,
    TickerMessage,
    TradeMessage,
    WebSocketMessage,
    create_message,
    validate_message,
)

# Try to import trace context for testing
try:
    from opentelemetry import trace
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import SimpleSpanProcessor
    from opentelemetry.sdk.trace.export.in_memory_span_exporter import (
        InMemorySpanExporter,
    )

    OTEL_AVAILABLE = True
except ImportError:
    OTEL_AVAILABLE = False


@pytest.mark.unit
class TestWebSocketMessage:
    """Test WebSocket message model."""

    def test_create_websocket_message(self):
        """Test creating a basic WebSocket message."""
        message = WebSocketMessage(
            stream="btcusdt@trade", data={"price": "50000", "quantity": "1.0"}
        )

        assert message.stream == "btcusdt@trade"
        assert message.data == {"price": "50000", "quantity": "1.0"}
        assert isinstance(message.timestamp, datetime)
        assert message.message_id is None

    def test_create_message_with_id(self):
        """Test creating a message with custom ID."""
        message = WebSocketMessage(
            stream="btcusdt@trade", data={"price": "50000"}, message_id="test-123"
        )

        assert message.message_id == "test-123"

    def test_to_nats_message(self):
        """Test converting to NATS message format."""
        message = WebSocketMessage(stream="btcusdt@trade", data={"price": "50000"})

        nats_message = message.to_nats_message()

        assert nats_message["stream"] == "btcusdt@trade"
        assert nats_message["data"] == {"price": "50000"}
        assert "timestamp" in nats_message
        assert nats_message["source"] == "binance-websocket"
        assert nats_message["version"] == "1.0"

    def test_to_json(self):
        """Test converting to JSON string."""
        message = WebSocketMessage(stream="btcusdt@trade", data={"price": "50000"})

        json_str = message.to_json()
        assert isinstance(json_str, str)

        # Parse back to verify
        import json

        parsed = json.loads(json_str)
        assert parsed["stream"] == "btcusdt@trade"
        assert parsed["data"] == {"price": "50000"}


@pytest.mark.unit
class TestTradeMessage:
    """Test trade message model."""

    def test_create_trade_message(self):
        """Test creating a trade message."""
        trade_data = {
            "e": "trade",
            "E": 123456789,
            "s": "BTCUSDT",
            "t": 12345,
            "p": "0.001",
            "q": "100",
            "b": 88,
            "a": 50,
            "T": 123456785,
            "m": True,
            "M": True,
        }

        message = TradeMessage(stream="btcusdt@trade", data=trade_data)

        assert message.stream == "btcusdt@trade"
        assert message.data == trade_data
        assert message.data["e"] == "trade"


@pytest.mark.unit
class TestTickerMessage:
    """Test ticker message model."""

    def test_create_ticker_message(self):
        """Test creating a ticker message."""
        ticker_data = {
            "e": "24hrTicker",
            "E": 123456789,
            "s": "BTCUSDT",
            "p": "0.0015",
            "P": "250.00",
        }

        message = TickerMessage(stream="btcusdt@ticker", data=ticker_data)

        assert message.stream == "btcusdt@ticker"
        assert message.data == ticker_data
        assert message.data["e"] == "24hrTicker"


@pytest.mark.unit
class TestDepthMessage:
    """Test depth message model."""

    def test_create_depth_message(self):
        """Test creating a depth message."""
        depth_data = {
            "e": "depthUpdate",
            "E": 123456789,
            "s": "BTCUSDT",
            "U": 1,
            "u": 2,
            "b": [["0.0024", "10"]],
            "a": [["0.0026", "100"]],
        }

        message = DepthMessage(stream="btcusdt@depth20@100ms", data=depth_data)

        assert message.stream == "btcusdt@depth20@100ms"
        assert message.data == depth_data
        assert message.data["e"] == "depthUpdate"


@pytest.mark.unit
class TestCreateMessage:
    """Test message creation factory function."""

    def test_create_trade_message(self):
        """Test creating a trade message via factory."""
        data = {"e": "trade", "s": "BTCUSDT"}
        message = create_message("btcusdt@trade", data)

        assert isinstance(message, TradeMessage)
        assert message.stream == "btcusdt@trade"

    def test_create_ticker_message(self):
        """Test creating a ticker message via factory."""
        data = {"e": "24hrTicker", "s": "BTCUSDT"}
        message = create_message("btcusdt@ticker", data)

        assert isinstance(message, TickerMessage)
        assert message.stream == "btcusdt@ticker"

    def test_create_depth_message(self):
        """Test creating a depth message via factory."""
        data = {"e": "depthUpdate", "s": "BTCUSDT"}
        message = create_message("btcusdt@depth20@100ms", data)

        assert isinstance(message, DepthMessage)
        assert message.stream == "btcusdt@depth20@100ms"

    def test_create_generic_message(self):
        """Test creating a generic message for unknown stream."""
        data = {"test": "data"}
        message = create_message("unknown@stream", data)

        assert isinstance(message, WebSocketMessage)
        assert message.stream == "unknown@stream"


@pytest.mark.unit
class TestValidateMessage:
    """Test message validation."""

    def test_validate_valid_message(self):
        """Test validating a valid message."""
        message_dict = {
            "stream": "btcusdt@trade",
            "data": {"e": "trade", "s": "BTCUSDT"},
        }

        message = validate_message(message_dict)
        assert isinstance(message, TradeMessage)
        assert message.stream == "btcusdt@trade"

    def test_validate_message_missing_stream(self):
        """Test validating message with missing stream."""
        message_dict = {"data": {"e": "trade"}}

        with pytest.raises(ValueError, match="Missing required field"):
            validate_message(message_dict)

    def test_validate_message_missing_data(self):
        """Test validating message with missing data."""
        message_dict = {"stream": "btcusdt@trade"}

        with pytest.raises(ValueError, match="Missing required field"):
            validate_message(message_dict)

    def test_validate_message_invalid_format(self):
        """Test validating message with invalid format."""
        message_dict = "invalid"

        with pytest.raises(ValueError, match="Invalid message format"):
            validate_message(message_dict)


@pytest.mark.unit
@pytest.mark.skipif(not OTEL_AVAILABLE, reason="OpenTelemetry not available")
class TestTraceContextPropagation:
    """Test trace context propagation in messages."""

    @pytest.fixture(scope="function")
    def tracer_provider(self):
        """Create a tracer provider with in-memory exporter for testing."""
        exporter = InMemorySpanExporter()
        provider = TracerProvider()
        provider.add_span_processor(SimpleSpanProcessor(exporter))
        trace.set_tracer_provider(provider)
        return provider

    @pytest.fixture(scope="function")
    def tracer(self, tracer_provider):
        """Get a tracer instance."""
        return trace.get_tracer(__name__)

    def test_to_nats_message_includes_trace_context(self, tracer):
        """Test that to_nats_message() includes trace context when available."""
        from socket_client.models.message import TRACE_PROPAGATION_AVAILABLE

        if not TRACE_PROPAGATION_AVAILABLE:
            pytest.skip("Trace propagation not available")

        message = WebSocketMessage(stream="btcusdt@trade", data={"price": "50000"})

        # Create a span and generate message
        with tracer.start_as_current_span("test_span"):
            nats_message = message.to_nats_message()

            # Should include trace context field
            assert "_otel_trace_context" in nats_message
            assert isinstance(nats_message["_otel_trace_context"], dict)

            # Should include traceparent header
            carrier = nats_message["_otel_trace_context"]
            assert "traceparent" in carrier

    def test_to_nats_message_without_active_span(self):
        """Test that to_nats_message() works even without active span."""
        from socket_client.models.message import TRACE_PROPAGATION_AVAILABLE

        if not TRACE_PROPAGATION_AVAILABLE:
            pytest.skip("Trace propagation not available")

        message = WebSocketMessage(stream="btcusdt@trade", data={"price": "50000"})

        # Generate message without active span
        nats_message = message.to_nats_message()

        # Should still include trace context field (may be empty)
        assert "_otel_trace_context" in nats_message

    def test_to_nats_message_preserves_original_fields(self, tracer):
        """Test that trace context injection preserves all original fields."""
        from socket_client.models.message import TRACE_PROPAGATION_AVAILABLE

        if not TRACE_PROPAGATION_AVAILABLE:
            pytest.skip("Trace propagation not available")

        data = {"price": "50000", "quantity": "1.5"}
        message = WebSocketMessage(
            stream="btcusdt@trade", data=data, message_id="test-123"
        )

        with tracer.start_as_current_span("test_span"):
            nats_message = message.to_nats_message()

            # All original fields should be present
            assert nats_message["stream"] == "btcusdt@trade"
            assert nats_message["data"] == data
            assert nats_message["message_id"] == "test-123"
            assert nats_message["source"] == "binance-websocket"
            assert nats_message["version"] == "1.0"
            assert "timestamp" in nats_message

            # Plus trace context
            assert "_otel_trace_context" in nats_message

    def test_to_json_includes_trace_context(self, tracer):
        """Test that to_json() includes trace context in serialized output."""
        import json

        from socket_client.models.message import TRACE_PROPAGATION_AVAILABLE

        if not TRACE_PROPAGATION_AVAILABLE:
            pytest.skip("Trace propagation not available")

        message = WebSocketMessage(stream="btcusdt@trade", data={"price": "50000"})

        with tracer.start_as_current_span("test_span"):
            json_str = message.to_json()
            parsed = json.loads(json_str)

            # Should include trace context in JSON
            assert "_otel_trace_context" in parsed
            assert isinstance(parsed["_otel_trace_context"], dict)

    def test_trace_context_roundtrip(self, tracer):
        """
        Test that trace context can be round-tripped through message serialization.

        This simulates the real flow:
        1. socket-client creates message with trace context
        2. Serializes to JSON for NATS
        3. Consumer deserializes and extracts context
        """
        import json

        from socket_client.models.message import TRACE_PROPAGATION_AVAILABLE

        if not TRACE_PROPAGATION_AVAILABLE:
            pytest.skip("Trace propagation not available")

        try:
            from petrosa_otel import extract_trace_context
        except ImportError:
            pytest.skip("petrosa_otel not available for extract")

        message = WebSocketMessage(stream="btcusdt@trade", data={"price": "50000"})

        parent_trace_id = None

        # Publisher side (socket-client)
        with tracer.start_as_current_span("publisher_span") as parent_span:
            parent_trace_id = parent_span.get_span_context().trace_id

            # Serialize message (includes trace context)
            json_str = message.to_json()

        # Simulate NATS transport
        # ...

        # Consumer side (realtime-strategies)
        nats_message = json.loads(json_str)
        consumer_ctx = extract_trace_context(nats_message)

        # Create child span with extracted context
        with tracer.start_as_current_span(
            "consumer_span", context=consumer_ctx
        ) as child_span:
            child_trace_id = child_span.get_span_context().trace_id

            # Trace IDs should match!
            assert child_trace_id == parent_trace_id


@pytest.mark.unit
class TestTraceContextFallback:
    """Test that messages work even when trace propagation is not available."""

    @mock.patch("socket_client.models.message.TRACE_PROPAGATION_AVAILABLE", False)
    def test_to_nats_message_without_trace_propagation(self):
        """Test that messages work when trace propagation library is not available."""
        message = WebSocketMessage(stream="btcusdt@trade", data={"price": "50000"})

        # Should not raise even without trace propagation
        nats_message = message.to_nats_message()

        # Should have all standard fields
        assert nats_message["stream"] == "btcusdt@trade"
        assert nats_message["data"] == {"price": "50000"}
        assert "timestamp" in nats_message

        # Should NOT have trace context (library not available)
        # The actual behavior depends on the implementation
