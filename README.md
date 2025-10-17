# Petrosa Socket Client

**Real-time market data ingestion from Binance WebSocket streams with NATS message bus integration**

A high-performance Binance WebSocket client designed for production cryptocurrency trading systems. Connects to Binance WebSocket API, receives real-time market data (trades, tickers, order book depth), and forwards structured messages to NATS for consumption by downstream services.

---

## 🌐 PETROSA ECOSYSTEM OVERVIEW

### System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         PETROSA TRADING ECOSYSTEM                            │
│                                                                              │
│  ┌────────────────┐    ┌──────────────────┐    ┌─────────────────────┐    │
│  │                │    │                  │    │                     │    │
│  │  Binance API   │───▶│  Data Extractor  │───▶│   MySQL Database    │    │
│  │  (Historical)  │    │  (Batch Jobs)    │    │   (Klines, Rates)   │    │
│  │                │    │                  │    │                     │    │
│  └────────────────┘    └──────────────────┘    └─────────────────────┘    │
│                                                            │                 │
│  ┌────────────────┐    ┌──────────────────┐              │                 │
│  │                │    │                  │              ▼                 │
│  │  Binance WS    │───▶│  Socket Client   │──┐    ┌─────────────────┐    │
│  │  (Real-time)   │    │  (THIS SERVICE)  │  │    │                 │    │
│  │                │    │                  │  │    │   TA Bot        │    │
│  └────────────────┘    └──────────────────┘  │    │   (28 Strategies│◀───┤
│                                │              │    │    Analysis)    │    │
│                                │              │    │                 │    │
│                                │ NATS         │    └─────────────────┘    │
│                                │              │             │              │
│                         binance.websocket.data│    signals.trading         │
│                                │              │             │              │
│                                │              │             ▼              │
│                                │              │    ┌─────────────────┐    │
│                                ▼              │    │                 │    │
│                         ┌──────────────────┐  │    │  Trade Engine   │    │
│                         │                  │  │    │  (Order Exec)   │    │
│                         │  Realtime        │──┘    │                 │◀───┤
│                         │  Strategies      │──────▶│  Binance API    │    │
│                         │  (Live Analysis) │       │                 │    │
│                         │                  │       └─────────────────┘    │
│                         └──────────────────┘                               │
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────┐    │
│  │                    Kubernetes (MicroK8s Cluster)                    │    │
│  │  Namespace: petrosa-apps  │  NATS: nats-server.nats:4222          │    │
│  │  Secrets: petrosa-sensitive-credentials                             │    │
│  │  ConfigMaps: petrosa-common-config                                  │    │
│  └────────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Services in the Ecosystem

| Service | Purpose | Input | Output | Status |
|---------|---------|-------|--------|--------|
| **petrosa-socket-client** | Real-time WebSocket data ingestion | Binance WebSocket API | NATS: `binance.websocket.data` | **YOU ARE HERE** |
| **petrosa-binance-data-extractor** | Historical data extraction & gap filling | Binance REST API | MySQL (klines, funding rates, trades) | Batch Processing |
| **petrosa-bot-ta-analysis** | Technical analysis (28 strategies) | MySQL klines data | NATS: `signals.trading` | Signal Generation |
| **petrosa-realtime-strategies** | Real-time signal generation | NATS: `binance.websocket.data` | NATS: `signals.trading` | Live Processing |
| **petrosa-tradeengine** | Order execution & trade management | NATS: `signals.trading` | Binance Orders API, MongoDB audit | Order Execution |
| **petrosa_k8s** | Centralized infrastructure | Kubernetes manifests | Cluster resources | Infrastructure |

### Data Flow Pipeline

```
┌─────────────┐
│   Binance   │
│  WebSocket  │
│   Streams   │
└──────┬──────┘
       │ wss://stream.binance.com:9443
       │ • btcusdt@trade
       │ • btcusdt@ticker  
       │ • btcusdt@depth20@100ms
       ▼
┌──────────────────────┐
│   Socket Client      │ ◄── THIS SERVICE
│   (WebSocket Client) │
│                      │
│ • Connects to Binance│
│ • Parses messages    │
│ • Transforms format  │
│ • Publishes to NATS  │
└──────┬───────────────┘
       │ NATS Topic: binance.websocket.data
       │
       ▼
┌──────────────────────┐
│    NATS Server       │
│  (Message Bus)       │
│                      │
│  Topic Subscribers:  │
│  • Realtime Strategies
│  • (Future services) │
└──────┬───────────────┘
       │
       ├─────────────────────────────────┐
       │                                 │
       ▼                                 ▼
┌──────────────────┐            ┌───────────────┐
│ Realtime         │            │  TA Bot       │
│ Strategies       │            │  (via MySQL)  │
│                  │            │               │
│ • Process live   │            │ • Historical  │
│ • Generate       │            │ • 28 strategies│
│   signals        │            │ • Signals     │
└────┬─────────────┘            └────┬──────────┘
     │                              │
     │ signals.trading             │ signals.trading
     └────────────┬─────────────────┘
                  │
                  ▼
         ┌─────────────────┐
         │  Trade Engine   │
         │                 │
         │ • Validate      │
         │ • Risk manage   │
         │ • Execute orders│
         └────┬────────────┘
              │
              ▼
         ┌──────────────┐
         │  Binance API │
         │  (Orders)    │
         └──────────────┘
```

