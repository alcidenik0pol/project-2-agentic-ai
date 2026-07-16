"""LangGraph workflow for the multi-agent Reddit analysis pipeline.

Replaces the custom AgentOrchestrator (runner.py) and Agent class (base.py)
with a LangGraph StateGraph. Each agent is a node in the graph, connected
by explicit edges instead of regex-based handoff detection.

Agent flow: orchestrator -> analyst -> hypothesis -> END

Business logic (classifier, clustering, hypothesis, providers) is unchanged.
"""

import json
import logging
import time
from typing import Any, Optional

from langgraph.graph import END, StateGraph
from typing_extensions import TypedDict

from app.agents.analyst import get_analyst_prompt
from app.agents.hypothesis import get_hypothesis_prompt
from app.agents.orchestrator import ORCHESTRATOR_SYSTEM_PROMPT
from app.agents.tools import execute_tool, get_tool_schemas
from app.agents.tools.shared import clear_shared_data, get_shared_data, set_shared_data
from app.analyst.providers import get_provider
from app.analyst.providers.base import LLMProvider
from app.config import config

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# State definition
# ---------------------------------------------------------------------------

class AgentState(TypedDict, total=False):
    """State flowing through the LangGraph pipeline."""

    messages: list[dict[str, Any]]
    user_query: str
    run_dir: str
    agents_run: list[str]
    total_tool_calls: int
    agent_results: dict[str, Any]
    final_response: str


# ---------------------------------------------------------------------------
# Module-level callback storage (set before pipeline execution)
# ---------------------------------------------------------------------------

_callbacks: dict[str, Any] = {
    "on_agent_started": None,
    "on_agent_completed": None,
}


def set_callbacks(
    on_agent_started: Any = None,
    on_agent_completed: Any = None,
) -> None:
    """Store callbacks for agent lifecycle events."""
    _callbacks["on_agent_started"] = on_agent_started
    _callbacks["on_agent_completed"] = on_agent_completed


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _truncate_tool_result(tool_name: str, result: str, iteration: int) -> str:
    """Truncate oversized tool results to prevent context overflow.

    Stores full result in shared data and returns a compact summary.
    Extracted from the former Agent._truncate_tool_result in base.py.

    NOTE: generate_hypotheses results are never truncated because the
    hypothesis agent needs the full output to write its final summary
    and correctly call save_artifact.
    """
    max_size = config.agent_tool_result_max_size
    if not config.agent_tool_result_enable_truncation:
        return result
    # Never truncate hypothesis results — the agent needs the full data
    # to write its summary and call save_artifact
    if tool_name == "generate_hypotheses":
        return result
    if len(result) <= max_size:
        return result

    # Don't truncate error messages
    try:
        result_json = json.loads(result)
        if isinstance(result_json, dict) and "error" in result_json:
            return result
    except json.JSONDecodeError:
        pass

    preview_length = config.agent_tool_result_preview_chars
    shared_key = f"tool_result_{tool_name}_{iteration}"
    set_shared_data(shared_key, result)

    preview = result[:preview_length]
    if len(result) > preview_length:
        preview += "..."

    summary = {
        "status": "truncated",
        "tool_name": tool_name,
        "original_size": len(result),
        "summary_size": len(preview),
        "shared_key": shared_key,
        "preview": preview,
        "message": (
            f"Full result (~{len(result) // 1024}KB) stored in shared data "
            f"as '{shared_key}'"
        ),
    }
    summary_json = json.dumps(summary, ensure_ascii=False)

    logger.warning(
        f"Truncated tool result for {tool_name}: "
        f"{len(result)} chars -> {len(summary_json)} chars "
        f"(stored as '{shared_key}')"
    )
    return summary_json


