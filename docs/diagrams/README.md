# Architecture Diagrams

This directory contains image versions of the architecture diagrams documented in
[`../ARCHITECTURE.md`](../ARCHITECTURE.md).

## Diagrams

| File | Description |
|------|-------------|
| `local-topology.svg` | Local development topology (Docker Compose on developer machine / Poridhi VM) with numbered request/metrics flow |
| `production-topology.svg` | Production topology — Single EC2 node on AWS with GitHub Actions CI/CD, ECR, S3, and numbered deployment/inference flow |

## 1) Local Topology (Image)

![Local Topology — Numbered Flow](./local-topology.svg)

### Step-by-step (Local)

1. Client sends `POST /predict` to FastAPI.
2. FastAPI reads model metadata/version from MLflow Registry.
3. MLflow uses PostgreSQL backend store.
4. FastAPI requests features through Feast SDK.
5. Feast fetches online features from Redis.
6. FastAPI exposes `/metrics`; Prometheus scrapes it.
7. Grafana reads Prometheus for dashboards and alerts.

## 2) Production Topology (Image)

![Production Topology — Numbered Flow](./production-topology.svg)

### Step-by-step (Production)

1. Developer pushes to `main`.
2. GitHub Actions runs the `test` job.
3. `build-and-push` builds/pushes image to ECR.
4. `deploy` SSHes to EC2 and updates `api` container.
5. FastAPI starts and loads Production model from MLflow.
6. MLflow reads model metadata from PostgreSQL.
7. FastAPI requests entity features via Feast SDK.
8. Feast reads Redis online store for feature values.
9. MLflow artifacts/offline data are persisted in S3.
10. Prometheus scrapes `/metrics` from FastAPI.
11. Grafana visualizes metrics and alert health.

> **Note:** The ASCII diagrams in `ARCHITECTURE.md` (Section 2) are the authoritative
> source. The images here are rendered for readability during the live demo and TA review.
> If you regenerate these images (e.g., from Excalidraw or draw.io), commit them here and
> keep the numbered flow in sync with this README.
