"""
Performance benchmark tests for the Petrosa Socket Client.

Tests cover throughput, latency, memory usage, connection handling,
and scalability under various load conditions.
"""

import asyncio
import time
import psutil
import os
import json
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import AsyncMock, Mock, patch
import pytest

from socket_client.core.client import BinanceWebSocketClient
from socket_client.models.message import WebSocketMessage
from socket_client.utils.circuit_breaker import AsyncCircuitBreaker


@pytest.mark.performance
class TestMessageThroughputPerformance:
    """Test message processing throughput performance."""

    @pytest.mark.asyncio
    async def test_high_frequency_message_processing(self):
        """Test processing high-frequency message streams."""
        mock_nats = AsyncMock()
        
        client = BinanceWebSocketClient(
            ws_url="wss://test.binance.com/ws",
            streams=["btcusdt@trade"],
            nats_url="nats://localhost:4222",
            nats_topic="crypto.trades"
        )
        client.nats_client = mock_nats
        
        # Generate high-frequency messages
        messages = []
        for i in range(10000):
            message = {
                "stream": "btcusdt@trade",
                "data": {
                    "e": "trade",
                    "s": "BTCUSDT",
                    "t": i,
                    "p": f"{50000 + (i % 1000)}",
                    "q": "1.0",
                    "T": int(time.time() * 1000) + i
                }
            }
            messages.append(json.dumps(message))
        
        # Measure processing time
        start_time = time.time()
        
        # Process messages sequentially
        for msg in messages:
            await client._handle_message(msg)
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        # Calculate throughput
        throughput = len(messages) / processing_time
        
        # Should process at least 1000 messages per second
        assert throughput >= 1000, f"Throughput: {throughput:.2f} msg/sec"
        assert mock_nats.publish.call_count == 10000

    @pytest.mark.asyncio
    async def test_concurrent_message_processing(self):
        """Test concurrent message processing performance."""
        mock_nats = AsyncMock()
        
        client = BinanceWebSocketClient(
            ws_url="wss://test.binance.com/ws",
            streams=["btcusdt@trade"],
            nats_url="nats://localhost:4222",
            nats_topic="crypto.trades"
        )
        client.nats_client = mock_nats
        
        # Generate messages
        messages = []
        for i in range(1000):
            message = {
                "stream": "btcusdt@trade",
                "data": {"e": "trade", "t": i, "p": f"{50000 + i}"}
            }
            messages.append(json.dumps(message))
        
        # Measure concurrent processing
        start_time = time.time()
        
        # Process messages concurrently
        tasks = [client._handle_message(msg) for msg in messages]
        await asyncio.gather(*tasks)
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        # Concurrent processing should be faster
        throughput = len(messages) / processing_time
        assert throughput >= 2000, f"Concurrent throughput: {throughput:.2f} msg/sec"

    @pytest.mark.asyncio
    async def test_message_processing_latency(self):
        """Test individual message processing latency."""
        mock_nats = AsyncMock()
        
        client = BinanceWebSocketClient(
            ws_url="wss://test.binance.com/ws",
            streams=["btcusdt@trade"],
            nats_url="nats://localhost:4222",
            nats_topic="crypto.trades"
        )
        client.nats_client = mock_nats
        
        message = json.dumps({
            "stream": "btcusdt@trade",
            "data": {"e": "trade", "s": "BTCUSDT", "p": "50000"}
        })
        
        # Measure latency for single message
        latencies = []
        for _ in range(100):
            start_time = time.perf_counter()
            await client._handle_message(message)
            end_time = time.perf_counter()
            latencies.append((end_time - start_time) * 1000)  # Convert to milliseconds
        
        avg_latency = sum(latencies) / len(latencies)
        p95_latency = sorted(latencies)[int(len(latencies) * 0.95)]
        
        # Latency should be low
        assert avg_latency < 10.0, f"Average latency: {avg_latency:.2f}ms"
        assert p95_latency < 20.0, f"P95 latency: {p95_latency:.2f}ms"

    @pytest.mark.asyncio
    async def test_batch_message_processing(self):
        """Test batch message processing performance."""
        mock_nats = AsyncMock()
        
        client = BinanceWebSocketClient(
            ws_url="wss://test.binance.com/ws",
            streams=["btcusdt@trade"],
            nats_url="nats://localhost:4222",
            nats_topic="crypto.trades"
        )
        client.nats_client = mock_nats
        
        # Create message batches
        batch_sizes = [10, 50, 100, 500, 1000]
        
        for batch_size in batch_sizes:
            messages = [
                json.dumps({
                    "stream": "btcusdt@trade",
                    "data": {"e": "trade", "t": i}
                })
                for i in range(batch_size)
            ]
            
            start_time = time.time()
            
            # Process batch
            for msg in messages:
                await client._handle_message(msg)
            
            end_time = time.time()
            batch_time = end_time - start_time
            throughput = batch_size / batch_time
            
            # Throughput should scale with batch size
            assert throughput >= batch_size * 0.8, f"Batch {batch_size} throughput: {throughput:.2f}"


