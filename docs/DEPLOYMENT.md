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