### Transport Layer

#### NATS Messaging (Primary Transport)

**Server Configuration:**
- **URL**: `nats://nats-server.nats:4222` (Kubernetes service name)
- **Client Name**: `petrosa-socket-client`
- **Reconnection**: Automatic with exponential backoff
- **Max Reconnect Attempts**: 10

**Published Topics:**

| Topic | Publisher | Content | Consumers | Message Rate |
|-------|-----------|---------|-----------|--------------|
| `binance.websocket.data` | **socket-client** | Real-time market data | realtime-strategies | 1000+/sec |
| `signals.trading` | ta-bot, realtime-strategies | Trading signals | tradeengine | 50-150/day |

**Message Format (binance.websocket.data):**
```json
{
  "stream": "btcusdt@trade",
  "data": {
    "e": "trade",
    "E": 1234567890123,
    "s": "BTCUSDT",
    "t": 12345,
    "p": "50000.00",
    "q": "0.001",
    "b": 88,
    "a": 50,
    "T": 1234567890120,
    "m": true,
    "M": true
  },
  "timestamp": "2024-01-01T00:00:00.000Z",
  "message_id": "uuid-here",
  "source": "binance-websocket",
  "version": "1.0"
}
```

#### WebSocket Connection

**Binance WebSocket API:**
- **URL**: `wss://stream.binance.com:9443`
- **Protocol**: WebSocket Secure (WSS)
- **Reconnection**: Exponential backoff (5s, 10s, 20s...)
- **Ping/Pong**: 30s interval for keepalive
- **Circuit Breaker**: 5 failures → 60s recovery timeout

**Subscription Message:**
```json
{
  "method": "SUBSCRIBE",
  "params": [
    "btcusdt@trade",
    "btcusdt@ticker",
    "btcusdt@depth20@100ms"
  ],
  "id": 1234567890
}
```

#### REST APIs

This service does not expose REST endpoints but includes health check endpoints:
- `GET /healthz` - Liveness probe
- `GET /ready` - Readiness probe  
- `GET /metrics` - Prometheus metrics
- `GET /` - Service information

### Shared Data Contracts

#### MarketData Models (Binance Streams)

**Trade Stream (`{symbol}@trade`):**
```python
{
  "e": "trade",              # Event type
  "E": 1234567890123,        # Event time
  "s": "BTCUSDT",            # Symbol
  "t": 12345,                # Trade ID
  "p": "50000.00",           # Price
  "q": "0.001",              # Quantity
  "b": 88,                   # Buyer order ID
  "a": 50,                   # Seller order ID
  "T": 1234567890120,        # Trade time
  "m": true,                 # Is buyer maker
  "M": true                  # Ignore (always true)
}
```

**Ticker Stream (`{symbol}@ticker`):**
```python
{
  "e": "24hrTicker",         # Event type
  "E": 1234567890123,        # Event time
  "s": "BTCUSDT",            # Symbol
  "p": "100.00",             # Price change
  "P": "0.20",               # Price change percent
  "w": "50000.00",           # Weighted average price
  "c": "50100.00",           # Last price
  "Q": "0.1",                # Last quantity
  "o": "50000.00",           # Open price
  "h": "51000.00",           # High price
  "l": "49000.00",           # Low price
  "v": "1000.00",            # Total traded base volume
  "q": "50000000.00",        # Total traded quote volume
  "n": 50000                 # Number of trades
}
```

**Depth Stream (`{symbol}@depth20@100ms`):**
```python
{
  "lastUpdateId": 160,       # Last update ID
  "bids": [                  # Bids to be updated
    ["50000.00", "0.1"],     # [Price, Quantity]
    ["49999.00", "0.2"]
  ],
  "asks": [                  # Asks to be updated
    ["50001.00", "0.1"],     # [Price, Quantity]
    ["50002.00", "0.2"]
  ]
}
```

#### Signal Model (Trading Signals)

