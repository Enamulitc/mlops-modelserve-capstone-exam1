"""main.py — FastAPI Inference Service
-------------------------------------
Dataset: Credit Card Fraud Detection (cc_num as entity key)

Endpoints:
  GET  /health                        -> {"status": "healthy", "model_version": "..."}
  POST /predict                       -> prediction response  (entity: cc_num)
  GET  /predict/{cc_num}?explain=true -> prediction + feature values used
  GET  /metrics                       -> Prometheus text format
"""

import time
# time: measure durations for metrics and latency tracking
import logging
# logging: runtime logs for debugging and operational visibility
from datetime import datetime, timezone
# datetime/timezone: produce ISO timestamps in responses
from typing import Optional, Dict, Any
# typing: annotate request/response shapes for readability

import numpy as np
# numpy: numeric array ops used by model input/output (kept for potential use)
import pandas as pd
# pandas: build DataFrame feature vectors expected by sklearn pipelines
from fastapi import FastAPI, HTTPException, Query
# fastapi: web framework exposing inference endpoints
from fastapi.responses import Response
# Response: serve Prometheus metrics (raw text) with correct media type
from pydantic import BaseModel, Field
# pydantic: schema validation for request/response bodies and auto-generated OpenAPI
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
# prometheus_client: export metrics in Prometheus text exposition format

from app.model_loader import load_model, get_model, get_model_version
# model_loader: functions to load and fetch the cached MLflow-trained model
from app.feature_client import get_online_features, fallback_features, FEATURE_NAMES
# feature_client: abstraction around Feast online lookups + fallback logic
from app.metrics import (
    prediction_requests_total,
    prediction_errors_total,
    prediction_duration_seconds,
    feast_lookup_duration_seconds,
    feast_cache_hits_total,
    feast_cache_misses_total,
    model_version_info,
)
# metrics: Prometheus metric instruments used to observe runtime behavior

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="ModelServe — ProdDetection (Fraud) Inference API",
    version="1.0.0",
)


# ── Startup ──────────────────────────────────────────────────────────────────
@app.on_event("startup")
async def startup_event():
    # Attempt to load the model at startup. In CI/test environments this may fail
    # and is intentionally caught so unit tests can import the module without MLflow.
    logger.info("Loading model from MLflow Registry...")
    try:
        load_model()
    except Exception as e:
        logger.warning(f"Model load skipped in test/dev: {e}")
    try:
        model_version_info.info({"version": get_model_version(), "name": "proddetection-model"})
    except Exception:
        pass
    logger.info(f"Model v{get_model_version()} ready.")


# ── Schemas ───────────────────────────────────────────────────────────────────
class PredictRequest(BaseModel):
    cc_num: int = Field(..., description="Credit card number (entity key)", example=2703186189652095)
    features: Optional[Dict[str, float]] = Field(
        None,
        description="Optional raw feature values to use as fallback when Feast misses",
        example={"amt": 4.97, "age": 51},
    )


class PredictResponse(BaseModel):
    prediction: int = Field(..., description="Predicted class (0 = legitimate, 1 = fraud)", example=0)
    probability: float = Field(..., description="Predicted probability for the positive class", example=0.1234)
    model_version: str = Field(..., description="Model version string from MLflow", example="1")
    timestamp: str = Field(..., description="UTC ISO timestamp when prediction was produced", example="2026-05-07T12:34:56Z")
    cc_num: int = Field(..., description="Entity key echoed back", example=2703186189652095)


class PredictExplainResponse(PredictResponse):
    features_used: Dict[str, Any] = Field(..., description="Feature values used for this prediction", example={"amt": 4.97, "age": 51})
    feast_cache_hit: bool = Field(..., description="Whether the features were fetched from Feast online store (True) or not (False)", example=True)


