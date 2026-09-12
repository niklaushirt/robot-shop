# Load Generator for Memory Leak Demo

This load generator creates traffic against the checkout-recommendations service to trigger and demonstrate the memory leak caused by unbounded MCP tool caching.

## 🎯 Purpose

Generate load to:
- Trigger the memory leak by creating unique cache entries
- Monitor cache growth in real-time
- Demonstrate how unbounded caching leads to OOM

## 🚀 Quick Start

### Using Docker Compose

```bash
# Start all services including load generator
docker-compose up -d

# View load generator logs
docker-compose logs -f memory-leak-load-gen

# Stop load generator
docker-compose stop memory-leak-load-gen
```

### Running Locally

```bash
cd load-generator

# Install dependencies
pip install requests

# Run sustained load test (default: 60 minutes, 10 req/min)
python load_test.py

# Run burst test (quick memory leak demo)
python load_test.py --mode burst --burst-size 100 --num-bursts 10

# Custom sustained test
python load_test.py --mode sustained --duration 30 --rate 20
```

## 📊 Load Test Modes

### 1. Sustained Load (Default)

Generates steady traffic over time to simulate normal usage:

```bash
python load_test.py --mode sustained --duration 60 --rate 10
```

**Parameters:**
- `--duration`: Test duration in minutes (default: 60)
- `--rate`: Requests per minute (default: 10)

**Memory Growth:**
- 10 req/min × 11 cache entries/req = 110 entries/min
- After 60 minutes: ~6,600 cache entries (~300 MB)

### 2. Burst Load

Sends bursts of requests with pauses between, simulating traffic spikes:

```bash
python load_test.py --mode burst --burst-size 100 --num-bursts 10
```

**Parameters:**
- `--burst-size`: Requests per burst (default: 100)
- `--num-bursts`: Number of bursts (default: 10)

**Memory Growth:**
- 100 requests × 11 cache entries = 1,100 entries per burst
- 10 bursts = 11,000 cache entries (~500 MB)
- **Faster memory leak demonstration!**

## 📈 Monitoring

### Real-time Cache Statistics

The load generator displays cache stats every 10 requests:

```
[2026-03-10 01:30:15] [INFO] 📊 Requests: 100 | Cache: 1,100 entries (49.5 MB) | Rate: 10.2 req/min | Errors: 0
[2026-03-10 01:31:15] [INFO] 📊 Requests: 200 | Cache: 2,200 entries (99.1 MB) | Rate: 10.1 req/min | Errors: 0
```

### Manual Cache Check

```bash
# Get cache statistics
curl http://localhost:8080/api/recommendations/cache/stats

# Response:
{
  "cache_entries": 2200,
  "cache_size_kb": 101478.4,
  "cache_size_mb": 99.1,
  "warning": "⚠️ Unbounded cache - memory will grow indefinitely"
}
```

### Docker Memory Usage

```bash
# Watch memory usage in real-time
docker stats checkout-recommendations

# Output:
CONTAINER ID   NAME                        CPU %     MEM USAGE / LIMIT
abc123         checkout-recommendations    5.2%      512MB / unlimited
```

## 🎮 Usage Examples

### Quick Demo (5 minutes)

```bash
# Fast burst test to quickly show memory leak
python load_test.py --mode burst --burst-size 200 --num-bursts 5
```

Expected result: ~11,000 cache entries (~500 MB) in 5 minutes

### Overnight Test

```bash
# Run overnight to trigger OOM
python load_test.py --mode sustained --duration 480 --rate 20
```

Expected result: ~105,600 cache entries (~5 GB) → OOM kill

### Stress Test

```bash
# High rate to quickly exhaust memory
python load_test.py --mode sustained --duration 30 --rate 100
```

Expected result: ~33,000 cache entries (~1.5 GB) in 30 minutes

## 🔧 Configuration

### Environment Variables

```bash
# Override service URL
export RECOMMENDATIONS_URL=http://localhost:8080
python load_test.py
```

### Command Line Options

```bash
python load_test.py --help

Options:
  --mode {sustained,burst}  Load test mode (default: sustained)
  --duration MINUTES        Duration for sustained test (default: 60)
  --rate REQUESTS_PER_MIN   Request rate for sustained test (default: 10)
  --burst-size SIZE         Requests per burst (default: 100)
  --num-bursts COUNT        Number of bursts (default: 10)
  --url URL                 Service URL (default: http://checkout-recommendations:8080)
```

## 📊 Expected Results

### Cache Growth Pattern

Each recommendation request generates approximately 11 cache entries:
- 1 entry for `get_product_popularity(limit=10)`
- 10+ entries for `get_product_ratings(sku)` (one per product)

### Memory Leak Timeline

| Time | Requests | Cache Entries | Memory | Status |
|------|----------|---------------|--------|--------|
| 10 min | 100 | 1,100 | ~50 MB | Normal |
| 1 hour | 600 | 6,600 | ~300 MB | Growing |
| 4 hours | 2,400 | 26,400 | ~1.2 GB | Warning |
| 8 hours | 4,800 | 52,800 | ~2.4 GB | Critical |
| 12 hours | 7,200 | 79,200 | ~3.6 GB | Near OOM |
| 16 hours | 9,600 | 105,600 | ~4.8 GB | **OOM Kill** |

## 🛑 Emergency Actions

### Clear Cache

```bash
# Clear cache to prevent OOM
curl -X POST http://localhost:8080/api/recommendations/cache/clear

# Response:
{
  "message": "Cache cleared",
  "entries_removed": 52800,
  "new_cache_size": 0
}
```

### Restart Service

```bash
# Restart to clear memory
docker-compose restart checkout-recommendations
```

## 📝 Output Example

```
======================================================================
🚀 Starting Memory Leak Load Test
======================================================================
Duration: 60 minutes
Rate: 10 requests/minute
Unique carts: True
Target URL: http://checkout-recommendations:8080
======================================================================
[2026-03-10 01:30:00] [INFO] Initial cache: 0 entries
[2026-03-10 01:30:06] [INFO] 📊 Requests: 10 | Cache: 110 entries (4.95 MB) | Rate: 10.0 req/min | Errors: 0
[2026-03-10 01:30:12] [INFO] 📊 Requests: 20 | Cache: 220 entries (9.91 MB) | Rate: 10.0 req/min | Errors: 0
...
======================================================================
📈 Final Statistics
======================================================================
Total requests: 600
Total errors: 0
Duration: 60.0 minutes
Average rate: 10.0 req/min
Initial cache: 0 entries
Final cache: 6600 entries
Cache growth: 6600 entries
Final memory: 297.00 MB
======================================================================
```

## 🎓 What This Demonstrates

1. **Unbounded Growth**: Cache grows linearly with unique requests
2. **No Eviction**: Old entries never removed, memory only increases
3. **Predictable Failure**: Can calculate time to OOM based on request rate
4. **Production Risk**: Shows why cache limits are critical

## 🔗 Related Documentation

- [Memory Leak Demo Guide](../checkout-recommendations/MEMORY_LEAK_DEMO.md)
- [Service Documentation](../checkout-recommendations/README.md)
- [Deployment Guide](../checkout-recommendations/DEPLOYMENT_GUIDE.md)

---

**Made with Bob** - Demonstrating memory leaks for educational purposes 🎓