#!/usr/bin/env bash
# Idempotent ensure for the shared deploy router container on the deploy host.
#
# Builds a self-contained image (Caddyfile baked in — no bind mount) and brings
# the container up. Re-running is cheap and safe:
#   - Caddyfile unchanged + container already running  -> no-op (no blip)
#   - Caddyfile changed, or container missing/stopped   -> recreate
#
# Designed to be called both as a one-time manual bootstrap AND on a schedule
# (Jenkinsfile.cleanup runs it hourly) so a dead router self-heals within an
# hour. Because the image is self-contained, the container also recovers on its
# own across reboots via `--restart unless-stopped`.
set -euo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"
NETWORK="${NETWORK:-preview-net}"
NAME="${NAME:-caddy-preview-router}"
IMAGE="${IMAGE:-caddy-preview-router:latest}"
HOST_PORT="${HOST_PORT:-127.0.0.1:18080}"

docker network inspect "$NETWORK" >/dev/null 2>&1 \
  || docker network create "$NETWORK"

# Build (layer-cached; only the COPY layer changes when Caddyfile changes).
docker build -q -t "$IMAGE" "$DIR" >/dev/null

want_img="$(docker image inspect "$IMAGE" --format '{{.Id}}')"
have_img="$(docker inspect "$NAME" --format '{{.Image}}' 2>/dev/null || echo "")"
running="$(docker inspect "$NAME" --format '{{.State.Running}}' 2>/dev/null || echo "false")"

if [ "$running" = "true" ] && [ "$have_img" = "$want_img" ]; then
  echo "router already up-to-date on ${HOST_PORT} (image ${want_img:0:19})"
  exit 0
fi

docker rm -f "$NAME" >/dev/null 2>&1 || true
docker run -d \
  --name "$NAME" \
  --restart unless-stopped \
  -p "${HOST_PORT}:80" \
  --network "$NETWORK" \
  "$IMAGE"

echo "router (re)created on ${HOST_PORT} using image ${IMAGE}"
