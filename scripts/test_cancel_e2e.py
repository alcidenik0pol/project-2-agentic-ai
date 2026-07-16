"""End-to-end test of the Stop button via the real backend WS cancel flow.

Replicates exactly what the frontend does: POST to create a run, open WS,
listen, then send {"type": "cancel_analysis"} mid-fetch. Verifies:
  1. analysis_cancelled frame is received after cancel.
  2. Cancel latency is short (fetch-phase cooperative flag works).
  3. The run directory is removed by the cleanup path.

Run with the backend already up on port 8901:
    conda run -n agentic-ai-p2 python scripts/test_cancel_e2e.py
"""
import asyncio
import json
import time
from pathlib import Path

import httpx
import websockets

BASE = "http://127.0.0.1:8901"
WS_BASE = "ws://127.0.0.1:8901"
PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPORTS = PROJECT_ROOT / "output" / "reports"

# Reactive cancel: once we see fetch phase start, wait this long, then cancel.
# This lands the cancel mid-fetch (~1-2 subreddits in) regardless of how long
# the LLM subreddit-selection call took.
CANCEL_DELAY_AFTER_FETCH_START_S = 8.0
# Fallback: if fetch never starts (e.g. LLM phase errors), give up after this.
FALLBACK_CANCEL_AFTER_S = 90.0
# How long to wait for analysis_cancelled after sending cancel.
WAIT_CANCEL_TIMEOUT_S = 30.0


async def main():
    # 1. Create run via REST (same as frontend).
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.post(
            f"{BASE}/api/v1/analysis",
            json={"query": "gaming", "data_source": "reddit_v2"},
        )
    if resp.status_code == 429:
        print("USAGE_LIMIT: blocked by monthly token cap. Aborting.")
        return
    resp.raise_for_status()
    run_id = resp.json()["run_id"]
    print(f"[run] created run_id={run_id}")

    # Snapshot run dirs before cancel so we can detect cleanup.
    from datetime import date
    today = date.today().isoformat()
    today_dir = REPORTS / today
    before = set(p.name for p in today_dir.glob("*")) if today_dir.exists() else set()

    cancelled_seen = {"val": False}
    fetch_started_at = {"val": None}
    last_fetch_log = {"val": None}
    cancel_sent_at = {"val": None}
    ws_t0 = time.time()

    # 2. Connect WS.
    async with websockets.connect(f"{WS_BASE}/ws/{run_id}", max_size=None) as ws:
        print(f"[ws] connected at t+0.0s")

        # Reactive cancel: armed once fetch phase is observed, fires after
        # CANCEL_DELAY_AFTER_FETCH_START_S. Fallback arms at FALLBACK_CANCEL_AFTER_S.
        cancel_armed = asyncio.Event()

        async def send_cancel():
            try:
                await asyncio.wait_for(cancel_armed.wait(), timeout=FALLBACK_CANCEL_AFTER_S)
            except asyncio.TimeoutError:
                print(f"\n[FALLBACK] fetch never started; cancelling at t+{time.time()-ws_t0:.1f}s")
            delay = CANCEL_DELAY_AFTER_FETCH_START_S if fetch_started_at["val"] else 0.0
            await asyncio.sleep(delay)
            cancel_sent_at["val"] = time.time()
            print(f"\n[CANCEL] sending cancel_analysis at t+{time.time()-ws_t0:.1f}s"
                  f" ({delay:.0f}s after fetch started)\n")
            await ws.send(json.dumps({"type": "cancel_analysis"}))

        cancel_task = asyncio.create_task(send_cancel())

        try:
            while True:
                raw = await asyncio.wait_for(ws.recv(), timeout=WAIT_CANCEL_TIMEOUT_S)
                msg = json.loads(raw)
                mtype = msg.get("type")
                t = time.time() - ws_t0
                if mtype == "log_entry":
                    txt = msg["data"].get("message", "")
                    aname = msg["data"].get("agent_name") or ""
                    low = txt.lower()
                    # Detect fetch phase start / progress.
                    if "starting data collection" in low or "progress:" in low or "collection complete" in low or "rate limit: 10" in low:
                        if fetch_started_at["val"] is None and "starting data collection" in low:
                            fetch_started_at["val"] = t
                            print(f"  [t+{t:5.1f}s][FETCH START] {txt[:110]}")
                            cancel_armed.set()
                        last_fetch_log["val"] = (t, txt[:120])
                        print(f"  [t+{t:5.1f}s][{aname}] {txt[:110]}")
                elif mtype == "analysis_cancelled":
                    cancelled_seen["val"] = True
                    latency = t - (cancel_sent_at["val"] or t)
                    print(f"\n[RECV] analysis_cancelled at t+{t:.1f}s (cancel->ack latency {latency*1000:.0f}ms)")
                    break
                elif mtype == "analysis_complete":
                    print(f"\n[RECV] analysis_COMPLETE at t+{t:.1f}s (run finished before cancel took effect!)")
                    break
                elif mtype == "error":
                    print(f"\n[RECV] error at t+{t:.1f}s: {msg['data'].get('message')}")
                    break
                else:
                    pass  # rate_limit_update spam is suppressed
        except asyncio.TimeoutError:
            print(f"\n[TIMEOUT] no message for {WAIT_CANCEL_TIMEOUT_S}s")

        cancel_task.cancel()
        try:
            await cancel_task
        except asyncio.CancelledError:
            pass

    # 4. Verify run dir cleanup.
    await asyncio.sleep(1.5)  # let rmtree settle
    after = set(p.name for p in today_dir.glob("*")) if today_dir.exists() else set()
    new_dirs = after - before
    leftover = [d for d in new_dirs if run_id in d or True]  # any dir from this run

    print("\n" + "=" * 60)
    print("RESULTS")
    print("=" * 60)
    print(f"  analysis_cancelled received : {cancelled_seen['val']}")
    if last_fetch_log["val"]:
        print(f"  fetch phase was active      : yes (last: t+{last_fetch_log['val'][0]:.1f}s)")
    else:
        print(f"  fetch phase was active      : no (cancel may have hit LLM-selection phase)")
    # Check for orphaned run dir
    orphan = None
    for d in new_dirs:
        full = today_dir / d
        meta = full / "metadata.json"
        if meta.exists():
            try:
                if json.loads(meta.read_text()).get("run_id") == run_id:
                    orphan = full
                    break
            except Exception:
                pass
    print(f"  run dir cleaned up          : {'YES' if orphan is None else 'NO -> ' + str(orphan)}")
    ok = cancelled_seen["val"] and orphan is None
    print(f"  OVERALL                     : {'PASS' if ok else 'FAIL'}")


if __name__ == "__main__":
    asyncio.run(main())
