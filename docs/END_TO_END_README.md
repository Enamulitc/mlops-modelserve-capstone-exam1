# End-to-End: modelserve-capstone-exam1 — Learner's Guide

This guide maps the most important files and commands in this repository to the major
stages of a typical ML production workflow: data collection/sourcing, data versioning,
feature engineering, model training, and model serving. It's written for learners who
want a concise, actionable walkthrough with pointers to the exact files to read and run.

Use this as a quick reference while exploring the repository. Each stage lists the
purpose, key files, and the minimal commands to run locally (no cloud required).

---

## Quick architecture (one-liner)

- Raw dataset → feature engineering → features.parquet (offline) → Feast materialize →
  Feast online store (Redis) + MLflow Model Registry (models/artifacts in S3 or local) →
  FastAPI inference service uses Feast online features + MLflow model to serve predictions.

---

## Prerequisites (local dev)

- Docker & Docker Compose (for recommended full stack)
- Python 3.10+ and a virtualenv (for running training or dev server)
- (Optional) Kaggle dataset `fraudTrain.csv` placed in `training/` to run the real training

Recommended quick setup (from repo root):

```bash
# create & activate venv
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# then use Docker Compose to run the full local stack (mlflow, redis, api, prometheus)
docker compose up --build -d
```

If you don't have Docker, you can run parts (training, uvicorn) locally in the venv.

---

## Stage 1 — Data collection & sourcing

Purpose: obtain raw dataset(s) and store them where the training script can read them.

Key files:
- `training/fraudTrain.csv` — (expected input) raw dataset used for training (not included here)
- `scripts/create_dummy_features.py` — helper to generate small synthetic data for local testing
- `training/train.py` — reads the CSV and performs feature engineering (see Stage 3)

What to run:

1) If you have the real dataset, place it at `training/fraudTrain.csv`.
2) To test without the full dataset, run the dummy generator:

```bash
python scripts/create_dummy_features.py  # writes a small CSV you can use for testing
```

Files to inspect (learners):
- `training/train.py` — top-to-bottom: loads CSV, derives temporal features, encodes categoricals, creates `features.parquet`, trains and registers a model.

---

## Stage 2 — Data versioning & artifacts

Purpose: keep a reproducible record of training runs and model artifacts (MLflow) and
the offline feature dataset (features.parquet) used for materialization.

Key files / systems:
- `training/features.parquet` — produced by `training/train.py`; used by Feast as the offline source
- `docker-compose.yml` & `docker/mlflow` — the MLflow server + Postgres backend configuration
- MLflow Model Registry (web UI at `http://localhost:5000` when using Docker Compose)

What to run / check:

```bash
# After running training (see next stage), open MLflow UI:
open http://localhost:5000
# or if not on macOS
xdg-open http://localhost:5000 || true
```

Notes for learners:
- MLflow stores run metadata in Postgres and artifacts in the location configured by `MLFLOW_DEFAULT_ARTIFACT_ROOT`.
- The training script logs params, metrics, and calls `mlflow.sklearn.log_model(..., registered_model_name=...)` to register the model.

---

## Stage 3 — Feature engineering & Feast

Purpose: transform raw transactions into features, store offline features, and materialize online features for low-latency lookups.

Key files:
- `training/train.py` — computes features and writes `training/features.parquet`
- `feast_repo/feature_definitions.py` — Feast Entity and FeatureView definitions (maps `features.parquet` into Feast)
- `scripts/materialize_features.py` — helper to materialize offline features into Feast online store (if present)
- `app/feature_client.py` — code the API uses to fetch online features from Feast

Typical workflow (local):

1) Produce offline features (if training script produced `features.parquet` already, skip):

```bash
python training/train.py   # trains and writes training/features.parquet (and registers model)
```

2) Register Feast definitions and materialize into the online store (requires Feast CLI and Redis):

```bash
cd feast_repo
feast apply
# choose an appropriate time window that covers your features.parquet timestamps
feast materialize 2026-05-01T00:00:00 2026-05-09T00:00:00
```

3) Verify online feature lookup (Python helper):

