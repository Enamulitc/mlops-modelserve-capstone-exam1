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
import pandas as pd
import numpy as np
from datetime import datetime, timezone

import mlflow
import mlflow.sklearn
from mlflow.tracking import MlflowClient

from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score, roc_auc_score,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

MLFLOW_TRACKING_URI = os.getenv("MLFLOW_TRACKING_URI", "http://localhost:5000")
EXPERIMENT_NAME     = os.getenv("MLFLOW_EXPERIMENT", "proddetection-fraud")
MODEL_NAME          = os.getenv("MLFLOW_MODEL_NAME", "proddetection-model")

TRAINING_DIR    = os.path.dirname(os.path.abspath(__file__))
DATA_PATH       = os.path.join(TRAINING_DIR, "fraudTrain.csv")
FEATURES_PATH   = os.path.join(TRAINING_DIR, "features.parquet")
SAMPLE_REQ_PATH = os.path.join(TRAINING_DIR, "sample_request.json")

ENTITY_COL  = "cc_num"
TARGET_COL  = "is_fraud"
FEATURE_COLS = [
    "amt", "city_pop", "lat", "long", "merch_lat", "merch_long",
    "hour", "day_of_week", "month", "age",
    "category_encoded", "gender_encoded", "state_encoded",
    "job_encoded", "trans_count",
]


def load_and_engineer(path):
    logger.info(f"Loading data from {path}")
    df = pd.read_csv(path)
    logger.info(f"Loaded {len(df):,} rows")

    df["trans_date_trans_time"] = pd.to_datetime(df["trans_date_trans_time"])
    df["hour"]        = df["trans_date_trans_time"].dt.hour
    df["day_of_week"] = df["trans_date_trans_time"].dt.dayofweek
    df["month"]       = df["trans_date_trans_time"].dt.month

    df["dob"] = pd.to_datetime(df["dob"], errors="coerce")
    df["age"] = (pd.Timestamp.now() - df["dob"]).dt.days // 365

    le = LabelEncoder()
    df["category_encoded"] = le.fit_transform(df["category"].astype(str))
    df["gender_encoded"]   = le.fit_transform(df["gender"].astype(str))
    df["state_encoded"]    = le.fit_transform(df["state"].astype(str))
    df["job_encoded"]      = le.fit_transform(df["job"].astype(str))

    df = df.sort_values("trans_date_trans_time")
    df["trans_count"] = df.groupby(ENTITY_COL).cumcount()

    available = [c for c in FEATURE_COLS if c in df.columns]
    logger.info(f"Using features: {available}")

    X = df[available].fillna(0).astype(float)
    y = df[TARGET_COL].astype(int)

    feast_df = X.copy()
    feast_df[ENTITY_COL]        = df[ENTITY_COL].values
    feast_df["event_timestamp"] = df["trans_date_trans_time"].values
    feast_df.to_parquet(FEATURES_PATH, index=False)
    logger.info(f"Saved features.parquet → {FEATURES_PATH}  ({len(feast_df):,} rows)")

    return X, y, available, df[ENTITY_COL].values


def train_model(X_train, y_train, X_test, y_test, feature_names):
    mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
    mlflow.set_experiment(EXPERIMENT_NAME)

    # Start an MLflow run. This logs params/metrics/artifacts to the configured tracking server.
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
        pipeline.fit(X_train, y_train)

        y_pred = pipeline.predict(X_test)
        y_prob = pipeline.predict_proba(X_test)[:, 1]
        metrics = {
            "accuracy":  accuracy_score(y_test, y_pred),
            "precision": precision_score(y_test, y_pred, zero_division=0),
            "recall":    recall_score(y_test, y_pred, zero_division=0),
            "f1":        f1_score(y_test, y_pred, zero_division=0),
            "roc_auc":   roc_auc_score(y_test, y_prob),
        }
        mlflow.log_metrics(metrics)
        for k, v in metrics.items():
            logger.info(f"  {k}: {v:.4f}")

    # Log and register the sklearn pipeline. MLflow will upload the artifact to the
    # configured artifact store (S3 in production, or local volume in dev).
    mlflow.sklearn.log_model(pipeline, "model", registered_model_name=MODEL_NAME)
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
