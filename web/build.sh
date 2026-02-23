#!/bin/bash

export CONT_VERSION=white1

# Create the Image
docker buildx build --platform linux/amd64 -t quay.io/niklaushirt/rs-web:$CONT_VERSION --load .
docker push quay.io/niklaushirt/rs-web:$CONT_VERSION

