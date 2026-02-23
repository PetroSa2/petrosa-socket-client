"""
Pytest configuration and fixtures for the Socket Client service.
"""

import asyncio
import os
from unittest.mock import AsyncMock, patch

import pytest

from socket_client.core.client import BinanceWebSocketClient

# Disable OpenTelemetry auto-initialization during tests
os.environ["OTEL_NO_AUTO_INIT"] = "1"


@pytest.fixture
def sample_trade_message() -> dict:
    """Sample trade message from Binance WebSocket."""
    return {
        "stream": "btcusdt@trade",
        "data": {
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
        },
    }


@pytest.fixture
def sample_ticker_message() -> dict:
    """Sample ticker message from Binance WebSocket."""
    return {
        "stream": "btcusdt@ticker",
        "data": {
            "e": "24hrTicker",
            "E": 123456789,
            "s": "BTCUSDT",
            "p": "0.001",
            "P": "0.1",
            "w": "0.001",
            "x": "0.0009",
            "c": "0.0011",
            "Q": "10",
            "b": "0.001",
            "B": "100",
            "a": "0.0012",
            "A": "200",
            "o": "0.001",
            "h": "0.0013",
            "l": "0.0008",
            "v": "10000",
            "q": "10",
            "O": 123456780,
            "C": 123456789,
            "F": 0,
            "L": 100,
            "n": 101,
        },
    }


@pytest.fixture
def sample_depth_message() -> dict:
    """Sample depth message from Binance WebSocket."""
    return {
        "stream": "btcusdt@depth5",
        "data": {
            "lastUpdateId": 160,
            "bids": [["0.001", "100"], ["0.0009", "200"]],
            "asks": [["0.0011", "150"], ["0.0012", "300"]],
        },
    }


@pytest.fixture
def mock_websocket():
    """Mock WebSocket connection."""
    mock_ws = AsyncMock()
    mock_ws.send = AsyncMock()
    mock_ws.close = AsyncMock()
    # Mock async iterator behavior
    mock_ws.__aiter__.return_value = []
    return mock_ws


@pytest.fixture
def mock_nats_client():
    """Mock NATS client."""
    mock_nc = AsyncMock()
    mock_nc.connect = AsyncMock()
    mock_nc.publish = AsyncMock()
    mock_nc.close = AsyncMock()
    return mock_nc


@pytest.fixture
def mock_nats_connect(mock_nats_client):
    """Mock nats.connect function."""
    with patch("nats.connect", return_value=mock_nats_client) as mock_connect:
        yield mock_connect


@pytest.fixture
def mock_websockets_connect(mock_websocket):
    """Mock websockets.connect function."""
    with patch("websockets.connect", return_value=mock_websocket) as mock_connect:
        yield mock_connect


@pytest.fixture
def websocket_client(mock_websocket, mock_nats_client):  # type: ignore[no-untyped-def]
    """WebSocket client with mocked dependencies."""
    client = BinanceWebSocketClient(
        ws_url="wss://test.binance.com",
        streams=["btcusdt@trade"],
        nats_url="nats://localhost:4222",
        nats_topic="test.topic",
    )
    client.websocket = mock_websocket
    client.nats_client = mock_nats_client
    return client


@pytest.fixture
def test_streams() -> list[str]:
    """Test stream list."""
    return ["btcusdt@trade", "ethusdt@ticker", "bnbusdt@depth5"]


@pytest.fixture
def test_config() -> dict:
    """Test configuration dictionary."""
    return {
        "ws_url": "wss://test.binance.com",
        "nats_url": "nats://localhost:4222",
        "nats_topic": "test.topic",
        "streams": ["btcusdt@trade"],
    }


@pytest.fixture
def mock_aiohttp_client_session():
    """Mock aiohttp ClientSession."""
    with patch("aiohttp.ClientSession") as mock_session:
        yield mock_session
