#!/usr/bin/env bash
#
# Cloud Agent start phase for Stan's Robot Shop.
#
# Runs on every boot. Brings up the Docker daemon (its data dir, including the
# images built during install, is already present) and starts the full stack.
# Must tolerate restarts and reach a clear success/failure state, then return.
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_DIR"

# 1. Start the Docker daemon (idempotent: the init script returns non-zero when
#    it is already running, so tolerate that and gate on an actual readiness check).
sudo service docker start || true
for _ in $(seq 1 60); do
    sudo docker info >/dev/null 2>&1 && break
    sleep 1
done
sudo docker info >/dev/null 2>&1 || { echo "Docker daemon failed to start" >&2; exit 1; }

# 2. The base VM ships an iptables-legacy FORWARD policy of DROP, which silently
#    blocks container-to-container traffic. Reapply ACCEPT on every boot.
sudo iptables-legacy -P FORWARD ACCEPT || true

# 3. Bring up the full Robot Shop stack (store front is published on :8080).
sudo docker compose up -d

echo "==> Robot Shop is starting; store front will be available on http://localhost:8080"
