"""feature_client.py — Feast online feature lookup wrapper
--------------------------------------------------------
Entity key: cc_num (credit card number)
"""

import os
# os: read environment variables and build paths
import logging
# logging: warn when Feast/Redis lookups fail
from typing import Dict, Any, Tuple
# typing: annotate function return shapes for clarity

# NOTE: we intentionally import Feast inside get_store() to avoid making Feast
# a hard dependency at import time. This keeps unit tests fast and avoids
# initialization errors when Feast or Redis aren't available during tests.

logger = logging.getLogger(__name__)

FEAST_REPO_PATH = os.getenv(
    "FEAST_REPO_PATH",
    os.path.join(os.path.dirname(__file__), "..", "feast_repo"),
)
# FEAST_REPO_PATH: where the feast_repo (feature definitions + offline store) lives

FEATURE_VIEW_NAME = "proddetection_features"
# FEATURE_VIEW_NAME: name declared in feast_repo.feature_definitions
FEATURE_NAMES = [
    "amt", "city_pop", "lat", "long", "merch_lat", "merch_long",
    "hour", "day_of_week", "month", "age",
    "category_encoded", "gender_encoded", "state_encoded",
    "job_encoded", "trans_count",
]
# FEATURE_NAMES: canonical list of features the model expects (keeps API stable)

# Module-level store instance (initialized lazily) so we reuse the Feast client
# across requests and avoid repeated startup cost
_store = None


def get_store():
    global _store
    if _store is None:
        # Lazy-load Feast to avoid making Feast a hard dependency for unit tests
        # and to speed up container startup when feature materialization is done separately.
        logger.info(f"Initialising Feast FeatureStore at {FEAST_REPO_PATH}")
        try:
            # Import inside function so tests or lightweight deployments that
            # don't need Feast won't fail at module import time.
            from feast import FeatureStore
        except Exception as e:
            # Raise a clear error if Feast isn't available at runtime
            raise RuntimeError("Feast is not installed. Install feast[redis] or run feature materialization in a container.") from e
        _store = FeatureStore(repo_path=FEAST_REPO_PATH)
    return _store


def get_online_features(cc_num: int) -> Tuple[Dict[str, Any], bool]:
    """
    Fetch online features for a credit card number from Feast Redis store.
    Returns (features_dict, cache_hit).
    """
    store = get_store()
    feature_refs = [f"{FEATURE_VIEW_NAME}:{f}" for f in FEATURE_NAMES]

    try:
        response = store.get_online_features(
            features=feature_refs,
            entity_rows=[{"cc_num": cc_num}],
        ).to_dict()

        values = {
            feat: response.get(f"{FEATURE_VIEW_NAME}__{feat}", [None])[0]
            for feat in FEATURE_NAMES
        }
        cache_hit = all(v is not None for v in values.values())
        return values, cache_hit

    except Exception as e:
        # If feature lookup fails (Feast not available, Redis down, etc.) return
        # a cache-miss signal so the API can use the request-supplied fallback features.
        # This keeps the prediction API resilient during maintenance or local dev.
        logger.warning(f"Feast lookup failed for cc_num={cc_num}: {e}")
        return {}, False


def fallback_features(raw_features: Dict[str, Any]) -> Dict[str, Any]:
    """Fall back to raw features from the request body when Feast misses."""
    return {k: float(v) for k, v in raw_features.items() if k in FEATURE_NAMES}
