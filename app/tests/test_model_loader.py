import importlib
import pytest
from unittest.mock import MagicMock


def test_load_model_no_versions(monkeypatch):
    # Simulate MlflowClient returning no Production versions
    class FakeClient:
        def __init__(self, uri):
            pass

        def get_latest_versions(self, name, stages=None):
            return []

    # Patch mlflow.tracking.MlflowClient so when app.model_loader imports it,
    # it will use our FakeClient and avoid network calls.
    monkeypatch.setattr("mlflow.tracking.MlflowClient", FakeClient, raising=False)
    # Ensure mlflow.sklearn.load_model exists (shouldn't be called in this test)
    monkeypatch.setattr("mlflow.sklearn.load_model", lambda uri: None, raising=False)

    # Reload module to reset state and pick up patched MlflowClient
    importlib.reload(__import__("app.model_loader", fromlist=["*"]))
    from app import model_loader

    with pytest.raises(RuntimeError):
        model_loader.load_model()


def test_load_model_success(monkeypatch):
    # Provide a fake version list and a fake mlflow.sklearn.load_model
    class FakeVersion:
        def __init__(self, version):
            self.version = version

    class FakeClient:
        def __init__(self, uri):
            pass

        def get_latest_versions(self, name, stages=None):
            return [FakeVersion("42")]

    monkeypatch.setattr("mlflow.tracking.MlflowClient", FakeClient, raising=False)
    monkeypatch.setattr("mlflow.sklearn.load_model", lambda uri: "FAKE_MODEL", raising=False)

    importlib.reload(__import__("app.model_loader", fromlist=["*"]))
    from app import model_loader

    model_loader.load_model()
    assert model_loader.get_model_version() == "42"
    assert model_loader.get_model() == "FAKE_MODEL"
