# Demo Runbook (concise)

This runbook lists the minimal commands to run during the live TA demo. Keep it to the point — each step should take < 2 minutes.

Prereqs
- Docker & docker-compose
- Python 3.10+ (for local scripts)
- Optional: Slack webhook URL (for alerting demo)

1) Start the stack (build & run)

```bash
# from repo root
docker compose up -d --build
```

2) Materialize features (ephemeral container)

```bash
docker run --rm -v "$PWD":/src -w /src \
  --network $(basename "$PWD")_default \
  python:3.11-slim bash -c "pip install 'feast[redis]' pandas pyarrow -q && cd feast_repo && feast apply && python3 ../scripts/materialize_features.py"
```

3) Verify API health

```bash
curl -sSf http://localhost:8000/health | jq
```

4) Run smoke tests

```bash
python3 scripts/smoke_test.py --url http://localhost:8000
```

5) Demo alerting (safe mode)
- Start mock PagerDuty receiver (safe; will not page on-call users):

```bash
python3 monitoring/mock_pagerduty_receiver.py --port 8080 &
export MOCK_PAGERDUTY_URL=http://host.docker.internal:8080
export SLACK_WEBHOOK_URL="https://hooks.slack.com/services/XXX/YYY/ZZZ"  # optional
docker compose -f monitoring/docker-compose.alerts.yml up -d
python3 scripts/trigger_synthetic_alert.py --alertmanager http://localhost:9093
```

6) Show dashboards
- Grafana: http://localhost:3000 (admin/admin)
- Prometheus: http://localhost:9090

7) Stop the stack after demo

```bash
docker compose down -v
```
