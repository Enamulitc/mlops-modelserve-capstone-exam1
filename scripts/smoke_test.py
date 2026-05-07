#!/usr/bin/env python3
"""
Simple end-to-end smoke test for the ModelServe API.
Calls /health, /predict (POST) and /predict/{cc_num}?explain=true, and /metrics.
Prints a compact pass/fail report.

Usage:
  python3 scripts/smoke_test.py --url http://localhost:8000
"""
import argparse
import json
import sys
from typing import Tuple

import requests


def check_health(base_url: str) -> Tuple[bool, str]:
    try:
        r = requests.get(f"{base_url}/health", timeout=5)
        if r.status_code == 200:
            return True, r.text
        return False, f"status={r.status_code}"
    except Exception as e:
        return False, str(e)


def check_predict(base_url: str, payload: dict) -> Tuple[bool, str]:
    try:
        r = requests.post(f"{base_url}/predict", json=payload, timeout=10)
        if r.status_code != 200:
            return False, f"status={r.status_code} body={r.text}"
        j = r.json()
        required = ("prediction", "probability", "model_version", "timestamp", "cc_num")
        missing = [k for k in required if k not in j]
        if missing:
            return False, f"missing fields: {missing}"
        return True, json.dumps(j)
    except Exception as e:
        return False, str(e)


def check_explain(base_url: str, cc_num: int) -> Tuple[bool, str]:
    try:
        r = requests.get(f"{base_url}/predict/{cc_num}?explain=true", timeout=10)
        if r.status_code != 200:
            return False, f"status={r.status_code} body={r.text}"
        j = r.json()
        if "features_used" not in j:
            return False, "missing features_used"
        return True, json.dumps(j)
    except Exception as e:
        return False, str(e)


def check_metrics(base_url: str) -> Tuple[bool, str]:
    try:
        r = requests.get(f"{base_url}/metrics", timeout=5)
        if r.status_code == 200 and "prediction_requests_total" in r.text:
            return True, "metrics_ok"
        return False, f"status={r.status_code}"
    except Exception as e:
        return False, str(e)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://localhost:8000", help="Base URL for the API")
    parser.add_argument("--sample", default="training/sample_request.json", help="Sample request JSON")
    args = parser.parse_args()

    try:
        with open(args.sample) as f:
            payload = json.load(f)
    except Exception:
        # minimal payload fallback
        payload = {"cc_num": 12345}

    checks = [
        ("health", lambda: check_health(args.url)),
        ("predict", lambda: check_predict(args.url, payload)),
        ("explain", lambda: check_explain(args.url, payload.get("cc_num", 12345))),
        ("metrics", lambda: check_metrics(args.url)),
    ]

    overall = True
    results = []
    for name, fn in checks:
        ok, info = fn()
        results.append((name, ok, info))
        overall = overall and ok

    print("Smoke test results:")
    for name, ok, info in results:
        print(f" - {name:7} : {'PASS' if ok else 'FAIL'} : {info}")

    if overall:
        print("ALL CHECKS PASS")
        sys.exit(0)
    else:
        print("SOME CHECKS FAILED")
        sys.exit(2)
