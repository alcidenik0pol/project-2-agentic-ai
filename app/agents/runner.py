"""Agent orchestration runner: manages multi-agent handoff loop."""

import json
import logging
from typing import Any

from app.agents.analyst import ANALYST_SYSTEM_PROMPT
from app.agents.base import Agent
from app.agents.hypothesis import HYPOTHESIS_SYSTEM_PROMPT
from app.agents.orchestrator import ORCHESTRATOR_SYSTEM_PROMPT
from app.agents.tools.shared import clear_shared_data, get_shared_data, set_shared_data
from app.analyst.providers import get_provider
from app.analyst.providers.base import LLMProvider
from app.config import config
from app.utils.timing import timed

logger = logging.getLogger(__name__)

# System prompts by agent name
SYSTEM_PROMPTS = {
    "orchestrator": ORCHESTRATOR_SYSTEM_PROMPT,
    "analyst": ANALYST_SYSTEM_PROMPT,
    "hypothesis": HYPOTHESIS_SYSTEM_PROMPT,
}


class AgentOrchestrator:
    """Manages the multi-agent handoff loop.

    Runs orchestrator -> analyst -> hypothesis in sequence.
    Each agent's output is passed as context to the next agent.
    The LLM decides which tools to call within each agent.

    Uses the configured LLMProvider (gcloud, lm_studio, or openai_gemini)
    for all LLM interactions. No hardcoded API keys or clients.

    Data flows between agents through a shared data store (not through
    LLM context), avoiding MALFORMED_FUNCTION_CALL errors from large JSON.
    """

    def __init__(self, provider_name: str | None = None):
        self._provider_name = provider_name or config.llm_provider
        self.provider: LLMProvider = get_provider(self._provider_name)

        logger.info(
            f"AgentOrchestrator initialized with provider: "
            f"{self._provider_name} ({self.provider.model_name})"
        )

    @timed("agent_orchestrator_run")
    def run(self, user_query: str, on_agent_started=None, on_agent_completed=None) -> dict[str, Any]:
        """Run the full agent pipeline for a user query.

        Args:
            user_query: The user's topic or question.
            on_agent_started: Optional callback(agent_name, idx, total) called before an agent runs.
            on_agent_completed: Optional callback(agent_name, duration_seconds) called after an agent finishes.

        Returns:
            {
                "final_response": str,
                "agents_run": list[str],
                "total_tool_calls": int,
                "agent_results": dict,
            }
        """
        logger.info(f"Starting agent pipeline for query: '{user_query}'")
        logger.info(f"Mode: {config.agent_mode}")

        # Clear shared data from previous runs, but preserve run_dir
        run_dir = get_shared_data("run_dir")
        clear_shared_data()
        if run_dir:
            set_shared_data("run_dir", run_dir)

        agents_run: list[str] = []
        total_tool_calls = 0
        agent_results: dict[str, Any] = {}

        # Start with user message
        messages: list[dict[str, Any]] = [
            {"role": "user", "content": user_query},
        ]

        current_agent_name = "orchestrator"
        total_agents = len(SYSTEM_PROMPTS)  # 3 agents
        agent_idx = 0

        while current_agent_name:
            logger.info(f"=== Running agent: {current_agent_name} ===")

            if on_agent_started:
                on_agent_started(current_agent_name, agent_idx + 1, total_agents)

            agent = Agent(
                name=current_agent_name,
                system_prompt=SYSTEM_PROMPTS[current_agent_name],
                provider=self.provider,
            )

            import time
            t0 = time.monotonic()
            result = agent.run(messages)
            duration = time.monotonic() - t0

            agents_run.append(current_agent_name)
            total_tool_calls += result["tool_calls_made"]
            agent_results[current_agent_name] = {
                "response": result["response"][:500],
                "tool_calls_made": result["tool_calls_made"],
                "handoff_to": result["handoff_to"],
            }

            if on_agent_completed:
                on_agent_completed(current_agent_name, duration)

            agent_idx += 1

            # Build messages for next agent
            if result["handoff_to"]:
                next_agent = result["handoff_to"]
                context_msg = self._build_context_message(current_agent_name, result)

                messages = [
                    {"role": "user", "content": user_query},
                    {"role": "assistant", "content": f"[{current_agent_name}]: {result['response']}"},
                    {"role": "user", "content": context_msg},
                ]
                current_agent_name = next_agent
            else:
                # No handoff — this is the final agent
                current_agent_name = None

        final_response = result["response"]
        logger.info(f"Pipeline complete. Agents run: {agents_run}, Tools called: {total_tool_calls}")

        return {
            "final_response": final_response,
            "agents_run": agents_run,
            "total_tool_calls": total_tool_calls,
            "agent_results": agent_results,
            "shared_data_keys": list(get_shared_data.__module__) if False else None,
        }

    def _build_context_message(
        self,
        from_agent: str,
        result: dict[str, Any],
    ) -> str:
        """Build a compact context message for the next agent.

        Since data flows through the shared store, we only tell the LLM
        what data is available, not the data itself.
        """
        if from_agent == "orchestrator":
            return (
                "The orchestrator has fetched Reddit posts for analysis. "
                "The post data is available in the shared store. "
                "Call classify_posts to analyze complaint themes, then cluster_themes to group them."
            )

        elif from_agent == "analyst":
            return (
                "The analyst has classified and clustered the posts. "
                "The clustering data is available in the shared store. "
                "Call generate_hypotheses to create business ideas, then save_artifact to persist results."
            )

        return f"The {from_agent} agent has completed its work."
