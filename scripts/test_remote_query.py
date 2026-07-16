"""Test remote querying of HuggingFace parquet files."""
import duckdb

conn = duckdb.connect()
conn.execute("INSTALL httpfs; LOAD httpfs;")

url = "https://huggingface.co/datasets/fddemarco/pushshift-reddit/resolve/main/data/RS_2012-01_00.parquet"

print(f"Trying remote query: {url[:60]}...")
try:
    result = conn.execute(f"SELECT id, subreddit, title FROM read_parquet('{url}') LIMIT 3").fetchall()
    print("SUCCESS - Remote query works!")
    for r in result:
        print(f"  r/{r[1]}: {r[2][:40]}...")
except Exception as e:
    print(f"FAILED: {type(e).__name__}: {e}")