@pytest.mark.performance
class TestMemoryUsagePerformance:
    """Test memory usage and garbage collection performance."""

    @pytest.mark.asyncio
    async def test_memory_usage_under_load(self):
        """Test memory usage under sustained message load."""
        import gc
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        mock_nats = AsyncMock()
        
        client = BinanceWebSocketClient(
            ws_url="wss://test.binance.com/ws",
            streams=["btcusdt@trade"],
            nats_url="nats://localhost:4222",
            nats_topic="crypto.trades"
        )
        client.nats_client = mock_nats
        
        # Process many messages to test memory usage
        for batch in range(10):
            messages = [
                json.dumps({
                    "stream": "btcusdt@trade",
                    "data": {
                        "e": "trade",
                        "t": batch * 1000 + i,
                        "p": f"{50000 + i}",
                        "large_data": "x" * 1000  # Add some data size
                    }
                })
                for i in range(1000)
            ]
            
            for msg in messages:
                await client._handle_message(msg)
            
            # Force garbage collection
            gc.collect()
            
            current_memory = process.memory_info().rss / 1024 / 1024
            memory_increase = current_memory - initial_memory
            
            # Memory should not grow excessively
            assert memory_increase < 50, f"Memory increased by {memory_increase:.2f}MB after batch {batch}"

    @pytest.mark.asyncio
    async def test_message_object_cleanup(self):
        """Test proper cleanup of message objects."""
        import weakref
        
        mock_nats = AsyncMock()
        
        client = BinanceWebSocketClient(
            ws_url="wss://test.binance.com/ws",
            streams=["btcusdt@trade"],
            nats_url="nats://localhost:4222",
            nats_topic="crypto.trades"
        )
        client.nats_client = mock_nats
        
        # Track message objects with weak references
        weak_refs = []
        
        for i in range(100):
            message_data = {
                "stream": "btcusdt@trade",
                "data": {"e": "trade", "t": i}
            }
            
            # Create message object and track it
            msg_obj = WebSocketMessage(**message_data)
            weak_refs.append(weakref.ref(msg_obj))
            
            # Process the message
            await client._handle_message(json.dumps(message_data))
            
            # Clear local reference
            del msg_obj
        
        # Force garbage collection
        import gc
        gc.collect()
        
        # Check that objects were cleaned up
        alive_objects = sum(1 for ref in weak_refs if ref() is not None)
        cleanup_rate = (len(weak_refs) - alive_objects) / len(weak_refs)
        
        # Most objects should be cleaned up
        assert cleanup_rate >= 0.9, f"Cleanup rate: {cleanup_rate:.2%}"

    def test_connection_pool_memory_efficiency(self):
        """Test memory efficiency of connection pooling."""
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024
        
        # Create multiple client instances
        clients = []
        for i in range(50):
            client = BinanceWebSocketClient(
                ws_url=f"wss://test{i}.binance.com/ws",
                streams=[f"symbol{i}@trade"],
                nats_url="nats://localhost:4222",
                nats_topic=f"crypto.trades{i}"
            )
            clients.append(client)
        
        current_memory = process.memory_info().rss / 1024 / 1024
        memory_per_client = (current_memory - initial_memory) / len(clients)
        
        # Each client should use reasonable memory
        assert memory_per_client < 5.0, f"Memory per client: {memory_per_client:.2f}MB"
        
        # Cleanup
        del clients
        import gc
        gc.collect()


