#!/usr/bin/env bash
set -euo pipefail

# feast_docker_runner.sh
# Run Feast CLI and materialize features inside a temporary Docker container.
# This avoids installing Feast on the host; it attaches to the docker-compose
# network so it can reach Redis started by docker compose.
#
# Usage:
#   ./prereqs-deployment/feast_docker_runner.sh [--network NETWORK_NAME]
#
# By default the script assumes the docker-compose network is named
# <project>_default (the default for `docker compose up`). You can override
# with --network.

PROJ_NAME=$(basename "$(pwd)")
DEFAULT_NET="${PROJ_NAME}_default"
NETWORK="${DEFAULT_NET}"

if [ "${1:-}" = "--network" ] && [ -n "${2:-}" ]; then
  NETWORK="$2"
fi

echo "Using docker network: $NETWORK"

# Check if network exists
if ! docker network inspect "$NETWORK" >/dev/null 2>&1; then
  echo "Warning: network '$NETWORK' not found. Falling back to host network." 1>&2
  NET_OPT="--network host"
else
  NET_OPT="--network $NETWORK"
fi

PWD_ABS=$(pwd)

echo "Launching temporary container to run Feast CLI and materialize features..."
docker run --rm $NET_OPT -v "$PWD_ABS":/work -w /work/feast_repo python:3.10-slim bash -lc '
  set -euo pipefail
  python -m pip install --upgrade pip
  pip install --no-cache-dir feast[redis]
  export REDIS_HOST=redis
  export REDIS_PORT=6379
  echo "Running: feast apply (inside container)"
  feast apply
  echo "Running: materialize features (inside container)"
  python3 /work/scripts/materialize_features.py
'

echo "Feast apply + materialize completed."
