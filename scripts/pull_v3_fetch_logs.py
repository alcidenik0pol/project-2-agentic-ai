"""Pull fetch-phase logs for the reddit_v3 run cd32b8b47e94.

Window: run start through analyst classify, so we can see which subreddits
were selected and how many posts each yielded.
"""
import subprocess, sys, json

FILTER = (
    'resource.type="cloud_run_revision" '
    'AND resource.labels.service_name="painpan-backend" '
    'AND timestamp>="2026-07-23T23:30:00Z" '
    'AND timestamp<="2026-07-23T23:41:00Z"'
)

cmd = [
    r"F:\Program Files (x86)\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd",
    "logging", "read",
    "--project=agenticaicolumbia",
    FILTER,
    "--limit=300",
    "--format=json",
    "--order=asc",
]

print("Running gcloud...", file=sys.stderr)
r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
print(f"Got rc={r.returncode}, stdout_len={len(r.stdout)}", file=sys.stderr)
if r.returncode != 0:
    print("STDERR:", r.stderr, file=sys.stderr)
    sys.exit(r.returncode)

entries = json.loads(r.stdout)
print(f"Got {len(entries)} entries\n", file=sys.stderr)

# Filter to interesting lines for THIS run
KEYS = [
    "cd32b8b47e94",
    "subreddit",
    "fetcher",
    "v3",
    "rss",
    "collector",
    "orchestrator",
    "Initializing",
    "Tool ",
    "Submission",
    "classified",
    "LLM call",
    "circuit",
    "429",
    "WARN",
    "ERROR",
    "PIPELINE",
]
for e in entries:
    msg = e.get("textPayload") or e.get("jsonPayload", {}).get("message", "")
    if not msg:
        continue
    if not any(k.lower() in msg.lower() for k in KEYS):
        continue
    ts = e.get("timestamp", "")[11:19]
    print(f"{ts}  {msg[:280]}")
