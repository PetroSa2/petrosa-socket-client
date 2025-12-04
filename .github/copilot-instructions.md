# GitHub Copilot Instructions - Socket Client

## Service Context

**Purpose**: Real-time WebSocket client streaming market data from Binance to NATS message bus.

**Deployment**: Kubernetes Deployment with health checks and auto-scaling

**Role in Ecosystem**: Real-time data pipeline → NATS → TA Bot & Realtime Strategies

---

## Architecture

**Data Flow**:
```
Binance WebSocket → Socket Client → NATS (market.binance.*) → TA Bot
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
    # Cancel running tasks
    # Close WebSocket and NATS connections gracefully

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
# Mock WebSocket (see tests/conftest.py for actual fixtures)
@pytest.fixture
def mock_websocket():
    # Use actual mock_websocket fixture from conftest.py
    pass

# Test reconnection backoff strategy
@pytest.mark.asyncio
async def test_reconnection_backoff():
    # Verify exponential backoff increases delay after failures
    # Test max_backoff ceiling is respected
    assert backoff_delay < MAX_BACKOFF
```

---

## Common Issues

**Reconnection Storms**: Use exponential backoff  
**Message Queue Full**: Monitor dropped_messages metric  
**NATS Disconnections**: Circuit breaker prevents cascading failures

---

**Master Rules**: See `.cursorrules` in `petrosa_k8s` repo  
**Service Rules**: `.cursorrules` in this repo