# ── Helpers ───────────────────────────────────────────────────────────────────
def _build_feature_vector(feast_features: Dict, raw_features: Optional[Dict]) -> pd.DataFrame:
    # Construct a feature vector (DataFrame) using Feast-provided features or
    # falling back to raw features supplied by the request body.
    if feast_features:
        values = {f: feast_features.get(f, 0.0) for f in FEATURE_NAMES}
    elif raw_features:
        values = {f: raw_features.get(f, 0.0) for f in FEATURE_NAMES}
    else:
        values = {f: 0.0 for f in FEATURE_NAMES}
    return pd.DataFrame([values])[FEATURE_NAMES]


# ── Routes ────────────────────────────────────────────────────────────────────
@app.get("/health", tags=["service"], summary="Health check")
def health():
    """Service health endpoint returning a simple status and the current model version."""
    return {"status": "healthy", "model_version": get_model_version()}


@app.post("/predict", response_model=PredictResponse, tags=["predictions"], summary="Get fraud prediction")
def predict(request: PredictRequest):
    start = time.time()
    try:
        # 1) Lookup features from Feast (online store)
        t0 = time.time()
        feast_features, cache_hit = get_online_features(request.cc_num)
        try:
            feast_lookup_duration_seconds.observe(time.time() - t0)
        except Exception:
            pass

        if cache_hit:
            try:
                feast_cache_hits_total.inc()
            except Exception:
                pass
        else:
            try:
                feast_cache_misses_total.inc()
            except Exception:
                pass
            if request.features:
                feast_features = fallback_features(request.features)

        # 2) Build feature vector and run the cached model
        X = _build_feature_vector(feast_features, request.features)
        model = get_model()
        pred = int(model.predict(X)[0])
        prob = float(model.predict_proba(X)[0][1])

        try:
            prediction_requests_total.labels(status="success").inc()
            prediction_duration_seconds.observe(time.time() - start)
        except Exception:
            pass

        return PredictResponse(
            prediction=pred,
            probability=round(prob, 4),
            model_version=get_model_version(),
            timestamp=datetime.now(timezone.utc).isoformat(),
            cc_num=request.cc_num,
        )

    except Exception as e:
        try:
            prediction_errors_total.labels(error_type=type(e).__name__).inc()
            prediction_requests_total.labels(status="error").inc()
        except Exception:
            pass
        logger.error(f"Prediction error: {e}")
        raise HTTPException(
            status_code=500,
            detail={"error": type(e).__name__, "message": str(e)},
        )


@app.get("/predict/{cc_num}", response_model=PredictExplainResponse, tags=["predictions"], summary="Get prediction with optional explanation")
def predict_explain(cc_num: int, explain: bool = Query(default=False, description="Set to true to include features used in the response")):
    start = time.time()
    try:
        t0 = time.time()
        feast_features, cache_hit = get_online_features(cc_num)
        try:
            feast_lookup_duration_seconds.observe(time.time() - t0)
        except Exception:
            pass

        if cache_hit:
            try:
                feast_cache_hits_total.inc()
            except Exception:
                pass
        else:
            try:
                feast_cache_misses_total.inc()
            except Exception:
                pass

        # Build feature vector (no request body in this route) and predict
        X = _build_feature_vector(feast_features, None)
        model = get_model()
        pred = int(model.predict(X)[0])
        prob = float(model.predict_proba(X)[0][1])

        try:
            prediction_requests_total.labels(status="success").inc()
            prediction_duration_seconds.observe(time.time() - start)
        except Exception:
            pass

        return PredictExplainResponse(
            prediction=pred,
            probability=round(prob, 4),
            model_version=get_model_version(),
            timestamp=datetime.now(timezone.utc).isoformat(),
            cc_num=cc_num,
            features_used=feast_features if explain else {},
            feast_cache_hit=cache_hit,
        )

    except Exception as e:
        try:
            prediction_errors_total.labels(error_type=type(e).__name__).inc()
            prediction_requests_total.labels(status="error").inc()
        except Exception:
            pass
        logger.error(f"Explain prediction error: {e}")
        raise HTTPException(
            status_code=500,
            detail={"error": type(e).__name__, "message": str(e)},
        )


@app.get("/metrics", tags=["metrics"], summary="Prometheus metrics endpoint")
def metrics():
    try:
        return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
    except Exception:
        return Response("", media_type=CONTENT_TYPE_LATEST)
