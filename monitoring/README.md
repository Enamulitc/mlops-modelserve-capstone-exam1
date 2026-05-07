# Monitoring & Alerting

This folder contains Prometheus rules, Grafana dashboards, and Alertmanager config used
by the ModelServe demo.

Key files:
- `prometheus/alerts.yml` — Prometheus alerting rules (service down, high latency, error rate).
- `alertmanager/alertmanager.yml` — Alertmanager configuration. Receivers are configured via
  environment variables (no secrets are committed to the repo).
- `docker-compose.alerts.yml` — Minimal compose file to run Prometheus + Alertmanager for local demo.

Switching between real and mock receivers
- Slack: set `SLACK_WEBHOOK_URL` to enable Slack notifications.
- PagerDuty (real): set `PAGERDUTY_ROUTING_KEY` to enable the PagerDuty receiver (will page on-call users).
- PagerDuty (mock/safe demo): set `MOCK_PAGERDUTY_URL` to an HTTP endpoint (e.g. the included
  `monitoring/mock_pagerduty_receiver.py`) to capture PagerDuty payloads without paging.

Example (safe demo):

```bash
# start mock receiver that prints requests
python3 monitoring/mock_pagerduty_receiver.py --port 8080 &
export MOCK_PAGERDUTY_URL=http://host.docker.internal:8080
export SLACK_WEBHOOK_URL="https://hooks.slack.com/services/XXX/YYY/ZZZ"  # optional
docker compose -f monitoring/docker-compose.alerts.yml up -d
```

Security note: never commit real webhook URLs or PagerDuty routing keys to the repository. Use
environment variables or CI secrets.
