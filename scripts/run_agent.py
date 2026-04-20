"""CLI entry point for the multi-agent Reddit complaint analysis pipeline.

Usage:
    conda activate agentic-ai-p2
    python scripts/run_agent.py "Find business ideas for people struggling with debt"
    python scripts/run_agent.py "What are common complaints about remote work?" --mode live
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))


def _make_run_dir(mode: str) -> Path:
    """Create and return a timestamped run directory: output/reports/YYYY-MM-DD/HHMMSS_MODE/"""
    now = datetime.now()
    run_dir = Path("output") / "reports" / now.strftime("%Y-%m-%d") / f"{now.strftime('%H%M%S')}_{mode}"
    run_dir.mkdir(parents=True, exist_ok=True)
    return run_dir


def main():
    parser = argparse.ArgumentParser(
        description="Multi-agent Reddit complaint analysis pipeline"
    )
    parser.add_argument(
        "query",
        type=str,
        help="Topic or question to analyze (e.g., 'pain points in personal finance')",
    )
    parser.add_argument(
        "--mode",
        choices=["test", "live"],
        default=None,
        help="Agent mode: 'test' uses sample data, 'live' calls Reddit API (default: from AGENT_MODE env var or 'test')",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable debug logging",
    )

    args = parser.parse_args()

    # Override mode if specified
    if args.mode:
        from app.config import set_agent_mode_override
        set_agent_mode_override(args.mode)

    # Import config AFTER mode override is set
    from app.config import config, get_agent_mode  # noqa: F811 – get_agent_mode used below

    # Create run directory and store it for tools/logging to use
    run_dir = _make_run_dir(get_agent_mode())

    from app.agents.tools.shared import set_shared_data
    set_shared_data("run_dir", str(run_dir))

    # Set up logging — writes to the run directory
    from app.agents.logging_setup import setup_agent_logging
    json_logger = setup_agent_logging(log_dir=str(run_dir))

    import logging
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # config already imported above

    print(f"\n{'='*60}")
    print(f"  Reddit Complaint Analysis - Multi-Agent Pipeline")
    print(f"  Query: {args.query}")
    print(f"  Mode:  {config.agent_mode}")
    print(f"  Provider: {config.llm_provider}")
    print(f"  Output: {run_dir}")
    print(f"{'='*60}\n")

    # Run the pipeline
    from app.agents.graph import run_pipeline

    try:
        result = run_pipeline(
            user_query=args.query,
            run_dir=str(run_dir),
        )

        # Print final results
        print(f"\n{'='*60}")
        print(f"  PIPELINE COMPLETE")
        print(f"{'='*60}")
        print(f"\nAgents executed: {' -> '.join(result['agents_run'])}")
        print(f"Total tool calls: {result['total_tool_calls']}")
        print(f"\n{'─'*60}")
        print(f"  FINAL RESPONSE")
        print(f"{'─'*60}")
        print(result["final_response"].encode("utf-8", errors="replace").decode("utf-8"))
        print(f"\n{'─'*60}")

        # Save final response as markdown report
        now = datetime.now()
        report_file = run_dir / "report.md"
        report_file.write_text(
            f"# Reddit Complaint Analysis Report\n\n"
            f"**Query:** {args.query}\n"
            f"**Mode:** {get_agent_mode()}\n"
            f"**Provider:** {config.llm_provider} ({config.gcloud_model})\n"
            f"**Agents:** {' -> '.join(result['agents_run'])}\n"
            f"**Tool calls:** {result['total_tool_calls']}\n"
            f"**Generated:** {now.isoformat()}\n\n"
            f"---\n\n"
            f"{result['final_response']}\n",
            encoding="utf-8",
        )

        print(f"\n  Output directory: {run_dir}/")
        print(f"    report.md")
        for f in sorted(run_dir.iterdir()):
            if f.name != "report.md":
                print(f"    {f.name}")
        print()

    except KeyboardInterrupt:
        print("\n\nPipeline interrupted by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\nERROR: Pipeline failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
