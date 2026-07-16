"""Extended remote-query test for Pushshift via DuckDB httpfs.

Hits the HuggingFace parquet endpoint directly (no local download).
"""
import duckdb
import sys
import time


def main():
    print("duckdb version:", duckdb.__version__)
    sys.stdout.flush()

    conn = duckdb.connect()
    print("LOAD httpfs...")
    sys.stdout.flush()
    t0 = time.time()
    try:
        conn.execute("LOAD httpfs;")
        print(f"  loaded in {time.time()-t0:.2f}s")
    except Exception as e:
        print(f"  LOAD failed ({e}); running INSTALL...")
        sys.stdout.flush()
        conn.execute("INSTALL httpfs;")
        conn.execute("LOAD httpfs;")
    sys.stdout.flush()

    url = (
        "https://huggingface.co/datasets/fddemarco/pushshift-reddit"
        "/resolve/main/data/RS_2012-01_00.parquet"
    )
    print(f"Endpoint: {url}")
    sys.stdout.flush()

    # 1. COUNT(*) over remote parquet — DuckDB uses row-group metadata,
    # no full data scan.
    print("\n[1] COUNT(*) over remote parquet...")
    sys.stdout.flush()
    t0 = time.time()
    n = conn.execute(f"SELECT COUNT(*) FROM read_parquet('{url}')").fetchone()[0]
    print(f"  total rows: {n:,}  in {time.time()-t0:.2f}s")
    sys.stdout.flush()

    # 2. Schema via DESCRIBE
    print("\n[2] Schema (DESCRIBE)...")
    sys.stdout.flush()
    t0 = time.time()
    schema = conn.execute(
        f"DESCRIBE SELECT * FROM read_parquet('{url}')"
    ).fetchall()
    print(f"  {len(schema)} cols in {time.time()-t0:.2f}s")
    for col in schema:
        print(f"    {col[0]}: {col[1]}")
    sys.stdout.flush()

    # 3. Simple LIMIT (uses byte-range reads)
    print("\n[3] SELECT ... LIMIT 3 ...")
    sys.stdout.flush()
    t0 = time.time()
    r = conn.execute(
        f"SELECT subreddit, title, score FROM read_parquet('{url}') LIMIT 3"
    ).fetchall()
    print(f"  3 rows in {time.time()-t0:.2f}s")
    for row in r:
        print(f"    [{row[2]}] r/{row[0]}: {row[1][:60]}")
    sys.stdout.flush()


if __name__ == "__main__":
    main()
