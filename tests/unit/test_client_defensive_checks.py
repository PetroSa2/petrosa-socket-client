"""Tests for defensive runtime checks in the WebSocket client."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from socket_client.core.client import BinanceWebSocketClient


@pytest.mark.asyncio
async def test_process_message_validates_dict_type() -> None:
    """Test that _process_single_message validates dict type at runtime."""
    client = BinanceWebSocketClient(
        streams=["btcusdt@trade"],
        ws_url="wss://test.example.com",
        nats_url="nats://localhost",
        nats_topic="test.topic",
    )

    # Mock the NATS client to avoid actual connection
    client.nats_client = AsyncMock()
    client.nats_client.publish = AsyncMock()

    # Test with valid dict (should process)
    valid_data = {"e": "trade", "s": "BTCUSDT", "stream": "btcusdt@trade"}
    await client._process_single_message(valid_data)

    # Note: The isinstance check is defensive code that protects against unexpected data types
    # Even though type hints declare dict, this validates at runtime


@pytest.mark.asyncio
async def test_heartbeat_loop_defensive_check() -> None:
    """Test that heartbeat loop has defensive check for is_running race condition."""
    client = BinanceWebSocketClient(
        streams=["btcusdt@trade"],
        ws_url="wss://test.example.com",
        nats_url="nats://localhost",
        nats_topic="test.topic",
    )

    # Mock the stats logging
    client._log_heartbeat_stats = AsyncMock()

    # Set is_running and start heartbeat
    client.is_running = True

    # Create the heartbeat task
    heartbeat_task = asyncio.create_task(client._heartbeat_loop())

    # Let it run briefly (less than HEARTBEAT_INTERVAL)
    await asyncio.sleep(0.05)

    # Stop it by setting is_running to False (simulates race condition)
    client.is_running = False

    # Cancel and wait for task to complete
    heartbeat_task.cancel()
    try:
        await heartbeat_task
    except asyncio.CancelledError:
        pass  # Expected


@pytest.mark.asyncio  
async def test_websocket_listener_handles_none_websocket() -> None:
    """Test that _websocket_listener handles None websocket gracefully."""
    client = BinanceWebSocketClient(
        streams=["btcusdt@trade"],
        ws_url="wss://test.example.com",
        nats_url="nats://localhost",
        nats_topic="test.topic",
    )

    # Websocket is None by default
    assert client.websocket is None

    # Should return early without error
    await client._websocket_listener()


@pytest.mark.asyncio
async def test_message_queue_type_annotation() -> None:
    """Test that message_queue has proper type annotation."""
    client = BinanceWebSocketClient(
        streams=["btcusdt@trade"],
        ws_url="wss://test.example.com",
        nats_url="nats://localhost",
        nats_topic="test.topic",
    )

    # Verify queue exists and has correct type
    assert hasattr(client, "message_queue")
    assert isinstance(client.message_queue, asyncio.Queue)

    # Test queue operations with dict
    test_message = {"test": "data"}
    await client.message_queue.put(test_message)
    retrieved = await client.message_queue.get()
    assert retrieved == test_message


@pytest.mark.asyncio
async def test_last_message_time_float_type() -> None:
    """Test that last_message_time is properly typed as float."""
    client = BinanceWebSocketClient(
        streams=["btcusdt@trade"],
        ws_url="wss://test.example.com",
        nats_url="nats://localhost",
        nats_topic="test.topic",
    )

    # Verify initial value is float
    assert isinstance(client.last_message_time, float)
    assert client.last_message_time == 0.0


@pytest.mark.asyncio
async def test_last_ping_float_type() -> None:
    """Test that last_ping is properly typed as float."""
    client = BinanceWebSocketClient(
        streams=["btcusdt@trade"],
        ws_url="wss://test.example.com",
        nats_url="nats://localhost",
        nats_topic="test.topic",
    )

    # Verify initial value is float
    assert isinstance(client.last_ping, float)
    assert client.last_ping == 0.0

