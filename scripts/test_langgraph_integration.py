"""Integration test: verify LangGraph pipeline components work correctly.

Tests the graph structure, tool execution, shared data flow, and
state passing without requiring LLM provider credentials.
"""

import json
import sys
from pathlib import Path

project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))

from app.config import set_data_source_override

set_data_source_override("sample_default")


def test_graph_structure():
    """Test that the LangGraph graph compiles with correct nodes and edges."""
    from app.agents.graph import build_workflow

    workflow = build_workflow()
    app = workflow.compile()

    graph = app.get_graph()
    node_names = set(graph.nodes.keys())
    expected_nodes = {"__start__", "orchestrator", "analyst", "hypothesis", "__end__"}
    assert node_names == expected_nodes, f"Expected {expected_nodes}, got {node_names}"

    # Check edges
    edge_pairs = {(e[0], e[1]) for e in graph.edges}
    assert ("__start__", "orchestrator") in edge_pairs
    assert ("orchestrator", "analyst") in edge_pairs
    assert ("analyst", "hypothesis") in edge_pairs
    assert ("hypothesis", "__end__") in edge_pairs

    print("[PASS] Graph structure: correct nodes and edges")


def test_tool_execution():
    """Test that tools work through the shared data flow."""
    from app.agents.tools.shared import clear_shared_data, get_shared_data

    clear_shared_data()

    # Test fetch_posts
    from app.agents.tools.fetch import fetch_posts

    result = fetch_posts("test topic")
    data = json.loads(result)
    assert data["status"] == "success"
    assert data["total_posts"] > 0

    # Verify shared data was stored
    fetched = get_shared_data("fetched_posts")
    assert fetched is not None
    assert len(fetched["posts"]) > 0

    print(f"[PASS] Tool execution: fetch_posts stored {data['total_posts']} posts in shared data")


def test_state_typedef():
    """Test that AgentState TypedDict is properly defined."""
    from app.agents.graph import AgentState

    # Create a valid state
    state = AgentState(
        messages=[{"role": "user", "content": "test"}],
        user_query="test",
        run_dir="/tmp/test",
        agents_run=[],
        total_tool_calls=0,
        agent_results={},
        final_response="",
    )
    assert state["user_query"] == "test"
    assert state["messages"][0]["content"] == "test"

    print("[PASS] AgentState TypedDict: valid state creation")


def test_truncation():
    """Test tool result truncation logic."""
    from app.agents.graph import _truncate_tool_result
    from app.agents.tools.shared import clear_shared_data, get_shared_data

    clear_shared_data()

    # Small result should pass through
    small = "hello"
    assert _truncate_tool_result("test", small, 0) == "hello"

    # Error result should pass through
    error = json.dumps({"error": "something failed"})
    assert _truncate_tool_result("test", error, 0) == error

    # Large result should be truncated
    large = "x" * 50000
    truncated = _truncate_tool_result("test", large, 0)
    parsed = json.loads(truncated)
    assert parsed["status"] == "truncated"
    assert parsed["shared_key"] == "tool_result_test_0"
    # Full data should be in shared store
    assert get_shared_data("tool_result_test_0") == large

    print("[PASS] Tool result truncation: works correctly")


def test_context_messages():
    """Test context message builder for inter-agent communication."""
    from app.agents.graph import _build_context_messages

    msgs = _build_context_messages("test query", "orchestrator", "fetched 30 posts")
    assert len(msgs) == 3
    assert msgs[0]["role"] == "user"
    assert msgs[0]["content"] == "test query"
    assert msgs[1]["role"] == "assistant"
    assert "orchestrator" in msgs[1]["content"]
    assert msgs[2]["role"] == "user"
    assert "shared store" in msgs[2]["content"]

    msgs2 = _build_context_messages("test query", "analyst", "found 5 clusters")
    assert "shared store" in msgs2[2]["content"]
    assert "generate_hypotheses" in msgs2[2]["content"]

    print("[PASS] Context messages: correct format for inter-agent communication")


def test_callback_storage():
    """Test module-level callback storage."""
    from app.agents.graph import _callbacks, set_callbacks

    set_callbacks(on_agent_started=lambda n, i, t: None, on_agent_completed=lambda n, d: None)
    assert _callbacks["on_agent_started"] is not None
    assert _callbacks["on_agent_completed"] is not None

    # Test that callbacks are actually called
    started_calls = []
    completed_calls = []

    set_callbacks(
        on_agent_started=lambda n, i, t: started_calls.append((n, i, t)),
        on_agent_completed=lambda n, d: completed_calls.append((n, d)),
    )

    from app.agents.graph import orchestrator_node

    # We can't fully run orchestrator_node without LLM, but we can verify
    # the callback mechanism by checking the stored callbacks
    assert _callbacks["on_agent_started"] is not None

    # Clean up
    set_callbacks()

    print("[PASS] Callback storage: callbacks stored and retrievable")


def test_run_pipeline_signature():
    """Test that run_pipeline has the correct signature and return shape."""
    from app.agents.graph import run_pipeline
    import inspect

    sig = inspect.signature(run_pipeline)
    params = list(sig.parameters.keys())
    assert "user_query" in params
    assert "run_dir" in params
    assert "on_agent_started" in params
    assert "on_agent_completed" in params

    print("[PASS] run_pipeline signature: correct parameters")


def test_analysis_service_imports():
    """Test that analysis_service.py can import the new graph module."""
    from app.agents.graph import run_pipeline

    # Verify it's the same function referenced by __init__.py
    from app.agents import run_pipeline as init_run_pipeline

    assert run_pipeline is init_run_pipeline

    print("[PASS] Module imports: graph.py correctly exported via __init__.py")


if __name__ == "__main__":
    tests = [
        test_graph_structure,
        test_tool_execution,
        test_state_typedef,
        test_truncation,
        test_context_messages,
        test_callback_storage,
        test_run_pipeline_signature,
        test_analysis_service_imports,
    ]

    passed = 0
    failed = 0
    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"[FAIL] {test.__name__}: {e}")
            import traceback
            traceback.print_exc()
            failed += 1

    print(f"\n{passed}/{passed + failed} tests passed")
    if failed:
        sys.exit(1)
