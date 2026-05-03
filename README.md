# ModelServe — ProdDetection

> A production-grade ML serving platform built for the MLOps with Cloud Season 2 Capstone Exam.
> It wraps a trained sklearn-compatible model with an MLflow registry, Feast feature store,
> FastAPI inference API, Prometheus + Grafana observability, Pulumi IaC, and a GitHub Actions CI/CD pipeline.

📖 Full Engineering Documentation → [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)

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