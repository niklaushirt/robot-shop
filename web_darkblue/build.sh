#!/bin/bash
podman machine start

podman login quay.io -u niklaushirt@gmail.com

cd rs-load-gen-controller

export CONT_VERSION=2.0
export CONT_VERSION=darkblue
export CONT_VERSION=darkgreen
export CONT_VERSION=darkblue
podman buildx build --platform linux/amd64 -t quay.io/niklaushirt/rs-web:$CONT_VERSION --load -f=Dockerfile
podman push quay.io/niklaushirt/rs-web:$CONT_VERSION

