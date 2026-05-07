import builtins
import importlib
from unittest.mock import patch, MagicMock

import pytest


def test_metric_exceptions_are_handled(monkeypatch):
    # Patch Feast lookup to return valid features so code proceeds to metrics
    from app.tests.test_predict import FRAUD_FEATURES, SAMPLE_CC_NUM

    monkeypatch.setattr("app.feature_client.get_online_features", lambda cc: (FRAUD_FEATURES, True))

    # Make metric observe/inc functions raise so we exercise the except branches
    import app.main as main_mod

    # Prevent the startup load_model from trying to contact MLflow during TestClient creation
    main_mod.load_model = lambda: None

    main_mod.feast_lookup_duration_seconds.observe = lambda x: (_ for _ in ()).throw(RuntimeError("metric fail"))
    main_mod.feast_cache_hits_total.inc = lambda: (_ for _ in ()).throw(RuntimeError("metric fail"))
    main_mod.prediction_requests_total.labels = lambda **kw: MagicMock(inc=lambda: (_ for _ in ()).throw(RuntimeError("metric fail")))
    main_mod.prediction_duration_seconds.observe = lambda x: (_ for _ in ()).throw(RuntimeError("metric fail"))

    client = MagicMock()
    from fastapi.testclient import TestClient
    client = TestClient(main_mod.app)

    r = client.post("/predict", json={"cc_num": SAMPLE_CC_NUM})
    assert r.status_code == 200


def test_get_store_import_failure(monkeypatch):
    # Simulate ImportError when importing 'feast' to hit the RuntimeError path
    import app.feature_client as fc

    orig_import = builtins.__import__

    def fake_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "feast" or (fromlist and "feast" in name):
            raise ImportError("no feast")
        return orig_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    # Ensure module-level store is reset
    monkeypatch.setattr(fc, "_store", None)

    with pytest.raises(RuntimeError):
        fc.get_store()
