#!/bin/bash

# Script to retry building and pushing failed images
# Run this after making Quay.io repositories public

set -e

REPO="quay.io/arthurdm-quay/itom"
MAX_RETRIES=3
RETRY_DELAY=10
COMPRESSION_LEVEL=6

echo "=========================================="
echo "Retrying Failed Robot Shop Images"
echo "Repository: $REPO"
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
    echo "Building: $service"
    echo "=========================================="
    
    if [ ! -f "$dockerfile_path/Dockerfile" ]; then
        echo "✗ Dockerfile not found at $dockerfile_path/Dockerfile"
        return 1
    fi
    
    echo "Building image: ${REPO}/${image_name}:latest"
    if podman build --format docker -t ${REPO}/${image_name}:latest $dockerfile_path; then
        echo "✓ Successfully built ${REPO}/${image_name}:latest"
        
        echo "Pushing image..."
        push_with_retry "${REPO}/${image_name}:latest"
    else
        echo "✗ Failed to build ${REPO}/${image_name}:latest"
        return 1
    fi
}

# Retry failed services
services=(
    "dispatch:rs-dispatch:./dispatch"
    "mysql:rs-mysql-db:./mysql"
    "shipping:rs-shipping:./shipping"
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
echo "Retry Summary"
echo "=========================================="

if [ ${#failed_services[@]} -eq 0 ]; then
    echo "✓ All failed images successfully built and pushed!"
    echo ""
    echo "All 9 services are now available in Quay.io:"
    echo "  - cart, catalogue, dispatch, mongodb, mysql"
    echo "  - payment, ratings, shipping, user"
    echo ""
    echo "The Kubernetes deployments should now be able to pull the images."
    echo "Monitor with: kubectl get pods -n robot-shop"
else
    echo "✗ Still failing: ${failed_services[*]}"
    echo ""
    echo "If authorization errors persist, verify:"
    echo "1. Repositories are set to PUBLIC in Quay.io"
    echo "2. You're logged in: podman login quay.io"
    exit 1
fi

echo ""

# Made with Bob
