# Memory Leak Demonstration: Checkout Recommendations Service

## 🚨 Overview

This service demonstrates a **memory leak** caused by **unbounded caching** of MCP (Model Context Protocol) tool call results. The leak occurs when the AI agent caches every unique tool call result without any limit, causing memory to grow indefinitely until the pod runs out of memory (OOM).

## 🎯 Purpose

This is an **intentional memory leak** designed to showcase:
- How unbounded caching can cause memory issues in production
- The importance of cache size limits and eviction policies
- How to monitor and detect memory leaks in AI agents
- Best practices for caching in production systems

## 🔍 The Memory Leak Pattern

### Vulnerable Code

The `AIAgent` class in [`server.py`](server.py) implements an unbounded cache:

```python
class AIAgent:
    def __init__(self):
        # 🚨 In-memory cache with NO LIMIT - this will cause memory leak
        self.tool_cache = {}
    
    def call_mcp_tool(self, tool_name: str, **kwargs) -> Dict[str, Any]:
        cache_key = f"{tool_name}:{hash(str(sorted(kwargs.items())))}"
        
        if cache_key in self.tool_cache:
            return self.tool_cache[cache_key]
        
        # Execute tool and cache result
        result = execute_tool(tool_name, **kwargs)
        
        # 🚨 MEMORY LEAK: Store result in unbounded cache
        self.tool_cache[cache_key] = result
        
        return result
```

### Why This Causes a Memory Leak

1. **Every unique tool call** creates a new cache entry
2. **No cache size limit** - cache grows indefinitely
3. **No eviction policy** - old entries never removed
4. **Large payloads** - MCP tool results can be substantial
5. **High request volume** - many recommendations = many cache entries

### MCP Tools Being Cached

The service caches results from two MCP tools:

1. **`get_product_popularity(limit=10)`** - Returns popular products
2. **`get_product_ratings(sku="PRODUCT_SKU")`** - Returns ratings for each SKU

With 12+ products in the catalog, each recommendation request can generate:
- 1 cache entry for popularity data
- 10+ cache entries for individual product ratings
- **11+ new cache entries per request**

## 📊 Memory Growth Scenario

### Example Calculation

- **Request 1**: 11 cache entries (~50 KB)
- **Request 10**: 110 cache entries (~500 KB)
- **Request 100**: 1,100 cache entries (~5 MB)
- **Request 1,000**: 11,000 cache entries (~50 MB)
- **Request 10,000**: 110,000 cache entries (~500 MB)
- **Request 100,000**: 1,100,000 cache entries (~5 GB) → **OOM Kill**

### Timeline to OOM

With moderate load (10 requests/minute):
- **1 hour**: ~600 requests → ~30 MB
- **8 hours**: ~4,800 requests → ~240 MB
- **24 hours**: ~14,400 requests → ~720 MB
- **3 days**: ~43,200 requests → ~2.1 GB → **Approaching OOM**

## 🔧 How to Trigger the Memory Leak

### 1. Start the Service

```bash
docker-compose up -d checkout-recommendations
```

### 2. Generate Load

Use the load generator or curl:

```bash
# Single request
curl http://localhost:8080/api/recommendations/test-cart-123

# Load test (requires load-gen service)
docker-compose up load-gen
```

### 3. Monitor Memory Growth

```bash
# Check cache statistics
curl http://localhost:8080/api/recommendations/cache/stats

# Watch memory usage
docker stats checkout-recommendations

# View logs
docker-compose logs -f checkout-recommendations
```

### 4. Observe the Leak

Watch for these log messages:

```
💾 Cached result for get_product_ratings | Cache size: 1000 entries | Estimated memory: ~45.23 KB
💾 Cached result for get_product_ratings | Cache size: 5000 entries | Estimated memory: ~225.67 KB
💾 Cached result for get_product_ratings | Cache size: 10000 entries | Estimated memory: ~512.34 KB
⚠️  Cache growing rapidly! Consider implementing cache limits.
```

## 📈 Monitoring Endpoints

### Cache Statistics

```bash
GET /cache/stats
```

Response:
```json
{
  "cache_entries": 15234,
  "cache_size_kb": 687.45,
  "cache_size_mb": 0.67,
  "warning": "⚠️ Unbounded cache - memory will grow indefinitely"
}
```

### Health Check (includes cache stats)

```bash
GET /health
```

Response:
```json
{
  "app": "OK",
  "service": "checkout-recommendations",
  "watsonx": true,
  "catalogue": true,
  "cache_stats": {
    "cache_entries": 15234,
    "cache_size_kb": 687.45,
    "cache_size_mb": 0.67
  }
}
```

### Emergency Cache Clear

```bash
POST /cache/clear
```

