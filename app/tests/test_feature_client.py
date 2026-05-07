import types
from unittest.mock import MagicMock

import pytest

from app import feature_client


def make_response_dict(values):
    # Feast returns a dict with keys like "proddetection_features__amt": [value]
    return {f"{feature_client.FEATURE_VIEW_NAME}__{k}": [v] for k, v in values.items()}


def test_get_online_features_success(monkeypatch):
    # Prepare a fake store whose get_online_features returns an object with to_dict()
    fake_store = MagicMock()
    sample = {f: 1.23 for f in feature_client.FEATURE_NAMES}
    fake_store.get_online_features.return_value.to_dict.return_value = make_response_dict(sample)

    monkeypatch.setattr(feature_client, "_store", fake_store)

    values, cache_hit = feature_client.get_online_features(1234)
    assert cache_hit is True
    assert set(values.keys()) == set(feature_client.FEATURE_NAMES)
    # Values should be returned as-is (first element)
    assert values[feature_client.FEATURE_NAMES[0]] == 1.23


def test_get_online_features_failure(monkeypatch, caplog):
    # Simulate the store raising an exception (Redis/Feast unavailable)
    fake_store = MagicMock()
    fake_store.get_online_features.side_effect = RuntimeError("redis down")
    monkeypatch.setattr(feature_client, "_store", fake_store)

    values, cache_hit = feature_client.get_online_features(9999)
    assert values == {}
    assert cache_hit is False
    assert any("Feast lookup failed" in rec.message for rec in caplog.records)


def test_fallback_features_filters_and_casts():
    raw = {"amt": "10", "city_pop": 100, "unknown": 5}
    out = feature_client.fallback_features(raw)
    assert "unknown" not in out
    assert isinstance(out["amt"], float)
