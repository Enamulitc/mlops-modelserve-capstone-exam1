"""app package initializer for the model serving project.

Keep this file minimal so importing `app.<module>` works in tests and
during lightweight runs. Heavy imports (Feast/MLflow) should remain in
their modules to avoid import-time side effects.
"""

__all__ = [
    "main",
    "model_loader",
    "feature_client",
    "metrics",
]
