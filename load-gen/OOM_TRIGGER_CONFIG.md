# Load Generator Configuration for OOM Trigger

## 🚨 Overview

This configuration is designed to trigger an **Out-Of-Memory (OOM)** condition in the `checkout-recommendations` service within **2 minutes** by exploiting the unbounded cache memory leak.

## 🎯 Changes Made

### 1. Reduced Wait Time (`robot-shop.py`)

**Before:**
```python
wait_time = between(2, 10)  # 2-10 seconds between requests
```

**After:**
```python
wait_time = between(0.1, 0.5)  # 0.1-0.5 seconds between requests
```

**Impact:** 20-100x more requests per user

### 2. Unique Cart IDs (`robot-shop.py`)

**Before:**
```python
uniqueid = user['uuid']  # Same cart ID reused (cache hits)
```

**After:**
```python
uniqueid = user['uuid'] + '-' + str(random.randint(1, 999999))  # Unique cart ID every time
```

**Impact:** Every request creates new cache entries (no cache hits)

### 3. Increased Concurrent Users

**Docker Compose (`docker-compose-load.yaml`):**
```yaml
NUM_CLIENTS: 50  # 50 concurrent users
RUN_TIME: 2m     # Run for 2 minutes
```

**Kubernetes (`K8s/load-deployment.yaml`):**
```yaml
NUM_CLIENTS: "50"
RUN_TIME: "2m"
```

**Shell Script (`load-gen.sh`):**
```bash
NUM_CLIENTS=50
RUN_TIME=2m
```

## 📊 Expected Memory Growth

### Cache Entry Calculation

Each recommendation request generates:
- **1 cache entry** for `get_product_popularity(limit=10)`
- **10+ cache entries** for `get_product_ratings(sku)` (one per product)
- **Total: ~11 cache entries per request**

### Load Calculation

With 50 concurrent users and 0.1-0.5s wait time:
- **Requests per second:** ~100-500 requests/sec
- **Cache entries per second:** ~1,100-5,500 entries/sec
- **Cache entries in 2 minutes:** ~132,000-660,000 entries

### Memory Growth Timeline

| Time | Requests | Cache Entries | Estimated Memory |
|------|----------|---------------|------------------|
| 10s  | ~1,000   | ~11,000       | ~50 MB          |
| 30s  | ~3,000   | ~33,000       | ~150 MB         |
| 60s  | ~6,000   | ~66,000       | ~300 MB         |
| 90s  | ~9,000   | ~99,000       | ~450 MB         |
| 120s | ~12,000  | ~132,000      | ~600 MB         |

**Expected OOM:** Between 90-120 seconds (1.5-2 minutes)

## 🚀 How to Use

### Docker Compose

```bash
# Start the services
docker-compose up -d

# Start the aggressive load generator
docker-compose -f docker-compose-load.yaml up

# Monitor memory usage
docker stats checkout-recommendations

# Watch cache growth
watch -n 1 'curl -s http://localhost:8080/api/recommendations/cache/stats'
```

### Kubernetes

```bash
# Deploy the load generator
kubectl apply -f K8s/load-deployment.yaml

# Monitor pod memory
kubectl top pod -l service=checkout-recommendations

# Watch for OOM kills
kubectl get events --watch | grep OOM

# Check cache stats
kubectl exec -it <checkout-recommendations-pod> -- curl localhost:8080/cache/stats
```

### Standalone Script

```bash
cd load-gen
./load-gen.sh -n 50 -t 2m -h http://localhost:8080
```

## 📈 Monitoring the OOM

### 1. Cache Statistics

```bash
curl http://localhost:8080/api/recommendations/cache/stats
```

Expected output progression:
```json
{"cache_entries": 11000, "cache_size_mb": 50.5}   # 10 seconds
{"cache_entries": 33000, "cache_size_mb": 151.2}  # 30 seconds
{"cache_entries": 66000, "cache_size_mb": 302.4}  # 60 seconds
{"cache_entries": 99000, "cache_size_mb": 453.6}  # 90 seconds
```

### 2. Docker Memory Usage

```bash
docker stats checkout-recommendations --no-stream
```

Watch for memory climbing rapidly:
```
CONTAINER              MEM USAGE / LIMIT
checkout-recommendations   50MB / 2GB    # 10s
checkout-recommendations   150MB / 2GB   # 30s
checkout-recommendations   300MB / 2GB   # 60s
checkout-recommendations   450MB / 2GB   # 90s
checkout-recommendations   OOMKilled     # 120s
```

### 3. Kubernetes Events

```bash
kubectl get events --field-selector involvedObject.name=<pod-name>
```

Look for:
```
OOMKilled: Container checkout-recommendations exceeded memory limit
```

## 🛡️ Safety Notes

### Container Memory Limits

The `checkout-recommendations` deployment **intentionally has no memory limits** to allow the OOM to occur. In production, you would set:

```yaml
resources:
  limits:
    memory: 512Mi  # Pod killed at 512MB
  requests:
    memory: 256Mi  # Guaranteed 256MB
```

### Emergency Cache Clear

If you need to stop the memory leak without restarting:

```bash
curl -X POST http://localhost:8080/api/recommendations/cache/clear
```

## 🎓 What This Demonstrates

1. **Unbounded caching is dangerous** - Memory grows indefinitely
2. **Unique keys prevent cache hits** - Every request adds new entries
3. **High concurrency accelerates leaks** - More users = faster OOM
4. **Memory limits are critical** - Without limits, pods can consume all node memory
5. **Monitoring is essential** - Track cache size and memory usage

## 📚 Related Documentation

- [Memory Leak Demo](../checkout-recommendations/MEMORY_LEAK_DEMO.md)
- [AI Agent Architecture](../checkout-recommendations/AI_AGENT_ARCHITECTURE.md)
- [Deployment Guide](../checkout-recommendations/DEPLOYMENT_GUIDE.md)

---

**⚠️ WARNING:** This configuration is for demonstration purposes only. Do NOT use in production!

**Made with Bob** - Demonstrating aggressive load testing 🚀