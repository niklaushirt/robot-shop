#!/bin/bash
podman machine start

podman login quay.io -u niklaushirt@gmail.com

cd tools/97_addons/ibm-aiops-demo-ui/demoui


export CONT_VERSION=5.1.2
podman buildx build --platform linux/amd64 -t quay.io/niklaushirt/ibm-aiops-demo-ui:$CONT_VERSION --load -f=Containerfile_small
podman push quay.io/niklaushirt/ibm-aiops-demo-ui:$CONT_VERSION
