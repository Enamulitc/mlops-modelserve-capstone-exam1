#!/usr/bin/env bash
set -euo pipefail

# Demo run script: start stack, materialize Feast features, run smoke tests, and trigger a synthetic alert.
# Usage: ./scripts/demo_run.sh

REPO_ROOT=$(dirname "$(dirname "${BASH_SOURCE[0]}")")
cd "$REPO_ROOT"

# Ensure env vars are set (SLACK_WEBHOOK_URL optional)
: ${SLACK_WEBHOOK_URL:=""}

echo "Starting docker-compose stack..."
docker compose up -d --build

# Wait for core services
echo "Waiting for services to become healthy (sleep 10s)..."
sleep 10

# Materialize Feast features using ephemeral container (if you prefer local host installation skip this)
echo "Materializing Feast features (ephemeral container)..."
docker run --rm -v "$PWD":/src -w /src \
  --network $(basename "$PWD")_default \
  python:3.11-slim bash -c "pip install 'feast[redis]' pandas pyarrow -q && cd feast_repo && feast apply && python3 ../scripts/materialize_features.py"

# Run smoke test
echo "Running smoke tests..."
.venv/bin/python scripts/smoke_test.py --url http://localhost:8000 || true

# Trigger synthetic alert for demo
echo "Triggering synthetic alert to Alertmanager..."
python3 scripts/trigger_synthetic_alert.py --alertmanager http://localhost:9093 || true

echo "Demo run complete."
