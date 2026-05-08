# ModelServe — ProdDetection

> A production-grade ML serving platform built for the MLOps with Cloud Season 2 Capstone Exam.
> It wraps a trained sklearn-compatible model with an MLflow registry, Feast feature store,
> FastAPI inference API, Prometheus + Grafana observability, Terraform IaC (see ADR), and a GitHub Actions CI/CD pipeline.

📖 Full Engineering Documentation → [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)

## Quickstart (Local)

```bash
git clone https://github.com/Enamulitc/mlops-modelserve-capstone-exam1.git
cd mlops-modelserve-capstone-exam1
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
docker compose up -d --build
```

Visit http://localhost:5000 for MLflow, http://localhost:8000/health for API health, and http://localhost:3000 for Grafana.

---

## Project Requirements

1. **FastAPI**: For building the RESTful API for model serving.
   - **Why Needed**: Provides a high-performance framework for serving machine learning models with easy integration of OpenAPI documentation.

2. **MLflow**: For model tracking and registry.
   - **Why Needed**: Ensures reproducibility and version control for machine learning models.

3. **Feast**: For feature management and online feature store.
   - **Why Needed**: Simplifies feature engineering and ensures consistency between training and serving.

4. **Prometheus and Grafana**: For monitoring and alerting.
   - **Why Needed**: Provides insights into the system's performance and ensures reliability through alerts.

5. **Pulumi**: For infrastructure as code.
   - **Why Needed**: Automates the deployment of cloud infrastructure, ensuring consistency and scalability.

6. **Docker**: For containerization.
   - **Why Needed**: Ensures the application runs consistently across different environments.

7. **GitHub Actions**: For CI/CD automation.
   - **Why Needed**: Automates testing, building, and deployment processes.

## Prerequisites

1. **Python 3.8+**: Required for running the FastAPI application and other scripts.
2. **Docker**: Ensure Docker is installed and running on your system.
3. **Pulumi CLI**: Install Pulumi for managing infrastructure.
4. **MLflow Tracking Server**: Set up an MLflow tracking server for model registry.
5. **Feast Feature Store**: Configure Feast for feature management.
6. **Prometheus and Grafana**: Install and configure for monitoring.
7. **Cloud Provider Account**: Required for deploying infrastructure (e.g., AWS, GCP, Azure).

## Implementation Steps

### 1. Setup
- Clone the repository.
- Navigate to the project directory.
- Install dependencies using `pip install -r requirements.txt`.

### 2. Model Training
- Navigate to the `training/` directory.
- Run `train.py` to train the model and register it in MLflow.

### 3. Feature Store Setup
- Navigate to the `feast_repo/` directory.
- Define features in `feature_definitions.py`.
- Apply the feature store configuration using Feast CLI.

### 4. API Development
- Navigate to the `app/` directory.
- Implement the FastAPI application in `main.py`.
- Add model loading logic in `model_loader.py`.
- Add feature lookup logic in `feature_client.py`.
- Define Prometheus metrics in `metrics.py`.

### 5. Testing
- Write unit tests in `tests/`.
- Run tests using `pytest`.

### Testing, CI, and End-to-end checks

- Unit tests: put unit tests under `app/tests/`. The repository includes pytest and pytest-cov in `requirements.txt`.
- CI: GitHub Actions workflows run the unit test suite (`pytest app/tests/ -v --cov=app`). Make sure the CI job passes on push/PR — this is part of the exam rubric.
- Test isolation: avoid contacting external services (MLflow server, Feast registry) from unit tests. Mock MLflow and Feast client calls so tests are fast and deterministic.
- Coverage bonus: the rubric awards a small bonus for test coverage above 80% (meaningful tests, not just trivial asserts).

- End-to-end (E2E) API checks after deployment: for the demo and for your deployed system it's recommended to include a simple post-deploy E2E script that:
   1. Calls each public inference endpoint (for example `/predict` and `/predict/{cc_num}?explain=true`).
   2. Verifies the response status code is 200 and that required JSON fields are present (prediction, probability, model_version, timestamp, cc_num, etc.).
   3. Prints a brief report summarizing the checks (endpoint, status, pass/fail, key fields). This script can be invoked manually after deployment and included in CI as an optional smoke-test step.

      Example scripts:
      - `scripts/smoke_test.py` — runs basic E2E checks against the API and prints a pass/fail report.
      - `scripts/trigger_synthetic_alert.py` — posts a synthetic alert to Alertmanager (useful to demo alert routing to Slack/PagerDuty).

- README policy for new APIs: when you add a new public API endpoint, update the `README.md` (or docs) to list:
   - the endpoint path and HTTP method,
   - required/requested JSON schema or query params,
   - expected response fields and types,
   - whether the endpoint is covered by unit/E2E tests and the test file path.


### 6. Monitoring Setup
- Configure Prometheus in `monitoring/prometheus/prometheus.yml`.
- Configure Grafana dashboards in `monitoring/grafana/`.

### 7. Infrastructure Deployment
- Navigate to the `infrastructure/` directory.
- Define infrastructure in `__main__.py`.
- Deploy using Pulumi CLI.

### 8. CI/CD
- Configure GitHub Actions workflows in `.github/workflows/deploy.yml`.
- Ensure automated testing and deployment.

### 9. Dockerization
- Create a `Dockerfile` for the application.
- Use `docker-compose.yml` for multi-container setup.

### 10. Documentation
- Add detailed documentation in `docs/ARCHITECTURE.md`.
- Include architecture diagrams in `docs/diagrams/`.

### 11. Deployment
- Deploy the application using Docker or cloud infrastructure.
- Verify the deployment and monitor using Prometheus and Grafana.

### 12. Maintenance
- Regularly update dependencies and monitor system performance.
- Address issues and improve the system iteratively.