@pytest.mark.performance
class TestConnectionPerformance:
    """Test WebSocket connection performance."""

    @pytest.mark.asyncio
    async def test_connection_establishment_time(self):
        """Test WebSocket connection establishment performance."""
        with patch('websockets.connect') as mock_connect, \
             patch('nats.connect') as mock_nats_connect:
            
            mock_websocket = AsyncMock()
            mock_websocket.closed = False
            mock_connect.return_value.__aenter__.return_value = mock_websocket
            
            mock_nats = AsyncMock()
            mock_nats_connect.return_value = mock_nats
            
            client = BinanceWebSocketClient(
                ws_url="wss://test.binance.com/ws",
                streams=["btcusdt@trade"],
                nats_url="nats://localhost:4222",
                nats_topic="crypto.trades"
            )
            
            # Measure connection time
            start_time = time.time()
            await client._connect()
            end_time = time.time()
            
            connection_time = end_time - start_time
            
            # Connection should be fast
            assert connection_time < 5.0, f"Connection time: {connection_time:.2f}s"

    @pytest.mark.asyncio
    async def test_reconnection_performance(self):
        """Test reconnection performance after failures."""
        connection_times = []
        
        with patch('websockets.connect') as mock_connect, \
             patch('nats.connect') as mock_nats_connect:
            
            mock_websocket = AsyncMock()
            mock_websocket.closed = False
            mock_connect.return_value.__aenter__.return_value = mock_websocket
            
            mock_nats = AsyncMock()
            mock_nats_connect.return_value = mock_nats
            
            client = BinanceWebSocketClient(
                ws_url="wss://test.binance.com/ws",
                streams=["btcusdt@trade"],
                nats_url="nats://localhost:4222",
                nats_topic="crypto.trades",
                reconnect_delay=0.1  # Fast reconnection for testing
            )
            
            # Test multiple reconnections
            for _ in range(5):
                start_time = time.time()
                await client._reconnect()
                end_time = time.time()
                
                connection_times.append(end_time - start_time)
            
            avg_reconnection_time = sum(connection_times) / len(connection_times)
            
            # Reconnections should be fast
            assert avg_reconnection_time < 2.0, f"Avg reconnection time: {avg_reconnection_time:.2f}s"

    @pytest.mark.asyncio
    async def test_concurrent_connections(self):
        """Test performance with multiple concurrent connections."""
        with patch('websockets.connect') as mock_connect, \
             patch('nats.connect') as mock_nats_connect:
            
            mock_websocket = AsyncMock()
            mock_websocket.closed = False
            mock_connect.return_value.__aenter__.return_value = mock_websocket
            
            mock_nats = AsyncMock()
            mock_nats_connect.return_value = mock_nats
            
            # Create multiple clients
            clients = [
                BinanceWebSocketClient(
                    ws_url=f"wss://test{i}.binance.com/ws",
                    streams=[f"symbol{i}@trade"],
                    nats_url="nats://localhost:4222",
                    nats_topic=f"crypto.trades{i}"
                )
                for i in range(10)
            ]
            
            # Connect all clients concurrently
            start_time = time.time()
            
            tasks = [client._connect() for client in clients]
            await asyncio.gather(*tasks)
            
            end_time = time.time()
            total_time = end_time - start_time
            
            # All connections should complete quickly
            assert total_time < 10.0, f"Concurrent connection time: {total_time:.2f}s"
            
            # Cleanup
            for client in clients:
                await client._disconnect()


