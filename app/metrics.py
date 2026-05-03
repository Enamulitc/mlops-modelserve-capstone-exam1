"""
metrics.py — Prometheus metric definitions
------------------------------------------
All Counter, Histogram, and Gauge objects are defined here once
and imported by main.py to avoid duplication.
"""

from prometheus_client import Counter, Histogram, Gauge, Info

# ── Counters ────────────────────────────────────────────────────────────────
prediction_requests_total = Counter(
    "prediction_requests_total",
    "Total number of prediction requests received",
    ["status"],           # label: success | error
)

prediction_errors_total = Counter(
    "prediction_errors_total",
    "Total number of failed prediction requests",
    ["error_type"],       # label: feast_error | model_error | validation_error
)

feast_cache_hits_total = Counter(
    "feast_cache_hits_total",
    "Total Feast online store feature lookups that returned data",
)

feast_cache_misses_total = Counter(
    "feast_cache_misses_total",
    "Total Feast online store feature lookups that returned no data (fallback used)",
)

# ── Histograms ───────────────────────────────────────────────────────────────
prediction_duration_seconds = Histogram(
    "prediction_duration_seconds",
    "End-to-end prediction request latency in seconds",
    buckets=[0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0],
)

feast_lookup_duration_seconds = Histogram(
    "feast_lookup_duration_seconds",
    "Time taken for Feast online feature lookup",
    buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.5],
)

# ── Gauges / Info ─────────────────────────────────────────────────────────────
model_version_info = Info(
    "model_version",
    "Currently loaded MLflow model version",
)
