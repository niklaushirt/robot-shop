#!/usr/bin/env bash
# Per-boot startup for Robot Shop: reconcile networking, start the Docker
# daemon, and bring the stack up. Tolerant of restarts and already-running state.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT"
# shellcheck source=/dev/null
source "$REPO_ROOT/.cursor/setup/docker-env.sh"

fix_legacy_forward
start_dockerd

echo "Starting Robot Shop stack (docker compose up -d)..."
sudo docker compose up -d

echo "Waiting for the web frontend on http://localhost:8080 ..."
for _ in $(seq 1 60); do
  code="$(curl -s -o /dev/null -w '%{http_code}' http://localhost:8080/ || true)"
  if [ "$code" = "200" ]; then
    echo "Web frontend is up (HTTP 200)."
    break
  fi
  sleep 2
done

sudo docker compose ps
