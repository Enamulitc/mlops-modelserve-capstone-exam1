"""
test_predict.py — Unit + integration tests for the FastAPI service
------------------------------------------------------------------
Dataset: Credit Card Fraud Detection — entity key: cc_num
Run with:  pytest app/tests/test_predict.py -v
"""

import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

FRAUD_FEATURES = {
    "amt": 4.97, "city_pop": 3495, "lat": 36.07, "long": -81.17,
    "merch_lat": 36.01, "merch_long": -82.04, "hour": 0,
    "day_of_week": 4, "month": 1, "age": 51,
    "category_encoded": 6, "gender_encoded": 0, "state_encoded": 15,
    "job_encoded": 123, "trans_count": 0,
}

SAMPLE_CC_NUM = 2703186189652095


@pytest.fixture(autouse=True)
def mock_dependencies():
    mock_model = MagicMock()
    mock_model.predict.return_value = [0]
    mock_model.predict_proba.return_value = [[0.85, 0.15]]

    with (
        patch("app.model_loader.load_model"),
        patch("app.model_loader.get_model", return_value=mock_model),
        patch("app.model_loader.get_model_version", return_value="1"),
        patch(
            "app.feature_client.get_online_features",
            return_value=(FRAUD_FEATURES, True),
        ),
    ):
        yield


@pytest.fixture
def client():
    from app.main import app
    return TestClient(app)


# ── /health ───────────────────────────────────────────────────────────────────
def test_health_returns_200(client):
    assert client.get("/health").status_code == 200


def test_health_schema(client):
    data = client.get("/health").json()
    assert data["status"] == "healthy"
    assert "model_version" in data


# ── POST /predict ─────────────────────────────────────────────────────────────
def test_predict_returns_200(client):
    assert client.post("/predict", json={"cc_num": SAMPLE_CC_NUM}).status_code == 200


def test_predict_response_schema(client):
    data = client.post("/predict", json={"cc_num": SAMPLE_CC_NUM}).json()
    for field in ("prediction", "probability", "model_version", "timestamp", "cc_num"):
        assert field in data


def test_predict_prediction_is_binary(client):
    data = client.post("/predict", json={"cc_num": SAMPLE_CC_NUM}).json()
    assert data["prediction"] in (0, 1)


def test_predict_probability_in_range(client):
    data = client.post("/predict", json={"cc_num": SAMPLE_CC_NUM}).json()
    assert 0.0 <= data["probability"] <= 1.0


def test_predict_cc_num_in_response(client):
    data = client.post("/predict", json={"cc_num": SAMPLE_CC_NUM}).json()
    assert data["cc_num"] == SAMPLE_CC_NUM


def test_predict_with_raw_features(client):
    payload = {"cc_num": 9999999999999999, "features": FRAUD_FEATURES}
    assert client.post("/predict", json=payload).status_code == 200


# ── GET /predict/{cc_num}?explain=true ────────────────────────────────────────
def test_explain_returns_200(client):
    assert client.get(f"/predict/{SAMPLE_CC_NUM}?explain=true").status_code == 200


def test_explain_includes_features_used(client):
    data = client.get(f"/predict/{SAMPLE_CC_NUM}?explain=true").json()
    assert isinstance(data["features_used"], dict)
    assert len(data["features_used"]) > 0


def test_explain_includes_feast_cache_hit(client):
    data = client.get(f"/predict/{SAMPLE_CC_NUM}?explain=true").json()
    assert "feast_cache_hit" in data


# ── GET /metrics ──────────────────────────────────────────────────────────────
def test_metrics_returns_200(client):
    assert client.get("/metrics").status_code == 200


def test_metrics_contains_required_counters(client):
    client.post("/predict", json={"cc_num": SAMPLE_CC_NUM})
    text = client.get("/metrics").text
    assert "prediction_requests_total" in text
    assert "prediction_duration_seconds" in text
    assert "prediction_errors_total" in text
    assert "model_version" in text