Defined in `contracts/signal.py` (tradeengine repository):

```python
class Signal(BaseModel):
    # Core fields
    strategy_id: str           # e.g., "volume_surge_breakout"
    symbol: str                # e.g., "BTCUSDT"
    action: Literal["buy", "sell", "hold", "close"]
    confidence: float          # 0.0 to 1.0
    price: float               # Signal price
    quantity: float            # Position size
    current_price: float       # Market price at signal time
    
    # Risk management
    stop_loss: Optional[float]
    take_profit: Optional[float]
    
    # Metadata
    timestamp: datetime
    timeframe: str             # e.g., "15m", "1h"
    indicators: Dict[str, Any] # Technical indicators used
    metadata: Dict[str, Any]   # Strategy-specific data
```

#### TradeOrder Model (Execution Orders)

Defined in `contracts/order.py` (tradeengine repository):

```python
class TradeOrder(BaseModel):
    # Core fields
    symbol: str                # e.g., "BTCUSDT"
    type: str                  # "market", "limit", "stop", etc.
    side: str                  # "buy", "sell"
    amount: float              # Order amount
    
    # Price levels
    target_price: Optional[float]
    stop_loss: Optional[float]
    take_profit: Optional[float]
    
    # Order metadata
    order_id: Optional[str]
    status: OrderStatus        # pending, filled, cancelled, etc.
    simulate: bool = True      # Simulation mode flag
    
    # Timestamps
    created_at: datetime
    updated_at: Optional[datetime]
```

### Integration Patterns

#### Service Discovery

Services discover each other through **Kubernetes DNS**:
- NATS Server: `nats://nats-server.nats:4222`
- Trade Engine API: `http://petrosa-tradeengine:8080`
- TA Bot API: `http://petrosa-ta-bot:8080`

#### Configuration Management

**Kubernetes ConfigMaps:**
- `petrosa-common-config` - Shared configuration (NATS URL, log level, environment)
- `[service]-config` - Service-specific configuration

**Kubernetes Secrets:**
- `petrosa-sensitive-credentials` - Shared secrets (Binance API keys, DB passwords)
- All services use the same secret for consistency

**Environment Variables:**
```bash
# Common (from petrosa-common-config)
ENVIRONMENT=production
LOG_LEVEL=INFO
NATS_URL=nats://nats-server.nats:4222

# Service-specific
BINANCE_WS_URL=wss://stream.binance.com:9443
BINANCE_STREAMS=btcusdt@trade,btcusdt@ticker,btcusdt@depth20@100ms
NATS_TOPIC=binance.websocket.data
```

#### Health Checks and Monitoring

**Health Check Pattern:**
All services expose standardized health endpoints:
- `/healthz` - Liveness (is service running?)
- `/ready` - Readiness (can service handle traffic?)
- `/metrics` - Prometheus metrics
- `/` or `/info` - Service information

**Kubernetes Probes:**
```yaml
livenessProbe:
  httpGet:
    path: /healthz
    port: 8080
  initialDelaySeconds: 30
  periodSeconds: 10

readinessProbe:
  httpGet:
    path: /ready
    port: 8080
  initialDelaySeconds: 5
  periodSeconds: 5
```

**OpenTelemetry Integration:**
- **Traces**: Distributed tracing across services
- **Metrics**: Prometheus-compatible metrics
- **Logs**: Structured JSON logs with correlation IDs
- **Exporter**: OTLP to Grafana Cloud

#### Error Handling and Circuit Breakers

**Circuit Breaker Pattern:**
```python
# Used for external connections (NATS, WebSocket)
CircuitBreaker(
    failure_threshold=5,      # Open after 5 failures
    recovery_timeout=60,      # Try recovery after 60s
    expected_exception=Exception
)
```

**Reconnection Strategy:**
- Exponential backoff: `delay * 2^attempt`
- Max delay cap: 60 seconds
- Max attempts: 10 (configurable)
- Jitter: Random 0-1s added to prevent thundering herd

**Error Propagation:**
- Critical errors: Log and restart service
- Transient errors: Retry with backoff
- Data errors: Log, increment metric, drop message

### Deployment Architecture

**Kubernetes Cluster:**
- **Type**: Remote MicroK8s
- **Server**: `https://192.168.194.253:16443`
- **Namespace**: `petrosa-apps`
- **Access**: Via `k8s/kubeconfig.yaml`

**Deployment Pattern:**
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: petrosa-socket-client
  namespace: petrosa-apps
