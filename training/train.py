"""
train.py — Model Training + MLflow Registration
------------------------------------------------
Dataset:  https://www.kaggle.com/datasets/kartik2112/fraud-detection
File:     fraudTrain.csv (~1.3M rows, 22 features)
Target:   is_fraud  (binary: 0 = legitimate, 1 = fraud)
Entity:   cc_num    (credit card number — Feast join key)

This script:
  1. Loads fraudTrain.csv
  2. Engineers features (15-20 features)
  3. Splits into train/test (stratified on is_fraud)
  4. Trains a sklearn-compatible model with class_weight='balanced'
  5. Logs params, metrics, and model artifact to MLflow
  6. Registers the model in the MLflow Model Registry → stage: Production
  7. Exports features.parquet (feature columns + cc_num + event_timestamp)
     for Feast ingestion
  8. Exports sample_request.json with a valid cc_num for testing

Prerequisites:
  - MLflow and Postgres must be running: docker compose up postgres mlflow
  - fraudTrain.csv must be placed in: training/fraudTrain.csv

Usage:
  python training/train.py

IMPORTANT: Reproducible — running again registers a new version with comparable metrics.
A baseline AUC of 0.85+ is sufficient.
"""

import os, json, logging
# os: interact with the operating system (paths, env vars)
# json: read/write JSON for sample request output
# logging: structured runtime logging for status and debug messages
import pandas as pd
# pandas: primary data manipulation library (CSV read, DataFrame ops)
import numpy as np
# numpy: numerical helpers and array operations used by pandas/sklearn
from datetime import datetime, timezone
# datetime: timestamp formatting for MLflow run names and event timestamps

import mlflow
# mlflow: tracking experiments, logging params/metrics/artifacts
import mlflow.sklearn
# mlflow.sklearn: helpers to log sklearn models as MLflow artifacts
from mlflow.tracking import MlflowClient
# MlflowClient: programmatic access to model registry (promote model stages)

from sklearn.model_selection import train_test_split
# train_test_split: split dataset into train/test sets reproducibly
from sklearn.ensemble import RandomForestClassifier
# RandomForestClassifier: chosen model (robust, works out-of-the-box for tabular data)
from sklearn.preprocessing import LabelEncoder, StandardScaler
# LabelEncoder: convert categorical/string columns to integer labels
# StandardScaler: scale numeric features to mean=0, std=1 for stable training
from sklearn.pipeline import Pipeline
# Pipeline: chain preprocessing (scaler) + estimator into a single object
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score, roc_auc_score,
)
# sklearn.metrics: common evaluation metrics (accuracy, precision, recall, F1, ROC AUC)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

MLFLOW_TRACKING_URI = os.getenv("MLFLOW_TRACKING_URI", "http://localhost:5000")
# MLFLOW_TRACKING_URI: where the MLflow tracking server is reachable (env overrideable)
EXPERIMENT_NAME     = os.getenv("MLFLOW_EXPERIMENT", "proddetection-fraud")
# EXPERIMENT_NAME: MLflow experiment to log runs under (grouping label)
MODEL_NAME          = os.getenv("MLFLOW_MODEL_NAME", "proddetection-model")
# MODEL_NAME: registered model name in MLflow Model Registry

TRAINING_DIR    = os.path.dirname(os.path.abspath(__file__))
# TRAINING_DIR: directory of this script (used to build relative file paths)
DATA_PATH       = os.path.join(TRAINING_DIR, "fraudTrain.csv")
# DATA_PATH: expected location of the raw CSV dataset
FEATURES_PATH   = os.path.join(TRAINING_DIR, "features.parquet")
# FEATURES_PATH: output parquet used for Feast ingestion (features + entity + timestamp)
SAMPLE_REQ_PATH = os.path.join(TRAINING_DIR, "sample_request.json")
# SAMPLE_REQ_PATH: example request saved for quick testing of the API

ENTITY_COL  = "cc_num"
# ENTITY_COL: primary entity key (credit card number) used for Feast joins
TARGET_COL  = "is_fraud"
# TARGET_COL: binary target column name in the dataset
FEATURE_COLS = [
    "amt", "city_pop", "lat", "long", "merch_lat", "merch_long",
    "hour", "day_of_week", "month", "age",
    "category_encoded", "gender_encoded", "state_encoded",
    "job_encoded", "trans_count",
]
# FEATURE_COLS: columns we plan to use as input features for the model


