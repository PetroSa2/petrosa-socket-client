# Logging Frequency Reduction - Socket Client

## Summary
Reduced logging frequency for the socket client to minimize log noise and improve observability.

## Changes Made

### 1. Heartbeat Interval Increased (constants.py)
**Before:** `HEARTBEAT_INTERVAL = 30 seconds`  
**After:** `HEARTBEAT_INTERVAL = 60 seconds` (1 minute)

- The comprehensive heartbeat log now appears once per minute instead of every 30 seconds
- This reduces heartbeat logs by 50%
- Heartbeat logs include: connection status, message processing stats, queue utilization, etc.

### 2. Message Processing Stats Throttled (client.py)
**Before:** Log every 100 messages processed  
**After:** Log at most once per minute (time-based throttling)

**Changes:**
- Added `self.last_stats_log_time` to track when last stats were logged
- Added `self.stats_log_interval = 60` seconds
- Changed from count-based logging (every 100 messages) to time-based logging (max once per minute)
- Enhanced the stats log to include `messages_per_second` metric

**Location:** Lines 92-94 and 344-355 in `socket_client/core/client.py`

## Impact

### Before
- **Heartbeat logs:** Every 30 seconds = 120 logs/hour
- **Message stats:** Every 100 messages = Variable (could be very frequent with high throughput)
- **Total:** Could easily be 1+ log per second during high activity

### After
- **Heartbeat logs:** Every 60 seconds = 60 logs/hour
- **Message stats:** Max once per minute = 60 logs/hour
- **Total:** Maximum ~2 logs per minute (120 logs/hour)

### Benefits
1. **Reduced log volume** by at least 50%
2. **Better log aggregation** - easier to track trends over time
3. **Lower storage costs** for log collection systems
4. **Better Grafana Loki performance** - fewer log entries to process
5. **Still comprehensive** - all important metrics are still logged

## Testing
- All tests pass with the new configuration
- The heartbeat interval is now configurable via `HEARTBEAT_INTERVAL` environment variable
- Coverage remains at 43.72% (above the 40% threshold)

## Deployment
The changes are backward compatible and can be deployed immediately. The logging interval can be further adjusted via environment variables:

```bash
# Override in Kubernetes deployment or .env file
HEARTBEAT_INTERVAL=60  # seconds (default is now 60)
```

## Example Log Output

### Heartbeat Log (once per minute):
```json
{
  "event": "HEARTBEAT: WebSocket Client Statistics",
  "connection_status": true,
  "websocket_state": "connected",
  "nats_state": "connected",
  "messages_processed_since_last": 5234,
  "messages_per_second": 87.23,
  "total_processed": 523456,
  "queue_utilization_percent": 12.5,
  "uptime_seconds": 3600
}
```

### Message Processing Stats (max once per minute):
```json
{
  "event": "Message processing stats",
  "processed": 523456,
  "dropped": 12,
  "messages_per_second": 87.23
}
```

## Configuration Reference

| Variable | Default | Description |
|----------|---------|-------------|
| `HEARTBEAT_INTERVAL` | 60 | Seconds between heartbeat logs |
| `ENABLE_HEARTBEAT` | true | Enable/disable heartbeat logs |

## Rollback
If needed, you can revert to the previous logging frequency by setting:
```bash
HEARTBEAT_INTERVAL=30  # Restore to 30 seconds
```

Or by reverting the commits in this change.

