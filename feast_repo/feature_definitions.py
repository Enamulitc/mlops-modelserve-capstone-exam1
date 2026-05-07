# ─────────────────────────────────────────────
# Feast feature definitions — Credit Card Fraud Detection
#
# This file tells Feast how to interpret the offline feature artifact produced
# by `training/train.py` (features.parquet) and how to expose the features via
# an online store (Redis) for low-latency retrieval during inference.
# In production you would typically replace the FileSource with an S3Source
# pointing to your S3 bucket where materialized features are stored.
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
# FileSource is convenient for local development. For cloud deployments swap
# to S3Source (or a data lake) so Feast can materialize from a shared storage.
proddetection_source = FileSource(
    path="../training/features.parquet",   # relative to feast_repo/
    timestamp_field="event_timestamp",
)

# Feature view — all numerical features used by the model
# TTL controls how long the online store should consider feature values fresh.
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
