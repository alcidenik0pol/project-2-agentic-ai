"""Base agent class with tool execution loop and handoff detection."""

import json
import logging
import re
from typing import Any

from app.agents.tools import execute_tool, get_tool_schemas
from app.analyst.providers.base import LLMProvider
from app.config import config
from app.utils.timing import timed

logger = logging.getLogger(__name__)

# Pattern to detect handoff markers in agent responses
HANDOFF_PATTERN = re.compile(r"HANDOFF_TO_AGENT:\s*(\w+)")


class Agent:
    """Base agent: sends messages + tools to LLM, executes tool calls, detects handoffs.

    Uses LLMProvider.chat_with_tools() for provider-agnostic LLM interaction.
    Works with gcloud (service account), lm_studio (local), or openai_gemini (API key).
    """

    def __init__(
        self,
        name: str,
        system_prompt: str,
        provider: LLMProvider,
    ):
        self.name = name
        self.system_prompt = system_prompt
        self.provider = provider
        self.tool_schemas = get_tool_schemas(name)

    @timed("agent_run")
    def run(
        self,
        messages: list[dict[str, Any]],
        max_iterations: int | None = None,
    ) -> dict[str, Any]:
        """Run the agent's tool execution loop.

        Sends messages to the LLM. If the LLM requests tool calls,
        executes them and feeds results back. Repeats until the LLM
        returns a text-only response or max iterations reached.

        Args:
            messages: Conversation messages so far (user + prior agent context).
            max_iterations: Max tool-calling rounds. Defaults to config.agent_max_iterations.

        Returns:
            {
                "response": str,           # Final text response from LLM
                "handoff_to": str | None,  # Name of next agent if handoff detected
                "tool_calls_made": int,     # Count of tool calls executed
                "messages": list,           # Full message history
            }
        """
        if max_iterations is None:
            max_iterations = config.agent_max_iterations

        all_messages = [{"role": "system", "content": self.system_prompt}] + messages
        tool_calls_made = 0

        for iteration in range(max_iterations):
            logger.info(f"[{self.name}] Iteration {iteration + 1}/{max_iterations}")

            # Call LLM via provider abstraction
            response = self.provider.chat_with_tools(
                messages=all_messages,
                tools=self.tool_schemas,
                temperature=0.3,
            )

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

            # If no tool calls, check for handoff or return final response
            if not response.tool_calls:
                final_text = response.content or ""
                handoff_to = self._detect_handoff(final_text)
                # Strip handoff marker from the response text
                clean_text = HANDOFF_PATTERN.sub("", final_text).strip()

                return {
                    "response": clean_text,
                    "handoff_to": handoff_to,
                    "tool_calls_made": tool_calls_made,
                    "messages": all_messages,
                }

            # Execute each tool call
            for tool_call in response.tool_calls:
                tool_name = tool_call.name
                tool_args_str = tool_call.arguments

                logger.info(f"[{self.name}] Tool call: {tool_name}")
                try:
                    tool_args = json.loads(tool_args_str)
                except json.JSONDecodeError:
                    tool_args = {}

                tool_result = execute_tool(tool_name, tool_args)
                tool_calls_made += 1

                # Truncate oversized results before adding to messages
                tool_result = self._truncate_tool_result(tool_name, tool_result, iteration)

                # Add tool result to messages
                all_messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": tool_result,
                })

                logger.info(f"[{self.name}] Tool result: {tool_result[:200]}...")

        # Max iterations reached
        return {
            "response": "Maximum iterations reached. Processing may be incomplete.",
            "handoff_to": None,
            "tool_calls_made": tool_calls_made,
            "messages": all_messages,
        }

    def _detect_handoff(self, text: str) -> str | None:
        """Check if the response contains a handoff marker."""
        match = HANDOFF_PATTERN.search(text)
        if match:
            target = match.group(1).lower()
            logger.info(f"[{self.name}] Handoff detected: -> {target}")
            return target
        return None

    def _truncate_tool_result(
        self,
        tool_name: str,
        result: str,
        iteration: int,
    ) -> str:
        """Truncate oversized tool results to prevent context overflow.

        Stores full result in shared data store and returns a compact summary.

        Args:
            tool_name: Name of the tool that produced the result
            result: Full tool result (potentially large JSON)
            iteration: Current iteration number (for shared key uniqueness)

        Returns:
            Either the original result (if small enough) or a summary JSON string
        """
        max_size = config.agent_tool_result_max_size
        enable_truncation = config.agent_tool_result_enable_truncation

        if not enable_truncation:
            logger.debug(f"Result truncation disabled, returning full result for {tool_name}")
            return result

        result_size = len(result)
        if result_size <= max_size:
            logger.debug(f"Tool {tool_name} result size ({result_size} chars) within threshold")
            return result

        # Don't truncate error messages
        try:
            result_json = json.loads(result)
            if isinstance(result_json, dict) and "error" in result_json:
                logger.debug("Result is an error, returning full message")
                return result
        except json.JSONDecodeError:
            pass

        # Result is too large - truncate it
        preview_length = config.agent_tool_result_preview_chars
        shared_key = f"tool_result_{tool_name}_{iteration}"

        # Store full result in shared data
        from app.agents.tools.shared import set_shared_data
        set_shared_data(shared_key, result)

        # Create preview
        preview = result[:preview_length]
        if result_size > preview_length:
            preview += "..."

        summary = {
            "status": "truncated",
            "tool_name": tool_name,
            "original_size": result_size,
            "summary_size": len(preview),
            "shared_key": shared_key,
            "preview": preview,
            "message": (
                f"Full result (~{result_size // 1024}KB) stored in shared data "
                f"to prevent context overflow. Access via key '{shared_key}'"
            ),
        }

        summary_json = json.dumps(summary, ensure_ascii=False)

        logger.warning(
            f"[{self.name}] Truncated tool result for {tool_name}: "
            f"{result_size} chars → {len(summary_json)} chars "
            f"(stored in shared data as '{shared_key}')"
        )

        return summary_json