def load_and_engineer(path):
    # Read CSV into a pandas DataFrame (pandas provides flexible parsing)
    logger.info(f"Loading data from {path}")
    df = pd.read_csv(path)
    logger.info(f"Loaded {len(df):,} rows")

    # Parse transaction timestamp into datetime and derive temporal features
    df["trans_date_trans_time"] = pd.to_datetime(df["trans_date_trans_time"])
    # hour, day_of_week, month are useful time-based signals for fraud
    df["hour"]        = df["trans_date_trans_time"].dt.hour
    df["day_of_week"] = df["trans_date_trans_time"].dt.dayofweek
    df["month"]       = df["trans_date_trans_time"].dt.month

    # Convert date-of-birth to datetime and compute approximate age in years
    df["dob"] = pd.to_datetime(df["dob"], errors="coerce")
    df["age"] = (pd.Timestamp.now() - df["dob"]).dt.days // 365

    # Encode categorical columns to integer labels (simple approach for tree models)
    le = LabelEncoder()
    df["category_encoded"] = le.fit_transform(df["category"].astype(str))
    df["gender_encoded"]   = le.fit_transform(df["gender"].astype(str))
    df["state_encoded"]    = le.fit_transform(df["state"].astype(str))
    df["job_encoded"]      = le.fit_transform(df["job"].astype(str))

    # Sort by time to ensure trans_count (cumulative transaction index) is chronological
    df = df.sort_values("trans_date_trans_time")
    # trans_count: number of prior transactions per entity — a simple behavioral feature
    df["trans_count"] = df.groupby(ENTITY_COL).cumcount()

    # Only keep features that actually exist in the DataFrame (defensive)
    available = [c for c in FEATURE_COLS if c in df.columns]
    logger.info(f"Using features: {available}")

    # X: feature matrix (float), y: binary target (int)
    X = df[available].fillna(0).astype(float)
    y = df[TARGET_COL].astype(int)

    # Prepare a separate parquet file (features + entity + timestamp) for Feast ingestion
    feast_df = X.copy()
    feast_df[ENTITY_COL]        = df[ENTITY_COL].values
    feast_df["event_timestamp"] = df["trans_date_trans_time"].values
    # Persist to parquet — compact, fast format that Feast materializers can read
    feast_df.to_parquet(FEATURES_PATH, index=False)
    logger.info(f"Saved features.parquet → {FEATURES_PATH}  ({len(feast_df):,} rows)")

    return X, y, available, df[ENTITY_COL].values


def train_model(X_train, y_train, X_test, y_test, feature_names):
    mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
    mlflow.set_experiment(EXPERIMENT_NAME)

    # Start an MLflow run. This logs params/metrics/artifacts to the configured tracking server.
    # Start an MLflow run context — grouped logging of params/metrics/artifacts
    with mlflow.start_run(run_name=f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}") as run:
        params = {
            "model_type": "RandomForestClassifier",
            "n_estimators": 100, "max_depth": 12,
            "min_samples_split": 10, "class_weight": "balanced", "random_state": 42,
        }
        mlflow.log_params(params)
        mlflow.log_param("feature_list", feature_names)
        mlflow.log_param("train_rows", len(X_train))
        mlflow.log_param("test_rows", len(X_test))
        mlflow.log_param("fraud_rate_train", round(float(y_train.mean()), 4))

        # Build a simple sklearn pipeline: scaler + RandomForest
        pipeline = Pipeline([
            ("scaler", StandardScaler()),
            ("clf", RandomForestClassifier(
                n_estimators=100, max_depth=12, min_samples_split=10,
                class_weight="balanced", random_state=42, n_jobs=-1,
            )),
        ])
        # Fit the pipeline: scaler followed by the RandomForest estimator
        pipeline.fit(X_train, y_train)

        # Predict labels and probabilities on the test set for evaluation
        y_pred = pipeline.predict(X_test)
        # y_prob is the positive-class probability used by ROC AUC
        y_prob = pipeline.predict_proba(X_test)[:, 1]
        metrics = {
            "accuracy":  accuracy_score(y_test, y_pred),
            "precision": precision_score(y_test, y_pred, zero_division=0),
            "recall":    recall_score(y_test, y_pred, zero_division=0),
            "f1":        f1_score(y_test, y_pred, zero_division=0),
            "roc_auc":   roc_auc_score(y_test, y_prob),
        }
        # Log computed metrics to MLflow so they are visible in the UI
        mlflow.log_metrics(metrics)
        for k, v in metrics.items():
            logger.info(f"  {k}: {v:.4f}")

    # After the run context, persist the sklearn pipeline as an MLflow model artifact
    # and register it in the Model Registry under MODEL_NAME. The artifact transport
    # (where the model files are stored) is configured via MLflow settings (S3, local, ...).
    mlflow.sklearn.log_model(pipeline, "model", registered_model_name=MODEL_NAME)
    # Log the run id so we can trace this registration from the logs
    logger.info(f"Run ID: {run.info.run_id}")
    return run.info.run_id


def promote_to_production():
    client = MlflowClient(MLFLOW_TRACKING_URI)
    versions = client.get_latest_versions(MODEL_NAME, stages=["None", "Staging"])
    if not versions:
        versions = list(client.search_model_versions(f"name='{MODEL_NAME}'"))
    if versions:
        latest = sorted(versions, key=lambda v: int(v.version))[-1]
        client.transition_model_version_stage(
            name=MODEL_NAME, version=latest.version,
            stage="Production", archive_existing_versions=True,
        )
        logger.info(f"Model '{MODEL_NAME}' v{latest.version} → Production")


def write_sample_request(cc_nums, feature_names):
    payload = {
        "cc_num": int(cc_nums[0]),
        "features": {col: 0.0 for col in feature_names},
    }
    with open(SAMPLE_REQ_PATH, "w") as f:
        json.dump(payload, f, indent=2)
    logger.info(f"Saved sample_request.json → {SAMPLE_REQ_PATH}")


if __name__ == "__main__":
    if not os.path.exists(DATA_PATH):
        logger.error(
            f"Dataset not found at {DATA_PATH}\n"
            "Download fraudTrain.csv from Kaggle:\n"
            "  https://www.kaggle.com/datasets/kartik2112/fraud-detection\n"
            "Place it in the training/ directory."
        )
        raise SystemExit(1)

    X, y, feature_names, cc_nums = load_and_engineer(DATA_PATH)
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    train_model(X_train, y_train, X_test, y_test, feature_names)
    promote_to_production()
    write_sample_request(cc_nums, feature_names)
    logger.info("Done. Next: feast apply → materialize_features.py → docker compose restart api")