@pytest.mark.performance
class TestCircuitBreakerPerformance:
    """Test circuit breaker performance impact."""

    @pytest.mark.asyncio
    async def test_circuit_breaker_overhead(self):
        """Test performance overhead of circuit breaker."""
        cb = AsyncCircuitBreaker(name="test")
        
        async def fast_function():
            return "result"
        
        # Measure time without circuit breaker
        start_time = time.time()
        for _ in range(1000):
            await fast_function()
        direct_time = time.time() - start_time
        
        # Measure time with circuit breaker
        start_time = time.time()
        for _ in range(1000):
            await cb.call(fast_function)
        cb_time = time.time() - start_time
        
        # Calculate overhead
        overhead_ratio = cb_time / direct_time if direct_time > 0 else float('inf')
        
        # Overhead should be minimal
        assert overhead_ratio < 2.0, f"Circuit breaker overhead: {overhead_ratio:.2f}x"

    @pytest.mark.asyncio
    async def test_circuit_breaker_under_load(self):
        """Test circuit breaker performance under high load."""
        cb = AsyncCircuitBreaker(failure_threshold=10, name="test")
        
        call_count = 0
        
        async def load_function():
            nonlocal call_count
            call_count += 1
            if call_count % 100 == 0:  # Occasional failures
                raise Exception("Load test failure")
            return "success"
        
        start_time = time.time()
        
        # Make many calls
        results = []
        for _ in range(1000):
            try:
                result = await cb.call(load_function)
                results.append(result)
            except Exception:
                pass  # Expected failures
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # Should handle load efficiently
        assert total_time < 5.0, f"Load test time: {total_time:.2f}s"
        assert len(results) > 900  # Most calls should succeed


