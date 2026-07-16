"""Quick test: POST a small reddit_v2 analysis to the prod backend
and poll the results to see if the proxy works."""
import requests, time, json

BASE = "https://painpan-backend-953400329307.us-central1.run.app"
HEADERS = {"Content-Type": "application/json", "Origin": "https://agenticaicolumbia-fb.web.app"}

# Small test: 1 subreddit, short topic
payload = {
    "query": "gaming mouse recommendations",
    "data_source": "reddit_v2",
    "max_subreddits": 1,
    "max_posts_per_subreddit": 3,
    "max_posts_with_comments": 1,
}

print("Submitting reddit_v2 analysis...")
resp = requests.post(f"{BASE}/api/v1/analysis", json=payload, headers=HEADERS, timeout=30)
print(f"Status: {resp.status_code}")
print(f"Response: {json.dumps(resp.json(), indent=2)[:500]}")

if resp.status_code == 202:
    run_id = resp.json().get("run_id")
    print(f"\nRun ID: {run_id}")
    print("Waiting 30s for fetch phase...")
    time.sleep(30)

    # Check results
    r2 = requests.get(f"{BASE}/api/v1/results/{run_id}", headers=HEADERS, timeout=15)
    print(f"\nResults status: {r2.status_code}")
    data = r2.json()
    status = data.get("status")
    print(f"Run status: {status}")

    if status == "failed":
        errors = data.get("errors", [])
        print(f"Errors: {errors[:3]}")

    posts = data.get("posts", [])
    print(f"Posts collected: {len(posts)}")
    if posts:
        print(f"First post title: {posts[0].get('title', 'N/A')}")
