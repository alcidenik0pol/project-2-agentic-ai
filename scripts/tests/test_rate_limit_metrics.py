"""Test rate limit metrics for frontend consumption."""

import json
import time

from app.reddit.client import RedditPublicAPI


def test_initial_state():
    """Test initial rate limit state."""
    api = RedditPublicAPI()

    assert api.requests_in_window == 0
    assert api.requests_remaining == 10
    assert api.is_throttled is False
    assert api.throttle_wait_time is None
    print("✓ Initial state correct")


def test_status_dict():
    """Test get_rate_limit_status returns valid dict."""
    api = RedditPublicAPI()
    status = api.get_rate_limit_status()

    assert isinstance(status, dict)
    assert status["requests_in_window"] == 0
    assert status["requests_remaining"] == 10
    assert status["limit"] == 10
    assert status["window_seconds"] == 60
    assert status["is_throttled"] is False
    assert status["throttle_wait_time"] is None
    print("✓ Status dict correct")


def test_json_serialization():
    """Test status dict is JSON-serializable."""
    api = RedditPublicAPI()
    status = api.get_rate_limit_status()

    # Should not raise
    json_str = json.dumps(status)
    assert len(json_str) > 0
    print(f"✓ JSON serialization works: {json_str}")


def test_after_simulated_requests():
    """Test state after simulating request timestamps."""
    api = RedditPublicAPI()

    # Simulate 5 requests in the window
    now = time.time()
    api._request_times = [now - 10, now - 20, now - 30, now - 40, now - 50]

    assert api.requests_in_window == 5
    assert api.requests_remaining == 5
    assert api.is_throttled is False
    print("✓ State after 5 requests correct")

    # Simulate 10 requests (at limit)
    api._request_times = [now - i for i in range(1, 11)]
    assert api.requests_in_window == 10
    assert api.requests_remaining == 0
    assert api.is_throttled is True
    assert api.throttle_wait_time is not None
    assert api.throttle_wait_time > 0
    print(f"✓ State at limit correct (throttle_wait_time: {api.throttle_wait_time:.1f}s)")


if __name__ == "__main__":
    test_initial_state()
    test_status_dict()
    test_json_serialization()
    test_after_simulated_requests()
    print("\n✅ All tests passed!")
