# OOM Trigger Improvements - 30 Second Memory Leak

## 🎯 Objective
Make the memory leak in checkout-recommendations service trigger an OOM error within **30 seconds** using a single button click in the admin UI.

## 🚨 Changes Made

### 1. Aggressive Memory Leak in `checkout-recommendations/server.py`

**Problem:** Original implementation cached small objects (~10KB each), requiring thousands of requests to fill memory.

**Solution:** Added 1MB padding to each cache entry:

```python
# Each cache entry now includes:
- Original MCP tool result (~10KB)
- 1MB padding string ('X' * 1024 * 1024)
- Metadata (cart_id, timestamp, cache_key)
- Duplicate storage in memory_padding list

Result: Each request creates ~2MB of memory growth (cache + padding list)
```

**Impact:**
- **Before:** ~10KB per cache entry → need 50,000 requests for 500MB
- **After:** ~2MB per cache entry → need only 250 requests for 500MB

### 2. Enhanced OOM Trigger in `load-gen-controller/app.py`

**Changes:**
- Increased parallel workers from 10 → **20**
- Changed default target from 1000 → **500 requests**
- Improved batch processing (50 → 100 requests per batch)
- Added microsecond timestamps + random numbers for 100% unique cart IDs
- Better error handling (don't log every error)

**Performance:**
- 20 parallel workers × 25 requests/second = **500 requests in ~25 seconds**
- 500 requests × 1MB padding = **~500MB memory growth**
- Total time to OOM: **~30 seconds**

### 3. Updated Admin UI

**Files Modified:**
- `web/static/admin.html` - Updated descriptions and default value
- `web/static/js/controller.js` - Changed default from 1000 → 500

**UI Changes:**
- Title: "🚨 OOM Trigger (30 Second OOM)"
- Description: Explains 1MB padding per request
- Default: 500 requests (down from 1000)
- Help text: "500 requests × 1MB = ~500MB in 30 seconds"

## 📊 Memory Growth Timeline

| Time | Requests | Memory Growth | Total Memory |
|------|----------|---------------|--------------|
| 0s   | 0        | 0 MB          | ~50 MB       |
| 10s  | ~200     | ~200 MB       | ~250 MB      |
| 20s  | ~400     | ~400 MB       | ~450 MB      |
| 30s  | ~500     | ~500 MB       | ~550 MB      |
| 35s  | -        | -             | **OOM Kill** |

## 🎮 How to Use

### Option 1: Admin UI (Recommended)
1. Navigate to `http://your-robot-shop/admin`
2. Click **"💥 TRIGGER OOM"** button
3. Watch memory climb in real-time
4. OOM occurs within 30 seconds

### Option 2: API Call
```bash
curl -X POST http://load-gen-controller:8080/api/oom/trigger \
  -H "Content-Type: application/json" \
  -d '{"target_requests": 500}'
```

### Option 3: Custom Request Count
```bash
# Faster OOM (15 seconds)
curl -X POST http://load-gen-controller:8080/api/oom/trigger \
  -H "Content-Type: application/json" \
  -d '{"target_requests": 250}'

# Slower OOM (60 seconds)
curl -X POST http://load-gen-controller:8080/api/oom/trigger \
  -H "Content-Type: application/json" \
  -d '{"target_requests": 1000}'
```

## 🔍 Monitoring

### Real-time Memory in Admin UI
The admin panel shows:
- Current memory usage (MB)
- Memory limit (MB)
- Percentage used
- Progress bar with color coding:
  - Green: < 70%
  - Yellow: 70-90%
  - Red: > 90%

### Kubernetes Monitoring
```bash
# Watch pod memory
kubectl top pod -l service=checkout-recommendations --watch

# Watch for OOM events
kubectl get events --watch | grep OOM

# Check pod status
kubectl get pod -l service=checkout-recommendations
```

### Cache Statistics
```bash
# Check cache size
curl http://checkout-recommendations:8080/cache/stats

# Response shows:
{
  "cache_entries": 500,
  "padding_entries": 500,
  "cache_size_mb": 250.5,
  "padding_size_mb": 250.5,
  "total_size_mb": 501.0,
  "warning": "⚠️ Unbounded cache - memory will grow indefinitely"
}
```

## 🛡️ Emergency Cache Clear

If you need to stop the memory leak without restarting:

```bash
curl -X POST http://checkout-recommendations:8080/cache/clear
```

This clears both the cache and padding list, freeing memory immediately.

## 🎓 What This Demonstrates

### Memory Leak Pattern
1. **Unbounded caching** - No size limits on cache
2. **Unique keys** - Each cart ID creates new entries
3. **Large payloads** - 1MB padding accelerates growth
4. **No eviction** - Old entries never removed
5. **Duplicate storage** - Data stored in multiple places

### Production Lessons
1. ✅ Always set cache size limits
2. ✅ Implement LRU or TTL eviction
3. ✅ Monitor memory usage
4. ✅ Set Kubernetes memory limits
5. ✅ Use external caches (Redis) for large data
6. ✅ Avoid storing large objects in memory

## 📈 Comparison: Before vs After

| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| Memory per request | ~10 KB | ~2 MB | 200x |
| Requests for OOM | ~50,000 | ~250 | 200x |
| Time to OOM | ~30 min | ~30 sec | 60x |
| Parallel workers | 10 | 20 | 2x |
| Default requests | 1000 | 500 | Optimized |

## ⚠️ Important Notes

1. **This is a demo** - Do NOT use in production
2. **Memory limits** - The deployment intentionally has no memory limits to allow OOM
3. **Cleanup** - Use cache clear endpoint or restart pod to recover
4. **Monitoring** - Always watch memory during demo
5. **IBM Cloud** - Works on any Kubernetes cluster including IBM Cloud

## 🚀 Deployment

The changes are ready to deploy. Simply rebuild and redeploy:

```bash
# Rebuild checkout-recommendations
cd checkout-recommendations
docker build -t robotshop/rs-checkout-recommendations:latest .

# Rebuild load-gen-controller
cd ../load-gen-controller
docker build -t robotshop/rs-load-gen-controller:latest .

# Rebuild web (for admin UI)
cd ../web
docker build -t robotshop/rs-web:latest .

# Push images
docker push robotshop/rs-checkout-recommendations:latest
docker push robotshop/rs-load-gen-controller:latest
docker push robotshop/rs-web:latest

# Restart pods in Kubernetes
kubectl rollout restart deployment checkout-recommendations
kubectl rollout restart deployment load-gen-controller
kubectl rollout restart deployment web
```

---

**Made with Bob** - Demonstrating aggressive memory leak triggering 🚀