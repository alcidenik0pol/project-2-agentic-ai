"""Pull logs for a specific run_id, sorted ascending.

Usage: python scripts/pull_run_logs.py <run_id>
"""
import subprocess, sys, json

if len(sys.argv) < 2:
    print("usage: python scripts/pull_run_logs.py <run_id>", file=sys.stderr)
    sys.exit(1)
RUN_ID = sys.argv[1]

FILTER = (
    'resource.type="cloud_run_revision" '
    'AND resource.labels.service_name="painpan-backend" '
    'AND timestamp>="2026-07-24T16:00:00Z"'
)

cmd = [
    r"F:\Program Files (x86)\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd",
    "logging", "read",
    "--project=agenticaicolumbia",
    FILTER,
    "--limit=1500",
    "--format=json",
    "--order=asc",
]

print(f"Running gcloud for run_id={RUN_ID}...", file=sys.stderr)
r = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
if r.returncode != 0:
    print("STDERR:", r.stderr, file=sys.stderr)
    sys.exit(r.returncode)

entries = json.loads(r.stdout)
print(f"Got {len(entries)} total entries", file=sys.stderr)

# Skip the noisy poll lines (GET /api/v1/results/<id> 200 OK from our probe)
NOISE_PATTERNS = [
    "results/" + RUN_ID + " HTTP",
    '169.254.169.126',  # Cloud Run metadata service / health checks
    "Raw Gemini response for",  # per-post classification output
    "Processing batch",
    "Progress:",
]

KEEP_KEYWORDS = [
    "reddit_v3", "[REDDIT_V3]", "Rate limit:", "Error fetching",
    "fetch_posts", "circuit", "429", "broken pipe",
    "PIPELINE", "classify", "cluster", "hypothesis", "Step ",
    "LLM call", "Iteration", "Tool ", "analyst", "orchestrator",
    "WARN", "ERROR",
]
for e in entries:
    msg = e.get("textPayload") or e.get("jsonPayload", {}).get("message", "")
    if not msg:
        continue
    if any(n in msg for n in NOISE_PATTERNS):
        continue
    is_this_run = RUN_ID in msg
    is_global = any(k.lower() in msg.lower() for k in KEEP_KEYWORDS)
    if not is_this_run and not is_global:
        continue
    ts = e.get("timestamp", "")[11:19]
    print(f"{ts}  {msg[:300]}")
