# Deployment & Runbook

This file documents how to run the full system locally and in AWS (Terraform-backed). It is written as a runbook for the TA demo.

## Prerequisites (local)
- Linux or macOS
- Docker & Docker Compose
- Python 3.10+ (for local training / scripts)
- Kaggle credentials (optional for full training): place `~/.kaggle/kaggle.json`

## Local quickstart

1. Create and activate virtualenv

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
```

2. Start core services with docker compose (in this repo root)

```bash
docker compose up -d --build
```

3. Verify services

- MLflow: http://localhost:5000
- API: http://localhost:8000/health
- Prometheus: http://localhost:9090
- Grafana: http://localhost:3000 (admin/admin by default)

4. (Optional) Download dataset and train

```bash
.venv/bin/kaggle datasets download -d kartik2112/fraud-detection -p training/ --unzip
.venv/bin/python training/train.py
```

This will register a model in MLflow and produce `training/features.parquet` and `training/sample_request.json`.

5. Materialize Feast features (example using ephemeral container)

```bash
docker run --rm -v "$PWD":/src -w /src \
  --network mlops-modelserve-capstone-exam1_default \
  python:3.11-slim bash -c "pip install 'feast[redis]' pandas pyarrow -q && cd feast_repo && feast apply && python3 ../scripts/materialize_features.py"
```

6. Test prediction

```bash
curl -X POST http://localhost:8000/predict -H 'Content-Type: application/json' -d @training/sample_request.json
```

## AWS (Terraform) — overview

The Terraform code is in `infrastructure/terraform/`. It provisions:
- VPC, public subnet
- EC2 instance with an instance profile `modelserve-ec2-workload-role`
- S3 bucket: `modelserve-artifacts-<suffix>` for MLflow artifacts
- ECR repository: `modelserve/proddetection`

**Note:** The author used Terraform in their personal AWS account due to environment constraints described in `docs/ADRs/0001-terraform-vs-pulumi.md`.

## CI/CD (GitHub Actions)

- `ci.yml`: runs unit tests on push/PR
- `deploy.yml`: runs on push to `main`: tests → build & push image to ECR → SSH deploy to EC2

**Secrets required (Repository secrets):**
- `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` (IAM user for Actions)
- `DEPLOY_HOST` (EC2 public IP)
- `DEPLOY_USER` (ssh user: `ubuntu`)
- `DEPLOY_SSH_KEY` (private key for SSH, added to `~/.ssh/authorized_keys` on EC2)

## Destroy / Cleanup

To tear down Terraform-managed infra (run from `infrastructure/terraform`):

```bash
terraform destroy
```

Be sure to `pulumi destroy` if a Pulumi stack is later added.

## Alerting & Night-time Response

The stack includes Prometheus alerting rules (`monitoring/prometheus/alerts.yml`) and an
Alertmanager configuration (`monitoring/alertmanager/alertmanager.yml`) that is set up to
route alerts to a Slack webhook. Follow these steps to enable alert delivery to your team:

1. Create a Slack Incoming Webhook and copy the webhook URL.
2. Set the environment variable `SLACK_WEBHOOK_URL` in your runtime (or populate it in
   a Docker Compose environment file) with the webhook URL.

Run Alertmanager locally for the demo (example):

```bash
docker run --rm -p 9093:9093 \
  -e SLACK_WEBHOOK_URL="$SLACK_WEBHOOK_URL" \
  -v "$PWD/monitoring/alertmanager/alertmanager.yml":/etc/alertmanager/alertmanager.yml \
  prom/alertmanager:latest
```

### Running the local alert stack (Prometheus + Alertmanager)

An example docker-compose file is provided at `monitoring/docker-compose.alerts.yml`. To run
the local alerting stack:

```bash
export SLACK_WEBHOOK_URL="https://hooks.slack.com/services/XXX/YYY/ZZZ"
export PAGERDUTY_ROUTING_KEY="<pagerduty-integration-key>"   # optional
docker compose -f monitoring/docker-compose.alerts.yml up -d
```

To fire a synthetic alert for testing, you can use Prometheus' API to push a fake rule evaluation
or temporarily change the `alerts.yml` expression to a tautology (for demo only). Always revert
after testing.

Recommendations for robust night-time response:

- Slack: good for team notifications and quick acknowledgement. Configure a dedicated `#alerts`
  channel and limit noisy alerts using Prometheus alert thresholds and `for` durations.
- PagerDuty (or equivalent): use for on-call escalation and paging. Alertmanager supports
  a PagerDuty receiver — add it to `alertmanager.yml` for guaranteed paging.
- AWS GuardDuty: for production deployments in AWS, enable GuardDuty and connect its findings
  to your incident response flow (GuardDuty is complementary — it surfaces security events
  rather than application-level outages). You can configure GuardDuty to forward findings to
  SNS -> Lambda -> PagerDuty/Slack for automated security alerts.

If you want, I can:
- add a PagerDuty receiver template to `monitoring/alertmanager/alertmanager.yml` (you'll need
  a PagerDuty integration key), and
- add a short `docker-compose.alerts.yml` to orchestrate Prometheus + Alertmanager for local demo.