```bash
python - <<'PY'
from feast import FeatureStore
fs = FeatureStore(repo_path='feast_repo')
print(fs.get_feature_view('proddetection_features'))
print(fs.get_online_features(['proddetection_features:amt'], entity_rows=[{'cc_num': 2703186189652095}]).to_dict())
PY
```

Learning notes:
- Feast separates offline storage (parquet/S3) from online storage (Redis). The materialize step writes recent values to Redis for low-latency lookup in the API.

---

## Stage 4 — Model training & registry

Purpose: train a model, evaluate it, log metrics & params to MLflow, and register the model into MLflow Model Registry (Production stage).

Key files:
- `training/train.py` — trains a sklearn pipeline (StandardScaler + RandomForest), logs params/metrics, calls `mlflow.sklearn.log_model(..., registered_model_name=...)`, and promotes to Production

What to run (local):

```bash
# ensure MLflow tracking server is running (via Docker Compose)
export MLFLOW_TRACKING_URI=http://localhost:5000
python training/train.py
```

After the script completes, open MLflow UI at `http://localhost:5000` and confirm the model appears under "Models" and a version is in the Production stage.

---

## Stage 5 — Model serving (FastAPI inference service)

Purpose: expose REST endpoints for health, predict, explain, and metrics. The API fetches features from Feast online store and runs the MLflow-loaded model for inference.

Key files:
- `app/main.py` — FastAPI app (routes: `/health`, `/predict`, `/predict/{cc_num}`, `/metrics`)
- `app/model_loader.py` — loads the Production model from MLflow and caches it
- `app/feature_client.py` — Feast wrapper used by the API to retrieve online features
- `app/metrics.py` — Prometheus metrics instruments
- `scripts/smoke_test.py` — convenience E2E smoke-test against the API
- `docker-compose.yml` — includes `api`, `mlflow`, `redis`, `prometheus`, `grafana`

Run the API (recommended: with docker compose so MLflow and Redis are available):

```bash
docker compose up --build -d

# Wait for the api service to be healthy, then test:
curl -s http://localhost:8000/health | jq .

# Try predict (example):
curl -s -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{"cc_num": 2703186189652095, "features": {"amt": 4.97, "age": 51}}' | jq .

# Open the interactive Swagger UI:
http://localhost:8000/docs
```

Notes for learners:
- The API gracefully falls back to request-provided `features` when Feast misses or is unavailable.
- Metrics are exported at `/metrics` in Prometheus format; Grafana dashboards are pre-provisioned under `monitoring/grafana`.

---

## Helpful verification & debug commands

- See containers and health:
  - `docker compose ps`
- Follow API logs:
  - `docker compose logs -f api`
- Check MLflow UI:
  - `http://localhost:5000`
- Check Redis (Feast online store):
  - `docker compose exec redis redis-cli ping` → `PONG`
- Run unit tests (project has pytest tests):
  - `.venv/bin/pytest -q`

---

## Files to read next (recommended order for learning)
1. `training/train.py` — end-to-end of dataset → features → model registration
2. `feast_repo/feature_definitions.py` — how features are declared for Feast
3. `app/feature_client.py` — how the API fetches online features and falls back
4. `app/model_loader.py` — how MLflow model retrieval & caching works
5. `app/main.py` — API routing, input validation, metrics, and prediction flow
6. `docker-compose.yml` — how local components are wired together for a demo

---

## Glossary (short)

- MLflow Tracking Server: stores experiment runs (params, metrics) and hosts Model Registry.
- Model Registry: MLflow component that stores model versions and stages (Staging/Production).
- Feast: feature store that separates offline features (data lake) from online store (Redis) for low-latency lookups.
- Materialize: Feast operation that copies offline feature data into the online store for a time window.
- Artifact store: where binary artifacts (model files) are stored; configured as S3 or local directory.

---

If you want, I can also add:
- a short script `scripts/inspect_features.py` that prints an online feature lookup for a provided `cc_num` (helpful for debugging Feast), or
- a minimal notebook that walks through training → materialize → serving in runnable cells.

Which one should I add next? Reply with `script` or `notebook` (or `both`) and I will implement it and push to your branch.
