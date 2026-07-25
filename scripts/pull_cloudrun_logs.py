"""Pull recent Cloud Run logs for painpan-backend via the gcloud REST API.

Used to diagnose the stuck reddit_v3 run cd32b8b47e94.
"""
import subprocess, sys, json

FILTER = (
    'resource.type="cloud_run_revision" '
    'AND resource.labels.service_name="painpan-backend" '
    'AND timestamp>="2026-07-23T12:00:00Z"'
)

cmd = [
    r"F:\Program Files (x86)\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd",
    "logging", "read",
    "--project=agenticaicolumbia",
    FILTER,
    "--limit=80",
    "--format=json",
    "--order=desc",
]

print("Running gcloud logging read...", file=sys.stderr)
result = subprocess.run(cmd, capture_output=True, text=True)
if result.returncode != 0:
    print("STDERR:", result.stderr, file=sys.stderr)
    print("STDOUT:", result.stdout, file=sys.stderr)
    sys.exit(result.returncode)

entries = json.loads(result.stdout)
print(f"Got {len(entries)} entries\n", file=sys.stderr)

for e in entries:
    ts = e.get("timestamp", "")
    payload = e.get("textPayload") or e.get("jsonPayload", {}).get("message") or ""
    if not payload and e.get("jsonPayload"):
        payload = json.dumps(e["jsonPayload"])[:200]
    print(f"{ts}  {payload}")
