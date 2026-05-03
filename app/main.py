"""
main.py — FastAPI Inference Service
-------------------------------------
Dataset: Credit Card Fraud Detection (cc_num as entity key)

Endpoints:
  GET  /health                        → {"status": "healthy", "model_version": "..."}
  POST /predict                       → prediction response  (entity: cc_num)
  GET  /predict/{cc_num}?explain=true → prediction + feature values used
  GET  /metrics                       → Prometheus text format
"""

import time
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any

import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import Response
from pydantic import BaseModel
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

from app.model_loader import load_model, get_model, get_model_version
from app.feature_client import (
    get_online_features, fallback_features, FEATURE_NAMES
)
from app.metrics import (
    prediction_requests_total,
    prediction_errors_total,
    prediction_duration_seconds,
    feast_lookup_duration_seconds,
    feast_cache_hits_total,
    feast_cache_misses_total,
    model_version_info,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="ModelServe — ProdDetection (Fraud) Inference API",
    version="1.0.0",
)


# ── Startup ──────────────────────────────────────────────────────────────────
@app.on_event("startup")
async def startup_event():
    logger.info("Loading model from MLflow Registry…")
    load_model()
    model_version_info.info({"version": get_model_version(), "name": "proddetection-model"})
    logger.info(f"Model v{get_model_version()} ready.")


# ── Schemas ───────────────────────────────────────────────────────────────────
class PredictRequest(BaseModel):
    cc_num: int
    features: Optional[Dict[str, float]] = None   # fallback raw features


class PredictResponse(BaseModel):
    prediction: int
    probability: float
    model_version: str
    timestamp: str
    cc_num: int


class PredictExplainResponse(PredictResponse):
    features_used: Dict[str, Any]
    feast_cache_hit: bool


# ── Helpers ───────────────────────────────────────────────────────────────────
def _build_feature_vector(feast_features: Dict, raw_features: Optional[Dict]) -> pd.DataFrame:
    if feast_features:
        values = {f: feast_features.get(f, 0.0) for f in FEATURE_NAMES}
    elif raw_features:
        values = {f: raw_features.get(f, 0.0) for f in FEATURE_NAMES}
    else:
        values = {f: 0.0 for f in FEATURE_NAMES}
    return pd.DataFrame([values])[FEATURE_NAMES]


# ── Routes ────────────────────────────────────────────────────────────────────
@app.get("/health")
def health():
    return {"status": "healthy", "model_version": get_model_version()}


@app.post("/predict", response_model=PredictResponse)
def predict(request: PredictRequest):
    start = time.time()
    try:
        t0 = time.time()
        feast_features, cache_hit = get_online_features(request.cc_num)
        feast_lookup_duration_seconds.observe(time.time() - t0)

        if cache_hit:
            feast_cache_hits_total.inc()
        else:
            feast_cache_misses_total.inc()
            if request.features:
                feast_features = fallback_features(request.features)

        X = _build_feature_vector(feast_features, request.features)
        model = get_model()
        pred = int(model.predict(X)[0])
        prob = float(model.predict_proba(X)[0][1])

        prediction_requests_total.labels(status="success").inc()
        prediction_duration_seconds.observe(time.time() - start)

        return PredictResponse(
            prediction=pred,
            probability=round(prob, 4),
            model_version=get_model_version(),
            timestamp=datetime.now(timezone.utc).isoformat(),
            cc_num=request.cc_num,
        )

    except Exception as e:
        prediction_errors_total.labels(error_type=type(e).__name__).inc()
        prediction_requests_total.labels(status="error").inc()
        logger.error(f"Prediction error: {e}")
        raise HTTPException(
            status_code=500,
            detail={"error": type(e).__name__, "message": str(e)},
        )


@app.get("/predict/{cc_num}", response_model=PredictExplainResponse)
def predict_explain(cc_num: int, explain: bool = Query(default=False)):
    start = time.time()
    try:
        t0 = time.time()
        feast_features, cache_hit = get_online_features(cc_num)
        feast_lookup_duration_seconds.observe(time.time() - t0)

        if cache_hit:
            feast_cache_hits_total.inc()
        else:
            feast_cache_misses_total.inc()

        X = _build_feature_vector(feast_features, None)
        model = get_model()
        pred = int(model.predict(X)[0])
        prob = float(model.predict_proba(X)[0][1])

        prediction_requests_total.labels(status="success").inc()
        prediction_duration_seconds.observe(time.time() - start)

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
        prediction_errors_total.labels(error_type=type(e).__name__).inc()
        prediction_requests_total.labels(status="error").inc()
        logger.error(f"Explain prediction error: {e}")
        raise HTTPException(
            status_code=500,
            detail={"error": type(e).__name__, "message": str(e)},
        )


@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

import time
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any

