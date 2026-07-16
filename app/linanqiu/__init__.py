# ═══════════════════════════════════════════════════════════════════════════
# WORKFLOW: LINANQIU (local static JSON)
# Historical Reddit data via pre-converted JSON on disk.
# Used when: get_data_source() == "linanqiu"
# ═══════════════════════════════════════════════════════════════════════════
"""linanqiu/reddit-dataset loader (static JSON-backed).

Loads the pre-converted dataset (data/linanqiu/linanqiu_dataset.json) and
filters in-memory. No network, no DuckDB, no new dependencies.
"""

from app.linanqiu.linanqiu_client import LinanqiuClient

__all__ = ["LinanqiuClient"]
