#!/usr/bin/env bash
#
# Cloud Agent install phase for Stan's Robot Shop.
#
# Sets up Docker-in-Docker inside the Cloud Agent VM and builds every service
# image from source. This runs after the repository is checked out and must be
# idempotent: it is safe to run repeatedly and against a cached/partially
# prepared state. No long-lived process is started here (see start.sh).
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_DIR"

# 1. Install Docker Engine + Compose plugin (skip if already present).
if ! command -v docker >/dev/null 2>&1; then
    echo "==> Installing Docker Engine"
    sudo install -m 0755 -d /etc/apt/keyrings
    if [ ! -f /etc/apt/keyrings/docker.gpg ]; then
        curl -fsSL https://download.docker.com/linux/ubuntu/gpg \
            | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
        sudo chmod a+r /etc/apt/keyrings/docker.gpg
    fi
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" \
        | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
    sudo apt-get update -qq
    sudo DEBIAN_FRONTEND=noninteractive apt-get install -y \
        -o Dpkg::Options::="--force-confnew" \
        docker-ce docker-ce-cli containerd.io \
        docker-buildx-plugin docker-compose-plugin fuse-overlayfs
fi

# 2. The Cloud Agent VM root is itself an overlay mount, so Docker's default
#    overlay2/overlayfs driver cannot mount overlay-on-overlay. Use fuse-overlayfs.
sudo mkdir -p /etc/docker
echo '{ "storage-driver": "fuse-overlayfs" }' | sudo tee /etc/docker/daemon.json > /dev/null

# 3. Start the daemon just for the build (start.sh owns the per-boot daemon).
sudo service docker restart
for _ in $(seq 1 60); do
    sudo docker info >/dev/null 2>&1 && break
    sleep 1
done

# 4. The base VM ships an iptables-legacy FORWARD policy of DROP, which silently
#    blocks container-to-container traffic. Allow it so builds can reach the network.
sudo iptables-legacy -P FORWARD ACCEPT || true

# 5. Build all Robot Shop service images from source (layer cache makes reruns fast).
echo "==> Building Robot Shop images"
sudo docker compose build

echo "==> Install complete"