spec:
  replicas: 1  # Single replica (WebSocket client should NOT scale horizontally)
  selector:
    matchLabels:
      app: socket-client
  template:
    spec:
      containers:
      - name: socket-client
        image: yurisa2/petrosa-socket-client:VERSION_PLACEHOLDER
        resources:
          requests:
            memory: "256Mi"
            cpu: "200m"
          limits:
            memory: "2Gi"  # Vertical scaling for higher throughput
            cpu: "1000m"
        env:
        - name: NATS_URL
          valueFrom:
            configMapKeyRef:
              name: petrosa-common-config
              key: NATS_URL
        - name: BINANCE_STREAMS
          valueFrom:
            configMapKeyRef:
              name: socket-client-config
              key: BINANCE_STREAMS
```

**Scaling Strategy:**
- **Socket Client**: Vertical scaling only (increase resources)
- **TA Bot**: Horizontal scaling (3 replicas with leader election)
- **Realtime Strategies**: Horizontal scaling (HPA based on CPU/memory)
- **Trade Engine**: Horizontal scaling (3 replicas)

**Network Policies:**
- Allow ingress from Kubernetes Ingress controller
- Allow egress to NATS server (nats:4222)
- Allow egress to Binance WebSocket (443)
- Deny all other traffic by default

---

## 🔧 SOCKET CLIENT - DETAILED DOCUMENTATION

### Service Architecture

```
┌────────────────────────────────────────────────────────────────────┐
│                      Socket Client Service                          │
│                                                                      │
│  ┌──────────────┐      ┌──────────────┐      ┌──────────────┐    │
│  │   Health     │      │   Main       │      │  WebSocket   │    │
│  │   Server     │◀────▶│   Service    │◀────▶│   Client     │    │
│  │  (HTTP:8080) │      │              │      │              │    │
│  └──────────────┘      └──────┬───────┘      └──────┬───────┘    │
│        │                       │                     │             │
│        │                       │                     │             │
│        ▼                       ▼                     ▼             │
│  ┌──────────────────────────────────────────────────────────┐     │
│  │                   Circuit Breakers                        │     │
│  │  • WebSocket Circuit Breaker (5 failures / 60s timeout)  │     │
│  │  • NATS Circuit Breaker (5 failures / 60s timeout)       │     │
│  └──────────────────────────────────────────────────────────┘     │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────┐     │
│  │              Message Processing Pipeline                  │     │
│  │                                                            │     │
│  │   WebSocket  →  Message Queue  →  Processor  →  NATS     │     │
│  │   Listener      (5000 capacity)    (Validate)   Publisher│     │
│  │      ↓              ↓                  ↓           ↓      │     │
│  │   Parse JSON    Backpressure      Transform    Publish   │     │
│  │   Determine     Detection         Add UUID     Topic      │     │
│  │   Stream Type   Drop if Full      Add Metadata  Encode   │     │
│  └──────────────────────────────────────────────────────────┘     │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────┐     │
│  │                    Monitoring                             │     │
│  │  • Heartbeat Loop (30s interval)                         │     │
│  │  • Metrics: messages processed, dropped, queue size      │     │
│  │  • Ping Loop (30s keepalive)                             │     │
│  └──────────────────────────────────────────────────────────┘     │
└────────────────────────────────────────────────────────────────────┘
```

### Core Components

#### 1. BinanceWebSocketClient (`socket_client/core/client.py`)

**Responsibilities:**
- Connect to Binance WebSocket API
- Subscribe to configured streams
- Parse incoming messages
- Forward messages to NATS
- Handle reconnections and errors

**Key Code Excerpt:**
```python
class BinanceWebSocketClient:
    """Binance WebSocket client with NATS integration."""
    
    def __init__(
        self,
        ws_url: str,
        streams: list[str],
        nats_url: str,
        nats_topic: str,
        max_reconnect_attempts: int = 10,
        reconnect_delay: int = 5,
    ):
        self.ws_url = ws_url
        self.streams = streams
        self.nats_url = nats_url
        self.nats_topic = nats_topic
        
        # Connection state
        self.websocket: Optional[websockets.WebSocketClientProtocol] = None
        self.nats_client: Optional[NATSClient] = None
        self.is_connected = False
        self.is_running = False
        
        # Message processing
        self.message_queue = asyncio.Queue(maxsize=5000)
        self.processed_messages = 0
        self.dropped_messages = 0
    
    async def start(self):
        """Start the WebSocket client."""
        await self._connect_nats()
        self.processor_task = asyncio.create_task(self._process_messages())
        await self._connect_websocket()
        self.ping_task = asyncio.create_task(self._ping_loop())
        
        if constants.ENABLE_HEARTBEAT:
            self.heartbeat_task = asyncio.create_task(self._heartbeat_loop())
    
    async def _process_single_message(self, data: dict):
        """Process a single message."""
        # Determine stream name from message type
        stream_name = self._determine_stream_name(data)
        
        # Create structured message
        message = create_message(
            stream=stream_name,
            data=data,
            message_id=str(uuid.uuid4())
        )
        
        # Publish to NATS
        await self.nats_client.publish(
            self.nats_topic,
            message.to_json().encode("utf-8")
        )
        
        self.processed_messages += 1
