"""
Binance WebSocket client implementation.

This module provides the main WebSocket client that connects to Binance
and forwards messages to NATS with proper error handling and reconnection logic.
"""

import asyncio
import json
import time
import uuid
from typing import Any, Optional

import nats
import websockets
from nats.aio.client import Client as NATSClient
from structlog import get_logger

import constants
from socket_client.models.message import create_message
from socket_client.utils.circuit_breaker import (
    nats_circuit_breaker,
    websocket_circuit_breaker,
)

logger = get_logger(__name__)


class BinanceWebSocketClient:
    """Binance WebSocket client with NATS integration."""

    def __init__(
        self,
        ws_url: str,
        streams: list[str],
        nats_url: str,
        nats_topic: str,
        logger: Optional[Any] = None,
        max_reconnect_attempts: Optional[int] = None,
        reconnect_delay: Optional[int] = None,
        ping_interval: Optional[int] = None,
        ping_timeout: Optional[int] = None,
    ) -> None:
        """
        Initialize the WebSocket client.

        Args:
            ws_url: Binance WebSocket URL
            streams: List of streams to subscribe to
            nats_url: NATS server URL
            nats_topic: NATS topic for publishing messages
            logger: Logger instance
            max_reconnect_attempts: Maximum reconnection attempts
            reconnect_delay: Reconnection delay in seconds
            ping_interval: WebSocket ping interval
            ping_timeout: WebSocket ping timeout
        """
        self.ws_url = ws_url
        self.streams = streams
        self.nats_url = nats_url
        self.nats_topic = nats_topic
        self.logger = logger or get_logger(__name__)

        # Connection settings
        self.max_reconnect_attempts = (
            max_reconnect_attempts or constants.WEBSOCKET_MAX_RECONNECT_ATTEMPTS
        )
        self.reconnect_delay = reconnect_delay or constants.WEBSOCKET_RECONNECT_DELAY
        self.ping_interval = ping_interval or constants.WEBSOCKET_PING_INTERVAL
        self.ping_timeout = ping_timeout or constants.WEBSOCKET_PING_TIMEOUT

        # Connection state
        self.websocket: Optional[Any] = None  # websockets.WebSocketClientProtocol
        self.nats_client: Optional[NATSClient] = None
        self.is_connected = False
        self.is_running = False
        self.reconnect_attempts = 0
        self.last_ping: float = 0.0

        # Message processing
        self.message_queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue(
            maxsize=constants.MAX_QUEUE_SIZE
        )
        self.processed_messages = 0
        self.dropped_messages = 0
        self.last_message_time: float = 0.0

        # Heartbeat statistics
        self.start_time = time.time()
        self.last_heartbeat_time = time.time()
        self.last_heartbeat_processed = 0
        self.last_heartbeat_dropped = 0

        # Message processing stats logging throttle
        self.last_stats_log_time = time.time()
        self.stats_log_interval = 60  # Log message stats at most once per minute

        # Parallel processing
        self.num_processors = constants.NUM_MESSAGE_PROCESSORS

        # Tasks
        self.websocket_task: Optional[asyncio.Task] = None
        self.nats_task: Optional[asyncio.Task] = None
        self.processor_tasks: list[asyncio.Task] = []
        self.ping_task: Optional[asyncio.Task] = None
        self.heartbeat_task: Optional[asyncio.Task] = None

        self.logger.info(
            "WebSocket client initialized",
            ws_url=ws_url,
            streams=streams,
            nats_url=nats_url,
            nats_topic=nats_topic,
            num_processors=self.num_processors,
            max_queue_size=constants.MAX_QUEUE_SIZE,
            heartbeat_enabled=constants.ENABLE_HEARTBEAT,
            heartbeat_interval=constants.HEARTBEAT_INTERVAL
            if constants.ENABLE_HEARTBEAT
            else None,
        )

    async def start(self) -> None:
        """Start the WebSocket client."""
        self.logger.info("Starting WebSocket client")
        self.is_running = True

        try:
            # Start NATS connection
            await self._connect_nats()

            # Start multiple message processors for parallel processing
            for i in range(self.num_processors):
                task = asyncio.create_task(self._process_messages(worker_id=i))
                self.processor_tasks.append(task)

            self.logger.info(
                "Started parallel message processors",
                num_processors=self.num_processors,
            )

            # Start WebSocket connection
            await self._connect_websocket()

            # Start ping task
            self.ping_task = asyncio.create_task(self._ping_loop())

            # Start heartbeat task if enabled
            if constants.ENABLE_HEARTBEAT:
                self.heartbeat_task = asyncio.create_task(self._heartbeat_loop())

            self.logger.info("WebSocket client started successfully")

        except Exception as e:
            self.logger.error(f"Failed to start WebSocket client: {e}")
            await self.stop()
            raise

    async def stop(self) -> None:
        """Stop the WebSocket client gracefully."""
        self.logger.info("Stopping WebSocket client")
        self.is_running = False

        # Cancel tasks
        tasks_to_cancel = [
            self.websocket_task,
            self.nats_task,
            self.ping_task,
            self.heartbeat_task,
        ] + self.processor_tasks

        for task in tasks_to_cancel:
            if task and not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

        # Close connections
        if self.websocket:
            try:
                await self.websocket.close()
            except Exception as e:
                self.logger.warning(f"Error closing WebSocket: {e}")

        if self.nats_client:
            await self.nats_client.close()

        self.is_connected = False
        self.logger.info("WebSocket client stopped")

    async def _connect_websocket(self) -> None:
        """Connect to Binance WebSocket."""
        try:
            # Build subscription message
            subscribe_message = {
                "method": "SUBSCRIBE",
                "params": self.streams,
                "id": int(time.time() * 1000),
            }

            # Connect with circuit breaker protection
            connect = await websocket_circuit_breaker.call(
                websockets.connect,
                self.ws_url,
                ping_interval=self.ping_interval,
                ping_timeout=self.ping_timeout,
                close_timeout=constants.WEBSOCKET_CLOSE_TIMEOUT,
            )

            # Get the actual connection from the context manager
            self.websocket = await connect.__aenter__()

            # Send subscription message
            await self.websocket.send(json.dumps(subscribe_message))

            # Start WebSocket listener
            self.websocket_task = asyncio.create_task(self._websocket_listener())

            self.is_connected = True
            self.reconnect_attempts = 0

            self.logger.info(
                "Connected to Binance WebSocket", streams=self.streams, url=self.ws_url
            )

        except Exception as e:
            self.logger.error(f"Failed to connect to WebSocket: {e}")
            self.is_connected = False
            raise

    async def _connect_nats(self) -> None:
        """Connect to NATS server."""
        try:
            # Circuit breaker expects a callable returning T directly, but nats.connect
            # returns an async context manager (to be used with 'async with'), hence the type
            # mismatch and the need for type: ignore[arg-type]
            self.nats_client = await nats_circuit_breaker.call(
                nats.connect,  # type: ignore[arg-type]
                self.nats_url,
                name=constants.NATS_CLIENT_NAME,
            )

            self.logger.info(f"Connected to NATS server: {self.nats_url}")

        except Exception as e:
            self.logger.error(f"Failed to connect to NATS: {e}")
            raise

    async def _websocket_listener(self) -> None:
        """Listen for WebSocket messages."""
        try:
            if self.websocket is None:
                return
            async for message in self.websocket:
                if not self.is_running:
                    break

                try:
                    # Parse message
                    data = json.loads(message)

                    # Update last message time
                    self.last_message_time = time.time()

                    # Add to processing queue
                    try:
                        self.message_queue.put_nowait(data)
                    except asyncio.QueueFull:
                        self.dropped_messages += 1
                        self.logger.warning(
                            "Message queue full, dropping message",
                            dropped_count=self.dropped_messages,
                        )

                except json.JSONDecodeError as e:
                    self.logger.error(f"Failed to parse WebSocket message: {e}")
                except Exception as e:
                    self.logger.error(f"Error processing WebSocket message: {e}")

        except websockets.exceptions.ConnectionClosed:
            self.logger.warning("WebSocket connection closed")
        except Exception as e:
            self.logger.error(f"WebSocket listener error: {e}")
        finally:
            self.is_connected = False
            await self._handle_disconnection()

    async def _process_messages(self, worker_id: int = 0) -> None:
        """
        Process messages from the queue and publish to NATS.

        Args:
            worker_id: ID of this worker for logging/debugging
        """
        self.logger.info(f"Message processor worker {worker_id} started")

        while self.is_running:
            try:
                # Get message from queue with timeout
                try:
                    data = await asyncio.wait_for(
                        self.message_queue.get(),
                        timeout=constants.MESSAGE_BATCH_TIMEOUT,
                    )
                except asyncio.TimeoutError:
                    continue

                # Process message
                await self._process_single_message(data)

                # Mark as done
                self.message_queue.task_done()

            except Exception as e:
                self.logger.error(
                    f"Error processing message in worker {worker_id}: {e}",
                    worker_id=worker_id,
                )

        self.logger.info(f"Message processor worker {worker_id} stopped")

    async def _process_single_message(self, data: dict) -> None:
        """Process a single message."""
        try:
            # Validate message format - Binance WebSocket messages come as direct JSON objects
            # Note: isinstance check is defensive code for runtime safety, though type hints declare dict
            if not isinstance(data, dict):
                self.logger.warning(
                    "Invalid message format - not a dictionary", data=data
                )
                return

            # Determine stream name from message type
            stream_name = self._determine_stream_name(data)
            if not stream_name:
                self.logger.warning("Could not determine stream name", data=data)
                return

            # Create message object
            message = create_message(
                stream=stream_name, data=data, message_id=str(uuid.uuid4())
            )

            # Publish to NATS
            if self.nats_client and not self.nats_client.is_closed:
                try:
                    await self.nats_client.publish(
                        self.nats_topic, message.to_json().encode("utf-8")
                    )

                    self.processed_messages += 1

                    # Log stats at most once per minute instead of every 100 messages
                    current_time = time.time()
                    if (
                        current_time - self.last_stats_log_time
                        >= self.stats_log_interval
                    ):
                        self.logger.info(
                            "Message processing stats",
                            processed=self.processed_messages,
                            dropped=self.dropped_messages,
                            messages_per_second=round(
                                self.processed_messages
                                / (current_time - self.start_time),
                                2,
                            )
                            if (current_time - self.start_time) > 0
                            else 0,
                        )
                        self.last_stats_log_time = current_time

                except Exception as e:
                    self.logger.error(f"Failed to publish to NATS: {e}")
            else:
                self.logger.warning("NATS client not connected, dropping message")
                self.dropped_messages += 1

        except Exception as e:
            self.logger.error(f"Error processing single message: {e}")

    def _determine_stream_name(self, data: dict) -> Optional[str]:
        """
        Determine stream name from message data.

        Args:
            data: Message data from Binance WebSocket

        Returns:
            Stream name or None if cannot determine
        """
        try:
            # Get event type and symbol from message
            event_type = data.get("e", "")
            symbol = data.get("s", "")

            # Handle depth updates (order book data)
            if "lastUpdateId" in data and "bids" in data and "asks" in data:
                # This is a depth update message
                if symbol:
                    return f"{symbol.lower()}@depth20@100ms"
                else:
                    # Try to determine symbol from the data structure
                    # For depth updates, we need to infer the symbol from context
                    # Since we're subscribed to specific streams, we can use the first stream
                    if self.streams:
                        # Extract symbol from the first stream (e.g., "btcusdt@depth20@100ms" -> "btcusdt")
                        first_stream = self.streams[0]
                        if "@" in first_stream:
                            symbol = first_stream.split("@")[0]
                            return f"{symbol}@depth20@100ms"

            if not event_type or not symbol:
                return None

            # Map event types to stream names
            if event_type == "trade":
                return f"{symbol.lower()}@trade"
            elif event_type == "24hrTicker":
                return f"{symbol.lower()}@ticker"
            elif event_type == "depthUpdate":
                return f"{symbol.lower()}@depth20@100ms"
            elif event_type == "markPriceUpdate":
                return f"{symbol.lower()}@markPrice@1s"
            elif event_type == "fundingRate":
                return f"{symbol.lower()}@fundingRate@1s"
            else:
                # For unknown event types, create a generic stream name
                return f"{symbol.lower()}@{event_type}"

        except Exception as e:
            self.logger.error(f"Error determining stream name: {e}")
            return None

    async def _ping_loop(self) -> None:
        """Send periodic pings to keep connection alive."""
        while self.is_running and self.is_connected:
            try:
                await asyncio.sleep(self.ping_interval)

                if self.websocket and not self.websocket.closed:
                    await self.websocket.ping()
                    self.last_ping = time.time()

            except Exception as e:
                self.logger.error(f"Ping error: {e}")
                break

    async def _heartbeat_loop(self) -> None:
        """Send periodic heartbeat logs with message processing statistics."""
        while self.is_running:
            try:
                await asyncio.sleep(constants.HEARTBEAT_INTERVAL)

                # Defensive check for race conditions where is_running could change between iterations
                if not self.is_running:
                    break

                await self._log_heartbeat_stats()

            except Exception as e:
                self.logger.error(f"Heartbeat error: {e}")
                break

    async def _log_heartbeat_stats(self) -> None:
        """Log heartbeat statistics."""
        current_time = time.time()
        time_since_last_heartbeat = current_time - self.last_heartbeat_time
        time_since_start = current_time - self.start_time

        # Calculate messages processed since last heartbeat
        messages_processed_since_last = (
            self.processed_messages - self.last_heartbeat_processed
        )
        messages_dropped_since_last = (
            self.dropped_messages - self.last_heartbeat_dropped
        )

        # Calculate rates
        messages_per_second = (
            messages_processed_since_last / time_since_last_heartbeat
            if time_since_last_heartbeat > 0
            else 0
        )

        overall_messages_per_second = (
            self.processed_messages / time_since_start if time_since_start > 0 else 0
        )

        # Calculate queue utilization percentage
        queue_utilization = (
            (self.message_queue.qsize() / constants.MAX_QUEUE_SIZE) * 100
            if constants.MAX_QUEUE_SIZE > 0
            else 0
        )

        # Time since last message received
        time_since_last_message = (
            current_time - self.last_message_time if self.last_message_time > 0 else 0
        )

        # Log comprehensive heartbeat statistics
        self.logger.info(
            "HEARTBEAT: WebSocket Client Statistics",
            # Connection status
            connection_status=self.is_connected,
            websocket_state="connected"
            if self.websocket and not self.websocket.closed
            else "disconnected",
            nats_state="connected"
            if self.nats_client and not self.nats_client.is_closed
            else "disconnected",
            # Message processing stats since last heartbeat
            messages_processed_since_last=messages_processed_since_last,
            messages_dropped_since_last=messages_dropped_since_last,
            messages_per_second=round(messages_per_second, 2),
            # Overall stats since start
            total_processed=self.processed_messages,
            total_dropped=self.dropped_messages,
            overall_rate_per_second=round(overall_messages_per_second, 2),
            # Queue and timing info
            queue_size=self.message_queue.qsize(),
            queue_utilization_percent=round(queue_utilization, 2),
            time_since_last_message_seconds=round(time_since_last_message, 2),
            # Uptime and intervals
            uptime_seconds=round(time_since_start, 2),
            heartbeat_interval_seconds=constants.HEARTBEAT_INTERVAL,
            # Connection health
            reconnect_attempts=self.reconnect_attempts,
            last_ping_seconds_ago=round(current_time - self.last_ping, 2)
            if self.last_ping > 0
            else None,
        )

        # Update heartbeat tracking variables
        self.last_heartbeat_time = current_time
        self.last_heartbeat_processed = self.processed_messages
        self.last_heartbeat_dropped = self.dropped_messages

    async def _handle_disconnection(self) -> None:
        """Handle WebSocket disconnection with reconnection logic."""
        if not self.is_running:
            return

        self.logger.warning("WebSocket disconnected, attempting reconnection")

        while self.is_running and self.reconnect_attempts < self.max_reconnect_attempts:
            try:
                await asyncio.sleep(self.reconnect_delay * (2**self.reconnect_attempts))

                self.logger.info(
                    f"Attempting reconnection {self.reconnect_attempts + 1}/{self.max_reconnect_attempts}"
                )

                await self._connect_websocket()
                break

            except Exception as e:
                self.reconnect_attempts += 1
                self.logger.error(
                    f"Reconnection attempt {self.reconnect_attempts} failed: {e}"
                )

        if self.reconnect_attempts >= self.max_reconnect_attempts:
            self.logger.error("Max reconnection attempts reached, stopping client")
            self.is_running = False

    def get_metrics(self) -> dict:
        """Get client metrics."""
        current_time = time.time()
        uptime = current_time - self.start_time

        return {
            "is_connected": self.is_connected,
            "is_running": self.is_running,
            "connection_status": "connected" if self.is_connected else "disconnected",
            "reconnect_attempts": self.reconnect_attempts,
            "processed_messages": self.processed_messages,
            "dropped_messages": self.dropped_messages,
            "stream_count": len(self.streams),
            "streams": self.streams.copy(),
            "uptime": uptime,
            "queue_size": self.message_queue.qsize(),
            "last_message_time": self.last_message_time,
            "last_ping": self.last_ping,
            "websocket_state": "connected"
            if self.websocket and not self.websocket.closed
            else "disconnected",
            "nats_state": "connected"
            if self.nats_client and not self.nats_client.is_closed
            else "disconnected",
            # Heartbeat-related metrics
            "uptime_seconds": round(uptime, 2),
            "messages_per_second": round(self.processed_messages / uptime, 2)
            if uptime > 0
            else 0,
            "queue_utilization_percent": round(
                (self.message_queue.qsize() / constants.MAX_QUEUE_SIZE) * 100, 2
            )
            if constants.MAX_QUEUE_SIZE > 0
            else 0,
            "time_since_last_message": round(current_time - self.last_message_time, 2)
            if self.last_message_time > 0
            else None,
            "heartbeat_enabled": constants.ENABLE_HEARTBEAT,
            "heartbeat_interval": constants.HEARTBEAT_INTERVAL,
        }
