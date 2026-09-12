#!/bin/bash

# Script to push images to Quay.io with retry logic

set -e

REPO="quay.io/arthurdm-quay/itom"
MAX_RETRIES=5
RETRY_DELAY=10

echo "=========================================="
echo "Pushing Robot Shop Images to Quay.io"
echo "=========================================="
echo ""

push_with_retry() {
    local image=$1
    local retries=0
    
    while [ $retries -lt $MAX_RETRIES ]; do
        echo "Attempting to push $image (attempt $((retries + 1))/$MAX_RETRIES)..."
        
        if podman push $image; then
            echo "✓ Successfully pushed $image"
            return 0
        else
            retries=$((retries + 1))
            if [ $retries -lt $MAX_RETRIES ]; then
                echo "Push failed, retrying in $RETRY_DELAY seconds..."
                sleep $RETRY_DELAY
            fi
        fi
    done
    
    echo "✗ Failed to push $image after $MAX_RETRIES attempts"
    return 1
}

# Check images exist
echo "Checking local images..."
podman images | grep -E "rs-load-gen-controller|rs-web|rs-load" | grep "$REPO"

echo ""
echo "Starting push process..."
echo ""

# Push load-gen-controller (smallest, already succeeded once)
echo "1/3: Pushing load-gen-controller..."
push_with_retry "${REPO}/rs-load-gen-controller:latest"

echo ""

# Push web
echo "2/3: Pushing web..."
push_with_retry "${REPO}/rs-web:latest"

echo ""

# Push load-gen (largest)
echo "3/3: Pushing load-gen..."
push_with_retry "${REPO}/rs-load:latest"

echo ""
echo "=========================================="
echo "All images pushed successfully!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Deploy to Kubernetes:"
echo "   cd K8s/helm"
echo "   helm upgrade --install robot-shop . \\"
echo "     --set image.repo=${REPO} \\"
echo "     --set image.version=latest \\"
echo "     --set image.pullPolicy=Always \\"
echo "     --set psp.enabled=true \\"
echo "     --namespace robot-shop"
echo ""
echo "2. Access admin UI:"
echo "   kubectl port-forward -n robot-shop svc/web 8080:8080"
echo "   open http://localhost:8080/admin"
echo ""

# Made with Bob
