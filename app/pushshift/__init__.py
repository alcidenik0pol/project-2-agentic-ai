# ═══════════════════════════════════════════════════════════════════════════
# WORKFLOW: PUSHSHIFT (HuggingFace + DuckDB)
# Historical Reddit data via local Parquet query.
# Used when: get_data_source() == "pushshift"
# (Renamed from "arcticshift" — the upstream dataset is fddemarco/pushshift-reddit,
# not the separate RoyalFortune24/The-Arctic-Shift dataset.)
# ═══════════════════════════════════════════════════════════════════════════
"""Pushshift module for querying historical Reddit data.

Reads pre-staged Parquet from a mounted GCS volume and queries with DuckDB.
This provides access to historical Reddit data without rate limits.
"""

from app.pushshift.client import PushshiftClient

__all__ = ["PushshiftClient"]