@pytest.mark.performance
class TestScalabilityPerformance:
    """Test scalability under various conditions."""

    @pytest.mark.asyncio
    async def test_stream_scalability(self):
        """Test performance with increasing number of streams."""
        mock_nats = AsyncMock()
        
        stream_counts = [1, 10, 50, 100]
        
        for stream_count in stream_counts:
            streams = [f"symbol{i}@trade" for i in range(stream_count)]
            
            client = BinanceWebSocketClient(
                ws_url="wss://test.binance.com/ws",
                streams=streams,
                nats_url="nats://localhost:4222",
                nats_topic="crypto.trades"
            )
            client.nats_client = mock_nats
            
            # Generate messages for all streams
            messages = []
            for i in range(stream_count):
                message = json.dumps({
                    "stream": f"symbol{i}@trade",
                    "data": {"e": "trade", "s": f"SYMBOL{i}"}
                })
                messages.append(message)
            
            # Measure processing time
            start_time = time.time()
            
            for msg in messages:
                await client._handle_message(msg)
            
            end_time = time.time()
            processing_time = end_time - start_time
            
            # Processing time should scale reasonably
            time_per_stream = processing_time / stream_count
            assert time_per_stream < 0.01, f"Time per stream ({stream_count}): {time_per_stream:.4f}s"

    @pytest.mark.asyncio
    async def test_message_size_scalability(self):
        """Test performance with varying message sizes."""
        mock_nats = AsyncMock()
        
        client = BinanceWebSocketClient(
            ws_url="wss://test.binance.com/ws",
            streams=["btcusdt@trade"],
            nats_url="nats://localhost:4222",
            nats_topic="crypto.trades"
        )
        client.nats_client = mock_nats
        
        message_sizes = [100, 1000, 10000, 50000]  # bytes
        
        for size in message_sizes:
            large_data = "x" * (size - 100)  # Account for base message size
            
            message = json.dumps({
                "stream": "btcusdt@trade",
                "data": {
                    "e": "trade",
                    "s": "BTCUSDT",
                    "large_field": large_data
                }
            })
            
            # Measure processing time for large messages
            start_time = time.time()
            
            for _ in range(10):  # Process multiple times
                await client._handle_message(message)
            
            end_time = time.time()
            avg_time = (end_time - start_time) / 10
            
            # Processing time should not increase dramatically with size
            assert avg_time < 0.1, f"Time for {size}B message: {avg_time:.4f}s"

    def test_cpu_usage_efficiency(self):
        """Test CPU usage efficiency under load."""
        import threading
        import queue
        
        # Monitor CPU usage
        process = psutil.Process(os.getpid())
        cpu_samples = queue.Queue()
        
        def monitor_cpu():
            for _ in range(20):  # Sample for 2 seconds
                cpu_samples.put(process.cpu_percent())
                time.sleep(0.1)
        
        # Start CPU monitoring
        monitor_thread = threading.Thread(target=monitor_cpu)
        monitor_thread.start()
        
        # Simulate load
        async def simulate_load():
            mock_nats = AsyncMock()
            
            client = BinanceWebSocketClient(
                ws_url="wss://test.binance.com/ws",
                streams=["btcusdt@trade"],
                nats_url="nats://localhost:4222",
                nats_topic="crypto.trades"
            )
            client.nats_client = mock_nats
            
            # Process many messages
            for i in range(1000):
                message = json.dumps({
                    "stream": "btcusdt@trade",
                    "data": {"e": "trade", "t": i}
                })
                await client._handle_message(message)
        
        # Run load simulation
        asyncio.run(simulate_load())
        
        # Wait for monitoring to complete
        monitor_thread.join()
        
        # Analyze CPU usage
        cpu_values = []
        while not cpu_samples.empty():
            cpu_values.append(cpu_samples.get())
        
        if cpu_values:
            avg_cpu = sum(cpu_values) / len(cpu_values)
            max_cpu = max(cpu_values)
            
            # CPU usage should be reasonable
            assert avg_cpu < 80.0, f"Average CPU usage: {avg_cpu:.2f}%"
            assert max_cpu < 95.0, f"Peak CPU usage: {max_cpu:.2f}%"


@pytest.mark.performance
class TestPerformanceRegression:
    """Test for performance regressions."""

    @pytest.mark.asyncio
    async def test_baseline_performance_metrics(self):
        """Establish baseline performance metrics."""
        mock_nats = AsyncMock()
        
        client = BinanceWebSocketClient(
            ws_url="wss://test.binance.com/ws",
            streams=["btcusdt@trade"],
            nats_url="nats://localhost:4222",
            nats_topic="crypto.trades"
        )
        client.nats_client = mock_nats
        
        # Standard test message
        message = json.dumps({
            "stream": "btcusdt@trade",
            "data": {
                "e": "trade",
                "s": "BTCUSDT",
                "t": 12345,
                "p": "50000.00",
                "q": "1.0"
            }
        })
        
        # Measure baseline metrics
        message_count = 1000
        
        start_time = time.time()
        for _ in range(message_count):
            await client._handle_message(message)
        end_time = time.time()
        
        processing_time = end_time - start_time
        throughput = message_count / processing_time
        
        # Store baseline metrics (in real implementation, these would be stored)
        baseline_metrics = {
            "throughput": throughput,
            "processing_time": processing_time,
            "messages_processed": message_count
        }
        
        # Verify baseline meets minimum requirements
        assert baseline_metrics["throughput"] >= 1000  # 1000 msg/sec minimum
        assert baseline_metrics["processing_time"] <= 5.0  # Max 5 seconds for 1000 messages
        
        # In a real test suite, you would compare against stored baselines
        # and alert if performance degrades beyond acceptable thresholds
