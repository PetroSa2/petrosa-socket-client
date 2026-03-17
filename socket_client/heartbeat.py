"""
Heartbeat Service for SocketClient.
Publishes a heartbeat to NATS every 30 seconds.
"""

import asyncio
import json
import logging
import os
import time
from typing import Optional

import nats
import nats.aio.client
from pydantic import BaseModel, Field

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("heartbeat")


class HeartbeatMessage(BaseModel):
    """Standardized heartbeat message model."""
    service: str = "socket-client"
    timestamp: float = Field(default_factory=time.time)
    version: str = os.getenv("VERSION", "1.0.0")
    status: str = "healthy"

    def to_json(self) -> str:
        """Compatibility helper for Pydantic v1/v2."""
        if hasattr(self, "model_dump_json"):
            return self.model_dump_json()
        return self.json()


class HeartbeatPublisher:
    """Publishes periodic heartbeats to NATS."""

    def __init__(self, nats_url: str, subject: Optional[str] = None):
        self.service_name = "socket-client"
        self.nats_url = nats_url
        self.subject = subject or os.getenv("NATS_TOPIC_HEARTBEAT") or f"heartbeat.{self.service_name}"
        self.interval = 30.0  # seconds
        self.nats_client: Optional[nats.aio.client.Client] = None
        self.is_running = False

    async def start(self):
        """Start the heartbeat publication loop."""
        self.is_running = True
        while self.is_running:
            try:
                if not self.nats_client or not self.nats_client.is_connected:
                    logger.info(f"Connecting to NATS at {self.nats_url}")
                    self.nats_client = await nats.connect(self.nats_url)

                message = HeartbeatMessage()
                await self.nats_client.publish(self.subject, message.to_json().encode())
                logger.debug(f"Published heartbeat to {self.subject}")

            except Exception as e:
                logger.error(f"Error publishing heartbeat: {e}")
                self.nats_client = None

            await asyncio.sleep(self.interval)

    def stop(self):
        """Stop the heartbeat loop."""
        self.is_running = False


async def main():
    nats_url = os.getenv("NATS_URL", "nats://localhost:4222")
    subject = os.getenv("NATS_TOPIC_HEARTBEAT")

    logger.info(f"🚀 Starting heartbeat service for socket-client on {subject or 'heartbeat.socket-client'}")
    publisher = HeartbeatPublisher(nats_url, subject)
    await publisher.start()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