```

**Stream Name Determination Logic:**
```python
def _determine_stream_name(self, data: dict) -> Optional[str]:
    """Determine stream name from Binance message data."""
    event_type = data.get("e", "")
    symbol = data.get("s", "")
    
    # Handle depth updates (order book)
    if "lastUpdateId" in data and "bids" in data:
        return f"{symbol.lower()}@depth20@100ms"
    
    # Map event types to stream names
    if event_type == "trade":
        return f"{symbol.lower()}@trade"
    elif event_type == "24hrTicker":
        return f"{symbol.lower()}@ticker"
    elif event_type == "depthUpdate":
        return f"{symbol.lower()}@depth20@100ms"
    
    return None
```

#### 2. Message Models (`socket_client/models/message.py`)

**Message Transformation:**
```python
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Dict, Any

class WebSocketMessage(BaseModel):
    """Standardized WebSocket message format."""
    
    stream: str = Field(..., description="Stream identifier")
    data: Dict[str, Any] = Field(..., description="Raw Binance data")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    message_id: str = Field(..., description="Unique message ID")
    source: str = Field(default="binance-websocket")
    version: str = Field(default="1.0")
    
    def to_json(self) -> str:
        """Convert to JSON string for NATS."""
        return self.json(by_alias=True)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

def create_message(stream: str, data: dict, message_id: str) -> WebSocketMessage:
    """Factory function to create messages."""
    return WebSocketMessage(
        stream=stream,
        data=data,
        message_id=message_id,
        timestamp=datetime.utcnow(),
        source="binance-websocket",
        version="1.0"
    )
```

#### 3. Circuit Breaker (`socket_client/utils/circuit_breaker.py`)

**Pattern Implementation:**
```python
class CircuitBreaker:
    """Circuit breaker for fault tolerance."""
    
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        expected_exception: type = Exception
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "closed"  # closed, open, half_open
    
    async def call(self, func, *args, **kwargs):
        """Call function with circuit breaker protection."""
        if self.state == "open":
            if self._should_attempt_reset():
                self.state = "half_open"
            else:
                raise CircuitBreakerOpenError("Circuit breaker is open")
        
        try:
            result = await func(*args, **kwargs)
            self._on_success()
            return result
        except self.expected_exception as e:
            self._on_failure()
            raise e
    
    def _on_success(self):
        """Reset circuit breaker on success."""
        self.failure_count = 0
        self.state = "closed"
    
    def _on_failure(self):
        """Track failure and open circuit if threshold reached."""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.failure_threshold:
            self.state = "open"
```

#### 4. Health Server (`socket_client/health/server.py`)

**Health Check Endpoints:**
```python
from fastapi import FastAPI
from typing import Dict, Any

app = FastAPI()

@app.get("/healthz")
async def healthz() -> Dict[str, str]:
    """Liveness probe - is service running?"""
    return {"status": "healthy"}

@app.get("/ready")
async def ready() -> Dict[str, Any]:
    """Readiness probe - can service handle traffic?"""
    # Check WebSocket connection
    if not client.is_connected:
        return {"status": "not_ready", "reason": "websocket_disconnected"}
    
    # Check NATS connection
    if not client.nats_client or client.nats_client.is_closed:
        return {"status": "not_ready", "reason": "nats_disconnected"}
    
    return {"status": "ready"}

@app.get("/metrics")
async def metrics() -> Dict[str, Any]:
    """Prometheus-compatible metrics."""
    return client.get_metrics()
