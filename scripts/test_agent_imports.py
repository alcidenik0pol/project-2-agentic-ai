"""Quick verification that agent framework imports and methods work."""

import json
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))


def main():
    errors = []

    # 1. Config
    try:
        from app.config import config, get_data_source
        print(f"[OK] Config: llm_provider={config.llm_provider}, data_source={get_data_source()}")
    except Exception as e:
        errors.append(f"Config: {e}")
        print(f"[FAIL] Config: {e}")

    # 2. Base dataclasses
    try:
        from app.analyst.providers.base import ChatToolResponse, ToolCallInfo

        tc = ToolCallInfo(id="test_1", name="fetch_posts", arguments='{"topic": "debt"}')
        assert tc.id == "test_1"
        resp = ChatToolResponse(content="hello", tool_calls=[tc])
        assert resp.content == "hello"
        assert len(resp.tool_calls) == 1
        resp2 = ChatToolResponse()
        assert resp2.content is None
        assert resp2.tool_calls == []
        print("[OK] ChatToolResponse + ToolCallInfo dataclasses")
    except Exception as e:
        errors.append(f"Dataclasses: {e}")
        print(f"[FAIL] Dataclasses: {e}")

    # 3. Provider methods
    try:
        from app.analyst.providers.gcloud import GCloudProvider
        from app.analyst.providers.lm_studio import LMStudioProvider
        from app.analyst.providers.openai_gemini import OpenAIGeminiProvider

        for cls in [GCloudProvider, LMStudioProvider, OpenAIGeminiProvider]:
            assert hasattr(cls, "chat_with_tools"), f"{cls.__name__} missing chat_with_tools"
        print("[OK] All providers have chat_with_tools()")
    except Exception as e:
        errors.append(f"Provider methods: {e}")
        print(f"[FAIL] Provider methods: {e}")

    # 4. Provider registry
    try:
        from app.analyst.providers import get_provider
        print("[OK] Provider registry works")
    except Exception as e:
        errors.append(f"Provider registry: {e}")
        print(f"[FAIL] Provider registry: {e}")

    # 5. Tool registry
    try:
        from app.agents.tools import execute_tool, get_tool_schemas

        orch_tools = get_tool_schemas("orchestrator")
        assert len(orch_tools) == 1
        assert orch_tools[0]["function"]["name"] == "fetch_posts"

        analyst_tools = get_tool_schemas("analyst")
        assert len(analyst_tools) == 2
        names = {t["function"]["name"] for t in analyst_tools}
        assert names == {"classify_posts", "cluster_themes"}

        hypo_tools = get_tool_schemas("hypothesis")
        assert len(hypo_tools) == 2
        names2 = {t["function"]["name"] for t in hypo_tools}
        assert names2 == {"generate_hypotheses", "save_artifact"}

        print("[OK] Tool registry correct for all agents")
    except Exception as e:
        errors.append(f"Tools: {e}")
        print(f"[FAIL] Tools: {e}")

    # 6. Fetch test mode
    try:
        from app.agents.tools.fetch import fetch_posts

        result = fetch_posts("test topic")
        data = json.loads(result)
        assert "status" in data or "total_posts" in data
        if "total_posts" in data:
            assert data["total_posts"] > 0
        print(f"[OK] fetch_posts test mode: {data}")
    except Exception as e:
        errors.append(f"Fetch: {e}")
        print(f"[FAIL] Fetch: {e}")

    # 7. LangGraph workflow (no OpenAI import)
    try:
        from app.agents.graph import AgentState, build_workflow, run_pipeline
        import app.agents.graph as graph_mod
        assert not hasattr(graph_mod, "OpenAI"), "graph.py should NOT import OpenAI"
        print("[OK] LangGraph workflow (AgentState, build_workflow, run_pipeline)")
    except Exception as e:
        errors.append(f"LangGraph: {e}")
        print(f"[FAIL] LangGraph: {e}")

    # 8. LangGraph dependencies
    try:
        from langgraph.graph import StateGraph, END
        print("[OK] LangGraph dependencies available")
    except Exception as e:
        errors.append(f"LangGraph deps: {e}")
        print(f"[FAIL] LangGraph deps: {e}")

    # 9. Logging
    try:
        from app.agents.logging_setup import setup_agent_logging
        print("[OK] Logging setup imported")
    except Exception as e:
        errors.append(f"Logging: {e}")
        print(f"[FAIL] Logging: {e}")

    # Summary
    print()
    if errors:
        print(f"FAILED: {len(errors)} errors")
        for e in errors:
            print(f"  - {e}")
        sys.exit(1)
    else:
        print("All 9 checks passed!")


if __name__ == "__main__":
    main()
