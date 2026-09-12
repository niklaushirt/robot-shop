#!/bin/bash

# 🚨 Quick OOM Trigger Script for checkout-recommendations service
# This script directly hammers the recommendations endpoint with unique cart IDs
# to rapidly fill the unbounded cache and trigger OOM

set -e

# Configuration
HOST="${1:-http://localhost:8080}"
NUM_REQUESTS="${2:-1000}"
CONCURRENT="${3:-50}"

echo "🚨 OOM Trigger Script"
echo "===================="
echo "Target: $HOST"
echo "Requests: $NUM_REQUESTS"
echo "Concurrent: $CONCURRENT"
echo ""

# Check if service is up
echo "Checking service health..."
if ! curl -s "$HOST/api/cache/stats" > /dev/null 2>&1; then
    echo "❌ Service not reachable at $HOST"
    echo "Make sure checkout-recommendations is running"
    exit 1
fi

echo "✅ Service is up"
echo ""

# Show initial cache stats
echo "📊 Initial cache stats:"
curl -s "$HOST/api/cache/stats" | python3 -m json.tool
echo ""

# Function to make a request with unique cart ID
make_request() {
    local cart_id="oom-trigger-$RANDOM-$RANDOM"
    curl -s "$HOST/api/recommendations/$cart_id" > /dev/null 2>&1
    echo -n "."
}

export -f make_request
export HOST

echo "🔥 Starting aggressive load..."
echo "Generating $NUM_REQUESTS requests with $CONCURRENT concurrent connections..."
echo ""

# Use GNU parallel if available, otherwise use xargs
if command -v parallel > /dev/null 2>&1; then
    seq 1 $NUM_REQUESTS | parallel -j $CONCURRENT make_request
else
    seq 1 $NUM_REQUESTS | xargs -P $CONCURRENT -I {} bash -c 'make_request'
fi

echo ""
echo ""
echo "✅ Load generation complete!"
echo ""

# Show final cache stats
echo "📊 Final cache stats:"
if curl -s "$HOST/api/cache/stats" > /dev/null 2>&1; then
    curl -s "$HOST/api/cache/stats" | python3 -m json.tool
else
    echo "❌ Service appears to be down (possibly OOM killed!)"
    echo ""
    echo "Check container status:"
    echo "  Docker: docker ps -a | grep checkout-recommendations"
    echo "  K8s: kubectl get pods | grep checkout-recommendations"
fi

echo ""
echo "🔍 To monitor memory:"
echo "  Docker: docker stats checkout-recommendations"
echo "  K8s: kubectl top pod -l app=checkout-recommendations"
echo ""
echo "🧹 To clear cache (if service is still up):"
echo "  curl -X POST $HOST/api/cache/clear"

# Made with Bob
