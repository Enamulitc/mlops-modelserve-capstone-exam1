"""
create_dummy_features.py
------------------------
Create a minimal features.parquet using the example payload in
training/sample_request.json. This lets Feast materialize and the
API to be exercised without downloading the full Kaggle dataset.

Usage:
  python scripts/create_dummy_features.py
"""
import json
import os
from datetime import datetime, timezone

import pandas as pd

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SAMPLE_PATH = os.path.join(REPO_ROOT, "training", "sample_request.json")
OUT_PATH = os.path.join(REPO_ROOT, "training", "features.parquet")


def main():
    if not os.path.exists(SAMPLE_PATH):
        raise SystemExit(f"Missing {SAMPLE_PATH}. Ensure sample_request.json exists.")

    with open(SAMPLE_PATH, "r") as f:
        payload = json.load(f)

    cc_num = payload.get("cc_num")
    features = payload.get("features", {})

    # Add required columns for Feast and event_timestamp
    row = {k: float(v) for k, v in features.items()}
    row["cc_num"] = int(cc_num)
    row["event_timestamp"] = datetime.now(tz=timezone.utc)

    df = pd.DataFrame([row])
    df.to_parquet(OUT_PATH, index=False)

    print(f"Wrote 1-row features parquet -> {OUT_PATH}")


if __name__ == "__main__":
    main()
