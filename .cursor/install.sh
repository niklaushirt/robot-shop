#!/usr/bin/env bash
#
# Idempotent Cloud Agent install step for Stan's Robot Shop.
#
# Responsibilities (durable, source-derived setup):
#   1. Install Docker Engine + Compose plugin if missing.
#   2. Configure the daemon for the nested Cloud Agent VM (fuse-overlayfs).
#   3. Start the daemon long enough to build every service image so the images
#      become part of the environment snapshot / build.
#
# Per-boot concerns (starting the daemon, `docker compose up`) live in start.sh.
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_DIR"

log() { echo "[install] $*"; }

install_docker() {
  if command -v docker >/dev/null 2>&1; then
    log "Docker already installed: $(docker --version)"
    return
  fi
  log "Installing Docker Engine + Compose plugin"
  export DEBIAN_FRONTEND=noninteractive
  # Keep apt fully non-interactive (sudo drops env vars, so pin it in apt.conf).
  echo 'Dpkg::Options { "--force-confdef"; "--force-confold"; }; APT::Get::Assume-Yes "true";' \
    | sudo tee /etc/apt/apt.conf.d/99noninteractive >/dev/null
  sudo install -m 0755 -d /etc/apt/keyrings
  if [ ! -f /etc/apt/keyrings/docker.gpg ]; then
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg \
      | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
    sudo chmod a+r /etc/apt/keyrings/docker.gpg
  fi
  echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" \
    | sudo tee /etc/apt/sources.list.d/docker.list >/dev/null
  sudo -E apt-get update -qq
  sudo -E apt-get install -y -qq \
    docker-ce docker-ce-cli containerd.io \
    docker-buildx-plugin docker-compose-plugin fuse-overlayfs
  sudo usermod -aG docker "$(id -un)" || true
  log "Installed $(docker --version)"
}

configure_daemon() {
  # overlay-on-overlay is unsupported in the nested VM; use fuse-overlayfs and
  # the classic image store so image builds and mounts work.
  sudo mkdir -p /etc/docker
  sudo tee /etc/docker/daemon.json >/dev/null <<'JSON'
{
  "storage-driver": "fuse-overlayfs",
  "features": { "containerd-snapshotter": false }
}
JSON
}

start_daemon() {
  if sudo docker info >/dev/null 2>&1; then
    log "Docker daemon already running"
    return
  fi
  log "Starting Docker daemon"
  sudo bash -c 'nohup dockerd >/var/log/dockerd.log 2>&1 &'
  for _ in $(seq 1 30); do
    if sudo docker info >/dev/null 2>&1; then
      log "Docker daemon is up"
      return
    fi
    sleep 1
  done
  log "Docker daemon failed to start:"
  sudo tail -n 40 /var/log/dockerd.log || true
  exit 1
}

build_images() {
  log "Building Robot Shop service images (this can take several minutes on a cold cache)"
  sudo -E docker compose build
  log "Build complete:"
  sudo docker images --format '  {{.Repository}}:{{.Tag}}' | grep -i 'rs-' || true
}

install_docker
configure_daemon
start_daemon
build_images
log "Install finished successfully"
