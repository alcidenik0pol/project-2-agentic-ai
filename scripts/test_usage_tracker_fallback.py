"""Test usage_tracker path resolution (normal + read-only fallback)."""

import tempfile
from pathlib import Path
from unittest.mock import patch

from app.services.usage_tracker import UsageTracker


def main():
    # Test 1: Normal dev case (writable data/usage)
    t = UsageTracker(bucket_name=None)
    print("TEST 1 (normal dev): local_path =", t._local_path)
    assert t._local_path == Path("data/usage"), f"Expected data/usage, got {t._local_path}"
    print("TEST 1 PASS")

    # Test 2: explicit local_path still works (mkdir honored)
    with tempfile.TemporaryDirectory() as td:
        explicit = Path(td) / "explicit_usage"
        t2 = UsageTracker(bucket_name=None, local_path=explicit)
        print("TEST 2 (explicit): local_path =", t2._local_path)
        assert t2._local_path == explicit
        assert explicit.exists()
    print("TEST 2 PASS")

    # Test 3: fallback to /tmp when primary not writable.
    # Monkeypatch Path.mkdir to raise PermissionError for the data/usage path,
    # simulating a read-only GCS mount, while allowing /tmp/usage to be created.
    original_mkdir = Path.mkdir

    def raising_mkdir(self, *a, **k):
        normalized = str(self).replace("\\", "/")
        if normalized.endswith("data/usage"):
            raise PermissionError("simulated read-only mount")
        return original_mkdir(self, *a, **k)

    with patch.object(Path, "mkdir", raising_mkdir):
        t3 = UsageTracker(bucket_name=None)
        print("TEST 3 (fallback): local_path =", t3._local_path)
        assert t3._local_path == Path("/tmp/usage"), f"Expected /tmp/usage, got {t3._local_path}"
    print("TEST 3 PASS")

    print()
    print("ALL USAGE TRACKER TESTS PASSED")


if __name__ == "__main__":
    main()