```

### Data Models

#### WebSocket Message Structure

**Input (from Binance):**
```json
{
  "e": "trade",
  "E": 1234567890123,
  "s": "BTCUSDT",
  "t": 12345,
  "p": "50000.00",
  "q": "0.001"
}
```

**Output (to NATS):**
```json
{
  "stream": "btcusdt@trade",
  "data": {
    "e": "trade",
    "E": 1234567890123,
    "s": "BTCUSDT",
    "t": 12345,
    "p": "50000.00",
    "q": "0.001"
  },
  "timestamp": "2024-01-01T00:00:00.000Z",
  "message_id": "550e8400-e29b-41d4-a716-446655440000",
  "source": "binance-websocket",
  "version": "1.0"
}
```

### Message Formats and Topics

**Published NATS Topic:** `binance.websocket.data`

**Message Types:**

1. **Trade Messages:**
```json
{
  "stream": "btcusdt@trade",
  "data": {
    "e": "trade",
    "E": 1234567890123,
    "s": "BTCUSDT",
    "t": 12345,
    "p": "50000.00",
    "q": "0.001",
    "m": true
  },
  "timestamp": "2024-01-01T00:00:00.000Z",
  "message_id": "uuid",
  "source": "binance-websocket",
  "version": "1.0"
}
```

2. **Ticker Messages:**
```json
{
  "stream": "btcusdt@ticker",
  "data": {
    "e": "24hrTicker",
    "s": "BTCUSDT",
    "p": "100.00",
    "P": "0.20",
    "c": "50100.00",
    "o": "50000.00",
    "h": "51000.00",
    "l": "49000.00"
  },
  "timestamp": "2024-01-01T00:00:00.000Z",
  "message_id": "uuid",
  "source": "binance-websocket",
  "version": "1.0"
}
```

3. **Depth Messages:**
```json
{
  "stream": "btcusdt@depth20@100ms",
  "data": {
    "lastUpdateId": 160,
    "bids": [["50000.00", "0.1"], ["49999.00", "0.2"]],
    "asks": [["50001.00", "0.1"], ["50002.00", "0.2"]]
  },
  "timestamp": "2024-01-01T00:00:00.000Z",
  "message_id": "uuid",
  "source": "binance-websocket",
  "version": "1.0"
}
```

### Code Examples

#### Basic Usage

```python
import asyncio
from socket_client.core.client import BinanceWebSocketClient

async def main():
    """Run the WebSocket client."""
    client = BinanceWebSocketClient(
        ws_url="wss://stream.binance.com:9443",
        streams=[
            "btcusdt@trade",
            "btcusdt@ticker",
            "btcusdt@depth20@100ms"
        ],
        nats_url="nats://localhost:4222",
        nats_topic="binance.websocket.data"
    )
    
    try:
        await client.start()
        # Client runs until interrupted
    except KeyboardInterrupt:
        await client.stop()

if __name__ == "__main__":
    asyncio.run(main())
```

#### Custom Configuration

```python
# Custom stream configuration
streams = []
symbols = ["BTCUSDT", "ETHUSDT", "BNBUSDT"]
for symbol in symbols:
    streams.extend([
        f"{symbol.lower()}@trade",
        f"{symbol.lower()}@ticker",
        f"{symbol.lower()}@depth20@100ms"
    ])

client = BinanceWebSocketClient(
    ws_url="wss://stream.binance.com:9443",
    streams=streams,
    nats_url="nats://nats-server.nats:4222",
    nats_topic="binance.websocket.data",
    max_reconnect_attempts=15,
    reconnect_delay=10
)
```

#### Monitoring Message Flow

```python
# Get metrics
metrics = client.get_metrics()
print(f"Messages processed: {metrics['processed_messages']}")
print(f"Messages dropped: {metrics['dropped_messages']}")
print(f"Queue size: {metrics['queue_size']}")
print(f"WebSocket state: {metrics['websocket_state']}")
print(f"NATS state: {metrics['nats_state']}")
```

### Configuration

**Environment Variables:**

| Variable | Default | Description |
|----------|---------|-------------|
| `BINANCE_WS_URL` | `wss://stream.binance.com:9443` | Binance WebSocket URL |
| `BINANCE_STREAMS` | `btcusdt@trade,btcusdt@ticker,btcusdt@depth20@100ms` | Comma-separated streams |
| `NATS_URL` | `nats://localhost:4222` | NATS server URL |
| `NATS_TOPIC` | `binance.websocket.data` | NATS topic for publishing |
| `LOG_LEVEL` | `INFO` | Logging level |
| `WEBSOCKET_RECONNECT_DELAY` | `5` | Reconnection delay (seconds) |
| `WEBSOCKET_MAX_RECONNECT_ATTEMPTS` | `10` | Max reconnection attempts |
| `MESSAGE_TTL_SECONDS` | `60` | Message TTL |
| `MAX_QUEUE_SIZE` | `5000` | Message queue capacity |
| `ENABLE_HEARTBEAT` | `true` | Enable heartbeat logging |
| `HEARTBEAT_INTERVAL` | `30` | Heartbeat interval (seconds) |

