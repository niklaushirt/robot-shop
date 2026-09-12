#!/bin/bash

# Script to build and push AMD64 images for IBM Cloud Kubernetes
# This ensures compatibility with x86_64/AMD64 cluster nodes

set -e

REPO="quay.io/arthurdm-quay/itom"
MAX_RETRIES=3
RETRY_DELAY=10
COMPRESSION_LEVEL=6
PLATFORM="linux/amd64"

echo "=========================================="
echo "Building AMD64 Images for IBM Cloud K8s"
echo "Repository: $REPO"
echo "Platform: $PLATFORM"
echo "Compression Level: $COMPRESSION_LEVEL"
echo "=========================================="
echo ""

push_with_retry() {
    local image=$1
    local retries=0
    
    while [ $retries -lt $MAX_RETRIES ]; do
        echo "Attempting to push $image (attempt $((retries + 1))/$MAX_RETRIES)..."
        
        if podman push --compression-level=$COMPRESSION_LEVEL $image; then
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

build_and_push() {
    local service=$1
    local image_name=$2
    local dockerfile_path=$3
    
    echo ""
    echo "=========================================="
    echo "Building: $service (AMD64)"
    echo "=========================================="
    
    if [ ! -f "$dockerfile_path/Dockerfile" ]; then
        echo "✗ Dockerfile not found at $dockerfile_path/Dockerfile"
        return 1
    fi
    
    echo "Building image: ${REPO}/${image_name}:latest"
    if podman build --platform=$PLATFORM --format docker -t ${REPO}/${image_name}:latest $dockerfile_path; then
        echo "✓ Successfully built ${REPO}/${image_name}:latest"
        
        echo "Pushing image..."
        push_with_retry "${REPO}/${image_name}:latest"
    else
        echo "✗ Failed to build ${REPO}/${image_name}:latest"
        return 1
    fi
}

# Array of services to build
services=(
    "cart:rs-cart:./cart"
    "catalogue:rs-catalogue:./catalogue"
    "dispatch:rs-dispatch:./dispatch"
    "mongodb:rs-mongodb:./mongo"
    "mysql:rs-mysql-db:./mysql"
    "payment:rs-payment:./payment"
    "ratings:rs-ratings:./ratings"
    "shipping:rs-shipping:./shipping"
    "user:rs-user:./user"
)

failed_services=()

for service_info in "${services[@]}"; do
    IFS=':' read -r service image_name path <<< "$service_info"
    
    if ! build_and_push "$service" "$image_name" "$path"; then
        failed_services+=("$service")
    fi
done

echo ""
echo "=========================================="
echo "Build and Push Summary"
echo "=========================================="

if [ ${#failed_services[@]} -eq 0 ]; then
    echo "✓ All AMD64 images built and pushed successfully!"
    echo ""
    echo "Next steps:"
    echo "1. Restart deployments: kubectl rollout restart deployment -n robot-shop --all"
    echo "2. Monitor pods: kubectl get pods -n robot-shop -w"
else
    echo "✗ Failed services: ${failed_services[*]}"
    exit 1
fi

echo ""

# Made with Bob
