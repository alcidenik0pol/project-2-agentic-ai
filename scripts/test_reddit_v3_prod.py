"""Quick test: POST a small reddit_v3 analysis to the prod backend
and poll the results to see if the RSS scraper works from Cloud Run.

Mirrors scripts/test_reddit_v2_prod.py but with data_source=reddit_v3.

Note: AnalysisRequest only accepts `query` and `data_source`. Any other
keys in the payload (e.g. max_subreddits) are silently ignored by Pydantic.

Polls every 30s for up to 15 min (the pipeline takes ~10-12 min end-to-end
on a cold Cloud Run instance: ~5 min fetch + ~7 min analyst).
"""
import requests, time, json, sys

BASE = "https://painpan-backend-953400329307.us-central1.run.app"
HEADERS = {"Content-Type": "application/json", "Origin": "https://agenticaicolumbia-fb.web.app"}

# A complaint-oriented niche that should surface real pain points.
# (Positive queries like "X recommendations" often yield no classified complaints.)
payload = {
    "query": "gaming mouse",
    "data_source": "reddit_v3",
}

print("Submitting reddit_v3 analysis...")
resp = requests.post(f"{BASE}/api/v1/analysis", json=payload, headers=HEADERS, timeout=30)
print(f"Status: {resp.status_code}")
print(f"Response: {json.dumps(resp.json(), indent=2)[:500]}")

if resp.status_code != 202:
    sys.exit(1)

run_id = resp.json().get("run_id")
print(f"\nRun ID: {run_id}")
print("Polling every 30s for up to 15 min (pipeline takes ~10-12 min on cold start)...")

data = None
status = "running"
deadline = time.time() + 900  # 15 min
poll_count = 0
while time.time() < deadline and status == "running":
    time.sleep(30)
    poll_count += 1
    try:
        r = requests.get(f"{BASE}/api/v1/results/{run_id}", headers=HEADERS, timeout=15)
        if r.status_code == 404:
            print(f"  poll #{poll_count}: 404 (run not yet registered)")
            continue
        data = r.json()
        status = data.get("status", "running")
        print(f"  poll #{poll_count}: status={status}")
    except Exception as e:
        print(f"  poll #{poll_count}: error {e}")

if status == "running":
    print("\nTIMEOUT: pipeline did not finish within 15 min.")
    sys.exit(2)

print(f"\n=== Final status: {status} ===")

if status == "failed":
    print(f"error: {data.get('error')}")
    sys.exit(3)

# status == "completed" — extract the meaningful bits of ResultResponse
print(f"\n--- Fetch / EDA summary ---")
agent_results = data.get("agent_results") or {}
for agent_name, info in agent_results.items():
    print(f"  [{agent_name}] tool_calls={info.get('tool_calls_made')}  "
          f"handoff={info.get('handoff_to')}")

cls_eda = data.get("classification_eda") or {}
if cls_eda:
    total = cls_eda.get("total_posts") or cls_eda.get("total") or "?"
    classified = cls_eda.get("classified_posts") or cls_eda.get("success") or "?"
    print(f"  classification: {classified}/{total} classified")

clu_eda = data.get("clustering_eda") or {}
if clu_eda:
    clusters = clu_eda.get("clusters") or []
    print(f"  clusters: {len(clusters)}")
    for c in clusters[:5]:
        name = c.get("name", "?")
        n = c.get("post_count", c.get("size", "?"))
        print(f"    - {name} ({n} posts)")

hyp = data.get("hypothesis")
if hyp:
    ideas = hyp.get("ideas", []) or []
    print(f"\n--- Hypothesis: {len(ideas)} ideas ---")
    print(f"  analysis_summary: {(hyp.get('analysis_summary') or '')[:200]}")
    for i, idea in enumerate(ideas[:5], 1):
        print(f"  {i}. {idea.get('idea', idea.get('title', '?'))[:100]}")
else:
    print("\n--- No hypothesis returned ---")

report = data.get("report_content")
if report:
    print(f"\n--- Report ({len(report)} chars) ---")
    print(report[:400])