import numpy as np
import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import Response
from pydantic import BaseModel
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

from app.model_loader import load_model, get_model, get_model_version
from app.feature_client import (
    get_online_features, fallback_features, FEATURE_NAMES
)
from app.metrics import (
    prediction_requests_total,
    prediction_errors_total,
    prediction_duration_seconds,
    feast_lookup_duration_seconds,
    feast_cache_hits_total,
    feast_cache_misses_total,
    model_version_info,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="ModelServe — ProdDetection Inference API",
    description="Production ML inference service for the proddetection model.",
    version="1.0.0",
)


# ─────────────────────────────────────────────
# Startup
# ─────────────────────────────────────────────
@app.on_event("startup")
async def startup_event():
    logger.info("Loading model from MLflow Registry…")
    load_model()
    model_version_info.info({"version": get_model_version(), "name": "proddetection-model"})
    logger.info(f"Model v{get_model_version()} ready.")


# ─────────────────────────────────────────────
# Schemas
# ─────────────────────────────────────────────
class PredictRequest(BaseModel):
    entity_id: int
    features: Optional[Dict[str, float]] = None   # fallback raw features


class PredictResponse(BaseModel):
    prediction: int
    probability: float
    model_version: str
    timestamp: str
    entity_id: int


class PredictExplainResponse(PredictResponse):
    features_used: Dict[str, Any]
    feast_cache_hit: bool


# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────
def _build_feature_vector(feast_features: Dict, raw_features: Optional[Dict]) -> pd.DataFrame:
    """Build a 1-row DataFrame in the order the model expects."""
    if feast_features:
        values = {f: feast_features.get(f, 0.0) for f in FEATURE_NAMES}
    elif raw_features:
        values = {f: raw_features.get(f, 0.0) for f in FEATURE_NAMES}
    else:
        values = {f: 0.0 for f in FEATURE_NAMES}
    return pd.DataFrame([values])[FEATURE_NAMES]


# ─────────────────────────────────────────────
# Routes
# ─────────────────────────────────────────────
@app.get("/health")
def health():
    return {"status": "healthy", "model_version": get_model_version()}


@app.post("/predict", response_model=PredictResponse)
def predict(request: PredictRequest):
    start = time.time()
    try:
        # Feature lookup
        t0 = time.time()
        feast_features, cache_hit = get_online_features(request.entity_id)
        feast_lookup_duration_seconds.observe(time.time() - t0)

        if cache_hit:
            feast_cache_hits_total.inc()
        else:
            feast_cache_misses_total.inc()
            if request.features:
                feast_features = fallback_features(request.features)

        # Build feature vector
        X = _build_feature_vector(feast_features, request.features)

        # Predict
        model = get_model()
        pred = int(model.predict(X)[0])
        prob = float(model.predict_proba(X)[0][1])

        prediction_requests_total.labels(status="success").inc()
        prediction_duration_seconds.observe(time.time() - start)

        return PredictResponse(
            prediction=pred,
            probability=round(prob, 4),
            model_version=get_model_version(),
            timestamp=datetime.now(timezone.utc).isoformat(),
            entity_id=request.entity_id,
        )

    except Exception as e:
        prediction_errors_total.labels(error_type=type(e).__name__).inc()
        prediction_requests_total.labels(status="error").inc()
        logger.error(f"Prediction error: {e}")
        raise HTTPException(
            status_code=500,
            detail={"error": type(e).__name__, "message": str(e)},
        )


@app.get("/predict/{entity_id}", response_model=PredictExplainResponse)
def predict_explain(
    entity_id: int,
    explain: bool = Query(default=False),
):
    start = time.time()
    try:
        t0 = time.time()
        feast_features, cache_hit = get_online_features(entity_id)
        feast_lookup_duration_seconds.observe(time.time() - t0)

        if cache_hit:
            feast_cache_hits_total.inc()
        else:
            feast_cache_misses_total.inc()

        X = _build_feature_vector(feast_features, None)
        model = get_model()
        pred = int(model.predict(X)[0])
        prob = float(model.predict_proba(X)[0][1])

        prediction_requests_total.labels(status="success").inc()
        prediction_duration_seconds.observe(time.time() - start)

        return PredictExplainResponse(
            prediction=pred,
            probability=round(prob, 4),
            model_version=get_model_version(),
            timestamp=datetime.now(timezone.utc).isoformat(),
            entity_id=entity_id,
            features_used=feast_features if explain else {},
            feast_cache_hit=cache_hit,
        )

    except Exception as e:
        prediction_errors_total.labels(error_type=type(e).__name__).inc()
        prediction_requests_total.labels(status="error").inc()
        logger.error(f"Explain prediction error: {e}")
        raise HTTPException(
            status_code=500,
            detail={"error": type(e).__name__, "message": str(e)},
        )


@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