**Configuration File (`constants.py`):**
```python
import os
from dotenv import load_dotenv

load_dotenv()

# Binance WebSocket settings
BINANCE_WS_URL = os.getenv("BINANCE_WS_URL", "wss://stream.binance.com:9443")

# NATS configuration
NATS_URL = os.getenv("NATS_URL", "nats://localhost:4222")
NATS_TOPIC = os.getenv("NATS_TOPIC", "binance.websocket.data")

# WebSocket connection settings
WEBSOCKET_RECONNECT_DELAY = int(os.getenv("WEBSOCKET_RECONNECT_DELAY", "5"))
WEBSOCKET_MAX_RECONNECT_ATTEMPTS = int(os.getenv("WEBSOCKET_MAX_RECONNECT_ATTEMPTS", "10"))
WEBSOCKET_PING_INTERVAL = int(os.getenv("WEBSOCKET_PING_INTERVAL", "30"))

# Message processing
MAX_QUEUE_SIZE = int(os.getenv("MAX_QUEUE_SIZE", "5000"))
MESSAGE_TTL_SECONDS = int(os.getenv("MESSAGE_TTL_SECONDS", "60"))

# Heartbeat
ENABLE_HEARTBEAT = os.getenv("ENABLE_HEARTBEAT", "true").lower() == "true"
HEARTBEAT_INTERVAL = int(os.getenv("HEARTBEAT_INTERVAL", "30"))
```

### Deployment

**Kubernetes Deployment:**
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: petrosa-socket-client
  namespace: petrosa-apps
  labels:
    app: socket-client
    version: v1
spec:
  replicas: 1  # IMPORTANT: Do NOT scale horizontally
  selector:
    matchLabels:
      app: socket-client
  template:
    metadata:
      labels:
        app: socket-client
    spec:
      containers:
      - name: socket-client
        image: yurisa2/petrosa-socket-client:VERSION_PLACEHOLDER
        ports:
        - containerPort: 8080
          name: health
        env:
        - name: BINANCE_WS_URL
          value: "wss://stream.binance.com:9443"
        - name: BINANCE_STREAMS
          valueFrom:
            configMapKeyRef:
              name: socket-client-config
              key: BINANCE_STREAMS
        - name: NATS_URL
          valueFrom:
            configMapKeyRef:
              name: petrosa-common-config
              key: NATS_URL
        - name: NATS_TOPIC
          value: "binance.websocket.data"
        - name: LOG_LEVEL
          valueFrom:
            configMapKeyRef:
              name: petrosa-common-config
              key: LOG_LEVEL
        resources:
          requests:
            memory: "256Mi"
            cpu: "200m"
          limits:
            memory: "2Gi"    # Vertical scaling for throughput
            cpu: "1000m"
        livenessProbe:
          httpGet:
            path: /healthz
            port: 8080
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /ready
            port: 8080
          initialDelaySeconds: 5
          periodSeconds: 5
---
apiVersion: v1
kind: Service
metadata:
  name: petrosa-socket-client
  namespace: petrosa-apps
spec:
  selector:
    app: socket-client
  ports:
  - port: 80
    targetPort: 8080
    name: http
  type: ClusterIP
```

**Why Single Replica?**

This service uses a **single replica** because:
1. WebSocket client maintains state (connection, subscriptions)
2. Multiple replicas would duplicate same data stream
3. Binance WebSocket sends same data to all connections
4. Creates unnecessary load on Binance API
5. NATS would receive duplicate messages

**Scaling Strategy:**
- ✅ **Vertical Scaling**: Increase memory/CPU for higher throughput
- ❌ **Horizontal Scaling**: Do NOT add more replicas
- 💡 **Load Distribution**: Use NATS consumer groups in downstream services

### Monitoring

**Prometheus Metrics:**

```
# Message processing
socket_client_messages_processed_total{stream="btcusdt@trade"} 150000
socket_client_messages_dropped_total 0
socket_client_queue_size 45
socket_client_queue_utilization_percent 0.9

# Connection status
socket_client_websocket_connected 1
socket_client_nats_connected 1
socket_client_reconnect_attempts_total 0

