## Copilot instructions for this repository

This file helps an AI coding assistant start making correct, low-risk changes in the
`mlops-modelserve-capstone-exam1` repo. Keep suggestions focused, concrete, and
refer to files listed below.

Key points (quick):
- Core service: FastAPI app at `app/main.py` (endpoints: `/health`, `/predict`, `/predict/{cc_num}`, `/metrics`).
- Model loading: `app/model_loader.py` — uses MLflow. Env vars: `MLFLOW_TRACKING_URI`, `MLFLOW_MODEL_NAME`.
- Feature lookup: `app/feature_client.py` — Feast FeatureStore; canonical feature list is `FEATURE_NAMES` and entity key is `cc_num`.
- Metrics: `app/metrics.py` — Prometheus Counters/Histograms/Info exported at `/metrics`.
- Tests: lightweight unit tests in `app/tests/` — `conftest.py` provides global mocks (note: it intentionally does NOT mock `get_online_features`).
- Local multi-service run: `docker-compose.yml` + `Dockerfile` (see top-level README quickstart).

Architecture notes (what to read together):
- `app/main.py` orchestrates request flow: 1) lookup features via `feature_client.get_online_features`, 2) build DataFrame (feature vector), 3) run cached MLflow model from `model_loader.get_model`, 4) respond and update Prometheus metrics from `app/metrics.py`.
- `model_loader.py` caches a single model in module state (`_model`) and exposes `load_model()`, `get_model()`, `get_model_version()`. `load_model()` is called on FastAPI startup but failures are caught in `startup_event` to allow tests/dev without MLflow.
- `feature_client.py` lazily initialises Feast `FeatureStore` (via `get_store()`), so import-time failures are avoided. If Feast/Redis are unavailable the code returns a cache-miss and `fallback_features()` is used.

Developer workflows & commands (concrete):
- Quick local dev:
  - Create venv and install deps: `python3 -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt`.
  - Start local stack (MLflow, Redis/Feast, Prometheus, Grafana): `docker compose up -d --build`.
  - Open MLflow UI: `http://localhost:5000`, API: `http://localhost:8000/`, Grafana: `http://localhost:3000`.
- Run tests locally (no external services required thanks to test mocks):
  - `pytest app/tests/ -v` or `pytest -q` for shorter output.
  - Tests rely on autouse fixture in `app/tests/conftest.py` that mocks model loader but leaves `get_online_features` available for per-test patching.
- Run a quick smoke test against a running API: see `scripts/smoke_test.py` (it executes basic E2E checks; useful after `docker compose up`).

Important repository conventions and patterns (do not break):
- Entity key is `cc_num` across API, tests and Feast feature views.
- Canonical feature order and names are defined in `app/feature_client.py` as `FEATURE_NAMES`. Always build model inputs using this order (see `_build_feature_vector` in `app/main.py`).
- Tests intentionally avoid heavy external dependencies at import time. Prefer using the existing autouse fixture or patching `app.feature_client.get_online_features` per-test.
- Metric names and labels are centralized in `app/metrics.py`. If you add instrumentation, import and reuse the existing counters/histograms instead of redefining them.
- Model loading is cached in module-level state in `app/model_loader.py`. Avoid re-loading per-request and prefer `get_model()`.

Integration points and environment variables:
- MLflow tracking server: `MLFLOW_TRACKING_URI` (default `http://mlflow:5000`). Model name: `MLFLOW_MODEL_NAME` (default `proddetection-model`). See `app/model_loader.py`.
- Feast FeatureStore repo path: `FEAST_REPO_PATH` (defaults to `feast_repo/` relative to project root). The feature view name is `proddetection_features`.
- Prometheus/Grafana: monitoring config under `monitoring/` and metrics exposed at `/metrics`.
- Infrastructure as code: Pulumi code in `infrastructure/pulumi/` and Terraform in `infrastructure/terraform/`.

Concrete examples to follow when editing code:
- Adding a new inference endpoint: mirror `POST /predict` style — validate input with Pydantic models, do feature lookup via `get_online_features`, build DataFrame using `FEATURE_NAMES`, call `get_model()` and update metrics from `app/metrics.py`.
- Handling Feast failures: follow `feature_client.get_online_features` behaviour — return ({}, False) and let callers use `fallback_features()`; tests expect this pattern.
- Unit test pattern: use `fastapi.testclient.TestClient(app)` (see `app/tests/test_predict.py`) and let the global autouse fixture provide a mocked model. Patch `app.feature_client.get_online_features` in tests that need different behavior.

What to check before submitting a PR:
- Run `pytest app/tests/` and ensure no external network calls are performed during import. If you added runtime imports of optional deps (Feast/MLflow), lazy-import them inside functions as existing code does.
- Keep API schema backwards-compatible. When adding fields, update Pydantic response models in `app/main.py` and corresponding tests.
- Update `README.md` or `docs/` when you add public endpoints or change deployment steps.

If anything above is unclear or you need repository-specific examples expanded (tests, CI, or deployment steps), ask for the specific area and I will expand with examples and PR-ready edits.