def _run_agent_loop(
    agent_name: str,
    system_prompt: str,
    provider: LLMProvider,
    messages: list[dict[str, Any]],
) -> dict[str, Any]:
    """Run a single agent's iterative tool-calling loop.

    Core logic extracted from the former Agent.run() in base.py.
    Sends messages to the LLM, executes any requested tool calls,
    and repeats until the LLM returns text only or max iterations reached.
    """
    max_iterations = config.agent_max_iterations
    tool_schemas = get_tool_schemas(agent_name)
    all_messages = [{"role": "system", "content": system_prompt}] + messages
    tool_calls_made = 0

    for iteration in range(max_iterations):
        logger.info(f"[{agent_name}] Iteration {iteration + 1}/{max_iterations}")

        try:
            response = provider.chat_with_tools(
                messages=all_messages,
                tools=tool_schemas,
                temperature=0.3,
                use_fast=True,
            )
        except Exception as e:
            logger.error(f"[{agent_name}] LLM failed after retries: {e}")
            return {
                "response": f"Error: LLM call failed after retries - {e}",
                "tool_calls_made": tool_calls_made,
                "messages": all_messages,
            }

        # Append assistant message to history
        assistant_msg: dict[str, Any] = {"role": "assistant"}
        if response.content:
            assistant_msg["content"] = response.content
        if response.tool_calls:
            assistant_msg["tool_calls"] = [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.name,
                        "arguments": tc.arguments,
                    },
                }
                for tc in response.tool_calls
            ]
        all_messages.append(assistant_msg)

        # No tool calls -> agent is done
        if not response.tool_calls:
            conclusion = (response.content or "").strip()
            logger.info(f"[{agent_name}] Concluded: {conclusion[:300]}")
            return {
                "response": response.content or "",
                "tool_calls_made": tool_calls_made,
                "messages": all_messages,
            }

        # Execute each tool call
        for tool_call in response.tool_calls:
            tool_name = tool_call.name
            tool_args_str = tool_call.arguments

            logger.info(f"[{agent_name}] Tool call: {tool_name}")
            try:
                tool_args = json.loads(tool_args_str)
            except json.JSONDecodeError:
                tool_args = {}

            tool_result = execute_tool(tool_name, tool_args)
            tool_calls_made += 1

            tool_result = _truncate_tool_result(tool_name, tool_result, iteration)

            all_messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": tool_result,
            })
            logger.info(f"[{agent_name}] Tool result: {tool_result[:200]}...")

    # Max iterations reached
    logger.warning(
        f"[{agent_name}] Halted at max iterations ({max_iterations}); "
        f"processing may be incomplete."
    )
    return {
        "response": "Maximum iterations reached. Processing may be incomplete.",
        "tool_calls_made": tool_calls_made,
        "messages": all_messages,
    }


def _build_context_messages(
    user_query: str,
    from_agent: str,
    response: str,
) -> list[dict[str, Any]]:
    """Build messages for the next agent in the pipeline.

    Since data flows through the shared store, we only tell the LLM
    what data is available, not the data itself.
    """
    context_map = {
        "orchestrator": (
            "The orchestrator has finished. Check what the orchestrator reported and "
            "what is in the shared store (fetched_posts). If the fetch returned an error "
            "or 0 posts, do NOT call classify_posts — there is nothing to analyze; "
            "state that clearly and stop. Otherwise proceed with classify_posts, "
            "then cluster_themes."
        ),
        "analyst": (
            "The analyst has finished. Check what the analyst reported and what is in "
            "the shared store (clustered_data). If classification or clustering could "
            "not produce results, do NOT call generate_hypotheses — state that clearly "
            "and stop. Otherwise proceed with generate_hypotheses, then save_artifact."
        ),
    }
    context_msg = context_map.get(
        from_agent,
        f"The {from_agent} agent has completed its work.",
    )

    return [
        {"role": "user", "content": user_query},
        {"role": "assistant", "content": f"[{from_agent}]: {response}"},
        {"role": "user", "content": context_msg},
    ]


# ---------------------------------------------------------------------------
# Graph node functions
# ---------------------------------------------------------------------------

def orchestrator_node(state: AgentState) -> dict:
    """Orchestrator node: accepts user query, fetches Reddit posts."""
    provider = get_provider(config.llm_provider)
    on_started = _callbacks.get("on_agent_started")
    if on_started:
        on_started("orchestrator", 1, 3)

    t0 = time.monotonic()
    result = _run_agent_loop(
        agent_name="orchestrator",
        system_prompt=ORCHESTRATOR_SYSTEM_PROMPT,
        provider=provider,
        messages=state.get("messages", []),
    )
    duration = time.monotonic() - t0

    on_completed = _callbacks.get("on_agent_completed")
    if on_completed:
        on_completed("orchestrator", duration)

    agents_run = state.get("agents_run", []) + ["orchestrator"]
    agent_results = dict(state.get("agent_results", {}))
    agent_results["orchestrator"] = {
        "response": result["response"][:500],
        "tool_calls_made": result["tool_calls_made"],
        "handoff_to": "analyst",
    }

    # Build context for the next agent
    user_query = state.get("user_query", "")
    new_messages = _build_context_messages(user_query, "orchestrator", result["response"])

    return {
        "messages": new_messages,
        "agents_run": agents_run,
        "total_tool_calls": state.get("total_tool_calls", 0) + result["tool_calls_made"],
        "agent_results": agent_results,
    }


