#!/usr/bin/env bash
#
# Per-boot start step for Stan's Robot Shop.
#   1. Ensure the Docker daemon is running (it is not persisted across boots).
#   2. Bring the full compose stack up in the background.
#   3. Wait until the web storefront answers before returning.
#
# Safe to run repeatedly: dockerd start is guarded and `compose up -d`
# reconciles the running stack instead of duplicating it.
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_DIR"

log() { echo "[start] $*"; }

ensure_forwarding() {
  # The nested Cloud Agent VM boots with the legacy iptables FORWARD policy set
  # to DROP, while Docker 29 installs its accept rules in the nftables backend.
  # Because packets traverse both backends, the legacy DROP silently blocks all
  # container-to-container traffic (apps cannot reach mongodb/mysql/redis/etc).
  # Ensure the FORWARD policy is ACCEPT on both backends so bridge traffic flows.
  for ipt in iptables-legacy iptables; do
    if command -v "$ipt" >/dev/null 2>&1; then
      sudo "$ipt" -P FORWARD ACCEPT 2>/dev/null || true
    fi
  done
  log "Enabled IPv4 FORWARD (container-to-container networking)"
}

ensure_daemon() {
  if sudo docker info >/dev/null 2>&1; then
    log "Docker daemon already running"
    return
  fi
  log "Starting Docker daemon"
  sudo mkdir -p /etc/docker
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

wait_for_web() {
  log "Waiting for the storefront on http://localhost:8080"
  for _ in $(seq 1 60); do
    if curl -fsS -o /dev/null http://localhost:8080/ 2>/dev/null; then
      log "Storefront is responding"
      return 0
    fi
    sleep 2
  done
  log "Storefront did not become ready in time; recent service status:"
  sudo docker compose ps || true
  return 1
}

ensure_daemon
ensure_forwarding
log "Bringing up the Robot Shop stack"
sudo -E docker compose up -d
wait_for_web
log "Robot Shop is up. Storefront: http://localhost:8080"
