FROM ghcr.io/mlflow/mlflow:v2.11.3

# Install psycopg2-binary so MLflow can talk to PostgreSQL backends
USER root
RUN pip install --no-cache-dir psycopg2-binary==2.9.9 boto3

# Revert to default user (if the base image had one, this keeps permissions sane)
USER 0