def analyst_node(state: AgentState) -> dict:
    """Analyst node: classifies posts and clusters themes."""
    provider = get_provider(config.llm_provider)
    on_started = _callbacks.get("on_agent_started")
    if on_started:
        on_started("analyst", 2, 3)

    user_query = state.get("user_query", "")
    analyst_prompt = get_analyst_prompt(user_query)

    t0 = time.monotonic()
    result = _run_agent_loop(
        agent_name="analyst",
        system_prompt=analyst_prompt,
        provider=provider,
        messages=state.get("messages", []),
    )
    duration = time.monotonic() - t0

    on_completed = _callbacks.get("on_agent_completed")
    if on_completed:
        on_completed("analyst", duration)

    agents_run = state.get("agents_run", []) + ["analyst"]
    agent_results = dict(state.get("agent_results", {}))
    agent_results["analyst"] = {
        "response": result["response"][:500],
        "tool_calls_made": result["tool_calls_made"],
        "handoff_to": "hypothesis",
    }

    user_query = state.get("user_query", "")
    new_messages = _build_context_messages(user_query, "analyst", result["response"])

    return {
        "messages": new_messages,
        "agents_run": agents_run,
        "total_tool_calls": state.get("total_tool_calls", 0) + result["tool_calls_made"],
        "agent_results": agent_results,
    }


def hypothesis_node(state: AgentState) -> dict:
    """Hypothesis node: generates business ideas from clustered data."""
    provider = get_provider(config.llm_provider)
    on_started = _callbacks.get("on_agent_started")
    if on_started:
        on_started("hypothesis", 3, 3)

    user_query = state.get("user_query", "")
    hypothesis_prompt = get_hypothesis_prompt(user_query)

    t0 = time.monotonic()
    result = _run_agent_loop(
        agent_name="hypothesis",
        system_prompt=hypothesis_prompt,
        provider=provider,
        messages=state.get("messages", []),
    )
    duration = time.monotonic() - t0

    on_completed = _callbacks.get("on_agent_completed")
    if on_completed:
        on_completed("hypothesis", duration)

    agents_run = state.get("agents_run", []) + ["hypothesis"]
    agent_results = dict(state.get("agent_results", {}))
    agent_results["hypothesis"] = {
        "response": result["response"][:500],
        "tool_calls_made": result["tool_calls_made"],
        "handoff_to": None,
    }

    return {
        "messages": result["messages"],
        "agents_run": agents_run,
        "total_tool_calls": state.get("total_tool_calls", 0) + result["tool_calls_made"],
        "agent_results": agent_results,
        "final_response": result["response"],
    }


# ---------------------------------------------------------------------------
# Workflow builder
# ---------------------------------------------------------------------------

def build_workflow() -> StateGraph:
    """Build the LangGraph StateGraph for the analysis pipeline."""
    workflow = StateGraph(AgentState)

    # Add nodes (each agent is a node)
    workflow.add_node("orchestrator", orchestrator_node)
    workflow.add_node("analyst", analyst_node)
    workflow.add_node("hypothesis", hypothesis_node)

    # Define edges: orchestrator -> analyst -> hypothesis -> END
    # This replaces the regex-based HANDOFF_TO_AGENT pattern
    workflow.set_entry_point("orchestrator")
    workflow.add_edge("orchestrator", "analyst")
    workflow.add_edge("analyst", "hypothesis")
    workflow.add_edge("hypothesis", END)

    return workflow


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def run_pipeline(
    user_query: str,
    run_dir: str | None = None,
    on_agent_started: Any = None,
    on_agent_completed: Any = None,
) -> dict[str, Any]:
    """Run the full LangGraph analysis pipeline.

    Args:
        user_query: The user's topic or question.
        run_dir: Output directory for artifacts.
        on_agent_started: Optional callback(agent_name, idx, total).
        on_agent_completed: Optional callback(agent_name, duration_seconds).

    Returns:
        dict with final_response, agents_run, total_tool_calls, agent_results.
    """
    logger.info(f"Starting LangGraph pipeline for query: '{user_query}'")

    # Store callbacks for node functions to access
    set_callbacks(on_agent_started=on_agent_started, on_agent_completed=on_agent_completed)

    # Clear shared data from previous runs, preserve run_dir
    old_run_dir = get_shared_data("run_dir")
    clear_shared_data()
    if run_dir:
        set_shared_data("run_dir", run_dir)
    elif old_run_dir:
        set_shared_data("run_dir", old_run_dir)

    # Build and compile the graph
    workflow = build_workflow()
    app = workflow.compile()

    # Initial state
    initial_state: AgentState = {
        "messages": [{"role": "user", "content": user_query}],
        "user_query": user_query,
        "run_dir": run_dir or "",
        "agents_run": [],
        "total_tool_calls": 0,
        "agent_results": {},
        "final_response": "",
    }

    # Execute the graph
    result = app.invoke(initial_state)

    logger.info(
        f"Pipeline complete. Agents run: {result.get('agents_run', [])}, "
        f"Tools called: {result.get('total_tool_calls', 0)}"
    )

    return {
        "final_response": result.get("final_response", ""),
        "agents_run": result.get("agents_run", []),
        "total_tool_calls": result.get("total_tool_calls", 0),
        "agent_results": result.get("agent_results", {}),
    }
