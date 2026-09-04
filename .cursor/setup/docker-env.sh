#!/usr/bin/env bash
# Shared helpers for running the Robot Shop docker-compose stack inside a
# Cursor Cloud Agent VM (nested containers, no systemd).
set -euo pipefail

DOCKER_DAEMON_JSON=/etc/docker/daemon.json
DOCKERD_LOG=/tmp/dockerd.log

# In this VM Docker runs on a nested overlay filesystem where the default
# overlay2 / containerd-snapshotter storage driver cannot mount layers.
# fuse-overlayfs works and is the supported driver for nested containers.
write_daemon_json() {
  if [ ! -f "$DOCKER_DAEMON_JSON" ] || ! grep -q fuse-overlayfs "$DOCKER_DAEMON_JSON" 2>/dev/null; then
    sudo mkdir -p /etc/docker
    printf '%s\n' '{' \
      '  "storage-driver": "fuse-overlayfs",' \
      '  "features": { "containerd-snapshotter": false }' \
      '}' | sudo tee "$DOCKER_DAEMON_JSON" >/dev/null
  fi
}

# The base image ships stale iptables-legacy rules whose FORWARD policy is DROP.
# Docker 29 programs its accept rules through the nft backend, but both netfilter
# hooks are evaluated, so the legacy DROP silently blocks all container-to-container
# traffic. Make the legacy FORWARD chain permissive; real filtering stays with the
# nft-based Docker chains. This must run on every boot.
fix_legacy_forward() {
  if command -v iptables-legacy >/dev/null 2>&1; then
    sudo iptables-legacy -P FORWARD ACCEPT || true
  fi
}

dockerd_running() {
  sudo docker info >/dev/null 2>&1
}

start_dockerd() {
  if dockerd_running; then
    return 0
  fi
  write_daemon_json
  sudo bash -c "dockerd >>'$DOCKERD_LOG' 2>&1 &"
  # Wait for the daemon socket to come up.
  for _ in $(seq 1 30); do
    if dockerd_running; then
      return 0
    fi
    sleep 1
  done
  echo "dockerd failed to start; last log lines:" >&2
  tail -n 40 "$DOCKERD_LOG" >&2 || true
  return 1
}
