import pytest
from unittest.mock import patch, MagicMock
import pytest
from unittest.mock import patch, MagicMock


@pytest.fixture(autouse=True)
def global_model_mocks():
    """Provide default mocks for model loading functions across tests.

    NOTE: This fixture intentionally does NOT mock `app.feature_client.get_online_features`.
    Tests that need to control feature lookups should patch that symbol explicitly. Keeping
    the feature-client unmocked here prevents the global fixture from masking tests which
    need to exercise Feast failure/success branches or which provide their own per-test
    feature-client patches.
    """
    mock_model = MagicMock()
    mock_model.predict.return_value = [0]
    mock_model.predict_proba.return_value = [[0.85, 0.15]]

    with (
        patch("app.main.get_model", return_value=mock_model),
        patch("app.main.get_model_version", return_value="1"),
        patch("app.model_loader.get_model", return_value=mock_model),
        patch("app.model_loader.get_model_version", return_value="1"),
    ):
        # Provide a lightweight fake Feast store so tests don't attempt to open the
        # repository registry.db on import. Tests that need other behaviors can
        # monkeypatch `app.feature_client.get_online_features` or replace
        # `app.feature_client._store` as needed.
        try:
            import app.feature_client as fc

            class _FakeResponse:
                def __init__(self, mapping):
                    self._mapping = mapping

                def to_dict(self):
                    return self._mapping

            class FakeStore:
                def get_online_features(self, features, entity_rows=None):
                    # Return a mapping that mirrors Feast's to_dict() shape but with None values
                    repo_prefix = fc.FEATURE_VIEW_NAME + "__"
                    mapping = {f"{repo_prefix}{f}": [None] for f in fc.FEATURE_NAMES}
                    return _FakeResponse(mapping)

            # assign fake store (restored after yield)
            old_store = getattr(fc, "_store", None)
            fc._store = FakeStore()
        except Exception:
            old_store = None

        try:
            yield
        finally:
            # restore original store if any
            try:
                if 'fc' in locals():
                    fc._store = old_store
            except Exception:
                pass