Response:
```json
{
  "message": "Cache cleared",
  "entries_removed": 15234,
  "new_cache_size": 0
}
```

## 🛡️ How to Fix the Memory Leak

### Option 1: Implement Cache Size Limit

```python
from collections import OrderedDict

class AIAgent:
    def __init__(self, max_cache_size=1000):
        self.tool_cache = OrderedDict()
        self.max_cache_size = max_cache_size
    
    def call_mcp_tool(self, tool_name: str, **kwargs):
        cache_key = f"{tool_name}:{hash(str(sorted(kwargs.items())))}"
        
        if cache_key in self.tool_cache:
            # Move to end (LRU)
            self.tool_cache.move_to_end(cache_key)
            return self.tool_cache[cache_key]
        
        result = execute_tool(tool_name, **kwargs)
        
        # Add to cache
        self.tool_cache[cache_key] = result
        
        # Evict oldest if over limit
        if len(self.tool_cache) > self.max_cache_size:
            self.tool_cache.popitem(last=False)
        
        return result
```

### Option 2: Use TTL (Time-To-Live)

```python
import time

class AIAgent:
    def __init__(self, cache_ttl=3600):  # 1 hour
        self.tool_cache = {}
        self.cache_ttl = cache_ttl
    
    def call_mcp_tool(self, tool_name: str, **kwargs):
        cache_key = f"{tool_name}:{hash(str(sorted(kwargs.items())))}"
        
        # Check if cached and not expired
        if cache_key in self.tool_cache:
            cached_time, result = self.tool_cache[cache_key]
            if time.time() - cached_time < self.cache_ttl:
                return result
            else:
                del self.tool_cache[cache_key]
        
        result = execute_tool(tool_name, **kwargs)
        self.tool_cache[cache_key] = (time.time(), result)
        
        return result
```

### Option 3: Use External Cache (Redis)

```python
import redis
import json

class AIAgent:
    def __init__(self):
        self.redis_client = redis.Redis(host='redis', port=6379)
    
    def call_mcp_tool(self, tool_name: str, **kwargs):
        cache_key = f"mcp:{tool_name}:{hash(str(sorted(kwargs.items())))}"
        
        # Check Redis cache
        cached = self.redis_client.get(cache_key)
        if cached:
            return json.loads(cached)
        
        result = execute_tool(tool_name, **kwargs)
        
        # Cache in Redis with TTL
        self.redis_client.setex(
            cache_key,
            3600,  # 1 hour TTL
            json.dumps(result)
        )
        
        return result
```

## 🎓 Learning Points

### What This Demo Teaches

1. **Unbounded data structures are dangerous** - Always set limits
2. **Memory leaks can be subtle** - They grow slowly over time
3. **Monitoring is critical** - Track cache size and memory usage
4. **Cache eviction is necessary** - Implement LRU, TTL, or size limits
5. **External caches help** - Redis, Memcached provide built-in limits

### Production Best Practices

1. ✅ **Set cache size limits** (e.g., max 10,000 entries)
2. ✅ **Implement TTL** (e.g., 1 hour expiration)
3. ✅ **Use LRU eviction** (remove least recently used)
4. ✅ **Monitor cache metrics** (size, hit rate, memory)
5. ✅ **Set memory limits** in Kubernetes/Docker
6. ✅ **Use external cache** for distributed systems
7. ✅ **Implement circuit breakers** for cache failures

## 🚀 Kubernetes Deployment Notes

### Memory Leak Configuration

The Kubernetes deployment **intentionally omits memory limits** to allow the leak to manifest:

```yaml
# ⚠️ MEMORY LEAK DEMO: No memory limits set intentionally
# In production, you would set limits like:
# resources:
#   limits:
#     memory: 512Mi
#   requests:
#     memory: 256Mi
```

### To Enable Memory Limits (Fix the Leak)

Edit [`K8s/helm/templates/recommendations-deployment.yaml`](../K8s/helm/templates/recommendations-deployment.yaml):

```yaml
resources:
  limits:
    cpu: 500m
    memory: 512Mi  # Pod will be killed if it exceeds this
  requests:
    cpu: 200m
    memory: 256Mi  # Guaranteed memory allocation
```

## 📚 Related Documentation

- [AI Agent Architecture](AI_AGENT_ARCHITECTURE.md)
- [MCP Server Documentation](MCP_SERVER_README.md)
- [Deployment Guide](DEPLOYMENT_GUIDE.md)
- [Quick Start Guide](QUICK_START_GUIDE.md)

## ⚠️ Warning

**This is a demonstration of a memory leak for educational purposes.**

Do NOT deploy this configuration to production without implementing proper cache limits and memory constraints!

---

**Made with Bob** - Demonstrating what NOT to do in production 😄