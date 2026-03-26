import asyncio
import json
import os
import time
from unittest.mock import AsyncMock, MagicMock, PropertyMock, patch

import pytest
from pydantic import Field

from socket_client.heartbeat import HeartbeatMessage, HeartbeatPublisher


class TestHeartbeat:
    """Tests for the standardized heartbeat service."""

    def test_message_creation(self):
        """Test HeartbeatMessage serialization."""
        msg = HeartbeatMessage(status="healthy")
        assert msg.service == "socket-client"
        assert msg.status == "healthy"
        assert isinstance(msg.timestamp, float)
        
        # Test serialization compatibility
        data = json.loads(msg.to_json())
        assert data["service"] == "socket-client"
        assert data["status"] == "healthy"

    @pytest.mark.asyncio
    async def test_publisher_loop(self):
        """Test HeartbeatPublisher connects and publishes periodically."""
        publisher = HeartbeatPublisher(nats_url="nats://localhost:4222", subject="test.heartbeat")
        publisher.interval = 0.1  # Fast loop
        
        with patch("nats.connect", new_callable=AsyncMock) as mock_connect:
            mock_nats = AsyncMock()
            # Mock the is_connected property (NATS client property)
            p = PropertyMock(return_value=False)
            type(mock_nats).is_connected = p
            mock_connect.return_value = mock_nats
            
            # Run the publisher for a short while
            task = asyncio.create_task(publisher.start())
            await asyncio.sleep(0.1)  # First iteration (starts connection)
            
            # Toggle is_connected to True for subsequent iterations
            p.return_value = True
            
            await asyncio.sleep(0.2)  # Should publish more heartbeats
            publisher.stop()
            await task
            
            # Assertions
            mock_connect.assert_called()
            assert mock_nats.publish.call_count >= 2
            
            # Check subject used
            args, _ = mock_nats.publish.call_args
            assert args[0] == "test.heartbeat"

    @pytest.mark.asyncio
    async def test_publisher_error_handling(self):
        """Test publisher robustness on connection failure."""
        publisher = HeartbeatPublisher(nats_url="nats://localhost:4222")
        publisher.interval = 0.1
        
        with patch("nats.connect", side_effect=Exception("Connection failed")):
            # Should not crash the whole process, just log error and retry
            task = asyncio.create_task(publisher.start())
            await asyncio.sleep(0.15)
            publisher.stop()
            await task
            # If we reached here without uncaught exception, test passed

    @pytest.mark.asyncio
    async def test_subject_overrides(self):
        """Test subject precedence (Env vs Param)."""
        # 1. Param override
        pub1 = HeartbeatPublisher(nats_url="url", subject="param.subject")
        assert pub1.subject == "param.subject"
        
        # 2. Env override
        with patch.dict(os.environ, {"NATS_TOPIC_HEARTBEAT": "env.subject"}):
            pub2 = HeartbeatPublisher(nats_url="url")
            assert pub2.subject == "env.subject"
            
        # 3. Default
        pub3 = HeartbeatPublisher(nats_url="url")
        assert pub3.subject == "heartbeat.socket-client"
