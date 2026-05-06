"""
model_loader.py — MLflow model loading logic
--------------------------------------------
Loads the latest Production model from the MLflow Registry on startup.
The loaded pipeline is cached in module-level state so it is only
loaded once per process.
"""

import os
import logging

try:
    import mlflow
    import mlflow.sklearn
    from mlflow.tracking import MlflowClient
except Exception:  # pragma: no cover - import-time fallback for test environments
    mlflow = None
    MlflowClient = None

logger = logging.getLogger(__name__)

MLFLOW_TRACKING_URI = os.getenv("MLFLOW_TRACKING_URI", "http://mlflow:5000")
MODEL_NAME = os.getenv("MLFLOW_MODEL_NAME", "proddetection-model")

# Module-level cache
_model = None
_model_version: str = "unknown"


def load_model():
    """
    Load the Production-stage model from MLflow Registry.
    Called once at FastAPI startup.
    Sets module-level _model and _model_version.
    """
    global _model, _model_version

    mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
    client = MlflowClient(MLFLOW_TRACKING_URI)

    try:
        versions = client.get_latest_versions(MODEL_NAME, stages=["Production"])
        if not versions:
            raise RuntimeError(
                f"No Production-stage version found for model '{MODEL_NAME}'. "
                "Run training/train.py first."
            )
        latest = versions[0]
        _model_version = latest.version
        model_uri = f"models:/{MODEL_NAME}/Production"
        logger.info(f"Loading model '{MODEL_NAME}' v{_model_version} from {model_uri}")
        _model = mlflow.sklearn.load_model(model_uri)
        logger.info("Model loaded successfully.")
    except Exception as e:
        logger.error(f"Failed to load model: {e}")
        raise


def get_model():
    """Return the cached model. Raises if not yet loaded."""
    if _model is None:
        raise RuntimeError("Model not loaded. Call load_model() first.")
    return _model


def get_model_version() -> str:
    """Return the currently loaded model version string."""
    return str(_model_version)