# Performance
socket_client_uptime_seconds 3600
socket_client_messages_per_second 41.67
socket_client_time_since_last_message_seconds 0.024
```

**Heartbeat Logs:**

Every 30 seconds, the service logs comprehensive statistics:

```json
{
  "level": "INFO",
  "message": "HEARTBEAT: WebSocket Client Statistics",
  "connection_status": true,
  "websocket_state": "connected",
  "nats_state": "connected",
  "messages_processed_since_last": 1250,
  "messages_dropped_since_last": 0,
  "messages_per_second": 41.67,
  "total_processed": 150000,
  "total_dropped": 0,
  "overall_rate_per_second": 41.67,
  "queue_size": 45,
  "queue_utilization_percent": 0.9,
  "time_since_last_message_seconds": 0.024,
  "uptime_seconds": 3600,
  "heartbeat_interval_seconds": 30,
  "reconnect_attempts": 0,
  "last_ping_seconds_ago": 15.3
}
```

**Grafana Dashboards:**

Access via Kubernetes port-forward:
```bash
kubectl port-forward service/optimized-grafana 3000:3000 -n observability
# Open: http://localhost:3000 (admin/admin123)
```

**Key Metrics to Monitor:**
- Message processing rate (should be 1000+/sec)
- Dropped messages (should be 0 or very low)
- Queue utilization (should be <80%)
- Connection status (should be 1)
- Time since last message (should be <1s)

### Development Guide

**Local Development:**

```bash
# Clone repository
git clone <repository-url>
cd petrosa-socket-client

# Setup environment
make setup

# Run locally (requires local NATS server)
make run-local

# Run tests
make test

# Run full pipeline
make pipeline
```

**Docker Development:**

```bash
# Build image
make build

# Run container
make run-docker

# Test container
make container
```

**Testing:**

```bash
# Unit tests
pytest tests/unit/ -v

# Integration tests
pytest tests/integration/ -v

# Performance tests
pytest tests/performance/ -v

# Coverage report
pytest tests/ --cov=socket_client --cov-report=html
```

**Code Quality:**

```bash
# Format code
make format

# Lint code
make lint

# Type checking
make type-check

# Security scan
make security
```

### Troubleshooting

#### WebSocket Connection Issues

**Symptom:** `websocket_state: "disconnected"`

**Solutions:**
```bash
# Check WebSocket connectivity
curl -I https://stream.binance.com

# Check environment variables
env | grep BINANCE

# View logs
kubectl logs -n petrosa-apps -l app=socket-client --tail=100

# Check pod status
kubectl get pods -n petrosa-apps -l app=socket-client
```

#### NATS Connection Issues

**Symptom:** `nats_state: "disconnected"`

**Solutions:**
```bash
# Check NATS connectivity
kubectl exec -it deployment/petrosa-socket-client -n petrosa-apps -- \
  nc -zv nats-server.nats 4222

# Check NATS server status
kubectl get pods -n nats

# Verify NATS URL in config
kubectl get configmap petrosa-common-config -n petrosa-apps -o yaml
```

#### High Message Drop Rate

**Symptom:** `messages_dropped > 0` or `queue_utilization > 90%`

**Solutions:**
1. **Increase queue size:**
   ```yaml
   env:
   - name: MAX_QUEUE_SIZE
     value: "10000"
   ```

2. **Increase resources (vertical scaling):**
   ```yaml
   resources:
     limits:
       memory: "4Gi"
       cpu: "2000m"
   ```

3. **Check NATS throughput:**
   ```bash
   kubectl logs -n nats -l app=nats
   ```

#### Memory Issues

**Symptom:** Pod restart due to OOM

**Solutions:**
```yaml
# Increase memory limit
resources:
  limits:
    memory: "4Gi"

# Enable memory profiling
env:
- name: LOG_LEVEL
  value: "DEBUG"
```

#### No Messages Received

**Symptom:** `processed_messages == 0`

**Checklist:**
1. Check WebSocket connection
2. Verify stream configuration
3. Check Binance API status: https://www.binance.com/en/support/announcement
4. Verify NATS topic subscribers
5. Check network policies

**Debug Commands:**
```bash
# Check WebSocket connection
kubectl logs -n petrosa-apps -l app=socket-client | grep "Connected to Binance"

# Check NATS messages
kubectl exec -it deployment/petrosa-socket-client -n petrosa-apps -- \
  nats sub binance.websocket.data

# Check health
kubectl exec -it deployment/petrosa-socket-client -n petrosa-apps -- \
  curl http://localhost:8080/metrics
```

---

## 🚀 Quick Start

### Local Development
```bash
# Complete setup
make setup

# Run locally
make run-local

# Run tests
make test
```

### Docker
```bash
# Build and run
make build
make run-docker
```

### Kubernetes
```bash
# Deploy to cluster
make deploy

# Check status
make k8s-status

# View logs
make k8s-logs
```

---

## 📚 Additional Documentation

- [OpenTelemetry Installation Guide](docs/OTEL_INSTALLATION_GUIDE.md)
- [Repository Setup Guide](docs/REPOSITORY_SETUP_GUIDE.md)
- [Deployment Guide](docs/DEPLOYMENT.md)
- [Troubleshooting Guide](docs/TROUBLESHOOTING.md)

---

**Production Status:** ✅ **ACTIVE** - Processing 1000+ messages/second in production
