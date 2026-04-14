"""Structured logging for the agent framework.

Provides:
- JSON file handler (logs/agent_run_*.jsonl)
- Pretty console handler with timestamps and agent names
"""

import json
import logging
from datetime import datetime
from pathlib import Path


class AgentEventLogger(logging.Handler):
    """Custom handler that writes structured JSON events to a .jsonl file."""

    def __init__(self, log_dir: str = "logs"):
        super().__init__()
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_file = self.log_dir / f"agent_run_{timestamp}.jsonl"
        self._file = open(self.log_file, "a", encoding="utf-8")

    def emit(self, record: logging.LogRecord) -> None:
        event = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        # Add agent name if present
        if hasattr(record, "agent_name"):
            event["agent"] = record.agent_name
        if hasattr(record, "tool_name"):
            event["tool"] = record.tool_name

        self._file.write(json.dumps(event, ensure_ascii=False) + "\n")
        self._file.flush()

    def close(self) -> None:
        self._file.close()
        super().close()


class PrettyConsoleFormatter(logging.Formatter):
    """Console formatter with colors and structured output."""

    AGENT_COLORS = {
        "orchestrator": "\033[94m",   # Blue
        "analyst": "\033[92m",        # Green
        "hypothesis": "\033[93m",     # Yellow
    }
    RESET = "\033[0m"
    BOLD = "\033[1m"

    def format(self, record: logging.LogRecord) -> str:
        timestamp = datetime.now().strftime("%H:%M:%S")

        # Detect agent name from logger path
        agent_name = ""
        for name, color in self.AGENT_COLORS.items():
            if name in record.getMessage().lower() or name in record.name:
                agent_name = name
                break

        # Format based on level
        if record.levelno >= logging.ERROR:
            level_str = f"\033[91m{record.levelname}\033[0m"
        elif record.levelno >= logging.WARNING:
            level_str = f"\033[93m{record.levelname}\033[0m"
        else:
            level_str = record.levelname

        msg = record.getMessage()

        # Truncate long messages for console
        if len(msg) > 300:
            msg = msg[:300] + "..."

        prefix = f"{timestamp} [{level_str}]"
        if agent_name:
            color = self.AGENT_COLORS[agent_name]
            prefix += f" {color}[{agent_name}]{self.RESET}"

        return f"{prefix} {msg}"


def setup_agent_logging(
    log_dir: str | None = None,
    preserve_handlers: list[logging.Handler] | None = None,
) -> AgentEventLogger:
    """Set up logging for the agent framework.

    Configures:
    - JSON file handler writing to log_dir/agent_run.jsonl
    - Pretty console handler with timestamps

    Args:
        log_dir: Directory for the JSONL log file. Defaults to "logs".
        preserve_handlers: Handlers to keep when clearing existing handlers.
            Useful for preserving WebSocket or other streaming handlers that
            were added before this function is called.

    Returns:
        The AgentEventLogger for access to the log file path.
    """
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    # Preserve specified handlers, remove others to avoid duplicates
    preserve = set(preserve_handlers or [])
    root_logger.handlers = [h for h in root_logger.handlers if h in preserve]

    # Console handler with pretty formatting
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(PrettyConsoleFormatter())
    root_logger.addHandler(console_handler)

    # JSON file handler
    json_handler = AgentEventLogger(log_dir=log_dir or "logs")
    json_handler.setLevel(logging.INFO)
    root_logger.addHandler(json_handler)

    return json_handler
