# GitHub Copilot Instructions - Socket Client

## Service Context

**Purpose**: Real-time WebSocket client streaming market data from Binance to NATS message bus.

**Deployment**: Kubernetes Deployment with health checks and auto-scaling

**Role in Ecosystem**: Real-time data pipeline → NATS → TA Bot & Realtime Strategies

---

## Architecture

**Data Flow**:
```
Binance WebSocket → Socket Client → NATS (crypto.market.data) → TA Bot
                                                                 → Realtime Strategies
```

**Key Components**:
- `socket_client/core/client.py` - Main WebSocket client
- `socket_client/utils/circuit_breaker.py` - Fault tolerance
- `socket_client/health/server.py` - K8s health checks
- `socket_client/api/` - Runtime configuration API

---

## Service-Specific Patterns

### WebSocket Lifecycle

```python
# Connection management
async def _connect_websocket():
    # Use circuit breaker
    # Handle reconnection with backoff
    # Subscribe to streams

# ✅ GOOD - Graceful shutdown
async def stop():
    self.is_running = False
    await cancel_all_tasks()
    await close_connections()

# ❌ BAD - Abrupt shutdown
def stop():
    sys.exit(0)
```

### Circuit Breaker Pattern

```python
# ✅ Use for external connections
await websocket_circuit_breaker.call(connect_websocket)
await nats_circuit_breaker.call(connect_nats)

# Thresholds:
# - WebSocket: 5 failures, 60s recovery
# - NATS: 3 failures, 30s recovery
```

### Message Processing

```python
# ✅ GOOD - Async queue with multiple processors
for i in range(NUM_PROCESSORS):
    asyncio.create_task(process_messages(worker_id=i))

# Publish to NATS with trace context
message = inject_trace_context(message_dict)
await nats_client.publish(topic, message)
```

---

## Testing Patterns

```python
# Mock WebSocket
@pytest.fixture
def mock_websocket():
    with patch('websockets.connect') as mock:
        mock.return_value = AsyncMock()
        yield mock

# Test reconnection
@pytest.mark.asyncio
async def test_reconnection_backoff():
    # Verify exponential backoff on failures
    pass
```

---

## Common Issues

**Reconnection Storms**: Use exponential backoff  
**Message Queue Full**: Monitor dropped_messages metric  
**NATS Disconnections**: Circuit breaker prevents cascading failures

---

**Master Rules**: See `/Users/yurisa2/petrosa/petrosa_k8s/.cursorrules`  
**Service Rules**: `.cursorrules` in this repo

