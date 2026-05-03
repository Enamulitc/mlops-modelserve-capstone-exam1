# ─────────────────────────────────────────────
# Feast feature definitions — Credit Card Fraud Detection
# ─────────────────────────────────────────────
from datetime import timedelta

from feast import Entity, FeatureView, Field, FileSource
from feast.types import Float32, Int64

# Entity — credit card number (join key used in /predict requests)
entity = Entity(
    name="cc_num",
    description="Credit card number — unique identifier per cardholder",
)

# Offline source — Parquet file produced by training/train.py
# In production swap for S3Source pointing to your S3 bucket
proddetection_source = FileSource(
    path="../training/features.parquet",   # relative to feast_repo/
    timestamp_field="event_timestamp",
)

# Feature view — all numerical features used by the model
proddetection_fv = FeatureView(
    name="proddetection_features",
    entities=[entity],
    ttl=timedelta(days=7),
    schema=[
        Field(name="amt",               dtype=Float32),
        Field(name="city_pop",          dtype=Int64),
        Field(name="lat",               dtype=Float32),
        Field(name="long",              dtype=Float32),
        Field(name="merch_lat",         dtype=Float32),
        Field(name="merch_long",        dtype=Float32),
        Field(name="hour",              dtype=Int64),
        Field(name="day_of_week",       dtype=Int64),
        Field(name="month",             dtype=Int64),
        Field(name="age",               dtype=Int64),
        Field(name="category_encoded",  dtype=Int64),
        Field(name="gender_encoded",    dtype=Int64),
        Field(name="state_encoded",     dtype=Int64),
        Field(name="job_encoded",       dtype=Int64),
        Field(name="trans_count",       dtype=Int64),
    ],
    source=proddetection_source,
    online=True,
)
