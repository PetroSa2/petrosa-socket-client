# Single Replica Architecture - Socket Client

## Overview
This document explains why the Petrosa Socket Client uses a single replica architecture with vertical scaling instead of horizontal scaling.

## Problem Statement
Previously, the socket client was configured with:
- 3 replicas in the deployment
- Horizontal Pod Autoscaler (HPA) with 2-10 replicas
- Standard resource limits (256Mi-512Mi memory, 100m-500m CPU)

This configuration resulted in **10 replicas running in production**, which was incorrect for a WebSocket client.

## Why Single Replica?

### WebSocket Client Design
The socket client is a **WebSocket client** that:
1. Connects to Binance WebSocket API
2. Subscribes to specific data streams (trades, tickers, depth, etc.)
3. Forwards received messages to NATS

### Issues with Multiple Replicas
When running multiple replicas:

1. **Data Duplication**: Each replica connects to the same Binance WebSocket streams, receiving identical data
2. **Unnecessary Load**: Multiple connections to Binance for the same data
3. **NATS Flooding**: The same messages are published to NATS multiple times
4. **Resource Waste**: Running 10 pods doing the same work as 1 pod
5. **No Load Balancing**: Unlike HTTP services, WebSocket clients don't distribute load - they all receive the same stream

### Correct Architecture
The socket client should use:

1. **Single Replica**: One pod connects to Binance and forwards data to NATS
2. **Vertical Scaling**: Increase resource limits if more capacity is needed
3. **High Availability**: If the pod fails, Kubernetes will restart it automatically

## Changes Made

### 1. Deployment Configuration
**Before:**
```yaml
spec:
  replicas: 3
  resources:
    requests:
      memory: 256Mi
      cpu: 100m
    limits:
      memory: 512Mi
      cpu: 500m
```

**After:**
```yaml
spec:
  replicas: 1
  resources:
    requests:
      memory: 512Mi
      cpu: 200m
    limits:
      memory: 2Gi
      cpu: 1000m
```

### 2. HPA Removal
- Deleted `k8s/hpa.yaml` completely
- Removed HPA from Kubernetes cluster
- Updated documentation to remove HPA references

### 3. Documentation Updates
Updated the following files:
- `README.md` - Added note about single replica design
- `docs/SERVICE_SUMMARY.md` - Updated deployment features
- `docs/CURSOR_AI_VERSION_RULES.md` - Removed hpa.yaml reference
- `docs/VERSION_PLACEHOLDER_GUIDE.md` - Removed hpa.yaml reference

## Production Verification

### Before Changes
```bash
$ kubectl get deployment petrosa-socket-client -n petrosa-apps
NAME                    READY   UP-TO-DATE   AVAILABLE   AGE
petrosa-socket-client   10/10   10           10          55d

$ kubectl get hpa -n petrosa-apps
NAME                         REFERENCE                        TARGETS                    MINPODS   MAXPODS   REPLICAS   AGE
petrosa-socket-client-hpa    Deployment/petrosa-socket-client cpu: 70%, memory: 80%     2         10        10         55d
```

### After Changes
```bash
$ kubectl get deployment petrosa-socket-client -n petrosa-apps
NAME                    READY   UP-TO-DATE   AVAILABLE   AGE
petrosa-socket-client   1/1     1            1           55d

$ kubectl get pods -n petrosa-apps -l app=socket-client
NAME                                     READY   STATUS    RESTARTS   AGE
petrosa-socket-client-59bcd8474d-4prrz   1/1     Running   0          24h

$ kubectl get hpa -n petrosa-apps | grep socket
# No socket client HPA found (removed)
```

## When to Scale

### Vertical Scaling (Recommended)
If the socket client needs more resources:
- Increase memory limits (e.g., to 4Gi)
- Increase CPU limits (e.g., to 2000m)
- Update the deployment manifest
- Redeploy

### Horizontal Scaling (NOT Recommended)
**Do NOT add more replicas** unless:
- You need to subscribe to **different** streams in separate pods
- You want to implement **stream partitioning** (requires code changes)
- You have a specific architecture that requires multiple consumers

## Resource Usage Monitoring

Monitor the single pod's resource usage:

```bash
# Check pod resources
kubectl top pod -n petrosa-apps -l app=socket-client

# Check pod metrics in Grafana
# Alert if memory usage > 1.5Gi
# Alert if CPU usage > 800m
```

If resource usage is consistently high, **increase limits** (vertical scaling), not replicas.

## Future Considerations

### If More Capacity is Needed
1. **Optimize the code**: Improve message processing efficiency
2. **Increase resources**: Use vertical scaling
3. **Stream partitioning**: Split streams across multiple pods (requires code changes)
4. **Connection pooling**: Optimize NATS connections

### High Availability
The current setup provides adequate HA:
- Kubernetes restarts failed pods automatically
- Health checks detect issues quickly
- Startup/liveness/readiness probes ensure pod health
- Historical data is not critical (real-time stream)

## Summary

✅ **Correct**: Single replica with vertical scaling
❌ **Incorrect**: Multiple replicas with horizontal scaling

The socket client is now properly configured as a single-instance WebSocket client with appropriate resource limits for vertical scaling.

---

**Last Updated**: October 15, 2025
**Status**: Implemented and verified in production

