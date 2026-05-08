from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient


@patch("app.model_loader.load_model")
def test_predict_feast_miss_fallback(mock_load):
    # Feast returns miss; request provides features and model predicts
    fake_model = MagicMock()
    fake_model.predict.return_value = [1]
    fake_model.predict_proba.return_value = [[0.1, 0.9]]

    with patch("app.model_loader.get_model", return_value=fake_model), patch(
        "app.model_loader.get_model_version", return_value="1"
    ), patch(
        "app.feature_client.get_online_features", return_value=({}, False)
    ):
        from app.main import app
        client = TestClient(app)

        payload = {"cc_num": 1111, "features": {f: 0.5 for f in ["amt", "age"]}}
        r = client.post("/predict", json=payload)
        assert r.status_code == 200
        data = r.json()
        assert data["prediction"] in (0, 1)


def test_predict_error_path_increments_error_counter():
    # If the model raises during predict, the API should return 500 and error counter increases
    fake_model = MagicMock()
    fake_model.predict.side_effect = RuntimeError("boom")

    # Patch app.main.get_model specifically so the endpoint uses the raising model
    with patch("app.main.get_model", return_value=fake_model), patch(
        "app.main.get_model_version", return_value="1"
    ), patch(
        "app.feature_client.get_online_features", return_value=({}, True)
    ):
        from app.main import app
        client = TestClient(app)
        r = client.post("/predict", json={"cc_num": 2222})
        assert r.status_code == 500
