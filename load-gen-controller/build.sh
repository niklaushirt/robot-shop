#!/bin/bash

# Build script for load-gen-controller

set -e

# Get the tag info from parent .env file
if [ -f ../.env ]; then
    eval $(egrep '[A-Z]+=' ../.env)
else
    echo "Warning: ../.env not found, using defaults"
    REPO=${REPO:-robotshop}
    TAG=${TAG:-latest}
fi

echo "Building load-gen-controller"
echo "Repository: $REPO"
echo "Tag: $TAG"

# Build the Docker image
docker build -t ${REPO}/rs-load-gen-controller:${TAG} .

echo "Build complete: ${REPO}/rs-load-gen-controller:${TAG}"
echo ""
echo "To push to registry:"
echo "  docker push ${REPO}/rs-load-gen-controller:${TAG}"

# Made with Bob
